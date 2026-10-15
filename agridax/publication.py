from __future__ import annotations

import argparse

from psycopg import sql
from psycopg.types.json import Jsonb
import psycopg
from psycopg.pq import TransactionStatus
from .config import Settings

class CommitOutcomeUnknown(RuntimeError):
    """COMMIT was attempted without a definitive connection-level result."""


MART_KEYS = {
    "dim_farms": ("farm_id",),
    "dim_fields": ("field_id",),
    "fct_crop_cycles": ("crop_cycle_id",),
    "fct_field_daily_performance": ("field_id", "business_date"),
    "fct_field_events": ("source_system", "source_event_id"),
}


def candidate_fingerprints(conn, schema: str = 'analytics') -> dict:
    """Full content fingerprint for local provenance, not a benchmark/large-scale design."""
    result = {}
    for mart in MART_KEYS:
        cur = conn.execute(sql.SQL(
            "select count(*), md5(coalesce(string_agg(to_jsonb(t)::text, E'\\n' "
            "order by to_jsonb(t)::text), '')) from {}.{} t"
        ).format(sql.Identifier(schema), sql.Identifier(mart)))
        count, digest = cur.fetchone()
        result[mart] = {"rows": count, "md5": digest, "columns": columns(conn, schema, mart)}
    return result


def columns(conn, schema: str, table: str) -> list:
    return [list(row) for row in conn.execute(
        "select a.attname, format_type(a.atttypid,a.atttypmod) "
        "from pg_attribute a join pg_class c on c.oid=a.attrelid "
        "join pg_namespace n on n.oid=c.relnamespace "
        "where n.nspname=%s and c.relname=%s and a.attnum>0 and not a.attisdropped "
        "order by a.attnum", (schema,table)
    ).fetchall()]


def require_validated_run(conn, run_id: str) -> tuple[dict, dict]:
    row = conn.execute(
        "select status, lock_owner_pid, evidence, candidate_fingerprints "
        "from ops.pipeline_runs where run_id=%s", (run_id,)
    ).fetchone()
    if not row or row[0] != "validated" or row[1] != conn.execute("select pg_backend_pid()").fetchone()[0]:
        raise RuntimeError("Publication requires the live coordinator of a freshly validated run")
    locks = conn.execute(
        "select count(*) from pg_locks where locktype='advisory' and classid=8142026::oid "
        "and objid in (1::oid,2::oid) and objsubid=2 and mode='ExclusiveLock' "
        "and granted and pid=pg_backend_pid()"
    ).fetchone()[0]
    if locks != 2:
        raise RuntimeError("Publication lost its single-writer / ingestion locks")
    evidence, expected = row[2], row[3]
    if evidence.get("run_id") != run_id or not evidence.get("build_passed") or not evidence.get("freshness_passed"):
        raise RuntimeError("Validation evidence is incomplete or belongs to another run")
    if candidate_fingerprints(conn) != expected:
        raise RuntimeError("Candidate changed after validation; rebuild instead of promoting it")
    return evidence, expected


def publish_marts(conn, run_id: str, *, simulate_failure_after_copy: int | None = None) -> None:
    if simulate_failure_after_copy is not None and simulate_failure_after_copy not in range(1,len(MART_KEYS)+1):
        raise ValueError("TEST ONLY failure position must be 1 through 5")
    if not conn.autocommit or conn.info.transaction_status != TransactionStatus.IDLE:
        raise RuntimeError('Publication requires an idle autocommit coordinator connection')
    # Data replacement and release evidence are committed together. No DROP/CASCADE.
    phase = "write"
    try:
        with conn.transaction():
            conn.execute('set transaction isolation level repeatable read')
            evidence, expected = require_validated_run(conn, run_id)
            for position, (mart, keys) in enumerate(MART_KEYS.items(),1):
                relation = sql.Identifier("published",mart)
                candidate = sql.Identifier("analytics",mart)
                exists = conn.execute("select to_regclass(%s)", (f"published.{mart}",)).fetchone()[0]
                if not exists:
                    conn.execute(sql.SQL("create table {} as select * from {} with no data").format(relation,candidate))
                primary = conn.execute(
                    "select array_agg(a.attname order by k.ordinality) "
                    "from pg_constraint c cross join lateral unnest(c.conkey) with ordinality k(attnum,ordinality) "
                    "join pg_attribute a on a.attrelid=c.conrelid and a.attnum=k.attnum "
                    "where c.conrelid=to_regclass(%s) and c.contype='p'", (f"published.{mart}",)
                ).fetchone()[0]
                if primary is None:
                    conn.execute(sql.SQL("alter table {} add primary key ({})").format(
                        relation, sql.SQL(",").join(sql.Identifier(k) for k in keys)))
                elif list(primary) != list(keys):
                    raise RuntimeError(f"Published primary key differs for {mart}; explicit migration is required")
                if columns(conn,"published",mart) != expected[mart]["columns"]:
                    raise RuntimeError(f"Published schema differs for {mart}; apply an explicit schema migration")
                names = sql.SQL(",").join(sql.Identifier(c[0]) for c in expected[mart]["columns"])
                conn.execute(sql.SQL("delete from {}").format(relation))
                conn.execute(sql.SQL("insert into {} ({}) select {} from {}").format(relation,names,names,candidate))
                reader=Settings.load().credentials("reader")[0]
                conn.execute(sql.SQL("grant select on {} to {}").format(relation,sql.Identifier(reader)))
                if simulate_failure_after_copy == position:
                    raise RuntimeError(f"TEST ONLY: simulated publication failure after copy {position}")
            if candidate_fingerprints(conn, 'published') != expected:
                raise RuntimeError('Published content differs from the validated candidate; rollback is required')
            conn.execute("insert into ops.releases(release_id,evidence,candidate_fingerprints) values(%s,%s,%s)",
                         (run_id,Jsonb(evidence),Jsonb(expected)))
            conn.execute("update ops.pipeline_runs set status='published',completed_at=clock_timestamp() where run_id=%s", (run_id,))
            phase = "commit"
    except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
        if phase == "commit" and (exc.sqlstate is None or exc.sqlstate.startswith("08")):
            raise CommitOutcomeUnknown(f"Commit result unknown for {run_id}; reconcile ops.releases") from exc
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Publication is coordinated with build/validation by agridax-release")
    parser.parse_args()
    parser.error("Standalone publication is refused. Use python -m agridax.pipeline; no table-name-only promotion is supported.")


if __name__ == "__main__":
    main()
