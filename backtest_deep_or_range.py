"""
backtest_deep_or_range.py
═══════════════════════════════════════════════════════════════════════
ESTUDIO PROFUNDO: OR Range >100pts × todos los dias × subfiltros

Para cada día (Lun-Vie), cuando el OR tiene rango >100pts:
  1. Accuracy base OR dir → NY dir
  2. + filtro PM direction
  3. + filtro día anterior (prev day NY dir)
  4. + filtro OR range (100-200 vs >200)
  5. Dónde se hace el HIGH/LOW del día primero
  6. Distribución de movimientos (histograma)
  7. Tabla detalle de cada día que cumple la condición
  8. Genera HTML completo con todo

Fuente: data/research/nq_15m_intraday.csv
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from collections import defaultdict

CSV = "data/research/nq_15m_intraday.csv"

# ══════════════════════════════════════════════════════════════════
# 1. CARGAR Y PREPARAR DATOS
# ══════════════════════════════════════════════════════════════════
print("═"*68)
print("  DEEP STUDY — OR Range >100pts × Lun-Vie")
print("═"*68)

df = pd.read_csv(CSV)
df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
df['et']   = df['Datetime'] - pd.Timedelta(hours=5)
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time
df['dow']  = df['et'].dt.weekday
for c in ['Open','High','Low','Close']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df = df.dropna(subset=['Close']).sort_values('et').reset_index(drop=True)

NY_S  = time(9, 30);  NY_E  = time(15, 59)
PM_S  = time(7,  0);  PM_E  = time(9,  29)
OR15_E = time(9, 44); OR30_E = time(9, 59); OR45_E = time(10,14)

DOW  = {0:'LUNES',1:'MARTES',2:'MIÉRCOLES',3:'JUEVES',4:'VIERNES'}
DOW_EN = {0:'monday',1:'tuesday',2:'wednesday',3:'thursday',4:'friday'}
DOW_COLOR = {0:'#38bdf8',1:'#a78bfa',2:'#34d399',3:'#fb923c',4:'#f472b6'}

def session(day_df, ts, te):
    return day_df[(day_df['time'] >= ts) & (day_df['time'] <= te)]

def or_stats(bars):
    if len(bars) < 1:
        return None
    o_  = float(bars.iloc[0]['Open'])
    c_  = float(bars.iloc[-1]['Close'])
    hi  = float(bars['High'].max())
    lo  = float(bars['Low'].min())
    mv  = c_ - o_
    rng = hi - lo
    dir_ = 'BULL' if mv > 10 else ('BEAR' if mv < -10 else 'FLAT')
    return {'open':o_,'close':c_,'high':hi,'low':lo,'move':round(mv),'range':round(rng),'dir':dir_}

# ══════════════════════════════════════════════════════════════════
# 2. PROCESAR TODOS LOS DÍAS
# ══════════════════════════════════════════════════════════════════
print("\n  Procesando días...")
rows = []
dates = sorted(df['date'].unique())

for i, d in enumerate(dates):
    day_df = df[df['date'] == d]
    if len(day_df) < 8: continue
    dow = int(day_df.iloc[0]['dow'])
    if dow > 4: continue

    ny   = session(day_df, NY_S, NY_E)
    pm   = session(day_df, PM_S, PM_E)
    if len(ny) < 4: continue

    ny_o  = float(ny.iloc[0]['Open'])
    ny_c  = float(ny.iloc[-1]['Close'])
    ny_hi = float(ny['High'].max())
    ny_lo = float(ny['Low'].min())
    ny_mv = round(ny_c - ny_o)
    ny_rng= round(ny_hi - ny_lo)
    ny_dir= 'BULL' if ny_mv > 30 else ('BEAR' if ny_mv < -30 else 'FLAT')

    # ¿Qué llega primero en NY — HIGH o LOW?
    idx_hi = ny['High'].idxmax()
    idx_lo = ny['Low'].idxmin()
    hi_first = idx_hi < idx_lo

    # PM
    pm_mv  = 0; pm_dir = 'FLAT'
    if len(pm) >= 2:
        pm_mv  = float(pm.iloc[-1]['Close']) - float(pm.iloc[0]['Open'])
        pm_dir = 'BULL' if pm_mv > 15 else ('BEAR' if pm_mv < -15 else 'FLAT')

    # OR timeframes
    or15 = or_stats(session(day_df, NY_S, OR15_E))
    or30 = or_stats(session(day_df, NY_S, OR30_E))
    or45 = or_stats(session(day_df, NY_S, OR45_E))

    rows.append({
        'date': d, 'dow': dow, 'dow_name': DOW[dow],
        'ny_open': round(ny_o), 'ny_close': round(ny_c),
        'ny_move': ny_mv, 'ny_range': ny_rng, 'ny_dir': ny_dir,
        'hi_first': hi_first,
        'pm_move': round(pm_mv), 'pm_dir': pm_dir,
        'or15': or15, 'or30': or30, 'or45': or45,
    })

df_r = pd.DataFrame(rows)

# Añadir prev_day_dir
prev_map = {}
for i, r in df_r.iterrows():
    prev_map[r['date']] = r['ny_dir']

df_r['prev_dir'] = df_r['date'].apply(
    lambda d: prev_map.get(dates[dates.index(d)-1] if dates.index(d) > 0 else d, 'FLAT')
)

n_total = len(df_r)
d_min   = df_r['date'].min()
d_max   = df_r['date'].max()
print(f"  Total: {n_total} días | {d_min} → {d_max}")

# ══════════════════════════════════════════════════════════════════
# 3. FUNCIÓN DE ANÁLISIS PROFUNDO
# ══════════════════════════════════════════════════════════════════
def deep_analysis(sub_df, or_key, or_dir, label=""):
    """Análisis profundo de un subconjunto de días."""
    # Extraer OR stats
    valid = sub_df[sub_df[or_key].notna()].copy()
    valid['_or_dir']   = valid[or_key].apply(lambda x: x['dir'] if x else None)
    valid['_or_range'] = valid[or_key].apply(lambda x: x['range'] if x else None)
    valid['_or_move']  = valid[or_key].apply(lambda x: x['move'] if x else None)

    # Filtrar OR dir + range > 100
    filt = valid[(valid['_or_dir'] == or_dir) & (valid['_or_range'] > 100)]
    n = len(filt)
    if n < 2:
        return None

    expected_ny = or_dir  # esperamos que NY siga OR
    correct   = (filt['ny_dir'] == expected_ny).sum()
    reversal  = (filt['ny_dir'] == ('BEAR' if or_dir == 'BULL' else 'BULL')).sum()
    flat_n    = n - correct - reversal
    acc       = correct / n * 100
    rev_pct   = reversal / n * 100
    avg_ny    = filt['ny_move'].mean()
    med_ny    = filt['ny_move'].median()
    avg_rng   = filt['_or_range'].mean()
    hi_1st    = filt['hi_first'].sum()
    lo_1st    = n - hi_1st

    # Sub-filtros
    subs = {}

    # Por PM direction
    for pm_d in ['BULL', 'BEAR', 'FLAT']:
        s = filt[filt['pm_dir'] == pm_d]
        if len(s) < 2: continue
        c = (s['ny_dir'] == expected_ny).sum()
        subs[f'PM_{pm_d}'] = {
            'n': len(s), 'correct': c, 'acc': c/len(s)*100,
            'avg_ny': s['ny_move'].mean(), 'label': f'PM {pm_d}'
        }

    # Por prev day
    for prev_d in ['BULL', 'BEAR', 'FLAT']:
        s = filt[filt['prev_dir'] == prev_d]
        if len(s) < 2: continue
        c = (s['ny_dir'] == expected_ny).sum()
        subs[f'PREV_{prev_d}'] = {
            'n': len(s), 'correct': c, 'acc': c/len(s)*100,
            'avg_ny': s['ny_move'].mean(), 'label': f'Día Anterior {prev_d}'
        }

    # Por rango OR 100-200 vs >200
    for rlo, rhi, lbl in [(100,200,'OR 100-200'), (200,500,'OR >200')]:
        s = filt[(filt['_or_range'] >= rlo) & (filt['_or_range'] < rhi)]
        if len(s) < 2: continue
        c = (s['ny_dir'] == expected_ny).sum()
        subs[f'RNG_{rlo}_{rhi}'] = {
            'n': len(s), 'correct': c, 'acc': c/len(s)*100,
            'avg_ny': s['ny_move'].mean(), 'label': lbl
        }

    # Combo PM mismo dir que OR
    s = filt[filt['pm_dir'] == or_dir]
    if len(s) >= 2:
        c = (s['ny_dir'] == expected_ny).sum()
        subs['PM_SAME'] = {
            'n': len(s), 'correct': c, 'acc': c/len(s)*100,
            'avg_ny': s['ny_move'].mean(), 'label': f'PM + OR ambos {or_dir}'
        }

    # Combo PM opuesto a OR (divergencia)
    opp = 'BEAR' if or_dir == 'BULL' else 'BULL'
    s = filt[filt['pm_dir'] == opp]
    if len(s) >= 2:
        c = (s['ny_dir'] == expected_ny).sum()
        subs['PM_OPP'] = {
            'n': len(s), 'correct': c, 'acc': c/len(s)*100,
            'avg_ny': s['ny_move'].mean(), 'label': f'PM {opp} (divergencia)'
        }

    # Tabla de días individuales
    detail = []
    for _, r in filt.sort_values('date', ascending=False).iterrows():
        detail.append({
            'date': str(r['date']),
            'pm_dir': r['pm_dir'],
            'pm_move': r['pm_move'],
            'or_range': int(r['_or_range']),
            'or_move': int(r['_or_move']),
            'ny_dir': r['ny_dir'],
            'ny_move': r['ny_move'],
            'ny_range': r['ny_range'],
            'hi_first': r['hi_first'],
            'prev_dir': r['prev_dir'],
            'correct': r['ny_dir'] == expected_ny,
        })

    return {
        'n': n, 'correct': int(correct), 'acc': round(acc,1),
        'reversal': int(reversal), 'rev_pct': round(rev_pct,1),
        'flat_n': int(flat_n),
        'avg_ny': round(avg_ny,0), 'med_ny': round(med_ny,0),
        'avg_rng': round(avg_rng,0),
        'hi_first': int(hi_first), 'lo_first': int(lo_1st),
        'subs': subs, 'detail': detail,
        'or_dir': or_dir, 'label': label,
    }

# ══════════════════════════════════════════════════════════════════
# 4. ANÁLISIS POR DÍA
# ══════════════════════════════════════════════════════════════════
OR_KEYS = {'OR_15m':'or15','OR_30m':'or30','OR_45m':'or45'}
OR_DIRS = ['BULL','BEAR']

all_results = {}  # [dow][or_key][or_dir] = result

for dow in range(5):
    all_results[dow] = {}
    day_df = df_r[df_r['dow'] == dow]
    n_day = len(day_df)

    print(f"\n{'━'*68}")
    print(f"  📅 {DOW[dow]} — {n_day} días")
    print(f"{'━'*68}")

    for or_key, col in OR_KEYS.items():
        all_results[dow][or_key] = {}
        for or_dir in OR_DIRS:
            tf = or_key.replace('OR_','')
            res = deep_analysis(day_df, col, or_dir, f"{DOW[dow]} {tf} {or_dir}")
            all_results[dow][or_key][or_dir] = res
            if res is None:
                continue

            star = "⭐" if res['acc'] >= 75 and res['n'] >= 5 else (
                   "🔥" if res['acc'] >= 65 and res['n'] >= 5 else "")
            arrow = "▲" if or_dir == 'BULL' else "▼"
            print(f"\n  ┌─ {tf} OR {or_dir} {arrow} (rng>100) → {res['n']} días │ {res['acc']:.0f}% {star}")
            print(f"  │  Correct: {res['correct']}/{res['n']} │ Rev: {res['reversal']}({res['rev_pct']:.0f}%) │ AvgNY: {res['avg_ny']:+.0f}pts │ MedNY: {res['med_ny']:+.0f}pts")
            print(f"  │  HighFirst: {res['hi_first']}/{res['n']} ({res['hi_first']/res['n']*100:.0f}%) │ LowFirst: {res['lo_first']}/{res['n']} ({res['lo_first']/res['n']*100:.0f}%)")

            # Sub-filtros ordenados por accuracy
            if res['subs']:
                print(f"  │  Sub-filtros:")
                for k, s in sorted(res['subs'].items(), key=lambda x: -x[1]['acc']):
                    star2 = " ⭐" if s['acc'] >= 80 and s['n'] >= 3 else ""
                    print(f"  │    {s['label']:<30} {s['correct']}/{s['n']} = {s['acc']:.0f}%  avg={s['avg_ny']:+.0f}pts{star2}")

# ══════════════════════════════════════════════════════════════════
# 5. RESUMEN GLOBAL — TOP COMBOS
# ══════════════════════════════════════════════════════════════════
print(f"\n\n{'═'*68}")
print(f"  🏆 TOP COMBOS — Ordenados por Accuracy (N≥3)")
print(f"{'═'*68}")

all_combos = []
for dow in range(5):
    for or_key, col in OR_KEYS.items():
        for or_dir in OR_DIRS:
            res = all_results[dow][or_key].get(or_dir)
            if not res: continue
            # Base
            if res['n'] >= 3:
                all_combos.append({
                    'dow': DOW[dow], 'or_key': or_key.replace('OR_',''),
                    'or_dir': or_dir, 'filter': 'Base (rng>100)',
                    'n': res['n'], 'correct': res['correct'],
                    'acc': res['acc'], 'avg_ny': res['avg_ny']
                })
            # Sub-filtros
            for k, s in res['subs'].items():
                if s['n'] >= 3:
                    all_combos.append({
                        'dow': DOW[dow], 'or_key': or_key.replace('OR_',''),
                        'or_dir': or_dir, 'filter': s['label'],
                        'n': s['n'], 'correct': s['correct'],
                        'acc': s['acc'], 'avg_ny': s['avg_ny']
                    })

top_combos = sorted(all_combos, key=lambda x: (-x['acc'], -x['n']))[:25]
print(f"\n  {'Día':<12} {'TF':<6} {'Dir':<5} {'Filtro':<35} {'N':>3} {'Acc':>6} {'AvgNY':>8}")
print(f"  {'─'*75}")
for c in top_combos:
    star = " ⭐" if c['acc'] >= 80 and c['n'] >= 5 else (
           " 🔥" if c['acc'] >= 70 and c['n'] >= 5 else "")
    print(f"  {c['dow']:<12} {c['or_key']:<6} {c['or_dir']:<5} {c['filter']:<35} {c['n']:>3} {c['acc']:>5.0f}% {c['avg_ny']:>+7.0f}pts{star}")

# ══════════════════════════════════════════════════════════════════
# 6. GENERAR HTML COMPLETO
# ══════════════════════════════════════════════════════════════════
print(f"\n\n  Generando HTML...")

def acc_color(a):
    if a >= 80: return '#10b981'
    if a >= 70: return '#34d399'
    if a >= 60: return '#f59e0b'
    return '#64748b'

def dir_color(d):
    return '#10b981' if d == 'BULL' else ('#ef4444' if d == 'BEAR' else '#94a3b8')

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Deep OR Study >100pts — NQ Whale Radar</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080812;color:#e2e8f0;font-family:'Segoe UI',Arial,sans-serif;padding:16px}}
h1{{color:#f59e0b;font-size:18px;text-align:center;margin-bottom:4px}}
.sub{{color:#475569;font-size:10px;text-align:center;margin-bottom:18px}}
.tabs{{display:flex;gap:6px;flex-wrap:wrap;justify-content:center;margin-bottom:18px}}
.tab{{padding:8px 18px;border-radius:20px;font-size:11px;font-weight:700;cursor:pointer;
      border:1px solid #334155;color:#64748b;background:none;transition:all .2s}}
.tab.active{{border-color:var(--c);color:var(--c);background:rgba(255,255,255,.04)}}
.day-section{{display:none}}.day-section.active{{display:block}}
.card{{background:#0f0f1e;border:1px solid #1e2235;border-radius:10px;padding:16px;margin-bottom:14px}}
.card-title{{font-size:12px;font-weight:800;margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}
.stat-box{{background:#080812;border:1px solid #1a1a2e;border-radius:8px;padding:10px;text-align:center}}
.stat-label{{font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.05em}}
.stat-val{{font-size:20px;font-weight:900;margin-top:3px}}
.stat-sub{{font-size:9px;color:#475569;margin-top:1px}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
th{{background:#0f0f1e;color:#475569;font-size:9px;font-weight:600;padding:6px 8px;
    text-align:center;border-bottom:1px solid #1e2235;position:sticky;top:0;z-index:5}}
td{{padding:5px 8px;text-align:center;border-bottom:1px solid #0d0d1a;vertical-align:middle}}
.ok{{background:#05150f}}.fail{{background:#150505}}.elite{{background:#0a0820}}
.pos{{color:#10b981;font-weight:700}}.neg{{color:#ef4444;font-weight:700}}
.neu{{color:#94a3b8}}
.badge{{display:inline-block;padding:2px 7px;border-radius:10px;font-size:9px;font-weight:700}}
.acc-bar{{height:8px;border-radius:3px;display:inline-block;vertical-align:middle;margin-left:4px}}
.section-divider{{border:0;border-top:1px solid #1e2235;margin:14px 0}}
.sub-filter-table td{{background:transparent}}
.sub-filter-table tr:hover td{{background:rgba(255,255,255,.02)}}
.top-badge{{display:inline-block;padding:1px 6px;border-radius:8px;font-size:9px;
            font-weight:700;background:rgba(245,158,11,.12);color:#f59e0b;border:1px solid rgba(245,158,11,.3)}}
</style>
</head>
<body>
<h1>🔬 DEEP STUDY — OR Range >100pts × Lunes a Viernes</h1>
<p class="sub">{d_min} → {d_max} · {n_total} días · OR 15m / 30m / 45m · Sub-filtros: PM, Día Anterior, Rango</p>

<div class="tabs">
"""
for dow in range(5):
    c = DOW_COLOR[dow]
    html += f'  <button class="tab{" active" if dow==0 else ""}" style="--c:{c}" onclick="showDay({dow})" id="tab-{dow}">{DOW[dow]}</button>\n'

