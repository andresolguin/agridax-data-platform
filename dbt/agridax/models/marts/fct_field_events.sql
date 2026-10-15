{{ config(materialized='table') }}

with events as (

    select
        source_system,
        source_event_id,
        event_id,
        field_id,
        farm_id,
        event_type,
        event_timestamp,
        quantity,
        unit,
        event_payload,
        source_updated_at,
        ingested_at,

        field_name,
        area_hectares,
        crop_type,
        soil_type,
        irrigation_type,
        field_status,

        field_state_valid_from,
        field_state_valid_to,
        field_history_match_status

    from {{ ref('int_field_events_with_history') }}

)

select
    source_system,
    source_event_id,
    event_id,
    field_id,
    farm_id,
    event_type,
    event_timestamp,
    quantity,
    unit,
    event_payload,
    source_updated_at,
    ingested_at,

    field_name,
    area_hectares,
    crop_type as crop_type_at_event,
    soil_type as soil_type_at_event,
    irrigation_type as irrigation_type_at_event,
    field_status as field_status_at_event,

    field_state_valid_from,
    field_state_valid_to

from events

where field_history_match_status = 'matched'
