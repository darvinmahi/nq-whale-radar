"""
tabla_bull_bear.py — CUADRO COMPLETO BULL + BEAR
Periodos INDEPENDIENTES (sin solaparse):
  Año 1:    Abr 2024 → Abr 2025
  Año 2a:   Abr 2025 → Oct 2025
  Año 2b:   Oct 2025 → Abr 2026  (los más recientes)

Muestra para cada día:
  - Cuántos días fueron BULL / BEAR / FLAT totales
  - OR BULL → NY BULL %
  - OR BEAR → NY BEAR %
  - Qué día de la semana es más BULL y cuál más BEAR
"""
import pandas as pd, pytz
from datetime import date, time as dtime

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_date"] = raw.index.date
grouped = {d: grp for d, grp in raw.groupby("_date")}

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

# PERIODOS INDEPENDIENTES
PERIODOS = {
    "Año1 (A24-A25)" : (date(2024,4,10), date(2025,4,9)),
    "Año2a(A25-O25)" : (date(2025,4,10), date(2025,10,9)),
    "Año2b(O25-A26)" : (date(2025,10,10), date(2026,4,10)),
    "2Y Total"        : (date(2024,4,10), date(2026,4,10)),
}

DIAS = ["LUNES","MARTES","MIER  ","JUEVES","VIERNES"]

print("Procesando...")
all_rows = []
for day in sorted(grouped.keys()):
    wd = pd.Timestamp(day).weekday()
    if wd >= 5: continue
    d = grouped[day]
    or_  = bt(d,"09:30","09:59")
    or45 = bt(d,"09:30","10:14")
    ny   = bt(d,"09:30","16:00")
    pm   = bt(d,"07:00","09:29")
    if len(or_)<1 or len(ny)<4: continue

    or_m  = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
    or45_m= float(or45.iloc[-1]["Close"])- float(or45.iloc[0]["Open"]) if len(or45)>=1 else 0
    ny_m  = float(ny.iloc[-1]["Close"])  - float(ny.iloc[0]["Open"])
    pm_m  = float(pm.iloc[-1]["Close"])  - float(pm.iloc[0]["Open"]) if len(pm)>=2 else 0

    all_rows.append({
        "day": day, "wd": wd,
        "or_d" : "BULL" if or_m  >10 else("BEAR" if or_m  <-10 else"FLAT"),
        "or45_d":"BULL" if or45_m>10 else("BEAR" if or45_m<-10 else"FLAT"),
        "pm_d" : "BULL" if pm_m  >15 else("BEAR" if pm_m  <-15 else"FLAT"),
        "ny_d" : "BULL" if ny_m  >30 else("BEAR" if ny_m  <-30 else"FLAT"),
        "ny_m" : round(ny_m),
    })

print(f"  {len(all_rows)} días\n")

def get(wd, p_start, p_end):
    return [r for r in all_rows if r["wd"]==wd and p_start<=r["day"]<=p_end]

def pct(n,d): return round(n/d*100) if d>0 else 0

def fmt(p, n, total, direction=""):
    if n<2: return f"  — ({n})"
    freq = pct(n, total)
    icon = "🔥" if p>=90 else("✅" if p>=75 else("~" if p>=62 else"✗"))
    return f"{p:>3}%{icon}({n}d/{freq}%días)"

# ══════════════════════════════════════════════════════════════
# TABLA 1 — Naturaleza del día: cuántos son BULL/BEAR/FLAT
# ══════════════════════════════════════════════════════════════
print("═"*80)
print("  TABLA 1 — NATURALEZA DE CADA DÍA: ¿Cuántos terminan BULL vs BEAR?")
print("  (todos los días sin filtro — la realidad cruda del mercado)")
print("═"*80)

p_start, p_end = date(2024,4,10), date(2026,4,10)
print(f"\n  {'Día':<9}  {'Total':>6}  {'🟢BULL':>8}  {'🔴BEAR':>8}  {'⚪FLAT':>8}  "
      f"{'%BULL':>6}  {'%BEAR':>6}  {'Tendencia'}")
print("  "+"─"*75)

day_profiles = {}
for wd in range(5):
    rows = get(wd, p_start, p_end)
    n    = len(rows)
    bull = sum(1 for r in rows if r["ny_d"]=="BULL")
    bear = sum(1 for r in rows if r["ny_d"]=="BEAR")
    flat = sum(1 for r in rows if r["ny_d"]=="FLAT")
    pb   = pct(bull,n); pb2=pct(bear,n)
    day_profiles[wd] = {"bull":bull,"bear":bear,"flat":flat,"n":n,"pb":pb,"pb2":pb2}
    tend = "🟢 MÁS BULL" if pb>pb2+10 else("🔴 MÁS BEAR" if pb2>pb+10 else"⚖️ NEUTRAL")
    print(f"  {DIAS[wd]:<9}  {n:>6}  {bull:>8}  {bear:>8}  {flat:>8}  "
          f"{pb:>5}%  {pb2:>5}%  {tend}")

print("\n  → El día con más dias BULL es:",
      DIAS[max(range(5), key=lambda w: day_profiles[w]["pb"])])
print("  → El día con más dias BEAR es:",
      DIAS[max(range(5), key=lambda w: day_profiles[w]["pb2"])])

# ══════════════════════════════════════════════════════════════
# TABLA 2 — OR BULL y OR BEAR por día y por período
# ══════════════════════════════════════════════════════════════
print()
print("═"*90)
print("  TABLA 2 — OR BULL → NY BULL  y  OR BEAR → NY BEAR  (por período independiente)")
print("═"*90)

