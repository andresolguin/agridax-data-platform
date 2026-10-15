{{ config(
    materialized='view'
) }}

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
    source_batch_id

from {{ ref('stg_field_event_winners') }}

where rejection_reason is null