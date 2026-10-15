with ordered_history as (

    select
        field_id,
        field_state_valid_from,
        field_state_valid_to,
        lag(field_state_valid_to) over (
            partition by field_id
            order by field_state_valid_from
        ) as previous_valid_to

    from {{ ref('int_field_history') }}

)

select
    field_id,
    field_state_valid_from,
    field_state_valid_to,
    previous_valid_to

from ordered_history

where previous_valid_to is not null
  and field_state_valid_from < previous_valid_to
