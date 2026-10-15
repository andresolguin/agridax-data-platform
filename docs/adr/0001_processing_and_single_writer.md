# ADR 0001 — Local progress and single writer

Status: implemented local design; native locking/authentication evidence is reported separately.

Problem: winner max arrival does not account for invalid/non-winning deliveries; concurrent builds/publishers can mix candidates. Decision: independent ops checkpoints/scans, fixed per-run horizon, shared ingestion transaction boundary and one exclusive build/promotion coordinator. Record physical window rows/keys and model-transaction progress. Backfill leaves normal checkpoints unchanged; full/global reconciliation protects acceptance. Application identity binds managed dbt connections to the active run. No progress claim is an event completeness watermark.

Trade-off: producers are paused for the local run; non-cooperating/arbitrarily delayed old-metadata writes need explicit recovery. Timeouts fail rather than wait forever. Larger/asynchronous workloads need a different batching/commit frontier, not naive max(identity). No scheduler/streaming service is added now.
