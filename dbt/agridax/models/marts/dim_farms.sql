{{ config(materialized='table') }}

with farms as (

    select
        farm_id,
        farm_name,
        country_code,
        region,
        owner_type,
        created_at,
        updated_at,
        ingested_at

    from {{ ref('stg_farms') }}

),

field_rollup as (

    select
        farm_id,
        count(*) as field_count,
        sum(area_hectares) as total_area_hectares,
        count(*) filter (where status = 'active') as active_field_count,
        count(distinct crop_type) filter (where crop_type is not null) as current_crop_type_count

    from {{ ref('stg_fields') }}

    group by farm_id

)

select
    f.farm_id,
    f.farm_name,
    f.country_code,
    f.region,
    f.owner_type,
    f.created_at,
    f.updated_at,
    f.ingested_at,

    coalesce(r.field_count, 0) as field_count,
    coalesce(r.active_field_count, 0) as active_field_count,
    coalesce(r.total_area_hectares, 0) as total_area_hectares,
    coalesce(r.current_crop_type_count, 0) as current_crop_type_count

from farms f

left join field_rollup r
    on f.farm_id = r.farm_id
