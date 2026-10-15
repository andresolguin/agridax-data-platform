{% test finite(model, column_name) %}
select {{ column_name }} from {{ model }}
where {{ column_name }}::text in ('NaN','Infinity','-Infinity')
{% endtest %}
