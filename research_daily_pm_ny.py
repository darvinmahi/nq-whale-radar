"""
research_daily_pm_ny.py
═══════════════════════
Réplica del estudio de MARTES para todos los días de la semana:
  - PM Direction (pre-market 7:00-9:29) → ¿predice la dirección NY (9:30-16:00)?
  - Qué % de veces el PM alcista → NY alcista
  - Qué % de veces el PM bajista → NY bajista
  - Rango promedio por día
  - Correlación PM range → NY range

Uso:
    python research_daily_pm_ny.py              → todos los dias
    python research_daily_pm_ny.py thursday     → solo jueves
    python research_daily_pm_ny.py wednesday    → solo miércoles
    python research_daily_pm_ny.py friday       → solo viernes
"""

import sys
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import date

DIAS_ES = {0:"LUNES", 1:"MARTES", 2:"MIÉRCOLES", 3:"JUEVES", 4:"VIERNES"}
DIAS_EN = {"monday":0, "tuesday":1, "wednesday":2, "thursday":3, "friday":4,
           "lunes":0, "martes":1, "miércoles":2, "jueves":3, "viernes":4}

# Filtrar por día si se pasa como argumento
filter_day = None
if len(sys.argv) > 1:
    arg = sys.argv[1].lower().replace("é","e").replace("e","e")
    filter_day = DIAS_EN.get(arg)
    if filter_day is None:
        print(f"Día no reconocido: {sys.argv[1]}")
        sys.exit(1)

print("\n" + "█"*65)
print("  NQ — ESTUDIO PM → NY (replicando metodología MARTES)")
print("  12 meses | 15 minutos | Yahoo Finance NQ=F")
print("█"*65)

# ─── 1. Descargar datos ──────────────────────────────────────
print("\n  Descargando datos 15min (60 días)...")
df15 = yf.download("NQ=F", period="60d", interval="15m", progress=False, auto_adjust=True)
if df15.empty:
    df15 = yf.download("MNQ=F", period="60d", interval="15m", progress=False, auto_adjust=True)

print("  Descargando datos 1h (12 meses para más sesiones)...")
df1h = yf.download("NQ=F", period="12mo", interval="1h", progress=False, auto_adjust=True)
if df1h.empty:
    df1h = yf.download("MNQ=F", period="12mo", interval="1h", progress=False, auto_adjust=True)

# Usar 15m si disponible (más preciso), 1h como fallback
if not df15.empty:
    df = df15
    interval_name = "15min"
elif not df1h.empty:
    df = df1h
    interval_name = "1h"
else:
    print("  ERROR: Sin datos"); sys.exit(1)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
if df.index.tz is None:
    df.index = df.index.tz_localize("UTC")
df.index = df.index.tz_convert("America/New_York")
df["date"]    = df.index.normalize()
df["weekday"] = df.index.dayofweek
print(f"  {len(df)} barras {interval_name} | {df.index[0].date()} → {df.index[-1].date()}")

