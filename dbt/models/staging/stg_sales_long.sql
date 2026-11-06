-- Geniş formattaki satış tablosunu (d_1..d_1941 sütunları) uzun formata çevirir.
-- Kapsam: var('states') eyaletleri, d_{first_day_idx}..d_{last_day_idx} günleri.
-- Sıfır satış günleri KORUNUR: kesikli talep (XYZ / sıfır gün oranı) analizi için gereklidir.
{{ config(materialized='table') }}

{% set first = var('first_day_idx') %}
{% set last = var('last_day_idx') %}
{% set day_cols = [] %}
{% for i in range(first, last + 1) %}
    {% do day_cols.append('d_' ~ i) %}
{% endfor %}

with wide as (
    select
        item_id,
        dept_id,
        cat_id,
        store_id,
        state_id,
        {{ day_cols | join(',\n        ') }}
    from {{ source('m5', 'sales_wide') }}
    where state_id in ({% for s in var('states') %}'{{ s }}'{% if not loop.last %}, {% endif %}{% endfor %})
)

select
    item_id,
    dept_id,
    cat_id,
    store_id,
    state_id,
    day_key,
    cast(sales_qty as integer) as sales_qty
from wide
unpivot (sales_qty for day_key in ({{ day_cols | join(', ') }}))
