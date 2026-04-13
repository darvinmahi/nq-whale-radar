import csv
from datetime import datetime, timedelta, date

target = date(2026, 3, 23)
count = 0
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        dt_str = r['Datetime'].replace('+00:00','')
        raw = datetime.fromisoformat(dt_str)
        et4 = raw - timedelta(hours=4)
        et5 = raw - timedelta(hours=5)
        if et4.date() == target and count < 10:
            print(f"UTC={raw.strftime('%H:%M')} ET-4={et4.strftime('%H:%M')} ET-5={et5.strftime('%H:%M')} O={r['Open']}")
            count += 1
        if et5.date() == target and count < 10:
            print(f"UTC={raw.strftime('%H:%M')} ET-4={et4.strftime('%H:%M')} ET-5={et5.strftime('%H:%M')} O={r['Open']}")
            count += 1
