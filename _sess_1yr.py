import csv, sys, math
from datetime import datetime, date, time, timedelta
from statistics import mean
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

START = date(2025, 4, 1)

bars = []
for fn in ['data/research/nq_15m_2024_2026.csv','data/research/nq_15m_intraday.csv']:
    try:
        with open(fn, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                try:
                    dt = datetime.fromisoformat((r.get('Datetime') or r.get('datetime','')).strip().replace('+00:00',''))
                    h=float(r.get('High') or 0); l=float(r.get('Low') or 0); c=float(r.get('Close') or 0)
                    if c>0: bars.append({'dt':dt,'h':h,'l':l,'c':c})
                except: pass
    except: pass
bars.sort(key=lambda x:x['dt'])
seen,bars_u=set(),[]
for b in bars:
    if b['dt'] not in seen: seen.add(b['dt']); bars_u.append(b)
bars=bars_u

def get_session(dt):
    h=dt.time()
    if time(22,0)<=h or h<time(8,0): return 'ASIA'
    elif time(8,0)<=h<time(14,30): return 'LONDON'
    elif time(14,30)<=h<time(21,0): return 'NY'
    return None

def trading_date(dt):
    d=dt.date()
    if dt.time()>=time(22,0): d=d+timedelta(days=1)
    return d

sess_data=defaultdict(lambda: defaultdict(list))
for b in bars:
    s=get_session(b['dt'])
    if not s: continue
    td=trading_date(b['dt'])
    if td<START or td.weekday()>4: continue
    sess_data[td][s].append(b)

def session_stats(sb):
    if len(sb)<2: return None
    sb=sorted(sb,key=lambda x:x['dt'])
    o=sb[0]['c']; c=sb[-1]['c']; h=max(b['h'] for b in sb); l=min(b['l'] for b in sb)
    ret=(c-o)/o*100; rng=(h-l)/o*100
    return {'ret':ret,'rng':rng,'dir':'BULL' if ret>0.05 else ('BEAR' if ret<-0.05 else 'FLAT')}

all_days=[]
for d in sorted(sess_data.keys()):
    a=session_stats(sess_data[d].get('ASIA',[])); lo=session_stats(sess_data[d].get('LONDON',[])); ny=session_stats(sess_data[d].get('NY',[]))
    if not(a and lo and ny): continue
    all_days.append({'date':d,'dow':d.weekday(),'dow_n':['Lun','Mar','Mie','Jue','Vie'][d.weekday()],'asia':a,'london':lo,'ny':ny})

n=len(all_days)
print(f"Periodo: {all_days[0]['date']} -> {all_days[-1]['date']}  ({n} dias)\n")
print(f"{'Sesion':<10} {'BULL%':>6} {'BEAR%':>6} {'FLAT%':>6}  {'Ret avg':>9}  {'Rango':>8}")
print('-'*52)
for sk,sn in [('asia','ASIA'),('london','LONDON'),('ny','NY')]:
    ss=[d[sk] for d in all_days]
    bull=sum(1 for s in ss if s['dir']=='BULL')
    bear=sum(1 for s in ss if s['dir']=='BEAR')
    flat=sum(1 for s in ss if s['dir']=='FLAT')
    print(f"{sn:<10} {bull/n*100:>5.0f}% {bear/n*100:>5.0f}% {flat/n*100:>5.0f}%  {mean(s['ret'] for s in ss):>+8.3f}%  {mean(s['rng'] for s in ss):>7.3f}%")

print('\nPOR DIA:')
print(f"{'Dia':<6}  {'ASIA%':>7} {'ret':>6}  {'LON%':>7} {'ret':>6}  {'NY%':>7} {'ret':>6}  {'NY rng':>7}")
print('-'*66)
DAYS=['Lun','Mar','Mie','Jue','Vie']
for dow,dn in enumerate(DAYS):
    grp=[d for d in all_days if d['dow']==dow]
    if not grp: continue
    def bp(sk): return sum(1 for d in grp if d[sk]['dir']=='BULL')/len(grp)*100
    def ar(sk): return mean(d[sk]['ret'] for d in grp)
    def rg(sk): return mean(d[sk]['rng'] for d in grp)
    print(f"{dn:<6}  {bp('asia'):>6.0f}% {ar('asia'):>+5.2f}%  {bp('london'):>6.0f}% {ar('london'):>+5.2f}%  {bp('ny'):>6.0f}% {ar('ny'):>+5.2f}%  {rg('ny'):>6.2f}%  (n={len(grp)})")

print('\nCOMBO:')
bb=[d for d in all_days if d['asia']['dir']=='BULL' and d['london']['dir']=='BULL']
be=[d for d in all_days if d['asia']['dir']=='BEAR' and d['london']['dir']=='BEAR']
if bb:
    ny_b=sum(1 for d in bb if d['ny']['dir']=='BULL')
    print(f"  Asia+London BULL -> NY BULL: {ny_b/len(bb)*100:.0f}%  avgNY: {mean(d['ny']['ret'] for d in bb):+.3f}%  n={len(bb)}")
if be:
    ny_b2=sum(1 for d in be if d['ny']['dir']=='BULL')
    print(f"  Asia+London BEAR -> NY BULL: {ny_b2/len(be)*100:.0f}%  avgNY: {mean(d['ny']['ret'] for d in be):+.3f}%  n={len(be)}")

# Por cada dia: si NY va en contra de Asia+London
contra=[(d['date'],d['dow_n']) for d in bb if d['ny']['dir']=='BEAR']
print(f"\n  Asia+London BULL -> NY BEAR (reversa): {len(contra)}/{len(bb)} = {len(contra)/len(bb)*100:.0f}%")
