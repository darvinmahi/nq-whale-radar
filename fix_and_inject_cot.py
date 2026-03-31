"""
fix_and_inject_cot.py — v4
Formato CFTC Clásico: Non-Commercial | Commercial | Total | Non-Reportable
Diseño: tabla Bloomberg dark luxury compacta (una sola tabla, no 4 bloques)
NC = Leveraged Funds + Asset Mgr  (igual que el reporte legacy CFTC)
COM= Dealer/Intermediary
"""
import csv, re, requests, zipfile, io, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH = 'index.html'
HIST_PATH = 'cot_historial.html'
MARKER_S  = '<!-- COT_TABLE_START -->'
MARKER_E  = '<!-- COT_TABLE_END -->'

# ── 1. Cargar CSV (TFF disaggregated) ────────────────────────────────────────
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d    = r['Report_Date_as_MM_DD_YYYY'].strip()
            lm_l = int(r.get('Lev_Money_Positions_Long_All')  or 0)
            lm_s = int(r.get('Lev_Money_Positions_Short_All') or 0)
            dl_l = int(r.get('Dealer_Positions_Long_All')     or 0)
            dl_s = int(r.get('Dealer_Positions_Short_All')    or 0)
            am_l = int(r.get('Asset_Mgr_Positions_Long_All')  or 0)
            am_s = int(r.get('Asset_Mgr_Positions_Short_All') or 0)
            if lm_l or lm_s:
                rows.append({'date': d,
                             'lm_l': lm_l, 'lm_s': lm_s,
                             'dl_l': dl_l, 'dl_s': dl_s,
                             'am_l': am_l, 'am_s': am_s,
                             'ret_l': 0, 'ret_s': 0})
        except:
            pass

rows.sort(key=lambda x: x['date'])

