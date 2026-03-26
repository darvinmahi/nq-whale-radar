"""
AUDIT del backtest: verificar si la logica es correcta
Revisar fila por fila el trade del dia real para ver si hay look-ahead bias u otros problemas
"""
import csv

rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv')))
print("=" * 70)
print("AUDITORIA: columnas del CSV y que significan")
print("=" * 70)
# Mostrar headers
print("COLUMNAS:", list(rows[0].keys()))
print()

# Tomar un jueves BELOW_VA y mostrar TODOS sus datos crudos
print("=" * 70)
print("FILA CRUDA — Jueves 2 Oct 2025 (el trade que backtestamos)")
print("=" * 70)
for r in rows:
    if r['date'] == '2025-10-02':
        for k, v in r.items():
            print(f"  {k:<30} = {v}")
        break

print()
print("=" * 70)
print("PREGUNTA CLAVE: cuando pm_open_pos='BELOW_VA'")
print("¿El vah/val son del DIA ANTERIOR o del MISMO dia?")
print("=" * 70)
# Ver dia anterior al 2 oct (1 oct = martes)
print("Dia anterior (2025-10-01):")
for r in rows:
    if r['date'] == '2025-10-01':
        print(f"  vah={r['vah']}  val={r['val']}  va_range={r['va_range']}")
        print(f"  ny_open={r['ny_open_price']}")
        break
print("Dia 2025-10-02:")
for r in rows:
    if r['date'] == '2025-10-02':
        print(f"  vah={r['vah']}  val={r['val']}  va_range={r['va_range']}")
        print(f"  ny_open={r['ny_open_price']}")
        break

print()
print("=" * 70)
print("VERIFICACION: el pm_open_pos indica que el pm_open estuvo")
print("DEBAJO del VAL — revisemos si eso es verdad:")
print("=" * 70)
for r in rows:
    if r['date'] == '2025-10-02':
        pm_open = float(r['pm_open'])
        val = float(r['val'])
        vah = float(r['vah'])
        ny_open = float(r['ny_open_price'])
        print(f"  pm_open = {pm_open}")
        print(f"  val     = {val}")
        print(f"  vah     = {vah}")
        print(f"  ny_open = {ny_open}")
        print(f"  pm_open < val? {pm_open < val} (deberia ser True para BELOW_VA)")
        print(f"  ny_open > vah? {ny_open > vah} (abrio ARRIBA del VAH!)")
        print(f"  pm_open_pos = {r['pm_open_pos']}")
        break

print()
print("PROBLEMA DETECTADO? Si ny_open abrio ARRIBA del VAH pero pm_open")
print("estuvo abajo del VAL... hay una contradiccion logica?")
print()
print("=" * 70)
print("REVISION DE TODOS LOS JUEVES BELOW_VA: pm_open vs ny_open")
print("=" * 70)
print(f"{'Fecha':<14} {'pm_open':>10} {'val':>10} {'vah':>10} {'ny_open':>10} {'pm_open<val':>12} {'ny_open>vah':>12}")
print("-" * 78)
for r in rows:
    if r['weekday'] == 'JUEVES' and r['pm_open_pos'] == 'BELOW_VA':
        pm_open = float(r['pm_open'])
        val = float(r['val'])
        vah = float(r['vah'])
        ny_open = float(r['ny_open_price'])
        below = pm_open < val
        above_vah = ny_open > vah
        flag = " <-- ?" if above_vah else ""
        print(f"{r['date']:<14} {pm_open:>10.1f} {val:>10.1f} {vah:>10.1f} {ny_open:>10.1f} {str(below):>12} {str(above_vah):>12}{flag}")
