import csv
rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv', encoding='utf-8')))
rows.sort(key=lambda r: r['date'])

print("Verificando prof_hi/prof_lo vs ny_open:")
for row in rows[:8]:
    ny_open = float(row['ny_open_price'])
    prof_hi = float(row['prof_hi'])
    prof_lo = float(row['prof_lo'])
    above = "YES" if prof_hi > ny_open else "no"
    below = "YES" if prof_lo < ny_open else "no"
    print(f"  {row['date']}: ny_open={ny_open:.1f}  prof_lo={prof_lo:.1f}  prof_hi={prof_hi:.1f}  prof_hi>ny_open:{above}  prof_lo<ny_open:{below}")

above_count = sum(1 for r in rows if float(r['prof_hi']) > float(r['ny_open_price']))
below_count = sum(1 for r in rows if float(r['prof_lo']) < float(r['ny_open_price']))
print(f"\nprof_hi > ny_open: {above_count}/{len(rows)}")
print(f"prof_lo < ny_open: {below_count}/{len(rows)}")
print("\nSi prof incluye toda la session NY, prof_lo o prof_hi deberian exceder ny_open")
print("en la mayoria de dias.")
print()

# Verificar si close_above_va y close_below_va dan informacion del cierre real
close_fields = ['close_above_va', 'close_below_va', 'close_inside', 'val', 'vah']
print("Campos de cierre disponibles:")
r0 = rows[0]
for f in close_fields:
    print(f"  {f}: {r0.get(f, 'NO EXISTE')}")
