"""
Análisis de viernes - últimos 3 meses - según METODOLOGIA.md (Whale Radar)
COT Index integrado: Net Lev_Money normalizado 52 semanas (0-100)
> 75 = extremo long especuladores → señal BAJISTA (contrarian)
< 25 = extremo short especuladores → señal ALCISTA (contrarian)
TODO futuro: abrir dentro/fuera del Value Profile (VAH/POC/VAL)
"""
import csv, sys
from datetime import datetime, date, timedelta
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 1. CARGAR ICT FLAGS ──────────────────────────────────────────────────────
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
        except:
            pass

# ── 2. CARGAR OHLCV 15m ──────────────────────────────────────────────────────
bars = []
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            dt = datetime.fromisoformat(r['Datetime'].replace('+00:00','').strip())
            cl = float(r.get('Close', 0) or 0)
            if cl > 0:
                bars.append(dict(dt=dt, o=float(r.get('Open',0)),
                                 h=float(r.get('High',0)), l=float(r.get('Low',0)), c=cl))
        except:
            pass
bars.sort(key=lambda x: x['dt'])

day_data = {}
for b in bars:
    d = b['dt'].date()
    if d not in day_data:
        day_data[d] = {'bars': []}
    day_data[d]['bars'].append(b)

for d_key, dd in day_data.items():
    ny = [b for b in dd['bars']
          if datetime(d_key.year, d_key.month, d_key.day, 14, 30)
             <= b['dt'] <
             datetime(d_key.year, d_key.month, d_key.day, 21, 0)]
    first = [b for b in dd['bars']
             if b['dt'].hour == 14 and b['dt'].minute == 30]
    dd['ny_bars']      = ny
    dd['first_candle'] = first[0] if first else None
    if ny:
        dd['ny_range'] = max(b['h'] for b in ny) - min(b['l'] for b in ny)
        dd['ny_open']  = ny[0]['o']
        dd['ny_close'] = ny[-1]['c']
    else:
        dd['ny_range'] = dd['ny_open'] = dd['ny_close'] = 0

# ── 3. CARGAR COT DATA Y CALCULAR COT INDEX ─────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_3yr.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d  = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'])
            ll = float(r.get('Lev_Money_Positions_Long_All', 0) or 0)
            ls = float(r.get('Lev_Money_Positions_Short_All', 0) or 0)
            al = float(r.get('Asset_Mgr_Positions_Long_All', 0) or 0)
            as_= float(r.get('Asset_Mgr_Positions_Short_All', 0) or 0)
            cot_rows.append({
                'date'     : d,
                'lev_net'  : ll - ls,       # especuladores: Long - Short
                'amgr_net' : al - as_,      # institucionales: Long - Short
                'lev_long' : ll,
                'lev_short': ls,
            })
        except:
            pass
cot_rows.sort(key=lambda x: x['date'])

# COT Index = (net - min52) / (max52 - min52) × 100  [ventana 52 semanas]
WINDOW = 52
for i, row in enumerate(cot_rows):
    start = max(0, i - WINDOW + 1)
    window_nets = [r['lev_net'] for r in cot_rows[start:i+1]]
    mn, mx = min(window_nets), max(window_nets)
    if mx != mn:
        row['cot_index'] = round((row['lev_net'] - mn) / (mx - mn) * 100, 1)
    else:
        row['cot_index'] = 50.0
    row['amgr_net_k'] = round(row['amgr_net'] / 1000, 1)

# Mapa fecha → COT (para lookup por semana)
cot_by_date = {r['date']: r for r in cot_rows}

def get_cot_for_friday(fri_date):
    """Devuelve el COT más reciente disponible antes o igual al viernes."""
    best = None
    for d, r in sorted(cot_by_date.items()):
        if d <= fri_date:
            best = r
    return best

# ── 4. CLASIFICAR PATRÓN ICT ────────────────────────────────────────────────
def classify(d, ict_row, dd):
    sh   = ict_row['sweep_hi']
    sl   = ict_row['sweep_lo']
    br   = ict_row['bull_rev']
    bear = ict_row['bear_rev']
    ret  = abs(ict_row.get('day_ret', 0))
    rng  = dd.get('ny_range', 0)
    if rng > 250 or ret > 0.01:
        return 'NEWS_DRIVE'
    if sh and not sl:
        return 'SWEEP_H_RETURN'
    if sl and not sh:
        return 'SWEEP_L_RETURN'
    if br and not bear:
        return 'EXPANSION_H'
    if bear and not br:
        return 'EXPANSION_L'
    return 'ROTATION_POC'

# ── 5. FILTRAR VIERNES ÚLTIMOS 3 MESES ──────────────────────────────────────
today  = date(2026, 3, 27)
cutoff = date(2025, 12, 27)
fridays = []

all_fri = set()
for d in day_data:
    if d.weekday() == 4 and cutoff <= d <= today:
        all_fri.add(d)
for d in ict:
    if d.weekday() == 4 and cutoff <= d <= today:
        all_fri.add(d)

