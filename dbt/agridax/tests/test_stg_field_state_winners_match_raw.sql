with normalized as ({{ normalized_field_states() }}), ranked as (
    select *, row_number() over(partition by field_id,effective_from order by updated_at desc,ingested_at desc,raw_record_id desc) as rank from normalized
), expected as (
    select to_jsonb(r) - 'rank' as row from ranked r where rank=1
), actual as (
    select to_jsonb(a) as row from {{ ref('stg_field_state_winners') }} a
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
