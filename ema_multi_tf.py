"""
ema_multi_tf.py - EMA 200 & 800 en multiples timeframes para NQ
Timeframes: 1m, 5m, 15m, 1h

Salida: precio actual vs EMA200 vs EMA800 en cada TF
        + si el precio está sobre o bajo cada EMA
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timezone

SYMBOL = "NQ=F"   # NQ Futures

TIMEFRAMES = [
    ("1m",  "1m",  "5d"),   # (label, yf interval, period)
    ("5m",  "5m",  "30d"),
    ("15m", "15m", "60d"),
    ("1h",  "1h",  "730d"),
]

EMA_PERIODS = [200, 800]

def get_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

def analyze(label, interval, period):
    df = yf.download(SYMBOL, interval=interval, period=period, progress=False, auto_adjust=True)
    if df.empty:
        return None

    close = df["Close"].squeeze()
    current = float(close.iloc[-1])

    result = {"TF": label, "Precio": round(current, 2)}
    for p in EMA_PERIODS:
        if len(close) < p:
            result[f"EMA{p}"] = "insuf.datos"
            result[f"vs EMA{p}"] = "—"
        else:
            ema_val = float(get_ema(close, p).iloc[-1])
            diff = current - ema_val
            pct  = diff / ema_val * 100
            pos  = "SOBRE" if diff > 0 else "BAJO"
            result[f"EMA{p}"] = round(ema_val, 2)
            result[f"vs EMA{p}"] = f"{pos} ({pct:+.2f}%)"

    return result

# ─── Main ─────────────────────────────────────────────────────────────────────
print(f"\n{'='*68}")
print(f"  NQ EMA 200 & 800 — Multi-Timeframe Analysis")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print(f"{'='*68}")

rows = []
for args in TIMEFRAMES:
    print(f"  Descargando {args[0]}...", end="\r")
    row = analyze(*args)
    if row:
        rows.append(row)

df_out = pd.DataFrame(rows)
df_out = df_out.set_index("TF")

print(df_out.to_string())
print(f"\n{'='*68}")

# ─── Resumen de confluencia ────────────────────────────────────────────────────
print("\n  CONFLUENCIA:")
for row in rows:
    tf = row["TF"]
    e200 = row.get("vs EMA200", "—")
    e800 = row.get("vs EMA800", "—")
    bullish = e200.startswith("SOBRE") and e800.startswith("SOBRE")
    bearish = e200.startswith("BAJO")  and e800.startswith("BAJO")
    bias = "ALCISTA" if bullish else ("BAJISTA" if bearish else "MIXTO  ")
    print(f"    {tf:4s} → {bias}  | EMA200: {e200:<20s} EMA800: {e800}")

print()
