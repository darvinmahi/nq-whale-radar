import csv
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter

def utc_off(d):
    if date(2025,3,9)<=d<date(2025,11,2) or date(2026,3,8)<=d: return 4
    return 5

by_date = defaultdict(list)
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            if et.weekday()>=5: continue
            by_date[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close'])
            })
        except: pass

sorted_dates = sorted(by_date.keys())
date_set = set(sorted_dates)
cases = []

for d in sorted_dates:
    if d.weekday() != 0: continue
    mn = sorted(
        [b for b in by_date[d] if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x:x['et']
    )
    if len(mn)<4: continue
    mon_chg = mn[-1]['c'] - mn[0]['o']
    if mon_chg > -50: continue

    tue = d + timedelta(days=1)
    if tue not in date_set or tue.weekday()!=1: continue
    tn = sorted(
        [b for b in by_date[tue] if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x:x['et']
    )
    if len(tn)<4: continue

    tue_o = tn[0]['o']
    tue_c = tn[-1]['c']
    tue_chg = round(tue_c - tue_o, 1)
    hi_hr = max(tn, key=lambda x:x['h'])['et'].hour
    lo_hr = min(tn, key=lambda x:x['l'])['et'].hour
    tue_rng = round(max(b['h'] for b in tn) - min(b['l'] for b in tn), 1)
    fc = next((b for b in tn if b['et'].hour==9 and b['et'].minute==30), None)
    fc_bull = (fc['c']>fc['o']) if fc else None
    fc_body = round(abs(fc['c']-fc['o']),1) if fc else 0

    cases.append({
        'mon':d,'tue':tue,'mon_chg':round(mon_chg,1),
        'tue_chg':tue_chg,'tue_bull':tue_chg>0,
        'hi_hr':hi_hr,'lo_hr':lo_hr,'tue_rng':tue_rng,
        'fc_bull':fc_bull,'fc_body':fc_body
    })

print("=== BACKTEST: MARTES DESPUES DE LUNES CAIDA FUERTE (2017-2026) ===")
print(f"Total casos (lunes caida >50pts): {len(cases)}")
print()

grupos = [
    ('BEAR  (-50 a -100)',  lambda c: -100 < c['mon_chg'] <= -50),
    ('CRASH (-100 a -200)', lambda c: -200 < c['mon_chg'] <= -100),
    ('MEGA  (> -200)',      lambda c: c['mon_chg'] <= -200),
]

for nombre, filtro in grupos:
    g = [c for c in cases if filtro(c)]
    if not g: continue
    n = len(g)
    ups = sum(1 for c in g if c['tue_bull'])
    avg = sum(c['tue_chg'] for c in g)/n
    avg_rng = sum(c['tue_rng'] for c in g)/n
    hi_c = Counter(c['hi_hr'] for c in g).most_common(3)
    lo_c = Counter(c['lo_hr'] for c in g).most_common(3)
    fc_up = sum(1 for c in g if c['fc_bull'])
    print(f"{'='*60}")
    print(f"GRUPO: {nombre}")
    print(f"  Casos: {n}")
    print(f"  Martes SUBE: {ups}/{n} = {ups/n*100:.0f}%")
    print(f"  Avg movimiento: {avg:+.0f}pts")
    print(f"  Avg RANGO del dia: {avg_rng:.0f}pts")
    print(f"  HIGH tipico en hora: {[f'{h}h({v}x)' for h,v in hi_c]}")
    print(f"  LOW  tipico en hora: {[f'{h}h({v}x)' for h,v in lo_c]}")
    print(f"  1a vela 9:30 verde: {fc_up}/{n} = {fc_up/n*100:.0f}%")
    print()
    print(f"  {'Lunes':<12} {'LunChg':>8}  {'Martes':<12} {'MarChg':>8}  {'Dir':>4}  {'HiHr':>5}  {'LoHr':>5}  {'Rng':>6}")
    print(f"  {'-'*70}")
    for c in g:
        arr = "UP  +" if c['tue_bull'] else "DOWN"
        print(f"  {str(c['mon']):<12} {c['mon_chg']:>+8.0f}  {str(c['tue']):<12} {c['tue_chg']:>+8.0f}  {arr:>6}  {c['hi_hr']:>5}  {c['lo_hr']:>5}  {c['tue_rng']:>6.0f}")
    print()

# HOY
print("="*60)
print("HOY MARTES 7 ABR 2026 — Lunes 6 fue MEGA CRASH tariff")
print("Filtro mas relevante: CRASH/MEGA grupos")
crash = [c for c in cases if c['mon_chg'] <= -100]
n=len(crash); ups=sum(1 for c in crash if c['tue_bull'])
avg=sum(c['tue_chg'] for c in crash)/max(1,n)
hi_c=Counter(c['hi_hr'] for c in crash).most_common(3)
lo_c=Counter(c['lo_hr'] for c in crash).most_common(3)
print(f"  n={n} | Sube: {ups/max(1,n)*100:.0f}% | Avg: {avg:+.0f}pts")
print(f"  HIGH suele ser a: {[f'{h}h({v}x)' for h,v in hi_c]}")
print(f"  LOW  suele ser a: {[f'{h}h({v}x)' for h,v in lo_c]}")
print(f"  SESION ACTUAL: 12:28 ET — si low fue en 9h, HIGH aun puede ser 10h-13h")
