"""
Pullback a 1ra vela 9:30 ET - TP 80/100/150pts - SL 50pts
El precio sale del rango de la 1ra vela, regresa, entras en la
misma direccion con TP grande.
"""
import csv
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV        = "data/research/nq_15m_intraday.csv"
MIN_BREAK  = 10.0   # pts que debe salir del rango para contar breakout
ENTRY_TOL  = 8.0    # pts de tolerancia para detectar el retorno
SL_PTS     = 80.0   # SL fijo ampliado
TP_LIST    = [120, 150, 200]

bars = []
with open(CSV, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            dt = datetime.fromisoformat(r['Datetime'].replace('+00:00','').strip())
            cl = float(r.get('Close',0) or 0)
            if cl > 0:
                bars.append(dict(dt=dt, o=float(r.get('Open',0) or 0),
                                 h=float(r.get('High',0) or 0),
                                 l=float(r.get('Low',0)  or 0), c=cl))
        except: pass
bars.sort(key=lambda x: x['dt'])

results = []
no_break = 0; no_ret = 0
fridays  = sorted(set(b['dt'].date() for b in bars if b['dt'].weekday()==4))

for fri in fridays:
    # 1ra vela 9:30 ET = 14:30 UTC
    f1s = [b for b in bars if b['dt'].date()==fri
           and b['dt'].hour==14 and b['dt'].minute==30]
    if not f1s: continue
    f1 = f1s[0]
    f1h = f1['h']; f1l = f1['l']; rng = f1h - f1l
    if rng < 5: continue
    bull = f1['c'] > f1['o']

    # Barras restantes del dia
    sess = [b for b in bars if b['dt'].date()==fri and
            datetime(fri.year,fri.month,fri.day,14,45)<=b['dt']<
            datetime(fri.year,fri.month,fri.day,21,0)]
    if len(sess) < 3: continue

    # Fase 1: breakout del rango
    phase = 'BREAK'; blevel = None; bbar = None; entry = None; ebar = None
    for i, b in enumerate(sess):
        if phase == 'BREAK':
            if bull  and b['h'] >= f1h + MIN_BREAK:
                blevel = b['h']; bbar = i; phase = 'RETURN'
            elif not bull and b['l'] <= f1l - MIN_BREAK:
                blevel = b['l']; bbar = i; phase = 'RETURN'
        elif phase == 'RETURN':
            if bull  and b['h'] > blevel: blevel = b['h']
            if not bull and b['l'] < blevel: blevel = b['l']
            # Precio regresa al rango de la 1ra vela (zona del HIGH para bull, LOW para bear)
            if bull  and b['l'] <= f1h + ENTRY_TOL:
                entry = f1h; ebar = i; phase = 'TRADE'; break
            if not bull and b['h'] >= f1l - ENTRY_TOL:
                entry = f1l; ebar = i; phase = 'TRADE'; break

    if phase != 'TRADE':
        if bbar is None: no_break += 1
        else: no_ret += 1
        continue

    post = sess[ebar:]
    sl_p = (entry - SL_PTS) if bull else (entry + SL_PTS)

    def sim(tp_pts):
        tp_p = (entry + tp_pts) if bull else (entry - tp_pts)
        for b in post:
            if bull:
                if b['h'] >= tp_p: return 'TP'
                if b['l'] <= sl_p: return 'SL'
            else:
                if b['l'] <= tp_p: return 'TP'
                if b['h'] >= sl_p: return 'SL'
        last = post[-1]['c'] if post else entry
        return 'W' if ((bull and last>entry) or (not bull and last<entry)) else 'L'

    results.append({'bull': bull, 'rng': round(rng,1),
                    'tp': {t: sim(t) for t in TP_LIST},
                    'bbar': bbar, 'ebar': ebar})

N = len(results)
sep = '='*60

print()
print(sep)
print(f"  PULLBACK A 1RA VELA (9:30 ET) | Viernes | N={N}")
print(f"  SL fijo={SL_PTS:.0f}pts | Breakout min={MIN_BREAK:.0f}pts")
print(f"  Sin breakout={no_break} | Breakout sin retorno={no_ret}")
print(sep)
print()
print(f"  {'TP':>6}  {'R:R':>5}  {'Hit TP':>12}  {'Hit SL':>12}  {'EOD':>8}  {'EV':>8}")
print('-'*60)
for tp in TP_LIST:
    h  = sum(1 for r in results if r['tp'][tp]=='TP')
    sl = sum(1 for r in results if r['tp'][tp]=='SL')
    ew = sum(1 for r in results if r['tp'][tp]=='W')
    el = sum(1 for r in results if r['tp'][tp]=='L')
    ev = (h/N)*tp - (sl/N)*SL_PTS
    rr = tp/SL_PTS
    print(f"  {tp:>5}pts  {rr:>4.1f}x  {h:>6}({h/N*100:.0f}%)  {sl:>6}({sl/N*100:.0f}%)  {ew}W/{el}L  {ev:>+7.1f}pts")

print()
print('-'*60)
print(f"  BULL vs BEAR con TP=100pts:")
for lbl, cond in [('1ra vela BULL (→ LONG)', True), ('1ra vela BEAR (→ SHORT)', False)]:
    sub = [r for r in results if r['bull']==cond]
    if not sub: continue
    h  = sum(1 for r in sub if r['tp'][100]=='TP')
    sl = sum(1 for r in sub if r['tp'][100]=='SL')
    ev = (h/len(sub))*100 - (sl/len(sub))*SL_PTS
    print(f"  {lbl}: N={len(sub)}  TP={h}({h/len(sub)*100:.0f}%)  SL={sl}({sl/len(sub)*100:.0f}%)  EV={ev:+.1f}pts")

# Tiempo promedio de espera del pullback
avg_wait = sum((r['ebar']-r['bbar'])*15 for r in results if r['ebar'] and r['bbar'])/N
print()
print(f"  Espera promedio desde breakout hasta retorno: {avg_wait:.0f} min")
print()
print(sep)
