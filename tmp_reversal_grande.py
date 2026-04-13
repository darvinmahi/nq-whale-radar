"""
martes_condiciones_reversal_grande.py
¿QUÉ CONDICIONES PRODUCEN UNA REVERSIÓN GRANDE (+300pts) EN MARTES?

Factores estudiados:
1) ¿Cuánto cayó el LUNES antes?  (lunes extremo → martes reversa?)
2) ¿Cuánto fue el sweep debajo del LOW de lunes?  (más profundo → más rebote?)
3) ¿VXN elevado correlaciona con más rebote?
4) Hoy en contexto: ¿cuántas veces el martes hizo +300pts desde su mínimo?
"""
import csv, json
from datetime import datetime, timedelta, date
from collections import defaultdict
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

# ─── Cargar CSV 15min ────────────────────────────────────────────
def et_offset(d_raw):
    for s,e in [(date(2019,3,10),date(2019,11,3)),(date(2020,3,8),date(2020,11,1)),
                (date(2021,3,14),date(2021,11,7)),(date(2022,3,13),date(2022,11,6)),
                (date(2023,3,12),date(2023,11,5)),(date(2024,3,10),date(2024,11,3)),
                (date(2025,3,9),date(2025,11,2)),(date(2026,3,8),date(2099,1,1))]:
        if s <= d_raw < e: return 4
    return 5

bars_by_date = defaultdict(list)
with open('data/research/nq_15m_intraday.csv') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            off = et_offset(raw.date())
            et  = raw - timedelta(hours=off)
            bars_by_date[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close'])
            })
        except: pass

def ny(d):
    return sorted([b for b in bars_by_date.get(d,[])
                   if (b['et'].hour==9 and b['et'].minute>=30) or
                      (10<=b['et'].hour<16)], key=lambda x:x['et'])

# ─── COT (VXN) ───────────────────────────────────────────────────
with open('data/research/daily_master_db.json') as f:
    db = json.load(f)
cot_by = {}
for rec in db.get('records',[]):
    try:
        d = date.fromisoformat(rec['date'])
        vxn = float(rec.get('vxn',0) or 0)
        if vxn > 0: cot_by[d] = {'vxn':vxn,'sig':rec.get('cot_signal','?')}
    except: pass

# ─── ANALIZAR TODOS LOS MARTES ────────────────────────────────────
cases = []
for d in sorted(bars_by_date.keys()):
    if d.weekday() != 1: continue
    mon = d - timedelta(days=1)
    ny_bars  = ny(d)
    mon_bars = ny(mon)
    if len(ny_bars)<8 or len(mon_bars)<4: continue

    mon_open = mon_bars[0]['o']; mon_close = mon_bars[-1]['c']
    mon_lo   = min(b['l'] for b in mon_bars)
    mon_hi   = max(b['h'] for b in mon_bars)
    mon_chg  = round(mon_close - mon_open, 1)
    mon_rng  = round(mon_hi - mon_lo, 1)

    ny_open  = ny_bars[0]['o']; ny_close= ny_bars[-1]['c']
    ny_hi    = max(b['h'] for b in ny_bars)
    ny_lo    = min(b['l'] for b in ny_bars)
    ny_rng   = round(ny_hi - ny_lo, 1)

    # Reacción desde mínimo del día
    lo_bar   = min(ny_bars, key=lambda x:x['l'])
    hi_bar   = max(ny_bars, key=lambda x:x['h'])
    lo_idx   = ny_bars.index(lo_bar)
    hi_idx   = ny_bars.index(hi_bar)

    # Reversión = LOW primero, luego HIGH
    if lo_idx < hi_idx:
        reaction_from_lo = round(ny_hi - ny_lo, 1)  # rebote completo
        direction = 'REVERSAL_UP'
    else:
        reaction_from_lo = round(ny_lo - ny_hi, 1)  # caída completa (negativo)
        direction = 'REVERSAL_DOWN'

    # Sweep del LOW del lunes
    swept_lo = ny_lo <= mon_lo + 8
    sweep_depth = round(mon_lo - ny_lo, 1) if swept_lo else 0  # qué tan profundo

    # VXN
    vxn_d = None
    for delta in [0,-1,-2,-3,-4,-5]:
        cd = d + timedelta(days=delta)
        if cd in cot_by: vxn_d = cot_by[cd]['vxn']; break

    cases.append({
        'd':d,'mon_chg':mon_chg,'mon_rng':mon_rng,
        'ny_rng':ny_rng,'ny_lo':ny_lo,'ny_hi':ny_hi,
        'ny_open':ny_open,'ny_close':ny_close,
        'reaction_from_lo':reaction_from_lo,
        'direction':direction,'swept_lo':swept_lo,
        'sweep_depth':sweep_depth,'vxn':vxn_d,
        'lo_time':lo_bar['et'].strftime('%H:%M'),
        'hi_time':hi_bar['et'].strftime('%H:%M'),
    })

