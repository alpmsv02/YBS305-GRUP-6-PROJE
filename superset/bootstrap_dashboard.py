"""Superset REST API ile dashboard'u sıfırdan kurar (idempotent: aynı slug varsa siler ve yeniden oluşturur).

Kullanım:  ../.venv/bin/python bootstrap_dashboard.py  [--base-url http://127.0.0.1:8088]
Kimlik bilgileri .env dosyasından (ADMIN_USERNAME / ADMIN_PASSWORD) okunur.

Yapı: 4 sekme (Genel Bakış / Depo Yerleşimi / Mağaza Sevkiyatı / Lojistik Ağı), 6 native filtre.
Zaman filtresinin API ile oluşturulan grafiklere uygulanabilmesi için her zamansal grafiğe TEMPORAL_RANGE adhoc filtresi eklenir.
"""
import argparse, json, pathlib, sys
import requests

HERE = pathlib.Path(__file__).resolve().parent
DB_NAME = "DC Planning (DuckDB)"
DB_URI = "duckdb:////data/warehouse/dc_planning.duckdb?access_mode=READ_ONLY"
SCHEMA = "main_marts"
DASH_SLUG = "dc-planning"
DASH_TITLE = "Merkez Hub → Bölgesel DC → Mağaza: Depo Yerleşimi ve Dağıtım Planı"


