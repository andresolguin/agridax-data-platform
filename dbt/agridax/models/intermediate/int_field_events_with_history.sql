{{ config(materialized='view') }}

with events as (

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

    from {{ ref('stg_field_events') }}

),

field_history as (

    select
        field_id,
        farm_id,
        field_name,
        area_hectares,
        crop_type,
        soil_type,
        irrigation_type,
        status,
        field_state_valid_from,
        field_state_valid_to,
        source_updated_at as field_source_updated_at

    from {{ ref('int_field_history') }}

),

enriched as (

    select
        e.raw_record_id,
        e.event_id,
        e.source_system,
        e.source_event_id,
        e.field_id,
        e.event_type,
        e.event_timestamp,
        e.quantity,
        e.unit,
        e.event_payload,
        e.source_updated_at,
        e.ingested_at,
        e.source_batch_id,

        f.farm_id,
        f.field_name,
        f.area_hectares,
        f.crop_type,
        f.soil_type,
        f.irrigation_type,
        f.status as field_status,
        f.field_state_valid_from,
        f.field_state_valid_to,
        f.field_source_updated_at,

        case
            when f.field_id is null then 'unmatched_temporal_state'
            else 'matched'
        end as field_history_match_status

    from events e

    left join field_history f
      on e.field_id = f.field_id
     and e.event_timestamp >= f.field_state_valid_from
     and (
            e.event_timestamp < f.field_state_valid_to
            or f.field_state_valid_to is null
         )

)

select *
from enriched
