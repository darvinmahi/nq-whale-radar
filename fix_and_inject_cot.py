"""
fix_and_inject_cot.py
1. Repara el HTML (el widget se inyectó en la línea 1 rompiendo <!DOCTYPE html>)
2. Elimina el bloque stale del principio
3. Reemplaza el widget correcto (dentro de cot-analysis) con diseño premium
4. Genera cot_historial.html
"""
import csv, re, requests, zipfile, io, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH = 'index.html'
HIST_PATH = 'cot_historial.html'
MARKER_S  = '<!-- COT_TABLE_START -->'
MARKER_E  = '<!-- COT_TABLE_END -->'

# ── 1. CSV ────────────────────────────────────────────────────────────────
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d    = r['Report_Date_as_MM_DD_YYYY'].strip()
            nc_l = int(r.get('Lev_Money_Positions_Long_All') or 0)
            nc_s = int(r.get('Lev_Money_Positions_Short_All') or 0)
            dl_l = int(r.get('Dealer_Positions_Long_All') or 0)
            dl_s = int(r.get('Dealer_Positions_Short_All') or 0)
            am_l = int(r.get('Asset_Mgr_Positions_Long_All') or 0)
            am_s = int(r.get('Asset_Mgr_Positions_Short_All') or 0)
            if nc_l or nc_s:
                rows.append({'date': d,
                             'nc_l': nc_l, 'nc_s': nc_s,
                             'dl_l': dl_l, 'dl_s': dl_s,
                             'am_l': am_l, 'am_s': am_s,
                             'ret_l': 0, 'ret_s': 0})
        except: pass

rows.sort(key=lambda x: x['date'])

