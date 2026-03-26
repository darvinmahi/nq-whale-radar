"""
DEBUG: Entender exactamente qué es pm_lo, pm_hi, pm_close en el CSV
"""
import csv

rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv', encoding='utf-8')))
rows.sort(key=lambda r: r['date'])

# Examinar un día específico para verificar
print("=== VERIFICACION DE CAMPOS ===\n")
print("Campos del CSV:")
print(list(rows[0].keys()))
print()

# Tomar 5 dias y mostrar todos los datos
for r in rows[:5]:
    print(f"Fecha: {r['date']} ({r['weekday']})")
    print(f"  pm_open={r['pm_open']}  pm_close={r['pm_close']}  pm_hi={r['pm_hi']}  pm_lo={r['pm_lo']}")
    print(f"  pm_direction={r['pm_direction']}  pm_range={r['pm_range']}")
    print(f"  ny_open_price={r['ny_open_price']}  ny_open_pos={r['ny_open_pos']}")
    print(f"  val={r['val']}  vah={r['vah']}  va_range={r['va_range']}")
    print()

# La pregunta: pm_close es el close de NY (4pm) o el close del premarket (9:30)?
# Si pm_close = close de toda la sesion del dia (incluyendo NY), tiene valor
# Si pm_close = solo premarket (antes de NY open), es inutil para el backtest
#
# Verificar: si pm_close = NY close, entonces deberia ser similar al close de ese dia
# Verificar: si pm_hi/pm_lo incluyen la sesion NY o solo premarket
#
# La clave: pm_direction = BULLISH si pm_close > pm_open
# Y el nombre "pm" puede significar:
#   a) Pre-Market (3am-9:30am)
#   b) Post-Market (cierre NY y algo mas)
#   c) Toda la sesion del dia (24 horas)

print("=== CALCULANDO pm_range manualmente ===")
print("pm_range deberia ser pm_hi - pm_lo\n")
for r in rows[:5]:
    pm_hi  = float(r['pm_hi'])
    pm_lo  = float(r['pm_lo'])
    pm_rng = float(r['pm_range'])
    calc   = round(pm_hi - pm_lo, 2)
    match  = "OK" if abs(calc - pm_rng) < 2 else "DIFERENTE!"
    print(f"  {r['date']}: pm_hi-pm_lo={calc}  pm_range={pm_rng}  [{match}]")
    print(f"           ny_open={r['ny_open_price']}  pm_hi={pm_hi}  pm_lo={pm_lo}")
    print(f"           ¿pm_hi > ny_open?: {pm_hi > float(r['ny_open_price'])}")
    print()

print("=== CONCLUSIÓN ===")
print("Si pm_hi > ny_open en algunos casos, entonces pm incluye la sesion NY")
print("(de lo contrario pm seria solo el premarket y terminaria ANTES del ny_open)")
above_ny = sum(1 for r in rows if float(r['pm_hi']) > float(r['ny_open_price']))
below_ny = sum(1 for r in rows if float(r['pm_hi']) < float(r['ny_open_price']))
print(f"pm_hi > ny_open: {above_ny} dias")
print(f"pm_hi < ny_open: {below_ny} dias")
print()
# Si pm incluye toda la sesion (incluyendo NY), entonces:
# pm_close = cierre de la sesion completa del dia
# pm_hi = high de todo el dia
# pm_lo = low de todo el dia
# Esto es correcto para el backtest (podemos saber si el target/stop fue tocado)
