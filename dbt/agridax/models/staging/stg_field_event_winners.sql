{% set scan = ingestion_scan_context('field_events') %}

{{ config(
    materialized='incremental',
    unique_key=['source_system', 'source_event_id'],
    incremental_strategy='delete+insert',
    on_schema_change='fail',
    pre_hook="{{ prepare_ingestion_scan('field_events') }}",
    post_hook="{{ processing_scan_hook('field_events') }}"
) }}

{% do validate_incremental_backfill() %}

with normalized_raw as not materialized (

    {{ normalized_field_events() }}
    where ingested_at < {{ processing_horizon_sql() }}

),

{% if is_incremental() %}

changed_keys as (

    select distinct
        source_system,
        source_event_id

    from normalized_raw

    where {{ incremental_ingestion_predicate('ingested_at', scan) }}

),

candidates as (

    select
        raw.*

    from normalized_raw as raw

    inner join changed_keys as changed
        on raw.source_system = changed.source_system
       and raw.source_event_id = changed.source_event_id

),

{% else %}

candidates as (

    select *
    from normalized_raw

),

{% endif %}

ranked as (

    select
        *,
        row_number() over (
            partition by source_system, source_event_id
            order by
                source_updated_at desc nulls last,
                ingested_at desc,
                raw_record_id desc
        ) as delivery_rank

    from candidates

),

validated as (

    select
        *,
        {{ field_event_rejection_reason() }} as rejection_reason

    from ranked

    where delivery_rank = 1

)

select
    raw_record_id,
    event_id,
    source_system,
    source_event_id,
    field_id,
    event_type,
    event_timestamp,
    quantity,
    unit,
    event_payload,
    source_updated_at,
    ingested_at,
    source_batch_id,
    rejection_reason

from validated
