"""
ESTRATEGIA: ICT + VOLUME PROFILE
=================================
Lógica:
  1. Sesión Asia (00:00 - 04:00 NY): Calcula el Value Profile del rango
       - POC  = nivel con más volumen (aproximado por precio medio ponderado)
       - VAH  = Value Area High (70% del volumen)
       - VAL  = Value Area Low  (70% del volumen)
  
  2. Sesión Londres (04:00 - 09:00 NY): Extiende el rango.
       - ¿London barreó el extremo Asia (Stop Hunt)?
  
  3. Sesión New York (09:30 - 12:00 NY): SOLO aquí se opera.
       SETUP A (COMPRA):
         - NY abre por DEBAJO del VAL o barre el Low de Asia/Londres
         - Precio regresa dentro del Value Area (retorno al valor)
         → COMPRA al tocar VAL desde abajo
       
       SETUP B (VENTA):
         - NY abre por ENCIMA del VAH o barre el High de Asia/Londres
         - Precio regresa dentro del Value Area
         → VENTA al tocar VAH desde arriba
       
       Objetivo: POC (+1 target) o VAH/VAL opuesto (+2 target)
       Stop: 0.3% más allá del extremo barrido

BACKTEST: 2 años de datos horarios NQ=F
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*65)
print("  ICT + VOLUME PROFILE STRATEGY — BACKTEST")
print("  Sesión Asia→Londres como Profile | Trades en NY")
print("="*65)

# ─── DATOS ──────────────────────────────────────────────────────────────────
print("\n📡 Descargando NQ=F horario (2 años)...")
df = yf.download("NQ=F", period="2y", interval="1h", progress=False)

if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.index = df.index.tz_convert('America/New_York')
df['hour']   = df.index.hour
df['date']   = df.index.date
df['volume'] = df['Volume'].fillna(1)

print(f"  ✅ {len(df)} velas horarias cargadas.")

# ─── FUNCIÓN: VOLUME PROFILE SIMPLIFICADO ────────────────────────────────────
def calc_value_area(session_df, value_pct=0.70):
    """
    Calcula POC, VAH, VAL a partir de un sub-dataframe.
    Aproximación: dividimos el rango en 20 niveles y ponderamos por volumen.
    """
    if session_df.empty or len(session_df) < 2:
        return None, None, None
    
    lo = float(session_df['Low'].min())
    hi = float(session_df['High'].max())
    if hi == lo:
        return (hi+lo)/2, hi, lo
    
    # 20 bins de precio
    n_bins = 20
    bins = np.linspace(lo, hi, n_bins + 1)
    vol_by_price = np.zeros(n_bins)
    
    for _, row in session_df.iterrows():
        r_lo = float(row['Low'])
        r_hi = float(row['High'])
        r_vol = float(row['volume'])
        # Distribuir volumen en los bins que cubre esta vela
        for b in range(n_bins):
            b_lo_b = bins[b]
            b_hi_b = bins[b+1]
            overlap = min(r_hi, b_hi_b) - max(r_lo, b_lo_b)
            if overlap > 0:
                vol_by_price[b] += r_vol * (overlap / (r_hi - r_lo + 1e-9))
    
    total_vol = vol_by_price.sum()
    if total_vol == 0:
        poc = (hi + lo) / 2
        return poc, hi, lo
    
    # POC: bin con más volumen
    poc_idx = np.argmax(vol_by_price)
    poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2
    
    # Value Area: acumular 70% del volumen desde el POC
    target_vol  = total_vol * value_pct
    accumulated = vol_by_price[poc_idx]
    high_idx    = poc_idx
    low_idx     = poc_idx
    
    while accumulated < target_vol:
        can_up   = high_idx + 1 < n_bins
        can_down = low_idx - 1 >= 0
        if not can_up and not can_down:
            break
        vol_up   = vol_by_price[high_idx + 1] if can_up   else -1
        vol_down = vol_by_price[low_idx  - 1] if can_down else -1
        if vol_up >= vol_down:
            high_idx    += 1
            accumulated += vol_up
        else:
            low_idx     -= 1
            accumulated += vol_down
    
    vah = bins[high_idx + 1]
    val = bins[low_idx]
    return poc, vah, val

# ─── BACKTEST ───────────────────────────────────────────────────────────────
print("\n🔍 Ejecutando backtest día por día...")

trades = []
dates  = df['date'].unique()
skipped = 0

for d in sorted(dates):
    day_df = df[df['date'] == d]
    
    # Sesiones
    asia   = day_df[(day_df['hour'] >= 0)  & (day_df['hour'] < 4)]
    london = day_df[(day_df['hour'] >= 4)  & (day_df['hour'] < 9)]
    ny_am  = day_df[(day_df['hour'] >= 9)  & (day_df['hour'] < 12)]
    
    if asia.empty or london.empty or ny_am.empty:
        skipped += 1
        continue
    
    # Profile sobre Asia (con volumen)
    poc_a, vah_a, val_a = calc_value_area(asia)
    if poc_a is None:
        continue
    
    # Rango Londres
    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())
    
    # Rango Asia
    asia_hi = float(asia['High'].max())
    asia_lo = float(asia['Low'].min())
    
    # ¿Londres barrió los extremos de Asia? (Manipulación ICT)
    lon_swept_asia_lo = lon_lo < asia_lo   # London hizo stop hunt bajista en Asia
    lon_swept_asia_hi = lon_hi > asia_hi   # London hizo stop hunt alcista en Asia
    
    # Vela de apertura NY (primera vela 09:xx)
    ny_open_bar = ny_am.iloc[0]
    ny_open     = float(ny_open_bar['Open'])
    
    # Posición de NY respecto al Profile de Asia
    ny_below_val = ny_open < val_a
    ny_above_vah = ny_open > vah_a
    
    trade = None
    
    # ─── SETUP A: COMPRA ─────────────────────────────────────────────────────
    # NY abre debajo del VAL + Londres barrió el Low de Asia (Stop Hunt completado)
    if ny_below_val and lon_swept_asia_lo:
        entry    = float(ny_am['Open'].iloc[0])
        target   = poc_a   # Retorno al POC
        stop_gap = (val_a - ny_open) * 0.5 + (asia_lo - lon_lo)
        stop     = entry - max(stop_gap, entry * 0.003)
        
        # Simular la vela siguiente
        for _, ny_bar in ny_am.iterrows():
            hi_bar = float(ny_bar['High'])
            lo_bar = float(ny_bar['Low'])
            
            if lo_bar <= stop:    # Stoploss
                trade = {"date": str(d), "setup": "BUY", "result": "LOSS",
                         "entry": entry, "exit": stop, "pnl_pts": stop - entry,
                         "poc": poc_a, "vah": vah_a, "val": val_a,
                         "lon_swept_lo": lon_swept_asia_lo}
                break
            if hi_bar >= target:  # Target
                trade = {"date": str(d), "setup": "BUY", "result": "WIN",
                         "entry": entry, "exit": target, "pnl_pts": target - entry,
                         "poc": poc_a, "vah": vah_a, "val": val_a,
                         "lon_swept_lo": lon_swept_asia_lo}
                break
        
        if trade is None:  # Fin de sesión sin tocar nada
            last_close = float(ny_am['Close'].iloc[-1])
            trade = {"date": str(d), "setup": "BUY", "result": "FLAT",
                     "entry": entry, "exit": last_close, "pnl_pts": last_close - entry,
                     "poc": poc_a, "vah": vah_a, "val": val_a,
                     "lon_swept_lo": lon_swept_asia_lo}
    
    # ─── SETUP B: VENTA ──────────────────────────────────────────────────────
    # NY abre encima del VAH + Londres barrió el High de Asia (Stop Hunt completo)
    elif ny_above_vah and lon_swept_asia_hi:
        entry    = float(ny_am['Open'].iloc[0])
        target   = poc_a
        stop_gap = (ny_open - vah_a) * 0.5 + (lon_hi - asia_hi)
        stop     = entry + max(stop_gap, entry * 0.003)
        
        for _, ny_bar in ny_am.iterrows():
            hi_bar = float(ny_bar['High'])
            lo_bar = float(ny_bar['Low'])
            
            if hi_bar >= stop:
                trade = {"date": str(d), "setup": "SELL", "result": "LOSS",
                         "entry": entry, "exit": stop, "pnl_pts": entry - stop,
                         "poc": poc_a, "vah": vah_a, "val": val_a,
                         "lon_swept_hi": lon_swept_asia_hi}
                break
            if lo_bar <= target:
                trade = {"date": str(d), "setup": "SELL", "result": "WIN",
                         "entry": entry, "exit": target, "pnl_pts": entry - target,
                         "poc": poc_a, "vah": vah_a, "val": val_a,
                         "lon_swept_hi": lon_swept_asia_hi}
                break
        
        if trade is None:
            last_close = float(ny_am['Close'].iloc[-1])
            trade = {"date": str(d), "setup": "SELL", "result": "FLAT",
                     "entry": entry, "exit": last_close, "pnl_pts": entry - last_close,
                     "poc": poc_a, "vah": vah_a, "val": val_a,
                     "lon_swept_hi": lon_swept_asia_hi}
    
    if trade:
        trades.append(trade)

# ─── ESTADÍSTICAS ────────────────────────────────────────────────────────────
t_df = pd.DataFrame(trades)

print(f"\n{'='*65}")
print(f"  📊 RESULTADOS DEL BACKTEST — ICT + VOLUME PROFILE")
print(f"{'='*65}")

if t_df.empty:
    print("  ❌ No se generaron trades. Revisando condiciones...")
else:
    total  = len(t_df)
    wins   = len(t_df[t_df['result'] == 'WIN'])
    losses = len(t_df[t_df['result'] == 'LOSS'])
    flats  = len(t_df[t_df['result'] == 'FLAT'])
    
    wr = wins / total * 100 if total > 0 else 0
    avg_win  = t_df[t_df['result'] == 'WIN']['pnl_pts'].mean()
    avg_loss = t_df[t_df['result'] == 'LOSS']['pnl_pts'].mean()
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # Por setup
    buy_trades  = t_df[t_df['setup'] == 'BUY']
    sell_trades = t_df[t_df['setup'] == 'SELL']
    
    buy_wr  = len(buy_trades[buy_trades['result']  == 'WIN']) / len(buy_trades)  * 100 if len(buy_trades)  > 0 else 0
    sell_wr = len(sell_trades[sell_trades['result'] == 'WIN']) / len(sell_trades) * 100 if len(sell_trades) > 0 else 0
    
    print(f"\n  🎯 Trades Totales:  {total}")
    print(f"      ✅ Wins:         {wins}  ({wr:.1f}%)")
    print(f"      ❌ Losses:       {losses}")
    print(f"      ↔️  Flats:        {flats}")
    print(f"\n  📈 BUY  setups:    {len(buy_trades)}  → WR: {buy_wr:.1f}%")
    print(f"  📉 SELL setups:    {len(sell_trades)} → WR: {sell_wr:.1f}%")
    print(f"\n  💰 Promedio WIN:   +{avg_win:.0f} puntos NQ")
    print(f"  💸 Promedio LOSS:  {avg_loss:.0f} puntos NQ")
    print(f"  ⚖️  Ratio RR real:  1:{rr:.2f}")
    
    # Guardar trades
    t_df.to_csv(os.path.join(BASE_DIR, "ict_profile_trades.csv"), index=False)
    
    # JSON resumen
    summary = {
        "strategy": "ICT + Volume Profile",
        "backtest_period": "2 años NQ=F horario",
        "total_trades": int(total),
        "win_rate": round(wr, 1),
        "buy_wr": round(buy_wr, 1),
        "sell_wr": round(sell_wr, 1),
        "avg_win_pts": round(float(avg_win), 1) if not np.isnan(avg_win) else 0,
        "avg_loss_pts": round(float(avg_loss), 1) if not np.isnan(avg_loss) else 0,
        "rr_ratio": round(rr, 2),
        "logic": "NY abre fuera del Value Area de Asia + Londres sweepea extremo → entrada retorno al POC"
    }
    
    with open(os.path.join(BASE_DIR, "ict_profile_strategy.json"), "w") as f:
        json.dump(summary, f, indent=4)
    
    print(f"\n✅ Trades guardados: ict_profile_trades.csv")
    print(f"✅ Resumen en:       ict_profile_strategy.json")

print(f"\n  📅 Días saltados (sin datos suficientes): {skipped}")
