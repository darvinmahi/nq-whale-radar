"""
TABLA ÚLTIMOS 15 LUNES: COT + VXN + Asia + London + NY
Usa yfinance 1h para sesiones + diario para VXN + COT local
"""
import yfinance as yf, csv, sys
from datetime import date, timedelta, datetime
from statistics import mean
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── COT ────────────────────────────────────────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            cot_rows.append({'date':d,'net':ll-ls})
        except: pass
cot_rows.sort(key=lambda x:x['date'])
for i,r in enumerate(cot_rows):
    hist=[x['net'] for x in cot_rows[max(0,i-52):i+1]]
    mn,mx=min(hist),max(hist)
    r['ci']=(r['net']-mn)/(mx-mn)*100 if mx>mn else 50.0

def get_cot(monday_d):
    prev=[r for r in cot_rows if r['date']<=monday_d-timedelta(days=3)]
    return prev[-1] if prev else None

# ── DESCARGAR DATOS ─────────────────────────────────────────────────────────
print("Descargando QQQ 1h + VXN diario...")
# QQQ 1h (máximo 60 días con yfinance interval=1h)
qqq_1h = yf.download('QQQ', period='60d', interval='1h',
                     auto_adjust=True, progress=False)
if hasattr(qqq_1h.columns,'levels'):
    qqq_1h.columns = qqq_1h.columns.get_level_values(0)

# VXN diario
vxn_d = yf.download('^VXN', period='90d', interval='1d',
                    auto_adjust=True, progress=False)
if hasattr(vxn_d.columns,'levels'):
    vxn_d.columns = vxn_d.columns.get_level_values(0)

# VIX diario
vix_d = yf.download('^VIX', period='90d', interval='1d',
                    auto_adjust=True, progress=False)
if hasattr(vix_d.columns,'levels'):
    vix_d.columns = vix_d.columns.get_level_values(0)

print(f"QQQ 1h: {len(qqq_1h)} barras")

# Asegurar que el índice es UTC-aware o naive consistente
qqq_1h.index = pd.to_datetime(qqq_1h.index).tz_localize(None)

# ── CALCULAR SESIONES POR DÍA ─────────────────────────────────────────────
# UTC: Asia=22prev→08 / London=08→14:30 / NY=14:30→21
# yfinance 1h QQQ es en ET (UTC-4 en verano, UTC-5 invierno)
# QQQ 1h en ET: pre-market ~4am ET / open 9:30am ET / close 4pm ET
# Aproximaciones ET:
#  Asia    → pre-market ET: 4:00am → 9:30am  (equivale a UTC 8-13:30)
#  London  → primer tramo NY: 9:30am → 11:30am ET
#  NY full → 9:30am → 4:00pm ET
# SIMPLIFICACIÓN: con QQQ 1h en ET
#  "Asia/Pre"  = 4h-9h ET    (pre-market)
#  "London"    = 9h-11h ET   (opening + London overlap)
#  "NY"        = 11h-16h ET  (NY afternoon)

def sess_ret(bars_df, h_start, h_end):
    """Retorno de sesión: open 1ra barra → close última."""
    sel = bars_df[(bars_df.index.hour >= h_start) & (bars_df.index.hour < h_end)]
    if len(sel) < 1: return None, None
    entry = float(sel['Open'].iloc[0])
    exit_ = float(sel['Close'].iloc[-1])
    if entry == 0: return None, None
    ret = (exit_ - entry)/entry*100
    direction = '🟢BULL' if ret > 0.1 else ('🔴BEAR' if ret < -0.1 else '⚪FLAT')
    return round(ret,3), direction

# Obtener viernes anterior para VXN
def get_vxn(friday_d):
    for delta in [0,-1,-2,-3]:
        fd = friday_d + timedelta(days=delta)
        matches = vxn_d[vxn_d.index.date == fd]
        if not matches.empty:
            return round(float(matches['Close'].iloc[-1]),1)
    return None

def get_vix(friday_d):
    for delta in [0,-1,-2,-3]:
        fd = friday_d + timedelta(days=delta)
        matches = vix_d[vix_d.index.date == fd]
        if not matches.empty:
            return round(float(matches['Close'].iloc[-1]),1)
    return None

# Todos los lunes en el dataset 1h
lunes_dates = sorted(set(
    d for d in qqq_1h.index.date if date.fromisoformat(str(d)).weekday()==0
))[-15:]  # últimos 15

