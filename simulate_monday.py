#!/usr/bin/env python3
"""Simular el lunes 07-Apr-2026 para verificar que analyze_today funcionara."""
import json
from datetime import date, timedelta
from collections import Counter

target_date = '2026-04-07'
dow_sim = 'monday'

with open('data/research/daily_master_db.json','r',encoding='utf-8') as f:
    db = json.load(f)
records = db.get('records', [])
print(f'DB: {len(records)} registros')

cot_idx    = 50.0
vxn_level  = 'ELEVATED'
semana_sim = 'W1'

similares = []
for r in records:
    if r.get('dow') != dow_sim:
        continue
    if r.get('date','') >= target_date:
        continue
    r_cot = r.get('cot_index') or 50
    r_vxn = r.get('vxn_level','')
    match_cot  = abs(r_cot - cot_idx) <= 15
    match_vxn  = r_vxn == vxn_level
    match_week = r.get('semana_ciclo','') == semana_sim
    if sum([match_cot, match_vxn, match_week]) >= 2:
        similares.append(r)

n        = len(similares)
bearish  = sum(1 for r in similares if r.get('direction') == 'BEARISH')
bullish  = n - bearish
bear_pct = round(bearish/n*100, 1) if n else 0
bull_pct = round(bullish/n*100, 1) if n else 0
ranges   = [r.get('ny_range',0) for r in similares if r.get('ny_range')]
avg_r    = round(sum(ranges)/len(ranges), 0) if ranges else 0
pats     = [r.get('pattern','N/A') for r in similares]
top_pat  = Counter(pats).most_common(1)[0][0] if pats else 'N/A'

print()
print('=== SIMULACION LUNES 07-Apr-2026 ===')
print(f'Parametros: COT={cot_idx} VXN={vxn_level} semana={semana_sim}')
print(f'Casos similares encontrados: {n}')
print(f'BULLISH: {bull_pct}%  |  BEARISH: {bear_pct}%')
print(f'Rango promedio: {avg_r} pts')
print(f'Patron dominante: {top_pat}')
print()
print('Ultimos 5 casos similares:')
for r in sorted(similares, key=lambda x: x['date'], reverse=True)[:5]:
    d = r['date']
    dw = r.get('dow','')
    direction = r.get('direction','?')
    rng = r.get('ny_range',0)
    pat = r.get('pattern','N/A')
    vxn = r.get('vxn','?')
    cot = r.get('cot_index','?')
    print(f'  {d} ({dw}) -> {direction} | rango={rng:.0f}pts | pat={pat} | VXN={vxn} COT={cot}')

print()
if n >= 5:
    print('✅ LISTO para lunes — suficientes casos historicos')
elif n > 0:
    print(f'⚠️  Solo {n} casos — resultado estadisticamente debil pero funciona')
else:
    print('❌ 0 casos encontrados — revisar logica de similitud')
