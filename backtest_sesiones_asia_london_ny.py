"""
BACKTEST: Comportamiento por Sesión — Asia / London / New York
¿Asia y Londres son alcistas? ¿NY consolida?

Sesiones (UTC):
- Asia:   23:00 → 08:00 UTC  (Tokyo/Sydney)
- London: 08:00 → 14:30 UTC  (Londres overlap Frankfurt)
- NY:     14:30 → 21:00 UTC  (New York)

Métricas por sesión:
1. Dirección (BULL/BEAR/FLAT)  — % de veces alcista
2. Retorno promedio (open→close de la sesión)
3. Rango promedio (High-Low de la sesión)
4. Por día de la semana (Lun-Vie)
5. NY después de Asia alcista vs bajista
6. Secuencia más probable: Asia→London→NY
"""
import csv, sys, math
from datetime import datetime, date, time, timedelta
from statistics import mean, stdev
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

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
                    h = float(r.get('High')  or 0)
                    l = float(r.get('Low')   or 0)
                    c = float(r.get('Close') or 0)
                    if c > 0: bars.append({'dt':dt,'h':h,'l':l,'c':c})
                except: pass
    except: pass
bars.sort(key=lambda x: x['dt'])
seen, bars_u = set(), []
for b in bars:
    if b['dt'] not in seen:
        seen.add(b['dt'])
        bars_u.append(b)
bars = bars_u
print(f"   {len(bars):,} barras")

# ─── DEFINICIÓN DE SESIONES (UTC) ─────────────────────────────────────────
# Asia: 23:00 día anterior → 08:00 (usamos 22:00-08:00 para NQ que opera casi 24h)
# London: 08:00 → 14:30
# NY: 14:30 → 21:00

def get_session(dt):
    h = dt.time()
    if time(22, 0) <= h or h < time(8, 0):
        return 'ASIA'
    elif time(8, 0) <= h < time(14, 30):
        return 'LONDON'
    elif time(14, 30) <= h < time(21, 0):
        return 'NY'
    return None

# ─── CALCULAR MÉTRICAS POR SESIÓN POR DÍA ─────────────────────────────────
# Agrupamos: cada sesión diaria tiene open, close, high, low
# La sesión Asia de un lunes = barras del domingo 22:00 → lunes 08:00

# Mejor: por cada barra asignamos (fecha_de_negociación, sesión)
# Fecha_negociación = fecha del día NY (lunes a viernes)

def trading_date(dt):
    """Fecha de negociación: Asia del lunes = lunes aunque las barras sean del domingo"""
    d = dt.date()
    h = dt.time()
    # Si es después de 22:00 UTC, pertenece al día siguiente
    if h >= time(22, 0):
        d = d + timedelta(days=1)
    return d

sessions_data = defaultdict(lambda: defaultdict(list))  # {date: {session: [bars]}}

for b in bars:
    sess = get_session(b['dt'])
    if not sess:
        continue
    td = trading_date(b['dt'])
    if td.weekday() > 4:  # skip sábado/domingo como fecha de negociación
        continue
    sessions_data[td][sess].append(b)

# ─── CONSTRUIR OBSERVACIONES ───────────────────────────────────────────────
def session_stats(sess_bars):
    if len(sess_bars) < 2:
        return None
    sess_bars = sorted(sess_bars, key=lambda x: x['dt'])
    o = sess_bars[0]['c']
    c = sess_bars[-1]['c']
    h = max(b['h'] for b in sess_bars)
    l = min(b['l'] for b in sess_bars)
    ret = (c - o) / o * 100
    rng = (h - l) / o * 100
    direction = 'BULL' if ret > 0.05 else ('BEAR' if ret < -0.05 else 'FLAT')
    return {'open': o, 'close': c, 'high': h, 'low': l,
            'ret': ret, 'rng': rng, 'dir': direction}

all_days = []
for d in sorted(sessions_data.keys()):
    if d < date(2022, 6, 1): continue
    asia   = session_stats(sessions_data[d].get('ASIA', []))
    london = session_stats(sessions_data[d].get('LONDON', []))
    ny     = session_stats(sessions_data[d].get('NY', []))
    if not (asia and london and ny):
        continue
    all_days.append({
        'date'  : d,
        'dow'   : d.weekday(),  # 0=Lun
        'dow_n' : ['Lun','Mar','Mié','Jue','Vie'][d.weekday()],
        'asia'  : asia,
        'london': london,
        'ny'    : ny,
    })

