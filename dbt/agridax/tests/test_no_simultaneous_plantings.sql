-- Distinct logical plantings at the same field/time are ambiguous, not silently merged.
select field_id, event_timestamp, count(*) as planting_count
from {{ ref('stg_field_events') }}
where event_type = 'planting'
group by field_id, event_timestamp
having count(*) > 1
