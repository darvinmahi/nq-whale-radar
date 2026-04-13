"""
cot_sweep_profundo.py
ESTUDIO COMPLETO: ¿Qué diferencia los 51 martes con SWEEP+REVERSAL
de los 52 que sweepearon pero NO revirtieron?
Variables: COT index, COT net, COT signal, VXN, VXN_delta, lunes tipo
"""
import json, csv
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

BG='#0a0a16'; PANEL='#0d0d1a'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; SOFT='#94a3b8'; DIM='#475569'
ORG='#f97316'; WHITE='#f1f5f9'; TEAL='#14b8a6'; PRP='#a78bfa'

# ════════════════════════════════════════════════════════════════════
# 1. CARGAR COT DB — ver qué rango tenemos
# ════════════════════════════════════════════════════════════════════
with open('data/research/daily_master_db.json') as f:
    db = json.load(f)

cot_by_date = {}
for rec in db.get('records', []):
    try:
        d = date.fromisoformat(rec['date'])
        cot_idx = float(rec.get('cot_index', 0) or 0)
        cot_n   = float(rec.get('cot_net',   0) or 0)
        cot_d   = float(rec.get('cot_delta', 0) or 0)
        vxn_v   = float(rec.get('vxn',       0) or 0)
        vxn_d   = float(rec.get('vxn_delta', 0) or 0)
        sig     = rec.get('cot_signal','?')
        if cot_idx > 0 or cot_n != 0 or vxn_v > 0:  # tiene datos reales
            cot_by_date[d] = {
                'cot_idx':cot_idx,'cot_net':cot_n,'cot_delta':cot_d,
                'vxn':vxn_v,'vxn_delta':vxn_d,'cot_sig':sig,
                'cot_bull': 'BULL' in sig,
                'cot_bear': 'BEAR' in sig,
            }
    except: pass

cot_dates = sorted(cot_by_date.keys())
if cot_dates:
    print(f"COT DB: {cot_dates[0]} → {cot_dates[-1]}  ({len(cot_dates)} días)")
    tues_cot = [d for d in cot_dates if d.weekday()==1]
    print(f"  Martes con COT: {len(tues_cot)}")
    # Muestra los últimos 5
    print("  Últimos 5:")
    for d in tues_cot[-5:]:
        c=cot_by_date[d]
        print(f"    {d}  idx={c['cot_idx']:.1f}  net={c['cot_net']:.0f}  delta={c['cot_delta']:+.0f}  vxn={c['vxn']:.1f}  sig={c['cot_sig']}")
else:
    print("ERROR: sin datos COT!")

# ════════════════════════════════════════════════════════════════════
# 2. CARGAR CSV 15MIN TODOS LOS MARTES
# ════════════════════════════════════════════════════════════════════
by_date_15 = defaultdict(list)
with open('data/research/nq_15m_intraday.csv') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            d_raw = raw.date()
            off = 4 if (date(2019,3,10)<=d_raw<date(2019,11,3) or
                        date(2020,3,8)<=d_raw<date(2020,11,1) or
                        date(2021,3,14)<=d_raw<date(2021,11,7) or
                        date(2022,3,13)<=d_raw<date(2022,11,6) or
                        date(2023,3,12)<=d_raw<date(2023,11,5) or
                        date(2024,3,10)<=d_raw<date(2024,11,3) or
                        date(2025,3,9)<=d_raw<date(2025,11,2) or
                        date(2026,3,8)<=d_raw) else 5
            et = raw - timedelta(hours=off)
            by_date_15[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close'])
            })
        except: pass

