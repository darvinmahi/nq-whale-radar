import yfinance as yf
import pandas as pd
import numpy as np

print("="*80)
print("🚀 BACKTEST PROMAX: ESTRATEGIA FINAL (60 DÍAS - 5 MIN)")
print("   Filtros: EMA 200 + Volume Profile + Continuación de Tendencia")
print("="*80)

# 1. DATOS
# Velas 5 min para ejecución
raw_5m = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw_5m.columns, pd.MultiIndex):
    raw_5m.columns = raw_5m.columns.get_level_values(0)
raw_5m.index = raw_5m.index.tz_convert('America/New_York')

# Velas diarias para EMA 200
raw_d = yf.download("NQ=F", period="300d", interval="1d", progress=False)
if isinstance(raw_d.columns, pd.MultiIndex):
    raw_d.columns = raw_d.columns.get_level_values(0)
raw_d.index = raw_d.index.tz_convert('America/New_York')
raw_d['EMA200'] = raw_d['Close'].ewm(span=200, adjust=False).mean()

# Mapeo de indicadores
ema_map = {d.date(): float(v) for d, v in raw_d['EMA200'].items()}
close_map = {d.date(): float(v) for d, v in raw_d['Close'].items()}

raw_5m['hour'] = raw_5m.index.hour
raw_5m['minute'] = raw_5m.index.minute
raw_5m['date'] = raw_5m.index.date
raw_5m['volume'] = raw_5m['Volume'].fillna(1).replace(0, 1)

def calc_profile(sdf, n_bins=40, pct=0.70):
    if len(sdf) < 2: return None, None, None
    lo, hi = float(sdf['Low'].min()), float(sdf['High'].max())
    if hi <= lo: return (hi+lo)/2, hi, lo
    bins = np.linspace(lo, hi, n_bins+1)
    vb = np.zeros(n_bins)
    for _, r in sdf.iterrows():
        rlo, rhi, rv = float(r['Low']), float(r['High']), float(r['volume'])
        rng = rhi - rlo if rhi > rlo else 1e-9
        for b in range(n_bins):
            ov = min(rhi, bins[b+1]) - max(rlo, bins[b])
            if ov > 0: vb[b] += rv*(ov/rng)
    tot = vb.sum()
    if tot == 0: return (hi+lo)/2, hi, lo
    pi = int(np.argmax(vb)); poc = (bins[pi]+bins[pi+1])/2
    acc = vb[pi]; hi_i, lo_i = pi, pi
    while acc < tot*pct:
        cu = hi_i+1 < n_bins; cd = lo_i-1 >= 0
        if not cu and not cd: break
        vu = vb[hi_i+1] if cu else -1
        vd = vb[lo_i-1] if cd else -1
        if vu >= vd: hi_i+=1; acc+=vu
        else:        lo_i-=1; acc+=vd
    return poc, bins[hi_i+1], bins[lo_i]

# 2. BACKTEST POR DÍA
fechas = sorted(raw_5m['date'].unique())
trades = []

for d in fechas:
    day = raw_5m[raw_5m['date'] == d]
    
    # Obtener tendencia del cierre anterior
    try:
        prev_idx = list(close_map.keys()).index(d) - 1
        if prev_idx < 0: continue
        d_prev = list(close_map.keys())[prev_idx]
        ema_prev = ema_map.get(d_prev, 0)
        close_prev = close_map.get(d_prev, 0)
        trend = "BULL" if close_prev > ema_prev else "BEAR"
    except:
        continue
    
    # Sesiones
    madrugada = day[(day['hour'] >= 0) & (day['hour'] < 9) | ((day['hour'] == 9) & (day['minute'] < 30))]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    ny_window = day[((day['hour'] == 9) & (day['minute'] >= 30)) | (day['hour'] == 10)] # 9:30 a 11:00 am
    
    if madrugada.empty or ny_window.empty: continue
    
    # Volume Profile de la madrugada (Asia + London)
    poc, vah, val = calc_profile(madrugada)
    
    # Rango de Londres (para Stop Loss)
    lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
    
    # DIRECCIÓN SEGÚN EMA200 (CONTINUACIÓN)
    if trend == "BULL":
        # Compro en el VAL (Value Area Low) para ir con la tendencia diaria
        entry = val
        stop = lon_lo - 5  # Stop bajo el mínimo de Londres
        target = vah + (vah - val) # Target extendido 1:1 del valor
        direction = "BUY"
    else:
        # Vendo en el VAH para ir con la tendencia diaria
        entry = vah
        stop = lon_hi + 5
        target = val - (vah - val)
        direction = "SELL"
    
    # EJECUCIÓN EN NY WINDOW
    entered = False
    result = "LOSS"
    pnl = 0
    t_entry = None
    
    for t, bar in ny_window.iterrows():
        hi, lo = float(bar['High']), float(bar['Low'])
        
        if not entered:
            # ¿Llegó al precio de entrada?
            if (direction == "BUY" and lo <= entry <= hi) or (direction == "SELL" and lo <= entry <= hi):
                entered = True
                t_entry = str(t.time())
        else:
            # Ya en el trade, buscar salida
            if direction == "BUY":
                if lo <= stop:
                    result = "LOSS"; pnl = stop - entry; break
                if hi >= target:
                    result = "WIN"; pnl = target - entry; break
            else:
                if hi >= stop:
                    result = "LOSS"; pnl = entry - stop; break
                if lo <= target:
                    result = "WIN"; pnl = entry - target; break
                    
    if entered:
        if pnl == 0: # Terminó fuera de rango al cierre de ventana
            close_ny = float(ny_window.iloc[-1]['Close'])
            pnl = (close_ny - entry) if direction == "BUY" else (entry - close_ny)
            result = "WIN" if pnl > 0 else "LOSS"
            
        trades.append({
            "Fecha": d,
            "Dir": direction,
            "Entrada": round(entry, 1),
            "Resultado": result,
            "pnl_pts": round(pnl, 1)
        })

# 3. RESULTADOS FINALES
df_trades = pd.DataFrame(trades)
if not df_trades.empty:
    win_rate = (len(df_trades[df_trades['Resultado'] == "WIN"]) / len(df_trades)) * 100
    total_pnl = df_trades['pnl_pts'].sum()
    profit_factor = abs(df_trades[df_trades['pnl_pts'] > 0]['pnl_pts'].sum() / df_trades[df_trades['pnl_pts'] < 0]['pnl_pts'].sum())
    
    print(f"\n✅ BACKTEST COMPLETADO")
    print(f"   Total Trades: {len(df_trades)}")
    print(f"   Win Rate: {win_rate:.1f}%")
    print(f"   Total PnL: {total_pnl:.1f} puntos (~${total_pnl*20:,.0f})")
    print(f"   Profit Factor: {profit_factor:.2f}")
    
    print("\n   Detalle de últimos trades:")
    print(df_trades.tail(10))
else:
    print("\n⚠️ No se ejecutaron trades con estas reglas.")
