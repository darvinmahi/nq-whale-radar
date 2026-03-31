"""
generate_cot_update.py
Lee CSV local + CFTC, escribe cot_data.js (namespace window.NQ_COT).
cot_data.js es incluido en index.html ANTES de agent_live_data_v2.js.
El engine cloud_runner.py NO toca este archivo.
"""
import csv, json, re, requests, zipfile, io, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH = 'data/cot/nasdaq_cot_historical.csv'
JS_OUT   = 'cot_data.js'
HTML_PATH= 'index.html'

# ── 1. Cargar CSV ─────────────────────────────────────────────────────────
all_rows = []
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
                all_rows.append({'date': d,
                                 'nc_l': nc_l, 'nc_s': nc_s, 'nc_net': nc_l-nc_s,
                                 'dl_l': dl_l, 'dl_s': dl_s, 'dl_net': dl_l-dl_s,
                                 'am_l': am_l, 'am_s': am_s, 'am_net': am_l-am_s,
                                 'ret_net': None})
        except: pass

all_rows.sort(key=lambda x: x['date'])

# ── 2. COT Index 3 años ───────────────────────────────────────────────────
for i, r in enumerate(all_rows):
    hist = [x['nc_net'] for x in all_rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = round((r['nc_net'] - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0
    r['hist_min'] = mn
    r['hist_max'] = mx

# ── 3. Retail desde CFTC ─────────────────────────────────────────────────
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
            for r2 in all_rows:
                if r2['date'] == d:
                    r2['ret_net'] = nr_l - nr_s
                    r2['ret_l']   = nr_l
                    r2['ret_s']   = nr_s
        except: pass
    print('✅ Retail (Non-Reportable) OK')
except Exception as e:
    print(f'⚠️ Retail no disponible: {e}')

# ── 4. recent_weeks ───────────────────────────────────────────────────────
def fmt_date(d):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try:
            return datetime.strptime(d, fmt).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d

recent = all_rows[-12:]
weeks_js = []
for r in reversed(recent):
    weeks_js.append({
        'date':       r['date'],
        'label':      fmt_date(r['date']),
        # Non-Commercial (Leveraged Money = Hedge Funds)
        'nc_long':    r['nc_l'],
        'nc_short':   r['nc_s'],
        'nc_net':     r['nc_net'],
        # Commercial (Dealers / Banks)
        'com_long':   r['dl_l'],
        'com_short':  r['dl_s'],
        'com_net':    r['dl_net'],
        # Institutional (Asset Managers)
        'am_long':    r['am_l'],
        'am_short':   r['am_s'],
        'am_net':     r['am_net'],
        # Retail
        'ret_long':   r.get('ret_l', 0),
        'ret_short':  r.get('ret_s', 0),
        'ret_net':    r.get('ret_net'),
        # COT Index
        'cot_index':  r['ci'],
    })

last = all_rows[-1]
updated = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
ci_signal = ('BEARISH' if last['ci'] < 25 else 'MUY BEARISH' if last['ci'] < 10 else
             'BEARISH'  if last['ci'] < 45 else 'NEUTRAL' if last['ci'] < 60 else
             'BULLISH'  if last['ci'] < 80 else 'MUY BULLISH')

# ── 5. Escribir cot_data.js ───────────────────────────────────────────────
cot_js = f"""// ════════════════════════════════════════════════
// NQ COT Data — CFTC Traders in Financial Futures
// Generated: {updated}
// Ultimo reporte: {last['date']}  |  COT Index: {last['ci']:.1f}%
// ════════════════════════════════════════════════
window.NQ_COT = {{
  generated:   "{updated}",
  last_date:   "{last['date']}",
  last_label:  "{fmt_date(last['date'])}",
  nc_net:      {last['nc_net']},
  com_net:     {last['dl_net']},
  am_net:      {last['am_net']},
  ret_net:     {last.get('ret_net') or 0},
  cot_index:   {last['ci']},
  hist_min:    {last['hist_min']},
  hist_max:    {last['hist_max']},
  signal:      "{ci_signal}",
  recent_weeks: {json.dumps(weeks_js, ensure_ascii=False, indent=2)}
}};
"""

with open(JS_OUT, 'w', encoding='utf-8') as f:
    f.write(cot_js)
print(f'✅ {JS_OUT} generado ({len(cot_js):,} bytes, {len(weeks_js)} semanas)')

# ── 6. Asegurar que cot_data.js esté incluido en index.html ──────────────
with open(HTML_PATH, 'r', encoding='utf-8') as f:
    html = f.read()

SCRIPT_TAG = '<script src="cot_data.js"></script>'
if SCRIPT_TAG not in html:
    # Insertar justo antes de agent_live_data_v2.js
    target = '<script src="agent_live_data_v2.js"'
    if target in html:
        html = html.replace(target, SCRIPT_TAG + '\n  ' + target)
    else:
        html = html.replace('</head>', f'  {SCRIPT_TAG}\n</head>')
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ <script src="cot_data.js"> añadido a index.html')
else:
    print('✅ cot_data.js ya incluido en index.html')

# ── 7. Resultado ─────────────────────────────────────────────────────────
print(f'\n📊 COT Data:')
print(f'   Fecha:          {last["date"]}')
print(f'   NC (HF) Net:    {last["nc_net"]:+,} contratos  (L:{last["nc_l"]:,} / S:{last["nc_s"]:,})')
print(f'   COM (Dealer):   {last["dl_net"]:+,} contratos  (L:{last["dl_l"]:,} / S:{last["dl_s"]:,})')
print(f'   AM (Inst):      {last["am_net"]:+,} contratos  (L:{last["am_l"]:,} / S:{last["am_s"]:,})')
if last.get('ret_net'): print(f'   Retail Net:     {last["ret_net"]:+,} contratos')
print(f'   COT Index:      {last["ci"]:.1f}% → {ci_signal}')
