"""
PREGUNTA SIMPLE:
¿El NQ de 11AM a 4PM (Close) sube o baja?
¿Cuántos puntos mueve?
¿Qué día de la semana es más predecible?
"""

import yfinance as yf
import pandas as pd
import numpy as np

print("█"*60)
print("  NQ — ¿Qué hace de 11 AM a 4 PM?")
print("  60 días | 15 minutos")
print("█"*60)

# Descargar
df = yf.download("NQ=F", period="60d", interval="15m", progress=False)
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
if df.index.tz is None:
    df.index = df.index.tz_localize("UTC")
df.index = df.index.tz_convert("America/New_York")
df["hour"]    = df.index.hour
df["date"]    = df.index.normalize()
df["weekday"] = df.index.dayofweek

DIAS = {0:"LUNES", 1:"MARTES", 2:"MIÉRCOLES", 3:"JUEVES", 4:"VIERNES"}

days = sorted(df["date"].unique())

registros = []

for day in days:
    wd = pd.Timestamp(day).weekday()
    if wd > 4: continue

    d = df[df["date"] == day]

    # PM: 11:00 → 15:59
    pm = d[(d["hour"] >= 11) & (d["hour"] <= 15)]
    if len(pm) < 4: continue

    pm_open  = float(pm.iloc[0]["Open"])
    pm_close = float(pm.iloc[-1]["Close"])
    pm_hi    = float(pm["High"].max())
    pm_lo    = float(pm["Low"].min())
    pm_move  = pm_close - pm_open          # positivo = sube, negativo = baja
    pm_range = pm_hi - pm_lo              # cuanto se mueve en total

    # ¿Subió o bajó?
    if pm_move > 20:
        direccion = "SUBE"
    elif pm_move < -20:
        direccion = "BAJA"
    else:
        direccion = "FLAT"

    # ¿Máximo primero o mínimo primero?
    # ¿La barra del máximo llega antes que la del mínimo?
    idx_hi = pm["High"].idxmax()
    idx_lo = pm["Low"].idxmin()
    hi_first = idx_hi < idx_lo

    registros.append({
        "date":      str(day.date()),
        "weekday":   DIAS[wd],
        "wd_num":    wd,
        "pm_open":   round(pm_open, 0),
        "pm_close":  round(pm_close, 0),
        "pm_move":   round(pm_move, 0),
        "pm_range":  round(pm_range, 0),
        "direccion": direccion,
        "hi_first":  hi_first,
    })

print(f"\n  {len(registros)} días analizados\n")

# ══════════════════════════════════════════
#  RESUMEN GLOBAL
# ══════════════════════════════════════════
n     = len(registros)
sube  = sum(1 for r in registros if r["direccion"] == "SUBE")
baja  = sum(1 for r in registros if r["direccion"] == "BAJA")
flat  = sum(1 for r in registros if r["direccion"] == "FLAT")
moves = [r["pm_move"]  for r in registros]
rngs  = [r["pm_range"] for r in registros]

print("  GLOBAL (todos los días)")
print("  " + "─"*50)
print(f"  SUBE  : {sube:>3}/{n} = {sube/n*100:.0f}%  {'▲'*(sube*20//n)}")
print(f"  BAJA  : {baja:>3}/{n} = {baja/n*100:.0f}%  {'▼'*(baja*20//n)}")
print(f"  FLAT  : {flat:>3}/{n} = {flat/n*100:.0f}%")
print(f"\n  Movimiento promedio : {np.mean(moves):+.0f} pts")
print(f"  Rango promedio      : {np.mean(rngs):.0f} pts (de mínimo a máximo)")
print(f"  Mejor día (más pts) : {max(moves):+.0f} pts")
print(f"  Peor día            : {min(moves):+.0f} pts")

# ══════════════════════════════════════════
#  POR DÍA DE SEMANA
# ══════════════════════════════════════════
print("\n\n  POR DÍA DE SEMANA")
print("  " + "─"*50)
print(f"  {'DÍA':<14} {'N':>3}  {'SUBE':>6}  {'BAJA':>6}  {'FLAT':>5}  "
      f"{'Mov Prom':>9}  {'Rango':>7}  {'SESGO':>12}")
print("  " + "─"*72)

for wd in range(5):
    recs = [r for r in registros if r["wd_num"] == wd]
    if not recs: continue
    n2   = len(recs)
    s    = sum(1 for r in recs if r["direccion"] == "SUBE")
    b    = sum(1 for r in recs if r["direccion"] == "BAJA")
    f    = n2 - s - b
    avg_mv  = np.mean([r["pm_move"]  for r in recs])
    avg_rng = np.mean([r["pm_range"] for r in recs])

    if s/n2 >= 0.65:   sesgo = "🟢 ALCISTA"
    elif b/n2 >= 0.65: sesgo = "🔴 BAJISTA"
    elif s/n2 >= 0.55: sesgo = "🟡 Leve↑"
    elif b/n2 >= 0.55: sesgo = "🟡 Leve↓"
    else:              sesgo = "⚪ Sin sesgo"

    print(f"  {DIAS[wd]:<14} {n2:>3}  "
          f"{s:>2}({s/n2*100:.0f}%)  "
          f"{b:>2}({b/n2*100:.0f}%)  "
          f"{f:>2}({f/n2*100:.0f}%)  "
          f"{avg_mv:>+9.0f}  "
          f"{avg_rng:>7.0f}p  "
          f"{sesgo}")

# ══════════════════════════════════════════
#  ¿EL MÁXIMO O MÍNIMO LLEGA PRIMERO?
# ══════════════════════════════════════════
print("\n\n  ¿QUÉ LLEGA PRIMERO — EL MÁXIMO O EL MÍNIMO?")
print("  (saber esto = saber si hay que buscar short primero o long primero)")
print("  " + "─"*50)

for wd in range(5):
    recs = [r for r in registros if r["wd_num"] == wd]
    if not recs: continue
    n2      = len(recs)
    hi_1st  = sum(1 for r in recs if r["hi_first"])
    lo_1st  = n2 - hi_1st

    if hi_1st/n2 >= 0.65:   señal = "→ Primero SUBE, luego BAJA"
    elif lo_1st/n2 >= 0.65: señal = "→ Primero BAJA, luego SUBE"
    else:                   señal = "→ Sin patrón claro"

    print(f"  {DIAS[wd]:<14} "
          f"Máx primero: {hi_1st}/{n2}={hi_1st/n2*100:.0f}%  "
          f"Mín primero: {lo_1st}/{n2}={lo_1st/n2*100:.0f}%   {señal}")

# ══════════════════════════════════════════
#  DISTRIBUCIÓN DE PUNTOS POR DÍA
# ══════════════════════════════════════════
print("\n\n  DISTRIBUCIÓN MOVIMIENTOS (11AM → 4PM)")
print("  " + "─"*50)
for wd in range(5):
    recs = [r for r in registros if r["wd_num"] == wd]
    if not recs: continue
    moves_d = sorted([r["pm_move"] for r in recs])
    print(f"\n  {DIAS[wd]}:")
    for r in registros:
        if r["wd_num"] != wd: continue
        bar = "█" * int(abs(r["pm_move"]) / 20)
        flecha = "▲" if r["pm_move"] > 0 else ("▼" if r["pm_move"] < 0 else "─")
        print(f"    {r['date']}  {flecha} {r['pm_move']:>+5.0f} pts  {bar}")

print("\n" + "█"*60 + "\n")
