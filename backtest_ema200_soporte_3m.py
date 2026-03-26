"""
backtest_ema200_soporte_3m.py
══════════════════════════════════════════════════════════════════════
EMA 200 como SOPORTE en 1m — 3 MESES de datos
Descarga 1m en chunks de 6 días (límite yfinance) para cubrir ~90 días.
Muestra WIN RATE COHERENTE: sesión → horas dentro de cada sesión.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# ─── Config ────────────────────────────────────────────────────────────────────
SYMBOL      = "NQ=F"
MIN_TOUCH   = 4      # puntos máx que el LOW puede alejarse de la EMA
MAX_BARS    = 45     # barras para buscar target
R_TARGETS   = [1, 2, 3]
DAYS_BACK   = 90     # meses de historia

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

# ─── Descarga en chunks ────────────────────────────────────────────────────────
def download_1m_extended(symbol, days_back=90):
    """yfinance da máx 7 días de 1m — descargamos chunks de 6 días."""
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=days_back)
    chunks = []
    cur = start

    print(f"\n  Descargando {days_back} días de datos 1m en chunks...", flush=True)
    while cur < end:
        chunk_end = min(cur + timedelta(days=6), end)
        try:
            raw = yf.download(
                symbol,
                start=cur.strftime("%Y-%m-%d"),
                end=chunk_end.strftime("%Y-%m-%d"),
                interval="1m",
                progress=False,
                auto_adjust=True,
            )
            if not raw.empty:
                def _col(n, r=raw):
                    c = r[n]
                    if isinstance(c, pd.DataFrame): c = c.iloc[:, 0]
                    return c.values.astype(float)
                chunk_df = pd.DataFrame({
                    "Open": _col("Open"), "High": _col("High"),
                    "Low":  _col("Low"),  "Close": _col("Close"),
                    "Volume": _col("Volume"),
                }, index=raw.index)
                chunks.append(chunk_df)
                print(f"    {cur.date()} → {chunk_end.date()} : {len(chunk_df)} velas")
        except Exception as e:
            print(f"    {cur.date()} → error: {e}")
        cur = chunk_end + timedelta(minutes=1)

    if not chunks:
        return pd.DataFrame()
    df = pd.concat(chunks).sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df

# ─── Indicadores ──────────────────────────────────────────────────────────────
def calc_rsi(series, p=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(p).mean()
    loss  = (-delta.clip(upper=0)).rolling(p).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def calc_vwap(df):
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    dates = df.index.date
    cum_tpvol = pd.Series(0.0, index=df.index)
    cum_vol   = pd.Series(0.0, index=df.index)
    for d in pd.unique(dates):
        mask = dates == d
        tv = (tp[mask] * df["Volume"][mask]).cumsum()
        cv = df["Volume"][mask].cumsum()
        cum_tpvol[mask] = tv.values
        cum_vol[mask]   = cv.values
    return cum_tpvol / cum_vol.replace(0, np.nan)

# ─── Main ──────────────────────────────────────────────────────────────────────
print("\n" + "═"*70)
print("  NQ — EMA 200 SOPORTE 1m | BACKTEST 3 MESES")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("═"*70)

df = download_1m_extended(SYMBOL, DAYS_BACK)

if df.empty:
    print("\n  Sin datos."); exit(1)

print(f"\n  Total: {len(df)} velas  ({df.index[0].date()} → {df.index[-1].date()})\n")

# Calcular indicadores
df["ema200"]   = df["Close"].ewm(span=200, adjust=False).mean()
df["rsi14"]    = calc_rsi(df["Close"], 14)
df["ema_slp"]  = df["ema200"].diff(5) / 5
try:
    df["vwap"]     = calc_vwap(df)
    df["abv_vwap"] = (df["Close"] > df["vwap"]).astype(int)
except:
    df["abv_vwap"] = 0

# ─── Detección de retests ─────────────────────────────────────────────────────
records = []
close = df["Close"].values
high  = df["High"].values
low   = df["Low"].values
ema   = df["ema200"].values
rsi_  = df["rsi14"].values
slp_  = df["ema_slp"].values
avwp  = df["abv_vwap"].values
vol_  = df["Volume"].values
open_ = df["Open"].values
idx   = df.index

# rolling vol average
vol_avg = df["Volume"].rolling(20).mean().values

for i in range(210, len(df) - MAX_BARS - 2):
    # Vela anterior estaba sobre la EMA
    if close[i-1] <= ema[i-1]:
        continue

    # Low del toque llega a la EMA
    lo = low[i]
    ema_v = ema[i]
    if lo > ema_v + MIN_TOUCH:
        continue
    if lo < ema_v - MIN_TOUCH * 5:
        continue

    # Cierra POR ENCIMA de la EMA (el soporte aguantó en el cierre)
    if close[i] <= ema_v:
        continue

    # Stop y 1R
    stop_price = lo - 6
    r1_dist    = close[i] - stop_price
    if r1_dist < 8:
        continue

    hour = idx[i].hour
    sess = session_label(hour)
    dow  = idx[i].weekday()  # 0=lun … 4=vier
    day_names = ["Lun","Mar","Mie","Jue","Vie","Sab","Dom"]
    day = day_names[dow]

    rsi_v = round(float(rsi_[i]), 1) if not np.isnan(rsi_[i]) else 50.0
    slp_v = round(float(slp_[i]), 2) if not np.isnan(slp_[i]) else 0.0
    avw_v = int(avwp[i])
    vol_r  = round(vol_[i] / vol_avg[i], 2) if vol_avg[i] > 0 else 1.0
    is_bull = int(close[i] > open_[i])
    body    = abs(close[i] - open_[i])
    rng     = high[i] - lo
    is_hmr  = int(rng > 0 and (close[i] - lo) > 0.55*rng and body < 0.35*rng)

    # Buscar targets
    f_hi  = high[i+1 : i+MAX_BARS+1]
    f_lo  = low[i+1  : i+MAX_BARS+1]
    f_cl  = close[i+1 : i+MAX_BARS+1]
    f_ema = ema[i+1   : i+MAX_BARS+1]

    hit_stop = False
    r_hit    = {r: False for r in R_TARGETS}

    for bi in range(len(f_hi)):
        if f_lo[bi] <= stop_price or f_cl[bi] < f_ema[bi] - 12:
            hit_stop = True; break
        for r in R_TARGETS:
            target = close[i] + r * r1_dist
            if not r_hit[r] and f_hi[bi] >= target:
                r_hit[r] = True
        if all(r_hit.values()):
            break

    records.append({
        "session": sess, "hour_utc": hour, "day": day,
        "rsi14": rsi_v, "ema_slope": slp_v,
        "above_vwap": avw_v, "vol_ratio": vol_r,
        "is_bull": is_bull, "is_hammer": is_hmr,
        "r1_pts": round(r1_dist, 1),
        "hit_stop": int(hit_stop),
        **{f"hit_{r}R": int(r_hit[r]) for r in R_TARGETS},
    })

df_res = pd.DataFrame(records)
N = len(df_res)
print(f"  Retests detectados: {N}")

if N < 10:
    print("  Muy pocos retests."); exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN A: SESIÓN + HORAS DENTRO DE CADA SESIÓN  (coherente)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n╔══ A. WIN RATE POR SESIÓN ── + ── HORAS DENTRO DE CADA SESIÓN ══════╗")
sess_order = ["Asia","London","NY-AM","NY-PM","After"]

for sess in sess_order:
    g = df_res[df_res["session"] == sess]
    if len(g) < 3: continue
    wr2  = round(g["hit_2R"].mean()*100, 1)
    wr3  = round(g["hit_3R"].mean()*100, 1)
    wr1  = round(g["hit_1R"].mean()*100, 1)
    stp  = round(g["hit_stop"].mean()*100, 1)
    print(f"\n  ┌── {sess.upper():<8}  Retests:{len(g):>4}  "
          f"1R:{wr1:>5.1f}%  2R:{wr2:>5.1f}%  3R:{wr3:>5.1f}%  Stop:{stp:>5.1f}%")

    # horas dentro de esta sesión
    hour_rows = []
    for h in sorted(g["hour_utc"].unique()):
        hg = g[g["hour_utc"] == h]
        if len(hg) < 3: continue
        hour_rows.append({
            "Hora UTC": f"{h:02d}:00",
            "Retests":  len(hg),
            "1R%":  round(hg["hit_1R"].mean()*100, 1),
            "2R%":  round(hg["hit_2R"].mean()*100, 1),
            "3R%":  round(hg["hit_3R"].mean()*100, 1),
            "Stop%":round(hg["hit_stop"].mean()*100, 1),
        })
    if hour_rows:
        df_h = pd.DataFrame(hour_rows).sort_values("2R%", ascending=False)
        for _, row in df_h.iterrows():
            marker = " ★" if row["2R%"] >= 50 else ("  " if row["2R%"] >= 35 else " ▼")
            print(f"  │  {row['Hora UTC']}  n={row['Retests']:>3}  "
                  f"1R:{row['1R%']:>5.1f}%  2R:{row['2R%']:>5.1f}%  "
                  f"3R:{row['3R%']:>5.1f}%  Stop:{row['Stop%']:>5.1f}%{marker}")

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN B: WIN RATE POR DÍA DE LA SEMANA
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n╔══ B. WIN RATE POR DÍA DE LA SEMANA (2R) ═══════════════════════════╗\n")
day_order_idx = ["Lun","Mar","Mie","Jue","Vie"]
day_rows = []
for d in day_order_idx:
    g = df_res[df_res["day"] == d]
    if len(g) < 3: continue
    day_rows.append({
        "Día": d, "Retests": len(g),
        "1R%": round(g["hit_1R"].mean()*100,1),
        "2R%": round(g["hit_2R"].mean()*100,1),
        "3R%": round(g["hit_3R"].mean()*100,1),
        "Stop%": round(g["hit_stop"].mean()*100,1),
    })
if day_rows:
    print(pd.DataFrame(day_rows).to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN C: FILTROS DE INDICADORES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n╔══ C. FILTROS — cuál sube el win rate 2R ════════════════════════════╗\n")
base = df_res["hit_2R"].mean()*100
filters = [
    ("RSI < 40 (sobrevendido)",     df_res["rsi14"]      < 40),
    ("RSI 40-55 (momentum saludable)", df_res["rsi14"].between(40,55)),
    ("RSI > 55 (sobrecomprado)",    df_res["rsi14"]      > 55),
    ("EMA subiendo (slope>0)",      df_res["ema_slope"]  > 0),
    ("EMA plana/bajando",           df_res["ema_slope"] <= 0),
    ("Precio sobre VWAP",           df_res["above_vwap"] == 1),
    ("Precio bajo VWAP",            df_res["above_vwap"] == 0),
    ("Vol alto (>1.5x)",            df_res["vol_ratio"]  > 1.5),
    ("Vol normal (<1.5x)",          df_res["vol_ratio"] <= 1.5),
    ("Vela alcista en toque",       df_res["is_bull"]   == 1),
    ("Vela bajista en toque",       df_res["is_bull"]   == 0),
    ("Martillo",                    df_res["is_hammer"] == 1),
    ("Stop chico (<15 pts)",        df_res["r1_pts"]     < 15),
    ("Stop grande (>15 pts)",       df_res["r1_pts"]    >= 15),
]
print(f"  BASE SIN FILTROS: {round(base,1)}%  (n={N})\n")
frows = []
for label, mask in filters:
    s = df_res[mask]
    if len(s) < 5: continue
    wr = s["hit_2R"].mean()*100
    frows.append({"Filtro": label, "n": len(s),
                  "2R Win%": round(wr,1), "vs Base": f"{wr-base:+.1f}%"})
fd = pd.DataFrame(frows).sort_values("2R Win%", ascending=False)
print(fd.to_string(index=False))

# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN D: TOP COMBINACIONES SESIÓN + FILTRO
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n╔══ D. TOP COMBINACIONES: SESIÓN + MEJOR FILTRO ════════════════════╗\n")
combos = []
best_filter_mask = df_res["rsi14"].between(40,55)  # usar el filtro que más ayuda
for sess in sess_order:
    g = df_res[(df_res["session"] == sess) & best_filter_mask]
    if len(g) < 3: continue
    combos.append({
        "Sesión + RSI 40-55": sess,
        "n": len(g),
        "2R Win%": round(g["hit_2R"].mean()*100,1),
        "3R Win%": round(g["hit_3R"].mean()*100,1),
        "Stop%":   round(g["hit_stop"].mean()*100,1),
    })
cd = pd.DataFrame(combos).sort_values("2R Win%", ascending=False)
print(cd.to_string(index=False))

print("\n" + "═"*70 + "\n")
