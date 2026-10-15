{{ config(materialized='table') }}

with crop_cycles as (

    select
        crop_cycle_id,
        field_id,
        planting_source_system,
        planting_source_event_id,
        planted_at,
        crop_type_at_planting,
        next_planting_at,
        harvest_source_system,
        harvest_source_event_id,
        harvested_at,
        harvest_quantity,
        harvest_unit,
        crop_cycle_status,
        cycle_duration_days

    from {{ ref('int_field_crop_cycles') }}

),

planting_context as (

    select
        source_system,
        source_event_id,
        farm_id,
        area_hectares

    from {{ ref('fct_field_events') }}

    where event_type = 'planting'

)

select
    c.crop_cycle_id,
    c.field_id,
    p.farm_id,

    c.planting_source_system,
    c.planting_source_event_id,
    c.planted_at,
    c.crop_type_at_planting,
    p.area_hectares as area_hectares_at_planting,
    c.next_planting_at,

    c.harvest_source_system,
    c.harvest_source_event_id,
    c.harvested_at,
    c.harvest_quantity,
    c.harvest_unit,

    c.crop_cycle_status,
    c.cycle_duration_days,

    case
        when c.crop_cycle_status = 'closed'
         and c.harvest_unit = 'kg'
         and p.area_hectares > 0
            then c.harvest_quantity / p.area_hectares
        else null
    end as yield_kg_per_hectare

from crop_cycles c

left join planting_context p
    on c.planting_source_system = p.source_system
   and c.planting_source_event_id = p.source_event_id