def ny15(d):
    return sorted([b for b in by_date_15.get(d,[])
                   if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
                  key=lambda x:x['et'])

# ════════════════════════════════════════════════════════════════════
# 3. ANALIZAR CADA MARTES CON SWEEP — BUSCAR DIFERENCIADORES
# ════════════════════════════════════════════════════════════════════
all_cases   = []   # sweep_lo cases (barrió LOW del lunes)
no_sweep_lo = []   # los que NO barrieron el LOW

for d in sorted(by_date_15.keys()):
    if d.weekday() != 1: continue
    mon = d - timedelta(days=1)
    bars = ny15(d); mon_bars = ny15(mon)
    if len(bars)<8 or len(mon_bars)<4: continue

    mon_lo=min(b['l'] for b in mon_bars)
    mon_hi=max(b['h'] for b in mon_bars)
    mon_chg=mon_bars[-1]['c']-mon_bars[0]['o']
    mon_type=('BULL_STRONG' if mon_chg/mon_bars[0]['o']>0.008
              else 'BULL' if mon_chg>0
              else 'BEAR' if mon_chg< -mon_bars[0]['o']*0.003 else 'FLAT')

    ny_open=bars[0]['o']; ny_close=bars[-1]['c']
    ny_hi=max(b['h'] for b in bars); ny_lo=min(b['l'] for b in bars)
    ny_rng=round(ny_hi-ny_lo,1); ny_chg=round(ny_close-ny_open,1)

    swept_lo = ny_lo <= mon_lo + 8

    # Buscar COT más cercano (mismo día o días anteriores)
    cot_d = None
    for delta in [0,-1,-2,-3,-4,-5]:
        cd = d + timedelta(days=delta)
        if cd in cot_by_date:
            cot_d = cot_by_date[cd]
            break

    if swept_lo:
        reversal = ny_chg > 0
        recovery_pct = round((ny_close-ny_lo)/ny_rng*100,1) if ny_rng>0 else 0
        lo_bar=min(bars,key=lambda x:x['l'])
        lo_time=lo_bar['et'].strftime('%H:%M')
        lo_hr=lo_bar['et'].hour+lo_bar['et'].minute/60

        all_cases.append({
            'd':d,'mon_type':mon_type,'mon_chg':round(mon_chg,1),
            'ny_open':ny_open,'ny_close':ny_close,'ny_chg':ny_chg,
            'ny_hi':ny_hi,'ny_lo':ny_lo,'ny_rng':ny_rng,
            'reversal':reversal,'recovery_pct':recovery_pct,
            'lo_time':lo_time,'lo_hr':lo_hr,
            'cot_idx':   cot_d['cot_idx']   if cot_d else None,
            'cot_net':   cot_d['cot_net']   if cot_d else None,
            'cot_delta': cot_d['cot_delta'] if cot_d else None,
            'vxn':       cot_d['vxn']       if cot_d else None,
            'vxn_delta': cot_d['vxn_delta'] if cot_d else None,
            'cot_sig':   cot_d['cot_sig']   if cot_d else '?',
            'cot_bull':  cot_d['cot_bull']  if cot_d else None,
            'has_cot':   cot_d is not None,
        })

    else:
        no_sweep_lo.append({
            'd':d,'mon_type':mon_type,'mon_chg':round(mon_chg,1),
            'ny_open':ny_open,'ny_close':ny_close,'ny_chg':ny_chg,
            'ny_hi':ny_hi,'ny_lo':ny_lo,'ny_rng':ny_rng,
            'swept_hi': ny_hi >= mon_hi - 8,
            'ny_bull': ny_chg > 0,
            'inside': ny_hi < mon_hi and ny_lo > mon_lo,
            'cot_idx':   cot_d['cot_idx']   if cot_d else None,
            'cot_sig':   cot_d['cot_sig']   if cot_d else '?',
            'cot_bull':  cot_d['cot_bull']  if cot_d else None,
            'vxn':       cot_d['vxn']       if cot_d else None,
            'has_cot':   cot_d is not None,
        })

N = len(all_cases)
REV  = [r for r in all_cases if r['reversal']]
NREV = [r for r in all_cases if not r['reversal']]
# Solo con datos COT
REV_cot  = [r for r in REV  if r['has_cot']]
NREV_cot = [r for r in NREV if r['has_cot']]

print(f"\n{'='*65}")
print(f"TOTAL SWEEP cases: {N}  |  Reversal: {len(REV)} ({len(REV)/N*100:.0f}%)  |  No-rev: {len(NREV)}")
print(f"  Con datos COT — Reversal: {len(REV_cot)}  No-rev: {len(NREV_cot)}")

# ── LOS OTROS (no sweepearon LOW) ────────────────────────────────────
N_other = len(no_sweep_lo)
other_bull  = sum(1 for r in no_sweep_lo if r['ny_bull'])
other_swept_hi = sum(1 for r in no_sweep_lo if r['swept_hi'])
other_inside   = sum(1 for r in no_sweep_lo if r['inside'])
print(f"\n{'='*65}")
print(f"LOS OTROS {N_other} MARTES (no barrieron LOW del lunes):")
print(f"{'='*65}")
print(f"  Barrieron HIGH del lunes:  {other_swept_hi}/{N_other} = {other_swept_hi/max(1,N_other)*100:.0f}%")
print(f"  Cerraron ARRIBA del open:  {other_bull}/{N_other} = {other_bull/max(1,N_other)*100:.0f}%")
print(f"  Día Inside (dentro de Lun):{other_inside}/{N_other} = {other_inside/max(1,N_other)*100:.0f}%")
print(f"  Promedio cambio NY: {sum(r['ny_chg'] for r in no_sweep_lo)/N_other:+.0f}pts")
print(f"  Rango promedio NY: {sum(r['ny_rng'] for r in no_sweep_lo)/N_other:.0f}pts")
# Tipo de lunes en el grupo 'otros'
print(f"  Tipo Lunes previo:")
from collections import Counter as Ctr2
for mt,c in Ctr2(r['mon_type'] for r in no_sweep_lo).most_common():
    up=sum(1 for r in no_sweep_lo if r['mon_type']==mt and r['ny_bull'])
    tot_=sum(1 for r in no_sweep_lo if r['mon_type']==mt)
    print(f"    {mt:<15}: {tot_} casos  ({up/tot_*100:.0f}% suben el martes)")
print(f"\n→ CONCLUSIÓN: Cuando NO barre el LOW, {other_bull/N_other*100:.0f}% de los martes SUBEN")
print(f"→ Esto es MÁS FÁCIL de operar: si no hay barrida temprana = LONG directo")

def avg(lst, key):
    vals = [r[key] for r in lst if r[key] is not None]
    return round(np.mean(vals),2) if vals else None

def med(lst, key):
    vals = [r[key] for r in lst if r[key] is not None]
    return round(np.median(vals),2) if vals else None

print(f"\n{'='*65}")
print(f"{'Variable':<22} {'REV (sube)':>14} {'NO-REV (baja)':>15} {'Diferencia':>12}")
print(f"{'-'*65}")
for var,lbl in [
    ('cot_idx','COT Index (0-100)'),
    ('cot_net','COT Net pos (K)'),
    ('cot_delta','COT Delta (cambio)'),
    ('vxn','VXN nivel'),
    ('vxn_delta','VXN Delta (cambio)'),
]:
    a_r=avg(REV_cot,var); a_n=avg(NREV_cot,var)
    m_r=med(REV_cot,var); m_n=med(NREV_cot,var)
    if a_r and a_n:
        diff=round(a_r-a_n,2)
        sig='↑ REV Mayor' if diff>0 else '↓ NREV Mayor'
        print(f"  {lbl:<20} avg={a_r:>8.1f}   avg={a_n:>8.1f}   {diff:>+8.1f}  {sig}")
    else:
        print(f"  {lbl:<20} avg={a_r}   avg={a_n}")

# COT signal distribution
print(f"\n  COT SIGNAL — Reversal vs No-Reversal:")
sigs_r = Counter(r['cot_sig'][:14] for r in REV_cot)
sigs_n = Counter(r['cot_sig'][:14] for r in NREV_cot)
all_sigs = set(list(sigs_r.keys())+list(sigs_n.keys()))
for s in sorted(all_sigs):
    nr=sigs_r.get(s,0); nn=sigs_n.get(s,0)
    print(f"    {s:<22}  SUBE:{nr}  BAJA:{nn}  EDGE:{'+' if nr>nn else '-'}")

# COT BULL vs BEAR breakdown
print(f"\n  COT BULL cuando hubo REVERSAL: {sum(1 for r in REV_cot if r['cot_bull'])}/{len(REV_cot)}")
print(f"  COT BULL cuando NO revirtió:   {sum(1 for r in NREV_cot if r['cot_bull'])}/{len(NREV_cot)}")
print(f"  COT BEAR cuando hubo REVERSAL: {sum(1 for r in REV_cot if r['cot_bull']==False)}/{len(REV_cot)}")
print(f"  COT BEAR cuando NO revirtió:   {sum(1 for r in NREV_cot if r['cot_bull']==False)}/{len(NREV_cot)}")

# VXN threshold analysis
print(f"\n  VXN THRESHOLD — ¿Qué nivel separa mejor?")
for threshold in [18,20,22,25,28,30]:
    r_high=[r for r in REV_cot if r['vxn'] and r['vxn']>=threshold]
    r_low =[r for r in REV_cot if r['vxn'] and r['vxn']< threshold]
    n_high=[r for r in NREV_cot if r['vxn'] and r['vxn']>=threshold]
    n_low =[r for r in NREV_cot if r['vxn'] and r['vxn']< threshold]
    if (len(r_high)+len(n_high))>0:
        wr_high=len(r_high)/(len(r_high)+len(n_high))*100
        print(f"    VXN >= {threshold}: {len(r_high)}rev/{len(r_high)+len(n_high)} = {wr_high:.0f}% revierte  |  VXN<{threshold}: {len(r_low)}rev/{len(r_low)+len(n_low)} = {len(r_low)/(max(1,len(r_low)+len(n_low)))*100:.0f}% revierte")

# COT Index threshold
print(f"\n  COT INDEX THRESHOLD — ¿Sobre cuánto separa mejor?")
for threshold in [30,40,50,60,70]:
    r_h=[r for r in REV_cot if r['cot_idx'] and r['cot_idx']>=threshold]
    n_h=[r for r in NREV_cot if r['cot_idx'] and r['cot_idx']>=threshold]
    t=len(r_h)+len(n_h)
    if t>0: print(f"    COT_idx >= {threshold}: {len(r_h)}rev/{t} = {len(r_h)/t*100:.0f}% revierte  n={t}")

# COT Delta threshold (divergencia)
print(f"\n  COT DELTA (divergencia) — ¿Sube vs baja?")
r_dpos=[r for r in REV_cot if r['cot_delta'] and r['cot_delta']>0]
n_dpos=[r for r in NREV_cot if r['cot_delta'] and r['cot_delta']>0]
r_dneg=[r for r in REV_cot if r['cot_delta'] and r['cot_delta']<=0]
n_dneg=[r for r in NREV_cot if r['cot_delta'] and r['cot_delta']<=0]
tot_pos=len(r_dpos)+len(n_dpos); tot_neg=len(r_dneg)+len(n_dneg)
if tot_pos>0: print(f"    Delta POSITIVO (institucionales compraron): {len(r_dpos)}rev/{tot_pos} = {len(r_dpos)/tot_pos*100:.0f}% revierte")
if tot_neg>0: print(f"    Delta NEGATIVO (institucionales vendieron): {len(r_dneg)}rev/{tot_neg} = {len(r_dneg)/tot_neg*100:.0f}% revierte")

# Monday type
print(f"\n  TIPO DE LUNES antes del sweep:")
mon_counter_r=Counter(r['mon_type'] for r in REV)
mon_counter_n=Counter(r['mon_type'] for r in NREV)
for mt in ['BULL_STRONG','BULL','FLAT','BEAR']:
    nr=mon_counter_r.get(mt,0); nn=mon_counter_n.get(mt,0)
    t=nr+nn; wr=nr/t*100 if t>0 else 0
    print(f"    Lunes {mt:<12}: {nr}rev/{t} = {wr:.0f}% revierte")

# ════════════════════════════════════════════════════════════════════
# MEJOR FILTRO COMBINADO
# ════════════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("MEJOR FILTRO COMBINADO (COT + VXN):")
print(f"{'='*65}")
combos=[
    ('COT BULL + VXN>22',  lambda r: r['has_cot'] and r['cot_bull'] and r['vxn'] and r['vxn']>22),
    ('COT BULL + VXN<22',  lambda r: r['has_cot'] and r['cot_bull'] and r['vxn'] and r['vxn']<=22),
    ('COT BULL + Delta>0', lambda r: r['has_cot'] and r['cot_bull'] and r['cot_delta'] and r['cot_delta']>0),
    ('COT BULL + Delta<0', lambda r: r['has_cot'] and r['cot_bull'] and r['cot_delta'] and r['cot_delta']<=0),
    ('COT idx>50 + VXN>22',lambda r: r['has_cot'] and r['cot_idx'] and r['cot_idx']>50 and r['vxn'] and r['vxn']>22),
    ('COT idx>50 + VXN<22',lambda r: r['has_cot'] and r['cot_idx'] and r['cot_idx']>50 and r['vxn'] and r['vxn']<=22),
    ('Lunes BEAR + COT BULL',lambda r: r['has_cot'] and r['cot_bull'] and r['mon_type']=='BEAR'),
    ('Lunes BULL + COT BULL',lambda r: r['has_cot'] and r['cot_bull'] and r['mon_type']=='BULL'),
]
for label,filt in combos:
    grp=[r for r in all_cases if filt(r)]
    if not grp: continue
    rev_=sum(1 for r in grp if r['reversal'])
    wr=rev_/len(grp)*100
    mark='🎯' if wr>=65 else ('✅' if wr>=60 else ('⚠️' if wr>=50 else '❌'))
    print(f"  {mark} {label:<35} {rev_}/{len(grp)} = {wr:.0f}%")

# ════════════════════════════════════════════════════════════════════
# FIGURA COMPLETA
# ════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(28,20), facecolor=BG)
fig.suptitle(
    'ESTUDIO COMPLETO: ¿QUÉ DIFERENCIA SWEEP+REVERSAL de SWEEP+SIGUE BAJANDO?\n'
    'COT Index / COT Delta / VXN / Tipo de Lunes — 103 Martes con Sweep del LOW',
    color=GOLD, fontsize=14, fontweight='bold', y=0.999
)

gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.42, wspace=0.30,
                       left=0.05, right=0.97, top=0.96, bottom=0.04)

