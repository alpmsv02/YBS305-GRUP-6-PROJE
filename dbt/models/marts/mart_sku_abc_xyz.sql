-- Depo yerleşimi: her depo seviyesi (HUB = merkez hub, CA/TX/WI = bölgesel DC) ve SKU için
-- ABC (ciro payı) × XYZ (haftalık talep düzensizliği) sınıfı, toplama sırası ve depo bölgesi.
-- Pencere: son 52 tam hafta; CV yalnızca ürünün listede olduğu haftalar üzerinden. zone_label: sıralama ön ekli Türkçe etiket. ABC/XYZ her depo seviyesinde kendi içinde hesaplanır.
with last_week as (
    select max(wm_yr_wk) as max_wk from {{ ref('fct_sales_weekly') }} where is_complete_week
),

weeks_in_scope as (
    select distinct wm_yr_wk
    from {{ ref('fct_sales_weekly') }}, last_week
    where wm_yr_wk <= max_wk and is_complete_week
    order by wm_yr_wk desc
    limit 52
),

weekly_dc as (
    select
        w.dc_id,
        w.item_id,
        w.dept_id,
        w.cat_id,
        w.wm_yr_wk,
        sum(w.units)        as units,
        sum(w.revenue)      as revenue,
        sum(w.zero_days)    as zero_days,
        sum(w.days_in_week) as days
    from {{ ref('fct_sales_weekly') }} w
    join weeks_in_scope s on s.wm_yr_wk = w.wm_yr_wk
    group by 1, 2, 3, 4, 5
),

weekly as (
    select * from weekly_dc
    union all
    select 'HUB' as dc_id, item_id, dept_id, cat_id, wm_yr_wk,
           sum(units), sum(revenue), sum(zero_days), sum(days)
    from weekly_dc
    group by 1, 2, 3, 4, 5
),

per_sku as (
    select
        dc_id,
        item_id,
        dept_id,
        cat_id,
        sum(units)                                  as units_52w,
        sum(revenue)                                as revenue_52w,
        count(*) filter (where revenue is not null) as active_weeks,   -- ürünün listede olduğu (fiyatı olan) haftalar
        avg(units)        filter (where revenue is not null) as avg_weekly_units,
        stddev_samp(units) filter (where revenue is not null) as std_weekly_units,
        sum(zero_days) * 1.0 / sum(days)            as zero_day_share
    from weekly
    group by 1, 2, 3, 4
),

ranked as (
    select
        *,
        sum(revenue_52w) over (partition by dc_id order by revenue_52w desc, units_52w desc, item_id rows between unbounded preceding and current row)
            / sum(revenue_52w) over (partition by dc_id)                 as cum_revenue_share,
        std_weekly_units / nullif(avg_weekly_units, 0)                  as cv_weekly,
        row_number() over (partition by dc_id order by units_52w desc, revenue_52w desc, item_id)  as picking_rank
    from per_sku
),

classified as (
    select
        *,
        case
            when cum_revenue_share <= {{ var('abc_a_threshold') }} then 'A'
            when cum_revenue_share <= {{ var('abc_b_threshold') }} then 'B'
            else 'C'
        end as abc_class,
        case
            when cv_weekly is null then 'Z'
            when cv_weekly < {{ var('xyz_x_threshold') }} then 'X'
            when cv_weekly < {{ var('xyz_y_threshold') }} then 'Y'
            else 'Z'
        end as xyz_class
    from ranked
)

select
    dc_id,
    case when dc_id = 'HUB' then 'Merkez Hub' else dc_id || ' Bölgesel DC' end as dc_name,
    item_id,
    dept_id,
    cat_id,
    units_52w,
    cast(revenue_52w as decimal(12, 2))         as revenue_52w,
    active_weeks,
    cast(avg_weekly_units as decimal(10, 2))    as avg_weekly_units,
    cast(cv_weekly as decimal(6, 3))            as cv_weekly,
    cast(zero_day_share as decimal(5, 3))       as zero_day_share,
    cast(cum_revenue_share as decimal(6, 4))    as cum_revenue_share,
    picking_rank,
    abc_class,
    xyz_class,
    abc_class || xyz_class                      as abc_xyz,
    case
        when abc_class = 'A' and xyz_class in ('X', 'Y') then 'HOT'
        when abc_class = 'A' or (abc_class = 'B' and xyz_class in ('X', 'Y')) then 'WARM'
        else 'COLD'
    end                                         as warehouse_zone,
    case
        when abc_class = 'A' and xyz_class in ('X', 'Y') then '1. HOT'
        when abc_class = 'A' or (abc_class = 'B' and xyz_class in ('X', 'Y')) then '2. WARM'
        else '3. COLD'
    end                                         as zone_label
from classified
