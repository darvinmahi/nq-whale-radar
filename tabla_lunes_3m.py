"""
TABLA HTML: Comparativa Lunes — VXN del Lunes + Estudio Histórico niveles
COT + VIX + VXN DEL LUNES + SP500 + QQQ
"""
import yfinance as yf, csv, sys
from datetime import date, timedelta
from statistics import mean
import pandas as pd
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── COT ────────────────────────────────────────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            cot_rows.append({'date':d,'net':ll-ls})
        except: pass
cot_rows.sort(key=lambda x:x['date'])
for i,r in enumerate(cot_rows):
    hist=[x['net'] for x in cot_rows[max(0,i-156):i+1]]
    mn,mx=min(hist),max(hist)
    r['ci']=(r['net']-mn)/(mx-mn)*100 if mx>mn else 50.0

def get_cot(monday_d):
    prev=[r for r in cot_rows if r['date']<=monday_d-timedelta(days=3)]
    return prev[-1] if prev else None

# ── Datos yfinance ─────────────────────────────────────────────────────────
print("Descargando...")
tickers = ['QQQ', '^GSPC', '^VIX', '^VXN']
data = yf.download(tickers, period='13mo', interval='1d',
                   auto_adjust=True, progress=False)
closes = data['Close']
opens  = data['Open']
highs  = data['High']
lows   = data['Low']
for df in [closes, opens, highs, lows]:
    if hasattr(df.columns,'levels'):
        df.columns = df.columns.get_level_values(0)

def get_val(df, ticker, target_date, col='close'):
    for delta in [0,-1,-2,-3]:
        fd = target_date + timedelta(days=delta)
        m = df[df.index.date == fd]
        if not m.empty and ticker in m.columns:
            return round(float(m[ticker].iloc[-1]), 2)
    return None

# ── TODOS LOS LUNES 1 AÑO para el estudio histórico ──────────────────────
all_lunes = closes[closes.index.weekday==0]
all_lunes = all_lunes[all_lunes.index >= pd.Timestamp.now() - pd.Timedelta(days=370)]

all_results = []
for idx in all_lunes.index:
    d  = idx.date()
    fri = d - timedelta(days=3)
    cot = get_cot(d)
    ci  = round(cot['ci'],1) if cot else 50.0
    vxn_mon = get_val(closes,'^VXN', d)   # VXN cierre del LUNES
    vxn_fri = get_val(closes,'^VXN', fri)  # VXN cierre del VIERNES (para señal)
    vix_mon = get_val(closes,'^VIX', d)
    qqq_o = get_val(opens,'QQQ', d)
    qqq_c = get_val(closes,'QQQ', d)
    spy_o = get_val(opens,'^GSPC', d)
    spy_c = get_val(closes,'^GSPC', d)
    if not (qqq_o and qqq_c): continue
    qqq_ret = round((qqq_c-qqq_o)/qqq_o*100, 2)
    spy_ret = round((spy_c-spy_o)/spy_o*100, 2) if spy_o and spy_c else None
    vxn_sig = vxn_fri or vxn_mon or 25
    if vxn_sig < 25 and ci > 50:
        señal = 'LONG'; acierto = qqq_ret > 0
    elif vxn_sig > 28 and ci < 60:
        señal = 'SHORT'; acierto = qqq_ret <= 0
    else:
        señal = 'NEUTRAL'; acierto = None
    all_results.append({
        'd': d, 'ci': ci, 'vxn_mon': vxn_mon, 'vxn_fri': vxn_fri,
        'vix': vix_mon, 'qqq_ret': qqq_ret, 'spy_ret': spy_ret,
        'señal': señal, 'acierto': acierto,
    })

# Últimos 6 meses para la tabla principal
results = [r for r in all_results
           if r['d'] >= (date.today() - timedelta(days=185))]

# Estudio histórico por niveles VXN del LUNES (1 año)
def vxn_zone_study(data, key='vxn_mon'):
    zones = [
        (0,  18,  '< 18 (Calma total)', '#00e676'),
        (18, 22,  '18–22 (Normal bajo)', '#69f0ae'),
        (22, 26,  '22–26 (Normal alto)', '#ffeb3b'),
        (26, 30,  '26–30 (Elevado)',     '#ff9800'),
        (30, 35,  '30–35 (Miedo)',       '#ff6b35'),
        (35, 999, '> 35 (Pánico)',       '#ff1744'),
    ]
    rows = []
    for lo, hi, label, color in zones:
        grp = [r for r in data if r.get(key) and lo <= r[key] < hi]
        if not grp: continue
        bp  = sum(1 for r in grp if r['qqq_ret'] > 0)
        av  = mean(r['qqq_ret'] for r in grp)
        rng = mean(abs(r['qqq_ret']) for r in grp)
        rows.append({'label': label, 'color': color, 'n': len(grp),
                     'bull': bp, 'bull_pct': bp/len(grp)*100,
                     'avg': av, 'rng': rng})
    return rows

vxn_study = vxn_zone_study(all_results, 'vxn_mon')

