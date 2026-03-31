"""
fix_and_inject_cot.py — v5
- COT Index calculado UNA VEZ y guardado en CSV (columna COT_Index)
- Si ya existe en el CSV, se usa el valor guardado — NUNCA se recalcula el histórico
- Solo las filas nuevas sin COT_Index reciben el cálculo
- Formato CFTC clásico: Non-Commercial | Commercial | Total | Non-Reportable
"""
import csv, re, requests, zipfile, io, sys, os
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH = 'index.html'
HIST_PATH = 'cot_historial.html'
MARKER_S  = '<!-- COT_TABLE_START -->'
MARKER_E  = '<!-- COT_TABLE_END -->'

# ── 1. Cargar CSV ─────────────────────────────────────────────────────────────
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    original_headers = list(reader.fieldnames)
    raw_rows = list(reader)

for r in raw_rows:
    try:
        d    = r['Report_Date_as_MM_DD_YYYY'].strip()
        lm_l = int(r.get('Lev_Money_Positions_Long_All')  or 0)
        lm_s = int(r.get('Lev_Money_Positions_Short_All') or 0)
        dl_l = int(r.get('Dealer_Positions_Long_All')     or 0)
        dl_s = int(r.get('Dealer_Positions_Short_All')    or 0)
        am_l = int(r.get('Asset_Mgr_Positions_Long_All')  or 0)
        am_s = int(r.get('Asset_Mgr_Positions_Short_All') or 0)
        stored_ci = r.get('COT_Index', '').strip()
        if lm_l or lm_s:
            rows.append({
                'date': d, 'raw': r,
                'lm_l': lm_l, 'lm_s': lm_s,
                'dl_l': dl_l, 'dl_s': dl_s,
                'am_l': am_l, 'am_s': am_s,
                'ret_l': 0, 'ret_s': 0,
                'stored_ci': float(stored_ci) if stored_ci else None,
            })
    except:
        pass

rows.sort(key=lambda x: x['date'])

# ── 2. Añadir Non-Reportable desde CFTC ───────────────────────────────────────
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

# ── 3. Calcular columnas clásicas CFTC ────────────────────────────────────────
# NC = Lev_Money + Asset_Mgr  (como en el legacy COT)
# COM = Dealer
for r in rows:
    r['NC_L']  = r['lm_l'] + r['am_l']
    r['NC_S']  = r['lm_s'] + r['am_s']
    r['COM_L'] = r['dl_l']
    r['COM_S'] = r['dl_s']
    r['RET_L'] = r['ret_l']
    r['RET_S'] = r['ret_s']
    r['TOT_L'] = r['NC_L'] + r['COM_L'] + r['RET_L']
    r['TOT_S'] = r['NC_S'] + r['COM_S'] + r['RET_S']
    r['NC_N']  = r['NC_L'] - r['NC_S']
    r['COM_N'] = r['COM_L'] - r['COM_S']
    r['RET_N'] = r['RET_L'] - r['RET_S']
    r['TOT_N'] = r['TOT_L'] - r['TOT_S']

# ── 4. COT Index — GUARDADO EN CSV (Lev_Money solo = especuladores puros) ─────
# Si la fila ya tiene COT_Index en el CSV → se usa el valor guardado
# Si NO tiene → se calcula y se guarda en el CSV para que sea permanente
csv_updated = False
for i, r in enumerate(rows):
    if r['stored_ci'] is not None:
        r['ci'] = r['stored_ci']   # ← VALOR FIJO, no se recalcula
    else:
        # Primera vez: calcular trailing 3 años (156 semanas) en Lev_Money
        hist = [x['lm_l'] - x['lm_s'] for x in rows[max(0, i-156):i+1]]
        mn, mx = min(hist), max(hist)
        lm_net = r['lm_l'] - r['lm_s']
        r['ci'] = round((lm_net - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0
        csv_updated = True
        print(f"  Nuevo COT Index calculado: {r['date']} → {r['ci']:.1f}%")

# Guardar COT_Index en el CSV si hubo filas nuevas
if csv_updated:
    new_headers = original_headers.copy()
    if 'COT_Index' not in new_headers:
        new_headers.append('COT_Index')
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=new_headers)
        w.writeheader()
        for r in rows:
            row_out = dict(r['raw'])
            row_out['COT_Index'] = f"{r['ci']:.1f}"
            w.writerow(row_out)
    print(f'CSV actualizado con COT_Index ({len(rows)} filas)')
elif 'COT_Index' not in original_headers:
    # Primera migración: guardar todos los CIs al CSV
    print('Migrando COT_Index al CSV por primera vez...')
    new_headers = original_headers + ['COT_Index']
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=new_headers)
        w.writeheader()
        for r in rows:
            row_out = dict(r['raw'])
            row_out['COT_Index'] = f"{r['ci']:.1f}"
            w.writerow(row_out)
    print(f'CSV migrado: COT_Index guardado en {len(rows)} filas')

