select
    field_id,
    activity_date,
    count(*) as record_count

from {{ ref('int_field_daily_conditions') }}

group by
    field_id,
    activity_date

having count(*) <> 1