def load_env():
    env = {}
    for line in (HERE / ".env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


class Superset:
    def __init__(self, base, user, pw):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        r = self.s.post(f"{self.base}/api/v1/security/login",
                        json={"username": user, "password": pw, "provider": "db", "refresh": True})
        r.raise_for_status()
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.s.headers["X-CSRFToken"] = self.s.get(f"{self.base}/api/v1/security/csrf_token/").json()["result"]
        self.s.headers["Referer"] = self.base

    def _chk(self, r):
        if r.status_code >= 400:
            print("API ERROR", r.request.method, r.url, r.status_code, r.text[:800], file=sys.stderr)
            r.raise_for_status()
        return r.json() if r.text else {}

    def get(self, path, **kw):   return self._chk(self.s.get(f"{self.base}/api/v1{path}", **kw))
    def post(self, path, body):  return self._chk(self.s.post(f"{self.base}/api/v1{path}", json=body))
    def put(self, path, body):   return self._chk(self.s.put(f"{self.base}/api/v1{path}", json=body))
    def delete(self, path):      return self._chk(self.s.delete(f"{self.base}/api/v1{path}"))

    def list_all(self, path):
        return self.get(f"{path}/?q={json.dumps({'page_size': 100})}")["result"]


# ---------- helpers for chart params ----------
def sql_metric(expr, label):
    return {"expressionType": "SQL", "sqlExpression": expr, "label": label, "hasCustomLabel": True}


def temporal(col):
    """Native 'Tarih Aralığı' filtresinin uygulanabilmesi için gereken adhoc zaman filtresi."""
    return {"expressionType": "SIMPLE", "subject": col, "operator": "TEMPORAL_RANGE", "operatorId": "TEMPORAL_RANGE",
            "comparator": "No filter", "clause": "WHERE", "isExtra": False, "isNew": False}


def simple(col, op, val):
    return {"expressionType": "SIMPLE", "subject": col, "operator": op, "operatorId": {"==": "EQUALS", ">": "GREATER_THAN"}[op],
            "comparator": val, "clause": "WHERE", "isExtra": False, "isNew": False}


def kpi(ds, title, expr, label, fmt="SMART_NUMBER", subheader="", filters=()):
    return dict(slice_name=title, viz_type="big_number_total", ds=ds, dims=[], params={
        "viz_type": "big_number_total", "metric": sql_metric(expr, label), "adhoc_filters": list(filters),
        "header_font_size": 0.4, "subheader_font_size": 0.125, "y_axis_format": fmt, "time_format": "smart_date",
        "subheader": subheader,
    })


def line(ds, title, x, metrics, groupby=(), filters=()):
    return dict(slice_name=title, viz_type="echarts_timeseries_line", ds=ds, dims=[x, *groupby], params={
        "viz_type": "echarts_timeseries_line", "x_axis": x, "time_grain_sqla": None,  # veri zaten haftalık; P1W Pazartesi'ye kaydırır
        "metrics": metrics, "groupby": list(groupby), "adhoc_filters": list(filters), "order_desc": True,
        "row_limit": 10000, "truncate_metric": True, "show_legend": True, "legendType": "scroll", "legendOrientation": "top",
        "rich_tooltip": True, "tooltipSortByMetric": True, "y_axis_format": "SMART_NUMBER", "x_axis_time_format": "smart_date",
        "color_scheme": "supersetColors", "markerEnabled": False, "seriesType": "line", "area": False, "opacity": 0.2,
    })


def bar(ds, title, x, metrics, groupby=(), stack=False, sort_by_metric=False, row_limit=100, y_fmt="SMART_NUMBER",
        show_values=False, rotate=0, filters=()):
    """Not: Superset 4.1'de metriğe göre sıralama yalnızca tek metrik ve groupby yokken çalışır; diğer durumlarda alfabetik.
    Bu yüzden sıralama gereken eksenlerde ön ekli etiketler (zone_label, day_type, weekday_label) kullanılır."""
    p = {
        "viz_type": "echarts_timeseries_bar", "x_axis": x, "time_grain_sqla": None, "metrics": metrics,
        "groupby": list(groupby), "adhoc_filters": list(filters), "order_desc": True, "row_limit": row_limit,
        "truncate_metric": True, "show_legend": bool(groupby) or len(metrics) > 1, "legendOrientation": "top",
        "rich_tooltip": True, "y_axis_format": y_fmt, "color_scheme": "supersetColors", "stack": stack,
        "orientation": "vertical", "show_value": show_values, "only_total": True,
        "x_axis_sort_series": "name", "x_axis_sort_series_ascending": True, "xAxisLabelRotation": rotate,
    }
    if sort_by_metric and len(metrics) == 1 and not groupby:
        p["x_axis_sort"] = metrics[0]["label"]
        p["x_axis_sort_asc"] = False
    return dict(slice_name=title, viz_type="echarts_timeseries_bar", ds=ds, dims=[x, *groupby], params=p)


def heatmap(ds, title, x, y, metric):
    return dict(slice_name=title, viz_type="heatmap_v2", ds=ds, dims=[x, y], params={
        "viz_type": "heatmap_v2", "x_axis": x, "groupby": y, "metric": metric, "adhoc_filters": [],
        "row_limit": 10000, "sort_x_axis": "alpha_asc", "sort_y_axis": "alpha_asc", "normalize_across": "heatmap",
        "legend_type": "continuous", "show_legend": True, "show_percentage": False, "show_values": True,
        "linear_color_scheme": "superset_seq_1", "value_bounds": [None, None], "y_axis_format": "SMART_NUMBER",
    })


def treemap(ds, title, groupby, metric, filters=()):
    return dict(slice_name=title, viz_type="treemap_v2", ds=ds, dims=list(groupby), params={
        "viz_type": "treemap_v2", "groupby": list(groupby), "metric": metric, "adhoc_filters": list(filters),
        "row_limit": 500, "color_scheme": "supersetColors", "show_labels": True, "show_upper_labels": True,
        "label_type": "key_value", "number_format": "SMART_NUMBER",
    })


def table_raw(ds, title, columns, order_by, row_limit=1000, page=25):
    return dict(slice_name=title, viz_type="table", ds=ds, dims=[], params={
        "viz_type": "table", "query_mode": "raw", "all_columns": list(columns),
        "order_by_cols": [json.dumps([order_by[0], order_by[1]])], "row_limit": row_limit, "adhoc_filters": [],
        "table_timestamp_format": "smart_date", "server_pagination": True, "server_page_length": page,
        "show_cell_bars": True, "color_pn": False, "allow_render_html": False, "groupby": [], "metrics": [], "percent_metrics": [],
    })


# ---------- layout ----------
class Layout:
    def __init__(self, header):
        self.pos = {
            "DASHBOARD_VERSION_KEY": "v2",
            "ROOT_ID": {"type": "ROOT", "id": "ROOT_ID", "children": ["GRID_ID"]},
            "GRID_ID": {"type": "GRID", "id": "GRID_ID", "children": ["TABS-main"], "parents": ["ROOT_ID"]},
            "HEADER_ID": {"id": "HEADER_ID", "type": "HEADER", "meta": {"text": header}},
            "TABS-main": {"type": "TABS", "id": "TABS-main", "children": [], "parents": ["ROOT_ID", "GRID_ID"]},
        }
        self.n = 0
        self.tabs = []

    def tab(self, key, text):
        tid = f"TAB-{key}"
        self.pos[tid] = {"type": "TAB", "id": tid, "children": [], "parents": ["ROOT_ID", "GRID_ID", "TABS-main"],
                         "meta": {"text": text, "defaultText": "Tab title", "placeholder": "Tab title"}}
        self.pos["TABS-main"]["children"].append(tid)
        self.tabs.append(tid)
        return tid

    def row(self, tid, charts, height):
        self.n += 1
        rid = f"ROW-{self.n}"
        parents = ["ROOT_ID", "GRID_ID", "TABS-main", tid]
        self.pos[rid] = {"type": "ROW", "id": rid, "children": [], "parents": parents, "meta": {"background": "BACKGROUND_TRANSPARENT"}}
        self.pos[tid]["children"].append(rid)
        for ch, w in charts:
            self.n += 1
            cid = f"CHART-{self.n}"
            self.pos[cid] = {"type": "CHART", "id": cid, "children": [], "parents": parents + [rid],
                             "meta": {"width": w, "height": height, "chartId": ch["id"], "sliceName": ch["slice_name"]}}
            self.pos[rid]["children"].append(cid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8088")
    a = ap.parse_args()
    env = load_env()
    api = Superset(a.base_url, env["ADMIN_USERNAME"], env["ADMIN_PASSWORD"])

    # 1) database
    dbs = {d["database_name"]: d["id"] for d in api.list_all("/database")}
    if DB_NAME in dbs:
        db_id = dbs[DB_NAME]
        api.put(f"/database/{db_id}", {"sqlalchemy_uri": DB_URI})
    else:
        db_id = api.post("/database/", {"database_name": DB_NAME, "sqlalchemy_uri": DB_URI, "expose_in_sqllab": True,
                                        "allow_ctas": False, "allow_cvas": False, "allow_dml": False})["id"]
    print("database id", db_id)

    # 2) datasets (+ column lists for filter/cross-filter scoping)
    wanted = ["fct_sales_daily", "fct_sales_weekly", "mart_sku_abc_xyz", "mart_store_replenishment", "mart_calendar_effects",
              "mart_delivery_options", "mart_delivery_plan", "mart_hub_supply_plan", "fct_route", "dim_store", "dim_dc", "dim_product"]
    existing = {(d["schema"], d["table_name"]): d["id"] for d in api.list_all("/dataset") if d["database"]["id"] == db_id}
    ds, cols = {}, {}
    for t in wanted:
        if (SCHEMA, t) in existing:
            ds[t] = existing[(SCHEMA, t)]
            api.put(f"/dataset/{ds[t]}/refresh", {})
        else:
            ds[t] = api.post("/dataset/", {"database": db_id, "schema": SCHEMA, "table_name": t})["id"]
        cols[ds[t]] = {c["column_name"] for c in api.get(f"/dataset/{ds[t]}")["result"]["columns"]}
    print("datasets", ds)

    # 3) wipe old dashboard + its charts
    for d in api.list_all("/dashboard"):
        if d.get("slug") == DASH_SLUG:
            for c in api.get(f"/dashboard/{d['id']}/charts")["result"]:
                api.delete(f"/chart/{c['id']}")
            api.delete(f"/dashboard/{d['id']}")
            print("deleted old dashboard", d["id"])
    dash_id = api.post("/dashboard/", {"dashboard_title": DASH_TITLE, "slug": DASH_SLUG, "published": False})["id"]

    # 4) charts
    W, A, R, C, D = ds["fct_sales_weekly"], ds["mart_sku_abc_xyz"], ds["mart_store_replenishment"], ds["mart_calendar_effects"], ds["fct_sales_daily"]
    H, P, O = ds["mart_hub_supply_plan"], ds["mart_delivery_plan"], ds["mart_delivery_options"]
    tw, td = [temporal("week_start")], [temporal("date_day")]
    specs = {
        # --- 1. Genel Bakış
        "kpi_rev":   kpi(W, "Toplam Ciro", "SUM(revenue)", "Ciro", "$,.3s", "tüm dönem (2 yıl); filtreler uygulanır", tw),
        "kpi_units": kpi(W, "Toplam Adet", "SUM(units)", "Adet", "SMART_NUMBER", "tüm dönem (2 yıl); filtreler uygulanır", tw),
        "kpi_sku":   kpi(W, "Satış Yapan SKU Sayısı", "COUNT(DISTINCT CASE WHEN units > 0 THEN item_id END)", "SKU sayısı", ",d",
                         "katalog: 3.049 SKU", tw),
        "kpi_need":  kpi(H, "Haftalık Sevkiyat İhtiyacı (hub → DC)", "SUM(weekly_qty)", "Haftalık adet", "SMART_NUMBER",
                         "mağaza planlarının toplamı, son 13 tam hafta"),
        "kpi_trucks": kpi(H, "Haftalık Tır Sayısı (hub → DC)", "SUM(trucks_per_week)", "Tır/hafta", ",d", "20.000 adet/tır varsayımı"),
        "line_rev":  line(W, "Dağıtım Merkezine Göre Haftalık Ciro", "week_start", [sql_metric("SUM(revenue)", "Ciro")], ["dc_id"],
                          [simple("is_complete_week", "==", True), *tw]),
        "bar_store": bar(W, "Mağazaya Göre Toplam Ciro", "store_id", [sql_metric("SUM(revenue)", "Ciro")], filters=tw, rotate=45),
        "tree_dept": treemap(W, "Kategori / Departman Payı (adet)", ["cat_id", "dept_id"], sql_metric("SUM(units)", "Adet"), tw),
        "line_cat":  line(W, "Kategoriye Göre Haftalık Satış Adedi", "week_start", [sql_metric("SUM(units)", "Adet")], ["cat_id"],
                          [simple("is_complete_week", "==", True), *tw]),
        # --- 2. Depo Yerleşimi  (depo seviyesi filtresi zorunlu: HUB / CA / TX / WI)
        "kpi_a":     kpi(A, "A Sınıfı SKU Payı", "SUM(CASE WHEN abc_class='A' THEN 1 ELSE 0 END)*1.0/COUNT(*)", "A sınıfı payı", ".1%",
                         "cironun %80'ini üretir · son 52 tam hafta"),
        "kpi_hot":   kpi(A, "HOT Bölgedeki SKU Sayısı", "SUM(CASE WHEN warehouse_zone='HOT' THEN 1 ELSE 0 END)", "HOT SKU sayısı", ",d",
                         "AX + AY · son 52 tam hafta"),
        "kpi_cold":  kpi(A, "COLD Bölge Sıfır Satış Günü Oranı", "AVG(CASE WHEN warehouse_zone='COLD' THEN zero_day_share END)",
                         "Sıfır gün oranı", ".0%", "COLD bölgedeki SKU'ların ortalaması"),
        "heat":      heatmap(A, "ABC × XYZ Matrisi (SKU sayısı)", "abc_class", "xyz_class", sql_metric("COUNT(*)", "SKU sayısı")),
        "bar_zone":  bar(A, "Depo Bölgesine Göre SKU Sayısı", "zone_label", [sql_metric("COUNT(*)", "SKU sayısı")], show_values=True),
        "bar_zone_share": bar(A, "Depo Bölgesine Göre Adet ve Ciro Payı", "zone_label",
                              [sql_metric("SUM(units_52w) * 1.0 / SUM(SUM(units_52w)) OVER ()", "Adet payı"),
                               sql_metric("SUM(revenue_52w) * 1.0 / SUM(SUM(revenue_52w)) OVER ()", "Ciro payı")],
                              y_fmt=".0%", show_values=True),
        "bar_zero":  bar(A, "ABC-XYZ Sınıfına Göre Sıfır Satış Günü Oranı", "abc_xyz", [sql_metric("AVG(zero_day_share)", "Sıfır gün oranı")],
                         y_fmt=".0%", show_values=True, rotate=45),
        "bar_zone_dept": bar(A, "Departman × Depo Bölgesi (SKU sayısı)", "dept_id", [sql_metric("COUNT(*)", "SKU sayısı")], ["zone_label"],
                             stack=True, rotate=30),
        "tbl_sku":   table_raw(A, "Toplama Sırası – SKU Listesi",
                               ["picking_rank", "item_id", "dept_id", "zone_label", "abc_xyz", "cv_weekly", "zero_day_share",
                                "avg_weekly_units", "units_52w", "revenue_52w", "active_weeks"], ("picking_rank", True), 12196),
        # --- 3. Mağaza Sevkiyatı
        "bar_rep":   bar(R, "Önerilen Haftalık Sevkiyat – Mağaza × Kategori (son 13 hafta)", "store_id",
                         [sql_metric("SUM(recommended_weekly_qty)", "Önerilen adet/hafta")], ["cat_id"], stack=True, rotate=45),
        "bar_wd":    bar(D, "Haftanın Gününe Göre SKU Başına Ort. Günlük Talep", "weekday_label",
                         [sql_metric("AVG(sales_qty)", "Ort. adet/SKU/gün")], show_values=True, y_fmt=".2f", rotate=45, filters=td),
        "bar_cal":   bar(C, "Gün Tipine Göre Talep Artışı (taban çizgisi: kuru hafta içi)", "day_type",
                         [sql_metric("SUM(avg_units_per_sku*n_days)/SUM(baseline_units*n_days) - 1", "Artış")], ["cat_id"], y_fmt="+.0%", rotate=45),
        "bar_wx":    bar(C, "Yağışlı ve Kuru Günlerde SKU Başına Günlük Talep", "weather_type",
                         [sql_metric("SUM(avg_units_per_sku*n_days)/SUM(n_days)", "Ort. adet/SKU/gün")], ["cat_id"], y_fmt=".2f"),
        "tbl_rep":   table_raw(R, "Sevkiyat Planı – SKU × Mağaza (son 13 hafta ort. + emniyet stoku)",
                               ["store_id", "item_id", "recommended_weekly_qty", "avg_weekly_units", "std_weekly_units", "safety_stock",
                                "warehouse_zone", "dept_id", "avg_unit_price"], ("recommended_weekly_qty", False), 30490),
        # --- 4. Lojistik Ağı
        "kpi_hubcost": kpi(H, "Hub → DC Haftalık Taşıma Maliyeti", "SUM(transport_cost_week_usd)", "USD/hafta", "$,.3s", "ATRI $/mil + bölgesel dizel"),
        "kpi_storecost": kpi(P, "DC → Mağaza Haftalık Toplam Maliyet", "SUM(total_cost_week_usd)", "USD/hafta", "$,.3s", "taşıma + stok taşıma"),
        "kpi_lead":  kpi(H, "Ortalama Tedarik Süresi (hub → DC)", "AVG(lead_time_days)", "Gün", ".1f", "sürüş süresi + 1 gün elleçleme"),
        "bar_hub":   bar(H, "Hub → DC: Haftalık Tır Sayısı", "dc_id", [sql_metric("SUM(trucks_per_week)", "Tır/hafta")], show_values=True),
        "bar_hubunit": bar(H, "Hub → DC: Adet Başına Taşıma Maliyeti", "dc_id", [sql_metric("AVG(transport_cost_per_unit_usd)", "USD/adet")],
                           y_fmt="$.3f", show_values=True),
        "bar_freq":  bar(P, "Mağaza Başına Optimum Teslimat Sıklığı", "store_id", [sql_metric("MAX(optimal_deliveries_per_week)", "Teslimat/hafta")],
                         show_values=True, rotate=45),
        "bar_opt":   bar(O, "Teslimat Sıklığına Göre Haftalık Maliyet (seçili mağazalar)", "deliveries_per_week",
                         [sql_metric("SUM(transport_cost_week_usd)", "Taşıma"), sql_metric("SUM(holding_cost_week_usd)", "Stok taşıma")],
                         stack=True, y_fmt="$,.3s"),
        "tbl_hub":   table_raw(H, "Hub → DC İkmal Planı", ["dc_city", "n_stores", "weekly_qty", "trucks_per_week", "distance_km", "duration_hours",
                                                           "lead_time_days", "diesel_usd_gal", "round_trip_cost_usd", "transport_cost_week_usd",
                                                           "pipeline_stock_units"], ("weekly_qty", False), 10, 10),
        "tbl_plan":  table_raw(P, "Mağaza Teslimat Planı", ["dc_id", "store_id", "store_city", "schedule_label", "trips_per_week", "weekly_qty",
                                                           "distance_km", "duration_hours", "round_trip_cost_usd", "transport_cost_week_usd",
                                                           "holding_cost_week_usd", "total_cost_week_usd"], ("total_cost_week_usd", False), 20, 10),
    }
    charts = {}
    for key, sp in specs.items():
        params = dict(sp["params"], datasource=f"{sp['ds']}__table")
        res = api.post("/chart/", {"slice_name": sp["slice_name"], "viz_type": sp["viz_type"], "datasource_id": sp["ds"],
                                   "datasource_type": "table", "params": json.dumps(params), "dashboards": [dash_id]})
        charts[key] = {"id": res["id"], "slice_name": sp["slice_name"], "ds": sp["ds"], "dims": sp["dims"]}
    print("charts", {k: v["id"] for k, v in charts.items()})

    # 5) layout
    L = Layout(DASH_TITLE)
    t1 = L.tab("overview", "Genel Bakış")
    L.row(t1, [(charts["kpi_rev"], 2), (charts["kpi_units"], 2), (charts["kpi_sku"], 2), (charts["kpi_need"], 3), (charts["kpi_trucks"], 3)], 22)
    L.row(t1, [(charts["line_rev"], 8), (charts["bar_store"], 4)], 55)
    L.row(t1, [(charts["line_cat"], 7), (charts["tree_dept"], 5)], 55)
    t2 = L.tab("layout", "Depo Yerleşimi")
    L.row(t2, [(charts["kpi_a"], 3), (charts["kpi_hot"], 3), (charts["kpi_cold"], 3), (charts["heat"], 3)], 40)
    L.row(t2, [(charts["bar_zone"], 4), (charts["bar_zone_share"], 4), (charts["bar_zero"], 4)], 50)
    L.row(t2, [(charts["bar_zone_dept"], 5), (charts["tbl_sku"], 7)], 70)
    t3 = L.tab("replenishment", "Mağaza Sevkiyatı")
    L.row(t3, [(charts["bar_rep"], 4), (charts["bar_wd"], 4), (charts["bar_cal"], 4)], 55)
    L.row(t3, [(charts["bar_wx"], 4), (charts["tbl_rep"], 8)], 70)
    t4 = L.tab("logistics", "Lojistik Ağı")
    L.row(t4, [(charts["kpi_hubcost"], 4), (charts["kpi_storecost"], 4), (charts["kpi_lead"], 4)], 22)
    L.row(t4, [(charts["bar_hub"], 3), (charts["bar_hubunit"], 3), (charts["bar_freq"], 3), (charts["bar_opt"], 3)], 50)
    L.row(t4, [(charts["tbl_hub"], 12)], 35)
    L.row(t4, [(charts["tbl_plan"], 12)], 60)

    # 6) native filters — scope = charts whose dataset has the column (and a few semantic exclusions)
    all_ids = [c["id"] for c in charts.values()]
    by_col = lambda col: [c["id"] for c in charts.values() if col in cols[c["ds"]]]
    A_ids = [c["id"] for c in charts.values() if c["ds"] == A]
    time_ids = [c["id"] for k, c in charts.items() if any(f.get("operator") == "TEMPORAL_RANGE" for f in specs[k]["params"]["adhoc_filters"])]
    share_sensitive = [charts[k]["id"] for k in ("kpi_a", "kpi_hot", "kpi_cold", "heat", "bar_zone", "bar_zone_share")]

    def nf(fid, name, col, dataset_id, in_scope, ftype="filter_select", multi=True, required=False, default=None, desc=""):
        f = {"id": fid, "name": name, "filterType": ftype, "type": "NATIVE_FILTER", "description": desc,
             "targets": [{"datasetId": dataset_id, "column": {"name": col}}] if ftype == "filter_select" else [{}],
             "controlValues": {"enableEmptyFilter": required, "defaultToFirstItem": False, "multiSelect": multi,
                               "searchAllOptions": False, "inverseSelection": False},
             "defaultDataMask": {"extraFormData": {}, "filterState": {}, "ownState": {}},
             "cascadeParentIds": [], "scope": {"rootPath": ["ROOT_ID"], "excluded": [i for i in all_ids if i not in in_scope]},
             "chartsInScope": list(in_scope), "tabsInScope": L.tabs}
        if default is not None:
            f["defaultDataMask"] = {"extraFormData": {"filters": [{"col": col, "op": "IN", "val": [default]}]},
                                    "filterState": {"value": [default]}, "ownState": {}}
        return f

    filters = [
        nf("NATIVE_FILTER-level", "Depo Seviyesi (Hub / Bölgesel DC)", "dc_id", A, A_ids, multi=False, required=True, default="HUB",
           desc="ABC/XYZ sınıfı seçilen depo seviyesinin toplam talebiyle hesaplanır."),
        nf("NATIVE_FILTER-dc", "Bölgesel DC", "dc_id", W, [i for i in by_col("dc_id") if i not in A_ids]),
        nf("NATIVE_FILTER-cat", "Kategori", "cat_id", W, by_col("cat_id")),
        nf("NATIVE_FILTER-store", "Mağaza", "store_id", W, by_col("store_id")),
        nf("NATIVE_FILTER-zone", "Depo Bölgesi", "warehouse_zone", A, [i for i in by_col("warehouse_zone") if i not in share_sensitive],
           desc="Pay ve KPI grafikleri bu filtreden etkilenmez (pay %100 olurdu)."),
        nf("NATIVE_FILTER-time", "Tarih Aralığı", None, None, time_ids, ftype="filter_time"),
    ]
    # cross-filters: a chart only emits to charts whose dataset has every column it groups by
    chart_cfg = {}
    for k, c in charts.items():
        scope = [o["id"] for o in charts.values() if o["id"] != c["id"] and c["dims"] and set(c["dims"]) <= cols[o["ds"]]]
        chart_cfg[str(c["id"])] = {"id": c["id"], "crossFilters": {"scope": {"rootPath": ["ROOT_ID"], "excluded": [i for i in all_ids if i not in scope and i != c["id"]]},
                                                                "chartsInScope": scope}}
    json_metadata = {"native_filter_configuration": filters, "color_scheme": "supersetColors", "refresh_frequency": 0,
                     "expanded_slices": {}, "label_colors": {}, "timed_refresh_immune_slices": [], "cross_filters_enabled": True,
                     "default_filters": "{}", "chart_configuration": chart_cfg}
    api.put(f"/dashboard/{dash_id}", {"position_json": json.dumps(L.pos), "json_metadata": json.dumps(json_metadata), "published": True})
    print(f"dashboard ready: {a.base_url}/superset/dashboard/{DASH_SLUG}/")


if __name__ == "__main__":
    main()
