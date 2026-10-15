{% macro normalized_field_events() %}
    select raw_record_id, trim(event_id) as event_id,
           lower(trim(source_system)) as source_system, trim(source_event_id) as source_event_id,
           trim(field_id) as field_id, lower(trim(event_type)) as event_type,
           event_timestamp, quantity, lower(trim(unit)) as unit, event_payload,
           source_updated_at, ingested_at, source_batch_id
    from {{ source('raw','field_events') }}
{% endmacro %}

{% macro normalized_weather() %}
    select raw_record_id, trim(observation_id) as observation_id, trim(field_id) as field_id,
           observed_at, temperature_c, rainfall_mm, humidity_pct, wind_speed_kmh,
           lower(trim(source_system)) as source_system, source_updated_at, ingested_at, source_batch_id
    from {{ source('raw','weather_observations') }}
{% endmacro %}

{% macro normalized_field_states() %}
    select raw_record_id, trim(field_id) as field_id, trim(farm_id) as farm_id,
           trim(field_name) as field_name, area_hectares, nullif(trim(crop_type),'') as crop_type,
           nullif(trim(soil_type),'') as soil_type, nullif(trim(irrigation_type),'') as irrigation_type,
           lower(trim(status)) as status, created_at, effective_from, updated_at,
           ingested_at, source_batch_id, source_file_name
    from {{ source('raw','fields') }}
{% endmacro %}
