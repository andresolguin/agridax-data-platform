select
    field_id,
    area_hectares

from {{ ref('stg_fields') }}

where area_hectares <= 0