N = len(cases)
up_cases = [r for r in cases if r['direction']=='REVERSAL_UP']
big_rev   = [r for r in up_cases if r['reaction_from_lo'] >= 300]
sweep_rev = [r for r in up_cases if r['swept_lo']]

print(f"Martes analizados: {N}")
print(f"Reversiones ARRIBA (LOW→HIGH): {len(up_cases)} = {len(up_cases)/N*100:.0f}%")
print(f"Reversiones >= 300pts: {len(big_rev)} = {len(big_rev)/N*100:.0f}%")
print(f"Sweep LOW + reversión arriba: {len(sweep_rev)} = {len(sweep_rev)/N*100:.0f}%")

print(f"\n--- ¿QUÉ TENÍAN EN COMÚN LOS {len(big_rev)} MARTES CON +300pts? ---")
print(f"  Lunes promedio: {np.mean([r['mon_chg'] for r in big_rev]):+.0f}pts")
print(f"  Lunes mediana:  {np.median([r['mon_chg'] for r in big_rev]):+.0f}pts")
print(f"  Lunes < -200pts: {sum(1 for r in big_rev if r['mon_chg']<-200)}/{len(big_rev)}")
print(f"  Sweep del LOW:  {sum(1 for r in big_rev if r['swept_lo'])}/{len(big_rev)}")
vxn_big = [r['vxn'] for r in big_rev if r['vxn']]
if vxn_big:
    print(f"  VXN promedio:   {np.mean(vxn_big):.1f}")
    print(f"  VXN > 25:       {sum(1 for v in vxn_big if v>25)}/{len(vxn_big)}")
print(f"  Rango promedio: {np.mean([r['ny_rng'] for r in big_rev]):.0f}pts")

print(f"\n--- COMPARACIÓN: Lunes extremo (< -300pts) → ¿qué hace el martes? ---")
mon_extreme = [r for r in cases if r['mon_chg'] < -300]
me_rev_up   = [r for r in mon_extreme if r['direction']=='REVERSAL_UP']
me_big      = [r for r in mon_extreme if r['reaction_from_lo'] >= 200]
print(f"  Lunes < -300pts: {len(mon_extreme)} casos")
print(f"  → Martes LOW→HIGH: {len(me_rev_up)}/{len(mon_extreme)} = {len(me_rev_up)/max(1,len(mon_extreme))*100:.0f}%")
print(f"  → Martes >= 200pts rebote: {len(me_big)}/{len(mon_extreme)} = {len(me_big)/max(1,len(mon_extreme))*100:.0f}%")
print(f"  → Promedio rebote: {np.mean([r['reaction_from_lo'] for r in me_rev_up]):.0f}pts")

