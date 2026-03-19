import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🏁 CONSOLIDACIÓN FINAL: CUADRO COMPARATIVO DIA POR DIA (90 DÍAS)")
print("="*80)

# 1. DOWNLOAD DATA (90 days)
raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')

raw_vxn = yf.download("^VXN", period="90d", interval="1h", progress=False)
if isinstance(raw_vxn.columns, pd.MultiIndex): raw_vxn.columns = raw_vxn.columns.get_level_values(0)
if raw_vxn.index.tz is None: raw_vxn.index = raw_vxn.index.tz_localize('UTC')
raw_vxn.index = raw_vxn.index.tz_convert('America/New_York')

raw['date'] = raw.index.date
raw['hour'] = raw.index.hour

def get_week_of_month(d):
    first_day = d.replace(day=1)
    adjusted_dom = d.day + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1

dates = sorted(raw['date'].unique())
records = []

for d in dates:
    day = raw[raw['date'] == d]
    vxn_day = raw_vxn[raw_vxn.index.date == d]
    if day.empty or vxn_day.empty: continue
    
    madr = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])
    vxn_open = float(vxn_day.iloc[0]['Open'])

    # Classification
    r_hi = ny_hi > pre_hi
    r_lo = ny_lo < pre_lo
    
    if r_hi and r_lo: perf = "MEGÁFONO"
    elif r_hi: perf = "EXP_ALCISTA" if ny_close > pre_hi else "TRAMPA_BULL"
    elif r_lo: perf = "EXP_BAJISTA" if ny_close < pre_lo else "TRAMPA_BEAR"
    else: perf = "RANGO"

    records.append({
        'Fecha': d.strftime('%Y-%m-%d'),
        'Día': d.strftime('%A'),
        'Sem_Mes': get_week_of_month(d),
        'Perfil': perf,
        'VXN': round(vxn_open, 1)
    })

df = pd.DataFrame(records)

# 2. OUTPUT AS MARKDOWN MANUALLY
header = "| Fecha | Día | Sem_Mes | Perfil | VXN |"
sep = "| :--- | :--- | :--- | :--- | :--- |"
rows = []
for _, r in df.iterrows():
    rows.append(f"| {r['Fecha']} | {r['Día']} | {r['Sem_Mes']} | {r['Perfil']} | {r['VXN']} |")

# Repetition Summary
counts = df['Perfil'].value_counts()
pcts = df['Perfil'].value_counts(normalize=True) * 100
summary_header = "| Perfil | Veces | Porcentaje |"
summary_sep = "| :--- | :--- | :--- |"
summary_rows = []
for p in counts.index:
    summary_rows.append(f"| {p} | {counts[p]} | {pcts[p]:.1f}% |")

with open("backtest_comparativo_final.md", "w", encoding='utf-8') as f:
    f.write("# 🏁 CUADRO COMPARATIVO: BACKTESTING 90 DÍAS (NQ)\n\n")
    f.write("## 📝 RESUMEN DE REPETICIONES TOTALES\n\n")
    f.write(summary_header + "\n" + summary_sep + "\n" + "\n".join(summary_rows) + "\n\n")
    f.write("## 📅 DETALLE DÍA POR DÍA\n\n")
    f.write(header + "\n" + sep + "\n" + "\n".join(rows) + "\n")

print("\n✅ Archivo backtest_comparativo_final.md generado exitosamente.")
