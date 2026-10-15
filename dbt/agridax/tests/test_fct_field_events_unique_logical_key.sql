select
    source_system,
    source_event_id,
    count(*) as row_count

from {{ ref('fct_field_events') }}

group by
    source_system,
    source_event_id

having count(*) <> 1
