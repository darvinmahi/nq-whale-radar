"""
backtest_or_completo.py
═══════════════════════════════════════════════════════════════
BACKTESTING COMPLETO: Opening Range (OR) por DÍA de la semana
Todos los días reales — OR 5min, 15min, 30min

Analiza CADA día de 2+ años para determinar:
  - OR BULL → ¿NY cierra BULL?
  - OR BEAR → ¿NY cierra BEAR?
  - Accuracy por día y por timeframe de OR
  - Mejor OR para cada día

Fuente: data/research/nq_15m_intraday.csv (barras 15min)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from collections import defaultdict

CSV = "data/research/nq_15m_intraday.csv"

# ═══════════════════════════════════════════════════════════════
# 1. CARGAR DATOS
# ═══════════════════════════════════════════════════════════════
print("═" * 70)
print("  BACKTEST COMPLETO — OR 5/15/30 min × Lun-Vie × 2+ años")
print("═" * 70)
print("\n  Cargando CSV...")

df = pd.read_csv(CSV)
df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
# Convertir a ET
df['et'] = df['Datetime'] - pd.Timedelta(hours=5)
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time
df['dow'] = df['et'].dt.weekday  # 0=Mon, 4=Fri

for c in ['Open', 'High', 'Low', 'Close']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df = df.dropna(subset=['Close']).sort_values('et')

total_days = df['date'].nunique()
date_min = df['date'].min()
date_max = df['date'].max()
print(f"  CSV: {date_min} → {date_max} ({total_days} días, {len(df)} barras)")

# ═══════════════════════════════════════════════════════════════
# 2. DEFINIR OR TIMEFRAMES Y SESIONES
# ═══════════════════════════════════════════════════════════════
# OR = Opening Range desde 9:30
# OR 5min  = 9:30-9:34 (1 barra de 5min, pero con 15min tenemos 9:30-9:44)
# OR 15min = 9:30-9:44 (1 barra 15min)
# OR 30min = 9:30-9:59 (2 barras 15min)
# OR 45min = 9:30-10:14 (3 barras 15min)

OR_DEFS = {
    'OR_15m': (time(9, 30), time(9, 44)),   # Primera barra 15min
    'OR_30m': (time(9, 30), time(9, 59)),   # Primeras 2 barras
    'OR_45m': (time(9, 30), time(10, 14)),  # Primeras 3 barras
}

# NY Session = 9:30-16:00
NY_START = time(9, 30)
NY_END   = time(15, 59)

# PM = Pre-Market 7:00-9:29
PM_START = time(7, 0)
PM_END   = time(9, 29)

DOW_NAMES = {0: 'LUNES', 1: 'MARTES', 2: 'MIÉRCOLES', 3: 'JUEVES', 4: 'VIERNES'}
DOW_NAMES_EN = {0: 'monday', 1: 'tuesday', 2: 'wednesday', 3: 'thursday', 4: 'friday'}

# ═══════════════════════════════════════════════════════════════
# 3. PROCESAR CADA DÍA
# ═══════════════════════════════════════════════════════════════
print("\n  Procesando cada día...")

results = []  # Lista de dicts con todos los datos por día

trade_dates = sorted(df['date'].unique())
for d in trade_dates:
    day_df = df[df['date'] == d].copy()
    if len(day_df) < 10:
        continue
    
    dow = day_df.iloc[0]['dow']
    if dow > 4:  # Skip weekends
        continue
    
    # NY Session
    ny = day_df[(day_df['time'] >= NY_START) & (day_df['time'] <= NY_END)]
    if len(ny) < 4:
        continue
    
    ny_open  = float(ny.iloc[0]['Open'])
    ny_close = float(ny.iloc[-1]['Close'])
    ny_high  = float(ny['High'].max())
    ny_low   = float(ny['Low'].min())
    ny_move  = ny_close - ny_open
    ny_range = ny_high - ny_low
    ny_dir   = 'BULL' if ny_move > 30 else ('BEAR' if ny_move < -30 else 'FLAT')
    
    # PM Session
    pm = day_df[(day_df['time'] >= PM_START) & (day_df['time'] <= PM_END)]
    pm_move = 0
    pm_dir = 'FLAT'
    if len(pm) >= 2:
        pm_move = float(pm.iloc[-1]['Close']) - float(pm.iloc[0]['Open'])
        pm_dir = 'BULL' if pm_move > 15 else ('BEAR' if pm_move < -15 else 'FLAT')
    
    # Calculate each OR
    row = {
        'date': d,
        'dow': dow,
        'dow_name': DOW_NAMES[dow],
        'ny_open': ny_open,
        'ny_close': ny_close,
        'ny_move': round(ny_move),
        'ny_range': round(ny_range),
        'ny_dir': ny_dir,
        'pm_move': round(pm_move),
        'pm_dir': pm_dir,
    }
    
    for or_name, (or_start, or_end) in OR_DEFS.items():
        or_bars = day_df[(day_df['time'] >= or_start) & (day_df['time'] <= or_end)]
        if len(or_bars) < 1:
            row[f'{or_name}_high'] = None
            row[f'{or_name}_low'] = None
            row[f'{or_name}_range'] = None
            row[f'{or_name}_dir'] = None
            row[f'{or_name}_move'] = None
            continue
        
        or_open  = float(or_bars.iloc[0]['Open'])
        or_close = float(or_bars.iloc[-1]['Close'])
        or_high  = float(or_bars['High'].max())
        or_low   = float(or_bars['Low'].min())
        or_move  = or_close - or_open
        or_range = or_high - or_low
        
        row[f'{or_name}_high']  = round(or_high)
        row[f'{or_name}_low']   = round(or_low)
        row[f'{or_name}_range'] = round(or_range)
        row[f'{or_name}_move']  = round(or_move)
        row[f'{or_name}_dir']   = 'BULL' if or_move > 10 else ('BEAR' if or_move < -10 else 'FLAT')
    
    results.append(row)

df_r = pd.DataFrame(results)
n_total = len(df_r)
print(f"  Total días procesados: {n_total}")

# ═══════════════════════════════════════════════════════════════
# 4. ANÁLISIS POR DÍA × OR TIMEFRAME
# ═══════════════════════════════════════════════════════════════
print("\n" + "═" * 70)
print("  RESULTADOS: OR Direction → NY Direction")
print("═" * 70)

# Estructura: stats[dow][or_name][or_dir] = {total, bull, bear, flat, correct}
stats = {}

for dow in range(5):
    stats[dow] = {}
    day_df = df_r[df_r['dow'] == dow]
    n_day = len(day_df)
    
    print(f"\n{'━' * 70}")
    print(f"  📅 {DOW_NAMES[dow]} — {n_day} días totales")
    print(f"{'━' * 70}")
    
    # General stats
    bull_pct = (day_df['ny_dir'] == 'BULL').sum() / n_day * 100
    bear_pct = (day_df['ny_dir'] == 'BEAR').sum() / n_day * 100
    flat_pct = (day_df['ny_dir'] == 'FLAT').sum() / n_day * 100
    print(f"  Sesgo base: BULL {bull_pct:.0f}% | BEAR {bear_pct:.0f}% | FLAT {flat_pct:.0f}%")
    print(f"  Rango NY medio: {day_df['ny_range'].mean():.0f}pts | Mediana: {day_df['ny_range'].median():.0f}pts")
    
    for or_name in OR_DEFS.keys():
        stats[dow][or_name] = {}
        col_dir = f'{or_name}_dir'
        col_rng = f'{or_name}_range'
        
        valid = day_df[day_df[col_dir].notna()]
        if len(valid) == 0:
            continue
        
        print(f"\n  ┌─ {or_name} ─────────────────────────────────────")
        
        for or_dir in ['BULL', 'BEAR', 'FLAT']:
            sub = valid[valid[col_dir] == or_dir]
            ns = len(sub)
            if ns == 0:
                continue
            
            ny_bull = (sub['ny_dir'] == 'BULL').sum()
            ny_bear = (sub['ny_dir'] == 'BEAR').sum()
            ny_flat = (sub['ny_dir'] == 'FLAT').sum()
            
            # "Correct" = OR and NY same direction
            if or_dir == 'BULL':
                correct = ny_bull
                follow = f"NY BULL={ny_bull}({ny_bull/ns*100:.0f}%)"
            elif or_dir == 'BEAR':
                correct = ny_bear
                follow = f"NY BEAR={ny_bear}({ny_bear/ns*100:.0f}%)"
            else:
                correct = ny_flat
                follow = f"NY FLAT={ny_flat}({ny_flat/ns*100:.0f}%)"
            
            accuracy = correct / ns * 100
            
            # Also check reversal (opposite direction)
            if or_dir == 'BULL':
                reversal = ny_bear
                rev_pct = reversal / ns * 100
            elif or_dir == 'BEAR':
                reversal = ny_bull
                rev_pct = reversal / ns * 100
            else:
                reversal = 0
                rev_pct = 0
            
            avg_move = sub['ny_move'].mean()
            avg_or_rng = sub[col_rng].mean()
            
            bar = "█" * int(accuracy / 5)
            star = " ⭐" if accuracy >= 75 and ns >= 5 else (" 🔥" if accuracy >= 65 and ns >= 5 else "")
            
            stats[dow][or_name][or_dir] = {
                'n': ns, 'correct': correct, 'accuracy': accuracy,
                'reversal': reversal, 'rev_pct': rev_pct,
                'avg_move': avg_move, 'avg_or_rng': avg_or_rng,
                'ny_bull': ny_bull, 'ny_bear': ny_bear, 'ny_flat': ny_flat,
            }
            
            arrow = "▲" if or_dir == "BULL" else ("▼" if or_dir == "BEAR" else "─")
            print(f"  │ OR {or_dir} {arrow} → {ns:>3} días | {follow} | Acc: {accuracy:.0f}% {bar}{star}")
            if or_dir in ('BULL', 'BEAR'):
                print(f"  │          Reversal: {reversal}({rev_pct:.0f}%) | Avg NY: {avg_move:+.0f}pts | Avg OR Range: {avg_or_rng:.0f}pts")
    
    # Best OR for this day
    print(f"\n  ┌─ 🏆 MEJOR OR para {DOW_NAMES[dow]} ─────────────")
    best_acc = 0
    best_label = ""
    for or_name in OR_DEFS.keys():
        for or_dir in ['BULL', 'BEAR']:
            s = stats[dow].get(or_name, {}).get(or_dir, {})
            if s and s['n'] >= 5 and s['accuracy'] > best_acc:
                best_acc = s['accuracy']
                best_label = f"{or_name} {or_dir} → NY {or_dir}: {s['accuracy']:.0f}% ({s['correct']}/{s['n']})"
    if best_label:
        print(f"  │  {best_label}")
    else:
        print(f"  │  Sin patrón claro con N≥5")

# ═══════════════════════════════════════════════════════════════
# 5. ANÁLISIS COMBINADO: OR + PM
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "═" * 70)
print("  COMBOS: OR + PM → NY (filtros combinados)")
print("═" * 70)

for dow in range(5):
    day_df = df_r[df_r['dow'] == dow]
    print(f"\n{'━' * 70}")
    print(f"  📅 {DOW_NAMES[dow]}")
    print(f"{'━' * 70}")
    
    for or_name in OR_DEFS.keys():
        col_dir = f'{or_name}_dir'
        col_rng = f'{or_name}_range'
        valid = day_df[day_df[col_dir].notna()]
        
        combos = [
            ('OR BEAR + PM BEAR', 'BEAR', 'BEAR', 'BEAR'),
            ('OR BULL + PM BULL', 'BULL', 'BULL', 'BULL'),
            ('OR BEAR + PM BULL', 'BEAR', 'BULL', 'BEAR'),  # Divergence
            ('OR BULL + PM BEAR', 'BULL', 'BEAR', 'BULL'),  # Divergence
        ]
        
        for label, or_d, pm_d, expect_ny in combos:
            sub = valid[(valid[col_dir] == or_d) & (valid['pm_dir'] == pm_d)]
            if len(sub) < 3:
                continue
            ns = len(sub)
            correct = (sub['ny_dir'] == expect_ny).sum()
            acc = correct / ns * 100
            avg = sub['ny_move'].mean()
            star = " ⭐" if acc >= 75 and ns >= 5 else ""
            if acc >= 60:
                print(f"  {or_name} | {label} → NY {expect_ny}: {correct}/{ns} = {acc:.0f}%  avg={avg:+.0f}pts{star}")

# ═══════════════════════════════════════════════════════════════
# 6. ANÁLISIS: OR Range Grande (>100pts) como filtro
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "═" * 70)
print("  FILTRO: OR Range >100pts → ¿mayor accuracy?")
print("═" * 70)

for dow in range(5):
    day_df = df_r[df_r['dow'] == dow]
    print(f"\n  📅 {DOW_NAMES[dow]}")
    
    for or_name in OR_DEFS.keys():
        col_dir = f'{or_name}_dir'
        col_rng = f'{or_name}_range'
        valid = day_df[(day_df[col_dir].notna()) & (day_df[col_rng].notna())]
        
        for or_dir in ['BULL', 'BEAR']:
            big = valid[(valid[col_dir] == or_dir) & (valid[col_rng] > 100)]
            if len(big) < 3:
                continue
            ns = len(big)
            correct = (big['ny_dir'] == or_dir).sum()
            acc = correct / ns * 100
            avg = big['ny_move'].mean()
            star = " ⭐" if acc >= 75 and ns >= 5 else ""
            if acc >= 60:
                print(f"    {or_name} {or_dir} (rng>100): {correct}/{ns} = {acc:.0f}%  avg={avg:+.0f}pts{star}")

# ═══════════════════════════════════════════════════════════════
# 7. RESUMEN FINAL — TABLA MAESTRA
# ═══════════════════════════════════════════════════════════════
print("\n\n" + "═" * 70)
print("  📊 TABLA MAESTRA — Accuracy por Día × OR Timeframe × Dirección")
print("═" * 70)

header = f"  {'DÍA':<12} {'OR TF':<8} {'DIR':<6} {'N':>4} {'ACC':>6} {'Rev%':>6} {'AvgNY':>8} {'Nota':<10}"
print(header)
print("  " + "─" * 65)

all_patterns = []
for dow in range(5):
    for or_name in OR_DEFS.keys():
        for or_dir in ['BULL', 'BEAR']:
            s = stats[dow].get(or_name, {}).get(or_dir)
            if not s or s['n'] < 3:
                continue
            
            nota = ""
            if s['accuracy'] >= 80 and s['n'] >= 5: nota = "💎 ELITE"
            elif s['accuracy'] >= 70 and s['n'] >= 5: nota = "⭐ FUERTE"
            elif s['accuracy'] >= 60 and s['n'] >= 5: nota = "🔥 OK"
            elif s['rev_pct'] >= 60: nota = "🔄 REVERSAL"
            
            tf_short = or_name.replace('OR_', '')
            print(f"  {DOW_NAMES[dow]:<12} {tf_short:<8} {or_dir:<6} {s['n']:>4} {s['accuracy']:>5.0f}% {s['rev_pct']:>5.0f}% {s['avg_move']:>+7.0f}  {nota}")
            
            all_patterns.append({
                'dow': dow, 'dow_name': DOW_NAMES[dow],
                'or_name': or_name, 'or_dir': or_dir,
                **s, 'nota': nota
            })

# TOP 10 patterns
print("\n\n" + "═" * 70)
print("  🏆 TOP 10 PATRONES (N≥5, ordenados por Accuracy)")
print("═" * 70)
top = sorted([p for p in all_patterns if p['n'] >= 5], key=lambda x: -x['accuracy'])[:10]
for i, p in enumerate(top, 1):
    tf = p['or_name'].replace('OR_', '')
    print(f"  #{i:>2}  {p['dow_name']:<12} {tf:<6} {p['or_dir']:<5} → {p['accuracy']:.0f}% ({p['correct']}/{p['n']})  avg={p['avg_move']:+.0f}pts")

# ═══════════════════════════════════════════════════════════════
# 8. GENERAR HTML
# ═══════════════════════════════════════════════════════════════
print("\n\n  Generando HTML...")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Backtest OR Completo — NQ Whale Radar</title>
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:#0d0d1a; color:#e2e8f0; font-family:'Segoe UI',Arial,sans-serif; padding:20px; }}
h1 {{ color:#f59e0b; font-size:20px; text-align:center; margin-bottom:4px; }}
.sub {{ color:#64748b; font-size:11px; text-align:center; margin-bottom:20px; }}
.card {{ background:#131325; border:1px solid #2d2d4e; border-radius:10px; padding:18px; margin-bottom:18px; }}
.card h2 {{ color:#38bdf8; font-size:14px; margin-bottom:12px; }}
.card h3 {{ color:#f59e0b; font-size:12px; margin-bottom:8px; }}
table {{ width:100%; border-collapse:collapse; font-size:11px; }}
th {{ background:#1a1a30; color:#94a3b8; font-size:10px; font-weight:600; padding:7px 8px; text-align:center;
     border-bottom:2px solid #312e81; position:sticky; top:0; z-index:10; }}
td {{ padding:5px 8px; text-align:center; border-bottom:1px solid #1a1a2e; }}
.elite {{ background:#1a0f30; border-left:3px solid #a78bfa; }}
.fuerte {{ background:#0a1a15; border-left:3px solid #10b981; }}
.ok {{ background:#1a1a0a; border-left:3px solid #f59e0b; }}
.pos {{ color:#10b981; font-weight:700; }}
.neg {{ color:#ef4444; font-weight:700; }}
.bar {{ height:12px; border-radius:2px; display:inline-block; }}
.top-badge {{ display:inline-block; background:rgba(245,158,11,.15); border:1px solid #f59e0b;
              color:#f59e0b; padding:2px 8px; border-radius:12px; font-size:10px; font-weight:700; margin:2px; }}
.day-tab {{ display:inline-block; padding:8px 18px; margin:3px; border-radius:20px; font-size:11px;
            font-weight:700; cursor:pointer; border:1px solid #334155; color:#94a3b8; background:none; }}
.day-tab.active {{ background:rgba(56,189,248,.1); border-color:#38bdf8; color:#38bdf8; }}
.day-tab:hover {{ background:rgba(56,189,248,.05); }}
.summary-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin:14px 0; }}
.sg-item {{ background:#0d0d1a; border:1px solid #1a1a2e; border-radius:8px; padding:10px; text-align:center; }}
.sg-label {{ font-size:9px; color:#64748b; text-transform:uppercase; letter-spacing:.05em; }}
.sg-value {{ font-size:18px; font-weight:900; margin-top:4px; }}
</style>
</head>
<body>

<h1>📊 BACKTEST OR COMPLETO — NQ Whale Radar</h1>
<p class="sub">{date_min} → {date_max} · {n_total} días · OR 15m / 30m / 45m · Todos los días reales</p>

<div class="card">
  <h2>🏆 TOP 10 Patrones (N≥5)</h2>
  <table>
    <tr><th>#</th><th>Día</th><th>OR TF</th><th>Dir</th><th>N</th><th>Accuracy</th><th>Reversal</th><th>Avg NY</th><th>Nota</th></tr>
"""

