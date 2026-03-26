"""
Verificacion definitiva: el VA en el CSV es del mismo dia o del anterior?
"""
import csv

rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv')))
rows.sort(key=lambda r: r['date'])

print("Secuencia val/vah: cada dia vs el dia anterior")
print(f"{'date':<14} {'val_today':>12} {'vah_today':>12} {'val_prev_day':>14} {'vah_prev_day':>14}")
print("-" * 68)
for i in range(1, 8):
    today = rows[i]
    prev  = rows[i-1]
    print(f"{today['date']:<14} {today['val']:>12} {today['vah']:>12} {prev['val']:>14} {prev['vah']:>14}")

print()
print("Si val_today != val_prev_day en todos los casos, cada dia tiene")
print("su propio VA (computed de ese dia mismo) --> LOOK-AHEAD BIAS")
print()
print("=" * 68)
print("CONCLUSION DEL CAMPO pm_open_pos:")
print("pm_open ocurre 3am-9:30am.")
print("El VA (val/vah) es el de la sesion NY del DIA ACTUAL (9:30am-4pm).")
print("Por lo tanto usar val/vah del MISMO DIA para clasificar pm_open = LOOK-AHEAD")
print()
print("SIN EMBARGO, veamos que dice el script que computo pm_open_pos...")
# Buscar en todos los scripts Python si hay logica de shift
import os
for fname in sorted(os.listdir('.')):
    if not fname.endswith('.py'):
        continue
    try:
        content = open(fname, encoding='utf-8', errors='ignore').read()
        if 'pm_open_pos' in content and ('shift' in content or 'prev' in content or 'anterior' in content):
            print(f"SCRIPT RELEVANTE: {fname}")
            # Mostrar lineas con pm_open_pos
            for i, line in enumerate(content.split('\n'), 1):
                if 'pm_open_pos' in line or 'shift' in line.lower():
                    print(f"  L{i}: {line.strip()}")
    except Exception:
        pass
