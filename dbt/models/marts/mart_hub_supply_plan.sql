-- Merkez hub → bölgesel DC ikmal planı: haftalık ihtiyaç (mağaza planlarının toplamı), sefer sayısı, tedarik süresi, maliyet.
with params as (
    select max(case when param = 'truck_capacity_units' then value end) as truck_capacity_units
    from {{ ref('cost_params') }}
),

dc_demand as (
    select dc_id, sum(weekly_qty) as weekly_qty, sum(weekly_value_usd) as weekly_value_usd, count(*) as n_stores
    from {{ ref('mart_delivery_plan') }}
    group by 1
)

select
    d.dc_id,
    dc.dc_name,
    dc.city                                            as dc_city,
    d.n_stores,
    d.weekly_qty,
    cast(d.weekly_value_usd as decimal(12, 2))          as weekly_value_usd,
    r.distance_km,
    r.duration_hours,
    r.lead_time_days,
    r.diesel_usd_gal,
    r.round_trip_cost_usd,
    cast(ceil(d.weekly_qty / p.truck_capacity_units) as integer)                       as trucks_per_week,
    cast(ceil(d.weekly_qty / p.truck_capacity_units) * r.round_trip_cost_usd as decimal(12, 2)) as transport_cost_week_usd,
    cast(ceil(d.weekly_qty / p.truck_capacity_units) * r.round_trip_cost_usd / d.weekly_qty as decimal(8, 4)) as transport_cost_per_unit_usd,
    cast(d.weekly_qty / 7.0 * r.lead_time_days as integer)                              as pipeline_stock_units  -- yoldaki stok
from dc_demand d
join {{ ref('dim_dc') }} dc on dc.dc_id = d.dc_id
join {{ ref('fct_route') }} r on r.leg_type = 'HUB_TO_DC' and r.dest_id = d.dc_id
cross join params p
