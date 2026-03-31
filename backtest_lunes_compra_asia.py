"""
BACKTEST SIMPLE: Compra el LUNES en apertura de Asia
¿Cuántos lunes cierra en positivo según donde cierres?

Entrada: apertura sesión Asia del lunes (22:00 UTC domingo)
Salida en: fin Asia / fin London / fin NY / cierre martes / cierre viernes
Periodo: ultimo 1 año
"""
import csv, sys
from datetime import datetime, date, time, timedelta
from statistics import mean
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

START = date(2025, 4, 1)

# Carga barras
bars = []
for fn in ['data/research/nq_15m_2024_2026.csv', 'data/research/nq_15m_intraday.csv']:
    try:
        with open(fn, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                try:
                    dt = datetime.fromisoformat(
                        (r.get('Datetime') or r.get('datetime','')).strip().replace('+00:00',''))
                    c = float(r.get('Close') or 0)
                    if c > 0: bars.append({'dt': dt, 'c': c})
                except: pass
    except: pass
bars.sort(key=lambda x: x['dt'])
seen, bars_u = set(), []
for b in bars:
    if b['dt'] not in seen: seen.add(b['dt']); bars_u.append(b)
bars = bars_u

# Agrupar por fecha
by_date = defaultdict(list)
for b in bars:
    by_date[b['dt'].date()].append(b)

# Para cada lunes: encontrar primera barra de Asia (domingo 22:00 en adelante)
results = []
all_dates = sorted(by_date.keys())

for d in all_dates:
    if d < START: continue
    if d.weekday() != 0: continue  # solo lunes

    # Domingo = d - 1 día
    sun = d - timedelta(days=1)

    # Apertura Asia = primera barra del domingo >= 22:00
    sun_bars = sorted([b for b in by_date.get(sun, []) if b['dt'].time() >= time(22, 0)],
                      key=lambda x: x['dt'])
    # o primera barra del lunes < 08:00
    mon_asia_bars = sorted([b for b in by_date.get(d, []) if b['dt'].time() < time(8, 0)],
                           key=lambda x: x['dt'])

    asia_bars = sun_bars + mon_asia_bars
    if not asia_bars: continue

    entry_price = asia_bars[0]['c']  # COMPRA aquí

    # Cierre de cada sesión del lunes
    mon_all = sorted(by_date.get(d, []), key=lambda x: x['dt'])

    def last_before(bars_list, end_time):
        filtered = [b for b in bars_list if b['dt'].time() < end_time]
        return filtered[-1]['c'] if filtered else None

    close_asia   = last_before(mon_all, time(8, 0))    # fin Asia = 08:00
    close_london = last_before(mon_all, time(14, 30))  # fin London = 14:30
    close_ny     = last_before(mon_all, time(21, 0))   # fin NY = 21:00

    # Cierre martes
    tue = d + timedelta(days=1)
    tue_bars = sorted(by_date.get(tue, []), key=lambda x: x['dt'])
    close_tue = last_before(tue_bars, time(21, 0))

    # Cierre viernes
    fri = d + timedelta(days=4)
    fri_bars = sorted(by_date.get(fri, []), key=lambda x: x['dt'])
    close_fri = last_before(fri_bars, time(21, 0))

    def ret(c):
        if c is None: return None
        return (c - entry_price) / entry_price * 100

    results.append({
        'date'    : d,
        'entry'   : entry_price,
        'asia'    : ret(close_asia),
        'london'  : ret(close_london),
        'ny'      : ret(close_ny),
        'martes'  : ret(close_tue),
        'viernes' : ret(close_fri),
    })

n = len(results)
print(f"BACKTEST: COMPRA APERTURA ASIA LUNES — último 1 año")
print(f"Período: {results[0]['date']} → {results[-1]['date']}  ({n} lunes)\n")

print(f"{'Salida en':<14} {'Positivos':>10} {'%Win':>7} {'Avg ret':>9} {'Mejor':>9} {'Peor':>9}")
print("─" * 55)

for lbl in ['asia','london','ny','martes','viernes']:
    vals = [r[lbl] for r in results if r[lbl] is not None]
    if not vals: continue
    pos = sum(1 for v in vals if v > 0)
    print(f"  {lbl:<12} {pos:>4}/{len(vals)}     {pos/len(vals)*100:>5.0f}%  {mean(vals):>+8.3f}%  {max(vals):>+8.2f}%  {min(vals):>+8.2f}%")

print()
print(f"DETALLE CADA LUNES:")
print(f"{'Fecha':<12} {'Entry':>8} {'Asia':>8} {'London':>8} {'NY':>8} {'Martes':>8} {'Viernes':>9}")
print("─" * 65)
for r in results:
    def fmt(v): return f"{v:+.2f}%" if v is not None else "  N/A"
    print(f"{str(r['date']):<12} {r['entry']:>8.1f} {fmt(r['asia']):>8} {fmt(r['london']):>8} {fmt(r['ny']):>8} {fmt(r['martes']):>8} {fmt(r['viernes']):>9}")