def bars_compare(ax, rev_vals, nrev_vals, title, xlabel, bins=10):
    """Histograma comparativo REV vs NO-REV"""
    rv=[v for v in rev_vals if v is not None]
    nv=[v for v in nrev_vals if v is not None]
    if not rv or not nv: ax.text(5,5,'sin datos',color=SOFT,ha='center'); return
    all_v=rv+nv
    b=np.linspace(min(all_v),max(all_v),bins+1)
    ax.hist(rv, bins=b, alpha=0.65, color=GRN, label=f'SUBE n={len(rv)}', density=True)
    ax.hist(nv, bins=b, alpha=0.60, color=RED, label=f'BAJA n={len(nv)}', density=True)
    if rv: ax.axvline(np.mean(rv),color=GRN,lw=2.5,ls='--',label=f'μSUBE={np.mean(rv):.1f}')
    if nv: ax.axvline(np.mean(nv),color=RED,lw=2.5,ls='--',label=f'μBAJA={np.mean(nv):.1f}')
    ax.set_title(title,color=GOLD,fontsize=11,fontweight='bold')
    ax.set_xlabel(xlabel,color=SOFT,fontsize=9)
    ax.set_ylabel('Densidad',color=SOFT,fontsize=8)
    ax.legend(fontsize=9.5,facecolor=BG,labelcolor=WHITE)
    ax.tick_params(colors=SOFT)
    [ax.spines[s].set_visible(False) for s in ['top','right']]

