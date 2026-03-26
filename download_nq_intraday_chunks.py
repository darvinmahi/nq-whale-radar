"""
download_nq_intraday_chunks.py
Descarga datos 1h de NQ=F en chunks de 55 dias para cubrir 2023-2026.
Yahoo Finance limita intraday a ~60 dias por peticion.
Guarda en data/research/nq_1h_2023_2026.csv
"""
import requests, csv, time
from datetime import datetime, timedelta

OUTPUT = "data/research/nq_1h_2023_2026.csv"
TICKER = "NQ=F"

def dl_chunk(t1, t2):
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/{}"
        "?period1={}&period2={}&interval=1h&events=history"
    ).format(TICKER, t1, t2)
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        js   = resp.json()
        res  = js.get("chart", {}).get("result")
        if not res:
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
            if c is None:
                continue
            dt = datetime.utcfromtimestamp(t)
            rows.append({"dt": dt, "open": o, "high": h, "low": l, "close": c, "vol": v})
        return rows
    except Exception as e:
        print("  ERROR en chunk: {}".format(e))
        return []

# Genera chunks de 55 dias desde 2022-01-01 hasta hoy
start = datetime(2022, 1, 1)
end   = datetime(2026, 3, 24)
CHUNK = timedelta(days=55)
all_bars = {}

cur = start
while cur < end:
    nxt = min(cur + CHUNK, end)
    t1  = int(cur.timestamp())
    t2  = int(nxt.timestamp())
    print("Descargando: {} -> {}".format(cur.date(), nxt.date()), end=" ... ")
    bars = dl_chunk(t1, t2)
    for b in bars:
        key = b["dt"].strftime("%Y-%m-%d %H:%M")
        all_bars[key] = b
    print("{} barras".format(len(bars)))
    time.sleep(0.8)  # evitar rate limit
    cur = nxt

# Ordena y guarda
sorted_bars = sorted(all_bars.values(), key=lambda x: x["dt"])
print("\nTotal barras unicas: {}".format(len(sorted_bars)))
print("Rango: {} -> {}".format(sorted_bars[0]["dt"], sorted_bars[-1]["dt"]))

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

print("Guardado en: {}".format(OUTPUT))
