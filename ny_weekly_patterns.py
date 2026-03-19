import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# 1. DOWNLOAD DATA (90 days of 1h to get the full 3 months range)
print("📡 Descargando 90 días de datos (1h) para análisis de perfiles...")
raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')

raw['date'] = raw.index.date
raw['hour'] = raw.index.hour
raw['week'] = raw.index.isocalendar().week
raw['year'] = raw.index.isocalendar().year

dates = sorted(raw['date'].unique())
records = []

for d in dates:
    day = raw[raw['date'] == d]
    if day.empty: continue
    
    # Sessions
    # Madrugada: 00:00 to 08:59 (Asia + London)
    madrugada = day[day['hour'] < 9]
    # NY: 09:00 to 16:00
    ny = day[day['hour'] >= 9]
    
    if madrugada.empty or ny.empty: continue
    
    pre_hi = float(madrugada['High'].max())
    pre_lo = float(madrugada['Low'].min())
    
    ny_hi = float(ny['High'].max())
    ny_lo = float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])

    # Classification
    rompio_hi = ny_hi > pre_hi
    rompio_lo = ny_lo < pre_lo
    
    # We use a threshold of 10 points to avoid tiny breaks (noise)
    if rompio_hi and rompio_lo:
        perfil = "MEGÁFONO"
    elif rompio_hi:
        if ny_close > pre_hi:
            perfil = "EXPANSIÓN_ALCISTA"
        else:
            perfil = "TRAMPA_BULL"
    elif rompio_lo:
        if ny_close < pre_lo:
            perfil = "EXPANSIÓN_BAJISTA"
        else:
            perfil = "TRAMPA_BEAR"
    else:
        perfil = "RANGO"
        
    records.append({
        'Fecha': d,
        'Año': int(day['year'].iloc[0]),
        'Semana': int(day['week'].iloc[0]),
        'Perfil': perfil
    })

df = pd.DataFrame(records)
df['Semana_ID'] = df['Año'].astype(str) + "-W" + df['Semana'].astype(str)

# Global stats
print("\n" + "="*50)
print("📊 RESUMEN GLOBAL DE PERFILES (90 DÍAS)")
print("="*50)
print(df['Perfil'].value_counts())

# Weekly repetitions
print("\n" + "="*50)
print("📅 REPETICIONES POR SEMANA")
print("="*50)
pivot = df.groupby(['Semana_ID', 'Perfil']).size().unstack(fill_value=0)
print(pivot)

# Save for drawing
df.to_csv("ny_patterns_3months.csv", index=False)
