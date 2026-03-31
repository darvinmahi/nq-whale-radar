"""
download_nq_15m_2yrs.py
Descarga NQ=F en 15m desde 2024-01-01 hasta hoy.
Yahoo Finance limita intraday a ~60 dias por request → usamos chunks.
Guarda en data/research/nq_15m_2024_2026.csv
"""
import requests, csv, time, os
from datetime import datetime, timedelta

OUTPUT = "data/research/nq_15m_2024_2026.csv"
TICKER = "NQ=F"
os.makedirs("data/research", exist_ok=True)

def dl_chunk(t1, t2):
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/{}"
        "?period1={}&period2={}&interval=15m&events=history"
    ).format(TICKER, t1, t2)
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        js   = resp.json()
        res  = js.get("chart", {}).get("result")
        if not res:
            print("  Sin datos")
            return []
        data  = res[0]
        ts    = data["timestamp"]
        quote = data["indicators"]["quote"][0]
        rows  = []
        for i, t in enumerate(ts):
            o = quote["open"][i]
            h = quote["high"][i]
            l = quote["low"][i]
            c = quote["close"][i]
            v = quote["volume"][i]
            if c is None: continue
            dt = datetime.utcfromtimestamp(t)
            rows.append({"dt": dt, "open": o, "high": h, "low": l, "close": c, "vol": v or 0})
        return rows
    except Exception as e:
        print("  ERROR: {}".format(e))
        return []

# Yahoo limita 15m a ~60 dias → chunks de 55 dias
start = datetime(2024, 1, 1)
end   = datetime(2026, 3, 27)
CHUNK = timedelta(days=55)
all_bars = {}

cur = start
while cur < end:
    nxt = min(cur + CHUNK, end)
    t1  = int(cur.timestamp())
    t2  = int(nxt.timestamp())
    print("Descargando {} → {} ...".format(cur.date(), nxt.date()), end=" ")
    bars = dl_chunk(t1, t2)
    for b in bars:
        key = b["dt"].strftime("%Y-%m-%d %H:%M")
        all_bars[key] = b
    print("{} barras".format(len(bars)))
    time.sleep(1.2)
    cur = nxt

sorted_bars = sorted(all_bars.values(), key=lambda x: x["dt"])
mondays = set(b["dt"].date() for b in sorted_bars if b["dt"].weekday() == 0)
print("\nTotal barras únicas: {}".format(len(sorted_bars)))
print("Rango: {} → {}".format(sorted_bars[0]["dt"], sorted_bars[-1]["dt"]))
print("Lunes con datos: {}".format(len(mondays)))

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["datetime", "open", "high", "low", "close", "volume"])
    for b in sorted_bars:
        w.writerow([
            b["dt"].strftime("%Y-%m-%d %H:%M"),
            round(b["open"]  or 0, 2),
            round(b["high"]  or 0, 2),
            round(b["low"]   or 0, 2),
            round(b["close"] or 0, 2),
            int(b["vol"]     or 0),
        ])

print("✅ Guardado en: {}".format(OUTPUT))
