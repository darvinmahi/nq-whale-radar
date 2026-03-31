"""
inject_cot_table.py  — Genera tabla COT estilo CFTC (hardcoded HTML) e inyecta en index.html
Columnas: Non-Commercial(L/S) | Commercial(L/S) | Institutional(L/S) | Retail Net | OI | COT Index
Filas: datos + cambio semana + % de OI
4 semanas por defecto + botón "Ver historial completo"
No depende de ningún JS externo.
"""
import csv, re, requests, zipfile, io, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH = 'index.html'
MARKER_S  = '<!-- COT_TABLE_START -->'
MARKER_E  = '<!-- COT_TABLE_END -->'

# ── 1. Cargar CSV ─────────────────────────────────────────────────────────
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
                # OI aproximado = suma de todos los longs reportables
                oi_est = nc_l + dl_l + am_l
                rows.append({'date': d, 'nc_l': nc_l, 'nc_s': nc_s,
                             'dl_l': dl_l, 'dl_s': dl_s,
                             'am_l': am_l, 'am_s': am_s,
                             'ret_l': 0, 'ret_s': 0, 'ret_net': None,
                             'oi': oi_est})
        except: pass

rows.sort(key=lambda x: x['date'])

# ── 2. Retail desde CFTC ─────────────────────────────────────────────────
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
            nr_l = int(row.get('NonRept_Positions_Long_All') or 0)
            nr_s = int(row.get('NonRept_Positions_Short_All') or 0)
            for r2 in rows:
                if r2['date'] == d:
                    r2['ret_l'] = nr_l
                    r2['ret_s'] = nr_s
                    r2['ret_net'] = nr_l - nr_s
        except: pass
    print('✅ Retail OK')
except Exception as e:
    print(f'⚠️ Retail: {e}')

