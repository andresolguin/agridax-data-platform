# ADR 0003 — Stable local consumer objects

Status: implemented local design.

Decision: verify the candidate, replace rows in five stable published tables, verify copied contents and record the release marker inside one REPEATABLE READ transaction. Initial creation adds required PKs and reader grants. Validate schema/PK compatibility and candidate fingerprints tied to fresh full-build/freshness evidence. Preserve OID/indexes/comments/constraints/views, instead of DROP/RENAME/CASCADE. Only the live single coordinator can promote; name-only standalone promotion is refused.

Trade-off: full copying/index maintenance/WAL can cost more as data grows. Arbitrary external FKs are not supported; failures retain accepted data. Readers pin REPEATABLE READ for a cohort. Commit acknowledgement loss is unknown, reconciled through the atomic marker. These controls prevent ordinary stale/accidental promotion, not an attestation against a malicious superuser/publisher who can manually alter tables/control evidence.

Target BigQuery needs a separately validated stable DML or release-version mechanism; permanent DDL in PostgreSQL transactions is not portable.
