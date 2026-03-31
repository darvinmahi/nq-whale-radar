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

# ── 5. Generar widget premium ─────────────────────────────────────────────
last4     = list(reversed(rows[-4:]))
last      = rows[-1]
updated   = datetime.now().strftime('%d/%m/%Y %H:%M')
total_wks = len(rows)

def week_table(r, prev, is_live=False):
    """Tabla CFTC compacta: Long/Short/Net/Cambio por categoría + TOTAL. Solo inline styles."""
    nc_l, nc_s = r['nc_l'], r['nc_s']
    dl_l, dl_s = r['dl_l'], r['dl_s']
    am_l, am_s = r['am_l'], r['am_s']
    rt_l, rt_s = r['ret_l'], r['ret_s']
    tot_l = nc_l + dl_l + am_l + rt_l
    tot_s = nc_s + dl_s + am_s + rt_s
    nc_n  = nc_l - nc_s
    dl_n  = dl_l - dl_s
    am_n  = am_l - am_s
    rt_n  = rt_l - rt_s
    tot_n = tot_l - tot_s
    ci    = r['ci']

    def chg_cell(r, prv):
        if prv is None: return '<td colspan="5" style="font-size:8px;color:#333;padding:4px 6px;text-align:center">—</td>'
        def b(n):
            if n is None: return '—'
            c = '#00ff88' if n > 0 else '#ff3355' if n < 0 else '#555'
            return f'<span style="color:{c};font-weight:700">{n:+,}</span>'
        dnc = (r['nc_l']-prv['nc_l']) - (r['nc_s']-prv['nc_s'])
        ddl = (r['dl_l']-prv['dl_l']) - (r['dl_s']-prv['dl_s'])
        dam = (r['am_l']-prv['am_l']) - (r['am_s']-prv['am_s'])
        drt = (r['ret_l']-prv['ret_l']) - (r['ret_s']-prv['ret_s'])
        dtot= dnc+ddl+dam+drt
        return (
            f'<td style="padding:4px 6px;text-align:right;border-bottom:1px solid rgba(255,255,255,.03)">{b(r["nc_l"]-prv["nc_l"])} / {b(r["nc_s"]-prv["nc_s"])}</td>'
            f'<td style="padding:4px 6px;text-align:right;border-bottom:1px solid rgba(255,255,255,.03)">{b(r["dl_l"]-prv["dl_l"])} / {b(r["dl_s"]-prv["dl_s"])}</td>'
            f'<td style="padding:4px 6px;text-align:right;border-bottom:1px solid rgba(255,255,255,.03)">{b(r["am_l"]-prv["am_l"])} / {b(r["am_s"]-prv["am_s"])}</td>'
            f'<td style="padding:4px 6px;text-align:right;border-bottom:1px solid rgba(255,255,255,.03)">{b(r["ret_l"]-prv["ret_l"])} / {b(r["ret_s"]-prv["ret_s"])}</td>'
            f'<td style="padding:4px 6px;text-align:right;border-left:1px solid rgba(255,255,255,.06);border-bottom:1px solid rgba(255,255,255,.03);font-weight:700">{b(dtot)}</td>'
        )

    live_badge = '<span style="font-size:7px;background:rgba(0,242,255,.12);color:#00f2ff;padding:1px 6px;border-radius:3px;margin-left:6px">LIVE</span>' if is_live else ''
    hdr_bg = 'rgba(0,242,255,.03)' if is_live else 'rgba(255,255,255,.02)'
    hdr_bd = 'rgba(0,242,255,.3)' if is_live else 'rgba(255,255,255,.06)'
    chg_row = chg_cell(r, prev)

    return f"""
<div style="background:rgba(0,0,0,.25);border:1px solid {hdr_bd};border-radius:10px;overflow:hidden;margin-bottom:12px">
  <div style="background:{hdr_bg};padding:8px 12px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,.05)">
    <span style="font-size:10px;font-weight:700;color:#e2e8f0;font-family:monospace">
      📅 {lbl(r['date'])}{live_badge}
    </span>
    <span style="font-size:10px;font-weight:900;color:{ci_clr(ci)}">COT Index: {ci:.1f}% — {ci_sig(ci)}</span>
  </div>
  <div style="overflow-x:auto">
  <table style="width:100%;border-collapse:collapse;font-size:10px;min-width:600px">
    <thead>
      <tr style="background:rgba(255,255,255,.02)">
        <th style="padding:6px 10px;text-align:left;font-size:8px;color:#334155;text-transform:uppercase;letter-spacing:.06em;font-weight:700;width:80px"></th>
        <th style="padding:6px 8px;text-align:right;font-size:8px;color:#00f2ff;text-transform:uppercase;letter-spacing:.05em;font-weight:700">Non-Commercial<br><span style="color:#1e3a5f;font-weight:400;text-transform:none;font-size:7px">Hedge Funds</span></th>
        <th style="padding:6px 8px;text-align:right;font-size:8px;color:#60a5fa;text-transform:uppercase;letter-spacing:.05em;font-weight:700">Commercial<br><span style="color:#1e3a5f;font-weight:400;text-transform:none;font-size:7px">Dealers</span></th>
        <th style="padding:6px 8px;text-align:right;font-size:8px;color:#a78bfa;text-transform:uppercase;letter-spacing:.05em;font-weight:700">Institucional<br><span style="color:#1e3a5f;font-weight:400;text-transform:none;font-size:7px">Asset Mgr</span></th>
        <th style="padding:6px 8px;text-align:right;font-size:8px;color:#fb923c;text-transform:uppercase;letter-spacing:.05em;font-weight:700">Retail<br><span style="color:#1e3a5f;font-weight:400;text-transform:none;font-size:7px">Non-Rept</span></th>
        <th style="padding:6px 10px;text-align:right;font-size:8px;color:#e2e8f0;text-transform:uppercase;letter-spacing:.05em;font-weight:700;border-left:1px solid rgba(255,255,255,.08)">TOTAL<br><span style="color:#1e3a5f;font-weight:400;text-transform:none;font-size:7px">Todas categ.</span></th>
      </tr>
    </thead>
    <tbody>
      <tr style="border-bottom:1px solid rgba(255,255,255,.04)">
        <td style="padding:6px 10px;font-size:8px;color:#4ade80;font-weight:700;text-transform:uppercase;letter-spacing:.06em">LONG</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#4ade80">{fmt(nc_l)}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#4ade80">{fmt(dl_l)}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#4ade80">{fmt(am_l)}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#4ade80">{fmt(rt_l)}</td>
        <td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:900;color:#e2e8f0;border-left:1px solid rgba(255,255,255,.08);font-size:11px">{fmt(tot_l)}</td>
      </tr>
      <tr style="border-bottom:1px solid rgba(255,255,255,.04)">
        <td style="padding:6px 10px;font-size:8px;color:#f87171;font-weight:700;text-transform:uppercase;letter-spacing:.06em">SHORT</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#f87171">{fmt(nc_s)}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#f87171">{fmt(dl_s)}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#f87171">{fmt(am_s)}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:700;color:#f87171">{fmt(rt_s)}</td>
        <td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:900;color:#e2e8f0;border-left:1px solid rgba(255,255,255,.08);font-size:11px">{fmt(tot_s)}</td>
      </tr>
      <tr style="background:rgba(0,0,0,.15);border-bottom:1px solid rgba(255,255,255,.04)">
        <td style="padding:6px 10px;font-size:8px;color:#94a3b8;font-weight:700;text-transform:uppercase;letter-spacing:.06em">NET</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:900;color:{clr(nc_n)}">{nc_n:+,}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:900;color:{clr(dl_n)}">{dl_n:+,}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:900;color:{clr(am_n)}">{am_n:+,}</td>
        <td style="padding:6px 8px;text-align:right;font-family:monospace;font-weight:900;color:{clr(rt_n)}">{rt_n:+,}</td>
        <td style="padding:6px 10px;text-align:right;font-family:monospace;font-weight:900;color:{clr(tot_n)};border-left:1px solid rgba(255,255,255,.08);font-size:12px">{tot_n:+,}</td>
      </tr>
      <tr style="background:rgba(0,0,0,.08)">
        <td style="padding:4px 10px;font-size:8px;color:#334155;font-weight:700;text-transform:uppercase;letter-spacing:.06em">CAMBIO</td>
        {chg_row}
      </tr>
    </tbody>
  </table>
  </div>
</div>"""

