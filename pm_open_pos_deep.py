"""
ANÁLISIS PM_OPEN_POS × NY DIRECTION × VA TIER
¿Cuando London abre fuera del VA, NY sigue esa dirección?
"""
import csv
from collections import defaultdict

def va_tier(va_range):
    if va_range < 100:
        return "TIER1(<100)"
    elif va_range <= 150:
        return "TIER2(100-150)"
    else:
        return "TIER3(>150)"

rows = []
with open("ny_profile_asia_london_daily.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

SEP = "=" * 65
sep = "-" * 65

print(f"\n{SEP}")
print("  ANÁLISIS: pm_open_pos — ¿London predice el día NY?")
print(f"  Total días: {len(rows)}")
print(f"{SEP}\n")

# ──────────────────────────────────────────────────────────────
# SECCIÓN 1: Distribución general de pm_open_pos
# ──────────────────────────────────────────────────────────────
pm_count = defaultdict(int)
for r in rows:
    pm_count[r["pm_open_pos"]] += 1

total = len(rows)
print("1) DISTRIBUCIÓN — ¿Con qué frecuencia London abre fuera del VA?\n")
for k, v in sorted(pm_count.items(), key=lambda x: -x[1]):
    barra = "█" * (v * 30 // total)
    print(f"   {k:<12}: {v:>3} días ({v/total*100:4.1f}%)  {barra}")
print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 2: pm_open_pos → ¿NY sigue esa dirección?
# Métrica: pm_direction (dirección real del día NY)
# ──────────────────────────────────────────────────────────────
print("2) pm_open_pos → DIRECCIÓN REAL DÍA NY (pm_direction)\n")
print("   ¿Cuando London abre arriba, NY es BULLISH? ¿Cuando London abre abajo, NY es BEARISH?\n")

pm_dir = defaultdict(lambda: defaultdict(int))
pm_close = defaultdict(lambda: defaultdict(int))

for r in rows:
    pos = r["pm_open_pos"]
    pm_dir[pos][r["pm_direction"]] += 1
    # Cierre: ¿dónde cerró el día?
    if r["close_above_va"] == "True":
        pm_close[pos]["ABOVE_VA"] += 1
    elif r["close_below_va"] == "True":
        pm_close[pos]["BELOW_VA"] += 1
    else:
        pm_close[pos]["INSIDE_VA"] += 1

POSICIONES = ["ABOVE_VA", "INSIDE_VA", "BELOW_VA"]
DIRS = ["BULLISH", "BEARISH", "NEUTRAL"]

print(f"   {'London abre':<14} | {'BULL día NY':^12} | {'BEAR día NY':^12} | {'NEUTRAL':^10} | Total")
print(f"   {sep}")
for pos in POSICIONES:
    dd = pm_dir[pos]
    total_pos = sum(dd.values())
    if total_pos == 0:
        continue
    bull = dd.get("BULLISH", 0)
    bear = dd.get("BEARISH", 0)
    neu  = dd.get("NEUTRAL", 0)

    # La flecha indica si "sigue" (ABOVE→BULL, BELOW→BEAR)
    if pos == "ABOVE_VA":
        # queremos BULL = "sigue" → marcar
        sigue_pct = bull/total_pos*100
        contra_pct = bear/total_pos*100
        nota = f"  ← sigue: {sigue_pct:.0f}%"
    elif pos == "BELOW_VA":
        sigue_pct = bear/total_pos*100
        contra_pct = bull/total_pos*100
        nota = f"  ← sigue: {sigue_pct:.0f}%"
    else:
        nota = ""
    
    print(f"   {pos:<14} | {bull:>4}({bull/total_pos*100:3.0f}%)    | {bear:>4}({bear/total_pos*100:3.0f}%)    | {neu:>3}({neu/total_pos*100:3.0f}%)  | {total_pos}{nota}")

print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 3: CIERRE DEL DÍA según pm_open_pos
# ──────────────────────────────────────────────────────────────
print("3) pm_open_pos → ¿DÓNDE CIERRA EL DÍA?\n")
print("   ('Sigue' = ABOVE_VA abre arriba y cierra arriba / BELOW abre abajo y cierra abajo)\n")

print(f"   {'London abre':<14} | {'Cierra ABOVE':^13} | {'Cierra BELOW':^13} | {'Cierra INSIDE':^13} | Total")
print(f"   {sep}")
for pos in POSICIONES:
    cd = pm_close[pos]
    total_pos = sum(cd.values())
    if total_pos == 0:
        continue
    above = cd.get("ABOVE_VA", 0)
    below = cd.get("BELOW_VA", 0)
    inside = cd.get("INSIDE_VA", 0)

    if pos == "ABOVE_VA":
        nota = f"  ← mantiene arriba: {above/total_pos*100:.0f}%"
    elif pos == "BELOW_VA":
        nota = f"  ← mantiene abajo: {below/total_pos*100:.0f}%"
    else:
        nota = ""
    
    print(f"   {pos:<14} | {above:>4}({above/total_pos*100:3.0f}%)    | {below:>4}({below/total_pos*100:3.0f}%)    | {inside:>4}({inside/total_pos*100:3.0f}%)   | {total_pos}{nota}")

print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 4: ABOVE_VA + TIER1 y BELOW_VA + TIER1 (filtrado)
# ──────────────────────────────────────────────────────────────
print("4) FILTRADO: Solo días TIER1 (<100 pts VA) × pm_open_pos\n")
print("   (¿El filtro de VA limpio mejora la predictividad de London?)\n")

for pos in ["ABOVE_VA", "BELOW_VA"]:
    dias_tier1 = [r for r in rows if r["pm_open_pos"] == pos and float(r["va_range"]) < 100]
    if not dias_tier1:
        print(f"   {pos} + TIER1: sin datos")
        continue
    n = len(dias_tier1)
    bull = sum(1 for r in dias_tier1 if r["pm_direction"] == "BULLISH")
    bear = sum(1 for r in dias_tier1 if r["pm_direction"] == "BEARISH")
    neu  = sum(1 for r in dias_tier1 if r["pm_direction"] == "NEUTRAL")
    close_sigue = sum(1 for r in dias_tier1 if 
                      (pos == "ABOVE_VA" and r["close_above_va"] == "True") or
                      (pos == "BELOW_VA" and r["close_below_va"] == "True"))
    print(f"   {pos} + TIER1 ({n} días):")
    print(f"     Dirección NY: BULL={bull}({bull/n*100:.0f}%)  BEAR={bear}({bear/n*100:.0f}%)  NEU={neu}({neu/n*100:.0f}%)")
    print(f"     Cierra 'siguiendo' London: {close_sigue}/{n} = {close_sigue/n*100:.0f}%")
    print()

# ──────────────────────────────────────────────────────────────
# SECCIÓN 5: Ejemplos reales de ABOVE_VA y BELOW_VA
# ──────────────────────────────────────────────────────────────
print("5) EJEMPLOS REALES del CSV\n")

for pos in ["ABOVE_VA", "BELOW_VA"]:
    dias = [r for r in rows if r["pm_open_pos"] == pos]
    print(f"   {pos} — {len(dias)} días:")
    print(f"   {'Fecha':<13} {'VA_range':>9} {'pm_dir':<10} {'Cierra':<12} {'Tier'}")
    print(f"   {'-'*60}")
    for r in dias[:8]:
        t = va_tier(float(r["va_range"]))
        cierre = "ABOVE" if r["close_above_va"]=="True" else ("BELOW" if r["close_below_va"]=="True" else "INSIDE")
        sigue = ""
        if (pos == "ABOVE_VA" and cierre == "ABOVE") or (pos == "BELOW_VA" and cierre == "BELOW"):
            sigue = "✓"
        print(f"   {r['date']:<13} {float(r['va_range']):>9.1f} {r['pm_direction']:<10} {cierre:<12} {t}  {sigue}")
    print()

# ──────────────────────────────────────────────────────────────
# CONCLUSIÓN
# ──────────────────────────────────────────────────────────────
print(f"{SEP}")
print("  CONCLUSIÓN")
print(f"{SEP}")

above_dias = [r for r in rows if r["pm_open_pos"] == "ABOVE_VA"]
below_dias  = [r for r in rows if r["pm_open_pos"] == "BELOW_VA"]
inside_dias = [r for r in rows if r["pm_open_pos"] == "INSIDE_VA"]

print(f"\n  London abre ABOVE_VA:  {len(above_dias)} días ({len(above_dias)/total*100:.0f}%)")
print(f"  London abre BELOW_VA:  {len(below_dias)} días ({len(below_dias)/total*100:.0f}%)")
print(f"  London abre INSIDE_VA: {len(inside_dias)} días ({len(inside_dias)/total*100:.0f}%) ← el más común")

if above_dias:
    bull_above = sum(1 for r in above_dias if r["pm_direction"] == "BULLISH")
    print(f"\n  Cuando London está ARRIBA del VA:")
    print(f"    → NY es BULLISH: {bull_above}/{len(above_dias)} = {bull_above/len(above_dias)*100:.0f}%")

if below_dias:
    bear_below = sum(1 for r in below_dias if r["pm_direction"] == "BEARISH")
    print(f"\n  Cuando London está ABAJO del VA:")
    print(f"    → NY es BEARISH: {bear_below}/{len(below_dias)} = {bear_below/len(below_dias)*100:.0f}%")

print(f"\n{SEP}\n")
