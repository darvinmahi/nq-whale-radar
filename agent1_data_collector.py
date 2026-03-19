"""
AGENTE 1 — DATA COLLECTOR
Responsabilidad: Fetching en tiempo real de todas las fuentes de datos.
  - Yahoo Finance → NDX, VXN, NQ Futures
  - Squeezemetrics → DIX, GEX
  - CFTC → COT semanal (Non-Commercial Net Position para Nasdaq 100)
  - CME → Open Interest NQ1! (via Yahoo Finance NQ=F)

Salida: agent1_data.json
"""

import yfinance as yf
import requests
import pandas as pd
import io
import datetime
import json
import os

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# ─── 1. YAHOO FINANCE ──────────────────────────────────────────────────────────
def fetch_yahoo():
    print("[Agent 1] 📡 Yahoo Finance — NDX, VXN, NQ=F...")
    result = {}
    tickers = {"NDX": "^NDX", "VXN": "^VXN", "NQ_futures": "NQ=F"}
    for name, symbol in tickers.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if hist.empty:
                result[name] = None
                continue
            close_today = float(hist["Close"].iloc[-1])
            close_prev  = float(hist["Close"].iloc[-2]) if len(hist) > 1 else close_today
            chg_pct = round(((close_today - close_prev) / close_prev) * 100, 2)
            result[name] = {
                "price": round(close_today, 2),
                "prev_close": round(close_prev, 2),
                "change_pct": chg_pct
            }
            print(f"  ✅ {name}: {close_today:.2f}  ({chg_pct:+.2f}%)")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            result[name] = None
    return result


# ─── 2. SQUEEZEMETRICS (DIX + GEX) ────────────────────────────────────────────
def fetch_squeezemetrics():
    print("[Agent 1] 📡 Squeezemetrics — DIX, GEX...")
    url = "https://squeezemetrics.com/monitor/static/DIX.csv"
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        # Normalize column names (lowercase)
        df.columns = [c.lower().strip() for c in df.columns]
        row = df.iloc[-1]
        dix = float(row["dix"])
        gex = float(row["gex"])
        date = str(row["date"])
        # DIX expressed as percentage
        dix_pct = round(dix * 100, 2) if dix < 1 else round(dix, 2)
        gex_b   = round(gex / 1e9, 3)  # Convert to Billions
        print(f"  ✅ DIX: {dix_pct}%  |  GEX: {gex_b}B  |  Date: {date}")
        return {"DIX": dix_pct, "GEX_raw": gex, "GEX_B": gex_b, "date": date}
    except Exception as e:
        print(f"  ❌ Squeezemetrics: {e}")
        return {"DIX": None, "GEX_raw": None, "GEX_B": None, "date": None}


# ─── 3. CFTC COT REPORT (Semanal) ─────────────────────────────────────────────
def fetch_cftc_cot():
    print("[Agent 1] 📡 CFTC COT — Nasdaq 100 Consolidated...")
    # Source: Financial Futures Weekly (Futures Only)
    url = "https://www.cftc.gov/dea/newcot/FinFutWk.txt"
    try:
        r = SESSION.get(url, timeout=20)
        r.raise_for_status()
        lines = r.text.splitlines()
        target = None
        
        # Search for Nasdaq-100 Consolidated or Mini
        for line in lines:
            if "NASDAQ-100 CONSOLIDATED" in line.upper():
                target = line
                break
        
        if not target:
            for line in lines:
                if "NASDAQ-100 STOCK INDEX" in line.upper():
                    target = line
                    break

        if target is None:
            print("  ⚠️  No se encontró línea de NASDAQ en el reporte COT.")
            return {
                "cot_nc_long": None, "cot_nc_short": None,
                "cot_net": None, "cot_oi": None, "cot_date": None
            }

        # Format: "NAME", YYMMDD, YYYY-MM-DD, ID, EXCHANGE...
        parts = [p.strip().replace('"', '') for p in target.split(",")]
        
        try:
            cot_date = parts[2]
            cot_oi = int(parts[7])
            # For Financial Futures report, NC (Non-Com) are usually Asset Managers
            # Long: Index 10, Short: Index 11 (based on typical FinFutWk structure)
            am_long = int(parts[10])
            am_short = int(parts[11])
            cot_net = am_long - am_short
        except (ValueError, IndexError) as e:
            print(f"  ⚠️  Error parseando FinFutWk: {e}")
            return {"cot_net": None, "cot_date": "unknown"}

        print(f"  ✅ COT Net: {cot_net:+,}  |  OI: {cot_oi:,}  |  Date: {cot_date}")
        return {
            "cot_nc_long": am_long,
            "cot_nc_short": am_short,
            "cot_net": cot_net,
            "cot_oi": cot_oi,
            "cot_date": cot_date
        }
    except Exception as e:
        print(f"  ❌ CFTC COT: {e}")
        return {
            "cot_nc_long": None, "cot_nc_short": None,
            "cot_net": None, "cot_oi": None, "cot_date": None
        }


# ─── 4. CME & PUT/CALL — NQ1! ─────────────────────────────────────────────────
def fetch_market_sentiment():
    print("[Agent 1] 📡 Sentiment — Put/Call Ratio & NQ Futures...")
    result = {"NQ1_OI": None, "NQ1_volume": None, "pcr": None}
    try:
        pc = yf.Ticker("^PCCR")
        pc_hist = pc.history(period="1d")
        if not pc_hist.empty:
            result["pcr"] = round(float(pc_hist["Close"].iloc[-1]), 2)
            print(f"  ✅ PCR: {result['pcr']}")
        else:
            result["pcr"] = 0.65 
            print(f"  ℹ️ PCR: 0.65 (Fallback)")

        nq = yf.Ticker("NQ=F")
        info = nq.info
        result["NQ1_OI"] = info.get("openInterest")
        result["NQ1_volume"] = info.get("volume")
        print(f"  ✅ NQ OI: {result['NQ1_OI']} | Vol: {result['NQ1_volume']}")
        
    except Exception as e:
        print(f"  ❌ Sentiment Data: {e}")
    return result


# ─── RUNNER ────────────────────────────────────────────────────────────────────
def run():
    print("\n" + "="*60)
    print("  AGENTE 1 · DATA COLLECTOR · INICIO")
    print("="*60 + "\n")

    output = {
        "agent": 1,
        "name": "Data Collector",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "yahoo": fetch_yahoo(),
        "squeezemetrics": fetch_squeezemetrics(),
        "cftc_cot": fetch_cftc_cot(),
        "sentiment": fetch_market_sentiment()
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent1_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Agent 1 completado → {out_path}")
    return output


if __name__ == "__main__":
    run()
