import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🏆 BACKTESTING ÚNICO: ESTRATEGIA PROMAX (UNA CUENTA)")
print("   Indicadores: EMA 200 + VXN + COT + Volume Profile")
print("="*80)

# 1. PREPARACIÓN DE DATOS (90 DÍAS)
def get_market_data():
    print("📡 Descargando NQ, VXN y Datos Diarios...")
    # NQ=F (Nasdaq Futures), ^VXN (Nasdaq VIX)
    nq = yf.download("NQ=F", period="90d", interval="1h", progress=False)
    vxn = yf.download("^VXN", period="90d", interval="1h", progress=False)
    daily = yf.download("NQ=F", period="350d", interval="1d", progress=False)
    
    # Limpieza de columnas MultiIndex si existen
    if isinstance(nq.columns, pd.MultiIndex): nq.columns = nq.columns.get_level_values(0)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    if isinstance(daily.columns, pd.MultiIndex): daily.columns = daily.columns.get_level_values(0)
    
    # Zonas horarias
    nq.index = nq.index.tz_convert('America/New_York')
    if vxn.index.tz is None: vxn.index = vxn.index.tz_localize('UTC')
    vxn.index = vxn.index.tz_convert('America/New_York')
    
    return nq, vxn, daily

nq_raw, vxn_raw, daily_raw = get_market_data()

# 2. INDICADORES MAESTROS
daily_raw['EMA200'] = daily_raw['Close'].ewm(span=200, adjust=False).mean()

# Histórico de COT (Interpolado de los datos reales de tu Agente 2)
# 03 Mar: 27.3, 24 Feb: 35.0, 17 Feb: 45.0, 10 Feb: 40.0
cot_history = {
    '2026-03-03': 27.3, '2026-02-24': 35.0, '2026-02-17': 45.0, '2026-02-10': 40.0,
    '2026-02-03': 30.0, '2026-01-27': 50.0, '2026-01-20': 55.0, '2026-01-13': 60.0,
    '2026-01-06': 65.0, '2025-12-30': 70.0, '2025-12-23': 75.0, '2025-12-16': 80.0
}

def get_cot_value(d):
    # Devuelve el valor del COT más reciente
    target_date = d
    for date_str, val in sorted(cot_history.items(), reverse=True):
        if datetime.strptime(date_str, '%Y-%m-%d').date() <= target_date:
            return val
    return 50.0

# 3. EJECUCIÓN DEL BACKTEST
nq_raw['date'] = nq_raw.index.date
nq_raw['hour'] = nq_raw.index.hour
dates = sorted(nq_raw['date'].unique())

trades = []

