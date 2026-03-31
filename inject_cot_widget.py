"""
inject_cot_widget.py — Widget COT con 4 semanas por defecto + botón "Ver todo"
Auto-invocado desde GitHub Actions cada viernes.
"""
import csv, requests, zipfile, io, sys, re
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH   = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH  = 'index.html'
ANCHOR     = '<!-- COT_WIDGET_START -->'
ANCHOR_END = '<!-- COT_WIDGET_END -->'

# ── 1. Leer CSV ───────────────────────────────────────────────────────────
rows = []
with open(CSV_PATH, encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d    = r['Report_Date_as_MM_DD_YYYY'].strip()
            lm_l = int(r.get('Lev_Money_Positions_Long_All') or 0)
            lm_s = int(r.get('Lev_Money_Positions_Short_All') or 0)
            dl_l = int(r.get('Dealer_Positions_Long_All') or 0)
            dl_s = int(r.get('Dealer_Positions_Short_All') or 0)
            am_l = int(r.get('Asset_Mgr_Positions_Long_All') or 0)
            am_s = int(r.get('Asset_Mgr_Positions_Short_All') or 0)
            if lm_l or lm_s:
                rows.append({'date':d,
                             'nc_l':lm_l,'nc_s':lm_s,'nc_net':lm_l-lm_s,
                             'com_l':dl_l,'com_s':dl_s,'com_net':dl_l-dl_s,
                             'am_l':am_l,'am_s':am_s,'am_net':am_l-am_s,
                             'ret_net':None})
        except: pass

rows.sort(key=lambda x: x['date'])

# ── 2. COT Index 3 años ───────────────────────────────────────────────────
for i, r in enumerate(rows):
    hist = [x['nc_net'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = (r['nc_net'] - mn) / (mx - mn) * 100 if mx > mn else 50.0

# ── 3. Non-Reportable (Retail) desde CFTC ────────────────────────────────
try:
    resp = requests.get(
        'https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=60)
    zf   = zipfile.ZipFile(io.BytesIO(resp.content))
    fobj = zf.open(zf.namelist()[0])
    reader = csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace'))
    for row in reader:
        if 'NASDAQ-100 Consolidated' not in row.get('Market_and_Exchange_Names',''):
            continue
        d = row.get('Report_Date_as_YYYY-MM-DD','').strip()
        try:
            nr_l = int(row.get('NonRept_Positions_Long_All') or 0)
            nr_s = int(row.get('NonRept_Positions_Short_All') or 0)
            for r in rows:
                if r['date'] == d:
                    r['ret_net'] = nr_l - nr_s
        except: pass
    print(f"✅ Non-Reportable OK")
except Exception as e:
    print(f"⚠️ Non-Reportable no disponible: {e}")

# ── 4. Helpers ────────────────────────────────────────────────────────────
def net_color(n): return '#00e676' if (n or 0) > 0 else '#ff1744'
def ci_color(ci):
    return '#ff1744' if ci<25 else '#ff9800' if ci<45 else '#888' if ci<60 else '#69f0ae' if ci<80 else '#00e676'
def ci_label(ci):
    return ('🔴🔴 MUY BEARISH' if ci<25 else '🔴 BEARISH' if ci<45
            else '🟡 NEUTRAL' if ci<60 else '🟢 BULLISH' if ci<80 else '🟢🟢 MUY BULLISH')
def delta_str(cur, prev):
    if prev is None: return ''
    d = cur - prev
    return (f'<span style="color:#00e676">+{d:,}</span>' if d > 0
            else f'<span style="color:#ff1744">{d:,}</span>' if d < 0
            else '<span style="color:#555">─</span>')

def make_rows(data, cls=''):
    html = ''
    for i, r in enumerate(data):
        prev   = data[i-1] if i > 0 else None
        nc_d   = delta_str(r['nc_net'],  prev['nc_net']  if prev else None)
        com_d  = delta_str(r['com_net'], prev['com_net'] if prev else None)
        am_d   = delta_str(r['am_net'],  prev['am_net']  if prev else None)
        ret_v  = r['ret_net']
        ret_td = (f'<td style="color:{net_color(ret_v)};font-weight:700">{ret_v:+,}</td>'
                  if ret_v is not None else '<td style="color:#444">—</td>')
        row_bg = 'background:rgba(255,255,255,0.015)' if i % 2 == 0 else ''
        html += f"""
<tr class="cot-tr {cls}" style="{row_bg}">
  <td style="color:#a78bfa;font-weight:700;white-space:nowrap;padding:9px 12px">{r['date']}</td>
  <td style="color:{net_color(r['nc_net'])};font-weight:700;padding:9px 12px;text-align:center">
    {r['nc_net']:+,}<br><small style="font-size:10px">{nc_d}</small></td>
  <td style="color:{net_color(r['com_net'])};font-weight:700;padding:9px 12px;text-align:center">
    {r['com_net']:+,}<br><small style="font-size:10px">{com_d}</small></td>
  <td style="color:{net_color(r['am_net'])};font-weight:700;padding:9px 12px;text-align:center">
    {r['am_net']:+,}<br><small style="font-size:10px">{am_d}</small></td>
  {ret_td.replace('<td', '<td style="padding:9px 12px;text-align:center;font-weight:700"', 1) if 'color' in ret_td else ret_td.replace('<td', '<td style="padding:9px 12px;text-align:center"', 1)}
  <td style="color:{ci_color(r['ci'])};font-weight:900;font-size:14px;padding:9px 12px;text-align:center">{r['ci']:.1f}%</td>
</tr>"""
    return html

last   = rows[-1]
last4  = rows[-4:]
all_rows_html = make_rows(list(reversed(rows)), cls='cot-hist')
four_rows_html = make_rows(last4)
updated = datetime.now().strftime('%d/%m/%Y %H:%M')

THEAD = """<thead>
  <tr style="background:rgba(255,255,255,0.04)">
    <th style="padding:10px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#444;border-bottom:1px solid rgba(255,255,255,.06)">Semana</th>
    <th style="padding:10px 12px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:#60a5fa;border-bottom:1px solid rgba(255,255,255,.06)">Non-Commercial<br><span style="color:#444;font-weight:400">Hedge Funds</span></th>
    <th style="padding:10px 12px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:#f59e0b;border-bottom:1px solid rgba(255,255,255,.06)">Commercial<br><span style="color:#444;font-weight:400">Dealers</span></th>
    <th style="padding:10px 12px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:#a78bfa;border-bottom:1px solid rgba(255,255,255,.06)">Institutional<br><span style="color:#444;font-weight:400">Asset Mgr</span></th>
    <th style="padding:10px 12px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:#888;border-bottom:1px solid rgba(255,255,255,.06)">Retail<br><span style="color:#444;font-weight:400">Non-Rept</span></th>
    <th style="padding:10px 12px;text-align:center;font-size:10px;font-weight:700;text-transform:uppercase;color:#34d399;border-bottom:1px solid rgba(255,255,255,.06)">COT Index<br><span style="color:#444;font-weight:400">3Y window</span></th>
  </tr>
</thead>"""

widget = f"""{ANCHOR}
<style>
.cot-hist{{display:none}}
#cot-expand-btn{{
  background:rgba(167,139,250,.1);border:1px solid rgba(167,139,250,.3);
  color:#a78bfa;padding:8px 20px;border-radius:20px;cursor:pointer;
  font-size:12px;font-family:inherit;transition:all .2s;margin-top:12px
}}
#cot-expand-btn:hover{{background:rgba(167,139,250,.2);border-color:#a78bfa}}
</style>

<section id="cot-positions" style="padding:32px 0">
<div style="max-width:1200px;margin:0 auto;padding:0 20px">

  <!-- HEADER -->
  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:12px">
    <div>
      <h2 style="font-size:18px;font-weight:900;color:#e2e8f0;margin:0">
        📜 COT — Posiciones Institucionales NQ
      </h2>
      <p style="color:#444;font-size:11px;margin:5px 0 0">
        CFTC Traders in Financial Futures · {len(rows)} semanas · Actualizado: {updated}
      </p>
    </div>
    <div style="text-align:right">
      <div style="font-size:28px;font-weight:900;color:{ci_color(last['ci'])}">{last['ci']:.1f}%</div>
      <div style="font-size:11px;color:#555">COT Index (3 años)</div>
      <div style="font-size:12px;font-weight:700;color:{ci_color(last['ci'])}">{ci_label(last['ci'])}</div>
      <div style="font-size:10px;color:#333;margin-top:2px">Último: {last['date']}</div>
    </div>
  </div>

  <!-- TARJETAS RESUMEN -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px">
    <div style="background:rgba(96,165,250,.06);border:1px solid rgba(96,165,250,.15);border-radius:12px;padding:14px;text-align:center">
      <div style="font-size:9px;color:#60a5fa;text-transform:uppercase;font-weight:700;letter-spacing:.06em;margin-bottom:8px">Non-Commercial<br>Hedge Funds</div>
      <div style="font-size:22px;font-weight:900;color:{net_color(last['nc_net'])}">{last['nc_net']:+,}</div>
      <div style="font-size:9px;color:#444;margin-top:4px">L {last['nc_l']:,} / S {last['nc_s']:,}</div>
    </div>
    <div style="background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.15);border-radius:12px;padding:14px;text-align:center">
      <div style="font-size:9px;color:#f59e0b;text-transform:uppercase;font-weight:700;letter-spacing:.06em;margin-bottom:8px">Commercial<br>Dealers / Bancos</div>
      <div style="font-size:22px;font-weight:900;color:{net_color(last['com_net'])}">{last['com_net']:+,}</div>
      <div style="font-size:9px;color:#444;margin-top:4px">L {last['com_l']:,} / S {last['com_s']:,}</div>
    </div>
    <div style="background:rgba(167,139,250,.06);border:1px solid rgba(167,139,250,.15);border-radius:12px;padding:14px;text-align:center">
      <div style="font-size:9px;color:#a78bfa;text-transform:uppercase;font-weight:700;letter-spacing:.06em;margin-bottom:8px">Institutional<br>Asset Managers</div>
      <div style="font-size:22px;font-weight:900;color:{net_color(last['am_net'])}">{last['am_net']:+,}</div>
      <div style="font-size:9px;color:#444;margin-top:4px">L {last['am_l']:,} / S {last['am_s']:,}</div>
    </div>
    <div style="background:rgba(136,136,136,.06);border:1px solid rgba(136,136,136,.15);border-radius:12px;padding:14px;text-align:center">
      <div style="font-size:9px;color:#888;text-transform:uppercase;font-weight:700;letter-spacing:.06em;margin-bottom:8px">Retail<br>Non-Reportable</div>
      <div style="font-size:22px;font-weight:900;color:{net_color(last['ret_net'] or 0)}">{(last['ret_net'] or 0):+,}</div>
      <div style="font-size:9px;color:#444;margin-top:4px">Posición neta</div>
    </div>
  </div>

  <!-- TABLA 4 SEMANAS (default) + HISTORIAL EXPANDIBLE -->
  <div style="overflow-x:auto;border-radius:12px;border:1px solid rgba(255,255,255,.06)">
    <table id="cot-table" style="width:100%;border-collapse:collapse;font-size:12px">
      {THEAD}
      <tbody>
        {four_rows_html}
        {all_rows_html}
      </tbody>
    </table>
  </div>

  <!-- BOTÓN EXPANDIR -->
  <div style="text-align:center">
    <button id="cot-expand-btn" onclick="cotToggle()">
      📂 Ver historial completo ({len(rows)} semanas)
    </button>
  </div>

  <p style="text-align:right;margin-top:10px;font-size:10px;color:#222">
    Fuente: CFTC · Traders in Financial Futures · NASDAQ-100 Consolidated CME · Se actualiza cada viernes
  </p>
</div>
</section>

<script>
function cotToggle(){{
  var rows = document.querySelectorAll('.cot-hist');
  var btn  = document.getElementById('cot-expand-btn');
  var open = rows[0] && rows[0].style.display !== 'none';
  rows.forEach(function(r){{ r.style.display = open ? 'none' : 'table-row'; }});
  btn.textContent = open
    ? '📂 Ver historial completo ({len(rows)} semanas)'
    : '📂 Ocultar historial';
}}
</script>
{ANCHOR_END}"""

# ── Inyectar en index.html ────────────────────────────────────────────────
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

if ANCHOR in html and ANCHOR_END in html:
    pattern = re.compile(re.escape(ANCHOR) + '.*?' + re.escape(ANCHOR_END), re.DOTALL)
    html = pattern.sub(widget, html)
    print("✅ Widget COT actualizado en index.html")
else:
    html = html.replace('</body>', widget + '\n</body>')
    print("✅ Widget COT insertado en index.html")

with open(HTML_PATH, 'w', encoding='utf-8') as f:
    f.write(html)

last = rows[-1]
print(f"  Non-Commercial: {last['nc_net']:+,}  COT Index: {last['ci']:.1f}%  → {ci_label(last['ci'])}")
print(f"  Commercial:     {last['com_net']:+,}")
print(f"  Institutional:  {last['am_net']:+,}")
if last['ret_net']: print(f"  Retail:         {last['ret_net']:+,}")
print(f"  Semanas totales en historial: {len(rows)}")
