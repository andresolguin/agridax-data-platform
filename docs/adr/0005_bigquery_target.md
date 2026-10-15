# ADR 0005 — Target BigQuery adaptation

Status: target / not deployed.

Preserve RAW delivery evidence, comparable producer revisions, changed-key/all-version selection, separate effective/observed history, quarantine, bounded recovery, validated cohorts and cost limits. Map PostgreSQL casts/timestamptz/AT TIME ZONE, FILTER aggregates, bool_or, LATERAL pairing, EPOCH durations, JSONB/identity/indexes, NOT MATERIALIZED, snapshot datasets and advisory locks through an adapter-specific design. IS DISTINCT FROM, windows and FULL OUTER are not automatically incompatible.

BigQuery DML transactions over stable tables or explicit versioned releases may preserve promotion; do not copy permanent transactional DDL literally. Partition RAW by ingestion and facts by affected business date only after access/volume assessment; correction moves must include previous/new keys/dates. Revision lookups need historical access and predictable bytes/job.

GCS can hold replayable batch files; Cloud Run/Scheduler can execute necessary jobs; Pub/Sub only if push/buffering/retries justify asynchronous ingestion. Secret Manager/IAM and persistent monitoring belong to an actual deployment. No cloud resource, benchmark, operating SLA or universal service list is claimed here.
