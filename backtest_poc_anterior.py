"""
BACKTEST: Reacción al POC del Día Anterior

¿Qué pasa cuando el precio toca el POC (Point of Control) del día anterior?

Estudio:
1. Para cada día → calcula el POC de la sesión NY anterior
2. Detecta si el precio toca ese POC hoy (dentro de ±buffer pts)
3. Mide el movimiento posterior a los 15, 30, 60, 120 minutos
4. Clasifica: ¿Rebota (respeta POC) o Rompe (usa como trampolín)?
5. Por dirección del día anterior (BULL/BEAR)
6. Por zona del precio (POC arriba/abajo de apertura)

Output: cuadro_poc_anterior.html
"""
import csv, sys, math
from datetime import datetime, timedelta, time
from statistics import mean, stdev
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

POC_BUFFER = 8.0   # puntos NQ de tolerancia para "toca el POC"
VP_BIN     = 5.0   # bin para calcular Value Profile

# ─── CARGA BARRAS 15M ─────────────────────────────────────────────────────
print("📥 Cargando NQ 15min...")
bars = []
for fn in ['data/research/nq_15m_2024_2026.csv', 'data/research/nq_15m_intraday.csv']:
    try:
        with open(fn, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                try:
                    dt = datetime.fromisoformat(
                        (r.get('Datetime') or r.get('datetime','')).strip()
                        .replace('+00:00',''))
                    h = float(r.get('High')  or r.get('high')  or 0)
                    l = float(r.get('Low')   or r.get('low')   or 0)
                    c = float(r.get('Close') or r.get('close') or 0)
                    v = float(r.get('Volume') or r.get('volume') or 0)
                    if h > 0 and c > 0:
                        bars.append({'dt':dt,'h':h,'l':l,'c':c,'v':v or (h-l)*100})
                except: pass
    except: pass

bars.sort(key=lambda x: x['dt'])
seen, bars_u = set(), []
for b in bars:
    if b['dt'] not in seen:
        seen.add(b['dt'])
        bars_u.append(b)
bars = bars_u
print(f"   {len(bars):,} barras cargadas")

# ─── SESIÓN NY: 14:30→21:00 UTC ───────────────────────────────────────────
def is_ny(dt):
    return time(14,30) <= dt.time() < time(21,0)

# Agrupar por fecha
by_date = defaultdict(list)
for b in bars:
    d = b['dt'].date()
    if d.weekday() < 5:
        by_date[d].append(b)

# ─── CALCULAR POC ─────────────────────────────────────────────────────────
def calc_poc(day_bars):
    """Calcula POC (Point of Control) de una sesión."""
    ny = [b for b in day_bars if is_ny(b['dt'])]
    if len(ny) < 3:
        return None, None, None

    lo_all = min(b['l'] for b in ny)
    hi_all = max(b['h'] for b in ny)
    if hi_all <= lo_all:
        return None, None, None

    n_bins = max(1, int(math.ceil((hi_all - lo_all) / VP_BIN)))
    bins   = [0.0] * n_bins

    for b in ny:
        vol  = b['v'] if b['v'] > 0 else 1.0
        rng  = b['h'] - b['l'] if b['h'] > b['l'] else VP_BIN
        for i in range(n_bins):
            bl = lo_all + i * VP_BIN
            bh = bl + VP_BIN
            overlap = max(0, min(b['h'], bh) - max(b['l'], bl))
            bins[i] += vol * (overlap / rng)

    pi  = bins.index(max(bins))
    poc = lo_all + pi * VP_BIN + VP_BIN / 2

    # Calcular VAH/VAL (70% del volumen)
    total = sum(bins)
    target = total * 0.70
    acc = bins[pi]; li = hi = pi
    while acc < target and (li > 0 or hi < n_bins - 1):
        el = li-1 if li>0 else None
        eh = hi+1 if hi<n_bins-1 else None
        vl = bins[el] if el is not None else -1
        vh = bins[eh] if eh is not None else -1
        if vl <= 0 and vh <= 0: break
        if vh >= vl: hi = eh; acc += vh
        else: li = el; acc += vl

    vah = round(lo_all + hi * VP_BIN + VP_BIN, 1)
    val = round(lo_all + li * VP_BIN, 1)

    ny_o = ny[0]['c']
    ny_c = ny[-1]['c']
    day_dir = 'BULL' if ny_c > ny_o else 'BEAR'

    return round(poc, 1), vah, val, ny_o, ny_c, day_dir

# ─── CONSTRUIR DÍAS CON POC ───────────────────────────────────────────────
from datetime import date as dt_date
sorted_dates = sorted(by_date.keys())
day_poc = {}  # date → {poc, vah, val, open, close, dir}

for d in sorted_dates:
    result = calc_poc(by_date[d])
    if result and result[0]:
        poc, vah, val, ny_o, ny_c, day_dir = result
        day_poc[d] = {'poc': poc, 'vah': vah, 'val': val,
                      'open': ny_o, 'close': ny_c, 'dir': day_dir}

print(f"   {len(day_poc)} días con POC calculado")

# ─── DETECTAR TOQUE AL POC DEL DÍA ANTERIOR ───────────────────────────────
observations = []

for i, d in enumerate(sorted_dates[1:], 1):
    prev_d = sorted_dates[i-1]
    if prev_d not in day_poc: continue
    if d not in by_date: continue

    prev_poc = day_poc[prev_d]['poc']
    prev_dir = day_poc[prev_d]['dir']
    prev_close = day_poc[prev_d]['close']

    today_bars = sorted([b for b in by_date[d] if is_ny(b['dt'])],
                        key=lambda x: x['dt'])
    if len(today_bars) < 8: continue

    today_open = today_bars[0]['c']

    # POC arriba o abajo de la apertura de hoy
    poc_position = 'ABOVE' if prev_poc > today_open else 'BELOW'

    # Buscar primer toque del POC en sesión NY
    touch_idx = None
    for idx, b in enumerate(today_bars):
        if b['l'] <= prev_poc + POC_BUFFER and b['h'] >= prev_poc - POC_BUFFER:
            touch_idx = idx
            break

    if touch_idx is None:
        continue  # Hoy no tocó el POC anterior

    touch_bar  = today_bars[touch_idx]
    touch_time = touch_bar['dt'].time()
    touch_price = prev_poc  # el precio exacto del POC

    # Movimiento posterior (+15m, +30m, +60m, +120m barras)
    moves = {}
    for steps, label in [(1,'15m'), (2,'30m'), (4,'60m'), (8,'120m')]:
        fut_idx = touch_idx + steps
        if fut_idx < len(today_bars):
            fut_c = today_bars[fut_idx]['c']
            moves[label] = (fut_c - touch_price) / touch_price * 100
        else:
            moves[label] = None

    # ¿Respetó el POC (rebote) o lo rompió?
    # Rebote: precio del POC y barra siguiente vuelve hacia el open
    # Ruptura: precio cruza claramente el POC
    fut2 = today_bars[touch_idx + 2]['c'] if touch_idx + 2 < len(today_bars) else None
    if fut2:
        if poc_position == 'BELOW':
            # POC abajo de open → POC es soporte → ¿rebota hacia arriba?
            rebote = fut2 > touch_price + POC_BUFFER / 2
        else:
            # POC arriba de open → POC es resistencia → ¿rebota hacia abajo?
            rebote = fut2 < touch_price - POC_BUFFER / 2
        tipo = 'REBOTE' if rebote else 'RUPTURA'
    else:
        tipo = 'N/A'

    # Gap overnight
    gap_pct = (today_open - prev_close) / prev_close * 100

    observations.append({
        'date'         : d,
        'prev_dir'     : prev_dir,
        'prev_poc'     : prev_poc,
        'today_open'   : today_open,
        'poc_position' : poc_position,
        'touch_time'   : touch_time,
        'touch_idx'    : touch_idx,
        'tipo'         : tipo,
        'gap_pct'      : round(gap_pct, 2),
        'm15'          : moves.get('15m'),
        'm30'          : moves.get('30m'),
        'm60'          : moves.get('60m'),
        'm120'         : moves.get('120m'),
    })

n = len(observations)
print(f"   {n} veces que el precio tocó el POC del día anterior")

# ─── ANÁLISIS ─────────────────────────────────────────────────────────────
SEP = '='*65

def stats(vals, pos_dir=1):
    """pos_dir=1 → positivo es ganador; -1 → negativo es ganador (short)"""
    vals = [v for v in vals if v is not None]
    if not vals: return f"n={len(vals)}", 0
    wins = sum(1 for v in vals if (v * pos_dir) > 0)
    avg  = mean(vals)
    return f"avg={avg:+.3f}%  win={wins/len(vals)*100:.0f}%  n={len(vals)}", len(vals)

print(f"\n{SEP}")
print("  BACKTEST: REACCIÓN AL POC DEL DÍA ANTERIOR")
print(SEP)

print(f"\n📊 1. REBOTE vs RUPTURA del POC anterior")
for tipo in ['REBOTE', 'RUPTURA']:
    grp = [o for o in observations if o['tipo'] == tipo]
    m15 = [o['m15'] for o in grp if o['m15'] is not None]
    m60 = [o['m60'] for o in grp if o['m60'] is not None]
    pct_total = len(grp) / n * 100
    print(f"\n  {tipo} ({len(grp)} veces = {pct_total:.0f}%)")
    if m15: print(f"   +15m: {stats(m15)[0]}")
    if m60: print(f"   +60m: {stats(m60)[0]}")

print(f"\n📊 2. Por DIRECCIÓN del día anterior")
for prev_dir in ['BULL', 'BEAR']:
    grp = [o for o in observations if o['prev_dir'] == prev_dir]
    print(f"\n  Día anterior {prev_dir} (n={len(grp)})")
    for lbl in ['m15','m30','m60','m120']:
        vals = [o[lbl] for o in grp if o.get(lbl) is not None]
        if vals:
            pos = sum(1 for v in vals if v > 0)
            print(f"   +{lbl[1:]}: avg={mean(vals):+.3f}%  alcistas={pos/len(vals)*100:.0f}%  n={len(vals)}")

print(f"\n📊 3. Por POSICIÓN del POC (arriba/abajo de la apertura)")
for pos in ['ABOVE', 'BELOW']:
    label = "POC ARRIBA del open (resistencia)" if pos == 'ABOVE' else "POC ABAJO del open (soporte)"
    grp = [o for o in observations if o['poc_position'] == pos]
    m60 = [o['m60'] for o in grp if o.get('m60') is not None]
    print(f"\n  {label} (n={len(grp)})")
    if m60:
        pos_c = sum(1 for v in m60 if v > 0)
        print(f"   +60m: avg={mean(m60):+.3f}%  alcistas={pos_c/len(m60)*100:.0f}%  n={len(m60)}")
    # desglose por tipo
    for tipo in ['REBOTE','RUPTURA']:
        sub = [o for o in grp if o['tipo']==tipo]
        sub_m60 = [o['m60'] for o in sub if o.get('m60') is not None]
        if sub_m60:
            p = sum(1 for v in sub_m60 if v>0)
            print(f"   → {tipo}: avg={mean(sub_m60):+.3f}%  alcistas={p/len(sub_m60)*100:.0f}%  n={len(sub_m60)}")

print(f"\n📊 4. COMBO: Día anterior BULL + POC como soporte (BELOW open)")
combo = [o for o in observations
         if o['prev_dir']=='BULL' and o['poc_position']=='BELOW']
m60c = [o['m60'] for o in combo if o.get('m60') is not None]
if m60c:
    pos_c = sum(1 for v in m60c if v > 0)
    print(f"   n={len(combo)}  +60m: avg={mean(m60c):+.3f}%  alcistas={pos_c/len(m60c)*100:.0f}%")

print(f"\n📊 5. Detalle últimas observaciones")
print(f"  {'Fecha':<12} {'POC ant':<8} {'Pos':<7} {'Tipo':<9} {'Dir ant':<7} {'15m':>7} {'60m':>7} {'120m':>8}")
print("  "+ "-"*60)
for o in sorted(observations, key=lambda x:x['date'])[-25:]:
    m15s  = f"{o['m15']:+.2f}%" if o['m15'] else " N/A"
    m60s  = f"{o['m60']:+.2f}%" if o['m60'] else " N/A"
    m120s = f"{o['m120']:+.2f}%" if o['m120'] else " N/A"
    print(f"  {str(o['date']):<12} {o['prev_poc']:<8.1f} {o['poc_position']:<7} "
          f"{o['tipo']:<9} {o['prev_dir']:<7} {m15s:>7} {m60s:>7} {m120s:>8}")

# ─── GENERAR HTML ─────────────────────────────────────────────────────────
from datetime import datetime as DT

def sign_color(v):
    if v is None: return '#555', 'N/A'
    c = '#00ff80' if v > 0 else '#ff2d55'
    return c, f"{v:+.2f}%"

rows_html = ""
for o in sorted(observations, key=lambda x: x['date'], reverse=True):
    poc_pos_label = "▲ Resistencia" if o['poc_position']=='ABOVE' else "▼ Soporte"
    poc_pos_color = "#ff6b35" if o['poc_position']=='ABOVE' else "#60a5fa"
    tipo_color = "#34d399" if o['tipo']=='REBOTE' else "#f59e0b"
    dir_color  = "#00ff80" if o['prev_dir']=='BULL' else "#ff2d55"

    def cell(v):
        c, t = sign_color(v)
        return f'<span style="color:{c};font-weight:700">{t}</span>'

    rows_html += f"""<tr class="lr">
<td style="font-weight:700">{o['date']}</td>
<td style="color:{dir_color};font-weight:700">{o['prev_dir']}</td>
<td style="color:#a78bfa;font-weight:700">{o['prev_poc']:.1f}</td>
<td style="color:{poc_pos_color};font-weight:700">{poc_pos_label}</td>
<td style="color:{tipo_color};font-weight:700">{o['tipo']}</td>
<td>{cell(o['m15'])}</td>
<td>{cell(o['m30'])}</td>
<td>{cell(o['m60'])}</td>
<td>{cell(o['m120'])}</td>
</tr>"""

# Stats para summary cards
reb = [o for o in observations if o['tipo']=='REBOTE']
rup = [o for o in observations if o['tipo']=='RUPTURA']
reb60 = [o['m60'] for o in reb if o.get('m60') is not None]
rup60 = [o['m60'] for o in rup if o.get('m60') is not None]
bull_reb = [o for o in reb if o['prev_dir']=='BULL']
bear_reb = [o for o in reb if o['prev_dir']=='BEAR']

bull_reb60 = [o['m60'] for o in bull_reb if o.get('m60') is not None]
bear_reb60 = [o['m60'] for o in bear_reb if o.get('m60') is not None]

def pct_wins(vals):
    if not vals: return "—"
    return f"{sum(1 for v in vals if v>0)/len(vals)*100:.0f}%"

def avg_fmt(vals):
    if not vals: return "—"
    return f"{mean(vals):+.3f}%"

now_str = DT.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>POC Anterior — NQ Whale Radar</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#07070f;color:#e2e8f0;padding:24px;min-height:100vh}}
h1{{font-size:24px;font-weight:900;background:linear-gradient(135deg,#a78bfa,#60a5fa,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{color:#444;font-size:12px;margin:6px 0 28px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}}
.card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:18px;text-align:center}}
.cn{{font-size:28px;font-weight:900}}
.cl{{font-size:10px;color:#555;text-transform:uppercase;letter-spacing:.06em;margin-top:4px}}
.cs{{font-size:12px;color:#888;margin-top:6px}}
.section{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:14px;padding:20px;margin-bottom:20px}}
.section h2{{font-size:13px;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px}}
table.mt{{width:100%;border-collapse:collapse;font-size:12px}}
.mt thead th{{background:rgba(255,255,255,0.04);padding:9px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#555;border-bottom:1px solid rgba(255,255,255,0.06);white-space:nowrap}}
.lr{{border-bottom:1px solid rgba(255,255,255,0.03);transition:background .15s}}
.lr:hover{{background:rgba(167,139,250,0.04)}}
.lr td{{padding:9px 12px;vertical-align:middle}}
.insight{{background:linear-gradient(135deg,rgba(167,139,250,0.08),rgba(96,165,250,0.06));border:1px solid rgba(167,139,250,0.2);border-radius:12px;padding:16px;margin-bottom:20px;font-size:13px;line-height:1.7}}
.insight strong{{color:#a78bfa}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px}}
.stat-row{{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px}}
.stat-row:last-child{{border-bottom:none}}
</style>
</head>
<body>
<h1>📐 Reacción al POC del Día Anterior — NQ</h1>
<p class="sub">Buffer: ±{POC_BUFFER}pts · Session NY · {n} eventos detectados · {now_str}</p>

<div class="insight">
  <strong>¿Qué mide este backtest?</strong><br>
  Cada vez que el precio de NQ toca el POC (Point of Control = precio con más volumen) del día anterior,
  medimos si <strong>rebota</strong> (respeta el POC como S/R) o lo <strong>rompe</strong>,
  y cuánto se mueve en los siguientes 15, 30, 60 y 120 minutos.
</div>

<div class="cards">
  <div class="card">
    <div class="cn" style="color:#a78bfa">{n}</div>
    <div class="cl">Eventos totales</div>
    <div class="cs">Toques al POC anterior</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#34d399">{len(reb)}</div>
    <div class="cl">REBOTES ({len(reb)/n*100:.0f}%)</div>
    <div class="cs">+60m avg: {avg_fmt(reb60)}</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#f59e0b">{len(rup)}</div>
    <div class="cl">RUPTURAS ({len(rup)/n*100:.0f}%)</div>
    <div class="cs">+60m avg: {avg_fmt(rup60)}</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#60a5fa">{pct_wins(reb60)}</div>
    <div class="cl">Win% Rebote +60m</div>
    <div class="cs">Alcistas tras rebote</div>
  </div>
</div>

<div class="grid2">
  <div class="section">
    <h2>📊 Rebote por Dirección del Día Anterior</h2>
    <div class="stat-row"><span style="color:#00ff80">🟢 BULL anterior → Rebote +60m:</span><span style="font-weight:700">{avg_fmt(bull_reb60)} ({pct_wins(bull_reb60)} alcista)</span></div>
    <div class="stat-row"><span style="color:#ff2d55">🔴 BEAR anterior → Rebote +60m:</span><span style="font-weight:700">{avg_fmt(bear_reb60)} ({pct_wins(bear_reb60)} alcista)</span></div>
    <div class="stat-row"><span style="color:#888">Total rebotes:</span><span>{len(reb)} / {n} ({len(reb)/n*100:.0f}%)</span></div>
  </div>
  <div class="section">
    <h2>🎯 Insight Operativo</h2>
    <div style="font-size:12px;line-height:1.8;color:#ccc">
      <b style="color:#a78bfa">Si día anterior = BULL:</b><br>
      → POC es soporte abajo del open<br>
      → Toque al POC = entrada LONG potencial<br><br>
      <b style="color:#a78bfa">Si día anterior = BEAR:</b><br>
      → POC es resistencia arriba del open<br>
      → Toque al POC = entrada SHORT potencial<br><br>
      <b style="color:#34d399">Confirmación:</b> espera vela de rechazo en el POC antes de entrar
    </div>
  </div>
</div>

<div class="section">
  <h2>📋 Detalle de Eventos (más reciente → antiguo)</h2>
  <div style="overflow-x:auto">
  <table class="mt">
    <thead><tr>
      <th>Fecha</th><th>Dir. Anterior</th><th>POC</th><th>Posición</th>
      <th>Tipo</th><th>+15m</th><th>+30m</th><th>+60m</th><th>+120m</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  </div>
</div>

<div style="text-align:center;margin-top:18px;color:#333;font-size:11px">
  Whale Radar · POC analysis · NQ 15min bars · {now_str}
</div>
</body>
</html>"""

with open('cuadro_poc_anterior.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ cuadro_poc_anterior.html generado")
print(f"   → http://localhost:8765/cuadro_poc_anterior.html")
print(f"\n🎯 RESUMEN:")
print(f"   Rebotes: {len(reb)} ({len(reb)/n*100:.0f}%) | Rupturas: {len(rup)} ({len(rup)/n*100:.0f}%)")
if reb60: print(f"   Rebote +60m: avg={mean(reb60):+.3f}% wins={pct_wins(reb60)}")
if rup60: print(f"   Ruptura +60m: avg={mean(rup60):+.3f}% wins={pct_wins(rup60)}")
if bull_reb60: print(f"   Bull+Rebote +60m: avg={mean(bull_reb60):+.3f}% wins={pct_wins(bull_reb60)}")
if bear_reb60: print(f"   Bear+Rebote +60m: avg={mean(bear_reb60):+.3f}% wins={pct_wins(bear_reb60)}")
