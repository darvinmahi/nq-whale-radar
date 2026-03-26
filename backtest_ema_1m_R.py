"""
backtest_ema_1m_R.py
══════════════════════════════════════════════════════════════════════
Backtest 1-MINUTO: Entradas en cruces EMA 200 / 800 con R alto en NQ

Lógica de entrada:
  - Detecta cruce del precio sobre/bajo EMA200 o EMA800 en 1m
  - Entrada: cierre de la vela del cruce
  - Stop: distancia del precio a la EMA en ese momento (1R)
  - Targets: 1R, 2R, 3R — mide qué % de trades los alcanza

Sesiones (UTC):
  Asia    : 00-07
  London  : 07-13
  NY-AM   : 13-17
  NY-PM   : 17-21
  After   : 21-24

Nota: yfinance limita 1m a los últimos 7 días.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# ─── Params ────────────────────────────────────────────────────────────────────
SYMBOL      = "NQ=F"
R_TARGETS   = [1, 2, 3]          # cuántos R medir
MIN_STOP_PT = 5                   # mínimo de puntos para el stop (evita ruido)
MAX_BARS    = 60                  # máximo de velas para buscar el target

SESSIONS = {
    "Asia":   (0,  7),
    "London": (7, 13),
    "NY-AM":  (13, 17),
    "NY-PM":  (17, 21),
    "After":  (21, 24),
}

def session_label(hour):
    for name, (s, e) in SESSIONS.items():
        if s <= hour < e:
            return name
    return "After"

# ─── Descargar 1m ──────────────────────────────────────────────────────────────
print("\n" + "═"*68)
print("  NQ EMA 200 & 800 — BACKTEST 1-MINUTO con R")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("═"*68)

print("\n  Descargando datos 1m (últimos 7 días)...", flush=True)
df = yf.download(SYMBOL, interval="1m", period="7d",
                 progress=False, auto_adjust=True)

if df.empty:
    print("  ERROR: No se recibieron datos.")
    exit(1)

# Normalizar
for col in ["Open","High","Low","Close"]:
    df[col] = df[col].squeeze()

print(f"  {len(df)} velas descargadas ({df.index[0]} → {df.index[-1]})\n")

close = df["Close"]
high  = df["High"]
low   = df["Low"]

# ─── Calcular EMAs ────────────────────────────────────────────────────────────
df["ema200"] = close.ewm(span=200, adjust=False).mean()
df["ema800"] = close.ewm(span=800, adjust=False).mean()

# ─── Función: backtest de una EMA ─────────────────────────────────────────────
def backtest_ema(ema_col, ema_label):
    ema    = df[ema_col]
    above  = (close > ema).astype(bool)
    prev   = above.shift(1).fillna(False).astype(bool)

    cross_up   = (~prev) & above    # cruce alcista
    cross_down = prev & (~above)    # cruce bajista

    trades = []

    for direction, cross_mask in [("LONG", cross_up), ("SHORT", cross_down)]:
        cross_idx = np.where(cross_mask.values)[0]

        for ci in cross_idx:
            if ci + MAX_BARS >= len(df):
                continue

            entry = float(close.iloc[ci])
            ema_v = float(ema.iloc[ci])
            dist  = abs(entry - ema_v)

            if dist < MIN_STOP_PT:
                continue             # cruce con muy poco momentum → ruido

            if direction == "LONG":
                stop   = entry - dist    # stop bajo la EMA
                t_dir  = 1
            else:
                stop   = entry + dist
                t_dir  = -1

            ts   = df.index[ci]
            hour = ts.hour if hasattr(ts, 'hour') else 0
            sess = session_label(hour)

            # buscar cuántos R alcanza en las próximas MAX_BARS velas
            future_hi = high.iloc[ci+1 : ci+MAX_BARS+1].values
            future_lo = low.iloc[ci+1  : ci+MAX_BARS+1].values

            # ¿llega al stop primero?
            hit_stop = False
            r_hit    = {}
            for r in R_TARGETS:
                r_hit[r] = False

            for bi in range(len(future_hi)):
                lo_bar = future_lo[bi]
                hi_bar = future_hi[bi]

                # ¿stop hit?
                if direction == "LONG"  and lo_bar <= stop:
                    hit_stop = True
                if direction == "SHORT" and hi_bar >= stop:
                    hit_stop = True

                if hit_stop:
                    break

                for r in R_TARGETS:
                    target = entry + t_dir * dist * r
                    if not r_hit[r]:
                        if direction == "LONG"  and hi_bar >= target:
                            r_hit[r] = True
                        if direction == "SHORT" and lo_bar <= target:
                            r_hit[r] = True

                # Si todos los targets alcanzados, salir
                if all(r_hit.values()):
                    break

            trades.append({
                "ema":       ema_label,
                "dir":       direction,
                "session":   sess,
                "hour_utc":  hour,
                "dist_pts":  round(dist, 1),
                "hit_stop":  hit_stop,
                **{f"hit_{r}R": int(r_hit[r]) for r in R_TARGETS},
            })

    return pd.DataFrame(trades)

# ─── Ejecutar para EMA200 y EMA800 ────────────────────────────────────────────
df200 = backtest_ema("ema200", "EMA200")
df800 = backtest_ema("ema800", "EMA800")
all_trades = pd.concat([df200, df800], ignore_index=True)

total = len(all_trades)
print(f"  Total de cruces con stop válido (>{MIN_STOP_PT}pts): {total}")

if total == 0:
    print("  Sin suficientes datos.")
    exit(1)

# ═══ 1. RESUMEN GENERAL ═══════════════════════════════════════════════════════
print("\n╔══ 1. WIN RATE GENERAL por EMA y R ════════════════════════════════╗\n")
summary_rows = []
for ema_lbl in ["EMA200", "EMA800"]:
    sub = all_trades[all_trades["ema"] == ema_lbl]
    row = {"EMA": ema_lbl, "Trades": len(sub), "Stop%": round(sub["hit_stop"].mean()*100,1)}
    for r in R_TARGETS:
        row[f"{r}R Win%"] = round(sub[f"hit_{r}R"].mean()*100, 1)
    summary_rows.append(row)
print(pd.DataFrame(summary_rows).to_string(index=False))

# ═══ 2. POR SESIÓN ════════════════════════════════════════════════════════════
print("\n\n╔══ 2. WIN RATE POR SESIÓN ══════════════════════════════════════════╗\n")
order = ["Asia","London","NY-AM","NY-PM","After"]

for ema_lbl in ["EMA200", "EMA800"]:
    sub = all_trades[all_trades["ema"] == ema_lbl]
    rows = []
    for sess in order:
        s = sub[sub["session"] == sess]
        if len(s) < 3:
            continue
        r = {"Sesión": sess, "Trades": len(s), "Stop%": round(s["hit_stop"].mean()*100,1)}
        for rv in R_TARGETS:
            r[f"{rv}R%"] = round(s[f"hit_{rv}R"].mean()*100, 1)
        rows.append(r)
    if rows:
        print(f"  ── {ema_lbl} ──")
        print(pd.DataFrame(rows).to_string(index=False))
        print()

# ═══ 3. POR HORA ══════════════════════════════════════════════════════════════
print("\n╔══ 3. WIN RATE 2R POR HORA UTC (mín 3 trades) ═════════════════════╗\n")
for ema_lbl in ["EMA200", "EMA800"]:
    sub = all_trades[all_trades["ema"] == ema_lbl]
    hour_rows = []
    for h in sorted(sub["hour_utc"].unique()):
        hd = sub[sub["hour_utc"] == h]
        if len(hd) < 3:
            continue
        sess = session_label(h)
        hour_rows.append({
            "HoraUTC": h,
            "Sesión":  sess,
            "Trades":  len(hd),
            "2R Win%": round(hd["hit_2R"].mean()*100, 1),
            "3R Win%": round(hd["hit_3R"].mean()*100, 1),
            "Stop%":   round(hd["hit_stop"].mean()*100, 1),
        })
    if hour_rows:
        print(f"  ── {ema_lbl} ──")
        df_h = pd.DataFrame(hour_rows).sort_values("2R Win%", ascending=False)
        print(df_h.to_string(index=False))
        print()

# ═══ 4. SESIÓN GANADORA ════════════════════════════════════════════════════════
print("\n╔══ 4. RANKING DE SESIONES (por 2R Win%) ════════════════════════════╗\n")
rows_rank = []
for ema_lbl in ["EMA200","EMA800"]:
    sub = all_trades[all_trades["ema"] == ema_lbl]
    for sess in order:
        s = sub[sub["session"] == sess]
        if len(s) < 3: continue
        rows_rank.append({
            "EMA":    ema_lbl,
            "Sesión": sess,
            "Trades": len(s),
            "1R Win%": round(s["hit_1R"].mean()*100,1),
            "2R Win%": round(s["hit_2R"].mean()*100,1),
            "3R Win%": round(s["hit_3R"].mean()*100,1),
            "Stop Hit%": round(s["hit_stop"].mean()*100,1),
        })
rank = pd.DataFrame(rows_rank).sort_values("2R Win%", ascending=False)
print(rank.to_string(index=False))

print("\n" + "═"*68 + "\n")