# ── HTML ───────────────────────────────────────────────────────────────────
def ret_color(v, is_long=True):
    if v is None: return '#555', 'N/A'
    c = '#00e676' if v > 0 else '#ff1744'
    return c, f"{v:+.2f}%"

def vxn_color(v):
    if v is None: return '#555'
    if v < 20: return '#00e676'
    if v < 25: return '#69f0ae'
    if v < 28: return '#ffeb3b'
    if v < 34: return '#ff9800'
    return '#ff1744'

def cot_color(v):
    if v > 75: return '#ff9800'
    if v > 50: return '#ffeb3b'
    if v > 25: return '#69f0ae'
    return '#00e676'

rows_html = ""
for r in results:
    qc, qt = ret_color(r['qqq_ret'])
    sc, st = ret_color(r.get('spy_ret'))
    vc = vxn_color(r['vxn_mon'])
    cc = cot_color(r['ci'])
    aok = '✅' if r['acierto'] is True else ('❌' if r['acierto'] is False else '⚪')
    señal_c = {'LONG':'#00e676','SHORT':'#ff1744','NEUTRAL':'#888'}[r['señal']]
    vix_c = '#ff1744' if r['vix'] and r['vix']>25 else ('#ff9800' if r['vix'] and r['vix']>20 else '#00e676')
    vxn_fri_v = r.get('vxn_fri') or 'N/A'
    vxn_fri_c = vxn_color(r.get('vxn_fri'))

    rows_html += f"""
<tr class="row">
  <td class="date-cell">{r['d']}</td>
  <td style="color:{cc};font-weight:700">{r['ci']:.1f}%</td>
  <td style="color:{vxn_fri_c};font-weight:700">{vxn_fri_v}</td>
  <td style="color:{vc};font-weight:700">{r['vxn_mon'] or 'N/A'}</td>
  <td style="color:{vix_c};font-weight:700">{r['vix'] or 'N/A'}</td>
  <td style="color:{qc};font-weight:800;font-size:14px">{qt}</td>
  <td style="color:{sc};font-weight:700">{st}</td>
  <td style="color:{señal_c};font-weight:700">{r['señal']}</td>
  <td style="font-weight:700">{aok}</td>
</tr>"""

n = len(results)
bull = sum(1 for r in results if r['qqq_ret']>0)
bear = sum(1 for r in results if r['qqq_ret']<=0)
acum = sum(r['qqq_ret'] for r in results)
ok_list = [r['acierto'] for r in results if r['acierto'] is not None]
model_pct = sum(ok_list)/len(ok_list)*100 if ok_list else 0
vxn_now = results[-1]['vxn_mon'] if results else 0

# HTML estudio VXN
vxn_study_html = ''
for z in vxn_study:
    bar_w = int(z['bull_pct'])
    bar_c = '#00e676' if z['bull_pct']>=65 else ('#ffeb3b' if z['bull_pct']>=50 else '#ff1744')
    avg_c = '#00e676' if z['avg']>0 else '#ff1744'
    vxn_study_html += f"""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;font-size:12px">
  <div style="width:120px;color:{z['color']};font-weight:700">{z['label']}</div>
  <div style="width:30px;text-align:right;color:#666">{z['n']}</div>
  <div style="flex:1;background:rgba(255,255,255,0.05);border-radius:4px;height:18px;overflow:hidden">
    <div style="width:{bar_w}%;background:{bar_c};height:100%;border-radius:4px;display:flex;align-items:center;padding-left:6px">
      <span style="font-size:10px;font-weight:700;color:#000">{z['bull_pct']:.0f}%</span>
    </div>
  </div>
  <div style="width:70px;text-align:right;color:{avg_c};font-weight:700">{z['avg']:+.3f}%</div>
  <div style="width:60px;text-align:right;color:#555;font-size:10px">rng {z['rng']:.2f}%</div>
</div>"""
now_str_html = vxn_now