n = len(all_days)
print(f"   {n} días con las 3 sesiones completas")
print(f"   Período: {all_days[0]['date']} → {all_days[-1]['date']}")

# ─── ANÁLISIS ─────────────────────────────────────────────────────────────
SEP = '='*65

def bull_pct(vals, key='dir'):
    t = [v for v in vals if v.get(key)=='BULL']
    return f"{len(t)/len(vals)*100:.0f}%" if vals else "—"

def avg_ret(vals):
    r = [v['ret'] for v in vals if 'ret' in v]
    return f"{mean(r):+.3f}%" if r else "—"

def avg_rng(vals):
    r = [v['rng'] for v in vals if 'rng' in v]
    return f"{mean(r):.3f}%" if r else "—"

print(f"\n{SEP}")
print("  BACKTEST: COMPORTAMIENTO POR SESIÓN — NQ")
print(SEP)

print(f"\n{'Sesión':<10} {'BULL%':>7} {'BEAR%':>7} {'FLAT%':>7} {'Ret avg':>10} {'Rango avg':>11}")
print("  " + "-"*55)
for sess_name, key in [('ASIA','asia'),('LONDON','london'),('NY','ny')]:
    ss = [d[key] for d in all_days]
    bull = sum(1 for s in ss if s['dir']=='BULL')
    bear = sum(1 for s in ss if s['dir']=='BEAR')
    flat = sum(1 for s in ss if s['dir']=='FLAT')
    rets = [s['ret'] for s in ss]
    rngs = [s['rng'] for s in ss]
    print(f"  {sess_name:<10} {bull/n*100:>6.0f}% {bear/n*100:>6.0f}% {flat/n*100:>6.0f}% "
          f"{mean(rets):>+9.3f}% {mean(rngs):>10.3f}%")

print(f"\n📊 2. POR DÍA DE LA SEMANA")
print(f"\n  Sesión ASIA — BULL % por día:")
print(f"  {'Día':<6}", end='')
for s_key, s_name in [('asia','ASIA'),('london','LONDON'),('ny','NY')]:
    print(f"  {s_name:>10}", end='')
print()
print("  " + "-"*40)
for dow, dname in enumerate(['Lun','Mar','Mié','Jue','Vie']):
    grp = [d for d in all_days if d['dow']==dow]
    if not grp: continue
    print(f"  {dname:<6}", end='')
    for s_key in ['asia','london','ny']:
        ss = [d[s_key] for d in grp]
        bp = sum(1 for s in ss if s['dir']=='BULL') / len(ss) * 100
        ar = mean(s['ret'] for s in ss)
        print(f"  {bp:>5.0f}% {ar:>+5.2f}%", end='')
    print()

print(f"\n📊 3. ¿NY CONSOLIDA? — Rango de NY comparado con Asia+London")
for dow, dname in enumerate(['Lun','Mar','Mié','Jue','Vie']):
    grp = [d for d in all_days if d['dow']==dow]
    if not grp: continue
    ny_rngs = [d['ny']['rng'] for d in grp]
    as_rngs = [d['asia']['rng'] for d in grp]
    lo_rngs = [d['london']['rng'] for d in grp]
    print(f"  {dname}: Asia={mean(as_rngs):.2f}%  London={mean(lo_rngs):.2f}%  NY={mean(ny_rngs):.2f}%")

print(f"\n📊 4. SECUENCIA: Si ASIA BULL → ¿Qué hace LONDON y NY?")
asia_bull = [d for d in all_days if d['asia']['dir']=='BULL']
asia_bear = [d for d in all_days if d['asia']['dir']=='BEAR']
for label, grp in [('Asia 🟢 BULL', asia_bull), ('Asia 🔴 BEAR', asia_bear)]:
    lon_bull = sum(1 for d in grp if d['london']['dir']=='BULL')
    ny_bull  = sum(1 for d in grp if d['ny']['dir']=='BULL')
    lon_ret  = mean(d['london']['ret'] for d in grp)
    ny_ret   = mean(d['ny']['ret'] for d in grp)
    print(f"\n  {label} (n={len(grp)})")
    print(f"   → London BULL: {lon_bull/len(grp)*100:.0f}%  avg={lon_ret:+.3f}%")
    print(f"   → NY    BULL:  {ny_bull/len(grp)*100:.0f}%  avg={ny_ret:+.3f}%")

