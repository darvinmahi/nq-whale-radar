"""
investigar_sweep_reversal.py
1. Confirma COT de los últimos días
2. Estudia el patrón SWEEP_LO_REVERSAL en los 195 martes
3. HOY: movimiento completo (de abajo a arriba)
"""
import json, csv, yfinance as yf, pandas as pd
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

# ═════════════════════════════════════════════════════════════════════
# 1. CONFIRMAR COT
# ═════════════════════════════════════════════════════════════════════
print("="*60)
print("COT DE LOS ÚLTIMOS DÍAS:")
print("="*60)
with open('data/research/daily_master_db.json') as f:
    db = json.load(f)
records_db = db.get('records', [])
target = ['2026-04-07','2026-04-06','2026-04-04','2026-04-03','2026-03-31','2026-03-28']
cot_lookup = {}
for rec in records_db:
    d = rec['date']
    cot_lookup[d] = rec
    if d in target:
        print(f"  {d} {rec.get('dow',''):<10}"
              f"  COT_idx={rec.get('cot_index',0):>5.1f}"
              f"  COT_sig={rec.get('cot_signal','n/a'):<22}"
              f"  COT_net={rec.get('cot_net',0):>8.0f}"
              f"  VXN={rec.get('vxn',0):>5.1f}"
              f"  VXN_lvl={rec.get('vxn_level','n/a')}")

cot_hoy  = cot_lookup.get('2026-04-07', {})
cot_lun  = cot_lookup.get('2026-04-06', {})
print(f"\n  → LUNES  COT neto: {cot_lun.get('cot_net',0):.0f}  señal: {cot_lun.get('cot_signal','?')}")
print(f"  → MARTES COT neto: {cot_hoy.get('cot_net',0):.0f}  señal: {cot_hoy.get('cot_signal','?')}")
print(f"  → COT_delta hoy: {cot_hoy.get('cot_delta',0):.0f} (cambio semana)")
print()

# ═════════════════════════════════════════════════════════════════════
# 2. CARGAR CSV 15MIN → BUSCAR SWEEP_LO_REVERSAL EN 195 MARTES
# ═════════════════════════════════════════════════════════════════════
print("="*60)
print("PATRONES SWEEP_LO_REVERSAL EN 195 MARTES:")
print("="*60)
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

sweep_lo_cases = []

for d in sorted(by_date_15.keys()):
    if d.weekday() != 1: continue
    mon = d - timedelta(days=1)
    bars = ny15(d); mon_bars = ny15(mon)
    if len(bars)<8 or len(mon_bars)<4: continue

    mon_lo=min(b['l'] for b in mon_bars)
    mon_hi=max(b['h'] for b in mon_bars)
    ny_open=bars[0]['o']; ny_close=bars[-1]['c']
    ny_hi=max(b['h'] for b in bars); ny_lo=min(b['l'] for b in bars)
    ny_rng=round(ny_hi-ny_lo,1); ny_chg=round(ny_close-ny_open,1)

    # Sweep del LOW de lunes
    swept_lo = ny_lo <= mon_lo + 8
    # ¿Reversión? = precio cerró SOBRE el open del día (subió tras barrer abajo)
    reversal = swept_lo and ny_chg > 0

    # ¿Reversión COMPLETA? = precio cerró sobre el HIGH de lunes
    full_reversal = reversal and ny_close >= mon_hi - 15

    # ¿Qué porcentaje del rango total se recuperó?
    sweep_depth = round(ny_open - ny_lo, 1)   # puntos que cayó desde el open
    recovery    = round(ny_close - ny_lo, 1)  # puntos que subió desde el mínimo
    pct_rec     = round(recovery / ny_rng * 100, 1) if ny_rng > 0 else 0

    # Timing del LOW
    lo_bar = min(bars, key=lambda x:x['l'])
    hi_bar = max(bars, key=lambda x:x['h'])
    lo_hr  = lo_bar['et'].hour + lo_bar['et'].minute/60
    hi_hr  = hi_bar['et'].hour + hi_bar['et'].minute/60

    if swept_lo:
        cot_d = cot_lookup.get(str(d), {})
        sweep_lo_cases.append({
            'd':d,'mon_lo':mon_lo,'mon_hi':mon_hi,
            'ny_open':ny_open,'ny_close':ny_close,
            'ny_hi':ny_hi,'ny_lo':ny_lo,'ny_rng':ny_rng,'ny_chg':ny_chg,
            'sweepDepth':sweep_depth,'recovery':recovery,'pct_rec':pct_rec,
            'reversal':reversal,'full_reversal':full_reversal,
            'lo_time':lo_bar['et'].strftime('%H:%M'),
            'hi_time':hi_bar['et'].strftime('%H:%M'),
            'lo_hr':lo_hr,'hi_hr':hi_hr,
            'cot_sig':cot_d.get('cot_signal','?'),
            'cot_idx':cot_d.get('cot_index',50),
        })

