{{ config(materialized='view') }}

with weather as (

    select
        field_id,
        observed_at,
        observed_at at time zone 'UTC' as observed_at_utc,
        temperature_c,
        rainfall_mm,
        humidity_pct,
        wind_speed_kmh

    from {{ ref('stg_weather_observations') }}

),

daily_weather as (

    select
        field_id,
        observed_at_utc::date as weather_date,

        avg(temperature_c) as avg_temperature_c,
        min(temperature_c) as min_temperature_c,
        max(temperature_c) as max_temperature_c,

        sum(rainfall_mm) as rainfall_mm,

        avg(humidity_pct) as avg_humidity_pct,
        avg(wind_speed_kmh) as avg_wind_speed_kmh,

        count(*) as observation_count,

        min(observed_at) as first_observation_at,
        max(observed_at) as last_observation_at

    from weather

    group by
        field_id,
        observed_at_utc::date

)

select *
from daily_weather