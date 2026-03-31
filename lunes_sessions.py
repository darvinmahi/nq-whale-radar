"""
TABLA DEFINITIVA: Lunes — Asia+London (pre-NY) + NY session
COT Index (52-week rolling) + VXN viernes + VXN apertura NY
Señal mejorada con Delta VXN como filtro

SESIONES (ET):
  Asia+London = pre-market 4am-9:20am ET
  NY session  = 9:30am-4pm ET

SEÑAL MEJORADA:
  Asia+London BULL + VXN(NY open) >27 + Delta(VXN) > -2 → SHORT NY
  Asia+London bajó  + VXN <25  + COT >50              → LONG NY
  Delta VXN < -2 (VXN cayó) → cancelar SHORT, posible rebote
"""
import yfinance as yf, csv, sys, pandas as pd
from datetime import date, timedelta, datetime as DT
from statistics import mean
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── 1. COT (52-week rolling) ───────────────────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d  = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            cot_rows.append({'date': d, 'net': ll - ls})
        except: pass
cot_rows.sort(key=lambda x: x['date'])
for i, r in enumerate(cot_rows):
    hist = [x['net'] for x in cot_rows[max(0, i-52):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = (r['net'] - mn) / (mx - mn) * 100 if mx > mn else 50.0

def get_cot(monday_d):
    prev = [r for r in cot_rows if r['date'] <= monday_d - timedelta(days=3)]
    return prev[-1] if prev else None

# ── 2. Descargar datos ─────────────────────────────────────────────────────
print("Descargando datos 1h (prepost=True)...")
# QQQ con pre-market para sesiones
qqq_1h = yf.download('QQQ', period='60d', interval='1h',
                      prepost=True, auto_adjust=True, progress=False)
vxn_1h = yf.download('^VXN', period='60d', interval='1h',
                      auto_adjust=True, progress=False)
vxn_d  = yf.download('^VXN', period='90d', interval='1d',
                      auto_adjust=True, progress=False)

for df in [qqq_1h, vxn_1h, vxn_d]:
    if hasattr(df.columns, 'levels'):
        df.columns = df.columns.get_level_values(0)

# Limpiar timezone del índice
for df in [qqq_1h, vxn_1h]:
    df.index = pd.to_datetime(df.index).tz_convert('US/Eastern').tz_localize(None)

print(f"QQQ 1h prepost: {len(qqq_1h)} barras")

def vxn_at(target_date, hour_et):
    """VXN en una hora específica de un día dado."""
    day_vxn = vxn_1h[vxn_1h.index.date == target_date]
    bars = day_vxn[day_vxn.index.hour == hour_et]
    if bars.empty:
        # tomar la más cercana
        bars = day_vxn
    if not bars.empty:
        return round(float(bars['Close'].iloc[-1]), 2)
    return None

def vxn_friday(monday_d):
    """VXN cierre del viernes anterior."""
    for delta in [3, 4, 5]:
        fd = monday_d - timedelta(days=delta)
        m = vxn_d[vxn_d.index.date == fd]
        if not m.empty:
            return round(float(m['Close'].iloc[-1]), 2)
    return None

def session_return(day_bars, h_start, h_end, m_end=59):
    """Retorno Open primera barra → Close última barra de la ventana horaria."""
    mask = (day_bars.index.hour >= h_start) & (
        (day_bars.index.hour < h_end) |
        ((day_bars.index.hour == h_end) & (day_bars.index.minute <= m_end))
    )
    sel = day_bars[mask]
    if len(sel) < 2:
        return None
    entry = float(sel['Open'].iloc[0])
    exit_ = float(sel['Close'].iloc[-1])
    if entry == 0:
        return None
    return round((exit_ - entry) / entry * 100, 3)

# ── 3. Calcular por lunes ──────────────────────────────────────────────────
lunes_dates = sorted(set(
    d for d in qqq_1h.index.date
    if date.fromisoformat(str(d)).weekday() == 0
))

results = []
for lunes_d in lunes_dates:
    day = qqq_1h[qqq_1h.index.date == lunes_d]
    if day.empty or len(day) < 4:
        continue

    cot = get_cot(lunes_d)
    ci  = round(cot['ci'], 1) if cot else 50.0

    # VXN referencias
    vxn_vie = vxn_friday(lunes_d)
    vxn_ny  = vxn_at(lunes_d, 9)   # VXN a las 9am ET ≈ minutos antes de NY open
    delta_vxn = round(vxn_ny - vxn_vie, 2) if (vxn_ny and vxn_vie) else None

    # Sesiones (ET)
    asia_lon = session_return(day, 4, 9, m_end=19)  # 4am → 9:19am
    ny_sess  = session_return(day, 9, 16)            # 9:30am → 4pm

    # ── SEÑAL MEJORADA ──────────────────────────────────────────────────────
    # Factores:
    #  A) Asia+London: BULL o BEAR
    #  B) VXN en NY open: alto o bajo
    #  C) Delta VXN: ¿VXN comprimió? (-2 = no shortear)
    #  D) COT Index

    vxn_ref = vxn_ny or vxn_vie or 25
    al_bull = asia_lon is not None and asia_lon > 0.1
    al_bear = asia_lon is not None and asia_lon < -0.1
    vxn_alto = vxn_ref > 27
    vxn_bajo = vxn_ref < 25
    delta_ok_short = delta_vxn is None or delta_vxn > -2.0  # VXN no cayó >2pts

    if vxn_alto and delta_ok_short and ci < 65:
        señal = 'SHORT 🔴'
        acierto = ny_sess is not None and ny_sess < 0
    elif vxn_bajo and ci > 45:
        señal = 'LONG 🟢'
        acierto = ny_sess is not None and ny_sess > 0
    elif vxn_alto and not delta_ok_short:
        señal = 'NEUTRO ⚪'  # VXN cayó → rebote, no shortear
        acierto = None
    else:
        señal = 'NEUTRO ⚪'
        acierto = None

    results.append({
        'd': lunes_d, 'ci': ci,
        'vxn_vie': vxn_vie, 'vxn_ny': vxn_ny, 'delta': delta_vxn,
        'asia_lon': asia_lon, 'ny': ny_sess,
        'señal': señal, 'acierto': acierto,
    })

# ── 4. HTML ────────────────────────────────────────────────────────────────
def ret_color(v):
    if v is None: return '#444', 'N/A'
    c = '#00e676' if v > 0 else '#ff1744'
    return c, f'{v:+.3f}%'

def delta_color(v):
    if v is None: return '#444', 'N/A'
    if v < -2:   c = '#00e676'; label = f'{v:+.2f} 📉VXN↓'
    elif v > 1.5: c = '#ff1744'; label = f'{v:+.2f} 📈VXN↑'
    else:         c = '#888';    label = f'{v:+.2f}'
    return c, label

def vxn_col(v):
    if v is None: return '#444', 'N/A'
    col = '#00e676' if v<20 else '#69f0ae' if v<25 else '#ffeb3b' if v<28 else '#ff9800' if v<34 else '#ff1744'
    return col, str(v)

def cot_col(v):
    return '#ff9800' if v>75 else '#ffeb3b' if v>50 else '#69f0ae' if v>25 else '#00e676'

rows = ''
for r in results:
    alc, alt = ret_color(r['asia_lon'])
    nyc, nyt = ret_color(r['ny'])
    dc, dt   = delta_color(r['delta'])
    v1c, v1t = vxn_col(r['vxn_vie'])
    v2c, v2t = vxn_col(r['vxn_ny'])
    cc = cot_col(r['ci'])
    aok = '✅' if r['acierto'] is True else ('❌' if r['acierto'] is False else '⚪')
    sc = '#00e676' if 'LONG' in r['señal'] else '#ff1744' if 'SHORT' in r['señal'] else '#555'
    al_dir = '🟢' if r['asia_lon'] and r['asia_lon']>0.1 else ('🔴' if r['asia_lon'] and r['asia_lon']<-0.1 else '⚪')

    rows += f"""
<tr class="row">
  <td class="dc">{r['d']}</td>
  <td style="color:{cc};font-weight:700">{r['ci']:.1f}%</td>
  <td style="color:{v1c};font-weight:700">{v1t}</td>
  <td style="color:{v2c};font-weight:700">{v2t}</td>
  <td style="color:{dc};font-weight:700;font-size:11px">{dt}</td>
  <td style="color:{alc};font-weight:800">{alt} {al_dir}</td>
  <td style="color:{nyc};font-weight:800;font-size:14px">{nyt}</td>
  <td style="color:{sc};font-weight:700">{r['señal']}</td>
  <td style="font-weight:700;text-align:center">{aok}</td>
</tr>"""

n = len(results)
ok_list = [r['acierto'] for r in results if r['acierto'] is not None]
model_pct = sum(ok_list)/len(ok_list)*100 if ok_list else 0
ny_bull = sum(1 for r in results if r['ny'] and r['ny']>0)
ny_bear = sum(1 for r in results if r['ny'] and r['ny']<0)
now_str = DT.now().strftime('%d/%m/%Y %H:%M')

# Estudio rápido: Asia+London BULL → NY qué hace
al_bull_r = [r for r in results if r['asia_lon'] and r['asia_lon']>0.1]
al_bull_ny_bear = sum(1 for r in al_bull_r if r['ny'] and r['ny']<0) if al_bull_r else 0
al_bear_r = [r for r in results if r['asia_lon'] and r['asia_lon']<-0.1]
al_bear_ny_bear = sum(1 for r in al_bear_r if r['ny'] and r['ny']<0) if al_bear_r else 0

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🎯 Lunes Sessions — Asia+London vs NY</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#07070f;color:#e2e8f0;padding:20px;min-height:100vh}}
h1{{font-size:20px;font-weight:900;background:linear-gradient(135deg,#f59e0b,#ef4444,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}}
.sub{{color:#333;font-size:11px;margin-bottom:20px}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px}}
.card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:14px;text-align:center}}
.cn{{font-size:24px;font-weight:900;margin-bottom:4px}}
.cl{{font-size:9px;color:#333;text-transform:uppercase;letter-spacing:.07em}}
.insight{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px}}
.box{{background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.06);border-radius:12px;padding:14px;font-size:12px;line-height:1.9}}
.box h3{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px}}
.tw{{overflow-x:auto;border-radius:12px;border:1px solid rgba(255,255,255,0.06)}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{background:rgba(255,255,255,0.04);padding:9px 10px;text-align:left;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#444;border-bottom:1px solid rgba(255,255,255,0.06);white-space:nowrap}}
.row{{border-bottom:1px solid rgba(255,255,255,0.03);transition:background .1s}}
.row:hover{{background:rgba(255,255,255,0.03)}}
.row td{{padding:9px 10px}}
.dc{{color:#a78bfa;font-weight:700;white-space:nowrap}}
.rule{{background:linear-gradient(135deg,rgba(239,68,68,0.08),rgba(167,139,250,0.05));border:1px solid rgba(239,68,68,0.2);border-radius:10px;padding:12px;margin-bottom:20px;font-size:12px;line-height:1.9}}
</style>
</head>
<body>
<h1>🎯 Lunes — Asia+London (Setup) vs NY (Trade)</h1>
<p class="sub">COT 52-week rolling · VXN viernes · VXN apertura NY · Señal mejorada · {now_str}</p>

<div class="rule">
  <strong style="color:#f59e0b">⚡ SETUP:</strong>
  Asia+London (4am→9:20am ET) = El contexto que se forma ANTES de NY
  &nbsp;|&nbsp;
  <strong style="color:#ef4444">🎯 TRADE:</strong>
  NY session (9:30am→4pm ET) = LA OPERACIÓN
  <br>
  <strong style="color:#a78bfa">Señal SHORT:</strong> VXN(NY open) &gt;27 + Delta &gt; -2 + COT&lt;65 &nbsp;|&nbsp;
  <strong style="color:#00e676">Señal LONG:</strong> VXN &lt;25 + COT &gt;45
  &nbsp;|&nbsp;
  <strong style="color:#888">DELTA &lt; -2:</strong> VXN cayendo → no shortear (rebote)
</div>

<div class="grid">
  <div class="card">
    <div class="cn" style="color:#a78bfa">{n}</div>
    <div class="cl">Lunes analizados</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#00e676">{ny_bull}</div>
    <div class="cl">NY Bull ({ny_bull/n*100:.0f}%)</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#ff1744">{ny_bear}</div>
    <div class="cl">NY Bear ({ny_bear/n*100:.0f}%)</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#60a5fa">{model_pct:.0f}%</div>
    <div class="cl">Modelo ({sum(ok_list)}/{len(ok_list)} ok)</div>
  </div>
</div>

<div class="insight">
  <div class="box">
    <h3 style="color:#00e676">Cuando Asia+London 🟢 BULL ({len(al_bull_r)} lunes)</h3>
    NY también BULL: <strong style="color:#00e676">{len(al_bull_r)-al_bull_ny_bear}/{len(al_bull_r)} = {(len(al_bull_r)-al_bull_ny_bear)/len(al_bull_r)*100:.0f}%</strong><br>
    NY BEAR (reversión): <strong style="color:#ff1744">{al_bull_ny_bear}/{len(al_bull_r)} = {al_bull_ny_bear/len(al_bull_r)*100:.0f}%</strong><br>
    <em style="color:#555">→ Cuando Asia+London suben, NY revierte</em>
  </div>
  <div class="box">
    <h3 style="color:#ff1744">Cuando Asia+London 🔴 BEAR ({len(al_bear_r)} lunes)</h3>
    NY también BEAR: <strong style="color:#ff1744">{al_bear_ny_bear}/{len(al_bear_r)} = {al_bear_ny_bear/len(al_bear_r)*100:.0f}%</strong><br>
    NY BULL (rebote): <strong style="color:#00e676">{len(al_bear_r)-al_bear_ny_bear}/{len(al_bear_r)} = {(len(al_bear_r)-al_bear_ny_bear)/len(al_bear_r)*100:.0f}%</strong><br>
    <em style="color:#555">→ Cuando Asia+London bajan, NY continúa o rebota</em>
  </div>
</div>

<div class="tw">
<table>
<thead><tr>
  <th>Fecha</th>
  <th>COT Index</th>
  <th>VXN viernes</th>
  <th>VXN NY open</th>
  <th>Delta VXN</th>
  <th>Asia+London (4a-9:20a ET)</th>
  <th>NY Session (9:30a-4p ET)</th>
  <th>Señal</th>
  <th>✓</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>
</div>

<div style="margin-top:14px;font-size:10px;color:#222;display:flex;gap:20px;flex-wrap:wrap">
  <span>🟢 Asia+London BULL &gt;+0.1%</span>
  <span>🔴 Asia+London BEAR &lt;-0.1%</span>
  <span>📈 Delta VXN subió &gt;1.5 pts (refuerza SHORT)</span>
  <span>📉 Delta VXN bajó &lt;-2 pts (cancela SHORT = rebote)</span>
</div>
<div style="text-align:center;margin-top:16px;color:#1a1a2e;font-size:10px">Whale Radar · Lunes Sessions · {now_str}</div>
</body>
</html>"""

with open('lunes_sessions.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ lunes_sessions.html → http://localhost:8765/lunes_sessions.html")
print(f"\n  {n} lunes  |  Modelo: {model_pct:.0f}% ({sum(ok_list)}/{len(ok_list)})")
print(f"  Asia+London BULL → NY BEAR: {al_bull_ny_bear}/{len(al_bull_r)} = {al_bull_ny_bear/len(al_bull_r)*100:.0f}%" if al_bull_r else "")
print(f"  NY Bull: {ny_bull}/{n} = {ny_bull/n*100:.0f}%  |  NY Bear: {ny_bear}/{n} = {ny_bear/n*100:.0f}%")
