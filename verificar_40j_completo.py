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
    return round(centers[hi_i], 0), round(poc, 0), round(centers[li], 0)

all_days  = df.index.normalize().unique()
thursdays = sorted([d for d in all_days if d.weekday() == 3])
last_40   = [t for t in thursdays[-40:] if len(df[df.index.normalize() == t]) >= 50]

results = []

for thu in last_40:
    prev = thu - timedelta(days=1)
    try:
        s = ET.localize(datetime(prev.year, prev.month, prev.day, 18, 0))
        e = ET.localize(datetime(thu.year, thu.month, thu.day, 9, 20))
        vp_df = df[(df.index >= s) & (df.index <= e)]
    except:
        vp_df = pd.DataFrame()
    vah, poc, val = calc_vp(vp_df)

    day_df = df[df.index.normalize() == thu]
    p930 = day_df[(day_df.index.hour == 9) & (day_df.index.minute >= 30)]
    if p930.empty: continue
    open_930 = round(float(p930.iloc[0]['Open']), 0)

    if vah is not None:
        if open_930 > vah:   pos = 'SOBRE_VAH'
        elif open_930 < val: pos = 'BAJO_VAL'
        else:                pos = 'DENTRO_VA'
    else:
        pos = 'SIN_VP'

    p10  = day_df[(day_df.index.hour == 10) & (day_df.index.minute == 0)]
    p945 = day_df[(day_df.index.hour == 9) & (day_df.index.minute == 45)]
    if not p10.empty:
        close_10 = round(float(p10.iloc[-1]['Close']), 0)
    elif not p945.empty:
        close_10 = round(float(p945.iloc[-1]['Close']), 0)
    else:
        close_10 = open_930

    first_move = close_10 - open_930
    if abs(first_move) < 20:
        main_dir = 'FLAT'
    else:
        main_dir = 'UP' if first_move > 0 else 'DOWN'

    if main_dir == 'FLAT':
        vp_filter = 'FLAT'
    elif pos == 'BAJO_VAL' and main_dir == 'UP':
        vp_filter = 'ALINEADO'
    elif pos == 'SOBRE_VAH' and main_dir == 'DOWN':
        vp_filter = 'ALINEADO'
    elif pos == 'DENTRO_VA':
        vp_filter = 'DENTRO'
    else:
        vp_filter = 'CONTRA_VP'

    retrace_df = day_df[(day_df.index.hour == 10) & (day_df.index.minute <= 45)]
    post_df = day_df[
        ((day_df.index.hour == 10) & (day_df.index.minute > 45)) |
        ((day_df.index.hour >= 11) & (day_df.index.hour < 15))
    ]

    if main_dir in ('UP', 'DOWN') and not retrace_df.empty and not post_df.empty:
        if main_dir == 'UP':
            entry        = round(float(retrace_df['Low'].min()), 0)
            retrace_pts  = round(close_10 - entry, 0)
            continuation = round(float(post_df['High'].max()) - entry, 0)
            adverso      = round(entry - float(post_df['Low'].min()), 0)
        else:
            entry        = round(float(retrace_df['High'].max()), 0)
            retrace_pts  = round(entry - close_10, 0)
            continuation = round(entry - float(post_df['Low'].min()), 0)
            adverso      = round(float(post_df['High'].max()) - entry, 0)
        result = 'WIN' if continuation >= 50 else ('LOSS' if adverso >= 80 else 'NEUT')
    else:
        retrace_pts = 0; entry = open_930; continuation = 0; adverso = 0
        result = 'SKIP'

    results.append({
        'Fecha':      str(thu.date()),
        'Pos_VP':     pos,
        'Filter':     vp_filter,
        'Dir':        main_dir,
        'Mov930':     int(first_move),
        'Pullback':   int(retrace_pts),
        'Cont':       int(continuation),
        'Adv':        int(adverso),
        'Result':     result,
    })

res = pd.DataFrame(results)
n = len(res)

print(f'=== VERIFICACION COMPLETA 40 JUEVES ===')
print(f'Total jueves analizados: {n}')
print()
print(f'{"Fecha":<12} {"Pos_VP":<11} {"Filter":<11} {"Dir":<5} {"Mov930":>7} {"Pullback":>9} {"Cont":>6} {"Adv":>5}  Result')
print('─' * 90)

for _, r in res.iterrows():
    icon = {'WIN':'✅','LOSS':'❌','NEUT':'⚪','SKIP':'─','FLAT':'─'}.get(r['Result'],'?')
    print(f"{r['Fecha']:<12} {r['Pos_VP']:<11} {r['Filter']:<11} {r['Dir']:<5} {r['Mov930']:>7} {r['Pullback']:>9}  {r['Cont']:>5}  {r['Adv']:>4}  {icon} {r['Result']}")

print()
print('=== RESUMEN POR FILTRO ===')
for filt in ['ALINEADO','DENTRO','CONTRA_VP','FLAT','SKIP']:
    sub = res[res['Filter'] == filt]
    if len(sub) == 0: continue
    w = (sub['Result']=='WIN').sum()
    l = (sub['Result']=='LOSS').sum()
    nn = len(sub)
    valid = sub[sub['Result'].isin(['WIN','LOSS','NEUT'])]
    nv = len(valid)
    wv = (valid['Result']=='WIN').sum()
    print(f"  {filt:<12}: {nn} días | WIN={wv}/{nv} ({wv/nv*100:.0f}% de válidos) | LOSS={l} | cont.prom={valid['Cont'].mean():.0f}pts")
