"""
ATLAS VISUAL: Pre-Market vs NY Session — 27 Martes NQ (Sep2025-Mar2026)
Crea gráficas detalladas con velas reales de cada martes mostrando:
- Vela Pre-Market (PM open/hi/lo/close)
- Niveles del Value Area (VAL / POC / VAH)
- Barra NY Session (prof_hi / prof_lo / ny_move)
- Labels de dirección, VXN, patrón
"""

import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.ticker as mticker
import numpy as np
from datetime import datetime

# ─── COLORES ────────────────────────────────────────────────────
BG        = '#070d1a'
CARD_BG   = '#0b1323'
CARD_BRD  = '#1a2540'
BULL_C    = '#00ff88'
BEAR_C    = '#ff3355'
NEUT_C    = '#ffd60a'
VA_LINE   = '#00f2ff'
POC_LINE  = '#ffd60a'
PM_BODY_B = '#00ff88'
PM_BODY_R = '#ff3355'
PM_BODY_N = '#ffd60a'
NY_BODY_B = '#00d4aa'
NY_BODY_R = '#ff6688'
WICK_C    = '#8899cc'
GRID_C    = '#1a2540'
TXT_MUT   = '#64748b'
TXT_MAIN  = '#e2e8f0'

# ─── CLASIFICACION DE PATRON ─────────────────────────────────────
def classify(row):
    pm_dir = row['pm_direction']
    ny_move = float(row.get('ny_move_pts', 0) or 0)
    breaks_vah = row.get('breaks_vah', '0')
    breaks_val = row.get('breaks_val', '0')
    
    if ny_move > 0:  # Alcista
        if pm_dir == 'BEARISH':
            return 'A', 'TRAMPA BAJISTA', '#ff3355'
        elif pm_dir == 'BULLISH':
            touches_val = str(row.get('touches_val', '0')).strip()
            if touches_val in ('1', 'True', 'true'):
                return 'C', 'RANGO COMPLETO', '#ffd60a'
            else:
                return 'B', 'CONTINUACIÓN', '#00ff88'
        else:
            return 'D', 'ALCISTA CONT.', '#00f2ff'
    else:  # Bajista / plano
        if pm_dir == 'BULLISH':
            return 'X', 'FALLO BULL PM', '#ff8c00'
        else:
            return 'E', 'BAJISTA', '#ff3355'

# ─── CARGAR DATA ─────────────────────────────────────────────────
with open('ny_profile_asia_london_daily.csv', newline='', encoding='utf-8') as f:
    rows = [r for r in csv.DictReader(f) if r['weekday'] == 'MARTES']

# Cargar ny_move_pts desde ny_profile_asia_london_daily (lo calculamos)
records = []
for r in rows:
    try:
        pm_o  = float(r['pm_open'])
        pm_h  = float(r['pm_hi'])
        pm_l  = float(r['pm_lo'])
        pm_c  = float(r['pm_close'])
        ny_o  = float(r['ny_open_price'])
        prof_h = float(r['prof_hi'])
        prof_l = float(r['prof_lo'])
        val   = float(r['val'])
        poc   = float(r['poc'])
        vah   = float(r['vah'])
        vxn   = float(r['vxn']) if r.get('vxn') else 22.0
        pm_range = pm_h - pm_l
        pm_dir = r['pm_direction']

        # NY abre en pm_close, cierra en prof_hi si alcista o prof_lo si bajista
        # Estimamos el cierre NY como el nivel más alejado del prof (hi o lo)
        ny_move_hi = prof_h - ny_o  # cuanto subió desde apertura
        ny_move_lo = ny_o - prof_l  # cuanto bajó desde apertura
        # El cierre NY del día es el prof_hi si alcista (ny_move > 0) o prof_lo
        # Para simplificar, tomamos la diferencia neta de la sesión
        # Usamos la tabla previa de la investigación
        
        # Calcular ny_move: comparar ny_open vs final (usamos prof_hi-prof_lo como rango,
        # y pm_close → dirección indica cierre)
        if pm_dir == 'BULLISH':
            ny_close_est = prof_h  # sesión alcista: cerró cerca del hi
        elif pm_dir == 'BEARISH':
            ny_close_est = prof_l  # sesión bajista: cerró cerca del lo
        else:
            ny_close_est = (prof_h + prof_l) / 2

        ny_move = ny_close_est - ny_o
        r['ny_move_pts'] = ny_move
        r['ny_close_est'] = ny_close_est
        r['pm_o']  = pm_o
        r['pm_h']  = pm_h
        r['pm_l']  = pm_l
        r['pm_c']  = pm_c
        r['ny_o']  = ny_o
        r['prof_h']= prof_h
        r['prof_l']= prof_l
        r['val_f'] = val
        r['poc_f'] = poc
        r['vah_f'] = vah
        r['vxn_f'] = vxn
        r['pr']    = pm_range
        records.append(r)
    except (ValueError, KeyError) as e:
        continue

