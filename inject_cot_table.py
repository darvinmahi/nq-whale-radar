"""
inject_cot_table.py
— Inyecta la tabla de 4 semanas DENTRO del WHALE RADAR COT (sin tocar el diseño)
— Genera cot_historial.html (página separada con 221 semanas)
— Botón "Historial" abre la página en nueva pestaña
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
                oi = nc_l + dl_l + am_l
                rows.append({'date': d,
                             'nc_l': nc_l, 'nc_s': nc_s,
                             'dl_l': dl_l, 'dl_s': dl_s,
                             'am_l': am_l, 'am_s': am_s,
                             'ret_l': 0, 'ret_s': 0, 'ret_net': None,
                             'oi': oi})
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
    hist   = [x['nc_l'] - x['nc_s'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    net    = r['nc_l'] - r['nc_s']
    r['ci']     = round((net - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0
    r['nc_net'] = net
    r['dl_net'] = r['dl_l'] - r['dl_s']
    r['am_net'] = r['am_l'] - r['am_s']

# ── 4. Helpers ───────────────────────────────────────────────────────────
def fmt(n):      return f'{n:,}' if n else '—'
def pct(n, oi):  return f'{n/oi*100:.1f}%' if oi > 0 else '—'
def ci_color(ci):
    return ('#ff1744' if ci < 25 else '#ff5722' if ci < 45
            else '#ffd600' if ci < 60 else '#69f0ae' if ci < 80 else '#00e676')
def ci_label(ci):
    return ('🔴 MUY BAJISTA' if ci < 25 else '🔴 BEARISH' if ci < 45
            else '🟡 NEUTRAL' if ci < 60 else '🟢 BULLISH' if ci < 80 else '🟢 MUY BULLISH')
def net_clr(n): return '#69f0ae' if n >= 0 else '#ff5252'
def chg_badge(n):
    if n is None: return '<span class="cb neu">—</span>'
    if n == 0:    return '<span class="cb neu">0</span>'
    c = 'pos' if n > 0 else 'neg'
    return f'<span class="cb {c}">{n:+,}</span>'
def lbl(d):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try: return datetime.strptime(d, fmt).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d

SHARED_CSS = """
<style>
* { box-sizing:border-box; margin:0; padding:0 }
body { background:#080d18; color:#c8d0dd; font-family:'Inter',system-ui,sans-serif }
.cot-tbl { width:100%; border-collapse:collapse; font-size:11px; margin-bottom:20px;
           border:1px solid rgba(255,255,255,.07); border-radius:12px; overflow:hidden }
.cot-tbl th, .cot-tbl td { padding:7px 10px; text-align:right }
.cot-tbl td:first-child, .cot-tbl th:first-child { text-align:left }
.cot-tbl thead th { background:rgba(255,255,255,.04); border-bottom:1px solid rgba(255,255,255,.08);
                    font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em }
.cot-tbl tbody tr { border-bottom:1px solid rgba(255,255,255,.04) }
.cot-tbl tbody tr:hover { background:rgba(255,255,255,.02) }
.row-data  td { font-family:monospace; font-weight:700; font-size:12px }
.row-net   td { background:rgba(0,0,0,.2); font-family:monospace }
.row-chg   td { background:rgba(0,0,0,.12) }
.row-pct   td { font-family:monospace; font-size:10px; color:#4a5a7a }
.lbl-cell  { color:#4a5a7a; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap }
.num-l     { color:#4ade80 }
.num-s     { color:#f87171 }
.wk-hdr    { background:rgba(255,255,255,.03); border-top:2px solid transparent }
.wk-hdr.live { border-top-color:rgba(0,242,255,.4) }
.wk-hdr th { font-size:12px; font-weight:700; color:#e2e8f0; text-align:left; padding:10px 12px }
.live-tag  { font-size:8px; background:rgba(0,242,255,.15); color:#00f2ff;
             padding:2px 7px; border-radius:4px; margin-left:8px; vertical-align:middle }
.ci-tag    { font-size:11px; font-weight:900 }
.cb { display:inline-block; padding:1px 5px; border-radius:4px; font-family:monospace;
      font-size:10px; font-weight:700 }
.cb.pos { background:rgba(74,222,128,.12); color:#4ade80 }
.cb.neg { background:rgba(248,113,113,.12); color:#f87171 }
.cb.neu { background:rgba(255,255,255,.05); color:#444 }
</style>"""

def week_block(r, prev, is_live=False):
    """Genera HTML de un bloque semanal completo con columna TOTAL"""
    oi      = r['oi']
    ci      = r['ci']
    nc_net  = r['nc_net']
    dl_net  = r['dl_net']
    am_net  = r['am_net']
    ret_net = r.get('ret_net') or 0

    # ── TOTAL (suma de todas las categorias) ──
    tot_l   = r['nc_l'] + r['dl_l'] + r['am_l'] + r['ret_l']
    tot_s   = r['nc_s'] + r['dl_s'] + r['am_s'] + r['ret_s']
    tot_net = tot_l - tot_s
    # Recalcular OI real como total de longs (mejor proxy)
    real_oi = tot_l if tot_l > 0 else oi

    if prev:
        d = {k: r[k] - prev.get(k, r[k])
             for k in ['nc_l','nc_s','dl_l','dl_s','am_l','am_s','ret_l','ret_s']}
        prev_tot_l = prev['nc_l']+prev['dl_l']+prev['am_l']+prev['ret_l']
        prev_tot_s = prev['nc_s']+prev['dl_s']+prev['am_s']+prev['ret_s']
        d['tot_l'] = tot_l - prev_tot_l
        d['tot_s'] = tot_s - prev_tot_s
    else:
        d = {k: None for k in ['nc_l','nc_s','dl_l','dl_s','am_l','am_s','ret_l','ret_s','tot_l','tot_s']}

    live_span = '<span class="live-tag">LIVE</span>' if is_live else ''
    hdr_cls   = 'wk-hdr live' if is_live else 'wk-hdr'
    ci_c      = ci_color(ci)

    return f"""<table class="cot-tbl">
  <thead>
    <tr class="{hdr_cls}">
      <th colspan="11">
        📅 {lbl(r['date'])} {live_span}
        <span style="float:right;font-size:10px;font-weight:400;color:#444">OI≈{fmt(real_oi)}</span>
        <span style="float:right;margin-right:20px;color:{ci_c};font-weight:900;font-size:11px">
          COT Index: {ci:.1f}% — {ci_label(ci)}
        </span>
      </th>
    </tr>
    <tr>
      <th></th>
      <th colspan="2" style="color:#60a5fa">Non-Commercial<br><small style="color:#2a3a5a;font-weight:400;text-transform:none">Hedge Funds</small></th>
      <th colspan="2" style="color:#f59e0b">Commercial<br><small style="color:#2a3a5a;font-weight:400;text-transform:none">Dealers</small></th>
      <th colspan="2" style="color:#a78bfa">Institucional<br><small style="color:#2a3a5a;font-weight:400;text-transform:none">Asset Mgr</small></th>
      <th colspan="2" style="color:#6b7280">Retail<br><small style="color:#2a3a5a;font-weight:400;text-transform:none">Non-Rept</small></th>
      <th colspan="2" style="color:#e2e8f0;border-left:1px solid rgba(255,255,255,.1)">TOTAL<br><small style="color:#2a3a5a;font-weight:400;text-transform:none">Todas categ.</small></th>
    </tr>
    <tr>
      <th style="color:#2a3a5a"></th>
      <th style="color:#4ade80;font-weight:600">Long</th><th style="color:#f87171;font-weight:600">Short</th>
      <th style="color:#4ade80;font-weight:600">Long</th><th style="color:#f87171;font-weight:600">Short</th>
      <th style="color:#4ade80;font-weight:600">Long</th><th style="color:#f87171;font-weight:600">Short</th>
      <th style="color:#4ade80;font-weight:600">Long</th><th style="color:#f87171;font-weight:600">Short</th>
      <th style="color:#4ade80;font-weight:600;border-left:1px solid rgba(255,255,255,.08)">Long</th><th style="color:#f87171;font-weight:600">Short</th>
    </tr>
  </thead>
  <tbody>
    <tr class="row-data">
      <td class="lbl-cell">Contratos</td>
      <td class="num-l">{fmt(r['nc_l'])}</td><td class="num-s">{fmt(r['nc_s'])}</td>
      <td class="num-l">{fmt(r['dl_l'])}</td><td class="num-s">{fmt(r['dl_s'])}</td>
      <td class="num-l">{fmt(r['am_l'])}</td><td class="num-s">{fmt(r['am_s'])}</td>
      <td class="num-l">{fmt(r['ret_l'])}</td><td class="num-s">{fmt(r['ret_s'])}</td>
      <td class="num-l" style="border-left:1px solid rgba(255,255,255,.08);font-size:13px;color:#e2e8f0">{fmt(tot_l)}</td>
      <td class="num-s" style="font-size:13px;color:#e2e8f0">{fmt(tot_s)}</td>
    </tr>
    <tr class="row-net">
      <td class="lbl-cell">Neto</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{net_clr(nc_net)}">{nc_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{net_clr(dl_net)}">{dl_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{net_clr(am_net)}">{am_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;color:{net_clr(ret_net)}">{ret_net:+,}</td>
      <td colspan="2" style="text-align:center;font-weight:900;font-size:13px;color:{net_clr(tot_net)};border-left:1px solid rgba(255,255,255,.08)">{tot_net:+,}</td>
    </tr>
    <tr class="row-chg">
      <td class="lbl-cell" style="color:#2a3a5a">Cambio sem.</td>
      <td>{chg_badge(d['nc_l'])}</td><td>{chg_badge(d['nc_s'])}</td>
      <td>{chg_badge(d['dl_l'])}</td><td>{chg_badge(d['dl_s'])}</td>
      <td>{chg_badge(d['am_l'])}</td><td>{chg_badge(d['am_s'])}</td>
      <td>{chg_badge(d['ret_l'])}</td><td>{chg_badge(d['ret_s'])}</td>
      <td style="border-left:1px solid rgba(255,255,255,.08)">{chg_badge(d.get('tot_l'))}</td><td>{chg_badge(d.get('tot_s'))}</td>
    </tr>
    <tr class="row-pct">
      <td class="lbl-cell" style="color:#2a3a5a">% Open Int.</td>
      <td>{pct(r['nc_l'],real_oi)}</td><td>{pct(r['nc_s'],real_oi)}</td>
      <td>{pct(r['dl_l'],real_oi)}</td><td>{pct(r['dl_s'],real_oi)}</td>
      <td>{pct(r['am_l'],real_oi)}</td><td>{pct(r['am_s'],real_oi)}</td>
      <td>{pct(r['ret_l'],real_oi)}</td><td>{pct(r['ret_s'],real_oi)}</td>
      <td style="border-left:1px solid rgba(255,255,255,.08);color:#e2e8f0;font-weight:700">{pct(tot_l,real_oi)}</td>
      <td style="color:#e2e8f0;font-weight:700">{pct(tot_s,real_oi)}</td>
    </tr>
  </tbody>
</table>"""

# ── 5. 4 semanas para index.html ──────────────────────────────────────────
last4     = list(reversed(rows[-4:]))
last      = rows[-1]
updated   = datetime.now().strftime('%d/%m/%Y %H:%M')
total_wks = len(rows)

four_html = ''
for i, r in enumerate(last4):
    prev = rows[rows.index(r)-1] if rows.index(r) > 0 else None
    four_html += week_block(r, prev, is_live=(i == 0))

widget = f"""{MARKER_S}
{SHARED_CSS}
<div style="margin-top:24px;border-top:1px solid rgba(255,255,255,.06);padding-top:20px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;flex-wrap:wrap;gap:10px">
    <div>
      <div style="font-size:10px;font-family:monospace;color:#4a5a7a;text-transform:uppercase;letter-spacing:.08em">
        CFTC · Traders in Financial Futures · {total_wks} semanas
      </div>
      <div style="font-size:10px;color:#2a3a5a;margin-top:3px;font-family:monospace">
        Actualizado: {updated} · Auto-update cada viernes 22:00 UTC
      </div>
    </div>
    <a href="cot_historial.html" target="_blank"
       style="display:inline-flex;align-items:center;gap:6px;
              background:rgba(167,139,250,.08);border:1px solid rgba(167,139,250,.25);
              color:#a78bfa;padding:8px 18px;border-radius:20px;text-decoration:none;
              font-size:11px;font-weight:700;transition:all .2s;font-family:inherit">
      📂 Historial completo ({total_wks} semanas) ↗
    </a>
  </div>
  {four_html}
</div>
{MARKER_E}"""

# ── 6. Inyectar en el WHALE RADAR COT ────────────────────────────────────
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

if MARKER_S in html and MARKER_E in html:
    pat  = re.compile(re.escape(MARKER_S) + '.*?' + re.escape(MARKER_E), re.DOTALL)
    html = pat.sub(widget, html)
    print('✅ Widget actualizado')
else:
    # Insertar AL FINAL del section#cot-analysis, antes de </section>
    cot_pos   = html.find('id="cot-analysis"')
    if cot_pos > 0:
        sec_end = html.find('</section>', cot_pos)
        html    = html[:sec_end] + '\n' + widget + '\n' + html[sec_end:]
        print('✅ Widget insertado en cot-analysis')
    else:
        html = html.replace('</body>', widget + '\n</body>')
        print('✅ Widget insertado antes de </body>')

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

# ── 7. Generar cot_historial.html ────────────────────────────────────────
all_blocks = ''
for i, r in enumerate(reversed(rows)):
    idx  = rows.index(r)
    prev = rows[idx-1] if idx > 0 else None
    all_blocks += week_block(r, prev, is_live=(i == 0))

hist_page = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>COT Historial — NASDAQ-100 · {total_wks} semanas</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
  <meta name="description" content="Historial completo de {total_wks} semanas del COT Report CFTC para NASDAQ-100 — Non-Commercial, Commercial, Institutional, Retail">
  {SHARED_CSS}
  <style>
  body {{ padding:24px 16px; max-width:1400px; margin:0 auto }}
  .page-header {{
    display:flex; align-items:flex-start; justify-content:space-between;
    margin-bottom:28px; padding-bottom:16px; border-bottom:1px solid rgba(255,255,255,.07);
    flex-wrap:wrap; gap:12px;
  }}
  .back-btn {{
    display:inline-flex; align-items:center; gap:6px;
    background:rgba(0,242,255,.08); border:1px solid rgba(0,242,255,.2);
    color:#00f2ff; padding:8px 16px; border-radius:20px; text-decoration:none;
    font-size:11px; font-weight:700; font-family:inherit;
  }}
  .back-btn:hover {{ background:rgba(0,242,255,.15) }}
  .search-wrap {{ margin-bottom:20px }}
  #wk-search {{
    background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.1);
    color:#e2e8f0; padding:8px 16px; border-radius:20px; font-family:monospace;
    font-size:12px; width:220px; outline:none;
  }}
  #wk-search:focus {{ border-color:rgba(167,139,250,.4) }}
  .ci-bar {{
    display:inline-block; width:60px; height:6px; border-radius:3px; margin-left:8px;
    background:linear-gradient(90deg, #ff1744, #ffd600, #00e676); position:relative; vertical-align:middle;
  }}
  </style>
</head>
<body>
  <div class="page-header">
    <div>
      <h1 style="font-size:22px;font-weight:900;color:#e2e8f0;margin-bottom:6px">
        📊 COT Historial — NASDAQ-100
      </h1>
      <p style="font-size:11px;color:#4a5a7a;font-family:monospace">
        CFTC · Traders in Financial Futures · {total_wks} semanas · Actualizado: {updated}
      </p>
      <p style="font-size:10px;color:#2a3a5a;margin-top:4px">
        Non-Commercial = Lev. Money (Hedge Funds) · Commercial = Dealers ·
        Institutional = Asset Managers · Retail = Non-Reportable
      </p>
    </div>
    <a href="index.html#cot-analysis" class="back-btn">← Volver al dashboard</a>
  </div>

  <div class="search-wrap">
    <input id="wk-search" type="text" placeholder="Buscar semana (ej: Mar 2026)..."
           oninput="filterWeeks(this.value)">
  </div>

  <div id="weeks-container">
    {all_blocks}
  </div>

  <script>
  function filterWeeks(q) {{
    q = q.toLowerCase();
    document.querySelectorAll('.cot-tbl').forEach(function(t) {{
      var hdr = t.querySelector('thead tr th')?.innerText?.toLowerCase() || '';
      t.style.display = (!q || hdr.includes(q)) ? '' : 'none';
    }});
  }}
  </script>
</body>
</html>"""

with open(HIST_PATH, 'w', encoding='utf-8') as f:
    f.write(hist_page)

print(f'✅ {HIST_PATH} generado ({total_wks} semanas, {len(hist_page)//1024}KB)')
print(f'\n📊 Último COT: {lbl(last["date"])}')
print(f'   NC  L:{last["nc_l"]:,}  S:{last["nc_s"]:,}  Net:{last["nc_net"]:+,}')
print(f'   COM L:{last["dl_l"]:,}  S:{last["dl_s"]:,}  Net:{last["dl_net"]:+,}')
print(f'   AM  L:{last["am_l"]:,}  S:{last["am_s"]:,}  Net:{last["am_net"]:+,}')
print(f'   COT Index: {last["ci"]:.1f}% → {ci_label(last["ci"])}')
