{{ config(materialized='view') }}

with normalized_raw as (

    {{ normalized_field_states() }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by field_id, effective_from
            order by
                updated_at desc,
                ingested_at desc,
                raw_record_id desc
        ) as revision_rank

    from normalized_raw

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

where revision_rank = 1