{{ config(materialized='view') }}

with source_data as (

    {{ normalized_weather() }}

),

validated as (

    select
        *,
        {{ weather_observation_rejection_reason() }} as rejection_reason

    from source_data

)

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
    source_batch_id,
    rejection_reason

from validated

where rejection_reason is not null