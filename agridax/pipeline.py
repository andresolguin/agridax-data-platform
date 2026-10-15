from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from .admin import initialize_database, wait_ready
from .config import PROJECT_ROOT, Settings
from .database import RAW_TABLES, connect, single_writer
from .publication import CommitOutcomeUnknown, candidate_fingerprints, publish_marts
from .time_contract import backfill_range

DBT_PROJECT = PROJECT_ROOT / "dbt/agridax"


def dbt_executable() -> str:
    path = Path(sys.executable).parent / ("dbt.exe" if os.name == "nt" else "dbt")
    if not path.is_file():
        raise RuntimeError("dbt is absent from this Python environment; install requirements.txt")
    return str(path)


def run_dbt(command: str, run_id: str, variables: dict, token: str, *, full_refresh: bool = False) -> dict:
    target = DBT_PROJECT / "target/runs" / run_id / command.replace(" ", "_")
    target.mkdir(parents=True,exist_ok=False)
    args = [dbt_executable(),*command.split(),"--project-dir",str(DBT_PROJECT),
            "--profiles-dir",str(DBT_PROJECT),"--target","dev",
            "--log-path",str(DBT_PROJECT / "logs/runs" / run_id / command)]
    if command != "debug":
        args.extend(["--target-path",str(target),"--vars",json.dumps(variables)])
    if full_refresh:
        args.append("--full-refresh")
    env = dict(os.environ, DBT_ENV_SECRET_RUN_TOKEN=token, DBT_SEND_ANONYMOUS_USAGE_STATS="false",
               DBT_EMPTY="false",DBT_DEFER="false",DBT_FAVOR_STATE="false",DBT_FULL_REFRESH="false")
    completed = subprocess.run(args,cwd=PROJECT_ROOT,env=env,check=False)
    if completed.returncode:
        raise RuntimeError(f"dbt {command} failed with exit {completed.returncode}; candidate is not publishable")
    if command == "debug":
        return {"exit_code":0}
    name = "sources.json" if command == "source freshness" else "run_results.json"
    artifact = target / name
    if not artifact.exists():
        raise RuntimeError(f"Fresh {name} was not produced in the unique target directory")
    data = json.loads(artifact.read_text())
    metadata = data.get("metadata",{})
    artifact_env = {str(k).lower(): v for k, v in metadata.get("env", {}).items()}

    if not metadata.get("invocation_id") or artifact_env.get("agridax_run_id") != run_id:
      raise RuntimeError("dbt artifact provenance does not match this run")
    statuses = [str(r.get("status", "")).lower() for r in data.get("results",[])]
    if any(s not in {"success","pass","warn"} for s in statuses):
        raise RuntimeError("Artifact contains an unsuccessful resource")
    if command == 'build':
        manifest=json.loads((target/'manifest.json').read_text())
        expected={key for key,node in manifest['nodes'].items() if node.get('package_name')=='agridax' and node.get('resource_type') in {'model','snapshot','test'}}
        actual={result['unique_id'] for result in data.get('results',[])}
        if not expected or not expected.issubset(actual) or data.get('args',{}).get('empty') or data.get('args',{}).get('defer'):
            raise RuntimeError('A complete non-empty-mode, non-deferred build of the platform is required')
    else:
        expected={'source.agridax.raw.'+name for name in RAW_TABLES}
        if {result['unique_id'] for result in data.get('results',[])} != expected:
            raise RuntimeError('Freshness must cover all five sources')
    return {"invocation_id":metadata["invocation_id"],"results":len(statuses),
            "tests":sum(result['unique_id'].startswith('test.') for result in data.get('results',[])),
            "warn":statuses.count("warn"),"artifact_sha256":hashlib.sha256(artifact.read_bytes()).hexdigest()}


