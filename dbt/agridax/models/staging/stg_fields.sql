{{ config(materialized='view') }}

with effective_states as (

    select
        raw_record_id,
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
        ingested_at,
        source_batch_id,
        source_file_name

    from {{ ref('stg_field_state_winners') }}

    where effective_from <= {{ processing_horizon_sql() }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by field_id
            order by
                effective_from desc,
                updated_at desc,
                ingested_at desc,
                raw_record_id desc
        ) as state_rank

    from effective_states

)

select
    raw_record_id,
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
    ingested_at,
    source_batch_id,
    source_file_name

from ranked

where state_rank = 1
