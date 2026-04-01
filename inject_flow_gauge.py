"""
inject_flow_gauge.py — v1
Commercial Flow Index: velocímetro basado en COM Short weekly change.
- Lee nasdaq_cot_historical.csv
- Calcula Flow Index (0-100) sobre últimas 156 semanas
- Genera widget SVG premium e inyecta en index.html
Markers: <!-- FLOW_GAUGE_START --> / <!-- FLOW_GAUGE_END -->
"""
import csv, re, sys, math
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH = 'index.html'
MARKER_S  = '<!-- FLOW_GAUGE_START -->'
MARKER_E  = '<!-- FLOW_GAUGE_END -->'
ANCHOR    = '<!-- COT_TABLE_END -->'          # inject AFTER this marker

# ── 1. Cargar COM Short histórico ─────────────────────────────────────────────
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            com_s = int(r.get('Dealer_Positions_Short_All') or 0)
            d = r['Report_Date_as_MM_DD_YYYY'].strip()
            if com_s:
                rows.append({'date': d, 'com_s': com_s})
        except:
            pass
rows.sort(key=lambda x: x['date'])
if len(rows) < 10:
    print('ERROR: CSV insuficiente'); sys.exit(1)

# ── 2. Cambios semana a semana ──────────────────────────────────────────────
changes = []
for i in range(1, len(rows)):
    delta = rows[i]['com_s'] - rows[i-1]['com_s']
    changes.append({'date': rows[i]['date'], 'com_s': rows[i]['com_s'], 'change': delta})

last156 = changes[-156:]
vals    = [x['change'] for x in last156]
ch_min  = min(vals)
ch_max  = max(vals)
curr    = changes[-1]

# ── 3. Flow Index (invertido: alto = alcista) ──────────────────────────────
# Cambio negativo (redujeron cortos/compraron) debe dar índice ALTO
fi_raw  = (ch_max - curr['change']) / (ch_max - ch_min) * 100 if ch_max != ch_min else 50.0
fi      = round(max(0.0, min(100.0, fi_raw)), 1)
change  = curr['change']
com_s   = curr['com_s']

# ── 4. Textos y colores ────────────────────────────────────────────────────
def lbl(d):
    for fmt in ('%m/%d/%Y', '%Y-%m-%d'):
        try: return datetime.strptime(d, fmt).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d

if fi >= 70:
    zcol  = '#22c55e'; zbg = 'rgba(34,197,94,.07)'; zborder = 'rgba(34,197,94,.2)'
    sesgo = 'ALCISTA'; emoji = '🟢'; zsub = 'Comerciales comprando fuerte — sesgo largo'
elif fi >= 30:
    zcol  = '#eab308'; zbg = 'rgba(234,179,8,.07)'; zborder = 'rgba(234,179,8,.2)'
    sesgo = 'NEUTRAL'; emoji = '🟡'; zsub = 'Sin señal dominante — operar solo con precio'
else:
    zcol  = '#ef4444'; zbg = 'rgba(239,68,68,.07)'; zborder = 'rgba(239,68,68,.2)'
    sesgo = 'BAJISTA'; emoji = '🔴'; zsub = 'Comerciales vendiendo fuerte — sesgo corto'

if change < 0:
    action = f'Compraron {abs(change):,} contratos · redujeron cortos'
    action_color = '#22c55e'
else:
    action = f'Vendieron {abs(change):,} contratos · aumentaron cortos'
    action_color = '#ef4444'

# ── 5. Generar SVG velocímetro ─────────────────────────────────────────────
def pt(f, r, cx=150, cy=148):
    a = math.radians(180 - f * 1.8)
    return cx + r * math.cos(a), cy - r * math.sin(a)