# Usar los valores reales de la investigación (sobrescribo ny_move con los conocidos)
REAL_NY = {
    '2025-09-16': +171, '2025-09-23': -179, '2025-09-30': +64,
    '2025-10-07': -209, '2025-10-14': +137, '2025-10-21': -7,
    '2025-10-28': +148, '2025-11-04': -136, '2025-11-11': +50,
    '2025-11-18': -149, '2025-11-25': +196, '2025-12-02': +93,
    '2025-12-09': +87,  '2025-12-16': -120, '2025-12-23': +190,
    '2025-12-30': -37,  '2026-01-06': +218, '2026-01-13': -66,
    '2026-01-20': -70,  '2026-01-27': +85,  '2026-02-03': -521,
    '2026-02-10': -154, '2026-02-17': +164, '2026-02-24': +153,
    '2026-03-03': +260, '2026-03-10': +16,  '2026-03-17': +78,
}
REAL_PM = {
    '2025-09-16': -14,  '2025-09-23': -114, '2025-09-30': +55,
    '2025-10-07': -141, '2025-10-14': +66,  '2025-10-21': -6,
    '2025-10-28': +124, '2025-11-04': -210, '2025-11-11': +134,
    '2025-11-18': +124, '2025-11-25': +262, '2025-12-02': -48,
    '2025-12-09': +20,  '2025-12-16': -189, '2025-12-23': +80,
    '2025-12-30': -67,  '2026-01-06': +148, '2026-01-13': +9,
    '2026-01-20': -222, '2026-01-27': -3,   '2026-02-03': -171,
    '2026-02-10': -156, '2026-02-17': +178, '2026-02-24': +53,
    '2026-03-03': +309, '2026-03-10': -165, '2026-03-17': -66,
}
REAL_RANGES = {
    '2025-09-16': 305, '2025-09-23': 189, '2025-09-30': 182,
    '2025-10-07': 207, '2025-10-14': 263, '2025-10-21': 106,
    '2025-10-28': 226, '2025-11-04': 279, '2025-11-11': 218,
    '2025-11-18': 430, '2025-11-25': 362, '2025-12-02': 249,
    '2025-12-09': 68,  '2025-12-16': 510, '2025-12-23': 94,
    '2025-12-30': 126, '2026-01-06': 192, '2026-01-13': 222,
    '2026-01-20': 332, '2026-01-27': 76,  '2026-02-03': 401,
    '2026-02-10': 202, '2026-02-17': 296, '2026-02-24': 110,
    '2026-03-03': 414, '2026-03-10': 277, '2026-03-17': 143,
}

for r in records:
    d = r['date']
    if d in REAL_NY:
        r['ny_move_pts'] = REAL_NY[d]
    if d in REAL_PM:
        r['pm_move_real'] = REAL_PM[d]
    r['ny_range_real'] = REAL_RANGES.get(d, abs(r['prof_h'] - r['prof_l']))

print(f"Total martes cargados: {len(records)}")

# ─── DIBUJAR ATLAS (grid 5x6 = 30 slots) ────────────────────────
COLS = 5
ROWS = 6
FIG_W = 28
FIG_H = 34

fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)
fig.patch.set_facecolor(BG)

# Título principal
fig.text(0.5, 0.985, '📊 ATLAS PRE-MARKET · 27 MARTES NQ (Sep2025 – Mar2026)',
         ha='center', va='top', fontsize=20, fontweight='900',
         color='#00f2ff', fontfamily='monospace',
         fontstyle='normal')
fig.text(0.5, 0.976,
         'Cada panel: vela PM real · niveles VA · barra sesión NY · dirección · VXN',
         ha='center', va='top', fontsize=11, color='#64748b', fontfamily='monospace')

