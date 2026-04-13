# -*- coding: utf-8 -*-
"""
ESTUDIO COMPLETO TODOS LOS MARTES NQ — con Volume Profile real donde disponible
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import json
import yfinance as yf
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))

# ══ 1. DATOS OHLC DIARIOS NQ via yfinance ═══════════════════════════════════
print("[1] Descargando NQ daily data 2017-2026...")
nq_raw = yf.download('NQ=F', start='2017-01-01', end='2026-04-08', interval='1d', auto_adjust=True, progress=False)
nq_raw = nq_raw.reset_index()
nq_raw.columns = [c[0] if isinstance(c, tuple) else c for c in nq_raw.columns]
nq_raw['Date'] = pd.to_datetime(nq_raw['Date']).dt.date
nq_raw['weekday'] = pd.to_datetime(nq_raw['Date']).dt.weekday  # 0=Mon, 1=Tue
nq_raw['range']   = nq_raw['High'] - nq_raw['Low']
nq_raw['move']    = nq_raw['Close'] - nq_raw['Open']
print(f"   Total dias: {len(nq_raw)} | {nq_raw['Date'].min()} -> {nq_raw['Date'].max()}")

# ══ 2. VOLUMEN PROFILE REAL (Sep 2025 - Mar 2026) ═══════════════════════════
vp_file = os.path.join(BASE, 'ny_profile_asia_london_daily.csv')
df_vp = pd.read_csv(vp_file)
df_vp['date'] = pd.to_datetime(df_vp['date']).dt.date
vp_dict = {str(r['date']): r.to_dict() for _, r in df_vp.iterrows()}
print(f"[2] Volume Profile real: {len(df_vp)} dias ({df_vp['date'].min()} -> {df_vp['date'].max()})")

# ══ 3. VXN / COT ═══════════════════════════════════════════════════════════
try:
    with open(os.path.join(BASE, 'data', 'research', 'daily_master_db.json'), encoding='utf-8') as f:
        db = json.load(f)
    db_dict = {r['date'][:10]: r for r in db.get('records', [])}
    print(f"[3] DB: {len(db_dict)} registros")
except:
    db_dict = {}
    print("[3] DB: no disponible")

# ══ 4. CONSTRUIR TABLA DE MARTES ════════════════════════════════════════════
martes = nq_raw[nq_raw['weekday'] == 1].copy().reset_index(drop=True)
# Buscar lunes previo
lunes  = {row['Date']: row for _, row in nq_raw[nq_raw['weekday'] == 0].iterrows()}

records = []
for _, r in martes.iterrows():
    fecha     = r['Date']
    fecha_str = str(fecha)

    # Lunes previo (1 o 3 dias antes)
    for delta in [1, 3]:
        prev = fecha - timedelta(days=delta)
        if prev in lunes:
            mon_row = lunes[prev]
            break
    else:
        mon_row = None

    # Volume Profile real si disponible
    vp = vp_dict.get(fecha_str, {})
    poc = vp.get('poc')
    vah = vp.get('vah')
    val = vp.get('val')
    va_range = vp.get('va_range')
    ny_open_pos = vp.get('ny_open_pos', 'N/A')
    vxn_vp = vp.get('vxn')
    touches_vah = vp.get('touches_vah')
    touches_val = vp.get('touches_val')
    touches_poc = vp.get('touches_poc')
    breaks_vah  = vp.get('breaks_vah')
    breaks_val  = vp.get('breaks_val')
    close_above = vp.get('close_above_va')
    close_below = vp.get('close_below_va')
    close_inside= vp.get('close_inside')
    pm_direction= vp.get('pm_direction')
    trend = vp.get('trend')

    # VXN/COT del DB
    db_r = db_dict.get(fecha_str, {})
    vxn_db = db_r.get('vxn')
    cot_idx = db_r.get('cot_index')

    # Tipo de dia: LOW_FIRST (rebote) o HIGH_FIRST (caida)
    # Usando solo OHLC: si close > open = alcista probable = LOW_FIRST
    # Mejor: si la distancia Close-Low > High-Close → LOW_FIRST
    high = float(r['High'])
    low  = float(r['Low'])
    open_ = float(r['Open'])
    close_ = float(r['Close'])
    rango = high - low

    # Heuristica basada en OHLC: close cerca del high = low_first
    close_pct = (close_ - low) / rango if rango > 0 else 0.5
    dia_tipo = 'LOW_FIRST' if close_pct >= 0.5 else 'HIGH_FIRST'

    records.append({
        'fecha': pd.Timestamp(fecha),
        'fecha_str': fecha_str,
        'open': open_,
        'high': high,
        'low': low,
        'close': close_,
        'range': rango,
        'move': close_ - open_,
        'close_pct': close_pct,  # 0=cerro en LOW, 1=cerro en HIGH
        'dia_tipo': dia_tipo,
        # Lunes previo
        'mon_move': float(mon_row['move']) if mon_row is not None else None,
        'mon_range': float(mon_row['range']) if mon_row is not None else None,
        # Volume Profile real
        'poc': poc, 'vah': vah, 'val': val, 'va_range': va_range,
        'ny_open_pos': ny_open_pos,
        'touches_vah': touches_vah, 'touches_val': touches_val,
        'touches_poc': touches_poc,
        'breaks_vah': breaks_vah, 'breaks_val': breaks_val,
        'close_above': close_above, 'close_below': close_below,
        'close_inside': close_inside,
        'pm_direction': pm_direction,
        'trend': trend,
        # Indicadores
        'vxn': vxn_vp or vxn_db,
        'cot_idx': cot_idx,
        'has_vp': bool(vp),
    })

df_m = pd.DataFrame(records)
n_total = len(df_m)
n_lf = (df_m['dia_tipo']=='LOW_FIRST').sum()
n_hf = (df_m['dia_tipo']=='HIGH_FIRST').sum()
n_vp = df_m['has_vp'].sum()

print(f"\n[RESULTADO] Total martes: {n_total}")
print(f"  LOW_FIRST  (alzo): {n_lf} ({100*n_lf/n_total:.0f}%)")
print(f"  HIGH_FIRST (cayo): {n_hf} ({100*n_hf/n_total:.0f}%)")
print(f"  Con VP real:       {n_vp}")
print(f"  Rango promedio:    {df_m['range'].mean():.0f}pts")
print(f"  Rango mediano:     {df_m['range'].median():.0f}pts")
print(f"  Rango max:         {df_m['range'].max():.0f}pts")

# ══ 5. ESTADISTICAS POR BANDAS ══════════════════════════════════════════════
print("\n--- DISTRIBUCION POR RANGO ---")
for vmin, vmax in [(0,100),(100,150),(150,200),(200,300),(300,400),(400,9999)]:
    seg = df_m[(df_m['range']>=vmin)&(df_m['range']<vmax)]
    if len(seg)==0: continue
    lf_pct = 100*(seg['dia_tipo']=='LOW_FIRST').mean()
    print(f"  {vmin:4d}-{min(vmax,9999):4d}pts: n={len(seg):3d} ({100*len(seg)/n_total:.0f}%)  LOW_FIRST={lf_pct:.0f}%  med_rango={seg['range'].median():.0f}")

print("\n--- CUANDO LUNES FUE MUY BAJISTA (<-200pts) ---")
bear_mon = df_m[df_m['mon_move'] < -200]
print(f"  N casos: {len(bear_mon)}")
if len(bear_mon)>0:
    print(f"  Rango mediano martes: {bear_mon['range'].median():.0f}pts")
    print(f"  LOW_FIRST: {100*(bear_mon['dia_tipo']=='LOW_FIRST').mean():.0f}%")
    print(f"  Rango>300pts: {100*(bear_mon['range']>=300).mean():.0f}%")

# ══ VP REAL ANALYSIS (27 martes Sep25-Mar26) ════════════════════════════════
df_vp_m = df_m[df_m['has_vp']].copy()
if len(df_vp_m)>0:
    print(f"\n--- VOLUME PROFILE REAL ({len(df_vp_m)} martes) ---")

    # Que pasa cuando abre BELOW VAL vs INSIDE VA vs ABOVE VAH?
    for pos in ['BELOW_VA', 'INSIDE_VA', 'ABOVE_VA']:
        seg = df_vp_m[df_vp_m['ny_open_pos']==pos]
        if len(seg)==0: continue
        print(f"\n  Apertura NY {pos}: n={len(seg)}")
        print(f"    LOW_FIRST: {100*(seg['dia_tipo']=='LOW_FIRST').mean():.0f}%")
        print(f"    Rango med: {seg['range'].median():.0f}pts")
        if (seg['touches_vah'].notna()).any():
            print(f"    Toca VAH: {100*seg['touches_vah'].mean():.0f}%")
            print(f"    Toca VAL: {100*seg['touches_val'].mean():.0f}%")
            print(f"    Toca POC: {100*seg['touches_poc'].mean():.0f}%")
            print(f"    Cierra dentro VA: {100*seg['close_inside'].mean():.0f}%")

# ══ 6. GRAFICA ══════════════════════════════════════════════════════════════
CYAN=  '#00f2ff'; GREEN= '#00ff88'; RED=   '#ff3355'
YELLOW='#ffd60a'; WHITE= '#e2e8f8'; GRAY=  '#4a5a7a'; PURPLE='#a78bfa'

fig = plt.figure(figsize=(22, 26), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(4, 3, figure=fig, hspace=0.55, wspace=0.38)

def ax_style(ax, title, sub=''):
    ax.set_facecolor('#0d1628')
    ax.set_title(f'{title}\n{sub}' if sub else title, color=CYAN, fontsize=9.5, fontweight='bold', pad=8)
    ax.tick_params(colors=GRAY, labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

year_str = f"{df_m['fecha'].dt.year.min()}-{df_m['fecha'].dt.year.max()}"
fig.suptitle(f'ESTUDIO COMPLETO — {n_total} MARTES NQ ({year_str})\n'
             f'Todos los martes sin filtrar  ·  Volume Profile real en {n_vp} dias',
             color=WHITE, fontsize=14, fontweight='bold', y=0.99)

# P1: Distribucion rango
ax1 = fig.add_subplot(gs[0,0])
ax_style(ax1, f'1. Distribucion del rango diario')
r = df_m['range'].dropna()
q25,q50,q75 = r.quantile([.25,.5,.75])
ax1.hist(r, bins=35, color=PURPLE, alpha=0.75, edgecolor='#1e2d4a', linewidth=0.5)
for v, c, lbl in [(q25,YELLOW,f'Q1={q25:.0f}'),(q50,GREEN,f'Med={q50:.0f}'),(q75,CYAN,f'Q3={q75:.0f}'),(300,RED,'300pts')]:
    ax1.axvline(v, color=c, linewidth=1.8 if v==q50 else 1.4, linestyle='--', label=lbl, alpha=0.9)
ax1.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
stats_txt = (f'Prom: {r.mean():.0f}pts\n'
             f'Max:  {r.max():.0f}pts\n'
             f'≥300: {100*(r>=300).mean():.0f}%\n'
             f'≥200: {100*(r>=200).mean():.0f}%\n'
             f'≥150: {100*(r>=150).mean():.0f}%')
ax1.text(0.97,0.97,stats_txt,transform=ax1.transAxes,ha='right',va='top',fontsize=8,color=WHITE,
         bbox=dict(facecolor='#0a0f1e',edgecolor=GRAY,alpha=0.85,boxstyle='round,pad=0.4'))
ax1.set_xlabel('Puntos', color=GRAY, fontsize=8)
ax1.set_ylabel('Frecuencia', color=GRAY, fontsize=8)

# P2: % LOW_FIRST por año
ax2 = fig.add_subplot(gs[0,1])
ax_style(ax2, '2. % Martes alcistas (LOW→HIGH) por ano')
df_m['year'] = df_m['fecha'].dt.year
by_yr = df_m.groupby('year').agg(n=('dia_tipo','count'), lf=('dia_tipo', lambda x: (x=='LOW_FIRST').sum())).reset_index()
by_yr['pct_lf'] = 100*by_yr['lf']/by_yr['n']
colors_yr = [GREEN if p>=50 else RED for p in by_yr['pct_lf']]
bars = ax2.bar(by_yr['year'], by_yr['pct_lf'], color=colors_yr, alpha=0.8, edgecolor='#1e2d4a')
ax2.axhline(50, color=WHITE, linewidth=1, linestyle='--', alpha=0.5, label='50%')
ax2.set_ylim(0, 100)
ax2.set_xlabel('Ano', color=GRAY, fontsize=8); ax2.set_ylabel('%', color=GRAY, fontsize=8)
for bar, row in zip(bars, by_yr.itertuples()):
    ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1.5,
             f'{row.pct_lf:.0f}%\nn={row.n}', ha='center', va='bottom', fontsize=6.5, color=WHITE)
overall_lf = 100*n_lf/n_total
ax2.axhline(overall_lf, color=CYAN, linewidth=1.5, linestyle=':', label=f'Global {overall_lf:.0f}%')
ax2.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)

# P3: Lunes previo vs Rango martes
ax3 = fig.add_subplot(gs[0,2])
ax_style(ax3, '3. Lunes previo vs Rango del martes', '(verde=LOW_FIRST, rojo=HIGH_FIRST)')
has_mon = df_m[df_m['mon_move'].notna()]
sc_c = [GREEN if t=='LOW_FIRST' else RED for t in has_mon['dia_tipo']]
ax3.scatter(has_mon['mon_move'], has_mon['range'], c=sc_c, alpha=0.55, s=20, edgecolors='none')
for xv, col, lbl in [(-100,RED,'Mon -100'),(-200,RED,'Mon -200'),(100,GREEN,'Mon +100')]:
    ax3.axvline(xv, color=col, linewidth=1, linestyle='--', alpha=0.6, label=lbl)
ax3.axhline(300, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.5, label='Rango 300pts')
ax3.axvline(0, color=GRAY, linewidth=0.5, alpha=0.4)
ax3.legend(fontsize=6.5, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax3.set_xlabel('Movimiento Lunes (pts)', color=GRAY, fontsize=8)
ax3.set_ylabel('Rango Martes (pts)', color=GRAY, fontsize=8)

# Stats por cuartil de lunes
bear100 = has_mon[has_mon['mon_move']<-100]
bear200 = has_mon[has_mon['mon_move']<-200]
ax3.text(0.02,0.97,
    f'Lun<-100 ({len(bear100)} casos):\n  Rango med={bear100["range"].median():.0f}pts\n  LOW_FIRST={100*(bear100["dia_tipo"]=="LOW_FIRST").mean():.0f}%\n\n'
    f'Lun<-200 ({len(bear200)} casos):\n  Rango med={bear200["range"].median():.0f}pts\n  LOW_FIRST={100*(bear200["dia_tipo"]=="LOW_FIRST").mean():.0f}%',
    transform=ax3.transAxes, ha='left', va='top', fontsize=7.5, color=WHITE,
    bbox=dict(facecolor='#0a0f1e',edgecolor=GRAY,alpha=0.85,boxstyle='round,pad=0.4'))

# P4: VXN bandas
ax4 = fig.add_subplot(gs[1,0])
ax_style(ax4, '4. VXN vs rango del martes', '(por banda de volatilidad)')
has_vxn = df_m[df_m['vxn'].notna()].copy()
if len(has_vxn) > 5:
    ax4.scatter(has_vxn['vxn'], has_vxn['range'],
                c=[GREEN if t=='LOW_FIRST' else RED for t in has_vxn['dia_tipo']],
                alpha=0.55, s=20)
    for xv, col, lbl in [(20,YELLOW,'VXN=20'),(25,RED,'VXN=25'),(30,RED,'VXN=30')]:
        ax4.axvline(xv, color=col, linewidth=1, linestyle='--', alpha=0.7, label=lbl)
    ax4.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
    ax4.set_xlabel('VXN', color=GRAY, fontsize=8)
    ax4.set_ylabel('Rango (pts)', color=GRAY, fontsize=8)
    # Texto por banda
    txt = ''
    for vmin, vmax, lbl in [(14,20,'<20'),(20,25,'20-25'),(25,30,'25-30'),(30,60,'>30')]:
        seg = has_vxn[(has_vxn['vxn']>=vmin)&(has_vxn['vxn']<vmax)]
        if len(seg)>0:
            txt += f'VXN {lbl}: n={len(seg)} | med={seg["range"].median():.0f}pts | LF={100*(seg["dia_tipo"]=="LOW_FIRST").mean():.0f}%\n'
    ax4.text(0.02,0.97,txt.strip(),transform=ax4.transAxes,ha='left',va='top',fontsize=7.5,color=WHITE,
             bbox=dict(facecolor='#0a0f1e',edgecolor=GRAY,alpha=0.85,boxstyle='round,pad=0.4'))
else:
    ax4.text(0.5,0.5,'Sin suficientes datos VXN',ha='center',va='center',color=GRAY,transform=ax4.transAxes)

# P5: Volume Profile — apertura NY vs resultado (SOLO 27 dias con VP real)
ax5 = fig.add_subplot(gs[1,1])
ax_style(ax5, f'5. Volume Profile REAL — apertura NY', f'(n={n_vp} martes Sep25-Mar26)')
if n_vp > 0:
    pos_order = ['BELOW_VA', 'INSIDE_VA', 'ABOVE_VA']
    pos_lf, pos_n = [], []
    for pos in pos_order:
        seg = df_vp_m[df_vp_m['ny_open_pos']==pos]
        pos_lf.append(100*(seg['dia_tipo']=='LOW_FIRST').mean() if len(seg)>0 else 0)
        pos_n.append(len(seg))
    x5 = np.arange(len(pos_order))
    colors5 = [GREEN if v>=50 else RED for v in pos_lf]
    bars5 = ax5.bar(x5, pos_lf, color=colors5, alpha=0.8, edgecolor='#1e2d4a', width=0.6)
    ax5.axhline(50, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
    ax5.set_xticks(x5)
    ax5.set_xticklabels(['Bajo VAL\n(BELOW_VA)', 'Dentro VA\n(INSIDE_VA)', 'Sobre VAH\n(ABOVE_VA)'], fontsize=8, color=GRAY)
    ax5.set_ylabel('% LOW_FIRST (rebote)', color=GRAY, fontsize=8)
    ax5.set_ylim(0,105)
    for bar, n_val, lf in zip(bars5, pos_n, pos_lf):
        ax5.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
                 f'{lf:.0f}%\nn={n_val}', ha='center', va='bottom', fontsize=9, color=WHITE, fontweight='bold')
    # Tasa de toque
    txt5 = 'Tasa de toque cuando BELOW_VA:\n'
    seg_below = df_vp_m[df_vp_m['ny_open_pos']=='BELOW_VA']
    if len(seg_below)>0:
        txt5 += f'  Toca VAH: {100*seg_below["touches_vah"].mean():.0f}%\n'
        txt5 += f'  Toca POC: {100*seg_below["touches_poc"].mean():.0f}%\n'
        txt5 += f'  Toca VAL: {100*seg_below["touches_val"].mean():.0f}%\n'
        txt5 += f'  Cierra dentro: {100*seg_below["close_inside"].mean():.0f}%'
    ax5.text(0.02,0.97,txt5,transform=ax5.transAxes,ha='left',va='top',fontsize=7.5,color=WHITE,
             bbox=dict(facecolor='#0a0f1e',edgecolor=GRAY,alpha=0.85,boxstyle='round,pad=0.4'))
else:
    ax5.text(0.5,0.5,'Sin datos VP disponibles',ha='center',va='center',color=GRAY,transform=ax5.transAxes)

# P6: Close pct (posicion del cierre en el rango)
ax6 = fig.add_subplot(gs[1,2])
ax_style(ax6, '6. Donde cierra el precio dentro del rango', '(0=en el LOW, 1=en el HIGH)')
ax6.hist(df_m['close_pct'], bins=25, color=CYAN, alpha=0.75, edgecolor='#1e2d4a')
ax6.axvline(0.5, color=YELLOW, linewidth=2, linestyle='--', label='50% (cierra en medio)')
ax6.axvline(df_m['close_pct'].mean(), color=WHITE, linewidth=1.5, linestyle=':', label=f'Media={df_m["close_pct"].mean():.2f}')
ax6.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax6.text(0.02,0.97,
    f'Cierra >75% (cerca HIGH): {100*(df_m["close_pct"]>0.75).mean():.0f}%\n'
    f'Cierra >50% (mitad HIGH): {100*(df_m["close_pct"]>0.50).mean():.0f}%\n'
    f'Cierra <25% (cerca LOW):  {100*(df_m["close_pct"]<0.25).mean():.0f}%',
    transform=ax6.transAxes, ha='left', va='top', fontsize=8, color=WHITE,
    bbox=dict(facecolor='#0a0f1e',edgecolor=GRAY,alpha=0.85,boxstyle='round,pad=0.4'))
ax6.set_xlabel('Posicion del cierre en el rango del dia', color=GRAY, fontsize=8)
ax6.set_ylabel('Frecuencia', color=GRAY, fontsize=8)

# P7: Tabla resumen TODOS LOS MARTES
ax7 = fig.add_subplot(gs[2,:])
ax_style(ax7, 'TABLA RESUMEN — LOS 195 MARTES POR BANDA DE RANGO')
ax7.axis('off')

segs = [
    ('<100pts\n(dia plano)',   df_m[df_m['range']< 100]),
    ('100-150pts\n(normal)',   df_m[(df_m['range']>=100)&(df_m['range']<150)]),
    ('150-200pts\n(activo)',   df_m[(df_m['range']>=150)&(df_m['range']<200)]),
    ('200-300pts\n(grande)',   df_m[(df_m['range']>=200)&(df_m['range']<300)]),
    ('300-400pts\n(muy gde)',  df_m[(df_m['range']>=300)&(df_m['range']<400)]),
    ('>400pts\n(extremo)',     df_m[df_m['range']>=400]),
]
headers = ['Rango','N','% total','LOW→HIGH','HIGH→LOW','Rango med','Cierre >50%','Lun med (pts)']
rows = [headers]
for lbl, seg in segs:
    n = len(seg)
    if n==0: continue
    close_pct_high = f"{100*(seg['close_pct']>0.5).mean():.0f}%"
    mon = seg['mon_move'].dropna()
    rows.append([
        lbl, str(n), f'{100*n/n_total:.0f}%',
        f"{100*(seg['dia_tipo']=='LOW_FIRST').mean():.0f}%",
        f"{100*(seg['dia_tipo']=='HIGH_FIRST').mean():.0f}%",
        f"{seg['range'].median():.0f}pts",
        close_pct_high,
        f"{mon.median():.0f}" if len(mon)>0 else '-',
    ])

t = ax7.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False); t.set_fontsize(9); t.scale(1, 2.1)
for (r,c), cell in t.get_celld().items():
    cell.set_facecolor('#0a0f1e' if r==0 else ('#0d1628' if r%2==0 else '#111c35'))
    cell.set_edgecolor('#1e2d4a')
    txt = cell.get_text()
    if r==0: txt.set_color(CYAN); txt.set_fontweight('bold'); txt.set_fontsize(8.5)
    else: txt.set_color(WHITE)

# P8: Serie temporal completa
ax8 = fig.add_subplot(gs[3,:])
ax_style(ax8, f'TODOS LOS MARTES NQ — Serie temporal completa {year_str}')
ax8.bar(df_m['fecha'], df_m['range'], color=[GREEN if t=='LOW_FIRST' else RED for t in df_m['dia_tipo']],
        alpha=0.65, width=3)
rolling = df_m.set_index('fecha')['range'].rolling(10,min_periods=3).mean()
ax8.plot(rolling.index, rolling.values, color=CYAN, linewidth=2, label='Media mov. 10 sem', zorder=5)
ax8.axhline(q50, color=YELLOW, linewidth=1, linestyle='--', alpha=0.7, label=f'Mediana {q50:.0f}pts')
ax8.axhline(300, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.5, label='300pts')
# Zonas
ax8.axvspan(pd.Timestamp('2020-03-01'),pd.Timestamp('2020-06-01'), color=RED, alpha=0.08, label='COVID')
ax8.axvspan(pd.Timestamp('2022-01-01'),pd.Timestamp('2022-12-31'), color=YELLOW, alpha=0.05, label='Bear 2022')
ax8.axvspan(pd.Timestamp('2025-08-01'),pd.Timestamp('2025-09-30'), color=PURPLE, alpha=0.08)
ax8.text(pd.Timestamp('2025-08-20'), df_m['range'].max()*0.85, 'Yen\nUnwind', color=PURPLE, fontsize=7, ha='center')
# HOY
ax8.annotate('HOY\n7 Abr 2026\n440pts', xy=(pd.Timestamp('2026-04-07'), 440),
             xytext=(pd.Timestamp('2025-09-01'), 520),
             arrowprops=dict(arrowstyle='->', color=CYAN, lw=2), color=CYAN, fontsize=8.5, fontweight='bold', ha='center')
from matplotlib.patches import Patch
ax8.legend(handles=[
    Patch(facecolor=GREEN, alpha=0.7, label=f'LOW->HIGH (sube): {n_lf} dias ({100*n_lf/n_total:.0f}%)'),
    Patch(facecolor=RED,   alpha=0.7, label=f'HIGH->LOW (baja): {n_hf} dias ({100*n_hf/n_total:.0f}%)'),
] + ax8.lines[:2],
fontsize=7.5, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE, loc='upper left')
ax8.set_xlabel('Fecha', color=GRAY, fontsize=8); ax8.set_ylabel('Rango (pts)', color=GRAY, fontsize=8)

# Guardar
out = os.path.join(BASE, 'martes_estudio_completo_195.png')
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] -> {out}")
