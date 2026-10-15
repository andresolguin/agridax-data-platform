# Recovery and database lifecycle

## Processing and acceptance

Each managed run takes single-writer and exclusive ingestion locks before its horizon H. Normal canonical models scan [previous processing horizon - configured overlap,H), or all deliveries below H on first/full/empty-target recovery. They count physical rows and changed logical keys, then resolve all RAW versions for affected keys. Deferred-rendered hooks freeze the lower boundary in a transaction-local session setting before target writes; the post-hook resolves the actual RAW source at execution and records that same window. Checkpoints/scans commit with the corresponding canonical model. A later downstream/test/freshness failure does not rewind successfully committed canonical processing; it prevents acceptance/promotion. Progress is not release eligibility or business completeness.

Cooperating ingestion takes a shared transaction boundary before assigning UTC arrival metadata. Pending writers cause an explicit contention failure rather than a hidden unlimited wait. The default overlap is 300 seconds and covers bounded clock/commit deviations; the protocol is the primary coordination mechanism. Clients that assign timestamps before waiting or replay old metadata are outside normal arrival assumptions. Identity is not a commit-order checkpoint. Future ingestion timestamps/checkpoints ahead of database clock fail explicitly. Old imports require recovery. RAW is never UPDATEd to make freshness pass.

## Supported bounded recovery

1. Load source deliveries through the documented ingestion boundary. Settle pending normal arrivals with a managed `--skip-publish` run if unrelated new keys would otherwise lie outside the selected backfill.
2. Run `python -m agridax.pipeline --backfill-start "2026-10-12T09:00:00-03:00" --backfill-end "2026-10-12T13:00:00Z"` from the installed environment.
3. The coordinator performs changed-key/all-version canonical selection, recreates trusted/intermediate/snapshot/mart descendants, runs the complete tests and all-source freshness, then promotes only validated unchanged candidate content.
4. If validation fails, retain the previous release, diagnose the failed run/scan/source evidence, and perform the necessary wider or normal recovery. Do not promote a partial candidate by relation names.

Bounds apply to ingested_at, not event/observed/effective dates. Seconds and explicit Z/±HH:MM offsets are required; up to six fractional digits are supported. Parsing and chronological comparison happen before timestamp SQL; UTC literals contain no arbitrary operator input. Equal/reversed/missing/malformed bounds fail. Bounded first-run and bounded + full-refresh fail. Backfill does not change normal checkpoints. A narrow scope cannot repair missing keys outside that scope; global reconciliation deliberately blocks incomplete promotion.

The only supported mutating selector is the COMPLETE platform. For lineage inspection, `python -m agridax.inspect_dbt ls --select stg_field_event_winners+` lists affected descendants; it is not a partial promotion recipe. Intermediate/marts/checksums/reconciliation may read/rebuild full history, so bounded input does not imply bounded end-to-end cost. No volume benchmark is claimed.

## Full reconstruction

Use `python -m agridax.pipeline --full-refresh` without bounded vars. Both canonical tables and all descendants are rebuilt. RAW-derived field business history is reconstructed independently of snapshots. Existing observed snapshot history is normally retained; explicitly deleting snapshots loses warehouse observations that RAW cannot recreate. Archive observations before an intentional reset. A missing/empty canonical table triggers all-key discovery; operational progress remains monotonic.

## Initialization versus migrations

Docker init runs only against an empty volume. `001_create_raw_schema.sql` is a baseline, not a migration engine; IF NOT EXISTS does not add missing columns. `--initialize` performs explicit admin role/grant setup and checksummed files in infra/postgres/migrations. Changing an applied file is refused: add a new numbered migration. Normal releases do not need admin to execute data transforms.

An existing volume must use its actual existing admin user/password; changing image environment variables does not change those credentials. The current RAW contract includes effective_from with timestamptz. Incompatible older RAW schemas require an explicit versioned ALTER migration and data assessment, not a silently destructive bootstrap. An older snapshot with naive/source-timestamp metadata needs an explicit assessed migration; missing observation time must not be fabricated. Incremental on_schema_change=fail requires deliberate full rebuild or schema migration. Published schema/PK evolution is checked and never silently drops consumer objects. Existing analytics/snapshot tables owned by a former admin/workload require an explicit ownership migration before dbt uses the new transform role; changing schema ownership alone does not transfer table ownership.

Normal operation never executes compose down --volumes or drops data schemas. The acceptance runner may reset only an explicitly disposable/prefixed database or its uniquely named Compose volume. Its cleanup cannot target the default local project. Backups, restoration, volume destruction and new physical fixture deliveries are different operations.

## Failure and commit outcomes

Read ops.pipeline_runs, ops.processing_scans/checkpoints and ops.releases by run_id. Failed builds may have valid canonical progress but no eligible release. Confirmed simulated publication failure rolls back all five copies, their metadata changes and the release marker. If a connection-level error occurs at COMMIT, the client reports unknown outcome. An ops.releases row and matching published run status were written in the same transaction; reconcile after connectivity returns. No automatic statement declares the old release unchanged for an unknown commit.

Standalone publication is refused; rerun the coordinator to create fresh evidence. Timeouts bound individual connections/locks/statements, not total DAG compute. Consumer reads across marts should use one read-only REPEATABLE READ transaction; multiple independent queries can span releases. External foreign keys against published rows are outside the supported replacement contract and may cause an explicit rollback.