def arc_band(f1, f2, col, r_out=108, r_in=82, cx=150, cy=148):
    x1o, y1o = pt(f1, r_out); x2o, y2o = pt(f2, r_out)
    x1i, y1i = pt(f1, r_in);  x2i, y2i = pt(f2, r_in)
    lg = 1 if (f2 - f1) > 55 else 0
    return (
        f'<path d="M{x1o:.2f},{y1o:.2f} A{r_out},{r_out} 0 {lg},1 {x2o:.2f},{y2o:.2f} '
        f'L{x2i:.2f},{y2i:.2f} A{r_in},{r_in} 0 {lg},0 {x1i:.2f},{y1i:.2f}Z" fill="{col}"/>'
    )

# Aguja
nx, ny       = pt(fi, 94)
nx_b, ny_b   = pt(fi, -14)   # pequeño remate opuesto (detrás del hub)
# Tick marks en 0, 30, 70, 100
def tick(f, r1=112, r2=120, cx=150, cy=148):
    x1, y1 = pt(f, r1); x2, y2 = pt(f, r2)
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="rgba(255,255,255,.25)" stroke-width="2"/>'

cx, cy = 150, 148
gauge_svg = f"""<svg viewBox="0 0 300 200" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:280px;display:block;margin:0 auto">
  <defs>
    <filter id="needle-glow">
      <feGaussianBlur stdDeviation="2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="hub-grad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{zcol}" stop-opacity="0.4"/>
      <stop offset="100%" stop-color="#0a0f1a"/>
    </radialGradient>
  </defs>
  <!-- Base track -->
  {arc_band(0, 100, 'rgba(255,255,255,.05)')}
  <!-- Color zones -->
  {arc_band(0, 30, 'rgba(239,68,68,.7)')}
  {arc_band(30, 70, 'rgba(234,179,8,.6)')}
  {arc_band(70, 100, 'rgba(34,197,94,.7)')}
  <!-- Highlight active zone -->
  {arc_band(max(0,fi-8), min(100,fi+8), 'rgba(255,255,255,.12)')}
  <!-- Tick marks -->
  {tick(0)} {tick(30)} {tick(50)} {tick(70)} {tick(100)}
  <!-- Zone labels -->
  <text x="22" y="172" fill="#ef4444" font-size="8" font-family="monospace" text-anchor="middle" opacity=".85">0</text>
  <text x="{pt(30,128)[0]:.0f}" y="{pt(30,128)[1]+4:.0f}" fill="#ef4444" font-size="8" font-family="monospace" text-anchor="middle" opacity=".7">30</text>
  <text x="{cx}" y="28" fill="#eab308" font-size="8" font-family="monospace" text-anchor="middle" opacity=".7">50</text>
  <text x="{pt(70,128)[0]:.0f}" y="{pt(70,128)[1]+4:.0f}" fill="#22c55e" font-size="8" font-family="monospace" text-anchor="middle" opacity=".7">70</text>
  <text x="278" y="172" fill="#22c55e" font-size="8" font-family="monospace" text-anchor="middle" opacity=".85">100</text>
  <!-- Needle shadow -->
  <line x1="{nx_b:.1f}" y1="{ny_b:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="rgba(0,0,0,.6)" stroke-width="5" stroke-linecap="round"/>
  <!-- Needle (con glow) -->
  <line x1="{nx_b:.1f}" y1="{ny_b:.1f}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{zcol}" stroke-width="3" stroke-linecap="round" filter="url(#needle-glow)"/>
  <!-- Hub -->
  <circle cx="{cx}" cy="{cy}" r="13" fill="url(#hub-grad)" stroke="{zcol}" stroke-width="1.5"/>
  <circle cx="{cx}" cy="{cy}" r="5"  fill="{zcol}"/>
  <!-- Flow Index number central -->
  <text x="{cx}" y="{cy+40}" fill="{zcol}" font-size="36" font-weight="900" font-family="'JetBrains Mono',monospace" text-anchor="middle" letter-spacing="-1">{fi:.0f}</text>
  <text x="{cx}" y="{cy+56}" fill="rgba(255,255,255,.25)" font-size="10" font-family="monospace" text-anchor="middle">/100</text>
</svg>"""

