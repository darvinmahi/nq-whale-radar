#!/usr/bin/env python3
"""
FETCH DIX — Dark Pool Index proxy via yfinance
===============================================
DIX = Dark Pool Index (% del volumen en dark pools)

Fuentes:
  1. GitHub CSV histórico (si disponible)
  2. Proxy via yfinance QQQ (estimación correlacionada)

Actualiza daily_master_db.json con DIX estimado
"""

import sys, os, json, requests
import yfinance as yf
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "data", "research", "daily_master_db.json")
HEADERS  = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

DIX_GITHUB_URLS = [
    "https://raw.githubusercontent.com/ercumentlacin/dix-gex-data/main/data.csv",
    "https://raw.githubusercontent.com/spmallick/learnopencv/master/StockMarket/dix.csv",
]

def fetch_dix_github():
    for url in DIX_GITHUB_URLS:
        try:
            print(f"  Intentando: {url}")
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200 and len(r.text) > 200:
                header = r.text.split("\n")[0].lower()
                if "dix" in header or "dark" in header:
                    print(f"  OK ({len(r.text)} bytes)")
                    return r.text
        except Exception as e:
            print(f"  fail: {e}")
    return None

def parse_github_csv(csv_text):
    dix_map = {}
    lines = csv_text.strip().split("\n")
    header = [h.strip().lower() for h in lines[0].split(",")]
    try:
        date_col = next(i for i,h in enumerate(header) if "date" in h)
        dix_col  = next(i for i,h in enumerate(header) if "dix" in h)
    except StopIteration:
        return {}
    for line in lines[1:]:
        parts = line.strip().split(",")
        if len(parts) <= max(date_col, dix_col):
            continue
        try:
            d = parts[date_col].strip().strip('"')
            v = float(parts[dix_col].strip().strip('"').replace("%",""))
            for fmt in ("%Y-%m-%d","%m/%d/%Y","%d/%m/%Y"):
                try:
                    d = datetime.strptime(d, fmt).strftime("%Y-%m-%d")
                    break
                except: pass
            if v <= 1.0:
                v *= 100
            dix_map[d] = round(v, 2)
        except: pass
    return dix_map

def calc_dix_proxy():
    """Calcula DIX proxy via comportamiento de volumen QQQ."""
    print("  Calculando DIX proxy via QQQ yfinance...")
    dix_map = {}
    try:
        qqq = yf.download("QQQ", start="2024-01-01", progress=False, auto_adjust=True)
        if qqq.empty:
            return {}
        roll_vol = qqq["Volume"].rolling(30).mean()
        for idx in qqq.index:
            try:
                date_str = idx.strftime("%Y-%m-%d")
                def val(col):
                    v = qqq.loc[idx, col]
                    return float(v.iloc[0]) if hasattr(v, "iloc") else float(v)
                close   = val("Close")
                open_p  = val("Open")
                volume  = val("Volume")
                rv_val  = roll_vol.loc[idx]
                vol_avg = float(rv_val.iloc[0]) if hasattr(rv_val, "iloc") else float(rv_val)
                vol_avg = vol_avg if vol_avg > 0 else volume
                day_ret = (close - open_p) / open_p
                vol_rel = volume / vol_avg
                # Heurística: días bajistas + vol alto → DIX sube (acumulación inst.)
                if day_ret < -0.005 and vol_rel > 1.1:
                    dix_est = 46.5 + abs(day_ret) * 200
                elif day_ret > 0.005 and vol_rel < 0.9:
                    dix_est = 40.0 - day_ret * 150
                else:
                    dix_est = 43.5 + (day_ret * -80)
                dix_map[date_str] = round(max(32.0, min(58.0, dix_est)), 2)
            except: pass
        print(f"  OK: {len(dix_map)} días calculados")
    except Exception as e:
        print(f"  ERROR: {e}")
    return dix_map

def update_db(dix_map, source):
    with open(DB_PATH, "r", encoding="utf-8") as f:
        db = json.load(f)
    # Handle both list and dict structure
    records = db if isinstance(db, list) else db.get("records", [])
    n = 0
    for entry in records:
        if not isinstance(entry, dict):
            continue
        d = entry.get("date","")
        if d in dix_map:
            entry["dix"]        = dix_map[d]
            entry["dix_source"] = source
            n += 1
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    return n

def main():
    print("=" * 55)
    print("  FETCH DIX — Dark Pool Index")
    print("=" * 55)

    if not os.path.exists(DB_PATH):
        print(f"ERROR: no existe {DB_PATH}")
        sys.exit(1)

    csv_text = fetch_dix_github()
    if csv_text:
        dix_map = parse_github_csv(csv_text)
        if dix_map:
            n = update_db(dix_map, "github_real")
            print(f"\nDIX REAL: {n} dias actualizados")
            return

    dix_map = calc_dix_proxy()
    if dix_map:
        n = update_db(dix_map, "yfinance_proxy")
        vmin = min(dix_map.values())
        vmax = max(dix_map.values())
        print(f"\nDIX PROXY: {n} dias | rango {vmin:.1f}% - {vmax:.1f}%")
    else:
        print("FALLO: sin datos DIX")

if __name__ == "__main__":
    main()
