import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🚀 GENERANDO AUDITORÍA FORENSE AVANZADA: NOTICIAS + DIRECCIÓN")
print("="*80)

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

# Simulation of news and institutional bias
cot_history = {
    '2026-03-03': 27.3, '2026-02-24': 35.0, '2026-02-17': 45.0, '2026-02-10': 40.0,
    '2026-02-03': 30.0, '2026-01-27': 50.0, '2026-01-20': 55.0, '2026-01-13': 60.0
}
def get_cot(d):
    for ds, val in sorted(cot_history.items(), reverse=True):
        if datetime.strptime(ds, '%Y-%m-%d').date() <= d: return val
    return 50.0

def get_news(d):
    # Lógica de Carpeta Roja
    wom = (d.day - 1) // 7 + 1
    wd = d.weekday() # 4=Fri, 2=Wed, 1=Tue
    if wom == 1 and wd == 4: return "🔴 NFP"
    if wom == 2 and wd in [1, 2]: return "🔴 CPI"
    if wom == 3 and wd == 2: return "🔴 FOMC"
    if wom == 4 and wd == 3: return "🔴 GDP"
    return "⚪ -"

def get_direction_icon(perf, close, open_px):
    if "ALC" in perf or (close > open_px and "MEGÁFONO" not in perf): return "⬆️"
    if "BAJ" in perf or (close < open_px and "MEGÁFONO" not in perf): return "⬇️"
    if "MEGÁFONO" in perf: return "↕️"
    return "↔️"

raw['date'] = raw.index.date
raw['hour'] = raw.index.hour
dates = sorted(raw['date'].unique())

master_data = []
for d in dates:
    day_nq = raw[raw['date'] == d]
    day_vxn = vxn[vxn.index.date == d]
    if day_nq.empty or day_vxn.empty: continue
    
    madr = day_nq[day_nq['hour'] < 9]
    ny = day_nq[(day_nq['hour'] >= 9) & (day_nq['hour'] < 16)]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_open = float(ny.iloc[0]['Open'])
    ny_close = float(ny.iloc[-1]['Close'])
    
    r_hi = ny_hi > pre_hi + 5
    r_lo = ny_lo < pre_lo - 5
    
    if r_hi and r_lo: perf = "MEGÁFONO"
    elif r_hi: perf = "EXPAN_ALC" if ny_close > pre_hi else "TRAMPA_BULL"
    elif r_lo: perf = "EXPAN_BAJ" if ny_close < pre_lo else "TRAMPA_BEAR"
    else: perf = "RANGO"

    vxn_val = round(float(day_vxn.iloc[0]['Open']), 1)
    cot_val = get_cot(d)
    wom = (d.day - 1) // 7 + 1
    news = get_news(d)
    dir_icon = get_direction_icon(perf, ny_close, ny_open)
    
    master_data.append({
        'Fecha': d.strftime('%Y-%m-%d'),
        'Día': d.strftime('%a'),
        'Sem': wom,
        'VIX': vxn_val,
        'COT': cot_val,
        'Noticia': news,
        'Dir': dir_icon,
        'Perfil': perf
    })

df = pd.DataFrame(master_data)

# Actualizar el MD (para referencia)
md_out = "# 📅 AUDITORÍA FORENSE: NOTICIAS Y DIRECCIÓN\n\n"
for w in [1, 2, 3, 4]:
    md_out += f"## SEMANA {w}\n"
    sub = df[df['Sem'] == w]
    md_out += "| Fecha | Día | VIX | COT | Noticia | Dir | Perfil |\n"
    md_out += "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n"
    for _, r in sub.iterrows():
        md_out += f"| {r['Fecha']} | {r['Día']} | {r['VIX']} | {r['COT']} | {r['Noticia']} | {r['Dir']} | {r['Perfil']} |\n"
    md_out += "\n"

with open("estudio_maestro_noticias.md", "w", encoding='utf-8') as f:
    f.write(md_out)

# Imprimir los últimos 15 días para copiar al HTML
print("\n📋 ÚLTIMOS DATOS PARA EL DASHBOARD (HTML):")
print("-" * 50)
last_days = df.tail(15)
for _, r in last_days.iterrows():
    print(f"| {r['Fecha']} | {r['Dir']} | {r['Noticia']} | {r['VIX']} | {r['Perfil']} |")
