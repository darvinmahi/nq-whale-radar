"""
martes_asia_profile.py
ANÁLISIS 195 MARTES — Con Volume Profile de Asia (6PM→9:20AM ET)
Filtros combinados:
  1. Posición del precio vs POC de Asia al abrir NY
  2. Combo velas (RRR/VVV/etc)
  3. V1 fuerza
Objetivo: descubrir cuánto mejora el WR con el profile de Asia
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict
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
by_date_bars = defaultdict(list)  # bars por fecha ET

with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            d_raw = raw.date()
            # Ajuste horario UTC → ET
            off = 4 if (date(2019,3,10)<=d_raw<date(2019,11,3) or
                        date(2020,3,8)<=d_raw<date(2020,11,1) or
                        date(2021,3,14)<=d_raw<date(2021,11,7) or
                        date(2022,3,13)<=d_raw<date(2022,11,6) or
                        date(2023,3,12)<=d_raw<date(2023,11,5) or
                        date(2024,3,10)<=d_raw<date(2024,11,3) or
                        date(2025,3,9)<=d_raw<date(2025,11,2) or
                        date(2026,3,8)<=d_raw) else 5
            et = raw - timedelta(hours=off)
            by_date_bars[et.date()].append({
                'et':et, 'o':float(r['Open']), 'h':float(r['High']),
                'l':float(r['Low']), 'c':float(r['Close']),
                'v':abs(float(r.get('Volume',0) or 0))
            })
        except: pass

# ── FUNCIÓN: Volume Profile aproximado (TPO con volumen) ──────────────
def calc_profile(bars, tick_size=5.0):
    """
    Calcula POC, VAH, VAL usando volumen por rango de precio.
    Divide cada barra en price buckets y asigna volumen proporcionalmente.
    """
    if not bars: return None, None, None, None, None

    lo_all = min(b['l'] for b in bars)
    hi_all = max(b['h'] for b in bars)
    if hi_all <= lo_all: return None, None, None, None, None

    # Precio mínimo redondeado al tick
    lo_floor = (lo_all // tick_size) * tick_size
    hi_ceil  = (hi_all // tick_size + 1) * tick_size

    n_ticks = int((hi_ceil - lo_floor) / tick_size)
    if n_ticks < 1: return None, None, None, None, None

    vol_profile = np.zeros(n_ticks)

    for b in bars:
        rng = b['h'] - b['l']
        if rng <= 0: continue
        # Ticks que toca esta barra
        lo_idx = int((b['l'] - lo_floor) / tick_size)
        hi_idx = int((b['h'] - lo_floor) / tick_size)
        lo_idx = max(0, lo_idx)
        hi_idx = min(n_ticks-1, hi_idx)
        n_touched = hi_idx - lo_idx + 1
        vol_per_tick = b['v'] / n_touched if n_touched > 0 else 0
        vol_profile[lo_idx:hi_idx+1] += vol_per_tick

    total_vol = vol_profile.sum()
    if total_vol == 0: return None, None, None, None, None

    # POC = tick con más volumen
    poc_idx  = np.argmax(vol_profile)
    poc_price= lo_floor + poc_idx * tick_size

    # Value Area = 70% del volumen total, expandiendo desde POC
    va_target = total_vol * 0.70
    va_vol = vol_profile[poc_idx]
    lo_va = poc_idx; hi_va = poc_idx

    while va_vol < va_target:
        expand_lo = lo_va > 0
        expand_hi = hi_va < n_ticks - 1
        if not expand_lo and not expand_hi: break
        add_lo = vol_profile[lo_va-1] if expand_lo else -1
        add_hi = vol_profile[hi_va+1] if expand_hi else -1
        if add_lo >= add_hi and expand_lo:
            lo_va -= 1; va_vol += vol_profile[lo_va]
        elif expand_hi:
            hi_va += 1; va_vol += vol_profile[hi_va]
        else:
            lo_va -= 1; va_vol += vol_profile[lo_va]

    val = lo_floor + lo_va * tick_size
    vah = lo_floor + hi_va * tick_size

    return poc_price, val, vah, lo_all, hi_all

# ── PROCESAR MARTES ───────────────────────────────────────────────────
records = []

all_dates = sorted(by_date_bars.keys())

for d in all_dates:
    if d.weekday() != 1: continue  # Solo martes

    # === ASIA PROFILE: 6PM ET lunes → 9:20 AM ET martes ===
    mon = d - timedelta(days=1)

    # Barra de lunes tarde (18:00 ET en adelante)
    asia_bars = []
    for b in by_date_bars.get(mon, []):
        if b['et'].hour >= 18:
            asia_bars.append(b)

    # Barras de madrugada del martes (0:00 → 9:20 ET)
    for b in by_date_bars.get(d, []):
        if b['et'].hour < 9 or (b['et'].hour == 9 and b['et'].minute < 20):
            asia_bars.append(b)

    # También incluir barras 4-9:20 (London/pre-market)
    # ya están incluidas arriba

    if len(asia_bars) < 4: continue

    poc, val, vah, asia_lo, asia_hi = calc_profile(asia_bars)
    if poc is None: continue

    # === NY SESSION: 9:30-16:00 ET ===
    ny_bars = sorted(
        [b for b in by_date_bars.get(d, [])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )
    if len(ny_bars) < 6: continue

    # Lunes NY para sweep levels
    mon_ny = sorted(
        [b for b in by_date_bars.get(mon, [])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )
    if len(mon_ny) < 4: continue

    mon_lo = min(b['l'] for b in mon_ny)
    mon_hi = max(b['h'] for b in mon_ny)
    mon_chg= round(mon_ny[-1]['c'] - mon_ny[0]['o'], 1)
    pct_m  = mon_chg / mon_ny[0]['o'] * 100
    mon_type=('BULL_STRONG' if pct_m>=0.8 else 'BULL' if pct_m>=0.3
              else 'FLAT' if pct_m>=-0.3 else 'BEAR' if pct_m>=-0.8 else 'BEAR_STRONG')

    # Posición del precio en NY vs POC de Asia
    ny_open = ny_bars[0]['o']
    above_poc = ny_open > poc + 5   # precio abre SOBRE el POC
    below_poc = ny_open < poc - 5   # precio abre BAJO el POC
    at_poc    = not above_poc and not below_poc

    above_vah = ny_open > vah + 5   # abre sobre el VAH (premium extremo)
    below_val = ny_open < val - 5   # abre bajo el VAL (discount extremo)

    # Distancia al POC
    dist_poc = round(ny_open - poc, 1)

    # ¿Retornó al POC durante NY?
    poc_tol = 8  # puntos de tolerancia
    returned_poc = any(abs(b['c'] - poc) < poc_tol or abs(b['o'] - poc) < poc_tol
                       for b in ny_bars)

    # === VELAS APERTURA ===
    def get_v(h, m):
        return next((b for b in ny_bars if b['et'].hour==h and b['et'].minute==m), None)

    v1=get_v(9,30); v2=get_v(9,45); v3=get_v(10,0)

    def vchar(v):
        if v is None: return None
        body=abs(v['c']-v['o']); rng=v['h']-v['l'] or 1
        return {
            'bull':v['c']>v['o'], 'body':round(body,1), 'rng':round(rng,1),
            'str': 'FUERTE' if body>rng*0.6 else ('DEBIL' if body<rng*0.3 else 'MEDIA')
        }

    vc1=vchar(v1); vc2=vchar(v2); vc3=vchar(v3)
    if not vc1 or not vc2: continue

    combo3 = (('V' if vc1['bull'] else 'R') + '+' +
              ('V' if vc2['bull'] else 'R') + '+' +
              (('V' if vc3['bull'] else 'R') if vc3 else '?'))

    # Resultado del día
    tue_chg  = round(ny_bars[-1]['c'] - ny_open, 1)
    tue_bull = tue_chg > 0
    tue_rng  = round(max(b['h'] for b in ny_bars) - min(b['l'] for b in ny_bars), 1)

    # Sigue v1?
    follow_v1 = vc1['bull'] == tue_bull

    # ¿La vela V1 va en dirección del sesgo de Asia (arriba/abajo del POC)?
    asia_bias_bull = above_poc  # si abre sobre POC → sesgo alcista de Asia
    v1_vs_asia_match = (vc1['bull'] == asia_bias_bull) if not at_poc else None

    # Sweeps
    swept_lo = any(b['l'] <= mon_lo+8 for b in ny_bars)
    swept_hi = any(b['h'] >= mon_hi-8 for b in ny_bars)

    records.append({
        'd':d,'mon_type':mon_type,'mon_chg':mon_chg,
        'mon_lo':mon_lo,'mon_hi':mon_hi,
        'poc':poc,'val':val,'vah':vah,'asia_lo':asia_lo,'asia_hi':asia_hi,
        'ny_open':ny_open,'dist_poc':dist_poc,
        'above_poc':above_poc,'below_poc':below_poc,'at_poc':at_poc,
        'above_vah':above_vah,'below_val':below_val,
        'returned_poc':returned_poc,
        'vc1':vc1,'vc2':vc2,'vc3':vc3,'combo3':combo3,
        'tue_bull':tue_bull,'tue_chg':tue_chg,'tue_rng':tue_rng,
        'follow_v1':follow_v1,
        'v1_vs_asia_match':v1_vs_asia_match,
        'asia_bias_bull':asia_bias_bull,
        'swept_lo':swept_lo,'swept_hi':swept_hi,
    })

N=len(records)
print(f"Martes procesados con Asia Profile: {N}")

# ═══════════════════════════════════════════════════════════════════════
# ANÁLISIS
# ═══════════════════════════════════════════════════════════════════════
g_above=[r for r in records if r['above_poc']]
g_below=[r for r in records if r['below_poc']]
g_at   =[r for r in records if r['at_poc']]

print(f"\n{'='*65}")
print(f"POSICIÓN vs POC ASIA → Resultado del día:")
print(f"{'='*65}")
for grp,lbl in[(g_above,'Abre SOBRE POC (above)'),(g_below,'Abre BAJO POC (below)'),(g_at,'Abre EN POC (at)')]:
    if not grp: continue
    n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    ret_poc=sum(1 for r in grp if r['returned_poc'])
    print(f"  {lbl:<28} n={n_:>3}: día sube={up_/n_*100:.0f}%  avg={avg_:+.0f}pts  ret.POC={ret_poc/n_*100:.0f}%")

print(f"\n{'='*65}")
print(f"COMBO3 + POSICIÓN ASIA → WR COMBINADO")
print(f"{'='*65}")
print(f"  {'Combo':<12} {'Asia pos':<14} {'n':>4} {'Dia Sube':>10} {'Avg Chg':>10}")

key_combos=['V+V+V','R+R+R','V+V+R','R+R+V']
asia_labels=[('above_poc','SOBRE POC'),('below_poc','BAJO POC')]

for combo in key_combos:
    for asia_key, asia_lbl in asia_labels:
        grp=[r for r in records if r['combo3']==combo and r[asia_key]]
        if len(grp)<2: continue
        n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
        avg_=sum(r['tue_chg'] for r in grp)/n_
        print(f"  {combo:<12} {asia_lbl:<14} {n_:>4} {up_/n_*100:>9.0f}%  {avg_:>+9.0f}")

print(f"\n{'='*65}")
print(f"V1 CON SESGO ASIA → WR mejorado?")
print(f"{'='*65}")
# V1 va en misma dirección que el sesgo de Asia
g_match    =[r for r in records if r['v1_vs_asia_match']==True]
g_mismatch =[r for r in records if r['v1_vs_asia_match']==False]
g_at_poc   =[r for r in records if r['v1_vs_asia_match'] is None]
for grp,lbl in[(g_match,'V1 CONFIRMA sesgo Asia'),
               (g_mismatch,'V1 CONTRA sesgo Asia'),
               (g_at_poc,'Abre EN POC (sin sesgo)')]:
    if not grp: continue
    n_=len(grp); up_=sum(1 for r in grp if r['follow_v1'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    print(f"  {lbl:<35} n={n_:>3}: sigue v1={up_/n_*100:.0f}%  avg={avg_:+.0f}pts")

print(f"\n{'='*65}")
print(f"RETORNO AL POC (¿cuántos vuelven?)")
print(f"{'='*65}")
ret_all=sum(1 for r in records if r['returned_poc'])
print(f"  Todos los Martes: {ret_all}/{N} = {ret_all/N*100:.0f}%")
for grp,lbl in[(g_above,'Sobre POC'),(g_below,'Bajo POC')]:
    if not grp: continue
    ret=sum(1 for r in grp if r['returned_poc'])
    print(f"  {lbl}: {ret}/{len(grp)} = {ret/len(grp)*100:.0f}%")

print(f"\n{'='*65}")
print(f"SETUP IDEAL: Combo + Asia + V1 alineados")
print(f"{'='*65}")
# VVV + sobre POC + v1 fuerte
best_long=[r for r in records
           if r['combo3']=='V+V+V' and r['above_poc'] and r['vc1']['str']=='FUERTE']
best_short=[r for r in records
            if r['combo3']=='R+R+R' and r['below_poc'] and r['vc1']['str']=='FUERTE']
for grp,lbl in[(best_long,'VVV + SOBRE POC + V1 FUERTE = LONG'),(best_short,'RRR + BAJO POC + V1 FUERTE = SHORT')]:
    if not grp:
        print(f"  {lbl}: insuficientes casos"); continue
    n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    print(f"  {lbl}: n={n_}  WR={up_/n_*100:.0f}%  avg={avg_:+.0f}pts")

# ═══════════════════════════════════════════════════════════════════════
# FIGURA
# ═══════════════════════════════════════════════════════════════════════
fig=plt.figure(figsize=(28,18),facecolor=BG)
fig.suptitle(
    f"MARTES NQ — Volume Profile ASIA (6PM→9:20AM ET) + Combo Apertura | n={N} casos (2017-2026)",
    color=GOLD,fontsize=14,fontweight='bold',y=0.998
)
gs=gridspec.GridSpec(2,4,figure=fig,hspace=0.42,wspace=0.30,
                     left=0.04,right=0.98,top=0.96,bottom=0.05)

# 1. Posición vs POC → día
ax1=fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
cats=['SOBRE\nPOC','BAJO\nPOC','EN POC\n(±5pts)']
grps_pos=[g_above,g_below,g_at]
vals_pos=[sum(1 for r in g if r['tue_bull'])/max(1,len(g))*100 for g in grps_pos]
ns_pos=[len(g) for g in grps_pos]
clrs_pos=[GRN,RED,GOLD]
bars1=ax1.bar(range(3),vals_pos,color=clrs_pos,alpha=0.85,width=0.6)
ax1.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,v,n_ in zip(bars1,vals_pos,ns_pos):
    ax1.text(b.get_x()+b.get_width()/2,v+2,f'{v:.0f}%',ha='center',fontsize=15,color='white',fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2,8,f'n={n_}',ha='center',fontsize=10.5,color=SOFT)
ax1.set_xticks(range(3)); ax1.set_xticklabels(cats,fontsize=11,color=SOFT)
ax1.set_ylim(0,100); ax1.set_ylabel('% Día Sube',color=SOFT)
ax1.set_title('NY abre SOBRE/BAJO POC Asia\n→ ¿Sube el día?',color=GOLD,fontsize=11,fontweight='bold')
ax1.tick_params(colors=SOFT); [ax1.spines[s].set_visible(False) for s in ['top','right']]

# 2. Retorno al POC
ax2=fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
labels_ret=['Todos\nMartes','Abre\nSobre POC','Abre\nBajo POC']
grps_ret=[records,g_above,g_below]
ret_vals=[sum(1 for r in g if r['returned_poc'])/max(1,len(g))*100 for g in grps_ret]
ns_ret=[len(g) for g in grps_ret]
bars2=ax2.bar(range(3),ret_vals,color=[BLU,GRN,RED],alpha=0.85,width=0.6)
for b,v,n_ in zip(bars2,ret_vals,ns_ret):
    ax2.text(b.get_x()+b.get_width()/2,v+2,f'{v:.0f}%',ha='center',fontsize=15,color='white',fontweight='bold')
    ax2.text(b.get_x()+b.get_width()/2,8,f'n={n_}',ha='center',fontsize=10.5,color=SOFT)
ax2.set_xticks(range(3)); ax2.set_xticklabels(labels_ret,fontsize=11,color=SOFT)
ax2.set_ylim(0,100); ax2.set_ylabel('% Retorna al POC',color=SOFT)
ax2.set_title('¿Cuántos MARTES\nregresan al POC de Asia?',color=GOLD,fontsize=11,fontweight='bold')
ax2.tick_params(colors=SOFT); [ax2.spines[s].set_visible(False) for s in ['top','right']]

# 3. Combo3 + Asia combinado — tabla visual
ax3=fig.add_subplot(gs[0,2:4]); ax3.set_facecolor(PANEL2)
ax3.axis('off')
ax3.set_xlim(0,20); ax3.set_ylim(0,12)
ax3.text(10,11.5,'COMBO 3 VELAS + POSICIÓN ASIA → WR COMBINADO',
         ha='center',fontsize=13,fontweight='bold',color=GOLD)

# Headers
headers=['Combo','Asia Pos','N','Día Sube%','Avg Chg','Señal']
col_x=[0.3,3.5,7.5,9.5,12.5,15.5]
for cx,h in zip(col_x,headers):
    ax3.text(cx,10.7,h,fontsize=10,color=SOFT,fontweight='bold')
ax3.axhline(10.4,color=DIM,lw=0.8,xmin=0.01,xmax=0.99)

row_i=0
combo_asia_rows=[]
for combo in['V+V+V','V+V+R','R+V+V','V+R+V','R+R+V','R+V+R','V+R+R','R+R+R']:
    for asia_key,asia_lbl in[('above_poc','▲ SOBRE POC'),('below_poc','▼ BAJO POC')]:
        grp=[r for r in records if r['combo3']==combo and r[asia_key]]
        if len(grp)<3: continue
        n_=len(grp); up_=sum(1 for r in grp if r['tue_bull']); avg_=sum(r['tue_chg'] for r in grp)/n_
        combo_asia_rows.append((combo,asia_lbl,n_,up_/n_*100,avg_))

# Ordenar por WR más extremo
combo_asia_rows.sort(key=lambda x:abs(x[3]-50),reverse=True)

for row_i,(c,al,n_,wr,avg) in enumerate(combo_asia_rows[:8]):
    y=9.8-row_i*1.1
    clr=GRN if wr>=65 else (RED if wr<=40 else GOLD)
    signal='▲ LONG' if wr>=65 else ('▼ SHORT' if wr<=40 else '─ WAIT')
    s_clr=GRN if wr>=65 else (RED if wr<=40 else SOFT)
    ax3.text(col_x[0],y,c,fontsize=10,color=clr,fontweight='bold',va='center')
    ax3.text(col_x[1],y,al,fontsize=9.5,color=SOFT,va='center')
    ax3.text(col_x[2],y,str(n_),fontsize=10,color=WHITE,va='center')
    ax3.text(col_x[3],y,f'{wr:.0f}%',fontsize=11,color=clr,fontweight='bold',va='center')
    ax3.text(col_x[4],y,f'{avg:+.0f}pts',fontsize=10,color=clr,va='center')
    ax3.text(col_x[5],y,signal,fontsize=11,color=s_clr,fontweight='bold',va='center')
    if row_i<7:
        ax3.axhline(y-0.5,color=DIM,lw=0.4,xmin=0.01,xmax=0.99,alpha=0.5)

# 4. V1 + Asia sesgo
ax4=fig.add_subplot(gs[1,0]); ax4.set_facecolor(PANEL2)
cats4=['V1 CONFIRMA\nsesgo Asia','V1 CONTRA\nsesgo Asia','En POC\nsin sesgo']
grps4=[g_match,g_mismatch,g_at_poc]
vals4=[sum(1 for r in g if r['follow_v1'])/max(1,len(g))*100 for g in grps4]
ns4=[len(g) for g in grps4]
clrs4=[GRN,RED,GOLD]
bars4=ax4.bar(range(3),vals4,color=clrs4,alpha=0.85,width=0.6)
ax4.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,v,n_ in zip(bars4,vals4,ns4):
    ax4.text(b.get_x()+b.get_width()/2,v+2,f'{v:.0f}%',ha='center',fontsize=14,color='white',fontweight='bold')
    ax4.text(b.get_x()+b.get_width()/2,8,f'n={n_}',ha='center',fontsize=10,color=SOFT)
ax4.set_xticks(range(3)); ax4.set_xticklabels(cats4,fontsize=9.5,color=SOFT)
ax4.set_ylim(0,100); ax4.set_ylabel('% día sigue V1',color=SOFT)
ax4.set_title('V1 alineada con sesgo POC\n→ ¿Mejora el WR de seguir V1?',color=GOLD,fontsize=11,fontweight='bold')
ax4.tick_params(colors=SOFT); [ax4.spines[s].set_visible(False) for s in ['top','right']]

# 5. Distribución distancia al POC
ax5=fig.add_subplot(gs[1,1]); ax5.set_facecolor(PANEL2)
dists=[r['dist_poc'] for r in records]
bins_d=np.arange(-200,201,20)
ax5.hist(dists,bins=bins_d,color=BLU,alpha=0.8,edgecolor='none')
ax5.axvline(0,color=GOLD,lw=2,ls='--',label='POC')
ax5.axvline(np.mean(dists),color=GRN,lw=1.5,ls=':',label=f'Media: {np.mean(dists):+.0f}pts')
ax5.set_xlabel('Distancia NY Open vs POC Asia (pts)',color=SOFT)
ax5.set_ylabel('N Martes',color=SOFT)
ax5.set_title('¿Cuánto lejos del POC de Asia\nabre NY?',color=GOLD,fontsize=11,fontweight='bold')
ax5.legend(fontsize=9.5,facecolor=BG,labelcolor=SOFT)
ax5.tick_params(colors=SOFT); [ax5.spines[s].set_visible(False) for s in ['top','right']]

# 6. Setup ideal + Card reglas
ax6=fig.add_subplot(gs[1,2:4]); ax6.set_facecolor('#07070f'); ax6.axis('off')
ax6.set_xlim(0,20); ax6.set_ylim(0,14)

ax6.add_patch(patches.FancyBboxPatch((0.2,12.8),19.6,0.95,
    boxstyle='round,pad=0.1',facecolor='#0a1a0a',edgecolor=GOLD,linewidth=2.5))
ax6.text(10,13.3,'SETUP COMPLETO: ASIA PROFILE + COMBO + V1 → ENTRADAS DE ALTA PROBABILIDAD',
         ha='center',va='center',fontsize=11,fontweight='bold',color=GOLD)

# Calcular stats setups
bl_pct=f"{(sum(1 for r in best_long if r['tue_bull'])/max(1,len(best_long))*100):.0f}%" if best_long else 'N/A'
bs_pct=f"{(sum(1 for r in best_short if not r['tue_bull'])/max(1,len(best_short))*100):.0f}%" if best_short else 'N/A'
bl_avg=f"{sum(r['tue_chg'] for r in best_long)/max(1,len(best_long)):+.0f}pts" if best_long else 'N/A'
bs_avg=f"{sum(r['tue_chg'] for r in best_short)/max(1,len(best_short)):+.0f}pts" if best_short else 'N/A'

lines=[
    (GOLD,'bold','── PROTOCOLO MARTES NY ──','',20,False),
    (SOFT,'normal','1. Calcular POC/VAH/VAL de Asia (6PM-9:20AM ET)','',20,False),
    (SOFT,'normal','2. ¿Dónde abre el precio vs el POC?','',20,False),
    (SOFT,'normal','3. Leer las 3 primeras velas de NY (9:30, 9:45, 10:00)','',20,False),
    (SOFT,'normal','4. ¿Combo + sesgo Asia coinciden?  → ENTRAR','',20,False),
    ('','','','',20,False),
    (GRN,'bold',f'LONG IDEAL (VVV + Sobre POC + V1 Fuerte):',f'n={len(best_long)}  WR={bl_pct}  avg={bl_avg}',20,False),
    (RED,'bold',f'SHORT IDEAL (RRR + Bajo POC + V1 Fuerte):',f'n={len(best_short)}  WR={bs_pct}  avg={bs_avg}',20,False),
    ('','','','',20,False),
    (GOLD,'bold','── REGLAS CLAVE ──','',20,False),
    (GRN,'normal','✓ Price SOBRE VAH + VVV = premium extremo → LONG fuerte','',20,False),
    (RED,'normal','✓ Price BAJO VAL + RRR = discount extremo → SHORT fuerte','',20,False),
    (BLU,'normal','✓ Price entre VAL-VAH + cualquier combo → retorno al POC posible','',20,False),
    (GOLD,'normal','✦ Si V1 va CONTRA el sesgo Asia → ESPERAR confirmación V2/V3','',20,False),
    (SOFT,'normal',f'✦ Retorno al POC: {ret_all/N*100:.0f}% de los martes  |  Rango promedio: {sum(r["tue_rng"] for r in records)/N:.0f}pts','',20,False),
]

for i,(c,w,k,v,_,_) in enumerate(lines):
    if not c: continue
    y=12.2-i*0.84
    if v:
        ax6.text(0.5,y,k,fontsize=9,color=c,fontweight=w,va='center')
        ax6.text(11.5,y,v,fontsize=9.5,color=c,fontweight='bold',va='center')
    else:
        ax6.text(0.5,y,k,fontsize=9,color=c,fontweight=w,va='center')

out='martes_asia_profile.png'
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
