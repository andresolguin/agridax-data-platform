{% set scan = ingestion_scan_context('weather_observations') %}

{{ config(
    materialized='incremental',
    unique_key=['field_id', 'observed_at'],
    incremental_strategy='delete+insert',
    on_schema_change='fail',
    pre_hook="{{ prepare_ingestion_scan('weather_observations') }}",
    post_hook="{{ processing_scan_hook('weather_observations') }}"
) }}

{% do validate_incremental_backfill() %}

with normalized_raw as not materialized (

    {{ normalized_weather() }}
    where ingested_at < {{ processing_horizon_sql() }}

),

{% if is_incremental() %}

changed_keys as (

    select distinct
        field_id,
        observed_at

    from normalized_raw

    where {{ incremental_ingestion_predicate('ingested_at', scan) }}

),

candidates as (

    select
        raw.*

    from normalized_raw as raw

    inner join changed_keys as changed
        on raw.field_id = changed.field_id
       and raw.observed_at = changed.observed_at

),

{% else %}

candidates as (

    select *
    from normalized_raw

),

{% endif %}

ranked as (

    select
        *,
        row_number() over (
            partition by field_id, observed_at
            order by
                source_updated_at desc nulls last,
                ingested_at desc,
                raw_record_id desc
        ) as delivery_rank

    from candidates

),

validated as (

    select
        *,
        {{ weather_observation_rejection_reason() }} as rejection_reason

    from ranked

    where delivery_rank = 1

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
