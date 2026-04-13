"""
tmp_dias_similares_hoy.py
Encuentra todos los MARTES con patron similar a hoy 7 Abril:
- LOW se forma primero en NY (no importa a que hora)
- Luego sube >= 300pts desde ese minimo
- Muestra que tienen en comun: Lunes previo, VXN, COT, hora del minimo
"""
import csv, json
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

BG='#0a0a16'; PANEL2='#131325'; GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; SOFT='#94a3b8'; DIM='#475569'; ORG='#f97316'; WHITE='#f1f5f9'; TEAL='#14b8a6'

# ══ Cargar 15min ══════════════════════════════════════════════════
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

# ══ COT/VXN DB ═══════════════════════════════════════════════════
with open('data/research/daily_master_db.json') as f:
    db = json.load(f)
cot_by = {}
for rec in db.get('records', []):
    try:
        d   = date.fromisoformat(rec['date'])
        vxn = float(rec.get('vxn', 0) or 0)
        idx = float(rec.get('cot_index', 0) or 0)
        sig = rec.get('cot_signal', '?')
        net = float(rec.get('cot_net', 0) or 0)
        if vxn > 0:
            cot_by[d] = {'vxn':vxn,'idx':idx,'sig':sig,'net':net}
    except: pass

print(f"COT DB: {min(cot_by)} -> {max(cot_by)}")
# Mostrar los ultimos 5 para saber que datos tiene
for d in sorted(cot_by.keys())[-5:]:
    c = cot_by[d]
    print(f"  {d}  vxn={c['vxn']:.1f}  idx={c['idx']:.1f}  sig={c['sig']}")

