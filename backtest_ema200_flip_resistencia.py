"""
backtest_ema200_flip_resistencia.py
══════════════════════════════════════════════════════════════════════
EMA 200: FLIP SOPORTE → RESISTENCIA  (SHORT setup)

Lógica de las 4 fases:
  1. UPTREND   — precio sobre EMA 200 durante ≥ BULL_BARS barras
  2. CHoCH     — cierre DEBAJO de la EMA (cambio de estructura)
  3. PULLBACK  — precio sube de vuelta hacia la EMA desde abajo
                 dentro de MAX_PB barras desde el CHoCH
  4. RECHAZO   — el LOW del retest no cruza la EMA hacia arriba
                 (cierra por debajo) → SHORT desde el cierre de esa vela

Target: stop arriba de la EMA, medir 1R/2R/3R hacia la baja.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# ─── Config ────────────────────────────────────────────────────────────────────
SYMBOL     = "NQ=F"
BULL_BARS  = 30      # barras mínimas sobre EMA para considerar uptrend
MAX_PB     = 60      # barras máximas para que llegue el pullback al EMA
TOUCH_PTS  = 6       # puntos máx que HIGH puede alejarse del EMA en el retest
MAX_BARS   = 50      # barras para buscar target tras el rechazo
R_TARGETS  = [1, 2, 3]
DAYS_BACK  = 30      # máximo que da yfinance en 1m

SESSIONS = {
    "Asia":   (0,  7),
    "London": (7, 13),
    "NY-AM":  (13, 17),
    "NY-PM":  (17, 21),
    "After":  (21, 24),
}
def session_label(h):
    for name, (s, e) in SESSIONS.items():
        if s <= h < e:
            return name
    return "After"

# ─── Descarga ──────────────────────────────────────────────────────────────────
def download_1m(symbol, days_back=30):
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    chunks = []
    cur   = start
    print(f"\n  Descargando {days_back}d de 1m en chunks...", flush=True)
    while cur < end:
        chunk_end = min(cur + timedelta(days=6), end)
        try:
            raw = yf.download(symbol,
                              start=cur.strftime("%Y-%m-%d"),
                              end=chunk_end.strftime("%Y-%m-%d"),
                              interval="1m", progress=False, auto_adjust=True)
            if not raw.empty:
                def _col(n, r=raw):
                    c = r[n]
                    if isinstance(c, pd.DataFrame): c = c.iloc[:, 0]
                    return c.values.astype(float)
                d = pd.DataFrame({
                    "Open": _col("Open"), "High": _col("High"),
                    "Low":  _col("Low"),  "Close": _col("Close"),
                    "Volume": _col("Volume"),
                }, index=raw.index)
                chunks.append(d)
                print(f"    {cur.date()} → {chunk_end.date()} : {len(d)} velas")
        except: pass
        cur = chunk_end + timedelta(minutes=1)
    if not chunks: return pd.DataFrame()
    df = pd.concat(chunks).sort_index()
    return df[~df.index.duplicated(keep="first")]

# ─── Indicadores básicos ───────────────────────────────────────────────────────
def calc_rsi(series, p=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(p).mean()
    loss  = (-delta.clip(upper=0)).rolling(p).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
print("\n" + "═"*70)
print("  NQ EMA 200 — FLIP SOPORTE → RESISTENCIA  |  SHORT SETUP")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("═"*70)

df = download_1m(SYMBOL, DAYS_BACK)
if df.empty:
    print("  Sin datos"); exit(1)

df["ema200"] = df["Close"].ewm(span=200, adjust=False).mean()
df["rsi14"]  = calc_rsi(df["Close"])
df["atr14"]  = (df["High"] - df["Low"]).rolling(14).mean()

close  = df["Close"].values
high   = df["High"].values
low    = df["Low"].values
open_  = df["Open"].values
ema    = df["ema200"].values
rsi_   = df["rsi14"].values
atr_   = df["atr14"].values
idx    = df.index

print(f"\n  Total: {len(df)} velas  ({idx[0].date()} → {idx[-1].date()})")

# ─── Detección de patrones ────────────────────────────────────────────────────
records = []
i = BULL_BARS + 10

while i < len(df) - MAX_BARS - 2:

    # ── FASE 1: Uptrend confirmado ─────────────────────────────────────────────
    # Todas (o casi) las últimas BULL_BARS velas cerraron SOBRE la EMA
    prev_window = close[i - BULL_BARS : i]
    ema_window  = ema[i  - BULL_BARS : i]
    bars_above  = np.sum(prev_window > ema_window)

    if bars_above < int(BULL_BARS * 0.80):   # 80% de las barras sobre EMA
        i += 1; continue

    # ── FASE 2: CHoCH — primer cierre DEBAJO de la EMA ────────────────────────
    if close[i] >= ema[i]:
        i += 1; continue

    # Confirmar que la vela anterior estaba sobre la EMA (cruce real)
    if close[i-1] <= ema[i-1]:
        i += 1; continue

    choch_idx  = i
    choch_ema  = ema[i]
    choch_close = close[i]

    # ── FASE 3: Pullback — precio sube de vuelta hacia la EMA desde abajo ─────
    found_pullback = False
    pb_idx = -1

    for j in range(choch_idx + 1, min(choch_idx + MAX_PB, len(df) - MAX_BARS - 2)):
        # Precio sigue debajo de EMA
        if close[j] > ema[j]:   # ya cruzó arriba → no cuenta, perdimos el flip
            break

        # HIGH del pullback llega a tocar (o casi) la EMA desde abajo
        dist_to_ema = ema[j] - high[j]   # positivo = high está debajo del EMA
        if -2 <= dist_to_ema <= TOUCH_PTS:
            # El cierre sigue por debajo → rechazo confirmado
            if close[j] < ema[j]:
                found_pullback = True
                pb_idx = j
                break

    if not found_pullback:
        i = choch_idx + 1; continue

    # ── FASE 4: Medir el SHORT desde el cierre del rechazo ────────────────────
    entry_price = close[pb_idx]
    stop_price  = max(high[pb_idx], ema[pb_idx]) + 6    # stop sobre EMA + buffer
    r1_dist     = stop_price - entry_price

    if r1_dist < 8 or r1_dist > 120:
        i = pb_idx + 1; continue

    hour  = idx[pb_idx].hour
    sess  = session_label(hour)
    dow   = idx[pb_idx].weekday()
    days  = ["Lun","Mar","Mie","Jue","Vie","Sab","Dom"]
    day   = days[dow]

    rsi_v = round(float(rsi_[pb_idx]), 1) if not np.isnan(rsi_[pb_idx]) else 50.0
    atr_v = round(float(atr_[pb_idx]), 1) if not np.isnan(atr_[pb_idx]) else 10.0

    # Contexto del CHoCH
    bars_bull_before = int(bars_above)   # barras de uptrend previo
    dist_choch_pb    = pb_idx - choch_idx  # barras entre CHoCH y el retest

    # Vela del pullback
    body   = abs(close[pb_idx] - open_[pb_idx])
    rng    = high[pb_idx] - low[pb_idx]
    is_bear_rej = int(close[pb_idx] < open_[pb_idx])         # vela bajista en el rechazo
    long_wick   = int(rng > 0 and (high[pb_idx] - max(close[pb_idx], open_[pb_idx])) > 0.40 * rng)

    # Buscar targets (SHORT = precio baja)
    f_lo  = low[pb_idx+1  : pb_idx+MAX_BARS+1]
    f_hi  = high[pb_idx+1 : pb_idx+MAX_BARS+1]
    f_cl  = close[pb_idx+1: pb_idx+MAX_BARS+1]

    hit_stop = False
    r_hit    = {r: False for r in R_TARGETS}

    for bi in range(len(f_lo)):
        if f_hi[bi] >= stop_price:
            hit_stop = True; break
        for r in R_TARGETS:
            target = entry_price - r * r1_dist
            if not r_hit[r] and f_lo[bi] <= target:
                r_hit[r] = True
        if all(r_hit.values()):
            break

    records.append({
        "session":       sess,
        "hour_utc":      hour,
        "day":           day,
        "rsi14":         rsi_v,
        "atr14":         atr_v,
        "bars_uptrend":  bars_bull_before,
        "bars_to_pb":    dist_choch_pb,
        "r1_pts":        round(r1_dist, 1),
        "is_bear_rej":   is_bear_rej,
        "long_wick_up":  long_wick,
        "hit_stop":      int(hit_stop),
        **{f"hit_{r}R": int(r_hit[r]) for r in R_TARGETS},
    })

    # Avanzar más allá del pullback para no reutilizar el mismo CHoCH
    i = pb_idx + 5

# ─── Resultados ───────────────────────────────────────────────────────────────
df_res = pd.DataFrame(records)
N = len(df_res)
print(f"\n  Flips detectados: {N}")

if N < 5:
    print("  Pocos flips — prueba con más datos o relaja los parámetros.")
    exit()

base2R = df_res["hit_2R"].mean() * 100
base1R = df_res["hit_1R"].mean() * 100
base3R = df_res["hit_3R"].mean() * 100
bstp   = df_res["hit_stop"].mean() * 100

print(f"\n╔══ RESULTADO GLOBAL ══════════════════════════════════════════════════╗")
print(f"\n  Flips  1R Win%  2R Win%  3R Win%  Stop%")
print(f"  {N:>5}  {base1R:>6.1f}  {base2R:>6.1f}  {base3R:>6.1f}  {bstp:>6.1f}")

# ── Por sesión + horas internas ────────────────────────────────────────────────
print(f"\n\n╔══ POR SESIÓN + HORAS INTERNAS ══════════════════════════════════════╗")
sess_order = ["Asia","London","NY-AM","NY-PM","After"]
for sess in sess_order:
    g = df_res[df_res["session"] == sess]
    if len(g) < 2: continue
    wr1 = g["hit_1R"].mean()*100
    wr2 = g["hit_2R"].mean()*100
    wr3 = g["hit_3R"].mean()*100
    stp = g["hit_stop"].mean()*100
    print(f"\n  ┌── {sess:<8}  n={len(g):>3}  "
          f"1R:{wr1:>5.1f}%  2R:{wr2:>5.1f}%  3R:{wr3:>5.1f}%  Stop:{stp:>5.1f}%")
    for h in sorted(g["hour_utc"].unique()):
        hg = g[g["hour_utc"] == h]
        if len(hg) < 2: continue
        h2 = hg["hit_2R"].mean()*100
        h3 = hg["hit_3R"].mean()*100
        hs = hg["hit_stop"].mean()*100
        mark = " ★" if h2 >= 50 else (" ▼" if h2 < 25 else "")
        print(f"  │  {h:02d}:00  n={len(hg):>2}  "
              f"2R:{h2:>5.1f}%  3R:{h3:>5.1f}%  Stop:{hs:>5.1f}%{mark}")

# ── Por día de la semana ───────────────────────────────────────────────────────
print(f"\n\n╔══ POR DÍA ═══════════════════════════════════════════════════════════╗\n")
day_rows = []
for d in ["Lun","Mar","Mie","Jue","Vie"]:
    g = df_res[df_res["day"] == d]
    if len(g) < 2: continue
    day_rows.append({"Día":d, "n":len(g),
                     "1R%": round(g["hit_1R"].mean()*100,1),
                     "2R%": round(g["hit_2R"].mean()*100,1),
                     "3R%": round(g["hit_3R"].mean()*100,1),
                     "Stop%": round(g["hit_stop"].mean()*100,1)})
if day_rows: print(pd.DataFrame(day_rows).to_string(index=False))

# ── Filtros ────────────────────────────────────────────────────────────────────
print(f"\n\n╔══ FILTROS — QUÉ MEJORA EL WIN RATE 2R ══════════════════════════════╗\n")
print(f"  BASE: {round(base2R,1)}%  (n={N})\n")
filters = [
    ("RSI < 40 (sobrevendido en el retest)", df_res["rsi14"] < 40),
    ("RSI 40-55",                            df_res["rsi14"].between(40,55)),
    ("RSI > 55 (fuerza aún arriba)",         df_res["rsi14"] > 55),
    ("Vela bajista en el rechazo ★",         df_res["is_bear_rej"] == 1),
    ("Mecha larga hacia arriba ★",           df_res["long_wick_up"] == 1),
    ("Pullback rápido (≤15 barras)",         df_res["bars_to_pb"] <= 15),
    ("Pullback lento (>15 barras)",          df_res["bars_to_pb"] > 15),
    ("Uptrend largo (>50 barras previas)",   df_res["bars_uptrend"] > 50),
    ("Uptrend corto (≤50 barras previas)",   df_res["bars_uptrend"] <= 50),
    ("Stop chico (<20 pts)",                 df_res["r1_pts"] < 20),
    ("Stop grande (≥20 pts)",                df_res["r1_pts"] >= 20),
    ("ATR alto (>10)",                       df_res["atr14"] > 10),
]
frows = []
for label, mask in filters:
    s = df_res[mask]
    if len(s) < 3: continue
    wr = s["hit_2R"].mean()*100
    frows.append({"Filtro": label, "n": len(s),
                  "2R Win%": round(wr,1), "vs Base": f"{wr-base2R:+.1f}%"})
fd = pd.DataFrame(frows).sort_values("2R Win%", ascending=False)
print(fd.to_string(index=False))

# ── Estadísticas del setup ─────────────────────────────────────────────────────
print(f"\n\n╔══ ESTADÍSTICAS DEL SETUP ════════════════════════════════════════════╗\n")
print(f"  Barras de uptrend previo — media : {df_res['bars_uptrend'].mean():.0f}")
print(f"  Barras CHoCH → retest   — media : {df_res['bars_to_pb'].mean():.1f}")
print(f"  Stop (R1) medio         — pts   : {df_res['r1_pts'].mean():.1f}")
print(f"  RSI promedio en retest           : {df_res['rsi14'].mean():.1f}")
print(f"  % con vela bajista en retest     : {df_res['is_bear_rej'].mean()*100:.1f}%")
print(f"  % con mecha larga hacia arriba   : {df_res['long_wick_up'].mean()*100:.1f}%")

print("\n" + "═"*70 + "\n")
