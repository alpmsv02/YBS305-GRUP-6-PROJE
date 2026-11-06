-- Mağaza teslimat planı: toplam haftalık maliyeti (taşıma + stok) en küçükleyen teslimat sıklığı.
with ranked as (
    select
        *,
        row_number() over (partition by store_id order by total_cost_week_usd asc, deliveries_per_week asc) as rn
    from {{ ref('mart_delivery_options') }}
)

select
    o.dc_id,
    o.store_id,
    st.city                                   as store_city,
    o.deliveries_per_week                     as optimal_deliveries_per_week,
    o.trips_per_week,
    o.weekly_qty,
    o.weekly_value_usd,
    o.distance_km,
    o.duration_hours,
    o.round_trip_cost_usd,
    o.transport_cost_week_usd,
    o.holding_cost_week_usd,
    o.total_cost_week_usd,
    cast(o.transport_cost_week_usd / nullif(o.weekly_qty, 0) as decimal(8, 4)) as transport_cost_per_unit_usd,
    case o.deliveries_per_week
        when 7 then 'Her gün' when 5 then 'Hafta içi her gün' when 3 then 'Haftada 3 (Pzt-Çrş-Cum)'
        when 2 then 'Haftada 2 (Pzt-Per)' else 'Haftada 1' end as schedule_label
from ranked o
join {{ ref('dim_store') }} st on st.store_id = o.store_id
where o.rn = 1
