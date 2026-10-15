select
    field_id,
    business_date,
    count(*) as row_count

from {{ ref('fct_field_daily_performance') }}

group by
    field_id,
    business_date

having count(*) <> 1
