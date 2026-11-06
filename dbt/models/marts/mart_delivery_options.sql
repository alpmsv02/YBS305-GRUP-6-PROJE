-- Teslimat sıklığı seçenekleri (DC → mağaza): haftada k teslimat için taşıma + stok taşıma maliyeti.
-- Taşıma: k × ⌈haftalık adet / (k × tır kapasitesi)⌉ sefer × gidiş-dönüş maliyeti.
-- Stok taşıma: ortalama stok (haftalık adet / 2k) × birim değer × yıllık taşıma oranı / 52.
with params as (
    select
        max(case when param = 'truck_capacity_units' then value end)   as truck_capacity_units,
        max(case when param = 'holding_cost_rate_annual' then value end) as holding_rate
    from {{ ref('cost_params') }}
),

store_demand as (
    select
        dc_id,
        store_id,
        sum(recommended_weekly_qty)                                   as weekly_qty,
        sum(recommended_weekly_qty * coalesce(avg_unit_price, 0))     as weekly_value_usd
    from {{ ref('mart_store_replenishment') }}
    group by 1, 2
),

k_options as (
    select * from (values (1), (2), (3), (5), (7)) as t(deliveries_per_week)
)

select
    s.dc_id,
    s.store_id,
    k.deliveries_per_week,
    s.weekly_qty,
    cast(s.weekly_value_usd as decimal(12, 2))                              as weekly_value_usd,
    r.distance_km,
    r.duration_hours,
    r.round_trip_cost_usd,
    cast(k.deliveries_per_week * ceil(s.weekly_qty / (k.deliveries_per_week * p.truck_capacity_units)) as integer) as trips_per_week,
    cast(k.deliveries_per_week * ceil(s.weekly_qty / (k.deliveries_per_week * p.truck_capacity_units)) * r.round_trip_cost_usd
         as decimal(12, 2))                                                 as transport_cost_week_usd,
    cast(s.weekly_value_usd / (2 * k.deliveries_per_week) * p.holding_rate / 52 as decimal(12, 2)) as holding_cost_week_usd,
    cast(k.deliveries_per_week * ceil(s.weekly_qty / (k.deliveries_per_week * p.truck_capacity_units)) * r.round_trip_cost_usd
         + s.weekly_value_usd / (2 * k.deliveries_per_week) * p.holding_rate / 52 as decimal(12, 2)) as total_cost_week_usd
from store_demand s
cross join k_options k
cross join params p
join {{ ref('fct_route') }} r
    on r.leg_type = 'DC_TO_STORE' and r.origin_id = s.dc_id and r.dest_id = s.store_id
