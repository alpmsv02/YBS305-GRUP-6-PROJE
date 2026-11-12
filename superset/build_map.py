"""Lojistik ağı haritası için veri üretir: DuckDB mart'larından superset/map/data.json.
Kullanım: ../.venv/bin/python build_map.py   (scripts/build_and_publish.sh tarafından da çağrılır)
"""
import json, pathlib
import duckdb

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "superset" / "map" / "data.json"
con = duckdb.connect(str(ROOT / "data/warehouse/dc_planning.duckdb"), read_only=True)


def rows(sql):
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


dcs = rows("""
    select d.dc_id, d.dc_name, d.dc_level, d.walmart_dc_number, d.city, d.state_id, d.latitude, d.longitude, d.source_note,
           h.n_stores, h.weekly_qty, h.weekly_value_usd, h.distance_km, h.duration_hours, h.lead_time_days, h.diesel_usd_gal,
           h.round_trip_cost_usd, h.trucks_per_week, h.transport_cost_week_usd, h.transport_cost_per_unit_usd, h.pipeline_stock_units
    from main_marts.dim_dc d left join main_marts.mart_hub_supply_plan h on h.dc_id = d.dc_id order by d.dc_level desc, d.dc_id""")

zones = rows("""
    select dc_id, warehouse_zone, count(*) as skus, sum(units_52w) as units
    from main_marts.mart_sku_abc_xyz group by 1, 2 order by 1, 2""")
zone_map = {}
for z in zones:
    zone_map.setdefault(z["dc_id"], {})[z["warehouse_zone"]] = {"skus": z["skus"], "units": int(z["units"])}
for d in dcs:
    d["zones"] = zone_map.get(d["dc_id"], {})

stores = rows("""
    select s.store_id, s.dc_id, s.city, s.latitude, s.longitude,
           p.schedule_label, p.optimal_deliveries_per_week, p.trips_per_week, p.weekly_qty, p.weekly_value_usd, p.distance_km,
           p.duration_hours, p.round_trip_cost_usd, p.transport_cost_week_usd, p.holding_cost_week_usd, p.total_cost_week_usd,
           p.transport_cost_per_unit_usd
    from main_marts.dim_store s join main_marts.mart_delivery_plan p on p.store_id = s.store_id order by s.store_id""")

cat = rows("""
    select store_id, cat_id, sum(recommended_weekly_qty) as qty, sum(case when warehouse_zone='HOT' then 1 else 0 end) as hot_skus
    from main_marts.mart_store_replenishment group by 1, 2 order by 1, 2""")
cat_map = {}
for c in cat:
    cat_map.setdefault(c["store_id"], {})[c["cat_id"]] = int(c["qty"])
rev = {r["store_id"]: float(r["rev"]) for r in rows("select store_id, sum(revenue) rev from main_marts.fct_sales_weekly group by 1")}
top = rows("""select store_id, item_id, recommended_weekly_qty from (
    select store_id, item_id, recommended_weekly_qty, row_number() over (partition by store_id order by recommended_weekly_qty desc) rn
    from main_marts.mart_store_replenishment) where rn <= 3 order by store_id, rn""")
top_map = {}
for t in top:
    top_map.setdefault(t["store_id"], []).append(f"{t['item_id']} ({t['recommended_weekly_qty']})")
for s in stores:
    s["categories"] = cat_map.get(s["store_id"], {})
    s["revenue_2y"] = rev.get(s["store_id"], 0)
    s["top_skus"] = top_map.get(s["store_id"], [])

opts = rows("select store_id, deliveries_per_week, total_cost_week_usd from main_marts.mart_delivery_options order by 1, 2")
opt_map = {}
for o in opts:
    opt_map.setdefault(o["store_id"], []).append([o["deliveries_per_week"], float(o["total_cost_week_usd"])])
for s in stores:
    s["cost_curve"] = opt_map.get(s["store_id"], [])

totals = rows("""
    select (select sum(trucks_per_week) from main_marts.mart_hub_supply_plan) as hub_trucks,
           (select sum(transport_cost_week_usd) from main_marts.mart_hub_supply_plan) as hub_cost,
           (select sum(weekly_qty) from main_marts.mart_hub_supply_plan) as weekly_qty,
           (select sum(trips_per_week) from main_marts.mart_delivery_plan) as store_trips,
           (select sum(total_cost_week_usd) from main_marts.mart_delivery_plan) as store_cost,
           (select sum(distance_km) from main_marts.fct_route) as network_km""")[0]


def clean(o):
    if isinstance(o, dict):
        return {k: clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [clean(v) for v in o]
    if hasattr(o, "__float__") and not isinstance(o, (int, float, bool)):
        return float(o)
    return o


OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(clean({"dcs": dcs, "stores": stores, "totals": totals,
                                 "generated_from": "dbt marts: mart_hub_supply_plan, mart_delivery_plan, mart_sku_abc_xyz, fct_route"}),
                          ensure_ascii=False, indent=1))
print("wrote", OUT, len(dcs), "dcs", len(stores), "stores")
