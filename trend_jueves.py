import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

ET = pytz.timezone('America/New_York')
df = pd.read_csv('data/research/nq_15m_intraday.csv', index_col=0, parse_dates=True)
df.index = pd.to_datetime(df.index, utc=True).tz_convert(ET)
df = df.sort_index()

all_days  = df.index.normalize().unique()
thursdays = sorted([d for d in all_days if d.weekday() == 3])
last_40   = [t for t in thursdays[-40:] if len(df[df.index.normalize() == t]) >= 50]

results = []
for thu in last_40:
    day_df = df[df.index.normalize() == thu]
    ny_df  = day_df[
        (day_df.index.hour >= 9) &
        ~((day_df.index.hour == 9) & (day_df.index.minute < 30)) &
        (day_df.index.hour < 16)
    ]
    if len(ny_df) < 4:
        continue

    ny_open  = float(ny_df.iloc[0]['Open'])
    ny_close = float(ny_df.iloc[-1]['Close'])
    ny_high  = float(ny_df['High'].max())
    ny_low   = float(ny_df['Low'].min())
    ny_move  = round(ny_close - ny_open, 0)
    ny_range = round(ny_high - ny_low, 0)
    ratio    = round(abs(ny_move) / ny_range, 2) if ny_range > 0 else 0
    
    if ratio >= 0.50:
        tipo = 'TREND'
    elif ratio <= 0.25:
        tipo = 'CHOP'
    else:
        tipo = 'MIXTO'

    results.append({
        'Date': str(thu.date()),
        'Move': ny_move,
        'Range': ny_range,
        'Ratio': ratio,
        'Tipo': tipo
    })

res = pd.DataFrame(results)
n = len(res)

print(f'Total jueves: {n}')
print()
trend = (res['Tipo'] == 'TREND').sum()
mixto = (res['Tipo'] == 'MIXTO').sum()
chop  = (res['Tipo'] == 'CHOP').sum()

print(f'TREND  (ratio>=0.50):  {trend}/{n} = {trend/n*100:.0f}%   ← mercado tomó dirección y no giró')
print(f'MIXTO  (0.25-0.50):    {mixto}/{n} = {mixto/n*100:.0f}%   ← partial trend / pullback')
print(f'CHOP   (ratio<0.25):   {chop}/{n}  = {chop/n*100:.0f}%    ← compra y vende, cierra donde abrió')
print()

print('── DIAS TREND ──')
print(res[res['Tipo'] == 'TREND'][['Date', 'Move', 'Range', 'Ratio']].to_string(index=False))
print()
print('── DIAS CHOP ──')
print(res[res['Tipo'] == 'CHOP'][['Date', 'Move', 'Range', 'Ratio']].to_string(index=False))
print()

# Rango promedio por tipo
for t in ['TREND', 'MIXTO', 'CHOP']:
    sub = res[res['Tipo'] == t]
    if len(sub) > 0:
        print(f'{t} - Rango promedio: {sub["Range"].mean():.0f} pts | Move promedio: {sub["Move"].abs().mean():.0f} pts')
