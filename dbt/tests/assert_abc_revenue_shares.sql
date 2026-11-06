-- Her depo seviyesinde A sınıfı SKU'ların ciro payı %75–%85 aralığında olmalı (ABC eşiği tutarlılık kontrolü).
with shares as (
    select dc_id, sum(case when abc_class = 'A' then revenue_52w else 0 end) / sum(revenue_52w) as a_share
    from {{ ref('mart_sku_abc_xyz') }}
    group by 1
)
select * from shares where a_share < 0.75 or a_share > 0.85
