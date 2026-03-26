"""
backtest_ema_cross.py
══════════════════════════════════════════════════════════════════════
Backtest: ¿Qué tan confiable es cruzar la EMA 200 / 800 en NQ?

Por cada cruce detectado analiza:
  - ¿El precio siguió la dirección del cruce? (follow-through)
  - En qué SESIÓN ocurrió (Asia / London / NY-AM / NY-PM / After)
  - A qué HORA UTC exacta
  - En qué TIMEFRAME (5m, 15m, 1h)

Métrica principal:
  Win rate = cruces que siguieron la dirección N barras después
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# ─── Config ────────────────────────────────────────────────────────────────────
SYMBOL        = "NQ=F"
FOLLOW_BARS   = 3       # cuántas velas después verificar el follow-through
EMA_PERIODS   = [200, 800]

SESSIONS = {
    "Asia":   (0,  7),
    "London": (7, 13),
    "NY-AM":  (13, 17),
    "NY-PM":  (17, 21),
    "After":  (21, 24),
}

TIMEFRAMES = [
    ("5m",  "5m",  "60d"),
    ("15m", "15m", "730d"),
    ("1h",  "1h",  "730d"),
]

# ─── Helpers ───────────────────────────────────────────────────────────────────
def session_label(hour_utc):
    for name, (start, end) in SESSIONS.items():
        if start <= hour_utc < end:
            return name
    return "After"

def detect_crosses(close, ema, direction="up"):
    """
    Devuelve índices donde el precio cruza la EMA.
    direction='up'  : pasa de debajo a encima
    direction='down': pasa de encima a debajo
    """
    above = (close > ema).astype(bool)  # cast explícito para evitar TypeError
    prev  = above.shift(1).fillna(False).astype(bool)
    if direction == "up":
        cross = (~prev) & above
    else:
        cross = prev & (~above)
    return cross

def run_backtest(label, interval, period):
    print(f"\n  Descargando {label}...", end="", flush=True)
    df = yf.download(SYMBOL, interval=interval, period=period,
                     progress=False, auto_adjust=True)
    if df.empty:
        print(" sin datos")
        return None

    close = df["Close"].squeeze()
    df["hour"] = pd.to_datetime(df.index).hour
    df["session"] = df["hour"].apply(session_label)

    records = []

    for ema_p in EMA_PERIODS:
        if len(close) < ema_p:
            continue

        ema_vals = close.ewm(span=ema_p, adjust=False).mean()
        df[f"ema{ema_p}"] = ema_vals

        for direction in ["up", "down"]:
            crosses = detect_crosses(close, ema_vals, direction)
            cross_idx = np.where(crosses.values)[0]

            for ci in cross_idx:
                if ci + FOLLOW_BARS >= len(close):
                    continue

                entry_price  = float(close.iloc[ci])
                future_price = float(close.iloc[ci + FOLLOW_BARS])
                row_time     = df.index[ci]

                if hasattr(row_time, 'to_pydatetime'):
                    row_time = row_time.to_pydatetime()

                hour_utc = row_time.hour if hasattr(row_time, 'hour') else 0
                sess     = df["session"].iloc[ci]

                # Win = el precio siguió la dirección del cruce
                if direction == "up":
                    win = future_price > entry_price
                else:
                    win = future_price < entry_price

                move_pct = abs((future_price - entry_price) / entry_price * 100)

                records.append({
                    "tf":        label,
                    "ema":       ema_p,
                    "direction": direction,
                    "session":   sess,
                    "hour_utc":  hour_utc,
                    "win":       int(win),
                    "move_pct":  round(move_pct, 3),
                })

    print(f" {len(records)} cruces", flush=True)
    return pd.DataFrame(records)

# ─── Main ──────────────────────────────────────────────────────────────────────
print("\n" + "═"*70)
print("  NQ EMA 200 & 800 — BACKTEST DE CRUCES")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print(f"  Follow-through medido {FOLLOW_BARS} velas después del cruce")
print("═"*70)

all_dfs = []
for tf_args in TIMEFRAMES:
    df_tf = run_backtest(*tf_args)
    if df_tf is not None and len(df_tf) > 0:
        all_dfs.append(df_tf)

if not all_dfs:
    print("Sin datos. Verifica tu conexión a internet.")
    exit(1)

df_all = pd.concat(all_dfs, ignore_index=True)

# ═══ 1. RESUMEN GENERAL ═══════════════════════════════════════════════════════
print("\n\n╔══ 1. WIN RATE GENERAL (por TF y EMA) ══════════════════════════════╗\n")
summary = (df_all.groupby(["tf","ema"])
           .agg(
               cruces=("win","count"),
               win_rate=("win","mean"),
               move_avg=("move_pct","mean"),
               move_max=("move_pct","max"),
           )
           .reset_index())
summary["win_rate"] = (summary["win_rate"] * 100).round(1)
summary["move_avg"] = summary["move_avg"].round(2)
summary["move_max"] = summary["move_max"].round(2)
summary.columns = ["TF","EMA","Cruces","Win%","Mov.Avg%","Mov.Max%"]
print(summary.to_string(index=False))

# ═══ 2. POR SESIÓN ════════════════════════════════════════════════════════════
print("\n\n╔══ 2. WIN RATE POR SESIÓN ═══════════════════════════════════════════╗\n")
order_sess = ["Asia","London","NY-AM","NY-PM","After"]

for tf_label in ["5m","15m","1h"]:
    subset = df_all[df_all["tf"] == tf_label]
    if subset.empty:
        continue
    sess_df = (subset.groupby(["session","ema"])
               .agg(cruces=("win","count"), win_rate=("win","mean"))
               .reset_index())
    sess_df["win_rate"] = (sess_df["win_rate"]*100).round(1)
    # pivot
    pv = sess_df.pivot_table(index="session", columns="ema",
                             values="win_rate", aggfunc="first")
    pv = pv.reindex([s for s in order_sess if s in pv.index])
    pv.columns = [f"EMA{c} Win%" for c in pv.columns]
    print(f"  ── {tf_label} ──")
    print(pv.to_string())
    print()

# ═══ 3. POR HORA (horas con >5 muestras) ═════════════════════════════════════
print("\n╔══ 3. WIN RATE POR HORA UTC — 1h ════════════════════════════════════╗\n")
df_1h = df_all[df_all["tf"] == "1h"]
if not df_1h.empty:
    hour_df = (df_1h.groupby(["hour_utc","ema"])
               .agg(cruces=("win","count"), win_rate=("win","mean"))
               .reset_index())
    hour_df = hour_df[hour_df["cruces"] >= 3]
    hour_df["win_rate"] = (hour_df["win_rate"]*100).round(1)
    pv_h = hour_df.pivot_table(index="hour_utc", columns="ema",
                               values="win_rate", aggfunc="first").sort_index()
    pv_h.columns = [f"EMA{c} Win%" for c in pv_h.columns]
    pv_h.index.name = "HoraUTC"
    print(pv_h.to_string())

# ═══ 4. MEJORES HORAS (top 5 más confiables) ══════════════════════════════════
print("\n\n╔══ 4. TOP HORAS MÁS CONFIABLES (win% >= 60%, mín 5 cruces) ═════════╗\n")
top = df_all.groupby(["tf","ema","hour_utc","session"]).agg(
    cruces=("win","count"), win_rate=("win","mean")
).reset_index()
top = top[top["cruces"] >= 5]
top["win_rate"] = (top["win_rate"] * 100).round(1)
top = top[top["win_rate"] >= 60].sort_values("win_rate", ascending=False).head(20)
top["session_label"] = top["hour_utc"].apply(session_label)
print(top[["tf","ema","hour_utc","session","win_rate","cruces"]].to_string(index=False))

print("\n" + "═"*70 + "\n")
