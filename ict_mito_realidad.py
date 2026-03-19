import yfinance as yf
import pandas as pd

print("="*70)
print("🔍 LA VERDAD SOBRE EL 'LONDON SWEEP' (ÚLTIMOS 60 DÍAS) 🔍")
print("="*70)

# Descargar últimos 60 días en velas de 5 minutos
raw = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')

raw['hour'] = raw.index.hour
raw['minute'] = raw.index.minute
raw['date'] = raw.index.date

fechas = sorted(raw['date'].unique())

total_dias = 0
total_sweeps_high = 0
total_sweeps_low = 0

ict_funciona_high = 0
ict_falla_high = 0

ict_funciona_low = 0
ict_falla_low = 0

sin_sweep = 0
choppy = 0

for d in fechas:
    day = raw[raw['date'] == d]
    
    asia = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    ny = day[(day['hour'] >= 9) & (day['hour'] < 16)] # Toda la sesión de NY
    
    if asia.empty or london.empty or ny.empty:
        continue
        
    total_dias += 1
    
    asia_hi = float(asia['High'].max())
    asia_lo = float(asia['Low'].min())
    
    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())
    
    swept_hi = lon_hi > asia_hi
    swept_lo = lon_lo < asia_lo
    
    ny_close = float(ny.iloc[-1]['Close'])
    ny_high = float(ny['High'].max())
    ny_low = float(ny['Low'].min())
    
    if swept_hi and swept_lo:
        choppy += 1
    elif swept_hi:
        total_sweeps_high += 1
        # ICT dice que si rompe arriba, es trampa y va a caer (SELL)
        # Falló si NY siguió subiendo (cerró fuerte o rompió el high de Londres)
        if ny_high > lon_hi + 20 and ny_close > asia_hi: 
            ict_falla_high += 1
        else:
            ict_funciona_high += 1
            
    elif swept_lo:
        total_sweeps_low += 1
        # ICT dice que si rompe abajo, es trampa y va a subir (BUY)
        # Falló si NY siguió bajando (cerró débil o rompió el low de Londres)
        if ny_low < lon_lo - 20 and ny_close < asia_lo:
            ict_falla_low += 1
        else:
            ict_funciona_low += 1
    else:
        sin_sweep += 1

print(f"Total de días analizados: {total_dias} días (aprox. 3 meses de trading)")
print(f"Días sin sweep de Asia: {sin_sweep}")
print(f"Días de rango roto por ambos lados (Choppy): {choppy}")
print("-" * 50)

print(f"\n📈 LONDRES ROMPE ARRIBA (ICT dice: TRAMPA, BUSCA VENTAS)")
print(f"Total de veces que pasó: {total_sweeps_high}")
if total_sweeps_high > 0:
    print(f"  ❌ ICT FALLÓ (El mercado siguió subiendo, te aplastó la tendencia): {ict_falla_high} veces ({(ict_falla_high/total_sweeps_high)*100:.1f}%)")
    print(f"  ✅ ICT FUNCIONÓ (Era una trampa y el mercado cayó): {ict_funciona_high} veces ({(ict_funciona_high/total_sweeps_high)*100:.1f}%)")

print(f"\n📉 LONDRES ROMPE ABAJO (ICT dice: TRAMPA, BUSCA COMPRAS)")
print(f"Total de veces que pasó: {total_sweeps_low}")
if total_sweeps_low > 0:
    print(f"  ❌ ICT FALLÓ (El mercado siguió bajando, te aplastó la tendencia): {ict_falla_low} veces ({(ict_falla_low/total_sweeps_low)*100:.1f}%)")
    print(f"  ✅ ICT FUNCIONÓ (Era una trampa y el mercado subió): {ict_funciona_low} veces ({(ict_funciona_low/total_sweeps_low)*100:.1f}%)")

print("\n" + "="*70)
print("CONCLUSIÓN MATEMÁTICA")
total_sweeps = total_sweeps_high + total_sweeps_low
total_fallas = ict_falla_high + ict_falla_low
total_exitos = ict_funciona_high + ict_funciona_low

if total_sweeps > 0:
    print(f"En los últimos {total_dias} días de NQ, apostar ciegamente a que Londres")
    print(f"hizo una trampa a Asia FUNCIONÓ el {(total_exitos/total_sweeps)*100:.1f}% de las veces, y fue un")
    print(f"error (el mercado estaba en tendencia real) el {(total_fallas/total_sweeps)*100:.1f}% de las veces.")
print("="*70)
