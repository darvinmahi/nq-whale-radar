"""
backtest_ema200_choch_real.py
══════════════════════════════════════════════════════════════════════
EMA 200: CHoCH REAL → FLIP SOPORTE→RESISTENCIA  (SHORT setup)

Diferencia clave vs versión anterior:
  Un CHoCH es REAL solo si cumple LAS 3 condiciones:
    A) Cierre de vela DEBAJO de EMA (no solo wick)
    B) Rompe el último SWING LOW significativo (Higher Low roto = CHoCH)
    C) Al menos 3 cierres consecutivos bajo EMA (no recupera rápido)

Solo se toma el PRIMER retest válido por cada CHoCH real.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# ─── Config ────────────────────────────────────────────────────────────────────
SYMBOL        = "NQ=F"
DAYS_BACK     = 30

# CHoCH quality
MIN_CONSEC    = 3     # mínimo de cierres consecutivos bajo EMA para validar cruce
SWING_LOOKBACK= 30    # barras hacia atrás para buscar el último swing low
SWING_BARS    = 5     # barras a cada lado para definir un swing low local
BODY_ATR_MULT = 0.40  # cuerpo de la vela rompedora > X * ATR

# Retest
TOUCH_PTS     = 8     # HIGH del retest puede estar a máx X pts bajo la EMA
MAX_PB_BARS   = 80    # máx barras para que llegue el pullback

# Medición de resultado
MAX_RESULT_BARS = 60
R_TARGETS     = [1, 2, 3]

SESSIONS = {"Asia":(0,7),"London":(7,13),"NY-AM":(13,17),"NY-PM":(17,21),"After":(21,24)}
def session_label(h):
    for name,(s,e) in SESSIONS.items():
        if s <= h < e: return name
    return "After"

# ─── Descarga ──────────────────────────────────────────────────────────────────
def download_1m(symbol, days_back=30):
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    chunks = []
    cur = start
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
                    if isinstance(c, pd.DataFrame): c = c.iloc[:,0]
                    return c.values.astype(float)
                d = pd.DataFrame({
                    "Open":_col("Open"),"High":_col("High"),
                    "Low":_col("Low"),"Close":_col("Close"),"Volume":_col("Volume"),
                }, index=raw.index)
                chunks.append(d)
                print(f"    {cur.date()} → {chunk_end.date()} : {len(d)} velas")
        except: pass
        cur = chunk_end + timedelta(minutes=1)
    if not chunks: return pd.DataFrame()
    df = pd.concat(chunks).sort_index()
    return df[~df.index.duplicated(keep="first")]

# ─── Swing Low local ───────────────────────────────────────────────────────────
def find_last_swing_low(low_arr, before_idx, lookback=30, bars_each_side=5):
    """Busca el swing low más reciente antes de before_idx."""
    start = max(bars_each_side, before_idx - lookback)
    end   = before_idx - bars_each_side
    best_idx  = -1
    best_low  = np.inf
    for k in range(start, end):
        window_l = low_arr[k - bars_each_side : k]
        window_r = low_arr[k + 1 : k + bars_each_side + 1]
        if len(window_l) < bars_each_side or len(window_r) < bars_each_side:
            continue
        if low_arr[k] < window_l.min() and low_arr[k] < window_r.min():
            if low_arr[k] < best_low:
                best_low = low_arr[k]
                best_idx = k
    return best_idx, best_low

# ─── RSI ───────────────────────────────────────────────────────────────────────
def calc_rsi(series, p=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(p).mean()
    loss  = (-delta.clip(upper=0)).rolling(p).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

# ─── MAIN ──────────────────────────────────────────────────────────────────────
print("\n" + "═"*72)
print("  NQ EMA 200 — CHoCH REAL + FLIP S→R  |  SHORT SETUP  v2")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("═"*72)

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
n      = len(df)

print(f"\n  Total: {n} velas  ({idx[0].date()} → {idx[-1].date()})")

# ─── Detección ────────────────────────────────────────────────────────────────
records   = []
used_choch = set()   # para no reutilizar el mismo CHoCH
i = max(SWING_LOOKBACK + SWING_BARS + 5, 250)  # warmup EMA

choch_list = []  # lista de CHoCH reales encontrados

# PASO 1: Encontrar todos los CHoCH reales
while i < n - MAX_RESULT_BARS - 5:

    # ---- A) Primer cierre bajo EMA (cruce bajista) ----
    if not (close[i-1] > ema[i-1] and close[i] < ema[i]):
        i += 1; continue

    # ---- B) Cuerpo de la vela rompedora ----
    atr_v = atr_[i] if not np.isnan(atr_[i]) else 10.0
    body  = abs(close[i] - open_[i])
    if body < BODY_ATR_MULT * atr_v:
        i += 1; continue

    # ---- C) Cierres consecutivos bajo EMA ----
    consec = 0
    for k in range(i, min(i + 20, n)):
        if close[k] < ema[k]: consec += 1
        else: break
    if consec < MIN_CONSEC:
        i += 1; continue

    # ---- D) Ruptura de swing low reciente ----
    sl_idx, sl_price = find_last_swing_low(low, i, SWING_LOOKBACK, SWING_BARS)
    if sl_idx < 0:
        i += 1; continue

    # El cierre de la vela CHoCH debe estar POR DEBAJO del swing low
    if close[i] >= sl_price:
        i += 1; continue

    choch_list.append({
        "idx": i, "ema": ema[i], "close": close[i],
        "sl_price": sl_price, "consec": consec,
        "body_pts": round(body, 1)
    })
    i += consec + 1   # saltar el período de consolidación

print(f"\n  CHoCH REALES detectados: {len(choch_list)}")
if len(choch_list) == 0:
    print("  Sin CHoCH reales — prueba reduciendo MIN_CONSEC o BODY_ATR_MULT")
    exit()

# PASO 2: Para cada CHoCH, buscar el PRIMER retest válido hacia la EMA
for choch in choch_list:
    ci    = choch["idx"]
    choch_ema = choch["ema"]

    found = False
    for j in range(ci + 1, min(ci + MAX_PB_BARS, n - MAX_RESULT_BARS - 2)):

        # Precio debe seguir bajo EMA (no recuperó)
        if close[j] > ema[j]:
            break  # recuperó — invalidado

        # HIGH del pullback toca (casi) la EMA desde abajo
        dist = ema[j] - high[j]
        if not (-2 <= dist <= TOUCH_PTS):
            continue

        # Cierre sigue bajo EMA = rechazo
        if close[j] >= ema[j]:
            continue

        # ── Setup encontrado ──
        entry  = close[j]
        stop   = max(high[j], ema[j]) + 5
        r1_dist = stop - entry
        if r1_dist < 6 or r1_dist > 100:
            continue

        hour  = idx[j].hour
        sess  = session_label(hour)
        dow   = idx[j].weekday()
        day   = ["Lun","Mar","Mie","Jue","Vie","Sab","Dom"][dow]
        rsi_v = float(rsi_[j]) if not np.isnan(rsi_[j]) else 50.0
        atr_v = float(atr_[j]) if not np.isnan(atr_[j]) else 10.0

        body_pb  = abs(close[j] - open_[j])
        wick_up  = high[j] - max(close[j], open_[j])
        rng_pb   = high[j] - low[j]
        is_bear  = int(close[j] < open_[j])
        lw_up    = int(rng_pb > 0 and wick_up > 0.35 * rng_pb)

        # Medir resultado (SHORT)
        f_lo  = low[j+1  : j+MAX_RESULT_BARS+1]
        f_hi  = high[j+1 : j+MAX_RESULT_BARS+1]

        hit_stop = False
        r_hit    = {r: False for r in R_TARGETS}
        for bi in range(len(f_lo)):
            if f_hi[bi] >= stop:
                hit_stop = True; break
            for r in R_TARGETS:
                tgt = entry - r * r1_dist
                if not r_hit[r] and f_lo[bi] <= tgt:
                    r_hit[r] = True
            if all(r_hit.values()): break

        records.append({
            "session":      sess,
            "hour_utc":     hour,
            "day":          day,
            "rsi14":        round(rsi_v, 1),
            "atr14":        round(atr_v, 1),
            "r1_pts":       round(r1_dist, 1),
            "choch_consec": choch["consec"],
            "choch_body":   choch["body_pts"],
            "bars_to_pb":   j - ci,
            "is_bear_rej":  is_bear,
            "long_wick_up": lw_up,
            "hit_stop":     int(hit_stop),
            **{f"hit_{r}R": int(r_hit[r]) for r in R_TARGETS},
        })
        found = True
        break  # solo el PRIMER retest


# ─── Resultados ───────────────────────────────────────────────────────────────
df_r = pd.DataFrame(records)
N    = len(df_r)
print(f"  Setups con retest válido: {N}")

if N < 3:
    print("  Muy pocos setups — datos insuficientes o parámetros muy estrictos.")
    print(f"  Sugerencia: bajar MIN_CONSEC a 2 o BODY_ATR_MULT a 0.25")
    exit()

b1   = df_r["hit_1R"].mean()*100
b2   = df_r["hit_2R"].mean()*100
b3   = df_r["hit_3R"].mean()*100
bstp = df_r["hit_stop"].mean()*100

print(f"\n╔══ RESULTADO GLOBAL ═════════════════════════════════════════════════╗")
print(f"\n  CHoCH Reales  Retests  1R Win%  2R Win%  3R Win%  Stop%")
print(f"  {len(choch_list):>12}  {N:>7}  {b1:>6.1f}%  {b2:>6.1f}%  {b3:>6.1f}%  {bstp:>5.1f}%")

# ── Por sesión ─────────────────────────────────────────────────────────────────
print(f"\n\n╔══ POR SESIÓN + HORAS ══════════════════════════════════════════════╗")
for sess in ["Asia","London","NY-AM","NY-PM","After"]:
    g = df_r[df_r["session"] == sess]
    if len(g) < 2: continue
    g1=g["hit_1R"].mean()*100; g2=g["hit_2R"].mean()*100
    g3=g["hit_3R"].mean()*100; gs=g["hit_stop"].mean()*100
    print(f"\n  ┌── {sess:<8} n={len(g):>3}  1R:{g1:>5.1f}%  2R:{g2:>5.1f}%  3R:{g3:>5.1f}%  Stop:{gs:>5.1f}%")
    for h in sorted(g["hour_utc"].unique()):
        hg = g[g["hour_utc"] == h]
        if len(hg) < 2: continue
        h2=hg["hit_2R"].mean()*100; h3=hg["hit_3R"].mean()*100; hs=hg["hit_stop"].mean()*100
        mk = " ★" if h2>=50 else (" ▼" if h2<25 else "")
        print(f"  │  {h:02d}:00  n={len(hg):>2}  2R:{h2:>5.1f}%  3R:{h3:>5.1f}%  Stop:{hs:>5.1f}%{mk}")

# ── Por día ────────────────────────────────────────────────────────────────────
print(f"\n\n╔══ POR DÍA ══════════════════════════════════════════════════════════╗\n")
dr = []
for d in ["Lun","Mar","Mie","Jue","Vie"]:
    g = df_r[df_r["day"]==d]
    if len(g)<2: continue
    dr.append({"Día":d,"n":len(g),"1R%":round(g["hit_1R"].mean()*100,1),
               "2R%":round(g["hit_2R"].mean()*100,1),"3R%":round(g["hit_3R"].mean()*100,1),
               "Stop%":round(g["hit_stop"].mean()*100,1)})
if dr: print(pd.DataFrame(dr).to_string(index=False))

# ── Filtros ────────────────────────────────────────────────────────────────────
print(f"\n\n╔══ FILTROS (base 2R = {b2:.1f}%) ══════════════════════════════════════╗\n")
filters = [
    ("Vela bajista en el rechazo",       df_r["is_bear_rej"]==1),
    ("Mecha larga hacia arriba",         df_r["long_wick_up"]==1),
    ("RSI < 40",                         df_r["rsi14"] < 40),
    ("RSI 40-55",                        df_r["rsi14"].between(40,55)),
    ("RSI > 55",                         df_r["rsi14"] > 55),
    ("Stop < 20 pts",                    df_r["r1_pts"] < 20),
    ("Stop >= 20 pts",                   df_r["r1_pts"] >= 20),
    ("CHoCH consec >= 5 barras",         df_r["choch_consec"] >= 5),
    ("Pullback rápido (<=10 barras)",    df_r["bars_to_pb"] <= 10),
    ("Pullback lento (>10 barras)",      df_r["bars_to_pb"] > 10),
    ("CHoCH cuerpo grande (>30 pts)",    df_r["choch_body"] > 30),
    ("ATR > 10 (volátil)",               df_r["atr14"] > 10),
]
rows = []
for label, mask in filters:
    s = df_r[mask]
    if len(s) < 3: continue
    wr = s["hit_2R"].mean()*100
    rows.append({"Filtro":label,"n":len(s),"2R%":round(wr,1),
                 "vs Base":f"{wr-b2:+.1f}%"})
fd = pd.DataFrame(rows).sort_values("2R%", ascending=False)
print(fd.to_string(index=False))

# ── Stats ──────────────────────────────────────────────────────────────────────
print(f"\n\n╔══ STATS DEL SETUP ══════════════════════════════════════════════════╗\n")
print(f"  CHoCH barras consec. bajo EMA — media : {df_r['choch_consec'].mean():.1f}")
print(f"  CHoCH cuerpo vela rompedora   — media : {df_r['choch_body'].mean():.1f} pts")
print(f"  CHoCH → retest (barras)       — media : {df_r['bars_to_pb'].mean():.1f}")
print(f"  R1 (stop) medio               — pts   : {df_r['r1_pts'].mean():.1f}")
print(f"  RSI en el retest              — media : {df_r['rsi14'].mean():.1f}")
print(f"  % vela bajista en el retest           : {df_r['is_bear_rej'].mean()*100:.1f}%")
print(f"  % mecha larga hacia arriba            : {df_r['long_wick_up'].mean()*100:.1f}%")
print("\n" + "═"*72 + "\n")
