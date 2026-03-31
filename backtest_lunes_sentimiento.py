"""
backtest_lunes_sentimiento.py
==============================
Backtest REAL de LUNES en NQ (QQQ proxy):
¿El VIX/VXN del viernes previo predice si el lunes es BULLISH o BEARISH?
Datos: yfinance — últimos 12 meses
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
LOOKBACK = 365
NQ  = "QQQ"
VIX = "^VIX"
VXN = "^VXN"
# ─────────────────────────────────────────────

print("="*70)
print("🐋 WHALE RADAR — Backtest LUNES: Sentimiento vs Dirección (Datos Reales)")
print("="*70)

end   = datetime.now()
start = end - timedelta(days=LOOKBACK)

raw = yf.download([NQ, VIX, VXN],
                  start=start.strftime("%Y-%m-%d"),
                  end=end.strftime("%Y-%m-%d"),
                  interval="1d", auto_adjust=True, progress=False)

# Construir DataFrame limpio
df = pd.DataFrame({
    "NQ_open":  raw["Open"][NQ],
    "NQ_close": raw["Close"][NQ],
    "NQ_high":  raw["High"][NQ],
    "NQ_low":   raw["Low"][NQ],
    "VIX":      raw["Close"][VIX],
    "VXN":      raw["Close"][VXN],
})
df.dropna(inplace=True)
df.index = pd.to_datetime(df.index)

# Métricas del día
df["return_pct"]   = (df["NQ_close"] - df["NQ_open"]) / df["NQ_open"] * 100
df["range_pct"]    = (df["NQ_high"]  - df["NQ_low"])  / df["NQ_open"] * 100
df["prev_close"]   = df["NQ_close"].shift(1)
df["gap_pct"]      = (df["NQ_open"] - df["prev_close"]) / df["prev_close"] * 100
df["total_pct"]    = (df["NQ_close"] - df["prev_close"]) / df["prev_close"] * 100

# VIX/VXN del viernes anterior (señal predictiva)
df["VIX_prev"] = df["VIX"].shift(1)
df["VXN_prev"] = df["VXN"].shift(1)
df.dropna(inplace=True)

# Filtrar solo LUNES
lunes = df[df.index.dayofweek == 0].copy()  # 0 = Monday

def sesgo(r):
    if r > 0.15:   return "🟢 BULLISH"
    elif r < -0.15: return "🔴 BEARISH"
    else:           return "🟡 FLAT"

def vxn_zona(v):
    # VXN umbrales (siempre ~3-5pts más alto que VIX)
    if v >= 33:  return "🔴🔴 XFEAR"
    elif v >= 25: return "🔴 FEAR"
    elif v >= 18: return "🟡 NEUTRAL"
    else:         return "🟢 GREED"

lunes["resultado"]  = lunes["total_pct"].apply(sesgo)
lunes["vix_zona"]   = lunes["VXN_prev"].apply(vxn_zona)   # ← VXN, no VIX
lunes["es_bullish"] = lunes["total_pct"] > 0

print(f"\n📅 Total de LUNES analizados: {len(lunes)}")
print(f"   Período: {lunes.index[0].date()} → {lunes.index[-1].date()}\n")

# ─────────────────────────────────────────────
# TABLA COMPLETA DE LUNES (más recientes primero)
# ─────────────────────────────────────────────
print("─"*78)
print(f"{'Fecha':<13} {'Día':>3} {'VIX prev':>9} {'VXN prev':>9} {'Gap%':>7} {'Total%':>8} {'Rango%':>8}  Resultado")
print("─"*78)

for idx, row in lunes.sort_index(ascending=False).head(20).iterrows():
    date_str  = idx.strftime("%Y-%m-%d")
    week_num  = f"S{(idx.day-1)//7+1}"
    print(f"{date_str} {week_num}  "
          f"VIX:{row['VIX_prev']:>5.1f}  "
          f"VXN:{row['VXN_prev']:>5.1f}  "
          f"Gap:{row['gap_pct']:>+6.2f}%  "
          f"Total:{row['total_pct']:>+6.2f}%  "
          f"Rng:{row['range_pct']:>5.2f}%  "
          f"{row['resultado']}")

# ─────────────────────────────────────────────
# ESTADÍSTICAS POR ZONA VIX
# ─────────────────────────────────────────────
print("\n" + "="*70)
print("📊 LUNES: ¿Qué pasa según el VXN del viernes anterior? (Nasdaq Vol)")
print("="*70)

zonas = ["🔴🔴 XFEAR", "🔴 FEAR", "🟡 NEUTRAL", "🟢 GREED"]
for zona in zonas:
    sub = lunes[lunes["vix_zona"] == zona]
    if len(sub) == 0:
        continue
    bull  = sub[sub["es_bullish"]]
    bear  = sub[~sub["es_bullish"]]
    pct_b = len(bull) / len(sub) * 100
    avg_r = sub["total_pct"].mean()
    avg_bull = bull["total_pct"].mean() if len(bull) > 0 else 0
    avg_bear = bear["total_pct"].mean() if len(bear) > 0 else 0
    avg_rng  = sub["range_pct"].mean()

    print(f"\n{zona}  (VXN viernes previo)")
    print(f"  Lunes en muestra:   {len(sub):>3}")
    print(f"  % BULLISH:          {pct_b:>5.0f}%  ({len(bull)} días)")
    print(f"  % BEARISH:          {100-pct_b:>5.0f}%  ({len(bear)} días)")
    print(f"  Retorno promedio:   {avg_r:>+6.2f}%")
    print(f"  Avg subida bull:    {avg_bull:>+6.2f}%")
    print(f"  Avg caída bear:     {avg_bear:>+6.2f}%")
    print(f"  Rango prom día:     {avg_rng:>6.2f}%")

# ─────────────────────────────────────────────
# VIX ACTUAL → PROYECCIÓN LUNES
# ─────────────────────────────────────────────
vix_actual = df["VIX"].iloc[-1]
vxn_actual = df["VXN"].iloc[-1]
zona_actual = vxn_zona(vxn_actual)   # ← VXN, no VIX

print("\n" + "="*70)
print(f"🎯 VXN VIERNES (Nasdaq Vol): {vxn_actual:.1f} ({zona_actual})")
print(f"   VIX referencia S&P: {vix_actual:.1f}")
print("="*70)

# Lunes similares por VXN ±4
similares = lunes[
    (lunes["VXN_prev"] >= vxn_actual - 4) &
    (lunes["VXN_prev"] <= vxn_actual + 4)
]

if len(similares) > 0:
    pct_b_sim = len(similares[similares["es_bullish"]]) / len(similares) * 100
    avg_sim   = similares["total_pct"].mean()
    avg_rng_s = similares["range_pct"].mean()
    nq_price  = df["NQ_close"].iloc[-1]
    pts_move  = abs(avg_sim / 100 * nq_price * 20)
    pts_range = avg_rng_s / 100 * nq_price * 20

    print(f"\n  Lunes históricos con VXN {vxn_actual-4:.0f}–{vxn_actual+4:.0f}: {len(similares)}")
    print(f"  % cerraron BULLISH: {pct_b_sim:.0f}%")
    print(f"  % cerraron BEARISH: {100-pct_b_sim:.0f}%")
    print(f"  Retorno promedio:   {avg_sim:>+.2f}%")
    print(f"  Rango prom día:     {avg_rng_s:.2f}%")
    print(f"\n  En puntos NQ (aprox):")
    print(f"  Movimiento esperado: ~{pts_move:.0f} pts")
    print(f"  Rango total:         ~{pts_range:.0f} pts")

    print(f"""
┌──────────────────────────────────────────────────────────────────┐
│  VEREDICTO LUNES 30 MAR — con VXN {vxn_actual:.0f} (viernes previo)       │
│                                                                  │
│  Probabilidad BEARISH:  {100-pct_b_sim:.0f}%                                   │
│  Probabilidad BULLISH:  {pct_b_sim:.0f}%                                   │
│  Rango esperado NQ:     ~{pts_range:.0f} pts                              │
│  Movimiento neto prom:  ~{pts_move:.0f} pts                              │
│                                                                  │
│  ⚠️  Con VXN>33: volatilidad Nasdaq elevada en AMBAS direcciones │
│     Tamaño reducido + stops más amplios recomendado              │
└──────────────────────────────────────────────────────────────────┘
""")
