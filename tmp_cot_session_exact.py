"""
Backtest exacto: COT semana → sesiones NY de esa semana
Segmentado por AM_delta y LEV_zona
"""
import csv, math
from datetime import datetime, date, timedelta
from collections import defaultdict
import yfinance as yf, pandas as pd

WINDOW = 52

# ── COT ───────────────────────────────────────────────────────────────
print("Cargando COT...")
rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d   = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
            al  = int(r.get('Asset_Mgr_Positions_Long_All',  0) or 0)
            as_ = int(r.get('Asset_Mgr_Positions_Short_All', 0) or 0)
            ll  = int(r.get('Lev_Money_Positions_Long_All',  0) or 0)
            ls  = int(r.get('Lev_Money_Positions_Short_All', 0) or 0)
            rows.append({'date':d, 'am_net':al-as_, 'lev_net':ll-ls})
        except: pass
rows.sort(key=lambda x: x['date'])

for i, r in enumerate(rows):
    r['am_delta'] = r['am_net'] - rows[i-1]['am_net'] if i > 0 else 0
    w = [x['lev_net'] for x in rows[max(0,i-WINDOW+1):i+1]]
    r['lev_idx'] = round((r['lev_net']-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0

print(f"  → {len(rows)} semanas COT ({rows[0]['date']} → {rows[-1]['date']})")

def get_cot_week(d):
    """Devuelve el COT vigente para una fecha dada (publicado el viernes anterior)."""
    # COT se publica viernes — datos del martes de esa semana
    prev = [r for r in rows if r['date'] <= d]
    return prev[-1] if prev else None

# ── NQ 15min ─────────────────────────────────────────────────────────
print("Cargando NQ 15min...")
bars = []
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            # Las horas vienen en UTC — convertir a ET (UTC-5, ignoramos DST por simplicidad)
            et = datetime.fromisoformat(r['Datetime'].replace('+00:00','')) - timedelta(hours=5)
            cl = float(r['Close']); hi = float(r['High']); lo = float(r['Low']); op = float(r['Open'])
            if cl > 0:
                bars.append({'et':et, 'c':cl, 'h':hi, 'l':lo, 'o':op})
        except: pass
bars.sort(key=lambda x: x['et'])

by_date = defaultdict(list)
for b in bars:
    by_date[b['et'].date()].append(b)
print(f"  → {len(by_date)} días con datos")

# ── SESIONES NY ────────────────────────────────────────────────────────
def ny_session(d):
    """Calcula open/close NY session (9:30 - 16:00 ET)."""
    bs = by_date.get(d, [])
    ny = [b for b in bs if (b['et'].hour==9 and b['et'].minute>=30) or
          (b['et'].hour>9 and b['et'].hour<16)]
    if len(ny) < 6: return None
    ny_o = ny[0]['o']
    ny_c = ny[-1]['c']
    ny_h = max(b['h'] for b in ny)
    ny_l = min(b['l'] for b in ny)
    pts  = round(ny_c - ny_o, 0)
    pct  = round((ny_c - ny_o) / ny_o * 100, 2)
    return {'open':ny_o, 'close':ny_c, 'high':ny_h, 'low':ny_l,
            'pts':pts, 'pct':pct,
            'dir':'BULL' if pts>10 else ('BEAR' if pts<-10 else 'FLAT')}

print("Construyendo tabla COT semana → sesiones NY de esa semana...")

# Para cada semana COT, asignar las sesiones NY Mon-Fri de la SEMANA SIGUIENTE
# (realista: el COT se publica el viernes, así que lo aplicas la siguiente semana)
sessions = []
all_dates = sorted(by_date.keys())

for i, cot in enumerate(rows[WINDOW:], start=WINDOW):
    cot_date = cot['date']  # Martes del reporte
    # Siguiente lunes
    days = (7 - cot_date.weekday()) % 7
    if days == 0: days = 7
    mon = cot_date + timedelta(days=days)

    # Sesiones NY de Mon a Fri de esa semana
    for offset in range(5):
        day = mon + timedelta(days=offset)
        if day.weekday() >= 5: continue
        ny = ny_session(day)
        if ny is None: continue
        sessions.append({
            'cot_date':  cot_date,
            'day':       day,
            'dow':       day.weekday(),
            'am_delta':  cot['am_delta'],
            'lev_idx':   cot['lev_idx'],
            'am_net':    cot['am_net'],
            'lev_net':   cot['lev_net'],
            **{f'ny_{k}': v for k,v in ny.items()}
        })

N = len(sessions)
print(f"  → {N} sesiones NY analizadas")

SEP = "=" * 80

# ── FUNCIÓN HELPER ─────────────────────────────────────────────────────
def stats(slist):
    n = len(slist)
    if n == 0: return None
    bull   = sum(1 for s in slist if s['ny_dir']=='BULL')
    bear   = sum(1 for s in slist if s['ny_dir']=='BEAR')
    flat   = n - bull - bear
    avg_p  = sum(s['ny_pts'] for s in slist) / n
    avg_up = sum(s['ny_pts'] for s in slist if s['ny_dir']=='BULL') / bull if bull else 0
    avg_dn = sum(s['ny_pts'] for s in slist if s['ny_dir']=='BEAR') / bear if bear else 0
    big200 = sum(1 for s in slist if abs(s['ny_pts']) >= 200)
    return {'n':n,'bull':bull,'bear':bear,'flat':flat,
            'bull_pct':bull/n*100,'bear_pct':bear/n*100,
            'avg_pts':avg_p,'avg_up':avg_up,'avg_dn':avg_dn,
            'big200_pct':big200/n*100}

def fmt(st, signal=None):
    if st is None: return "  —"
    ok = ""
    if signal=='BULL': ok = "✅" if st['bull_pct']>=55 else ("🟡" if st['bull_pct']>=50 else "❌")
    elif signal=='BEAR': ok = "✅" if st['bear_pct']>=55 else ("🟡" if st['bear_pct']>=50 else "❌")
    return (f"n={st['n']:>4}  BULL={st['bull_pct']:>4.0f}%  BEAR={st['bear_pct']:>4.0f}%  "
            f"avgPts={st['avg_pts']:>+6.0f}  up≈{st['avg_up']:>+5.0f}  dn≈{st['avg_dn']:>+5.0f}pt  {ok}")

# ── 1. AM DELTA BUCKETS ────────────────────────────────────────────────
print()
print(SEP)
print("  REGLA 1: AM DELTA → SESIONES NY DE LA SEMANA SIGUIENTE")
print(SEP)
buckets = {
    ">+5000 (BlackRock compra fuerte)":   [s for s in sessions if s['am_delta'] >  5000],
    "-5000 a +5000 (Neutral)":            [s for s in sessions if -5000 <= s['am_delta'] <= 5000],
    "<-5000 (BlackRock reduce)":          [s for s in sessions if s['am_delta'] < -5000],
    "<-10000 (BlackRock liquida masivo)": [s for s in sessions if s['am_delta'] < -10000],
}
for label, slist in buckets.items():
    st = stats(slist)
    sig = 'BULL' if '+' in label or 'compra' in label else ('BEAR' if 'liquida' in label or 'reduce' in label else None)
    print(f"\n  {label}")
    print(f"  {fmt(st, sig)}")

# ── 2. LEV ZONA ───────────────────────────────────────────────────────
print()
print(SEP)
print("  REGLA 2: LEV MONEY ZONA 52w → SESIONES NY")
print(SEP)
lev_buckets = {
    ">80% XBULL":    [s for s in sessions if s['lev_idx'] > 80],
    "60-80% BULL":   [s for s in sessions if 60 < s['lev_idx'] <= 80],
    "40-60% NEUT":   [s for s in sessions if 40 <= s['lev_idx'] <= 60],
    "20-40% BEAR":   [s for s in sessions if 20 <= s['lev_idx'] < 40],
    "<20% XBEAR":    [s for s in sessions if s['lev_idx'] < 20],
}
for label, slist in lev_buckets.items():
    st = stats(slist)
    sig = 'BULL' if 'BULL' in label else ('BEAR' if 'BEAR' in label else None)
    print(f"\n  LEV {label}")
    print(f"  {fmt(st, sig)}")

# ── 3. COMBINACIÓN AM DELTA × LEV ZONA ────────────────────────────────
print()
print(SEP)
print("  COMBINACIÓN: AM DELTA × LEV ZONA → SESIONES NY")
print(SEP)
combos = [
    (">+5k", "BULL_LEV",  lambda s: s['am_delta']> 5000 and s['lev_idx']>60),
    (">+5k", "BEAR_LEV",  lambda s: s['am_delta']> 5000 and s['lev_idx']<40),
    ("<-5k", "BULL_LEV",  lambda s: s['am_delta']<-5000 and s['lev_idx']>60),
    ("<-5k", "BEAR_LEV",  lambda s: s['am_delta']<-5000 and s['lev_idx']<40),
    ("<-10k","BULL_LEV",  lambda s: s['am_delta']<-10000 and s['lev_idx']>60),
    ("<-10k","BEAR_LEV",  lambda s: s['am_delta']<-10000 and s['lev_idx']<40),
]
for am_label, lev_label, fn in combos:
    slist = [s for s in sessions if fn(s)]
    if not slist: continue
    st = stats(slist)
    print(f"\n  AM{am_label} + LEV {lev_label}")
    print(f"  {fmt(st)}")

# ── 4. POR DÍA DE SEMANA ─────────────────────────────────────────────
print()
print(SEP)
print("  AM DELTA >+5k × DÍA DE SEMANA → SESIONES NY")
print("  (¿Cuándo es más poderosa la señal alcista?)")
print(SEP)
DOW = ["Lun","Mar","Mié","Jue","Vie"]
buy_sessions = [s for s in sessions if s['am_delta'] > 5000]
for d in range(5):
    slist = [s for s in buy_sessions if s['dow']==d]
    if not slist: continue
    st = stats(slist)
    print(f"\n  AM>+5k — {DOW[d]}:")
    print(f"  {fmt(st, 'BULL')}")

# ── 5. RESUMEN EJECUTIVO ──────────────────────────────────────────────
print()
print(SEP)
print("  RESUMEN EJECUTIVO — REGLAS CONFIRMADAS CON DATOS")
print(SEP)
am_buy  = stats([s for s in sessions if s['am_delta'] > 5000])
am_sell = stats([s for s in sessions if s['am_delta'] < -10000])
lev_bull= stats([s for s in sessions if s['lev_idx'] > 60])
lev_bear= stats([s for s in sessions if s['lev_idx'] < 40])
all_st  = stats(sessions)

print(f"""
  BASELINE (todas las sesiones):        BULL={all_st['bull_pct']:.0f}%  BEAR={all_st['bear_pct']:.0f}%  avg={all_st['avg_pts']:+.0f}pt
  
  REGLA 1A — AM Delta >+5k:             BULL={am_buy['bull_pct']:.0f}%  BEAR={am_buy['bear_pct']:.0f}%  avg={am_buy['avg_pts']:+.0f}pt  (n={am_buy['n']})
  REGLA 1B — AM Delta <-10k (alerta):   BULL={am_sell['bull_pct']:.0f}%  BEAR={am_sell['bear_pct']:.0f}%  avg={am_sell['avg_pts']:+.0f}pt  (n={am_sell['n']})
  
  REGLA 2A — LEV >60% (alcista):        BULL={lev_bull['bull_pct']:.0f}%  BEAR={lev_bull['bear_pct']:.0f}%  avg={lev_bull['avg_pts']:+.0f}pt  (n={lev_bull['n']})
  REGLA 2B — LEV <40% (bajista):        BULL={lev_bear['bull_pct']:.0f}%  BEAR={lev_bear['bear_pct']:.0f}%  avg={lev_bear['avg_pts']:+.0f}pt  (n={lev_bear['n']})
""")