# ── 6. Widget HTML completo ────────────────────────────────────────────────
date_str = lbl(curr['date'])
recent_changes = changes[-5:]  # últimas 5 semanas para mini-tabla

rows_html = ''
for i, wk in enumerate(reversed(recent_changes)):
    is_live = (i == 0)
    w_date  = lbl(wk['date'])
    w_fi    = (ch_max - wk['change']) / (ch_max - ch_min) * 100 if ch_max != ch_min else 50.0
    w_fi    = round(max(0, min(100, w_fi)), 1)
    w_col   = '#22c55e' if w_fi >= 70 else '#eab308' if w_fi >= 30 else '#ef4444'
    w_sign  = '+' if wk['change'] >= 0 else ''
    w_act   = 'COMPRARON' if wk['change'] < 0 else 'VENDIERON'
    w_acol  = '#22c55e' if wk['change'] < 0 else '#ef4444'
    live_badge = '<span style="font-size:7px;background:rgba(0,242,255,.15);color:#00f2ff;padding:1px 5px;border-radius:8px;margin-left:4px;border:1px solid rgba(0,242,255,.25)">LIVE</span>' if is_live else ''
    rows_html += f'''<tr style="border-top:1px solid rgba(255,255,255,.04)">
      <td style="padding:5px 8px;font-family:monospace;font-size:9px;color:{'#94a3b8' if not is_live else '#00f2ff'};white-space:nowrap">{w_date}{live_badge}</td>
      <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:{w_acol};font-weight:{'700' if is_live else '400'}">{w_sign}{wk['change']:,}</td>
      <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:{w_acol};font-size:8px">{w_act}</td>
      <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:10px;color:{w_col};font-weight:{'700' if is_live else '400'}">{w_fi:.0f}</td>
    </tr>'''

