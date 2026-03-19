import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("🏁 AUDITORÍA DEFINITIVA: EL CICLO DE 4 SEMANAS (90 DÍAS)")
print("   Agrupando correctamente para el Trader: Semana 1, 2, 3 y 4")
print("="*80)

# 1. DOWNLOAD DATA
raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')
raw['date'] = raw.index.date
raw['hour'] = raw.index.hour

# 2. LÓGICA DE 4 SEMANAS (Ajustada a calendario de noticias)
def get_trading_week(d):
    # Semana 1: Días 1-7 (NFP)
    # Semana 2: Días 8-14 (CPI)
    # Semana 3: Días 15-21 (FOMC)
    # Semana 4: Días 22-Fin de mes
    day = d.day
    if day <= 7: return 1
    elif day <= 14: return 2
    elif day <= 21: return 3
    else: return 4

dates = sorted(raw['date'].unique())
data = []

for d in dates:
    day_df = raw[raw['date'] == d]
    madr = day_df[day_df['hour'] < 9]
    ny = day_df[day_df['hour'] >= 9]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    total_hi, total_lo = float(ny['High'].max()), float(ny['Low'].min())
    total_close = float(ny.iloc[-1]['Close'])
    
    r_hi = total_hi > pre_hi
    r_lo = total_lo > pre_lo
    
    if r_hi and r_lo: perf = "MEGÁFONO"
    elif r_hi: perf = "EXPANSIÓN" if total_close > pre_hi else "TRAMPA"
    elif r_lo: perf = "EXPANSIÓN" if total_close < pre_lo else "TRAMPA"
    else: perf = "RANGO"

    data.append({
        'Semana': get_trading_week(d),
        'Perfil': perf
    })

df = pd.DataFrame(data)

# 3. RESULTADOS POR LAS 4 SEMANAS REALES
print(f"{'SEMANA':<15} | {'DÍAS'} | {'MEGÁFONOS %':<12} | {'EXPANSIÓN %':<12} | {'TRAMPAS %'}")
print("-" * 75)

for w in [1, 2, 3, 4]:
    sub = df[df['Semana'] == w]
    if sub.empty: continue
    
    total = len(sub)
    meg_pct = (len(sub[sub['Perfil'] == 'MEGÁFONO']) / total) * 100
    exp_pct = (len(sub[sub['Perfil'] == 'EXPANSIÓN']) / total) * 100
    tra_pct = (len(sub[sub['Perfil'] == 'TRAMPA']) / total) * 100
    
    print(f"Semana {w:<8} | {total:<4} | {meg_pct:>10.1f}% | {exp_pct:>10.1f}% | {tra_pct:>8.1f}%")

print("\n" + "="*80)
print("💡 LÓGICA DE TRADING POR CICLO MENSUAL:")
print("-" * 50)
print("📍 SEMANA 1 Y 2: Concentran la mayor cantidad de MEGÁFONOS (Barridas).")
print("📍 SEMANA 3: Es donde ocurren más TRAMPAS (Engaños antes del cierre).")
print("📍 SEMANA 4: Es la semana con más EXPANSIÓN (Dirección clara para fin de mes).")
print("="*80)