# ── A. COT Index —————————————————————-
ax=fig.add_subplot(gs[0,0]); ax.set_facecolor(PANEL2)
bars_compare(ax,
    [r['cot_idx'] for r in REV_cot],[r['cot_idx'] for r in NREV_cot],
    'COT Index cuando hay SWEEP\n¿Diferente entre sube/baja?','COT Index (0=bajista, 100=alcista)')

# ── B. COT Delta (divergencia) ———————————-
ax=fig.add_subplot(gs[0,1]); ax.set_facecolor(PANEL2)
bars_compare(ax,
    [r['cot_delta'] for r in REV_cot],[r['cot_delta'] for r in NREV_cot],
    'COT Delta (Divergencia)\nInstitucionales comprando o vendiendo?','COT Delta (contratos/semana)')

# ── C. VXN ————————————————————————-
ax=fig.add_subplot(gs[0,2]); ax.set_facecolor(PANEL2)
bars_compare(ax,
    [r['vxn'] for r in REV_cot],[r['vxn'] for r in NREV_cot],
    'VXN cuando hay SWEEP\n¿Más volatilidad → más reversión?','VXN (Volatilidad NQ)')

# ── D. COT BULL WR por threshold ——————————-
ax=fig.add_subplot(gs[1,0]); ax.set_facecolor(PANEL2)
thresholds=[20,25,30,35,40,45,50,55,60,65,70,75,80]
wrs_above=[]; ns_above=[]
for thr in thresholds:
    grp=[r for r in all_cases if r['has_cot'] and r['cot_idx'] and r['cot_idx']>=thr]
    wr_=sum(1 for r in grp if r['reversal'])/max(1,len(grp))*100
    wrs_above.append(wr_); ns_above.append(len(grp))
