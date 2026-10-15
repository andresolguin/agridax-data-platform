with scenarios as (

    select
        'ZERO_QTY_TEST'::text as event_id,
        'field_ops'::text as source_system,
        'ZERO_QTY_TEST'::text as source_event_id,
        'FIELD_TEST'::text as field_id,
        'irrigation'::text as event_type,
        '2026-01-01 12:00:00+00'::timestamptz as event_timestamp,
        0::numeric as quantity,
        'mm'::text as unit,
        null::text as expected_rejection_reason

    union all

    select
        'NEGATIVE_QTY_TEST',
        'field_ops',
        'NEGATIVE_QTY_TEST',
        'FIELD_TEST',
        'irrigation',
        '2026-01-01 12:00:00+00'::timestamptz,
        -1::numeric,
        'mm',
        'negative_quantity'

),

evaluated as (

    select
        *,
        {{ field_event_rejection_reason() }} as actual_rejection_reason

    from scenarios

)

select *
from evaluated
where actual_rejection_reason is distinct from expected_rejection_reason