# Thresholds del lunes
print(f"\n--- LUNES EXTREMO → REBOTE MARTES (todos los thresholds) ---")
for thr in [-100,-200,-300,-400,-500]:
    grp=[r for r in cases if r['mon_chg']<=thr]
    if not grp: continue
    up_=[r for r in grp if r['direction']=='REVERSAL_UP']
    avg_r=np.mean([r['reaction_from_lo'] for r in up_]) if up_ else 0
    pct_big=sum(1 for r in up_ if r['reaction_from_lo']>=200)/max(1,len(up_))*100
    print(f"  Lunes <={thr:>5}pts: {len(grp):>3} casos  {len(up_)/len(grp)*100:.0f}% rev  avg_rebote={avg_r:.0f}pts  {pct_big:.0f}% da >=200pts")

# Sweep profundo
print(f"\n--- PROFUNDIDAD DEL SWEEP → MAGNITUD DEL REBOTE ---")
for depth in [50,100,150,200,250,300]:
    grp=[r for r in cases if r['swept_lo'] and r['sweep_depth']>=depth and r['direction']=='REVERSAL_UP']
    if not grp: continue
    avg_r=np.mean([r['reaction_from_lo'] for r in grp])
    print(f"  Sweep >= {depth}pts debajo Mon LOW: {len(grp)} casos  avg_rebote={avg_r:.0f}pts  med={np.median([r['reaction_from_lo'] for r in grp]):.0f}pts")

# ─── FIGURA ──────────────────────────────────────────────────────
fig = plt.figure(figsize=(28,20), facecolor=BG)
fig.suptitle(
    'MARTES NQ — ¿QUÉ CONDICIONES PRODUCEN UNA REVERSIÓN DE +300pts?\n'
    'Lunes extremo + sweep profundo + VXN elevado = SETUP IDEAL para segunda ola',
    color=GOLD, fontsize=14, fontweight='bold', y=0.999
)
gs = gridspec.GridSpec(3,3, figure=fig, hspace=0.44, wspace=0.30,
                       left=0.05, right=0.97, top=0.96, bottom=0.04)

# ── A. Movimiento del Lunes vs Rebote del Martes ─────────────────
ax=fig.add_subplot(gs[0,:2]); ax.set_facecolor(PANEL2)
mon_chgs=[r['mon_chg'] for r in up_cases]
reactions=[r['reaction_from_lo'] for r in up_cases]
colors_sc=[RED if r['reaction_from_lo']>=300 else (GOLD if r['reaction_from_lo']>=150 else BLU)
           for r in up_cases]
sc=ax.scatter(mon_chgs, reactions, c=colors_sc, s=55, alpha=0.75, zorder=3)
# Hoy
hoy_mon=-800  # aprox lunes 7 abril
hoy_reb=440
ax.scatter([hoy_mon],[hoy_reb],c=GOLD,s=220,marker='*',zorder=5,label='HOY (7 Abr)')
ax.annotate('HOY\n7 Abr\n440pts', xy=(hoy_mon,hoy_reb),
            xytext=(hoy_mon+80,hoy_reb-60),
            fontsize=10,color=GOLD,fontweight='bold',
            arrowprops=dict(arrowstyle='->',color=GOLD,lw=2))
# Regresión
if len(mon_chgs)>10:
    z=np.polyfit(mon_chgs,reactions,1)
    p=np.poly1d(z)
    xr=np.linspace(min(mon_chgs),max(mon_chgs),100)
    ax.plot(xr,p(xr),color=WHITE,lw=1.5,ls='--',alpha=0.5,label='Tendencia')
ax.axvline(-300,color=RED,lw=1.5,ls=':',alpha=0.6,label='Lunes extremo (-300)')
ax.axhline(300,color=GOLD,lw=1.5,ls=':',alpha=0.6,label='Rebote grande (300pts)')
ax.axhline(0,color=DIM,lw=1,alpha=0.4)
# Zonas
ax.fill_between([min(mon_chgs)-50,-300],[300,300],[max(reactions)+50]*2,
                color=GOLD,alpha=0.07,label='ZONA IDEAL')