ax.plot(thresholds,wrs_above,color=GRN,lw=2.5,marker='o',ms=7)
ax.axhline(50,color=DIM,lw=1.5,ls='--',alpha=0.6,label='50% base')
ax.fill_between(thresholds,wrs_above,50,
                where=[w>50 for w in wrs_above],alpha=0.2,color=GRN,label='Edge ▲')
ax.fill_between(thresholds,wrs_above,50,
                where=[w<=50 for w in wrs_above],alpha=0.2,color=RED,label='Edge ▼')
for t,w,n_ in zip(thresholds,wrs_above,ns_above):
    if n_>3: ax.text(t,w+2,f'{w:.0f}%\nn={n_}',ha='center',fontsize=7.5,color=SOFT)
ax.set_title('WR Reversión vs Umbral COT Index\n¿Cuándo el COT index predice bien?',color=GOLD,fontsize=11,fontweight='bold')
ax.set_xlabel('COT Index ≥ X',color=SOFT); ax.set_ylabel('% que revierte (sube)',color=SOFT)
ax.set_ylim(0,100); ax.legend(fontsize=9,facecolor=BG,labelcolor=WHITE)
ax.tick_params(colors=SOFT); [ax.spines[s].set_visible(False) for s in ['top','right']]

# ── E. VXN threshold heatmap ——————————————-
ax=fig.add_subplot(gs[1,1]); ax.set_facecolor(PANEL2)
vxn_thr=[15,18,20,22,25,28,30,35]
wrs_v_hi=[]; wrs_v_lo=[]; ns_v=[]
for vt in vxn_thr:
    g_hi=[r for r in all_cases if r['has_cot'] and r['vxn'] and r['vxn']>=vt]
    g_lo=[r for r in all_cases if r['has_cot'] and r['vxn'] and r['vxn']< vt]
    wr_h=sum(1 for r in g_hi if r['reversal'])/max(1,len(g_hi))*100
    wr_l=sum(1 for r in g_lo if r['reversal'])/max(1,len(g_lo))*100
    wrs_v_hi.append(wr_h); wrs_v_lo.append(wr_l); ns_v.append((len(g_hi),len(g_lo)))