def ny_bars(d):
    return sorted(
        [b for b in bars_by_date.get(d,[])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )

# ══ Analizar todos los martes ════════════════════════════════════
all_tues = []
for d in sorted(bars_by_date.keys()):
    if d.weekday() != 1: continue
    mon = d - timedelta(days=1)
    ny  = ny_bars(d)
    mny = ny_bars(mon)
    if len(ny) < 8 or len(mny) < 4: continue

    mon_open  = mny[0]['o'];  mon_close = mny[-1]['c']
    mon_lo    = min(b['l'] for b in mny)
    mon_hi    = max(b['h'] for b in mny)
    mon_chg   = round(mon_close - mon_open, 1)
    mon_rng   = round(mon_hi - mon_lo, 1)

    ny_open  = ny[0]['o'];   ny_close  = ny[-1]['c']
    ny_lo    = min(b['l'] for b in ny)
    ny_hi    = max(b['h'] for b in ny)
    lo_bar   = min(ny, key=lambda x: x['l'])
    hi_bar   = max(ny, key=lambda x: x['h'])
    lo_idx   = ny.index(lo_bar)
    hi_idx   = ny.index(hi_bar)

    # Solo LOW→HIGH (reversal alcista dentro del dia)
    if lo_idx >= hi_idx: continue

    reaction   = round(ny_hi - ny_lo, 1)
    swept      = ny_lo <= mon_lo + 8
    sweep_depth= round(mon_lo - ny_lo, 1) if swept else 0
    lo_hr      = lo_bar['et'].hour + lo_bar['et'].minute/60.0

    # COT/VXN
    cot_d = None
    for delta in [0,-1,-2,-3,-4,-5]:
        cd = d + timedelta(days=delta)
        if cd in cot_by: cot_d = cot_by[cd]; break

    # Gap overnight (open martes vs close lunes)
    gap = round(ny_open - mon_close, 1)

    all_tues.append({
        'd': d, 'mon_chg': mon_chg, 'mon_rng': mon_rng,
        'mon_lo': mon_lo, 'mon_hi': mon_hi,
        'ny_lo': ny_lo, 'ny_hi': ny_hi, 'ny_open': ny_open,
        'reaction': reaction, 'swept': swept, 'sweep_depth': sweep_depth,
        'lo_time': lo_bar['et'].strftime('%H:%M'), 'lo_hr': lo_hr,
        'gap': gap,
        'vxn':      cot_d['vxn'] if cot_d else None,
        'cot_idx':  cot_d['idx'] if cot_d else None,
        'cot_sig':  cot_d['sig'] if cot_d else '?',
    })

# ══ FILTRAR similares a hoy: rebote >= 300pts (LOW primero) ══════
similar = [r for r in all_tues if r['reaction'] >= 300]
similar.sort(key=lambda x: -x['reaction'])

print(f"\nTotal martes LOW->HIGH analizados: {len(all_tues)}")
print(f"Con rebote >= 300pts (similar a hoy): {len(similar)}")
print(f"\n{'Fecha':<12} {'Mon_chg':>8} {'Swept':>6} {'Depth':>6} {'Gap':>7} "
      f"{'VXN':>6} {'COT_idx':>8} {'Reaccion':>9} {'Lo_time':>8}")
print('-'*80)
for r in similar:
    sw   = 'SI' if r['swept'] else 'NO'
    vxn  = f"{r['vxn']:.1f}"  if r['vxn']    else '  ?'
    cidx = f"{r['cot_idx']:.0f}" if r['cot_idx'] else '  ?'
    print(f"{str(r['d']):<12} {r['mon_chg']:>+8.0f} {sw:>6} {r['sweep_depth']:>6.0f} "
          f"{r['gap']:>+7.0f} {vxn:>6} {cidx:>8} {r['reaction']:>9.0f} {r['lo_time']:>8}")

# ══ QUE TIENEN EN COMUN ═══════════════════════════════════════════
print(f"\n{'='*60}")
print(f"QUE TIENEN EN COMUN LOS {len(similar)} MARTES:")
print(f"{'='*60}")

mon_chgs = [r['mon_chg'] for r in similar]
vxn_vals = [r['vxn'] for r in similar if r['vxn']]
cot_vals = [r['cot_idx'] for r in similar if r['cot_idx']]
lo_hrs   = [r['lo_hr'] for r in similar]

print(f"  Lunes previo promedio:  {np.mean(mon_chgs):+.0f}pts  mediana={np.median(mon_chgs):+.0f}pts")
print(f"  Lunes < 0 (bajistas):   {sum(1 for v in mon_chgs if v<0)}/{len(similar)}")
print(f"  Lunes < -100pts:        {sum(1 for v in mon_chgs if v<-100)}/{len(similar)}")
print(f"  Sweep del Mon LOW:      {sum(1 for r in similar if r['swept'])}/{len(similar)}")

if vxn_vals:
    print(f"  VXN promedio:           {np.mean(vxn_vals):.1f}  med={np.median(vxn_vals):.1f}")
    print(f"  VXN > 20:               {sum(1 for v in vxn_vals if v>20)}/{len(vxn_vals)}")
    print(f"  VXN > 25:               {sum(1 for v in vxn_vals if v>25)}/{len(vxn_vals)}")

if cot_vals:
    print(f"  COT idx promedio:       {np.mean(cot_vals):.1f}  mediana={np.median(cot_vals):.1f}")
    print(f"  COT idx < 50 (neutral): {sum(1 for v in cot_vals if v<50)}/{len(cot_vals)}")

print(f"  Hora del minimo prom:   {int(np.mean(lo_hrs))}:{int((np.mean(lo_hrs)%1)*60):02d} ET")
print(f"  Minimo ANTES de 10:30:  {sum(1 for r in similar if r['lo_hr']<10.5)}/{len(similar)}")
print(f"  Minimo 10:30-12:00:     {sum(1 for r in similar if 10.5<=r['lo_hr']<12)}/{len(similar)}")
print(f"  Minimo DESPUES de 12:00:{sum(1 for r in similar if r['lo_hr']>=12)}/{len(similar)}")

# ══ FIGURA: tabla visual + scatter ═══════════════════════════════
fig = plt.figure(figsize=(26, 18), facecolor=BG)
fig.suptitle(
    f'MARTES NQ con REBOTE >= 300pts (LOW primero → luego sube)\n'
    f'{len(similar)} casos en historia vs. HOY 7 Abr (440pts) — ¿Qué tienen en común?',
    color=GOLD, fontsize=13, fontweight='bold', y=0.999
)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.40, wspace=0.28,
                       left=0.05, right=0.97, top=0.96, bottom=0.04)

# ── Tabla de los casos ───────────────────────────────────────────
ax_t = fig.add_subplot(gs[0, :]); ax_t.set_facecolor('#06060f'); ax_t.axis('off')
ax_t.set_xlim(0, 26); ax_t.set_ylim(0, len(similar)+2.5)

headers = ['Fecha','Lunes (pts)','Sweep','Profundidad','Gap open','VXN','COT idx','Rebote','Min ET']
xs      = [0.2, 3.2, 6.2, 7.6, 9.3, 11.3, 13.3, 16.0, 19.0]
top_y   = len(similar)+1.8
for h, x in zip(headers, xs):
    ax_t.text(x, top_y, h, fontsize=10, color=GOLD, fontweight='bold', va='center')
ax_t.plot([0.1, 25.9], [top_y-0.45, top_y-0.45], color=DIM, lw=0.8)