print(f"\n📊 5. COMBO: Asia🟢 + London🟢 → ¿Qué hace NY?")
both_bull = [d for d in all_days
             if d['asia']['dir']=='BULL' and d['london']['dir']=='BULL']
ny_bull_b = sum(1 for d in both_bull if d['ny']['dir']=='BULL')
ny_rets_b = [d['ny']['ret'] for d in both_bull]
print(f"  Asia🟢 + London🟢 → NY BULL: {ny_bull_b/len(both_bull)*100:.0f}%  avg NY={mean(ny_rets_b):+.3f}%  n={len(both_bull)}")

both_bear = [d for d in all_days
             if d['asia']['dir']=='BEAR' and d['london']['dir']=='BEAR']
ny_bull_bb = sum(1 for d in both_bear if d['ny']['dir']=='BULL')
ny_rets_bb = [d['ny']['ret'] for d in both_bear]
print(f"  Asia🔴 + London🔴 → NY BULL: {ny_bull_bb/len(both_bear)*100:.0f}%  avg NY={mean(ny_rets_bb):+.3f}%  n={len(both_bear)}")

# Asia+London alcistas pero NY va contra ellos
contra = [d for d in both_bull if d['ny']['dir']=='BEAR']
print(f"\n  Asia🟢+London🟢 → NY BEAR (contra-tendencia): {len(contra)/len(both_bull)*100:.0f}%")

# ─── GENERAR HTML ─────────────────────────────────────────────────────────
from datetime import datetime as DT

def dir_badge(d):
    if d == 'BULL': return '<span style="background:rgba(0,255,128,.12);color:#00ff80;padding:2px 7px;border-radius:6px;font-weight:700;font-size:11px">🟢 BULL</span>'
    if d == 'BEAR': return '<span style="background:rgba(255,45,85,.12);color:#ff2d55;padding:2px 7px;border-radius:6px;font-weight:700;font-size:11px">🔴 BEAR</span>'
    return '<span style="background:rgba(148,163,184,.1);color:#94a3b8;padding:2px 7px;border-radius:6px;font-weight:700;font-size:11px">— FLAT</span>'

def ret_span(v):
    c = '#00ff80' if v > 0 else '#ff2d55' if v < 0 else '#888'
    return f'<span style="color:{c};font-weight:700">{v:+.3f}%</span>'

rows_html = ""
for d in sorted(all_days, key=lambda x:x['date'], reverse=True)[:120]:
    rows_html += f"""<tr style="border-bottom:1px solid rgba(255,255,255,0.04)">
<td style="padding:7px 10px;font-weight:700;white-space:nowrap">{d['date']}</td>
<td style="padding:7px 10px;color:#888;font-size:11px">{d['dow_n']}</td>
<td style="padding:7px 10px">{dir_badge(d['asia']['dir'])}<br><span style="color:#666;font-size:10px">{ret_span(d['asia']['ret'])} · rng {d['asia']['rng']:.2f}%</span></td>
<td style="padding:7px 10px">{dir_badge(d['london']['dir'])}<br><span style="color:#666;font-size:10px">{ret_span(d['london']['ret'])} · rng {d['london']['rng']:.2f}%</span></td>
<td style="padding:7px 10px">{dir_badge(d['ny']['dir'])}<br><span style="color:#666;font-size:10px">{ret_span(d['ny']['ret'])} · rng {d['ny']['rng']:.2f}%</span></td>
</tr>"""

# Stats globales
all_asia   = [d['asia']   for d in all_days]
all_london = [d['london'] for d in all_days]
all_ny     = [d['ny']     for d in all_days]

a_bull  = sum(1 for s in all_asia   if s['dir']=='BULL')
lo_bull = sum(1 for s in all_london if s['dir']=='BULL')
ny_bull_all = sum(1 for s in all_ny if s['dir']=='BULL')
a_ret   = mean(s['ret'] for s in all_asia)
lo_ret  = mean(s['ret'] for s in all_london)
ny_ret  = mean(s['ret'] for s in all_ny)
a_rng   = mean(s['rng'] for s in all_asia)
lo_rng  = mean(s['rng'] for s in all_london)
ny_rng  = mean(s['rng'] for s in all_ny)