ax.plot(vxn_thr,wrs_v_hi,color=RED,lw=2.5,marker='s',ms=7,label='VXN ≥ X')
ax.plot(vxn_thr,wrs_v_lo,color=GRN,lw=2.5,marker='o',ms=7,label='VXN < X')
ax.axhline(50,color=DIM,lw=1.5,ls='--',alpha=0.6)
for t,h,l,(nh,nl) in zip(vxn_thr,wrs_v_hi,wrs_v_lo,ns_v):
    if nh>2: ax.text(t,h+2,f'{h:.0f}%',ha='center',fontsize=8,color=RED)
    if nl>2: ax.text(t,l-5,f'{l:.0f}%',ha='center',fontsize=8,color=GRN)
ax.set_title('WR Reversión vs VXN Umbral\nMás VXN = ¿más o menos reversión?',color=GOLD,fontsize=11,fontweight='bold')
ax.set_xlabel('VXN umbral',color=SOFT); ax.set_ylabel('% que revierte',color=SOFT)
ax.set_ylim(0,100); ax.legend(fontsize=9.5,facecolor=BG,labelcolor=WHITE)
ax.tick_params(colors=SOFT); [ax.spines[s].set_visible(False) for s in ['top','right']]

# ── F. Tipo Lunes —————————————————————-
ax=fig.add_subplot(gs[1,2]); ax.set_facecolor(PANEL2)
mon_types=['BULL_STRONG','BULL','FLAT','BEAR']
wr_by_mon=[]; n_by_mon=[]
for mt in mon_types:
    g=[r for r in all_cases if r['mon_type']==mt]
    wr_=sum(1 for r in g if r['reversal'])/max(1,len(g))*100
    wr_by_mon.append(wr_); n_by_mon.append(len(g))
