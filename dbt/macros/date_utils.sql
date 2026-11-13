{% macro last_n_complete_weeks(n) %}
    -- Son n tam haftayı filtrelemek için ortak makro mantığı
    is_complete_week = true
    qualify row_number() over (order by wm_yr_wk desc) <= {{ n }}
{% endmacro %}