def source_health(horizon) -> dict:
    with connect("dbt") as conn:
        for table in RAW_TABLES:
            future = conn.execute(f"select count(*) from raw.{table} where ingested_at > %s", (horizon,)).fetchone()[0]
            if future:
                raise RuntimeError(f"RAW {table} has {future} future ingestion timestamps; resolve metadata explicitly")
        ahead = conn.execute("select count(*) from ops.processing_checkpoints where processed_through > %s", (horizon,)).fetchone()[0]
        if ahead:
            raise RuntimeError("Processing clock is behind a persisted checkpoint; no automatic rewind is allowed")
        return {"future_ingestion_rows":0,"checkpoint_ahead":0}


def run_pipeline(*, initialize: bool = False, create_raw: bool = False, seed_baseline: bool = False,
                 skip_publish: bool = False, full_refresh: bool = False,
                 backfill_start: str | None = None, backfill_end: str | None = None,
                 readiness_timeout: int = 90, simulate_failure_after_copy: int | None = None,
                 dbt_vars: dict | None = None) -> str:
    bounds = backfill_range(backfill_start,backfill_end,full_refresh)
    settings = Settings.load()
    settings.validate_all()
    if initialize:
        initialize_database(create_raw=create_raw)
    elif create_raw:
        raise ValueError("--create-raw requires --initialize and is an explicit empty-database setup")
    if initialize:
        wait_ready(readiness_timeout)
    if seed_baseline:
        from data_generator.seed_initial_data import load_baseline
        load_baseline()
    run_id = str(uuid.uuid4())
    token = "agri_dbt_" + uuid.uuid4().hex
    os.environ["DBT_ENV_CUSTOM_ENV_agridax_run_id"] = run_id
    publication_completed = False
    with connect("publish",autocommit=True) as conn, single_writer(conn):
        horizon, pid = conn.execute("select clock_timestamp(), pg_backend_pid()").fetchone()
        if bounds:
            for relation in ("stg_field_event_winners","stg_weather_observation_winners"):
                if conn.execute("select to_regclass(%s)",(f"analytics.{relation}",)).fetchone()[0] is None:
                    raise ValueError("Bounded backfill requires existing canonical targets; first run is refused")
        conn.execute("insert into ops.pipeline_runs(run_id,processing_horizon,lock_owner_pid,dbt_application_hash,run_kind,backfill_start,backfill_end,status) "
                     "values(%s,%s,%s,%s,%s,%s,%s,'building')",
                     (run_id,horizon,pid,hashlib.md5(token.encode()).hexdigest(),
                      "backfill" if bounds else "full_refresh" if full_refresh else "normal",
                      bounds[0] if bounds else None,bounds[1] if bounds else None))
        try:
            evidence = {"run_id":run_id,"health":source_health(horizon)}
            variables = dict(dbt_vars or {})
            forbidden = {"release_run_id","processing_horizon","ingestion_lookback_seconds","backfill_start","backfill_end"} & variables.keys()
            if forbidden:
                raise ValueError("Operational variables are owned by the coordinator")
            if variables.keys() - {"weather_freshness_warn_minutes","weather_freshness_error_minutes"}:
                raise ValueError("Only weather freshness count overrides are supported")
            warn = variables.get("weather_freshness_warn_minutes",90)
            error = variables.get("weather_freshness_error_minutes",180)
            if type(warn) is not int or type(error) is not int or not 0 < warn < error:
                raise ValueError("Weather freshness requires integer 0 < warn < error")
            evidence["freshness_policy"] = {"gate":"all-source ERROR blocks publication; WARN allowed", "weather_warn_minutes":warn,"weather_error_minutes":error}
            variables.update(release_run_id=run_id,processing_horizon=horizon.isoformat(),ingestion_lookback_seconds=settings.lookback_seconds)
            if bounds:
                variables.update(backfill_start=bounds[0].isoformat(),backfill_end=bounds[1].isoformat())
            evidence["debug"] = run_dbt("debug",run_id,variables,token)
            evidence["build"] = run_dbt("build",run_id,variables,token,full_refresh=full_refresh)
            with connect('dbt') as health_conn:
                evidence['quality_health']={
                    'invalid_current_events':health_conn.execute('select count(*) from analytics.stg_field_event_winners where rejection_reason is not null').fetchone()[0],
                    'invalid_current_weather':health_conn.execute('select count(*) from analytics.stg_weather_observation_winners where rejection_reason is not null').fetchone()[0],
                    'quarantined_physical_events':health_conn.execute('select count(*) from analytics.quarantine_field_events').fetchone()[0],
                    'quarantined_physical_weather':health_conn.execute('select count(*) from analytics.quarantine_weather_observations').fetchone()[0],
                    'unassigned_closing_harvests':health_conn.execute("select count(*) from analytics.int_harvest_cycle_assignment where assignment_status<>'closing_harvest'").fetchone()[0],
                    'undated_event_deliveries':health_conn.execute('select count(*) from raw.field_events where source_updated_at is null').fetchone()[0],
                    'undated_weather_deliveries':health_conn.execute('select count(*) from raw.weather_observations where source_updated_at is null').fetchone()[0],
                }
            scans = conn.execute("select count(*) from ops.processing_scans where run_id=%s", (run_id,)).fetchone()[0]
            if scans != 2:
                raise RuntimeError("Both canonical streams must record processing evidence")
            evidence["freshness"] = run_dbt("source freshness",run_id,variables,token)
            evidence.update(build_passed=True,freshness_passed=True)
            fingerprints = candidate_fingerprints(conn)
            conn.execute("update ops.pipeline_runs set status='validated',evidence=%s,candidate_fingerprints=%s where run_id=%s",
                         (Jsonb(evidence),Jsonb(fingerprints),run_id))
            if not skip_publish:
                publish_marts(conn,run_id,simulate_failure_after_copy=simulate_failure_after_copy)
                publication_completed = True
            print(f"Run {run_id}: {'validated, not published' if skip_publish else 'published'}")
            return run_id
        except Exception as exc:
            # A lost connection while COMMIT is attempted does not prove rollback.
            unknown = isinstance(exc, CommitOutcomeUnknown)
            if not conn.closed and not conn.broken:
                try:
                    conn.execute("update ops.pipeline_runs set status=%s,completed_at=clock_timestamp() where run_id=%s and status<>'published'",
                                 ("commit_unknown" if unknown else "failed",run_id))
                except psycopg.Error:
                    print(f"Unable to record failure status for {run_id}; preserve the original error and reconcile the release marker.",file=sys.stderr)
            print(f"Run {run_id} failed. " + ("Commit outcome unknown; reconcile ops.releases." if unknown else "Release committed; reporting failed." if publication_completed else "No successful release was confirmed."),file=sys.stderr)
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Single-writer build, validation, arrival freshness and atomic publication")
    parser.add_argument("--initialize",action="store_true")
    parser.add_argument("--create-raw",action="store_true",help="Explicit setup of an empty non-Docker database; never a reset")
    parser.add_argument("--seed-baseline",action="store_true")
    parser.add_argument("--skip-publish",action="store_true")
    parser.add_argument("--full-refresh",action="store_true")
    parser.add_argument("--backfill-start")
    parser.add_argument("--backfill-end")
    parser.add_argument("--readiness-timeout",type=int,default=90)
    parser.add_argument("--simulate-failure-after-copy",type=int,choices=range(1,6),help="TEST ONLY")
    parser.add_argument("--weather-warn-minutes",type=int,help="Operational validation override; recorded in evidence")
    parser.add_argument("--weather-error-minutes",type=int,help="Operational validation override; recorded in evidence")
    args = parser.parse_args()
    if not 1 <= args.readiness_timeout <= 600:
        parser.error("readiness timeout must be 1 through 600 seconds")
    options=vars(args)
    overrides={}
    for arg,var in [("weather_warn_minutes","weather_freshness_warn_minutes"),("weather_error_minutes","weather_freshness_error_minutes")]:
        value=options.pop(arg)
        if value is not None: overrides[var]=value
    run_pipeline(**options,dbt_vars=overrides)


if __name__ == "__main__":
    main()