# ── 5. Helpers ────────────────────────────────────────────────────────────────
def fmt(n):  return f'{n:,}'
def sgn(n):  return f'+{n:,}' if n >= 0 else f'{n:,}'
def clr(n):  return '#34d399' if n > 0 else '#f87171' if n < 0 else '#64748b'

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
        try: return datetime.strptime(d, fmt2).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d

def dlbl(n):
    if n is None: return '<span style="color:#1e3a5f">—</span>'
    c = clr(n)
    return f'<span style="color:{c};font-weight:700">{sgn(n)}</span>'

def delta(r, prev, key):
    if prev is None: return None
    return r[key] - prev[key]

def dh(r, p, k):
    if p is None: return '<span style="color:#1e3a5f">—</span>'
    n = r[k] - p[k]
    c = '#34d399' if n > 0 else '#f87171' if n < 0 else '#64748b'
    return f'<span style="color:{c};font-weight:700">{sgn(n)}</span>'

# ── 6. Preparar datos semana actual ──────────────────────────────────────────
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

dNC_L  = dlbl(delta(r0,prev,'NC_L'));  dNC_S  = dlbl(delta(r0,prev,'NC_S'));  dNC_N  = dlbl(delta(r0,prev,'NC_N'))
dCOM_L = dlbl(delta(r0,prev,'COM_L')); dCOM_S = dlbl(delta(r0,prev,'COM_S')); dCOM_N = dlbl(delta(r0,prev,'COM_N'))
dRET_L = dlbl(delta(r0,prev,'RET_L')); dRET_S = dlbl(delta(r0,prev,'RET_S')); dRET_N = dlbl(delta(r0,prev,'RET_N'))
dTOT_L = dlbl(delta(r0,prev,'TOT_L')); dTOT_S = dlbl(delta(r0,prev,'TOT_S')); dTOT_N = dlbl(delta(r0,prev,'TOT_N'))

# ── 7. Filas historia compactas (3 semanas anteriores) ──────────────────────
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

# ── 8. Widget HTML ────────────────────────────────────────────────────────────
TH = 'padding:6px 8px;text-align:right;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;border-bottom:2px solid rgba(255,255,255,.08)'
TD_G = 'padding:8px 8px;text-align:right;font-family:monospace;font-size:12px;font-weight:800;color:#4ade80'
TD_R = 'padding:8px 8px;text-align:right;font-family:monospace;font-size:12px;font-weight:800;color:#f87171'

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
        CFTC · fut_fin_txt · NC = Lev.Funds + Asset Mgr · COT Index = Lev.Funds solo (guardado en CSV) · {total_wks}w
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
        <tr style="background:rgba(255,255,255,.02)">
          <th style="padding:8px 12px;text-align:left;font-size:8px;color:#334155;font-weight:400;min-width:90px"></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#38bdf8;letter-spacing:.07em;border-left:1px solid rgba(255,255,255,.05);border-right:1px solid rgba(255,255,255,.06)">NON-COMMERCIAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Lev.Funds + Asset Mgr</span></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#818cf8;letter-spacing:.07em;border-right:1px solid rgba(255,255,255,.06)">COMMERCIAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Dealer/Intermediary</span></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#e2e8f0;letter-spacing:.07em;border-right:1px solid rgba(255,255,255,.08)">TOTAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">todas categorias</span></th>
          <th colspan="3" style="padding:8px 0;text-align:center;font-size:9px;font-weight:800;color:#94a3b8;letter-spacing:.07em">NON-REPORTABLE<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Retail</span></th>
        </tr>
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
    CFTC fut_fin_txt · NC = Lev.Funds + Asset Mgr · COT Index fijado en CSV · Auto-update viernes
  </div>