n_sweep = len(sweep_lo_cases)
n_rev   = sum(1 for r in sweep_lo_cases if r['reversal'])
n_full  = sum(1 for r in sweep_lo_cases if r['full_reversal'])
avg_rec = sum(r['pct_rec'] for r in sweep_lo_cases)/max(1,n_sweep)
avg_depth = sum(r['sweepDepth'] for r in sweep_lo_cases)/max(1,n_sweep)

print(f"\n  Martes que barrieron LOW del lunes: {n_sweep}/195 = {n_sweep/195*100:.0f}%")
print(f"  → De esos, cerraron ARRIBA del open: {n_rev}/{n_sweep} = {n_rev/n_sweep*100:.0f}%")
print(f"  → Reversión completa (sobre Mon HIGH): {n_full}/{n_sweep} = {n_full/n_sweep*100:.0f}%")
print(f"  → Recuperación promedio del rango: {avg_rec:.0f}%")
print(f"  → Sweep promedio desde open: {avg_depth:.0f}pts")

# Timing del LOW (¿a qué hora se forma el mínimo?)
print(f"\n  TIMING DEL MÍNIMO (sweep days):")
from collections import Counter
lo_times = Counter(r['lo_time'] for r in sweep_lo_cases)
for t,c in lo_times.most_common(6):
    print(f"    {t}: {c}x = {c/n_sweep*100:.0f}%")

print(f"\n  COT cuando hubo SWEEP + REVERSAL ({n_rev} casos):")
cot_dist = Counter(r['cot_sig'][:16] for r in sweep_lo_cases if r['reversal'])
for sig,c in cot_dist.most_common():
    print(f"    {sig:<22}: {c}x = {c/n_rev*100:.0f}%")

# ═════════════════════════════════════════════════════════════════════
# 3. DATOS HOY
# ═════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("HOY MARTES 7 ABR — MOVIMIENTO COMPLETO:")
print("="*60)
tk = yf.Ticker("NQ=F")
df5 = tk.history(period="5d", interval="5m", auto_adjust=True)
df5.index = pd.to_datetime(df5.index)
try:    df5.index = df5.index.tz_convert('America/New_York')
except: df5.index = df5.index.tz_localize('UTC').tz_convert('America/New_York')
today = date(2026,4,7)
tue_ny = df5[(df5.index.date==today) &
             (((df5.index.hour==9)&(df5.index.minute>=30))|(df5.index.hour>=10)&(df5.index.hour<16))]
if not tue_ny.empty:
    ny_open=tue_ny['Open'].iloc[0]; ny_close=tue_ny['Close'].iloc[-1]
    ny_hi=tue_ny['High'].max(); ny_lo=tue_ny['Low'].min()
    lo_idx=tue_ny['Low'].idxmin(); hi_idx=tue_ny['High'].idxmax()
    print(f"  Open: {ny_open:.0f}  Close: {ny_close:.0f}  Chg: {ny_close-ny_open:+.0f}pts")
    print(f"  LOW: {ny_lo:.0f} @ {lo_idx.strftime('%H:%M')}  HIGH: {ny_hi:.0f} @ {hi_idx.strftime('%H:%M')}")
    print(f"  Rango total: {ny_hi-ny_lo:.0f}pts")
    print(f"  Sweep desde open: {ny_open-ny_lo:.0f}pts abajo")
    print(f"  Recuperación desde LOW: {ny_close-ny_lo:.0f}pts ({(ny_close-ny_lo)/(ny_hi-ny_lo)*100:.0f}% del rango)")
    lo_pos=tue_ny.index.get_loc(lo_idx); hi_pos=tue_ny.index.get_loc(hi_idx)
    print(f"  LOW antes HIGH: {'SI' if lo_pos<hi_pos else 'NO'}")
    print(f"  Ventana LOW→HIGH: ~{abs(hi_pos-lo_pos)*5}min ({lo_idx.strftime('%H:%M')} → {hi_idx.strftime('%H:%M')})")

