select
    source_system,
    source_event_id,
    count(*) as record_count

from {{ ref('stg_field_events') }}

group by
    source_system,
    source_event_id

having count(*) <> 1