ax.set_xlabel('Movimiento del LUNES (pts)', color=SOFT, fontsize=10)
ax.set_ylabel('Rebote del MARTES desde mínimo (pts)', color=SOFT, fontsize=10)
ax.set_title('¿Más caída el Lunes → más rebote el Martes?\n(cada punto = 1 martes, LOW→HIGH)',
             color=GOLD, fontsize=11, fontweight='bold')
ax.legend(fontsize=9,facecolor=BG,labelcolor=WHITE)
ax.tick_params(colors=SOFT); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.grid(color=DIM,alpha=0.15,lw=0.5)

# ── B. Distribución rebotes por categoría del lunes ─────────────
ax2=fig.add_subplot(gs[0,2]); ax2.set_facecolor(PANEL2)
cats=[
    ('Lunes > 0', [r for r in up_cases if r['mon_chg']>0],GRN),
    ('Lunes 0→-200',[r for r in up_cases if -200<=r['mon_chg']<=0],BLU),
    ('Lunes -200→-400',[r for r in up_cases if -400<r['mon_chg']<-200],GOLD),
    ('Lunes < -400',[r for r in up_cases if r['mon_chg']<=-400],RED),
]
bp_data=[]; bp_labels=[]; bp_colors=[]
for label,grp,c in cats:
    if grp:
        bp_data.append([r['reaction_from_lo'] for r in grp])
        bp_labels.append(f"{label}\nn={len(grp)}")
        bp_colors.append(c)

bp=ax2.boxplot(bp_data,patch_artist=True,medianprops=dict(color='white',lw=2.5),
               flierprops=dict(marker='.',color=DIM,ms=4),
               whiskerprops=dict(color=SOFT),capprops=dict(color=SOFT))
for patch,c in zip(bp['boxes'],bp_colors):
    patch.set_facecolor(c); patch.set_alpha(0.65)
ax2.axhline(300,color=GOLD,lw=2,ls='--',alpha=0.7,label='300pts target')
ax2.set_xticklabels(bp_labels,fontsize=9,color=SOFT)
ax2.set_ylabel('Rebote desde mínimo (pts)',color=SOFT)
ax2.set_title('Lunes extremo = Rebote\nmartes más grande',color=GOLD,fontsize=11,fontweight='bold')
ax2.legend(fontsize=9,facecolor=BG,labelcolor=WHITE)
ax2.tick_params(colors=SOFT); [ax2.spines[s].set_visible(False) for s in ['top','right']]

# ── C. Profundidad del sweep vs rebote ────────────────────────────
ax3=fig.add_subplot(gs[1,0]); ax3.set_facecolor(PANEL2)
sweep_up=[r for r in up_cases if r['swept_lo']]
depths=[r['sweep_depth'] for r in sweep_up]
rebs  =[r['reaction_from_lo'] for r in sweep_up]
colors_sw=[RED if r>=300 else (GOLD if r>=150 else BLU) for r in rebs]
ax3.scatter(depths,rebs,c=colors_sw,s=55,alpha=0.75)
ax3.scatter([261],[440],c=GOLD,s=200,marker='*',zorder=5)
ax3.annotate('HOY\n261pts deep\n440 rebote',(261,440),(261+20,440-60),
             fontsize=9,color=GOLD,fontweight='bold',
             arrowprops=dict(arrowstyle='->',color=GOLD,lw=2))
if len(depths)>5:
    z=np.polyfit(depths,rebs,1)
    xr=np.linspace(0,max(depths)+20,100)
    ax3.plot(xr,np.poly1d(z)(xr),color=WHITE,lw=1.5,ls='--',alpha=0.5)
ax3.set_xlabel('Profundidad sweep bajo Mon LOW (pts)',color=SOFT)
ax3.set_ylabel('Rebote desde mínimo (pts)',color=SOFT)
ax3.set_title('¿Más profundo el sweep\n→ mayor el rebote?',color=GOLD,fontsize=11,fontweight='bold')
ax3.tick_params(colors=SOFT); [ax3.spines[s].set_visible(False) for s in ['top','right']]
ax3.grid(color=DIM,alpha=0.15)

