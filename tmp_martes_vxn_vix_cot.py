# -*- coding: utf-8 -*-
"""
CLUSTERS MARTES ALCISTAS vs BAJISTAS — Con VXN, VIX y COT
==========================================================
Compara los 16 alcistas vs 11 bajistas usando:
  - VXN (volatilidad NQ)
  - VIX (volatilidad SP500)
  - COT Index (posicion institucional)
  - Volume Profile (VAL/POC/VAH)
  - Pre-market direction
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
import json
import yfinance as yf

BASE = os.path.dirname(os.path.abspath(__file__))

# ══ 1. DATOS MARTES ══════════════════════════════════════════════════════════
df = pd.read_csv(os.path.join(BASE, 'ny_profile_asia_london_daily.csv'))
df['date'] = pd.to_datetime(df['date'])
mar = df[df['weekday'] == 'MARTES'].copy().reset_index(drop=True)
mar['ny_move_pts'] = mar['pm_close'] - mar['ny_open_price']
mar['ny_range']    = mar['pm_hi'] - mar['pm_lo']
mar['alcista']     = mar['pm_close'] > mar['ny_open_price']
mar['tipo']        = mar['alcista'].map({True: 'ALCISTA', False: 'BAJISTA'})
n_total = len(mar)

# Lunes previo
lun = df[df['weekday'] == 'LUNES'].copy()
lun_dict = {row['date']: row for _, row in lun.iterrows()}
def get_lun_pm(fecha):
    f = fecha - pd.Timedelta(days=1)
    if f in lun_dict:
        lr = lun_dict[f]
        return float(lr['pm_close']) - float(lr['pm_open'])
    return None
mar['move_lunes'] = mar['date'].apply(get_lun_pm)

# ══ 2. VIX via yfinance ══════════════════════════════════════════════════════
print("[1] Descargando VIX...")
vix_raw = yf.download('^VIX', start='2025-09-01', end='2026-04-08', interval='1d', auto_adjust=True, progress=False)
vix_raw = vix_raw.reset_index()
vix_raw.columns = [c[0] if isinstance(c, tuple) else c for c in vix_raw.columns]
vix_raw['Date'] = pd.to_datetime(vix_raw['Date']).dt.date
vix_dict = {str(row['Date']): float(row['Close']) for _, row in vix_raw.iterrows() if pd.notna(row['Close'])}
mar['vix'] = mar['date'].apply(lambda x: vix_dict.get(str(x.date())))

# ══ 3. VXN + COT del DB ══════════════════════════════════════════════════════
print("[2] Cargando VXN/COT del DB...")
with open(os.path.join(BASE, 'data', 'research', 'daily_master_db.json'), encoding='utf-8') as f:
    db = json.load(f)
db_dict = {r['date'][:10]: r for r in db.get('records', [])}
mar['vxn_db'] = mar['date'].apply(lambda x: db_dict.get(str(x.date()), {}).get('vxn'))
mar['cot_idx'] = mar['date'].apply(lambda x: db_dict.get(str(x.date()), {}).get('cot_index'))

# Preferir VXN del CSV del VP (mas preciso para ese dia)
mar['vxn_final'] = mar['vxn'].fillna(mar['vxn_db'])

print(f"[3] Total martes: {n_total} | Alcistas: {mar['alcista'].sum()} | Bajistas: {(~mar['alcista']).sum()}")
print(f"    VIX disponible: {mar['vix'].notna().sum()}/{n_total}")
print(f"    COT disponible: {mar['cot_idx'].notna().sum()}/{n_total}")

# ══ 4. SEPARAR ALCISTAS / BAJISTAS ══════════════════════════════════════════
alc = mar[mar['alcista']].copy().reset_index(drop=True)
baj = mar[~mar['alcista']].copy().reset_index(drop=True)

# ══ 5. CLASIFICACION DE ALCISTAS ═════════════════════════════════════════════
def clasificar_alc(r):
    pm  = r['pm_direction']
    bv  = bool(r['breaks_val'])
    bvh = bool(r['breaks_vah'])
    vxn = float(r['vxn_final']) if pd.notna(r['vxn_final']) else 21
    cot = float(r['cot_idx']) if pd.notna(r['cot_idx']) else 60
    mov = float(r['ny_move_pts'])

    # A: TRAMPA BAJISTA — PM bajista, barre VAL, explota
    if pm == 'BEARISH' and bv and bvh and mov > 0:
        return 'A — TRAMPA BAJISTA'
    # B: CONTINUACION sin toque VAL
    if pm == 'BULLISH' and not bv and bvh:
        return 'B — CONTINUACION LIMPIA'
    # C: PM Bull pero toco los dos lados
    if pm == 'BULLISH' and bv and bvh:
        return 'C — RANGO COMPLETO'
    # D: No rompe VAH (move menor, contenido)
    if not bvh:
        return 'D — ALCISTA CONTENIDO'
    # E: Neutral PM
    if pm == 'NEUTRAL' and mov > 0:
        return 'E — NEUTRAL->ALZA'
    return 'OTRO'

alc['patron'] = alc.apply(clasificar_alc, axis=1)

# ══ 6. COMPARACIONES ESTADISTICAS ════════════════════════════════════════════
print("\n" + "="*65)
print("ALCISTAS vs BAJISTAS — COMPARACION VXN / VIX / COT")
print("="*65)

def stats(g, nombre):
    vxn_m = g['vxn_final'].dropna().median()
    vix_m = g['vix'].dropna().median()
    cot_m = g['cot_idx'].dropna().median()
    mov_m = g['ny_move_pts'].median()
    rng_m = g['ny_range'].median()
    print(f"\n  {nombre} (n={len(g)}):")
    print(f"    VXN mediano:   {vxn_m:.1f}")
    vix_str = f"{vix_m:.1f}" if pd.notna(vix_m) else 'N/A'
    cot_str = f"{cot_m:.0f}" if pd.notna(cot_m) else 'N/A'
    print(f"    VIX mediano:   {vix_str}")
    print(f"    COT mediano:   {cot_str}")
    print(f"    Move mediano:  {mov_m:+.0f}pts")
    print(f"    Rango mediano: {rng_m:.0f}pts")
    # Barrio VAL primero
    bval = g['breaks_val'].astype(bool).mean()
    bvah = g['breaks_vah'].astype(bool).mean()
    print(f"    Barrio VAL:    {100*bval:.0f}%")
    print(f"    Rompio VAH:    {100*bvah:.0f}%")
    # PM direction
    pm_counts = g['pm_direction'].value_counts()
    print(f"    PM BULL:       {pm_counts.get('BULLISH',0)}  PM BEAR: {pm_counts.get('BEARISH',0)}  PM NEU: {pm_counts.get('NEUTRAL',0)}")

stats(alc, "ALCISTAS")
stats(baj, "BAJISTAS")

# COT > 50 = institucionales alcistas
print("\n--- COT como filtro ---")
for threshold in [50, 60, 70]:
    alc_t = alc[alc['cot_idx'] >= threshold]
    baj_t = baj[baj['cot_idx'] >= threshold]
    alc_b = alc[alc['cot_idx'] < threshold]
    baj_b = baj[baj['cot_idx'] < threshold]
    print(f"  COT >= {threshold}: Alcistas={len(alc_t)}/{len(alc)}  Bajistas={len(baj_t)}/{len(baj)}")
    print(f"  COT <  {threshold}: Alcistas={len(alc_b)}/{len(alc)}  Bajistas={len(baj_b)}/{len(baj)}")

print("\n--- PATRONES ALCISTAS ---")
for pat, grupo in alc.groupby('patron'):
    print(f"\n  {pat} (n={len(grupo)}):")
    vix_med_str = f"{grupo['vix'].median():.1f}" if grupo['vix'].notna().any() else 'N/A'
    cot_med_str = f"{grupo['cot_idx'].median():.0f}" if grupo['cot_idx'].notna().any() else 'N/A'
    print(f"    VXN med: {grupo['vxn_final'].median():.1f}  VIX med: {vix_med_str}  COT med: {cot_med_str}")
    print(f"    Move med: {grupo['ny_move_pts'].median():+.0f}pts  Rango: {grupo['ny_range'].median():.0f}pts")
    for _, r in grupo.sort_values('date').iterrows():
        vix_str = f"VIX={r['vix']:.1f}" if pd.notna(r['vix']) else "VIX=?"
        cot_str = f"COT={r['cot_idx']:.0f}" if pd.notna(r['cot_idx']) else "COT=?"
        print(f"    {r['date'].date()}  VXN={r['vxn_final']:.1f}  {vix_str}  {cot_str}  "
              f"PM={r['pm_direction']:7s}  move={r['ny_move_pts']:+5.0f}  bval={'SI' if r['breaks_val'] else 'no'}")

# ══════════════════════════════════════════════════════════════════════════════
# GRAFICA
# ══════════════════════════════════════════════════════════════════════════════
CYAN   = '#00f2ff'; GREEN  = '#00ff88'; RED    = '#ff3355'
YELLOW = '#ffd60a'; WHITE  = '#e2e8f8'; GRAY   = '#4a5a7a'
PURPLE = '#a78bfa'; ORANGE = '#ff8c00'

fig = plt.figure(figsize=(22, 30), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(5, 3, figure=fig, hspace=0.60, wspace=0.40)

def ax_style(ax, title):
    ax.set_facecolor('#0d1628')
    ax.set_title(title, color=CYAN, fontsize=9.5, fontweight='bold', pad=10)
    ax.tick_params(colors=GRAY, labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

fig.suptitle(f'MARTES NQ — {n_total} SESIONES: ALCISTAS vs BAJISTAS\n'
             f'Comparacion con VXN · VIX · COT Index · Volume Profile  (Sep2025-Mar2026)',
             color=WHITE, fontsize=14, fontweight='bold', y=0.995)

# ── P1: VXN — Alcistas vs Bajistas ─────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax_style(ax1, '1. VXN: Alcistas vs Bajistas')
bp_data = [alc['vxn_final'].dropna().values, baj['vxn_final'].dropna().values]
bp = ax1.boxplot(bp_data, labels=['ALCISTA', 'BAJISTA'], patch_artist=True, widths=0.5,
                 medianprops=dict(color=YELLOW, linewidth=2.5),
                 whiskerprops=dict(color=GRAY), capprops=dict(color=GRAY),
                 flierprops=dict(marker='o', color=GRAY, markersize=5))
bp['boxes'][0].set_facecolor(GREEN + '55')
bp['boxes'][1].set_facecolor(RED   + '55')
bp['boxes'][0].set_edgecolor(GREEN)
bp['boxes'][1].set_edgecolor(RED)
ax1.set_ylabel('VXN', color=GRAY, fontsize=9)
# Puntos individuales
for i, (grp, col) in enumerate([(alc, GREEN), (baj, RED)], 1):
    y = grp['vxn_final'].dropna().values
    ax1.scatter(np.random.normal(i, 0.05, len(y)), y, color=col, alpha=0.7, s=45, zorder=5)
ax1.text(0.5, 0.97,
    f'ALC med: {alc["vxn_final"].median():.1f}\nBAJ med: {baj["vxn_final"].median():.1f}',
    transform=ax1.transAxes, ha='center', va='top', fontsize=9, color=WHITE,
    bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.9, boxstyle='round'))

# ── P2: VIX — Alcistas vs Bajistas ─────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax_style(ax2, '2. VIX: Alcistas vs Bajistas')
bp_data2 = [alc['vix'].dropna().values, baj['vix'].dropna().values]
bp2 = ax2.boxplot(bp_data2, labels=['ALCISTA', 'BAJISTA'], patch_artist=True, widths=0.5,
                  medianprops=dict(color=YELLOW, linewidth=2.5),
                  whiskerprops=dict(color=GRAY), capprops=dict(color=GRAY),
                  flierprops=dict(marker='o', color=GRAY, markersize=5))
bp2['boxes'][0].set_facecolor(GREEN+'55'); bp2['boxes'][0].set_edgecolor(GREEN)
bp2['boxes'][1].set_facecolor(RED  +'55'); bp2['boxes'][1].set_edgecolor(RED)
ax2.set_ylabel('VIX', color=GRAY, fontsize=9)
for i, (grp, col) in enumerate([(alc, GREEN), (baj, RED)], 1):
    y = grp['vix'].dropna().values
    ax2.scatter(np.random.normal(i, 0.05, len(y)), y, color=col, alpha=0.7, s=45, zorder=5)
ax2.text(0.5, 0.97,
    f'ALC med: {alc["vix"].median():.1f}\nBAJ med: {baj["vix"].median():.1f}',
    transform=ax2.transAxes, ha='center', va='top', fontsize=9, color=WHITE,
    bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.9, boxstyle='round'))

# ── P3: COT Index — Alcistas vs Bajistas ────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax_style(ax3, '3. COT Index: Alcistas vs Bajistas\n(>50 = institucionales alcistas)')
bp_data3 = [alc['cot_idx'].dropna().values, baj['cot_idx'].dropna().values]
bp3 = ax3.boxplot(bp_data3, labels=['ALCISTA', 'BAJISTA'], patch_artist=True, widths=0.5,
                  medianprops=dict(color=YELLOW, linewidth=2.5),
                  whiskerprops=dict(color=GRAY), capprops=dict(color=GRAY),
                  flierprops=dict(marker='o', color=GRAY, markersize=5))
bp3['boxes'][0].set_facecolor(GREEN+'55'); bp3['boxes'][0].set_edgecolor(GREEN)
bp3['boxes'][1].set_facecolor(RED  +'55'); bp3['boxes'][1].set_edgecolor(RED)
ax3.axhline(50, color=WHITE, linewidth=1.5, linestyle='--', alpha=0.6, label='COT=50 (neutro)')
ax3.axhline(70, color=GREEN, linewidth=1,   linestyle=':', alpha=0.5, label='COT=70 (muy alcista)')
ax3.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax3.set_ylabel('COT Index', color=GRAY, fontsize=9)
for i, (grp, col) in enumerate([(alc, GREEN), (baj, RED)], 1):
    y = grp['cot_idx'].dropna().values
    ax3.scatter(np.random.normal(i, 0.05, len(y)), y, color=col, alpha=0.7, s=45, zorder=5)
ax3.text(0.5, 0.97,
    f'ALC med: {alc["cot_idx"].median():.0f}\nBAJ med: {baj["cot_idx"].median():.0f}',
    transform=ax3.transAxes, ha='center', va='top', fontsize=9, color=WHITE,
    bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.9, boxstyle='round'))

# ── P4: COT como filtro de prediccion ───────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0])
ax_style(ax4, '4. % Alcistas segun banda de COT\n(N martes en cada banda)')
cot_bands = [(0,40,'0-40\nMUY BAJ'),(40,55,'40-55\nNEUTRAL'),(55,70,'55-70\nALCISTA'),(70,100,'70-100\nMUY ALC')]
x4 = np.arange(len(cot_bands))
pct_alc4 = []
ns4 = []
for cmin, cmax, lbl in cot_bands:
    seg = mar[(mar['cot_idx'] >= cmin) & (mar['cot_idx'] < cmax)]
    ns4.append(len(seg))
    pct_alc4.append(100*seg['alcista'].mean() if len(seg)>0 else 0)

colors4 = [RED if p < 50 else (YELLOW if p < 60 else GREEN) for p in pct_alc4]
bars4 = ax4.bar(x4, pct_alc4, color=colors4, alpha=0.85, edgecolor='#1e2d4a', width=0.6)
ax4.axhline(50, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
ax4.set_xticks(x4)
ax4.set_xticklabels([l for _, _, l in cot_bands], fontsize=8, color=GRAY)
ax4.set_ylabel('% Martes Alcistas', color=GRAY, fontsize=8)
ax4.set_ylim(0, 105)
for bar, pct, n_v in zip(bars4, pct_alc4, ns4):
    ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{pct:.0f}%\nn={n_v}', ha='center', va='bottom', fontsize=9.5, color=WHITE, fontweight='bold')

# ── P5: VXN como filtro de prediccion ────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 1])
ax_style(ax5, '5. % Alcistas segun banda de VXN\n(mas VXN = mas volatilidad)')
vxn_bands = [(14,20,'<20\nCalma'),(20,23,'20-23\nNormal'),(23,27,'23-27\nElevado'),(27,60,'>27\nAlto')]
x5 = np.arange(len(vxn_bands))
pct_alc5 = []
ns5 = []
for vmin, vmax, lbl in vxn_bands:
    seg = mar[(mar['vxn_final'] >= vmin) & (mar['vxn_final'] < vmax)]
    ns5.append(len(seg))
    pct_alc5.append(100*seg['alcista'].mean() if len(seg)>0 else 0)

colors5 = [CYAN if p >= 60 else (YELLOW if p >= 50 else RED) for p in pct_alc5]
bars5 = ax5.bar(x5, pct_alc5, color=colors5, alpha=0.85, edgecolor='#1e2d4a', width=0.6)
ax5.axhline(50, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
ax5.set_xticks(x5)
ax5.set_xticklabels([l for _, _, l in vxn_bands], fontsize=8, color=GRAY)
ax5.set_ylabel('% Martes Alcistas', color=GRAY, fontsize=8)
ax5.set_ylim(0, 105)
for bar, pct, n_v in zip(bars5, pct_alc5, ns5):
    ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{pct:.0f}%\nn={n_v}', ha='center', va='bottom', fontsize=9.5, color=WHITE, fontweight='bold')

# ── P6: VIX como filtro ──────────────────────────────────────────────────────
ax6 = fig.add_subplot(gs[1, 2])
ax_style(ax6, '6. % Alcistas segun banda de VIX\n(SP500 volatilidad)')
vix_bands = [(10,18,'<18\nCalma'),(18,22,'18-22\nNormal'),(22,28,'22-28\nElevado'),(28,80,'>28\nPanico')]
x6 = np.arange(len(vix_bands))
pct_alc6 = []
ns6 = []
for vmin, vmax, lbl in vix_bands:
    seg = mar[(mar['vix'] >= vmin) & (mar['vix'] < vmax)]
    ns6.append(len(seg))
    pct_alc6.append(100*seg['alcista'].mean() if len(seg)>0 else 0)

colors6 = [CYAN if p >= 60 else (YELLOW if p >= 50 else RED) for p in pct_alc6]
bars6 = ax6.bar(x6, pct_alc6, color=colors6, alpha=0.85, edgecolor='#1e2d4a', width=0.6)
ax6.axhline(50, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
ax6.set_xticks(x6)
ax6.set_xticklabels([l for _, _, l in vix_bands], fontsize=8, color=GRAY)
ax6.set_ylabel('% Martes Alcistas', color=GRAY, fontsize=8)
ax6.set_ylim(0, 105)
for bar, pct, n_v in zip(bars6, pct_alc6, ns6):
    ax6.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
             f'{pct:.0f}%\nn={n_v}', ha='center', va='bottom', fontsize=9.5, color=WHITE, fontweight='bold')

# ── P7: Scatter VXN vs COT coloreado por tipo ────────────────────────────────
ax7 = fig.add_subplot(gs[2, :2])
ax_style(ax7, '7. VXN vs COT Index — cada martes coloreado por resultado\n(zona verde = condiciones favorables para alcista)')
for grp, col, lbl, alpha in [(alc, GREEN, 'ALCISTA', 0.9), (baj, RED, 'BAJISTA', 0.85)]:
    sc = ax7.scatter(grp['vxn_final'], grp['cot_idx'],
                     c=col, alpha=alpha, s=100, edgecolors=WHITE, linewidths=0.5,
                     label=lbl, zorder=5)
    for _, r in grp.iterrows():
        ax7.annotate(r['date'].strftime('%m/%d'), (r['vxn_final'], r['cot_idx']),
                     fontsize=6.5, color=col, xytext=(3, 3), textcoords='offset points')

# Zona ideal (VXN<25, COT>55)
from matplotlib.patches import FancyBboxPatch
ax7.axhline(50, color=YELLOW, linewidth=1.2, linestyle='--', alpha=0.6, label='COT=50 (neutro)')
ax7.axhline(70, color=GREEN,  linewidth=1,   linestyle=':', alpha=0.5, label='COT=70 (muy alc)')
ax7.axvline(25, color=RED,    linewidth=1.2, linestyle='--', alpha=0.6, label='VXN=25')
ax7.set_xlabel('VXN (volatilidad NQ)', color=GRAY, fontsize=9)
ax7.set_ylabel('COT Index (posicion institucional)', color=GRAY, fontsize=9)
ax7.legend(fontsize=8, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# ── P8: Scatter VIX vs COT ───────────────────────────────────────────────────
ax8 = fig.add_subplot(gs[2, 2])
ax_style(ax8, '8. VIX vs COT\n(SP500 vol. vs inst. posicion)')
for grp, col, lbl in [(alc, GREEN, 'ALCISTA'), (baj, RED, 'BAJISTA')]:
    ax8.scatter(grp['vix'], grp['cot_idx'],
                c=col, alpha=0.85, s=80, edgecolors=WHITE, linewidths=0.5, label=lbl)
    for _, r in grp.iterrows():
        if pd.notna(r['vix']):
            ax8.annotate(r['date'].strftime('%m/%d'), (r['vix'], r['cot_idx']),
                         fontsize=6, color=col, xytext=(2,2), textcoords='offset points')
ax8.axhline(50, color=YELLOW, linewidth=1, linestyle='--', alpha=0.6)
ax8.axvline(22, color=RED, linewidth=1, linestyle='--', alpha=0.6, label='VIX=22')
ax8.set_xlabel('VIX', color=GRAY, fontsize=8)
ax8.set_ylabel('COT Index', color=GRAY, fontsize=8)
ax8.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# ── P9: Tabla comparativa ALCISTAS ────────────────────────────────────────────
ax9 = fig.add_subplot(gs[3, :])
ax_style(ax9, 'TABLA ALCISTAS — ordenados por patron (con VXN, VIX, COT)')
ax9.axis('off')

PAT_COLORS_MAP = {
    'A — TRAMPA BAJISTA':    '#ff3355',
    'B — CONTINUACION LIMPIA': '#00ff88',
    'C — RANGO COMPLETO':    '#ffd60a',
    'D — ALCISTA CONTENIDO': '#00f2ff',
    'E — NEUTRAL->ALZA':     '#a78bfa',
    'OTRO':                  '#888888',
}

headers = ['Fecha','Patron','PM','VXN','VIX','COT','Bar.VAL','Romp.VAH','Cierre','Move','Rango']
rows = [headers]
for pat in list(PAT_COLORS_MAP.keys()):
    for _, r in alc[alc['patron']==pat].sort_values('date').iterrows():
        cierre = 'ENCIMA' if r['close_above_va'] else ('BAJO' if r['close_below_va'] else 'DENTRO')
        rows.append([
            r['date'].strftime('%Y-%m-%d'), pat,
            r['pm_direction'][:4],
            f"{r['vxn_final']:.1f}" if pd.notna(r['vxn_final']) else '-',
            f"{r['vix']:.1f}"      if pd.notna(r['vix'])       else '-',
            f"{r['cot_idx']:.0f}"  if pd.notna(r['cot_idx'])   else '-',
            'SI' if r['breaks_val'] else 'no',
            'SI' if r['breaks_vah'] else 'no',
            cierre,
            f"+{r['ny_move_pts']:.0f}",
            f"{r['ny_range']:.0f}",
        ])

t = ax9.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(8.5); t.scale(1, 1.68)
for (row, col), cell in t.get_celld().items():
    cell.set_facecolor('#0a0f1e' if row == 0 else ('#0d1628' if row%2==0 else '#0f1c30'))
    cell.set_edgecolor('#1e2d4a')
    txt = cell.get_text()
    if row == 0:
        txt.set_color(CYAN); txt.set_fontweight('bold')
    else:
        v = rows[row][col]
        pat_r = rows[row][1]
        if col == 1:
            txt.set_color(PAT_COLORS_MAP.get(pat_r, GRAY)); txt.set_fontweight('bold')
        elif v == 'SI': txt.set_color(GREEN); txt.set_fontweight('bold')
        elif v == 'no': txt.set_color(GRAY)
        elif v == 'ENCIMA': txt.set_color(GREEN); txt.set_fontweight('bold')
        elif v == 'BAJO': txt.set_color(RED)
        elif '+' in str(v): txt.set_color(GREEN); txt.set_fontweight('bold')
        else: txt.set_color(WHITE)

# ── P10: Tabla BAJISTAS ──────────────────────────────────────────────────────
ax10 = fig.add_subplot(gs[4, :])
ax_style(ax10, 'TABLA BAJISTAS — los 11 martes que bajaron (con VXN, VIX, COT)')
ax10.axis('off')

headers_b = ['Fecha','PM Dir','VXN','VIX','COT','Bar.VAL','Romp.VAL','Cierre','Move','Rango','Lunes prev']
rows_b = [headers_b]
for _, r in baj.sort_values('date').iterrows():
    cierre = 'ENCIMA' if r['close_above_va'] else ('BAJO' if r['close_below_va'] else 'DENTRO')
    lun_str = f"{r['move_lunes']:+.0f}" if pd.notna(r.get('move_lunes')) else '-'
    rows_b.append([
        r['date'].strftime('%Y-%m-%d'),
        r['pm_direction'][:4],
        f"{r['vxn_final']:.1f}" if pd.notna(r['vxn_final']) else '-',
        f"{r['vix']:.1f}"       if pd.notna(r['vix'])        else '-',
        f"{r['cot_idx']:.0f}"   if pd.notna(r['cot_idx'])    else '-',
        'SI' if r['breaks_val'] else 'no',
        'SI' if r['breaks_val'] else 'no',
        cierre,
        f"{r['ny_move_pts']:+.0f}",
        f"{r['ny_range']:.0f}",
        lun_str,
    ])

t2 = ax10.table(cellText=rows_b[1:], colLabels=rows_b[0], loc='center', cellLoc='center')
t2.auto_set_font_size(False); t2.set_fontsize(8.5); t2.scale(1, 1.68)
for (row, col), cell in t2.get_celld().items():
    cell.set_facecolor('#0a0f1e' if row == 0 else ('#200a0a' if row%2==0 else '#2a0f0f'))
    cell.set_edgecolor('#3a1e1e')
    txt = cell.get_text()
    if row == 0:
        txt.set_color(RED); txt.set_fontweight('bold')
    else:
        v = rows_b[row][col]
        if col == 8 and '-' in str(v): txt.set_color(RED); txt.set_fontweight('bold')
        elif v == 'SI': txt.set_color(YELLOW)
        elif v == 'BAJO': txt.set_color(RED); txt.set_fontweight('bold')
        else: txt.set_color(WHITE)

out = os.path.join(BASE, 'martes_alcistas_vxn_vix_cot.png')
plt.savefig(out, dpi=135, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] -> {out}")
