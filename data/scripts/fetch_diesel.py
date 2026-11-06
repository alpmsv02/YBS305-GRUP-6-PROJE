"""Dış veri kaynağı 3: haftalık dizel fiyatları (EIA verisi, FRED CSV üzerinden; anahtar gerekmez).
Bölge eşlemesi: CA → Kaliforniya (GASDESCAW, yoksa ABD ortalaması), TX → PADD 3 Gulf Coast (GASDESGCW),
WI → PADD 2 Midwest (GASDESMWW), HUB (AR) → ABD ortalaması (GASDESW).
Çıktı: data/external/diesel_prices.csv  (region, week_date, price_usd_gal)
"""
import csv, io, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "external" / "diesel_prices.csv"
SERIES = {"US": ["GASDESW"], "CA": ["GASDESCAW", "GASDESW"], "TX": ["GASDESGCW"], "WI": ["GASDESMWW"]}
START, END = "2014-01-01", "2016-12-31"

def fetch(sid):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={START}&coed={END}"
    with urllib.request.urlopen(url, timeout=60) as r:
        txt = r.read().decode()
    rows = list(csv.DictReader(io.StringIO(txt)))
    val_key = [k for k in rows[0].keys() if k != "observation_date" and k != "DATE"][0]
    date_key = "observation_date" if "observation_date" in rows[0] else "DATE"
    return [(r[date_key], float(r[val_key])) for r in rows if r[val_key] not in (".", "")]

out = []
for region, ids in SERIES.items():
    for sid in ids:
        try:
            data = fetch(sid)
            out += [dict(region=region, series_id=sid, week_date=d, price_usd_gal=v) for d, v in data]
            print(region, sid, len(data), "weeks", file=sys.stderr); break
        except Exception as e:
            print(region, sid, "failed:", e, file=sys.stderr)
with OUT.open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["region", "series_id", "week_date", "price_usd_gal"]); w.writeheader(); w.writerows(out)
print("wrote", OUT, len(out), "rows")
