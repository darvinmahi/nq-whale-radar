"""
generate_cot_update.py
Lee el CSV local + descarga datos de CFTC, actualiza el bloque COT en
agent_live_data.js con la estructura completa, y añade el JS que inyecta
las barras de la Trifecta en el HTML.
"""
import csv, json, re, requests, zipfile, io, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
JS_PATH   = 'agent_live_data.js'

# ── 1. Cargar datos del CSV (Lev_Money + Dealer + Asset Mgr) ──────────────
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
                all_rows.append({'date': d, 'nc_l': nc_l, 'nc_s': nc_s, 'nc_net': nc_l - nc_s,
                                 'com_l': dl_l, 'com_s': dl_s, 'com_net': dl_l - dl_s,
                                 'am_l': am_l, 'am_s': am_s, 'am_net': am_l - am_s,
                                 'ret_net': None})
        except: pass

all_rows.sort(key=lambda x: x['date'])

# ── 2. COT Index 3 años (156 semanas) ────────────────────────────────────
for i, r in enumerate(all_rows):
    hist = [x['nc_net'] for x in all_rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = round((r['nc_net'] - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0
    r['hist_min'] = mn
    r['hist_max'] = mx

# ── 3. Intentar bajar Non-Reportable desde CFTC ───────────────────────────
try:
    resp = requests.get(
        'https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=60)
    zf   = zipfile.ZipFile(io.BytesIO(resp.content))
    fobj = zf.open(zf.namelist()[0])
    reader = csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace'))
    for row in reader:
        if 'NASDAQ-100 Consolidated' not in row.get('Market_and_Exchange_Names', ''):
            continue
        d = row.get('Report_Date_as_YYYY-MM-DD', '').strip()
        try:
            nr_l = int(row.get('NonRept_Positions_Long_All') or 0)
            nr_s = int(row.get('NonRept_Positions_Short_All') or 0)
            for r2 in all_rows:
                if r2['date'] == d:
                    r2['ret_net'] = nr_l - nr_s
        except: pass
    print('✅ Non-Reportable (Retail) OK')
except Exception as e:
    print(f'⚠️ Non-Reportable no disponible: {e}')

# ── 4. Generar la estructura recent_weeks (últimas 12 semanas) ────────────
def fmt_date(d):
    # "2026-03-24" → "24 Mar 2026"
    try:
        return datetime.strptime(d, '%Y-%m-%d').strftime('%-d %b %Y')
    except:
        try:
            return datetime.strptime(d, '%Y-%m-%d').strftime('%d %b %Y').lstrip('0')
        except:
            return d

recent = all_rows[-12:]
recent_weeks_js = []
for r in reversed(recent):
    entry = {
        'date':      r['date'],
        'date_label': fmt_date(r['date']),
        'nc_long':   r['nc_l'],
        'nc_short':  r['nc_s'],
        'nc_net':    r['nc_net'],
        'com_long':  r['com_l'],
        'com_short': r['com_s'],
        'com_net':   r['com_net'],
        'am_long':   r['am_l'],
        'am_short':  r['am_s'],
        'am_net':    r['am_net'],
        'ret_net':   r['ret_net'],
        'cot_index': r['ci'],
    }
    recent_weeks_js.append(entry)

last = all_rows[-1]
print(f'\nLast week: {last["date"]} | NC Net: {last["nc_net"]:+,} | COT Index: {last["ci"]:.1f}%')

# ── 5. Construir el bloque COT para NQ_LIVE ───────────────────────────────
cot_block = f"""  COT: {{
    net:            {last['nc_net']},
    commercial_net: {last['com_net']},
    retail_net:     {last['ret_net'] or 0},
    index:          {last['ci']},
    signal:         "{'BEARISH' if last['ci'] < 45 else 'BULLISH' if last['ci'] > 60 else 'NEUTRAL'}",
    razonamiento:   "Non-Commercial (Hedge Funds) Net: {last['nc_net']:+,} contratos. COT Index {last['ci']:.1f}% ({'BEARISH - posiciones en zona baja' if last['ci'] < 45 else 'NEUTRAL' if last['ci'] < 60 else 'BULLISH'}). Último reporte CFTC: {last['date']}",
    last_date:      "{last['date']}",
    hist_min:       {last['hist_min']},
    hist_max:       {last['hist_max']},
    consecutive_weeks: {sum(1 for r in all_rows[-4:] if r['nc_net'] < all_rows[all_rows.index(r)-1]['nc_net'] if all_rows.index(r) > 0)},
    recent_weeks: {json.dumps(recent_weeks_js, ensure_ascii=False, indent=6)}
  }}"""

# ── 6. Actualizar agent_live_data.js — solo el bloque COT ────────────────
with open(JS_PATH, 'r', encoding='utf-8') as f:
    js_content = f.read()

# Reemplazar el bloque COT existente
cot_pattern = re.compile(r'COT:\s*\{[^}]*\}', re.DOTALL)
match = cot_pattern.search(js_content)
if match:
    js_content = js_content[:match.start()] + cot_block + js_content[match.end():]
    print('✅ Bloque COT reemplazado en agent_live_data.js')
else:
    print('⚠️ No se encontró el bloque COT en agent_live_data.js')

# ── 7. Añadir función Trifecta si no existe ───────────────────────────────
TRIFECTA_MARKER = '// ─── TRIFECTA COT BARS ───'
if TRIFECTA_MARKER not in js_content:
    trifecta_js = f"""
{TRIFECTA_MARKER}
(function injectTrifecta() {{
  const COT = window.NQ_LIVE && window.NQ_LIVE.COT;
  if (!COT || !COT.recent_weeks || COT.recent_weeks.length === 0) return;

  const weeks  = COT.recent_weeks.slice(0, 4);   // ← ultimas 4
  const maxNC  = Math.max(...weeks.map(w => Math.max(w.nc_long, w.nc_short, 1)));
  const maxCOM = Math.max(...weeks.map(w => Math.max(w.com_long, w.com_short, 1)));

  function bar(label, long, short, max, isLive) {{
    const lPct = Math.max(4, long  / max * 100).toFixed(1);
    const sPct = Math.max(4, short / max * 100).toFixed(1);
    const lk   = (long  / 1000).toFixed(1);
    const sk   = (short / 1000).toFixed(1);
    const tag  = isLive ? '<span style="font-size:8px;background:#0ff2;color:#00f2ff;padding:1px 5px;border-radius:4px;margin-left:4px">LIVE</span>' : '';
    return `<div style="font-size:9px;color:#4a5a7a;margin-bottom:8px">
      <div style="display:flex;align-items:center;margin-bottom:4px">
        <span style="color:#94a3b8;font-size:9px;min-width:90px">${{label}}</span>${{tag}}
      </div>
      <div style="display:flex;gap:4px;align-items:center;margin-bottom:2px">
        <span style="width:12px;font-size:8px;color:#00ff88">L</span>
        <div style="flex:1;height:8px;background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden">
          <div style="width:${{lPct}}%;height:100%;background:#00ff88;border-radius:4px"></div>
        </div>
        <span style="font-size:9px;color:#00ff88;min-width:36px;text-align:right">${{lk}}k</span>
      </div>
      <div style="display:flex;gap:4px;align-items:center">
        <span style="width:12px;font-size:8px;color:#ff3355">S</span>
        <div style="flex:1;height:8px;background:rgba(255,255,255,.04);border-radius:4px;overflow:hidden">
          <div style="width:${{sPct}}%;height:100%;background:#ff3355;border-radius:4px"></div>
        </div>
        <span style="font-size:9px;color:#ff3355;min-width:36px;text-align:right">${{sk}}k</span>
      </div>
    </div>`;
  }}

  const specsEl = document.getElementById('cot-specs-bars');
  const banksEl = document.getElementById('cot-comm-bars');
  const retailEl= document.getElementById('cot-retail-bars');
  const tableEl = document.getElementById('cot-table-body');
  const heroEl  = document.getElementById('cot-net-val');
  const dateEl  = document.getElementById('cot-date-label');
  const signalEl= document.getElementById('cot-signal-label');
  const pinEl   = document.getElementById('cot-pin');
  const heroIdx = document.getElementById('hero-cot-index');

  if (specsEl) specsEl.innerHTML = weeks.map((w, i) => bar(w.date_label, w.nc_long, w.nc_short, maxNC, i===0)).join('');
  if (banksEl) banksEl.innerHTML = weeks.map((w, i) => bar(w.date_label, w.com_long, w.com_short, maxCOM, i===0)).join('');
  if (retailEl && weeks[0].ret_net !== null) {{
    retailEl.innerHTML = weeks.map(w => {{
      const n = w.ret_net || 0;
      const c = n > 0 ? '#00ff88' : '#ff3355';
      return `<div style="font-size:9px;color:#94a3b8;margin-bottom:6px">
        <div>${{w.date_label}}</div>
        <div style="font-size:16px;font-weight:700;color:${{c}}">${{n > 0 ? '+' : ''}}${{(n/1000).toFixed(1)}}k</div>
      </div>`;
    }}).join('');
  }}

  if (tableEl) {{
    tableEl.innerHTML = weeks.map((w, i) => {{
      const ncN  = w.nc_net  >= 0 ? '+' + (w.nc_net/1000).toFixed(1)+'k' : (w.nc_net/1000).toFixed(1)+'k';
      const comN = w.com_net >= 0 ? '+' + (w.com_net/1000).toFixed(1)+'k' : (w.com_net/1000).toFixed(1)+'k';
      const retN = w.ret_net != null ? ((w.ret_net>=0?'+':'')+( w.ret_net/1000).toFixed(1)+'k') : '—';
      const bg   = i === 0 ? 'background:rgba(0,242,255,.04)' : '';
      const dot  = i === 0 ? '<span style="color:#00f2ff;font-size:10px">●</span> ' : '';
      return `<tr style="${{bg}}">
        <td>${{dot}}${{w.date_label}}</td>
        <td class="r" style="color:${{w.nc_net>=0?'#00ff88':'#ff3355'}};font-weight:700">${{ncN}}</td>
        <td class="r" style="color:${{w.com_net>=0?'#00ff88':'#ff3355'}}">${{comN}}</td>
        <td class="r" style="color:#94a3b8">${{retN}}</td>
        <td class="r" style="color:#4a5a7a">—</td>
      </tr>`;
    }}).join('');
  }}

  const first = weeks[0];
  const ci    = first.cot_index;
  const ciC   = ci > 60 ? '#00ff88' : ci < 40 ? '#ff3355' : '#ffd60a';
  if (heroEl)  heroEl.innerText = (first.nc_net >= 0 ? '+' : '') + (first.nc_net/1000).toFixed(1) + 'k';
  if (dateEl)  dateEl.innerText = first.date_label + ' · CFTC';
  if (heroIdx) {{ heroIdx.innerText = ci.toFixed(1) + '%'; heroIdx.style.color = ciC; }}
  if (signalEl) {{
    const sig = ci < 25 ? 'NC MUY BAJISTA · BEARISH' : ci < 45 ? 'NC BAJISTA · BEARISH' : ci < 60 ? 'NEUTRAL' : ci < 80 ? 'NC ALCISTA · BULLISH' : 'NC EXTREMO LARGO · BULLISH';
    signalEl.innerText = sig;
    signalEl.style.color = ciC;
  }}
  if (pinEl) pinEl.style.left = Math.max(1, Math.min(99, ci)) + '%';

  // Actualizar metros min/max
  const minEl = document.querySelector('.text-risk-red');
  const maxEl = document.querySelector('.text-emerald-400');
  if (minEl) minEl.innerText = '🔴 MÍN: ' + (COT.hist_min/1000).toFixed(0) + 'k';
  if (maxEl) maxEl.innerText = '🟢 MÁX: ' + (COT.hist_max/1000).toFixed(0) + 'k';

  console.log('[NQ COT Trifecta] Barras actualizadas ✅ COT Index:', ci);
}})();
"""
    # Insert before closing })(); of the inject IIFE
    inject_end = js_content.rfind(  "console.log(\"[NQ Engine] Visuals Updated successfully.\");")
    if inject_end > 0:
        end_pos = js_content.find('\n', inject_end)
        js_content = js_content[:end_pos+1] + trifecta_js + js_content[end_pos+1:]
    else:
        js_content += trifecta_js
    print('✅ Función Trifecta añadida a agent_live_data.js')
else:
    # Actualizar timestamp dentro del Trifecta existente
    print('✅ Función Trifecta ya existe')

# ── 8. Guardar ───────────────────────────────────────────────────────────
with open(JS_PATH, 'w', encoding='utf-8') as f:
    f.write(js_content)

print(f'\n✅ agent_live_data.js actualizado.')
print(f'   Fecha: {last["date"]}  |  NC Net: {last["nc_net"]:+,}  |  COT Index: {last["ci"]:.1f}%')
print(f'   Semanas en historial: {len(recent_weeks_js)}')
