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
    return centers[hi_i], poc, centers[li]

all_days  = df.index.normalize().unique()
thursdays = sorted([d for d in all_days if d.weekday() == 3])
last_40   = [t for t in thursdays[-40:] if len(df[df.index.normalize() == t]) >= 50]

results = []

for thu in last_40:
    prev = thu - timedelta(days=1)

    # VP Asia 18:00 prev → 9:20 ET
    try:
        s = ET.localize(datetime(prev.year, prev.month, prev.day, 18, 0))
        e = ET.localize(datetime(thu.year, thu.month, thu.day, 9, 20))
        vp_df = df[(df.index >= s) & (df.index <= e)]
    except:
        vp_df = pd.DataFrame()
    vah, poc, val = calc_vp(vp_df)

    day_df = df[df.index.normalize() == thu]

    # Precio apertura 9:30
    p930 = day_df[(day_df.index.hour == 9) & (day_df.index.minute >= 30)]
    if p930.empty: continue
    open_930 = float(p930.iloc[0]['Open'])

    # Posición vs Value Area
    if vah is not None:
        if open_930 > vah:     pos = 'SOBRE_VAH'
        elif open_930 < val:   pos = 'BAJO_VAL'
        else:                  pos = 'DENTRO_VA'
    else:
        pos = 'SIN_VP'

    # Movimiento 9:30→10:00
    p10 = day_df[(day_df.index.hour == 10) & (day_df.index.minute == 0)]
    p945 = day_df[(day_df.index.hour == 9) & (day_df.index.minute == 45)]
    if not p10.empty:
        close_10 = float(p10.iloc[-1]['Close'])
    elif not p945.empty:
        close_10 = float(p945.iloc[-1]['Close'])
    else:
        continue

    first_move = round(close_10 - open_930, 0)
    if abs(first_move) < 20: continue

    main_dir = 'UP' if first_move > 0 else 'DOWN'

    # Filtro VP: alineación dirección con posición
    # UP + BAJO_VAL = alineado (rebote alcista fuera de VA)
    # DOWN + SOBRE_VAH = alineado (rechazo bajista fuera de VA)
    # Cualquier otro = no alineado
    if pos == 'BAJO_VAL' and main_dir == 'UP':
        vp_filter = 'ALINEADO'
    elif pos == 'SOBRE_VAH' and main_dir == 'DOWN':
        vp_filter = 'ALINEADO'
    elif pos == 'DENTRO_VA':
        vp_filter = 'DENTRO'
    else:
        vp_filter = 'CONTRA_VP'

    # Retroceso 10:00→10:45
    retrace_df = day_df[
        (day_df.index.hour == 10) & (day_df.index.minute <= 45)
    ]
    if retrace_df.empty: continue

    if main_dir == 'UP':
        retrace_low  = float(retrace_df['Low'].min())
        retrace_pts  = round(close_10 - retrace_low, 0)
        retrace_pct  = round(retrace_pts / abs(first_move) * 100, 0)
        entry = retrace_low
    else:
        retrace_high = float(retrace_df['High'].max())
        retrace_pts  = round(retrace_high - close_10, 0)
        retrace_pct  = round(retrace_pts / abs(first_move) * 100, 0)
        entry = retrace_high

    # Resultado post-10:45 → 15:00
    post_df = day_df[
        ((day_df.index.hour == 10) & (day_df.index.minute > 45)) |
        ((day_df.index.hour >= 11) & (day_df.index.hour < 15))
    ]
    if post_df.empty: continue

    if main_dir == 'UP':
        continuation = round(float(post_df['High'].max()) - entry, 0)
        adverso      = round(entry - float(post_df['Low'].min()), 0)
    else:
        continuation = round(entry - float(post_df['Low'].min()), 0)
        adverso      = round(float(post_df['High'].max()) - entry, 0)

    result = 'WIN' if continuation >= 50 else ('LOSS' if adverso >= 80 else 'NEUTRAL')

    results.append({
        'Date':         str(thu.date()),
        'Pos_VP':       pos,
        'VP_Filter':    vp_filter,
        'Main_Dir':     main_dir,
        'First_Move':   first_move,
        'Retrace_Pts':  retrace_pts,
        'Retrace_Pct':  retrace_pct,
        'Continuation': continuation,
        'Adverso':      adverso,
        'Result':       result,
    })

res = pd.DataFrame(results)
n = len(res)

print(f'=== 10am PULLBACK + FILTRO VP — 40 JUEVES ===')
print(f'Total dias con movimiento claro: {n}')
print()

for label, sub in [('TODOS', res),
                   ('ALINEADO (fuera VA + dir correcta)', res[res['VP_Filter']=='ALINEADO']),
                   ('DENTRO VA', res[res['VP_Filter']=='DENTRO']),
                   ('CONTRA VP', res[res['VP_Filter']=='CONTRA_VP'])]:
    nn = len(sub)
    if nn == 0: continue
    w = (sub['Result']=='WIN').sum()
    l = (sub['Result']=='LOSS').sum()
    neu = (sub['Result']=='NEUTRAL').sum()
    print(f'  [{label}]  n={nn}')
    print(f'    WIN={w} ({w/nn*100:.0f}%)  LOSS={l} ({l/nn*100:.0f}%)  NEUTRAL={neu} ({neu/nn*100:.0f}%)')
    if nn > 0:
        wins_df = sub[sub['Result']=='WIN']
        print(f'    Continuación prom WIN: {wins_df["Continuation"].mean():.0f} pts')
    print()

print('── TABLA COMPLETA ──')
print(res[['Date','Pos_VP','VP_Filter','Main_Dir','First_Move','Retrace_Pts','Continuation','Adverso','Result']].to_string(index=False))
