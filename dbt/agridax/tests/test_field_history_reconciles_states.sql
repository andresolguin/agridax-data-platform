with expected as (
    select field_id,farm_id,field_name,area_hectares,crop_type,soil_type,irrigation_type,status,
           created_at,effective_from as field_state_valid_from,updated_at as source_updated_at,ingested_at
    from {{ ref('stg_field_state_winners') }}
), actual as (
    select field_id,farm_id,field_name,area_hectares,crop_type,soil_type,irrigation_type,status,
           created_at,field_state_valid_from,source_updated_at,ingested_at
    from {{ ref('int_field_history') }}
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
