import yfinance as yf, pytz
from datetime import datetime, date, time as dtime

ET = pytz.timezone('America/New_York')
df = yf.download('NQ=F', period='5d', interval='15m', progress=False, auto_adjust=True)
if hasattr(df.columns, 'get_level_values'): df.columns = df.columns.get_level_values(0)
df.index = df.index.tz_convert(ET)

target = date(2026, 4, 9)
day_df = df[df.index.date == target].copy()
print(f'April 9 bars: {len(day_df)}')

if len(day_df) > 0:
    print(f'First: {day_df.index[0]}  Open={day_df.iloc[0]["Open"]:.0f}')
    print(f'Last:  {day_df.index[-1]}  Close={day_df.iloc[-1]["Close"]:.0f}')

    or_bars = day_df[(day_df.index.time >= dtime(9,30)) & (day_df.index.time <= dtime(9,59))]
    print(f'\nOR bars (9:30-10:00): {len(or_bars)}')
    if len(or_bars) > 0:
        or_high  = float(or_bars['High'].max())
        or_low   = float(or_bars['Low'].min())
        or_open  = float(or_bars.iloc[0]['Open'])
        or_close = float(or_bars.iloc[-1]['Close'])
        or_dir   = 'BULL' if or_close > or_open else 'BEAR'
        or_range = or_high - or_low
        print(f'OR HIGH:  {or_high:.0f}')
        print(f'OR LOW:   {or_low:.0f}')
        print(f'OR Range: {or_range:.0f} pts')
        print(f'OR Dir:   {or_dir}  (open={or_open:.0f}  close={or_close:.0f})')

    ny_bars = day_df[(day_df.index.time >= dtime(9,30)) & (day_df.index.time <= dtime(16,0))]
    if len(ny_bars) > 1:
        ny_open  = float(ny_bars.iloc[0]['Open'])
        ny_close = float(ny_bars.iloc[-1]['Close'])
        ny_high  = float(ny_bars['High'].max())
        ny_low   = float(ny_bars['Low'].min())
        ny_move  = ny_close - ny_open
        ny_dir   = 'BULL' if ny_move > 0 else 'BEAR'
        print(f'\nNY Session:')
        print(f'  Open:  {ny_open:.0f}')
        print(f'  Close: {ny_close:.0f}')
        print(f'  High:  {ny_high:.0f}')
        print(f'  Low:   {ny_low:.0f}')
        print(f'  Move:  {ny_move:+.0f} pts')
        print(f'  Dir:   {ny_dir}')

    print('\n--- ALL 15min BARS ---')
    for idx, row in day_df.iterrows():
        marker = ''
        if dtime(9,30) <= idx.time() <= dtime(9,59): marker = '  <<< OR ZONE'
        print(f'{idx.strftime("%H:%M")}  O={row["Open"]:.0f} H={row["High"]:.0f} L={row["Low"]:.0f} C={row["Close"]:.0f}{marker}')
else:
    print('No data for April 9 - trying April 8')
    target2 = date(2026, 4, 8)
    day_df2 = df[df.index.date == target2].copy()
    print(f'April 8 bars: {len(day_df2)}')
    for idx, row in day_df2.iterrows():
        print(f'{idx.strftime("%H:%M")}  O={row["Open"]:.0f} H={row["High"]:.0f} L={row["Low"]:.0f} C={row["Close"]:.0f}')
