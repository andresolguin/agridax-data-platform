# RAW data contracts

RAW is the durable physical-delivery boundary. Business-invalid but structurally loadable evidence remains here. Every table has physical grain `raw_record_id`, an identity PK. There are no business uniqueness constraints or cross-source foreign keys. Workload ingestion has SELECT/INSERT and sequence USAGE, without UPDATE/DELETE. Identity ordering is not transaction commit ordering.

Normal cooperating writers acquire the shared ingestion boundary before assigning `ingested_at` in UTC and inserting. The release coordinator holds the exclusive boundary while selecting its upper horizon, building, validating and promoting. A trigger also guards inserts. A client that assigns a timestamp before waiting, imports old delivery metadata or bypasses this protocol must use supported backfill/full recovery; arbitrary out-of-order external commits are not guaranteed by a five-minute overlap. Global winner reconciliation detects missed current revisions before promotion.

Baseline fixtures deliberately simulate earlier arrival times relative to a controllable anchor. Seed them before first build; a historical anchored load after a checkpoint requires recovery. New scenario deliveries use database receipt time after the lock. Existing RAW timestamps are never modified to pass freshness. The `*_baseline.csv` source_file_name values are fixture labels, not hidden input files.

## Grains and revision rules

| Table | Logical/current grain | Revision and validity contract |
|---|---|---|
| farms | farm_id | normalized ID; latest updated_at, ingestion, raw identity; current state only |
| fields | field_id + effective_from | latest updated_at, ingestion, raw identity within a business state; current selects greatest effective_from not after run horizon |
| field_events | normalized source_system + source_event_id | dated source_updated_at descending NULLS LAST, ingestion then raw identity |
| weather_observations | normalized field_id + observed_at | one canonical revision across providers, same dated-first ordering; producer update clocks must be comparable |
| sustainability_practices | normalized practice_id | latest updated_at, ingestion, raw identity; source-reported current assignment/status only |

A dated revision has priority over an undated delivery. If every revision is undated, latest arrival wins; protection against stale undated replay cannot be inferred. Unknown-revision counts are recorded in run health. Source_updated_at and ingested_at are not interchangeable clocks. Changing field effective_from changes state identity: arbitrary boundary replacement/tombstones requires a future source-state identity/supersession contract.

## farms

| Column | PostgreSQL type | Nullable | Meaning |
|---|---|---|---|
| `raw_record_id` | `BIGINT` | No | Physical identity PK |
| `farm_id` | `TEXT` | No | Source value / delivery metadata |
| `farm_name` | `TEXT` | No | Source value / delivery metadata |
| `country_code` | `CHAR(2)` | No | Source value / delivery metadata |
| `region` | `TEXT` | Yes | Source value / delivery metadata |
| `owner_type` | `TEXT` | Yes | Source value / delivery metadata |
| `created_at` | `TIMESTAMPTZ` | No | Source value / delivery metadata |
| `updated_at` | `TIMESTAMPTZ` | No | Source update/revision time |
| `ingested_at` | `TIMESTAMPTZ` | No | UTC arrival metadata |
| `source_batch_id` | `TEXT` | Yes | Source value / delivery metadata |
| `source_file_name` | `TEXT` | Yes | Source value / delivery metadata |

## fields

| Column | PostgreSQL type | Nullable | Meaning |
|---|---|---|---|
| `raw_record_id` | `BIGINT` | No | Physical identity PK |
| `field_id` | `TEXT` | No | Source value / delivery metadata |
| `farm_id` | `TEXT` | No | Source value / delivery metadata |
| `field_name` | `TEXT` | No | Source value / delivery metadata |
| `area_hectares` | `NUMERIC(12,2)` | No | Source value / delivery metadata |
| `crop_type` | `TEXT` | Yes | Source value / delivery metadata |
| `soil_type` | `TEXT` | Yes | Source value / delivery metadata |
| `irrigation_type` | `TEXT` | Yes | Source value / delivery metadata |
| `status` | `TEXT` | No | Source value / delivery metadata |
| `created_at` | `TIMESTAMPTZ` | No | Source value / delivery metadata |
| `effective_from` | `TIMESTAMPTZ` | No | Business-effective state start |
| `updated_at` | `TIMESTAMPTZ` | No | Source update/revision time |
| `ingested_at` | `TIMESTAMPTZ` | No | UTC arrival metadata |
| `source_batch_id` | `TEXT` | Yes | Source value / delivery metadata |
| `source_file_name` | `TEXT` | Yes | Source value / delivery metadata |

## field_events

