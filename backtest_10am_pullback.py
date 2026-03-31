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

    # Movimiento principal: 9:30 → 10:00 (primera media hora NY)
    move_df = day_df[
        ((day_df.index.hour == 9) & (day_df.index.minute >= 30)) |
        (day_df.index.hour == 10 & (day_df.index.minute == 0))
    ]
    # Más simple: precio 9:30 y precio 10:00
    p930 = day_df[(day_df.index.hour == 9) & (day_df.index.minute >= 30)]
    p10  = day_df[(day_df.index.hour == 10) & (day_df.index.minute == 0)]
    p10b = day_df[(day_df.index.hour == 9) & (day_df.index.minute == 45)]  # fallback

    if p930.empty:
        continue
    open_930 = float(p930.iloc[0]['Open'])

    # Precio a las ~10:00 (primer movimiento establecido)
    if not p10.empty:
        close_10 = float(p10.iloc[-1]['Close'])
    elif not p10b.empty:
        close_10 = float(p10b.iloc[-1]['Close'])
    else:
        continue

    first_move = round(close_10 - open_930, 0)

    if abs(first_move) < 20:   # sin movimiento claro, skip
        continue

    main_dir = 'UP' if first_move > 0 else 'DOWN'

    # Retroceso entre 10:00 y 10:45
    retrace_df = day_df[
        (day_df.index.hour == 10) &
        (day_df.index.minute >= 0) &
        (day_df.index.minute <= 45)
    ]

    if retrace_df.empty:
        continue

    if main_dir == 'UP':
        retrace_low  = float(retrace_df['Low'].min())
        retrace_pts  = round(close_10 - retrace_low, 0)  # cuánto retrocedió
        retrace_pct  = round(retrace_pts / abs(first_move) * 100, 0)
        # Entrada en el retroceso: low de 10am zone
        entry = retrace_low
    else:
        retrace_high = float(retrace_df['High'].max())
        retrace_pts  = round(retrace_high - close_10, 0)
        retrace_pct  = round(retrace_pts / abs(first_move) * 100, 0)
        entry = retrace_high

    # Resultado post-10:45 hasta 15:00
    post_df = day_df[
        ((day_df.index.hour == 10) & (day_df.index.minute > 45)) |
        ((day_df.index.hour >= 11) & (day_df.index.hour < 15))
    ]

    if post_df.empty:
        continue

    if main_dir == 'UP':
        high_post = float(post_df['High'].max())
        low_post  = float(post_df['Low'].min())
        continuation = round(high_post - entry, 0)   # si sigue para arriba
        adverso      = round(entry - low_post, 0)    # si baja en contra
    else:
        high_post = float(post_df['High'].max())
        low_post  = float(post_df['Low'].min())
        continuation = round(entry - low_post, 0)    # si sigue para abajo
        adverso      = round(high_post - entry, 0)   # si sube en contra

    result = 'WIN' if continuation >= 50 else ('LOSS' if adverso >= 80 else 'NEUTRAL')

    results.append({
        'Date':        str(thu.date()),
        'Open_930':    round(open_930, 1),
        'Close_10':    round(close_10, 1),
        'First_Move':  first_move,
        'Main_Dir':    main_dir,
        'Retrace_Pts': retrace_pts,
        'Retrace_Pct': retrace_pct,
        'Entry':       round(entry, 1),
        'Continuation':continuation,
        'Adverso':     adverso,
        'Result':      result,
    })

res = pd.DataFrame(results)
n = len(res)

wins    = (res['Result'] == 'WIN').sum()
losses  = (res['Result'] == 'LOSS').sum()
neutral = (res['Result'] == 'NEUTRAL').sum()

print(f'=== BACKTEST RETROCESO 10AM EN JUEVES ===')
print(f'Total jueves con movimiento claro (>20 pts a las 10am): {n}')
print()
print(f'WIN     (continua >50 pts):  {wins}/{n}  = {wins/n*100:.0f}%')
print(f'LOSS    (adverso >80 pts):   {losses}/{n} = {losses/n*100:.0f}%')
print(f'NEUTRAL (ni uno ni otro):    {neutral}/{n} = {neutral/n*100:.0f}%')
print()
print(f'Retroceso promedio del movimiento: {res["Retrace_Pct"].mean():.0f}%  ({res["Retrace_Pts"].mean():.0f} pts)')
print(f'Retroceso mediana:                 {res["Retrace_Pct"].median():.0f}%  ({res["Retrace_Pts"].median():.0f} pts)')
print(f'Continuación promedio (WIN days):  {res[res["Result"]=="WIN"]["Continuation"].mean():.0f} pts')
print(f'Adverso promedio (LOSS days):      {res[res["Result"]=="LOSS"]["Adverso"].mean():.0f} pts')
print()
print('── TABLA COMPLETA ──')
print(res[['Date','Main_Dir','First_Move','Retrace_Pts','Retrace_Pct','Continuation','Adverso','Result']].to_string(index=False))
