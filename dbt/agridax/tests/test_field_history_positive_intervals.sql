select field_id,field_state_valid_from,field_state_valid_to,area_hectares
from {{ ref('int_field_history') }}
where field_state_valid_to <= field_state_valid_from
   or area_hectares is null or area_hectares <= 0
   or area_hectares::text in ('NaN','Infinity','-Infinity')
