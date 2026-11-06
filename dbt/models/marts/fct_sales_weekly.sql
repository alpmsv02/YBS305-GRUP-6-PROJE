-- Haftalık toplam: SKU × mağaza × Walmart haftası. Sevkiyat planlaması haftalık yapılır.
select
    wm_yr_wk,
    min(date_day)                       as week_start,
    dc_id,
    state_id,
    store_id,
    item_id,
    dept_id,
    cat_id,
    sum(sales_qty)                      as units,
    sum(revenue)                        as revenue,
    sum(case when sales_qty = 0 then 1 else 0 end) as zero_days,
    count(*)                            as days_in_week,
    count(*) = 7                        as is_complete_week
from {{ ref('fct_sales_daily') }}
group by 1, 3, 4, 5, 6, 7, 8
