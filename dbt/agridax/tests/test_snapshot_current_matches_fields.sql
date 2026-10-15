with expected as (
    select field_id,farm_id,field_name,area_hectares,crop_type,soil_type,irrigation_type,status,
           created_at,effective_from,updated_at
    from {{ ref('stg_fields') }}
), actual as (
    select field_id,farm_id,field_name,area_hectares,crop_type,soil_type,irrigation_type,status,
           created_at,effective_from,updated_at
    from {{ ref('snap_fields') }} where dbt_valid_to is null
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
