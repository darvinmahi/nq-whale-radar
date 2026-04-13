# -*- coding: utf-8 -*-
"""
¿El VXN explica las diferencias de movimiento entre los grupos A/B/C/D?
=======================================================================
Pregunta exacta: dentro de los 16 alcistas ya agrupados,
¿los que movieron más lo hicieron porque tenían VXN más alto?
¿O el VXN era similar entre grupos y el patron es lo que explica el tamaño?
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json, yfinance as yf

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Cargar datos ─────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(BASE, 'ny_profile_asia_london_daily.csv'))
df['date'] = pd.to_datetime(df['date'])
mar = df[df['weekday'] == 'MARTES'].copy().reset_index(drop=True)
mar['ny_move_pts'] = mar['pm_close'] - mar['ny_open_price']
mar['ny_range']    = mar['pm_hi'] - mar['pm_lo']
mar['alcista']     = mar['pm_close'] > mar['ny_open_price']

# VIX
vix_raw = yf.download('^VIX', start='2025-09-01', end='2026-04-08', interval='1d', auto_adjust=True, progress=False)
vix_raw = vix_raw.reset_index()
vix_raw.columns = [c[0] if isinstance(c, tuple) else c for c in vix_raw.columns]
vix_raw['Date'] = pd.to_datetime(vix_raw['Date']).dt.date
vix_dict = {str(r['Date']): float(r['Close']) for _, r in vix_raw.iterrows() if pd.notna(r['Close'])}
mar['vix'] = mar['date'].apply(lambda x: vix_dict.get(str(x.date())))

# COT
with open(os.path.join(BASE, 'data', 'research', 'daily_master_db.json'), encoding='utf-8') as f:
    db = json.load(f)
db_dict = {r['date'][:10]: r for r in db.get('records', [])}
mar['cot_idx'] = mar['date'].apply(lambda x: db_dict.get(str(x.date()), {}).get('cot_index'))

# ── Solo ALCISTAS ─────────────────────────────────────────────────────────────
alc = mar[mar['alcista']].copy().reset_index(drop=True)

def clasificar(r):
    pm = r['pm_direction']; bv = bool(r['breaks_val']); bvh = bool(r['breaks_vah'])
    mov = float(r['ny_move_pts'])
    if pm == 'BEARISH' and bv and bvh and mov > 0: return 'A — TRAMPA BAJISTA'
    if pm == 'BULLISH' and not bv and bvh:          return 'B — CONTINUACION LIMPIA'
    if pm == 'BULLISH' and bv and bvh:              return 'C — RANGO COMPLETO'
    if not bvh:                                      return 'D — ALCISTA CONTENIDO'
    if pm == 'NEUTRAL' and mov > 0:                  return 'E — NEUTRAL->ALZA'
    return 'OTRO'

alc['patron'] = alc.apply(clasificar, axis=1)

# ══════════════════════════════════════════════════════════════════════════════
# ANALISIS: ¿El VXN de cada grupo explica su move?
# ══════════════════════════════════════════════════════════════════════════════
print("="*65)
print("¿EL VXN EXPLICA LA DIFERENCIA DE PUNTOS ENTRE GRUPOS?")
print("="*65)
print()
print(f"{'GRUPO':<28} {'N':>3} {'VXN med':>8} {'Rango med':>10} {'Move med':>10}")
print("-"*65)
for pat, g in alc.groupby('patron'):
    vxn_m  = g['vxn'].median()
    rng_m  = g['ny_range'].median()
    mov_m  = g['ny_move_pts'].median()
    print(f"  {pat:<26} {len(g):>3}    {vxn_m:>6.1f}    {rng_m:>8.0f}pts    {mov_m:>+8.0f}pts")

print()

# Correlacion dentro de alcistas: VXN vs rango
from scipy import stats as sst
corr_r, corr_p = sst.pearsonr(alc['vxn'].dropna(), alc.loc[alc['vxn'].notna(), 'ny_range'])
print(f"Correlacion VXN vs Rango (todos alcistas): r={corr_r:.3f}  p={corr_p:.3f}")
corr_r2, corr_p2 = sst.pearsonr(alc['vxn'].dropna(), alc.loc[alc['vxn'].notna(), 'ny_move_pts'])
print(f"Correlacion VXN vs Move  (todos alcistas): r={corr_r2:.3f}  p={corr_p2:.3f}")
print()
print("Interpretacion de r:")
print("  r cerca de 0   → VXN NO explica el movimiento")
print("  r cerca de 1   → VXN SI explica: mas VXN = mas puntos")
print("  r cerca de -1  → VXN inverso: mas VXN = menos puntos")
print()

# ──────────────────────────────────────────────────────────────────────────────
# GRAFICA
# ──────────────────────────────────────────────────────────────────────────────
CYAN='#00f2ff'; GREEN='#00ff88'; RED='#ff3355'; YELLOW='#ffd60a'
WHITE='#e2e8f8'; GRAY='#4a5a7a'; PURPLE='#a78bfa'; ORANGE='#ff8c00'

PAT_COLORS = {
    'A — TRAMPA BAJISTA':    '#ff3355',
    'B — CONTINUACION LIMPIA': '#00ff88',
    'C — RANGO COMPLETO':    '#ffd60a',
    'D — ALCISTA CONTENIDO': '#00f2ff',
    'E — NEUTRAL->ALZA':     '#a78bfa',
    'OTRO':                  '#888888',
}

fig = plt.figure(figsize=(20, 22), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.55, wspace=0.40)

def ax_style(ax, title):
    ax.set_facecolor('#0d1628')
    ax.set_title(title, color=CYAN, fontsize=9.5, fontweight='bold', pad=10)
    ax.tick_params(colors=GRAY, labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

fig.suptitle('¿EL VXN EXPLICA LAS DIFERENCIAS ENTRE GRUPOS ALCISTAS?\n'
             'Martes NQ Sep2025-Mar2026 — 16 sesiones alcistas divididas en 4 patrones',
             color=WHITE, fontsize=13, fontweight='bold', y=0.995)

# ── P1: VXN por patron (barras) ───────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax_style(ax1, '1. VXN mediano de cada patron\n(¿tienen diferente VXN?)')
pats = [p for p in PAT_COLORS if p in alc['patron'].values]
vxn_meds = [alc[alc['patron']==p]['vxn'].median() for p in pats]
cols = [PAT_COLORS[p] for p in pats]
bars = ax1.bar(range(len(pats)), vxn_meds, color=cols, alpha=0.85, edgecolor='#1e2d4a')
ax1.set_xticks(range(len(pats)))
ax1.set_xticklabels([p.split('—')[0].strip() for p in pats], fontsize=8, color=GRAY, rotation=20, ha='right')
ax1.set_ylabel('VXN mediano', color=GRAY, fontsize=9)
ax1.axhline(alc['vxn'].median(), color=WHITE, linewidth=1.5, linestyle='--', alpha=0.7, label=f'VXN global={alc["vxn"].median():.1f}')
ax1.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
for i, (bar, v) in enumerate(zip(bars, vxn_meds)):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2, f'{v:.1f}', ha='center', va='bottom', fontsize=10, color=WHITE, fontweight='bold')

# ── P2: RANGO mediano por patron (barras) ─────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax_style(ax2, '2. RANGO mediano de cada patron\n(¿movieron diferente?)')
rng_meds = [alc[alc['patron']==p]['ny_range'].median() for p in pats]
bars2 = ax2.bar(range(len(pats)), rng_meds, color=cols, alpha=0.85, edgecolor='#1e2d4a')
ax2.set_xticks(range(len(pats)))
ax2.set_xticklabels([p.split('—')[0].strip() for p in pats], fontsize=8, color=GRAY, rotation=20, ha='right')
ax2.set_ylabel('Rango mediano (pts)', color=GRAY, fontsize=9)
ax2.axhline(alc['ny_range'].median(), color=WHITE, linewidth=1.5, linestyle='--', alpha=0.7, label=f'Rango global={alc["ny_range"].median():.0f}pts')
ax2.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
for bar, v in zip(bars2, rng_meds):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+3, f'{v:.0f}pts', ha='center', va='bottom', fontsize=10, color=WHITE, fontweight='bold')

# ── P3: Tabla resumen lado a lado ─────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax_style(ax3, '3. Resumen: VXN vs Rango vs Move\npor patron')
ax3.axis('off')
headers = ['Patron','N','VXN\nmed','Rango\nmed','Move\nmed']
rows3 = [headers]
for p in pats:
    g = alc[alc['patron']==p]
    rows3.append([p.split('—')[1].strip() if '—' in p else p,
                  str(len(g)),
                  f"{g['vxn'].median():.1f}",
                  f"{g['ny_range'].median():.0f}pts",
                  f"{g['ny_move_pts'].median():+.0f}pts"])
t3 = ax3.table(cellText=rows3[1:], colLabels=rows3[0], loc='center', cellLoc='center')
t3.auto_set_font_size(False); t3.set_fontsize(9); t3.scale(1, 2.2)
for (row, col), cell in t3.get_celld().items():
    cell.set_facecolor('#0a0f1e' if row==0 else '#0d1628')
    cell.set_edgecolor('#1e2d4a')
    txt = cell.get_text()
    if row == 0: txt.set_color(CYAN); txt.set_fontweight('bold')
    else:
        pat_name = rows3[row][0]
        # Buscar el patron completo
        full_pat = next((p for p in pats if pat_name in p), None)
        if col == 0: txt.set_color(PAT_COLORS.get(full_pat, GRAY) if full_pat else WHITE)
        else: txt.set_color(WHITE)

# ── P4: Scatter principal — VXN vs RANGO coloreado por patron ─────────────────
ax4 = fig.add_subplot(gs[1, :2])
ax_style(ax4, '4. LA PREGUNTA CENTRAL: VXN vs Rango — cada punto es un martes alcista\n¿Siguen una linea? → VXN lo explica   ¿Estan dispersos? → VXN NO lo explica')

for pat in pats:
    g = alc[alc['patron']==pat]
    col = PAT_COLORS[pat]
    ax4.scatter(g['vxn'], g['ny_range'], c=col, s=140, edgecolors=WHITE,
                linewidths=0.7, zorder=5, label=pat.split('—')[1].strip() if '—' in pat else pat, alpha=0.9)
    for _, r in g.iterrows():
        ax4.annotate(r['date'].strftime('%m/%d'), (r['vxn'], r['ny_range']),
                     fontsize=7, color=col, xytext=(4, 4), textcoords='offset points')

# Linea de tendencia global
from numpy.polynomial import polynomial as P
x_all = alc['vxn'].values
y_all = alc['ny_range'].values
idx = ~np.isnan(x_all) & ~np.isnan(y_all)
x_v, y_v = x_all[idx], y_all[idx]
m, b = np.polyfit(x_v, y_v, 1)
x_line = np.linspace(x_v.min(), x_v.max(), 100)
ax4.plot(x_line, m*x_line + b, color=WHITE, linewidth=2, linestyle='--', alpha=0.7,
         label=f'Tendencia global (r={corr_r:.2f})')

ax4.set_xlabel('VXN al momento del martes', color=GRAY, fontsize=10)
ax4.set_ylabel('Rango del dia (high - low, en puntos)', color=GRAY, fontsize=10)
ax4.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE, ncol=2)

# Texto de conclusion
veredicto = "SÍ lo explica parcialmente" if abs(corr_r) > 0.4 else "NO lo explica bien" if abs(corr_r) < 0.25 else "Explica algo pero no todo"
ax4.text(0.02, 0.97,
    f'Correlacion VXN vs Rango: r = {corr_r:.3f}\n'
    f'→ VXN {veredicto}\n'
    f'(r=0 = sin relacion, r=1 = relacion perfecta)',
    transform=ax4.transAxes, ha='left', va='top', fontsize=10,
    color=YELLOW if abs(corr_r) < 0.4 else GREEN,
    bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.95, boxstyle='round,pad=0.5'))

# ── P5: VXN promedio de cada CASO individual (barras horizontales) ─────────────
ax5 = fig.add_subplot(gs[1, 2])
ax_style(ax5, '5. VXN vs Move — cada caso\n¿Mas VXN = mas movimiento?')
for pat in pats:
    g = alc[alc['patron']==pat]
    col = PAT_COLORS[pat]
    ax5.scatter(g['vxn'], g['ny_move_pts'], c=col, s=100, edgecolors=WHITE,
                linewidths=0.6, zorder=5, alpha=0.9)
    for _, r in g.iterrows():
        ax5.annotate(r['date'].strftime('%m/%d'), (r['vxn'], r['ny_move_pts']),
                     fontsize=6.5, color=col, xytext=(3,3), textcoords='offset points')

m2, b2 = np.polyfit(x_v, alc.loc[alc['vxn'].notna(), 'ny_move_pts'].values, 1)
ax5.plot(x_line, m2*x_line + b2, color=WHITE, linewidth=1.5, linestyle='--', alpha=0.6,
         label=f'Tendencia (r={corr_r2:.2f})')
ax5.set_xlabel('VXN', color=GRAY, fontsize=8)
ax5.set_ylabel('Move NY (puntos)', color=GRAY, fontsize=8)
ax5.legend(fontsize=7.5, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# ── P6: Panel de CONCLUSION visual ────────────────────────────────────────────
ax6 = fig.add_subplot(gs[2, :])
ax_style(ax6, '6. CONCLUSION: ¿Que explica la diferencia de movimiento entre grupos?')
ax6.axis('off')

# Tabla comparativa VXN vs Rango dentro de cada patron
concl_data = []
for p in pats:
    g = alc[alc['patron']==p]
    vxn_m = g['vxn'].median()
    rng_m = g['ny_range'].median()
    mov_m = g['ny_move_pts'].median()
    # Si el VXN fuera la causa, el patron con mas VXN deberia tener mas rango
    concl_data.append({'patron': p, 'n': len(g), 'vxn': vxn_m, 'rango': rng_m, 'move': mov_m})

cdf = pd.DataFrame(concl_data).sort_values('vxn', ascending=False)

# Chequeamos: ¿la ordenacion por VXN coincide con la ordenacion por rango?
rango_orden = sorted(pats, key=lambda p: alc[alc['patron']==p]['ny_range'].median(), reverse=True)
vxn_orden   = sorted(pats, key=lambda p: alc[alc['patron']==p]['vxn'].median(), reverse=True)

coincide = rango_orden == vxn_orden

# Texto de explicacion
lines = [
    f"PREGUNTA: ¿Los grupos alcistas que movieron MAS puntos tenian VXN MAS ALTO?",
    "",
    f"Orden por RANGO (mayor a menor):  {' → '.join([p.split('—')[1].strip()[:15] if '—' in p else p[:15] for p in rango_orden])}",
    f"Orden por VXN   (mayor a menor):  {' → '.join([p.split('—')[1].strip()[:15] if '—' in p else p[:15] for p in vxn_orden])}",
    "",
    f"¿Las ordenes coinciden?: {'SI — el VXN explica las diferencias de tamaño' if coincide else 'NO — el orden es diferente'}",
    "",
]

if not coincide:
    lines.append("→ CONCLUSION: El VXN NO es lo que diferencia el tamaño de movimiento entre grupos.")
    lines.append("  El patron de comportamiento (Tipo A/B/C) es lo que determina cuanto mueve cada grupo,")
    lines.append("  NO el nivel de VXN que tenian ese dia.")
    lines.append("")
    lines.append("  Ejemplo: el Grupo B movio +160pts con VXN=21, y el Grupo C movio similar con VXN=22.")
    lines.append("  Si el VXN fuera el causante, el grupo con mas VXN deberia mover mas — pero no es así.")
else:
    lines.append("→ CONCLUSION: El VXN SÍ coincide con los grupos que mas movieron.")
    lines.append("  Pero eso puede ser coincidencia — necesitamos mas datos para confirmarlo.")

lines.append("")
lines.append(f"  Correlacion VXN vs Rango (r={corr_r:.3f}): {'fuerte' if abs(corr_r) > 0.5 else 'debil o moderada' if abs(corr_r) > 0.3 else 'muy debil / casi nula'}")
lines.append(f"  El VXN explica aprox. el {corr_r**2*100:.0f}% de la variacion en el rango del dia")

ax6.text(0.01, 0.97, '\n'.join(lines), transform=ax6.transAxes,
         ha='left', va='top', fontsize=10.5, color=WHITE, fontfamily='monospace',
         bbox=dict(facecolor='#0d1628', edgecolor=CYAN, alpha=0.95, boxstyle='round,pad=0.6'))

# Añadir los números claves en color
for i, p in enumerate(pats):
    g = alc[alc['patron']==p]
    col = PAT_COLORS[p]
    txt = (f"{p.split('—')[1].strip() if '—' in p else p} (n={len(g)}): "
           f"VXN={g['vxn'].median():.1f} → Rango={g['ny_range'].median():.0f}pts → Move ={g['ny_move_pts'].median():+.0f}pts")
    ax6.text(0.01, 0.42 - i*0.09, txt, transform=ax6.transAxes,
             ha='left', va='top', fontsize=10, color=col, fontfamily='monospace', fontweight='bold')

out = os.path.join(BASE, 'martes_vxn_explica_grupos.png')
plt.savefig(out, dpi=135, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] -> {out}")
print(f"\nCorrelacion r={corr_r:.3f} | R²={corr_r**2*100:.0f}%")
if coincide:
    print("Los ordenes de VXN y Rango COINCIDEN")
else:
    print("Los ordenes de VXN y Rango NO coinciden — VXN no explica las diferencias entre grupos")
