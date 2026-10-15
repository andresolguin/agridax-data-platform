{{ config(materialized='view') }}

with events as (

    select
        field_id,
        event_timestamp,
        event_timestamp at time zone 'UTC' as event_timestamp_utc,
        event_type,
        quantity,
        unit

    from {{ ref('stg_field_events') }}

),

daily_activity as (

    select
        field_id,
        event_timestamp_utc::date as activity_date,

        count(*) as event_count,

        count(*) filter (
            where event_type = 'planting'
        ) as planting_event_count,

        count(*) filter (
            where event_type = 'irrigation'
        ) as irrigation_event_count,

        count(*) filter (
            where event_type = 'fertilizer'
        ) as fertilizer_event_count,

        count(*) filter (
            where event_type = 'pesticide'
        ) as pesticide_event_count,

        count(*) filter (
            where event_type = 'harvest'
        ) as harvest_event_count,

        count(*) filter (
            where event_type = 'soil_measurement'
        ) as soil_measurement_event_count,

        sum(quantity) filter (
            where event_type = 'irrigation'
              and unit = 'mm'
        ) as irrigation_mm,

        sum(quantity) filter (
            where event_type = 'fertilizer'
              and unit = 'kg'
        ) as fertilizer_kg,

        sum(quantity) filter (
            where event_type = 'pesticide'
              and unit = 'kg'
        ) as pesticide_kg,

        sum(quantity) filter (
            where event_type = 'harvest'
              and unit = 'kg'
        ) as harvest_kg,

        min(event_timestamp) as first_event_at,
        max(event_timestamp) as last_event_at

    from events

    group by
        field_id,
        event_timestamp_utc::date

)

select *
from daily_activity