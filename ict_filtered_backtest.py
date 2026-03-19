"""
ICT FILTERED STRATEGY — BACKTEST CON REGLAS APLICADAS
======================================================
Opera SOLO cuando se cumplen las condiciones del árbol de decisión:

LUNES:   London sweep LOW de Asia  → BUY
MARTES:  London sweep HIGH + DOWNTREND → SELL
MIÉRCOLES: London sweep HIGH + DOWNTREND → SELL  
JUEVES:  London sweep HIGH → SELL
VIERNES: NO OPERAR

Filtros adicionales:
- Siempre A FAVOR de la tendencia (MA10 diaria)
- Sweep limpio (solo un lado)
- Rango mínimo Asia > 10 puntos
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*65)
print("  ICT FILTERED — BACKTEST 2 AÑOS")
print("  Solo los setups del árbol de decisión confirmado")
print("="*65)

# ─── DATOS ──────────────────────────────────────────────────────────────────
print("\n📡 Descargando datos...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek  # 0=Lun 1=Mar 2=Mier 3=Jue 4=Vie

# Tendencia diaria MA10
ndx_d = yf.download("NQ=F", period="2y", interval="1d", progress=False)
if isinstance(ndx_d.columns, pd.MultiIndex):
    ndx_d.columns = ndx_d.columns.get_level_values(0)
ndx_d.index = pd.to_datetime(ndx_d.index)
if ndx_d.index.tz is None:
    ndx_d.index = ndx_d.index.tz_localize('UTC')
ndx_d.index = ndx_d.index.tz_convert('America/New_York')
ndx_d['MA10'] = ndx_d['Close'].rolling(10).mean()
ndx_d['uptrend'] = (ndx_d['Close'] > ndx_d['MA10'])
trend_map = ndx_d['uptrend'].to_dict()
# Normalizar keys a date objects
trend_map2 = {k.date(): v for k, v in trend_map.items()}

print(f"  ✅ {len(raw)} velas horarias | Tendencia calculada")

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

# ─── BACKTEST ───────────────────────────────────────────────────────────────
print("\n🔍 Aplicando árbol de decisión dia a dia...")

trades = []
skipped_no_rule = 0
skipped_no_sweep = 0
skipped_no_data  = 0

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1

    # Viernes NO operar
    if wd == 4:
        skipped_no_rule += 1
        continue
    if wd not in DAYS:
        continue

    asia   = day[day['hour'].between(0, 3)]
    london = day[day['hour'].between(4, 8)]
    ny     = day[day['hour'].between(9, 11)]

    if asia.empty or london.empty or ny.empty:
        skipped_no_data += 1
        continue

    asia_hi  = float(asia['High'].max())
    asia_lo  = float(asia['Low'].min())
    asia_rng = asia_hi - asia_lo
    if asia_rng < 10:
        skipped_no_data += 1
        continue

    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())

    swept_lo = lon_lo < asia_lo   # Sweep alcista (reversion BUY)
    swept_hi = lon_hi > asia_hi   # Sweep bajista (reversion SELL)

    # Solo UN sweep limpio
    if swept_lo == swept_hi:
        skipped_no_sweep += 1
        continue

    # Tendencia
    uptrend = trend_map2.get(d, True)

    # ── ÁRBOL DE DECISIÓN ──────────────────────────────────────────────────
    direction = None

    if wd == 0:   # LUNES
        if swept_lo:
            direction = "BUY"
        # SELL en Lunes → NO (17.8% WR)

    elif wd == 1:  # MARTES
        if swept_hi and not uptrend:
            direction = "SELL"
        # BUY en Martes → NO (33.3% WR)

    elif wd == 2:  # MIÉRCOLES
        if swept_hi and not uptrend:
            direction = "SELL"
        # SELL sin downtrend → NO (24.3%)
        # BUY → NO

    elif wd == 3:  # JUEVES
        if swept_hi:
            direction = "SELL"
        # BUY Jueves → NO (33.3%, -36 pts avg)

    if direction is None:
        skipped_no_rule += 1
        continue

    # ── SIMULAR TRADE ──────────────────────────────────────────────────────
    if direction == "BUY":
        entry  = asia_lo
        target = asia_hi
        stop   = lon_lo - (asia_lo - lon_lo) * 0.3
    else:
        entry  = asia_hi
        target = asia_lo
        stop   = lon_hi + (lon_hi - asia_hi) * 0.3

    ny_bars = ny.reset_index(drop=True)
    result  = "FLAT"
    exit_p  = float(ny_bars.iloc[-1]['Close'])
    entered = False

    for _, bar in ny_bars.iterrows():
        lo_b = float(bar['Low'])
        hi_b = float(bar['High'])

        if direction == "BUY":
            if not entered and hi_b >= entry:
                entered = True
            if entered:
                if lo_b <= stop:
                    result = "LOSS"; exit_p = stop; break
                if hi_b >= target:
                    result = "WIN"; exit_p = target; break
        else:
            if not entered and lo_b <= entry:
                entered = True
            if entered:
                if hi_b >= stop:
                    result = "LOSS"; exit_p = stop; break
                if lo_b <= target:
                    result = "WIN"; exit_p = target; break

    if result == "FLAT" and not entered:
        skipped_no_rule += 1
        continue  # Precio nunca llegó al entry → no hay trade

    pnl = (exit_p - entry) if direction == "BUY" else (entry - exit_p)

    trades.append({
        "date":      str(d),
        "weekday":   DAYS[wd],
        "direction": direction,
        "result":    result,
        "entry":     round(entry, 1),
        "exit":      round(exit_p, 1),
        "pnl_pts":   round(pnl, 1),
        "uptrend":   uptrend,
        "sweep_size": round((asia_lo - lon_lo)/asia_rng if direction=="BUY" else (lon_hi - asia_hi)/asia_rng, 3),
        "asia_rng":  round(asia_rng, 1),
    })

# ─── RESULTADOS ─────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  📊 RESULTADOS — ICT CON ÁRBOL DE DECISIÓN APLICADO")
print(f"{'='*65}\n")

if not trades:
    print("  ❌ Sin trades.")
else:
    t = pd.DataFrame(trades)
    closed = t[t['result'].isin(['WIN','LOSS'])]

    total  = len(closed)
    wins   = len(closed[closed['result']=='WIN'])
    losses = len(closed[closed['result']=='LOSS'])
    flats  = len(t[t['result']=='FLAT'])
    wr     = wins / total * 100 if total > 0 else 0
    avg_w  = closed[closed['result']=='WIN']['pnl_pts'].mean()
    avg_l  = closed[closed['result']=='LOSS']['pnl_pts'].mean()
    rr     = abs(avg_w / avg_l) if avg_l != 0 else 0
    total_pnl = closed['pnl_pts'].sum()

    print(f"  🎯 Trades ejecutados (cerrados): {total}")
    print(f"  ✅ Wins:   {wins}  ({wr:.1f}%)")
    print(f"  ❌ Losses: {losses}")
    print(f"  ↔️  Flats:  {flats}  (precio no llegó al entry o cierre sesión)")
    print(f"\n  💰 Avg WIN:     +{avg_w:.0f} pts  (~${avg_w*20:.0f}/contrato)")
    print(f"  💸 Avg LOSS:    {avg_l:.0f} pts  (~${avg_l*20:.0f}/contrato)")
    print(f"  ⚖️  RR Real:     1:{rr:.2f}")
    print(f"\n  💵 PnL Total:   {total_pnl:+.0f} pts  (~${total_pnl*20:+.0f}/contrato 2 años)")
    print(f"  📈 Avg semanal: {total_pnl/104:+.1f} pts/semana")

    # Por día
    print(f"\n  {'Día':<12} {'Wins':>5} {'Total':>6} {'WR':>7} {'Avg PnL':>9} {'Total PnL':>10}")
    print("  " + "-"*55)
    for day in ["Lunes","Martes","Miércoles","Jueves"]:
        sub  = closed[closed['weekday']==day]
        if len(sub)==0: continue
        w    = len(sub[sub['result']=='WIN'])
        n    = len(sub)
        avg  = sub['pnl_pts'].mean()
        tot  = sub['pnl_pts'].sum()
        flag = " ✅" if w/n >= 0.50 else (" ⚠️" if w/n < 0.40 else "")
        print(f"  {day:<12} {w:>5} {n:>6} {w/n*100:>6.1f}%  {avg:>+8.1f}  {tot:>+9.0f}{flag}")

    # Dias sin operar contabilizados
    print(f"\n  📅 Días sin setup válido: {skipped_no_rule}")
    print(f"  📅 Días sin datos suficientes: {skipped_no_data}")
    print(f"  📅 Días con doble sweep (ambos lados): {skipped_no_sweep}")

    t.to_csv(os.path.join(BASE_DIR, "ict_filtered_trades.csv"), index=False)
    print(f"\n✅ Trades guardados: ict_filtered_trades.csv")
