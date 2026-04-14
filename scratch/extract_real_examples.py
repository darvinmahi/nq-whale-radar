import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pandas as pd
import datetime
import json

SL_PTS = 20
TP_PTS = 20
PB_PTS = 20

print("Cargando datos reales...")
df = pd.read_csv('data/research/nq_5m_polygon.csv')
df['Datetime_ET'] = pd.to_datetime(df['Datetime_ET'])
df = df.sort_values('Datetime_ET').reset_index(drop=True)

days = df['Datetime_ET'].dt.date.unique()
day_map = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri'}
day_name_es = {'Mon': 'LUNES', 'Tue': 'MARTES', 'Wed': 'MIERCOLES', 'Thu': 'JUEVES', 'Fri': 'VIERNES'}

winners = []

for date in days:
    day_df = df[df['Datetime_ET'].dt.date == date].copy()
    dow = date.weekday()
    if dow not in day_map: continue
    day_str = day_map[dow]
    
    _930 = day_df[day_df['Datetime_ET'].dt.time == datetime.time(9, 30)]
    _1000 = day_df[day_df['Datetime_ET'].dt.time == datetime.time(10, 0)]
    
    if _930.empty or _1000.empty: continue
    
    open_930 = _930.iloc[0]['Open']
    open_1000 = _1000.iloc[0]['Open']
    is_long = open_1000 > open_930
    
    trade_df = day_df[day_df['Datetime_ET'].dt.time >= datetime.time(10, 0)].copy()
    pb_entry = open_1000 - PB_PTS if is_long else open_1000 + PB_PTS
    
    pb_hit = False
    pb_time = None
    tp_time = None
    sl_time = None
    
    for idx, row in trade_df.iterrows():
        if not pb_hit:
            if is_long and row['Low'] <= pb_entry:
                pb_hit = True
                pb_time = row['Datetime_ET']
                pb_trade_df = trade_df.loc[idx:]
                continue
            elif not is_long and row['High'] >= pb_entry:
                pb_hit = True
                pb_time = row['Datetime_ET']
                pb_trade_df = trade_df.loc[idx:]
                continue
        else:
            if is_long:
                if row['Low'] <= pb_entry - SL_PTS:
                    sl_time = row['Datetime_ET']
                    break
                if row['High'] >= pb_entry + TP_PTS:
                    tp_time = row['Datetime_ET']
                    break
            else:
                if row['High'] >= pb_entry + SL_PTS:
                    sl_time = row['Datetime_ET']
                    break
                if row['Low'] <= pb_entry - TP_PTS:
                    tp_time = row['Datetime_ET']
                    break
    
    if pb_hit and tp_time and not sl_time:
        # Extraemos velas del dia (9:30 a 13:00 max)
        velas = day_df[
            (day_df['Datetime_ET'].dt.time >= datetime.time(9, 30)) & 
            (day_df['Datetime_ET'].dt.time <= datetime.time(13, 0))
        ][['Datetime_ET','Open','High','Low','Close']].copy()
        velas['time_str'] = velas['Datetime_ET'].dt.strftime('%H:%M')
        
        winners.append({
            'date': str(date),
            'day': day_str,
            'day_es': day_name_es[day_str],
            'open_930': round(open_930, 2),
            'open_1000': round(open_1000, 2),
            'is_long': int(is_long),
            'direction': 'BULL' if is_long else 'BEAR',
            'pb_entry': round(pb_entry, 2),
            'tp_target': round(pb_entry + TP_PTS if is_long else pb_entry - TP_PTS, 2),
            'sl_level': round(pb_entry - SL_PTS if is_long else pb_entry + SL_PTS, 2),
            'pb_time': str(pb_time.time().strftime('%H:%M')),
            'tp_time': str(tp_time.time().strftime('%H:%M')),
            'candles': velas[['time_str','Open','High','Low','Close']].round(2).to_dict('records')
        })

# Tomar 3 buenos ejemplos (un jueves, un martes, un viernes)
thu_examples = [w for w in winners if w['day'] == 'Thu'][:2]
tue_examples = [w for w in winners if w['day'] == 'Tue'][:1]
examples = thu_examples + tue_examples

print(f"\nEjemplos encontrados: {len(winners)} ganadores totales")
for ex in examples:
    print(f"\n{'='*60}")
    print(f"FECHA: {ex['date']} ({ex['day_es']})")
    print(f"Apertura 9:30 -> {ex['open_930']}")
    print(f"Apertura 10:00 -> {ex['open_1000']} ({ex['direction']})")
    print(f"Orden Limit puesta en -> {ex['pb_entry']}")
    print(f"Executed PB a las -> {ex['pb_time']}")
    print(f"TP alcanzado a las -> {ex['tp_time']}")
    print(f"Ganancia = +$200 x 20 cuentas = +$4,000")

with open('data/research/real_examples.json', 'w') as f:
    json.dump(examples, f, indent=2)
print(f"\nDatos guardados en data/research/real_examples.json")
