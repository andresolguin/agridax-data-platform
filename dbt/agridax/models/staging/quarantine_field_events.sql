{{ config(materialized='view') }}

with source_data as (

    {{ normalized_field_events() }}

),

validated as (

    select
        *,
        {{ field_event_rejection_reason() }} as rejection_reason

    from source_data

)

select
    raw_record_id,
    event_id,
    source_system,
    source_event_id,
    field_id,
    event_type,
    event_timestamp,
    quantity,
    unit,
    event_payload,
    source_updated_at,
    ingested_at,
    source_batch_id,
    rejection_reason

from validated

where rejection_reason is not null
