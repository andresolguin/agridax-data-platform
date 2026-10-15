with normalized as ({{ normalized_weather() }}), ranked as (
    select *, row_number() over(partition by field_id,observed_at order by source_updated_at desc nulls last,ingested_at desc,raw_record_id desc) as rank from normalized
), expected as (
    select to_jsonb(r) - 'rank' || jsonb_build_object('rejection_reason', {{ weather_observation_rejection_reason() }}) as row from ranked r where rank=1
), actual as (
    select to_jsonb(a) as row from {{ ref('stg_weather_observation_winners') }} a
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