| Column | PostgreSQL type | Nullable | Meaning |
|---|---|---|---|
| `raw_record_id` | `BIGINT` | No | Physical identity PK |
| `event_id` | `TEXT` | No | Source value / delivery metadata |
| `source_system` | `TEXT` | No | Source value / delivery metadata |
| `source_event_id` | `TEXT` | No | Source value / delivery metadata |
| `field_id` | `TEXT` | No | Source value / delivery metadata |
| `event_type` | `TEXT` | No | Source value / delivery metadata |
| `event_timestamp` | `TIMESTAMPTZ` | No | Business event/observation instant |
| `quantity` | `NUMERIC(18,4)` | Yes | Source value / delivery metadata |
| `unit` | `TEXT` | Yes | Source value / delivery metadata |
| `event_payload` | `JSONB` | Yes | Source value / delivery metadata |
| `source_updated_at` | `TIMESTAMPTZ` | Yes | Source update/revision time |
| `ingested_at` | `TIMESTAMPTZ` | No | UTC arrival metadata |
| `source_batch_id` | `TEXT` | Yes | Source value / delivery metadata |

## weather_observations

| Column | PostgreSQL type | Nullable | Meaning |
|---|---|---|---|
| `raw_record_id` | `BIGINT` | No | Physical identity PK |
| `observation_id` | `TEXT` | No | Source value / delivery metadata |
| `field_id` | `TEXT` | No | Source value / delivery metadata |
| `observed_at` | `TIMESTAMPTZ` | No | Business event/observation instant |
| `temperature_c` | `NUMERIC(6,2)` | Yes | Source value / delivery metadata |
| `rainfall_mm` | `NUMERIC(10,2)` | Yes | Source value / delivery metadata |
| `humidity_pct` | `NUMERIC(5,2)` | Yes | Source value / delivery metadata |
| `wind_speed_kmh` | `NUMERIC(8,2)` | Yes | Source value / delivery metadata |
| `source_system` | `TEXT` | No | Source value / delivery metadata |
| `source_updated_at` | `TIMESTAMPTZ` | Yes | Source update/revision time |
| `ingested_at` | `TIMESTAMPTZ` | No | UTC arrival metadata |
| `source_batch_id` | `TEXT` | Yes | Source value / delivery metadata |

## sustainability_practices

| Column | PostgreSQL type | Nullable | Meaning |
|---|---|---|---|
| `raw_record_id` | `BIGINT` | No | Physical identity PK |
| `practice_id` | `TEXT` | No | Source value / delivery metadata |
| `field_id` | `TEXT` | No | Source value / delivery metadata |
| `practice_type` | `TEXT` | No | Source value / delivery metadata |
| `status` | `TEXT` | No | Source value / delivery metadata |
| `verified` | `BOOLEAN` | No | Source value / delivery metadata |
| `valid_from` | `DATE` | No | Source value / delivery metadata |
| `valid_to` | `DATE` | Yes | Source value / delivery metadata |
| `updated_at` | `TIMESTAMPTZ` | No | Source update/revision time |
| `ingested_at` | `TIMESTAMPTZ` | No | UTC arrival metadata |
| `source_batch_id` | `TEXT` | Yes | Source value / delivery metadata |
| `source_file_name` | `TEXT` | Yes | Source value / delivery metadata |

## Business validation

Required trusted identifiers are trimmed and non-blank; source_system/event_type/unit are lowercased. Farms use a two-uppercase-letter country-code format (not a validated ISO catalog). Fields require positive finite area; historical intervals must be positive when bounded. Invalid master states block validation rather than falling back to an older valid state.

Events require a supported category, timestamp, finite non-negative quantity and compatible unit. Zero is a legitimate observation; negative/non-finite quantities are rejected. Quantity NULL is rejected. Units: planting ha; irrigation mm; fertilizer/pesticide/harvest kg; soil_measurement ph. No automatic tonnes/unit conversion exists. Source event timestamps are business semantics; processing windows never filter by them.

Weather requires non-blank observation/field/provider identifiers and an observation instant. Measurements may be NULL. When supplied they must be finite; rainfall and wind non-negative, humidity within 0–100. Temperature has no invented range. Rainfall denotes reported interval accumulation, not a cumulative counter; coverage normalization remains the producer contract.

Canonical event/weather winners retain rejection_reason, including an invalid current revision. Trusted views filter valid canonical rows. A newer invalid revision removes the prior trusted row; a later valid correction restores it. Physical quarantine includes every rejected RAW delivery, even after a logical key recovers. The shared CASE macro chooses its first matching reason; it is not a list of every defect. Reference/history failures are separately observable required tests, because independently arriving masters may temporarily be unavailable.

Irrigation daily depth is the sum of compatible reported event quantities; zone area weighting is not implemented. Crop-cycle yield divides FIRST eligible harvest mass by whole-field area valid at planting, not actual planted acreage or total multi-harvest production. Practice active/verified metrics refer to latest reported flags, without historical validity-period or as-of-date inference.

Required business text rejects empty or POSIX-whitespace-only values, including tabs/newlines. Blank validation is shared by event/weather rejection and generic non_blank. Key normalization uses SQL trim/lower as documented; it is not a universal Unicode identifier normalization policy.