colors_m=[GRN if w>55 else (RED if w<45 else GOLD) for w in wr_by_mon]
bars_m=ax.bar(range(len(mon_types)),wr_by_mon,color=colors_m,alpha=0.85,width=0.6)
ax.axhline(50,color=WHITE,lw=1.5,ls='--',alpha=0.5)
for i,(b,w,n_) in enumerate(zip(bars_m,wr_by_mon,n_by_mon)):
    ax.text(b.get_x()+b.get_width()/2, w+2, f'{w:.0f}%',
            ha='center',fontsize=13,color='white',fontweight='bold')
    ax.text(b.get_x()+b.get_width()/2, 5, f'n={n_}',
            ha='center',fontsize=10,color=SOFT)
ax.set_xticks(range(len(mon_types)))
ax.set_xticklabels(mon_types,fontsize=10,color=SOFT)
ax.set_ylim(0,100); ax.set_title('¿Qué tipo de LUNES precede\nal SWEEP con reversión?',color=GOLD,fontsize=11,fontweight='bold')
ax.set_ylabel('% que revierte',color=SOFT)
ax.tick_params(colors=SOFT); [ax.spines[s].set_visible(False) for s in ['top','right']]

# ── G. TABLA RESUMEN FILTROS ——————————————-
ax=fig.add_subplot(gs[2,:]); ax.set_facecolor('#07070f'); ax.axis('off')
ax.set_xlim(0,28); ax.set_ylim(0,10)
ax.text(14,9.5,'TABLA FINAL: MEJORES FILTROS PARA SWEEP+REVERSAL → ¿CUÁNDO ES ALTA PROBABILIDAD LONG?',
        ha='center',fontsize=12,fontweight='bold',color=GOLD,va='center')

