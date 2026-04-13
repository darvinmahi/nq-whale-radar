"""
estudio_martes_sweeps.py
¿Qué niveles toca/barre el MARTES?
- Low/High del LUNES NY
- Low/High de Asia (overnight antes del NY martes)  
- Low/High de la semana anterior (Friday close)
- ¿Cuándo lo toca? ¿Revierte después?
HOY: Martes 7 Abril 2026
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

# ── CARGAR TODO ───────────────────────────────────────────────────────
by_date = defaultdict(list)
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            by_date[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close'])
            })
        except: pass

sorted_dates = sorted(by_date.keys())
date_set = set(sorted_dates)

def get_session(d, h_start, m_start, h_end, m_end):
    bars = [b for b in by_date.get(d,[])
            if (b['et'].hour*60+b['et'].minute >= h_start*60+m_start) and
               (b['et'].hour*60+b['et'].minute <= h_end*60+m_end)]
    if not bars: return None
    return {
        'hi': max(b['h'] for b in bars),
        'lo': min(b['l'] for b in bars),
        'open': bars[0]['o'],
        'close': bars[-1]['c'],
        'bars': bars
    }

def get_overnight(tue):
    """Asia/London antes del NY del martes: desde 18:00 ET del lunes hasta 9:29 ET martes"""
    mon = tue - timedelta(days=1)
    bars = []
    # Lunes 18:00+ (after hours lunes)
    bars += [b for b in by_date.get(mon,[]) if b['et'].hour >= 18]
    # Martes pre-market (hasta 9:29)
    bars += [b for b in by_date.get(tue,[])
             if b['et'].hour < 9 or (b['et'].hour==9 and b['et'].minute<30)]
    if not bars: return None
    return {
        'hi': max(b['h'] for b in bars),
        'lo': min(b['l'] for b in bars),
        'n': len(bars)
    }

def get_prev_week_range(d):
    """Rango de la semana anterior (buscar el viernes previo)"""
    prev = d - timedelta(days=7)
    wk_bars = []
    for dd in [prev+timedelta(days=i) for i in range(5)]:
        ny = get_session(dd, 9, 30, 16, 0)
        if ny: wk_bars += ny['bars']
    if not wk_bars: return None
    return {
        'hi': max(b['h'] for b in wk_bars),
        'lo': min(b['l'] for b in wk_bars)
    }

# ── CONSTRUIR CASOS ───────────────────────────────────────────────────
results = []
for d in sorted_dates:
    if d.weekday() != 1: continue  # Solo martes

    mon = d - timedelta(days=1)
    if mon not in date_set: continue

    # Niveles clave
    mon_ny  = get_session(mon, 9, 30, 16, 0)
    tue_ny  = get_session(d,   9, 30, 16, 0)
    asia_ov = get_overnight(d)
    prev_wk = get_prev_week_range(d)

    if not mon_ny or not tue_ny: continue
    if len(tue_ny['bars']) < 6: continue

    tue_lo   = tue_ny['lo']
    tue_hi   = tue_ny['hi']
    tue_open = tue_ny['open']
    tue_close= tue_ny['close']
    tue_chg  = round(tue_close - tue_open, 1)
    tue_bull = tue_chg > 0
    mon_chg  = round(mon_ny['close'] - mon_ny['open'], 1)

    # ── SWEEP CHECKS (barre = llega dentro de 5pts del nivel) ──────────
    tol = 5  # tolerancia en puntos para considerar "tocó" el nivel

    # 1. Sweep del LOW del lunes
    swept_mon_lo  = tue_lo <= mon_ny['lo'] + tol
    # 2. Sweep del HIGH del lunes
    swept_mon_hi  = tue_hi >= mon_ny['hi'] - tol
    # 3. Sweep del LOW de Asia/overnight
    swept_asia_lo = (asia_ov is not None) and (tue_lo <= asia_ov['lo'] + tol)
    # 4. Sweep del HIGH de Asia/overnight
    swept_asia_hi = (asia_ov is not None) and (tue_hi >= asia_ov['hi'] - tol)
    # 5. Sweep del LOW semana anterior
    swept_prevwk_lo = (prev_wk is not None) and (tue_lo <= prev_wk['lo'] + tol)
    # 6. Sweep del HIGH semana anterior
    swept_prevwk_hi = (prev_wk is not None) and (tue_hi >= prev_wk['hi'] - tol)

    # ── TIMING del sweep del low mon ────────────────────────────────────
    mon_lo_time = None
    if swept_mon_lo:
        for b in tue_ny['bars']:
            if b['l'] <= mon_ny['lo'] + tol:
                mon_lo_time = b['et'].hour
                break

    # ── REVERSIÓN después de sweep ──────────────────────────────────────
    # Sweep low lunes y luego CIERRA por encima del open del martes
    sweep_and_reverse = swept_mon_lo and tue_close > tue_open

    results.append({
        'tue': d, 'mon': mon,
        'mon_chg': mon_chg, 'tue_chg': tue_chg, 'tue_bull': tue_bull,
        'tue_lo': tue_lo, 'tue_hi': tue_hi,
        'mon_lo': mon_ny['lo'], 'mon_hi': mon_ny['hi'],
        'asia_lo': asia_ov['lo'] if asia_ov else None,
        'asia_hi': asia_ov['hi'] if asia_ov else None,
        'swept_mon_lo': swept_mon_lo,
        'swept_mon_hi': swept_mon_hi,
        'swept_asia_lo': swept_asia_lo,
        'swept_asia_hi': swept_asia_hi,
        'swept_prevwk_lo': swept_prevwk_lo,
        'swept_prevwk_hi': swept_prevwk_hi,
        'mon_lo_time': mon_lo_time,
        'sweep_and_reverse': sweep_and_reverse,
        'tue_rng': round(tue_hi - tue_lo, 1)
    })

n_total = len(results)
print(f"Total Martes analizados: {n_total}")
print()

# ── ESTADÍSTICAS SWEEP ────────────────────────────────────────────────
def stats(grp, label):
    n = len(grp)
    if n == 0: return
    pct = lambda k: sum(1 for r in grp if r[k])/n*100
    print(f"{'='*55}")
    print(f"{label}  (n={n})")
    print(f"  Barre LOW  del Lunes:       {pct('swept_mon_lo'):>5.0f}%")
    print(f"  Barre HIGH del Lunes:       {pct('swept_mon_hi'):>5.0f}%")
    print(f"  Barre LOW  de Asia ovn:     {pct('swept_asia_lo'):>5.0f}%")
    print(f"  Barre HIGH de Asia ovn:     {pct('swept_asia_hi'):>5.0f}%")
    print(f"  Barre LOW  sem anterior:    {pct('swept_prevwk_lo'):>5.0f}%")
    print(f"  Barre HIGH sem anterior:    {pct('swept_prevwk_hi'):>5.0f}%")
    # Cuando barre el low del lunes y revierte
    sw_rev = [r for r in grp if r['swept_mon_lo']]
    if sw_rev:
        n_sw = len(sw_rev)
        rev = sum(1 for r in sw_rev if r['sweep_and_reverse'])
        print(f"  Sweep low lunes → REVIERTE:{rev/n_sw*100:>5.0f}%  (n={n_sw})")
        # Timing
        times = [r['mon_lo_time'] for r in sw_rev if r['mon_lo_time']]
        tc = Counter(times).most_common(4)
        print(f"  Timing sweep low: {tc}")
    print()

# Todos los martes
stats(results, "TODOS LOS MARTES")

# Martes después de lunes BAJISTA
mon_bear = [r for r in results if r['mon_chg'] < -50]
stats(mon_bear, "MARTES después de LUNES BAJISTA (>-50pts)")

# Martes después de lunes CRASH
mon_crash = [r for r in results if r['mon_chg'] <= -100]
stats(mon_crash, "MARTES después de LUNES CRASH (>-100pts)")

# Cuando sweep low lunes y revierte: detalles
sw_rev_cases = [r for r in mon_crash if r['swept_mon_lo']]
print(f"\nCASOS CRASH+SWEEP LOW LUNES ({len(sw_rev_cases)} casos):")
print(f"  {'Martes':<12} {'MonChg':>8} {'TueChg':>9} {'Rev':>5} {'Timing':>7}")
for r in sw_rev_cases:
    rev = 'SI' if r['sweep_and_reverse'] else 'NO'
    tm  = f"{r['mon_lo_time']}h" if r['mon_lo_time'] else '?'
    print(f"  {str(r['tue']):<12} {r['mon_chg']:>+8.0f} {r['tue_chg']:>+9.0f} {rev:>5} {tm:>7}")

# ── Para HOY ─────────────────────────────────────────────────────────
print()
print("="*55)
print("HOY MARTES 7 ABR 2026 — Lo que dice la historia:")
print()
print("Con lunes CRASH > -100pts:")
n_c = len(mon_crash)
sw_lo = sum(1 for r in mon_crash if r['swept_mon_lo'])
sw_hi = sum(1 for r in mon_crash if r['swept_mon_hi'])
sw_as_lo = sum(1 for r in mon_crash if r['swept_asia_lo'])
sw_as_hi = sum(1 for r in mon_crash if r['swept_asia_hi'])
print(f"  Barre LOW  lunes NY:  {sw_lo}/{n_c} = {sw_lo/max(1,n_c)*100:.0f}%")
print(f"  Barre HIGH lunes NY:  {sw_hi}/{n_c} = {sw_hi/max(1,n_c)*100:.0f}%")
print(f"  Barre LOW  Asia:      {sw_as_lo}/{n_c} = {sw_as_lo/max(1,n_c)*100:.0f}%")
print(f"  Barre HIGH Asia:      {sw_as_hi}/{n_c} = {sw_as_hi/max(1,n_c)*100:.0f}%")

if sw_rev_cases:
    n_sw = len(sw_rev_cases)
    rev  = sum(1 for r in sw_rev_cases if r['sweep_and_reverse'])
    print(f"\n  Sweep low lunes + REVIERTE alcista: {rev}/{n_sw} = {rev/max(1,n_sw)*100:.0f}%")
    times_crash = [r['mon_lo_time'] for r in sw_rev_cases if r['mon_lo_time']]
    if times_crash:
        tc = Counter(times_crash).most_common(3)
        print(f"  Timing sweep: {[f'{h}h ({v}x)' for h,v in tc]}")
        print(f"  Setup: Esperar sweep low lunes → entrada LONG → TP 50-80pts")

# ── FIGURA ────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22,13), facecolor=BG)
fig.suptitle("ESTUDIO MARTES — ¿Qué niveles BARRE? NQ 2017-2026 | Setup: Sweep Low Lunes → Long",
             color=GOLD, fontsize=13, fontweight='bold', y=0.99)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.30,
                       left=0.05, right=0.97, top=0.95, bottom=0.05)

# Panel A: Frecuencia de sweep por nivel
ax1 = fig.add_subplot(gs[0, 0])
ax1.set_facecolor(PANEL2)
grupos_sweep = {
    'TODOS': results,
    'Lun Bajista\n(>-50)': mon_bear,
    'Lun CRASH\n(>-100)': mon_crash,
}
sweep_keys = ['swept_mon_lo','swept_mon_hi','swept_asia_lo','swept_asia_hi']
sweep_lbls = ['LOW Lunes','HIGH Lunes','LOW Asia','HIGH Asia']
sweep_clrs = [RED, GRN, ORG, BLU]

x = np.arange(len(sweep_lbls))
width = 0.25
offsets = [-0.25, 0, 0.25]
grp_clrs = [SOFT, GOLD, GRN]

for gi, (gnm, grp) in enumerate(grupos_sweep.items()):
    n_ = len(grp)
    if n_ == 0: continue
    pcts = [sum(1 for r in grp if r[k])/n_*100 for k in sweep_keys]
    bars = ax1.bar(x + offsets[gi], pcts, width,
                   color=grp_clrs[gi], alpha=0.8, label=f'{gnm} (n={n_})')
    for b_, p_ in zip(bars, pcts):
        ax1.text(b_.get_x()+b_.get_width()/2, p_+1.5,
                 f'{p_:.0f}%', ha='center', fontsize=8, color='white', fontweight='bold')

ax1.set_xticks(x); ax1.set_xticklabels(sweep_lbls, fontsize=9, color=SOFT)
ax1.set_ylim(0, 100); ax1.set_ylabel('% Tuesdays que tocan el nivel', color=SOFT)
ax1.set_title('¿Qué niveles barre el Martes?', color=GOLD, fontsize=11, fontweight='bold')
ax1.axhline(50, color=DIM, lw=0.8, ls='--', alpha=0.5)
ax1.legend(fontsize=8, facecolor=BG, labelcolor=SOFT)
ax1.tick_params(colors=SOFT)
[ax1.spines[s].set_visible(False) for s in ['top','right']]

# Panel B: Timing del sweep del low lunes
ax2 = fig.add_subplot(gs[0, 1])
ax2.set_facecolor(PANEL2)
times_all = [r['mon_lo_time'] for r in results if r['swept_mon_lo'] and r['mon_lo_time']]
times_crash = [r['mon_lo_time'] for r in mon_crash if r['swept_mon_lo'] and r['mon_lo_time']]

all_hrs = list(range(9, 16))
count_all   = [times_all.count(h) for h in all_hrs]
count_crash = [times_crash.count(h) for h in all_hrs]

ax2.bar([h-0.2 for h in all_hrs], count_all,   0.35, color=SOFT,   alpha=0.7, label=f'Todos los martes (n={len(times_all)})')
ax2.bar([h+0.2 for h in all_hrs], count_crash, 0.35, color=GOLD,   alpha=0.9, label=f'Post-CRASH (n={len(times_crash)})')
ax2.set_xticks(all_hrs)
ax2.set_xticklabels([f'{h}:00' for h in all_hrs], fontsize=8.5, color=SOFT, rotation=30)
ax2.set_ylabel('Cantidad de veces', color=SOFT)
ax2.set_title('TIMING: ¿A qué hora se toca\nel LOW del Lunes?', color=GOLD, fontsize=11, fontweight='bold')
ax2.legend(fontsize=8.5, facecolor=BG, labelcolor=SOFT)
ax2.tick_params(colors=SOFT)
[ax2.spines[s].set_visible(False) for s in ['top','right']]

# Panel C: Sweep + Reversión
ax3 = fig.add_subplot(gs[0, 2])
ax3.set_facecolor(PANEL2)
# Cuando hay sweep del low lunes ¿qué pasa después?
sw_all = [r for r in results if r['swept_mon_lo']]
sw_cr  = [r for r in mon_crash if r['swept_mon_lo']]

categorias = ['Revierte\n(cierra↑)', 'No revierte\n(cierra↓)']
vals_all  = [sum(1 for r in sw_all if r['sweep_and_reverse']),
             sum(1 for r in sw_all if not r['sweep_and_reverse'])]
vals_cr   = [sum(1 for r in sw_cr if r['sweep_and_reverse']),
             sum(1 for r in sw_cr if not r['sweep_and_reverse'])]

x3 = np.arange(2)
ax3.bar(x3-0.2, vals_all, 0.35, color=[GRN,RED], alpha=0.6, label=f'Todos sweep (n={len(sw_all)})')
ax3.bar(x3+0.2, vals_cr,  0.35, color=[GRN,RED], alpha=0.9,
        edgecolor=GOLD, linewidth=1.5, label=f'Post-CRASH (n={len(sw_cr)})')
for i,(a,c) in enumerate(zip(vals_all,vals_cr)):
    ax3.text(i-0.2, a+0.2, str(a), ha='center', fontsize=11, color='white', fontweight='bold')
    ax3.text(i+0.2, c+0.2, str(c), ha='center', fontsize=11, color=GOLD, fontweight='bold')
ax3.set_xticks(x3); ax3.set_xticklabels(categorias, fontsize=10, color=SOFT)
ax3.set_title('Después del SWEEP LOW Lunes\n¿Revierte o continúa?', color=GOLD, fontsize=11, fontweight='bold')
ax3.legend(fontsize=8.5, facecolor=BG, labelcolor=SOFT)
ax3.tick_params(colors=SOFT)
[ax3.spines[s].set_visible(False) for s in ['top','right']]

# Panel D: Tabla resumen completa
ax4 = fig.add_subplot(gs[1, :2])
ax4.set_facecolor(PANEL2)
ax4.set_xlim(0, 16); ax4.set_ylim(0, len(mon_crash)+1); ax4.axis('off')

hdrs = ['Martes','LunChg','TueChg','Low Lun?','High Lun?','Low Asia?','High Asia?','SwpRevrt?','Timing']
xs   = [0.1, 2.0, 3.6, 5.1, 6.7, 8.3, 9.9, 11.5, 13.2]
yh   = len(mon_crash)+0.5
for h_,x_ in zip(hdrs,xs):
    ax4.text(x_, yh, h_, fontsize=8.5, color=GOLD, fontweight='bold', va='center')
ax4.axhline(yh-0.2, color=DIM, lw=0.7)

for i, r in enumerate(reversed(mon_crash)):
    y = i + 0.35
    def yn(v, yes_clr=GRN, no_clr=RED):
        return ('SI', yes_clr) if v else ('NO', no_clr)
    tc = r['tue_chg']; tc_c = GRN if tc>0 else RED
    mc = r['mon_chg']
    ax4.text(xs[0], y, str(r['tue']),        fontsize=8,   color=SOFT,  va='center')
    ax4.text(xs[1], y, f'{mc:+.0f}',         fontsize=8.5, color=RED,   va='center', fontweight='bold')
    ax4.text(xs[2], y, f'{tc:+.0f}',         fontsize=8.5, color=tc_c,  va='center', fontweight='bold')
    for j,key in enumerate(['swept_mon_lo','swept_mon_hi','swept_asia_lo','swept_asia_hi','sweep_and_reverse']):
        txt, clr = yn(r[key])
        ax4.text(xs[3+j], y, txt, fontsize=8, color=clr, va='center', fontweight='bold')
    tm = f"{r['mon_lo_time']}h" if r['mon_lo_time'] else '-'
    ax4.text(xs[8], y, tm, fontsize=8.5, color=BLU, va='center', fontweight='bold')
    ax4.axhline(y - 0.25, color='#1e293b', lw=0.4)

ax4.set_title(f'TODOS LOS MARTES POST-CRASH (lunes <-100pts) — {len(mon_crash)} casos',
              color=GOLD, fontsize=11, fontweight='bold', pad=8)

# Panel E: Card HOY
ax5 = fig.add_subplot(gs[1, 2])
ax5.set_facecolor('#070718')
ax5.set_xlim(0,10); ax5.set_ylim(0,14); ax5.axis('off')

from matplotlib import patches as mpatches
ax5.add_patch(mpatches.FancyBboxPatch((0.2,13.1),9.6,0.75,
    boxstyle='round,pad=0.1',facecolor='#0d0d30',edgecolor=GOLD,linewidth=2))
ax5.text(5,13.48,'HOY MARTES 7 ABR — SETUP',
         ha='center',va='center',fontsize=11,fontweight='bold',color=GOLD)

n_c2 = len(mon_crash)
sw_l  = sum(1 for r in mon_crash if r['swept_mon_lo'])
sw_lr = sum(1 for r in mon_crash if r['swept_mon_lo'] and r['sweep_and_reverse'])
sw_h  = sum(1 for r in mon_crash if r['swept_mon_hi'])
sw_al = sum(1 for r in mon_crash if r['swept_asia_lo'])
sw_ah = sum(1 for r in mon_crash if r['swept_asia_hi'])

if sw_rev_cases:
    t_best = Counter([r['mon_lo_time'] for r in sw_rev_cases if r['mon_lo_time']]).most_common(1)
    best_hr = t_best[0][0] if t_best else 9
else:
    best_hr = 9

lines_card = [
    (GOLD, 'bold',   '── ESTADÍSTICAS CRASH ──', ''),
    (RED,  'bold',   'Barre LOW Lunes:',   f'{sw_l}/{n_c2} = {sw_l/max(1,n_c2)*100:.0f}%'),
    (GRN if sw_lr/max(1,sw_l)>=0.5 else RED,'bold',
                     '  → y REVIERTE:',   f'{sw_lr}/{sw_l} = {sw_lr/max(1,sw_l)*100:.0f}%'),
    (GRN,  'bold',   'Barre HIGH Lunes:',  f'{sw_h}/{n_c2} = {sw_h/max(1,n_c2)*100:.0f}%'),
    (ORG,  'bold',   'Barre LOW Asia:',    f'{sw_al}/{n_c2} = {sw_al/max(1,n_c2)*100:.0f}%'),
    (BLU,  'bold',   'Barre HIGH Asia:',   f'{sw_ah}/{n_c2} = {sw_ah/max(1,n_c2)*100:.0f}%'),
    ('','','',''),
    (GOLD, 'bold',   '── SETUP HOY ──', ''),
    (SOFT, 'normal', 'Nivel clave:', f'LOW Lunes 6 Abr'),
    (SOFT, 'normal', 'Hora sweep típica:', f'{best_hr}:00-{best_hr+1}:00 ET'),
    (GRN,  'bold',   'Si toca LOW+revierte:','→ LONG'),
    (SOFT, 'normal', 'SL: bajo el sweep', 'TP1: +50pts'),
    (ORG,  'bold',   'Rango esperado hoy:', '~200-380pts'),
    (RED,  'bold',   'SIN sweep confirmado:', 'NO entrar'),
]
for i,(c,w,k,v) in enumerate(lines_card):
    y = 12.4 - i*0.82
    if c:
        ax5.text(0.4,y,k,fontsize=9,color=c,fontweight=w,va='center')
        if v: ax5.text(5.4,y,v,fontsize=9,color=c,fontweight='bold',va='center')

out = 'estudio_martes_sweeps.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