# ── 2. Retail ─────────────────────────────────────────────────────────────
try:
    resp = requests.get(
        'https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=60)
    zf   = zipfile.ZipFile(io.BytesIO(resp.content))
    fobj = zf.open(zf.namelist()[0])
    for row in csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace')):
        if 'NASDAQ-100 Consolidated' not in row.get('Market_and_Exchange_Names', ''):
            continue
        d = row.get('Report_Date_as_YYYY-MM-DD', '').strip()
        try:
            for r2 in rows:
                if r2['date'] == d:
                    r2['ret_l'] = int(row.get('NonRept_Positions_Long_All') or 0)
                    r2['ret_s'] = int(row.get('NonRept_Positions_Short_All') or 0)
        except: pass
    print('✅ Retail OK')
except Exception as e:
    print(f'⚠️ Retail: {e}')

# ── 3. COT Index ─────────────────────────────────────────────────────────
for i, r in enumerate(rows):
    hist   = [x['nc_l'] - x['nc_s'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    net    = r['nc_l'] - r['nc_s']
    r['ci']     = round((net - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0
    r['nc_net'] = net
    r['dl_net'] = r['dl_l'] - r['dl_s']
    r['am_net'] = r['am_l'] - r['am_s']
    r['ret_net']= r['ret_l'] - r['ret_s']
    r['tot_l']  = r['nc_l'] + r['dl_l'] + r['am_l'] + r['ret_l']
    r['tot_s']  = r['nc_s'] + r['dl_s'] + r['am_s'] + r['ret_s']
    r['tot_net']= r['tot_l'] - r['tot_s']

# ── 4. Helpers ───────────────────────────────────────────────────────────
def K(n, d=1):
    """Formato compacto: 45.1k"""
    if abs(n) >= 1000: return f'{n/1000:.{d}f}k'
    return str(n)
def fmt(n): return f'{n:,}'
def clr(n): return '#00ff88' if n >= 0 else '#ff3355'
def ci_clr(ci):
    return '#ff1744' if ci<20 else '#ff5722' if ci<40 else '#ffd600' if ci<60 else '#69f0ae' if ci<80 else '#00e676'
def ci_sig(ci):
    return ('⬇ MUY BAJISTA' if ci<20 else '↘ BEARISH' if ci<40
            else '→ NEUTRAL' if ci<60 else '↗ BULLISH' if ci<80 else '⬆ MUY BULLISH')
def lbl(d):
    for fmt2 in ('%Y-%m-%d','%m/%d/%Y'):
        try: return datetime.strptime(d, fmt2).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d
def bar_html(val, maxv, color, height=6):
    pct = max(2, min(100, val / maxv * 100)) if maxv > 0 else 2
    return (f'<div style="height:{height}px;background:rgba(255,255,255,.04);'
            f'border-radius:3px;overflow:hidden;margin-top:3px">'
            f'<div style="width:{pct:.0f}%;height:100%;background:{color};'
            f'border-radius:3px;box-shadow:0 0 6px {color}44"></div></div>')

def chg(n, prev_n):
    if prev_n is None: return ''
    d = n - prev_n
    c = '#00ff88' if d > 0 else '#ff3355' if d < 0 else '#444'
    s = f'+{K(d,0)}' if d > 0 else K(d,0)
    return f'<span style="font-size:8px;color:{c};font-weight:700">{s}</span>'

# ── 5. Generar widget premium ─────────────────────────────────────────────
last4     = list(reversed(rows[-4:]))
last      = rows[-1]
updated   = datetime.now().strftime('%d/%m/%Y %H:%M')
total_wks = len(rows)
maxNC     = max(max(r['nc_l'], r['nc_s']) for r in last4)
maxCOM    = max(max(r['dl_l'], r['dl_s']) for r in last4)
maxAM     = max(max(r['am_l'], r['am_s']) for r in last4)
maxRET    = max(max(r['ret_l'], r['ret_s']) for r in last4) or 1

def category_card(label, icon, rows4, get_l, get_s, get_net, max_val, accent):
    rows_html = ''
    for i, r in enumerate(rows4):
        prev   = rows[rows.index(r)-1] if rows.index(r) > 0 else None
        is_live= i == 0
        l, s, n= get_l(r), get_s(r), get_net(r)
        lp     = max(2, l/max_val*100) if max_val else 2
        sp     = max(2, s/max_val*100) if max_val else 2
        chg_l  = chg(l, get_l(prev)) if prev else ''
        chg_s  = chg(s, get_s(prev)) if prev else ''
        live_t = f'<span style="font-size:7px;background:{accent}22;color:{accent};padding:1px 5px;border-radius:3px;margin-left:5px">LIVE</span>' if is_live else ''
        date_c = accent if is_live else '#333'
        rows_html += f'''
<div style="padding:8px 10px;border-radius:8px;margin-bottom:4px;
            background:{'rgba(0,0,0,.25)' if is_live else 'transparent'};
            border:{'1px solid '+accent+'22' if is_live else '1px solid transparent'}">
  <div style="font-size:8px;color:{date_c};font-family:monospace;margin-bottom:5px;letter-spacing:.04em">
    {lbl(r['date'])}{live_t}
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">
    <div>
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span style="font-size:7px;color:#00ff8866;font-weight:700">LONG</span>
        <span style="font-size:10px;color:#00ff88;font-family:monospace;font-weight:900">{K(l)}</span>
        {chg_l}
      </div>
      <div style="height:5px;background:rgba(255,255,255,.04);border-radius:3px;overflow:hidden;margin-top:2px">
        <div style="width:{lp:.0f}%;height:100%;background:#00ff88;box-shadow:0 0 4px #00ff8866;border-radius:3px"></div>
      </div>
    </div>
    <div>
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span style="font-size:7px;color:#ff335566;font-weight:700">SHORT</span>
        <span style="font-size:10px;color:#ff3355;font-family:monospace;font-weight:900">{K(s)}</span>
        {chg_s}
      </div>
      <div style="height:5px;background:rgba(255,255,255,.04);border-radius:3px;overflow:hidden;margin-top:2px">
        <div style="width:{sp:.0f}%;height:100%;background:#ff3355;box-shadow:0 0 4px #ff335566;border-radius:3px"></div>
      </div>
    </div>
  </div>
  <div style="margin-top:5px;display:flex;justify-content:flex-end;align-items:center;gap:6px">
    <span style="font-size:7px;color:#333;text-transform:uppercase;letter-spacing:.05em">Net</span>
    <span style="font-size:11px;font-weight:900;font-family:monospace;color:{clr(n)}">{n:+,}</span>
  </div>
</div>'''
    return f'''
<div style="background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.05);
            border-radius:12px;padding:12px 14px;flex:1;min-width:200px">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:10px;
              padding-bottom:8px;border-bottom:1px solid rgba(255,255,255,.05)">
    <span style="font-size:14px">{icon}</span>
    <div>
      <div style="font-size:10px;font-weight:700;color:#e2e8f0;text-transform:uppercase;letter-spacing:.06em">{label}</div>
    </div>
  </div>
  {rows_html}
</div>'''

# Cuatro tarjetas de categoría
specs_card = category_card('Non-Commercial','📈',last4,
    lambda r:r['nc_l'], lambda r:r['nc_s'], lambda r:r['nc_net'], maxNC, '#00f2ff')
banks_card = category_card('Commercial','🏦',last4,
    lambda r:r['dl_l'], lambda r:r['dl_s'], lambda r:r['dl_net'], maxCOM, '#60a5fa')
inst_card  = category_card('Institucional','💼',last4,
    lambda r:r['am_l'], lambda r:r['am_s'], lambda r:r['am_net'], maxAM, '#a78bfa')
ret_card   = category_card('Retail','👾',last4,
    lambda r:r['ret_l'], lambda r:r['ret_s'], lambda r:r['ret_net'], maxRET, '#fb923c')

# Tabla compacta de totales
ci_last = last['ci']
table_rows = ''
for i, r in enumerate(last4):
    prev = rows[rows.index(r)-1] if rows.index(r) > 0 else None
    dot = f'<span style="color:#00f2ff;margin-right:4px">●</span>' if i == 0 else '''<span style="margin-right:4px;color:#222">○</span>'''
    bg  = 'background:rgba(0,242,255,.03)' if i == 0 else ''
    nc_n= r['nc_net']
    dl_n= r['dl_net']
    am_n= r['am_net']
    rt_n= r['ret_net']
    tot = r['tot_net']
    ci  = r['ci']
    table_rows += (
        f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);{bg}">'
        f'<td style="padding:7px 10px;font-size:9px;color:#94a3b8;font-family:monospace;white-space:nowrap">{dot}{lbl(r["date"])}</td>'
        f'<td style="padding:7px 8px;font-family:monospace;font-size:10px;font-weight:700;color:{clr(nc_n)};text-align:right">{nc_n:+,}</td>'
        f'<td style="padding:7px 8px;font-family:monospace;font-size:10px;color:{clr(dl_n)};text-align:right">{dl_n:+,}</td>'
        f'<td style="padding:7px 8px;font-family:monospace;font-size:10px;color:{clr(am_n)};text-align:right">{am_n:+,}</td>'
        f'<td style="padding:7px 8px;font-family:monospace;font-size:10px;color:{clr(rt_n)};text-align:right">{rt_n:+,}</td>'
        f'<td style="padding:7px 10px;font-family:monospace;font-size:11px;font-weight:900;color:{clr(tot)};text-align:right;border-left:1px solid rgba(255,255,255,.06)">{tot:+,}</td>'
        f'<td style="padding:7px 10px;font-family:monospace;font-size:10px;font-weight:700;color:{ci_clr(ci)};text-align:right">{ci:.1f}%</td>'
        f'</tr>'
    )

widget = f"""{MARKER_S}
<style>
.cot-cards-wrap {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:16px }}
@media(max-width:900px) {{ .cot-cards-wrap {{ flex-direction:column }} }}
</style>

<div style="margin-top:28px;padding-top:20px;border-top:1px solid rgba(255,255,255,.06)">

  <!-- Header -->
  <div style="display:flex;align-items:center;justify-content:space-between;
              margin-bottom:18px;flex-wrap:wrap;gap:10px">
    <div>
      <div style="font-size:9px;font-family:monospace;color:#1e3a5f;
                  text-transform:uppercase;letter-spacing:.1em;margin-bottom:3px">
        CFTC · TFF · NASDAQ-100 CONSOLIDATED · {total_wks} SEMANAS
      </div>
      <div style="display:flex;align-items:center;gap:12px">
        <span style="font-size:11px;font-weight:900;color:{ci_clr(ci_last)}">
          COT Index: {ci_last:.1f}% — {ci_sig(ci_last)}
        </span>
        <span style="font-size:9px;color:#1e3a5f;font-family:monospace">
          {lbl(last['date'])} · {updated}
        </span>
      </div>
    </div>
    <a href="cot_historial.html" target="_blank"
       style="display:inline-flex;align-items:center;gap:6px;
              background:rgba(0,242,255,.05);border:1px solid rgba(0,242,255,.15);
              color:#00f2ff;padding:7px 16px;border-radius:20px;text-decoration:none;
              font-size:10px;font-weight:700;font-family:monospace;letter-spacing:.04em;
              transition:all .2s">
      HISTORIAL {total_wks}W ↗
    </a>
  </div>

  <!-- 4 tarjetas con barras -->
  <div class="cot-cards-wrap">
    {specs_card}
    {banks_card}
    {inst_card}
    {ret_card}
  </div>

  <!-- Tabla de totales -->
  <div style="background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.05);
              border-radius:12px;overflow:hidden">
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="background:rgba(255,255,255,.03)">
          <th style="padding:8px 10px;font-size:8px;color:#1e3a5f;text-align:left;
                     text-transform:uppercase;letter-spacing:.08em;font-weight:700">Semana</th>
          <th style="padding:8px 8px;font-size:8px;color:#00f2ff;text-align:right;
                     text-transform:uppercase;letter-spacing:.06em;font-weight:700">NC Net</th>
          <th style="padding:8px 8px;font-size:8px;color:#60a5fa;text-align:right;
                     text-transform:uppercase;letter-spacing:.06em;font-weight:700">COM Net</th>
          <th style="padding:8px 8px;font-size:8px;color:#a78bfa;text-align:right;
                     text-transform:uppercase;letter-spacing:.06em;font-weight:700">AM Net</th>
          <th style="padding:8px 8px;font-size:8px;color:#fb923c;text-align:right;
                     text-transform:uppercase;letter-spacing:.06em;font-weight:700">Retail</th>
          <th style="padding:8px 10px;font-size:8px;color:#e2e8f0;text-align:right;
                     text-transform:uppercase;letter-spacing:.06em;font-weight:700;
                     border-left:1px solid rgba(255,255,255,.06)">Total Net</th>
          <th style="padding:8px 10px;font-size:8px;color:#ffd600;text-align:right;
                     text-transform:uppercase;letter-spacing:.06em;font-weight:700">COT Index</th>
        </tr>
      </thead>
      <tbody>
        {table_rows}
      </tbody>
    </table>
  </div>

  <div style="text-align:right;margin-top:8px;font-size:8px;color:#111;font-family:monospace">
    CFTC · Traders in Financial Futures · Auto-update cada viernes 22:00 UTC
  </div>
</div>
{MARKER_E}"""

# ── 6. Reparar + inyectar index.html ────────────────────────────────────
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# ─ Eliminamos el primer bloque stale (línea 1) ─
# El html empieza con <!DOCTYPE\n<!-- COT_TABLE_START -->...<!-- COT_TABLE_END --> html>
# Hay que restaurarlo a <!DOCTYPE html>
first_start = html.find(MARKER_S)
first_end   = html.find(MARKER_E)
second_start= html.find(MARKER_S, first_end + len(MARKER_E))
second_end  = html.find(MARKER_E, second_start + len(MARKER_S))

print(f'1st block: chars {first_start}–{first_end}')
print(f'2nd block: chars {second_start}–{second_end}')

# El HTML está así: "<!DOCTYPE\n" + primer bloque + " html>\n<!-- saved from..."
# Necesitamos: "<!DOCTYPE html>\n..." + contenido sin primer bloque + nuevo widget en 2nd

# 1. Quitar primer bloque y reparar DOCTYPE
doctype_prefix = html[:first_start]          # "<!DOCTYPE\n"
after_first    = html[first_end + len(MARKER_E):]  # " html>\n<!-- saved from ..."

# Reparar: "<!DOCTYPE\n" → "<!DOCTYPE html>" y " html>\n" → "\n"
doctype_prefix = doctype_prefix.rstrip('\n\r') + ' html>'
after_first    = re.sub(r'^\s*html\>', '', after_first, count=1).lstrip()

html_fixed = doctype_prefix + '\n' + after_first
print(f'HTML reparado. Empieza con: {repr(html_fixed[:60])}')

# 2. Reemplazar el segundo bloque (ahora el único) con el nuevo widget
if MARKER_S in html_fixed and MARKER_E in html_fixed:
    pat      = re.compile(re.escape(MARKER_S) + '.*?' + re.escape(MARKER_E), re.DOTALL)
    html_out = pat.sub(widget, html_fixed, count=1)
    print('✅ Widget inyectado en posición correcta')
else:
    # Fallback: insertar dentro de cot-analysis
    cot_pos  = html_fixed.find('id="cot-analysis"')
    sec_end  = html_fixed.find('</section>', cot_pos)
    html_out = html_fixed[:sec_end] + '\n' + widget + '\n' + html_fixed[sec_end:]
    print('✅ Widget insertado en cot-analysis (fallback)')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html_out)
print(f'✅ index.html guardado ({len(html_out)//1024}KB)')

# ── 7. Historial premium ─────────────────────────────────────────────────
all_rows_html = ''
for i, r in enumerate(reversed(rows)):
    idx    = rows.index(r)
    prev   = rows[idx-1] if idx > 0 else None
    is_live= i == 0
    ci     = r['ci']
    nc_net = r['nc_net']
    dl_net = r['dl_net']
    am_net = r['am_net']
    rt_net = r['ret_net']
    tot    = r['tot_net']

    if prev:
        dnc = r['nc_net']  - prev['nc_net']
        dco = r['dl_net']  - prev['dl_net']
        dam = r['am_net']  - prev['am_net']
        drt = r['ret_net'] - prev['ret_net']
        dtot= r['tot_net'] - prev['tot_net']
        def dc_badge(n):
            c = '#00ff88' if n>0 else '#ff3355' if n<0 else '#333'
            s = f'+{K(n,0)}' if n>0 else K(n,0)
            return f'<span style="font-size:9px;color:{c}">{s}</span>'
        chg_cells = f'<td style="text-align:right;padding:6px 8px">{dc_badge(dnc)}</td><td style="text-align:right;padding:6px 8px">{dc_badge(dco)}</td><td style="text-align:right;padding:6px 8px">{dc_badge(dam)}</td><td style="text-align:right;padding:6px 8px">{dc_badge(drt)}</td><td style="text-align:right;padding:6px 10px;border-left:1px solid rgba(255,255,255,.05)">{dc_badge(dtot)}</td>'
    else:
        chg_cells = '<td></td><td></td><td></td><td></td><td></td>'

    dot = '●' if is_live else ''
    bg  = 'background:rgba(0,242,255,.03)' if is_live else ''
    all_rows_html += (
        f'<tr style="border-bottom:1px solid rgba(255,255,255,.04);{bg}" data-date="{lbl(r["date"]).lower()}">'
        f'<td style="padding:7px 10px;font-size:9px;color:{"#00f2ff" if is_live else "#94a3b8"};font-family:monospace;white-space:nowrap">{dot}{lbl(r["date"])}</td>'
        f'<td style="padding:6px 8px;font-family:monospace;font-size:10px;font-weight:700;color:{clr(nc_net)};text-align:right">{nc_net:+,}</td>'
        f'<td style="padding:6px 8px;font-family:monospace;font-size:10px;color:{clr(dl_net)};text-align:right">{dl_net:+,}</td>'
        f'<td style="padding:6px 8px;font-family:monospace;font-size:10px;color:{clr(am_net)};text-align:right">{am_net:+,}</td>'
        f'<td style="padding:6px 8px;font-family:monospace;font-size:10px;color:{clr(rt_net)};text-align:right">{rt_net:+,}</td>'
        f'<td style="padding:6px 10px;font-family:monospace;font-size:11px;font-weight:900;color:{clr(tot)};text-align:right;border-left:1px solid rgba(255,255,255,.06)">{tot:+,}</td>'
        f'<td style="padding:6px 10px;font-family:monospace;font-size:10px;font-weight:700;color:{ci_clr(ci)};text-align:right">{ci:.1f}%</td>'
        f'{chg_cells}'
        f'</tr>'
    )

hist_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>COT Historial · NQ Whale Radar · {total_wks} semanas</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#080d18;color:#94a3b8;font-family:'Inter',system-ui;padding:24px 20px}}
    h1{{font-size:20px;font-weight:900;color:#e2e8f0;margin-bottom:4px}}
    .meta{{font-size:10px;color:#1e3a5f;font-family:monospace;margin-bottom:20px}}
    .toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:16px;flex-wrap:wrap}}
    input#srch{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
                color:#e2e8f0;padding:7px 14px;border-radius:16px;font-family:monospace;
                font-size:11px;width:200px;outline:none}}
    input#srch:focus{{border-color:rgba(0,242,255,.3)}}
    .back{{display:inline-flex;align-items:center;gap:5px;
           background:rgba(0,242,255,.05);border:1px solid rgba(0,242,255,.15);
           color:#00f2ff;padding:7px 14px;border-radius:16px;text-decoration:none;
           font-size:10px;font-weight:700;font-family:monospace}}
    table{{width:100%;border-collapse:collapse;font-size:10px}}
    thead th{{padding:8px 10px;text-align:right;background:rgba(255,255,255,.03);
              font-size:8px;font-weight:700;text-transform:uppercase;
              letter-spacing:.07em;border-bottom:1px solid rgba(255,255,255,.07)}}
    thead th:first-child{{text-align:left}}
    tbody tr:hover{{background:rgba(255,255,255,.015)}}
    .tbl-wrap{{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.06);
               border-radius:12px;overflow:hidden;overflow-x:auto}}
  </style>
</head>
<body>
  <h1>📊 COT Historial — NASDAQ-100</h1>
  <div class="meta">CFTC · Traders in Financial Futures · {total_wks} semanas · {updated} UTC · Auto-update viernes</div>
  <div class="toolbar">
    <a href="index.html#cot-analysis" class="back">← Dashboard</a>
    <input id="srch" type="text" placeholder="Buscar fecha... (Mar 2026)">
    <span style="font-size:9px;color:#1e3a5f;font-family:monospace">{total_wks} registros</span>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th style="text-align:left">Semana</th>
        <th style="color:#00f2ff">NC Net</th>
        <th style="color:#60a5fa">COM Net</th>
        <th style="color:#a78bfa">AM Net</th>
        <th style="color:#fb923c">Retail</th>
        <th style="color:#e2e8f0;border-left:1px solid rgba(255,255,255,.06)">Total Net</th>
        <th style="color:#ffd600">COT%</th>
        <th style="color:#444">ΔNC</th>
        <th style="color:#444">ΔCOM</th>
        <th style="color:#444">ΔAM</th>
        <th style="color:#444">ΔRet</th>
        <th style="color:#444;border-left:1px solid rgba(255,255,255,.06)">ΔTotal</th>
      </tr></thead>
      <tbody id="tbody">{all_rows_html}</tbody>
    </table>
  </div>
  <script>
  document.getElementById('srch').addEventListener('input', function() {{
    var q = this.value.toLowerCase();
    document.querySelectorAll('#tbody tr').forEach(function(tr) {{
      tr.style.display = !q || (tr.dataset.date||'').includes(q) ? '' : 'none';
    }});
  }});
  </script>
</body>
</html>"""

with open(HIST_PATH, 'w', encoding='utf-8') as f:
    f.write(hist_page)

print(f'✅ {HIST_PATH} ({len(hist_page)//1024}KB, {total_wks} semanas)')
print(f'\n📊 {lbl(last["date"])} | NC:{last["nc_net"]:+,} | COM:{last["dl_net"]:+,} | AM:{last["am_net"]:+,} | COT:{last["ci"]:.1f}%')
