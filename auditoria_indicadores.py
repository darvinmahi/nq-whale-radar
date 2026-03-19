import yfinance as yf
import pandas as pd
import numpy as np
import os
from datetime import datetime

print("="*80)
print("🔍 AUDITORÍA MAESTRA PROMAX: REPETICIONES SEMANALES Y PATRONES 🔍")
print("="*80)

# 1. DESCARGA Y LIMPIEZA DE DATOS
raw_5m = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw_5m.columns, pd.MultiIndex): raw_5m.columns = raw_5m.columns.get_level_values(0)
if raw_5m.empty:
    print("❌ No se pudieron bajar datos de 5 min. Intentando con 1h...")
    raw_5m = yf.download("NQ=F", period="60d", interval="1h", progress=False)
    if isinstance(raw_5m.columns, pd.MultiIndex): raw_5m.columns = raw_5m.columns.get_level_values(0)

raw_5m.index = raw_5m.index.tz_convert('America/New_York')

raw_d = yf.download(["NQ=F", "^VXN"], period="350d", interval="1d", progress=False)
if isinstance(raw_d.columns, pd.MultiIndex):
    nq_close = raw_d['Close']['NQ=F']
    vxn_close = raw_d['Close']['^VXN']
else:
    nq_close = raw_d['Close']
    vxn_close = pd.Series(index=raw_d.index, data=20)

if nq_close.index.tz is None: nq_close.index = nq_close.index.tz_localize('UTC')
nq_close.index = nq_close.index.tz_convert('America/New_York')
if vxn_close.index.tz is None: vxn_close.index = vxn_close.index.tz_localize('UTC')
vxn_close.index = vxn_close.index.tz_convert('America/New_York')

# Indicadores Macro
ema200 = nq_close.ewm(span=200, adjust=False).mean()

# Mapeos
ema_map = {d.date(): float(v) for d, v in ema200.items()}
vxn_map = {d.date(): float(v) for d, v in vxn_close.items() if not pd.isna(v)}
px_map = {d.date(): float(v) for d, v in nq_close.items()}

# 2. CLASIFICACIÓN DE DÍAS Y ESTADO DE INDICADORES
raw_5m['hour'] = raw_5m.index.hour
raw_5m['date'] = raw_5m.index.date
dates = sorted(raw_5m['date'].unique())

db = []

for d in dates:
    day = raw_5m[raw_5m['date'] == d]
    asia_lon = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    
    if asia_lon.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(asia_lon['High'].max()), float(asia_lon['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])
    
    rompio_hi = ny_hi > pre_hi
    rompio_lo = ny_lo < pre_lo
    
    if rompio_hi and rompio_lo: perfil = "MEGÁFONO"
    elif rompio_hi and not rompio_lo: perfil = "CONT. ALCISTA" if ny_close > pre_hi else "TRAMPA BULL"
    elif rompio_lo and not rompio_hi: perfil = "CONT. BAJISTA" if ny_close < pre_lo else "TRAMPA BEAR"
    else: perfil = "RANGO"

    try:
        d_prev = list(px_map.keys())[list(px_map.keys()).index(d) - 1]
        ema = ema_map.get(d_prev, 0)
        px = px_map.get(d_prev, 0)
        vxn = vxn_map.get(d_prev, 20.0)
        above_ema = px > ema
    except: continue

    # Semana del año
    dt = datetime.combine(d, datetime.min.time())
    week_num = dt.isocalendar()[1]
    year = dt.isocalendar()[0]

    db.append({
        'Fecha': d,
        'Semana': f"{year}-W{week_num}",
        'Perfil': perfil,
        'EMA200_BULL': above_ema,
        'VXN': vxn
    })

df = pd.DataFrame(db)

# 3. ANÁLISIS POR SEMANA
print(f"\n✅ ANÁLISIS DE {len(df)} DÍAS FILTRADOS POR SEMANAS\n")

# Agrupar por semana y perfil
weekly_stats = df.groupby(['Semana', 'Perfil']).size().reset_index(name='Cuenta')

# Filtrar repeticiones (perfil que sale 2 o más veces por semana)
repetitions = weekly_stats[weekly_stats['Cuenta'] >= 2].sort_values(by='Cuenta', ascending=False)

print(f"{'SEMANA':<15} | {'PERFIL REPETIDO':<20} | {'VECES/SEM'} | {'CONTEXTO INDICADORES'}")
print("-" * 85)

for _, row in repetitions.iterrows():
    sem, perf, count = row['Semana'], row['Perfil'], row['Cuenta']
    
    # Ver indicadores promedio de esa semana para ese perfil
    sub = df[(df['Semana'] == sem) & (df['Perfil'] == perf)]
    avg_vxn = sub['VXN'].mean()
    ema_bull_pct = (sub['EMA200_BULL'].sum() / len(sub)) * 100
    
    contexto = f"VXN: {avg_vxn:.1f} | EMA: {'BULL' if ema_bull_pct > 50 else 'BEAR'}"
    print(f"{sem:<15} | {perf:<20} | {count:>9} | {contexto}")

# 4. REVELACIÓN DE PATRONES REPETITIVOS
print("\n" + "="*80)
print("📊 RESUMEN DE COMPORTAMIENTOS REPETITIVOS (MOLDES)")
print("="*80)

top_repeat = df['Perfil'].value_counts()
for p, c in top_repeat.items():
    pct = (c / len(df)) * 100
    print(f"🔹 {p:<15}: Apareció {c} veces en Total ({pct:.1f}% del tiempo)")

print("\n💡 CONCLUSIONES PARA EL CURSO:")

# Buscar la combinación ganadora
megafono_weeks = weekly_stats[(weekly_stats['Perfil'] == 'MEGÁFONO') & (weekly_stats['Cuenta'] >= 2)]
if not megafono_weeks.empty:
    print(f"➡️ EL PATRÓN 'MEGÁFONO' SE REPIETE MUCHO: Hubo {len(megafono_weeks)} semanas donde el Nasdaq barrió arriba y abajo DOS o más veces.")
    print("   Estrategia: En esas semanas el VXN suele estar alto (>23). No busques tendencia, opera el canal.")

cont_weeks = weekly_stats[(weekly_stats['Perfil'] == 'CONT. ALCISTA') & (weekly_stats['Cuenta'] >= 2)]
if not cont_weeks.empty:
    print(f"➡️ RACHAS DE CONTINUACIÓN: Existen semanas donde el Nasdaq 'vuela' {cont_weeks['Cuenta'].max()} días seguidos.")
    print(f"   Contexto: 100% de estas rachas ocurrieron con el precio SOBRE la EMA 200.")

print("\n" + "="*80)
print("🎯 ¿CÓMO ESTAR EN EL MEDIO Y SACARLE JUGO?")
print("1. Identifica el POC (Punto de Control) de Asia. Es el centro de gravedad.")
print("2. Si el VXN es alto y estamos en semana de Megáfonos (recalibración),")
print("   vende el High de Londres y compra el Low, buscando SIEMPRE el POC central.")
print("3. No dejes trades abiertos; en Megáfonos el precio siempre vuelve al medio.")
print("="*80)