for i, p in enumerate(top, 1):
    tf = p['or_name'].replace('OR_', '')
    acc_clr = '#10b981' if p['accuracy'] >= 70 else ('#f59e0b' if p['accuracy'] >= 60 else '#94a3b8')
    row_cls = 'elite' if p['accuracy'] >= 80 else ('fuerte' if p['accuracy'] >= 70 else 'ok')
    mv_cls = 'pos' if p['avg_move'] > 0 else 'neg'
    html += f"""    <tr class="{row_cls}">
      <td>{i}</td><td style="font-weight:700">{p['dow_name']}</td><td>{tf}</td>
      <td><span class="{'pos' if p['or_dir']=='BULL' else 'neg'}">{p['or_dir']}</span></td>
      <td>{p['n']}</td>
      <td style="color:{acc_clr};font-weight:900;font-size:13px">{p['accuracy']:.0f}%</td>
      <td>{p['rev_pct']:.0f}%</td>
      <td class="{mv_cls}">{p['avg_move']:+.0f}pts</td>
      <td>{p['nota']}</td>
    </tr>\n"""

html += """  </table>
</div>
"""

# Per-day detail cards
for dow in range(5):
    day_df = df_r[df_r['dow'] == dow]
    n_day = len(day_df)
    bull_n = (day_df['ny_dir'] == 'BULL').sum()
    bear_n = (day_df['ny_dir'] == 'BEAR').sum()
    flat_n = n_day - bull_n - bear_n
    avg_rng = day_df['ny_range'].mean()
    
    html += f"""
<div class="card" id="day-{DOW_NAMES_EN[dow]}">
  <h2>📅 {DOW_NAMES[dow]} — {n_day} días</h2>
  <div class="summary-grid">
    <div class="sg-item"><div class="sg-label">Total</div><div class="sg-value" style="color:#38bdf8">{n_day}</div></div>
    <div class="sg-item"><div class="sg-label">BULL</div><div class="sg-value pos">{bull_n} ({bull_n/n_day*100:.0f}%)</div></div>
    <div class="sg-item"><div class="sg-label">BEAR</div><div class="sg-value neg">{bear_n} ({bear_n/n_day*100:.0f}%)</div></div>
    <div class="sg-item"><div class="sg-label">Rango Promedio</div><div class="sg-value" style="color:#f59e0b">{avg_rng:.0f}pts</div></div>
  </div>
  <table>
    <tr><th>OR TF</th><th>OR Dir</th><th>N</th><th>NY BULL</th><th>NY BEAR</th><th>NY FLAT</th><th>Accuracy</th><th>Avg NY</th><th>Bar</th></tr>
"""
    for or_name in OR_DEFS.keys():
        for or_dir in ['BULL', 'BEAR']:
            s = stats[dow].get(or_name, {}).get(or_dir)
            if not s or s['n'] < 2:
                continue
            tf = or_name.replace('OR_', '')
            acc = s['accuracy']
            acc_clr = '#10b981' if acc >= 70 else ('#f59e0b' if acc >= 60 else '#64748b')
            bar_w = int(acc * 0.8)
            bar_c = '#10b981' if acc >= 70 else ('#f59e0b' if acc >= 60 else '#334155')
            mv_cls = 'pos' if s['avg_move'] > 0 else 'neg'
            row_cls = 'elite' if acc >= 80 and s['n'] >= 5 else ('fuerte' if acc >= 70 and s['n'] >= 5 else '')
            
            html += f"""    <tr class="{row_cls}">
      <td>{tf}</td>
      <td><span class="{'pos' if or_dir=='BULL' else 'neg'}">{or_dir}</span></td>
      <td>{s['n']}</td>
      <td class="pos">{s['ny_bull']} ({s['ny_bull']/s['n']*100:.0f}%)</td>
      <td class="neg">{s['ny_bear']} ({s['ny_bear']/s['n']*100:.0f}%)</td>
      <td>{s['ny_flat']}</td>
      <td style="color:{acc_clr};font-weight:900">{acc:.0f}%</td>
      <td class="{mv_cls}">{s['avg_move']:+.0f}pts</td>
      <td><div class="bar" style="width:{bar_w}px;background:{bar_c}"></div></td>
    </tr>\n"""
    
    html += """  </table>
</div>
"""

html += f"""
<div style="text-align:center;margin-top:20px;color:#334155;font-size:10px">
  Backtest OR Completo · {n_total} días · {date_min} → {date_max} · NQ Whale Radar
</div>
</body></html>"""

out = "backtest_or_completo.html"
with open(out, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n  ✅ HTML generado: {out}")
print(f"  📊 Total: {n_total} días | {date_min} → {date_max}")
print("═" * 70)
