-- Ana olgu tablosu: SKU × mağaza × gün. Adet, fiyat, ciro, takvim bayrakları (SNAP: mağazanın eyaletine göre) ve hava durumu.
select
    c.date_day,
    c.wm_yr_wk,
    s.state_id                                      as dc_id,        -- bölgesel dağıtım merkezi = eyalet
    s.state_id,
    s.store_id,
    s.item_id,
    s.dept_id,
    s.cat_id,
    s.sales_qty,
    p.sell_price,
    cast(s.sales_qty * p.sell_price as decimal(12, 2)) as revenue,
    c.weekday_name,
    c.weekday_num,
    cast(c.weekday_num as varchar) || '. ' || case c.weekday_name
        when 'Saturday' then 'Cumartesi' when 'Sunday' then 'Pazar' when 'Monday' then 'Pazartesi'
        when 'Tuesday' then 'Salı' when 'Wednesday' then 'Çarşamba' when 'Thursday' then 'Perşembe'
        else 'Cuma' end                              as weekday_label,  -- M5 kuralı: 1 = Cumartesi
    c.is_weekend,
    c.is_event,
    c.event_type,
    c.event_name,
    case s.state_id
        when 'CA' then c.is_snap_ca
        when 'TX' then c.is_snap_tx
        when 'WI' then c.is_snap_wi
    end                                             as is_snap,
    w.temp_mean_c,
    w.precipitation_mm,
    w.is_rainy
from {{ ref('stg_sales_long') }} s
join {{ ref('stg_calendar') }} c
    on c.day_key = s.day_key
left join {{ ref('stg_prices') }} p
    on p.store_id = s.store_id
   and p.item_id = s.item_id
   and p.wm_yr_wk = c.wm_yr_wk
left join {{ ref('stg_weather') }} w
    on w.store_id = s.store_id
   and w.date_day = c.date_day
