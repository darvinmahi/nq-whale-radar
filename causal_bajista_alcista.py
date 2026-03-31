"""
Análisis causal: ¿Por qué cada viernes fue bajista o alcista?
Compara señales disponibles para los 3 alcistas vs los 9 bajistas.
"""
import csv, sys
from datetime import datetime, date

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── CARGA DE DATOS ──────────────────────────────────────────────────────────

# 1. ICT flags diarios
ict = {}
with open('data/research/ict_master_strategy.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['date'])
            ict[d] = {
                'sweep_hi': r.get('ny_sweep_lon_hi','').lower()=='true',
                'sweep_lo': r.get('ny_sweep_lon_lo','').lower()=='true',
                'bull_rev': r.get('bull_reversal','').lower()=='true',
                'bear_rev': r.get('bear_reversal','').lower()=='true',
                'day_ret':  float(r.get('day_return', 0) or 0),
            }
        except: pass

# 2. SMC history (FVG, volumen, bullish_ob)
smc = {}
with open('data/research/ndx_smc_history.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Date'][:10])
            smc[d] = {
                'close' : float(r.get('Close', 0) or 0),
                'open'  : float(r.get('Open', 0) or 0),
                'high'  : float(r.get('High', 0) or 0),
                'low'   : float(r.get('Low', 0) or 0),
                'vol'   : float(r.get('Volume', 0) or 0),
                'fvg_up'   : r.get('fvg_up','').lower()=='true',
                'fvg_down' : r.get('fvg_down','').lower()=='true',
                'high_vol' : r.get('high_vol','').lower()=='true',
                'bull_ob'  : r.get('bullish_ob','').lower()=='true',
                'is_down'  : r.get('is_down_candle','').lower()=='true',
            }
        except: pass

# 3. OHLCV 15m por día
bars = []
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            dt = datetime.fromisoformat(r['Datetime'].replace('+00:00','').strip())
            cl = float(r.get('Close', 0) or 0)
            if cl > 0:
                bars.append(dict(dt=dt, o=float(r.get('Open',0)),
                                 h=float(r.get('High',0)), l=float(r.get('Low',0)), c=cl,
                                 v=float(r.get('Volume',0) or 0)))
        except: pass
bars.sort(key=lambda x: x['dt'])

day_15m = {}
for b in bars:
    d = b['dt'].date()
    if d not in day_15m: day_15m[d] = []
    day_15m[d].append(b)

def ny_bars_of(d):
    return [b for b in day_15m.get(d,[])
            if datetime(d.year,d.month,d.day,14,30)
               <= b['dt'] <
               datetime(d.year,d.month,d.day,21,0)]

# ── FUNCIÓN: construir perfil de un viernes ─────────────────────────────────
def build_profile(fri):
    from datetime import timedelta
    ny = ny_bars_of(fri)
    if not ny:
        return None

    # datos básicos NY
    ny_open  = ny[0]['o']
    ny_close = ny[-1]['c']
    ny_high  = max(b['h'] for b in ny)
    ny_low   = min(b['l'] for b in ny)
    ny_range = ny_high - ny_low
    alcista  = ny_close > ny_open

    # primera vela 9:30
    f1 = next((b for b in ny if b['dt'].hour==14 and b['dt'].minute==30), None)
    f1_bull = bool(f1 and f1['c'] > f1['o'])

    # primera hora (9:30-10:30 ET = 14:30-15:30 UTC)
    h1 = [b for b in ny if b['dt'] <= datetime(fri.year,fri.month,fri.day,15,30)]
    h1_ret = (h1[-1]['c'] - ny_open) / ny_open * 100 if h1 else 0
    h1_bull = h1_ret > 0

    # gap vs jueves previo
    thu = fri - timedelta(days=1)
    thu_smc = smc.get(thu)
    gap_pct = ((ny_open - thu_smc['close']) / thu_smc['close'] * 100) if thu_smc else 0
    gap_up  = gap_pct > 0.05   # > 0.05% gap alcista

    # jueves: ¿fue bajista?
    thu_bajista = thu_smc['is_down'] if thu_smc else None
    thu_fvg_u   = thu_smc['fvg_up']   if thu_smc else False
    thu_fvg_d   = thu_smc['fvg_down'] if thu_smc else False
    thu_high_v  = thu_smc['high_vol'] if thu_smc else False

    # propio viernes SMC
    fri_smc = smc.get(fri, {})
    fri_high_v = fri_smc.get('high_vol', False)
    fri_fvg_d  = fri_smc.get('fvg_down', False)
    fri_fvg_u  = fri_smc.get('fvg_up', False)

    # ICT flags del viernes
    ict_f = ict.get(fri, {})

    return {
        'date'       : fri,
        'alcista'    : alcista,
        'ny_ret'     : round((ny_close-ny_open)/ny_open*100,2),
        'ny_range'   : round(ny_range,0),
        'f1_bull'    : f1_bull,
        'f1_match'   : f1_bull == alcista,
        'h1_bull'    : h1_bull,
        'h1_ret'     : round(h1_ret,2),
        'h1_match'   : h1_bull == alcista,
        'gap_pct'    : round(gap_pct,3),
        'gap_up'     : gap_up,
        'thu_bajo'   : thu_bajista,
        'thu_fvg_u'  : thu_fvg_u,
        'thu_fvg_d'  : thu_fvg_d,
        'thu_high_v' : thu_high_v,
        'fri_high_v' : fri_high_v,
        'fri_fvg_d'  : fri_fvg_d,
        'sweep_hi'   : ict_f.get('sweep_hi', False),
        'sweep_lo'   : ict_f.get('sweep_lo', False),
        'bull_rev'   : ict_f.get('bull_rev', False),
        'bear_rev'   : ict_f.get('bear_rev', False),
    }

