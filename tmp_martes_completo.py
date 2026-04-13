"""
estudio_martes_completo.py
195 MARTES — Estudio profundo:
 1. Tipo de LUNES (BULL / BEAR / FLAT) → qué hace el Martes
 2. 6 ESCENARIOS de apertura NY (basados en Asia Profile pre-9:20 ET)
 3. Profile Asia: ¿precio sigue la dirección pre-NY?
 4. ¿Barre el High o Low del Lunes?
 5. ¿Regresa al POC del día?
 6. Movimientos más frecuentes para actuar
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; SOFT='#94a3b8'; DIM='#475569'; ORG='#f97316'
WHITE='#f1f5f9'

def utc_off(d):
    if date(2025,3,9)<=d<date(2025,11,2) or date(2026,3,8)<=d: return 4
    return 5

# ── CARGAR DATOS ──────────────────────────────────────────────────────
by_date = defaultdict(list)
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            by_date[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close']),
                'v':float(r.get('Volume',0) or 0)
            })
        except: pass

sorted_dates = sorted(by_date.keys())
date_set = set(sorted_dates)

def get_ny(d):
    return sorted([b for b in by_date.get(d,[])
                   if (b['et'].hour==9 and b['et'].minute>=30) or
                      (10<=b['et'].hour<16)], key=lambda x:x['et'])

def get_pre_ny(d):
    """Asia + London: desde 18h del dia anterior hasta 9:20 ET del dia actual"""
    prev = d - timedelta(days=1)
    bars = [b for b in by_date.get(prev,[]) if b['et'].hour>=18]
    bars += [b for b in by_date.get(d,[])
             if b['et'].hour<9 or (b['et'].hour==9 and b['et'].minute<=20)]
    return sorted(bars, key=lambda x:x['et'])

def calc_poc(bars):
    """Point of Control simplificado (precio con más tiempo en él)"""
    if not bars: return None
    price_counter = defaultdict(float)
    for b in bars:
        mid = round((b['h']+b['l'])/2)
        price_counter[mid] += 1
    return max(price_counter, key=price_counter.get)

def vwap(bars):
    """VWAP simple de las barras dadas"""
    total_vol = sum(b['v'] for b in bars if b['v']>0)
    if total_vol == 0: return None
    return sum((b['h']+b['l']+b['c'])/3 * b['v'] for b in bars if b['v']>0) / total_vol

# ── CONSTRUIR DATASET MARTES ──────────────────────────────────────────
records = []
for d in sorted_dates:
    if d.weekday() != 1: continue  # Solo martes

    mon = d - timedelta(days=1)
    if mon not in date_set: continue

    tue_ny   = get_ny(d)
    mon_ny   = get_ny(mon)
    pre_bars = get_pre_ny(d)

    if len(tue_ny) < 8 or len(mon_ny) < 4: continue

    # ── Estadísticas del LUNES ────────────────────────────────────────
    mon_open  = mon_ny[0]['o']
    mon_close = mon_ny[-1]['c']
    mon_chg   = round(mon_close - mon_open, 1)
    mon_hi    = max(b['h'] for b in mon_ny)
    mon_lo    = min(b['l'] for b in mon_ny)
    mon_rng   = round(mon_hi - mon_lo, 1)
    mon_poc   = calc_poc(mon_ny)

    # Tipo de lunes
    pct_mon = mon_chg / mon_open * 100
    if   pct_mon >=  0.8: mon_type = 'BULL_STRONG'
    elif pct_mon >=  0.3: mon_type = 'BULL'
    elif pct_mon >= -0.3: mon_type = 'FLAT'
    elif pct_mon >= -0.8: mon_type = 'BEAR'
    else:                  mon_type = 'BEAR_STRONG'

    # ── Estadísticas pre-NY (Asia/London) ────────────────────────────
    if len(pre_bars) < 3:
        asia_hi = asia_lo = asia_poc = asia_dir = None
        asia_close = None
    else:
        asia_hi    = max(b['h'] for b in pre_bars)
        asia_lo    = min(b['l'] for b in pre_bars)
        asia_close = pre_bars[-1]['c']  # precio 10min antes del open
        asia_poc   = calc_poc(pre_bars)
        # Dirección: ¿está el precio arriba o abajo del POC de Asia?
        if asia_poc:
            asia_dir = 'ABOVE_POC' if asia_close > asia_poc else 'BELOW_POC'
        else:
            asia_dir = None

    # ── Estadísticas del MARTES NY ────────────────────────────────────
    tue_open   = tue_ny[0]['o']
    tue_close  = tue_ny[-1]['c']
    tue_chg    = round(tue_close - tue_open, 1)
    tue_hi     = max(b['h'] for b in tue_ny)
    tue_lo     = min(b['l'] for b in tue_ny)
    tue_rng    = round(tue_hi - tue_lo, 1)
    tue_poc    = calc_poc(tue_ny)
    tue_bull   = tue_chg > 0

    # Primera vela 9:30
    fc = next((b for b in tue_ny if b['et'].hour==9 and b['et'].minute==30), None)
    fc_bull = (fc['c'] > fc['o']) if fc else None
    fc_body = round(abs(fc['c']-fc['o']), 1) if fc else 0

    # ── ESCENARIO DE APERTURA (6 tipos) ──────────────────────────────
    # Basado en relación apertura NY vs rango de Asia
    if asia_hi and asia_lo:
        asia_rng = asia_hi - asia_lo
        if asia_rng < 50: asia_rng = 50  # evitar división por cero
        if   tue_open > asia_hi + 5:
            open_scenario = '1_GAP_UP'        # Abre por encima de Asia High
        elif tue_open < asia_lo - 5:
            open_scenario = '2_GAP_DOWN'      # Abre por debajo de Asia Low
        elif tue_open > (asia_hi + asia_lo)/2 + asia_rng*0.15:
            open_scenario = '3_OPEN_HIGH_VA'  # Abre en parte alta del rango Asia
        elif tue_open < (asia_hi + asia_lo)/2 - asia_rng*0.15:
            open_scenario = '4_OPEN_LOW_VA'   # Abre en parte baja del rango Asia
        else:
            open_scenario = '5_OPEN_MID_VA'   # Abre en mitad del rango Asia
    else:
        open_scenario = '6_NO_ASIA'

    # ── ¿SIGUE LA DIRECCIÓN PRE-NY? ──────────────────────────────────
    # Dirección del último movimiento pre-NY (últimas 2 barras antes del open)
    if len(pre_bars) >= 2:
        pre_move = pre_bars[-1]['c'] - pre_bars[-4]['c'] if len(pre_bars)>=4 else pre_bars[-1]['c']-pre_bars[0]['c']
        pre_dir_bull = pre_move > 0
        follows_pre  = (pre_dir_bull == tue_bull)
    else:
        pre_dir_bull = None
        follows_pre  = None

    # ── SWEEPS vs RESPETO DE RANGO LUNES ─────────────────────────────
    TOL = 5  # puntos de tolerancia
    swept_mon_lo  = tue_lo <= mon_lo + TOL
    swept_mon_hi  = tue_hi >= mon_hi - TOL
    respects_both = not swept_mon_lo and not swept_mon_hi
    sweeps_both   = swept_mon_lo and swept_mon_hi

    # ¿Cuándo barre el low/high del lunes?
    lo_sweep_hr = None; hi_sweep_hr = None
    for b in tue_ny:
        if lo_sweep_hr is None and b['l'] <= mon_lo + TOL:
            lo_sweep_hr = b['et'].hour
        if hi_sweep_hr is None and b['h'] >= mon_hi - TOL:
            hi_sweep_hr = b['et'].hour

    # ── ¿REGRESA AL POC DEL DÍA? ─────────────────────────────────────
    # ¿El precio en algún momento regresa al POC calculado?
    returns_to_poc = False
    poc_return_hr  = None
    if tue_poc:
        poc_found = False
        for b in tue_ny:
            if b['l'] <= tue_poc + 3 and b['h'] >= tue_poc - 3:
                if not poc_found:
                    poc_found = True
                else:  # Segunda visita = retorno
                    returns_to_poc = True
                    poc_return_hr  = b['et'].hour
                    break

    records.append({
        'd': d, 'mon': mon,
        'mon_type': mon_type, 'mon_chg': mon_chg, 'mon_rng': mon_rng,
        'mon_lo': mon_lo, 'mon_hi': mon_hi, 'mon_poc': mon_poc,
        'tue_chg': tue_chg, 'tue_rng': tue_rng, 'tue_bull': tue_bull,
        'tue_lo': tue_lo, 'tue_hi': tue_hi, 'tue_poc': tue_poc,
        'fc_bull': fc_bull, 'fc_body': fc_body,
        'asia_dir': asia_dir,
        'open_scenario': open_scenario,
        'follows_pre': follows_pre,
        'pre_dir_bull': pre_dir_bull,
        'swept_mon_lo': swept_mon_lo, 'swept_mon_hi': swept_mon_hi,
        'respects_both': respects_both, 'sweeps_both': sweeps_both,
        'lo_sweep_hr': lo_sweep_hr, 'hi_sweep_hr': hi_sweep_hr,
        'returns_to_poc': returns_to_poc, 'poc_return_hr': poc_return_hr,
    })

N = len(records)
print(f"Total MARTES analizados: {N}")
print()

# ═══════════════════════════════════════════════════
# A. TIPO LUNES → COMPORTAMIENTO MARTES
# ═══════════════════════════════════════════════════
print("A. TIPO DE LUNES → ¿QUÉ HACE EL MARTES?")
print(f"{'Tipo Lunes':<15} {'n':>4} {'Mar↑%':>7} {'Avg Pts':>9} {'Rng Med':>8} {'Sw Lo%':>8} {'Sw Hi%':>8} {'POC Ret%':>9}")
print("-"*75)
for mtype in ['BULL_STRONG','BULL','FLAT','BEAR','BEAR_STRONG']:
    g = [r for r in records if r['mon_type']==mtype]
    if not g: continue
    n_ = len(g)
    pct = lambda k: sum(1 for r in g if r[k])/n_*100
    avg = sum(r['tue_chg'] for r in g)/n_
    rng = sum(r['tue_rng'] for r in g)/n_
    print(f"  {mtype:<13} {n_:>4} {pct('tue_bull'):>6.0f}% {avg:>+9.0f} {rng:>8.0f} {pct('swept_mon_lo'):>7.0f}% {pct('swept_mon_hi'):>7.0f}% {pct('returns_to_poc'):>8.0f}%")

# ═══════════════════════════════════════════════════
# B. HOY LUNES 6 ABR FUE BULLISH → ¿Qué hace Martes?
# ═══════════════════════════════════════════════════
print()
print("B. LUNES BULLISH (COT BULL + Lunes Verde) → MARTES")
bull_mon = [r for r in records if r['mon_type'] in ['BULL','BULL_STRONG']]
n_b = len(bull_mon)
ups_b = sum(1 for r in bull_mon if r['tue_bull'])
avg_b = sum(r['tue_chg'] for r in bull_mon)/n_b
sw_lo_b = sum(1 for r in bull_mon if r['swept_mon_lo'])
sw_hi_b = sum(1 for r in bull_mon if r['swept_mon_hi'])
poc_b = sum(1 for r in bull_mon if r['returns_to_poc'])
print(f"  n={n_b} | Martes sube: {ups_b}/{n_b} = {ups_b/n_b*100:.0f}%")
print(f"  Avg cambio: {avg_b:+.0f}pts | Barre LOW lunes: {sw_lo_b/n_b*100:.0f}% | Barre HIGH lunes: {sw_hi_b/n_b*100:.0f}%")
print(f"  Regresa al POC: {poc_b/n_b*100:.0f}%")

# ═══════════════════════════════════════════════════
# C. 6 ESCENARIOS DE APERTURA
# ═══════════════════════════════════════════════════
print()
print("C. 6 ESCENARIOS DE APERTURA (basados en perfil Asia)")
scenarios = ['1_GAP_UP','2_GAP_DOWN','3_OPEN_HIGH_VA','4_OPEN_LOW_VA','5_OPEN_MID_VA','6_NO_ASIA']
labels_s  = {
    '1_GAP_UP':       'Gap Arriba Asia',
    '2_GAP_DOWN':     'Gap Abajo Asia',
    '3_OPEN_HIGH_VA': 'Abre en High VA',
    '4_OPEN_LOW_VA':  'Abre en Low VA',
    '5_OPEN_MID_VA':  'Abre en Mid VA',
    '6_NO_ASIA':      'Sin datos Asia',
}
print(f"{'Escenario':<20} {'n':>4} {'Sube%':>7} {'Avg Pts':>9} {'Sw Lo%':>8} {'Sw Hi%':>8} {'Sigue Pre%':>11}")
print("-"*75)
for sc in scenarios:
    g = [r for r in records if r['open_scenario']==sc]
    if not g: continue
    n_ = len(g)
    up_ = sum(1 for r in g if r['tue_bull'])
    avg_ = sum(r['tue_chg'] for r in g)/n_
    swl = sum(1 for r in g if r['swept_mon_lo'])
    swh = sum(1 for r in g if r['swept_mon_hi'])
    fol = [r for r in g if r['follows_pre'] is not None]
    fol_pct = sum(1 for r in fol if r['follows_pre'])/len(fol)*100 if fol else 0
    print(f"  {labels_s[sc]:<18} {n_:>4} {up_/n_*100:>6.0f}% {avg_:>+9.0f} {swl/n_*100:>7.0f}% {swh/n_*100:>7.0f}% {fol_pct:>10.0f}%")

# ═══════════════════════════════════════════════════
# D. DIRECCIÓN PRE-NY SEÑAL
# ═══════════════════════════════════════════════════
print()
print("D. ¿PRECIO SIGUE DIRECCIÓN PRE-NY (10min antes de las 9:30)?")
pre_bull = [r for r in records if r['pre_dir_bull'] is True]
pre_bear = [r for r in records if r['pre_dir_bull'] is False]
for grp, lbl in [(pre_bull,'Pre-NY SUBE'),(pre_bear,'Pre-NY BAJA')]:
    if not grp: continue
    n_ = len(grp)
    fol = [r for r in grp if r['follows_pre'] is True]
    up_ = sum(1 for r in grp if r['tue_bull'])
    print(f"  {lbl} (n={n_}): Martes sube {up_/n_*100:.0f}% | Sigue dirección: {len(fol)/n_*100:.0f}%")

# ═══════════════════════════════════════════════════
# E. SWEEPS: TIMING
# ═══════════════════════════════════════════════════
print()
print("E. TIMING DE SWEEPS (¿cuándo barre el High/Low del Lunes?)")
lo_hours = [r['lo_sweep_hr'] for r in records if r['swept_mon_lo'] and r['lo_sweep_hr']]
hi_hours = [r['hi_sweep_hr'] for r in records if r['swept_mon_hi'] and r['hi_sweep_hr']]
lo_c = Counter(lo_hours).most_common(5)
hi_c = Counter(hi_hours).most_common(5)
print(f"  Sweep LOW lunes  ({len(lo_hours)} casos): {[f'{h}h:{v}x' for h,v in lo_c]}")
print(f"  Sweep HIGH lunes ({len(hi_hours)} casos): {[f'{h}h:{v}x' for h,v in hi_c]}")

# ═══════════════════════════════════════════════════
# F. MOVIMIENTOS MÁS FRECUENTES (patrón del día)
# ═══════════════════════════════════════════════════
print()
print("F. PATRONES DE MOVIMIENTO MARTES (los 4 más frecuentes)")

patterns = {
    'TREND_UP':        sum(1 for r in records if r['tue_bull'] and not r['swept_mon_lo']),
    'TREND_DOWN':      sum(1 for r in records if not r['tue_bull'] and not r['swept_mon_hi']),
    'SWEEP_LO_REVERTS':sum(1 for r in records if r['swept_mon_lo'] and r['tue_bull']),
    'SWEEP_HI_REVERTS':sum(1 for r in records if r['swept_mon_hi'] and not r['tue_bull']),
    'SWEEP_BOTH':      sum(1 for r in records if r['sweeps_both']),
    'INSIDE_DAY':      sum(1 for r in records if r['respects_both']),
}

for pat,cnt in sorted(patterns.items(), key=lambda x:-x[1]):
    pct = cnt/N*100
    bar = '█'*int(pct/2)
    print(f"  {pat:<22} {cnt:>4} casos  {pct:>5.1f}%  {bar}")

print()
print("="*75)
print("HOY MARTES 7 ABR — LUNES 6 FUE BULLISH (Trump pausa aranceles)")
print("Filtro: BULL_STRONG + COT BULL")
bull_str = [r for r in records if r['mon_type']=='BULL_STRONG']
n_bs = max(1, len(bull_str))
print(f"  n={n_bs} | Martes sube: {sum(1 for r in bull_str if r['tue_bull'])/n_bs*100:.0f}%")
print(f"  Avg: {sum(r['tue_chg'] for r in bull_str)/n_bs:+.0f}pts")
print(f"  Barre LOW lunes: {sum(1 for r in bull_str if r['swept_mon_lo'])/n_bs*100:.0f}% (trampa)")
print(f"  Barre HIGH lunes: {sum(1 for r in bull_str if r['swept_mon_hi'])/n_bs*100:.0f}%")
print(f"  Regresa POC: {sum(1 for r in bull_str if r['returns_to_poc'])/n_bs*100:.0f}%")
pat_counts = Counter(r['open_scenario'] for r in bull_str)
print(f"  Escenarios apertura más comunes: {pat_counts.most_common(3)}")

# ═══════════════════════════════════════════════════
# FIGURA
# ═══════════════════════════════════════════════════
fig = plt.figure(figsize=(24,16), facecolor=BG)
fig.suptitle("ESTUDIO MARTES COMPLETO (195 casos) — 6 Escenarios + Sweep + POC + Dirección Pre-NY",
             color=GOLD, fontsize=13, fontweight='bold', y=0.99)
gs = gridspec.GridSpec(2,3, figure=fig, hspace=0.45, wspace=0.28,
                       left=0.05, right=0.97, top=0.94, bottom=0.06)

# ── 1. WR Martes por tipo Lunes ───────────────────────────────────────
ax1 = fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
types_o = ['BULL_STRONG','BULL','FLAT','BEAR','BEAR_STRONG']
types_l = ['Lun\nBULL+','Lun\nBULL','Lun\nFLAT','Lun\nBEAR','Lun\nBEAR+']
wr1=[]; n1=[]; avg1=[]
for mt in types_o:
    g=[r for r in records if r['mon_type']==mt]
    if g:
        wr1.append(sum(1 for r in g if r['tue_bull'])/len(g)*100)
        n1.append(len(g))
        avg1.append(sum(r['tue_chg'] for r in g)/len(g))
    else:
        wr1.append(0); n1.append(0); avg1.append(0)

x1=np.arange(len(types_o))
bars1=ax1.bar(x1,wr1,color=[GRN if w>=55 else (RED if w<45 else GOLD) for w in wr1],alpha=0.85,width=0.6)
ax1.axhline(50,color='white',lw=1,ls='--',alpha=0.4)
ax1.axhline(60,color=GOLD,lw=0.8,ls='--',alpha=0.3)
for b,w,n,a in zip(bars1,wr1,n1,avg1):
    ax1.text(b.get_x()+b.get_width()/2,w+1.5,f'{w:.0f}%',color='white',ha='center',fontsize=10,fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2,5 ,f'n={n}',color=SOFT,ha='center',fontsize=8)
    ax1.text(b.get_x()+b.get_width()/2,w+7,f'{a:+.0f}',color=GRN if a>0 else RED,ha='center',fontsize=8,fontweight='bold')
ax1.set_xticks(x1); ax1.set_xticklabels(types_l,fontsize=9,color=SOFT)
ax1.set_ylim(0,100); ax1.set_ylabel('Martes Sube %',color=SOFT)
ax1.set_title('WR Martes por Tipo de Lunes\n(n= / Avg pts= )',color=GOLD,fontsize=10,fontweight='bold')
ax1.tick_params(colors=SOFT)
[ax1.spines[s].set_visible(False) for s in ['top','right']]

# ── 2. 6 Escenarios apertura ───────────────────────────────────────────
ax2 = fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
sc_data=[]
for sc in ['1_GAP_UP','2_GAP_DOWN','3_OPEN_HIGH_VA','4_OPEN_LOW_VA','5_OPEN_MID_VA']:
    g=[r for r in records if r['open_scenario']==sc]
    if not g: continue
    n_=len(g)
    sc_data.append((labels_s[sc].replace(' ','\n'),
                    sum(1 for r in g if r['tue_bull'])/n_*100,
                    n_, sum(r['tue_chg'] for r in g)/n_))

x2=np.arange(len(sc_data)); lbl2=[s[0] for s in sc_data]; wr2=[s[1] for s in sc_data]
n2=[s[2] for s in sc_data]; avg2=[s[3] for s in sc_data]
bars2=ax2.bar(x2,wr2,color=[GRN if w>=55 else (RED if w<45 else GOLD) for w in wr2],alpha=0.85,width=0.6)
ax2.axhline(50,color='white',lw=1,ls='--',alpha=0.4)
for b,w,n,a in zip(bars2,wr2,n2,avg2):
    ax2.text(b.get_x()+b.get_width()/2,w+1.5,f'{w:.0f}%',color='white',ha='center',fontsize=9.5,fontweight='bold')
    ax2.text(b.get_x()+b.get_width()/2,5,f'n={n}',color=SOFT,ha='center',fontsize=7.5)
    ax2.text(b.get_x()+b.get_width()/2,w+8,f'{a:+.0f}',color=GRN if a>0 else RED,ha='center',fontsize=8,fontweight='bold')
ax2.set_xticks(x2); ax2.set_xticklabels(lbl2,fontsize=7.5,color=SOFT)
ax2.set_ylim(0,100); ax2.set_ylabel('Martes Sube %',color=SOFT)
ax2.set_title('6 Escenarios Apertura NY\nvs Perfil Asia',color=GOLD,fontsize=10,fontweight='bold')
ax2.tick_params(colors=SOFT)
[ax2.spines[s].set_visible(False) for s in ['top','right']]

# ── 3. Patrones frecuencia ─────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0,2]); ax3.set_facecolor(PANEL2)
pat_items = sorted(patterns.items(), key=lambda x:-x[1])
pat_n = [v for _,v in pat_items]
pat_l = [k.replace('_','\n') for k,_ in pat_items]
pat_c = [GRN,RED,GRN,RED,GOLD,BLU][:len(pat_items)]
ax3.barh(list(range(len(pat_l))), pat_n, color=pat_c, alpha=0.85)
ax3.set_yticks(list(range(len(pat_l)))); ax3.set_yticklabels(pat_l,fontsize=8.5,color=SOFT)
for i,v in enumerate(pat_n):
    ax3.text(v+0.5, i, f'{v} ({v/N*100:.0f}%)', va='center', fontsize=9, color=WHITE, fontweight='bold')
ax3.set_xlabel('Cantidad de Martes',color=SOFT)
ax3.set_title('Patrones de Movimiento\n(más frecuentes primero)',color=GOLD,fontsize=10,fontweight='bold')
ax3.tick_params(colors=SOFT)
[ax3.spines[s].set_visible(False) for s in ['top','right']]

# ── 4. Timing sweeps ──────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1,0]); ax4.set_facecolor(PANEL2)
all_hrs = list(range(9,16))
lo_c_all = [lo_hours.count(h) for h in all_hrs]
hi_c_all = [hi_hours.count(h) for h in all_hrs]
x4 = np.arange(len(all_hrs))
ax4.bar(x4-0.2, lo_c_all, 0.35, color=RED,  alpha=0.8, label='Sweep LOW Lunes')
ax4.bar(x4+0.2, hi_c_all, 0.35, color=GOLD, alpha=0.8, label='Sweep HIGH Lunes')
ax4.set_xticks(x4); ax4.set_xticklabels([f'{h}h' for h in all_hrs],fontsize=9,color=SOFT)
ax4.set_ylabel('Cantidad',color=SOFT); ax4.set_xlabel('Hora ET',color=SOFT)
ax4.set_title('TIMING: ¿A qué hora barre\nel rango del Lunes?',color=GOLD,fontsize=10,fontweight='bold')
ax4.legend(fontsize=9,facecolor=BG,labelcolor=SOFT)
ax4.tick_params(colors=SOFT)
[ax4.spines[s].set_visible(False) for s in ['top','right']]

# ── 5. ¿Sigue dirección Pre-NY? ───────────────────────────────────────
ax5 = fig.add_subplot(gs[1,1]); ax5.set_facecolor(PANEL2)
pre_b_up = [r for r in records if r['pre_dir_bull'] is True]
pre_b_dn = [r for r in records if r['pre_dir_bull'] is False]
grps5 = [
    ('Pre-NY\nSUBE', pre_b_up, BLU),
    ('Pre-NY\nBAJA', pre_b_dn, ORG),
]
x5 = np.arange(2)
wr5 = []
for gn,g,c in grps5:
    n_=len(g)
    if n_==0: wr5.append(0); continue
    wr5.append(sum(1 for r in g if r['tue_bull'])/n_*100)
fol5 = []
for gn,g,c in grps5:
    n_=len(g)
    if n_==0: fol5.append(0); continue
    fol_=sum(1 for r in g if r['follows_pre'] is True)
    fol5.append(fol_/n_*100)

bars5a = ax5.bar(x5-0.2, wr5,  0.35, color=[GRN,RED], alpha=0.8, label='Martes Sube')
bars5b = ax5.bar(x5+0.2, fol5, 0.35, color=[BLU,ORG], alpha=0.7, label='Sigue Pre-NY')
for b,w in zip(list(bars5a)+list(bars5b), wr5+fol5):
    ax5.text(b.get_x()+b.get_width()/2, w+1.5, f'{w:.0f}%',
             color='white', ha='center', fontsize=9.5, fontweight='bold')
ax5.set_xticks(x5); ax5.set_xticklabels([g[0] for g in grps5],fontsize=9,color=SOFT)
ax5.axhline(50,color='white',lw=0.8,ls='--',alpha=0.4)
ax5.set_ylim(0,100); ax5.set_ylabel('%',color=SOFT)
ax5.set_title('¿El Martes sigue la\ndirección pre-NY (Asia/London)?',color=GOLD,fontsize=10,fontweight='bold')
ax5.legend(fontsize=8.5,facecolor=BG,labelcolor=SOFT)
ax5.tick_params(colors=SOFT)
[ax5.spines[s].set_visible(False) for s in ['top','right']]

# ── 6. Card HOY + resumen accionable ─────────────────────────────────
from matplotlib import patches as mpat
ax6 = fig.add_subplot(gs[1,2]); ax6.set_facecolor('#07070f')
ax6.set_xlim(0,10); ax6.set_ylim(0,16); ax6.axis('off')

ax6.add_patch(mpat.FancyBboxPatch((0.2,14.9),9.6,0.85,
    boxstyle='round,pad=0.1',facecolor='#0a1a0a',edgecolor=GRN,linewidth=2))
ax6.text(5,15.33,'HOY MARTES 7 ABR — LUNES BULLISH',
         ha='center',va='center',fontsize=10,fontweight='bold',color=GRN)

bull_str2 = [r for r in records if r['mon_type']=='BULL_STRONG']
bs_n = max(1,len(bull_str2))
bs_up= sum(1 for r in bull_str2 if r['tue_bull'])
bs_lo= sum(1 for r in bull_str2 if r['swept_mon_lo'])
bs_hi= sum(1 for r in bull_str2 if r['swept_mon_hi'])
bs_poc=sum(1 for r in bull_str2 if r['returns_to_poc'])
bs_avg=sum(r['tue_chg'] for r in bull_str2)/bs_n
bs_rng=sum(r['tue_rng'] for r in bull_str2)/bs_n

card_lines = [
    (GOLD,'bold','── Lunes BULL_STRONG (n=%d) ──'%bs_n,''),
    (GRN, 'bold','Martes sube:',f'{bs_up}/{bs_n} = {bs_up/bs_n*100:.0f}%'),
    (GRN if bs_avg>0 else RED,'bold','Avg Martes:',f'{bs_avg:+.0f}pts'),
    (SOFT,'normal','Rango típico del día:',f'{bs_rng:.0f}pts'),
    (RED, 'bold','Barre LOW lunes (trampa):',f'{bs_lo/bs_n*100:.0f}%'),
    (GOLD,'bold','Barre HIGH lunes:',f'{bs_hi/bs_n*100:.0f}%'),
    (BLU, 'bold','Regresa al POC:',f'{bs_poc/bs_n*100:.0f}%'),
    ('','','',''),
    (GOLD,'bold','── SETUP HOY ──',''),
    (GRN, 'bold','Sesgo: LONG','COT BULL + Lun Bullish'),
    (SOFT,'normal','Si abre en High VA Asia →','Extension alcista'),
    (SOFT,'normal','Si toca LOW lunes →','Sweep + LONG inmediato'),
    (BLU, 'bold','POC nivel clave:','Esperar retorno al POC'),
    (GRN, 'bold','Setup: 1a vela verde >15pts →','LONG TP1 +50pts'),
    (RED, 'bold','NO SHORTS','Contra COT BULL'),
]
for i,(c,w,k,v) in enumerate(card_lines):
    y = 14.1-i*0.82
    if c:
        ax6.text(0.4,y,k,fontsize=8.8,color=c,fontweight=w,va='center')
        if v: ax6.text(5.5,y,v,fontsize=8.8,color=c,fontweight='bold',va='center')

WHITE='#f1f5f9'
out='estudio_martes_completo.png'
plt.savefig(out,dpi=125,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