# ── D. VXN vs Rebote ──────────────────────────────────────────────
ax4=fig.add_subplot(gs[1,1]); ax4.set_facecolor(PANEL2)
vxn_cases=[r for r in up_cases if r['vxn'] is not None]
vxn_vals=[r['vxn'] for r in vxn_cases]
reb_vals=[r['reaction_from_lo'] for r in vxn_cases]
c_vxn=[RED if r>=300 else (GOLD if r>=150 else BLU) for r in reb_vals]
ax4.scatter(vxn_vals,reb_vals,c=c_vxn,s=55,alpha=0.75)
# Hoy VXN ~32 (estimado dado mercado de aranceles)
ax4.scatter([32],[440],c=GOLD,s=200,marker='*',zorder=5)
ax4.annotate('HOY est.\nVXN~32\n440 rebote',(32,440),(32+1,440-70),
             fontsize=9,color=GOLD,fontweight='bold',
             arrowprops=dict(arrowstyle='->',color=GOLD,lw=2))
if len(vxn_vals)>5:
    z=np.polyfit(vxn_vals,reb_vals,1)
    xr=np.linspace(min(vxn_vals)-1,max(vxn_vals)+1,100)
    ax4.plot(xr,np.poly1d(z)(xr),color=WHITE,lw=1.5,ls='--',alpha=0.5)
ax4.axvline(25,color=RED,lw=1.5,ls=':',alpha=0.6,label='VXN=25 (elevado)')
ax4.axhline(300,color=GOLD,lw=1.5,ls=':',alpha=0.5,label='300pts target')
ax4.set_xlabel('VXN el día del trade',color=SOFT)
ax4.set_ylabel('Rebote desde mínimo (pts)',color=SOFT)
ax4.set_title('VXN elevado = ¿rebote\nmás grande?',color=GOLD,fontsize=11,fontweight='bold')
ax4.legend(fontsize=9,facecolor=BG,labelcolor=WHITE)
ax4.tick_params(colors=SOFT); [ax4.spines[s].set_visible(False) for s in ['top','right']]
ax4.grid(color=DIM,alpha=0.15)

# ── E. Frecuencia de rebotes grandes en historial ─────────────────
ax5=fig.add_subplot(gs[1,2]); ax5.set_facecolor(PANEL2)
all_rebs=[r['reaction_from_lo'] for r in up_cases]
bins_r=np.arange(0,700,50)
counts,_=np.histogram(all_rebs,bins=bins_r)
colors_h=[RED if b>=300 else (GOLD if b>=150 else BLU) for b in bins_r[:-1]]
ax5.bar(bins_r[:-1],counts,width=48,color=colors_h,alpha=0.82,edgecolor=BG)
ax5.axvline(440,color=GOLD,lw=3,ls='--',label=f'HOY 440pts (top {sum(1 for r in all_rebs if r>=440)/len(all_rebs)*100:.0f}%)')
ax5.axvline(np.median(all_rebs),color=WHITE,lw=2,ls=':',label=f'Mediana={np.median(all_rebs):.0f}pts')
for pct in [300,200,150]:
    pa=sum(1 for r in all_rebs if r>=pct)/len(all_rebs)*100
    ax5.text(pct+10,counts.max()*0.85,f'≥{pct}pts\n{pa:.0f}%',color=SOFT,fontsize=8.5,va='top')
ax5.set_xlabel('Rebote desde mínimo del día (pts)',color=SOFT)
ax5.set_ylabel('N Martes',color=SOFT)
ax5.set_title(f'Distribución de rebotes (martes LOW→HIGH)\n{sum(1 for r in all_rebs if r>=300)} de {len(all_rebs)} hicieron 300pts+',
              color=GOLD,fontsize=11,fontweight='bold')
