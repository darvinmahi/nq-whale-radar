"""
BACKTEST: ¿Qué día de la semana forma el HIGH/LOW semanal de NQ?

Concepto ICT: el mercado forma el "Weekly High" o "Weekly Low" en días
específicos. Si lunes/martes hacen el HIGH con más frecuencia → bias bajista
el resto de la semana. Si miércoles/jueves → la reversión puede ser diferente.

Estudio:
1. Frecuencia de weekly HIGH por día (Lun-Vie)
2. Frecuencia de weekly LOW por día (Lun-Vie)
3. Por año (¿ha cambiado el patrón?)
4. ¿Si el HIGH se forma Lunes/Martes → retorno del viernes?
5. Condicional: HIGH + LOW mismo día = pin bar semanal
"""
import csv, sys
from datetime import datetime, date, timedelta
from statistics import mean
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ──────────── CARGA BARRAS 15M ────────────────────────────────────────────
bars = []
for fn in ['data/research/nq_15m_2024_2026.csv', 'data/research/nq_15m_intraday.csv']:
    try:
        with open(fn, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                try:
                    dt_s = (r.get('Datetime') or r.get('datetime','') or '').strip()
                    dt = datetime.fromisoformat(dt_s.replace('+00:00',''))
                    h = float(r.get('High') or r.get('high') or 0)
                    l = float(r.get('Low')  or r.get('low')  or 0)
                    c = float(r.get('Close') or r.get('close') or 0)
                    if h > 0:
                        bars.append({'dt': dt, 'h': h, 'l': l, 'c': c})
                except: pass
    except: pass

bars.sort(key=lambda x: x['dt'])
# dedup
seen, bars_u = set(), []
for b in bars:
    if b['dt'] not in seen:
        seen.add(b['dt'])
        bars_u.append(b)
bars = bars_u

# ──────────── SESIÓN NY ONLY (14:30–21:00 UTC) ───────────────────────────
NY_OPEN  = timedelta(hours=14, minutes=30)
NY_CLOSE = timedelta(hours=21)

def is_ny(dt):
    start = datetime(dt.year, dt.month, dt.day) + NY_OPEN
    end   = datetime(dt.year, dt.month, dt.day) + NY_CLOSE
    return start <= dt < end

bars_ny = [b for b in bars if is_ny(b['dt'])]

# ──────────── AGRUPAR POR SEMANA ISO ─────────────────────────────────────
# Semana = lunes→viernes
weeks = defaultdict(lambda: defaultdict(list))  # {week_key: {day_abbr: [bars]}}

DAYS = {0:'Lun', 1:'Mar', 2:'Mié', 3:'Jue', 4:'Vie'}

for b in bars_ny:
    d = b['dt'].date()
    if d.weekday() > 4: continue          # skip sábado/domingo
    iso = d.isocalendar()[:2]             # (year, week_number)
    day_abbr = DAYS[d.weekday()]
    weeks[iso][day_abbr].append(b)

# ──────────── CONSTRUIR HIGH/LOW semanal ──────────────────────────────────
weekly = []
for iso, day_bars in weeks.items():
    all_bars_week = [b for dbs in day_bars.values() for b in dbs]
    if len(all_bars_week) < 50: continue   # semana incompleta

    week_high = max(b['h'] for b in all_bars_week)
    week_low  = min(b['l'] for b in all_bars_week)

    high_day = low_day = None
    for day_name, dbs in day_bars.items():
        if not dbs: continue
        if max(b['h'] for b in dbs) >= week_high:
            high_day = day_name
        if min(b['l'] for b in dbs) <= week_low:
            low_day  = day_name

    # retorno del viernes (para conditional)
    vie_bars = day_bars.get('Vie', [])
    fri_ret = None
    if vie_bars:
        fri_ret = (vie_bars[-1]['c'] - vie_bars[0]['c']) / vie_bars[0]['c'] * 100

    # retorno semanal (lunes open → viernes close)
    mon_bars = day_bars.get('Lun', [])
    wk_ret = None
    if mon_bars and vie_bars:
        wk_ret = (vie_bars[-1]['c'] - mon_bars[0]['c']) / mon_bars[0]['c'] * 100

    if high_day and low_day:
        year     = date.fromisocalendar(iso[0], iso[1], 1).year
        mon_date = date.fromisocalendar(iso[0], iso[1], 1)
        weekly.append({
            'iso'     : iso,
            'date'    : mon_date,
            'year'    : year,
            'high_day': high_day,
            'low_day' : low_day,
            'fri_ret' : fri_ret,
            'wk_ret'  : wk_ret,
            'wk_high' : week_high,
            'wk_low'  : week_low,
        })

total = len(weekly)
print(f"\nSemanas analizadas: {total}")
print(f"Período: {weekly[0]['date']} → {weekly[-1]['date']}")

SEP = '='*68

# ──────────── 1. FRECUENCIA HIGH/LOW POR DÍA ──────────────────────────────
print(f"\n{SEP}")
print("  📊 1. ¿QUÉ DÍA FORMA EL WEEKLY HIGH? (barras NY 14:30-21:00)")
print(SEP)
print(f"\n  {'Día':<8} {'Veces':>6} {'%':>7}   {'████ visual'}")
print("  " + "-"*45)
for day in ['Lun','Mar','Mié','Jue','Vie']:
    n = sum(1 for w in weekly if w['high_day']==day)
    pct = n/total*100
    bar = '█' * int(pct/2)
    print(f"  {day:<8} {n:>6} {pct:>6.1f}%   {bar}")

print(f"\n{SEP}")
print("  📊 2. ¿QUÉ DÍA FORMA EL WEEKLY LOW?")
print(SEP)
print(f"\n  {'Día':<8} {'Veces':>6} {'%':>7}   {'████ visual'}")
print("  " + "-"*45)
for day in ['Lun','Mar','Mié','Jue','Vie']:
    n = sum(1 for w in weekly if w['low_day']==day)
    pct = n/total*100
    bar = '█' * int(pct/2)
    print(f"  {day:<8} {n:>6} {pct:>6.1f}%   {bar}")

# ──────────── 2. POR AÑO ─────────────────────────────────────────────────
print(f"\n{SEP}")
print("  📊 3. HIGH DAY POR AÑO (¿Ha cambiado el patrón?)")
print(SEP)
print(f"\n  {'Año':<6}", end='')
for day in ['Lun','Mar','Mié','Jue','Vie']:
    print(f"  {day:>5}", end='')
print()
print("  " + "-"*35)
for yr in sorted(set(w['year'] for w in weekly)):
    yr_data = [w for w in weekly if w['year']==yr]
    print(f"  {yr:<6}", end='')
    for day in ['Lun','Mar','Mié','Jue','Vie']:
        n = sum(1 for w in yr_data if w['high_day']==day)
        pct = n/len(yr_data)*100 if yr_data else 0
        print(f"  {pct:>4.0f}%", end='')
    print(f"  ({len(yr_data)}s)")

# ──────────── 3. CONDICIONAL: Si HIGH fue Lun o Mar → ¿resto qué hace? ────
print(f"\n{SEP}")
print("  📊 4. CONDICIONAL: Si HIGH semanal se formó temprano (Lun/Mar)")
print("       → ¿Cómo fue el retorno del VIERNES y de la SEMANA?")
print(SEP)

for label, grp in [
    ("HIGH en Lun o Mar (bajista rest.)",
     [w for w in weekly if w['high_day'] in ('Lun','Mar')]),
    ("HIGH en Mié",
     [w for w in weekly if w['high_day'] == 'Mié']),
    ("HIGH en Jue o Vie (alcista fin s.)",
     [w for w in weekly if w['high_day'] in ('Jue','Vie')]),
]:
    fri_v = [w['fri_ret'] for w in grp if w.get('fri_ret') is not None]
    wk_v  = [w['wk_ret']  for w in grp if w.get('wk_ret')  is not None]
    print(f"\n  {label}  (n={len(grp)})")
    if fri_v:
        pos_fri = sum(1 for v in fri_v if v > 0)
        print(f"   Viernes: avg={mean(fri_v):+.3f}%  alcistas={pos_fri}/{len(fri_v)} ({pos_fri/len(fri_v)*100:.0f}%)")
    if wk_v:
        pos_wk = sum(1 for v in wk_v if v > 0)
        print(f"   Semana:  avg={mean(wk_v):+.3f}%  alcistas={pos_wk}/{len(wk_v)} ({pos_wk/len(wk_v)*100:.0f}%)")

# ──────────── 4. COMBO HIGH+LOW ──────────────────────────────────────────
print(f"\n{SEP}")
print("  📊 5. PARES HIGH DAY + LOW DAY más frecuentes")
print(SEP)
from collections import Counter
pairs = Counter((w['high_day'], w['low_day']) for w in weekly)
print(f"\n  {'HIGH→LOW':<16} {'Veces':>6} {'%':>7}")
print("  " + "-"*32)
for (h,l), n in pairs.most_common(12):
    print(f"  {h}→{l:<12} {n:>6} {n/total*100:>6.1f}%")

# ──────────── 5. RESUMEN EJECUTIVO ───────────────────────────────────────
top_high = max(['Lun','Mar','Mié','Jue','Vie'],
               key=lambda d: sum(1 for w in weekly if w['high_day']==d))
top_low  = max(['Lun','Mar','Mié','Jue','Vie'],
               key=lambda d: sum(1 for w in weekly if w['low_day']==d))

print(f"""
{SEP}
  🎯 RESUMEN EJECUTIVO
{SEP}

  Día más frecuente de WEEKLY HIGH : {top_high}
  Día más frecuente de WEEKLY LOW  : {top_low}

  SIGNIFICADO OPERATIVO:
  → Si el HIGH se forma Lun/Mar → hay sesgo bajista para Jue/Vie
    (busca cortos cuando el precio vuelve al HIGH a principios de semana)
  → Si el LOW se forma Lun/Mar → hay sesgo alcista para Jue/Vie
    (busca largos cuando el precio baja al LOW temprano)

  COMO USAR COT + DÍA DE HIGH:
  ┌─────────────────────────────────────────────
  │ COT Index >75 (bajista) + HIGH el Lun/Mar
  │ → CORTO el miércoles cuando precio retoca
  │    el high de lunes/martes  ← EDGE DOBLE
  └─────────────────────────────────────────────
""")
