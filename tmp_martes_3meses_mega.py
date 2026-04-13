"""
martes_3meses_mega.py
ESTUDIO MEGA — Últimos 3 meses de MARTES
Variables integradas:
  - Asia Profile (POC/VAH/VAL) de 6PM ET lunes → 9:20 AM ET martes
  - COT signal + VXN level del día
  - Combo 5min apertura NY (9:30, 9:35, 9:40)
  - Primer movimiento, sweeps, patrón del día
  - CATEGORIZACIÓN por tipo de escenario
"""
import yfinance as yf
import pandas as pd
import json
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
ORG='#f97316'; WHITE='#f1f5f9'; TEAL='#14b8a6'; PINK='#f472b6'

# ── 1. DESCARGAR DATOS 5MIN (60 días, 24h) ────────────────────────────
print("Descargando NQ 5min (60 días, 24h)...")
tk = yf.Ticker("NQ=F")
df5 = tk.history(period="60d", interval="5m", auto_adjust=True)
df5.index = pd.to_datetime(df5.index)
try:    df5.index = df5.index.tz_convert('America/New_York')
except: df5.index = df5.index.tz_localize('UTC').tz_convert('America/New_York')

by_date = defaultdict(list)
for ts, row in df5.iterrows():
    by_date[ts.date()].append({
        'et': ts, 'o': float(row['Open']), 'h': float(row['High']),
        'l': float(row['Low']),  'c': float(row['Close']),
        'v': float(row.get('Volume', 0) or 0)
    })

print(f"  Rango: {sorted(by_date.keys())[0]} → {sorted(by_date.keys())[-1]}")

# ── 2. CARGAR COT + VXN ───────────────────────────────────────────────
print("Cargando COT + VXN...")
with open('data/research/daily_master_db.json') as f:
    db = json.load(f)
cot_by_date = {}
for rec in db.get('records', []):
    try:
        d = date.fromisoformat(rec['date'])
        cot_by_date[d] = {
            'cot_index':   float(rec.get('cot_index', 50) or 50),
            'cot_signal':  rec.get('cot_signal', 'NEUTRAL'),
            'cot_net':     float(rec.get('cot_net', 0) or 0),
            'vxn':         float(rec.get('vxn', 20) or 20),
            'vxn_level':   rec.get('vxn_level', 'NORMAL'),
            'vxn_delta':   float(rec.get('vxn_delta', 0) or 0),
        }
    except: pass