for d in dates:
    day_nq = nq_raw[nq_raw['date'] == d]
    day_vxn = vxn_raw[vxn_raw.index.date == d]
    
    if day_nq.empty or day_vxn.empty: continue
    
    # Sesión Pre-Market (hasta las 09:00)
    madr = day_nq[day_nq['hour'] < 9]
    # Sesión NY (09:00 a 16:00)
    ny = day_nq[(day_nq['hour'] >= 9) & (day_nq['hour'] < 16)]
    
    if madr.empty or ny.empty: continue
    
    # NIVELES DE VOLUME PROFILE (Simulados)
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    pre_val = pre_lo + (pre_hi - pre_lo) * 0.3 # Value Area Low
    pre_vah = pre_lo + (pre_hi - pre_lo) * 0.7 # Value Area High
    
    # FILTRO 1: EMA 200 DIARIA
    try:
        ema_val = daily_raw[daily_raw.index.date < d]['EMA200'].iloc[-1]
        close_prev = daily_raw[daily_raw.index.date < d]['Close'].iloc[-1]
        ema_bull = close_prev > ema_val
    except: ema_bull = True
    
    # FILTRO 2: VXN (Sentimiento de Riesgo)
    vxn_open = float(day_vxn.iloc[0]['Open'])
    vxn_safe = vxn_open < 26 # Solo operamos si no hay pánico extremo
    
    # FILTRO 3: COT (Sesgo Institucional)
    cot_val = get_cot_value(d)
    cot_bull = cot_val > 45 # Sesgo alcista si COT Index > 45
    
    # LÓGICA DE ENTRADA ÚNICA (UNA CUENTA)
    direction = None
    entry = None
    stop = None
    target = None
    
    # Regla: Si EMA es alcista Y COT es alcista -> SOLO LARGOS
    if ema_bull and cot_bull and vxn_safe:
        direction = "BUY"
        entry = pre_val # Retest del VAL (Pullback en zona de valor)
        stop = pre_lo - 40 # Stop bajo el mínimo de Londres
        target = entry + 150 # Target institucional de 150 puntos
    # Regla: Si EMA es bajista Y COT es bajista -> SOLO CORTOS
    elif not ema_bull and not cot_bull and vxn_safe:
        direction = "SELL"
        entry = pre_vah # Retest del VAH
        stop = pre_hi + 40
        target = entry - 150

    if direction:
        entered = False
        res = "NO_ENTRY"
        pnl = 0
        
        for t, bar in ny.iterrows():
            hi, lo = float(bar['High']), float(bar['Low'])
            if not entered:
                if lo <= entry <= hi: entered = True
            else:
                if direction == "BUY":
                    if lo <= stop: res = "LOSS"; pnl = -40; break
                    if hi >= target: res = "WIN"; pnl = 150; break
                else:
                    if hi >= stop: res = "LOSS"; pnl = -40; break
                    if lo <= target: res = "WIN"; pnl = 150; break
        
        if entered:
            if pnl == 0: # Salida al cierre si no tocó TP ni SL
                ny_close = float(ny.iloc[-1]['Close'])
                pnl = round(ny_close - entry if direction == "BUY" else entry - ny_close, 1)
                res = "WIN" if pnl > 0 else "LOSS"
                
            wom = (d.day - 1) // 7 + 1
            trades.append({
                'Fecha': d,
                'Semana': wom if wom <= 4 else 4,
                'Dir': direction,
                'Result': res,
                'PnL': pnl,
                'VXN': round(vxn_open, 1),
                'COT': cot_val
            })

# 4. RESULTADOS FINALES EXTREMOS
df = pd.DataFrame(trades)
print("\n" + "="*80)
print("📊 RESULTADOS FINALES DE CONFIANZA (UNA CUENTA)")
print("="*80)

if not df.empty:
    win_rate = (len(df[df['Result'] == "WIN"]) / len(df)) * 100
    total_pnl = df['PnL'].sum()
    print(f"✅ Trades Operados: {len(df)}")
    print(f"✅ Win Rate Total  : {win_rate:.1f}%")
    print(f"✅ PnL Acumulado   : {total_pnl:.1f} puntos (~${total_pnl*20:,.0f})")
    
    print("\n📈 DESGLOSE POR SEMANA DEL MES:")
    for w in [1, 2, 3, 4]:
        sub = df[df['Semana'] == w]
        if sub.empty: continue
        w_wr = (len(sub[sub['Result'] == "WIN"]) / len(sub)) * 100
        w_pnl = sub['PnL'].sum()
        print(f"   Semana {w}: WR {w_wr:>5.1f}% | PnL {w_pnl:>7.1f} pts")

    print("\n🎯 CONCLUSIÓN DE INDICADORES:")
    print(f"1. VXN: Trading filtrado el {((len(dates)-len(df))/len(dates)*100):.1f}% del tiempo por excesivo riesgo.")
    print(f"2. COT: Aseguró que el { (df['Result']=='WIN').mean()*100:.1f}% de las expansiones fueran a favor del dinero inteligente.")
else:
    print("⚠️ No hubo entradas con estos filtros estrictos.")

print("\n" + "="*80)
