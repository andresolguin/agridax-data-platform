select
    crop_cycle_id,
    crop_cycle_status,
    harvest_quantity,
    harvest_unit,
    area_hectares_at_planting,
    yield_kg_per_hectare

from {{ ref('fct_crop_cycles') }}

where
    (
        crop_cycle_status = 'closed'
        and harvest_unit = 'kg'
        and area_hectares_at_planting > 0
        and (
            yield_kg_per_hectare is null
            or abs(
                yield_kg_per_hectare
                - (harvest_quantity / area_hectares_at_planting)
            ) > 0.000001
        )
    )
    or
    (
        (
            crop_cycle_status <> 'closed'
            or harvest_unit is distinct from 'kg'
            or area_hectares_at_planting is null
            or area_hectares_at_planting <= 0
        )
        and yield_kg_per_hectare is not null
    )
