select crop_cycle_id, planted_at, next_planting_at, crop_cycle_status
from {{ ref('int_field_crop_cycles') }}
where next_planting_at <= planted_at
   or (crop_cycle_status='open' and next_planting_at is not null)
   or (crop_cycle_status='superseded' and (next_planting_at is null or harvested_at is not null))
