select
    field_id,
    observed_at,
    count(*) as record_count

from {{ ref('stg_weather_observations') }}

group by
    field_id,
    observed_at

having count(*) <> 1