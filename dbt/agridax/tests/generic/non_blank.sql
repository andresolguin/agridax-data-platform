{% test non_blank(model, column_name) %}
select {{ column_name }} from {{ model }}
where {{ business_text_is_blank(column_name) }}
{% endtest %}
