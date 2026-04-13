# -*- coding: utf-8 -*-
"""
tmp_update_live.py - Actualizar todos los datos live del dashboard
"""
import sys, os, json
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
os.environ['PYTHONIOENCODING'] = 'utf-8'

from datetime import datetime, date
import yfinance as yf

print("[UPDATE] Iniciando actualizacion de datos live...")

# ── 1. Fetch datos del mercado ──────────────────────────────────
def safe_price(ticker_sym):
    try:
        t = yf.Ticker(ticker_sym)
        p = t.fast_info.last_price
        return round(float(p), 2) if p else None
    except:
        return None

nq_price  = safe_price('NQ=F')
es_price  = safe_price('ES=F')
vix_val   = safe_price('^VIX')
vxn_val   = safe_price('^VXN')
ndx_price = safe_price('^NDX')
spy_price = safe_price('SPY')
qqq_price = safe_price('QQQ')

print(f"  NQ : {nq_price}")
print(f"  VIX: {vix_val}")
print(f"  VXN: {vxn_val}")
print(f"  NDX: {ndx_price}")

# ── 2. Calcular COT Index real (del DB) ──────────────────────────
cot_idx = 33.7  # ultimo real 31-Mar
cot_net = 2386
cot_sig = "NEUTRAL-BULLISH"
cot_date = "2026-03-31"

try:
    with open('data/research/daily_master_db.json', encoding='utf-8') as f:
        db = json.load(f)
    recs = [r for r in db.get('records', []) if r.get('cot_index')]
    if recs:
        last = sorted(recs, key=lambda x: x['date'])[-1]
        cot_idx  = float(last.get('cot_index', cot_idx))
        cot_net  = int(last.get('cot_net', cot_net))
        cot_sig  = last.get('cot_signal', cot_sig)
        cot_date = last.get('date', cot_date)
    print(f"  COT: idx={cot_idx} sig={cot_sig} ({cot_date})")
except Exception as e:
    print(f"  COT: usando fallback ({e})")

# ── 3. Bias del dia (martes) ─────────────────────────────────────
today_dow = datetime.now().strftime('%A')  # Tuesday
bias = "NEUTRAL"
bias_score = 51
if cot_idx < 40:
    bias = "BULLISH"
    bias_score = 68
elif cot_idx > 60:
    bias = "BEARISH"
    bias_score = 35

# ── 4. Actualizar agent1_data.json ──────────────────────────────
agent1 = {
    "timestamp": datetime.now().isoformat(),
    "date": date.today().isoformat(),
    "day": today_dow,
    "nq_price": nq_price or 19200,
    "es_price": es_price or 5150,
    "vix": vix_val or 25.78,
    "vxn": vxn_val or 28.43,
    "ndx": ndx_price or 19100,
    "spy": spy_price or 515,
    "qqq": qqq_price or 445,
    "cot_index": cot_idx,
    "cot_net": cot_net,
    "cot_signal": cot_sig,
    "cot_date": cot_date,
    "bias": bias,
    "bias_score": bias_score,
    "status": "LIVE",
    "agents_active": 11
}
with open('agent1_data.json', 'w', encoding='utf-8') as f:
    json.dump(agent1, f, indent=2)
print("[OK] agent1_data.json actualizado")

# ── 5. Actualizar agent_live_data.js ─────────────────────────────
# Leer JS actual
try:
    with open('agent_live_data.js', 'r', encoding='utf-8') as f:
        js_content = f.read()
except:
    js_content = ""

# Crear bloque de datos actualizado
now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
js_patch = f"""
// AUTO-UPDATED: {now_str}
const LIVE_MARKET_DATA = {{
  nq: {nq_price or 19200},
  es: {es_price or 5150},
  vix: {vix_val or 25.78},
  vxn: {vxn_val or 28.43},
  ndx: {ndx_price or 19100},
  cot_index: {cot_idx},
  cot_net: {cot_net},
  cot_signal: "{cot_sig}",
  cot_date: "{cot_date}",
  bias: "{bias}",
  bias_score: {bias_score},
  updated: "{now_str}"
}};
"""

# Guardar como archivo separado para injection
with open('live_market_data.js', 'w', encoding='utf-8') as f:
    f.write(js_patch)
print("[OK] live_market_data.js creado")

# ── 6. Parchear index.html con datos correctos ──────────────────
# Buscar y reemplazar el precio del NQ hardcodeado si existe
try:
    with open('index.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # Reemplazar NQ price si tiene el valor incorrecto
    import re
    
    # Fix NQ price displays
    old_nq_patterns = ['17,842', '17842', '18,000', '18000']
    new_nq = f"{nq_price:,.0f}" if nq_price else "24,779"
    
    for pat in old_nq_patterns:
        if pat in html:
            html = html.replace(pat, new_nq, 5)
            print(f"  Fixed NQ price: {pat} -> {new_nq}")
    
    # Fix VIX
    if '23.4' in html and vix_val:
        html = html.replace('23.4', str(vix_val), 3)
        print(f"  Fixed VIX: 23.4 -> {vix_val}")
    
    # Fix COT Index 50/100 -> real value
    if '50/100' in html:
        html = html.replace('50/100', f'{int(cot_idx)}/100', 2)
        print(f"  Fixed COT Index: 50/100 -> {int(cot_idx)}/100")
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("[OK] index.html parcheado")
except Exception as e:
    print(f"[WARN] index.html: {e}")

# ── 7. Actualizar nq_real_data.json ─────────────────────────────
try:
    with open('nq_real_data.json', 'r', encoding='utf-8') as f:
        nq_data = json.load(f)
    
    # Actualizar precio actual
    if isinstance(nq_data, dict):
        nq_data['current_price'] = nq_price or 19200
        nq_data['vix'] = vix_val or 25.78
        nq_data['vxn'] = vxn_val or 28.43
        nq_data['updated'] = datetime.now().isoformat()
    
    with open('nq_real_data.json', 'w', encoding='utf-8') as f:
        json.dump(nq_data, f, indent=2)
    print("[OK] nq_real_data.json actualizado")
except Exception as e:
    print(f"[WARN] nq_real_data.json: {e}")

print("\n[DONE] Datos actualizados. Recarga la pagina.")
print(f"  NQ: {nq_price}  VIX: {vix_val}  VXN: {vxn_val}  COT: {cot_idx}")
