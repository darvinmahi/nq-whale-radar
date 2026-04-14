import pandas as pd
import datetime
import json

TARGET_DATES = [
    '2024-04-25',   # Jueves BULL
    '2024-05-09',   # Jueves BEAR
    '2024-04-16',   # Martes BULL
]

print("Cargando CSV 5m...")
df = pd.read_csv('data/research/nq_5m_polygon.csv')
df['Datetime_ET'] = pd.to_datetime(df['Datetime_ET'])

output = []

for target in TARGET_DATES:
    date = datetime.date.fromisoformat(target)
    day_df = df[df['Datetime_ET'].dt.date == date].copy()
    
    # Ventana: 9:25 AM a 10:35 AM (velas del drama real)
    window = day_df[
        (day_df['Datetime_ET'].dt.time >= datetime.time(9, 25)) &
        (day_df['Datetime_ET'].dt.time <= datetime.time(10, 35))
    ].copy()
    
    _930 = day_df[day_df['Datetime_ET'].dt.time == datetime.time(9, 30)]
    _1000 = day_df[day_df['Datetime_ET'].dt.time == datetime.time(10, 0)]
    
    if _930.empty or _1000.empty or window.empty:
        print(f"SKIP: {target} - datos insuficientes")
        continue
    
    o930 = float(_930.iloc[0]['Open'])
    o1000 = float(_1000.iloc[0]['Open'])
    is_long = o1000 > o930
    pb = round(o1000 - 20, 2) if is_long else round(o1000 + 20, 2)
    tp = round(pb + 20, 2) if is_long else round(pb - 20, 2)
    sl = round(pb - 20, 2) if is_long else round(pb + 20, 2)
    
    day_map = {0:'Lunes',1:'Martes',2:'Miercoles',3:'Jueves',4:'Viernes'}
    dow = day_map[date.weekday()]
    
    candles = []
    for _, row in window.iterrows():
        candles.append({
            't': row['Datetime_ET'].strftime('%H:%M'),
            'o': round(float(row['Open']), 2),
            'h': round(float(row['High']), 2),
            'l': round(float(row['Low']), 2),
            'c': round(float(row['Close']), 2),
        })
    
    example = {
        'date': target,
        'dow': dow,
        'o930': round(o930, 2),
        'o1000': round(o1000, 2),
        'is_long': int(is_long),
        'direction': 'BULL' if is_long else 'BEAR',
        'pb': pb,
        'tp': tp,
        'sl': sl,
        'candles': candles
    }
    output.append(example)
    
    print(f"\n{target} ({dow}):")
    print(f"  Open 9:30={o930:.2f} | Open 10:00={o1000:.2f} | {'BULL' if is_long else 'BEAR'}")
    print(f"  PB Entry={pb:.2f} | TP={tp:.2f} | SL={sl:.2f}")
    print(f"  Velas extraidas: {len(candles)}")
    for c in candles:
        tag = " <-- BIAS 10AM" if c['t']=='10:00' else ""
        pb_hit = (" <-- !!! PULLBACK HIT !!!" if (is_long and c['l'] <= pb) or (not is_long and c['h'] >= pb) else "")
        tp_hit = (" <-- !!! TP HIT !!!" if (is_long and c['h'] >= tp) or (not is_long and c['l'] <= tp) else "")
        print(f"    {c['t']}  O:{c['o']:.2f}  H:{c['h']:.2f}  L:{c['l']:.2f}  C:{c['c']:.2f}{tag}{pb_hit}{tp_hit}")

with open('data/research/real_candles_3days.json', 'w') as f:
    json.dump(output, f, indent=2)
print(f"\n✓ Guardado en data/research/real_candles_3days.json")
