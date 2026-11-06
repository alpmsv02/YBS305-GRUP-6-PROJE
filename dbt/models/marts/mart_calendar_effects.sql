-- Takvim ve hava etkileri: DC × kategori × gün tipi × hava tipi bazında SKU başına ortalama günlük talep
-- ve taban çizgisine (kuru hafta içi günleri) göre artış. day_type ön eki sıralama içindir.
with daily as (
    select
        dc_id,
        cat_id,
        date_day,
        case
            when is_event then case event_type
                when 'Sporting' then '4. Spor etkinliği' when 'Cultural' then '5. Kültürel etkinlik'
                when 'National' then '6. Ulusal bayram' when 'Religious' then '7. Dinî bayram' else '8. Etkinlik' end
            when is_snap and not is_weekend then '3. SNAP hafta içi'
            when is_weekend then '2. Hafta sonu'
            else '1. Hafta içi'
        end as day_type,
        case when is_rainy then 'Yağışlı' else 'Kuru' end as weather_type,
        avg(sales_qty) as avg_units_per_sku
    from {{ ref('fct_sales_daily') }}
    group by 1, 2, 3, 4, 5
),

baseline as (
    select dc_id, cat_id, avg(avg_units_per_sku) as baseline_units
    from daily
    where day_type = '1. Hafta içi' and weather_type = 'Kuru'
    group by 1, 2
)

select
    d.dc_id,
    d.cat_id,
    d.day_type,
    d.weather_type,
    count(*)                                                    as n_days,
    cast(avg(d.avg_units_per_sku) as decimal(8, 3))             as avg_units_per_sku,
    cast(b.baseline_units as decimal(8, 3))                     as baseline_units,
    cast(avg(d.avg_units_per_sku) / b.baseline_units - 1 as decimal(6, 3)) as lift_vs_baseline
from daily d
join baseline b on b.dc_id = d.dc_id and b.cat_id = d.cat_id
group by 1, 2, 3, 4, b.baseline_units
