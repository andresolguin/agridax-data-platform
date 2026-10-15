{{ config(materialized='view') }}

with planting_events as (

    select
        field_id,
        source_system as planting_source_system,
        source_event_id as planting_source_event_id,
        event_timestamp as planted_at,
        crop_type as crop_type_at_planting,
        lead(event_timestamp) over (
            partition by field_id
            order by event_timestamp, source_system, source_event_id
        ) as next_planting_at

    from {{ ref('int_field_events_with_history') }}

    where event_type = 'planting'
      and field_history_match_status = 'matched'

),

harvest_events as (

    select
        field_id,
        source_system as harvest_source_system,
        source_event_id as harvest_source_event_id,
        event_timestamp as harvested_at,
        quantity as harvest_quantity,
        unit as harvest_unit

    from {{ ref('int_field_events_with_history') }}

    where event_type = 'harvest'
      and field_history_match_status = 'matched'

),

crop_cycles as (

    select
        p.field_id,

        md5(jsonb_build_array(
            p.field_id, p.planting_source_system, p.planting_source_event_id
        )::text) as crop_cycle_id,

        p.planting_source_system,
        p.planting_source_event_id,
        p.planted_at,
        p.crop_type_at_planting,
        p.next_planting_at,

        h.harvest_source_system,
        h.harvest_source_event_id,
        h.harvested_at,
        h.harvest_quantity,
        h.harvest_unit,

        case
            when h.harvested_at is not null then 'closed'
            when p.next_planting_at is not null then 'superseded'
            else 'open'
        end as crop_cycle_status,

        case
            when h.harvested_at is not null
            then extract(epoch from (h.harvested_at - p.planted_at)) / 86400.0
            else null
        end as cycle_duration_days

    from planting_events p

    left join lateral (

        select
            h.harvest_source_system,
            h.harvest_source_event_id,
            h.harvested_at,
            h.harvest_quantity,
            h.harvest_unit

        from harvest_events h

        where h.field_id = p.field_id
          and h.harvested_at >= p.planted_at
          and (
                p.next_planting_at is null
                or h.harvested_at < p.next_planting_at
              )

        order by
            h.harvested_at,
            h.harvest_source_system,
            h.harvest_source_event_id

        limit 1

    ) h on true

)

select *
from crop_cycles
