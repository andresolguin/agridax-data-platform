with expected as (
    select source_system, source_event_id, quantity
    from {{ ref('stg_field_events') }} where event_type = 'harvest'
), actual as (
    select source_system, source_event_id, harvest_quantity, count(*) over (
        partition by source_system, source_event_id) as matches
    from {{ ref('int_harvest_cycle_assignment') }}
)
select coalesce(e.source_system,a.source_system) as source_system,
       coalesce(e.source_event_id,a.source_event_id) as source_event_id
from expected e full outer join actual a
  on e.source_system=a.source_system and e.source_event_id=a.source_event_id
where e.source_event_id is null or a.source_event_id is null
   or a.matches <> 1 or e.quantity is distinct from a.harvest_quantity
