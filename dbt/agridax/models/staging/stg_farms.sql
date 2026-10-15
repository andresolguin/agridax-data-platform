{{ config(materialized='view') }}

with source_data as (

    select
        raw_record_id,
        trim(farm_id) as farm_id,
        trim(farm_name) as farm_name,
        upper(trim(country_code)) as country_code,
        nullif(trim(region), '') as region,
        nullif(trim(owner_type), '') as owner_type,
        created_at,
        updated_at,
        ingested_at,
        source_batch_id,
        source_file_name

    from {{ source('raw', 'farms') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by farm_id
            order by
                updated_at desc,
                ingested_at desc,
                raw_record_id desc
        ) as version_rank

    from source_data

)

select
    raw_record_id,
    farm_id,
    farm_name,
    country_code,
    region,
    owner_type,
    created_at,
    updated_at,
    ingested_at,
    source_batch_id,
    source_file_name

from ranked
where version_rank = 1