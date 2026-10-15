{{ config(materialized='view') }}

-- One row per trusted logical harvest. A first-harvest cycle is not a total-production model.
select
    h.source_system,
    h.source_event_id,
    h.field_id,
    h.event_timestamp as harvested_at,
    h.quantity as harvest_quantity,
    c.crop_cycle_id as eligible_crop_cycle_id,
    case
        when c.crop_cycle_id is null then 'before_first_planting'
        when h.source_system = c.harvest_source_system
         and h.source_event_id = c.harvest_source_event_id then 'closing_harvest'
        else 'additional_harvest'
    end as assignment_status
from {{ ref('int_field_events_with_history') }} h
left join {{ ref('int_field_crop_cycles') }} c
    on h.field_id = c.field_id
   and h.event_timestamp >= c.planted_at
   and (c.next_planting_at is null or h.event_timestamp < c.next_planting_at)
where h.event_type = 'harvest'
  and h.field_history_match_status = 'matched'
