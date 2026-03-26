"""
lunes_cot_cruce.py
Cruza cada sesion LUNES con el COT Index de su semana.
COT se publica viernes → aplica al lunes siguiente.
"""
import json
from datetime import datetime, timedelta

with open('data/research/backtest_5dias_6meses.json', encoding='utf-8') as f:
    bt = json.load(f)

with open('data/cot_index_weekly.json', encoding='utf-8') as f:
    cot_raw = json.load(f)

# Construir lookup COT: semana (lunes de esa semana) -> cot_index
# El JSON tiene la fecha del lunes de cada semana de reporte
cot_map = {}
for entry in cot_raw:
    d = datetime.strptime(entry['week'].strip(), '%Y-%m-%d').date()
    cot_map[d] = entry['cot_index']

def get_cot_for_monday(monday_date):
    """
    El COT publicado el VIERNES anterior aplica al LUNES.
    La key en cot_index_weekly.json es el LUNES de la semana de reporte.
    Buscamos la semana mas cercana anterior o igual.
    """
    from datetime import date
    best = None
    best_idx = None
    for key_d, val in cot_map.items():
        if key_d <= monday_date:
            if best is None or key_d > best:
                best = key_d
                best_idx = val
    return best, best_idx

def cot_label(idx):
    if idx is None: return 'N/A'
    if idx >= 70:   return 'BULL FUERTE (>=70)'
    if idx >= 50:   return 'BULL MODERADO (50-69)'
    if idx >= 30:   return 'NEUTRO (30-49)'
    if idx >= 10:   return 'BEAR MODERADO (10-29)'
    return             'BEAR EXTREMO (<10)'

lunes_sessions = bt['by_day']['LUNES']['sessions_detail']

print('=' * 72)
print('LUNES + COT INDEX — Cruce completo')
print('=' * 72)
print(f'{"Fecha":<14} {"Pat":<18} {"Dir":<8} {"Rango":>7} | {"COT":>6} | {"COT Label":<25} | Match?')
print('-' * 72)

matches = 0
totals  = 0

for s in lunes_sessions:
    date_str  = s['date']
    monday    = datetime.strptime(date_str, '%Y-%m-%d').date()
    pattern   = s['pattern']
    direction = s['direction']
    ny_range  = s['ny_range']

    cot_date, cot_idx = get_cot_for_monday(monday)
    label = cot_label(cot_idx)

    # Match: COT >=50 y sesion BULLISH  OR  COT <50 y sesion BEARISH
    if cot_idx is not None:
        cot_bull = cot_idx >= 50
        sess_bull = direction == 'BULLISH'
        match = '✅' if cot_bull == sess_bull else '❌'
        if cot_bull == sess_bull:
            matches += 1
        totals += 1
    else:
        match = '—'

    dir_arrow = '🟢' if direction == 'BULLISH' else '🔴'
    cot_str = f'{cot_idx:.1f}' if cot_idx is not None else 'N/A'

    print(f'{date_str:<14} {pattern:<18} {dir_arrow} {direction:<7} {ny_range:>7.1f}pts | {cot_str:>6} | {label:<25} | {match}')

print('=' * 72)
print(f'Match COT → Direccion Lunes: {matches}/{totals} = {round(matches/totals*100)}%')
print()

# Por patron
print('--- Por patron ---')
for pat in ['EXPANSION_H', 'NEWS_DRIVE', 'REVERSAL']:
    subs = [s for s in lunes_sessions if s['pattern'] == pat]
    if not subs: continue
    m = 0
    t = 0
    cot_vals = []
    for s in subs:
        monday = datetime.strptime(s['date'], '%Y-%m-%d').date()
        _, cot_idx = get_cot_for_monday(monday)
        if cot_idx is not None:
            cot_vals.append(cot_idx)
            cot_bull = cot_idx >= 50
            sess_bull = s['direction'] == 'BULLISH'
            if cot_bull == sess_bull: m += 1
            t += 1
    avg_cot = round(sum(cot_vals)/len(cot_vals), 1) if cot_vals else 0
    pct = round(m/t*100) if t else 0
    print(f'  {pat:<18}: {len(subs)} sess | COT avg={avg_cot} | Match={m}/{t} ({pct}%)')