# Generar 4 semanas
four_weeks_html = ''
for i, r in enumerate(last4):
    idx  = rows.index(r)
    prev = rows[idx-1] if idx > 0 else None
    four_weeks_html += week_table(r, prev, is_live=(i == 0))

ci_last = last['ci']

widget = f"""{MARKER_S}
<div style="padding-top:8px">

  <!-- COT Header -->
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px;padding-bottom:12px;border-bottom:1px solid rgba(255,255,255,.06)">
    <div>
      <div style="font-size:9px;font-family:monospace;color:#334155;text-transform:uppercase;letter-spacing:.1em;margin-bottom:4px">
        CFTC · Traders in Financial Futures · NASDAQ-100 · {total_wks} semanas
      </div>
      <div style="font-size:11px;font-weight:900;color:{ci_clr(ci_last)}">
        COT Index: {ci_last:.1f}% — {ci_sig(ci_last)}
        <span style="font-size:9px;color:#334155;font-weight:400;margin-left:8px">{lbl(last['date'])} · {updated}</span>
      </div>
    </div>
    <a href="cot_historial.html" target="_blank"
       style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,242,255,.05);
              border:1px solid rgba(0,242,255,.2);color:#00f2ff;padding:6px 14px;
              border-radius:16px;text-decoration:none;font-size:10px;font-weight:700;font-family:monospace">
      📂 HISTORIAL {total_wks}W ↗
    </a>
  </div>

  <!-- 4 semanas con datos exactos -->
  {four_weeks_html}

  <div style="text-align:right;margin-top:6px;font-size:8px;color:#1e3a5f;font-family:monospace">
    CFTC · Auto-update viernes 22:00 UTC
  </div>
</div>
{MARKER_E}"""

