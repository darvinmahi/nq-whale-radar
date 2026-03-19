"""
ICT + VOLUME PROFILE — BACKTEST MEJORADO
==========================================
Mejora el sistema ICT (62.9% WR) añadiendo Volume Profile
para refinar el punto de entrada.

LÓGICA:
  El ICT nos dice CUÁNDO y EN QUÉ DIRECCIÓN operar.
  El Volume Profile nos dice DÓNDE entrar exactamente.

  SIN Profile:  entramos en el High/Low exacto de Asia
  CON Profile:  esperamos que el precio toque el VAL o VAH
                del profile de Asia+Londres → mejor precio,
                stop más ajustado, mejor RR

COMPARATIVA:
  Sistema         WR      RR      PnL
  ICT Solo       62.9%   1:1.76  +$57k
  ICT + Profile   ???     ???     ???
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*65)
print("  ICT + VOLUME PROFILE — BACKTEST 2 AÑOS")
print("  Mismas reglas ICT + entrada en VAL/VAH del Profile")
print("="*65)

# ─── DATOS ──────────────────────────────────────────────────────────────────
print("\n📡 Descargando NQ=F horario...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index  = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek
raw['volume']  = raw['Volume'].fillna(1).replace(0, 1)

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

print(f"  ✅ {len(raw)} velas horarias cargadas")

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves"}

# ─── VOLUME PROFILE ─────────────────────────────────────────────────────────
def calc_profile(session_df, n_bins=30, value_pct=0.70):
    """
    Calcula POC, VAH, VAL del rango usando volumen real.
    Retorna (poc, vah, val) o None si no hay datos.
    """
    if len(session_df) < 2:
        return None, None, None

    lo  = float(session_df['Low'].min())
    hi  = float(session_df['High'].max())
    if hi <= lo:
        mid = (hi + lo) / 2
        return mid, hi, lo

    bins   = np.linspace(lo, hi, n_bins + 1)
    vol_by = np.zeros(n_bins)

    for _, row in session_df.iterrows():
        r_lo  = float(row['Low'])
        r_hi  = float(row['High'])
        r_vol = float(row['volume'])
        r_rng = r_hi - r_lo if r_hi > r_lo else 1e-9
        for b in range(n_bins):
            b_lo = bins[b]
            b_hi = bins[b + 1]
            overlap = min(r_hi, b_hi) - max(r_lo, b_lo)
            if overlap > 0:
                vol_by[b] += r_vol * (overlap / r_rng)

    total = vol_by.sum()
    if total == 0:
        mid = (hi + lo) / 2
        return mid, hi * 0.998, lo * 1.002

    # POC
    poc_idx = int(np.argmax(vol_by))
    poc     = (bins[poc_idx] + bins[poc_idx + 1]) / 2

    # Value Area 70%
    target  = total * value_pct
    accum   = vol_by[poc_idx]
    hi_idx  = poc_idx
    lo_idx  = poc_idx

    while accum < target:
        can_up   = hi_idx + 1 < n_bins
        can_down = lo_idx - 1 >= 0
        if not can_up and not can_down:
            break
        vol_up   = vol_by[hi_idx + 1] if can_up   else -1
        vol_down = vol_by[lo_idx - 1] if can_down else -1
        if vol_up >= vol_down:
            hi_idx += 1
            accum  += vol_up
        else:
            lo_idx -= 1
            accum  += vol_down

    return poc, bins[hi_idx + 1], bins[lo_idx]

# ─── BACKTEST ───────────────────────────────────────────────────────────────
print("\n🔍 Ejecutando backtest ICT + Volume Profile...")

trades_ict     = []   # ICT solo (baseline)
trades_profile = []   # ICT + Profile (mejorado)

no_setup = 0

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1

    if wd == 4 or wd not in DAYS:
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

    uptrend = trend_map.get(d, True)

    # Árbol ICT
    if wd == 0 and swept_lo:
        direction = "BUY"
    elif wd in [1, 2] and swept_hi:
        direction = "SELL"
    elif wd == 3 and swept_hi:
        direction = "SELL"
    else:
        no_setup += 1
        continue

    # ── Calcular Volume Profile de Asia + Londres ─────────────────────────
    pre_ny = day[day['hour'].between(0, 8)]   # Asia + Londres juntos
    poc, vah, val = calc_profile(pre_ny)

    if poc is None:
        continue

    # ── Entradas ──────────────────────────────────────────────────────────
    # ICT solo: entry = extremo Asia
    # ICT + Profile: entry = VAL (si BUY) o VAH (si SELL)

    if direction == "BUY":
        entry_ict     = asia_lo
        entry_profile = val        # Comprar en Value Area Low del profile
        target_ict    = asia_hi
        target_profile= vah        # Target: VAH del profile (o POC como conservador)
        stop_ict      = lon_lo - (asia_lo - lon_lo) * 0.3
        stop_profile  = lon_lo - (val - lon_lo) * 0.2   # Stop más ajustado
    else:
        entry_ict     = asia_hi
        entry_profile = vah
        target_ict    = asia_lo
        target_profile= val
        stop_ict      = lon_hi + (lon_hi - asia_hi) * 0.3
        stop_profile  = lon_hi + (lon_hi - vah) * 0.2

    ny_bars = ny.reset_index(drop=True)

    def simulate(entry, target, stop, bars, direction):
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
        last = float(bars.iloc[-1]['Close'])
        return "FLAT", last

    # Simular ICT solo
    res_ict, exit_ict = simulate(entry_ict, target_ict, stop_ict, ny_bars, direction)
    if res_ict != "NO_ENTRY":
        pnl = (exit_ict - entry_ict) if direction == "BUY" else (entry_ict - exit_ict)
        trades_ict.append({
            "date": str(d), "weekday": DAYS[wd], "direction": direction,
            "result": res_ict, "pnl_pts": round(pnl, 1),
        })

    # Simular ICT + Profile
    res_pro, exit_pro = simulate(entry_profile, target_profile, stop_profile, ny_bars, direction)
    if res_pro != "NO_ENTRY":
        pnl = (exit_pro - entry_profile) if direction == "BUY" else (entry_profile - exit_pro)
        trades_profile.append({
            "date": str(d), "weekday": DAYS[wd], "direction": direction,
            "result": res_pro, "pnl_pts": round(pnl, 1),
            "entry": round(entry_profile, 1), "target": round(target_profile, 1),
            "stop": round(stop_profile, 1), "poc": round(poc, 1),
            "vah": round(vah, 1), "val": round(val, 1),
        })

# ─── COMPARATIVA FINAL ──────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  📊 COMPARATIVA: ICT Solo vs ICT + Volume Profile")
print(f"{'='*65}\n")

def print_stats(trades, label):
    t = pd.DataFrame(trades)
    c = t[t['result'].isin(['WIN','LOSS'])]
    if c.empty:
        print(f"  {label}: sin datos")
        return 0, 0, 0
    total = len(c)
    wins  = len(c[c['result']=='WIN'])
    wr    = wins/total*100
    avg_w = c[c['result']=='WIN']['pnl_pts'].mean()
    avg_l = c[c['result']=='LOSS']['pnl_pts'].mean()
    rr    = abs(avg_w/avg_l) if avg_l != 0 else 0
    pnl   = c['pnl_pts'].sum()
    print(f"  📌 {label}")
    print(f"     Trades: {total}  |  WR: {wr:.1f}%  |  RR: 1:{rr:.2f}")
    print(f"     Avg WIN: +{avg_w:.0f}pts  |  Avg LOSS: {avg_l:.0f}pts")
    print(f"     PnL Total: {pnl:+.0f} pts  (~${pnl*20:+,.0f}/contrato)\n")

    # Por día
    for day in ["Lunes","Martes","Miércoles","Jueves"]:
        sub = c[c['weekday']==day]
        if len(sub)==0: continue
        w = len(sub[sub['result']=='WIN'])
        n = len(sub)
        flag = " ✅" if w/n >= 0.65 else (" 🔥" if w/n >= 0.75 else "")
        print(f"     {day:<12} WR:{w/n*100:5.1f}% | n={n:2d} | PnL:{sub['pnl_pts'].sum():+6.0f}pts{flag}")
    print()
    return wr, pnl*20, rr

wr1, pnl1, rr1 = print_stats(trades_ict,     "ICT SOLO (árbol de decisión)")
wr2, pnl2, rr2 = print_stats(trades_profile, "ICT + VOLUME PROFILE")

print(f"{'='*65}")
print(f"  🏆 VEREDICTO FINAL")
print(f"{'='*65}")
print(f"  WR:  ICT={wr1:.1f}%  →  ICT+Profile={wr2:.1f}%  ({wr2-wr1:+.1f}pp)")
print(f"  RR:  ICT=1:{rr1:.2f} →  ICT+Profile=1:{rr2:.2f}")
print(f"  PnL: ICT=${pnl1:+,.0f} →  ICT+Profile=${pnl2:+,.0f} ({pnl2-pnl1:+,.0f})")

# Guardar
pd.DataFrame(trades_profile).to_csv(
    os.path.join(BASE_DIR, "ict_profile_trades_v2.csv"), index=False)
print(f"\n✅ Trades guardados: ict_profile_trades_v2.csv")
