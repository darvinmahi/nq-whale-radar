"""
backtest_ema200_soporte_1m.py
══════════════════════════════════════════════════════════════════════
Estudio: EMA 200 como SOPORTE en NQ — 1 minuto

¿Qué analiza?
  - Detecta cuando el precio TOCA la EMA 200 desde arriba (retest)
  - Mide si el precio rebota: alcanza 1R, 2R, 3R sin romper el soporte
  - Registra indicadores en el momento exacto del toque:
      * RSI 14 (sobrevendido o momentum?)
      * Volumen relativo (vela excepcional o normal?)
      * Vela del toque (martillo, doji, cierre alcista?)
      * Distancia del precio al VWAP
      * Pendiente de la EMA (plana/subiendo = más fuerte)
      * Hora y sesión

Stop: cierre por debajo de la EMA 200 por más de 5 puntos
Target: 1R = distancia del high de la vela al low del toque
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timezone

# ─── Config ────────────────────────────────────────────────────────────────────
SYMBOL      = "NQ=F"
MIN_TOUCH   = 3     # el precio debe bajar dentro de X puntos de la EMA
MAX_BARS    = 45    # barras máximo para buscar target
R_TARGETS   = [1, 2, 3]

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

# ─── Indicadores ───────────────────────────────────────────────────────────────
def rsi(series, period=14):
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def vwap(df):
    """VWAP simple del día completo"""
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    cum_vol    = df.groupby(df.index.date)["Volume"].cumsum()
    cum_tpvol  = (tp * df["Volume"]).groupby(df.index.date).cumsum()
    return cum_tpvol / cum_vol

def vol_ratio(volume, window=20):
    """Volumen de la vela vs promedio móvil"""
    avg = volume.rolling(window).mean()
    return (volume / avg.replace(0, np.nan)).round(2)

def ema_slope(ema, bars=5):
    """Pendiente de la EMA en puntos por barra"""
    return ema.diff(bars) / bars

# ─── Descarga ──────────────────────────────────────────────────────────────────
print("\n" + "═"*68)
print("  NQ EMA 200 SOPORTE 1m — Backtest + Indicadores")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("═"*68)

print("\n  Descargando 1m (7 días)...", end="", flush=True)
_raw = yf.download(SYMBOL, interval="1m", period="7d",
                   progress=False, auto_adjust=True)

if _raw.empty:
    print(" sin datos"); exit(1)

# ── Fix definitivo: aplanar MultiIndex de yfinance ──────────────────────────
# yfinance v0.2+ devuelve MultiIndex (Price, Ticker) — extraemos columnas como arrays
def _col(name):
    """Extrae columna del DataFrame crudo como array numpy 1D"""
    c = _raw[name]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]      # tomar primer ticker si hay MultiIndex
    return c.values.astype(float)

# Reconstruir DataFrame limpio con columnas planas
df = pd.DataFrame({
    "Open":   _col("Open"),
    "High":   _col("High"),
    "Low":    _col("Low"),
    "Close":  _col("Close"),
    "Volume": _col("Volume"),
}, index=_raw.index)

print(f" {len(df)} velas\n")

# ─── Calcular indicadores ──────────────────────────────────────────────────────
df["ema200"]   = df["Close"].ewm(span=200, adjust=False).mean()
df["rsi14"]    = rsi(df["Close"], 14)
df["vol_rat"]  = vol_ratio(df["Volume"], 20)
df["ema_slp"]  = ema_slope(df["ema200"], 5)
df["above_ema"]= (df["Close"] > df["ema200"]).astype(int)

# VWAP (requiere index con fecha)
try:
    df["vwap"] = vwap(df)
    df["above_vwap"] = (df["Close"] > df["vwap"]).astype(int)
    has_vwap = True
except Exception:
    has_vwap = False

# ─── Detectar retests ─────────────────────────────────────────────────────────
#  Retest válido:
#   - La vela TOCA la EMA200 (Low dentro de MIN_TOUCH puntos) 
#   - El precio venía desde ARRIBA (close anterior > EMA)
#   - El cierre de la vela del toque está POR ENCIMA de la EMA (no rompió)

records = []

for i in range(20, len(df) - MAX_BARS - 2):
    row     = df.iloc[i]
    prev    = df.iloc[i-1]
    ema_val = float(row["ema200"])

    # 1. El price venía desde arriba
    if float(prev["Close"]) <= float(prev["ema200"]):
        continue

    # 2. El low toca la EMA (dentro de MIN_TOUCH puntos)
    lo = float(row["Low"])
    if lo > ema_val + MIN_TOUCH:
        continue               # no llegó a la EMA
    if lo < ema_val - MIN_TOUCH * 4:
        continue               # perforó demasiado

    # 3. El cierre está por encima de la EMA (vela cerró como soporte)
    if float(row["Close"]) <= ema_val:
        continue

    # ── Variables del momento del toque ──────────────────────────────────────
    touch_close  = float(row["Close"])
    touch_low    = lo
    touch_high   = float(row["High"])
    stop_price   = touch_low - 5            # stop = 5 pts bajo el low del toque
    r1_dist      = touch_close - stop_price # 1R = distancia entry→stop

    if r1_dist < 5:
        continue   # stop demasiado chico, ruido

    hour     = row.name.hour if hasattr(row.name, 'hour') else 0
    sess     = session_label(hour)
    rsi_val  = round(float(row["rsi14"]), 1) if not pd.isna(row["rsi14"]) else None
    vol_r    = round(float(row["vol_rat"]), 2) if not pd.isna(row["vol_rat"]) else None
    slp      = round(float(row["ema_slp"]), 2) if not pd.isna(row["ema_slp"]) else None
    above_vw = int(row["above_vwap"]) if has_vwap and not pd.isna(row["above_vwap"]) else None

    # ── Tipo de vela ─────────────────────────────────────────────────────────
    body    = abs(touch_close - float(row["Open"]))
    candle_range = touch_high - touch_low
    is_bull = int(touch_close > float(row["Open"]))
    is_hammer = int(
        (touch_close - touch_low) > 0.6 * candle_range and body < 0.4 * candle_range
    )

    # ── Medir R en barras futuras ─────────────────────────────────────────────
    future  = df.iloc[i+1 : i+MAX_BARS+1]
    f_hi    = future["High"].values.astype(float)
    f_lo    = future["Low"].values.astype(float)
    f_cl    = future["Close"].values.astype(float)
    f_ema   = future["ema200"].values.astype(float)

    hit_stop = False
    r_hit    = {r: False for r in R_TARGETS}

    for bi in range(len(f_hi)):
        # Stop: close bajo EMA250 o lo < stop_price
        if f_lo[bi] <= stop_price:
            hit_stop = True; break
        if f_cl[bi] < f_ema[bi] - 10:
            hit_stop = True; break

        for r in R_TARGETS:
            target = touch_close + r * r1_dist
            if not r_hit[r] and f_hi[bi] >= target:
                r_hit[r] = True

        if all(r_hit.values()):
            break

    records.append({
        "session":   sess,
        "hour_utc":  hour,
        "rsi14":     rsi_val,
        "vol_ratio": vol_r,
        "ema_slope": slp,
        "above_vwap":above_vw,
        "is_bull_candle": is_bull,
        "is_hammer": is_hammer,
        "r1_pts":    round(r1_dist, 1),
        "hit_stop":  int(hit_stop),
        **{f"hit_{r}R": int(r_hit[r]) for r in R_TARGETS},
    })

df_res = pd.DataFrame(records)
print(f"  Retests detectados: {len(df_res)}")

if len(df_res) < 3:
    print("  Muy pocos retests con datos de 7 días. Ampliando criterios...")
    exit(1)

# ═══ 1. RESUMEN GENERAL ═══════════════════════════════════════════════════════
print("\n╔══ 1. WIN RATE GENERAL ════════════════════════════════════════════╗\n")
g = df_res
row = {"Retests": len(g), "Stop%": round(g["hit_stop"].mean()*100,1)}
for r in R_TARGETS:
    row[f"{r}R Win%"] = round(g[f"hit_{r}R"].mean()*100, 1)
print(pd.DataFrame([row]).to_string(index=False))

# ═══ 2. POR SESIÓN ════════════════════════════════════════════════════════════
print("\n\n╔══ 2. WIN RATE POR SESIÓN ══════════════════════════════════════════╗\n")
sess_rows = []
for sess in ["Asia","London","NY-AM","NY-PM","After"]:
    s = df_res[df_res["session"] == sess]
    if len(s) < 2: continue
    r = {"Sesión": sess, "Retests": len(s), "Stop%": round(s["hit_stop"].mean()*100,1)}
    for rv in R_TARGETS:
        r[f"{rv}R%"] = round(s[f"hit_{rv}R"].mean()*100,1)
    sess_rows.append(r)
if sess_rows:
    df_sess = pd.DataFrame(sess_rows).sort_values("2R%", ascending=False)
    print(df_sess.to_string(index=False))

# ═══ 3. POR HORA ══════════════════════════════════════════════════════════════
print("\n\n╔══ 3. WIN RATE 2R POR HORA UTC ═════════════════════════════════════╗\n")
hour_rows = []
for h in sorted(df_res["hour_utc"].unique()):
    hd = df_res[df_res["hour_utc"] == h]
    if len(hd) < 2: continue
    hour_rows.append({
        "HoraUTC": h,
        "Sesión":  session_label(h),
        "Retests": len(hd),
        "2R Win%": round(hd["hit_2R"].mean()*100,1),
        "3R Win%": round(hd["hit_3R"].mean()*100,1),
        "Stop%":   round(hd["hit_stop"].mean()*100,1),
    })
if hour_rows:
    df_h = pd.DataFrame(hour_rows).sort_values("2R Win%", ascending=False)
    print(df_h.to_string(index=False))

# ═══ 4. INDICADORES — ¿Cuáles coinciden con los trades ganadores? ══════════
print("\n\n╔══ 4. INDICADORES EN RETESTS GANADORES (2R) vs PERDEDORES ═══════════╗\n")
winners = df_res[df_res["hit_2R"] == 1]
losers  = df_res[df_res["hit_2R"] == 0]

cols_ind = ["rsi14","vol_ratio","ema_slope","is_bull_candle","is_hammer","above_vwap","r1_pts"]
comp = pd.DataFrame({
    "Indicador": cols_ind,
    "Winners (2R)": [round(winners[c].mean(), 2) if c in winners.columns else "N/A" for c in cols_ind],
    "Losers":       [round(losers[c].mean(),  2) if c in losers.columns  else "N/A" for c in cols_ind],
})
print(comp.to_string(index=False))

# ═══ 5. FILTRO: CON QUÉ COMBINACIÓN EL WIN % SUBE ════════════════════════════
print("\n\n╔══ 5. FILTROS QUE MEJORAN EL WIN RATE (2R) ══════════════════════════╗\n")
filters = [
    ("RSI < 40 (sobrevendido)",          df_res["rsi14"]         < 40),
    ("RSI 40-60 (neutral momentum)",      df_res["rsi14"].between(40,60)),
    ("Vol alto (>1.3x promedio)",         df_res["vol_ratio"]     > 1.3),
    ("EMA subiendo (slope > 0)",          df_res["ema_slope"]     > 0),
    ("Vela alcista en toque",             df_res["is_bull_candle"]== 1),
    ("Martillo en el toque",              df_res["is_hammer"]     == 1),
    ("Precio sobre VWAP",                 df_res["above_vwap"]    == 1),
    ("Stop > 15 pts (R gordo)",           df_res["r1_pts"]        > 15),
]

filt_rows = []
base_wr = df_res["hit_2R"].mean() * 100
for label, mask in filters:
    sub = df_res[mask]
    if len(sub) < 2: continue
    wr = sub["hit_2R"].mean() * 100
    filt_rows.append({
        "Filtro":    label,
        "Muestras":  len(sub),
        "2R Win%":   round(wr, 1),
        "vs Base":   f"{wr - base_wr:+.1f}%",
    })
print(f"  Base (sin filtros): {round(base_wr,1)}% con {len(df_res)} muestras\n")
fdf = pd.DataFrame(filt_rows).sort_values("2R Win%", ascending=False)
print(fdf.to_string(index=False))

print("\n" + "═"*68 + "\n")
