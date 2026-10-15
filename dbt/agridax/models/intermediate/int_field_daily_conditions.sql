{{ config(materialized='view') }}

with activity as (

    select *
    from {{ ref('int_field_daily_activity') }}

),

weather as (

    select *
    from {{ ref('int_field_daily_weather') }}

),

combined as (

    select
        coalesce(a.field_id, w.field_id) as field_id,
        coalesce(a.activity_date, w.weather_date) as activity_date,

        a.event_count,
        a.planting_event_count,
        a.irrigation_event_count,
        a.fertilizer_event_count,
        a.pesticide_event_count,
        a.harvest_event_count,
        a.soil_measurement_event_count,

        a.irrigation_mm,
        a.fertilizer_kg,
        a.pesticide_kg,
        a.harvest_kg,

        a.first_event_at,
        a.last_event_at,

        w.avg_temperature_c,
        w.min_temperature_c,
        w.max_temperature_c,
        w.rainfall_mm,
        w.avg_humidity_pct,
        w.avg_wind_speed_kmh,
        w.observation_count,
        w.first_observation_at,
        w.last_observation_at

    from activity a

    full outer join weather w
        on a.field_id = w.field_id
       and a.activity_date = w.weather_date

)

select *
from combined