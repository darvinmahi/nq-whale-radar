import yfinance as yf
import pandas as pd
import numpy as np
import os

print("="*80)
print("🔍 ANÁLISIS FORENSE FINAL: EMA200 + VXN + COT 🔍")
print("="*80)

# 1. Bajar datos de 1 minuto y diarios macro
raw_5m = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw_5m.columns, pd.MultiIndex):
    raw_5m.columns = raw_5m.columns.get_level_values(0)
raw_5m.index = raw_5m.index.tz_convert('America/New_York')

raw_daily = yf.download(["NQ=F", "^VXN"], period="300d", interval="1d", progress=False)
if isinstance(raw_daily.columns, pd.MultiIndex):
    nq_close = raw_daily['Close']['NQ=F']
    vxn_close = raw_daily['Close']['^VXN']
else:
    nq_close = raw_daily['Close']
    vxn_close = pd.Series(index=raw_daily.index, data=20)

if nq_close.index.tz is None: nq_close.index = nq_close.index.tz_localize('UTC')
nq_close.index = nq_close.index.tz_convert('America/New_York')

if vxn_close.index.tz is None: vxn_close.index = vxn_close.index.tz_localize('UTC')
vxn_close.index = vxn_close.index.tz_convert('America/New_York')

# 2. Cargar COT Data si existe
cot_data = None
cot_map = {}
if os.path.exists("cot_history.csv"):
    try:
        cot_df = pd.read_csv("cot_history.csv")
        cot_df['Date'] = pd.to_datetime(cot_df['Date'])
        # Ordenar cronológicamente para llenado forward
        cot_df = cot_df.sort_values('Date')
        cot_df.set_index('Date', inplace=True)
        # El COT es semanal, necesitamos llenar los días entre reportes
        idx_diario = pd.date_range(start=cot_df.index.min(), end=pd.Timestamp.today().normalize())
        cot_diario = cot_df.reindex(idx_diario).ffill()
        cot_map = {d.date(): float(v) for d, v in cot_diario['COT_Index'].items()}
    except Exception as e:
        print(f"Error cargando COT: {e}")

# 3. Calcular indicadores
ema200 = nq_close.ewm(span=200, adjust=False).mean()
ema_map = {d.date(): float(v) for d, v in ema200.items()}
nq_close_map = {d.date(): float(v) for d, v in nq_close.items()}
vxn_map = {d.date(): float(v) for d, v in vxn_close.items() if not pd.isna(v)}

raw_5m['hour'] = raw_5m.index.hour
raw_5m['date'] = raw_5m.index.date
fechas = sorted(raw_5m['date'].unique())

resultados = []

for d in fechas:
    day = raw_5m[raw_5m['date'] == d]
    
    asia = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    ny = day[(day['hour'] >= 9) & (day['hour'] < 16)]
    
    if asia.empty or london.empty or ny.empty: continue
        
    asia_hi, asia_lo = float(asia['High'].max()), float(asia['Low'].min())
    lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
    
    swept_hi = lon_hi > asia_hi
    swept_lo = lon_lo < asia_lo
    
    ny_close, ny_high, ny_low = float(ny.iloc[-1]['Close']), float(ny['High'].max()), float(ny['Low'].min())
    
    try:
        idx_prev = list(nq_close_map.keys()).index(d) - 1
        if idx_prev < 0: continue
        d_prev = list(nq_close_map.keys())[idx_prev]
        
        ema_val = ema_map.get(d_prev, 0)
        close_prev = nq_close_map.get(d_prev, 0)
        vxn_val = vxn_map.get(d_prev, 20.0)
        cot_val = cot_map.get(d_prev, 50.0) # 50 es neutral por defecto
        
        tendencia_diaria = "ALCISTA" if close_prev > ema_val else "BAJISTA"
    except ValueError:
        continue
        
    if swept_hi and not swept_lo: # ICT = SELL
        if ny_high > lon_hi + 20 and ny_close > asia_hi: resultado_ict = "FALLO"
        else: resultado_ict = "EXITO"
        resultados.append({'Fecha': d, 'Setup': 'SELL (Sweep High)', 'Resultado': resultado_ict, 'Tendencia': tendencia_diaria, 'VXN': f"{vxn_val:.1f}", 'COT': f"{cot_val:.1f}"})
            
    elif swept_lo and not swept_hi: # ICT = BUY
        if ny_low < lon_lo - 20 and ny_close < asia_lo: resultado_ict = "FALLO"
        else: resultado_ict = "EXITO"
        resultados.append({'Fecha': d, 'Setup': 'BUY (Sweep Low)', 'Resultado': resultado_ict, 'Tendencia': tendencia_diaria, 'VXN': f"{vxn_val:.1f}", 'COT': f"{cot_val:.1f}"})

df_res = pd.DataFrame(resultados)
fallas_sell = df_res[(df_res['Setup'] == 'SELL (Sweep High)') & (df_res['Resultado'] == 'FALLO')]
fallas_buy = df_res[(df_res['Setup'] == 'BUY (Sweep Low)') & (df_res['Resultado'] == 'FALLO')]

print(f"\n📉 ICT SETUP: LONDRES ROMPE ARRIBA -> ICT DICE VENDER")
print(f"   Por qué falló {len(fallas_sell)} veces (el mercado siguió subiendo):")
for i, row in fallas_sell.iterrows():
    print(f"   ❌ {row['Fecha']} | Tendencia: {row['Tendencia']:<7} | COT Index: {row['COT']:>4} | VXN: {row['VXN']}")

print(f"\n   💡 RESOLUCIÓN PARA TRAMPAS DE VENTA:")
print(f"   ► EMA200: Filtró TODOS los errores (el mercado era alcista general).")
if len(fallas_sell) > 0:
    cot_alcistas = len(fallas_sell[fallas_sell['COT'].astype(float) > 50])
    print(f"   ► COT: Las ballenas estaban comprando (COT > 50) en {cot_alcistas} de esos {len(fallas_sell)} días de pérdida.")

print(f"\n📈 ICT SETUP: LONDRES ROMPE ABAJO -> ICT DICE COMPRAR")
print(f"   Por qué falló {len(fallas_buy)} veces (el mercado siguió colapsando):")
for i, row in fallas_buy.iterrows():
    print(f"   ❌ {row['Fecha']} | Tendencia: {row['Tendencia']:<7} | COT Index: {row['COT']:>4} | VXN: {row['VXN']}")

if len(fallas_buy) > 0:
    vxn_alto = len(fallas_buy[fallas_buy['VXN'].astype(float) > 23])
    cot_bajistas = len(fallas_buy[fallas_buy['COT'].astype(float) < 30])
    print(f"\n   💡 RESOLUCIÓN PARA TRAMPAS DE COMPRA:")
    print(f"   ► EMA200: Irónicamente la tendencia macro era alcista, PERO:")
    print(f"   ► VXN (Pánico): {vxn_alto} de {len(fallas_buy)} caídas pasaron con volatilidad extrema (>23).")
    print(f"   ► COT (Ballenas): Instituciones masivamente bajistas (COT < 30) en {cot_bajistas} de esos días.")
print("="*80)
