{% macro weather_observation_rejection_reason(
    observation_id_col='observation_id',
    field_id_col='field_id',
    observed_at_col='observed_at',
    temperature_c_col='temperature_c',
    humidity_pct_col='humidity_pct',
    rainfall_mm_col='rainfall_mm',
    wind_speed_kmh_col='wind_speed_kmh',
    source_system_col='source_system',
    ingested_at_col='ingested_at'
) %}

    case
        when {{ business_text_is_blank(observation_id_col) }}
            then 'missing_observation_id'

        when {{ business_text_is_blank(field_id_col) }}
            then 'missing_field_id'

        when {{ observed_at_col }} is null
            then 'missing_observed_at'

        when {{ business_text_is_blank(source_system_col) }}
            then 'missing_source_system'

        when {{ ingested_at_col }} is null
            then 'missing_ingested_at'

        when {{ temperature_c_col }}::text in ('NaN', 'Infinity', '-Infinity')
            then 'non_finite_temperature'

        when {{ humidity_pct_col }}::text in ('NaN', 'Infinity', '-Infinity')
            then 'non_finite_humidity'

        when {{ rainfall_mm_col }}::text in ('NaN', 'Infinity', '-Infinity')
            then 'non_finite_rainfall'

        when {{ wind_speed_kmh_col }}::text in ('NaN', 'Infinity', '-Infinity')
            then 'non_finite_wind_speed'

        when {{ humidity_pct_col }} is not null
         and (
                {{ humidity_pct_col }} < 0
                or {{ humidity_pct_col }} > 100
             )
            then 'invalid_humidity_pct'

        when {{ rainfall_mm_col }} is not null
         and {{ rainfall_mm_col }} < 0
            then 'negative_rainfall'

        when {{ wind_speed_kmh_col }} is not null
         and {{ wind_speed_kmh_col }} < 0
            then 'negative_wind_speed'

        else null
    end

{% endmacro %}
