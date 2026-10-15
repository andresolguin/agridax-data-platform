-- AgriDax Data Platform
-- PostgreSQL RAW layer initialization
--
-- Design notes:
-- - RAW preserves physical deliveries and may therefore contain repeated versions
--   of the same logical business record.
-- - Business uniqueness is NOT enforced in RAW.
-- - Referential integrity across independently arriving sources is validated
--   downstream in dbt rather than with RAW foreign keys.
-- - Business-rule validation is enforced downstream so structurally loadable
--   source evidence remains auditable and replayable.
-- - raw_record_id is a physical ingestion surrogate only; it is never used as
--   a business key.

BEGIN;

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.farms (
    raw_record_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    farm_id           TEXT NOT NULL,
    farm_name         TEXT NOT NULL,
    country_code      CHAR(2) NOT NULL,
    region            TEXT,
    owner_type        TEXT,
    created_at        TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL,
    ingested_at       TIMESTAMPTZ NOT NULL,
    source_batch_id   TEXT,
    source_file_name  TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_farms_ingested_at
    ON raw.farms (ingested_at);

CREATE INDEX IF NOT EXISTS idx_raw_farms_entity_version
    ON raw.farms (farm_id, updated_at DESC, ingested_at DESC);

CREATE TABLE IF NOT EXISTS raw.fields (
    raw_record_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    field_id          TEXT NOT NULL,
    farm_id           TEXT NOT NULL,
    field_name        TEXT NOT NULL,
    area_hectares     NUMERIC(12,2) NOT NULL,
    crop_type         TEXT,
    soil_type         TEXT,
    irrigation_type   TEXT,
    status            TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL,
    effective_from    TIMESTAMPTZ NOT NULL,
    updated_at        TIMESTAMPTZ NOT NULL,
    ingested_at       TIMESTAMPTZ NOT NULL,
    source_batch_id   TEXT,
    source_file_name  TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_fields_ingested_at
    ON raw.fields (ingested_at);

CREATE INDEX IF NOT EXISTS idx_raw_fields_entity_version
    ON raw.fields (field_id, updated_at DESC, ingested_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_fields_effective_from
    ON raw.fields (field_id, effective_from);

CREATE INDEX IF NOT EXISTS idx_raw_fields_farm_id
    ON raw.fields (farm_id);

CREATE TABLE IF NOT EXISTS raw.field_events (
    raw_record_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id           TEXT NOT NULL,
    source_system      TEXT NOT NULL,
    source_event_id    TEXT NOT NULL,
    field_id           TEXT NOT NULL,
    event_type         TEXT NOT NULL,
    event_timestamp    TIMESTAMPTZ NOT NULL,
    quantity           NUMERIC(18,4),
    unit               TEXT,
    event_payload      JSONB,
    source_updated_at  TIMESTAMPTZ,
    ingested_at        TIMESTAMPTZ NOT NULL,
    source_batch_id    TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_field_events_ingested_at
    ON raw.field_events (ingested_at);

CREATE INDEX IF NOT EXISTS idx_raw_field_events_logical_key
    ON raw.field_events (source_system, source_event_id);

CREATE INDEX IF NOT EXISTS idx_raw_field_events_event_time
    ON raw.field_events (event_timestamp);

CREATE INDEX IF NOT EXISTS idx_raw_field_events_field_time
    ON raw.field_events (field_id, event_timestamp);

CREATE TABLE IF NOT EXISTS raw.weather_observations (
    raw_record_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    observation_id     TEXT NOT NULL,
    field_id           TEXT NOT NULL,
    observed_at        TIMESTAMPTZ NOT NULL,
    temperature_c      NUMERIC(6,2),
    rainfall_mm        NUMERIC(10,2),
    humidity_pct       NUMERIC(5,2),
    wind_speed_kmh     NUMERIC(8,2),
    source_system      TEXT NOT NULL,
    source_updated_at  TIMESTAMPTZ,
    ingested_at        TIMESTAMPTZ NOT NULL,
    source_batch_id    TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_weather_ingested_at
    ON raw.weather_observations (ingested_at);

CREATE INDEX IF NOT EXISTS idx_raw_weather_logical_key
    ON raw.weather_observations (field_id, observed_at);

CREATE INDEX IF NOT EXISTS idx_raw_weather_source_time
    ON raw.weather_observations (source_system, observed_at);

CREATE TABLE IF NOT EXISTS raw.sustainability_practices (
    raw_record_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    practice_id       TEXT NOT NULL,
    field_id          TEXT NOT NULL,
    practice_type     TEXT NOT NULL,
    status            TEXT NOT NULL,
    verified          BOOLEAN NOT NULL,
    valid_from        DATE NOT NULL,
    valid_to          DATE,
    updated_at        TIMESTAMPTZ NOT NULL,
    ingested_at       TIMESTAMPTZ NOT NULL,
    source_batch_id   TEXT,
    source_file_name  TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_sustainability_ingested_at
    ON raw.sustainability_practices (ingested_at);

CREATE INDEX IF NOT EXISTS idx_raw_sustainability_assignment_version
    ON raw.sustainability_practices (practice_id, updated_at DESC, ingested_at DESC);

CREATE INDEX IF NOT EXISTS idx_raw_sustainability_field_type
    ON raw.sustainability_practices (field_id, practice_type);

COMMENT ON SCHEMA raw IS
    'Durable ingestion boundary preserving source semantics, delivery history, and platform ingestion metadata.';

COMMENT ON COLUMN raw.fields.effective_from IS
    'Business-effective timestamp from which the delivered field state is valid.';

COMMENT ON COLUMN raw.field_events.event_timestamp IS
    'Business event time; distinct from platform ingestion time.';

COMMENT ON COLUMN raw.field_events.ingested_at IS
    'Physical arrival metadata; operational progress is tracked separately in ops.processing_checkpoints.';

COMMIT;
