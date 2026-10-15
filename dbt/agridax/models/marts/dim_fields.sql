{{ config(materialized='table') }}

with fields as (

    select
        field_id,
        farm_id,
        field_name,
        area_hectares,
        crop_type,
        soil_type,
        irrigation_type,
        status,
        created_at,
        effective_from,
        updated_at,
        ingested_at

    from {{ ref('stg_fields') }}

),

sustainability as (

    select
        field_id,
        practice_count,
        active_practice_count,
        verified_practice_count,
        verified_active_practice_count,
        has_active_cover_crop,
        has_active_reduced_tillage,
        has_active_crop_rotation,
        has_active_water_efficiency,
        has_active_organic_fertilizer

    from {{ ref('int_field_sustainability_metrics') }}

)

select
    f.field_id,
    f.farm_id,
    f.field_name,
    f.area_hectares,
    f.crop_type,
    f.soil_type,
    f.irrigation_type,
    f.status,
    f.created_at,
    f.effective_from,
    f.updated_at,
    f.ingested_at,

    coalesce(s.practice_count, 0) as practice_count,
    coalesce(s.active_practice_count, 0) as active_practice_count,
    coalesce(s.verified_practice_count, 0) as verified_practice_count,
    coalesce(s.verified_active_practice_count, 0) as verified_active_practice_count,

    coalesce(s.has_active_cover_crop, false) as has_active_cover_crop,
    coalesce(s.has_active_reduced_tillage, false) as has_active_reduced_tillage,
    coalesce(s.has_active_crop_rotation, false) as has_active_crop_rotation,
    coalesce(s.has_active_water_efficiency, false) as has_active_water_efficiency,
    coalesce(s.has_active_organic_fertilizer, false) as has_active_organic_fertilizer

from fields f

left join sustainability s
    on f.field_id = s.field_id
