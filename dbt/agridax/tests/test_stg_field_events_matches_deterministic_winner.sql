with normalized as ({{ normalized_field_events() }}), ranked as (
    select *, row_number() over(partition by source_system,source_event_id order by source_updated_at desc nulls last,ingested_at desc,raw_record_id desc) as rank from normalized
), expected as (
    select to_jsonb(r) - 'rank' || jsonb_build_object('rejection_reason', {{ field_event_rejection_reason() }}) as row from ranked r where rank=1
), actual as (
    select to_jsonb(a) as row from {{ ref('stg_field_event_winners') }} a
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
