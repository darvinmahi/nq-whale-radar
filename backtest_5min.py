"""
SISTEMA DEFINITIVO — BACKTEST 60 DÍAS EN VELAS DE 5 MINUTOS
=============================================================
Misma lógica completa: ICT + Profile + OTE + Silver Bullet + EMA200 + COT + VXN
Pero con velas de 5 minutos para mayor precisión en entradas/stops.

Datos: últimos 60 días (máximo disponible en Yahoo Finance gratis)
Velas: 5 minutos (resolución alta)
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COT_CSV  = os.path.join(BASE_DIR, "data", "cot", "nasdaq_cot_historical_study.csv")

print("="*70)
print("  SISTEMA DEFINITIVO — 60 DÍAS | VELAS 5 MINUTOS")
print("  ICT + Profile + OTE + Silver Bullet + EMA200 + COT + VXN")
print("="*70)

# ─── DATOS 5 MINUTOS ─────────────────────────────────────────────────────────
print("\n📡 Descargando NQ=F en 5 minutos (60 días)...")
raw = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index   = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['minute']  = raw.index.minute
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek
raw['volume']  = raw['Volume'].fillna(1).replace(0, 1)
print(f"  ✅ {len(raw)} velas de 5 minutos | {raw['date'].nunique()} días")

# ─── DATOS DIARIOS: EMA200 + VXN ─────────────────────────────────────────────
print("📡 Descargando indicadores diarios...")
ndx_d = yf.download("NQ=F", period="300d", interval="1d", progress=False)
if isinstance(ndx_d.columns, pd.MultiIndex):
    ndx_d.columns = ndx_d.columns.get_level_values(0)
ndx_d.index = pd.to_datetime(ndx_d.index)
if ndx_d.index.tz is None:
    ndx_d.index = ndx_d.index.tz_localize('UTC')
ndx_d.index  = ndx_d.index.tz_convert('America/New_York')
ndx_d['EMA200']       = ndx_d['Close'].ewm(span=200, adjust=False).mean()
ndx_d['above_ema200'] = ndx_d['Close'] > ndx_d['EMA200']
ema200_map = {d.date(): bool(v) for d, v in ndx_d['above_ema200'].items()}

vxn_d = yf.download("^VXN", period="60d", interval="1d", progress=False)
if isinstance(vxn_d.columns, pd.MultiIndex):
    vxn_d.columns = vxn_d.columns.get_level_values(0)
vxn_d.index = pd.to_datetime(vxn_d.index)
if vxn_d.index.tz is None:
    vxn_d.index = vxn_d.index.tz_localize('UTC')
vxn_d.index = vxn_d.index.tz_convert('America/New_York')
vxn_map = {d.date(): float(v) for d, v in vxn_d['Close'].items()}

# ─── COT ─────────────────────────────────────────────────────────────────────
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
except: cot_ok = False

def get_cot(d):
    if not cot_ok: return None, None
    sub = cot[cot['date_key'] <= d]
    if sub.empty: return None, None
    row = sub.iloc[-1]
    return float(row['net_chg']), float(row['cot_idx'])

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

# ─── PROFILE ─────────────────────────────────────────────────────────────────
def calc_profile(sdf, n_bins=40, pct=0.70):
    if len(sdf) < 2: return None, None, None
    lo, hi = float(sdf['Low'].min()), float(sdf['High'].max())
    if hi <= lo: return (hi+lo)/2, hi, lo
    bins = np.linspace(lo, hi, n_bins+1)
    vb   = np.zeros(n_bins)
    for _, r in sdf.iterrows():
        rlo, rhi, rv = float(r['Low']), float(r['High']), float(r['volume'])
        rng = rhi-rlo if rhi>rlo else 1e-9
        for b in range(n_bins):
            ov = min(rhi, bins[b+1]) - max(rlo, bins[b])
            if ov > 0: vb[b] += rv*(ov/rng)
    tot = vb.sum()
    if tot == 0: return (hi+lo)/2, hi, lo
    pi = int(np.argmax(vb));  poc = (bins[pi]+bins[pi+1])/2
    acc = vb[pi]; hi_i, lo_i = pi, pi
    while acc < tot*pct:
        cu = hi_i+1<n_bins; cd = lo_i-1>=0
        if not cu and not cd: break
        vu = vb[hi_i+1] if cu else -1
        vd = vb[lo_i-1] if cd else -1
        if vu >= vd: hi_i+=1; acc+=vu
        else:        lo_i-=1; acc+=vd
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

def rec(col, res, ex, entry, direc, day_name, d):
    if res == "NO_ENTRY": return
    pnl = (ex-entry) if direc=="BUY" else (entry-ex)
    col.append({"date": str(d), "weekday": day_name, "direction": direc,
                "result": res, "pnl_pts": round(pnl, 2)})

# ─── BACKTEST ─────────────────────────────────────────────────────────────────
print("\n🔍 Ejecutando backtest de 60 días en 5 minutos...")

t1 = []; t2 = []; t3 = []; t4 = []; t5 = []

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1
    if wd not in DAYS: continue

    # Sesiones en velas de 5 minutos
    # Asia: 00:00 - 03:55 NY
    asia   = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    # Londres: 04:00 - 08:55 NY
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    # NY completo: 09:30 - 11:55
    ny_all = day[(day['hour'] == 9)  & (day['minute'] >= 30) |
                  (day['hour'] == 10) |
                  (day['hour'] == 11)]
    # Silver Bullet: 09:30 - 10:00 (ventana de 30 min con 5m = 6 velas)
    ny_sb  = day[(day['hour'] == 9) & (day['minute'] >= 30)]

    if asia.empty or london.empty or len(ny_all) < 3 or len(ny_sb) < 1: continue
    if len(asia) < 3: continue

    asia_hi = float(asia['High'].max())
    asia_lo = float(asia['Low'].min())
    if asia_hi - asia_lo < 10: continue

    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())
    swept_lo = lon_lo < asia_lo
    swept_hi = lon_hi > asia_hi
    if swept_lo == swept_hi: continue

    # Volume Profile de Asia + Londres
    poc, vah, val = calc_profile(day[(day['hour'] >= 0) & (day['hour'] < 9)])
    if poc is None or val is None or vah is None: continue
    if (vah - val) < 5: continue

    # ICT árbol
    if   wd == 0 and swept_lo:     direction = "BUY"
    elif wd in [1,2] and swept_hi: direction = "SELL"
    elif wd == 3 and swept_hi:     direction = "SELL"
    elif wd == 4 and swept_lo:     direction = "BUY"
    else: continue

    # Indicadores
    above_ema200 = ema200_map.get(d, True)
    vxn_val      = vxn_map.get(d, 20.0)
    cot_chg, cot_idx = get_cot(d)

    ema_ok = (direction=="BUY" and above_ema200) or (direction=="SELL" and not above_ema200)
    vxn_ok = vxn_val < 35
    cot_ok2 = True
    if cot_chg is not None:
        bull = cot_chg > 0 or (cot_idx and cot_idx < 30)
        bear = cot_chg < 0 or (cot_idx and cot_idx > 70)
        if direction=="BUY"  and bear and not bull: cot_ok2 = False
        if direction=="SELL" and bull and not bear: cot_ok2 = False

    # Niveles
    if direction == "BUY":
        e_base = float(val); t_base = float(vah); s_base = lon_lo-(float(val)-lon_lo)*0.2
        swing  = asia_hi - lon_lo
        e_ote  = max(asia_hi - swing*0.618, float(val)); s_ote = lon_lo - swing*0.05
    else:
        e_base = float(vah); t_base = float(val); s_base = lon_hi+(lon_hi-float(vah))*0.2
        swing  = lon_hi - asia_lo
        e_ote  = min(asia_lo + swing*0.618, float(vah)); s_ote = lon_hi + swing*0.05

    nb = ny_all.reset_index(drop=True)
    sb = ny_sb.reset_index(drop=True)

    r,e = sim(e_base, t_base, s_base, nb, direction); rec(t1,r,e,e_base,direction,DAYS[wd],d)
    if ema_ok:
        r,e = sim(e_base, t_base, s_base, nb, direction); rec(t2,r,e,e_base,direction,DAYS[wd],d)
        r,e = sim(e_ote,  t_base, s_ote,  nb, direction); rec(t3,r,e,e_ote, direction,DAYS[wd],d)
        r,e = sim(e_ote,  t_base, s_ote,  sb, direction); rec(t4,r,e,e_ote, direction,DAYS[wd],d)
    if ema_ok and vxn_ok and cot_ok2:
        r,e = sim(e_ote,  t_base, s_ote,  sb, direction); rec(t5,r,e,e_ote, direction,DAYS[wd],d)

# ─── RESULTADOS ──────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  📊 RESULTADOS — 60 DÍAS | VELAS 5 MINUTOS")
print(f"{'='*70}\n")

def show(col, label):
    if not col: print(f"  ❌ {label}: sin datos\n"); return 0,0,0
    t = pd.DataFrame(col)
    c = t[t['result'].isin(['WIN','LOSS'])]
    if c.empty: print(f"  ❌ {label}: sin cerrados\n"); return 0,0,0
    n=len(c); w=len(c[c['result']=='WIN'])
    wr=w/n*100
    aw=c[c['result']=='WIN']['pnl_pts'].mean() if w>0 else 0
    al=c[c['result']=='LOSS']['pnl_pts'].mean() if (n-w)>0 else 0
    rr=abs(aw/al) if al!=0 else 0
    pnl=c['pnl_pts'].sum()
    ic="🔥" if wr>=65 else ("✅" if wr>=55 else ("⚠️" if wr>=45 else "❌"))
    print(f"  {ic} {label}")
    print(f"     Trades:{n:3d} | WR:{wr:5.1f}% | RR:1:{rr:.2f} | PnL:{pnl:+.1f}pts (~${pnl*20:+,.0f})")
    for day in ["Lunes","Martes","Miércoles","Jueves","Viernes"]:
        s=c[c['weekday']==day]
        if len(s)==0: continue
        ww,nn=len(s[s['result']=='WIN']),len(s)
        fl=" 🔥" if ww/nn>=0.70 else (" ✅" if ww/nn>=0.60 else "")
        print(f"     {day:<12} WR:{ww/nn*100:5.1f}% n={nn:2d} PnL:{s['pnl_pts'].sum():+.1f}pts{fl}")
    print()
    return wr,pnl*20,rr

r1=show(t1,"BASE — ICT + Profile (5m)")
r2=show(t2,"+ EMA200")
r3=show(t3,"+ EMA200 + OTE 61.8%")
r4=show(t4,"+ EMA200 + OTE + Silver Bullet (30m ventana)")
r5=show(t5,"COMPLETO — + COT + VXN")

print(f"{'='*70}")
print(f"  🏆 RANKING FINAL — 60 DÍAS EN 5 MINUTOS")
print(f"{'='*70}")
print(f"  {'Sistema':<46} {'WR':>6}  {'RR':>6}  {'PnL 60 días':>12}")
print(f"  {'-'*72}")
for lbl,rs in [
    ("BASE (ICT + Profile 5m)",             r1),
    ("+ EMA200",                            r2),
    ("+ EMA200 + OTE",                      r3),
    ("+ EMA200 + OTE + Silver Bullet",      r4),
    ("COMPLETO (todo: EMA200+OTE+SB+COT+VXN)", r5),
]:
    wr,p,rr = rs
    ic="🔥" if wr>=65 else ("✅" if wr>=55 else "  ")
    print(f"  {ic} {lbl:<44} {wr:>5.1f}%  1:{rr:>4.2f}  ${p:>+11,.0f}")

pd.DataFrame(t5).to_csv(os.path.join(BASE_DIR,"sistema_5m_trades.csv"),index=False)
print(f"\n✅ Guardado: sistema_5m_trades.csv")
print(f"📅 Días analizados: {raw['date'].nunique()} días | Período: {raw['date'].min()} — {raw['date'].max()}")
