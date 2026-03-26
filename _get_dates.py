import re
from datetime import datetime, timedelta

with open('daily_dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

dates = sorted(set(re.findall(r'date:"(\d{4}-\d{2}-\d{2})"', content)))
cutoff = datetime(2026, 3, 25) - timedelta(days=60)
recent = [d for d in dates if datetime.strptime(d, '%Y-%m-%d') >= cutoff]
old    = [d for d in dates if datetime.strptime(d, '%Y-%m-%d') < cutoff]

print('RECIENTES:', len(recent))
for d in recent:
    print(d)
print()
print('ANTIGUAS:', len(old))
for d in old:
    print(d)