for d in sorted(all_fri):
    dd = day_data.get(d, {})
    if not dd or dd.get('ny_range', 0) == 0:
        continue
    has_ict  = d in ict
    row      = ict[d] if has_ict else {'sweep_hi':False,'sweep_lo':False,
                                        'bull_rev':False,'bear_rev':False,'day_ret':0}
    pat      = classify(d, row, dd)
    f1       = dd.get('first_candle')
    ny_o     = dd.get('ny_open', 0)
    ny_c     = dd.get('ny_close', 0)
    alcista  = ny_c > ny_o if ny_o > 0 else None
    day_ret  = (row['day_ret']*100 if has_ict
                else ((ny_c - ny_o)/ny_o*100 if ny_o else 0))

    # COT
    cot = get_cot_for_friday(d)
    if cot:
        cot_idx  = cot['cot_index']
        amgr_net = cot['amgr_net_k']
        # señal contrarian
        if cot_idx >= 75:
            cot_signal = '🐻CORTO'
        elif cot_idx <= 25:
            cot_signal = '🐂LARGO'
        else:
            cot_signal = '  NEUTRO'
    else:
        cot_idx = cot_signal = amgr_net = None

    fridays.append({
        'date'       : d,
        'pattern'    : pat,
        'ny_range'   : round(dd['ny_range'], 0),
        'day_ret'    : round(day_ret, 2),
        'alcista'    : alcista,
        'f1_bull'    : bool(f1 and f1['c'] > f1['o']),
        'has_ict'    : has_ict,
        'cot_idx'    : cot_idx,
        'cot_signal' : cot_signal,
        'amgr_net_k' : amgr_net,
    })

fridays.sort(key=lambda x: x['date'])

# ── 6. IMPRIMIR ──────────────────────────────────────────────────────────────
SEP = '='*80
EMOJIS = {
    'NEWS_DRIVE':     '📰',
    'SWEEP_H_RETURN': '🐻',
    'SWEEP_L_RETURN': '🐂',
    'EXPANSION_H':    '🚀',
    'EXPANSION_L':    '💥',
    'ROTATION_POC':   '🔄',
}
DIA = ['Lun','Mar','Mie','Jue','Vie','Sab','Dom']

print(f'\n{SEP}')
print(f'  VIERNES | ÚLTIMOS 3 MESES | N={len(fridays)}  |  COT Index Lev_Money (52w)')
print(SEP)
print(f"  {'Fecha':<11} {'Patrón':<22} {'Rango':>6} {'Ret%':>6}  {'DIR':>9}  {'COT':>5}  {'Señal':>9}  {'AM Net':>7}")
print('-'*80)
for f in fridays:
    emo  = EMOJIS.get(f['pattern'], '?')
    mark = '' if f['has_ict'] else '*'
    if f['alcista'] is None:       dirstr = '     ?'
    elif f['alcista']:             dirstr = '🟢ALCI'
    else:                          dirstr = '🔴BAJI'
    cotstr = f"{f['cot_idx']:>5.1f}" if f['cot_idx'] is not None else '  N/A'
    sig    = f['cot_signal'] or '     -'
    amgr   = f"{f['amgr_net_k']:>+7.1f}k" if f['amgr_net_k'] is not None else '      -'
    nm = f"{emo}{f['pattern']}"
    print(f"  {str(f['date']):<11}{mark} {nm:<22} {f['ny_range']:>5}pts {f['day_ret']:>+5.2f}%  {dirstr}  {cotstr}  {sig}  {amgr}")

print(f"  * sin datos ICT completos")

# ── 7. RESUMEN FRECUENCIAS ───────────────────────────────────────────────────
counts = Counter(f['pattern'] for f in fridays)
total  = len(fridays)
print(f'\n{SEP}')
print(f'  PATRONES MÁS FRECUENTES (viernes, últimos 3 meses)')
print(SEP)
for pat, n in counts.most_common():
    bar = '█' * n
    print(f"  {EMOJIS.get(pat,'')} {pat:<22}  {n}x  ({n/total*100:.0f}%)  {bar}")

# ── 8. COT CRUZADO CON DIRECCIÓN ────────────────────────────────────────────
print(f'\n{SEP}')
print(f'  COT SIGNAL vs DIRECCIÓN REAL DEL DÍA')
print(SEP)
print(f"  {'COT Señal':<12} {'Día alcista':>12} {'Día bajista':>12} {'Acierto'}") 
print('-'*55)
groups = {}
for f in fridays:
    sig = f['cot_signal'] or 'NEUTRO'
    if sig not in groups:
        groups[sig] = {'alc': 0, 'baj': 0}
    if f['alcista'] is True:
        groups[sig]['alc'] += 1
    elif f['alcista'] is False:
        groups[sig]['baj'] += 1

for sig, g in sorted(groups.items()):
    tot = g['alc'] + g['baj']
    if tot == 0:
        continue
    # señal CORTO → esperas bajista → acierto si bajista
    # señal LARGO → esperas alcista → acierto si alcista
    if 'CORTO' in sig:
        hit = g['baj']
    elif 'LARGO' in sig:
        hit = g['alc']
    else:
        hit = max(g['alc'], g['baj'])
    acc = f"{hit/tot*100:.0f}%" if tot else '-'
    print(f"  {sig:<14}  {g['alc']:>10}x  {g['baj']:>10}x  {acc:>7}")

print(f'\n{SEP}')
