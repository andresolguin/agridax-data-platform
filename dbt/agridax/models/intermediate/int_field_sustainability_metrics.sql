{{ config(materialized='view') }}

with practices as (

    select
        practice_id,
        field_id,
        practice_type,
        status,
        verified,
        valid_from,
        valid_to,
        updated_at,
        ingested_at

    from {{ ref('stg_sustainability_practices') }}

),

aggregated as (

    select
        field_id,

        count(*) as practice_count,

        count(*) filter (
            where status = 'active'
        ) as active_practice_count,

        count(*) filter (
            where verified
        ) as verified_practice_count,

        count(*) filter (
            where status = 'active'
              and verified
        ) as verified_active_practice_count,

        bool_or(practice_type = 'cover_crop' and status = 'active') as has_active_cover_crop,
        bool_or(practice_type = 'reduced_tillage' and status = 'active') as has_active_reduced_tillage,
        bool_or(practice_type = 'crop_rotation' and status = 'active') as has_active_crop_rotation,
        bool_or(practice_type = 'water_efficiency' and status = 'active') as has_active_water_efficiency,
        bool_or(practice_type = 'organic_fertilizer' and status = 'active') as has_active_organic_fertilizer,

        min(valid_from) as earliest_practice_valid_from,
        max(updated_at) as latest_practice_source_updated_at,
        max(ingested_at) as latest_practice_ingested_at

    from practices

    group by field_id

)

select *
from aggregated
