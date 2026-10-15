select
    crop_cycle_id,
    field_id,
    crop_cycle_status,
    planted_at,
    harvested_at,
    cycle_duration_days

from {{ ref('int_field_crop_cycles') }}

where
    (
        crop_cycle_status = 'closed'
        and (
            harvested_at is null
            or harvested_at < planted_at
            or cycle_duration_days is null
            or cycle_duration_days < 0
        )
    )
    or
    (
        crop_cycle_status = 'open'
        and harvested_at is not null
    )
