with events as (
    select 'EVT'::text as event_id, E'\t\r\n'::text as source_system,
           'KEY'::text as source_event_id, 'FIELD'::text as field_id,
           'irrigation'::text as event_type, '2026-01-01T00:00:00Z'::timestamptz as event_timestamp,
           1::numeric as quantity, 'mm'::text as unit,
           'missing_source_system'::text as expected
    union all
    select E'\t','field_ops','KEY','FIELD','irrigation','2026-01-01T00:00:00Z'::timestamptz,1,'mm','missing_event_id'
    union all
    select 'EVT','field_ops',E'\n','FIELD','irrigation','2026-01-01T00:00:00Z'::timestamptz,1,'mm','missing_source_event_id'
), weather as (
    select E'\t'::text as observation_id,'FIELD'::text as field_id,
           '2026-01-01T00:00:00Z'::timestamptz as observed_at,
           20::numeric as temperature_c,60::numeric as humidity_pct,0::numeric as rainfall_mm,
           0::numeric as wind_speed_kmh,'weather'::text as source_system,
           '2026-01-01T00:00:01Z'::timestamptz as ingested_at,'missing_observation_id'::text as expected
    union all
    select 'WX','FIELD','2026-01-01T00:00:00Z'::timestamptz,20,60,0,0,E'\n','2026-01-01T00:00:01Z'::timestamptz,'missing_source_system'
)
select 'event' as kind,expected from events
where {{ field_event_rejection_reason() }} is distinct from expected
union all
select 'weather' as kind,expected from weather
where {{ weather_observation_rejection_reason() }} is distinct from expected
