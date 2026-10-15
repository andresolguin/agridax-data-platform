{% macro field_event_rejection_reason(
    event_id_col='event_id',
    source_system_col='source_system',
    source_event_id_col='source_event_id',
    field_id_col='field_id',
    event_type_col='event_type',
    event_timestamp_col='event_timestamp',
    quantity_col='quantity',
    unit_col='unit'
) %}

    case
        when {{ business_text_is_blank(event_id_col) }}
            then 'missing_event_id'

        when {{ business_text_is_blank(source_system_col) }}
            then 'missing_source_system'

        when {{ business_text_is_blank(source_event_id_col) }}
            then 'missing_source_event_id'

        when {{ business_text_is_blank(field_id_col) }}
            then 'missing_field_id'

        when {{ business_text_is_blank(event_type_col) }}
            then 'missing_event_type'

        when {{ event_timestamp_col }} is null
            then 'missing_event_timestamp'

        when {{ event_type_col }} not in (
            'planting',
            'irrigation',
            'fertilizer',
            'pesticide',
            'harvest',
            'soil_measurement'
        )
            then 'unsupported_event_type'

        when {{ quantity_col }} is null
            then 'missing_quantity'

        when {{ quantity_col }}::text in ('NaN', 'Infinity', '-Infinity')
            then 'non_finite_quantity'

        when {{ quantity_col }} < 0
           then 'negative_quantity'

        when {{ business_text_is_blank(unit_col) }}
            then 'missing_unit'

        when {{ event_type_col }} = 'planting'
         and {{ unit_col }} is distinct from 'ha'
            then 'invalid_unit_for_planting'

        when {{ event_type_col }} = 'irrigation'
         and {{ unit_col }} is distinct from 'mm'
            then 'invalid_unit_for_irrigation'

        when {{ event_type_col }} in ('fertilizer', 'pesticide', 'harvest')
         and {{ unit_col }} is distinct from 'kg'
            then 'invalid_unit_for_mass_event'

        when {{ event_type_col }} = 'soil_measurement'
         and {{ unit_col }} is distinct from 'ph'
            then 'invalid_unit_for_soil_measurement'

        else null
    end

{% endmacro %}
