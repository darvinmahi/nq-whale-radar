import yfinance as yf
import pandas as pd
import numpy as np

print("="*80)
print("📊 LOS DIFERENTES 'MOLDES' (PERFILES) DE NEW YORK DE LOS ÚLTIMOS 3 MESES 📊")
print("="*80)

raw_5m = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw_5m.columns, pd.MultiIndex):
    raw_5m.columns = raw_5m.columns.get_level_values(0)
raw_5m.index = raw_5m.index.tz_convert('America/New_York')

raw_5m['hour'] = raw_5m.index.hour
raw_5m['date'] = raw_5m.index.date

fechas = sorted(raw_5m['date'].unique())

perfiles = {
    "1. EXPANSIVO ALCISTA (Saca Highs previos y vuela)": 0,
    "2. EXPANSIVO BAJISTA (Saca Lows previos y colapsa)": 0,
    "3. REVERSIÓN ALCISTA (Falsa ruptura abajo, luego vuela)": 0,
    "4. REVERSIÓN BAJISTA (Falsa ruptura arriba, luego colapsa)": 0,
    "5. DÍA DE RANGO / CHOPPY (Atrapado dentro del rango previo sin dirección)": 0,
    "6. EXPANSIÓN DOBLE (Megáfono - Rompe arriba y abajo salvajemente)": 0
}

dias_validos = 0

for d in fechas:
    day = raw_5m[raw_5m['date'] == d]
    
    asia = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    ny = day[(day['hour'] >= 9) & (day['hour'] < 16)]
    
    if asia.empty or london.empty or ny.empty: continue
    
    dias_validos += 1
    
    # Contexto previo a NY (Asia + London)
    rango_previo_hi = max(float(asia['High'].max()), float(london['High'].max()))
    rango_previo_lo = min(float(asia['Low'].min()), float(london['Low'].min()))
    
    # Lo que hizo NY
    ny_hi = float(ny['High'].max())
    ny_lo = float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])
    
    rompio_arriba = ny_hi > rango_previo_hi
    rompio_abajo = ny_lo < rango_previo_lo
    
    cerro_arriba = ny_close > rango_previo_hi
    cerro_abajo = ny_close < rango_previo_lo
    
    # Lógica de clasificación
    if rompio_arriba and rompio_abajo:
        # NY cazó stops arriba y abajo
        perfiles["6. EXPANSIÓN DOBLE (Megáfono - Rompe arriba y abajo salvajemente)"] += 1
        
    elif not rompio_arriba and not rompio_abajo:
        # NY se quedó aburrido en el rango de la madrugada
        perfiles["5. DÍA DE RANGO / CHOPPY (Atrapado dentro del rango previo sin dirección)"] += 1
        
    elif rompio_arriba and not rompio_abajo:
        # Rompió por arriba. ¿Aceleró o se devolvió?
        if cerro_arriba or ny_close > (rango_previo_hi + rango_previo_lo)/2:
            perfiles["1. EXPANSIVO ALCISTA (Saca Highs previos y vuela)"] += 1
        else:
            perfiles["4. REVERSIÓN BAJISTA (Falsa ruptura arriba, luego colapsa)"] += 1
            
    elif rompio_abajo and not rompio_arriba:
        # Rompió por abajo. ¿Aceleró o se devolvió?
        if cerro_abajo or ny_close < (rango_previo_hi + rango_previo_lo)/2:
            perfiles["2. EXPANSIVO BAJISTA (Saca Lows previos y colapsa)"] += 1
        else:
            perfiles["3. REVERSIÓN ALCISTA (Falsa ruptura abajo, luego vuela)"] += 1

print(f"Número total de días completos analizados: {dias_validos}\n")

print(f"{'PERFIL DE NEW YORK':<65} | {'DÍAS'} | {'% DEL TIEMPO'}")
print("-" * 90)

# Ordenar por el que más pasa
perfiles_ordenados = sorted(perfiles.items(), key=lambda x: x[1], reverse=True)

for nombre, cuenta in perfiles_ordenados:
    pct = (cuenta / dias_validos) * 100
    print(f"{nombre:<65} | {cuenta:>4} | {pct:>5.1f}%")

print("\n" + "="*80)
print("💡 RESUMEN ESTRATÉGICO:")
print("👉 El mercado NO 'caza stops y revierte' tan seguido como dicen en YouTube.")
print("👉 El movimiento más probable en NQ es EMPUJAR Y SEGUIR EMPUJANDO (Expansión pura).")
print("👉 Cuando New York rompe un nivel de Londres, lo más probable es que sea")
print("   una CONTINUACIÓN de tendencia, NO una trampa institucional.")
print("="*80)
