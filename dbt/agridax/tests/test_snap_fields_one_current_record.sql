select
    field_id,
    count(*) as current_record_count

from {{ ref('snap_fields') }}

where dbt_valid_to is null

group by field_id

having count(*) <> 1