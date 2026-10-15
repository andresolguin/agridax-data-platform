with expected as (
    select to_jsonb(c) - 'rejection_reason' as row
    from {{ ref('stg_weather_observation_winners') }} c where rejection_reason is null
), actual as (
    select to_jsonb(t) as row from {{ ref('stg_weather_observations') }} t
)
(select * from expected except select * from actual)
union all
(select * from actual except select * from expected)