html += '</div>\n'

# Global top combos card
html += f"""
<div class="card">
  <div class="card-title">🏆 TOP 25 COMBOS — Todos los días (N≥3)</div>
  <div style="overflow-x:auto">
  <table>
    <tr><th>Día</th><th>TF</th><th>Dir</th><th>Filtro</th><th>N</th><th>Acc</th><th>Avg NY</th></tr>
"""
for c in top_combos:
    star = "⭐" if c['acc'] >= 80 and c['n'] >= 5 else ("🔥" if c['acc'] >= 70 and c['n'] >= 5 else "")
    row_cls = 'elite' if c['acc'] >= 80 else ('ok' if c['acc'] >= 70 else '')
    acc_c = acc_color(c['acc'])
    dir_c = dir_color(c['or_dir'])
    mv_c  = 'pos' if c['avg_ny'] > 0 else 'neg'
    bar_w = min(int(c['acc'] * 0.7), 70)
    bar_c = acc_c
    html += f"""    <tr class="{row_cls}">
      <td style="font-weight:700;color:{DOW_COLOR[list(DOW.values()).index(c['dow'])]}">{c['dow']}</td>
      <td>{c['or_key']}</td>
      <td><span style="color:{dir_c};font-weight:700">{'▲' if c['or_dir']=='BULL' else '▼'} {c['or_dir']}</span></td>
      <td style="text-align:left">{c['filter']}</td>
      <td>{c['n']}</td>
      <td><span style="color:{acc_c};font-weight:900;font-size:13px">{c['acc']:.0f}%</span>
          <span class="acc-bar" style="width:{bar_w}px;background:{bar_c}"></span>
          {star}</td>
      <td class="{mv_c}">{c['avg_ny']:+.0f}pts</td>
    </tr>\n"""