# ─── 2. Calcular sesiones ────────────────────────────────────
sessions = []
for day in sorted(df["date"].unique()):
    wd = pd.Timestamp(day).weekday()
    if wd > 4: continue
    if filter_day is not None and wd != filter_day: continue

    d = df[df["date"] == day]

    pm   = d.between_time("07:00", "09:29")   # Pre-market
    ny   = d.between_time("09:30", "16:00")   # NY session
    pre8 = d.between_time("07:00", "07:15")   # Apertura PM
    spk  = d.between_time("08:30", "08:44")   # Spike 8:30 (datos econ)

    if len(pm) < 3 or len(ny) < 4: continue

    # PM stats
    pm_open  = float(pm.iloc[0]["Open"])
    pm_close = float(pm.iloc[-1]["Close"])
    pm_move  = pm_close - pm_open
    pm_range = float(pm["High"].max()) - float(pm["Low"].min())
    pm_dir   = "BULL" if pm_move > 15 else ("BEAR" if pm_move < -15 else "FLAT")

    # NY stats
    ny_open  = float(ny.iloc[0]["Open"])
    ny_close = float(ny.iloc[-1]["Close"])
    ny_move  = ny_close - ny_open
    ny_range = float(ny["High"].max()) - float(ny["Low"].min())
    ny_hi    = float(ny["High"].max())
    ny_lo    = float(ny["Low"].min())
    ny_dir   = "BULL" if ny_move > 20 else ("BEAR" if ny_move < -20 else "FLAT")

    # ¿Máximo o mínimo primero en NY?
    idx_hi = ny["High"].idxmax()
    idx_lo = ny["Low"].idxmin()
    hi_first = idx_hi < idx_lo  # True = sube primero

    # Spike 8:30
    spk_move = 0
    if not spk.empty:
        spk_move = float(spk.iloc[-1]["Close"]) - float(spk.iloc[0]["Open"])

    sessions.append({
        "date":      str(day.date()),
        "weekday":   DIAS_ES[wd],
        "wd":        wd,
        "pm_open":   round(pm_open),
        "pm_close":  round(pm_close),
        "pm_move":   round(pm_move),
        "pm_range":  round(pm_range),
        "pm_dir":    pm_dir,
        "ny_open":   round(ny_open),
        "ny_close":  round(ny_close),
        "ny_move":   round(ny_move),
        "ny_range":  round(ny_range),
        "ny_hi":     round(ny_hi),
        "ny_lo":     round(ny_lo),
        "ny_dir":    ny_dir,
        "hi_first":  hi_first,
        "spk_move":  round(spk_move),
    })

if not sessions:
    print("  Sin sesiones para analizar."); sys.exit(0)

df_s = pd.DataFrame(sessions)

# ─── 3. Análisis por día ─────────────────────────────────────
days_to_show = [filter_day] if filter_day is not None else range(5)

