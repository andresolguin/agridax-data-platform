CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE ops.pipeline_runs (
    run_id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    processing_horizon TIMESTAMPTZ NOT NULL,
    lock_owner_pid INTEGER NOT NULL,
    dbt_application_hash TEXT NOT NULL,
    run_kind TEXT NOT NULL CHECK (run_kind IN ('normal', 'backfill', 'full_refresh')),
    backfill_start TIMESTAMPTZ,
    backfill_end TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('building', 'validated', 'published', 'failed', 'commit_unknown')),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_fingerprints JSONB,
    completed_at TIMESTAMPTZ,
    CHECK ((backfill_start IS NULL) = (backfill_end IS NULL)),
    CHECK (backfill_start IS NULL OR backfill_start < backfill_end)
);

CREATE TABLE ops.processing_checkpoints (
    stream TEXT PRIMARY KEY CHECK (stream IN ('field_events', 'weather_observations')),
    processed_through TIMESTAMPTZ NOT NULL,
    last_run_id UUID NOT NULL REFERENCES ops.pipeline_runs(run_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE ops.processing_scans (
    run_id UUID NOT NULL REFERENCES ops.pipeline_runs(run_id),
    stream TEXT NOT NULL CHECK (stream IN ('field_events', 'weather_observations')),
    lower_bound TIMESTAMPTZ,
    upper_bound TIMESTAMPTZ NOT NULL,
    rows_in_window BIGINT NOT NULL CHECK (rows_in_window >= 0),
    changed_keys BIGINT NOT NULL CHECK (changed_keys >= 0),
    is_backfill BOOLEAN NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (run_id, stream),
    CHECK (lower_bound IS NULL OR lower_bound < upper_bound)
);

CREATE TABLE ops.releases (
    release_id UUID PRIMARY KEY REFERENCES ops.pipeline_runs(run_id),
    published_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    evidence JSONB NOT NULL,
    candidate_fingerprints JSONB NOT NULL
);

CREATE FUNCTION ops.assert_managed_run(candidate_run_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, ops AS $$
DECLARE run_row ops.pipeline_runs%ROWTYPE;
BEGIN
    SELECT * INTO run_row FROM ops.pipeline_runs WHERE run_id = candidate_run_id;
    IF NOT FOUND OR run_row.status <> 'building' THEN
        RAISE EXCEPTION 'Mutating dbt commands require an active managed building run';
    END IF;
    IF md5(current_setting('application_name')) IS DISTINCT FROM run_row.dbt_application_hash THEN
        RAISE EXCEPTION 'dbt connection does not belong to the managed invocation';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_locks
        WHERE locktype = 'advisory' AND classid = 8142026::oid
          AND objid = 1::oid AND objsubid = 2 AND granted
          AND pid = run_row.lock_owner_pid
    ) OR NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_locks
        WHERE locktype = 'advisory' AND classid = 8142026::oid
          AND objid = 2::oid AND objsubid = 2 AND mode = 'ExclusiveLock'
          AND granted AND pid = run_row.lock_owner_pid
    ) THEN
        RAISE EXCEPTION 'Managed run no longer owns the writer / ingestion boundary';
    END IF;
END;
$$;

CREATE FUNCTION ops.record_processing_scan(
    candidate_run_id UUID, stream_name TEXT, window_lower TIMESTAMPTZ,
    window_upper TIMESTAMPTZ, physical_rows BIGINT, logical_keys BIGINT,
    bounded_backfill BOOLEAN
) RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, ops AS $$
BEGIN
    PERFORM ops.assert_managed_run(candidate_run_id);
    INSERT INTO ops.processing_scans(
        run_id, stream, lower_bound, upper_bound, rows_in_window, changed_keys, is_backfill
    ) VALUES (
        candidate_run_id, stream_name, window_lower, window_upper,
        physical_rows, logical_keys, bounded_backfill
    );
    IF NOT bounded_backfill THEN
        INSERT INTO ops.processing_checkpoints(stream, processed_through, last_run_id)
        VALUES (stream_name, window_upper, candidate_run_id)
        ON CONFLICT (stream) DO UPDATE
        SET processed_through = greatest(ops.processing_checkpoints.processed_through, EXCLUDED.processed_through),
            last_run_id = CASE
                WHEN EXCLUDED.processed_through >= ops.processing_checkpoints.processed_through
                THEN EXCLUDED.last_run_id ELSE ops.processing_checkpoints.last_run_id END,
            updated_at = clock_timestamp();
    END IF;
END;
$$;

CREATE FUNCTION ops.guard_raw_insert()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog AS $$
BEGIN
    -- Cooperating writers also take this lock BEFORE assigning ingestion timestamps.
    -- This trigger makes an already-started insert finish before a release can enter.
    PERFORM pg_advisory_xact_lock_shared(8142026, 2);
    RETURN NEW;
END;
$$;

CREATE TRIGGER ingestion_boundary BEFORE INSERT ON raw.farms
FOR EACH ROW EXECUTE FUNCTION ops.guard_raw_insert();
CREATE TRIGGER ingestion_boundary BEFORE INSERT ON raw.fields
FOR EACH ROW EXECUTE FUNCTION ops.guard_raw_insert();
CREATE TRIGGER ingestion_boundary BEFORE INSERT ON raw.field_events
FOR EACH ROW EXECUTE FUNCTION ops.guard_raw_insert();
CREATE TRIGGER ingestion_boundary BEFORE INSERT ON raw.weather_observations
FOR EACH ROW EXECUTE FUNCTION ops.guard_raw_insert();
CREATE TRIGGER ingestion_boundary BEFORE INSERT ON raw.sustainability_practices
FOR EACH ROW EXECUTE FUNCTION ops.guard_raw_insert();

CREATE INDEX idx_raw_field_event_normalized_versions
ON raw.field_events (lower(btrim(source_system)), btrim(source_event_id),
    source_updated_at DESC NULLS LAST, ingested_at DESC, raw_record_id DESC);
CREATE INDEX idx_raw_weather_normalized_versions
ON raw.weather_observations (btrim(field_id), observed_at,
    source_updated_at DESC NULLS LAST, ingested_at DESC, raw_record_id DESC);
CREATE INDEX idx_raw_field_state_normalized_versions
ON raw.fields (btrim(field_id), effective_from, updated_at DESC, ingested_at DESC, raw_record_id DESC);

REVOKE ALL ON ALL TABLES IN SCHEMA ops FROM PUBLIC;
REVOKE ALL ON ALL FUNCTIONS IN SCHEMA ops FROM PUBLIC;
