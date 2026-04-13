# -*- coding: utf-8 -*-
"""
CLUSTER DE LOS 16 MARTES ALCISTAS — Sep2025-Mar2026
=====================================================
Agrupa los martes alcistas por similitud de patron:
- PM direction
- Apertura vs VA
- Si barrió VAL antes de subir
- VXN nivel
- Toques de niveles
- Tamaño del move
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Cargar datos ─────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(BASE, 'ny_profile_asia_london_daily.csv'))
df['date'] = pd.to_datetime(df['date'])
mar = df[df['weekday'] == 'MARTES'].copy().reset_index(drop=True)
mar['ny_move_pts'] = mar['pm_close'] - mar['ny_open_price']
mar['ny_range']    = mar['pm_hi'] - mar['pm_lo']
mar['alcista']     = mar['pm_close'] > mar['ny_open_price']

# Lunes previo
lun = df[df['weekday'] == 'LUNES'].copy()
lun_dict = {row['date']: row for _, row in lun.iterrows()}
def get_lun_pm(fecha):
    fecha_lun = fecha - pd.Timedelta(days=1)
    if fecha_lun in lun_dict:
        lr = lun_dict[fecha_lun]
        return float(lr['pm_close']) - float(lr['pm_open'])
    return None
mar['move_lunes'] = mar['date'].apply(get_lun_pm)

# ── Solo los 16 ALCISTAS ──────────────────────────────────────────────────────
alc = mar[mar['alcista']].copy().reset_index(drop=True)
n = len(alc)
print(f"Total alcistas: {n}\n")

# ── DEFINICION MANUAL DE CLUSTERS / PATRONES ─────────────────────────────────
# Basandonos en las variables clave:
#   1. PM direction (BULL/BEAR/NEUTRAL)
#   2. Si barrió VAL primero (breaks_val=True → barrió abajo, luego subió)
#   3. VXN nivel (<22 vs >22)
#   4. Tamaño del move (grande >200pts vs normal)

def clasificar(r):
    pm  = r['pm_direction']
    bv  = bool(r['breaks_val'])    # bajo VAL primero antes de subir
    bvh = bool(r['breaks_vah'])    # rompió VAH
    vxn = float(r['vxn']) if pd.notna(r['vxn']) else 20
    mov = abs(float(r['ny_move_pts']))
    rng = float(r['ny_range'])
    mon = r['move_lunes'] if pd.notna(r.get('move_lunes')) else 0

    # PATRON A: PM Bearish, barre VAL primero, luego explota al VAH+
    # = La "trampa bajista" — el mercado hace creer que cae, engancha vendedores
    if pm in ['BEARISH'] and bv and bvh and mov > 100:
        return 'A — TRAMPA BAJISTA\n(PM BEAR → sweep VAL → explota VAH+)'

    # PATRON B: PM Bullish, directo al VAH, sin tocar VAL
    # = La "continuacion alcista limpia"
    if pm in ['BULLISH'] and not bv and bvh and mov > 80:
        return 'B — CONTINUACION ALCISTA\n(PM BULL → directo al VAH)'

    # PATRON C: PM Bullish pero toca VAL también (rango amplio, dos caras)
    if pm in ['BULLISH'] and bv and bvh:
        return 'C — RANGO COMPLETO ALCISTA\n(PM BULL → toca VAL Y VAH)'

    # PATRON D: No rompe VAH pero cierra encima/adentro
    if not bvh and mov > 0:
        return 'D — ALCISTA CONTENIDO\n(Sube pero no rompe VAH)'

    # PATRON E: Neutral PM, sube igualmente
    if pm in ['NEUTRAL'] and mov > 0:
        return 'E — NEUTRAL→ALCISTA\n(PM sin dir. pero sube)'

    return 'OTRO'

alc['patron'] = alc.apply(clasificar, axis=1)

print("=== PATRONES ENCONTRADOS ===\n")
for pat, grupo in alc.groupby('patron'):
    print(f"\n{'='*55}")
    print(f"  PATRON: {pat}")
    print(f"  N casos: {len(grupo)}")
    print(f"  Move promedio:  {grupo['ny_move_pts'].mean():.0f}pts")
    print(f"  Move mediano:   {grupo['ny_move_pts'].median():.0f}pts")
    print(f"  Rango promedio: {grupo['ny_range'].mean():.0f}pts")
    print(f"  VXN promedio:   {grupo['vxn'].mean():.1f}")
    print(f"  Lunes previo:   {grupo['move_lunes'].mean():.0f}pts" if grupo['move_lunes'].notna().any() else "")
    print(f"\n  Fechas:")
    for _, r in grupo.iterrows():
        tval = "barrio VAL" if r['breaks_val'] else "no toco VAL"
        print(f"    {r['date'].date()}  PM={r['pm_direction']:7s}  VXN={r['vxn']:.1f}  "
              f"move={r['ny_move_pts']:+6.0f}pts  rng={r['ny_range']:.0f}  {tval}")

# ══════════════════════════════════════════════════════════════════════════════
# GRAFICA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════
CYAN=  '#00f2ff'; GREEN= '#00ff88'; RED=   '#ff3355'
YELLOW='#ffd60a'; WHITE= '#e2e8f8'; GRAY=  '#4a5a7a'; PURPLE='#a78bfa'
ORANGE='#ff8c00'; PINK  ='#ff79c6'

PAT_COLORS = {
    'A — TRAMPA BAJISTA\n(PM BEAR → sweep VAL → explota VAH+)':  '#ff3355',
    'B — CONTINUACION ALCISTA\n(PM BULL → directo al VAH)':       '#00ff88',
    'C — RANGO COMPLETO ALCISTA\n(PM BULL → toca VAL Y VAH)':     '#ffd60a',
    'D — ALCISTA CONTENIDO\n(Sube pero no rompe VAH)':            '#00f2ff',
    'E — NEUTRAL→ALCISTA\n(PM sin dir. pero sube)':               '#a78bfa',
    'OTRO': '#888888',
}
PAT_SHORT = {
    'A — TRAMPA BAJISTA\n(PM BEAR → sweep VAL → explota VAH+)':  'A — TRAMPA BAJISTA',
    'B — CONTINUACION ALCISTA\n(PM BULL → directo al VAH)':       'B — CONTINUACION ALCISTA',
    'C — RANGO COMPLETO ALCISTA\n(PM BULL → toca VAL Y VAH)':     'C — RANGO COMPLETO',
    'D — ALCISTA CONTENIDO\n(Sube pero no rompe VAH)':            'D — ALCISTA CONTENIDO',
    'E — NEUTRAL→ALCISTA\n(PM sin dir. pero sube)':               'E — NEUTRAL→ALCISTA',
    'OTRO': 'OTRO',
}

fig = plt.figure(figsize=(22, 28), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(5, 3, figure=fig, hspace=0.65, wspace=0.40)

def ax_style(ax, title):
    ax.set_facecolor('#0d1628')
    ax.set_title(title, color=CYAN, fontsize=10, fontweight='bold', pad=10)
    ax.tick_params(colors=GRAY, labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

fig.suptitle(f'CLUSTERS DE LOS {n} MARTES ALCISTAS — Sep2025 a Mar2026\n'
             f'Agrupados por patron de comportamiento',
             color=WHITE, fontsize=14, fontweight='bold', y=0.995)

# ── Panel overview de patrones ───────────────────────────────────────────────
ax0 = fig.add_subplot(gs[0,:])
ax_style(ax0, 'OVERVIEW — Patrones de martes alcistas por fecha (cronologico)')
ax0.set_facecolor('#0d1628')

for i, (_, r) in enumerate(alc.iterrows()):
    pat = r['patron']
    col = PAT_COLORS.get(pat, GRAY)
    move = r['ny_move_pts']
    rng  = r['ny_range']
    fecha= r['date']

    # Barra del rango
    ax0.bar(i, rng, color=col, alpha=0.55, edgecolor='#1e2d4a', width=0.8)
    # Linea del move
    ax0.bar(i, move, color=col, alpha=0.95, width=0.5)
    # Texto
    ax0.text(i, rng + 8, r['date'].strftime('%m/%d'), ha='center', va='bottom',
             fontsize=6.5, color=col, rotation=45)
    ax0.text(i, move/2 if move > 20 else 8, f'+{move:.0f}', ha='center', va='center',
             fontsize=6, color=WHITE, fontweight='bold')

ax0.axhline(0, color=GRAY, linewidth=0.5)
# Leyenda
ax0.set_xticks(range(n))
ax0.set_xticklabels([''] * n)
ax0.set_ylabel('Puntos', color=GRAY, fontsize=9)

legend_handles = [mpatches.Patch(facecolor=v, alpha=0.85, label=PAT_SHORT[k])
                  for k, v in PAT_COLORS.items() if k != 'OTRO' and any(alc['patron']==k)]
ax0.legend(handles=legend_handles, fontsize=8, facecolor='#0d1628',
           edgecolor=GRAY, labelcolor=WHITE, loc='upper left', ncol=2)
ax0.text(0.99, 0.97, 'Barra opaca = rango total\nBarra brillante = move NY\n(close-open)',
         transform=ax0.transAxes, ha='right', va='top', fontsize=7.5, color=GRAY,
         style='italic')

# ── Un panel por patron ───────────────────────────────────────────────────────
patrones_uniq = [p for p in PAT_COLORS if p in alc['patron'].values]
panel_positions = [(1,0),(1,1),(1,2),(2,0),(2,1)]

for idx, patron in enumerate(patrones_uniq[:5]):
    ax = fig.add_subplot(gs[panel_positions[idx]])
    grupo = alc[alc['patron'] == patron].copy()
    col   = PAT_COLORS[patron]
    short = PAT_SHORT[patron]
    ax_style(ax, f'{short}\n(n={len(grupo)} casos)')

    # Scatter VXN vs Move
    sc = ax.scatter(grupo['vxn'], grupo['ny_move_pts'],
                    c=col, alpha=0.9, s=120, edgecolors=WHITE, linewidths=0.5, zorder=5)

    # Etiquetas de fecha
    for _, r in grupo.iterrows():
        ax.annotate(r['date'].strftime('%m/%d/%y'),
                    (r['vxn'], r['ny_move_pts']),
                    fontsize=7, color=WHITE,
                    xytext=(5, 5), textcoords='offset points')

    ax.axhline(grupo['ny_move_pts'].mean(), color=col, linewidth=1.5, linestyle='--',
               alpha=0.7, label=f'Media {grupo["ny_move_pts"].mean():.0f}pts')
    ax.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
    ax.set_xlabel('VXN', color=GRAY, fontsize=8)
    ax.set_ylabel('Move NY (pts)', color=GRAY, fontsize=8)
    ax.set_facecolor('#0a0f1e' + '22')

    # Estadisticas en el panel
    txt = (f'Move med:  {grupo["ny_move_pts"].median():+.0f}pts\n'
           f'Rango med: {grupo["ny_range"].median():.0f}pts\n'
           f'VXN med:   {grupo["vxn"].mean():.1f}\n'
           f'Barrio VAL: {int(grupo["breaks_val"].astype(bool).sum())}/{len(grupo)}\n'
           f'Rompio VAH: {int(grupo["breaks_vah"].astype(bool).sum())}/{len(grupo)}')
    ax.text(0.97, 0.03, txt, transform=ax.transAxes, ha='right', va='bottom',
            fontsize=8, color=WHITE, fontfamily='monospace',
            bbox=dict(facecolor='#0a0f1e', edgecolor=col, alpha=0.9, boxstyle='round,pad=0.4'))

# ── Panel: Comparacion de medias entre patrones ────────────────────────────────
ax_comp = fig.add_subplot(gs[3,:])
ax_style(ax_comp, 'COMPARACION ENTRE PATRONES — Move promedio vs Rango promedio')
ax_comp.set_facecolor('#0d1628')

pats_list  = [p for p in PAT_COLORS if p in alc['patron'].values and p != 'OTRO']
moves_med  = [alc[alc['patron']==p]['ny_move_pts'].median() for p in pats_list]
ranges_med = [alc[alc['patron']==p]['ny_range'].median() for p in pats_list]
ns         = [len(alc[alc['patron']==p]) for p in pats_list]
cols_comp  = [PAT_COLORS[p] for p in pats_list]
x_comp = np.arange(len(pats_list))
w = 0.38

bars_m = ax_comp.bar(x_comp - w/2, moves_med,  w, color=cols_comp, alpha=0.9, label='Move mediano')
bars_r = ax_comp.bar(x_comp + w/2, ranges_med, w, color=cols_comp, alpha=0.45, label='Rango mediano', linewidth=2, edgecolor=cols_comp)

ax_comp.set_xticks(x_comp)
ax_comp.set_xticklabels([PAT_SHORT[p] for p in pats_list], fontsize=7.5, color=GRAY, wrap=True)
ax_comp.set_ylabel('Puntos (pts)', color=GRAY, fontsize=9)
ax_comp.axhline(0, color=GRAY, linewidth=0.5)

for bar, mv, rng, n_v in zip(bars_m, moves_med, ranges_med, ns):
    ax_comp.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
                 f'+{mv:.0f}pts\nn={n_v}', ha='center', va='bottom', fontsize=8.5, color=WHITE, fontweight='bold')

from matplotlib.patches import Patch
ax_comp.legend(handles=[
    Patch(facecolor=GRAY, alpha=0.9, label='Move NY mediano (close-open)'),
    Patch(facecolor=GRAY, alpha=0.4, label='Rango mediano (high-low)')
], fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# ── Panel: Tabla detallada ────────────────────────────────────────────────────
ax_tab = fig.add_subplot(gs[4,:])
ax_style(ax_tab, 'TABLA DETALLADA — Los 16 martes alcistas ordenados por patron')
ax_tab.axis('off')

headers = ['Fecha','Patron','PM Dir','VXN','Barrio VAL','Rompio VAH','Cierre','Move NY','Rango','Lunes previo']
rows = [headers]
for pat in pats_list + ['OTRO']:
    for _, r in alc[alc['patron']==pat].sort_values('date').iterrows():
        lun_str = f"{r['move_lunes']:+.0f}pts" if pd.notna(r.get('move_lunes')) else '-'
        cierre = 'ENCIMA' if r['close_above_va'] else ('BAJO' if r['close_below_va'] else 'DENTRO')
        rows.append([
            r['date'].strftime('%Y-%m-%d'),
            PAT_SHORT[r['patron']],
            r['pm_direction'],
            f"{r['vxn']:.1f}",
            'SI' if r['breaks_val'] else 'no',
            'SI' if r['breaks_vah'] else 'no',
            cierre,
            f"+{r['ny_move_pts']:.0f}pts",
            f"{r['ny_range']:.0f}pts",
            lun_str,
        ])

t = ax_tab.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.65)

for (row, col), cell in t.get_celld().items():
    cell.set_facecolor('#0a0f1e' if row == 0 else ('#0d1628' if row % 2 == 0 else '#0f1c30'))
    cell.set_edgecolor('#1e2d4a')
    txt = cell.get_text()
    if row == 0:
        txt.set_color(CYAN); txt.set_fontweight('bold'); txt.set_fontsize(8.5)
    else:
        v = rows[row][col]
        pat_raw = rows[row][1]
        c = [k for k, s in PAT_SHORT.items() if s == pat_raw]
        row_col = PAT_COLORS.get(c[0], GRAY) if c else GRAY
        if col == 1: txt.set_color(row_col); txt.set_fontweight('bold')
        elif v == 'SI': txt.set_color(GREEN); txt.set_fontweight('bold')
        elif v == 'no': txt.set_color(GRAY)
        elif v == 'ENCIMA': txt.set_color(GREEN)
        elif v == 'BAJO': txt.set_color(RED)
        elif '+' in str(v) and 'pts' in str(v): txt.set_color(GREEN); txt.set_fontweight('bold')
        else: txt.set_color(WHITE)

out = os.path.join(BASE, 'martes_clusters_alcistas.png')
plt.savefig(out, dpi=135, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] -> {out}")

# ── Resumen ejecutivo de cada patron ──────────────────────────────────────────
print("\n" + "="*60)
print("RECETA DE CADA PATRON")
print("="*60)

recetas = {
    'A — TRAMPA BAJISTA': [
        "El pre-market baja (BEAR)",
        "Al abrir NY, el precio barrio por debajo del VAL",
        "Luego explota hacia arriba, rompiendo VAH",
        "IDEA: esperar que barre VAL, confirmacion de rechazo, entrar LONG",
        "Target: VAH + extension",
    ],
    'B — CONTINUACION ALCISTA': [
        "El pre-market sube (BULL)",
        "Abre NY y va DIRECTO al VAH — no toca VAL",
        "Rompe VAH y cierra encima",
        "IDEA: si PM es BULL y el precio aguanta arriba del POC al abrir NY",
        "Entrar LONG en pullback al POC o VAH convertido en soporte",
    ],
    'C — RANGO COMPLETO': [
        "PM BULL pero el dia tiene los dos lados",
        "Toca VAL Y rompe VAH — rango amplio",
        "IDEA: mas dificil — el mercado engana antes de decidir",
        "Requiere confirmacion antes de entrar",
    ],
    'D — ALCISTA CONTENIDO': [
        "Sube pero no llega a romper VAH",
        "Cierra dentro o en el borde del VA",
        "IDEA: scalp inside VA — no tiene fuerza para extension",
    ],
}

for pat, lineas in recetas.items():
    hay = [k for k, s in PAT_SHORT.items() if s == pat and k in pats_list]
    if not hay: continue
    grupo = alc[alc['patron'] == hay[0]]
    print(f"\n{pat} (n={len(grupo)}):")
    for l in lineas: print(f"  - {l}")
