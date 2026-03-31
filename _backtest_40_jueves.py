import pandas as pd
import numpy as np

df = pd.read_csv('data/research/nq_15m_intraday.csv', index_col=0, parse_dates=True)
df.index = pd.to_datetime(df.index, utc=True)

days = df.index.normalize().unique()
thursdays = sorted([d for d in days if d.weekday() == 3])
last_40 = thursdays[-40:]
valid = [t for t in last_40 if len(df[df.index.normalize() == t]) >= 50]
print(f'Jueves validos: {len(valid)}')

results = []
for thu in valid:
    day_df = df[df.index.normalize() == thu].sort_index()

    pre = day_df[day_df.index.hour < 14]
    ny  = day_df[(day_df.index.hour >= 14) & (day_df.index.hour < 21)]

    if len(ny) < 5:
        continue

    pre_h = pre['High'].max() if not pre.empty else np.nan
    pre_l = pre['Low'].min()  if not pre.empty else np.nan
    asia  = day_df[day_df.index.hour >= 18]
    asia_h = asia['High'].max() if not asia.empty else np.nan
    asia_l = asia['Low'].min()  if not asia.empty else np.nan

    ny_open  = ny['Open'].iloc[0]
    ny_high  = ny['High'].max()
    ny_low   = ny['Low'].min()
    ny_close = ny['Close'].iloc[-1]
    direction = 'UP' if ny_close > ny_open else 'DOWN'
    rng = round(ny_high - ny_low, 2)

    results.append({
        'Date': str(thu.date()),
        'NY_Open': round(ny_open, 2),
        'NY_High': round(ny_high, 2),
        'NY_Low':  round(ny_low, 2),
        'NY_Close': round(ny_close, 2),
        'Direction': direction,
        'Range_pts': rng,
        'Break_PreHigh': bool(ny_high > pre_h) if not np.isnan(pre_h) else False,
        'Break_PreLow':  bool(ny_low < pre_l)  if not np.isnan(pre_l) else False,
    })

res = pd.DataFrame(results)
print(res.to_string(index=False))
print()
up   = (res['Direction'] == 'UP').sum()
down = (res['Direction'] == 'DOWN').sum()
print(f'UP: {up} ({up/len(res)*100:.0f}%)  DOWN: {down} ({down/len(res)*100:.0f}%)')
print(f'Avg Range NY: {res["Range_pts"].mean():.1f} pts')
print(f'Median Range: {res["Range_pts"].median():.1f} pts')
print(f'Break Pre-High: {res["Break_PreHigh"].sum()} / {len(res)}')
print(f'Break Pre-Low:  {res["Break_PreLow"].sum()} / {len(res)}')
