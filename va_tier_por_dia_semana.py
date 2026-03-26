"""
Análisis: VA Tier (<100 / 100-150 / >150) cruzado con:
  - Día de semana (Lunes–Viernes)
  - Semana del mes (1ª, 2ª, 3ª, 4ª)

Métrica principal: cuando el precio LLEGA al VAL, ¿lo respeta (no rompe)?
"""
import csv
from datetime import datetime
from collections import defaultdict

def get_week_of_month(date_str):
    """Semana del mes: 1=primera semana, 4=cuarta semana"""
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return (d.day - 1) // 7 + 1

def va_tier(va_range):
    if va_range < 100:
        return "TIER1 (<100)"
    elif va_range <= 150:
        return "TIER2 (100-150)"
    else:
        return "TIER3 (>150)"

rows = []
with open("ny_profile_asia_london_daily.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

print(f"\n{'='*65}")
print(f"  ANÁLISIS: VA TIER × DÍA DE SEMANA × SEMANA DEL MES")
print(f"  Total días: {len(rows)}")
print(f"{'='*65}\n")

# ──────────────────────────────────────────────────────────────
# SECCIÓN 1: Por DÍA DE SEMANA × VA TIER
# Métrica: touches_val=True → breaks_val=True (falló) vs False (aguantó)
# ──────────────────────────────────────────────────────────────
print("1) VAL RESPETADO vs ROTO — por DÍA DE SEMANA y VA TIER")
print("   (solo días donde el precio tocó el VAL)\n")

DIAS = ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES"]
TIERS = ["TIER1 (<100)","TIER2 (100-150)","TIER3 (>150)"]

# {dia: {tier: [breaks_val]}}
dia_tier = defaultdict(lambda: defaultdict(list))
for r in rows:
    if r["touches_val"] == "True":
        d = r["weekday"]
        t = va_tier(float(r["va_range"]))
        broke = r["breaks_val"] == "True"
        dia_tier[d][t].append(broke)

header = f"{'Día':<12} | {'TIER1(<100)':^16} | {'TIER2(100-150)':^16} | {'TIER3(>150)':^16}"
print(header)
print("-"*65)
for dia in DIAS:
    row_str = f"{dia:<12} |"
    for tier in TIERS:
        lst = dia_tier[dia][tier]
        if lst:
            n = len(lst)
            respeta = sum(1 for x in lst if not x)
            pct = respeta/n*100
            row_str += f" {respeta}/{n}={pct:4.0f}% aguanta |"
        else:
            row_str += f"{'  n/a':^18}|"
    print(row_str)

print()

# Totales por tier (todos los días)
print("   Totales generales por TIER (todos los días):")
tier_total = defaultdict(list)
for r in rows:
    if r["touches_val"] == "True":
        t = va_tier(float(r["va_range"]))
        tier_total[t].append(r["breaks_val"] == "True")

for t in TIERS:
    lst = tier_total[t]
    if lst:
        n = len(lst)
        respeta = sum(1 for x in lst if not x)
        pct = respeta/n*100
        barra = "█" * int(pct/5)
        print(f"  {t:<18}: {respeta:>2}/{n:>2} = {pct:5.1f}% aguanta  {barra}")

print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 2: Por SEMANA DEL MES × VA TIER
# ──────────────────────────────────────────────────────────────
print("2) VAL RESPETADO vs ROTO — por SEMANA DEL MES y VA TIER\n")

sem_tier = defaultdict(lambda: defaultdict(list))
sem_count = defaultdict(int)
for r in rows:
    sem = get_week_of_month(r["date"])
    sem_count[sem] += 1
    if r["touches_val"] == "True":
        t = va_tier(float(r["va_range"]))
        broke = r["breaks_val"] == "True"
        sem_tier[sem][t].append(broke)

SEM_NOMBRES = {1:"1ª semana", 2:"2ª semana", 3:"3ª semana", 4:"4ª semana"}
header2 = f"{'Semana':<12} | {'TIER1(<100)':^16} | {'TIER2(100-150)':^16} | {'TIER3(>150)':^16} | Total días"
print(header2)
print("-"*75)
for sem in sorted(sem_tier.keys()):
    nombre = SEM_NOMBRES.get(sem, f"Sem {sem}")
    row_str = f"{nombre:<12} |"
    for tier in TIERS:
        lst = sem_tier[sem][tier]
        if lst:
            n = len(lst)
            respeta = sum(1 for x in lst if not x)
            pct = respeta/n*100
            row_str += f" {respeta}/{n}={pct:4.0f}% aguanta |"
        else:
            row_str += f"{'  n/a':^18}|"
    row_str += f"  {sem_count[sem]} días"
    print(row_str)

print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 3: VA TIER — distribución por día de semana
# ¿Qué días tienen más días TIER1 (señal limpia)?
# ──────────────────────────────────────────────────────────────
print("3) DISTRIBUCIÓN DE TIER por DÍA DE SEMANA")
print("   (¿Qué día es más probable tener VA limpio <100 pts?)\n")

dia_tier_count = defaultdict(lambda: defaultdict(int))
dia_total = defaultdict(int)
for r in rows:
    d = r["weekday"]
    t = va_tier(float(r["va_range"]))
    dia_tier_count[d][t] += 1
    dia_total[d] += 1

header3 = f"{'Día':<12} | {'TIER1(<100)':^14} | {'TIER2(100-150)':^14} | {'TIER3(>150)':^14} | Total"
print(header3)
print("-"*70)
for dia in DIAS:
    n  = dia_total[dia]
    t1 = dia_tier_count[dia]["TIER1 (<100)"]
    t2 = dia_tier_count[dia]["TIER2 (100-150)"]
    t3 = dia_tier_count[dia]["TIER3 (>150)"]
    print(f"{dia:<12} | {t1:>4} ({t1/n*100:3.0f}%)      | {t2:>4} ({t2/n*100:3.0f}%)      | {t3:>4} ({t3/n*100:3.0f}%)      | {n}")

print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 4: ¿Qué VA TIER tiene mejor resultado de PM (dirección NY)?
# ──────────────────────────────────────────────────────────────
print("4) DIRECCIÓN DEL DÍA NY (pm_direction) por TIER")
print("   (¿Con VA limpio, el día NY es más direccional?)\n")

tier_dir = defaultdict(lambda: defaultdict(int))
for r in rows:
    t = va_tier(float(r["va_range"]))
    d = r["pm_direction"]
    tier_dir[t][d] += 1

for t in TIERS:
    dd = tier_dir[t]
    total = sum(dd.values())
    bull = dd.get("BULLISH",0)
    bear = dd.get("BEARISH",0)
    neu  = dd.get("NEUTRAL",0)
    print(f"  {t:<20}: BULL={bull}({bull/total*100:.0f}%)  BEAR={bear}({bear/total*100:.0f}%)  NEU={neu}({neu/total*100:.0f}%)  n={total}")

print(f"\n{'='*65}")
print("  CONCLUSIONES CLAVE")
print(f"{'='*65}")
# Encontrar el día con más TIER1
best_tier1_day = max(DIAS, key=lambda d: dia_tier_count[d]["TIER1 (<100)"] / dia_total[d] if dia_total[d] else 0)
pct_best = dia_tier_count[best_tier1_day]["TIER1 (<100)"] / dia_total[best_tier1_day] * 100

tier1_aguanta = tier_total["TIER1 (<100)"]
tier3_aguanta = tier_total["TIER3 (>150)"]
pct_t1 = sum(1 for x in tier1_aguanta if not x)/len(tier1_aguanta)*100 if tier1_aguanta else 0
pct_t3 = sum(1 for x in tier3_aguanta if not x)/len(tier3_aguanta)*100 if tier3_aguanta else 0

print(f"  • TIER1 (<100): VAL aguanta {pct_t1:.0f}% cuando es tocado")
print(f"  • TIER3 (>150): VAL aguanta solo {pct_t3:.0f}% cuando es tocado")
print(f"  • Día con más días TIER1: {best_tier1_day} ({pct_best:.0f}% de sus días son TIER1)")
print(f"  • Recomendación: operar BOUNCE_FROM_VAL solo en TIER1")
print(f"{'='*65}\n")
