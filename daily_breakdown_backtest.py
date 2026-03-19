"""
BACKTEST COMPLETO LUNES-VIERNES — ICT + VOLUME PROFILE
=======================================================
Prueba TODOS los setups posibles cada día y muestra:
  - WR por día
  - Qué hacer y qué NO hacer
  - PnL real por día
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*65)
print("  BACKTEST COMPLETO — LUNES A VIERNES (2 AÑOS)")
print("  ICT + Volume Profile | Cada día analizado por separado")
print("="*65)

# ─── DATOS ──────────────────────────────────────────────────────────────────
print("\n📡 Descargando datos...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index  = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek
raw['volume']  = raw['Volume'].fillna(1).replace(0, 1)

ndx_d = yf.download("NQ=F", period="2y", interval="1d", progress=False)
if isinstance(ndx_d.columns, pd.MultiIndex):
    ndx_d.columns = ndx_d.columns.get_level_values(0)
ndx_d.index = pd.to_datetime(ndx_d.index)
if ndx_d.index.tz is None:
    ndx_d.index = ndx_d.index.tz_localize('UTC')
ndx_d.index = ndx_d.index.tz_convert('America/New_York')
ndx_d['MA10']    = ndx_d['Close'].rolling(10).mean()
ndx_d['uptrend'] = ndx_d['Close'] > ndx_d['MA10']
trend_map = {d.date(): bool(v) for d, v in ndx_d['uptrend'].items()}

print(f"  ✅ {len(raw)} velas | tendencia calculada")
DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

# ─── PROFILE ────────────────────────────────────────────────────────────────
def calc_profile(sdf, n_bins=30, pct=0.70):
    if len(sdf) < 2: return None, None, None
    lo, hi = float(sdf['Low'].min()), float(sdf['High'].max())
    if hi <= lo: return (hi+lo)/2, hi, lo
    bins = np.linspace(lo, hi, n_bins+1)
    vb   = np.zeros(n_bins)
    for _, r in sdf.iterrows():
        rlo, rhi, rv = float(r['Low']), float(r['High']), float(r['volume'])
        rng = rhi - rlo if rhi > rlo else 1e-9
        for b in range(n_bins):
            ov = min(rhi, bins[b+1]) - max(rlo, bins[b])
            if ov > 0: vb[b] += rv * (ov/rng)
    tot = vb.sum()
    if tot == 0: return (hi+lo)/2, hi, lo
    pi  = int(np.argmax(vb))
    poc = (bins[pi]+bins[pi+1])/2
    acc = vb[pi]; hi_i, lo_i = pi, pi
    while acc < tot*pct:
        cu = hi_i+1 < n_bins; cd = lo_i-1 >= 0
        if not cu and not cd: break
        vu = vb[hi_i+1] if cu else -1
        vd = vb[lo_i-1] if cd else -1
        if vu >= vd: hi_i += 1; acc += vu
        else:        lo_i -= 1; acc += vd
    return poc, bins[hi_i+1], bins[lo_i]

def sim(entry, target, stop, bars, direc):
    entered = False
    for _, b in bars.iterrows():
        lo_b, hi_b = float(b['Low']), float(b['High'])
        if direc == "BUY":
            if not entered and hi_b >= entry: entered = True
            if entered:
                if lo_b <= stop:   return "LOSS", stop
                if hi_b >= target: return "WIN",  target
        else:
            if not entered and lo_b <= entry: entered = True
            if entered:
                if hi_b >= stop:   return "LOSS", stop
                if lo_b <= target: return "WIN",  target
    if not entered: return "NO_ENTRY", 0
    return "FLAT", float(bars.iloc[-1]['Close'])

# ─── BACKTEST: TODOS LOS SETUPS POR DÍA ─────────────────────────────────────
print("\n🔍 Analizando cada día de la semana...")

# Para cada día guardamos resultados de BUY y SELL
all_trades = []

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1
    if wd not in DAYS: continue

    asia   = day[day['hour'].between(0, 3)]
    london = day[day['hour'].between(4, 8)]
    ny     = day[day['hour'].between(9, 11)]

    if asia.empty or london.empty or ny.empty or len(asia) < 2: continue

    asia_hi = float(asia['High'].max())
    asia_lo = float(asia['Low'].min())
    asia_rng = asia_hi - asia_lo
    if asia_rng < 10: continue

    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())
    swept_lo = lon_lo < asia_lo
    swept_hi = lon_hi > asia_hi

    uptrend = trend_map.get(d, True)

    pre_ny = day[day['hour'].between(0, 8)]
    poc, vah, val = calc_profile(pre_ny)
    if poc is None: continue
    if (vah - val) < 5: continue

    ny_bars = ny.reset_index(drop=True)

    # ── Probar BUY ──────────────────────────────────────────────────────
    if swept_lo:
        entry  = val
        target = vah
        stop   = lon_lo - (val - lon_lo) * 0.2

        res, ex = sim(entry, target, stop, ny_bars, "BUY")
        if res != "NO_ENTRY":
            pnl = (ex - entry)
            all_trades.append({
                "date": str(d), "weekday": DAYS[wd], "direction": "BUY",
                "sweep": "BAJO", "uptrend": uptrend,
                "result": res, "pnl_pts": round(pnl, 1),
            })

    # ── Probar SELL ─────────────────────────────────────────────────────
    if swept_hi:
        entry  = vah
        target = val
        stop   = lon_hi + (lon_hi - vah) * 0.2

        res, ex = sim(entry, target, stop, ny_bars, "SELL")
        if res != "NO_ENTRY":
            pnl = (entry - ex)
            all_trades.append({
                "date": str(d), "weekday": DAYS[wd], "direction": "SELL",
                "sweep": "ALTO", "uptrend": uptrend,
                "result": res, "pnl_pts": round(pnl, 1),
            })

# ─── ANÁLISIS POR DÍA ───────────────────────────────────────────────────────
T = pd.DataFrame(all_trades)
C = T[T['result'].isin(['WIN','LOSS'])]

print(f"\n{'='*65}")
print(f"  📊 RESULTADOS POR DÍA — ICT + VOLUME PROFILE (2 AÑOS)")
print(f"{'='*65}\n")

day_summary = {}

for wd_name in ["Lunes","Martes","Miércoles","Jueves","Viernes"]:
    sub = C[C['weekday'] == wd_name]
    buy_all  = sub[sub['direction'] == 'BUY']
    sell_all = sub[sub['direction'] == 'SELL']

    def stats(s):
        if len(s) == 0: return None
        w = len(s[s['result']=='WIN'])
        n = len(s)
        wr = w/n*100
        avg_w = s[s['result']=='WIN']['pnl_pts'].mean() if w>0 else 0
        avg_l = s[s['result']=='LOSS']['pnl_pts'].mean() if (n-w)>0 else 0
        rr    = abs(avg_w/avg_l) if avg_l!=0 else 0
        pnl   = s['pnl_pts'].sum()
        return {"n":n, "wr":wr, "avg_w":avg_w, "avg_l":avg_l, "rr":rr, "pnl":pnl}

    bs = stats(buy_all)
    ss = stats(sell_all)

    print(f"  ╔══ {wd_name.upper()} {'═'*(50-len(wd_name))}╗")

    if bs:
        icon = "✅" if bs['wr'] >= 50 else ("⚠️" if bs['wr'] >= 40 else "❌")
        accion = "OPERAR BUY" if bs['wr'] >= 50 else ("CON CUIDADO" if bs['wr'] >= 40 else "NO OPERAR BUY")
        print(f"  ║  📈 BUY (London barrió LOW de Asia + entra en VAL)")
        print(f"  ║     WR:    {bs['wr']:5.1f}% {icon}  |  n={bs['n']:2d} trades")
        print(f"  ║     Avg WIN: +{bs['avg_w']:5.0f}pts  |  Avg LOSS: {bs['avg_l']:5.0f}pts  |  RR: 1:{bs['rr']:.2f}")
        print(f"  ║     PnL:  {bs['pnl']:+.0f} pts  (~${bs['pnl']*20:+,.0f}/contrato 2 años)")
        print(f"  ║     👉 {accion}")
    else:
        print(f"  ║  📈 BUY: Sin datos suficientes")

    print(f"  ║")

    if ss:
        icon = "✅" if ss['wr'] >= 50 else ("⚠️" if ss['wr'] >= 40 else "❌")
        accion = "OPERAR SELL" if ss['wr'] >= 50 else ("CON CUIDADO" if ss['wr'] >= 40 else "NO OPERAR SELL")
        print(f"  ║  📉 SELL (London barrió HIGH de Asia + entra en VAH)")
        print(f"  ║     WR:    {ss['wr']:5.1f}% {icon}  |  n={ss['n']:2d} trades")
        print(f"  ║     Avg WIN: +{ss['avg_w']:5.0f}pts  |  Avg LOSS: {ss['avg_l']:5.0f}pts  |  RR: 1:{ss['rr']:.2f}")
        print(f"  ║     PnL:  {ss['pnl']:+.0f} pts  (~${ss['pnl']*20:+,.0f}/contrato 2 años)")
        print(f"  ║     👉 {accion}")
    else:
        print(f"  ║  📉 SELL: Sin datos suficientes")

    print(f"  ╚{'═'*62}╝\n")

    day_summary[wd_name] = {"buy": bs, "sell": ss}

# ─── TABLA RESUMEN ──────────────────────────────────────────────────────────
print(f"{'='*65}")
print(f"  🗓️  TABLA RESUMEN RÁPIDA — QUÉ HACER CADA DÍA")
print(f"{'='*65}")
print(f"\n  {'Día':<12} {'BUY WR':>8} {'SELL WR':>9} {'Mejor Acción'}")
print(f"  {'-'*58}")

for wd_name in ["Lunes","Martes","Miércoles","Jueves","Viernes"]:
    bs = day_summary[wd_name]['buy']
    ss = day_summary[wd_name]['sell']

    buy_wr  = f"{bs['wr']:.1f}%" if bs else "N/A"
    sell_wr = f"{ss['wr']:.1f}%" if ss else "N/A"

    best_wr  = max((bs['wr'] if bs else 0), (ss['wr'] if ss else 0))
    best_dir = "BUY" if (bs and (not ss or bs['wr'] >= ss['wr'])) else "SELL"

    if best_wr >= 55:
        accion = f"✅ {best_dir}"
    elif best_wr >= 45:
        accion = f"⚠️  Selectivo ({best_dir})"
    else:
        accion = "🚫 Mejor no operar"

    print(f"  {wd_name:<12} {buy_wr:>8} {sell_wr:>9}   {accion}")

print(f"\n  Total trades analizados: {len(C)}")
print(f"  PnL Global: {C['pnl_pts'].sum():+.0f} pts  (~${C['pnl_pts'].sum()*20:+,.0f}/contrato)")

T.to_csv(os.path.join(BASE_DIR, "daily_breakdown_trades.csv"), index=False)
print(f"\n✅ Guardado: daily_breakdown_trades.csv")