results = []
for lunes_d in lunes_dates:
    day_bars = qqq_1h[qqq_1h.index.date == lunes_d]
    if len(day_bars) < 3: continue

    fri_prev = lunes_d - timedelta(days=3)
    cot = get_cot(lunes_d)
    vxn = get_vxn(fri_prev)
    vix = get_vix(fri_prev)
    cot_ci = round(cot['ci'],1) if cot else 50.0
    cot_net = cot['net'] if cot else 0

    # Sesiones aproximadas en ET (QQQ)
    pre_ret, pre_dir   = sess_ret(day_bars, 4, 9)    # Pre-market ≈ Asia
    lon_ret, lon_dir   = sess_ret(day_bars, 9, 12)   # NY open ≈ London overlap
    ny_ret,  ny_dir    = sess_ret(day_bars, 12, 16)  # NY tarde

    # Día completo
    day_open  = float(day_bars['Open'].iloc[0])
    day_close = float(day_bars['Close'].iloc[-1])
    day_ret   = (day_close-day_open)/day_open*100
    day_dir   = '🟢BULL' if day_ret>0.15 else ('🔴BEAR' if day_ret<-0.15 else '⚪FLAT')

    results.append({
        'd': lunes_d, 'cot_ci': cot_ci, 'cot_net': cot_net,
        'vxn': vxn, 'vix': vix,
        'pre': (pre_ret, pre_dir), 'lon': (lon_ret, lon_dir), 'ny': (ny_ret, ny_dir),
        'day_ret': round(day_ret,3), 'day_dir': day_dir,
        'day_open': day_open, 'day_close': day_close,
    })

# ── IMPRIMIR TABLA ─────────────────────────────────────────────────────────
print(f"\n{'='*82}")
print(f"  ÚLTIMOS {len(results)} LUNES — COT + VXN + Sesiones (ET local)")
print(f"  Pre-mkt(4-9h) ≈ Asia  |  Apertura(9-12h) ≈ London  |  Tarde(12-16h) = NY")
print(f"{'='*82}")
print(f"\n  {'Fecha':<12} {'COT%':>6} {'VXN':>5} {'DÍA':>8} {'Pre/Asia':>10} {'Apertura':>10} {'NY tarde':>10}")
print("  "+"-"*72)

for r in results:
    pr = f"{r['pre'][0]:+.2f}% {r['pre'][1]}" if r['pre'][0] else "  N/A"
    lo = f"{r['lon'][0]:+.2f}% {r['lon'][1]}" if r['lon'][0] else "  N/A"
    ny = f"{r['ny'][0]:+.2f}% {r['ny'][1]}"  if r['ny'][0]  else "  N/A"
    vxn_str = f"{r['vxn']}" if r['vxn'] else "N/A"
    cot_flag = "🔴" if r['cot_ci']>75 else ("🟡" if r['cot_ci']>50 else "🟢")
    print(f"  {str(r['d']):<12} {r['cot_ci']:>5.1f}%{cot_flag} {vxn_str:>5} "
          f"{r['day_ret']:>+6.2f}%{r['day_dir'][-4:]:>6}  {pr:<18}  {lo:<18}  {ny}")

print(f"\n{'='*82}")
print("  RANKING: Lunes más BULLISH:")
bull_rank = sorted(results, key=lambda x: x['day_ret'], reverse=True)
for i,r in enumerate(bull_rank[:5],1):
    print(f"  {i}. {r['d']}  +{r['day_ret']:.2f}%  COT={r['cot_ci']:.0f}%  VXN={r['vxn']}")

print(f"\n  Lunes más BEARISH:")
bear_rank = sorted(results, key=lambda x: x['day_ret'])
for i,r in enumerate(bear_rank[:5],1):
    print(f"  {i}. {r['d']}  {r['day_ret']:.2f}%  COT={r['cot_ci']:.0f}%  VXN={r['vxn']}")

print(f"\n  PATRÓN Pre-mkt🟢 → día ¿alcista?")
pre_bull = [r for r in results if r['pre'][1] and 'BULL' in r['pre'][1]]
if pre_bull:
    dia_bull = sum(1 for r in pre_bull if r['day_ret']>0)
    print(f"  Pre-mkt BULL {len(pre_bull)} lunes → día BULL {dia_bull}/{len(pre_bull)} = {dia_bull/len(pre_bull)*100:.0f}%")

pre_bear = [r for r in results if r['pre'][1] and 'BEAR' in r['pre'][1]]
if pre_bear:
    dia_bull2 = sum(1 for r in pre_bear if r['day_ret']>0)
    print(f"  Pre-mkt BEAR {len(pre_bear)} lunes → día BULL {dia_bull2}/{len(pre_bear)} = {dia_bull2/len(pre_bear)*100:.0f}%")
print(f"{'='*82}\n")