# ═════════════════════════════════════════════════════════════════════
# 4. FIGURA: 3 paneles
# ═════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(28,18), facecolor=BG)
fig.suptitle(
    f"PATRÓN SWEEP LOW → REVERSIÓN COMPLETA NY\n"
    f"¿Qué pasa cuando el MARTES barre el LOW del lunes y luego SUBE TODO NY?",
    color=GOLD, fontsize=14, fontweight='bold', y=0.999
)
gs = gridspec.GridSpec(2,3, figure=fig, hspace=0.38, wspace=0.28,
                       left=0.05, right=0.97, top=0.96, bottom=0.05)

# ── Panel 1: Frecuencia sweep vs reversión ───────────────────────────
ax1=fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
cats=['Barrió\nLOW lunes','Reversal\n(cerró ▲)','Reversión\nCOMPLETA']
vals=[n_sweep/195*100, n_rev/n_sweep*100, n_full/n_sweep*100]
ns  =[n_sweep,n_rev,n_full]
clrs=[RED,GRN,GOLD]
bars=ax1.bar(range(3),vals,color=clrs,alpha=0.85,width=0.6)
ax1.axhline(50,color='white',lw=1.5,ls='--',alpha=0.4)
for b,v,n_ in zip(bars,vals,ns):
    ax1.text(b.get_x()+b.get_width()/2, v+2, f'{v:.0f}%',
             ha='center',fontsize=15,color='white',fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2, 8, f'n={n_}',
             ha='center',fontsize=10.5,color=SOFT)
ax1.set_xticks(range(3)); ax1.set_xticklabels(cats,fontsize=11,color=SOFT)
ax1.set_ylim(0,100); ax1.set_ylabel('% de 195 martes',color=SOFT)
ax1.set_title('Sweep LOW → ¿Cuántos revierten?\n(195 martes 2017-2026)',color=GOLD,fontsize=11,fontweight='bold')
ax1.tick_params(colors=SOFT); [ax1.spines[s].set_visible(False) for s in ['top','right']]

# ── Panel 2: Porcentaje de rango recuperado ──────────────────────────
ax2=fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
pcts=[r['pct_rec'] for r in sweep_lo_cases]
bins_p=np.arange(0,105,10)
ax2.hist(pcts,bins=bins_p,color=BLU,alpha=0.8,edgecolor=BG,linewidth=0.5)
ax2.axvline(50,color=GOLD,lw=2,ls='--',label='50% rango')
ax2.axvline(np.mean(pcts),color=GRN,lw=2,ls=':',label=f'Media {np.mean(pcts):.0f}%')
ax2.set_xlabel('% del rango total recuperado desde el LOW',color=SOFT)
ax2.set_ylabel('N Martes',color=SOFT)
ax2.set_title(f'¿Cuánto del rango recupera\nel precio tras el sweep? (n={n_sweep})',color=GOLD,fontsize=11,fontweight='bold')
ax2.legend(fontsize=10,facecolor=BG,labelcolor=SOFT)
ax2.tick_params(colors=SOFT); [ax2.spines[s].set_visible(False) for s in ['top','right']]

# Percentiles
p25=np.percentile(pcts,25);p50=np.percentile(pcts,50);p75=np.percentile(pcts,75)
ax2.text(2,ax2.get_ylim()[1]*0.88,
         f'P25={p25:.0f}%\nP50={p50:.0f}%\nP75={p75:.0f}%\nMedia={np.mean(pcts):.0f}%',
         fontsize=10,color=WHITE,va='top',
         bbox=dict(boxstyle='round',facecolor='#1a1a2e',edgecolor=GOLD,alpha=0.8))

# ── Panel 3: Timing del LOW ──────────────────────────────────────────
ax3=fig.add_subplot(gs[0,2]); ax3.set_facecolor(PANEL2)
lo_hrs=[r['lo_hr'] for r in sweep_lo_cases]
bins_t=np.arange(9.5,16.25,0.25)
ax3.hist(lo_hrs,bins=bins_t,color=RED,alpha=0.85,edgecolor=BG)
ax3.axvspan(9.5,10.0,alpha=0.15,color=GOLD,label='9:30-10:00 ET')
ax3.axvspan(10.0,11.0,alpha=0.10,color=BLU,label='Power Hour')
ax3.set_xticks(np.arange(10,16.5,0.5))
ax3.set_xticklabels([f'{int(h)}:{int((h%1)*60):02d}' for h in np.arange(10,16.5,0.5)],
                    fontsize=8.5,color=SOFT,rotation=45)
ax3.set_ylabel('N Martes con sweep',color=SOFT)
ax3.set_title(f'¿A qué hora se forma el MÍNIMO\ncuando hay sweep del LOW? (n={n_sweep})',
              color=GOLD,fontsize=11,fontweight='bold')
