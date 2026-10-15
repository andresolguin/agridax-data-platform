select
    source_system,
    source_event_id,
    field_id,
    event_timestamp,
    field_history_match_status

from {{ ref('int_field_events_with_history') }}

where field_history_match_status <> 'matched'
