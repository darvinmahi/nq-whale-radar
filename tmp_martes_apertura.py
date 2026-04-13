"""
martes_apertura_ny.py
HOY: MARTES 7 ABR 2026
Estudio de las primeras velas de NY en los MARTES:
- Vela 9:30 (primeros 15min = 3 velas de 5min)
- Vela 9:45 (siguientes 15min)
- ¿Cuántas oportunidades se dan?
- ¿Qué WR tiene seguir/fade la primera vela?
- Todo usando sesión NY 9:30-16:00 ET
Nota: datos en 15min, 9:30=5min approx, 9:45=10min approx
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

def get_ny_bars(d):
    return sorted(
        [b for b in by_date.get(d,[])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )

def get_mon_ny(d):
    mon = d - timedelta(days=1)
    bars = get_ny_bars(mon)
    if not bars: return None
    return {
        'lo': min(b['l'] for b in bars),
        'hi': max(b['h'] for b in bars),
        'open': bars[0]['o'],
        'close': bars[-1]['c'],
        'chg': round(bars[-1]['c'] - bars[0]['o'], 1),
        'type': lambda chg: (
            'BULL_STRONG' if chg/bars[0]['o']*100 >= 0.8
            else 'BULL' if chg/bars[0]['o']*100 >= 0.3
            else 'FLAT' if chg/bars[0]['o']*100 >= -0.3
            else 'BEAR' if chg/bars[0]['o']*100 >= -0.8
            else 'BEAR_STRONG'
        )
    }

# ── CONSTRUIR ANÁLISIS ────────────────────────────────────────────────
records = []
for d in sorted_dates:
    if d.weekday() != 1: continue   # Solo martes

    ny = get_ny_bars(d)
    if len(ny) < 10: continue

    # Vela 1: 9:30 (primeros 15min)
    v1 = next((b for b in ny if b['et'].hour==9 and b['et'].minute==30), None)
    # Vela 2: 9:45 (siguientes 15min)
    v2 = next((b for b in ny if b['et'].hour==9 and b['et'].minute==45), None)
    # Vela 3: 10:00
    v3 = next((b for b in ny if b['et'].hour==10 and b['et'].minute==0), None)
    # Vela 4: 10:15
    v4 = next((b for b in ny if b['et'].hour==10 and b['et'].minute==15), None)

    if not v1 or not v2: continue

    tue_open  = v1['o']
    tue_close = ny[-1]['c']
    tue_hi    = max(b['h'] for b in ny)
    tue_lo    = min(b['l'] for b in ny)
    tue_chg   = round(tue_close - tue_open, 1)
    tue_bull  = tue_chg > 0
    tue_rng   = round(tue_hi - tue_lo, 1)

    # ── Características v1 (9:30) ─────────────────────────────────────
    v1_bull  = v1['c'] > v1['o']
    v1_body  = round(abs(v1['c'] - v1['o']), 1)
    v1_range = round(v1['h'] - v1['l'], 1)
    v1_wick_hi = round(v1['h'] - max(v1['o'], v1['c']), 1)
    v1_wick_lo = round(min(v1['o'], v1['c']) - v1['l'], 1)
    v1_close_str = 'STRONG' if v1_body > v1_range * 0.6 else ('WEAK' if v1_body < v1_range * 0.3 else 'MED')

    # ¿Precio siguió la dirección de v1?
    follow_v1 = (v1_bull == tue_bull)

    # ── Características v2 (9:45) ─────────────────────────────────────
    v2_bull  = v2['c'] > v2['o']
    v2_body  = round(abs(v2['c'] - v2['o']), 1)
    v2_confirms_v1 = (v2_bull == v1_bull)  # ¿v2 confirma v1?

    # ¿Si v2 confirma v1, el día sigue esa dirección?
    both_agree = v1_bull == v2_bull
    both_agree_correct = both_agree and (v1_bull == tue_bull)

    # ── Monday context ────────────────────────────────────────────────
    mon = d - timedelta(days=1)
    if mon in date_set:
        mon_ny = get_ny_bars(mon)
        mon_chg = round(mon_ny[-1]['c'] - mon_ny[0]['o'], 1) if mon_ny else 0
        pct_mon = mon_chg / mon_ny[0]['o'] * 100 if mon_ny else 0
        if   pct_mon >=  0.8: mon_type = 'BULL_STRONG'
        elif pct_mon >=  0.3: mon_type = 'BULL'
        elif pct_mon >= -0.3: mon_type = 'FLAT'
        elif pct_mon >= -0.8: mon_type = 'BEAR'
        else:                  mon_type = 'BEAR_STRONG'
        mon_lo = min(b['l'] for b in mon_ny) if mon_ny else 0
        mon_hi = max(b['h'] for b in mon_ny) if mon_ny else 0
    else:
        mon_type = 'UNKNOWN'; mon_chg = 0; mon_lo = 0; mon_hi = 0

    # ── Oportunidades identificables ──────────────────────────────────
    # Setup A: Seguir v1 (entry al cierre de v1)
    setup_a_entry = v1['c'] + (1 if v1_bull else -1)
    setup_a_sl    = v1['l'] - 5 if v1_bull else v1['h'] + 5
    setup_a_sl_pts = round(abs(setup_a_entry - setup_a_sl), 1)
    setup_a_tp1   = setup_a_entry + (50 if v1_bull else -50)
    # ¿Se tocó el TP1 sin antes tocar el SL?
    remaining = [b for b in ny if b['et'] > v1['et']]
    tp1_hit_a = False; sl_hit_a = False
    for b in remaining:
        if v1_bull:
            if not sl_hit_a and b['l'] <= setup_a_sl: sl_hit_a=True; break
            if b['h'] >= setup_a_tp1: tp1_hit_a=True; break
        else:
            if not sl_hit_a and b['h'] >= setup_a_sl: sl_hit_a=True; break
            if b['l'] <= setup_a_tp1: tp1_hit_a=True; break
    pnl_a = 50*3*2 if tp1_hit_a else (-setup_a_sl_pts*3*2 if sl_hit_a else 0)

    # Setup B: Fade v1 (contra la dirección de v1, entrada en v2)
    if v2:
        setup_b_bull  = not v1_bull
        setup_b_entry = v2['c'] + (1 if setup_b_bull else -1)
        setup_b_sl    = v2['l'] - 5 if setup_b_bull else v2['h'] + 5
        setup_b_tp1   = setup_b_entry + (50 if setup_b_bull else -50)
        remaining_b   = [b for b in ny if b['et'] > v2['et']]
        tp1_hit_b = False; sl_hit_b = False
        for b in remaining_b:
            if setup_b_bull:
                if not sl_hit_b and b['l'] <= setup_b_sl: sl_hit_b=True; break
                if b['h'] >= setup_b_tp1: tp1_hit_b=True; break
            else:
                if not sl_hit_b and b['h'] >= setup_b_sl: sl_hit_b=True; break
                if b['l'] <= setup_b_tp1: tp1_hit_b=True; break
        pnl_b = 50*3*2 if tp1_hit_b else (-abs(setup_b_entry-setup_b_sl)*3*2 if sl_hit_b else 0)
    else:
        tp1_hit_b=False; sl_hit_b=False; pnl_b=0

    # Setup C: Esperar que v2 confirme v1 → entrar en cierre de v2
    if v2 and v2_confirms_v1:
        setup_c_bull  = v1_bull
        setup_c_entry = v2['c'] + (1 if setup_c_bull else -1)
        setup_c_sl    = min(v1['l'], v2['l']) - 5 if setup_c_bull else max(v1['h'], v2['h']) + 5
        setup_c_tp1   = setup_c_entry + (50 if setup_c_bull else -50)
        tp1_hit_c=False; sl_hit_c=False
        for b in remaining_b:
            if setup_c_bull:
                if not sl_hit_c and b['l']<=setup_c_sl: sl_hit_c=True; break
                if b['h']>=setup_c_tp1: tp1_hit_c=True; break
            else:
                if not sl_hit_c and b['h']>=setup_c_sl: sl_hit_c=True; break
                if b['l']<=setup_c_tp1: tp1_hit_c=True; break
        sl_c_pts = round(abs(setup_c_entry-setup_c_sl), 1)
        pnl_c = 50*3*2 if tp1_hit_c else (-sl_c_pts*3*2 if sl_hit_c else 0)
        c_valid = True
    else:
        tp1_hit_c=False; sl_hit_c=False; pnl_c=0; c_valid=False

    records.append({
        'd': d, 'mon_type': mon_type, 'mon_chg': mon_chg,
        'tue_bull': tue_bull, 'tue_chg': tue_chg, 'tue_rng': tue_rng,
        'v1_bull': v1_bull, 'v1_body': v1_body, 'v1_range': v1_range,
        'v1_close_str': v1_close_str, 'v1_wick_hi': v1_wick_hi, 'v1_wick_lo': v1_wick_lo,
        'v2_bull': v2_bull, 'v2_body': v2_body, 'v2_confirms_v1': v2_confirms_v1,
        'follow_v1': follow_v1, 'both_agree': both_agree, 'both_agree_correct': both_agree_correct,
        # Setup A: seguir v1
        'tp1_a': tp1_hit_a, 'sl_a': sl_hit_a, 'pnl_a': pnl_a,
        # Setup B: fade v1
        'tp1_b': tp1_hit_b, 'sl_b': sl_hit_b, 'pnl_b': pnl_b,
        # Setup C: v2 confirma v1
        'tp1_c': tp1_hit_c, 'sl_c': sl_hit_c, 'pnl_c': pnl_c, 'c_valid': c_valid,
    })

N = len(records)
print(f"MARTES analizados: {N}")
print()

# ═══════════════════════════════════════
# A. VELA 9:30 — ¿Sigue el día?
# ═══════════════════════════════════════
v1_green = [r for r in records if r['v1_bull']]
v1_red   = [r for r in records if not r['v1_bull']]
v1_strong= [r for r in records if r['v1_close_str']=='STRONG']
v1_weak  = [r for r in records if r['v1_close_str']=='WEAK']

print("A. VELA 9:30 ET — ¿El día sigue esa dirección?")
for grp, lbl in [(v1_green,'V1 VERDE (9:30)'),(v1_red,'V1 ROJA (9:30)'),
                  (v1_strong,'V1 FUERTE (body>60%rng)'),(v1_weak,'V1 DEBIL (body<30%rng)')]:
    n_=len(grp)
    if n_==0: continue
    follow_ = sum(1 for r in grp if r['follow_v1'])
    print(f"  {lbl} n={n_}: Día sigue v1 = {follow_}/{n_} = {follow_/n_*100:.0f}%")
    avg_b = sum(r['v1_body'] for r in grp)/n_
    avg_r = sum(r['v1_range'] for r in grp)/n_
    print(f"    Body avg: {avg_b:.0f}pts  Rango avg: {avg_r:.0f}pts")

# ═══════════════════════════════════════
# B. VELA 9:45 — ¿Confirma v1?
# ═══════════════════════════════════════
print()
print("B. VELA 9:45 ET — ¿Confirma la dirección de la 9:30?")
confirms = sum(1 for r in records if r['v2_confirms_v1'])
print(f"  v2 confirma v1: {confirms}/{N} = {confirms/N*100:.0f}%")
# Cuando v2 confirma v1 → ¿el día sigue?
conf_grp = [r for r in records if r['v2_confirms_v1']]
if conf_grp:
    follow_c = sum(1 for r in conf_grp if r['both_agree_correct'])
    print(f"  Cuando v2 confirma v1 → día va en esa dirección: {follow_c}/{len(conf_grp)} = {follow_c/len(conf_grp)*100:.0f}%")

# Patrones de combinación
combos = {
    'V+V (verde+verde)': [r for r in records if r['v1_bull'] and r['v2_bull']],
    'R+R (roja+roja)':   [r for r in records if not r['v1_bull'] and not r['v2_bull']],
    'V+R (verde+roja)':  [r for r in records if r['v1_bull'] and not r['v2_bull']],
    'R+V (roja+verde)':  [r for r in records if not r['v1_bull'] and r['v2_bull']],
}
print()
print("  COMBINACIONES de velas (v1+v2) → WR del día:")
print(f"  {'Combo':<22} {'n':>4} {'Dia Sube%':>10} {'Avg Tue':>9}")
for lbl,grp in combos.items():
    n_=len(grp)
    if n_==0: continue
    # define "correct" para cada combo
    is_up = 'V' in lbl[:3]
    up_ = sum(1 for r in grp if r['tue_bull'])
    avg_ = sum(r['tue_chg'] for r in grp)/n_
    print(f"  {lbl:<20} {n_:>4} {up_/n_*100:>9.0f}% {avg_:>+9.0f}")

# ═══════════════════════════════════════
# C. SETUPS — P&L histórico
# ═══════════════════════════════════════
print()
print("C. BACKTESTING SETUPS (3 MNQ, TP1=+50pts, SL=bajo v1)")
for sname, tp_k, sl_k, pnl_k, grp_filter in [
    ('A: Seguir v1 al cierre', 'tp1_a', 'sl_a', 'pnl_a', records),
    ('B: Fade v1 (contra)',    'tp1_b', 'sl_b', 'pnl_b', records),
    ('C: v2 confirma v1',      'tp1_c', 'sl_c', 'pnl_c', [r for r in records if r['c_valid']]),
]:
    grp = grp_filter
    n_ = len(grp)
    if n_ == 0: continue
    hits = sum(1 for r in grp if r[tp_k])
    loss = sum(1 for r in grp if r[sl_k])
    no_r = n_ - hits - loss
    pnl_tot = sum(r[pnl_k] for r in grp)
    wr = hits/(hits+loss)*100 if (hits+loss)>0 else 0
    print(f"\n  SETUP {sname}:")
    print(f"    n={n_} | TP1: {hits} | SL: {loss} | No resuelto: {no_r}")
    print(f"    WR: {wr:.0f}% | P&L total: {'+' if pnl_tot>=0 else ''}${pnl_tot:.0f}")
    print(f"    P&L promedio/día: {'+' if pnl_tot/n_>=0 else ''}${pnl_tot/n_:.0f}")

# ═══════════════════════════════════════
# D. FILTRO: Solo Lunes BULLISH
# ═══════════════════════════════════════
print()
print("D. FILTRO: Lunes BULL + Setup")
bull_mon_rec = [r for r in records if r['mon_type'] in ['BULL','BULL_STRONG']]
n_bm = len(bull_mon_rec)
print(f"  Con Lunes BULL (n={n_bm}):")
print(f"  v1 verde → día sube: {sum(1 for r in bull_mon_rec if r['v1_bull'] and r['tue_bull'])}/{sum(1 for r in bull_mon_rec if r['v1_bull'])} = {sum(1 for r in bull_mon_rec if r['v1_bull'] and r['tue_bull'])/max(1,sum(1 for r in bull_mon_rec if r['v1_bull']))*100:.0f}%")
print(f"  v1 roja  → día baja: {sum(1 for r in bull_mon_rec if not r['v1_bull'] and not r['tue_bull'])}/{sum(1 for r in bull_mon_rec if not r['v1_bull'])} = {sum(1 for r in bull_mon_rec if not r['v1_bull'] and not r['tue_bull'])/max(1,sum(1 for r in bull_mon_rec if not r['v1_bull']))*100:.0f}%")
# Setup A filtrado
a_bm = [r for r in bull_mon_rec]
hits_a = sum(1 for r in a_bm if r['tp1_a'])
loss_a = sum(1 for r in a_bm if r['sl_a'])
pnl_a  = sum(r['pnl_a'] for r in a_bm)
print(f"  Setup A filtrado: WR={hits_a/max(1,hits_a+loss_a)*100:.0f}% P&L=${pnl_a:+.0f}")

# ═══════════════════════════════════════
# FIGURA
# ═══════════════════════════════════════
fig = plt.figure(figsize=(24,15), facecolor=BG)
fig.suptitle(
    "ESTUDIO APERTURA NY — MARTES (195 casos) | Vela 9:30 y 9:45 ET | Sesión NY only",
    color=GOLD, fontsize=13, fontweight='bold', y=0.99
)
gs = gridspec.GridSpec(2,3, figure=fig, hspace=0.42, wspace=0.28,
                       left=0.05, right=0.97, top=0.94, bottom=0.06)

# ── 1. V1 verde/roja → ¿sigue el día? ─────────────────────────────────
ax1 = fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
grps1 = [
    ('V1\nVERDE 9:30', v1_green, GRN),
    ('V1\nROJA 9:30',  v1_red,   RED),
    ('V1\nFUERTE',     v1_strong, GOLD),
    ('V1\nDEBIL',      v1_weak,   BLU),
]
x1 = np.arange(len(grps1))
wr1_vals = []
for gn,grp,c in grps1:
    n_=len(grp)
    f=sum(1 for r in grp if r['follow_v1'])
    wr1_vals.append(f/max(1,n_)*100)

bars1 = ax1.bar(x1, wr1_vals,
                color=[c for _,_,c in grps1],
                alpha=0.85, width=0.55)
ax1.axhline(50, color='white', lw=1, ls='--', alpha=0.4)
ax1.axhline(60, color=GOLD, lw=0.8, ls='--', alpha=0.3)
for b,w,(gn,grp,c) in zip(bars1, wr1_vals, grps1):
    ax1.text(b.get_x()+b.get_width()/2, w+1.5,
             f'{w:.0f}%', color='white', ha='center', fontsize=12, fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2, 5,
             f'n={len(grp)}', color=SOFT, ha='center', fontsize=8.5)
ax1.set_xticks(x1)
ax1.set_xticklabels([g[0] for g in grps1], fontsize=9, color=SOFT)
ax1.set_ylim(0, 100)
ax1.set_ylabel('% Día sigue dirección v1', color=SOFT)
ax1.set_title('Vela 9:30 ET → ¿El DÍA\nsigue esa dirección?', color=GOLD, fontsize=11, fontweight='bold')
ax1.tick_params(colors=SOFT)
[ax1.spines[s].set_visible(False) for s in ['top','right']]

# ── 2. Combinaciones v1+v2 ────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
combo_data = []
for lbl,grp in combos.items():
    n_=len(grp)
    if n_==0: continue
    up_ = sum(1 for r in grp if r['tue_bull'])
    combo_data.append((lbl, up_/n_*100, n_))

xlbl2 = [c[0] for c in combo_data]
wr2   = [c[1] for c in combo_data]
n2    = [c[2] for c in combo_data]
clrs2 = [GRN if w>=55 else (RED if w<45 else GOLD) for w in wr2]
x2 = np.arange(len(xlbl2))
bars2 = ax2.bar(x2, wr2, color=clrs2, alpha=0.85, width=0.55)
ax2.axhline(50, color='white', lw=1, ls='--', alpha=0.4)
for b,w,n in zip(bars2, wr2, n2):
    ax2.text(b.get_x()+b.get_width()/2, w+1.5, f'{w:.0f}%',
             color='white', ha='center', fontsize=12, fontweight='bold')
    ax2.text(b.get_x()+b.get_width()/2, 5, f'n={n}',
             color=SOFT, ha='center', fontsize=8.5)
ax2.set_xticks(x2); ax2.set_xticklabels(xlbl2, fontsize=9, color=SOFT)
ax2.set_ylim(0, 100)
ax2.set_ylabel('% Día Sube', color=SOFT)
ax2.set_title('Combo V1+V2 (9:30+9:45)\n→ WR del Día', color=GOLD, fontsize=11, fontweight='bold')
ax2.tick_params(colors=SOFT)
[ax2.spines[s].set_visible(False) for s in ['top','right']]

# ── 3. P&L de los 3 setups ────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0,2]); ax3.set_facecolor(PANEL2)
setup_labels = ['A: Seguir\nV1', 'B: Fade\nV1', 'C: V2 conf\nV1']
setup_pnls = [
    sum(r['pnl_a'] for r in records),
    sum(r['pnl_b'] for r in records),
    sum(r['pnl_c'] for r in records if r['c_valid']),
]
setup_wrs = [
    sum(1 for r in records if r['tp1_a']) /
    max(1, sum(1 for r in records if r['tp1_a'] or r['sl_a'])) * 100,
    sum(1 for r in records if r['tp1_b']) /
    max(1, sum(1 for r in records if r['tp1_b'] or r['sl_b'])) * 100,
    sum(1 for r in records if r['c_valid'] and r['tp1_c']) /
    max(1, sum(1 for r in records if r['c_valid'] and (r['tp1_c'] or r['sl_c']))) * 100,
]
clrs3=[GRN if p>0 else RED for p in setup_pnls]
x3=np.arange(3)
bars3=ax3.bar(x3, setup_pnls, color=clrs3, alpha=0.85, width=0.55)
ax3.axhline(0, color='white', lw=1, alpha=0.4)
for b,p,w in zip(bars3, setup_pnls, setup_wrs):
    ax3.text(b.get_x()+b.get_width()/2,
             p + (2000 if p>0 else -4000),
             f'{"+$" if p>=0 else "-$"}{abs(p):.0f}\nWR={w:.0f}%',
             ha='center', fontsize=9.5, color=WHITE, fontweight='bold')
ax3.set_xticks(x3); ax3.set_xticklabels(setup_labels, fontsize=9, color=SOFT)
ax3.set_ylabel('P&L Total ($) — 3MNQ', color=SOFT)
ax3.set_title('P&L Acumulado 195 Martes\n(3 MNQ, TP1=+50pts)', color=GOLD, fontsize=11, fontweight='bold')
ax3.tick_params(colors=SOFT)
[ax3.spines[s].set_visible(False) for s in ['top','right']]

# ── 4. Distribución tamaño v1 ─────────────────────────────────────────
ax4 = fig.add_subplot(gs[1,0]); ax4.set_facecolor(PANEL2)
v1_bodies = [r['v1_body'] for r in records]
v1_ranges = [r['v1_range'] for r in records]
bins = [0,10,20,30,50,80,150,500]
hist_b, _ = np.histogram(v1_bodies, bins=bins)
hist_r, _ = np.histogram(v1_ranges, bins=bins)
xb = np.arange(len(bins)-1)
lbls_b = [f'{bins[i]}-{bins[i+1]}' for i in range(len(bins)-1)]
ax4.bar(xb-0.2, hist_b, 0.35, color=GOLD, alpha=0.8, label='Body v1 (relleno)')
ax4.bar(xb+0.2, hist_r, 0.35, color=SOFT, alpha=0.6, label='Rango v1 (mecha-mecha)')
ax4.set_xticks(xb); ax4.set_xticklabels(lbls_b, fontsize=8, color=SOFT, rotation=30)
ax4.set_ylabel('N casos', color=SOFT)
ax4.set_title('Tamaño de la Vela 9:30\n(pts)', color=GOLD, fontsize=11, fontweight='bold')
for i,(b,r) in enumerate(zip(hist_b,hist_r)):
    if b>2: ax4.text(i-0.2, b+0.5, str(b), ha='center', fontsize=8, color=GOLD)
    if r>2: ax4.text(i+0.2, r+0.5, str(r), ha='center', fontsize=8, color=SOFT)
ax4.legend(fontsize=9, facecolor=BG, labelcolor=SOFT)
ax4.tick_params(colors=SOFT)
[ax4.spines[s].set_visible(False) for s in ['top','right']]

# ── 5. Setup A WR por tipo lunes ──────────────────────────────────────
ax5 = fig.add_subplot(gs[1,1]); ax5.set_facecolor(PANEL2)
types_o=['BULL_STRONG','BULL','FLAT','BEAR','BEAR_STRONG']
types_l=['LUN\nBULL+','LUN\nBULL','LUN\nFLAT','LUN\nBEAR','LUN\nBEAR+']
wr5=[]; n5=[]; pnl5=[]
for mt in types_o:
    g=[r for r in records if r['mon_type']==mt]
    n_=len(g)
    h_=sum(1 for r in g if r['tp1_a'])
    l_=sum(1 for r in g if r['sl_a'])
    wr5.append(h_/max(1,h_+l_)*100)
    n5.append(n_)
    pnl5.append(sum(r['pnl_a'] for r in g))
bars5=ax5.bar(np.arange(5), wr5,
              color=[GRN if w>=55 else (RED if w<45 else GOLD) for w in wr5],
              alpha=0.85, width=0.55)
ax5.axhline(50,color='white',lw=1,ls='--',alpha=0.4)
for b,w,n,p in zip(bars5,wr5,n5,pnl5):
    ax5.text(b.get_x()+b.get_width()/2,w+1.5,f'{w:.0f}%',color='white',ha='center',fontsize=10,fontweight='bold')
    ax5.text(b.get_x()+b.get_width()/2,8,f'n={n}',color=SOFT,ha='center',fontsize=8)
    ax5.text(b.get_x()+b.get_width()/2,w+9,f'{"+$" if p>=0 else "-$"}{abs(p):.0f}',
             color=GRN if p>=0 else RED,ha='center',fontsize=7.5,fontweight='bold')
ax5.set_xticks(np.arange(5)); ax5.set_xticklabels(types_l,fontsize=8.5,color=SOFT)
ax5.set_ylim(0,100); ax5.set_ylabel('WR Setup A (%)',color=SOFT)
ax5.set_title('WR Setup A (Seguir v1)\npor Tipo de Lunes',color=GOLD,fontsize=11,fontweight='bold')
ax5.tick_params(colors=SOFT)
[ax5.spines[s].set_visible(False) for s in ['top','right']]

# ── 6. Card resumen HOY ────────────────────────────────────────────────
ax6=fig.add_subplot(gs[1,2]); ax6.set_facecolor('#07070f')
ax6.set_xlim(0,10); ax6.set_ylim(0,16); ax6.axis('off')

ax6.add_patch(patches.FancyBboxPatch((0.2,14.9),9.6,0.85,
    boxstyle='round,pad=0.1',facecolor='#0a1a0a',edgecolor=GRN,linewidth=2))
ax6.text(5,15.33,'HOY MARTES — APERTURA 9:30 ET',
         ha='center',va='center',fontsize=10,fontweight='bold',color=GRN)

# Stats filtrado Lun BULL
bm=[r for r in records if r['mon_type'] in ['BULL','BULL_STRONG']]
n_bm=max(1,len(bm))
v1g_bm=[r for r in bm if r['v1_bull']]
v1r_bm=[r for r in bm if not r['v1_bull']]
n_v1g=max(1,len(v1g_bm)); n_v1r=max(1,len(v1r_bm))
f_v1g=sum(1 for r in v1g_bm if r['follow_v1'])
f_v1r=sum(1 for r in v1r_bm if r['follow_v1'])
pnl_bm_a=sum(r['pnl_a'] for r in bm)
combo_vv=[r for r in bm if r['v1_bull'] and r['v2_bull']]
combo_rr=[r for r in bm if not r['v1_bull'] and not r['v2_bull']]
n_vv=max(1,len(combo_vv)); n_rr=max(1,len(combo_rr))
up_vv=sum(1 for r in combo_vv if r['tue_bull'])
up_rr=sum(1 for r in combo_rr if not r['tue_bull'])

lines=[
    (GOLD,'bold','── FILTRO Lun BULLISH (n=%d) ──'%n_bm,''),
    (GRN,'bold','V1 verde → día sube:',f'{f_v1g}/{n_v1g} = {f_v1g/n_v1g*100:.0f}%'),
    (RED,'bold','V1 roja  → día baja:',f'{n_v1r-f_v1r}/{n_v1r} = {(n_v1r-f_v1r)/n_v1r*100:.0f}%'),
    (SOFT,'normal','Setup A P&L total:',f'{"+$" if pnl_bm_a>=0 else "-$"}{abs(pnl_bm_a):.0f}'),
    ('','','',''),
    (GOLD,'bold','── COMBO V1+V2 ──',''),
    (GRN,'bold','VERDE+VERDE → más alcista:',f'{up_vv}/{len(combo_vv)} = {up_vv/n_vv*100:.0f}%'),
    (RED,'bold','ROJA+ROJA  → más bajista:',f'{up_rr}/{len(combo_rr)} = {up_rr/n_rr*100:.0f}%'),
    ('','','',''),
    (GOLD,'bold','── REGLA HOY ──',''),
    (GRN,'bold','Si v1(9:30) VERDE + v2(9:45) VERDE:','→ LONG'),
    (RED,'bold','Si v1(9:30) ROJA + v2(9:45) ROJA:','→ SHORT'),
    (GOLD,'bold','Si v1 fuerte (body>60%):','→ Entrada directa'),
    (SOFT,'normal','Si v1 débil o mixto:','Esperar v2 confirm'),
    (BLU,'bold','SL: bajo/alto v1  TP1: +50pts','3MNQ = +$300'),
]
for i,(c,w,k,v) in enumerate(lines):
    y=14.1-i*0.82
    if c:
        ax6.text(0.4,y,k,fontsize=8.5,color=c,fontweight=w,va='center')
        if v: ax6.text(5.3,y,v,fontsize=8.5,color=c,fontweight='bold',va='center')

out='martes_apertura_ny.png'
plt.savefig(out,dpi=125,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