# ── 3. FUNCIÓN ASIA PROFILE ───────────────────────────────────────────
def calc_profile(bars, tick_size=5.0):
    if not bars: return None, None, None
    lo_all=min(b['l'] for b in bars); hi_all=max(b['h'] for b in bars)
    if hi_all<=lo_all: return None,None,None
    lo_floor=(lo_all//tick_size)*tick_size
    hi_ceil =(hi_all//tick_size+1)*tick_size
    n_ticks =int((hi_ceil-lo_floor)/tick_size)
    if n_ticks<1: return None,None,None
    vol=np.zeros(n_ticks)
    for b in bars:
        rng=b['h']-b['l']
        if rng<=0: continue
        lo_i=max(0,int((b['l']-lo_floor)/tick_size))
        hi_i=min(n_ticks-1,int((b['h']-lo_floor)/tick_size))
        n_t=hi_i-lo_i+1
        vpb=b['v']/n_t if n_t>0 else 0
        # Si volumen=0, usar rango como proxy
        if vpb==0: vpb=(hi_i-lo_i+1)
        vol[lo_i:hi_i+1]+=vpb
    total=vol.sum()
    if total==0: return None,None,None
    poc_i=np.argmax(vol); poc=lo_floor+poc_i*tick_size
    va_vol=vol[poc_i]; lo_va=poc_i; hi_va=poc_i
    va_target=total*0.70
    while va_vol<va_target:
        exp_lo=lo_va>0; exp_hi=hi_va<n_ticks-1
        if not exp_lo and not exp_hi: break
        add_lo=vol[lo_va-1] if exp_lo else -1
        add_hi=vol[hi_va+1] if exp_hi else -1
        if add_lo>=add_hi and exp_lo: lo_va-=1; va_vol+=vol[lo_va]
        elif exp_hi: hi_va+=1; va_vol+=vol[hi_va]
        else: lo_va-=1; va_vol+=vol[lo_va]
    return poc, lo_floor+lo_va*tick_size, lo_floor+hi_va*tick_size  # poc, val, vah

# ── 4. ANALIZAR CADA MARTES ───────────────────────────────────────────
records = []
sorted_dates = sorted(by_date.keys())

for d in sorted_dates:
    if d.weekday()!=1: continue

    mon = d - timedelta(days=1)

    # Asia profile: lunes 18:00 ET → martes 9:20 ET
    asia_bars = []
    for b in by_date.get(mon, []):
        if b['et'].hour>=18: asia_bars.append(b)
    for b in by_date.get(d, []):
        if b['et'].hour<9 or (b['et'].hour==9 and b['et'].minute<20):
            asia_bars.append(b)

    poc, val, vah = calc_profile(asia_bars)
    asia_lo = min(b['l'] for b in asia_bars) if asia_bars else None
    asia_hi = max(b['h'] for b in asia_bars) if asia_bars else None
    pre_close = asia_bars[-1]['c'] if asia_bars else None  # Último cierre antes de NY

    # NY session
    ny_bars = sorted(
        [b for b in by_date.get(d,[])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x:x['et']
    )
    if len(ny_bars)<10: continue

    # Monday NY (para sweep levels)
    mon_ny = sorted(
        [b for b in by_date.get(mon,[])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x:x['et']
    )
    mon_lo = min(b['l'] for b in mon_ny) if mon_ny else None
    mon_hi = max(b['h'] for b in mon_ny) if mon_ny else None
    mon_chg = round(mon_ny[-1]['c']-mon_ny[0]['o'],1) if len(mon_ny)>1 else 0
    pct_m = mon_chg/mon_ny[0]['o']*100 if mon_ny else 0
    mon_type=('BULL_STRONG' if pct_m>=0.8 else 'BULL' if pct_m>=0.3
              else 'FLAT' if pct_m>=-0.3 else 'BEAR' if pct_m>=-0.8 else 'BEAR_STRONG')

    # COT + VXN (buscar en el martes o viernes anterior)
    cot_data = cot_by_date.get(d) or cot_by_date.get(d-timedelta(days=1))
    cot_idx   = cot_data['cot_index']  if cot_data else 50
    cot_sig   = cot_data['cot_signal'] if cot_data else 'NEUTRAL'
    vxn_val   = cot_data['vxn']        if cot_data else 20
    vxn_lvl   = cot_data['vxn_level']  if cot_data else 'NORMAL'

    # Velas apertura 5min
    def gv(h,m): return next((b for b in ny_bars if b['et'].hour==h and b['et'].minute==m), None)
    v1=gv(9,30); v2=gv(9,35); v3=gv(9,40); v4=gv(9,45); v5=gv(9,50)

    def vc(v):
        if v is None: return None
        body=abs(v['c']-v['o']); rng=v['h']-v['l'] or 1
        return {'bull':v['c']>v['o'],'body':round(body,1),'rng':round(rng,1),
                'str':'FUERTE' if body>rng*0.6 else ('DEBIL' if body<rng*0.3 else 'MEDIA'),
                'v':float(v['v']),'bar':v}

    vc1=vc(v1); vc2=vc(v2); vc3=vc(v3)
    if not vc1: continue

    combo = ''.join('V' if vc(vx) and vc(vx)['bull'] else 'R' for vx in [v1,v2,v3] if vx)

    # NY open
    ny_open  = ny_bars[0]['o']
    ny_close = ny_bars[-1]['c']
    ny_hi    = max(b['h'] for b in ny_bars)
    ny_lo    = min(b['l'] for b in ny_bars)
    ny_chg   = round(ny_close-ny_open,1)
    ny_bull  = ny_chg>0
    ny_rng   = round(ny_hi-ny_lo,1)

    hi_bar=max(ny_bars,key=lambda x:x['h']); lo_bar=min(ny_bars,key=lambda x:x['l'])
    hi_time=hi_bar['et'].strftime('%H:%M'); lo_time=lo_bar['et'].strftime('%H:%M')

    # Posición vs POC Asia
    above_poc = poc is not None and ny_open > poc+5
    below_poc = poc is not None and ny_open < poc-5
    at_poc    = poc is not None and not above_poc and not below_poc
    above_vah = vah is not None and ny_open > vah+5
    below_val = val is not None and ny_open < val-5
    dist_poc  = round(ny_open-poc,1) if poc else None
    ret_poc   = any(abs(b['c']-poc)<10 for b in ny_bars) if poc else False

    # Sesgo Asia vs COT
    asia_bias = 'BULL' if above_poc else ('BEAR' if below_poc else 'NEUTRAL')
    cot_bull  = 'BULL' in cot_sig
    cot_bear  = 'BEAR' in cot_sig
    vxn_high  = vxn_val > 25
    vxn_extreme = vxn_val > 35

    # First move
    first_move_bull=None; first_move_pts=0
    streak=0; streak_dir=None
    for i,b in enumerate(ny_bars[:10]):
        bd=b['c']>b['o']
        if streak_dir is None or bd!=streak_dir: streak=1; streak_dir=bd
        else: streak+=1
        if streak>=2 and first_move_bull is None:
            first_move_bull=streak_dir
            s_i=max(0,i-streak+1)
            first_move_pts=round(abs(ny_bars[i]['c']-ny_bars[s_i]['o']),1)

    # Sweeps
    swept_lo = mon_lo is not None and any(b['l']<=mon_lo+8 for b in ny_bars)
    swept_hi = mon_hi is not None and any(b['h']>=mon_hi-8 for b in ny_bars)

    # Pattern
    if swept_lo and swept_hi: pat='SWEEP_BOTH'
    elif swept_lo and ny_bull: pat='SWEEP_LO_REV'
    elif swept_hi and not ny_bull: pat='SWEEP_HI_REV'
    elif ny_bull: pat='TREND_UP'
    else: pat='TREND_DOWN'

    # ── CATEGORÍA ESCENARIO ───────────────────────────────────────────
    # Combina: COT + VXN + Asia Pos + Combo
    if cot_bull and not vxn_high:
        cot_cat='📈 COT_BULL_NORMAL'
    elif cot_bull and vxn_high:
        cot_cat='⚡ COT_BULL_HIGH_VOL'
    elif cot_bear and not vxn_high:
        cot_cat='📉 COT_BEAR_NORMAL'
    elif cot_bear and vxn_high:
        cot_cat='🔥 COT_BEAR_HIGH_VOL'
    else:
        cot_cat='⚖️ COT_NEUTRAL'

    if above_vah:
        pos_cat='🔴 PREMIUM_EXTREMO'
    elif above_poc:
        pos_cat='🟡 SOBRE_POC'
    elif below_val:
        pos_cat='🟢 DISCOUNT_EXTREMO'
    elif below_poc:
        pos_cat='🟡 BAJO_POC'
    else:
        pos_cat='⚪ EN_POC'

    # Señal global
    if cot_bull and above_poc and 'VVV' in (''.join(combo)):
        signal='🚀 LONG FUERTE'
    elif cot_bull and above_poc:
        signal='📈 LONG PROBABLE'
    elif cot_bull and below_poc:
        signal='↩️ RETORNO POC'
    elif cot_bear and below_poc and 'RRR' in (''.join(combo)):
        signal='🔻 SHORT FUERTE'
    elif cot_bear and below_poc:
        signal='📉 SHORT PROBABLE'
    elif vxn_extreme:
        signal='⚠️ VOLATILIDAD'
    else:
        signal='⚖️ NEUTRAL'

    records.append({
        'd':d,'mon_type':mon_type,'mon_chg':mon_chg,
        'mon_lo':mon_lo,'mon_hi':mon_hi,
        'poc':poc,'val':val,'vah':vah,'asia_lo':asia_lo,'asia_hi':asia_hi,
        'pre_close':pre_close,'dist_poc':dist_poc,
        'above_poc':above_poc,'below_poc':below_poc,'at_poc':at_poc,
        'above_vah':above_vah,'below_val':below_val,'ret_poc':ret_poc,
        'asia_bias':asia_bias,
        'cot_idx':cot_idx,'cot_sig':cot_sig,'vxn':vxn_val,'vxn_lvl':vxn_lvl,
        'cot_bull':cot_bull,'vxn_high':vxn_high,'vxn_extreme':vxn_extreme,
        'combo':combo,'vc1':vc1,'vc2':vc2,'vc3':vc3,
        'ny_open':ny_open,'ny_close':ny_close,'ny_hi':ny_hi,'ny_lo':ny_lo,
        'ny_chg':ny_chg,'ny_bull':ny_bull,'ny_rng':ny_rng,
        'hi_time':hi_time,'lo_time':lo_time,
        'first_move_bull':first_move_bull,'first_move_pts':first_move_pts,
        'swept_lo':swept_lo,'swept_hi':swept_hi,'pat':pat,
        'cot_cat':cot_cat,'pos_cat':pos_cat,'signal':signal,
    })

N=len(records)
print(f"\nMARTES analizados (3 meses, 5min + COT + VXN + Asia): {N}")

# ── SALIDA TEXTO ──────────────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"TABLA COMPLETA DE LOS {N} MARTES (más reciente primero):")
print(f"{'='*80}")
print(f"{'Fecha':<12} {'COT':^18} {'VXN':>6} {'Asia':^12} {'Combo':^5} {'Día':>8} {'Patron':<16} {'Señal'}")
print(f"{'-'*80}")
for r in sorted(records,key=lambda x:x['d'],reverse=True):
    chg_str=f"{r['ny_chg']:+.0f}pts ({'▲' if r['ny_bull'] else '▼'})"
    poc_str=f"POC:{r['poc']:.0f}" if r['poc'] else 'no poc'
    pos_str='▲POC' if r['above_poc'] else ('▼POC' if r['below_poc'] else '=POC')
    print(f"{r['d']}  {r['cot_sig'][:16]:<18} {r['vxn']:>5.1f}  {pos_str:<5} {r['combo']:^5}  {chg_str:>10}  {r['pat']:<16}  {r['signal']}")

# Categorías
from collections import Counter
print(f"\n{'='*65}")
print("CATEGORÍAS (COT + VXN + Asia bias):")
print(f"{'='*65}")
cat_counter=Counter(r['cot_cat'] for r in records)
for cat,cnt in cat_counter.most_common():
    grp=[r for r in records if r['cot_cat']==cat]
    up=sum(1 for r in grp if r['ny_bull'])
    print(f"  {cat:<30} {cnt}x  día sube: {up}/{cnt} = {up/cnt*100:.0f}%")

print(f"\n{'='*65}")
print("LO QUE SE REPITE SIEMPRE (3 meses, 5min):")
print(f"{'='*65}")
ff1=sum(1 for r in records if r['first_move_bull']==r['vc1']['bull'] if r['vc1'])
sw_lo=sum(1 for r in records if r['swept_lo']); sw_hi=sum(1 for r in records if r['swept_hi'])
ret=sum(1 for r in records if r['ret_poc'])
rrr_d=sum(1 for r in records if r['combo']=='RRR' and not r['ny_bull'])
rrr_t=[r for r in records if r['combo']=='RRR']
vvv_u=sum(1 for r in records if r['combo']=='VVV' and r['ny_bull'])
vvv_t=[r for r in records if r['combo']=='VVV']
print(f"  1er impulso sigue V1: {ff1}/{N} = {ff1/N*100:.0f}%")
print(f"  Barre LOW lunes: {sw_lo}/{N} = {sw_lo/N*100:.0f}%")
print(f"  Barre HIGH lunes: {sw_hi}/{N} = {sw_hi/N*100:.0f}%")
print(f"  Retorna al POC Asia: {ret}/{N} = {ret/N*100:.0f}%")
if rrr_t: print(f"  RRR → día baja: {rrr_d}/{len(rrr_t)} = {rrr_d/len(rrr_t)*100:.0f}%")
if vvv_t: print(f"  VVV → día sube: {vvv_u}/{len(vvv_t)} = {vvv_u/len(vvv_t)*100:.0f}%")

# ── FIGURA MEGA ───────────────────────────────────────────────────────
fig = plt.figure(figsize=(30, 22), facecolor=BG)
fig.suptitle(
    f"MEGA ANÁLISIS MARTES — Últimos {N} Martes (5min + Asia Profile + COT + VXN)\n"
    f"Todos los estudios integrados | Buscar qué se repite SIEMPRE",
    color=GOLD, fontsize=14, fontweight='bold', y=0.998
)

# GridSpec: fila superior = tarjetas por martes, filas inferiores = stats
rows_needed = N
cols_per_row = min(N, 5)
card_rows = (N + cols_per_row - 1) // cols_per_row

gs = gridspec.GridSpec(2 + card_rows, 1, figure=fig,
                       height_ratios=[0.04] + [1]*card_rows + [1.4],
                       hspace=0.35, left=0.03, right=0.97, top=0.96, bottom=0.04)

# Título de sección tarjetas
ax_hdr = fig.add_subplot(gs[0])
ax_hdr.axis('off')
ax_hdr.text(0.5, 0.5, '▼ CADA MARTES DE LOS ÚLTIMOS 3 MESES — TODOS LOS FILTROS',
            ha='center', va='center', fontsize=12, color=GOLD, fontweight='bold',
            transform=ax_hdr.transAxes)

# ── TARJETAS POR MARTES ───────────────────────────────────────────────
recs_sorted = sorted(records, key=lambda x:x['d'])
cols = min(N, 5)

for card_row in range(card_rows):
    gs_inner = gridspec.GridSpecFromSubplotSpec(
        1, cols, subplot_spec=gs[1+card_row], wspace=0.08
    )
    for col in range(cols):
        idx = card_row * cols + col
        if idx >= N: break
        r = recs_sorted[idx]

        ax = fig.add_subplot(gs_inner[col])
        ax.set_facecolor(PANEL2 if r['ny_bull'] else '#1a0606')
        ax.axis('off')
        ax.set_xlim(0, 10); ax.set_ylim(0, 22)

        # Borde color por resultado
        border_c = GRN if r['ny_bull'] else RED
        for spine in ax.spines.values():
            spine.set_edgecolor(border_c); spine.set_linewidth(2)
        ax.set_frame_on(True)

        # Header fecha
        ax.add_patch(patches.FancyBboxPatch((0.1,20.5),9.8,1.2,
            boxstyle='round,pad=0.05',facecolor=border_c,alpha=0.25,linewidth=0))
        ax.text(5,21.1,r['d'].strftime('%d %b %Y'),ha='center',va='center',
                fontsize=10,fontweight='bold',color=WHITE)
        ax.text(5,20.6,f"{'▲ SUBE' if r['ny_bull'] else '▼ BAJA'} {r['ny_chg']:+.0f}pts  Rng:{r['ny_rng']:.0f}",
                ha='center',va='center',fontsize=8.5,color=border_c,fontweight='bold')

        # COT
        cot_c=GRN if r['cot_bull'] else RED
        ax.text(0.3,19.8,'COT:',fontsize=8.5,color=SOFT,va='center')
        ax.text(2.5,19.8,f"{r['cot_sig'][:14]}",fontsize=8,color=cot_c,fontweight='bold',va='center')
        ax.add_patch(patches.Rectangle((7.5,19.4),2.2,0.85,
                     facecolor=cot_c,alpha=0.2,linewidth=0))
        ax.text(8.6,19.8,f"{r['cot_idx']:.0f}",fontsize=9,color=cot_c,fontweight='bold',ha='center',va='center')

        # VXN
        vxn_c=RED if r['vxn_extreme'] else (GOLD if r['vxn_high'] else GRN)
        ax.text(0.3,18.9,'VXN:',fontsize=8.5,color=SOFT,va='center')
        ax.text(2.5,18.9,f"{r['vxn']:.1f}  {r['vxn_lvl'][:8]}",fontsize=8,color=vxn_c,fontweight='bold',va='center')

        # Lunes
        mon_c=GRN if r['mon_chg']>0 else RED
        ax.text(0.3,18.0,'Lunes:',fontsize=8.5,color=SOFT,va='center')
        ax.text(2.5,18.0,f"{r['mon_chg']:+.0f}pts  {r['mon_type']}",fontsize=8,color=mon_c,va='center')

        # Divisor
        ax.axhline(17.4,color=DIM,lw=0.6,xmin=0.03,xmax=0.97)

        # Asia Profile
        ax.text(5,17.1,'─ ASIA PROFILE ─',ha='center',fontsize=8,color=GOLD,fontweight='bold',va='center')
        if r['poc']:
            pos_c=GRN if r['above_poc'] else (RED if r['below_poc'] else BLU)
            ax.text(0.3,16.5,'POC:',fontsize=8,color=SOFT,va='center')
            ax.text(2,16.5,f"{r['poc']:.0f}",fontsize=8.5,color=GOLD,fontweight='bold',va='center')
            ax.text(0.3,15.8,'VAL/VAH:',fontsize=7.5,color=SOFT,va='center')
            ax.text(3,15.8,f"{r['val']:.0f}─{r['vah']:.0f}",fontsize=7.5,color=SOFT,va='center')
            pos_lbl='▲ SOBRE POC' if r['above_poc'] else ('▼ BAJO POC' if r['below_poc'] else '= EN POC')
            ax.text(5,15.15,pos_lbl,ha='center',fontsize=8.5,color=pos_c,fontweight='bold',va='center')
            if r['dist_poc'] is not None:
                ax.text(5,14.55,f"dist: {r['dist_poc']:+.0f}pts",ha='center',fontsize=8,color=SOFT,va='center')
        else:
            ax.text(5,15.8,'sin profile',ha='center',fontsize=8,color=DIM,va='center')

        ax.axhline(14.0,color=DIM,lw=0.6,xmin=0.03,xmax=0.97)

        # Apertura velas
        ax.text(5,13.6,'─ APERTURA NY ─',ha='center',fontsize=8,color=GOLD,fontweight='bold',va='center')
        combo_colors={'V':GRN,'R':RED}
        cx=1.0
        for i,ch in enumerate(r['combo']):
            cc=GRN if ch=='V' else RED
            desc='9:30' if i==0 else ('9:35' if i==1 else '9:40')
            ax.add_patch(patches.FancyBboxPatch((cx-0.3,12.6),2.0,0.75,
                boxstyle='round,pad=0.05',facecolor=cc,alpha=0.25,linewidth=0))
            ax.text(cx+0.7,13.0,f"{ch}\n{desc}",ha='center',fontsize=7.5,color=cc,fontweight='bold',va='center')
            cx+=2.8

        ax.text(5,12.1,f"Combo: {r['combo']}",ha='center',fontsize=9,color=WHITE,fontweight='bold',va='center')

        ax.axhline(11.6,color=DIM,lw=0.6,xmin=0.03,xmax=0.97)

        # Movimiento
        ax.text(5,11.2,'─ MOVIMIENTO ─',ha='center',fontsize=8,color=GOLD,fontweight='bold',va='center')
        fm_c=GRN if r['first_move_bull'] else RED
        ax.text(0.3,10.6,'1er impulso:',fontsize=7.5,color=SOFT,va='center')
        ax.text(4.5,10.6,f"{'▲' if r['first_move_bull'] else '▼'} {r['first_move_pts']:.0f}pts",fontsize=8.5,color=fm_c,fontweight='bold',va='center')
        ax.text(0.3,9.9,'Sweep LOW:',fontsize=7.5,color=SOFT,va='center')
        ax.text(4.5,9.9,'✓' if r['swept_lo'] else '✗',fontsize=9,color=RED if r['swept_lo'] else DIM,fontweight='bold',va='center')
        ax.text(0.3,9.2,'Sweep HIGH:',fontsize=7.5,color=SOFT,va='center')
        ax.text(4.5,9.2,'✓' if r['swept_hi'] else '✗',fontsize=9,color=GOLD if r['swept_hi'] else DIM,fontweight='bold',va='center')
        ax.text(0.3,8.5,'Ret. POC:',fontsize=7.5,color=SOFT,va='center')
        ax.text(4.5,8.5,'✓' if r['ret_poc'] else '✗',fontsize=9,color=BLU if r['ret_poc'] else DIM,fontweight='bold',va='center')
        ax.text(0.3,7.8,'Max:',fontsize=7.5,color=SOFT,va='center')
        ax.text(2.5,7.8,f"{r['hi_time']}",fontsize=8,color=GOLD,va='center')
        ax.text(5.5,7.8,'Min:',fontsize=7.5,color=SOFT,va='center')
        ax.text(7.0,7.8,f"{r['lo_time']}",fontsize=8,color=RED,va='center')

        ax.axhline(7.2,color=DIM,lw=0.6,xmin=0.03,xmax=0.97)

        # Patrón + Señal
        ax.text(5,6.8,r['pat'],ha='center',fontsize=8.5,color=BLU,fontweight='bold',va='center')
        sig_c=(GRN if 'LONG' in r['signal'] or 'SUBE' in r['signal']
               else (RED if 'SHORT' in r['signal'] else GOLD))
        ax.add_patch(patches.FancyBboxPatch((0.2,5.6),9.6,0.9,
            boxstyle='round,pad=0.05',facecolor=sig_c,alpha=0.15,linewidth=1,edgecolor=sig_c))
        ax.text(5,6.05,r['signal'],ha='center',fontsize=9,color=sig_c,fontweight='bold',va='center')

        # Mini spark chart (precio último día)
        ax_mini = ax.inset_axes([0.05, 0.01, 0.90, 0.23])
        ax_mini.set_facecolor('#0a0a0a')
        closes=[b['c'] for b in sorted(by_date[r['d']],key=lambda x:x['et'])
                if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)]
        if closes:
            ax_mini.plot(closes, color=border_c, lw=1.2, alpha=0.85)
            ax_mini.set_xlim(0,len(closes)-1)
            ax_mini.axis('off')
            if r['poc']:
                ax_mini.axhline(r['poc'], color=GOLD, lw=0.8, ls='--', alpha=0.7)

# ── STATS BOTTOM ───────────────────────────────────────────────────────
gs_stats = gridspec.GridSpecFromSubplotSpec(
    1, 4, subplot_spec=gs[-1], wspace=0.25
)

# Panel A: COT + VXN stats
axA = fig.add_subplot(gs_stats[0]); axA.set_facecolor(PANEL2); axA.axis('off')
axA.set_xlim(0,10); axA.set_ylim(0,18)
axA.text(5,17.2,'COT + VXN → WR',ha='center',fontsize=11,fontweight='bold',color=GOLD)
from collections import Counter
cot_cats_uniq=['📈 COT_BULL_NORMAL','⚡ COT_BULL_HIGH_VOL','📉 COT_BEAR_NORMAL','🔥 COT_BEAR_HIGH_VOL','⚖️ COT_NEUTRAL']
y=16.2
for cat in cot_cats_uniq:
    grp=[r for r in records if r['cot_cat']==cat]
    if not grp: continue
    up=sum(1 for r in grp if r['ny_bull'])
    c_=GRN if up/len(grp)>0.6 else (RED if up/len(grp)<0.4 else GOLD)
    axA.text(0.3,y,cat,fontsize=8,color=c_,fontweight='bold',va='center')
    axA.text(7.5,y,f"{up}/{len(grp)} {up/len(grp)*100:.0f}%",fontsize=8.5,color=c_,fontweight='bold',va='center')
    y-=1.4

# Panel B: Asia Pos stats
axB = fig.add_subplot(gs_stats[1]); axB.set_facecolor(PANEL2); axB.axis('off')
axB.set_xlim(0,10); axB.set_ylim(0,18)
axB.text(5,17.2,'Asia POC → WR',ha='center',fontsize=11,fontweight='bold',color=GOLD)
for grp_f,lbl,c_ in[
    (lambda r:r['above_vah'],'▲ SOBRE VAH',RED),
    (lambda r:r['above_poc'] and not r['above_vah'],'▲ Sobre POC',GOLD),
    (lambda r:r['at_poc'],'= En POC',BLU),
    (lambda r:r['below_poc'] and not r['below_val'],'▼ Bajo POC',GOLD),
    (lambda r:r['below_val'],'▼ BAJO VAL',GRN),
]:
    grp=[r for r in records if grp_f(r)]
    if not grp: continue
    up=sum(1 for r in grp if r['ny_bull'])
    axB.text(0.3,y,lbl,fontsize=9,color=c_,fontweight='bold',va='center')
    axB.text(7.0,y,f"{up}/{len(grp)} {up/len(grp)*100:.0f}%",fontsize=9,color=c_,fontweight='bold',va='center')
    y-=1.4
    
y=16.2  # reset para los parches
# Re-dibujar
for grp_f,lbl,c_c in[
    (lambda r:r['above_vah'],'▲ SOBRE VAH',RED),
    (lambda r:r['above_poc'] and not r['above_vah'],'▲ Sobre POC',GOLD),
    (lambda r:r['at_poc'],'= En POC',BLU),
    (lambda r:r['below_poc'] and not r['below_val'],'▼ Bajo POC',GOLD),
    (lambda r:r['below_val'],'▼ BAJO VAL',GRN),
]:
    grp=[r for r in records if grp_f(r)]
    if not grp: continue
    up=sum(1 for r in grp if r['ny_bull'])
    pct_=up/len(grp)*100
    bc=GRN if pct_>60 else (RED if pct_<40 else GOLD)
    axB.text(0.3,y,lbl,fontsize=9,color=bc,fontweight='bold',va='center')
    axB.text(7.0,y,f"{up}/{len(grp)}  {pct_:.0f}%",fontsize=9,color=bc,fontweight='bold',va='center')
    y-=1.35

# Panel C: Combo stats
axC = fig.add_subplot(gs_stats[2]); axC.set_facecolor(PANEL2); axC.axis('off')
axC.set_xlim(0,10); axC.set_ylim(0,18)
axC.text(5,17.2,'Combo 5min → WR',ha='center',fontsize=11,fontweight='bold',color=GOLD)
y=16.2
combo_c=Counter(r['combo'] for r in records)
for combo,cnt in combo_c.most_common():
    grp=[r for r in records if r['combo']==combo]
    up=sum(1 for r in grp if r['ny_bull'])
    pct_=up/len(grp)*100
    bc=GRN if pct_>60 else (RED if pct_<40 else GOLD)
    axC.text(0.3,y,combo,fontsize=11,color=bc,fontweight='bold',va='center')
    axC.text(2.5,y,f"→ {pct_:.0f}% sube",fontsize=9,color=bc,va='center')
    axC.text(7.5,y,f"n={cnt}",fontsize=9,color=SOFT,va='center')
    y-=1.4

# Panel D: Reglas SIEMPRE
axD = fig.add_subplot(gs_stats[3]); axD.set_facecolor('#07070f'); axD.axis('off')
axD.set_xlim(0,10); axD.set_ylim(0,18)
axD.add_patch(patches.FancyBboxPatch((0.1,16.6),9.8,1.1,
    boxstyle='round,pad=0.05',facecolor='#1a1000',edgecolor=GOLD,linewidth=2))
axD.text(5,17.2,'SIEMPRE EN MARTES',ha='center',fontsize=11,fontweight='bold',color=GOLD)

siempre_lines=[
    (GRN,f"1er impulso sigue V1: {ff1}/{N} = {ff1/N*100:.0f}%"),
    (RED,f"Barre LOW lunes: {sw_lo}/{N} = {sw_lo/N*100:.0f}%"),
    (GOLD,f"Barre HIGH lunes: {sw_hi}/{N} = {sw_hi/N*100:.0f}%"),
    (BLU,f"Retorna al POC Asia: {ret}/{N} = {ret/N*100:.0f}%"),
    (WHITE,''),
    (GOLD,'─ REGLAS CLAVE ─'),
    (GRN,"COT BULL  + Sobre POC + VVV → LONG"),
    (RED,"COT BEAR  + Bajo POC  + RRR → SHORT"),
    (BLU,"V1 débil + POC cerca  → Esperar"),
    (GOLD,"VXN>25 → Rango +50%  extra"),
    (WHITE,''),
    (SOFT,f"Rango promedio: {sum(r['ny_rng'] for r in records)/N:.0f}pts"),
    (SOFT,f"Max del día: {Counter(r['hi_time'] for r in records).most_common(1)[0][0]} ET (más frecuente)"),
    (SOFT,f"Min del día: {Counter(r['lo_time'] for r in records).most_common(1)[0][0]} ET (más frecuente)"),
]
y=16.0
for item in siempre_lines:
    c_,txt=item
    if not txt: y-=0.4; continue
    axD.text(0.4,y,txt,fontsize=8.5,color=c_,fontweight='bold' if txt.startswith('─') else 'normal',va='center')
    y-=1.05

out='martes_3meses_mega.png'
plt.savefig(out,dpi=120,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGráfica: {out}')
