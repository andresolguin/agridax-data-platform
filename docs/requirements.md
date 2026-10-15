# AgriDax implementation requirements

## Implemented local scope

Executable PostgreSQL16 + dbt Core + Python transformations, fixture generators, PowerShell/Docker startup and managed releases. Five RAW physical-delivery tables, canonical state/revision selection, trusted/quarantine views, RAW-derived field history, separate observed current-state snapshot, daily and cycle analytics, validation, global arrival-freshness gate, stable published tables and an operational ledger are implemented in source.

Data fixtures are reproducible inputs, not live agricultural connectors. No hidden CSV file or manually inserted database row is required. No GitHub remote/repository is configured by the platform. GCP/BigQuery deployment is a target and is not implemented. Runtime execution limits are reported separately; source existence is not proof of native validation.

## Required correctness invariants

1. RAW is append-only for the workload role, preserves deliveries and has no logical uniqueness/FKs.
2. Event grain is normalized source_system + source_event_id; weather grain is normalized field_id + observed_at. Windows discover keys; all versions of affected keys select a canonical winner. Dated source update sorts before NULL, then ingestion and physical identity break ties.
3. Invalid current winners retain rejection metadata and cannot leave an old valid row visible in trusted. Physical quarantine is independent of logical current state.
4. Field-state grain is field_id + effective_from. Corrections keep that state identity. History uses consecutive business starts; intervals are half-open and bounded intervals positive. Current state is the greatest effective_from at/before the managed horizon. Historical enrichment never uses current dimensions.
5. Source update, arrival, business validity, processing progress and warehouse observation are distinct. Snapshots capture current-state attribute/source-update changes observed between runs; ingestion-only retries do not create versions. Observed history cannot be reconstructed as if missing observations had happened.
6. A measured quantity zero remains zero and contributes activity coverage. NULL is not replaced by a blanket zero. Weather NULL measurements are supported; missing both daily sources produces no row.
7. Independent ingestion/checkpoint assumptions must be explicit. Invalid/non-winning window rows are counted. Backfill never rewinds/advances normal progress. Complete RAW winner reconciliation protects publication from missed changes.
8. Only one managed build/promotion may run. Required resources, health and freshness must pass under fresh invocation evidence; candidate fingerprints must still match.
9. Consumer promotion is one transaction across all five stable marts and its release marker. Data/OIDs/grants/views must survive a confirmed rollback. Connection-level COMMIT uncertainty is reported and reconciled by release ID.

## Models and grains

Staging: stg_farms, stg_fields, stg_sustainability_practices are current views; stg_field_state_winners is a view at field/effective-from grain. stg_field_event_winners and stg_weather_observation_winners are canonical incrementals including rejected winners. stg_field_events and stg_weather_observations are valid projections. quarantine_field_events and quarantine_weather_observations have physical raw_record_id grain.

Intermediate: int_field_history (business state), int_field_events_with_history (logical event, exactly one match), int_field_daily_activity and int_field_daily_weather (field/UTC date before joining), int_field_daily_conditions (union of date keys), int_field_sustainability_metrics (current reported field practice flags), int_field_crop_cycles (logical planting), int_harvest_cycle_assignment (logical harvest diagnostics).

Marts: dim_farms (farm), dim_fields (field), fct_field_events (logical event), fct_field_daily_performance (field/UTC date), fct_crop_cycles (cycle ID). All marts are full tables; intermediate/trusted views do not promise materialized isolation during a build. Only published is the accepted consumer surface.

## Domain limits

First eligible harvest closes a cycle in [planting,next planting). Additional harvests and harvests without an eligible prior planting are observable and reconciled, not hidden in cycle totals. A next planting without harvest makes the earlier cycle superseded. Distinct simultaneous plantings fail validation; correction must be a source revision, not silent deduplication. Whole-field area at planting is the explicit yield denominator. Domain cycle IDs, multiple partial harvest totals, actual planted area, practice as-of validity and area-weighted irrigation require new contracts before implementation.

## Operating policy

All-source freshness ERROR blocks the whole release; WARN is recorded but eligible. Arrival max is aggregate RAW delivery recency, not trusted validity or per-producer/event-time completeness. Quality evidence persists invalid current/physical quarantine and unassigned closing-harvest counts. There is no deployed alerting, scheduler, benchmark, measured production SLA or automatic cloud recovery.

Managed recovery builds the full DAG and all tests, so selected staging replacement cannot leave descendants absent in a successful run. It may still leave a failed candidate incomplete; consumers retain the accepted published release. Incremental schema changes fail; RAW init is not an existing-volume migration. Versioned checksummed SQL migrations and explicit object migrations are required.

## Target architecture and deferred work

BigQuery is the analytical warehouse target. Batch object replay (GCS), containerized jobs (Cloud Run), scheduling, identities/secrets and monitoring are options only for concrete deployment needs. Pub/Sub is not implied by a 15-minute threshold. Partitioning/clustering and bounded job cost must follow volumes/access patterns. PostgreSQL advisory locks, NOT MATERIALIZED, SQL casts/aggregates and snapshot configuration need adapter-specific changes. Stable multi-table DML promotion is a candidate pattern for BigQuery; permanent DDL cannot be translated as PostgreSQL transactional DDL. ADRs document local decisions and target trade-offs; they are not deployed cloud capabilities.
