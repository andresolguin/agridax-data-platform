{{ config(
    materialized='view'
) }}

select
    raw_record_id,
    observation_id,
    field_id,
    observed_at,
    temperature_c,
    rainfall_mm,
    humidity_pct,
    wind_speed_kmh,
    source_system,
    source_updated_at,
    ingested_at,
    source_batch_id

from {{ ref('stg_weather_observation_winners') }}

where rejection_reason is null