# ── VIERNES DEL ANÁLISIS ────────────────────────────────────────────────────
from datetime import timedelta
VIERNES = [
    date(2026, 1, 2),  date(2026, 1, 9),  date(2026, 1, 16),
    date(2026, 1, 23), date(2026, 1, 30), date(2026, 2, 6),
    date(2026, 2, 13), date(2026, 2, 20), date(2026, 2, 27),
    date(2026, 3, 6),  date(2026, 3, 13), date(2026, 3, 20),
]

profiles = [build_profile(d) for d in VIERNES]
profiles = [p for p in profiles if p]

alcistas = [p for p in profiles if p['alcista']]
bajistas = [p for p in profiles if not p['alcista']]

# ── IMPRIMIR DETALLE ────────────────────────────────────────────────────────
SEP = '='*72

def avg(lst, key):
    vals = [x[key] for x in lst if isinstance(x[key], (int, float))]
    return sum(vals)/len(vals) if vals else 0

def pct_true(lst, key):
    vals = [x[key] for x in lst if isinstance(x[key], bool)]
    return sum(vals)/len(vals)*100 if vals else 0

def mark(val):
    """Marca ✓ si es True/positivo, ✗ si no, - si es None."""
    if val is None: return '  -'
    if isinstance(val, bool): return '✓' if val else '✗'
    return f'{val:+.2f}%'

print(f'\n{SEP}')
print(f'  DETALLE SEÑALES POR VIERNES  ({len(bajistas)} bajistas | {len(alcistas)} alcistas)')
print(SEP)

for group, label, emoji in [(bajistas,'BAJISTAS 🔴','baj'), (alcistas,'ALCISTAS 🟢','alc')]:
    print(f'\n  ── {label} ──')
    print(f"  {'Fecha':<12} {'Ret%':>6} {'Gap':>6} {'1rV':>4} {'1rH':>5} {'JueBaj':>7} {'Swp↑':>5} {'Swp↓':>5} {'BRev':>5} {'FVGd':>5}")
    print('  ' + '-'*65)
    for p in group:
        print(f"  {str(p['date']):<12} {p['ny_ret']:>+5.2f}% {p['gap_pct']:>+5.2f}% "
              f"{'🐂' if p['f1_bull'] else '🐻':>4} {p['h1_ret']:>+5.2f}% "
              f"{mark(p['thu_bajo']):>7} {mark(p['sweep_hi']):>5} {mark(p['sweep_lo']):>5} "
              f"{mark(p['bear_rev']):>5} {mark(p['fri_fvg_d']):>5}")

# ── COMPARACIÓN ESTADÍSTICA ─────────────────────────────────────────────────
print(f'\n\n{SEP}')
print(f'  COMPARACIÓN ESTADÍSTICA: ¿QUÉ DIFERENCIÓ AL ALCISTA DEL BAJISTA?')
print(SEP)
print(f"  {'Señal':<28} {'BAJISTAS':>10} {'ALCISTAS':>10}  {'Diferencia'}")
print('  ' + '-'*65)

comparaciones = [
    ('Gap alcista (>0.05%)',        'gap_up'),
    ('1ra vela alcista (9:30)',      'f1_bull'),
    ('1ra hora alcista',             'h1_bull'),
    ('1ra vela coincide dirección',  'f1_match'),
    ('1ra hora coincide dirección',  'h1_match'),
    ('Jueves previo bajista',        'thu_bajo'),
    ('Jueves con FVG alcista',       'thu_fvg_u'),
    ('Jueves con FVG bajista',       'thu_fvg_d'),
    ('Jueves con alto volumen',      'thu_high_v'),
    ('Viernes alto volumen',         'fri_high_v'),
    ('Sweep High (London)',          'sweep_hi'),
    ('Sweep Low (London)',           'sweep_lo'),
    ('Bear Reversal',                'bear_rev'),
    ('Bull Reversal',                'bull_rev'),
]

for label, key in comparaciones:
    pb = pct_true(bajistas, key)
    pa = pct_true(alcistas, key)
    diff = pa - pb
    arrow = '⬆' if diff > 15 else ('⬇' if diff < -15 else ' ')
    print(f"  {label:<28} {pb:>9.0f}%  {pa:>9.0f}%  {arrow} {diff:>+5.0f}pp")

# ── CONCLUSIÓN ────────────────────────────────────────────────────────────────
print(f'\n{SEP}')
print(f'  RESUMEN: PATRONES QUE DIFERENCIAN ALCISTA vs BAJISTA')
print(SEP)

# Buscar señales con mayor diferencia
diffs = []
for label, key in comparaciones:
    pb = pct_true(bajistas, key)
    pa = pct_true(alcistas, key)
    diffs.append((abs(pa-pb), label, pa-pb))
diffs.sort(reverse=True)

print()
print('  Top señales diferenciadoras:')
for delta, label, diff in diffs[:6]:
    if diff > 0:
        print(f'  ✅ {label}: más frecuente en ALCISTAS ({diff:+.0f}pp)')
    else:
        print(f'  🚨 {label}: más frecuente en BAJISTAS ({diff:+.0f}pp)')

h1_baj_avg = avg(bajistas,'h1_ret')
h1_alc_avg = avg(alcistas,'h1_ret')
gap_baj_avg = avg(bajistas,'gap_pct')
gap_alc_avg = avg(alcistas,'gap_pct')
print(f'\n  Retorno 1ra hora promedio → Bajistas: {h1_baj_avg:+.2f}%  Alcistas: {h1_alc_avg:+.2f}%')
print(f'  Gap apertura promedio     → Bajistas: {gap_baj_avg:+.3f}%  Alcistas: {gap_alc_avg:+.3f}%')
print(f'\n{SEP}\n')
