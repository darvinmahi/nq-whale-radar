import pandas as pd
import datetime

# Constantes financieras
SL_PTS = 20
TP_PTS = 20
PULLBACK_PTS = 10

print("Cargando 39,000 velas de 5m (nq_5m_polygon.csv)...")
df = pd.read_csv('data/research/nq_5m_polygon.csv')
df['Datetime_ET'] = pd.to_datetime(df['Datetime_ET'])
df = df.sort_values('Datetime_ET').reset_index(drop=True)

days = df['Datetime_ET'].dt.date.unique()
print(f"Total de dias a procesar: {len(days)}")

results = {
    'PB_10': {'Mon': {'W':0,'L':0,'S':0}, 'Tue': {'W':0,'L':0,'S':0}, 'Wed': {'W':0,'L':0,'S':0}, 'Thu': {'W':0,'L':0,'S':0}, 'Fri': {'W':0,'L':0,'S':0}},
    'PB_15': {'Mon': {'W':0,'L':0,'S':0}, 'Tue': {'W':0,'L':0,'S':0}, 'Wed': {'W':0,'L':0,'S':0}, 'Thu': {'W':0,'L':0,'S':0}, 'Fri': {'W':0,'L':0,'S':0}},
    'PB_20': {'Mon': {'W':0,'L':0,'S':0}, 'Tue': {'W':0,'L':0,'S':0}, 'Wed': {'W':0,'L':0,'S':0}, 'Thu': {'W':0,'L':0,'S':0}, 'Fri': {'W':0,'L':0,'S':0}},
}

day_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}

def sim_trade(entry_price, sl_price, tp_price, is_long, df_slice):
    for _, row in df_slice.iterrows():
        low = row['Low']
        high = row['High']
        
        hit_sl = False
        hit_tp = False
        
        if is_long:
            if low <= sl_price: hit_sl = True
            if high >= tp_price: hit_tp = True
        else:
            if high >= sl_price: hit_sl = True
            if low <= tp_price: hit_tp = True
            
        # Si choca con ambos en la MISMA vela de 5 minutos, sumimos lo PEOR (Pérdida), 
        # esto garantiza un backtest súper conservador.
        if hit_sl and hit_tp: return 'L'
        elif hit_sl: return 'L'
        elif hit_tp: return 'W'
        
    return 'S' # Fin del día sin tocar nada

for date in days:
    day_df = df[df['Datetime_ET'].dt.date == date].copy()
    _930 = day_df[day_df['Datetime_ET'].dt.time == datetime.time(9, 30)]
    _1000 = day_df[day_df['Datetime_ET'].dt.time == datetime.time(10, 0)]
    
    if _930.empty or _1000.empty:
        continue
        
    open_930 = _930.iloc[0]['Open']
    open_1000 = _1000.iloc[0]['Open']
    direction = "BULL" if open_1000 > open_930 else "BEAR"
    
    # OR Range
    or_df = day_df[(day_df['Datetime_ET'].dt.time >= datetime.time(9, 30)) & 
                   (day_df['Datetime_ET'].dt.time < datetime.time(10, 0))]
    or_high = or_df['High'].max()
    or_low = or_df['Low'].min()
    
    # Velas desde las 10:00 (Trade zone)
    trade_df = day_df[day_df['Datetime_ET'].dt.time >= datetime.time(10, 0)]
    
    day_str = day_map[date.weekday()]
    if day_str in ['Sat', 'Sun']: continue
    
    is_long = (direction == "BULL")

    for pb_pts, strat_key in [(10, 'PB_10'), (15, 'PB_15'), (20, 'PB_20')]:
        pb_hit = False
        pb_idx = -1
        pb_entry = open_1000 - pb_pts if is_long else open_1000 + pb_pts
        
        for idx, row in trade_df.iterrows():
            if is_long and row['Low'] <= pb_entry:
                pb_hit = True; pb_idx = idx; break
            elif not is_long and row['High'] >= pb_entry:
                pb_hit = True; pb_idx = idx; break
                
        if not pb_hit:
            results[strat_key][day_str]['S'] += 1
        else:
            pb_trade_df = trade_df.loc[pb_idx:]
            if is_long:
                resB = sim_trade(pb_entry, pb_entry - SL_PTS, pb_entry + TP_PTS, True, pb_trade_df)
            else:
                resB = sim_trade(pb_entry, pb_entry + SL_PTS, pb_entry - TP_PTS, False, pb_trade_df)
            results[strat_key][day_str][resB] += 1

print("\n================ RESULTADOS POR DIA Y PULLBACK (SL=20, TP=20) ===============")

for strat_key in ['PB_10', 'PB_15', 'PB_20']:
    print(f"\n--- Estrategia: {strat_key} (Pullback de {strat_key.split('_')[1]} pts) ---")
    for d in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']:
        r = results[strat_key][d]
        tot = r['W'] + r['L']
        wr = (r['W'] / tot * 100) if tot > 0 else 0
        pf = (r['W'] * 200 * 20) - (r['L'] * 200 * 20)
        print(f"{d} -> WR: {wr:>5.2f}% | Ganadas: {r['W']:>3}, Perdidas: {r['L']:>3} | Skipped: {r['S']:>2} | Profit(20cts): ${pf:,.2f}")