combos_full=[
    ('SIN FILTRO (base)','(todos los 103 sweeps)',len(REV),N,''),
    ('─────','────────','─','─',''),
    ('COT NEUTRAL (Datos limitados)','Señal más débil','?','?','⚠️'),
    ('COT NEUTRAL-BULL','Señal media',20,20+20,'✅ mejor'),
]
# Calcular combos reales con datos
combo_results=[]
for label,cond,filt in [
    ('COT BULL + VXN>22','COT bullish, VXN elevada',lambda r:r['has_cot'] and r['cot_bull'] and r['vxn'] and r['vxn']>22),
    ('COT BULL + VXN<22','COT bullish, mercado calmado',lambda r:r['has_cot'] and r['cot_bull'] and r['vxn'] and r['vxn']<=22),
    ('COT BULL + Delta>0','Inst. aumentaron posición',lambda r:r['has_cot'] and r['cot_bull'] and r['cot_delta'] and r['cot_delta']>0),
    ('COT BULL + Delta<0','Inst. redujeron posición',lambda r:r['has_cot'] and r['cot_bull'] and r['cot_delta'] and r['cot_delta']<=0),
    ('COT idx>50','COT mayoritariamente alcista',lambda r:r['has_cot'] and r['cot_idx'] and r['cot_idx']>50),
    ('Lunes BEAR + COT_BULL','Lunes bajista + inst. alcistas',lambda r:r['has_cot'] and r['cot_bull'] and r['mon_type']=='BEAR'),
    ('Lunes FLAT + COT_BULL','Lunes lateral + inst. alcistas',lambda r:r['has_cot'] and r['cot_bull'] and r['mon_type']=='FLAT'),
    ('SIN FILTRO (base)','Todos los sweep cases',lambda r:True),
]:
    g=[r for r in all_cases if filt(r)]
    if not g: continue
    rev_=sum(1 for r in g if r['reversal'])
    wr=rev_/len(g)*100
    combo_results.append((label,cond,rev_,len(g),wr))

combo_results.sort(key=lambda x:-x[4])

# Dibujar tabla
headers=['Filtro','Condición','Rev.','Total','WR %','Calidad']
col_x=[0.3,5.5,13.5,15.5,17.5,21]
col_w=[5.2,8.0,2.0,2.0,2.0,6.8]
ax.text(14,9.1,'',ha='center',fontsize=9,color=SOFT)

# Header
for hdr,x in zip(headers,col_x):
    ax.text(x,8.7,hdr,fontsize=10,color=GOLD,fontweight='bold',va='center')
ax.axhline(8.4,color=DIM,lw=0.8,xmin=0.01,xmax=0.99)

y_row=7.9
for (label,cond,rev_,tot,wr) in combo_results[:8]:
    mark='🎯 EXCELENTE' if wr>=70 else ('✅ BUENO' if wr>=60 else ('⚠️  NEUTRAL' if wr>=50 else '❌ EVITAR'))
    c_=GRN if wr>=65 else (RED if wr<45 else GOLD)
    for txt,x in zip([label,cond,str(rev_),str(tot),f'{wr:.0f}%',mark],[col_x[0],col_x[1],col_x[2],col_x[3],col_x[4],col_x[5]]):
        fw='bold' if txt in [f'{wr:.0f}%',mark] else 'normal'
        ax.text(x,y_row,txt,fontsize=9.5,color=c_ if txt in [f'{wr:.0f}%',mark,label] else SOFT,
                fontweight=fw,va='center')
    y_row-=0.85

out='cot_sweep_profundo.png'
plt.savefig(out,dpi=120,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
