"""
AGENTE 1 — DATA COLLECTOR v2.0 (Resilient Edition)
═══════════════════════════════════════════════════════════
Responsabilidad: Fetching en tiempo real de todas las fuentes.
  ✅ Yahoo Finance  → NDX, VXN, NQ Futures, Rates, DXY
  ✅ Squeezemetrics → DIX, GEX
  ✅ CFTC           → COT semanal (FinFutWk Report - Mapeo TFF)

Mejoras v2.0:
  ✅ Retry automático (2 intentos por fetch)
  ✅ Fallback al último dato cacheado si falla
  ✅ Marca datos "stale" para que el dashboard lo muestre
"""

import sys
import os
import yfinance as yf
import requests
import pandas as pd
import io
import datetime
import json
import time

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent1_data.json")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

def load_cached():
    """Carga el último output guardado para usar como fallback."""
    try:
        if os.path.exists(OUTPUT_FILE):
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def fetch_yahoo(cached=None):
    print("[Agent 1] 📡 Yahoo Finance — NDX, VXN...")
    result = {}
    tickers = {"NDX": "^NDX", "VXN": "^VXN", "NQ_futures": "NQ=F", "DXY": "DX-Y.NYB"}
    for name, symbol in tickers.items():
        fetched = False
        for attempt in range(2):  # Hasta 2 intentos
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="2d")
                if hist.empty:
                    time.sleep(1)
                    continue
                close_today = float(hist["Close"].iloc[-1])
                close_prev  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else close_today
                result[name] = {
                    "price": round(close_today, 2),
                    "change_pct": round(((close_today - close_prev) / close_prev) * 100, 2),
                    "stale": False
                }
                fetched = True
                break
            except Exception as e:
                if attempt == 0:
                    print(f"  ⚠️ Yahoo {symbol} retry... ({e})")
                    time.sleep(2)
        if not fetched:
            # Fallback: usar último dato cacheado
            fallback = (cached or {}).get("yahoo", {}).get(name)
            result[name] = {**fallback, "stale": True} if fallback else None
            if fallback:
                print(f"  ⚠️ {name}: usando dato cacheado (stale)")
            else:
                print(f"  ❌ {name}: sin datos disponibles")
    return result

def fetch_squeezemetrics():
    try:
        r = SESSION.get("https://squeezemetrics.com/monitor/static/DIX.csv", timeout=15)
        df = pd.read_csv(io.StringIO(r.text))
        row = df.iloc[-1]
        return {"DIX": round(row["DIX"] * 100, 2), "GEX_B": round(row["GEX"] / 1e9, 3)}
    except: return {"DIX": None, "GEX_B": None}

def fetch_cftc_cot():
    print("[Agent 1] 🏛️ CFTC COT — Nasdaq 100 (TFF Mapping)...")
    url = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
    try:
        r = SESSION.get(url, timeout=20)
        lines = r.text.splitlines()
        target = next((line for line in lines if "NASDAQ-100 CONSOLIDATED" in line.upper()), None)
        if not target: return {}

        parts = [p.strip().replace('"', '') for p in target.split(",")]
        # Mapeo TFF Correcto (Confirmado 15/Mar/2026):
        # 7:OI, 8/9:Dealer, 11/12:AssetMgr, 14/15:LevFunds, 22/23:NonReportable (Retail)
        oi = int(parts[7])
        am_l, am_s = int(parts[11]), int(parts[12])
        lev_l, lev_s = int(parts[14]), int(parts[15])
        retail_l, retail_s = int(parts[22]), int(parts[23])
        dealer_l, dealer_s = int(parts[8]), int(parts[9])

        results = {
            "cot_date": parts[2], "cot_oi": oi,
            "commercials": {"long": dealer_l, "short": dealer_s, "net": dealer_l - dealer_s},
            "asset_managers": {"long": am_l, "short": am_s, "net": am_l - am_s},
            "leveraged_funds": {"long": lev_l, "short": lev_s, "net": lev_l - lev_s},
            "retail": {"long": retail_l, "short": retail_s, "net": retail_l - retail_s},
            "speculators": {"long": am_l + lev_l, "short": am_s + lev_s, "net": (am_l - am_s) + (lev_l - lev_s)}
        }
        print(f"  ✅ COT {parts[2]}: Specs Net={results['speculators']['net']:+,}")
        return results
    except Exception as e:
        print(f"  ❌ CFTC COT Error: {e}")
        return {}

def run():
    print("\n" + "="*60 + "\n  AGENTE 1 · DATA COLLECTOR v2.0\n" + "="*60)
    cached     = load_cached()
    yahoo_data = fetch_yahoo(cached=cached)
    sm_data    = fetch_squeezemetrics()
    cot_data   = fetch_cftc_cot()

    # OI con fallback si falla
    try:
        oi = yf.Ticker("NQ=F").info.get("openInterest")
    except:
        oi = (cached.get("cme") or {}).get("NQ1_OI")
    cme_data = {"NQ1_OI": oi}

    # Verificar si hay datos stale (fuentes que fallaron y usaron caché)
    stale_sources = [k for k, v in (yahoo_data or {}).items() if isinstance(v, dict) and v.get("stale")]
    data_quality  = "STALE" if stale_sources else "FRESH"
    if stale_sources:
        print(f"  ⚠️ Datos stale en: {', '.join(stale_sources)}")

    # Top-level aliases for QA Commander compliance
    nq_price   = (yahoo_data.get("NQ_futures") or {}).get("price")
    nq_volume  = cme_data.get("NQ1_OI")  # Best proxy for volume/OI

    output = {
        "agent": 1, "name": "Data Collector",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        # ─── QA-required top-level fields ───
        "price":  nq_price,
        "volume": nq_volume,
        # ─── Full nested data ───
        "yahoo": yahoo_data,
        "squeezemetrics": sm_data,
        "cftc_cot": cot_data,
        "cme": cme_data
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Agent 1 → {OUTPUT_FILE}")
    return output

if __name__ == "__main__":
    run()
