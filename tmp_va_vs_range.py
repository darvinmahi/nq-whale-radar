import csv
rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv')))
print('Fecha         | Range dia total | VA range | VA es % del dia')
print('-'*65)
for r in rows[:20]:
    try:
        prof = float(r['prof_range'])
        va   = float(r['va_range'])
        pct  = va/prof*100
        bar = "█" * int(pct/5)
        print(f"{r['date']:<14}| {prof:>15.0f} pts | {va:>8.1f} pts | {pct:.0f}%  {bar}")
    except:
        pass
print()
import statistics
va_ranges = [float(r['va_range']) for r in rows]
prof_ranges = [float(r['prof_range']) for r in rows]
print(f"PROMEDIO VA range   : {statistics.mean(va_ranges):.0f} pts")
print(f"PROMEDIO Range dia  : {statistics.mean(prof_ranges):.0f} pts")
print(f"VA es en promedio   : {statistics.mean(va_ranges)/statistics.mean(prof_ranges)*100:.0f}% del día")
print(f"VA < 100 pts        : {sum(1 for v in va_ranges if v<100)} dias ({sum(1 for v in va_ranges if v<100)/len(va_ranges)*100:.0f}%)")
print(f"VA < 150 pts        : {sum(1 for v in va_ranges if v<150)} dias ({sum(1 for v in va_ranges if v<150)/len(va_ranges)*100:.0f}%)")