ax3.legend(fontsize=9.5,facecolor=BG,labelcolor=SOFT)
ax3.tick_params(colors=SOFT); [ax3.spines[s].set_visible(False) for s in ['top','right']]

lo_before_10=sum(1 for h in lo_hrs if h<10)
lo_1011=sum(1 for h in lo_hrs if 10<=h<11)
lo_after11=sum(1 for h in lo_hrs if h>=11)
ax3.text(11.5,ax3.get_ylim()[1]*0.80,
         f'Antes 10ET: {lo_before_10} ({lo_before_10/n_sweep*100:.0f}%)\n'
         f'10-11ET: {lo_1011} ({lo_1011/n_sweep*100:.0f}%)\n'
         f'11ET+: {lo_after11} ({lo_after11/n_sweep*100:.0f}%)',
         fontsize=10.5,color=WHITE,va='top',
         bbox=dict(boxstyle='round',facecolor='#1a1a2e',edgecolor=RED,alpha=0.85))

# ── Panel 4: HOY — Gráfica de velas (panel grande) ──────────────────
ax4=fig.add_subplot(gs[1,:2]); ax4.set_facecolor(PANEL)

if not tue_ny.empty:
    opens2=tue_ny['Open'].values; highs2=tue_ny['High'].values
    lows2=tue_ny['Low'].values; closes2=tue_ny['Close'].values
    vols2=tue_ny['Volume'].values
    times2=[ts.strftime('%H:%M') for ts in tue_ny.index]
    n2=len(times2)

    for i in range(n2):
        o,h,l,c=opens2[i],highs2[i],lows2[i],closes2[i]
        color=GRN if c>=o else RED
        ax4.plot([i,i],[l,h],color=color,lw=0.8,alpha=0.85,zorder=2)
        ax4.add_patch(patches.Rectangle(
            (i-0.4,min(o,c)),0.8,abs(c-o),
            facecolor=color,edgecolor=color,lw=0,alpha=0.9,zorder=3))

    # Asia levels
    poc_val=24215; val_val=24165; vah_val=24310
    ax4.axhline(poc_val,color=GOLD,lw=1.5,ls='--',alpha=0.8)
    ax4.axhline(val_val,color=TEAL,lw=1.0,ls=':',alpha=0.7)
    ax4.axhline(vah_val,color=RED,lw=1.0,ls=':',alpha=0.7)
    ax4.axhline(24203,color=RED,lw=1.3,ls=(0,(4,2)),alpha=0.6)  # Mon LOW
    ax4.axhline(24452,color=GRN,lw=1.3,ls=(0,(4,2)),alpha=0.6)  # Mon HIGH

    ax4.text(n2+0.3,poc_val,'POC 24215',color=GOLD,fontsize=8,va='center',fontweight='bold')
    ax4.text(n2+0.3,val_val,'VAL 24165',color=TEAL,fontsize=7.5,va='center')
    ax4.text(n2+0.3,vah_val,'VAH 24310',color=RED,fontsize=7.5,va='center')
    ax4.text(n2+0.3,24203,'Mon LOW 24203',color=RED,fontsize=8,va='center')
    ax4.text(n2+0.3,24452,'Mon HIGH 24452',color=GRN,fontsize=8,va='center')

    # Marcar LOW y HIGH del día
    lo_pos2=np.argmin(lows2); hi_pos2=np.argmax(highs2)
    ax4.annotate(f'MIN\n{lows2[lo_pos2]:.0f}\n{times2[lo_pos2]}',
                 xy=(lo_pos2,lows2[lo_pos2]),xytext=(lo_pos2+8,lows2[lo_pos2]-120),
                 fontsize=9.5,color=RED,fontweight='bold',ha='center',
                 arrowprops=dict(arrowstyle='->', color=RED, lw=2))
    ax4.annotate(f'MAX\n{highs2[hi_pos2]:.0f}\n{times2[hi_pos2]}',
                 xy=(hi_pos2,highs2[hi_pos2]),xytext=(hi_pos2-10,highs2[hi_pos2]+90),
                 fontsize=9.5,color=GRN,fontweight='bold',ha='center',
                 arrowprops=dict(arrowstyle='->', color=GRN, lw=2))

    # Flecha de recuperación
    if lo_pos2 < hi_pos2:
        ax4.annotate('', xy=(hi_pos2,highs2[hi_pos2]-30),
                     xytext=(lo_pos2,lows2[lo_pos2]+30),
                     arrowprops=dict(arrowstyle='->',color=GOLD,lw=3.5,
                                     connectionstyle='arc3,rad=-0.3'))
        mid=(lo_pos2+hi_pos2)//2
        move_pts=round(highs2[hi_pos2]-lows2[lo_pos2],0)
        move_min=abs(hi_pos2-lo_pos2)*5
        ax4.text(mid,lows2[lo_pos2]+200,
                 f'MOVIMIENTO COMPLETO\n{move_pts:.0f}pts en {move_min}min\n'
                 f'({times2[lo_pos2]} → {times2[hi_pos2]})',
                 ha='center',fontsize=11,color=GOLD,fontweight='bold',
                 bbox=dict(boxstyle='round',facecolor='#1a1500',edgecolor=GOLD,alpha=0.9))

    step2=max(1,n2//18)
    ax4.set_xticks(range(0,n2,step2))
    ax4.set_xticklabels([times2[i] for i in range(0,n2,step2)],fontsize=8.5,color=SOFT,rotation=30)
    ax4.set_xlim(-1,n2+12); ax4.set_ylim(lows2.min()-200,highs2.max()+250)
    ax4.tick_params(colors=SOFT)
    [ax4.spines[s].set_visible(False) for s in ['top','right']]
    ax4.grid(axis='y',color=DIM,alpha=0.2,lw=0.5)

ax4.set_title('HOY 7 ABR 2026 — SWEEP LOW → REVERSIÓN COMPLETA (el movimiento que da todo el rango del día)',
              color=GOLD,fontsize=12,fontweight='bold')

# ── Panel 5: COT + Análisis textual ─────────────────────────────────
ax5=fig.add_subplot(gs[1,2]); ax5.set_facecolor('#07070f'); ax5.axis('off')
ax5.set_xlim(0,10); ax5.set_ylim(0,24)

ax5.add_patch(patches.FancyBboxPatch((0.1,22.8),9.8,1.0,
    boxstyle='round,pad=0.05',facecolor='#0a1500',edgecolor=GOLD,linewidth=2))
ax5.text(5,23.3,'CONFIRMACIÓN COT + ANÁLISIS',ha='center',va='center',
         fontsize=11,fontweight='bold',color=GOLD)

lines_cot=[
    (GOLD,'bold','── COT SITUACIÓN ACTUAL ──',''),
    (SOFT,'normal','Señal COT hoy:',cot_hoy.get('cot_signal','?')),
    (SOFT,'normal','COT Index:',f"{cot_hoy.get('cot_index',0):.1f}/100"),
    (SOFT,'normal','COT Net pos:',f"{cot_hoy.get('cot_net',0):.0f} contratos"),
    (SOFT,'normal','COT Delta:',f"{cot_hoy.get('cot_delta',0):+.0f} (cambio semanal)"),
    (SOFT,'normal','VXN hoy:',f"{cot_hoy.get('vxn',0):.1f} ({cot_hoy.get('vxn_level','?')})"),
    ('','','',''),
    (RED,'bold','── ¿POR QUÉ EL PRECIO BAJÓ? ──',''),
    (RED,'normal','COT NEUTRAL → sin sesgo claro',''),
    (RED,'normal','Precio buscó liquidez bajo Mon LOW',''),
    (RED,'normal','Sweep = -270pts desde open',''),
    ('','','',''),
    (GRN,'bold','── ¿POR QUÉ SUBIÓ TODO? ──',''),
    (GRN,'normal','Barrió liquidity pool debajo',''),
    (GRN,'normal','COT neutrales → institucionales',''),
    (GRN,'normal','compraron en el sweep',''),
    (GRN,'normal','POC Asia = soporte magnético',''),
    ('','','',''),
    (GOLD,'bold','── ESTADÍSTICA SWEEP_LO_REV ──',''),
    (GOLD,'normal',f'Martes: {n_sweep}/195 barrean LOW',f'{n_sweep/195*100:.0f}%'),
    (GRN,'normal',f'De esos, revierten:',f'{n_rev}/{n_sweep} = {n_rev/n_sweep*100:.0f}%'),
    (BLU,'normal',f'Recuperación media del rango:',f'{avg_rec:.0f}%'),
    (GOLD,'bold','REGLA: LOW 9:30-11ET → LONG','entrada al retoque del POC'),
]

y=22.0
for item in lines_cot:
    c_,w,k,v=item
    if not c_: y-=0.4; continue
    ax5.text(0.3,y,k,fontsize=8.5,color=c_,fontweight=w,va='center')
    if v: ax5.text(5.5,y,v,fontsize=8.5,color=c_,fontweight='bold',va='center')
    y-=0.94

out='martes_sweep_reversal.png'
plt.savefig(out,dpi=125,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