# Leyenda global
handles = [
    plt.Rectangle((0,0),1,1, color=BULL_C,  label='PM BULL'),
    plt.Rectangle((0,0),1,1, color=BEAR_C,  label='PM BEAR'),
    plt.Rectangle((0,0),1,1, color=NEUT_C,  label='PM NEUTRAL'),
    plt.Rectangle((0,0),1,1, color=VA_LINE, label='VAH/VAL'),
    plt.Rectangle((0,0),1,1, color=POC_LINE,label='POC'),
]
fig.legend(handles=handles, loc='upper right', ncol=5,
           framealpha=0, labelcolor='white', fontsize=9,
           bbox_to_anchor=(0.98, 0.984))

# Grid de subplots
axes = fig.subplots(ROWS, COLS)
axes_flat = [axes[r][c] for r in range(ROWS) for c in range(COLS)]

for i, ax in enumerate(axes_flat):
    ax.set_facecolor(CARD_BG)
    for spine in ax.spines.values():
        spine.set_color(CARD_BRD)
        spine.set_linewidth(0.8)

    if i >= len(records):
        ax.set_visible(False)
        continue

    rec = records[i]
    date_str = rec['date']
    date_dt  = datetime.strptime(date_str, '%Y-%m-%d')
    date_lbl = date_dt.strftime('%d-%b\n%Y')

    pm_dir   = rec['pm_direction']
    pm_o     = rec['pm_o']
    pm_h     = rec['pm_h']
    pm_l     = rec['pm_l']
    pm_c     = rec['pm_c']
    ny_o     = rec['ny_o']
    prof_h   = rec['prof_h']
    prof_l   = rec['prof_l']
    val      = rec['val_f']
    poc      = rec['poc_f']
    vah      = rec['vah_f']
    vxn      = rec['vxn_f']
    ny_move  = float(rec.get('ny_move_pts', 0) or 0)
    pm_move  = float(rec.get('pm_move_real', pm_c - pm_o))
    ny_range = rec.get('ny_range_real', 0)

    # Estimar cierre NY desde ny_open + ny_move
    ny_close = ny_o + ny_move

    pat_id, pat_name, pat_color = classify(rec)

    # ── Zoom del precio ──────────────────────────────────────────
    all_prices = [pm_o, pm_h, pm_l, pm_c, ny_o, prof_h, prof_l, val, poc, vah]
    price_min  = min(all_prices) - 30
    price_max  = max(all_prices) + 30
    price_range = price_max - price_min or 100

    ax.set_xlim(0, 3.5)
    ax.set_ylim(price_min, price_max)
    ax.set_xticks([])
    ax.yaxis.set_major_locator(mticker.MaxNLocator(4))
    ax.tick_params(axis='y', labelsize=6, colors='#64748b', pad=1)
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()
    ax.grid(axis='y', color=GRID_C, linewidth=0.5, linestyle='--', alpha=0.5)

    # ── Colores según dirección PM ──────────────────────────────
    if pm_dir == 'BULLISH':
        pm_body_col = PM_BODY_B
        pm_body_alpha = 0.85
    elif pm_dir == 'BEARISH':
        pm_body_col = PM_BODY_R
        pm_body_alpha = 0.85
    else:
        pm_body_col = PM_BODY_N
        pm_body_alpha = 0.85

    NY_col = BULL_C if ny_move > 0 else BEAR_C

    # ── Líneas VA ──────────────────────────────────────────────
    for level, color, ls, lw, lbl in [
        (vah, VA_LINE, '--', 1.0, 'VAH'),
        (val, VA_LINE, '--', 1.0, 'VAL'),
        (poc, POC_LINE, '-',  0.8, 'POC'),
    ]:
        ax.axhline(level, color=color, linewidth=lw, linestyle=ls, alpha=0.6, zorder=1)
        ax.text(0.03, level, lbl, fontsize=5.5, color=color, va='center',
                fontfamily='monospace', fontweight='bold', zorder=5, alpha=0.8)

    # ── Vela PM (x=0.8, ancho=0.6) ───────────────────────────
    pm_x  = 0.8
    pm_w  = 0.6
    pm_bot = min(pm_o, pm_c)
    pm_top = max(pm_o, pm_c)
    pm_body_h = max(pm_top - pm_bot, 4)  # min 4pts visible

    # Mecha
    ax.plot([pm_x, pm_x], [pm_l, pm_bot], color=WICK_C, lw=0.8, zorder=2)
    ax.plot([pm_x, pm_x], [pm_top, pm_h], color=WICK_C, lw=0.8, zorder=2)
    # Cuerpo
    rect_pm = plt.Rectangle((pm_x - pm_w/2, pm_bot), pm_w, pm_body_h,
                              facecolor=pm_body_col, edgecolor=pm_body_col,
                              alpha=pm_body_alpha, zorder=3)
    ax.add_patch(rect_pm)
    # Label PM move
    pm_move_lbl = f'+{int(abs(pm_move))}' if pm_move >= 0 else f'-{int(abs(pm_move))}'
    ax.text(pm_x, pm_h + price_range * 0.03, pm_move_lbl,
            ha='center', va='bottom', fontsize=6.5, color=pm_body_col,
            fontfamily='monospace', fontweight='bold', zorder=5)
    ax.text(pm_x, pm_l - price_range * 0.04, 'PM',
            ha='center', va='top', fontsize=5.5, color='#64748b',
            fontfamily='monospace', zorder=5)

    # ── Línea de apertura NY (conectar PM close → NY) ─────────
    ny_x = 2.2
    ax.annotate('', xy=(ny_x - 0.3, ny_o), xytext=(pm_x + pm_w/2, pm_c),
                arrowprops=dict(arrowstyle='->', color='#4a5568', lw=0.7),
                zorder=4)

    # ── Barra NY Session (x=2.2, ancho=0.6) ──────────────────
    ny_w   = 0.6
    ny_bot = min(ny_o, ny_close)
    ny_top = max(ny_o, ny_close)
    ny_body_h = max(ny_top - ny_bot, 4)

    # Meecha NY (rango completo)
    ax.plot([ny_x, ny_x], [prof_l, ny_bot], color=WICK_C, lw=0.8, zorder=2)
    ax.plot([ny_x, ny_x], [ny_top, prof_h], color=WICK_C, lw=0.8, zorder=2)
    # Cuerpo NY
    rect_ny = plt.Rectangle((ny_x - ny_w/2, ny_bot), ny_w, ny_body_h,
                              facecolor=NY_col, edgecolor=NY_col,
                              alpha=0.75, zorder=3)
    ax.add_patch(rect_ny)
    # Label NY move
    ny_move_lbl = f'+{int(abs(ny_move))}' if ny_move >= 0 else f'-{int(abs(ny_move))}'
    ny_lbl_y = prof_h + price_range * 0.03 if ny_move >= 0 else prof_l - price_range * 0.04
    ny_lbl_va = 'bottom' if ny_move >= 0 else 'top'
    ax.text(ny_x, ny_lbl_y, ny_move_lbl,
            ha='center', va=ny_lbl_va, fontsize=7, color=NY_col,
            fontfamily='monospace', fontweight='bold', zorder=5)
    ax.text(ny_x, prof_l - price_range * 0.04, 'NY',
            ha='center', va='top', fontsize=5.5, color='#64748b',
            fontfamily='monospace', zorder=5)

    # ── Header del panel ──────────────────────────────────────
    ax.set_title('', pad=0)

    # Fecha
    ax.text(0.5, 1.01, date_lbl.replace('\n', ' '),
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=7, color=TXT_MAIN, fontfamily='monospace',
            fontweight='bold')

    # PM direction badge
    dir_color = BULL_C if pm_dir == 'BULLISH' else (BEAR_C if pm_dir == 'BEARISH' else NEUT_C)
    dir_lbl = '▲ BULL' if pm_dir == 'BULLISH' else ('▼ BEAR' if pm_dir == 'BEARISH' else '→ NEUT')
    ax.text(0.03, 0.97, dir_lbl,
            transform=ax.transAxes, ha='left', va='top',
            fontsize=6.5, color=dir_color, fontfamily='monospace',
            fontweight='bold', zorder=5)

    # VXN badge
    vxn_color = '#10b981' if vxn < 20 else ('#fbbf24' if vxn < 25 else '#ef4444')
    ax.text(0.97, 0.97, f'VXN {vxn:.1f}',
            transform=ax.transAxes, ha='right', va='top',
            fontsize=6, color=vxn_color, fontfamily='monospace', zorder=5)

    # Patrón badge (abajo)
    ax.text(0.5, 0.02, pat_name,
            transform=ax.transAxes, ha='center', va='bottom',
            fontsize=6, color=pat_color, fontfamily='monospace',
            fontweight='bold', zorder=5)

    # Separador NY range 
    ax.text(0.97, 0.02, f'Rng:{int(ny_range)}',
            transform=ax.transAxes, ha='right', va='bottom',
            fontsize=5.5, color='#64748b', fontfamily='monospace', zorder=5)

