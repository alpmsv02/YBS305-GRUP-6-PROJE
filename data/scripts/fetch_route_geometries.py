"""Dış veri kaynağı 2b: OSRM /route ile her lojistik bacağının (HUB→DC, DC→mağaza) gerçek yol geometrisi.
Harita çizimi içindir; mesafe/süre hesapları fetch_routes.py (OSRM /table) ile yapılır.
Çıktı: data/external/route_geometries.geojson   (OSRM demo: ≤1 istek/sn, ODbL atıf)
"""
import csv, json, pathlib, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "external" / "route_geometries.geojson"
dcs = {d["dc_id"]: d for d in csv.DictReader((ROOT / "dbt/seeds/dc_locations.csv").open())}
stores = list(csv.DictReader((ROOT / "dbt/seeds/store_locations.csv").open()))
legs = [("HUB", d, "HUB_TO_DC") for d in dcs if d != "HUB"] + [(s["state_id"], s["store_id"], "DC_TO_STORE") for s in stores]
pos = {k: (float(v["latitude"]), float(v["longitude"])) for k, v in dcs.items()}
pos.update({s["store_id"]: (float(s["latitude"]), float(s["longitude"])) for s in stores})

features = []
for o, d, leg in legs:
    (la1, lo1), (la2, lo2) = pos[o], pos[d]
    url = f"https://router.project-osrm.org/route/v1/driving/{lo1},{la1};{lo2},{la2}?overview=full&geometries=geojson"
    req = urllib.request.Request(url, headers={"User-Agent": "ybs305-dc-planning/1.0 (student project)"})
    try:
        res = None
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    res = json.load(r)
                break
            except Exception as e:
                print(o, "->", d, "attempt", attempt + 1, "failed:", e, file=sys.stderr); time.sleep(3)
        if res is None:
            raise RuntimeError("OSRM unreachable after retries")
        rt = res["routes"][0]
        features.append({"type": "Feature", "geometry": rt["geometry"],
                         "properties": {"origin_id": o, "dest_id": d, "leg_type": leg, "distance_km": round(rt["distance"] / 1000, 1),
                                        "duration_min": round(rt["duration"] / 60, 1), "method": "osrm"}})
        print(o, "->", d, round(rt["distance"] / 1000), "km", len(rt["geometry"]["coordinates"]), "pts", file=sys.stderr)
    except Exception as e:  # yedek: düz çizgi
        print(o, "->", d, "OSRM failed, straight line:", e, file=sys.stderr)
        features.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[lo1, la1], [lo2, la2]]},
                         "properties": {"origin_id": o, "dest_id": d, "leg_type": leg, "method": "straight"}})
    time.sleep(1.1)
OUT.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
print("wrote", OUT, len(features), "legs")
