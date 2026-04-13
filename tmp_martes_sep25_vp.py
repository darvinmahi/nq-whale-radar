# -*- coding: utf-8 -*-
"""
ESTUDIO MARTES NQ — DESDE SEP 2025 CON VOLUME PROFILE REAL
==============================================================
Basado en ny_profile_asia_london_daily.csv (nuestro propio backtest)
Contiene: VAL, POC, VAH reales + apertura NY + VXN + trend
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Cargar datos ─────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(BASE, 'ny_profile_asia_london_daily.csv'))
df['date'] = pd.to_datetime(df['date'])

# Solo martes
mar = df[df['weekday'] == 'MARTES'].copy().reset_index(drop=True)

# Dia de la semana del lunes previo para comparar
# Vamos a vincular con el lunes de la misma semana
lun = df[df['weekday'] == 'LUNES'].copy()
lun_dict = {row['date']: row for _, row in lun.iterrows()}

# Enriquecer martes con datos del lunes previo
for col in ['move_lunes', 'range_lunes', 'pm_direction_lunes', 'close_lunes']:
    mar[col] = None

for i, r in mar.iterrows():
    fecha_lun = r['date'] - pd.Timedelta(days=1)
    if fecha_lun in lun_dict:
        lr = lun_dict[fecha_lun]
        pm_move = float(lr['pm_close']) - float(lr['pm_open'])
        mar.at[i, 'move_lunes'] = pm_move
        mar.at[i, 'range_lunes'] = float(lr['pm_range'])
        mar.at[i, 'pm_direction_lunes'] = lr['pm_direction']

mar['move_lunes'] = pd.to_numeric(mar['move_lunes'], errors='coerce')

n = len(mar)
print(f"\nTotal martes estudiados: {n}")
print(f"Rango de fechas: {mar['date'].min().date()} -> {mar['date'].max().date()}")
print("\nColumnas disponibles:")
for c in mar.columns: print(f"  {c}: {mar[c].dtype}")

# ── Calcular resultado del martes ─────────────────────────────────────────────
# El cierre del pre-market del dia siguiente nos da el resultado del dia
# Pero con lo que tenemos: pm_close - pm_open del mismo martes nos da el pre-market
# El movimiento principal es: ny_open_price vs pm_close (resultado del dia)
mar['ny_move_pts'] = mar['pm_close'] - mar['ny_open_price']  # cuanto se movio desde apertura NY
mar['ny_range'] = mar['pm_hi'] - mar['pm_lo']  # rango del dia completo
# Tipo: si cierra arriba de apertura = alcista
mar['alcista'] = mar['pm_close'] > mar['ny_open_price']
mar['tipo'] = mar['alcista'].map({True: 'ALCISTA', False: 'BAJISTA'})

print(f"\nTipo de martes:")
print(f"  ALCISTA (sube): {mar['alcista'].sum()} ({100*mar['alcista'].mean():.0f}%)")
print(f"  BAJISTA (baja): {(~mar['alcista']).sum()} ({100*(~mar['alcista']).mean():.0f}%)")
print(f"\nRango pm_hi-pm_lo:")
print(f"  Promedio: {mar['ny_range'].mean():.0f}pts")
print(f"  Mediana:  {mar['ny_range'].median():.0f}pts")
print(f"  Max:      {mar['ny_range'].max():.0f}pts")

# ── Estadisticas por posicion de apertura ────────────────────────────────────
print("\n--- APERTURA NY POSITION vs RESULTADO ---")
for pos in ['BELOW_VA', 'INSIDE_VA', 'ABOVE_VA']:
    seg = mar[mar['ny_open_pos'] == pos]
    if len(seg)==0: continue
    print(f"\n  {pos} (n={len(seg)}):")
    print(f"    Alcistas:     {100*seg['alcista'].mean():.0f}%")
    print(f"    Move mediano: {seg['ny_move_pts'].median():.0f}pts")
    print(f"    Rango mediano:{seg['ny_range'].median():.0f}pts")
    if seg['touches_vah'].notna().any():
        print(f"    Toca VAH:     {100*seg['touches_vah'].astype(bool).mean():.0f}%")
        print(f"    Toca POC:     {100*seg['touches_poc'].astype(bool).mean():.0f}%")
        print(f"    Toca VAL:     {100*seg['touches_val'].astype(bool).mean():.0f}%")
        print(f"    Rompe VAH:    {100*seg['breaks_vah'].astype(bool).mean():.0f}%")
        print(f"    Rompe VAL:    {100*seg['breaks_val'].astype(bool).mean():.0f}%")
        print(f"    Cierra dentro:{100*seg['close_inside'].astype(bool).mean():.0f}%")
        print(f"    Cierra encima:{100*seg['close_above_va'].astype(bool).mean():.0f}%")

# ── Pre-market direction ──────────────────────────────────────────────────────
print("\n--- PREMARKET DIRECTION vs RESULTADO ---")
for pm in ['BULL', 'BEAR', 'NEUTRAL']:
    seg = mar[mar['pm_direction'] == pm]
    if len(seg)==0: continue
    print(f"\n  PM {pm} (n={len(seg)}):")
    print(f"    Alcistas NY:  {100*seg['alcista'].mean():.0f}%")
    print(f"    Move mediano: {seg['ny_move_pts'].median():.0f}pts")

# ── VXN ───────────────────────────────────────────────────────────────────────
print("\n--- VXN al momento del martes ---")
has_vxn = mar[mar['vxn'].notna()]
for vmin, vmax, lbl in [(14,20,'< 20  (calma)'),(20,25,'20-25 (normal)'),(25,30,'25-30 (miedo)'),(30,60,'> 30  (panico)')]:
    seg = has_vxn[(has_vxn['vxn']>=vmin)&(has_vxn['vxn']<vmax)]
    if len(seg)==0: continue
    print(f"  VXN {lbl}: n={len(seg):2d} | Alcistas={100*seg['alcista'].mean():.0f}% | Rango={seg['ny_range'].median():.0f}pts")

# ── Tabla completa de todos los martes ───────────────────────────────────────
print("\n--- TODOS LOS MARTES (tabla) ---")
tabla = mar[['date','ny_open_pos','vxn','pm_direction','touches_vah','touches_val',
             'touches_poc','breaks_vah','breaks_val','close_inside','close_above_va',
             'close_below_va','ny_move_pts','ny_range','alcista']].copy()
tabla['date'] = tabla['date'].dt.strftime('%Y-%m-%d')
tabla['ny_move_pts'] = tabla['ny_move_pts'].round(0).astype(int)
tabla['ny_range'] = tabla['ny_range'].round(0).astype(int)
print(tabla.to_string(index=False))

# ══════════════════════════════════════════════════════════════════════════════
# GRAFICA
# ══════════════════════════════════════════════════════════════════════════════
CYAN=  '#00f2ff'; GREEN= '#00ff88'; RED=   '#ff3355'
YELLOW='#ffd60a'; WHITE= '#e2e8f8'; GRAY=  '#4a5a7a'; PURPLE='#a78bfa'

fig = plt.figure(figsize=(22, 24), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(4, 3, figure=fig, hspace=0.6, wspace=0.38)

def ax_style(ax, title, sub=''):
    ax.set_facecolor('#0d1628')
    ax.set_title(f'{title}\n{sub}' if sub else title, color=CYAN, fontsize=9.5, fontweight='bold', pad=8)
    ax.tick_params(colors=GRAY, labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

fig.suptitle(f'ESTUDIO MARTES NQ — {n} SESIONES CON VOLUME PROFILE REAL\n'
             f'Sep 2025 - Mar 2026  ·  Datos de ny_profile_asia_london_daily.csv',
             color=WHITE, fontsize=14, fontweight='bold', y=0.99)

# P1: Rango por posicion de apertura
ax1 = fig.add_subplot(gs[0,0])
ax_style(ax1, '1. Rango del dia segun\napertura NY vs Value Area')
pos_order = ['BELOW_VA', 'INSIDE_VA', 'ABOVE_VA']
pos_labels = ['Bajo VAL', 'Dentro VA', 'Sobre VAH']
pos_ranges  = []
pos_alc     = []
pos_ns      = []
for pos in pos_order:
    seg = mar[mar['ny_open_pos']==pos]
    pos_ranges.append(seg['ny_range'].median() if len(seg)>0 else 0)
    pos_alc.append(100*seg['alcista'].mean() if len(seg)>0 else 0)
    pos_ns.append(len(seg))

x1 = np.arange(3)
c1 = [GREEN, YELLOW, RED]
bars1 = ax1.bar(x1, pos_ranges, color=c1, alpha=0.82, edgecolor='#1e2d4a', width=0.6)
ax1.set_xticks(x1)
ax1.set_xticklabels(pos_labels, fontsize=8.5, color=GRAY)
ax1.set_ylabel('Rango mediano (pts)', color=GRAY, fontsize=8)
ax1_r = ax1.twinx()
ax1_r.plot(x1, pos_alc, 'o--', color=CYAN, linewidth=2, markersize=9, label='% Alcistas')
ax1_r.set_ylabel('% Alcistas', color=CYAN, fontsize=8)
ax1_r.tick_params(colors=CYAN, labelsize=8)
ax1_r.set_ylim(0, 110)
for bar, pts, alc, n_v in zip(bars1, pos_ranges, pos_alc, pos_ns):
    ax1.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{pts:.0f}pts\n{alc:.0f}% alc\nn={n_v}', ha='center', va='bottom',
             fontsize=8.5, color=WHITE, fontweight='bold')

# P2: Tasa de toque VAH/POC/VAL
ax2 = fig.add_subplot(gs[0,1])
ax_style(ax2, '2. Tasa de toque de niveles\n(todos los martes)')
niveles = ['VAH', 'POC', 'VAL']
cols_t  = ['touches_vah', 'touches_poc', 'touches_val']
cols_b  = ['breaks_vah',  None,          'breaks_val']
toques  = [100*mar[c].astype(bool).mean() if c in mar.columns else 0 for c in cols_t]
rupturas= [100*mar[c].astype(bool).mean() if c and c in mar.columns else 0 for c in cols_b]

x2 = np.arange(3)
w2 = 0.38
bars2a = ax2.bar(x2-w2/2, toques,   w2, color=CYAN,   alpha=0.8, label='Toca nivel')
bars2b = ax2.bar(x2+w2/2, rupturas, w2, color=PURPLE, alpha=0.8, label='Rompe nivel')
ax2.axhline(50, color=YELLOW, linewidth=1, linestyle='--', alpha=0.6)
ax2.set_xticks(x2); ax2.set_xticklabels(niveles, fontsize=10, color=GRAY)
ax2.set_ylabel('%', color=GRAY, fontsize=8); ax2.set_ylim(0, 105)
ax2.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
for bar, v in list(zip(bars2a, toques)) + list(zip(bars2b, rupturas)):
    if v>0: ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
                     f'{v:.0f}%', ha='center', va='bottom', fontsize=9, color=WHITE, fontweight='bold')

# P3: Cierre de la sesion
ax3 = fig.add_subplot(gs[0,2])
ax_style(ax3, '3. Como cierra la sesion\n(dentro/encima/bajo VA)')
cierre_cats = [
    ('Dentro VA',    'close_inside',    YELLOW),
    ('Encima VA',    'close_above_va',  GREEN),
    ('Bajo VA',      'close_below_va',  RED),
]
c3_vals = [100*mar[c].astype(bool).mean() for _, c, _ in cierre_cats]
c3_lbl  = [l for l, _, _ in cierre_cats]
c3_col  = [c for _, _, c in cierre_cats]
bars3 = ax3.bar(range(3), c3_vals, color=c3_col, alpha=0.82, edgecolor='#1e2d4a', width=0.6)
ax3.set_xticks(range(3)); ax3.set_xticklabels(c3_lbl, fontsize=9, color=GRAY)
ax3.set_ylabel('%', color=GRAY, fontsize=8); ax3.set_ylim(0, 105)
for bar, v in zip(bars3, c3_vals):
    ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{v:.0f}%', ha='center', va='bottom', fontsize=11, color=WHITE, fontweight='bold')
ax3.text(0.5, 0.08,
    f'Tot: n={n} martes\nAlcistas: {100*mar["alcista"].mean():.0f}%',
    transform=ax3.transAxes, ha='center', fontsize=9, color=CYAN,
    bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.8, boxstyle='round'))

# P4: VXN vs Resultado
ax4 = fig.add_subplot(gs[1,0])
ax_style(ax4, '4. VXN vs Rango del martes')
has_vxn = mar[mar['vxn'].notna()].copy()
if len(has_vxn) > 0:
    sc = ax4.scatter(has_vxn['vxn'], has_vxn['ny_range'],
                c=[GREEN if a else RED for a in has_vxn['alcista']],
                alpha=0.75, s=60, edgecolors='none', zorder=4)
    for _, r in has_vxn.iterrows():
        ax4.annotate(r['date'].strftime('%m/%d'), (r['vxn'], r['ny_range']),
                     fontsize=5.5, color=GRAY, xytext=(2,2), textcoords='offset points')
    for xv, col, lbl in [(20,YELLOW,'VXN=20'),(25,YELLOW,'VXN=25'),(30,RED,'VXN=30')]:
        ax4.axvline(xv, color=col, linewidth=1.2, linestyle='--', alpha=0.65, label=lbl)
    ax4.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
    ax4.set_xlabel('VXN', color=GRAY, fontsize=8)
    ax4.set_ylabel('Rango del dia (pts)', color=GRAY, fontsize=8)
    # Correlacion
    from scipy import stats as sst
    if len(has_vxn) > 3:
        r_val, p_val = sst.pearsonr(has_vxn['vxn'].astype(float), has_vxn['ny_range'].astype(float))
        ax4.text(0.02,0.97,f'r={r_val:.2f} (p={p_val:.3f})\nMas VXN = mas rango',
                 transform=ax4.transAxes, ha='left', va='top', fontsize=8, color=WHITE,
                 bbox=dict(facecolor='#0a0f1e',edgecolor=GRAY,alpha=0.85,boxstyle='round'))

# P5: Pre-market direction vs resultado NY
ax5 = fig.add_subplot(gs[1,1])
ax_style(ax5, '5. Direction pre-market\nvs resultado sesion NY')
pm_cats = ['BULL', 'BEAR', 'NEUTRAL']
pm_alc  = [100*mar[mar['pm_direction']==p]['alcista'].mean() if len(mar[mar['pm_direction']==p])>0 else 0 for p in pm_cats]
pm_rng  = [mar[mar['pm_direction']==p]['ny_range'].median() if len(mar[mar['pm_direction']==p])>0 else 0 for p in pm_cats]
pm_n    = [len(mar[mar['pm_direction']==p]) for p in pm_cats]
x5 = np.arange(3)
pm_colors = [GREEN, RED, YELLOW]
bars5 = ax5.bar(x5, pm_alc, color=pm_colors, alpha=0.82, edgecolor='#1e2d4a', width=0.6)
ax5.axhline(50, color=WHITE, linewidth=1, linestyle='--', alpha=0.5, label='50%')
ax5.set_xticks(x5); ax5.set_xticklabels(['PM BULL', 'PM BEAR', 'PM NEUTRAL'], fontsize=8, color=GRAY)
ax5.set_ylabel('% Alcistas en NY', color=GRAY, fontsize=8); ax5.set_ylim(0, 110)
ax5_r = ax5.twinx()
ax5_r.plot(x5, pm_rng, 'D--', color=CYAN, linewidth=2, markersize=9)
ax5_r.set_ylabel('Rango mediano (pts)', color=CYAN, fontsize=8)
ax5_r.tick_params(colors=CYAN, labelsize=8)
for bar, alc, rng, n_v in zip(bars5, pm_alc, pm_rng, pm_n):
    ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{alc:.0f}% alc\n{rng:.0f}pts\nn={n_v}', ha='center', va='bottom', fontsize=8, color=WHITE)

# P6: Moves del lunes previo vs resultado martes
ax6 = fig.add_subplot(gs[1,2])
ax_style(ax6, '6. Lunes previo vs Martes\n(pre-market move lunes)')
has_mon = mar[mar['move_lunes'].notna()].copy()
if len(has_mon) > 0:
    ax6.scatter(has_mon['move_lunes'], has_mon['ny_move_pts'],
                c=[GREEN if a else RED for a in has_mon['alcista']],
                alpha=0.75, s=60, edgecolors='none')
    for _, r in has_mon.iterrows():
        ax6.annotate(r['date'].strftime('%m/%d'), (r['move_lunes'], r['ny_move_pts']),
                     fontsize=5.5, color=GRAY, xytext=(2,2), textcoords='offset points')
    ax6.axhline(0, color=GRAY, linewidth=0.8, alpha=0.5)
    ax6.axvline(0, color=GRAY, linewidth=0.8, alpha=0.5)
    ax6.set_xlabel('Move pre-market lunes (pts)', color=GRAY, fontsize=8)
    ax6.set_ylabel('Move NY del martes (pts)', color=GRAY, fontsize=8)
    from matplotlib.patches import Patch
    ax6.legend(handles=[Patch(facecolor=GREEN,alpha=0.7,label='Martes ALCISTA'),
                        Patch(facecolor=RED,  alpha=0.7,label='Martes BAJISTA')],
               fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# P7: Tabla completa de los 27 martes
ax7 = fig.add_subplot(gs[2,:])
ax_style(ax7, f'TABLA COMPLETA — LOS {n} MARTES CON VOLUME PROFILE REAL (Sep2025-Mar2026)')
ax7.axis('off')

headers = ['Fecha','NY Open','VAL','POC','VAH','VA Rng','PM Dir','VXN','Toca VAH','Toca POC','Toca VAL','Rompe','Cierre','NY Move','Rango','Dir']
rows = [headers]
for _, r in mar.iterrows():
    rompe = ''
    if r.get('breaks_vah'): rompe = 'VAH'
    elif r.get('breaks_val'): rompe = 'VAL'
    cierre = 'DENTRO' if r.get('close_inside') else ('ENCIMA' if r.get('close_above_va') else 'BAJO')
    rows.append([
        r['date'].strftime('%Y-%m-%d'),
        r['ny_open_pos'].replace('_VA','').replace('_',' '),
        f"{r['val']:.0f}" if pd.notna(r.get('val')) else '-',
        f"{r['poc']:.0f}" if pd.notna(r.get('poc')) else '-',
        f"{r['vah']:.0f}" if pd.notna(r.get('vah')) else '-',
        f"{r['va_range']:.0f}" if pd.notna(r.get('va_range')) else '-',
        str(r.get('pm_direction','?')),
        f"{r['vxn']:.1f}" if pd.notna(r.get('vxn')) else '-',
        'SI' if r.get('touches_vah') else 'no',
        'SI' if r.get('touches_poc') else 'no',
        'SI' if r.get('touches_val') else 'no',
        rompe or '-',
        cierre,
        f"{r['ny_move_pts']:.0f}pts",
        f"{r['ny_range']:.0f}pts",
        'ALZA' if r['alcista'] else 'BAJA',
    ])

t = ax7.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(7.5); t.scale(1, 1.7)
for (row,col), cell in t.get_celld().items():
    cell.set_facecolor('#0a0f1e' if row==0 else ('#0d1628' if row%2==0 else '#111c35'))
    cell.set_edgecolor('#1e2d4a')
    txt = cell.get_text()
    if row==0:
        txt.set_color(CYAN); txt.set_fontweight('bold')
    else:
        val_str = rows[row][col]
        if val_str in ('ALZA',): txt.set_color(GREEN); txt.set_fontweight('bold')
        elif val_str in ('BAJA',): txt.set_color(RED); txt.set_fontweight('bold')
        elif val_str == 'SI': txt.set_color(GREEN)
        elif val_str in ('VAH','VAL'): txt.set_color(RED); txt.set_fontweight('bold')
        elif val_str == 'ENCIMA': txt.set_color(GREEN)
        elif val_str == 'BAJO': txt.set_color(RED)
        else: txt.set_color(WHITE)

# P8: Serie temporal
ax8 = fig.add_subplot(gs[3,:])
ax_style(ax8, f'TODOS LOS {n} MARTES — Sep2025 a Mar2026 (cronologico)')
colors8 = [GREEN if a else RED for a in mar['alcista']]
bars8 = ax8.bar(mar['date'], mar['ny_range'], color=colors8, alpha=0.75, width=3)
# Anotar cada barra con el VP position
for i, r in mar.iterrows():
    pos_short = {'BELOW_VA':'BEL','INSIDE_VA':'IN','ABOVE_VA':'ABV'}.get(r['ny_open_pos'],'?')
    ax8.text(r['date'], r['ny_range']+5, pos_short, ha='center', va='bottom', fontsize=6.5, color=CYAN)
# Anotar el resultado
for i, r in mar.iterrows():
    move = r['ny_move_pts']
    ax8.text(r['date'], r['ny_range']/2, f"{'+' if move>0 else ''}{move:.0f}",
             ha='center', va='center', fontsize=6, color=WHITE, fontweight='bold')
ax8.axhline(mar['ny_range'].median(), color=YELLOW, linewidth=1.5, linestyle='--', alpha=0.7,
            label=f"Mediana {mar['ny_range'].median():.0f}pts")
ax8.set_xlabel('Fecha', color=GRAY, fontsize=8)
ax8.set_ylabel('Rango del dia (pts)', color=GRAY, fontsize=8)
# Leyenda
from matplotlib.patches import Patch
ax8.legend(handles=[
    Patch(facecolor=GREEN,alpha=0.75,label=f'Alcista ({mar["alcista"].sum()})'),
    Patch(facecolor=RED,  alpha=0.75,label=f'Bajista ({(~mar["alcista"]).sum()})'),
] + ax8.get_lines(), fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax8.tick_params(axis='x', rotation=45)

# Guardar
out = os.path.join(BASE, 'martes_sep25_vp_completo.png')
plt.savefig(out, dpi=140, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] -> {out}")
