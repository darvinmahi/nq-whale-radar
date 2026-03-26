#!/usr/bin/env python3
"""
Descarga datos REALES de NQ Futures (5min) para 2026-03-19
y genera el JSON de candles para el chart HTML.
"""

import json
import sys
from datetime import datetime, timezone

try:
    import yfinance as yf
except ImportError:
    print("Instalando yfinance...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
    import yfinance as yf

# ──────────────────────────────────────
# Intentar varios tickers de NQ futures
# ──────────────────────────────────────
TICKERS_TO_TRY = [
    "NQ=F",   # NQ continuo
    "MNQ=F",  # Micro NQ
    "QQQ",    # ETF proxy (si futuros fallan)
]

TARGET_DATE = "2026-03-19"
PREV_DATE   = "2026-03-18"   # Asia empieza día anterior

candles = []
used_ticker = None
raw_df = None

for ticker in TICKERS_TO_TRY:
    print(f"  → Intentando descargar {ticker} ...")
    try:
        df = yf.download(
            ticker,
            start=PREV_DATE,
            end="2026-03-20",
            interval="5m",
            progress=False,
            prepost=True,   # incluir pre/post-market
        )
        if df is not None and len(df) > 0:
            print(f"  ✅ {ticker}: {len(df)} barras descargadas")
            raw_df = df
            used_ticker = ticker
            break
        else:
            print(f"  ⚠️  {ticker}: sin datos")
    except Exception as e:
        print(f"  ❌ {ticker}: {e}")

if raw_df is None or len(raw_df) == 0:
    print("\n❌ No se pudieron descargar datos reales.")
    print("   Genera datos de referencia simulados basados en backtest...")

    # Datos de referencia del backtest para usar como fallback
    fallback = {
        "status": "simulated",
        "source": "backtest_data",
        "message": "yfinance no devolvio datos reales para NQ el 2026-03-19",
        "params": {
            "POC": 24579.3,
            "VAH": 24639.0,
            "VAL": 24504.6,
            "NY_OPEN": 24327.0,
            "SWEEP_LOW": 24225.0,
            "NY_RANGE": 313.8,
            "MOVE_OC": 0.0,
            "POC_HIT": "11:05",
            "PATTERN": "SWEEP_L_RETURN"
        }
    }
    with open("nq_real_data.json", "w") as f:
        json.dump(fallback, f, indent=2)
    print("   Guardado en nq_real_data.json (fallback)")
    sys.exit(1)

# ──────────────────────────────────────
# Procesar y convertir a formato Lightweight Charts
# ──────────────────────────────────────
print(f"\n📊 Procesando datos de {used_ticker}...")
print(f"   Columnas: {list(raw_df.columns)}")
print(f"   Rango: {raw_df.index[0]} → {raw_df.index[-1]}")

# Flatten columnas si son MultiIndex (yfinance v0.2+)
if hasattr(raw_df.columns, 'levels'):
    raw_df.columns = raw_df.columns.get_level_values(0)

candles = []
for ts_idx, row in raw_df.iterrows():
    try:
        # Convertir timestamp a Unix seconds
        if hasattr(ts_idx, 'timestamp'):
            unix_ts = int(ts_idx.timestamp())
        else:
            unix_ts = int(ts_idx.value // 1_000_000_000)

        o = float(row['Open'])
        h = float(row['High'])
        l = float(row['Low'])
        c = float(row['Close'])

        # Filtrar NaN
        if any(v != v for v in [o, h, l, c]):
            continue
        # Filtrar valores 0
        if o == 0 or h == 0 or l == 0 or c == 0:
            continue

        candles.append({
            "time": unix_ts,
            "open":  round(o, 2),
            "high":  round(h, 2),
            "low":   round(l, 2),
            "close": round(c, 2),
        })
    except Exception as e:
        continue

print(f"   ✅ {len(candles)} barras válidas procesadas")

if candles:
    # Stats básicos
    all_highs = [c['high']  for c in candles]
    all_lows  = [c['low']   for c in candles]
    print(f"   High del día: {max(all_highs):.2f}")
    print(f"   Low  del día: {min(all_lows):.2f}")
    print(f"   Rango: {max(all_highs) - min(all_lows):.2f} pts")

    # Buscar sesión NY (13:30–20:00 UTC = 9:30–16:00 ET)
    ny_open_ts  = int(datetime(2026, 3, 19, 13, 30, tzinfo=timezone.utc).timestamp())
    ny_close_ts = int(datetime(2026, 3, 19, 20,  0, tzinfo=timezone.utc).timestamp())
    ny_candles  = [c for c in candles if ny_open_ts <= c['time'] <= ny_close_ts]
    if ny_candles:
        ny_open_price  = ny_candles[0]['open']
        ny_close_price = ny_candles[-1]['close']
        ny_high  = max(c['high'] for c in ny_candles)
        ny_low   = min(c['low']  for c in ny_candles)
        print(f"\n   NY Session:")
        print(f"   Open:  {ny_open_price:.2f}")
        print(f"   Close: {ny_close_price:.2f}")
        print(f"   High:  {ny_high:.2f}")
        print(f"   Low:   {ny_low:.2f}")
        print(f"   Range: {ny_high - ny_low:.2f} pts")
        print(f"   Move:  {ny_close_price - ny_open_price:+.2f} pts")

output = {
    "status": "real",
    "source": used_ticker,
    "total_bars": len(candles),
    "candles": candles
}

with open("nq_real_data.json", "w") as f:
    json.dump(output, f, indent=2)

print(f"\n✅ Guardado en nq_real_data.json ({len(candles)} barras)")