from datetime import datetime as DT
now_str = DT.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Comparativa Lunes 6 Meses</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#07070f;color:#e2e8f0;padding:24px;min-height:100vh}}
h1{{font-size:22px;font-weight:900;background:linear-gradient(135deg,#a78bfa,#60a5fa,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}}
.sub{{color:#444;font-size:12px;margin-bottom:24px}}
.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:24px}}
.card{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;text-align:center}}
.cn{{font-size:26px;font-weight:900;margin-bottom:2px}}
.cl{{font-size:9px;color:#444;text-transform:uppercase;letter-spacing:.07em;margin-bottom:4px}}
.cs{{font-size:11px;color:#666}}
.insight{{background:linear-gradient(135deg,rgba(167,139,250,0.08),rgba(52,211,153,0.05));border:1px solid rgba(167,139,250,0.2);border-radius:12px;padding:14px;margin-bottom:20px;font-size:12px;line-height:1.8}}
.insight strong{{color:#a78bfa}}
.tw{{overflow-x:auto;border-radius:14px;border:1px solid rgba(255,255,255,0.07)}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{background:rgba(255,255,255,0.04);padding:10px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#555;border-bottom:1px solid rgba(255,255,255,0.07);white-space:nowrap}}
.row{{border-bottom:1px solid rgba(255,255,255,0.03);transition:background .15s}}
.row:hover{{background:rgba(167,139,250,0.05)}}
.row td{{padding:10px 12px;vertical-align:middle}}
.date-cell{{font-weight:700;color:#a78bfa;white-space:nowrap}}
.legend{{display:flex;gap:16px;margin-top:16px;flex-wrap:wrap;font-size:11px}}
.leg{{display:flex;align-items:center;gap:6px}}
.dot{{width:10px;height:10px;border-radius:50%}}
</style>
</head>
<body>
<h1>📅 Lunes — VXN del Día + Estudio Histórico 1 Año</h1>
<p class="sub">QQQ + SP500 + VXN LUNES + VIX + COT Index · {n} lunes tabla / {len(all_results)} lunes estudio · {now_str}</p>

<div class="cards">
  <div class="card">
    <div class="cn" style="color:#a78bfa">{n}</div>
    <div class="cl">Lunes (6m tabla)</div>
    <div class="cs">{len(all_results)} lunes en el estudio</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#00e676">{bull}</div>
    <div class="cl">BULL ({bull/n*100:.0f}%)</div>
    <div class="cs">QQQ subió</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#ff1744">{bear}</div>
    <div class="cl">BEAR ({bear/n*100:.0f}%)</div>
    <div class="cs">QQQ bajó</div>
  </div>
  <div class="card">
    <div class="cn" style="color:{'#00e676' if acum>0 else '#ff1744'}">{acum:+.1f}%</div>
    <div class="cl">Acum. LONG</div>
    <div class="cs">si compras todos</div>
  </div>
  <div class="card">
    <div class="cn" style="color:#60a5fa">{model_pct:.0f}%</div>
    <div class="cl">Modelo VXN+COT</div>
    <div class="cs">{sum(ok_list)}/{len(ok_list)} aciertos</div>
  </div>
</div>

<div style="background:rgba(255,255,255,0.02);border:1px solid rgba(255,255,255,0.07);border-radius:14px;padding:18px;margin-bottom:20px">
  <div style="font-size:11px;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:.07em;margin-bottom:14px">🔬 Estudio VXN del Lunes → BULL% del día (último 1 año · {len(all_results)} lunes)</div>
  <div style="font-size:10px;color:#555;margin-bottom:10px;display:flex;gap:10px">
    <span style="width:120px">Nivel VXN</span><span style="width:30px">N</span><span style="flex:1">% BULL lunes</span><span style="width:70px">Avg ret</span><span style="width:60px">Rango</span>
  </div>
  {vxn_study_html}
</div>

<div class="insight">
  <strong>🎯 Regla:</strong> VXN lunes &lt; 25 → <strong style="color:#00e676">LONG lunes</strong> &nbsp;|&nbsp; VXN &gt; 28 + COT &lt; 60% → <strong style="color:#ff1744">SHORT lunes</strong> (entrada en venta)<br>
  <strong>VXN ahora:</strong> {vxn_now} → <strong style="color:{'#ff1744' if vxn_now and vxn_now>28 else '#00e676'}">{'🔴 SHORT — VXN alto = mercado bajista el lunes' if vxn_now and vxn_now>28 else '🟢 LONG — VXN bajo = mercado alcista el lunes'}</strong>
</div>

<div class="tw">
<table>
  <thead><tr>
    <th>Fecha</th>
    <th>COT Index</th>
    <th>VXN Vier.</th>
    <th>VXN Lunes</th>
    <th>VIX Lunes</th>
    <th>QQQ día</th>
    <th>SP500 día</th>
    <th>Señal</th>
    <th>✓</th>
  </tr></thead>
  <tbody>{rows_html}</tbody>
</table>
</div>

<div class="legend">
  <div class="leg"><div class="dot" style="background:#00e676"></div> VXN &lt;20 (Calma)</div>
  <div class="leg"><div class="dot" style="background:#ffeb3b"></div> VXN 22-27 (Normal)</div>
  <div class="leg"><div class="dot" style="background:#ff9800"></div> VXN 27-34 (Miedo)</div>
  <div class="leg"><div class="dot" style="background:#ff1744"></div> VXN &gt;34 (Pánico)</div>
  <div class="leg"><div class="dot" style="background:#a78bfa"></div> COT (escala 0-100%)</div>
</div>

<div style="text-align:center;margin-top:20px;color:#222;font-size:11px">
  Whale Radar · Lunes 3M · {now_str}
</div>
</body>
</html>"""

with open('tabla_lunes_3m.html','w',encoding='utf-8') as f:
    f.write(html)

print(f"✅ tabla_lunes_3m.html → http://localhost:8765/tabla_lunes_3m.html")
print(f"\n   {bull}/{n} BULL ({bull/n*100:.0f}%) | Acum LONG: {acum:+.2f}%")
print(f"   Modelo acierto: {model_pct:.0f}%  ({sum(ok_list)}/{len(ok_list)})")
