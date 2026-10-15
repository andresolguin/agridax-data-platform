# ADR 0002 — Effective states and source revisions

Status: implemented local contract.

Decision: canonical field-state identity is (field_id,effective_from); updated_at, ingestion and physical ID resolve corrections. Consecutive effective starts define half-open business intervals. Current chooses latest effective start not after the managed horizon. History can be rebuilt from all RAW states regardless of snapshot cadence. A check snapshot independently records current-state attributes/source-update changes at warehouse observation time, not source update time; ingestion-only retries do not version it.

Event/weather dated source revisions outrank undated deliveries, then ingestion/physical ID tie-break. All-undated keys remain latest-arrival semantics: stale retry ordering cannot be inferred without producer revisions. Counts make undated evidence visible. Provider clocks must be comparable for the one-observation-per-field/time contract; provider-specific grain/priority needs a new source agreement.

Limits: arbitrary effective_from replacement changes identity; gaps/explicit validity ends, tombstones, as-known bitemporal facts and replay with regenerated ambiguous IDs are not promised. Preserve source identity/metadata when recovering; introduce stable source-state/delivery revision IDs if those needs arise.
