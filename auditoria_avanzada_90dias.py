import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🧠 AUDITORÍA ULTRA-DETALLADA: LOS 6 MOLDES REALES DEL NASDAQ")
print("   Refinando perfiles: P-shape, b-shape, D-shape y más")
print("="*80)

# 1. DOWNLOAD DATA
print("📡 Descargando datos (1h) para análisis de perfiles avanzados...")
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
    madrugada = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    if madrugada.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madrugada['High'].max()), float(madrugada['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_open = float(ny.iloc[0]['Open'])
    ny_close = float(ny.iloc[-1]['Close'])
    
    # POC Simplificado (Precio con más tiempo/volumen aproximado)
    poc = ny['Close'].median() 
    
    # 2. CLASIFICACIÓN AVANZADA (6 MOLDES)
    rompio_hi = ny_hi > pre_hi + 5
    rompio_lo = ny_lo < pre_lo - 5

    # 1. TRAMPAS (Reversión rápida)
    if rompio_hi and ny_close < (pre_hi + pre_lo)/2:
        perfil = "TRAMPA BULL (Saca y cae)"
    elif rompio_lo and ny_close > (pre_hi + pre_lo)/2:
        perfil = "TRAMPA BEAR (Saca y sube)"
        
    # 2. MEGÁFONO (Doble expansión)
    elif rompio_hi and rompio_lo:
        perfil = "MEGÁFONO (Neutral Day)"
        
    # 3. P-SHAPE (Subida fuerte y se queda arriba consolidando)
    elif rompio_hi and ny_close > pre_hi and poc > (ny_hi + ny_open)/2:
        perfil = "P-SHAPE (Short Covering)"
        
    # 4. b-SHAPE (Bajada fuerte y se queda abajo consolidando)
    elif rompio_lo and ny_close < pre_lo and poc < (ny_lo + ny_open)/2:
        perfil = "b-SHAPE (Long Liquidation)"
        
    # 5. TREND DAY (Expansión pura sin mucha consolidación)
    elif rompio_hi and ny_close > ny_hi - 30:
        perfil = "TREND DAY ALCISTA"
    elif rompio_lo and ny_close < ny_lo + 30:
        perfil = "TREND DAY BAJISTA"
        
    # 6. D-SHAPE (Rango o equilibrio total)
    else:
        perfil = "D-SHAPE (Equilibrio/Rango)"
        
    records.append({
        'Fecha': d,
        'Año': int(day['year'].iloc[0]),
        'Semana': int(day['week'].iloc[0]),
        'Perfil': perfil
    })

df = pd.DataFrame(records)
df['Semana_ID'] = df['Año'].astype(str) + "-W" + df['Semana'].astype(str)

print("\n📈 ESTADÍSTICAS DE LOS 6 MOLDES (90 DÍAS):")
print("-" * 50)
stats = df['Perfil'].value_counts(normalize=True) * 100
for p, pct in stats.items():
    count = df['Perfil'].value_counts()[p]
    print(f"{p:<30} : {pct:>5.1f}% ({count} días)")

print("\n" + "="*80)
print("💡 REVELACIÓN: EL NASDAQ ES MÁS COMPLEJO")
print("="*80)
print("Los perfiles P y b son claves: nos indican si las instituciones están")
print("atrapadas cubriendo posiciones o liquidando. No son simples expansiones.")
print("="*80)