# ── 2. Añadir Non-Reportable desde CFTC ──────────────────────────────────────
try:
    resp = requests.get(
        'https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=60)
    zf   = zipfile.ZipFile(io.BytesIO(resp.content))
    fobj = zf.open(zf.namelist()[0])
    for row in csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace')):
        if 'NASDAQ-100 Consolidated' not in row.get('Market_and_Exchange_Names', ''):
            continue
        d = row.get('Report_Date_as_YYYY-MM-DD', '').strip()
        for r2 in rows:
            if r2['date'] == d:
                r2['ret_l'] = int(row.get('NonRept_Positions_Long_All')  or 0)
                r2['ret_s'] = int(row.get('NonRept_Positions_Short_All') or 0)
    print('OK Retail (NonRept)')
except Exception as e:
    print(f'WARN Retail: {e}')

# ── 3. Calcular columnas formato CFTC clásico ─────────────────────────────────
# Non-Commercial = Lev_Money + Asset_Mgr  (como en el legacy COT)
# Commercial     = Dealer/Intermediary
for i, r in enumerate(rows):
    r['NC_L']  = r['lm_l'] + r['am_l']
    r['NC_S']  = r['lm_s'] + r['am_s']
    r['COM_L'] = r['dl_l']
    r['COM_S'] = r['dl_s']
    r['RET_L'] = r['ret_l']
    r['RET_S'] = r['ret_s']
    r['TOT_L'] = r['NC_L'] + r['COM_L'] + r['RET_L']
    r['TOT_S'] = r['NC_S'] + r['COM_S'] + r['RET_S']
    r['NC_N']  = r['NC_L']  - r['NC_S']
    r['COM_N'] = r['COM_L'] - r['COM_S']
    r['RET_N'] = r['RET_L'] - r['RET_S']
    r['TOT_N'] = r['TOT_L'] - r['TOT_S']
    # COT Index (trailing 3 años sobre NC Net)
    hist = [x['NC_L']-x['NC_S'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = round((r['NC_N']-mn)/(mx-mn)*100, 1) if mx > mn else 50.0

# ── 4. Helpers ────────────────────────────────────────────────────────────────
def fmt(n):
    return f'{n:,}'

def sgn(n):
    return f'+{n:,}' if n >= 0 else f'{n:,}'

def clr(n):
    return '#34d399' if n > 0 else '#f87171' if n < 0 else '#64748b'

def ci_clr(ci):
    if ci < 20: return '#f87171'
    if ci < 40: return '#fb923c'
    if ci < 60: return '#fbbf24'
    if ci < 80: return '#34d399'
    return '#22c55e'

def ci_sig(ci):
    if ci < 20: return 'BAJISTA EXTREMO'
    if ci < 40: return 'BEARISH'
    if ci < 60: return 'NEUTRAL'
    if ci < 80: return 'BULLISH'
    return 'BULLISH EXTREMO'

def lbl(d):
    for fmt2 in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(d, fmt2).strftime('%d %b %Y').lstrip('0')
        except:
            pass
    return d

def dlbl(n):
    if n is None:
        return '<span style="color:#1e3a5f">—</span>'
    c = clr(n)
    return f'<span style="color:{c};font-weight:700">{sgn(n)}</span>'

def delta(r, prev, key):
    if prev is None:
        return None
    return r[key] - prev[key]

# ── 5. Preparar datos ─────────────────────────────────────────────────────────
last4     = list(reversed(rows[-4:]))
last      = rows[-1]
updated   = datetime.now().strftime('%d/%m/%Y %H:%M')
total_wks = len(rows)

r0   = last4[0]
idx0 = rows.index(r0)
prev = rows[idx0 - 1] if idx0 > 0 else None

NC_L,  NC_S,  NC_N  = r0['NC_L'],  r0['NC_S'],  r0['NC_N']
COM_L, COM_S, COM_N = r0['COM_L'], r0['COM_S'], r0['COM_N']
RET_L, RET_S, RET_N = r0['RET_L'], r0['RET_S'], r0['RET_N']
TOT_L, TOT_S, TOT_N = r0['TOT_L'], r0['TOT_S'], r0['TOT_N']
ci0 = r0['ci']

dNC_L  = dlbl(delta(r0, prev, 'NC_L'));  dNC_S  = dlbl(delta(r0, prev, 'NC_S'));  dNC_N  = dlbl(delta(r0, prev, 'NC_N'))
dCOM_L = dlbl(delta(r0, prev, 'COM_L')); dCOM_S = dlbl(delta(r0, prev, 'COM_S')); dCOM_N = dlbl(delta(r0, prev, 'COM_N'))
dRET_L = dlbl(delta(r0, prev, 'RET_L')); dRET_S = dlbl(delta(r0, prev, 'RET_S')); dRET_N = dlbl(delta(r0, prev, 'RET_N'))
dTOT_L = dlbl(delta(r0, prev, 'TOT_L')); dTOT_S = dlbl(delta(r0, prev, 'TOT_S')); dTOT_N = dlbl(delta(r0, prev, 'TOT_N'))

# ── 6. Filas históricas compactas ─────────────────────────────────────────────
hist_rows_html = ''
for rx in last4[1:]:
    hist_rows_html += f"""
  <tr style="background:rgba(255,255,255,.01);border-top:1px solid rgba(255,255,255,.04)">
    <td style="padding:5px 10px;font-size:9px;color:#64748b;font-family:monospace;white-space:nowrap">{lbl(rx['date'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['NC_L'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['NC_S'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:{clr(rx['NC_N'])};font-weight:700;border-right:1px solid rgba(255,255,255,.05)">{sgn(rx['NC_N'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['COM_L'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['COM_S'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:{clr(rx['COM_N'])};font-weight:700;border-right:1px solid rgba(255,255,255,.05)">{sgn(rx['COM_N'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['TOT_L'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['TOT_S'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:{clr(rx['TOT_N'])};font-weight:700;border-right:1px solid rgba(255,255,255,.06)">{sgn(rx['TOT_N'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['RET_L'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:#6b7280">{fmt(rx['RET_S'])}</td>
    <td style="padding:5px 8px;text-align:right;font-family:monospace;font-size:9px;color:{clr(rx['RET_N'])};font-weight:700">{sgn(rx['RET_N'])}</td>
  </tr>"""

# ── 7. Widget HTML ────────────────────────────────────────────────────────────
TH = 'padding:6px 8px;text-align:right;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid rgba(255,255,255,.08)'
TD_G = f'padding:8px 8px;text-align:right;font-family:monospace;font-size:12px;font-weight:800;color:#4ade80'
TD_R = f'padding:8px 8px;text-align:right;font-family:monospace;font-size:12px;font-weight:800;color:#f87171'

widget = f"""{MARKER_S}
<div style="font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif">

  <!-- Header -->
  <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px">
    <div>
      <div style="font-size:11px;color:#00f2ff;font-weight:800;letter-spacing:.05em;text-transform:uppercase">
        NASDAQ-100 &nbsp;·&nbsp; COT Report
        <span style="font-size:8px;background:rgba(0,242,255,.08);border:1px solid rgba(0,242,255,.2);color:#00f2ff;padding:2px 8px;border-radius:10px;margin-left:8px;font-weight:700">LIVE · {lbl(r0['date'])}</span>
      </div>
      <div style="font-size:8px;color:#334155;margin-top:3px;font-family:monospace">
        CFTC · fut_fin_txt · Traders in Financial Futures · NC = Lev.Funds + Asset Mgr · {total_wks} semanas · {updated}
      </div>
      <div style="margin-top:7px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <span style="font-size:13px;font-weight:900;color:{ci_clr(ci0)}">COT Index {ci0:.1f}%</span>
        <span style="font-size:10px;font-weight:700;color:{ci_clr(ci0)};background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);padding:3px 10px;border-radius:20px">{ci_sig(ci0)}</span>
      </div>
    </div>
    <a href="cot_historial.html" target="_blank"
       style="display:inline-flex;align-items:center;gap:6px;background:rgba(0,242,255,.07);
              border:1px solid rgba(0,242,255,.25);color:#00f2ff;padding:9px 18px;
              border-radius:20px;text-decoration:none;font-size:10px;font-weight:800;
              font-family:monospace;letter-spacing:.04em;white-space:nowrap;flex-shrink:0">
      📂 HISTORIAL {total_wks}W ↗
    </a>
  </div>

  <!-- Tabla COT -->
  <div style="background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.07);border-radius:12px;overflow:hidden;overflow-x:auto">
    <table style="width:100%;border-collapse:collapse;font-size:11px;min-width:720px">
      <thead>
        <!-- Grupos de columnas -->
        <tr style="background:rgba(255,255,255,.02)">
          <th style="padding:8px 12px;text-align:left;font-size:8px;color:#334155;font-weight:400;min-width:90px"></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#38bdf8;letter-spacing:.07em;border-left:1px solid rgba(255,255,255,.05);border-right:1px solid rgba(255,255,255,.06)">NON-COMMERCIAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Lev.Funds + Asset Mgr</span></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#818cf8;letter-spacing:.07em;border-right:1px solid rgba(255,255,255,.06)">COMMERCIAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Dealer/Intermediary</span></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#e2e8f0;letter-spacing:.07em;border-right:1px solid rgba(255,255,255,.08)">TOTAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">todas categorias</span></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#94a3b8;letter-spacing:.07em">NON-REPORTABLE<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Retail</span></th>
        </tr>
        <!-- Long / Short / Net -->
        <tr style="background:rgba(0,0,0,.25)">
          <th style="padding:5px 12px;text-align:left;font-size:8px;color:#1e3a5f;font-weight:600;border-top:1px solid rgba(255,255,255,.04)">SEMANA</th>
          <th style="{TH};color:#4ade80;border-left:1px solid rgba(255,255,255,.05)">LONG</th>
          <th style="{TH};color:#f87171">SHORT</th>
          <th style="{TH};color:#94a3b8;border-right:1px solid rgba(255,255,255,.06)">NET</th>
          <th style="{TH};color:#4ade80">LONG</th>
          <th style="{TH};color:#f87171">SHORT</th>
          <th style="{TH};color:#94a3b8;border-right:1px solid rgba(255,255,255,.06)">NET</th>
          <th style="{TH};color:#4ade80">LONG</th>
          <th style="{TH};color:#f87171">SHORT</th>
          <th style="{TH};color:#94a3b8;border-right:1px solid rgba(255,255,255,.08)">NET</th>
          <th style="{TH};color:#4ade80">LONG</th>
          <th style="{TH};color:#f87171">SHORT</th>
          <th style="{TH};color:#94a3b8">NET</th>
        </tr>
      </thead>
      <tbody>
        <!-- Semana LIVE -->
        <tr style="background:rgba(0,242,255,.04)">
          <td style="padding:10px 12px;font-size:9px;font-weight:800;color:#00f2ff;font-family:monospace;white-space:nowrap;border-top:1px solid rgba(0,242,255,.1)">
            {lbl(r0['date'])}
            <span style="display:block;font-size:7px;color:#00f2ff;opacity:.7;margin-top:2px">◉ LIVE</span>
          </td>
          <td style="{TD_G};border-left:1px solid rgba(255,255,255,.05)">{fmt(NC_L)}</td>
          <td style="{TD_R}">{fmt(NC_S)}</td>
          <td style="padding:8px 8px;text-align:right;font-family:monospace;font-size:13px;font-weight:900;color:{clr(NC_N)};border-right:1px solid rgba(255,255,255,.06)">{sgn(NC_N)}</td>
          <td style="{TD_G}">{fmt(COM_L)}</td>
          <td style="{TD_R}">{fmt(COM_S)}</td>
          <td style="padding:8px 8px;text-align:right;font-family:monospace;font-size:13px;font-weight:900;color:{clr(COM_N)};border-right:1px solid rgba(255,255,255,.06)">{sgn(COM_N)}</td>
          <td style="{TD_G}">{fmt(TOT_L)}</td>
          <td style="{TD_R}">{fmt(TOT_S)}</td>
          <td style="padding:8px 8px;text-align:right;font-family:monospace;font-size:15px;font-weight:900;color:{clr(TOT_N)};border-right:1px solid rgba(255,255,255,.08)">{sgn(TOT_N)}</td>
          <td style="{TD_G}">{fmt(RET_L)}</td>
          <td style="{TD_R}">{fmt(RET_S)}</td>
          <td style="padding:8px 8px;text-align:right;font-family:monospace;font-size:13px;font-weight:900;color:{clr(RET_N)}">{sgn(RET_N)}</td>
        </tr>
        <!-- Fila cambios -->
        <tr style="background:rgba(0,0,0,.2);border-bottom:2px solid rgba(255,255,255,.06)">
          <td style="padding:5px 12px;font-size:7px;color:#334155;font-weight:700;letter-spacing:.1em;text-transform:uppercase">CAMBIO Δ</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px;border-left:1px solid rgba(255,255,255,.04)">{dNC_L}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dNC_S}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px;border-right:1px solid rgba(255,255,255,.06)">{dNC_N}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dCOM_L}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dCOM_S}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px;border-right:1px solid rgba(255,255,255,.06)">{dCOM_N}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dTOT_L}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dTOT_S}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px;border-right:1px solid rgba(255,255,255,.08)">{dTOT_N}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dRET_L}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dRET_S}</td>
          <td style="padding:5px 8px;text-align:right;font-size:10px">{dRET_N}</td>
        </tr>
        <!-- Semanas anteriores -->
        {hist_rows_html}
      </tbody>
    </table>
  </div>

  <div style="text-align:right;margin-top:6px;font-size:8px;color:#1e3a5f;font-family:monospace">
    CFTC fut_fin_txt (Traders in Financial Futures, Disaggregated) · NC = Lev.Funds + Asset Mgr · Auto-update viernes
  </div>
</div>
{MARKER_E}"""

# ── 8. Reparar e inyectar index.html ─────────────────────────────────────────
import re as _re

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Paso A: Reparar DOCTYPE corrompido
if html.startswith('<!DOCTYPE\n') or (html.startswith('<!DOCTYPE') and 'html>' not in html[:30]):
    s0 = html.find(MARKER_S)
    e0 = html.find(MARKER_E, s0)
    if e0 > 0:
        html = '<!DOCTYPE html>\n' + html[e0 + len(MARKER_E):]
        html = _re.sub(r'^\s*html>', '', html).lstrip('\n')
        print('DOCTYPE reparado')

# Paso B: Eliminar bloques COT existentes
pat_full   = _re.compile(_re.escape(MARKER_S) + '.*?' + _re.escape(MARKER_E), _re.DOTALL)
pat_orphan = _re.compile(_re.escape(MARKER_S))
before = len(_re.findall(_re.escape(MARKER_S), html))
html = pat_full.sub('', html)
html = pat_orphan.sub('', html)
after = len(_re.findall(_re.escape(MARKER_S), html))
print(f'Marcadores eliminados: {before} -> {after}')

# Paso C: REEMPLAZAR todo el contenido del section#cot-analysis
cot_pos = html.find('id="cot-analysis"')
if cot_pos > 0:
    tag_end = html.find('>', cot_pos) + 1
    sec_end = html.find('</section>', cot_pos)
    html    = html[:tag_end] + '\n' + widget + '\n' + html[sec_end:]
    print('Widget REEMPLAZA cot-analysis')
else:
    html = html.replace('</body>', '\n' + widget + '\n</body>', 1)
    print('Widget inyectado antes de </body>')

# Verificacion
starts = len(_re.findall(_re.escape(MARKER_S), html))
ends   = len(_re.findall(_re.escape(MARKER_E), html))
print(f'Verificacion: {starts} START, {ends} END')
assert starts == 1 and ends == 1, 'ERROR: marcadores duplicados!'

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'index.html guardado ({len(html)//1024}KB)')

# ── 9. Generar cot_historial.html ─────────────────────────────────────────────
all_rows_html = ''
for i in range(len(rows)-1, -1, -1):
    rx   = rows[i]
    prev = rows[i-1] if i > 0 else None
    bg = 'rgba(0,242,255,.03)' if i == len(rows)-1 else ''
    live = ' style="color:#00f2ff;font-weight:800"' if i == len(rows)-1 else ''

    def dh(r, p, k):
        if p is None: return '—'
        n = r[k]-p[k]
        c = '#34d399' if n > 0 else '#f87171' if n < 0 else '#64748b'
        return f'<span style="color:{c}">{sgn(n)}</span>'

    all_rows_html += f"""
  <tr style="background:{bg}" data-date="{lbl(rx['date']).lower()}">
    <td{live}>{lbl(rx['date'])}</td>
    <td>{fmt(rx['NC_L'])}</td><td>{fmt(rx['NC_S'])}</td><td style="color:{clr(rx['NC_N'])};font-weight:700">{sgn(rx['NC_N'])}</td>
    <td>{fmt(rx['COM_L'])}</td><td>{fmt(rx['COM_S'])}</td><td style="color:{clr(rx['COM_N'])};font-weight:700">{sgn(rx['COM_N'])}</td>
    <td>{fmt(rx['TOT_L'])}</td><td>{fmt(rx['TOT_S'])}</td><td style="color:{clr(rx['TOT_N'])};font-weight:700;border-right:1px solid rgba(255,255,255,.06)">{sgn(rx['TOT_N'])}</td>
    <td>{fmt(rx['RET_L'])}</td><td>{fmt(rx['RET_S'])}</td><td style="color:{clr(rx['RET_N'])};font-weight:700">{sgn(rx['RET_N'])}</td>
    <td style="color:{ci_clr(rx['ci'])};font-weight:700">{rx['ci']:.1f}%</td>
    <td>{dh(rx,prev,'NC_N')}</td><td>{dh(rx,prev,'COM_N')}</td><td>{dh(rx,prev,'TOT_N')}</td>
  </tr>"""

hist_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>COT Historial · NQ Whale Radar · {total_wks} semanas</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#060b12;color:#94a3b8;font-family:system-ui,-apple-system,sans-serif;padding:20px}}
    h1{{font-size:18px;color:#00f2ff;margin-bottom:6px;font-weight:800}}
    .meta{{font-size:9px;color:#334155;font-family:monospace;margin-bottom:14px}}
    .toolbar{{display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap}}
    input#srch{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);
                color:#94a3b8;padding:7px 14px;border-radius:8px;font-size:11px;width:220px;outline:none}}
    input#srch:focus{{border-color:rgba(0,242,255,.3)}}
    .back{{display:inline-flex;align-items:center;gap:5px;
           background:rgba(0,242,255,.05);border:1px solid rgba(0,242,255,.15);
           color:#00f2ff;padding:7px 14px;border-radius:16px;text-decoration:none;
           font-size:10px;font-weight:700;font-family:monospace}}
    .tbl-wrap{{background:rgba(0,0,0,.3);border:1px solid rgba(255,255,255,.06);
               border-radius:12px;overflow:hidden;overflow-x:auto}}
    table{{width:100%;border-collapse:collapse;font-size:10px}}
    thead th{{padding:8px 10px;text-align:right;background:rgba(255,255,255,.03);
              font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;
              border-bottom:1px solid rgba(255,255,255,.07)}}
    thead th:first-child{{text-align:left}}
    tbody td{{padding:6px 10px;text-align:right;border-bottom:1px solid rgba(255,255,255,.03)}}
    tbody td:first-child{{text-align:left;font-family:monospace}}
    tbody tr:hover{{background:rgba(255,255,255,.015)}}
  </style>
</head>
<body>
  <h1>COT Historial — NASDAQ-100</h1>
  <div class="meta">CFTC · Traders in Financial Futures · {total_wks} semanas · {updated} UTC · NC = Lev.Funds + Asset Mgr</div>
  <div class="toolbar">
    <a href="https://darvinmahi.github.io/nq-whale-radar/#cot-analysis" class="back">← Volver al Dashboard</a>
    <input id="srch" type="text" placeholder="Buscar fecha... (Mar 2026)">
    <span style="font-size:9px;color:#334155;font-family:monospace">{total_wks} registros</span>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th style="text-align:left">Semana</th>
        <th style="color:#4ade80">NC Long</th><th style="color:#f87171">NC Short</th><th style="color:#38bdf8">NC Net</th>
        <th style="color:#4ade80">COM Long</th><th style="color:#f87171">COM Short</th><th style="color:#818cf8">COM Net</th>
        <th style="color:#4ade80">TOT Long</th><th style="color:#f87171">TOT Short</th><th style="color:#e2e8f0;border-right:1px solid rgba(255,255,255,.06)">TOT Net</th>
        <th style="color:#4ade80">RET Long</th><th style="color:#f87171">RET Short</th><th style="color:#94a3b8">RET Net</th>
        <th style="color:#fbbf24">COT%</th>
        <th style="color:#444">ΔNC</th><th style="color:#444">ΔCOM</th><th style="color:#444">ΔTOT</th>
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
print(f'cot_historial.html ({len(hist_page)//1024}KB, {total_wks} semanas)')

# ── 10. Resumen ────────────────────────────────────────────────────────────────
print(f'\n{lbl(last["date"])} | NC:{sgn(last["NC_N"])} | COM:{sgn(last["COM_N"])} | TOT:{sgn(last["TOT_N"])} | COT:{last["ci"]:.1f}%')