PERIOD_LIST = [
    ("Año1",  date(2024,4,10), date(2025,4,9)),
    ("Año2a", date(2025,4,10), date(2025,10,9)),
    ("Año2b", date(2025,10,10), date(2026,4,10)),
    ("2Y",    date(2024,4,10), date(2026,4,10)),
]

for wd in range(5):
    print(f"\n  ┌─ {DIAS[wd]} ─────────────────────────────────────────────────────────────────┐")
    print(f"  │ {'Período':<9}  {'días tot':>8}  {'OR BULL→BULL':>20}  {'OR BEAR→BEAR':>20}  {'OR FLAT':>8} │")
    print(f"  ├─────────────────────────────────────────────────────────────────────────────┤")

    for pname, ps, pe in PERIOD_LIST:
        rows = get(wd, ps, pe)
        n    = len(rows)
        if n == 0: continue

        # BULL side
        bull_rows = [r for r in rows if r["or_d"]=="BULL"]
        bull_hits  = sum(1 for r in bull_rows if r["ny_d"]=="BULL")
        nb = len(bull_rows)
        pb = pct(bull_hits, nb) if nb>0 else 0
        bull_icon = "🔥" if pb>=90 else("✅" if pb>=75 else("~" if pb>=62 else"✗"))
        bull_cell = f"{pb:>3}%{bull_icon} ({bull_hits}/{nb})" if nb>=2 else f"   — ({nb})"

        # BEAR side
        bear_rows = [r for r in rows if r["or_d"]=="BEAR"]
        bear_hits  = sum(1 for r in bear_rows if r["ny_d"]=="BEAR")
        nbe = len(bear_rows)
        pbe = pct(bear_hits, nbe) if nbe>0 else 0
        bear_icon = "🔥" if pbe>=90 else("✅" if pbe>=75 else("~" if pbe>=62 else"✗"))
        bear_cell = f"{pbe:>3}%{bear_icon} ({bear_hits}/{nbe})" if nbe>=2 else f"   — ({nbe})"

        flat_n = sum(1 for r in rows if r["or_d"]=="FLAT")
        sep = "◀ 2Y" if pname=="2Y" else ""

        print(f"  │ {pname:<9}  {n:>8}  {bull_cell:>20}  {bear_cell:>20}  {flat_n:>5}d    {sep:<5}│")

    print(f"  └─────────────────────────────────────────────────────────────────────────────┘")

# ══════════════════════════════════════════════════════════════
# TABLA 3 — Ranking de días: cuál es el más BULL y más BEAR
# ══════════════════════════════════════════════════════════════
print()
print("═"*80)
print("  TABLA 3 — RANKING: ¿Cuál día es más BULL? ¿Cuál más BEAR?")
print("  Basado en OR BULL → NY BULL  y  OR BEAR → NY BEAR en 2 años")
print("═"*80)

ps, pe = date(2024,4,10), date(2026,4,10)
rankings = []
for wd in range(5):
    rows = get(wd, ps, pe)
    n = len(rows)
    # BULL signal quality
    bull_rows = [r for r in rows if r["or_d"]=="BULL"]
    bear_rows = [r for r in rows if r["or_d"]=="BEAR"]
    bull_acc = pct(sum(1 for r in bull_rows if r["ny_d"]=="BULL"), len(bull_rows)) if len(bull_rows)>=3 else 0
    bear_acc = pct(sum(1 for r in bear_rows if r["ny_d"]=="BEAR"), len(bear_rows)) if len(bear_rows)>=3 else 0
    # Overall bull rate
    all_bull = pct(sum(1 for r in rows if r["ny_d"]=="BULL"), n)
    all_bear = pct(sum(1 for r in rows if r["ny_d"]=="BEAR"), n)
    rankings.append((wd, bull_acc, bear_acc, all_bull, all_bear, len(bull_rows), len(bear_rows)))

print(f"\n  🟢 RANKING BULL — días ordenados por mejor señal OR BULL → NY BULL:")
for rank, (wd, bull_acc, bear_acc, all_bull, all_bear, nb, nbe) in enumerate(
        sorted(rankings, key=lambda x:-x[1]), 1):
    bar = "█"*round(bull_acc/10) if bull_acc else ""
    print(f"  {rank}. {DIAS[wd]}  {bull_acc:>3}% OR BULL→BULL ({nb}d)  |  {all_bull}% dias cierran BULL  {bar}")

print(f"\n  🔴 RANKING BEAR — días ordenados por mejor señal OR BEAR → NY BEAR:")
for rank, (wd, bull_acc, bear_acc, all_bull, all_bear, nb, nbe) in enumerate(
        sorted(rankings, key=lambda x:-x[2]), 1):
    bar = "█"*round(bear_acc/10) if bear_acc else ""
    print(f"  {rank}. {DIAS[wd]}  {bear_acc:>3}% OR BEAR→BEAR ({nbe}d)  |  {all_bear}% dias cierran BEAR  {bar}")

print()
print("  CONCLUSIÓN:")
best_bull = DIAS[sorted(rankings, key=lambda x:-x[1])[0][0]]
best_bear = DIAS[sorted(rankings, key=lambda x:-x[2])[0][0]]
print(f"  → Para operar LONG:  mejor día = {best_bull}")
print(f"  → Para operar SHORT: mejor día = {best_bear}")
