import json
from datetime import datetime

with open('data/research/backtest_5dias_6meses.json', encoding='utf-8') as f:
    d = json.load(f)

def week_of_month(date_str):
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    w = (dt.day - 1) // 7 + 1
    return min(w, 4)  # semana 5 (dia 29-31) -> semana 4

WEEKLY_EVENTS = {
    1: 'ISM Mfg/Svcs + NFP (viernes)',
    2: 'CPI + PPI + Consumer Sentiment',
    3: 'FOMC / Fed Decision + Retail Sales',
    4: 'GDP / PCE / Core PCE / Durable Goods',
}

print('=== NEWS_DRIVE por semana del mes ===')
print()

for dia, info in d['by_day'].items():
    nd_sessions = [s for s in info['sessions_detail'] if s['pattern'] == 'NEWS_DRIVE']
    if not nd_sessions:
        continue
    print(f'--- {dia} ({len(nd_sessions)} NEWS_DRIVE) ---')
    weeks_count = {1:0, 2:0, 3:0, 4:0}
    for s in nd_sessions:
        w = week_of_month(s['date'])
        weeks_count[w] += 1
        arrow = 'BULL' if s['direction'] == 'BULLISH' else 'BEAR'
        date = s['date']
        rng  = s['ny_range']
        print(f'  {date}  [SEMANA {w}]  {arrow}  rango={rng}pts')
    print(f'  Dist: S1={weeks_count[1]}  S2={weeks_count[2]}  S3={weeks_count[3]}  S4={weeks_count[4]}')
    print()

print('=== RESUMEN GLOBAL NEWS_DRIVE por semana del mes ===')
total = {1:[], 2:[], 3:[], 4:[]}
for dia, info in d['by_day'].items():
    for s in info['sessions_detail']:
        if s['pattern'] == 'NEWS_DRIVE':
            w = week_of_month(s['date'])
            total[w].append(s['direction'])

for w, dirs in total.items():
    n = len(dirs)
    bull = dirs.count('BULLISH')
    bear = dirs.count('BEARISH')
    pct  = round(bull/n*100) if n else 0
    evento = WEEKLY_EVENTS[w]
    print(f'  Semana {w}: {n} sesiones | BULL={bull} BEAR={bear} ({pct}% bull) | {evento}')
