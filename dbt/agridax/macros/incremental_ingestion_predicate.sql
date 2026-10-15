{% macro normalized_timestamp(value, label) %}
    {% if value is not string or value != value | trim or value | length < 20 %}
        {{ exceptions.raise_compiler_error(label ~ ' must be ISO-8601 with seconds and an explicit timezone offset') }}
    {% endif %}
    {% set normalized = value[:-1] ~ '+00:00' if value.endswith('Z') else value %}
    {% if normalized[10:11] != 'T' or normalized[-6:-5] not in ['+','-'] or normalized[-3:-2] != ':' %}
        {{ exceptions.raise_compiler_error(label ~ ' requires explicit Z or ±HH:MM timezone') }}
    {% endif %}
    {% set fraction = normalized[19:-6] %}
    {% if fraction and (fraction[0:1] != '.' or not fraction[1:].isdigit() or fraction | length > 7) %}
        {{ exceptions.raise_compiler_error(label ~ ' supports at most six fractional digits') }}
    {% endif %}
    {% set format = '%Y-%m-%dT%H:%M:%S.%f%z' if fraction else '%Y-%m-%dT%H:%M:%S%z' %}
    {# Invalid calendars raise a compilation error, before PostgreSQL execution. #}
    {% set parsed = modules.datetime.datetime.strptime(normalized, format) %}
    {{ return(parsed.astimezone(modules.pytz.timezone('UTC'))) }}
{% endmacro %}

{% macro validate_incremental_backfill() %}
    {% set start = var('backfill_start', none) %}
    {% set end = var('backfill_end', none) %}
    {% if (start is none) != (end is none) %}
        {{ exceptions.raise_compiler_error('Controlled backfills require both backfill_start and backfill_end') }}
    {% endif %}
    {% if start is not none %}
        {% set lower = normalized_timestamp(start, 'backfill_start') %}
        {% set upper = normalized_timestamp(end, 'backfill_end') %}
        {% if lower >= upper %}
            {{ exceptions.raise_compiler_error('backfill_start must be strictly earlier than backfill_end') }}
        {% endif %}
        {% if flags.FULL_REFRESH %}
            {{ exceptions.raise_compiler_error('Controlled backfills cannot be combined with --full-refresh') }}
        {% endif %}
        {% if execute and not is_incremental() %}
            {{ exceptions.raise_compiler_error('Controlled backfills require an existing incremental table; first run is refused') }}
        {% endif %}
    {% endif %}
{% endmacro %}

{% macro processing_horizon_sql() %}
    {% set horizon = normalized_timestamp(var('processing_horizon', run_started_at.isoformat()), 'processing_horizon') %}
    {{ return("cast('" ~ horizon.isoformat() ~ "' as timestamptz)") }}
{% endmacro %}

{% macro ingestion_scan_context(stream) %}
    {% do validate_incremental_backfill() %}
    {% if stream not in ['field_events','weather_observations'] %}
        {{ exceptions.raise_compiler_error('Unknown incremental stream') }}
    {% endif %}
    {% set seconds = var('ingestion_lookback_seconds', 300) %}
    {% if seconds is boolean or seconds is not number or seconds < 0 or seconds > 86400 or seconds != seconds | int %}
        {{ exceptions.raise_compiler_error('ingestion_lookback_seconds must be an integer from 0 through 86400') }}
    {% endif %}
    {% if var('backfill_start', none) is not none %}
        {% set lower = "cast('" ~ normalized_timestamp(var('backfill_start'),'backfill_start').isoformat() ~ "' as timestamptz)" %}
        {% set upper = "cast('" ~ normalized_timestamp(var('backfill_end'),'backfill_end').isoformat() ~ "' as timestamptz)" %}
        {{ return({'lower':lower, 'upper':upper, 'backfill':true}) }}
    {% endif %}
    {% set lower = '(case when exists (select 1 from ' ~ this ~ ') then (select processed_through - (' ~ (seconds | int) ~ " * interval '1 second') from ops.processing_checkpoints where stream='" ~ stream ~ "') else null::timestamptz end)" if is_incremental() else 'null::timestamptz' %}
    {{ return({'lower':lower, 'upper':processing_horizon_sql(), 'backfill':false}) }}
{% endmacro %}

{% macro incremental_ingestion_predicate(column_name='ingested_at', scan=none) %}
    {% if scan is none %}
        {{ exceptions.raise_compiler_error('An explicit stream scan context is required') }}
    {% endif %}
    ({{ scan.lower }} is null or {{ column_name }} >= {{ scan.lower }})
    and {{ column_name }} < {{ scan.upper }}
{% endmacro %}

{% macro safe_run_id() %}
    {% set value = var('release_run_id', none) %}
    {% if value is none %}{{ return(none) }}{% endif %}
    {% if value is not string or value | length != 36 or value[8:9] != '-' or value[13:14] != '-' or value[18:19] != '-' or value[23:24] != '-' or value | replace('-','') | length != 32 %}
        {{ exceptions.raise_compiler_error('release_run_id must be a UUID') }}
    {% endif %}
    {% for char in value | lower | replace('-','') %}
        {% if char not in '0123456789abcdef' %}{{ exceptions.raise_compiler_error('Invalid release_run_id') }}{% endif %}
    {% endfor %}
    {{ return(value | lower) }}
{% endmacro %}

{% macro managed_run_hook() %}
    {% if flags.WHICH in ['run','build','snapshot','seed'] %}
        {% set run_id = safe_run_id() %}
        {% if run_id is none %}
            {{ exceptions.raise_compiler_error('Use python -m agridax.pipeline for mutating dbt commands; a managed run is required') }}
        {% endif %}
        {% set app = target.application_name %}
        {% if app is not string or app | length != 41 or not app.startswith('agri_dbt_') %}
            {{ exceptions.raise_compiler_error('A managed dbt application identity is required') }}
        {% endif %}
        {% for char in app[9:] %}
            {% if char not in '0123456789abcdef' %}
                {{ exceptions.raise_compiler_error('Invalid managed application identity') }}
            {% endif %}
        {% endfor %}
        select set_config('application_name', '{{ app }}', false);
        select ops.assert_managed_run('{{ run_id }}'::uuid)
    {% else %}
        select 1
    {% endif %}
{% endmacro %}

{% macro prepare_ingestion_scan(stream) %}
    {% set scan = ingestion_scan_context(stream) %}
    {# Freeze BEFORE target writes: an empty target must keep an all-key scan. #}
    select set_config(
        'agridax.{{ stream }}_scan_lower', coalesce(({{ scan.lower }})::text, ''), true
    )
{% endmacro %}

{% macro processing_scan_hook(stream) %}
    {% set run_id = safe_run_id() %}
    {% if run_id is none %}{{ return('select 1') }}{% endif %}
    {% set context = ingestion_scan_context(stream) %}
    {% set scan = {'lower': "nullif(current_setting('agridax." ~ stream ~ "_scan_lower'), '')::timestamptz", 'upper':context.upper, 'backfill':context.backfill} %}
    {% set key = '(lower(trim(source_system)), trim(source_event_id))' if stream == 'field_events' else '(trim(field_id), observed_at)' %}
    select ops.record_processing_scan(
        '{{ run_id }}'::uuid, '{{ stream }}', {{ scan.lower }}, {{ scan.upper }},
        (select count(*) from {{ source('raw',stream) }} where {{ incremental_ingestion_predicate('ingested_at',scan) }}),
        (select count(distinct {{ key }}) from {{ source('raw',stream) }} where {{ incremental_ingestion_predicate('ingested_at',scan) }}),
        {{ 'true' if scan.backfill else 'false' }}
    )
{% endmacro %}
