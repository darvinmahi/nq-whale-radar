import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🚀 BACKTEST ESTRATÉGICO PROMAX: 3 MESES (90 DÍAS)")
print("   Estrategia: EMA 200 + Volume Profile + Reconocimiento de Molde")
print("="*80)

# 1. DATOS (90 días de 1h para tener histórico completo)
def get_backtest_data():
    print("📡 Descargando datos del Nasdaq y VXN...")
    nq = yf.download("NQ=F", period="90d", interval="1h", progress=False)
    vxn = yf.download("^VXN", period="90d", interval="1h", progress=False)
    daily = yf.download("NQ=F", period="350d", interval="1d", progress=False)

    if isinstance(nq.columns, pd.MultiIndex): nq.columns = nq.columns.get_level_values(0)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    if isinstance(daily.columns, pd.MultiIndex): daily.columns = daily.columns.get_level_values(0)

    nq.index = nq.index.tz_convert('America/New_York')
    if vxn.index.tz is None: vxn.index = vxn.index.tz_localize('UTC')
    vxn.index = vxn.index.tz_convert('America/New_York')
    
    return nq, vxn, daily

nq, vxn, daily = get_backtest_data()

# Indicadores Macro
daily['EMA200'] = daily['Close'].ewm(span=200, adjust=False).mean()
ema_map = {d.date(): float(v) for d, v in daily['EMA200'].items()}
close_map = {d.date(): float(v) for d, v in daily['Close'].items()}

# 2. LOGICA DE BACKTEST
nq['date'] = nq.index.date
nq['hour'] = nq.index.hour
dates = sorted(nq['date'].unique())

trades = []

for d in dates:
    # Obtener tendencia del cierre anterior
    try:
        prev_idx = list(close_map.keys()).index(d) - 1
        if prev_idx < 0: continue
        d_prev = list(close_map.keys())[prev_idx]
        ema_prev = ema_map.get(d_prev, 0)
        close_prev = close_map.get(d_prev, 0)
        trend = "BULL" if close_prev > ema_prev else "BEAR"
    except: continue

    day = nq[nq['date'] == d]
    day_vxn = vxn[vxn.index.date == d]
    
    # Sesiones
    madr = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    pre_val = pre_lo + (pre_hi - pre_lo) * 0.3 # VAL aproximado
    pre_vah = pre_lo + (pre_hi - pre_lo) * 0.7 # VAH aproximado
    
    # VXN a la apertura
    try: opening_vxn = float(day_vxn.iloc[0]['Open'])
    except: opening_vxn = 20.0

    # REGLAS DE ENTRADA PROMAX
    # 1. Si VXN > 24 -> Molde probable: MEGÁFONO o TRAMPA. Operamos REVERSIÓN al centro.
    # 2. Si VXN < 24 -> Molde probable: EXPANSIÓN (P/b Shape). Operamos CONTINUACIÓN a favor de EMA200.

    direction = None
    entry = None
    stop = None
    target = None

    if opening_vxn > 24:
        # Modo Reversión (Regreso al POC de Madrid)
        if trend == "BULL":
            entry = pre_lo # Compramos el suelo de Londres
            target = (pre_hi + pre_lo) / 2 # Target: Mitad del rango
            stop = pre_lo - 40
            direction = "BUY"
        else:
            entry = pre_hi # Vendemos el techo de Londres
            target = (pre_hi + pre_lo) / 2
            stop = pre_hi + 40
            direction = "SELL"
    else:
        # Modo Expansión (Continuación EMA 200)
        if trend == "BULL":
            entry = pre_vah # Entramos en el rompimiento/test del VAH
            target = entry + (pre_hi - pre_lo) # 1:1 del rango
            stop = (pre_hi + pre_lo) / 2
            direction = "BUY"
        else:
            entry = pre_val
            target = entry - (pre_hi - pre_lo)
            stop = (pre_hi + pre_lo) / 2
            direction = "SELL"

    # Simular Ejecución
    entered = False
    result = "LOSS"
    pnl = 0
    
    for t, bar in ny.iterrows():
        hi, lo = float(bar['High']), float(bar['Low'])
        
        if not entered:
            # ¿Tocó nuestro precio de entrada?
            if lo <= entry <= hi:
                entered = True
        else:
            if direction == "BUY":
                if lo <= stop: result = "LOSS"; pnl = stop - entry; break
                if hi >= target: result = "WIN"; pnl = target - entry; break
            else:
                if hi >= stop: result = "LOSS"; pnl = entry - stop; break
                if lo <= target: result = "WIN"; pnl = entry - target; break

    if entered:
        if pnl == 0: # Salida al cierre de sesión
            ny_close = float(ny.iloc[-1]['Close'])
            pnl = (ny_close - entry) if direction == "BUY" else (entry - ny_close)
            result = "WIN" if pnl > 0 else "LOSS"

        trades.append({
            'Fecha': d,
            'Contexto': f"VXN:{opening_vxn:.1f} | {trend}",
            'Dir': direction,
            'Resultado': result,
            'PnL': round(pnl, 1)
        })

# 3. RESULTADOS
df_t = pd.DataFrame(trades)
if not df_t.empty:
    wr = (len(df_t[df_t['Resultado'] == "WIN"]) / len(df_t)) * 100
    total_pts = df_t['PnL'].sum()
    print(f"\n📊 RESULTADOS FINAL BACKTEST (90 DÍAS)")
    print("-" * 50)
    print(f"Trades Ejecutados: {len(df_t)}")
    print(f"Win Rate:         {wr:.1f}%")
    print(f"PnL Total:        {total_pts:.1f} puntos (~${total_pts*20:,.0f})")
    print("-" * 50)
    print("\nDetalle de últimos 10 trades:")
    print(df_t.tail(10))
else:
    print("No se ejecutaron trades.")