widget = f'''{MARKER_S}
<section class="relative z-20 max-w-7xl mx-auto px-6 pb-2" id="comm-flow-gauge">
<div style="font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif">

  <!-- Header -->
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px;flex-wrap:wrap">
    <div style="font-size:11px;color:#00f2ff;font-weight:800;letter-spacing:.06em;text-transform:uppercase">
      Commercial Flow Index
    </div>
    <span style="font-size:8px;background:rgba(0,242,255,.08);border:1px solid rgba(0,242,255,.2);color:#00f2ff;padding:2px 9px;border-radius:10px;font-weight:700">COM SHORT Δ · CFTC</span>
    <span style="font-size:8px;color:#334155;font-family:monospace">{date_str} · 156w window</span>
  </div>

  <!-- Card principal -->
  <div style="background:rgba(0,0,0,.25);border:1px solid {zborder};border-radius:14px;padding:20px 22px;display:flex;flex-wrap:wrap;gap:24px;align-items:flex-start">

    <!-- Velocímetro -->
    <div style="flex:0 0 auto;text-align:center;min-width:200px;max-width:300px;width:100%">
      {gauge_svg}
      <div style="margin-top:6px;font-size:14px;font-weight:900;color:{zcol};letter-spacing:.03em">{emoji} {sesgo}</div>
      <div style="margin-top:3px;font-size:9px;color:rgba(255,255,255,.35);font-family:monospace">{zsub}</div>
    </div>

    <!-- Panel derecho -->
    <div style="flex:1;min-width:240px;display:flex;flex-direction:column;gap:14px">

      <!-- Cambio esta semana (grande) -->
      <div style="background:{zbg};border:1px solid {zborder};border-radius:10px;padding:14px 16px">
        <div style="font-size:8px;color:#94a3b8;text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px">Cambio COM Short esta semana</div>
        <div style="font-size:26px;font-weight:900;color:{action_color};font-family:'JetBrains Mono',monospace;letter-spacing:-1px">{change:+,}</div>
        <div style="font-size:10px;color:{action_color};margin-top:4px;font-weight:600">{action}</div>
        <div style="margin-top:8px;font-size:9px;color:rgba(255,255,255,.25);font-family:monospace">COM Short: {com_s:,} contratos totales</div>
      </div>

      <!-- Regla de lectura -->
      <div style="background:rgba(0,0,0,.15);border:1px solid rgba(255,255,255,.05);border-radius:10px;padding:12px 14px">
        <div style="font-size:8px;color:#334155;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">Cómo leer el indicador</div>
        <div style="display:flex;flex-direction:column;gap:5px">
          <div style="font-size:10px;color:rgba(255,255,255,.5);display:flex;align-items:center;gap:8px">
            <span style="width:10px;height:10px;background:#22c55e;border-radius:50%;flex-shrink:0;display:inline-block"></span>
            <span><strong style="color:#22c55e">&gt; 70</strong> · Comerciales comprando fuerte → sesgo <strong style="color:#22c55e">LARGO</strong></span>
          </div>
          <div style="font-size:10px;color:rgba(255,255,255,.5);display:flex;align-items:center;gap:8px">
            <span style="width:10px;height:10px;background:#eab308;border-radius:50%;flex-shrink:0;display:inline-block"></span>
            <span><strong style="color:#eab308">30–70</strong> · Neutral → operar solo con precio</span>
          </div>
          <div style="font-size:10px;color:rgba(255,255,255,.5);display:flex;align-items:center;gap:8px">
            <span style="width:10px;height:10px;background:#ef4444;border-radius:50%;flex-shrink:0;display:inline-block"></span>
            <span><strong style="color:#ef4444">&lt; 30</strong> · Comerciales vendiendo fuerte → sesgo <strong style="color:#ef4444">CORTO</strong></span>
          </div>
        </div>
      </div>

    </div>

    <!-- Tabla histórico 5 semanas -->
    <div style="width:100%;border-top:1px solid rgba(255,255,255,.05);padding-top:12px;margin-top:2px">
      <div style="font-size:8px;color:#334155;font-family:monospace;text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px">Últimas 5 semanas — COM Short Δ</div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:10px;min-width:320px">
          <thead>
            <tr style="background:rgba(0,0,0,.2)">
              <th style="padding:5px 8px;text-align:left;font-size:8px;color:#334155;font-weight:600;text-transform:uppercase">Semana</th>
              <th style="padding:5px 8px;text-align:right;font-size:8px;color:#334155;font-weight:600;text-transform:uppercase">Cambio Δ</th>
              <th style="padding:5px 8px;text-align:right;font-size:8px;color:#334155;font-weight:600;text-transform:uppercase">Acción</th>
              <th style="padding:5px 8px;text-align:right;font-size:8px;color:#334155;font-weight:600;text-transform:uppercase">Flow</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
      <div style="text-align:right;margin-top:6px;font-size:8px;color:#1e3a5f;font-family:monospace">
        Flow = (Max − Δ) / (Max − Min) × 100 · Rango 3 años · Auto-update viernes
      </div>
    </div>

  </div>
</div>
</section>
{MARKER_E}'''

# ── 7. Inyectar en index.html ──────────────────────────────────────────────
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Eliminar bloque anterior si existe
if MARKER_S in html and MARKER_E in html:
    pat = re.compile(re.escape(MARKER_S) + r'.*?' + re.escape(MARKER_E), re.DOTALL)
    html, n_del = pat.subn('', html, count=1)
    print(f'  Bloque anterior eliminado ({n_del})')

# Insertar después del ANCHOR
if ANCHOR in html:
    html = html.replace(ANCHOR, ANCHOR + '\n' + widget, 1)
    print(f'  Gauge inyectado después de {ANCHOR}')
else:
    # Fallback: insertar antes de </body>
    html = html.replace('</body>', widget + '\n</body>', 1)
    print('  Gauge inyectado antes de </body> (anchor no encontrado)')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'✅ Commercial Flow Index: {fi:.0f}/100 ({sesgo}) | Cambio: {change:+,} | {date_str}')
print(f'   {action}')
print(f'   index.html guardado ({len(html)//1024}KB)')
