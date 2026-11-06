-- Lojistik ağ bacakları: HUB→DC ve DC→STORE; mesafe, süre ve sefer maliyeti (ATRI maliyet/mil + bölgesel dizel fiyatı).
with params as (
    select
        max(case when param = 'atri_cost_per_mile_2016' then value end)       as cost_per_mile,
        max(case when param = 'atri_fuel_cost_per_mile_2016' then value end)  as fuel_cost_per_mile,
        max(case when param = 'truck_mpg' then value end)                     as truck_mpg,
        max(case when param = 'handling_days_dc' then value end)              as handling_days_dc
    from {{ ref('cost_params') }}
),

last_sales_day as (
    select max(date_day) as d from {{ ref('fct_sales_daily') }}
),

diesel_latest as (  -- satış döneminin son haftasındaki bölgesel dizel fiyatı
    select region, price_usd_gal
    from (
        select region, price_usd_gal,
               row_number() over (partition by region order by week_date desc) as rn
        from {{ ref('stg_diesel_prices') }}, last_sales_day
        where week_date <= last_sales_day.d
    )
    where rn = 1
)

select
    r.leg_type,
    r.origin_id,
    r.dest_id,
    r.distance_km,
    r.distance_miles,
    r.duration_min,
    cast(r.duration_min / 60.0 as decimal(6, 1))                            as duration_hours,
    cast(ceil(r.duration_min / 60.0 / 24.0) + p.handling_days_dc as integer) as lead_time_days,
    d.price_usd_gal                                                          as diesel_usd_gal,
    cast((p.cost_per_mile - p.fuel_cost_per_mile) + d.price_usd_gal / p.truck_mpg as decimal(6, 3)) as cost_per_mile_usd,
    cast(2 * r.distance_miles * ((p.cost_per_mile - p.fuel_cost_per_mile) + d.price_usd_gal / p.truck_mpg) as decimal(10, 2))
                                                                             as round_trip_cost_usd,
    r.method
from {{ ref('stg_routes') }} r
cross join params p
left join diesel_latest d
    on d.region = case when r.dest_type = 'DC' then r.dest_id else split_part(r.dest_id, '_', 1) end
where r.leg_type in ('HUB_TO_DC', 'DC_TO_STORE')
