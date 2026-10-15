# AgriDax Data Platform

AgriDax is an analytical data platform for agricultural operations, field events, weather, sustainability practices and crop-cycle analytics. The executable local implementation uses PostgreSQL 16, dbt Core, Python, Docker Compose and PowerShell. GCP with BigQuery is the target deployment architecture; it is not deployed by this working tree.

## Local architecture

| Schema | Responsibility |
|---|---|
| raw | Durable physical source deliveries, corrections, retries and metadata |
| analytics | Canonical winners, valid trusted views, physical quarantine, intermediate transformations and candidate marts |
| snapshots | Warehouse-observed changes to current field state; separate from business history |
| published | Stable consumer tables with atomic transactional row replacement |
| ops | Processing windows/checkpoints, managed run evidence and accepted release markers |

Business field history is reconstructed from RAW at `(field_id,effective_from)`. Events join the half-open business interval `[valid_from,valid_to)`. Current dimensions are not used to infer historical field context. Snapshots record observed current-state changes at a timezone-aware warehouse_observed_at; they do not reconstruct versions that were never observed.

Events and weather discover changed logical keys using ingestion windows, then resolve their winner against all RAW revisions for those keys. A canonical winner may be invalid; trusted views filter its rejection_reason. A newer invalid revision therefore removes the prior trusted value. Physical quarantine retains every rejected delivery after a key recovers. Dated source revisions take priority over undated deliveries; all-undated keys use latest arrival and do not guarantee protection against stale undated replay.

The coordinator freezes cooperating ingestion while it selects a per-run upper horizon, builds the complete DAG, runs tests/arrival freshness and promotes the same candidate generation. Normal progress is persisted independently of winners. Backfills do not move normal checkpoints. Progress is not accepted-release state and is not event-time completeness.

## Setup from the working tree

Use Python **3.12**, Docker Desktop/Compose v2 with `up --wait`, and PowerShell 5.1 or 7 on Windows. Run installation commands from the extracted working-tree root. There is no published repository/remote required for this setup.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\scripts\configure_env.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

The configuration helper generates unique private local credentials in ignored `.env`, without printing them or overwriting an existing file. Alternatively copy `.env.example` to `.env` and replace **all** password placeholders. Literal placeholders are rejected. Existing process environment variables take precedence, including empty values (which fail validation). Quoted values use standard python-dotenv semantics. Credentials are never supplied by a hidden user-level dbt profile.

Bootstrap validates configuration, starts Compose with bounded authenticated TCP/schema health, checks the required RAW columns/types/identity keys, applies checked operational migrations and workload grants, seeds the baseline, executes dbt debug/build/freshness and promotes. Docker or any subsequent failure stops the flow. Baseline is transactional and rerunnable; an incomplete baseline batch fails explicitly. A rerun does not change RAW timestamps or business counts; it creates new run/release evidence when eligible. As unchanged fixtures age, arrival freshness can warn/fail: it is not a continuously refreshed source feed.

