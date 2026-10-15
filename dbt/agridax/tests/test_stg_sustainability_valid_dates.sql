select
    practice_id,
    valid_from,
    valid_to

from {{ ref('stg_sustainability_practices') }}

where valid_to is not null
  and valid_to < valid_from