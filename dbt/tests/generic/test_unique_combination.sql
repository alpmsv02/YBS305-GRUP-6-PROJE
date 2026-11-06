{% test dbt_utils_free_unique_combination(model, combination_of_columns) %}
-- Belirtilen sütun kombinasyonunun tekil olduğunu doğrular (dbt_utils bağımlılığı olmadan).
select {{ combination_of_columns | join(', ') }}, count(*) as n
from {{ model }}
group by {{ combination_of_columns | join(', ') }}
having count(*) > 1
{% endtest %}