The Linux equivalent, when a Docker engine is available:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/configure_env.py
docker compose up -d --wait --wait-timeout 90
.venv/bin/python -m agridax.pipeline --initialize --seed-baseline
```

Workload roles are separate: ingest appends/reads RAW, dbt reads RAW and owns analytics/snapshots, publication reads candidate marts and owns published, reader selects published/release metadata. Admin credentials are used only for explicit initialization/migrations. PostgreSQL is bound to 127.0.0.1. This local credential file does not isolate secrets from other processes owned by the same local OS account.

## Supported operations

After installation, use the same Python environment:

```powershell
.\.venv\Scripts\python.exe -m agridax.pipeline
.\.venv\Scripts\python.exe -m agridax.pipeline --skip-publish
.\.venv\Scripts\python.exe -m agridax.pipeline --full-refresh
.\.venv\Scripts\python.exe -m agridax.pipeline --backfill-start "2026-10-12T09:00:00-03:00" --backfill-end "2026-10-12T13:00:00Z"
```

Both backfill bounds are required, include seconds and an explicit Z/±HH:MM offset, and define `[start,end)` on **ingested_at**. Equal/reversed/malformed ranges, first-run bounded backfills and bounded + full-refresh are rejected. Supported recovery always rebuilds the complete platform and validates descendants. Bounded key discovery is not bounded end-to-end compute: marts, checksums and global winner reconciliation can scan/rebuild the full dataset. See [recovery](docs/recovery.md).

Standalone publisher invocation and unmanaged mutating dbt commands are refused. Read-only inspection remains available from the root, using the local profile:

```powershell
.\.venv\Scripts\python.exe -m agridax.inspect_dbt debug
.\.venv\Scripts\python.exe -m agridax.inspect_dbt parse
.\.venv\Scripts\python.exe -m agridax.inspect_dbt compile
.\.venv\Scripts\python.exe -m agridax.inspect_dbt source-freshness
```

The inspection wrapper loads the same private dotenv and fixes the local profile/paths; dbt itself does not load .env automatically. A standalone test/freshness artifact is inspection, not eligibility for publication. The coordinator uses unique per-run targets, checks every required build resource, records invocation IDs/content hashes and refuses a changed candidate.

## Quality and freshness

| Source | Arrival WARN | Arrival ERROR |
|---|---:|---:|
| field_events | 15 minutes | 60 minutes |
| weather_observations | 90 minutes | 180 minutes |
| farms/fields/sustainability_practices | 24 hours | 36 hours |

All-source ERROR is a global publication gate. WARN remains eligible and is recorded. Only weather count overrides are supported; `--weather-warn-minutes` / `--weather-error-minutes` are operational-validation options recorded in evidence. They do not modify RAW timestamps. Aggregate max RAW arrival can hide a stopped producer or recent invalid/retry traffic; persisted quality counts supplement it without claiming per-producer health or alerts.

Daily flags mean source presence, not complete 24-hour coverage. No calendar spine is implemented: a field/day without both sources has no row. Measured zero, NULL measurement and absent source remain distinct. Weather temperature has no invented range; finite measurements, humidity 0–100 and non-negative rainfall/wind are validated.

Crop cycles open at planting and close at the first eligible harvest before next planting. Without harvest, a next planting marks the earlier cycle superseded; otherwise it remains open. Distinct simultaneous plantings fail validation. Additional/orphan harvests are reconciled in int_harvest_cycle_assignment and remain in event/daily facts. Yield is FIRST closing harvest kg / whole-field area valid at planting, not total cycle production or planted-area yield.

## Publication contract

The five marts dim_farms, dim_fields, fct_crop_cycles, fct_field_daily_performance and fct_field_events are stable tables. Candidate verification, DELETE + INSERT of all five, copied-content verification and the release marker execute in one REPEATABLE READ transaction. OIDs, reader grants, indexes, comments, constraints and dependent read views are retained. Schema/PK changes require explicit migration. Arbitrary external foreign keys are not supported; an incompatible dependency/constraint fails safely rather than being dropped. No CASCADE is used for publication.

Readers needing one cohort across several queries use one REPEATABLE READ read-only transaction. Independent queries can straddle a release. Single-writer locks cover the managed build and promotion; this is not a multi-writer system. A connection loss during COMMIT can leave outcome unknown: reconcile ops.releases by run_id rather than claiming rollback.

## Validation and publication preflight

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m agridax.acceptance --docker
.\.venv\Scripts\python.exe -m agridax.preflight
```

Docker acceptance creates and removes only a uniquely named disposable Compose project/volume. It checks clean setup, PowerShell bootstrap/rerun, adversarial data, recovery, publication and native login/locking. A missing PowerShell executable is recorded as NOT RUN and makes complete Docker acceptance fail. It does not reset the normal volume. `--existing-disposable --allow-reset` additionally requires a prefixed PostgreSQL16 database and tests the native SQL path separately from bootstrap. Embedded diagnostics explicitly exclude native auth/concurrency and cannot count as complete native acceptance.

Current execution evidence and remaining acceptance gates are in FINAL_AUDIT.md and VALIDATION_EVIDENCE.md. The audit environment did not provide Docker/PowerShell; no native clean-volume/bootstrap claim is made from its embedded tests. No measured production scale, operating SLA or cloud deployment is asserted.

`agridax-preflight --staged` inspects already-staged content through read-only Git commands; it never stages, commits or pushes. The heuristic scan supplements review and does not prove absence of every possible secret. See [runtime/dependencies](docs/runtime_and_dependencies.md), [contracts](docs/raw_data_contracts.md), [fixtures](docs/fixtures.md), [requirements](docs/requirements.md) and [ADRs](docs/adr).