# ── 6. Reparar + inyectar index.html ────────────────────────────────────
import re as _re

with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

# ─ Paso A: Reparar DOCTYPE corrompido ────────────────────────────────────
# Si empieza con "<!DOCTYPE\n<!-- COT_TABLE_START -->" → corregir
if html.startswith('<!DOCTYPE\n') or (html.startswith('<!DOCTYPE') and 'html>' not in html[:30]):
    # Encontrar primer bloque stale y eliminarlo
    s0 = html.find(MARKER_S)
    e0_raw = html.find(MARKER_E, s0)
    if e0_raw > 0:
        # Reconstruir DOCTYPE limpio
        html = '<!DOCTYPE html>\n' + html[e0_raw + len(MARKER_E):]
        # Eliminar " html>" residual al principio si quedó
        html = _re.sub(r'^\s*html\>', '', html).lstrip('\n')
        print('✅ DOCTYPE reparado (bloque stale head eliminado)')

# ─ Paso B: Eliminar TODOS los bloques COT_TABLE_START/END ─────────────────
# (incluso bloques sin cierre = orphans)
# Estrategia: eliminar todo lo que esté entre START y END (inclusive)
# Para orphans sin END: eliminar solo la línea del START
pat_full   = _re.compile(_re.escape(MARKER_S) + '.*?' + _re.escape(MARKER_E), _re.DOTALL)
pat_orphan = _re.compile(_re.escape(MARKER_S))

before_count = len(_re.findall(_re.escape(MARKER_S), html))
html = pat_full.sub('', html)   # quitar bloques completos
html = pat_orphan.sub('', html) # quitar orphans que queden
after_count = len(_re.findall(_re.escape(MARKER_S), html))
print(f'Marcadores START eliminados: {before_count} → {after_count}')

# ─ Paso C: REEMPLAZAR todo el contenido del section#cot-analysis ────────────
cot_pos = html.find('id="cot-analysis"')
if cot_pos > 0:
    # Encontrar el cierre del tag de apertura del section
    tag_open_end = html.find('>', cot_pos) + 1
    sec_end      = html.find('</section>', cot_pos)
    # REEMPLAZAR todo el interior del section (no solo append)
    html = html[:tag_open_end] + '\n' + widget + '\n' + html[sec_end:]
    print('✅ Widget REEMPLAZA contenido de cot-analysis (viejo eliminado)')
else:
    html = html.replace('</body>', '\n' + widget + '\n</body>', 1)
    print('✅ Widget inyectado antes de </body>')

# ─ Verificación final ────────────────────────────────────────────────────
assert html.startswith('<!DOCTYPE html>'), f'DOCTYPE roto: {html[:50]}'
starts_final = len(_re.findall(_re.escape(MARKER_S), html))
ends_final   = len(_re.findall(_re.escape(MARKER_E), html))
print(f'Verificación: {starts_final} START, {ends_final} END — OK')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)
print(f'✅ index.html guardado ({len(html)//1024}KB)')

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
    <a href="https://darvinmahi.github.io/nq-whale-radar/#cot-analysis" class="back">← Volver al Dashboard</a>
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
