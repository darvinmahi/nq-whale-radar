import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd

CSV = 'data/research/nq_5m_polygon.csv'
df = pd.read_csv(CSV)
df['et'] = pd.to_datetime(df['Datetime_ET'])
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time
df['dow'] = df['et'].dt.weekday

targets = {
    0: 'BULL', # Lunes
    1: 'BULL', # Martes
    3: 'BEAR', # Jueves
    4: 'BEAR'  # Viernes
}

results = []

for dow, target_dir in targets.items():
    subset = df[df['dow'] == dow]
    
    lunch_pts = []
    close_pts = []
    win_lunch = 0
    win_close = 0
    total = 0
    
    for d in subset['date'].unique():
        day = subset[subset['date'] == d].copy()
        day.set_index('et', inplace=True)
        
        o30 = day.between_time('09:30', '09:59')
        if len(o30) < 5: continue
        
        o_open = o30.iloc[0]['Open']
        o_close = o30.iloc[-1]['Close']
        o_mv = o_close - o_open
        
        o_dir = 'BULL' if o_mv > 0 else 'BEAR'
        if o_dir != target_dir: continue # Solo tomamos los días que nos dan la señal
        
        # Entry at 10:00
        core = day.between_time('10:00', '15:59')
        if len(core) < 10: continue
        
        entry = core.iloc[0]['Open']
        
        # Extremos para el Stop Loss
        sl_bull = o30['Low'].min()
        sl_bear = o30['High'].max()
        
        # Simulamos operacion 
        # Exit at Lunch (12:00 PM)
        lunch_data = day.between_time('10:00', '11:59')
        if len(lunch_data) > 0:
            lunch_exit = lunch_data.iloc[-1]['Close']
            
            # Chequeamos si toco stop loss antes del lunch
            hit_sl = False
            for idx, row in lunch_data.iterrows():
                if target_dir == 'BULL' and row['Low'] < sl_bull: hit_sl = True; break
                if target_dir == 'BEAR' and row['High'] > sl_bear: hit_sl = True; break
                
            if hit_sl:
                # Perdimos
                val = sl_bull - entry if target_dir == 'BULL' else entry - sl_bear
                lunch_pts.append(val)
            else:
                val = lunch_exit - entry if target_dir == 'BULL' else entry - lunch_exit
                lunch_pts.append(val)
                if val > 0: win_lunch += 1
                
        # Exit at Close (16:00 PM)
        close_data = day.between_time('10:00', '15:59')
        if len(close_data) > 0:
            close_exit = close_data.iloc[-1]['Close']
            
            hit_sl = False
            for idx, row in close_data.iterrows():
                if target_dir == 'BULL' and row['Low'] < sl_bull: hit_sl = True; break
                if target_dir == 'BEAR' and row['High'] > sl_bear: hit_sl = True; break
                
            if hit_sl:
                val = sl_bull - entry if target_dir == 'BULL' else entry - sl_bear
                close_pts.append(val)
            else:
                val = close_exit - entry if target_dir == 'BULL' else entry - close_exit
                close_pts.append(val)
                if val > 0: win_close += 1
                
        total += 1
        
    avg_l = sum(lunch_pts)/len(lunch_pts) if lunch_pts else 0
    avg_c = sum(close_pts)/len(close_pts) if close_pts else 0
    acc_l = win_lunch / total * 100 if total > 0 else 0
    acc_c = win_close / total * 100 if total > 0 else 0
    
    results.append({
        'DOW': dow,
        'DIR': target_dir,
        'N': total,
        'Acc Lunch (12pm)': acc_l,
        'Avg Pts Lunch': avg_l,
        'Acc Close (4pm)': acc_c,
        'Avg Pts Close': avg_c
    })

print(pd.DataFrame(results).to_string())
