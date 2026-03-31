import csv
from datetime import date
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d  = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            rows.append({'date':d,'long':ll,'short':ls,'net':ll-ls})
        except:
            pass

rows.sort(key=lambda x: x['date'])

# COT Index = percentil de la posicion neta en ventana de 3 años (156 semanas)
for i, r in enumerate(rows):
    hist = [x['net'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = (r['net'] - mn) / (mx - mn) * 100 if mx > mn else 50.0

print(f"  {'Fecha':<14} {'Long':>10} {'Short':>10} {'Net':>10} {'COT Index':>10}")
print("  " + "-"*55)
for r in rows[-8:]:
    blen = int(r['ci'] / 5)
    bar  = "=" * blen
    print(f"  {str(r['date']):<14} {r['long']:>10,} {r['short']:>10,} {r['net']:>10,}   {r['ci']:>5.1f}%  {bar}")

last = rows[-1]
prev = rows[-2]
delta = last['ci'] - prev['ci']

print()
print(f"  ULTIMO REPORTE : {last['date']}")
print(f"  COT Index      : {last['ci']:.1f}%  (semana anterior: {prev['ci']:.1f}%  delta: {delta:+.1f}%)")
print(f"  Net position   : {last['net']:,}")
print(f"  Long           : {last['long']:,}")
print(f"  Short          : {last['short']:,}")

if last['ci'] < 30:
    print("  Señal          : << MUY BEARISH — institucionales vendiendo fuerte")
elif last['ci'] < 50:
    print("  Señal          :  < BEARISH — institucionales en zona baja")
elif last['ci'] < 70:
    print("  Señal          :  > BULLISH — institucionales acumulando")
else:
    print("  Señal          : >> MUY BULLISH — institucionales comprando fuerte")
