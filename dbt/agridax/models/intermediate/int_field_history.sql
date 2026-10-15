{{ config(materialized='view') }}

with canonical_states as (

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

    from {{ ref('stg_field_state_winners') }}

),

business_history as (

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
        effective_from as field_state_valid_from,
        lead(effective_from) over (
            partition by field_id
            order by effective_from
        ) as field_state_valid_to,
        updated_at as source_updated_at,
        ingested_at

    from canonical_states

)

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
    field_state_valid_from,
    field_state_valid_to,
    source_updated_at,
    ingested_at

from business_history