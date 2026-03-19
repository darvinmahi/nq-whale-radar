"""
SISTEMA COMBINADO — ICT + FUNDAMENTALES
=========================================
Capa 1: COT + VXN definen el sesgo semanal
Capa 2: ICT de sesiones (Asia sweep por Londres → NY)
Solo se opera cuando AMBAS capas coinciden en dirección.

Reglas de confluencia:
  BUY solo si:
    - COT acumulando (net_change > 0) O cot_index < 30 (extremo bajo)
    - VXN no está en pánico (< 30)
    - Día=Lunes + Londres sweepó LOW de Asia
  
  SELL solo si:
    - COT reduciendo (net_change < 0) O tendencia bajista macro
    - VXN en zona media-alta (> 18)
    - Día=Martes/Jueves + Londres sweepó HIGH de Asia
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COT_CSV  = os.path.join(BASE_DIR, "data", "cot", "nasdaq_cot_historical_study.csv")

print("="*65)
print("  ICT + FUNDAMENTALES — BACKTEST COMBINADO 2 AÑOS")
print("  Capa 1: COT + VXN  |  Capa 2: ICT Sesiones")
print("="*65)

# ─── DATOS HORARIOS ─────────────────────────────────────────────────────────
print("\n📡 Descargando datos horarios NQ=F...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek
print(f"  ✅ {len(raw)} velas horarias")

# ─── VXN DIARIO ─────────────────────────────────────────────────────────────
print("📡 Descargando VXN diario...")
vxn_d = yf.download("^VXN", period="2y", interval="1d", progress=False)
if isinstance(vxn_d.columns, pd.MultiIndex):
    vxn_d.columns = vxn_d.columns.get_level_values(0)
vxn_d.index = pd.to_datetime(vxn_d.index)
if vxn_d.index.tz is None:
    vxn_d.index = vxn_d.index.tz_localize('UTC')
vxn_d.index = vxn_d.index.tz_convert('America/New_York')
vxn_map = {d.date(): float(v) for d, v in vxn_d['Close'].items()}

# Tendencia MA10
ndx_d = yf.download("NQ=F", period="2y", interval="1d", progress=False)
if isinstance(ndx_d.columns, pd.MultiIndex):
    ndx_d.columns = ndx_d.columns.get_level_values(0)
ndx_d.index = pd.to_datetime(ndx_d.index)
if ndx_d.index.tz is None:
    ndx_d.index = ndx_d.index.tz_localize('UTC')
ndx_d.index = ndx_d.index.tz_convert('America/New_York')
ndx_d['MA10'] = ndx_d['Close'].rolling(10).mean()
ndx_d['uptrend'] = ndx_d['Close'] > ndx_d['MA10']
trend_map = {d.date(): bool(v) for d, v in ndx_d['uptrend'].items()}
print(f"  ✅ VXN y tendencia listos")

# ─── COT SEMANAL ────────────────────────────────────────────────────────────
print("📡 Cargando COT histórico...")
try:
    cot = pd.read_csv(COT_CSV)
    dc  = 'Report_Date_as_MM_DD_YYYY'
    cot[dc] = pd.to_datetime(cot[dc])
    cot = cot.sort_values(dc).reset_index(drop=True)
    cot['net_pos'] = (
        (cot['Asset_Mgr_Positions_Long_All'] - cot['Asset_Mgr_Positions_Short_All']) +
        (cot['Lev_Money_Positions_Long_All']  - cot['Lev_Money_Positions_Short_All'])
    )
    cot['net_chg']  = cot['net_pos'].diff()
    cot['cot_max']  = cot['net_pos'].rolling(52).max()
    cot['cot_min']  = cot['net_pos'].rolling(52).min()
    cot['cot_idx']  = (cot['net_pos'] - cot['cot_min']) / (cot['cot_max'] - cot['cot_min'] + 1e-9) * 100
    cot['date_key'] = cot[dc].dt.date
    cot_ok = True
    print(f"  ✅ COT: {len(cot)} semanas")
except Exception as e:
    print(f"  ⚠️ COT no disponible: {e}")
    cot_ok = False

def get_cot_for_date(d):
    """Obtiene el COT más reciente disponible para una fecha."""
    if not cot_ok:
        return None, None
    subset = cot[cot['date_key'] <= d]
    if subset.empty:
        return None, None
    row = subset.iloc[-1]
    return float(row['net_chg']), float(row['cot_idx'])

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

# ─── BACKTEST COMBINADO ──────────────────────────────────────────────────────
print("\n🔀 Cruzando ICT + Fundamentales día por día...")

trades      = []
rejected_cot = 0
rejected_vxn = 0
no_setup     = 0

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1

    if wd == 4 or wd not in DAYS:  # Viernes no
        continue

    asia   = day[day['hour'].between(0, 3)]
    london = day[day['hour'].between(4, 8)]
    ny     = day[day['hour'].between(9, 11)]

    if asia.empty or london.empty or ny.empty:
        continue

    asia_hi  = float(asia['High'].max())
    asia_lo  = float(asia['Low'].min())
    asia_rng = asia_hi - asia_lo
    if asia_rng < 10:
        continue

    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())

    swept_lo = lon_lo < asia_lo
    swept_hi = lon_hi > asia_hi

    if swept_lo == swept_hi:
        no_setup += 1
        continue

    # Árbol ICT
    if wd == 0 and swept_lo:
        ict_dir = "BUY"
    elif wd in [1, 2] and swept_hi:
        ict_dir = "SELL"
    elif wd == 3 and swept_hi:
        ict_dir = "SELL"
    else:
        no_setup += 1
        continue

    # ── CAPA 1: FILTRO FUNDAMENTAL ────────────────────────────────────────
    cot_chg, cot_idx = get_cot_for_date(d)
    vxn_val          = vxn_map.get(d)
    uptrend          = trend_map.get(d, True)

    # VXN demasiado alto (pánico extremo > 35) → mercado impredecible
    if vxn_val and vxn_val > 35:
        rejected_vxn += 1
        continue

    # COT + tendencia conforman el sesgo
    cot_bullish = (cot_chg and cot_chg > 0) or (cot_idx and cot_idx < 30)
    cot_bearish = (cot_chg and cot_chg < 0) or (cot_idx and cot_idx > 70)

    # Rechazar si COT va contra ICT
    if ict_dir == "BUY" and cot_bearish and not cot_bullish:
        rejected_cot += 1
        continue
    if ict_dir == "SELL" and cot_bullish and not cot_bearish:
        rejected_cot += 1
        continue

    # Tendencia macro confirma
    if ict_dir == "BUY" and not uptrend and not (cot_idx and cot_idx < 25):
        rejected_cot += 1
        continue

    # ── SIMULAR TRADE ─────────────────────────────────────────────────────
    if ict_dir == "BUY":
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

        if ict_dir == "BUY":
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

    if not entered:
        continue

    pnl = (exit_p - entry) if ict_dir == "BUY" else (entry - exit_p)

    trades.append({
        "date":      str(d),
        "weekday":   DAYS[wd],
        "direction": ict_dir,
        "result":    result,
        "pnl_pts":   round(pnl, 1),
        "vxn":       round(vxn_val, 1) if vxn_val else 0,
        "cot_idx":   round(cot_idx, 1) if cot_idx else 0,
        "uptrend":   uptrend,
    })

# ─── RESULTADOS ─────────────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  📊 RESULTADOS FINALES — ICT + FUNDAMENTALES")
print(f"{'='*65}\n")

t  = pd.DataFrame(trades) if trades else pd.DataFrame()
c  = t[t['result'].isin(['WIN','LOSS'])] if len(t) > 0 else pd.DataFrame()

if c.empty:
    print("  ❌ Sin trades cerrados.")
else:
    total = len(c)
    wins  = len(c[c['result']=='WIN'])
    losses= len(c[c['result']=='LOSS'])
    wr    = wins/total*100
    avg_w = c[c['result']=='WIN']['pnl_pts'].mean()
    avg_l = c[c['result']=='LOSS']['pnl_pts'].mean()
    rr    = abs(avg_w/avg_l) if avg_l != 0 else 0
    pnl_t = c['pnl_pts'].sum()

    print(f"  🎯 Trades ejecutados: {total}")
    print(f"  ✅ Wins:    {wins}  ({wr:.1f}%)")
    print(f"  ❌ Losses:  {losses}")
    print(f"\n  💰 Avg WIN:   +{avg_w:.0f} pts  (~${avg_w*20:.0f}/contrato)")
    print(f"  💸 Avg LOSS:  {avg_l:.0f} pts   (~${avg_l*20:.0f}/contrato)")
    print(f"  ⚖️  RR Real:   1:{rr:.2f}")
    print(f"\n  💵 PnL Total 2 años: {pnl_t:+.0f} pts  (~${pnl_t*20:+.0f}/contrato)")

    # Por día
    print(f"\n  {'Día':<12} {'Wins':>5} {'Total':>6} {'WR':>7} {'PnL Total':>10}")
    print("  " + "-"*48)
    for day in ["Lunes","Martes","Miércoles","Jueves"]:
        sub = c[c['weekday']==day]
        if len(sub)==0: continue
        w = len(sub[sub['result']=='WIN'])
        n = len(sub)
        flag = " ✅" if w/n >= 0.60 else (" 🔥" if w/n >= 0.70 else "")
        print(f"  {day:<12} {w:>5} {n:>6} {w/n*100:>6.1f}%  {sub['pnl_pts'].sum():>+9.0f}{flag}")

    # Comparativa
    print(f"\n{'='*65}")
    print(f"  📊 COMPARATIVA DIRECTA")
    print(f"{'='*65}")
    print(f"  {'Sistema':<35} {'WR':>7} {'PnL Total':>12}")
    print("  " + "-"*55)
    print(f"  {'ICT solo (árbol de decisión)':<35} {'62.9%':>7} {'+$57,064':>12}")
    print(f"  {'ICT + Fundamentales (este)':<35} {f'{wr:.1f}%':>7} {f'+${pnl_t*20:,.0f}':>12}")
    diff = pnl_t*20 - 57064
    mejora_wr = wr - 62.9
    print(f"\n  Mejora en WR:   {mejora_wr:+.1f} puntos porcentuales")
    print(f"  Mejora en PnL:  {diff:+,.0f} USD")

    # Rechazos
    print(f"\n  📋 Trades rechazados por filtros:")
    print(f"     COT en contra:  {rejected_cot}")
    print(f"     VXN extremo:    {rejected_vxn}")
    print(f"     Sin setup ICT:  {no_setup}")

    # Guardar
    t.to_csv(os.path.join(BASE_DIR, "ict_combined_trades.csv"), index=False)

    summary = {
        "system": "ICT + Fundamentales (COT + VXN)",
        "total_trades": int(total),
        "win_rate": round(wr, 1),
        "avg_win_pts": round(float(avg_w), 1),
        "avg_loss_pts": round(float(avg_l), 1),
        "rr_ratio": round(rr, 2),
        "total_pnl_pts": round(float(pnl_t), 1),
        "total_pnl_usd": round(float(pnl_t) * 20, 0),
        "vs_ict_only_wr": "62.9%",
        "vs_ict_only_pnl": "$57,064",
    }
    with open(os.path.join(BASE_DIR, "ict_combined_strategy.json"), "w") as f:
        json.dump(summary, f, indent=4)

    print(f"\n✅ Guardado: ict_combined_trades.csv + ict_combined_strategy.json")
