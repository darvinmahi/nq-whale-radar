"""
backtest_fear_sell_days.py
==========================
Backtest con datos REALES (yfinance):
¿Qué tan fuertes fueron las ventas en NQ los días con VXN/VIX alto?

Metodología:
  - Descarga NQ (QQQ como proxy) + VIX + VXN últimos 12 meses
  - Clasifica días según nivel de miedo (VIX umbral)
  - Mide la magnitud del movimiento bajista
  - Muestra estadísticas y tabla de los peores días
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ─────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────
LOOKBACK_DAYS  = 365        # Últimos 12 meses
VIX_FEAR_LEVEL = 20         # VIX > 20 = Fear
VIX_XFEAR_LEVEL = 30        # VIX > 30 = Extreme Fear
NQ_TICKER      = "QQQ"      # Proxy liquid de NQ futures
VIX_TICKER     = "^VIX"
VXN_TICKER     = "^VXN"

# ─────────────────────────────────────────────
# 1. DESCARGA DE DATOS REALES
# ─────────────────────────────────────────────
print("="*65)
print("🐋 WHALE RADAR — Backtest Fear vs Sell Magnitude (Datos Reales)")
print("="*65)
print(f"\n📡 Descargando {LOOKBACK_DAYS} días de datos desde yfinance...")

end   = datetime.now()
start = end - timedelta(days=LOOKBACK_DAYS)

# Descargar en paralelo
raw = yf.download(
    [NQ_TICKER, VIX_TICKER, VXN_TICKER],
    start=start.strftime("%Y-%m-%d"),
    end=end.strftime("%Y-%m-%d"),
    interval="1d",
    auto_adjust=True,
    progress=False
)

# Aplanar columnas multi-nivel
close = raw["Close"].copy()
close.columns = ["NQ_close", "VIX_close", "VXN_close"]
open_ = raw["Open"].copy()
open_.columns = ["NQ_open", "VIX_open", "VXN_open"]
high_ = raw["High"].copy()
high_.columns = ["NQ_high", "VIX_high", "VXN_high"]
low_  = raw["Low"].copy()
low_.columns  = ["NQ_low", "VIX_low", "VXN_low"]

df = pd.concat([close, open_[["NQ_open"]], high_[["NQ_high"]], low_[["NQ_low"]]], axis=1)
df.dropna(inplace=True)

print(f"✅ {len(df)} sesiones cargadas ({df.index[0].date()} → {df.index[-1].date()})")
print(f"   NQ (QQQ): {df['NQ_close'].iloc[0]:.2f} → {df['NQ_close'].iloc[-1]:.2f}")
print(f"   VIX actual: {df['VIX_close'].iloc[-1]:.1f}")
print(f"   VXN actual: {df['VXN_close'].iloc[-1]:.1f}")

# ─────────────────────────────────────────────
# 2. CALCULAR MÉTRICAS DE CADA DÍA
# ─────────────────────────────────────────────
df["day_return_pct"] = (df["NQ_close"] - df["NQ_open"]) / df["NQ_open"] * 100
df["day_range_pct"]  = (df["NQ_high"] - df["NQ_low"])   / df["NQ_open"] * 100
df["close_prev"]     = df["NQ_close"].shift(1)
df["gap_pct"]        = (df["NQ_open"] - df["close_prev"]) / df["close_prev"] * 100
df["total_change_pct"]= (df["NQ_close"] - df["close_prev"]) / df["close_prev"] * 100

# Clasificar por nivel de VIX del día anterior (como señal predictiva)
df["VIX_prev"]       = df["VIX_close"].shift(1)
df["VXN_prev"]       = df["VXN_close"].shift(1)
df.dropna(inplace=True)

def classify_fear(vix):
    if vix >= VIX_XFEAR_LEVEL:
        return "EXTREME_FEAR (VIX≥30)"
    elif vix >= VIX_FEAR_LEVEL:
        return "FEAR (VIX 20-30)"
    elif vix >= 15:
        return "NEUTRAL (VIX 15-20)"
    else:
        return "GREED (VIX<15)"

df["fear_level"] = df["VIX_prev"].apply(classify_fear)

# Días de venta real (cierre < apertura)
df["es_bajista"] = df["day_return_pct"] < 0

# ─────────────────────────────────────────────
# 3. ESTADÍSTICAS POR NIVEL DE MIEDO
# ─────────────────────────────────────────────
print("\n" + "="*65)
print("📊 ESTADÍSTICAS: Fuerza de venta por nivel de VIX")
print("="*65)

order = ["EXTREME_FEAR (VIX≥30)", "FEAR (VIX 20-30)", "NEUTRAL (VIX 15-20)", "GREED (VIX<15)"]
emoji_map = {
    "EXTREME_FEAR (VIX≥30)": "🔴🔴",
    "FEAR (VIX 20-30)":      "🔴",
    "NEUTRAL (VIX 15-20)":   "🟡",
    "GREED (VIX<15)":        "🟢",
}

results = []
for level in order:
    subset = df[df["fear_level"] == level]
    if len(subset) == 0:
        continue
    
    bajistas = subset[subset["es_bajista"]]
    pct_bajista   = len(bajistas) / len(subset) * 100
    avg_drop      = bajistas["day_return_pct"].mean() if len(bajistas) > 0 else 0
    max_drop      = bajistas["day_return_pct"].min()  if len(bajistas) > 0 else 0
    avg_range     = subset["day_range_pct"].mean()
    avg_gap       = subset["gap_pct"].mean()
    
    em = emoji_map.get(level, "")
    print(f"\n{em} {level}")
    print(f"   Sesiones:         {len(subset):>4}")
    print(f"   Días bajistas:    {len(bajistas):>4}  ({pct_bajista:.0f}%)")
    print(f"   Caída promedio:   {avg_drop:>7.2f}%")
    print(f"   Peor caída:       {max_drop:>7.2f}%")
    print(f"   Rango prom día:   {avg_range:>7.2f}%")
    print(f"   Gap apertura:     {avg_gap:>7.2f}%")
    
    results.append({
        "level": level,
        "n": len(subset),
        "pct_bajista": pct_bajista,
        "avg_drop": avg_drop,
        "max_drop": max_drop,
        "avg_range": avg_range,
    })

# ─────────────────────────────────────────────
# 4. TOP 15 PEORES DÍAS (con VIX de ese día)
# ─────────────────────────────────────────────
print("\n" + "="*65)
print("💀 TOP 15 PEORES DÍAS DE VENTA — Últimos 12 meses")
print("="*65)
print(f"\n{'Fecha':<12} {'VIX ant':>8} {'VXN ant':>8} {'Gap%':>7} {'IntraDay%':>10} {'Total%':>8} {'Rango%':>8}")
print("-"*65)

worst = df[df["es_bajista"]].nsmallest(15, "total_change_pct")
for idx, row in worst.iterrows():
    date_str = idx.strftime("%Y-%m-%d")
    day_name = idx.strftime("%a")
    print(f"{date_str} {day_name}  "
          f"VIX:{row['VIX_prev']:>5.1f}  "
          f"VXN:{row['VXN_prev']:>5.1f}  "
          f"Gap:{row['gap_pct']:>+6.2f}%  "
          f"Intra:{row['day_return_pct']:>+7.2f}%  "
          f"Total:{row['total_change_pct']:>+7.2f}%")

# ─────────────────────────────────────────────
# 5. ANÁLISIS: ¿PREDICE EL VIX LA MAGNITUD?
# ─────────────────────────────────────────────
print("\n" + "="*65)
print("🔬 ¿MAYOR VIX = CAÍDA MÁS FUERTE?")
print("="*65)

# Solo días bajistas
solo_bajistas = df[df["es_bajista"]].copy()
corr_vix = solo_bajistas["VIX_prev"].corr(solo_bajistas["day_return_pct"])
corr_vxn = solo_bajistas["VXN_prev"].corr(solo_bajistas["day_return_pct"])

print(f"\n   Correlación VIX previo → caída del día: {corr_vix:.3f}")
print(f"   Correlación VXN previo → caída del día: {corr_vxn:.3f}")

if corr_vix < -0.15:
    print("   ✅ CONFIRMADO: VIX alto predice caídas MÁS fuertes")
elif -0.15 <= corr_vix <= 0.05:
    print("   ⚠️  DÉBIL: VIX alto tiene poca relación directa con magnitud")
else:
    print("   ❌ INVERSO: VIX alto coincide con rebotes (capitulación)")

# ─────────────────────────────────────────────
# 6. RESUMEN FINAL — PARA MAÑANA LUNES
# ─────────────────────────────────────────────
vix_hoy = df["VIX_close"].iloc[-1]
vxn_hoy = df["VXN_close"].iloc[-1]

print("\n" + "="*65)
print(f"🎯 APLICACIÓN MAÑANA — VIX actual: {vix_hoy:.1f} | VXN: {vxn_hoy:.1f}")
print("="*65)

# Buscar días históricos con VIX similar (±3 puntos)
vix_similar = df[
    (df["VIX_prev"] >= vix_hoy - 3) & 
    (df["VIX_prev"] <= vix_hoy + 3)
]

if len(vix_similar) > 0:
    pct_baj = len(vix_similar[vix_similar["es_bajista"]]) / len(vix_similar) * 100
    avg_drop_sim = vix_similar[vix_similar["es_bajista"]]["day_return_pct"].mean()
    avg_range_sim = vix_similar["day_range_pct"].mean()
    
    print(f"\n   Sesiones históricas con VIX {vix_hoy-3:.0f}–{vix_hoy+3:.0f}: {len(vix_similar)}")
    print(f"   % que cerraron BAJISTAS:   {pct_baj:.0f}%")
    print(f"   Caída promedio esos días:   {avg_drop_sim:.2f}%")
    print(f"   Rango promedio esos días:   {avg_range_sim:.2f}%")
    
    # Convertir a puntos NQ (QQQ ~$480 ≈ NQ/20)
    nq_price = df["NQ_close"].iloc[-1]
    avg_drop_pts  = abs(avg_drop_sim / 100 * nq_price * 20)
    avg_range_pts = avg_range_sim / 100 * nq_price * 20
    
    print(f"\n   En puntos NQ (aprox):")
    print(f"   Caída esperada si baja:  ~{avg_drop_pts:.0f} pts")
    print(f"   Rango esperado total:    ~{avg_range_pts:.0f} pts")

print(f"""
─────────────────────────────────────────────────────────────────
📋 CONCLUSIÓN PARA TU TRADING DEL LUNES:
─────────────────────────────────────────────────────────────────
   Con VIX {vix_hoy:.0f} el mercado históricamente tiene:
   → Mayor volatilidad intraday
   → Caídas más abruptas si el sesgo es bajista
   → Rebotes técnicos también más violentos (2 caras)
   
   RECOMENDACIÓN: Stops más anchos o tamaño reducido.
─────────────────────────────────────────────────────────────────
""")
