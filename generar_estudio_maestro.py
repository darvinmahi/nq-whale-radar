import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("📚 GENERANDO ESTUDIO MAESTRO: DÍA POR DÍA, SEMANA POR SEMANA")
print("="*80)

# 1. DOWNLOAD DATA
def get_data():
    raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
    if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
    raw.index = raw.index.tz_convert('America/New_York')
    
    vxn = yf.download("^VXN", period="90d", interval="1h", progress=False)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    if vxn.index.tz is None: vxn.index = vxn.index.tz_localize('UTC')
    vxn.index = vxn.index.tz_convert('America/New_York')
    
    return raw, vxn

raw, vxn = get_data()

# 2. COT HISTORY (Simulado basado en agentes)
cot_history = {
    '2026-03-03': 27.3, '2026-02-24': 35.0, '2026-02-17': 45.0, '2026-02-10': 40.0,
    '2026-02-03': 30.0, '2026-01-27': 50.0, '2026-01-20': 55.0, '2026-01-13': 60.0,
    '2026-01-06': 65.0, '2025-12-30': 70.0, '2025-12-23': 75.0, '2025-12-16': 80.0
}
def get_cot(d):
    for ds, val in sorted(cot_history.items(), reverse=True):
        if datetime.strptime(ds, '%Y-%m-%d').date() <= d: return val
    return 50.0

# 3. PROCESAMIENTO
raw['date'] = raw.index.date
raw['hour'] = raw.index.hour
dates = sorted(raw['date'].unique())

def get_week_of_month(d):
    day = d.day
    if day <= 7: return 1
    elif day <= 14: return 2
    elif day <= 21: return 3
    else: return 4

def classify(madr, ny):
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])
    r_hi = ny_hi > pre_hi + 5
    r_lo = ny_lo < pre_lo - 5
    if r_hi and r_lo: return "MEGÁFONO"
    if r_hi: return "EXPAN_ALC" if ny_close > pre_hi else "TRAMPA_BULL"
    if r_lo: return "EXPAN_BAJ" if ny_close < pre_lo else "TRAMPA_BEAR"
    return "RANGO"

master_data = []
for d in dates:
    day_nq = raw[raw['date'] == d]
    day_vxn = vxn[vxn.index.date == d]
    if day_nq.empty or day_vxn.empty: continue
    
    madr = day_nq[day_nq['hour'] < 9]
    ny = day_nq[(day_nq['hour'] >= 9) & (day_nq['hour'] < 16)]
    if madr.empty or ny.empty: continue
    
    perf = classify(madr, ny)
    vxn_val = round(float(day_vxn.iloc[0]['Open']), 1)
    cot_val = get_cot(d)
    wom = get_week_of_month(d)
    
    master_data.append({
        'Fecha': d.strftime('%Y-%m-%d'),
        'Día': d.strftime('%a'),
        'Sem': wom,
        'VIX': vxn_val,
        'COT': cot_val,
        'Perfil': perf
    })

# 4. GENERAR MARKDOWN POR SEMANAS
df = pd.DataFrame(master_data)
md_output = "# 📅 ESTUDIO DETALLADO: DÍA POR DÍA (90 DÍAS)\n\n"

for w in [1, 2, 3, 4]:
    md_output += f"## 🗓️ SEMANA {w}\n"
    sub = df[df['Sem'] == w]
    if sub.empty:
        md_output += "Sin datos para esta semana.\n\n"
        continue
    
    md_output += "| Fecha | Día | VIX | COT | Perfil Resultante |\n"
    md_output += "| :--- | :--- | :--- | :--- | :--- |\n"
    for _, r in sub.iterrows():
        color = "🔴" if r['Perfil'] == "MEGÁFONO" else ("🔵" if "EXPAN" in r['Perfil'] else "🟡")
        md_output += f"| {r['Fecha']} | {r['Día']} | {r['VIX']} | {r['COT']} | {color} {r['Perfil']} |\n"
    md_output += "\n"

with open("estudio_maestro_tabla.md", "w", encoding='utf-8') as f:
    f.write(md_output)

print("✅ Archivo estudio_maestro_tabla.md generado.")
