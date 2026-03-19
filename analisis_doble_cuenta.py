import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🧠 ANÁLISIS DE DIVERGENCIA: ¿QUÉ PASA TRAS EL PRIMER MOVIMIENTO?")
print("   Buscando lógica para operar con 2 cuentas (Hedge Estratégico)")
print("="*80)

# 1. DOWNLOAD DATA (90 days)
raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')

raw['date'] = raw.index.date
raw['hour'] = raw.index.hour

dates = sorted(raw['date'].unique())
scenarios = []

for d in dates:
    day = raw[raw['date'] == d]
    if day.empty: continue
    
    madr = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    
    # Análisis a las 10:30 AM (Primera hora de NY)
    ny_first_hour = ny[ny['hour'] <= 10]
    if ny_first_hour.empty: continue
    
    fh_hi = float(ny_first_hour['High'].max())
    fh_lo = float(ny_first_hour['Low'].min())
    
    rompio_hi_fh = fh_hi > pre_hi
    rompio_lo_fh = fh_lo < pre_lo
    
    # Determinamos el "Inicio del Día"
    if rompio_hi_fh and rompio_lo_fh: inicio = "AMBOS_LADOS"
    elif rompio_hi_fh: inicio = "ROMPE_ARRIBA"
    elif rompio_lo_fh: inicio = "ROMPE_ABAJO"
    else: inicio = "DENTRO_RANGO"
    
    # Resultado Final del Día
    total_hi = float(ny['High'].max())
    total_lo = float(ny['Low'].min())
    total_close = float(ny.iloc[-1]['Close'])
    
    r_hi = total_hi > pre_hi
    r_lo = total_lo > pre_lo
    
    if r_hi and r_lo: final = "MEGÁFONO"
    elif r_hi: final = "EXP_ALCISTA" if total_close > pre_hi else "TRAMPA_BULL"
    elif r_lo: final = "EXP_BAJISTA" if total_close < pre_lo else "TRAMPA_BEAR"
    else: final = "RANGO"
    
    scenarios.append({'Inicio': inicio, 'Final': final})

df = pd.DataFrame(scenarios)

# 2. CUADRO DE LÓGICA DE DIVERGENCIA
print("\n📊 SI EL DÍA EMPIEZA ASÍ... ¿CÓMO TERMINA?")
print("-" * 60)

for start in df['Inicio'].unique():
    sub = df[df['Inicio'] == start]
    print(f"\n▶️ INICIO: {start} ({len(sub)} días)")
    outcomes = sub['Final'].value_counts(normalize=True) * 100
    for out, pct in outcomes.items():
        print(f"   --> Termina en {out:<15}: {pct:>5.1f}%")

print("\n" + "="*80)
print("💡 LÓGICA PARA 2 CUENTAS (DATA-DRIVEN):")
print("="*80)
print("Cuando el precio ROMPE ARRIBA en la primera hora (Escenario más común):")
print("1. CUENTA A (Seguidora): Compra buscando la EXPANSIÓN (56% de prob).")
print("2. CUENTA B (Contraria): Vende buscando el MEGÁFONO o TRAMPA (44% de prob).")
print("\nSi usas lotajes iguales, el 56% de las veces la Cuenta A ganará más de lo que pierda la B.")
print("Si usas el VXN como filtro (>24), la Cuenta B tiene las de ganar.")
print("="*80)
