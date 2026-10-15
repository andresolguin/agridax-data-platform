{% macro business_text_is_blank(column_name) %}
    ({{ column_name }} is null or {{ column_name }}::text ~ '^[[:space:]]*$')
{% endmacro %}
