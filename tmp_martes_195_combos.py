"""
martes_195_combos.py
ESTUDIO COMPLETO — 195 MARTES (2017-2026)
Usando CSV 15min como proxy de las primeras 3 velas
Foco: RRR / VVV → ¿qué hace el día SIEMPRE?
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; SOFT='#94a3b8'; DIM='#475569'
ORG='#f97316'; WHITE='#f1f5f9'; TEAL='#14b8a6'

print("Cargando 15min historico...")
by_date = defaultdict(list)
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
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
            by_date[et.date()].append({
                'et':et, 'o':float(r['Open']), 'h':float(r['High']),
                'l':float(r['Low']), 'c':float(r['Close'])
            })
        except: pass

def ny_bars(d):
    return sorted(
        [b for b in by_date.get(d,[])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x:x['et']
    )

# ── PROCESAR TODOS LOS MARTES ──────────────────────────────────────────
records = []

for d in sorted(by_date.keys()):
    if d.weekday() != 1: continue

    bars = ny_bars(d)
    if len(bars) < 8: continue

    mon = d - timedelta(days=1)
    mon_bars = ny_bars(mon)
    if len(mon_bars) < 4: continue

    # 15min → 3 velas proxy: 9:30, 9:45, 10:00
    def get_v(h, m):
        return next((b for b in bars if b['et'].hour==h and b['et'].minute==m), None)

    v1 = get_v(9, 30)
    v2 = get_v(9, 45)
    v3 = get_v(10, 0)
    v3b= get_v(10, 15)  # 4ta vela

    if not v1 or not v2: continue

    def vchar(v):
        if v is None: return None
        body=abs(v['c']-v['o']); rng=v['h']-v['l'] or 1
        return {
            'bull': v['c']>v['o'],
            'body': round(body,1), 'rng': round(rng,1),
            'str':  'FUERTE' if body>rng*0.6 else ('DEBIL' if body<rng*0.3 else 'MEDIA'),
        }

    vc1=vchar(v1); vc2=vchar(v2); vc3=vchar(v3); vc4=vchar(v3b)

    tue_open  = v1['o']
    tue_close = bars[-1]['c']
    tue_hi    = max(b['h'] for b in bars)
    tue_lo    = min(b['l'] for b in bars)
    tue_chg   = round(tue_close - tue_open, 1)
    tue_bull  = tue_chg > 0
    tue_rng   = round(tue_hi - tue_lo, 1)

    mon_lo = min(b['l'] for b in mon_bars)
    mon_hi = max(b['h'] for b in mon_bars)
    mon_chg= round(mon_bars[-1]['c'] - mon_bars[0]['o'], 1)
    pct_m  = mon_chg / mon_bars[0]['o'] * 100
    mon_type=('BULL_STRONG' if pct_m>=0.8 else 'BULL' if pct_m>=0.3
              else 'FLAT' if pct_m>=-0.3 else 'BEAR' if pct_m>=-0.8 else 'BEAR_STRONG')

    # Combos (V=verde R=roja)
    combo2 = ('V' if vc1['bull'] else 'R') + '+' + ('V' if vc2['bull'] else 'R')
    combo3 = combo2 + '+' + (('V' if vc3['bull'] else 'R') if vc3 else '?')
    combo4 = combo3 + '+' + (('V' if vc4['bull'] else 'R') if vc4 else '?')

    # Primer impulso (primeras 3 velas de 15min = ~45min)
    first_bull = vc1['bull']  # dirección de v1
    # ¿El día termina en esa dirección?
    follow_v1 = (vc1['bull'] == tue_bull)

    # Fuerza v1
    v1_strong = vc1['str'] == 'FUERTE'
    v1_weak   = vc1['str'] == 'DEBIL'

    # Sweeps
    TOL=8
    swept_lo = any(b['l'] <= mon_lo+TOL for b in bars)
    swept_hi = any(b['h'] >= mon_hi-TOL for b in bars)

    # Timing HIGH y LOW
    hi_bar = max(bars, key=lambda x:x['h'])
    lo_bar = min(bars, key=lambda x:x['l'])
    hi_time=hi_bar['et'].strftime('%H:%M')
    lo_time=lo_bar['et'].strftime('%H:%M')

    # ¿El min/max se forma antes o después de las 11 ET?
    hi_early = hi_bar['et'].hour < 11
    lo_early = lo_bar['et'].hour < 11

    records.append({
        'd':d, 'mon_type':mon_type, 'mon_chg':mon_chg,
        'mon_lo':mon_lo, 'mon_hi':mon_hi,
        'tue_bull':tue_bull, 'tue_chg':tue_chg, 'tue_rng':tue_rng,
        'tue_hi':tue_hi, 'tue_lo':tue_lo,
        'vc1':vc1, 'vc2':vc2, 'vc3':vc3,
        'combo2':combo2, 'combo3':combo3, 'combo4':combo4,
        'follow_v1':follow_v1, 'v1_strong':v1_strong, 'v1_weak':v1_weak,
        'swept_lo':swept_lo, 'swept_hi':swept_hi,
        'hi_time':hi_time, 'lo_time':lo_time,
        'hi_early':hi_early, 'lo_early':lo_early,
    })

N=len(records)
print(f"Martes procesados: {N}")

# ═══════════════════════════════════════════════════════════════════════
# ANÁLISIS COMPLETO
# ═══════════════════════════════════════════════════════════════════════

print(f"\n{'='*65}")
print(f"COMBOS 2 VELAS (9:30 + 9:45 ET, 15min proxy, n={N})")
print(f"{'='*65}")
print(f"{'Combo':<10} {'N':>5} {'Dia Sube':>10} {'Avg Chg':>10} {'Avg Rng':>10}")
for c in ['V+V','V+R','R+V','R+R']:
    g=[r for r in records if r['combo2']==c]
    if not g: continue
    n_=len(g); up_=sum(1 for r in g if r['tue_bull'])
    avg=sum(r['tue_chg'] for r in g)/n_
    rng=sum(r['tue_rng'] for r in g)/n_
    print(f"{c:<10} {n_:>5} {up_/n_*100:>9.0f}%  {avg:>+9.0f}  {rng:>9.0f}")

print(f"\n{'='*65}")
print(f"COMBOS 3 VELAS (9:30 + 9:45 + 10:00 ET, 15min proxy)")
print(f"{'='*65}")
print(f"{'Combo':<12} {'N':>5} {'Dia Sube':>10} {'Avg Chg':>10} {'Avg Rng':>10}")
all_c3=sorted(set(r['combo3'] for r in records if '?' not in r['combo3']))
c3_data=[]
for c in all_c3:
    g=[r for r in records if r['combo3']==c]
    if len(g)<3: continue
    n_=len(g); up_=sum(1 for r in g if r['tue_bull'])
    avg=sum(r['tue_chg'] for r in g)/n_
    rng=sum(r['tue_rng'] for r in g)/n_
    c3_data.append((c,n_,up_,avg,rng))
    print(f"{c:<12} {n_:>5} {up_/n_*100:>9.0f}%  {avg:>+9.0f}  {rng:>9.0f}")

print(f"\n{'='*65}")
print(f"FOCO: RRR vs VVV (las señales MÁS CLARAS)")
print(f"{'='*65}")
for c,label in [('R+R+R','TRES ROJAS (bajista?)'),('V+V+V','TRES VERDES (alcista?)')]:
    g=[r for r in records if r['combo3']==c]
    if not g:
        print(f"{label}: sin datos"); continue
    n_=len(g); up_=sum(1 for r in g if r['tue_bull'])
    avg=sum(r['tue_chg'] for r in g)/n_
    rng=sum(r['tue_rng'] for r in g)/n_
    sw_lo=sum(1 for r in g if r['swept_lo'])
    sw_hi=sum(1 for r in g if r['swept_hi'])
    hi_e=sum(1 for r in g if r['hi_early'])
    lo_e=sum(1 for r in g if r['lo_early'])

    # Distribución por tipo de lunes
    mon_dist=Counter(r['mon_type'] for r in g)

    print(f"\n  {label} — n={n_}")
    print(f"  ├ Día sube:          {up_}/{n_} = {up_/n_*100:.0f}%")
    print(f"  ├ Día baja:          {n_-up_}/{n_} = {(n_-up_)/n_*100:.0f}%")
    print(f"  ├ Avg cambio día:    {avg:+.0f}pts")
    print(f"  ├ Avg rango NY:      {rng:.0f}pts")
    print(f"  ├ Barre LOW lunes:   {sw_lo}/{n_} = {sw_lo/n_*100:.0f}%")
    print(f"  ├ Barre HIGH lunes:  {sw_hi}/{n_} = {sw_hi/n_*100:.0f}%")
    print(f"  ├ Max antes 11ET:    {hi_e}/{n_} = {hi_e/n_*100:.0f}%")
    print(f"  ├ Min antes 11ET:    {lo_e}/{n_} = {lo_e/n_*100:.0f}%")
    print(f"  └ Tipo lunes: {dict(mon_dist)}")

    # Casos con lunes BULL_STRONG
    g_bull=[r for r in g if r['mon_type'] in ['BULL_STRONG','BULL']]
    if g_bull:
        up_b=sum(1 for r in g_bull if r['tue_bull'])
        print(f"     CON LUNES BULL (n={len(g_bull)}): día sube {up_b}/{len(g_bull)} = {up_b/len(g_bull)*100:.0f}%")

print(f"\n{'='*65}")
print(f"V1 FUERTE vs DÉBIL → predicción")
print(f"{'='*65}")
g_str=[r for r in records if r['v1_strong']]
g_wk =[r for r in records if r['v1_weak']]
for grp,lbl in[(g_str,'V1 FUERTE (body>60%rng)'),(g_wk,'V1 DÉBIL  (body<30%rng)')]:
    if not grp: continue
    n_=len(grp); up_=sum(1 for r in grp if r['follow_v1'])
    print(f"  {lbl} n={n_}: sigue v1 = {up_}/{n_} = {up_/n_*100:.0f}%")

print(f"\n{'='*65}")
print(f"TIMING MAX y MIN (todos los martes, 15min)")
print(f"{'='*65}")
hi_early_all=sum(1 for r in records if r['hi_early'])
lo_early_all=sum(1 for r in records if r['lo_early'])
print(f"  Max del día ANTES de 11ET: {hi_early_all}/{N} = {hi_early_all/N*100:.0f}%")
print(f"  Min del día ANTES de 11ET: {lo_early_all}/{N} = {lo_early_all/N*100:.0f}%")
hi_c=Counter(r['hi_time'] for r in records)
lo_c=Counter(r['lo_time'] for r in records)
print(f"  Top 5 horarios del MAX:")
for t,c in hi_c.most_common(5): print(f"    {t}: {c}x ({c/N*100:.0f}%)")
print(f"  Top 5 horarios del MIN:")
for t,c in lo_c.most_common(5): print(f"    {t}: {c}x ({c/N*100:.0f}%)")

print(f"\n{'='*65}")
print(f"SWEEPS GLOBALES")
print(f"{'='*65}")
sw_lo_all=sum(1 for r in records if r['swept_lo'])
sw_hi_all=sum(1 for r in records if r['swept_hi'])
print(f"  Barre LOW lunes:  {sw_lo_all}/{N} = {sw_lo_all/N*100:.0f}%")
print(f"  Barre HIGH lunes: {sw_hi_all}/{N} = {sw_hi_all/N*100:.0f}%")

# ═══════════════════════════════════════════════════════════════════════
# FIGURA
# ═══════════════════════════════════════════════════════════════════════
fig=plt.figure(figsize=(28,18),facecolor=BG)
fig.suptitle(
    f"ESTUDIO 195 MARTES NQ (2017-2026) — ¿Qué se repite SIEMPRE?\n"
    f"Apertura NY 9:30 ET | 15min proxy | n={N} casos",
    color=GOLD,fontsize=14,fontweight='bold',y=0.998
)
gs=gridspec.GridSpec(2,4,figure=fig,hspace=0.40,wspace=0.32,
                     left=0.04,right=0.98,top=0.96,bottom=0.05)

# 1. COMBO 2 VELAS
ax1=fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
c2=['V+V','R+R','V+R','R+V']
c2_g=[r for r in records if r['combo2']=='V+V']
c2_r=[r for r in records if r['combo2']=='R+R']
c2_m=[r for r in records if r['combo2']=='V+R']
c2_rv=[r for r in records if r['combo2']=='R+V']
grps_2=[c2_g,c2_r,c2_m,c2_rv]
vals_2=[sum(1 for r in g if r['tue_bull'])/max(1,len(g))*100 for g in grps_2]
ns_2=[len(g) for g in grps_2]
clrs_2=[GRN,RED,GOLD,TEAL]
bars1=ax1.bar(range(4),vals_2,color=clrs_2,alpha=0.85,width=0.65)
ax1.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,v,n_ in zip(bars1,vals_2,ns_2):
    ax1.text(b.get_x()+b.get_width()/2,v+2,f'{v:.0f}%',color='white',
             ha='center',fontsize=14,fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2,8,f'n={n_}',color=SOFT,ha='center',fontsize=10)
ax1.set_xticks(range(4)); ax1.set_xticklabels(['V+V','R+R','V+R','R+V'],fontsize=11,color=SOFT)
ax1.set_ylim(0,100); ax1.set_ylabel('% Día Sube',color=SOFT)
ax1.set_title('COMBO 2 VELAS\n(9:30+9:45 ET)',color=GOLD,fontsize=11,fontweight='bold')
ax1.tick_params(colors=SOFT); [ax1.spines[s].set_visible(False) for s in ['top','right']]

# 2. COMBO 3 VELAS — barras horizontales
ax2=fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
c3_plot=[(c,n_,up_/n_*100,avg) for c,n_,up_,avg,rng in c3_data]
c3_plot.sort(key=lambda x:-x[1])  # por frecuencia
y3=np.arange(len(c3_plot))
clrs_c3=[GRN if d[2]>=60 else (RED if d[2]<40 else GOLD) for d in c3_plot]
bars2=ax2.barh(y3,[d[2] for d in c3_plot],color=clrs_c3,alpha=0.85)
ax2.axvline(50,color='white',lw=1.2,ls='--',alpha=0.5)
for b,d in zip(bars2,c3_plot):
    ax2.text(d[2]+1.5,b.get_y()+b.get_height()/2,
             f'{d[2]:.0f}%  n={d[1]}  avg{d[3]:+.0f}pts',
             va='center',fontsize=9,color=WHITE,fontweight='bold')
ax2.set_yticks(y3); ax2.set_yticklabels([d[0] for d in c3_plot],fontsize=10,color=SOFT)
ax2.set_xlim(0,120); ax2.set_xlabel('% Día Sube',color=SOFT)
ax2.set_title('COMBO 3 VELAS\n(9:30+9:45+10:00 ET)',color=GOLD,fontsize=11,fontweight='bold')
ax2.tick_params(colors=SOFT); [ax2.spines[s].set_visible(False) for s in ['top','right']]

# 3. RRR vs VVV detalle
ax3=fig.add_subplot(gs[0,2]); ax3.set_facecolor(PANEL2)
g_rrr=[r for r in records if r['combo3']=='R+R+R']
g_vvv=[r for r in records if r['combo3']=='V+V+V']

cats_d=['Día sube','Barre\nLOW','Barre\nHIGH','Max<11ET','Min<11ET']
def pct(grp, fn): return sum(1 for r in grp if fn(r))/max(1,len(grp))*100

rrr_vals=[100-pct(g_rrr,lambda r:r['tue_bull']),  # % DÍA BAJA para RRR
          pct(g_rrr,lambda r:r['swept_lo']),
          pct(g_rrr,lambda r:r['swept_hi']),
          pct(g_rrr,lambda r:r['lo_early']),  # Min early (más relevante en bajista)
          pct(g_rrr,lambda r:r['hi_early'])]

vvv_vals=[pct(g_vvv,lambda r:r['tue_bull']),
          pct(g_vvv,lambda r:r['swept_lo']),
          pct(g_vvv,lambda r:r['swept_hi']),
          pct(g_vvv,lambda r:r['hi_early']),  # Max early (más relevante en alcista)
          pct(g_vvv,lambda r:r['lo_early'])]

x3=np.arange(len(cats_d)); w=0.35
bars3r=ax3.bar(x3-w/2,rrr_vals,w,color=RED,alpha=0.85,label=f'RRR (n={len(g_rrr)})')
bars3v=ax3.bar(x3+w/2,vvv_vals,w,color=GRN,alpha=0.85,label=f'VVV (n={len(g_vvv)})')
for b,v in zip(list(bars3r)+list(bars3v),rrr_vals+vvv_vals):
    ax3.text(b.get_x()+b.get_width()/2,v+1.5,f'{v:.0f}%',ha='center',fontsize=9.5,color=WHITE,fontweight='bold')
ax3.set_xticks(x3); ax3.set_xticklabels(cats_d,fontsize=9.5,color=SOFT)
ax3.set_ylim(0,115); ax3.set_ylabel('%',color=SOFT)
ax3.set_title(f'RRR vs VVV — Comportamiento\n(n={len(g_rrr)} RRR | n={len(g_vvv)} VVV)',
              color=GOLD,fontsize=11,fontweight='bold')
ax3.legend(fontsize=9.5,facecolor=BG,labelcolor=SOFT)
ax3.tick_params(colors=SOFT); [ax3.spines[s].set_visible(False) for s in ['top','right']]

# 4. Card resumen SIEMPRE
ax4=fig.add_subplot(gs[0,3]); ax4.set_facecolor('#07070f'); ax4.axis('off')
ax4.set_xlim(0,10); ax4.set_ylim(0,22)
ax4.add_patch(patches.FancyBboxPatch((0.2,20.8),9.6,0.95,
    boxstyle='round,pad=0.1',facecolor='#1a0a00',edgecolor=GOLD,linewidth=2.5))
ax4.text(5,21.3,'LO QUE PASA SIEMPRE',ha='center',va='center',fontsize=11,fontweight='bold',color=GOLD)

rrr_down_pct=pct(g_rrr,lambda r:not r['tue_bull'])
vvv_up_pct=pct(g_vvv,lambda r:r['tue_bull'])
follow_all=sum(1 for r in records if r['follow_v1'])/N*100
str_fol=sum(1 for r in records if r['v1_strong'] and r['follow_v1'])/max(1,sum(1 for r in records if r['v1_strong']))*100
hi_early_pct=hi_early_all/N*100; lo_early_pct=lo_early_all/N*100
avg_rng=sum(r['tue_rng'] for r in records)/N

siempre=[
    (GOLD,'bold','── SEÑAL COMBO 3 VELAS ──',''),
    (RED,'bold',f'R+R+R → día BAJA:',f'{rrr_down_pct:.0f}%  ({len(g_rrr)} casos)'),
    (GRN,'bold',f'V+V+V → día SUBE:',f'{vvv_up_pct:.0f}%  ({len(g_vvv)} casos)'),
    ('','','',''),
    (GOLD,'bold','── DIRECCIÓN V1 ──',''),
    (BLU,'bold','V1 cualquiera → sigue día:',f'{follow_all:.0f}%'),
    (GRN,'bold','V1 FUERTE → sigue día:',f'{str_fol:.0f}%'),
    ('','','',''),
    (GOLD,'bold','── TIMING ──',''),
    (GOLD,'bold','Max antes 11ET:',f'{hi_early_pct:.0f}%  ({hi_early_all}/{N})'),
    (RED,'bold','Min antes 11ET:',f'{lo_early_pct:.0f}%  ({lo_early_all}/{N})'),
    (SOFT,'normal',f'Rango promedio NY:',f'{avg_rng:.0f}pts'),
    ('','','',''),
    (GOLD,'bold','── SWEEPS ──',''),
    (RED,'bold','Barre LOW lunes:',f'{sw_lo_all/N*100:.0f}%  ({sw_lo_all}/{N})'),
    (GOLD,'bold','Barre HIGH lunes:',f'{sw_hi_all/N*100:.0f}%  ({sw_hi_all}/{N})'),
    ('','','',''),
    (TEAL,'bold','── REGLA OPERATIVA ──',''),
    (GRN,'bold','R+R+R → SHORT en cierre V3','SL sobre HIGH V1'),
    (GRN,'bold','V+V+V → LONG en cierre V3','SL bajo LOW V1'),
    (RED,'bold','V1 DÉBIL → NO operar','Esperar confirmación'),
]
for i,(c,w,k,v) in enumerate(siempre):
    if not c: continue
    y=20.2-i*0.97
    ax4.text(0.4,y,k,fontsize=8.5,color=c,fontweight=w,va='center')
    if v: ax4.text(5.5,y,v,fontsize=8.5,color=c,fontweight='bold',va='center')

# 5. TIMING del HIGH y LOW (histograma por hora)
ax5=fig.add_subplot(gs[1,0:2]); ax5.set_facecolor(PANEL2)
def hr_num(t):
    h,m=int(t[:2]),int(t[3:])
    return h+m/60

hi_hrs=[hr_num(r['hi_time']) for r in records]
lo_hrs=[hr_num(r['lo_time']) for r in records]
bins_t=np.arange(9.5,16.25,0.25)

ax5.hist(hi_hrs,bins=bins_t,color=GOLD,alpha=0.75,label=f'Max del día (n={N})',edgecolor='none')
ax5.hist(lo_hrs,bins=bins_t,color=RED,alpha=0.75,label=f'Min del día (n={N})',edgecolor='none')

# Destacar zonas clave
for xz,lbl,c in [(9.5,'9:30-10:00\nApertura',BLU),(10.0,'Power\nHour',PRP)]:
    ax5.axvspan(xz,xz+0.5,alpha=0.12,color=c)

ax5.set_xticks(np.arange(10,16.5,0.5))
ax5.set_xticklabels([f'{int(h)}:{int((h%1)*60):02d}' for h in np.arange(10,16.5,0.5)],
                    fontsize=8.5,color=SOFT,rotation=45)
ax5.set_ylabel('N Martes',color=SOFT)
ax5.set_title('¿A qué hora se forma el MÁXIMO y MÍNIMO del día en Martes? (195 casos)',
              color=GOLD,fontsize=12,fontweight='bold')
ax5.legend(fontsize=10.5,facecolor=BG,labelcolor=SOFT)
ax5.tick_params(colors=SOFT); [ax5.spines[s].set_visible(False) for s in ['top','right']]

# 6. WR del seguir V1 por fuerza de v1
ax6=fig.add_subplot(gs[1,2]); ax6.set_facecolor(PANEL2)
cats_v=['V1\nCualquiera','V1\nFUERTE','V1\nMEDIA','V1\nDÉBIL']
g_all=records
g_str=[r for r in records if r['v1_strong']]
g_med=[r for r in records if not r['v1_strong'] and not r['v1_weak']]
g_wk =[r for r in records if r['v1_weak']]
wr_v=[sum(1 for r in g if r['follow_v1'])/max(1,len(g))*100 for g in [g_all,g_str,g_med,g_wk]]
ns_v=[len(g) for g in [g_all,g_str,g_med,g_wk]]
clrs_v=[BLU,GRN,GOLD,RED]
bars6=ax6.bar(range(4),wr_v,color=clrs_v,alpha=0.85,width=0.6)
ax6.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,w,n_ in zip(bars6,wr_v,ns_v):
    ax6.text(b.get_x()+b.get_width()/2,w+2,f'{w:.0f}%',ha='center',fontsize=13,color='white',fontweight='bold')
    ax6.text(b.get_x()+b.get_width()/2,8,f'n={n_}',ha='center',fontsize=10,color=SOFT)
ax6.set_xticks(range(4)); ax6.set_xticklabels(cats_v,fontsize=10,color=SOFT)
ax6.set_ylim(0,100); ax6.set_ylabel('% día sigue dirección V1',color=SOFT)
ax6.set_title('¿La FUERZA de V1\npredice mejor el día?',color=GOLD,fontsize=11,fontweight='bold')
ax6.tick_params(colors=SOFT); [ax6.spines[s].set_visible(False) for s in ['top','right']]

# 7. RRR detail por año
ax7=fig.add_subplot(gs[1,3]); ax7.set_facecolor(PANEL2)
years=sorted(set(r['d'].year for r in g_rrr))
rrr_by_yr=[(y,
            [r for r in g_rrr if r['d'].year==y]) for y in years]
yr_lbl=[str(y) for y,_ in rrr_by_yr]
yr_dn=[sum(1 for r in g if not r['tue_bull'])/max(1,len(g))*100 for _,g in rrr_by_yr]
yr_n=[len(g) for _,g in rrr_by_yr]
bars7=ax7.bar(range(len(yr_lbl)),yr_dn,color=[RED if v>=60 else GOLD for v in yr_dn],alpha=0.85,width=0.7)
ax7.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,v,n_ in zip(bars7,yr_dn,yr_n):
    ax7.text(b.get_x()+b.get_width()/2,v+2,f'{v:.0f}%',ha='center',fontsize=11,color='white',fontweight='bold')
    ax7.text(b.get_x()+b.get_width()/2,8,f'n={n_}',ha='center',fontsize=9,color=SOFT)
ax7.set_xticks(range(len(yr_lbl))); ax7.set_xticklabels(yr_lbl,fontsize=10,color=SOFT)
ax7.set_ylim(0,110); ax7.set_ylabel('% Día BAJA (bearish)',color=SOFT)
ax7.set_title(f'RRR → % que el día BAJA\npor año (total n={len(g_rrr)})',color=GOLD,fontsize=11,fontweight='bold')
ax7.tick_params(colors=SOFT); [ax7.spines[s].set_visible(False) for s in ['top','right']]

out='martes_195_siempre.png'
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
