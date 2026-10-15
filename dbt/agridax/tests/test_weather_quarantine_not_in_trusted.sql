select q.raw_record_id
from {{ ref('quarantine_weather_observations') }} q
join {{ ref('stg_weather_observations') }} t using (raw_record_id)