for i, r in enumerate(similar):
    y = len(similar) - i + 0.4
    row_c = '#0f0f20' if i % 2 == 0 else '#0a0a18'
    ax_t.add_patch(plt.Rectangle((0.1, y-0.42), 25.8, 0.84,
                                  facecolor=row_c, edgecolor='none'))
    is_today = r['d'] == date(2026, 4, 7)
    
    sw   = 'SI' if r['swept'] else 'NO'
    vxn  = f"{r['vxn']:.1f}" if r['vxn'] else '?'
    cidx = f"{r['cot_idx']:.0f}" if r['cot_idx'] else '?'
    mon_c = GRN if r['mon_chg'] > 0 else RED
    reb_c = GOLD if r['reaction'] >= 400 else (GRN if r['reaction'] >= 300 else WHITE)

    vals = [str(r['d']), f"{r['mon_chg']:+.0f}", sw, f"{r['sweep_depth']:.0f}",
            f"{r['gap']:+.0f}", vxn, cidx, f"{r['reaction']:.0f}pts", r['lo_time']]
    colors= [GOLD if is_today else WHITE, mon_c, GRN if sw=='SI' else SOFT,
             TEAL if r['sweep_depth']>100 else SOFT,
             SOFT, ORG if (r['vxn'] or 0)>25 else SOFT,
             SOFT, reb_c, SOFT]
    for val, x, c in zip(vals, xs, colors):
        fw = 'bold' if is_today else 'normal'
        ax_t.text(x, y, val, fontsize=9.5, color=c, fontweight=fw, va='center')

    if is_today:
        ax_t.plot([0.1, 25.9], [y+0.43, y+0.43], color=GOLD, lw=1.2, alpha=0.6)
        ax_t.plot([0.1, 25.9], [y-0.43, y-0.43], color=GOLD, lw=1.2, alpha=0.6)

# ── VXN vs Rebote ────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[1, 0]); ax1.set_facecolor(PANEL2)
for r in similar:
    if r['vxn']:
        c = GOLD if r['d']==date(2026,4,7) else GRN
        s = 200 if r['d']==date(2026,4,7) else 55
        mk= '*' if r['d']==date(2026,4,7) else 'o'
        ax1.scatter(r['vxn'], r['reaction'], c=c, s=s, marker=mk, zorder=5 if mk=='*' else 3)
ax1.axvline(25, color=RED, lw=1.5, ls='--', alpha=0.6, label='VXN=25')
ax1.set_xlabel('VXN el dia del trade', color=SOFT)
ax1.set_ylabel('Rebote (pts)', color=SOFT)
ax1.set_title('VXN al momento del trade', color=GOLD, fontsize=11, fontweight='bold')
ax1.legend(fontsize=9, facecolor=BG, labelcolor=WHITE)
ax1.tick_params(colors=SOFT); [ax1.spines[s].set_visible(False) for s in ['top','right']]
ax1.grid(color=DIM, alpha=0.15)

# ── Lunes previo vs Rebote ────────────────────────────────────────
ax2 = fig.add_subplot(gs[1, 1]); ax2.set_facecolor(PANEL2)
for r in similar:
    c = GOLD if r['d']==date(2026,4,7) else (RED if r['mon_chg']<0 else GRN)
    s = 200 if r['d']==date(2026,4,7) else 55
    mk= '*' if r['d']==date(2026,4,7) else 'o'
    ax2.scatter(r['mon_chg'], r['reaction'], c=c, s=s, marker=mk, zorder=5 if mk=='*' else 3)
ax2.axvline(0, color=SOFT, lw=1, alpha=0.4)
ax2.set_xlabel('Movimiento del LUNES previo (pts)', color=SOFT)
ax2.set_ylabel('Rebote del martes (pts)', color=SOFT)
ax2.set_title('¿Lunes bajista → martes revierte más?', color=GOLD, fontsize=11, fontweight='bold')
ax2.tick_params(colors=SOFT); [ax2.spines[s].set_visible(False) for s in ['top','right']]
ax2.grid(color=DIM, alpha=0.15)

# ── Hora del mínimo ─────────────────────────────────────────────
ax3 = fig.add_subplot(gs[1, 2]); ax3.set_facecolor(PANEL2)
lo_h = [r['lo_hr'] for r in similar]
bins_h = np.arange(9.5, 16.5, 0.5)
counts, edges = np.histogram(lo_h, bins=bins_h)
bar_colors = [GOLD if (b>=9.5 and b<11) else BLU for b in edges[:-1]]
ax3.bar(edges[:-1], counts, width=0.48, color=bar_colors, alpha=0.85, edgecolor=BG)
ax3.axvline(11.083, color=GOLD, lw=2.5, ls='--', label='HOY 11:05 ET')
ax3.set_xlabel('Hora del minimo del dia (ET)', color=SOFT)
ax3.set_ylabel('N casos', color=SOFT)
ax3.set_title('¿A qué hora se forma el mínimo\nen los rebotes de 300pts+?', color=GOLD, fontsize=11, fontweight='bold')
ax3.legend(fontsize=9, facecolor=BG, labelcolor=WHITE)
xt = [9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 13.0, 14.0, 15.0]
ax3.set_xticks(xt)
ax3.set_xticklabels([f'{int(h)}:{int((h%1)*60):02d}' for h in xt], fontsize=8.5, rotation=45)
ax3.tick_params(colors=SOFT); [ax3.spines[s].set_visible(False) for s in ['top','right']]

out = 'martes_similares_hoy.png'
plt.savefig(out, dpi=118, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
