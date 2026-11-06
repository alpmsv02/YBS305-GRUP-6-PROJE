"""Dış veri kaynağı: Open-Meteo Historical Weather API (ücretsiz, anahtar gerektirmez).
M5 veri setinde mağaza şehirleri anonimdir; her mağaza için eyaletin büyük bir şehri varsayılmıştır (dbt/seeds/store_locations.csv).
Çıktı: data/external/weather_ca.csv
"""
import csv, json, urllib.request, urllib.parse, pathlib, sys

import csv as _csv
_SEED = pathlib.Path(__file__).resolve().parents[2] / "dbt" / "seeds" / "store_locations.csv"
STORES = {r["store_id"]: (r["city"], float(r["latitude"]), float(r["longitude"]))
          for r in _csv.DictReader(_SEED.open())}  # VARSAYIM: şehirler dbt/seeds/store_locations.csv
START, END = "2014-05-01", "2016-06-19"
OUT = pathlib.Path(__file__).resolve().parents[1] / "external" / "weather.csv"

rows = []
for store, (city, lat, lon) in STORES.items():
    params = dict(latitude=lat, longitude=lon, start_date=START, end_date=END,
                  daily="temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum",
                  timezone="auto")
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=60) as r:
        d = json.load(r)["daily"]
    for i, day in enumerate(d["time"]):
        rows.append(dict(store_id=store, city=city, date=day,
                         temp_max=d["temperature_2m_max"][i], temp_min=d["temperature_2m_min"][i],
                         temp_mean=d["temperature_2m_mean"][i], precipitation_mm=d["precipitation_sum"][i]))
    print(store, city, len(d["time"]), "days", file=sys.stderr)

OUT.parent.mkdir(parents=True, exist_ok=True)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print("wrote", OUT, len(rows), "rows")
