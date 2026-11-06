"""Her chart için query_context oluşturur, /api/v1/chart/data ile çalıştırır ve chart'a kaydeder.
Ayrıca zaman filtresi olan grafiklerde 'Tarih Aralığı' filtresinin SQL'e gerçekten yansıdığını doğrular.
Kullanım: ../.venv/bin/python verify_charts.py
"""
import json, pathlib, sys, time
import requests

HERE = pathlib.Path(__file__).resolve().parent
BASE = "http://127.0.0.1:8088"
TEST_RANGE = "2015-01-01 : 2015-02-01"


def login():
    env = dict(l.split("=", 1) for l in (HERE / ".env").read_text().split() if "=" in l)
    s = requests.Session()
    tok = s.post(f"{BASE}/api/v1/security/login", json={"username": env["ADMIN_USERNAME"], "password": env["ADMIN_PASSWORD"],
                                                        "provider": "db"}).json()["access_token"]
    s.headers["Authorization"] = f"Bearer {tok}"
    s.headers["X-CSRFToken"] = s.get(f"{BASE}/api/v1/security/csrf_token/").json()["result"]
    s.headers["Referer"] = BASE
    return s


def axis(col, grain=None):
    c = {"columnType": "BASE_AXIS", "sqlExpression": col, "label": col, "expressionType": "SQL"}
    if grain:
        c["timeGrain"] = grain
    return c


def build_query_context(ds_id, p, time_range="No filter"):
    v = p["viz_type"]
    flt = []
    for f in p.get("adhoc_filters", []):
        if f.get("expressionType") != "SIMPLE":
            continue
        if f["operator"] == "TEMPORAL_RANGE":
            flt.append({"col": f["subject"], "op": "TEMPORAL_RANGE", "val": time_range})
        else:
            flt.append({"col": f["subject"], "op": f["operator"], "val": f["comparator"]})
    q = {"filters": flt, "extras": {"having": "", "where": ""}, "applied_time_extras": {}, "annotation_layers": [],
         "row_limit": p.get("row_limit", 10000), "series_limit": 0, "order_desc": True, "url_params": {}, "custom_params": {},
         "custom_form_data": {}, "time_range": time_range}
    if v == "big_number_total":
        q.update(columns=[], metrics=[p["metric"]])
    elif v in ("echarts_timeseries_line", "echarts_timeseries_bar"):
        grain = p.get("time_grain_sqla")
        q.update(columns=[axis(p["x_axis"], grain)] + p.get("groupby", []), metrics=p["metrics"], series_columns=p.get("groupby", []))
        if grain:
            q["extras"]["time_grain_sqla"] = grain
        if p.get("x_axis_sort"):
            q["orderby"] = [[p["metrics"][0], False]]
    elif v == "heatmap_v2":
        q.update(columns=[p["x_axis"], p["groupby"]], metrics=[p["metric"]])
    elif v == "treemap_v2":
        q.update(columns=p["groupby"], metrics=[p["metric"]])
    elif v == "table":
        ob = [json.loads(o) for o in p.get("order_by_cols", [])]
        q.update(columns=p["all_columns"], metrics=None, orderby=[[c, asc] for c, asc in ob])
        q["row_limit"] = p.get("row_limit", 100)
    else:
        raise ValueError(v)
    return {"datasource": {"id": ds_id, "type": "table"}, "force": False, "queries": [q], "form_data": p,
            "result_format": "json", "result_type": "full"}


def main():
    s = login()
    charts = s.get(f"{BASE}/api/v1/chart/?q={json.dumps({'page_size': 100})}").json()["result"]
    bad = 0
    for c in sorted(charts, key=lambda c: c["id"]):
        p = json.loads(c["params"])
        ds_id = int(p["datasource"].split("__")[0])
        qc = build_query_context(ds_id, p)
        t = time.time()
        r = s.post(f"{BASE}/api/v1/chart/data", json=qc)
        ok = r.status_code == 200 and not r.json()["result"][0].get("error")
        if not ok:
            bad += 1
            msg = (r.json().get("message") or r.json()["result"][0].get("error")) if r.text.startswith("{") else r.text
            print(f"{c['id']:2} ERR {c['slice_name']} :: {str(msg)[:400]}")
            continue
        res = r.json()["result"][0]
        note = ""
        temporal_cols = [f["subject"] for f in p.get("adhoc_filters", []) if f.get("operator") == "TEMPORAL_RANGE"]
        if temporal_cols:  # zaman filtresi SQL'e yansıyor mu?
            qc2 = build_query_context(ds_id, p, TEST_RANGE); qc2["result_type"] = "query"
            sql = s.post(f"{BASE}/api/v1/chart/data", json=qc2).json()["result"][0]["query"]
            applied = all(col in sql and ">=" in sql for col in temporal_cols)
            note = "  [time filter OK]" if applied else "  [TIME FILTER NOT APPLIED!]"
            if not applied:
                bad += 1
        print(f"{c['id']:2} OK  {time.time()-t:5.1f}s rows={res['rowcount']:<6} {c['slice_name']}{note}")
        s.put(f"{BASE}/api/v1/chart/{c['id']}", {"query_context": json.dumps(qc)})
    print("errors:", bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
