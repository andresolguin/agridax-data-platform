select * from {{ ref('fct_field_daily_performance') }}
where data_completeness_status='unexpected_empty'
   or has_activity_data is distinct from (event_count is not null)
   or has_weather_data is distinct from (observation_count is not null)
