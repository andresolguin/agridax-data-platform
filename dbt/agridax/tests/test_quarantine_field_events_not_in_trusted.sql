select
    q.raw_record_id,
    q.source_system,
    q.source_event_id,
    q.rejection_reason

from {{ ref('quarantine_field_events') }} q

inner join {{ ref('stg_field_events') }} s
    on q.raw_record_id = s.raw_record_id
