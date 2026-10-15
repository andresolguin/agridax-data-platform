{{ config(materialized='table') }}

with daily_conditions as (

    select
        field_id,
        activity_date as business_date,

        event_count,
        planting_event_count,
        irrigation_event_count,
        fertilizer_event_count,
        pesticide_event_count,
        harvest_event_count,
        soil_measurement_event_count,

        irrigation_mm,
        fertilizer_kg,
        pesticide_kg,
        harvest_kg,

        first_event_at,
        last_event_at,

        avg_temperature_c,
        min_temperature_c,
        max_temperature_c,
        rainfall_mm,
        avg_humidity_pct,
        avg_wind_speed_kmh,
        observation_count,
        first_observation_at,
        last_observation_at

    from {{ ref('int_field_daily_conditions') }}

)

select
    field_id,
    business_date,

    event_count,
    planting_event_count,
    irrigation_event_count,
    fertilizer_event_count,
    pesticide_event_count,
    harvest_event_count,
    soil_measurement_event_count,

    irrigation_mm,
    fertilizer_kg,
    pesticide_kg,
    harvest_kg,

    first_event_at,
    last_event_at,

    avg_temperature_c,
    min_temperature_c,
    max_temperature_c,
    rainfall_mm,
    avg_humidity_pct,
    avg_wind_speed_kmh,
    observation_count,
    first_observation_at,
    last_observation_at,

    event_count is not null as has_activity_data,
    observation_count is not null as has_weather_data,

    case
        when event_count is not null
         and observation_count is not null
            then 'both_sources'
        when event_count is not null
            then 'activity_only'
        when observation_count is not null
            then 'weather_only'
        else 'unexpected_empty'
    end as data_completeness_status

from daily_conditions