# ── 3. COT Index ─────────────────────────────────────────────────────────
for i, r in enumerate(rows):
    hist = [x['nc_l'] - x['nc_s'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    net = r['nc_l'] - r['nc_s']
    r['ci'] = round((net - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0

# ── 4. Helpers ───────────────────────────────────────────────────────────
def fmt(n):      return f'{n:,}' if n else '—'
def pct(n, oi):  return f'{n/oi*100:.1f}%' if oi > 0 else '—'
def chg_badge(n):
    if n is None or n == 0: return '<span class="cotbadge neutral">0</span>'
    cls = 'pos' if n > 0 else 'neg'
    return f'<span class="cotbadge {cls}">{n:+,}</span>'
def ci_color(ci):
    return '#ff1744' if ci < 25 else '#ff9800' if ci < 45 else '#ffd60a' if ci < 60 else '#69f0ae' if ci < 80 else '#00e676'
def ci_label(ci):
    return ('🔴 MUY BAJISTA' if ci < 25 else '🔴 BEARISH' if ci < 45
            else '🟡 NEUTRAL' if ci < 60 else '🟢 BULLISH' if ci < 80 else '🟢 MUY BULLISH')

def fmt_date(d):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try: return datetime.strptime(d, fmt).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d

def make_week_block(r, prev, is_latest=False, hidden=False):
    nc_net  = r['nc_l'] - r['nc_s']
    dl_net  = r['dl_l'] - r['dl_s']
    am_net  = r['am_l'] - r['am_s']
    ret_net = r.get('ret_net') or 0
    oi      = r['oi']

    # Cambios vs semana anterior
    if prev:
        d_nc_l  = r['nc_l'] - prev['nc_l']
        d_nc_s  = r['nc_s'] - prev['nc_s']
        d_dl_l  = r['dl_l'] - prev['dl_l']
        d_dl_s  = r['dl_s'] - prev['dl_s']
        d_am_l  = r['am_l'] - prev['am_l']
        d_am_s  = r['am_s'] - prev['am_s']
        d_oi    = oi - prev['oi']
        d_ret_l = r['ret_l'] - prev['ret_l']
        d_ret_s = r['ret_s'] - prev['ret_s']
    else:
        d_nc_l = d_nc_s = d_dl_l = d_dl_s = d_am_l = d_am_s = d_oi = d_ret_l = d_ret_s = None

    live_badge = '<span class="cotlive">LIVE</span>' if is_latest else ''
    hide_attr  = 'class="cot-hist-row"' if hidden else ''
    row_bg     = 'style="border-top:2px solid rgba(0,242,255,.3)"' if is_latest else ''

    return f'''
<div {hide_attr}>
<table class="cot-full-table" {row_bg}>
  <thead>
    <tr class="cot-week-header">
      <th colspan="9" style="text-align:left;padding:10px 12px;font-size:12px;color:#e2e8f0">
        📅 {fmt_date(r['date'])} {live_badge}
        <span style="float:right;font-size:11px;font-weight:400;color:#555">OI: {fmt(oi)}</span>
        <span style="float:right;margin-right:20px;font-size:12px;font-weight:900;color:{ci_color(r['ci'])}">
          COT Index: {r['ci']:.1f}% — {ci_label(r['ci'])}
        </span>
      </th>
    </tr>
    <tr class="cot-col-header">
      <th></th>
      <th colspan="2" style="color:#60a5fa">Non-Commercial<br><small>Hedge Funds</small></th>
      <th colspan="2" style="color:#f59e0b">Commercial<br><small>Dealers/Bancos</small></th>
      <th colspan="2" style="color:#a78bfa">Institutional<br><small>Asset Managers</small></th>
      <th colspan="2" style="color:#888">Retail<br><small>Non-Reportable</small></th>
    </tr>
    <tr class="cot-subheader">
      <th>Categoría</th>
      <th style="color:#4ade80">Long</th>
      <th style="color:#f87171">Short</th>
      <th style="color:#4ade80">Long</th>
      <th style="color:#f87171">Short</th>
      <th style="color:#4ade80">Long</th>
      <th style="color:#f87171">Short</th>
      <th style="color:#4ade80">Long</th>
      <th style="color:#f87171">Short</th>
    </tr>
  </thead>
  <tbody>
    <!-- POSICIONES -->
    <tr class="cot-data-row">
      <td class="rowlabel">Contratos</td>
      <td class="num-l">{fmt(r['nc_l'])}</td>
      <td class="num-s">{fmt(r['nc_s'])}</td>
      <td class="num-l">{fmt(r['dl_l'])}</td>
      <td class="num-s">{fmt(r['dl_s'])}</td>
      <td class="num-l">{fmt(r['am_l'])}</td>
      <td class="num-s">{fmt(r['am_s'])}</td>
      <td class="num-l">{fmt(r['ret_l'])}</td>
      <td class="num-s">{fmt(r['ret_s'])}</td>
    </tr>
    <!-- NET -->
    <tr class="cot-net-row">
      <td class="rowlabel">Neto</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{'#4ade80' if nc_net>=0 else '#f87171'}">{nc_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{'#4ade80' if dl_net>=0 else '#f87171'}">{dl_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{'#4ade80' if am_net>=0 else '#f87171'}">{am_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{'#4ade80' if ret_net>=0 else '#f87171'}">{ret_net:+,}</td>
    </tr>
    <!-- CAMBIOS -->
    <tr class="cot-chg-row">
      <td class="rowlabel" style="color:#555">Cambio sem.</td>
      <td>{chg_badge(d_nc_l)}</td>
      <td>{chg_badge(d_nc_s)}</td>
      <td>{chg_badge(d_dl_l)}</td>
      <td>{chg_badge(d_dl_s)}</td>
      <td>{chg_badge(d_am_l)}</td>
      <td>{chg_badge(d_am_s)}</td>
      <td>{chg_badge(d_ret_l)}</td>
      <td>{chg_badge(d_ret_s)}</td>
    </tr>
    <!-- % OI -->
    <tr class="cot-pct-row">
      <td class="rowlabel" style="color:#555">% Open Int.</td>
      <td>{pct(r['nc_l'],oi)}</td>
      <td>{pct(r['nc_s'],oi)}</td>
      <td>{pct(r['dl_l'],oi)}</td>
      <td>{pct(r['dl_s'],oi)}</td>
      <td>{pct(r['am_l'],oi)}</td>
      <td>{pct(r['am_s'],oi)}</td>
      <td>{pct(r['ret_l'],oi)}</td>
      <td>{pct(r['ret_s'],oi)}</td>
    </tr>
  </tbody>
</table>
</div>'''

# ── 5. Construir el widget completo ───────────────────────────────────────
last4     = list(reversed(rows[-4:]))
hist_rows = list(reversed(rows[:-4]))
last      = rows[-1]
updated   = datetime.now().strftime('%d/%m/%Y %H:%M')
total_wks = len(rows)

# 4 semanas visibles
four_html = ''
for i, r in enumerate(last4):
    prev = rows[rows.index(r) - 1] if rows.index(r) > 0 else None
    four_html += make_week_block(r, prev, is_latest=(i == 0))

# historial oculto
hist_html = ''
for r in hist_rows:
    idx  = rows.index(r)
    prev = rows[idx - 1] if idx > 0 else None
    hist_html += make_week_block(r, prev, hidden=True)

css = """
<style>
.cot-full-table {
  width:100%;border-collapse:collapse;margin-bottom:16px;
  border:1px solid rgba(255,255,255,.06);border-radius:10px;overflow:hidden;
  background:rgba(0,0,0,.3);font-size:11px;
}
.cot-week-header td,.cot-week-header th {
  background:rgba(255,255,255,.04);
}
.cot-col-header th {
  padding:6px 8px;text-align:center;border-bottom:1px solid rgba(255,255,255,.06);
  font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;
}
.cot-col-header small { display:block;font-weight:400;color:#444;font-size:9px;text-transform:none }
.cot-subheader th {
  padding:4px 8px;text-align:right;font-size:9px;font-weight:600;
  color:#444;border-bottom:1px solid rgba(255,255,255,.08);
  background:rgba(0,0,0,.2);
}
.cot-subheader th:first-child { text-align:left }
.cot-data-row td, .cot-net-row td, .cot-chg-row td, .cot-pct-row td {
  padding:7px 10px;text-align:right;border-bottom:1px solid rgba(255,255,255,.04);
}
.cot-data-row td { font-family:monospace;font-size:12px;font-weight:700;color:#e2e8f0 }
.cot-net-row td  { font-family:monospace;font-size:11px;background:rgba(0,0,0,.15) }
.cot-chg-row td  { background:rgba(0,0,0,.1) }
.cot-pct-row td  { font-size:10px;color:#555;font-family:monospace }
.rowlabel { text-align:left!important;color:#444;font-size:10px;font-weight:600;
            text-transform:uppercase;letter-spacing:.04em;white-space:nowrap }
.num-l { color:#4ade80;font-family:monospace }
.num-s { color:#f87171;font-family:monospace }
.cotbadge {
  display:inline-block;padding:1px 6px;border-radius:4px;
  font-family:monospace;font-size:10px;font-weight:700;
}
.cotbadge.pos     { background:rgba(74,222,128,.15);color:#4ade80 }
.cotbadge.neg     { background:rgba(248,113,113,.15);color:#f87171 }
.cotbadge.neutral { background:rgba(255,255,255,.06);color:#555 }
.cotlive {
  display:inline-block;font-size:8px;padding:1px 6px;border-radius:4px;
  background:rgba(0,242,255,.15);color:#00f2ff;margin-left:8px;vertical-align:middle;
}
.cot-hist-row { display:none }
#cot-expand-btn2 {
  background:rgba(167,139,250,.08);border:1px solid rgba(167,139,250,.25);
  color:#a78bfa;padding:10px 24px;border-radius:20px;cursor:pointer;
  font-size:12px;font-family:inherit;transition:all .2s;margin:8px auto;display:block;
}
#cot-expand-btn2:hover { background:rgba(167,139,250,.18);border-color:#a78bfa }
</style>"""

widget = f"""{MARKER_S}
{css}
<section style="padding:0 0 40px 0">
  <div style="max-width:1400px;margin:0 auto;padding:0 20px">

    <!-- Cabecera -->
    <div style="display:flex;align-items:center;justify-content:space-between;
                margin-bottom:20px;flex-wrap:wrap;gap:10px">
      <div>
        <h3 style="font-size:14px;font-weight:900;color:#e2e8f0;margin:0;
                   text-transform:uppercase;letter-spacing:.06em">
          📊 CFTC — Traders in Financial Futures · NASDAQ-100
        </h3>
        <p style="color:#333;font-size:10px;margin:4px 0 0;font-family:monospace">
          {total_wks} semanas · Último: {fmt_date(last['date'])} · Actualizado: {updated}
          &nbsp;|&nbsp; Auto-update cada viernes 22:00 UTC
        </p>
      </div>
      <div style="text-align:right">
        <div style="font-size:24px;font-weight:900;color:{ci_color(last['ci'])}">{last['ci']:.1f}%</div>
        <div style="font-size:10px;color:#444">COT Index (3 años)</div>
        <div style="font-size:11px;font-weight:700;color:{ci_color(last['ci'])}">{ci_label(last['ci'])}</div>
      </div>
    </div>

    <!-- 4 semanas -->
    {four_html}

    <!-- historial -->
    {hist_html}

    <!-- botón -->
    <button id="cot-expand-btn2" onclick="(function(){{
      var rs=document.querySelectorAll('.cot-hist-row');
      var btn=document.getElementById('cot-expand-btn2');
      var open=rs[0]&&rs[0].style.display!=='none';
      rs.forEach(function(r){{r.style.display=open?'none':'block'}});
      btn.textContent=open?'📂 Ver historial completo ({total_wks} semanas)':'📂 Ocultar historial';
    }})()">
      📂 Ver historial completo ({total_wks} semanas)
    </button>

    <p style="text-align:right;font-size:9px;color:#222;margin-top:8px;font-family:monospace">
      Fuente: CFTC · Traders in Financial Futures · NASDAQ-100 Consolidated CME
    </p>
  </div>
</section>
{MARKER_E}"""

# ── 6. Inyectar en index.html ─────────────────────────────────────────────
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

if MARKER_S in html and MARKER_E in html:
    pat  = re.compile(re.escape(MARKER_S) + '.*?' + re.escape(MARKER_E), re.DOTALL)
    html = pat.sub(widget, html)
    print('✅ Tabla COT actualizada')
else:
    # Insertar después del cierre del section cot-analysis
    close = '</section>\n<!-- COT_WIDGET_START -->'
    if '<!-- COT_WIDGET_START -->' in html:
        html = html.replace('<!-- COT_WIDGET_START -->', MARKER_S, 1)
        # Buscar ref cierre y añadir el widget justo antes
        pos = html.find('<section id="cot-analysis"')
        end = html.find('</section>', pos) + len('</section>')
        html = html[:end] + '\n' + widget + html[end:]
    else:
        # Insertar después del section cot-analysis
        pos = html.find('<section id="cot-analysis"')
        if pos > 0:
            end = html.find('</section>', pos) + len('</section>')
            html = html[:end] + '\n' + widget + html[end:]
        else:
            html = html.replace('</body>', widget + '\n</body>')
    print('✅ Tabla COT insertada')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

print(f'\n📊 Resumen:')
print(f'   Último: {last["date"]}  |  NC Net: {last["nc_l"]-last["nc_s"]:+,}  |  COT Index: {last["ci"]:.1f}%')
print(f'   NC  L:{last["nc_l"]:,}  S:{last["nc_s"]:,}  Net:{last["nc_l"]-last["nc_s"]:+,}')
print(f'   COM L:{last["dl_l"]:,}  S:{last["dl_s"]:,}  Net:{last["dl_l"]-last["dl_s"]:+,}')
print(f'   AM  L:{last["am_l"]:,}  S:{last["am_s"]:,}  Net:{last["am_l"]-last["am_s"]:+,}')
print(f'   OI: {last["oi"]:,}  |  Semanas: {total_wks}')
