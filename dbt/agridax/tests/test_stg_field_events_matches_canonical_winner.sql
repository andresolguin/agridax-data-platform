with expected as (
    select to_jsonb(c) - 'rejection_reason' as row
    from {{ ref('stg_field_event_winners') }} c where rejection_reason is null
), actual as (
    select to_jsonb(t) as row from {{ ref('stg_field_events') }} t
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