for wd in days_to_show:
    d = df_s[df_s["wd"] == wd]
    if d.empty: continue
    n = len(d)
    print("\n\n" + "═"*65)
    print(f"  📅 {DIAS_ES[wd]}  —  {n} sesiones analizadas")
    print("═"*65)

    # ── PM → NY predictibilidad ─────────────────────────────
    bull_pm = d[d["pm_dir"] == "BULL"]
    bear_pm = d[d["pm_dir"] == "BEAR"]
    flat_pm = d[d["pm_dir"] == "FLAT"]

    print(f"\n  PRE-MARKET → NY (principal predictor)")
    print(f"  {'─'*55}")

    if len(bull_pm) > 0:
        bull_to_bull = (bull_pm["ny_dir"] == "BULL").sum()
        pct = bull_to_bull / len(bull_pm) * 100
        bar = "█" * int(pct/5)
        print(f"  PM BULL ({len(bull_pm):>2}sess) → NY BULL: {bull_to_bull:>2}/{len(bull_pm):>2} = {pct:>5.1f}%  {bar}")

    if len(bear_pm) > 0:
        bear_to_bear = (bear_pm["ny_dir"] == "BEAR").sum()
        pct = bear_to_bear / len(bear_pm) * 100
        bar = "█" * int(pct/5)
        print(f"  PM BEAR ({len(bear_pm):>2}sess) → NY BEAR: {bear_to_bear:>2}/{len(bear_pm):>2} = {pct:>5.1f}%  {bar}")

    if len(flat_pm) > 0:
        flat_bull = (flat_pm["ny_dir"] == "BULL").sum()
        flat_bear = (flat_pm["ny_dir"] == "BEAR").sum()
        print(f"  PM FLAT ({len(flat_pm):>2}sess) → NY: BULL {flat_bull} / BEAR {flat_bear} / FLAT {len(flat_pm)-flat_bull-flat_bear}")

    # ── Rangos ──────────────────────────────────────────────
    print(f"\n  RANGOS NY  (de mínimo a máximo del día)")
    print(f"  {'─'*55}")
    print(f"  Mediana    : {d['ny_range'].median():>6.0f} pts")
    print(f"  Promedio   : {d['ny_range'].mean():>6.0f} pts")
    print(f"  Máximo     : {d['ny_range'].max():>6.0f} pts")
    print(f"  Mínimo     : {d['ny_range'].min():>6.0f} pts")
    print(f"  Percentil 25: {d['ny_range'].quantile(0.25):>5.0f} pts")
    print(f"  Percentil 75: {d['ny_range'].quantile(0.75):>5.0f} pts")

    # ── PM Range → NY Range correlation ─────────────────────
    if len(d) >= 5:
        corr = d["pm_range"].corr(d["ny_range"])
        print(f"\n  Correlación PM_range → NY_range: r = {corr:.3f}")
        if abs(corr) >= 0.5:
            print(f"  → ALTA correlación: PM predice tamaño del movimiento NY")
        elif abs(corr) >= 0.3:
            print(f"  → Correlación moderada")
        else:
            print(f"  → Baja correlación: PM range NO predice NY range este dia")

        # ── PM size buckets ──────────────────────────────────
        print(f"\n  TAMAÑO PM → rango esperado NY (pt. promedio)")
        print(f"  {'─'*55}")
        for lo, hi, label in [(0,100,"PM <100pts"), (100,200,"PM 100-200"), (200,999,"PM >200pts")]:
            sub = d[(d["pm_range"] >= lo) & (d["pm_range"] < hi)]
            if len(sub) >= 2:
                print(f"  {label:<15}: n={len(sub):>2}  NY avg={sub['ny_range'].mean():>5.0f}pts  NY med={sub['ny_range'].median():>5.0f}pts")

    # ── ¿Máximo o mínimo primero en NY? ─────────────────────
    hi_1st = d["hi_first"].sum()
    lo_1st = n - hi_1st
    print(f"\n  ¿QUÉ LLEGA PRIMERO EN NY?  (para saber si buscar long o short antes)")
    print(f"  {'─'*55}")
    print(f"  Máximo primero (sube→baja): {hi_1st:>2}/{n} = {hi_1st/n*100:.0f}%")
    print(f"  Mínimo primero (baja→sube): {lo_1st:>2}/{n} = {lo_1st/n*100:.0f}%")
    if hi_1st/n >= 0.6:
        print(f"  → Patrón: SUBE PRIMERO luego baja")
    elif lo_1st/n >= 0.6:
        print(f"  → Patrón: BAJA PRIMERO luego sube ('trampa alcista')")

    # ── Sesgo global ─────────────────────────────────────────
    bulls = (d["ny_dir"] == "BULL").sum()
    bears = (d["ny_dir"] == "BEAR").sum()
    print(f"\n  SESGO GLOBAL NY  (todos los días sin filtro)")
    print(f"  {'─'*55}")
    print(f"  BULL: {bulls:>2}/{n} = {bulls/n*100:.0f}%   BEAR: {bears:>2}/{n} = {bears/n*100:.0f}%")
    if bulls/n >= 0.6:
        print(f"  → DÍA CON SESGO ALCISTA")
    elif bears/n >= 0.6:
        print(f"  → DÍA CON SESGO BAJISTA")
    else:
        print(f"  → Sin sesgo claro (depende del contexto)")

    # ── Tabla detalle ────────────────────────────────────────
    print(f"\n  DETALLE SESIONES")
    print(f"  {'─'*65}")
    print(f"  {'Fecha':<12} {'PM':>5} {'PMdir':<5} {'NYmov':>6} {'NYrang':>6} {'NYdir':<5} {'Hi1st'}")
    print(f"  {'─'*65}")
    for _, row in d.sort_values("date", ascending=False).iterrows():
        hi = "↑" if row["hi_first"] else "↓"
        pm_sym = "▲" if row["pm_dir"]=="BULL" else ("▼" if row["pm_dir"]=="BEAR" else "—")
        ny_sym = "▲" if row["ny_dir"]=="BULL" else ("▼" if row["ny_dir"]=="BEAR" else "—")
        match = "✅" if row["pm_dir"] == row["ny_dir"] else ("❌" if row["pm_dir"] in ("BULL","BEAR") and row["ny_dir"] in ("BULL","BEAR") else "")
        print(f"  {row['date']:<12} {row['pm_move']:>+5.0f} {pm_sym:<5} {row['ny_move']:>+6.0f} {row['ny_range']:>6.0f} {ny_sym:<5} {hi}  {match}")

print("\n\n" + "█"*65)
print("  FIN DEL ANÁLISIS")
print("█"*65 + "\n")
