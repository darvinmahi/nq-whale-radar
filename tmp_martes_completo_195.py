# -*- coding: utf-8 -*-
"""
ESTUDIO COMPLETO — TODOS LOS MARTES NQ (2017-2026)
=====================================================
Sin filtros. Muestra que pasa en los 195 martes completos:
- Distribucion de movimientos
- Condiciones del lunes vs resultado del martes
- VXN y COT como predictores
- Hora del LOW y HIGH
- Rangos por cuartiles
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import os, json
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))

# ── Cargar datos ─────────────────────────────────────────────────────────────
df = pd.read_csv(os.path.join(BASE, 'nq_15m_intraday.csv'), parse_dates=['datetime'])
df = df.sort_values('datetime').reset_index(drop=True)
df['date']    = df['datetime'].dt.date
df['hour']    = df['datetime'].dt.hour
df['minute']  = df['datetime'].dt.minute
df['weekday'] = df['datetime'].dt.weekday  # 0=Lun, 1=Mar

# Sesion diaria (9:30 - 16:00 ET)
daily = df[(df['hour'] >= 9) & ~((df['hour'] == 9) & (df['minute'] < 30)) &
           (df['hour'] < 16)].copy()

agg = daily.groupby('date').agg(
    open  = ('open', 'first'),
    high  = ('high', 'max'),
    low   = ('low', 'min'),
    close = ('close', 'last'),
).reset_index()
agg['date']    = pd.to_datetime(agg['date'])
agg['weekday'] = agg['date'].dt.weekday
agg['range']   = agg['high'] - agg['low']
agg['move']    = agg['close'] - agg['open']  # positivo = ALCISTA

# Solo martes
martes = agg[agg['weekday'] == 1].copy().reset_index(drop=True)
martes['prev_date'] = martes['date'] - timedelta(days=1)

# Lunes previo
lunes  = agg[agg['weekday'] == 0].copy()
lunes_d = {row['date']: row for _, row in lunes.iterrows()}

records = []
for _, r in martes.iterrows():
    lun = lunes_d.get(r['prev_date'])
    if lun is None:
        prev_date2 = r['date'] - timedelta(days=3)  # viernes si lunes fue festivo
        lun = lunes_d.get(prev_date2)

    mon_move = float(lun['move']) if lun is not None else None
    mon_range= float(lun['range']) if lun is not None else None

    # Determinar si fue LOW->HIGH o HIGH->LOW
    # Buscar la hora del LOW y HIGH del martes
    mar_bars = df[(df['date'].dt.date == r['date'].date()) &
                  (df['hour'] >= 9) & ~((df['hour'] == 9) & (df['minute'] < 30)) &
                  (df['hour'] < 16)].copy()

    if mar_bars.empty:
        continue

    low_idx  = mar_bars['low'].idxmin()
    high_idx = mar_bars['high'].idxmax()
    low_time  = mar_bars.loc[low_idx, 'datetime']
    high_time = mar_bars.loc[high_idx, 'datetime']

    # Tipo de dia
    if low_time < high_time:
        dia_tipo = 'LOW_FIRST'   # bajo primero, luego sube
        move_total = float(r['high']) - float(r['low'])
    else:
        dia_tipo = 'HIGH_FIRST'  # sube primero, luego baja
        move_total = -(float(r['high']) - float(r['low']))

    records.append({
        'fecha': r['date'],
        'open': r['open'],
        'high': r['high'],
        'low':  r['low'],
        'close': r['close'],
        'range': r['range'],
        'close_move': r['move'],  # cierre vs apertura
        'move_total': move_total,  # positivo=rebote, negativo=caida
        'dia_tipo': dia_tipo,
        'low_hour': low_time.hour + low_time.minute/60,
        'high_hour': high_time.hour + high_time.minute/60,
        'low_time_str': low_time.strftime('%H:%M'),
        'high_time_str': high_time.strftime('%H:%M'),
        'mon_move': mon_move,
        'mon_range': mon_range,
    })

df_m = pd.DataFrame(records)
n_total = len(df_m)
print(f"\nTotal martes analizados: {n_total}")
print(f"  LOW primero (rebote): {(df_m['dia_tipo']=='LOW_FIRST').sum()} ({100*(df_m['dia_tipo']=='LOW_FIRST').mean():.0f}%)")
print(f"  HIGH primero (caida): {(df_m['dia_tipo']=='HIGH_FIRST').sum()} ({100*(df_m['dia_tipo']=='HIGH_FIRST').mean():.0f}%)")

# ── Cargar VXN/COT ───────────────────────────────────────────────────────────
try:
    with open(os.path.join(BASE, 'data', 'research', 'daily_master_db.json'), encoding='utf-8') as f:
        db = json.load(f)
    recs_db = {r['date'][:10]: r for r in db.get('records', [])}
    def get_vxn(fecha): return recs_db.get(str(fecha)[:10], {}).get('vxn')
    def get_cot(fecha): return recs_db.get(str(fecha)[:10], {}).get('cot_index')
    df_m['vxn'] = df_m['fecha'].apply(lambda x: get_vxn(x))
    df_m['cot_idx'] = df_m['fecha'].apply(lambda x: get_cot(x))
    print(f"  VXN disponible: {df_m['vxn'].notna().sum()} dias")
    print(f"  COT disponible: {df_m['cot_idx'].notna().sum()} dias")
except Exception as e:
    print(f"  [WARN] DB: {e}")
    df_m['vxn'] = None
    df_m['cot_idx'] = None

# ══════════════════════════════════════════════════════════════════════════════
# FIGURA PRINCIPAL: 4x4 paneles del estudio completo
# ══════════════════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(20, 24), facecolor='#0a0f1e')
gs  = gridspec.GridSpec(4, 3, figure=fig, hspace=0.55, wspace=0.35)

CYAN   = '#00f2ff'
GREEN  = '#00ff88'
RED    = '#ff3355'
YELLOW = '#ffd60a'
PURPLE = '#a78bfa'
GRAY   = '#4a5a7a'
WHITE  = '#e2e8f8'

def ax_style(ax, title):
    ax.set_facecolor('#0d1628')
    ax.set_title(title, color=CYAN, fontsize=10, fontweight='bold', pad=8)
    ax.tick_params(colors=GRAY, labelsize=8)
    for spine in ax.spines.values(): spine.set_color('#1e2d4a')
    ax.grid(True, color='#1e2d4a', alpha=0.5, linewidth=0.5)

fig.suptitle(f'ESTUDIO COMPLETO — {n_total} MARTES NQ (2017-2026)\n'
             f'Analisis sin filtros de todos los dias martes',
             color=WHITE, fontsize=14, fontweight='bold', y=0.98)

# ── Panel 1: Distribucion del rango diario ────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
ax_style(ax1, f'Rango promedio del dia martes')
ranges = df_m['range'].dropna()
q25, q50, q75 = ranges.quantile([0.25, 0.5, 0.75])
ax1.hist(ranges, bins=30, color=PURPLE, alpha=0.7, edgecolor='#1e2d4a')
ax1.axvline(q25,  color=YELLOW, linestyle='--', linewidth=1.5, label=f'Q1={q25:.0f}pts')
ax1.axvline(q50,  color=GREEN,  linestyle='--', linewidth=2,   label=f'Mediana={q50:.0f}pts')
ax1.axvline(q75,  color=CYAN,   linestyle='--', linewidth=1.5, label=f'Q3={q75:.0f}pts')
ax1.axvline(300,  color=RED,    linestyle='-',  linewidth=1, alpha=0.7, label='300pts')
leg = ax1.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax1.set_xlabel('Puntos', color=GRAY, fontsize=8)
ax1.set_ylabel('Frecuencia', color=GRAY, fontsize=8)
# Texto stats
pct_300 = 100*(ranges >= 300).mean()
pct_200 = 100*(ranges >= 200).mean()
pct_150 = 100*(ranges >= 150).mean()
ax1.text(0.97, 0.78, f'≥ 300pts: {pct_300:.0f}%\n≥ 200pts: {pct_200:.0f}%\n≥ 150pts: {pct_150:.0f}%',
         transform=ax1.transAxes, ha='right', va='top', fontsize=8, color=WHITE,
         bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.8, boxstyle='round'))

# ── Panel 2: LOW FIRST vs HIGH FIRST por año ────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
ax_style(ax2, 'Tipo de martes por año\n(LOW primero vs HIGH primero)')
df_m['year'] = df_m['fecha'].dt.year
por_anio = df_m.groupby('year')['dia_tipo'].value_counts(normalize=True).unstack(fill_value=0) * 100
anos = por_anio.index.tolist()
x = np.arange(len(anos))
w = 0.4
lf = por_anio.get('LOW_FIRST',  pd.Series(0, index=anos)).values
hf = por_anio.get('HIGH_FIRST', pd.Series(0, index=anos)).values
bars1 = ax2.bar(x - w/2, lf, w, color=GREEN, alpha=0.8, label='LOW→HIGH (rebote)')
bars2 = ax2.bar(x + w/2, hf, w, color=RED,   alpha=0.8, label='HIGH→LOW (caida)')
ax2.set_xticks(x)
ax2.set_xticklabels(anos, color=GRAY, fontsize=7)
ax2.set_ylabel('%', color=GRAY, fontsize=8)
ax2.axhline(50, color=YELLOW, linestyle='--', linewidth=1, alpha=0.6)
leg2 = ax2.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
for bar, val in zip(bars1, lf):
    if val > 0: ax2.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1, f'{val:.0f}%', ha='center', va='bottom', fontsize=6, color=GREEN)

# ── Panel 3: Hora del LOW en martes LOW_FIRST ────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
ax_style(ax3, 'A que hora se forma el LOW\n(en martes LOW→HIGH)')
lf_df = df_m[df_m['dia_tipo'] == 'LOW_FIRST']
bins_horas = np.arange(9.5, 16.5, 0.25)
ax3.hist(lf_df['low_hour'], bins=bins_horas, color=GREEN, alpha=0.75, edgecolor='#1e2d4a')
# Ventanas clave
ax3.axvspan(9.5,   10.0,  color=GREEN, alpha=0.12, label='9:30-10:00 ET')
ax3.axvspan(10.0,  10.5,  color=YELLOW, alpha=0.08, label='10:00-10:30 ET')
ax3.axvspan(10.83, 11.0,  color=PURPLE, alpha=0.12, label='SB Window 1')
ax3.axvline(lf_df['low_hour'].median(), color=CYAN, linewidth=2,
            label=f'Mediana={int(lf_df["low_hour"].median())}:{int((lf_df["low_hour"].median()%1)*60):02d}')
leg3 = ax3.legend(fontsize=6, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax3.set_xlabel('Hora ET', color=GRAY, fontsize=8)

# Estadisticas por cuartil de hora
antes_10 = 100*(lf_df['low_hour'] < 10.0).mean()
antes_1030 = 100*(lf_df['low_hour'] < 10.5).mean()
ax3.text(0.97, 0.97, f'Antes 10:00: {antes_10:.0f}%\nAntes 10:30: {antes_1030:.0f}%',
         transform=ax3.transAxes, ha='right', va='top', fontsize=8, color=WHITE,
         bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.8, boxstyle='round'))

# ── Panel 4: Lunes previo → resultado martes ─────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0])
ax_style(ax4, 'Movimiento del LUNES previo\nvs Rango del MARTES')
has_mon = df_m[df_m['mon_move'].notna()]
colors4 = [GREEN if t == 'LOW_FIRST' else RED for t in has_mon['dia_tipo']]
ax4.scatter(has_mon['mon_move'], has_mon['range'], c=colors4, alpha=0.6, s=25)
ax4.axvline(0, color=WHITE, linewidth=0.8, alpha=0.5)
ax4.axvline(-100, color=RED, linewidth=1, linestyle='--', alpha=0.6, label='Lunes -100pts')
ax4.axvline(-200, color=RED, linewidth=1.5, linestyle='--', alpha=0.8, label='Lunes -200pts')
ax4.axhline(200, color=YELLOW, linewidth=1, linestyle='--', alpha=0.6, label='Rango 200pts')
ax4.axhline(300, color=CYAN,   linewidth=1, linestyle='--', alpha=0.6, label='Rango 300pts')
leg4 = ax4.legend(fontsize=6, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax4.set_xlabel('Movimiento Lunes (pts)', color=GRAY, fontsize=8)
ax4.set_ylabel('Rango Martes (pts)', color=GRAY, fontsize=8)

# Cuadro correlation
from scipy import stats as sst
corr, pval = sst.pearsonr(has_mon['mon_move'].abs(), has_mon['range'])
# Cuando lunes < -100, q pasa el martes?
lun_bear = has_mon[has_mon['mon_move'] < -100]
lun_bull = has_mon[has_mon['mon_move'] > 100]
ax4.text(0.02, 0.97,
         f'Correlacion: r={corr:.2f} (p={pval:.3f})\n'
         f'Lun<-100: {len(lun_bear)} casos\n'
         f'  Rango mediano: {lun_bear["range"].median():.0f}pts\n'
         f'  LOW_FIRST: {100*(lun_bear["dia_tipo"]=="LOW_FIRST").mean():.0f}%',
         transform=ax4.transAxes, ha='left', va='top', fontsize=7.5, color=WHITE,
         bbox=dict(facecolor='#0a0f1e', edgecolor=GRAY, alpha=0.8, boxstyle='round'))

# ── Panel 5: VXN vs Rango Martes ─────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 1])
ax_style(ax5, 'VXN vs Rango del Martes\n(cuanto depende el rango del VXN)')
has_vxn = df_m[df_m['vxn'].notna()].copy()
ax5.scatter(has_vxn['vxn'], has_vxn['range'],
            c=[GREEN if t=='LOW_FIRST' else RED for t in has_vxn['dia_tipo']],
            alpha=0.6, s=25)
# Linea de tendencia
if len(has_vxn) > 3:
    z = np.polyfit(has_vxn['vxn'].astype(float), has_vxn['range'].astype(float), 1)
    p = np.poly1d(z)
    vxn_x = np.linspace(has_vxn['vxn'].min(), has_vxn['vxn'].max(), 100)
    ax5.plot(vxn_x, p(vxn_x), color=CYAN, linewidth=1.5, alpha=0.8, label='Tendencia')
ax5.axvline(20, color=YELLOW, linestyle='--', linewidth=1, alpha=0.7, label='VXN=20')
ax5.axvline(25, color=RED,    linestyle='--', linewidth=1, alpha=0.7, label='VXN=25')
ax5.axvline(30, color=RED,    linestyle='--', linewidth=1.5, alpha=0.8, label='VXN=30')
leg5 = ax5.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
ax5.set_xlabel('VXN', color=GRAY, fontsize=8)
ax5.set_ylabel('Rango (pts)', color=GRAY, fontsize=8)

# Stats por band de VXN
for vmin, vmax, label in [(14,20,'<20'), (20,25,'20-25'), (25,30,'25-30'), (30,50,'>30')]:
    sub = has_vxn[(has_vxn['vxn'] >= vmin) & (has_vxn['vxn'] < vmax)]
    if len(sub) > 0:
        print(f"  VXN {label:6s}: n={len(sub):3d}  Rango med={sub['range'].median():.0f}pts  LOW_FIRST={100*(sub['dia_tipo']=='LOW_FIRST').mean():.0f}%")

# ── Panel 6: COT Index vs tipo de martes ─────────────────────────────────────
ax6 = fig.add_subplot(gs[1, 2])
ax_style(ax6, 'COT Index vs tipo de martes\n(posicion institucional)')
has_cot = df_m[df_m['cot_idx'].notna()].copy()
if len(has_cot) > 5:
    # Boxplot por cuartil de COT
    has_cot['cot_band'] = pd.cut(has_cot['cot_idx'],
                                  bins=[0, 25, 50, 75, 100],
                                  labels=['0-25\n(Extremo\nBajista)', '25-50\n(Neutral\nBajista)',
                                          '50-75\n(Neutral\nAlcista)', '75-100\n(Extremo\nAlcista)'])
    bands = ['0-25\n(Extremo\nBajista)', '25-50\n(Neutral\nBajista)', '50-75\n(Neutral\nAlcista)', '75-100\n(Extremo\nAlcista)']
    x6 = np.arange(len(bands))
    lf_pcts = []
    hf_pcts = []
    ns = []
    for b in bands:
        sub = has_cot[has_cot['cot_band'] == b]
        ns.append(len(sub))
        if len(sub) > 0:
            lf_pcts.append(100*(sub['dia_tipo']=='LOW_FIRST').mean())
            hf_pcts.append(100*(sub['dia_tipo']=='HIGH_FIRST').mean())
        else:
            lf_pcts.append(0); hf_pcts.append(0)
    w6 = 0.4
    b1 = ax6.bar(x6 - w6/2, lf_pcts, w6, color=GREEN, alpha=0.8, label='LOW_FIRST (rebote)')
    b2 = ax6.bar(x6 + w6/2, hf_pcts, w6, color=RED,   alpha=0.8, label='HIGH_FIRST (caida)')
    ax6.axhline(50, color=YELLOW, linestyle='--', linewidth=1, alpha=0.6)
    ax6.set_xticks(x6)
    ax6.set_xticklabels(bands, fontsize=6.5, color=GRAY)
    ax6.set_ylabel('%', color=GRAY, fontsize=8)
    for bar, n_val in zip(b1, ns):
        ax6.text(bar.get_x()+bar.get_width()/2, -8, f'n={n_val}', ha='center', va='top', fontsize=6, color=GRAY)
    leg6 = ax6.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE)
else:
    ax6.text(0.5, 0.5, 'Sin datos COT\nsuficientes', ha='center', va='center', color=GRAY, transform=ax6.transAxes)

# ── Panel 7: Tabla resumen por cuartil de rango ───────────────────────────────
ax7 = fig.add_subplot(gs[2, :])
ax_style(ax7, 'TABLA COMPLETA — DISTRIBUCION DE MARTES NQ POR RANGO')
ax7.axis('off')

# Segmentos
segs = [
    ('< 100pts\n(rango chico)',  df_m[df_m['range'] < 100]),
    ('100-150pts\n(normal bajo)', df_m[(df_m['range'] >= 100) & (df_m['range'] < 150)]),
    ('150-200pts\n(normal)',      df_m[(df_m['range'] >= 150) & (df_m['range'] < 200)]),
    ('200-300pts\n(grande)',      df_m[(df_m['range'] >= 200) & (df_m['range'] < 300)]),
    ('300-400pts\n(muy grande)', df_m[(df_m['range'] >= 300) & (df_m['range'] < 400)]),
    ('>400pts\n(extremo)',        df_m[df_m['range'] >= 400]),
]
headers = ['Rango', 'N casos', '% del total', 'LOW→HIGH', 'HIGH→LOW', 
           'Rango med', 'Hora LOW med', 'Lun previo med']
rows = [headers]
for label, seg in segs:
    n = len(seg)
    if n == 0:
        rows.append([label, '0', '0%', '-', '-', '-', '-', '-'])
        continue
    pct_total = f'{100*n/n_total:.0f}%'
    lf_pct = f"{100*(seg['dia_tipo']=='LOW_FIRST').mean():.0f}%"
    hf_pct = f"{100*(seg['dia_tipo']=='HIGH_FIRST').mean():.0f}%"
    rmed   = f"{seg['range'].median():.0f}"
    lf_seg = seg[seg['dia_tipo'] == 'LOW_FIRST']
    low_med = f"{int(lf_seg['low_hour'].median())}:{int((lf_seg['low_hour'].median()%1)*60):02d}" if len(lf_seg)>0 else '-'
    mon_seg = seg['mon_move'].dropna()
    mon_med = f"{mon_seg.median():.0f}pts" if len(mon_seg) > 0 else '-'
    rows.append([label, str(n), pct_total, lf_pct, hf_pct, rmed+'pts', low_med, mon_med])

t = ax7.table(cellText=rows[1:], colLabels=rows[0], loc='center', cellLoc='center')
t.auto_set_font_size(False)
t.set_fontsize(9)
t.scale(1, 2.1)

for (r, c), cell in t.get_celld().items():
    cell.set_facecolor('#0a0f1e' if r == 0 else ('#0d1628' if r % 2 == 0 else '#111c35'))
    cell.set_edgecolor('#1e2d4a')
    text = cell.get_text()
    if r == 0:
        text.set_color(CYAN)
        text.set_fontweight('bold')
        text.set_fontsize(8.5)
    else:
        col = rows[r][c]
        if 'LOW' in str(col) and 'HIGH' not in str(col): text.set_color(GREEN)
        elif 'HIGH' in str(col): text.set_color(RED)
        else: text.set_color(WHITE)

# ── Panel 8: Serie temporal — rango del martes a lo largo del tiempo ──────────
ax8 = fig.add_subplot(gs[3, :])
ax_style(ax8, 'EVOLUCION HISTORICA — Rango de cada martes (2017-2026)')
colors8 = [GREEN if t == 'LOW_FIRST' else RED for t in df_m['dia_tipo']]
ax8.bar(df_m['fecha'], df_m['range'], color=colors8, alpha=0.7, width=3)
# Media movil 10 semanas
rolling = df_m.set_index('fecha')['range'].rolling(10, min_periods=3).mean()
ax8.plot(rolling.index, rolling.values, color=CYAN, linewidth=1.5, label='Media movil 10 sem')
ax8.axhline(q50, color=YELLOW, linestyle='--', linewidth=1, alpha=0.7, label=f'Mediana {q50:.0f}pts')
ax8.axhline(300, color=WHITE,  linestyle='--', linewidth=0.8, alpha=0.5, label='300pts')
ax8.set_xlabel('Fecha', color=GRAY, fontsize=8)
ax8.set_ylabel('Rango (pts)', color=GRAY, fontsize=8)
# Zonas COVID y volatilidad
ax8.axvspan(pd.Timestamp('2020-03-01'), pd.Timestamp('2020-06-01'), color=RED, alpha=0.07, label='COVID')
ax8.axvspan(pd.Timestamp('2022-01-01'), pd.Timestamp('2022-12-31'), color=YELLOW, alpha=0.05, label='Bear 2022')
ax8.axvspan(pd.Timestamp('2025-08-01'), pd.Timestamp('2025-09-30'), color=PURPLE, alpha=0.07)
ax8.text(pd.Timestamp('2025-08-15'), df_m['range'].max()*0.9, 'Yen Carry\nUnwind', color=PURPLE, fontsize=7, ha='center')
ax8.annotate('HOY: 7 Abr', xy=(pd.Timestamp('2026-04-07'), 440),
             xytext=(pd.Timestamp('2025-10-01'), 500),
             arrowprops=dict(arrowstyle='->', color=CYAN), color=CYAN, fontsize=8, fontweight='bold')
leg8 = ax8.legend(fontsize=7, facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE, loc='upper left')

# Leyenda de colores
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=GREEN, alpha=0.7, label='LOW→HIGH (rebote alcista)'),
                   Patch(facecolor=RED,   alpha=0.7, label='HIGH→LOW (caida bajista)')]
ax8.legend(handles=legend_elements + ax8.get_lines(), fontsize=7,
           facecolor='#0d1628', edgecolor=GRAY, labelcolor=WHITE, loc='upper left')

# ── Guardar ───────────────────────────────────────────────────────────────────
out = os.path.join(BASE, 'martes_estudio_completo_195.png')
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0a0f1e')
plt.close()
print(f"\n[OK] Guardado: {out}")

# ── Resumen en texto ──────────────────────────────────────────────────────────
print("\n" + "="*60)
print("RESUMEN DEL ESTUDIO COMPLETO")
print("="*60)
print(f"  Total martes:         {n_total}")
print(f"  Rango promedio:       {df_m['range'].mean():.0f}pts")
print(f"  Rango mediano:        {df_m['range'].median():.0f}pts")
print(f"  Rango maxima:         {df_m['range'].max():.0f}pts")
print(f"  Dias LOW→HIGH:        {(df_m['dia_tipo']=='LOW_FIRST').sum()} ({100*(df_m['dia_tipo']=='LOW_FIRST').mean():.0f}%)")
print(f"  Dias HIGH→LOW:        {(df_m['dia_tipo']=='HIGH_FIRST').sum()} ({100*(df_m['dia_tipo']=='HIGH_FIRST').mean():.0f}%)")
print(f"  Rango ≥300pts:        {(df_m['range']>=300).sum()} casos ({100*(df_m['range']>=300).mean():.0f}%)")
print(f"  Rango ≥200pts:        {(df_m['range']>=200).sum()} casos ({100*(df_m['range']>=200).mean():.0f}%)")
print(f"\n  TOP 10 martes mayor rango:")
top10 = df_m.nlargest(10, 'range')[['fecha','range','dia_tipo','mon_move','low_time_str']].reset_index(drop=True)
print(top10.to_string(index=False))
