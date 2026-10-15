with ranked as (
    select *, row_number() over (partition by field_id order by effective_from desc) as rank
    from {{ ref('stg_field_state_winners') }}
    where effective_from <= {{ processing_horizon_sql() }}
), expected as (
    select to_jsonb(r) - 'rank' as row from ranked r where rank=1
), actual as (
    select to_jsonb(t) as row from {{ ref('stg_fields') }} t
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
