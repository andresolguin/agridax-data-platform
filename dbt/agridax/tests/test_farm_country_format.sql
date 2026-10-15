select farm_id,country_code from {{ ref('stg_farms') }}
where country_code !~ '^[A-Z]{2}$'