</div>
{MARKER_E}"""

# ── 9. Reparar e inyectar index.html ──────────────────────────────────────────
import re as _re

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# Paso A: DOCTYPE
if html.startswith('<!DOCTYPE\n') or (html.startswith('<!DOCTYPE') and 'html>' not in html[:30]):
    s0 = html.find(MARKER_S)
    e0 = html.find(MARKER_E, s0)
    if e0 > 0:
        html = '<!DOCTYPE html>\n' + html[e0 + len(MARKER_E):]
        html = _re.sub(r'^\s*html>', '', html).lstrip('\n')

# Paso B: Eliminar bloques COT existentes
pat_full   = _re.compile(_re.escape(MARKER_S) + '.*?' + _re.escape(MARKER_E), _re.DOTALL)
pat_orphan = _re.compile(_re.escape(MARKER_S))
before = len(_re.findall(_re.escape(MARKER_S), html))
html = pat_full.sub('', html)
html = pat_orphan.sub('', html)
print(f'Marcadores eliminados: {before}')

# Paso C: REEMPLAZAR todo el contenido de section#cot-analysis
cot_pos = html.find('id="cot-analysis"')
if cot_pos > 0:
    tag_end = html.find('>', cot_pos) + 1
    sec_end = html.find('</section>', cot_pos)
    html    = html[:tag_end] + '\n' + widget + '\n' + html[sec_end:]
    print('Widget REEMPLAZA cot-analysis')
else:
    html = html.replace('</body>', '\n' + widget + '\n</body>', 1)
    print('Widget inyectado antes de </body>')

starts = len(_re.findall(_re.escape(MARKER_S), html))
ends   = len(_re.findall(_re.escape(MARKER_E), html))
assert starts == 1 and ends == 1, f'ERROR marcadores: {starts} START, {ends} END'

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'index.html guardado ({len(html)//1024}KB)')

# ── 10. Generar cot_historial.html ────────────────────────────────────────────
all_rows_html = ''
for i in range(len(rows)-1, -1, -1):
    rx      = rows[i]
    prev    = rows[i-1] if i > 0 else None
    is_live = (i == len(rows)-1)
    row_bg  = 'rgba(0,242,255,.05)' if is_live else ('rgba(255,255,255,.01)' if i % 2 == 0 else '')
    d_style = 'color:#00f2ff;font-weight:800' if is_live else 'color:#94a3b8'
    badge   = '<span style="font-size:7px;background:rgba(0,242,255,.1);color:#00f2ff;padding:1px 5px;border-radius:3px;margin-left:5px">LIVE</span>' if is_live else ''

    all_rows_html += f"""
  <tr class="data-row" style="background:{row_bg}" data-date="{lbl(rx['date']).lower()}" data-ci="{rx['ci']:.1f}">
    <td style="{d_style};padding:7px 12px;font-family:monospace;font-size:10px;white-space:nowrap">{lbl(rx['date'])}{badge}</td>
    <td class="g">{fmt(rx['NC_L'])}</td><td class="r">{fmt(rx['NC_S'])}</td>
    <td style="color:{clr(rx['NC_N'])};font-weight:800;padding:7px 8px;text-align:right;font-family:monospace;border-right:1px solid rgba(255,255,255,.05)">{sgn(rx['NC_N'])}</td>
    <td class="g">{fmt(rx['COM_L'])}</td><td class="r">{fmt(rx['COM_S'])}</td>
    <td style="color:{clr(rx['COM_N'])};font-weight:800;padding:7px 8px;text-align:right;font-family:monospace;border-right:1px solid rgba(255,255,255,.05)">{sgn(rx['COM_N'])}</td>
    <td class="g">{fmt(rx['TOT_L'])}</td><td class="r">{fmt(rx['TOT_S'])}</td>
    <td style="color:{clr(rx['TOT_N'])};font-weight:900;padding:7px 8px;text-align:right;font-family:monospace;font-size:11px;border-right:1px solid rgba(255,255,255,.07)">{sgn(rx['TOT_N'])}</td>
    <td class="g">{fmt(rx['RET_L'])}</td><td class="r">{fmt(rx['RET_S'])}</td>
    <td style="color:{clr(rx['RET_N'])};font-weight:800;padding:7px 8px;text-align:right;font-family:monospace;border-right:1px solid rgba(255,255,255,.07)">{sgn(rx['RET_N'])}</td>
    <td style="color:{ci_clr(rx['ci'])};font-weight:900;padding:7px 8px;text-align:center;font-family:monospace;font-size:11px">{rx['ci']:.1f}%</td>
    <td style="padding:7px 8px;text-align:right;font-size:10px">{dh(rx,prev,'NC_N')}</td>
    <td style="padding:7px 8px;text-align:right;font-size:10px">{dh(rx,prev,'COM_N')}</td>
    <td style="padding:7px 8px;text-align:right;font-size:10px">{dh(rx,prev,'TOT_N')}</td>
  </tr>"""

hist_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>COT Historial · NQ Whale Radar · {total_wks} semanas</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    html,body{{height:100%;background:#060b12;color:#94a3b8;font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif}}
    .page-header{{position:sticky;top:0;z-index:100;background:rgba(6,11,18,.96);backdrop-filter:blur(14px);border-bottom:1px solid rgba(255,255,255,.06);padding:14px 20px 10px}}
    .page-header h1{{font-size:16px;color:#00f2ff;font-weight:900;letter-spacing:.04em;margin-bottom:2px}}
    .page-meta{{font-size:8px;color:#334155;font-family:monospace;margin-bottom:8px}}
    .toolbar{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:8px}}
    #srch{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);color:#cbd5e1;padding:6px 14px;border-radius:8px;font-size:11px;width:200px;outline:none;transition:border-color .2s}}
    #srch:focus{{border-color:rgba(0,242,255,.4);background:rgba(0,242,255,.02)}}
    #srch::placeholder{{color:#1e3a5f}}
    .filter-btn{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);color:#64748b;padding:5px 12px;border-radius:20px;font-size:9px;font-weight:700;cursor:pointer;transition:all .15s;font-family:monospace}}
    .filter-btn.active,.filter-btn:hover{{background:rgba(0,242,255,.08);border-color:rgba(0,242,255,.3);color:#00f2ff}}
    .back{{display:inline-flex;align-items:center;gap:5px;background:rgba(0,242,255,.07);border:1px solid rgba(0,242,255,.2);color:#00f2ff;padding:6px 14px;border-radius:16px;text-decoration:none;font-size:9px;font-weight:800;font-family:monospace;flex-shrink:0}}
    .back:hover{{background:rgba(0,242,255,.12)}}
    #count{{font-size:9px;color:#334155;font-family:monospace}}
    .legend{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
    .leg{{font-size:8px;font-family:monospace;font-weight:700;padding:2px 8px;border-radius:10px;border:1px solid rgba(255,255,255,.06)}}
    .content{{padding:14px 20px 30px}}
    .tbl-wrap{{background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.07);border-radius:12px;overflow:hidden;overflow-x:auto}}
    table{{width:100%;border-collapse:collapse;font-size:10px}}
    tr.grp-row th{{padding:8px 0;text-align:center;font-size:9px;font-weight:800;letter-spacing:.07em;text-transform:uppercase;background:rgba(255,255,255,.02);border-bottom:1px solid rgba(255,255,255,.04)}}
    tr.col-row th{{padding:6px 8px;text-align:right;font-size:8px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;background:rgba(0,0,0,.25);border-bottom:2px solid rgba(255,255,255,.08)}}
    tr.col-row th:first-child{{text-align:left;padding:6px 12px}}
    td.g{{padding:7px 8px;text-align:right;font-family:monospace;color:#4ade80}}
    td.r{{padding:7px 8px;text-align:right;font-family:monospace;color:#f87171}}
    .data-row{{border-bottom:1px solid rgba(255,255,255,.03)}}
    .data-row:hover td{{background:rgba(255,255,255,.01)!important}}
  </style>
</head>
<body>
  <div class="page-header">
    <h1>📊 COT Historial — NASDAQ-100</h1>
    <div class="page-meta">CFTC · TFF Disaggregated · NC = Lev.Funds + Asset Mgr · COT Index = Lev.Funds solo (fijado en CSV) · {total_wks}w · {updated}</div>
    <div class="toolbar">
      <a href="https://darvinmahi.github.io/nq-whale-radar/#cot-analysis" class="back">← Dashboard</a>
      <input id="srch" type="text" placeholder="Buscar: mar 2026…">
      <button class="filter-btn active" onclick="setFilter(this,'all')">Todas ({total_wks}w)</button>
      <button class="filter-btn" onclick="setFilter(this,'bull')">🟢 Bullish &gt;60%</button>
      <button class="filter-btn" onclick="setFilter(this,'bear')">🔴 Bearish &lt;40%</button>
      <button class="filter-btn" onclick="setFilter(this,'extreme')">⚡ Extremo &lt;20%</button>
      <span id="count">{total_wks} semanas</span>
    </div>
    <div class="legend">
      <span class="leg" style="color:#f87171;border-color:rgba(248,113,113,.2)">0–20% BAJISTA EXTREMO</span>
      <span class="leg" style="color:#fb923c;border-color:rgba(251,146,60,.2)">20–40% BEARISH</span>
      <span class="leg" style="color:#fbbf24;border-color:rgba(251,191,36,.2)">40–60% NEUTRAL</span>
      <span class="leg" style="color:#34d399;border-color:rgba(52,211,153,.2)">60–80% BULLISH</span>
      <span class="leg" style="color:#22c55e;border-color:rgba(34,197,94,.2)">80–100% BULLISH EXTREMO</span>
    </div>
  </div>

  <div class="content">
    <div class="tbl-wrap">
      <table>
        <thead>
          <tr class="grp-row">
            <th style="text-align:left;padding:8px 12px;font-size:8px;color:#334155;font-weight:400">SEMANA</th>
            <th colspan="3" style="color:#38bdf8;border-left:1px solid rgba(255,255,255,.05);border-right:1px solid rgba(255,255,255,.06)">NON-COMMERCIAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Lev.Funds + Asset Mgr</span></th>
            <th colspan="3" style="color:#818cf8;border-right:1px solid rgba(255,255,255,.06)">COMMERCIAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Dealer / Intermediary</span></th>
            <th colspan="3" style="color:#e2e8f0;border-right:1px solid rgba(255,255,255,.08)">TOTAL<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">todas categorias</span></th>
            <th colspan="3" style="color:#94a3b8;border-right:1px solid rgba(255,255,255,.07)">NON-REPORTABLE<br><span style="font-size:7px;font-weight:400;color:#1e3a5f">Retail</span></th>
            <th style="color:#fbbf24">COT<br>Index</th>
            <th colspan="3" style="color:#334155;border-left:1px solid rgba(255,255,255,.04)">Δ CAMBIO SEMANAL<br><span style="font-size:7px;font-weight:400">NC / COM / TOT net</span></th>
          </tr>
          <tr class="col-row">
            <th></th>
            <th style="color:#4ade80;border-left:1px solid rgba(255,255,255,.05)">LONG</th><th style="color:#f87171">SHORT</th><th style="color:#94a3b8;border-right:1px solid rgba(255,255,255,.05)">NET</th>
            <th style="color:#4ade80">LONG</th><th style="color:#f87171">SHORT</th><th style="color:#94a3b8;border-right:1px solid rgba(255,255,255,.05)">NET</th>
            <th style="color:#4ade80">LONG</th><th style="color:#f87171">SHORT</th><th style="color:#94a3b8;border-right:1px solid rgba(255,255,255,.07)">NET</th>
            <th style="color:#4ade80">LONG</th><th style="color:#f87171">SHORT</th><th style="color:#94a3b8;border-right:1px solid rgba(255,255,255,.07)">NET</th>
            <th style="color:#fbbf24;text-align:center">%</th>
            <th style="color:#334155">ΔNC</th><th style="color:#334155">ΔCOM</th><th style="color:#334155">ΔTOT</th>
          </tr>
        </thead>
        <tbody id="tbody">{all_rows_html}</tbody>
      </table>
    </div>
    <div style="text-align:right;margin-top:8px;font-size:8px;color:#1e3a5f;font-family:monospace">
      CFTC fut_fin_txt · COT Index fijado en CSV · Auto-update viernes 22:30 UTC · {total_wks} semanas
    </div>
  </div>

  <script>
  var allRows = Array.from(document.querySelectorAll('#tbody .data-row'));
  var activeFilter = 'all';
  document.getElementById('srch').addEventListener('input', function() {{ applyFilters(this.value.toLowerCase()); }});
  function setFilter(btn, f) {{
    document.querySelectorAll('.filter-btn').forEach(function(b){{b.classList.remove('active')}});
    btn.classList.add('active'); activeFilter = f;
    applyFilters(document.getElementById('srch').value.toLowerCase());
  }}
  function applyFilters(q) {{
    var visible = 0;
    allRows.forEach(function(tr) {{
      var dateOK = !q || (tr.dataset.date||'').includes(q);
      var ci = parseFloat(tr.dataset.ci) || 0;
      var fOK = activeFilter==='all' || (activeFilter==='bull'&&ci>=60) || (activeFilter==='bear'&&ci<40) || (activeFilter==='extreme'&&ci<20);
      tr.style.display = (dateOK && fOK) ? '' : 'none';
      if (dateOK && fOK) visible++;
    }});
    document.getElementById('count').textContent = visible + ' semanas';
  }}
  </script>
</body>
</html>"""

with open(HIST_PATH, 'w', encoding='utf-8') as f:
    f.write(hist_page)
print(f'cot_historial.html ({len(hist_page)//1024}KB, {total_wks} semanas)')

# ── 11. Resumen ────────────────────────────────────────────────────────────────
print(f'\n{lbl(last["date"])} | NC:{sgn(last["NC_N"])} | COM:{sgn(last["COM_N"])} | TOT:{sgn(last["TOT_N"])} | COT:{last["ci"]:.1f}% (FIJO en CSV)')
