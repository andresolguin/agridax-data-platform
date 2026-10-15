{{ config(materialized='view') }}

with source_data as (

    select
        raw_record_id,
        trim(practice_id) as practice_id,
        trim(field_id) as field_id,
        lower(trim(practice_type)) as practice_type,
        lower(trim(status)) as status,
        verified,
        valid_from,
        valid_to,
        updated_at,
        ingested_at,
        source_batch_id,
        source_file_name

    from {{ source('raw', 'sustainability_practices') }}

),

ranked as (

    select
        *,
        row_number() over (
            partition by practice_id
            order by
                updated_at desc,
                ingested_at desc,
                raw_record_id desc
        ) as version_rank

    from source_data

)

select
    raw_record_id,
    practice_id,
    field_id,
    practice_type,
    status,
    verified,
    valid_from,
    valid_to,
    updated_at,
    ingested_at,
    source_batch_id,
    source_file_name

from ranked
where version_rank = 1