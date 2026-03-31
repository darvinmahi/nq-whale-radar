import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

ET = pytz.timezone('America/New_York')
df = pd.read_csv('data/research/nq_15m_intraday.csv', index_col=0, parse_dates=True)
df.index = pd.to_datetime(df.index, utc=True).tz_convert(ET)
df = df.sort_index()

VP_BINS = 50
def calc_vp(sl):
    if sl.empty or len(sl) < 2: return None, None, None
    lo, hi = sl['Low'].min(), sl['High'].max()
    if hi == lo: return None, None, None
    edges = np.linspace(lo, hi, VP_BINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols = np.zeros(VP_BINS)
    for _, row in sl.iterrows():
        mask = (centers >= float(row['Low'])) & (centers <= float(row['High']))
        c = mask.sum()
        if c > 0: vols[mask] += 1.0 / c
    poc_i = int(np.argmax(vols))
    poc = centers[poc_i]
    total = vols.sum(); target = total * 0.70
    li = hi_i = poc_i; acc = vols[poc_i]
    while acc < target and (li > 0 or hi_i < VP_BINS - 1):
        la = vols[li-1] if li > 0 else 0
        ha = vols[hi_i+1] if hi_i < VP_BINS-1 else 0
        if la >= ha and li > 0: li -= 1; acc += la
        elif hi_i < VP_BINS - 1: hi_i += 1; acc += ha
        else: break
    return round(centers[hi_i], 1), round(poc, 1), round(centers[li], 1)

all_days  = df.index.normalize().unique()
thursdays = sorted([d for d in all_days if d.weekday() == 3])
last_40   = [t for t in thursdays[-40:] if len(df[df.index.normalize() == t]) >= 50]

print('=== VERIFICACION REAL: SETUP ALINEADO 10am PULLBACK ===')
print('Setup: Precio fuera Value Area + movimiento confirma dirección + pullback 10am')
print()
print(f'{"Fecha":<12} {"Setup":<18} {"VAH/VAL":<8} {"Open930":<9} {"10am":<8} {"Pullback":<10} {"Entry":<8} {"Post10:45":<12} {"Resultado":<10}')
print('─' * 110)

count = 0
wins = 0

for thu in last_40:
    prev = thu - timedelta(days=1)
    try:
        s = ET.localize(datetime(prev.year, prev.month, prev.day, 18, 0))
        e = ET.localize(datetime(thu.year, thu.month, thu.day, 9, 20))
        vp_df = df[(df.index >= s) & (df.index <= e)]
    except:
        vp_df = pd.DataFrame()
    vah, poc, val = calc_vp(vp_df)
    if vah is None: continue

    day_df = df[df.index.normalize() == thu]
    p930 = day_df[(day_df.index.hour == 9) & (day_df.index.minute >= 30)]
    if p930.empty: continue
    open_930 = round(float(p930.iloc[0]['Open']), 1)

    if open_930 > vah:     pos = 'SOBRE_VAH'
    elif open_930 < val:   pos = 'BAJO_VAL'
    else:                  continue  # solo fuera de VA

    p10 = day_df[(day_df.index.hour == 10) & (day_df.index.minute == 0)]
    p945 = day_df[(day_df.index.hour == 9) & (day_df.index.minute == 45)]
    if not p10.empty:
        close_10 = round(float(p10.iloc[-1]['Close']), 1)
    elif not p945.empty:
        close_10 = round(float(p945.iloc[-1]['Close']), 1)
    else:
        continue

    first_move = close_10 - open_930
    if abs(first_move) < 20: continue

    main_dir = 'UP' if first_move > 0 else 'DOWN'

    # Solo ALINEADO
    if pos == 'BAJO_VAL' and main_dir != 'UP': continue
    if pos == 'SOBRE_VAH' and main_dir != 'DOWN': continue

    setup_label = 'BAJO_VAL→UP' if pos == 'BAJO_VAL' else 'SOBRE_VAH→DN'
    ref_level = val if pos == 'BAJO_VAL' else vah

    retrace_df = day_df[(day_df.index.hour == 10) & (day_df.index.minute <= 45)]
    if retrace_df.empty: continue

    if main_dir == 'UP':
        entry = round(float(retrace_df['Low'].min()), 1)
        retrace_pts = round(close_10 - entry, 0)
    else:
        entry = round(float(retrace_df['High'].max()), 1)
        retrace_pts = round(entry - close_10, 0)

    post_df = day_df[
        ((day_df.index.hour == 10) & (day_df.index.minute > 45)) |
        ((day_df.index.hour >= 11) & (day_df.index.hour < 15))
    ]
    if post_df.empty: continue

    if main_dir == 'UP':
        best_post = round(float(post_df['High'].max()), 1)
        continuation = round(best_post - entry, 0)
        worst_post = round(float(post_df['Low'].min()), 1)
        adverso = round(entry - worst_post, 0)
    else:
        best_post = round(float(post_df['Low'].min()), 1)
        continuation = round(entry - best_post, 0)
        worst_post = round(float(post_df['High'].max()), 1)
        adverso = round(worst_post - entry, 0)

    win = continuation >= 50
    result_str = f'✅ +{int(continuation)}pts' if win else f'❌ -{int(adverso)}pts'
    if win: wins += 1
    count += 1

    print(f'{str(thu.date()):<12} {setup_label:<18} {ref_level:<8} {open_930:<9} {close_10:<8} -{retrace_pts}pts{"":<4} {entry:<8} +{int(continuation)}→-{int(adverso):<7} {result_str}')

print()
print(f'TOTAL ALINEADO: {wins}/{count} WIN = {wins/count*100:.0f}%')
print()
print('Columnas: VAH/VAL=nivel clave VP | Open930=precio apertura NY | 10am=precio a las 10 |')
print('          Pullback=cuanto retrocedió | Entry=precio entrada | Post10:45=mejor/peor despues')