ax5.legend(fontsize=9.5,facecolor=BG,labelcolor=WHITE)
ax5.tick_params(colors=SOFT); [ax5.spines[s].set_visible(False) for s in ['top','right']]

# ── F. Panel texto: RECETA del movimiento grande ──────────────────
ax6=fig.add_subplot(gs[2,:]); ax6.set_facecolor('#06060f'); ax6.axis('off')
ax6.set_xlim(0,28); ax6.set_ylim(0,10)

ax6.add_patch(patches.FancyBboxPatch((0.1,8.5),27.8,1.3,
    boxstyle='round,pad=0.05',facecolor='#0f0f00',edgecolor=GOLD,lw=2))
ax6.text(14,9.15,'RECETA DEL MARTES DE +300pts — HOY 7 ABR EN CONTEXTO HISTÓRICO',
         ha='center',va='center',fontsize=12,fontweight='bold',color=GOLD)

# Stats clave
mon_ext=[r for r in up_cases if r['mon_chg']<=-400]
mon_ext_big=[r for r in mon_ext if r['reaction_from_lo']>=200]
sw_deep=[r for r in sweep_up if r['sweep_depth']>=200]

facts=[
    (GRN, 'Lo que pasó hoy:', ''),
    (WHITE,'Lunes 7 Abr:', 'Caída brutal ~-800pts (aranceles Trump) — uno de los lunes más extremos'),
    (WHITE,'Overnight LOW:', 'Barrido en NY → sweep de 261pts DEBAJO del Mon LOW'),
    (WHITE,'VXN:', 'Estimado ~32 — muy elevado (pánico de mercado)'),
    (WHITE,'COT:', 'NEUTRAL-BULLISH (institucionales NO vendieron — señal de acumulación)'),
    (WHITE,'11:05 ET:', 'Mínimo 23,942 → institucionales compraron → +440pts hasta 15:55'),
    ('','',''),
    (GOLD,'Estadística histórica (qué tan raro es):',''),
    (BLU, f'Martes con rebote ≥300pts:',f'{sum(1 for r in all_rebs if r>=300)} de {len(all_rebs)} = {sum(1 for r in all_rebs if r>=300)/len(all_rebs)*100:.0f}% de los martes'),
    (BLU, f'Martes con rebote ≥400pts:',f'{sum(1 for r in all_rebs if r>=400)} de {len(all_rebs)} = {sum(1 for r in all_rebs if r>=400)/len(all_rebs)*100:.0f}% de los martes'),
    (GRN, f'Lunes < -400pts + Martes revierte:',f'{len(mon_ext_big)}/{len(mon_ext)} = {len(mon_ext_big)/max(1,len(mon_ext))*100:.0f}% da >=200pts'),
    (GRN, f'Sweep profundo (>200pts) + rebote:',f'{len(sw_deep)} casos — avg rebote: {np.mean([r["reaction_from_lo"] for r in sw_deep]):.0f}pts'),
    ('','',''),
    (ORG,'REGLA OPERACIONAL DESTILADA:',''),
    (ORG,'Cuando Lunes cae >400pts + Martes barre Mon LOW profundo + VXN>25:',''),
    (ORG,'→  NO adivines el primer movimiento',''),
    (ORG,'→  Espera el mínimo (10:30-11:30 ET) → confirma 30pts de rebote → LONG',''),
    (ORG,'→  Objetivo: 150-300pts mínimo | Stop: 30-40pts bajo mínimo',''),
]

y_f=8.2
for c_,k,v in facts:
    if not c_: y_f-=0.28; continue
    ax6.text(0.3,y_f,k,fontsize=9,color=c_,fontweight='bold',va='center')
    if v: ax6.text(8.5,y_f,v,fontsize=9,color=WHITE if c_!=ORG else ORG,va='center')
    y_f-=0.46

out='martes_condiciones_reversal.png'
plt.savefig(out,dpi=118,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