# ─── Guardar PNG principal (todos) ─────────────────────────────
plt.tight_layout(rect=[0, 0.0, 1, 0.972], h_pad=2.0, w_pad=1.0)
out = 'martes_pm_atlas.png'
plt.savefig(out, dpi=160, bbox_inches='tight', facecolor=BG)
plt.close()
print(f"[OK] Atlas (27 paneles) → {out}")

# ─── SEGUNDA FIGURA: Panel GRANDE de los 5 martes CON PM que falló ──
EXCEPTIONS = ['2025-11-18', '2025-12-02', '2026-03-10', '2026-03-17']
exc_records = [r for r in records if r['date'] in EXCEPTIONS]

fig2 = plt.figure(figsize=(20, 9), facecolor=BG)
fig2.patch.set_facecolor(BG)
fig2.text(0.5, 0.985, '⚠️  EXCEPCIONES: Cuando el PM Mintió — 4 Casos NQ Martes',
          ha='center', va='top', fontsize=16, fontweight='900',
          color='#ffd60a', fontfamily='monospace')
fig2.text(0.5, 0.968, 'PM direction NO coincidió con el resultado del NY — Estudiar patrones de fallo',
          ha='center', va='top', fontsize=10, color='#64748b', fontfamily='monospace')

axs2 = fig2.subplots(1, len(exc_records))

