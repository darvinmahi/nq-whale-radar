"""
VOLUME PROFILE SOLO — BACKTEST 2 AÑOS
=======================================
Sin reglas ICT. Solo el profile.

Lógica pura de Volume Profile:
  1. Construye el profile de Asia + Londres (00:00 - 09:00 NY)
  2. Calcula VAH, VAL, POC
  3. New York abre:
     - Si NY abre DEBAJO del VAL → espera retorno al VAL → COMPRA en VAL
     - Si NY abre ENCIMA del VAH → espera retorno al VAH → VENTA en VAH
     - Si NY abre DENTRO del VA  → no hay setup claro
  
  Target: POC (conservador) o el VAH/VAL opuesto (agresivo)
  Stop: 0.25% más allá del low/high más extremo de la sesión pre-NY

Sin filtros de día. Sin ICT. Solo el precio vs el profile.
TODOS los días de la semana incluidos.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*65)
print("  VOLUME PROFILE SOLO — BACKTEST 2 AÑOS")
print("  VAH / VAL / POC del rango Asia+Londres → entrada NY")
print("="*65)

# ─── DATOS ──────────────────────────────────────────────────────────────────
print("\n📡 Descargando NQ=F horario (2 años)...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index  = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek
raw['volume']  = raw['Volume'].fillna(1).replace(0, 1)
print(f"  ✅ {len(raw)} velas cargadas")

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

# ─── VOLUME PROFILE ─────────────────────────────────────────────────────────
def calc_profile(session_df, n_bins=30, value_pct=0.70):
    if len(session_df) < 2:
        return None, None, None
    lo  = float(session_df['Low'].min())
    hi  = float(session_df['High'].max())
    if hi <= lo:
        return (hi+lo)/2, hi, lo

    bins   = np.linspace(lo, hi, n_bins + 1)
    vol_by = np.zeros(n_bins)

    for _, row in session_df.iterrows():
        r_lo  = float(row['Low'])
        r_hi  = float(row['High'])
        r_vol = float(row['volume'])
        r_rng = r_hi - r_lo if r_hi > r_lo else 1e-9
        for b in range(n_bins):
            overlap = min(r_hi, bins[b+1]) - max(r_lo, bins[b])
            if overlap > 0:
                vol_by[b] += r_vol * (overlap / r_rng)

    total = vol_by.sum()
    if total == 0:
        return (hi+lo)/2, hi, lo

    poc_idx = int(np.argmax(vol_by))
    poc     = (bins[poc_idx] + bins[poc_idx+1]) / 2

    target  = total * value_pct
    accum   = vol_by[poc_idx]
    hi_i, lo_i = poc_idx, poc_idx

    while accum < target:
        can_up   = hi_i + 1 < n_bins
        can_down = lo_i - 1 >= 0
        if not can_up and not can_down:
            break
        v_up   = vol_by[hi_i+1] if can_up   else -1
        v_down = vol_by[lo_i-1] if can_down else -1
        if v_up >= v_down:
            hi_i += 1; accum += v_up
        else:
            lo_i -= 1; accum += v_down

    return poc, bins[hi_i+1], bins[lo_i]

# ─── BACKTEST ───────────────────────────────────────────────────────────────
print("\n🔍 Ejecutando backtest puro de Volume Profile...")

trades = []
no_setup = 0

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1
    if wd not in DAYS:
        continue

    pre_ny = day[day['hour'].between(0, 8)]   # Asia + Londres
    ny     = day[day['hour'].between(9, 11)]  # NY apertura

    if pre_ny.empty or ny.empty or len(pre_ny) < 3:
        continue

    # Profile completo de la noche
    poc, vah, val = calc_profile(pre_ny)
    if poc is None:
        continue

    va_range = vah - val
    if va_range < 5:   # Value Area demasiado estrecha
        no_setup += 1
        continue

    # Apertura NY
    ny_open = float(ny.iloc[0]['Open'])

    # ─── SETUP ────────────────────────────────────────────────────────────
    # NY abre fuera del Value Area → espera retorno
    if ny_open < val:          # Debajo del VA → COMPRA en VAL
        direction      = "BUY"
        entry          = val
        target_con     = poc           # Conservador: POC
        target_agr     = vah           # Agresivo: VAH completo
        pre_lo         = float(pre_ny['Low'].min())
        stop           = pre_lo - va_range * 0.15  # Stop ajustado

    elif ny_open > vah:        # Encima del VA → VENTA en VAH
        direction      = "SELL"
        entry          = vah
        target_con     = poc
        target_agr     = val
        pre_hi         = float(pre_ny['High'].max())
        stop           = pre_hi + va_range * 0.15

    else:                      # NY abre dentro del VA → sin setup
        no_setup += 1
        continue

    # Simular ambos targets
    ny_bars = ny.reset_index(drop=True)

    def sim(entry, target, stop, bars, direction):
        entered = False
        for _, bar in bars.iterrows():
            lo_b = float(bar['Low'])
            hi_b = float(bar['High'])
            if direction == "BUY":
                if not entered and hi_b >= entry: entered = True
                if entered:
                    if lo_b <= stop:   return "LOSS", stop
                    if hi_b >= target: return "WIN",  target
            else:
                if not entered and lo_b <= entry: entered = True
                if entered:
                    if hi_b >= stop:   return "LOSS", stop
                    if lo_b <= target: return "WIN",  target
        if not entered:
            return "NO_ENTRY", 0
        return "FLAT", float(bars.iloc[-1]['Close'])

    # Target conservador (POC)
    res_c, ex_c = sim(entry, target_con, stop, ny_bars, direction)
    # Target agresivo (VAH/VAL opuesto)
    res_a, ex_a = sim(entry, target_agr, stop, ny_bars, direction)

    for res, ex, tgt_type in [(res_c, ex_c, "POC"), (res_a, ex_a, "VA_OPUESTO")]:
        if res == "NO_ENTRY":
            continue
        pnl = (ex - entry) if direction == "BUY" else (entry - ex)
        trades.append({
            "date":       str(d),
            "weekday":    DAYS[wd],
            "direction":  direction,
            "target_type":tgt_type,
            "result":     res,
            "pnl_pts":    round(pnl, 1),
            "entry":      round(entry, 1),
            "exit":       round(ex, 1),
            "poc":        round(poc, 1),
            "vah":        round(vah, 1),
            "val":        round(val, 1),
            "va_range":   round(va_range, 1),
        })

# ─── RESULTADOS ─────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  📊 RESULTADOS — VOLUME PROFILE SOLO")
print(f"{'='*65}\n")

t = pd.DataFrame(trades)

for tgt in ["POC", "VA_OPUESTO"]:
    sub = t[t['target_type'] == tgt]
    c   = sub[sub['result'].isin(['WIN','LOSS'])]
    if c.empty: continue
    total = len(c)
    wins  = len(c[c['result']=='WIN'])
    wr    = wins/total*100
    avg_w = c[c['result']=='WIN']['pnl_pts'].mean()
    avg_l = c[c['result']=='LOSS']['pnl_pts'].mean()
    rr    = abs(avg_w/avg_l) if avg_l != 0 else 0
    pnl   = c['pnl_pts'].sum()

    label = "🎯 Target CONSERVADOR (→ POC)" if tgt == "POC" else "🚀 Target AGRESIVO (→ VAH/VAL opuesto)"
    print(f"  {label}")
    print(f"     Trades: {total}  |  WR: {wr:.1f}%  |  RR: 1:{rr:.2f}")
    print(f"     Avg WIN: +{avg_w:.0f}pts (~${avg_w*20:.0f})  |  Avg LOSS: {avg_l:.0f}pts")
    print(f"     PnL 2 años: {pnl:+.0f} pts  (~${pnl*20:+,.0f}/contrato)\n")

    # Por dirección
    for direc in ["BUY", "SELL"]:
        sd = c[c['direction']==direc]
        if len(sd)==0: continue
        w  = len(sd[sd['result']=='WIN'])
        n  = len(sd)
        flag = " ✅" if w/n >= 0.60 else ""
        print(f"     {direc}: WR={w/n*100:.1f}% | n={n} | PnL={sd['pnl_pts'].sum():+.0f}pts{flag}")
    print()

    # Por día
    print(f"     {'Día':<12} {'WR':>7} {'n':>4} {'PnL':>8}")
    print("     " + "-"*36)
    for day in ["Lunes","Martes","Miércoles","Jueves","Viernes"]:
        sd = c[c['weekday']==day]
        if len(sd)==0: continue
        w  = len(sd[sd['result']=='WIN'])
        n  = len(sd)
        flag = " ✅" if w/n >= 0.60 else (" ⚠️" if w/n < 0.40 else "")
        print(f"     {day:<12} {w/n*100:>6.1f}% {n:>4} {sd['pnl_pts'].sum():>+7.0f}pts{flag}")
    print()

# Comparativa global
print(f"{'='*65}")
print(f"  📊 RESUMEN COMPARATIVO HASTA AHORA")
print(f"{'='*65}")
print(f"  {'Sistema':<40} {'WR':>6} {'PnL/contrato':>14}")
print("  " + "-"*62)
print(f"  {'ICT solo (árbol de decisión)':<40} {'53.4%':>6} {'+$53,868':>14}")
print(f"  {'ICT + Volume Profile':<40} {'42.0%':>6} {'+$76,744':>14}")

poc_sub = t[t['target_type']=='POC']
poc_c   = poc_sub[poc_sub['result'].isin(['WIN','LOSS'])]
agr_sub = t[t['target_type']=='VA_OPUESTO']
agr_c   = agr_sub[agr_sub['result'].isin(['WIN','LOSS'])]

if not poc_c.empty:
    wr_poc = len(poc_c[poc_c['result']=='WIN'])/len(poc_c)*100
    pnl_poc= poc_c['pnl_pts'].sum()*20
    print(f"  {'Profile Solo (target POC)':<40} {f'{wr_poc:.1f}%':>6} {f'+${pnl_poc:,.0f}':>14}")

if not agr_c.empty:
    wr_agr = len(agr_c[agr_c['result']=='WIN'])/len(agr_c)*100
    pnl_agr= agr_c['pnl_pts'].sum()*20
    print(f"  {'Profile Solo (target VAH/VAL)':<40} {f'{wr_agr:.1f}%':>6} {f'+${pnl_agr:,.0f}':>14}")

t.to_csv(os.path.join(BASE_DIR, "profile_only_trades.csv"), index=False)
print(f"\n✅ Trades guardados: profile_only_trades.csv")
print(f"📅 Días sin setup (NY dentro del VA): {no_setup}")
