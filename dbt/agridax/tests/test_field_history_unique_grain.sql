select field_id,field_state_valid_from,count(*) as state_count
from {{ ref('int_field_history') }}
group by field_id,field_state_valid_from
having count(*) <> 1
