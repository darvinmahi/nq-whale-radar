# -*- coding: utf-8 -*-
"""
ESTUDIO DEL PRE-MARKET DEL MARTES — 27 sesiones Sep2025-Mar2026
================================================================
Analizamos:
  1. PM direction (BULL/BEAR/NEUTRAL) vs resultado NY
  2. PM magnitud (cuantos puntos movio el PM) vs magnitud NY
  3. PM rango (hi-lo) vs alcista/bajista
  4. Donde cerro el PM respecto al VA → resultado NY
  5. PM fuerte vs PM debil: umbrales de magnitud
  6. Combinaciones: PM direction + posicion VA al cerrar
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats as sst

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Datos ─────────────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(BASE, 'ny_profile_asia_london_daily.csv'))
df['date'] = pd.to_datetime(df['date'])
mar = df[df['weekday'] == 'MARTES'].copy().reset_index(drop=True)

# Calcular variables del PM
mar['pm_move']   = mar['pm_close'] - mar['pm_open']   # cuanto movio el PM (positivo=sube)
mar['pm_move_abs'] = mar['pm_move'].abs()              # magnitud bruta
mar['ny_move']   = mar['pm_close'] - mar['ny_open_price']  # movimiento NY (close-open)
# NOTA: ny_open_price = precio al abrir NY (9:30am) que es el cierre del PM normalmente
# pm_close es el cierre del PM → pm_hi-pm_lo = rango del PM
mar['alcista']   = mar['pm_close'] > mar['ny_open_price']
mar['ny_range']  = mar['pm_hi'] - mar['pm_lo']

# Variables que ya tiene el CSV
# pm_direction: BULLISH/BEARISH/NEUTRAL
# pm_open_pos: donde abrio el PM vs VA
# pm_range: rango del PM (ya calculado en el CSV)
# ny_open_pos: donde abrio NY vs VA (= cierre del PM)

n = len(mar)

# ── Analisis en consola ────────────────────────────────────────────────────────
print("="*65)
print(f"ESTUDIO PRE-MARKET — {n} MARTES (Sep2025-Mar2026)")
print("="*65)

print("\n--- 1. PM DIRECTION vs RESULTADO NY ---")
for pm_dir in ['BULLISH','BEARISH','NEUTRAL']:
    seg = mar[mar['pm_direction'] == pm_dir]
    if len(seg) == 0: continue
    n_alc = seg['alcista'].sum()
    pct = 100 * n_alc / len(seg) if len(seg) > 0 else 0
    mov_med = seg['ny_move'].median()
    rng_med = seg['ny_range'].median()
    pm_pts_med = (seg['pm_close'] - seg['pm_open']).median()
    print(f"\n  PM {pm_dir:8s} (n={len(seg)}):")
    print(f"    → NY alcista:       {n_alc}/{len(seg)} = {pct:.0f}%")
    print(f"    → NY move mediano:  {mov_med:+.0f}pts")
    print(f"    → NY rango mediano: {rng_med:.0f}pts")
    print(f"    → PM movio:         {pm_pts_med:+.0f}pts en promedio")

print("\n--- 2. MAGNITUD DEL PM vs RESULTADO NY ---")
# Cuarto bajo/alto de PM magnitude
q25 = mar['pm_move_abs'].quantile(0.33)
q75 = mar['pm_move_abs'].quantile(0.67)
print(f"  Terciles de magnitud PM: Q33={q25:.0f}pts | Q67={q75:.0f}pts")
for lbl, mask in [
    ('PM debil  (<33pts)',    mar['pm_move_abs'] <  q25),
    ('PM medio  (33-77pts)', (mar['pm_move_abs'] >= q25) & (mar['pm_move_abs'] < q75)),
    ('PM fuerte (>77pts)',    mar['pm_move_abs'] >= q75),
]:
    seg = mar[mask]
    print(f"\n  {lbl} (n={len(seg)}):")
    print(f"    → % Alcistas:    {100*seg['alcista'].mean():.0f}%")
    print(f"    → NY range med:  {seg['ny_range'].median():.0f}pts")
    print(f"    → NY move med:   {seg['ny_move'].median():+.0f}pts")

print("\n--- 3. CORRELACIONES PM vs NY ---")
r1, p1 = sst.pearsonr(mar['pm_move'], mar['ny_move'])
r2, p2 = sst.pearsonr(mar['pm_move_abs'], mar['ny_range'])
r3, p3 = sst.pearsonr(mar['pm_range'], mar['ny_range'])
print(f"  Correlacion PM_move vs NY_move:      r={r1:.3f}  p={p1:.3f}")
print(f"  Correlacion PM_abs  vs NY_range:     r={r2:.3f}  p={p2:.3f}")
print(f"  Correlacion PM_range vs NY_range:    r={r3:.3f}  p={p3:.3f}")

print("\n--- 4. POSICION CIERRE PM vs VA → RESULTADO ---")
for pos in mar['ny_open_pos'].dropna().unique():
    seg = mar[mar['ny_open_pos'] == pos]
    print(f"\n  Cierra PM en {pos} (n={len(seg)}):")
    print(f"    → Alcistas:     {100*seg['alcista'].mean():.0f}%")
    print(f"    → NY move med:  {seg['ny_move'].median():+.0f}pts")

print("\n--- 5. TABLA COMPLETA PM ---")
print(f"{'Fecha':<12} {'PM Dir':8} {'PM Move':8} {'PM Range':9} {'PM_pos':10} {'NY Move':8} {'Tipo'}")
for _, r in mar.sort_values('date').iterrows():
    pm_m = r['pm_close'] - r['pm_open']
    tipo = 'ALC' if r['alcista'] else 'BAJ'
    print(f"  {str(r['date'].date()):<12} {r['pm_direction']:8} {pm_m:+7.0f}  {r['pm_range']:8.0f}   {r['ny_open_pos']:10} {r['ny_move']:+7.0f}   {tipo}")

# ══════════════════════════════════════════════════════════════════════════════
# GRAFICAS
# ══════════════════════════════════════════════════════════════════════════════
CYAN='#00f2ff'; GREEN='#00ff88'; RED='#ff3355'; YELLOW='#ffd60a'
WHITE='#e2e8f8'; GRAY='#4a5a7a'; PURPLE='#a78bfa'; ORANGE='#ff8c00'

fig = plt.figure(figsize=(22, 28), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(4, 3, figure=fig, hspace=0.60, wspace=0.40)

def ax_style(ax, title):
    ax.set_facecolor('#0d1628')
    ax.set_title(title, color=CYAN, fontsize=9.5, fontweight='bold', pad=10)
    ax.tick_params(colors=GRAY, labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

fig.suptitle(f'ESTUDIO PRE-MARKET MARTES NQ — {n} sesiones Sep2025-Mar2026\n'
             f'¿Qué nos dice el pre-market sobre la sesión NY?',
             color=WHITE, fontsize=14, fontweight='bold', y=0.995)

alcol = mar['alcista'].map({True: GREEN, False: RED})
pm_cols = {'BULLISH': GREEN, 'BEARISH': RED, 'NEUTRAL': YELLOW}

# ── P1: PM direction → % alcistas NY ─────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax_style(ax1, '1. PM Direction → % Alcistas en NY\n(la prediccion mas poderosa)')
dirs = ['BULLISH','BEARISH','NEUTRAL']
pcts = []
ns_d = []
for d in dirs:
    seg = mar[mar['pm_direction']==d]
    pcts.append(100*seg['alcista'].mean() if len(seg) > 0 else 0)
    ns_d.append(len(seg))
cols1 = [pm_cols[d] for d in dirs]
bars1 = ax1.bar(range(3), pcts, color=cols1, alpha=0.9, edgecolor='#1e2d4a', width=0.6)
ax1.axhline(50, color=WHITE, linewidth=1.5, linestyle='--', alpha=0.5)
ax1.set_xticks(range(3)); ax1.set_xticklabels(dirs, color=GRAY, fontsize=9)
ax1.set_ylabel('% Martes Alcistas', color=GRAY, fontsize=9); ax1.set_ylim(0,110)
for bar, pct, n_v in zip(bars1, pcts, ns_d):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
             f'{pct:.0f}%\nn={n_v}', ha='center', va='bottom', fontsize=11, color=WHITE, fontweight='bold')

# ── P2: PM direction → NY move mediano ────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax_style(ax2, '2. PM Direction → Move NY mediano\n(puntos ganados/perdidos en sesion NY)')
movs = [mar[mar['pm_direction']==d]['ny_move'].median() for d in dirs]
cols2 = [GREEN if m > 0 else RED for m in movs]
bars2 = ax2.bar(range(3), movs, color=cols2, alpha=0.9, edgecolor='#1e2d4a', width=0.6)
ax2.axhline(0, color=WHITE, linewidth=1, alpha=0.5)
ax2.set_xticks(range(3)); ax2.set_xticklabels(dirs, color=GRAY, fontsize=9)
ax2.set_ylabel('Move NY mediano (pts)', color=GRAY, fontsize=9)
for bar, v in zip(bars2, movs):
    ax2.text(bar.get_x()+bar.get_width()/2,
             bar.get_height() + (5 if v >= 0 else -15),
             f'{v:+.0f}pts', ha='center', va='bottom', fontsize=12, color=WHITE, fontweight='bold')

# ── P3: PM direction → NY range ───────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax_style(ax3, '3. PM Direction → Rango NY\n(amplitud total de la sesion NY)')
rngs = [mar[mar['pm_direction']==d]['ny_range'].median() for d in dirs]
bars3 = ax3.bar(range(3), rngs, color=[pm_cols[d] for d in dirs], alpha=0.85, edgecolor='#1e2d4a', width=0.6)
ax3.set_xticks(range(3)); ax3.set_xticklabels(dirs, color=GRAY, fontsize=9)
ax3.set_ylabel('Rango NY mediano (pts)', color=GRAY, fontsize=9)
for bar, v in zip(bars3, rngs):
    ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{v:.0f}pts', ha='center', va='bottom', fontsize=12, color=WHITE, fontweight='bold')

# ── P4: Scatter PM_move vs NY_move ────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, :2])
ax_style(ax4, '4. PM Move (puntos) vs NY Move (puntos)\n¿Cuando el PM sube mucho, NY también sube mucho?')
pm_move_vals = (mar['pm_close'] - mar['pm_open']).values
ny_move_vals = mar['ny_move'].values

ax4.scatter(pm_move_vals, ny_move_vals, c=alcol, s=100,
            edgecolors=WHITE, linewidths=0.6, zorder=5, alpha=0.9)

for _, r in mar.iterrows():
    pm_m = r['pm_close'] - r['pm_open']
    col = GREEN if r['alcista'] else RED
    ax4.annotate(r['date'].strftime('%m/%d'), (pm_m, r['ny_move']),
                 fontsize=7, color=col, xytext=(4, 4), textcoords='offset points')

# Linea de tendencia
idx = ~np.isnan(pm_move_vals) & ~np.isnan(ny_move_vals)
m_fit, b_fit = np.polyfit(pm_move_vals[idx], ny_move_vals[idx], 1)
x_l = np.linspace(pm_move_vals.min(), pm_move_vals.max(), 100)
ax4.plot(x_l, m_fit*x_l + b_fit, color=WHITE, linewidth=2, linestyle='--', alpha=0.7, label=f'Tendencia (r={r1:.2f})')

ax4.axhline(0, color=GRAY, linewidth=1, alpha=0.4)
ax4.axvline(0, color=GRAY, linewidth=1, alpha=0.4)
ax4.set_xlabel('PM Move (pts) — negativo = PM bajó', color=GRAY, fontsize=10)
ax4.set_ylabel('NY Move (pts) — negativo = NY bajó', color=GRAY, fontsize=10)
ax4.legend(fontsize=9, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

import matplotlib.patches as mpatches
ax4.legend(handles=[
    mpatches.Patch(facecolor=GREEN, label='Martes Alcista'),
    mpatches.Patch(facecolor=RED,   label='Martes Bajista'),
    plt.Line2D([0],[0], color=WHITE, linewidth=2, linestyle='--', label=f'Tendencia r={r1:.2f}')
], fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

ax4.text(0.02, 0.97,
    f'r = {r1:.3f}  p={p1:.3f}\n'
    f'→ {"PM predice bien la direccion NY" if abs(r1) > 0.5 else "PM no predice bien la magnitud NY"}',
    transform=ax4.transAxes, ha='left', va='top', fontsize=10, color=YELLOW,
    bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.9, boxstyle='round'))

# ── P5: PM range vs NY range ───────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 2])
ax_style(ax5, '5. PM Range vs NY Range\n(rango PM predice el rango NY?)')
ax5.scatter(mar['pm_range'], mar['ny_range'], c=alcol, s=90,
            edgecolors=WHITE, linewidths=0.5, zorder=5, alpha=0.9)
for _, r in mar.iterrows():
    col = GREEN if r['alcista'] else RED
    ax5.annotate(r['date'].strftime('%m/%d'), (r['pm_range'], r['ny_range']),
                 fontsize=6.5, color=col, xytext=(3,3), textcoords='offset points')
m3, b3 = np.polyfit(mar['pm_range'].values, mar['ny_range'].values, 1)
xl3 = np.linspace(mar['pm_range'].min(), mar['pm_range'].max(), 100)
ax5.plot(xl3, m3*xl3+b3, color=WHITE, linewidth=1.5, linestyle='--', alpha=0.7, label=f'r={r3:.2f}')
ax5.set_xlabel('PM Range (hi-lo, pts)', color=GRAY, fontsize=8)
ax5.set_ylabel('NY Range (pts)', color=GRAY, fontsize=8)
ax5.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# ── P6: PM magnitude (debil/medio/fuerte) vs % alcistas ───────────────────────
ax6 = fig.add_subplot(gs[2, 0])
ax_style(ax6, '6. Magnitud del PM vs % Alcistas NY\n(si el PM es muy fuerte, ¿garantiza la dir?)')
mag_bands = [
    (f'<{q25:.0f}pts\n(debil)',   mar['pm_move_abs'] < q25),
    (f'{q25:.0f}-{q75:.0f}pts\n(medio)', (mar['pm_move_abs']>=q25)&(mar['pm_move_abs']<q75)),
    (f'>{q75:.0f}pts\n(fuerte)',  mar['pm_move_abs'] >= q75),
]
for i, (lbl, mask) in enumerate(mag_bands):
    seg = mar[mask]
    pct = 100*seg['alcista'].mean() if len(seg) > 0 else 0
    col = CYAN if pct >= 60 else (YELLOW if pct >= 50 else RED)
    bar = ax6.bar(i, pct, color=col, alpha=0.85, edgecolor='#1e2d4a', width=0.6)
    ax6.text(i, pct+2, f'{pct:.0f}%\nn={len(seg)}', ha='center', va='bottom', fontsize=11, color=WHITE, fontweight='bold')
ax6.set_xticks(range(3)); ax6.set_xticklabels([l for l,_ in mag_bands], color=GRAY, fontsize=8)
ax6.axhline(50, color=WHITE, linewidth=1.5, linestyle='--', alpha=0.5)
ax6.set_ylabel('% Alcistas', color=GRAY, fontsize=9); ax6.set_ylim(0,110)

# ── P7: Desglose BULL PM — cuántos son realmente alcistas ────────────────────
ax7 = fig.add_subplot(gs[2, 1])
ax_style(ax7, '7. PM BULLISH: cuantos subieron vs bajaron\n(¿es 100% fiable?)')
bull_alc = mar[(mar['pm_direction']=='BULLISH') & (mar['alcista'])]
bull_baj = mar[(mar['pm_direction']=='BULLISH') & (~mar['alcista'])]
bear_alc = mar[(mar['pm_direction']=='BEARISH') & (mar['alcista'])]
bear_baj = mar[(mar['pm_direction']=='BEARISH') & (~mar['alcista'])]

cats = ['BULL PM\n+Alcista', 'BULL PM\n+Bajista', 'BEAR PM\n+Bajista', 'BEAR PM\n+Alcista']
vals = [len(bull_alc), len(bull_baj), len(bear_baj), len(bear_alc)]
cols7 = [GREEN, '#ff3355', RED, '#00ffaa']
bars7 = ax7.bar(range(4), vals, color=cols7, alpha=0.85, edgecolor='#1e2d4a', width=0.6)
ax7.set_xticks(range(4)); ax7.set_xticklabels(cats, color=GRAY, fontsize=8)
ax7.set_ylabel('N casos', color=GRAY, fontsize=9)
for bar, v in zip(bars7, vals):
    ax7.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.1,
             str(v), ha='center', va='bottom', fontsize=13, color=WHITE, fontweight='bold')
ax7.text(0.5, 0.92, f'BULL PM → {100*len(bull_alc)/(len(bull_alc)+len(bull_baj)):.0f}% son alcistas\nBEAR PM → {100*len(bear_baj)/(len(bear_baj)+len(bear_alc)):.0f}% son bajistas',
         transform=ax7.transAxes, ha='center', va='top', fontsize=10, color=WHITE,
         bbox=dict(facecolor='#0a0f1e', edgecolor=CYAN, alpha=0.95, boxstyle='round'))

# ── P8: Excepciones — cuando el PM miente ────────────────────────────────────
ax8 = fig.add_subplot(gs[2, 2])
ax_style(ax8, '8. Excepciones: cuando el PM\nmintio (PM vs NY opuestos)')
excepciones = mar[
    ((mar['pm_direction']=='BULLISH') & (~mar['alcista'])) |
    ((mar['pm_direction']=='BEARISH') & (mar['alcista']))
].copy()
pm_m_exc = (excepciones['pm_close'] - excepciones['pm_open']).values
ny_m_exc = excepciones['ny_move'].values
col_exc = [GREEN if r['alcista'] else RED for _, r in excepciones.iterrows()]
ax8.barh(range(len(excepciones)), ny_m_exc, color=col_exc, alpha=0.85, edgecolor='#1e2d4a')
ax8.set_yticks(range(len(excepciones)))
ax8.set_yticklabels([f"{r['date'].strftime('%m/%d')} PM={r['pm_direction'][:4]}"
                     for _, r in excepciones.iterrows()], fontsize=8, color=GRAY)
ax8.axvline(0, color=WHITE, linewidth=1)
ax8.set_xlabel('Move NY (pts)', color=GRAY, fontsize=8)
for i, (pm_m, ny_m) in enumerate(zip(pm_m_exc, ny_m_exc)):
    ax8.text(ny_m + (5 if ny_m >= 0 else -5), i, f'{ny_m:+.0f}', ha='left' if ny_m >= 0 else 'right',
             va='center', fontsize=8.5, color=WHITE, fontweight='bold')

# ── P9: Tabla completa ────────────────────────────────────────────────────────
ax9 = fig.add_subplot(gs[3, :])
ax_style(ax9, 'TABLA COMPLETA — Pre-market vs Sesion NY (todos los 27 martes)')
ax9.axis('off')

headers = ['Fecha','PM Dir','PM Move','PM Range','NY abre en','NY Move','NY Range','Tipo']
rows = [headers]
for _, r in mar.sort_values('date').iterrows():
    pm_m = r['pm_close'] - r['pm_open']
    tipo = 'ALCISTA' if r['alcista'] else 'BAJISTA'
    rows.append([
        r['date'].strftime('%Y-%m-%d'),
        r['pm_direction'],
        f'{pm_m:+.0f}pts',
        f"{r['pm_range']:.0f}pts",
        str(r.get('ny_open_pos', r.get('pm_open_pos', '-'))),
        f"{r['ny_move']:+.0f}pts",
        f"{r['ny_range']:.0f}pts",
        tipo,
    ])

t = ax9.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.55)
for (row, col), cell in t.get_celld().items():
    cell.set_facecolor('#0a0f1e' if row==0 else ('#0d1628' if row%2==0 else '#0f1c30'))
    cell.set_edgecolor('#1e2d4a')
    txt = cell.get_text()
    if row == 0:
        txt.set_color(CYAN); txt.set_fontweight('bold')
    else:
        v = rows[row][col]
        tipo = rows[row][7]
        if col == 1:
            txt.set_color(GREEN if v=='BULLISH' else (RED if v=='BEARISH' else YELLOW))
        elif col == 2:
            txt.set_color(GREEN if '+' in str(v) and v not in ['+0'] else RED)
        elif col == 7:
            txt.set_color(GREEN if v=='ALCISTA' else RED)
            txt.set_fontweight('bold')
        elif '+' in str(v) and 'pts' in str(v) and col in [5]:
            txt.set_color(GREEN); txt.set_fontweight('bold')
        elif '-' in str(v) and 'pts' in str(v) and col in [5]:
            txt.set_color(RED); txt.set_fontweight('bold')
        else:
            txt.set_color(WHITE)

out = os.path.join(BASE, 'martes_premarket_estudio.png')
plt.savefig(out, dpi=135, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] -> {out}")
