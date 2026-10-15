select
    source_system,
    source_event_id,
    count(*) as matched_row_count

from {{ ref('int_field_events_with_history') }}

group by
    source_system,
    source_event_id

having count(*) <> 1