html += "  </table></div></div>\n"

# Per-day sections
for dow in range(5):
    display = 'block' if dow == 0 else 'none'
    color   = DOW_COLOR[dow]
    day_df  = df_r[df_r['dow'] == dow]
    n_day   = len(day_df)
    bull_n  = (day_df['ny_dir']=='BULL').sum()
    bear_n  = (day_df['ny_dir']=='BEAR').sum()
    avg_rng = day_df['ny_range'].mean()

    html += f'<div class="day-section{"  active" if dow==0 else ""}" id="day-{dow}">\n'
    html += f"""
  <div class="card">
    <div class="card-title" style="color:{color}">📅 {DOW[dow]} — {n_day} días totales</div>
    <div class="grid3">
      <div class="stat-box"><div class="stat-label">Total Días</div>
        <div class="stat-val" style="color:{color}">{n_day}</div></div>
      <div class="stat-box"><div class="stat-label">Sesgo Base</div>
        <div class="stat-val" style="font-size:14px">
          <span class="pos">▲{bull_n/n_day*100:.0f}%</span> /
          <span class="neg">▼{bear_n/n_day*100:.0f}%</span>
        </div></div>
      <div class="stat-box"><div class="stat-label">Rango Promedio</div>
        <div class="stat-val" style="color:#f59e0b">{avg_rng:.0f}pts</div></div>
    </div>
  </div>
"""
    # Each OR timeframe
    for or_key, col in OR_KEYS.items():
        tf = or_key.replace('OR_','')
        for or_dir in OR_DIRS:
            res = all_results[dow][or_key].get(or_dir)
            if not res or res['n'] < 2:
                continue

            star_html = ""
            if res['acc'] >= 80 and res['n'] >= 5: star_html = ' <span class="top-badge">⭐ ELITE</span>'
            elif res['acc'] >= 70 and res['n'] >= 5: star_html = ' <span class="top-badge">🔥 FUERTE</span>'

            acc_c  = acc_color(res['acc'])
            dir_c  = dir_color(or_dir)
            arrow  = '▲' if or_dir == 'BULL' else '▼'
            bar_w  = min(int(res['acc'] * 0.9), 90)

            html += f"""
  <div class="card" style="border-color:rgba({','.join(str(int(c,16)) for c in [color[1:3],color[3:5],color[5:7]])},0.2)">
    <div class="card-title">
      {tf} OR <span style="color:{dir_c}">{arrow} {or_dir}</span> · Range >100pts{star_html}
    </div>
    <div class="grid2" style="margin-bottom:12px">
      <div>
        <div class="stat-box" style="margin-bottom:8px">
          <div class="stat-label">Accuracy (NY sigue OR)</div>
          <div class="stat-val" style="color:{acc_c}">{res['acc']:.0f}%</div>
          <div class="stat-sub">{res['correct']}/{res['n']} días &nbsp;|&nbsp;
            <span style="width:{bar_w}px;height:6px;background:{acc_c};display:inline-block;border-radius:2px;vertical-align:middle"></span>
          </div>
        </div>
        <div class="stat-box">
          <div class="stat-label">Reversal (NY opuesto)</div>
          <div class="stat-val neg" style="font-size:16px">{res['rev_pct']:.0f}%</div>
          <div class="stat-sub">{res['reversal']}/{res['n']} días</div>
        </div>
      </div>
      <div>
        <div class="stat-box" style="margin-bottom:8px">
          <div class="stat-label">Avg Movimiento NY</div>
          <div class="stat-val {'pos' if res['avg_ny']>0 else 'neg'}">{res['avg_ny']:+.0f}pts</div>
          <div class="stat-sub">Mediana: {res['med_ny']:+.0f}pts</div>
        </div>
        <div class="stat-box">
          <div class="stat-label">¿Qué llega 1° en NY?</div>
          <div class="stat-val" style="font-size:13px">
            <span style="color:#10b981">H:{res['hi_first']}</span> /
            <span style="color:#ef4444">L:{res['lo_first']}</span>
          </div>
          <div class="stat-sub">de {res['n']} días</div>
        </div>
      </div>
    </div>

    <!-- Sub-filtros -->
    <hr class="section-divider">
    <div style="font-size:10px;color:#475569;font-weight:600;margin-bottom:6px">SUB-FILTROS</div>
    <table class="sub-filter-table">
      <tr><th style="text-align:left">Filtro</th><th>N</th><th>Acc</th><th>Avg NY</th><th>Bar</th></tr>
"""
            for k, s in sorted(res['subs'].items(), key=lambda x: -x[1]['acc']):
                s_star = " ⭐" if s['acc'] >= 80 and s['n'] >= 3 else ""
                s_acc_c = acc_color(s['acc'])
                s_mv_c  = 'pos' if s['avg_ny'] > 0 else 'neg'
                bw = min(int(s['acc'] * 0.6), 60)
                row_cls = 'ok' if s['acc'] >= 75 else ('fail' if s['acc'] < 40 else '')
                html += f"""      <tr class="{row_cls}">
        <td style="text-align:left;color:#94a3b8">{s['label']}{s_star}</td>
        <td>{s['n']}</td>
        <td style="color:{s_acc_c};font-weight:700">{s['acc']:.0f}%</td>
        <td class="{s_mv_c}">{s['avg_ny']:+.0f}pts</td>
        <td><span style="display:inline-block;width:{bw}px;height:7px;background:{s_acc_c};border-radius:2px"></span></td>
      </tr>\n"""

            html += "    </table>\n"

            # Detail table
            html += """    <hr class="section-divider">
    <div style="font-size:10px;color:#475569;font-weight:600;margin-bottom:6px">DETALLE DÍAS</div>
    <div style="overflow-x:auto">
    <table>
      <tr><th>Fecha</th><th>PM</th><th>PM Mov</th><th>OR Rng</th><th>OR Mov</th><th>NY Dir</th><th>NY Mov</th><th>NY Rng</th><th>Hi 1°</th><th>Día Ant</th><th>✓</th></tr>
"""
            for d in res['detail']:
                row_cls = 'ok' if d['correct'] else 'fail'
                ny_c = dir_color(d['ny_dir'])
                pm_c = dir_color(d['pm_dir'])
                ny_mv_c = 'pos' if d['ny_move'] > 0 else 'neg'
                chk = '✅' if d['correct'] else '❌'
                hi_s = '↑Hi' if d['hi_first'] else '↓Lo'
                html += f"""      <tr class="{row_cls}">
        <td>{d['date']}</td>
        <td style="color:{pm_c};font-weight:700">{d['pm_dir']}</td>
        <td class="{'pos' if d['pm_move']>0 else 'neg'}">{d['pm_move']:+}pts</td>
        <td style="color:#f59e0b;font-weight:700">{d['or_range']}pts</td>
        <td class="{'pos' if d['or_move']>0 else 'neg'}">{d['or_move']:+}pts</td>
        <td style="color:{ny_c};font-weight:700">{d['ny_dir']}</td>
        <td class="{ny_mv_c}">{d['ny_move']:+}pts</td>
        <td>{d['ny_range']}pts</td>
        <td style="color:{'#10b981' if d['hi_first'] else '#ef4444'}">{hi_s}</td>
        <td style="color:{dir_color(d['prev_dir'])}">{d['prev_dir']}</td>
        <td>{chk}</td>
      </tr>\n"""

            html += "    </table></div>\n  </div>\n"

    html += "</div>\n"

# JS para tabs
html += """
<script>
function showDay(idx) {
  document.querySelectorAll('.day-section').forEach((s,i) => {
    s.classList.toggle('active', i === idx);
  });
  document.querySelectorAll('.tab').forEach((t,i) => {
    t.classList.toggle('active', i === idx);
  });
}
</script>
"""
html += f"""
<div style="text-align:center;margin-top:20px;color:#1e2235;font-size:10px">
  NQ Whale Radar · Deep OR Study · {d_min} → {d_max} · {n_total} días
</div>
</body></html>"""

out = "backtest_deep_or.html"
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n  ✅ HTML: {out}")
print(f"  📊 {n_total} días · {d_min} → {d_max}")
print("═"*68)
