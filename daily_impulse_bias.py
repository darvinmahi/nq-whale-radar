"""
Daily IMPULSE BIAS — NQ Futures
Métrica: desde el NY open (09:30), ¿cuánto sube vs cuánto baja?
  up_pts   = day_high  - ny_open
  down_pts = ny_open   - day_low
  Si up_pts > down_pts → BULLISH (el impulso más largo fue arriba)
  Si down_pts > up_pts → BEARISH (el impulso más largo fue abajo)
Usa datos 15min intraday reales.
"""
import pandas as pd
import numpy as np
import os
from datetime import timedelta
from collections import defaultdict

CSV = "data/research/nq_15m_intraday.csv"
if not os.path.exists(CSV):
    print("❌ No se encontró:", CSV)
    exit()

# ─── Cargar datos ─────────────────────────────────────────────────────────────
df = pd.read_csv(CSV, skiprows=2)
df.columns = ['Datetime','Close','High','Low','Open']
df = df.dropna(subset=['Datetime'])
df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
df.set_index('Datetime', inplace=True)
df.index = df.index.tz_convert('America/New_York')
df = df.sort_index()

end_date   = df.index.max()
start_date = end_date - timedelta(days=180)   # 6 meses (igual que tu backtest)
df_w  = df.loc[start_date:]
days  = df_w.index.normalize().unique()

DAYS_ES = {0:"LUNES", 1:"MARTES", 2:"MIÉRCOLES", 3:"JUEVES", 4:"VIERNES"}

print(f"\n  Período: {start_date.date()} → {end_date.date()}")
print(f"  Total días: {len(days)}\n")

by_day = defaultdict(list)

for day in days:
    wd = day.weekday()
    if wd > 4: continue

    open_ts = day.replace(hour=9,  minute=30)
    clos_ts = day.replace(hour=16, minute=0)

    ny = df_w.loc[open_ts:clos_ts]
    if ny.empty or len(ny) < 3: continue

    ny_open  = float(ny.iloc[0]['Open'])
    day_high = float(ny['High'].max())
    day_low  = float(ny['Low'].min())

    up_pts   = day_high  - ny_open   # impulso alcista máximo
    down_pts = ny_open   - day_low   # impulso bajista máximo

    # Dirección = impulso más largo
    if up_pts > down_pts:
        impulse_dir = "BULLISH"
    elif down_pts > up_pts:
        impulse_dir = "BEARISH"
    else:
        impulse_dir = "NEUTRAL"

    by_day[wd].append({
        "date":        day.strftime('%Y-%m-%d'),
        "up_pts":      round(up_pts, 1),
        "down_pts":    round(down_pts, 1),
        "ratio":       round(up_pts / down_pts, 2) if down_pts else 999,
        "impulse_dir": impulse_dir,
    })

# ─── Reporte ──────────────────────────────────────────────────────────────────
print("═" * 72)
print("  📊 IMPULSO DOMINANTE POR DÍA  (6 meses · NQ 15min · desde NY open)")
print("=" * 72)
print(f"  {'DÍA':<13} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'AvgUP':>7}  {'AvgDN':>7}  {'RATIO':>6}  SESGO")
print("  " + "─"*68)

summary = {}
for wd in range(5):
    recs  = by_day[wd]
    if not recs: continue
    n     = len(recs)
    name  = DAYS_ES[wd]

    bulls    = [r for r in recs if r['impulse_dir']=="BULLISH"]
    bears    = [r for r in recs if r['impulse_dir']=="BEARISH"]
    bull_pct = len(bulls)/n*100
    bear_pct = len(bears)/n*100

    avg_up   = np.mean([r['up_pts']   for r in recs])
    avg_dn   = np.mean([r['down_pts'] for r in recs])
    ratio    = avg_up / avg_dn if avg_dn else 999   # >1 = más alcista

    if bull_pct >= 60:
        sesgo = "🟢 BULLISH"
    elif bear_pct >= 60:
        sesgo = "🔴 BEARISH"
    elif bull_pct >= 53:
        sesgo = "🟡 BULL LEVE"
    elif bear_pct >= 53:
        sesgo = "🟠 BEAR LEVE"
    else:
        sesgo = "⚪ NEUTRO"

    print(f"  {name:<13} {n:>3}  {bull_pct:>5.1f}%  {bear_pct:>5.1f}%  "
          f"{avg_up:>6.0f}p  {avg_dn:>6.0f}p  {ratio:>6.2f}x  {sesgo}")
    summary[name] = {"bull_pct": bull_pct, "avg_up": avg_up, "avg_dn": avg_dn, "ratio": ratio}

print()
print("  RATIO > 1.0 = mayor impulso alcista que bajista desde NY open")
print()

# ─── Tabla detallada por día ──────────────────────────────────────────────────
for wd in range(5):
    recs = by_day[wd]
    if not recs: continue
    name = DAYS_ES[wd]
    bulls = sum(1 for r in recs if r['impulse_dir']=="BULLISH")
    print(f"  {name}: {bulls}/{len(recs)} días BULL  "
          f"| UP avg {np.mean([r['up_pts'] for r in recs]):.0f}p  "
          f"| DN avg {np.mean([r['down_pts'] for r in recs]):.0f}p  "
          f"| Ratio {np.mean([r['up_pts'] for r in recs])/np.mean([r['down_pts'] for r in recs]):.2f}x")

print()
print("  ─── ADAPTACIÓN DE ESTRATEGIA ───")
for name, s in summary.items():
    r = s['ratio']
    if r >= 1.15:
        tip = f"→ Buscar LONGS desde VAL/POC. Ride de {s['avg_up']:.0f}p avg."
    elif r <= 0.85:
        tip = f"→ Buscar SHORTS desde VAH/POC. Ride de {s['avg_dn']:.0f}p avg."
    else:
        tip = f"→ Ambos lados válidos. UP={s['avg_up']:.0f}p / DN={s['avg_dn']:.0f}p"
    print(f"  {name:<13} ratio={r:.2f}  {tip}")
