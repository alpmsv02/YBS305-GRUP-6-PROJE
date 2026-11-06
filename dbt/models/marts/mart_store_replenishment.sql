-- Mağaza sevkiyat planı: SKU × mağaza için önerilen haftalık sevkiyat miktarı (bölgesel DC → mağaza).
-- Yöntem: son 13 tam haftanın ortalama talebi + emniyet stoku (z × σ, tedarik süresi 1 hafta).
with last_week as (
    select max(wm_yr_wk) as max_wk from {{ ref('fct_sales_weekly') }} where is_complete_week
),

weeks_in_scope as (
    select distinct wm_yr_wk
    from {{ ref('fct_sales_weekly') }}, last_week
    where wm_yr_wk <= max_wk and is_complete_week
    order by wm_yr_wk desc
    limit 13
),

stats as (
    select
        w.dc_id,
        w.store_id,
        w.item_id,
        w.dept_id,
        w.cat_id,
        avg(w.units)          as avg_weekly_units,
        stddev_samp(w.units)  as std_weekly_units,
        max(w.units)          as max_weekly_units,
        sum(w.units)          as units_13w,
        sum(w.revenue)        as revenue_13w
    from {{ ref('fct_sales_weekly') }} w
    join weeks_in_scope s on s.wm_yr_wk = w.wm_yr_wk
    group by 1, 2, 3, 4, 5
)

select
    s.dc_id,
    s.store_id,
    s.item_id,
    s.dept_id,
    s.cat_id,
    z.abc_class,
    z.xyz_class,
    z.warehouse_zone,
    s.units_13w,
    cast(s.avg_weekly_units as decimal(10, 2))                                    as avg_weekly_units,
    cast(coalesce(s.std_weekly_units, 0) as decimal(10, 2))                       as std_weekly_units,
    cast(ceil({{ var('service_level_z') }} * coalesce(s.std_weekly_units, 0)) as integer) as safety_stock,
    cast(ceil(s.avg_weekly_units + {{ var('service_level_z') }} * coalesce(s.std_weekly_units, 0)) as integer)
                                                                                  as recommended_weekly_qty,
    s.max_weekly_units,
    cast(s.revenue_13w / nullif(s.units_13w, 0) as decimal(10, 2))              as avg_unit_price
from stats s
left join {{ ref('mart_sku_abc_xyz') }} z
    on z.item_id = s.item_id
   and z.dc_id = s.dc_id            -- sınıf, mağazanın bağlı olduğu bölgesel DC'nin sınıfıdır
