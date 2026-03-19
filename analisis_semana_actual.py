import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

print("="*60)
print("📊 ANÁLISIS DE LA SEMANA ACTUAL (9 - 13 MARZO 2026)")
print("="*60)

# 1. DOWNLOAD DATA (Last 7 days to cover the full week)
raw = yf.download("NQ=F", period="7d", interval="15m", progress=False)
if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')

raw['date'] = raw.index.date
raw['hour'] = raw.index.hour

# Filter specifically for March 9 to March 13
start_date = datetime(2026, 3, 9).date()
end_date = datetime(2026, 3, 13).date()
week_days = raw[(raw['date'] >= start_date) & (raw['date'] <= end_date)]

dates = sorted(week_days['date'].unique())
records = []

for d in dates:
    day = week_days[week_days['date'] == d]
    madrugada = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    
    if madrugada.empty or ny.empty: continue
    
    pre_hi = float(madrugada['High'].max())
    pre_lo = float(madrugada['Low'].min())
    ny_hi = float(ny['High'].max())
    ny_lo = float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])

    # Classification
    rompio_hi = ny_hi > pre_hi + 5 # 5 pts buffer
    rompio_lo = ny_lo < pre_lo - 5
    
    if rompio_hi and rompio_lo:
        perfil = "MEGÁFONO (Doble Expansión)"
    elif rompio_hi:
        perfil = "EXPANSIÓN ALCISTA" if ny_close > pre_hi else "TRAMPA BULL (Saca Hi y Revierte)"
    elif rompio_lo:
        perfil = "EXPANSIÓN BAJISTA" if ny_close < pre_lo else "TRAMPA BEAR (Saca Lo y Revierte)"
    else:
        perfil = "RANGO (Consolidación)"
        
    records.append({'Fecha': d, 'Perfil': perfil})

df = pd.DataFrame(records)

# 2. CALCULAR PORCENTAJES
print("\n📅 RESUMEN DIARIO:")
print("-" * 30)
for _, row in df.iterrows():
    day_name = row['Fecha'].strftime('%A')
    print(f"{day_name:<10} | {row['Perfil']}")

print("\n📈 ESTADÍSTICAS DE LA SEMANA (en %):")
print("-" * 30)
stats = df['Perfil'].value_counts(normalize=True) * 100
for perfil, pct in stats.items():
    count = df['Perfil'].value_counts()[perfil]
    print(f"{perfil:<30} : {pct:>5.0f}% ({count} veces)")

print("\n" + "="*60)