for j, (ax, rec) in enumerate(zip(axs2, exc_records)):
    ax.set_facecolor(CARD_BG)
    for spine in ax.spines.values():
        spine.set_color('#ffd60a')
        spine.set_linewidth(1.2)

    date_str = rec['date']
    pm_dir   = rec['pm_direction']
    pm_o     = rec['pm_o']
    pm_h     = rec['pm_h']
    pm_l     = rec['pm_l']
    pm_c     = rec['pm_c']
    ny_o     = rec['ny_o']
    prof_h   = rec['prof_h']
    prof_l   = rec['prof_l']
    val      = rec['val_f']
    poc      = rec['poc_f']
    vah      = rec['vah_f']
    vxn      = rec['vxn_f']
    ny_move  = float(rec.get('ny_move_pts', 0) or 0)
    pm_move  = float(rec.get('pm_move_real', pm_c - pm_o))
    ny_range = rec.get('ny_range_real', 0)
    ny_close = ny_o + ny_move

    all_prices = [pm_o, pm_h, pm_l, pm_c, ny_o, prof_h, prof_l, val, poc, vah]
    price_min  = min(all_prices) - 60
    price_max  = max(all_prices) + 60
    price_range = price_max - price_min or 100

    ax.set_xlim(0, 3.5)
    ax.set_ylim(price_min, price_max)
    ax.set_xticks([])
    ax.yaxis.set_major_locator(mticker.MaxNLocator(6))
    ax.tick_params(axis='y', labelsize=8, colors='#94a3b8', pad=2)
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()
    ax.grid(axis='y', color=GRID_C, linewidth=0.5, linestyle='--', alpha=0.4)

    pm_body_col = PM_BODY_B if pm_dir == 'BULLISH' else (PM_BODY_R if pm_dir == 'BEARISH' else PM_BODY_N)
    NY_col = BULL_C if ny_move > 0 else BEAR_C

    # VA lines
    for level, color, ls, lw, lbl in [
        (vah, VA_LINE, '--', 1.2, 'VAH'), (val, VA_LINE, '--', 1.2, 'VAL'),
        (poc, POC_LINE, '-', 1.0, 'POC'),
    ]:
        ax.axhline(level, color=color, linewidth=lw, linestyle=ls, alpha=0.7, zorder=1)
        ax.text(0.04, level, lbl, fontsize=7, color=color, va='center',
                fontfamily='monospace', fontweight='bold', zorder=5, alpha=0.9)

    pm_x, pm_w = 0.9, 0.7
    pm_bot = min(pm_o, pm_c); pm_top = max(pm_o, pm_c)
    pm_body_h = max(pm_top - pm_bot, 6)
    ax.plot([pm_x, pm_x], [pm_l, pm_bot], color=WICK_C, lw=1.2, zorder=2)
    ax.plot([pm_x, pm_x], [pm_top, pm_h], color=WICK_C, lw=1.2, zorder=2)
    ax.add_patch(plt.Rectangle((pm_x-pm_w/2, pm_bot), pm_w, pm_body_h,
                                facecolor=pm_body_col, edgecolor=pm_body_col,
                                alpha=0.85, zorder=3))
    pm_lbl = f'PM {("+" if pm_move >= 0 else "")}{int(pm_move)}pts'
    ax.text(pm_x, pm_h + price_range*0.04, pm_lbl, ha='center', va='bottom',
            fontsize=8, color=pm_body_col, fontfamily='monospace', fontweight='bold', zorder=5)

    ny_x, ny_w = 2.5, 0.7
    ny_bot = min(ny_o, ny_close); ny_top = max(ny_o, ny_close)
    ny_body_h = max(ny_top - ny_bot, 6)
    ax.plot([ny_x, ny_x], [prof_l, ny_bot], color=WICK_C, lw=1.2, zorder=2)
    ax.plot([ny_x, ny_x], [ny_top, prof_h], color=WICK_C, lw=1.2, zorder=2)
    ax.add_patch(plt.Rectangle((ny_x-ny_w/2, ny_bot), ny_w, ny_body_h,
                                facecolor=NY_col, edgecolor=NY_col,
                                alpha=0.75, zorder=3))
    ny_lbl = f'NY {("+" if ny_move >= 0 else "")}{int(ny_move)}pts'
    ny_y = prof_h + price_range*0.04 if ny_move >= 0 else prof_l - price_range*0.04
    ax.text(ny_x, ny_y, ny_lbl, ha='center', va='bottom' if ny_move>=0 else 'top',
            fontsize=8, color=NY_col, fontfamily='monospace', fontweight='bold', zorder=5)

    ax.annotate('', xy=(ny_x-0.35, ny_o), xytext=(pm_x+pm_w/2+0.1, pm_c),
                arrowprops=dict(arrowstyle='->', color='#4a5568', lw=1.0), zorder=4)

    # Title
    dt = datetime.strptime(date_str, '%Y-%m-%d').strftime('%d %b %Y')
    ax.set_title(f'{dt}', fontsize=10, color='#ffd60a', fontfamily='monospace',
                 fontweight='bold', pad=8)

    # Por qué falló
    if date_str == '2025-11-18':
        why = 'PM BULL +124pts\nPM muy fuerte → agotó\nel movimiento antes de NY'
    elif date_str == '2025-12-02':
        why = 'PM BEAR -48pts (débil)\n→ Trampa bajista clásica\nNY revirtió +93pts'
    elif date_str == '2026-03-10':
        why = 'PM BEAR -165pts\n→ Bear muy extendido\nNY rebote técnico +16pts'
    else:
        why = 'PM BEAR -66pts\n→ PM débil + VA soporte\nNY rebote +78pts'

    ax.text(0.5, 0.04, why, transform=ax.transAxes, ha='center', va='bottom',
            fontsize=7.5, color='#ffd60a', fontfamily='monospace',
            linespacing=1.5, zorder=6,
            bbox=dict(boxstyle='round,pad=0.4', facecolor=(0,0,0,0.5),
                      edgecolor='#ffd60a', alpha=0.85))

    dir_color = BULL_C if pm_dir == 'BULLISH' else (BEAR_C if pm_dir == 'BEARISH' else NEUT_C)
    dir_sym = '▲' if pm_dir == 'BULLISH' else ('▼' if pm_dir == 'BEARISH' else '→')
    ax.text(0.03, 0.97, f'{dir_sym} {pm_dir}',
            transform=ax.transAxes, ha='left', va='top',
            fontsize=8, color=dir_color, fontfamily='monospace', fontweight='bold', zorder=5)

    vxn_color = '#10b981' if vxn < 20 else ('#fbbf24' if vxn < 25 else '#ef4444')
    ax.text(0.97, 0.97, f'VXN {vxn:.1f}',
            transform=ax.transAxes, ha='right', va='top',
            fontsize=8, color=vxn_color, fontfamily='monospace', fontweight='bold', zorder=5)

# ── Badge ⚠ en cada panel
for ax in axs2:
    ax.text(0.5, 0.96, '⚠ PM FALLÓ',
            transform=ax.transAxes, ha='center', va='top',
            fontsize=8, color='#ffd60a', fontfamily='monospace',
            fontweight='bold', zorder=6)

plt.tight_layout(rect=[0, 0, 1, 0.96], h_pad=1.5, w_pad=2.0)
out2 = 'martes_pm_excepciones.png'
plt.savefig(out2, dpi=160, bbox_inches='tight', facecolor=BG)
plt.close()
print(f"[OK] Excepciones (4 paneles) → {out2}")
print("✅ DONE: Dos archivos generados.")
