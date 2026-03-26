"""
BACKTEST: pm_open_pos × Día de la semana
¿Lunes, Martes, Miércoles, Jueves, Viernes — cuál tiene mejor win rate?
"""
import csv
from collections import defaultdict

rows = list(csv.DictReader(open("ny_profile_asia_london_daily.csv")))

# Día de semana de la columna 'weekday'
DIAS = ["LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES"]
DIAS_ES = {"LUNES":"Lunes","MARTES":"Martes","MIÉRCOLES":"Miércoles",
           "JUEVES":"Jueves","VIERNES":"Viernes"}

def evaluar_trade(r, direccion):
    try:
        ny_open  = float(r["ny_open_price"])
        vah      = float(r["vah"])
        val      = float(r["val"])
        va_range = float(r["va_range"])
        pm_hi    = float(r["pm_hi"])
        pm_lo    = float(r["pm_lo"])
        pm_close = float(r["pm_close"])
    except:
        return None, 0

    if va_range <= 0:
        return None, 0

    if direccion == "LONG":
        entrada  = ny_open
        target   = vah if ny_open < vah else vah + va_range * 0.5
        stop     = val - va_range * 0.10
        riesgo   = max(entrada - stop, 1)
        potencial= target - entrada
        if pm_lo <= stop and pm_hi >= target:
            return "LOSS", round(-riesgo, 1)
        elif pm_lo <= stop:
            return "LOSS", round(-riesgo, 1)
        elif pm_hi >= target:
            return "WIN", round(potencial, 1)
        else:
            diff = pm_close - entrada
            return ("PARTIAL_WIN" if diff > 0 else "PARTIAL_LOSS"), round(diff, 1)
    else:
        entrada  = ny_open
        target   = val if ny_open > val else val - va_range * 0.5
        stop     = vah + va_range * 0.10
        riesgo   = max(stop - entrada, 1)
        potencial= entrada - target
        if pm_hi >= stop and pm_lo <= target:
            return "LOSS", round(-riesgo, 1)
        elif pm_hi >= stop:
            return "LOSS", round(-riesgo, 1)
        elif pm_lo <= target:
            return "WIN", round(potencial, 1)
        else:
            diff = entrada - pm_close
            return ("PARTIAL_WIN" if diff > 0 else "PARTIAL_LOSS"), round(diff, 1)

SEP = "=" * 65
print(f"\n{SEP}")
print("  BACKTEST: pm_open_pos × DÍA DE LA SEMANA")
print(f"{SEP}\n")

# Tabla resumen
print(f"  {'Día':<12} {'Pos':<10} {'N':>4} {'WIN%':>6} {'Pts/trade':>10} {'Total pts':>10}")
print(f"  {'─'*55}")

resumen_global = []

for dia in DIAS:
    for pos, direc in [("ABOVE_VA","LONG"), ("BELOW_VA","SHORT")]:
        dias_fil = [r for r in rows if r["weekday"]==dia and r["pm_open_pos"]==pos]
        if not dias_fil:
            continue
        resultados = []
        pts_total = 0
        for r in dias_fil:
            res, pts = evaluar_trade(r, direc)
            if res:
                resultados.append(res)
                pts_total += pts
        n = len(resultados)
        if n == 0:
            continue
        wins = sum(1 for x in resultados if "WIN" in x)
        wr = wins/n*100
        ppt = pts_total/n
        dia_es = DIAS_ES[dia]
        bar_wr = "▓" * int(wr/10) + "░" * (10 - int(wr/10))
        print(f"  {dia_es:<12} {pos:<10} {n:>4}  {bar_wr} {wr:>4.0f}%  {ppt:>+9.1f}  {pts_total:>+9.1f}")
        resumen_global.append((dia_es, pos, direc, n, wr, ppt, pts_total))

print(f"\n{SEP}")
print("  TOP 5 SETUPS MÁS RENTABLES (por pts/trade)")
print(f"{SEP}\n")
top = sorted(resumen_global, key=lambda x: -x[5])[:5]
print(f"  {'Día':<12} {'Setup':<11} {'N':>4} {'Win%':>6} {'Pts/trade':>10}")
print(f"  {'─'*45}")
for r in top:
    print(f"  {r[0]:<12} {r[1]:<11} {r[3]:>4} {r[4]:>5.0f}%  {r[5]:>+9.1f}")

print(f"\n{SEP}")
print("  TABLA COMPLETA: WIN RATE POR DÍA (ABOVE + BELOW combinado)")
print(f"{SEP}\n")
print(f"  {'Día':<12} {'Trades':>7} {'Win rate':>9} {'Pts total':>10} {'Pts/trade':>10}")
print(f"  {'─'*52}")
for dia in DIAS:
    all_res = []
    all_pts = 0
    for pos, direc in [("ABOVE_VA","LONG"),("BELOW_VA","SHORT")]:
        dias_fil = [r for r in rows if r["weekday"]==dia and r["pm_open_pos"]==pos]
        for r in dias_fil:
            res, pts = evaluar_trade(r, direc)
            if res:
                all_res.append(res)
                all_pts += pts
    n = len(all_res)
    if n:
        wr = sum(1 for x in all_res if "WIN" in x)/n*100
        print(f"  {DIAS_ES[dia]:<12} {n:>7} {wr:>8.0f}%  {all_pts:>+9.1f}  {all_pts/n:>+9.1f}")

print(f"\n{SEP}\n")