now_str = DT.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Sesiones: Asia / London / NY — NQ Whale Radar</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#07070f;color:#e2e8f0;padding:24px}}
h1{{font-size:22px;font-weight:900;background:linear-gradient(135deg,#a78bfa,#60a5fa,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}}
.sub{{color:#444;font-size:12px;margin-bottom:28px}}
.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:24px}}
.card{{border-radius:16px;padding:20px;text-align:center}}
.cn{{font-size:32px;font-weight:900;margin-bottom:4px}}
.cl{{font-size:10px;text-transform:uppercase;letter-spacing:.07em;opacity:.6;margin-bottom:10px}}
.cm{{font-size:12px;opacity:.8;line-height:1.6}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:20px}}
.section{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:18px}}
.section h2{{font-size:12px;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px}}
.stat-row{{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);font-size:12px}}
.stat-row:last-child{{border-bottom:none}}
.insight{{background:linear-gradient(135deg,rgba(167,139,250,0.08),rgba(52,211,153,0.05));border:1px solid rgba(167,139,250,0.2);border-radius:12px;padding:16px;margin-bottom:20px;font-size:12px;line-height:1.8}}
.insight strong{{color:#a78bfa}}
.dow-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-bottom:20px}}
.dow-card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:12px;text-align:center;font-size:11px}}
.dow-day{{font-weight:900;color:#a78bfa;font-size:13px;margin-bottom:8px}}
.tw{{overflow-x:auto;border-radius:12px;border:1px solid rgba(255,255,255,0.06);margin-top:20px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{background:rgba(255,255,255,0.04);padding:10px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#555;border-bottom:1px solid rgba(255,255,255,0.06)}}
</style>
</head>
<body>
<h1>🌏 Sesiones Asia / London / NY — NQ</h1>
<p class="sub">UTC · {n} días · {all_days[0]['date']} → {all_days[-1]['date']} · {now_str}</p>

<div class="cards">
  <div class="card" style="background:linear-gradient(135deg,rgba(96,165,250,0.1),rgba(96,165,250,0.04));border:1px solid rgba(96,165,250,0.25)">
    <div class="cn" style="color:#60a5fa">🌏 ASIA</div>
    <div class="cl">22:00–08:00 UTC</div>
    <div class="cm">
      <b style="color:#00ff80">{a_bull/n*100:.0f}% BULL</b><br>
      Ret avg: <b>{a_ret:+.3f}%</b><br>
      Rango avg: <b>{a_rng:.3f}%</b>
    </div>
  </div>
  <div class="card" style="background:linear-gradient(135deg,rgba(167,139,250,0.1),rgba(167,139,250,0.04));border:1px solid rgba(167,139,250,0.25)">
    <div class="cn" style="color:#a78bfa">🏛️ LONDON</div>
    <div class="cl">08:00–14:30 UTC</div>
    <div class="cm">
      <b style="color:#00ff80">{lo_bull/n*100:.0f}% BULL</b><br>
      Ret avg: <b>{lo_ret:+.3f}%</b><br>
      Rango avg: <b>{lo_rng:.3f}%</b>
    </div>
  </div>
  <div class="card" style="background:linear-gradient(135deg,rgba(52,211,153,0.1),rgba(52,211,153,0.04));border:1px solid rgba(52,211,153,0.25)">
    <div class="cn" style="color:#34d399">🗽 NEW YORK</div>
    <div class="cl">14:30–21:00 UTC</div>
    <div class="cm">
      <b style="color:#00ff80">{ny_bull_all/n*100:.0f}% BULL</b><br>
      Ret avg: <b>{ny_ret:+.3f}%</b><br>
      Rango avg: <b>{ny_rng:.3f}%</b>
    </div>
  </div>
</div>

<div class="insight">
  <strong>🎯 Conclusión:</strong><br>
  Asia BULL {a_bull/n*100:.0f}% · London BULL {lo_bull/n*100:.0f}% · NY BULL {ny_bull_all/n*100:.0f}%<br>
  Asia+London🟢🟢 → NY BULL: <strong>{ny_bull_b/len(both_bull)*100:.0f}%</strong> (avg NY {mean(ny_rets_b):+.3f}%) · n={len(both_bull)}<br>
  Asia+London🔴🔴 → NY BULL: <strong>{ny_bull_bb/len(both_bear)*100:.0f}%</strong> (avg NY {mean(ny_rets_bb):+.3f}%) · n={len(both_bear)}<br>
  Asia🟢+London🟢 → NY BEAR (contra): <strong>{len(contra)/len(both_bull)*100:.0f}%</strong> de veces NY va en contra
</div>

<div class="grid2">
  <div class="section">
    <h2>📊 Si Asia BULL → London y NY</h2>
    {''.join([f"""<div class="stat-row"><span>→ London BULL:</span><span style="font-weight:700;color:#00ff80">{sum(1 for d in asia_bull if d['london']['dir']=='BULL')/len(asia_bull)*100:.0f}%  avg {mean(d['london']['ret'] for d in asia_bull):+.3f}%</span></div>""",
              f"""<div class="stat-row"><span>→ NY BULL:</span><span style="font-weight:700;color:#60a5fa">{sum(1 for d in asia_bull if d['ny']['dir']=='BULL')/len(asia_bull)*100:.0f}%  avg {mean(d['ny']['ret'] for d in asia_bull):+.3f}%</span></div>"""])}
  </div>
  <div class="section">
    <h2>📊 Si Asia BEAR → London y NY</h2>
    {''.join([f"""<div class="stat-row"><span>→ London BULL:</span><span style="font-weight:700;color:#f59e0b">{sum(1 for d in asia_bear if d['london']['dir']=='BULL')/len(asia_bear)*100:.0f}%  avg {mean(d['london']['ret'] for d in asia_bear):+.3f}%</span></div>""",
              f"""<div class="stat-row"><span>→ NY BULL:</span><span style="font-weight:700;color:#f59e0b">{sum(1 for d in asia_bear if d['ny']['dir']=='BULL')/len(asia_bear)*100:.0f}%  avg {mean(d['ny']['ret'] for d in asia_bear):+.3f}%</span></div>"""])}
  </div>
</div>

<div class="dow-grid">
{''.join([f"""<div class="dow-card">
  <div class="dow-day">{dname}</div>
  {''.join([f'<div style="margin-bottom:6px"><span style="color:#666;font-size:9px">{sn}</span><br><b style="color:{"#60a5fa" if sn=="ASIA" else "#a78bfa" if sn=="LONDON" else "#34d399"}">{sum(1 for d in all_days if d["dow"]==dow and d[sk]["dir"]=="BULL")/max(1,sum(1 for d in all_days if d["dow"]==dow))*100:.0f}%</b> <span style="color:#555;font-size:9px">{mean(d[sk]["ret"] for d in all_days if d["dow"]==dow):+.2f}%</span></div>' for sk,sn in [("asia","ASIA"),("london","LONDON"),("ny","NY")]])}
</div>""" for dow,dname in enumerate(['Lun','Mar','Mié','Jue','Vie'])])}
</div>

<div class="tw">
<table>
  <thead><tr>
    <th>Fecha</th><th>Día</th>
    <th>🌏 Asia</th><th>🏛️ London</th><th>🗽 New York</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</div>

<div style="text-align:center;margin-top:18px;color:#333;font-size:11px">
  Whale Radar · Session Analysis · NQ 15min · UTC · {now_str}
</div>
</body>
</html>"""

with open('cuadro_sesiones.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n✅ cuadro_sesiones.html → http://localhost:8765/cuadro_sesiones.html")
print(f"\n🎯 RESUMEN:")
print(f"   ASIA   BULL: {a_bull/n*100:.0f}%  avg ret: {a_ret:+.3f}%  rango: {a_rng:.3f}%")
print(f"   LONDON BULL: {lo_bull/n*100:.0f}%  avg ret: {lo_ret:+.3f}%  rango: {lo_rng:.3f}%")
print(f"   NY     BULL: {ny_bull_all/n*100:.0f}%  avg ret: {ny_ret:+.3f}%  rango: {ny_rng:.3f}%")
print(f"\n   Asia🟢+London🟢 → NY BULL: {ny_bull_b/len(both_bull)*100:.0f}%  avg: {mean(ny_rets_b):+.3f}%")
print(f"   Asia🔴+London🔴 → NY BULL: {ny_bull_bb/len(both_bear)*100:.0f}%  avg: {mean(ny_rets_bb):+.3f}%")
