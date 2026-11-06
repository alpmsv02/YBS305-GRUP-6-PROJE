"""Dış veri kaynağı 2: OSRM (OpenStreetMap) yol mesafesi ve sürüş süresi matrisi.
Noktalar: merkez hub + 3 bölgesel DC (dbt/seeds/dc_locations.csv) + 10 mağaza (dbt/seeds/store_locations.csv).
Tek bir /table isteği ile tüm çiftler alınır. OSRM demo sunucusu: anahtar gerektirmez, ≤1 istek/sn, ODbL atıf.
Yedek: OSRM erişilemezse Haversine × 1.25 dolambaç katsayısı ve 55 mph (işaretlenir: method='haversine').
Çıktı: data/external/routes.csv
"""
import csv, json, math, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "external" / "routes.csv"
dcs = list(csv.DictReader((ROOT / "dbt/seeds/dc_locations.csv").open()))
stores = list(csv.DictReader((ROOT / "dbt/seeds/store_locations.csv").open()))
points = [(d["dc_id"], "DC", float(d["latitude"]), float(d["longitude"])) for d in dcs] + \
         [(s["store_id"], "STORE", float(s["latitude"]), float(s["longitude"])) for s in stores]

def haversine_km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[2]), math.radians(b[2]); dp = p2 - p1; dl = math.radians(b[3] - a[3])
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*R*math.asin(math.sqrt(h))

method, dist, dur = "osrm", None, None
try:
    coords = ";".join(f"{lon},{lat}" for _, _, lat, lon in points)
    url = f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration,distance"
    req = urllib.request.Request(url, headers={"User-Agent": "ybs305-dc-planning/1.0 (student project)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        res = json.load(r)
    if res.get("code") != "Ok":
        raise RuntimeError(res)
    dist, dur = res["distances"], res["durations"]
except Exception as e:
    print("OSRM failed, falling back to haversine:", e, file=sys.stderr)
    method = "haversine"

rows = []
for i, o in enumerate(points):
    for j, d in enumerate(points):
        if i == j:
            continue
        if method == "osrm" and dist[i][j] is not None:
            km, mins = dist[i][j] / 1000.0, dur[i][j] / 60.0
        else:
            km = haversine_km(o, d) * 1.25; mins = km / (55 * 1.609) * 60
        rows.append(dict(origin_id=o[0], origin_type=o[1], dest_id=d[0], dest_type=d[1],
                         distance_km=round(km, 1), duration_min=round(mins, 1), method=method))
OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("wrote", OUT, len(rows), "rows, method =", method)
