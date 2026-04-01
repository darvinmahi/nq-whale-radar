import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    rows = []
    for r in csv.DictReader(f):
        try:
            com_s = int(r.get('Dealer_Positions_Short_All') or 0)
            d = r['Report_Date_as_MM_DD_YYYY'].strip()
            if com_s: rows.append({'date':d,'com_s':com_s})
        except: pass
rows.sort(key=lambda x: x['date'])
changes = []
for i in range(1, len(rows)):
    delta = rows[i]['com_s'] - rows[i-1]['com_s']
    changes.append({'date':rows[i]['date'],'com_s':rows[i]['com_s'],'change':delta})
last156 = changes[-156:]
vals = [x['change'] for x in last156]
ch_min, ch_max = min(vals), max(vals)
curr = changes[-1]
fi = (ch_max - curr['change']) / (ch_max - ch_min) * 100
fi = round(max(0, min(100, fi)), 1)
action = 'Compraron' if curr['change'] < 0 else 'Vendieron'
print(f"COM Short actual:   {curr['com_s']:,}")
print(f"Cambio esta semana: {curr['change']:+,}")
print(f"Min 3 anos:         {ch_min:+,}")
print(f"Max 3 anos:         {ch_max:+,}")
print(f"Flow Index:         {fi:.1f}/100")
print(f"Fecha:              {curr['date']}")
print(f"Accion:             {action} {abs(curr['change']):,} contratos")
