"""
cot_viernes.py — Asset Manager DELTA vs comportamiento del VIERNES
Datos COT extraídos del tabla_cot_completa.html
Pregunta: cuando AM Delta es positivo/negativo, que pasa el viernes de esa semana?
"""
import pandas as pd, pytz, sys, io
from datetime import date, timedelta, time as dtime

sys.stdout.reconfigure(encoding="utf-8")
ET = pytz.timezone("America/New_York")

# ══ COT DATA extraído del HTML (fecha = martes de esa semana COT) ══
# formato: (fecha_cot, am_delta, lev_pct, señal)
COT_RAW = [
    # fecha         am_delta  lev%  señal
    ("2025-04-08",  -10184,   100,  "BEAR"),
    ("2025-04-15",  +2659,    66,   "NEUTRAL"),
    ("2025-04-22",  -6335,    82,   "BEAR"),
    ("2025-04-29",  +6106,    41,   "NEUTRAL"),
    ("2025-05-06",  +1356,    22,   "NEUTRAL"),
    ("2025-05-13",  +2147,    0,    "NEUTRAL"),
    ("2025-05-20",  +5968,    5,    "BULL"),
    ("2025-05-27",  +2249,    14,   "NEUTRAL"),
    ("2025-06-03",  +2973,    14,   "NEUTRAL"),
    ("2025-06-10",  -729,     26,   "NEUTRAL"),
    ("2025-06-17",  +1498,    21,   "NEUTRAL"),
    ("2025-06-24",  -5498,    57,   "NEUTRAL"),
    ("2025-07-01",  +5139,    80,   "NEUTRAL"),
    ("2025-07-08",  +6413,    87,   "NEUTRAL"),
    ("2025-07-15",  +6811,    75,   "NEUTRAL"),
    ("2025-07-22",  -2555,    68,   "NEUTRAL"),
    ("2025-07-29",  +7865,    72,   "NEUTRAL"),
    ("2025-08-05",  +3187,    76,   "NEUTRAL"),
    ("2025-08-12",  +5622,    78,   "NEUTRAL"),
    ("2025-08-19",  +602,     72,   "NEUTRAL"),
    ("2025-08-26",  -2688,    78,   "NEUTRAL"),
    ("2025-09-02",  -4625,    73,   "NEUTRAL"),
    ("2025-09-09",  +4528,    63,   "NEUTRAL"),
    ("2025-09-16",  +1950,    64,   "NEUTRAL"),
    ("2025-09-23",  -3782,    62,   "NEUTRAL"),
    ("2025-09-30",  +1660,    94,   "NEUTRAL"),
    ("2025-10-07",  +4512,    84,   "NEUTRAL"),
    ("2025-10-14",  -741,     84,   "NEUTRAL"),
    ("2025-10-21",  -1527,    97,   "NEUTRAL"),
    ("2025-10-28",  -5578,    100,  "BEAR"),
    ("2025-11-04",  +3799,    93,   "NEUTRAL"),
    ("2025-11-10",  -6179,    100,  "BEAR"),
    ("2025-11-18",  +3675,    87,   "NEUTRAL"),
    ("2025-11-25",  -600,     83,   "NEUTRAL"),
    ("2025-12-02",  -26,      66,   "NEUTRAL"),
    ("2025-12-09",  +3485,    42,   "NEUTRAL"),
    ("2025-12-16",  +337,     57,   "NEUTRAL"),
    ("2025-12-23",  +10713,   70,   "NEUTRAL"),
    ("2025-12-30",  +4719,    58,   "NEUTRAL"),
    ("2026-01-06",  +128,     68,   "NEUTRAL"),
    ("2026-01-13",  +3185,    61,   "NEUTRAL"),
    ("2026-01-20",  -4480,    51,   "NEUTRAL"),
    ("2026-01-27",  +12441,   66,   "NEUTRAL"),
    ("2026-02-03",  -6902,    66,   "BEAR"),
    ("2026-02-10",  -299,     70,   "NEUTRAL"),
    ("2026-02-17",  +1632,    66,   "NEUTRAL"),
    ("2026-02-24",  -4204,    56,   "NEUTRAL"),
    ("2026-03-03",  -1543,    46,   "NEUTRAL"),
    ("2026-03-10",  -3100,    44,   "NEUTRAL"),
    ("2026-03-17",  -4127,    36,   "NEUTRAL"),
    ("2026-03-24",  -9933,    34,   "NEUTRAL"),
    ("2026-03-31",  +7133,    35,   "BULL"),
]

# El COT se publica el viernes COT_DATE
# Aplica a los VIERNES de la SEMANA SIGUIENTE lógicamente
# Pero como la fecha COT es el martes de referencia,
# el VIERNES de esa misma semana ya refleja ese posicionamiento
# Usaremos: viernes de la semana del COT (cot_date + 4 días aprox)

cot_map = {}  # date -> {am_delta, lev, señal}
for fecha_str, am_delta, lev, señal in COT_RAW:
    d = date.fromisoformat(fecha_str)
    # Buscar el viernes de esa semana
    dias_hasta_viernes = (4 - d.weekday()) % 7
    viernes = d + timedelta(days=dias_hasta_viernes)
    cot_map[viernes] = {"am_delta": am_delta, "lev": lev, "señal": señal, "cot_date": d}

# ══ Cargar datos de precios ══
with open("data/research/nq_15m_intraday.csv", "r") as f:
    lines = f.readlines()
raw = pd.read_csv(io.StringIO("".join(lines[:2] + lines[-35000:])),
                  header=None, names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True, errors="coerce").dt.tz_convert(ET)
raw = raw.dropna(subset=["Datetime"])
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_d"] = raw.index.date
grouped = {d: g for d, g in raw.groupby("_d")}

def bt(d, t0, t1):
    a = dtime(*map(int, t0.split(":"))); b = dtime(*map(int, t1.split(":")))
    return d[(d.index.time >= a) & (d.index.time <= b)]

START = date(2025, 4, 10); END = date(2026, 4, 10)

rows = []
for day in sorted(grouped.keys()):
    if pd.Timestamp(day).weekday() != 4: continue
    if not (START <= day <= END): continue
    d = grouped[day]
    or_ = bt(d, "09:30", "09:59"); ny = bt(d, "09:30", "16:00")
    if len(or_) < 1 or len(ny) < 4: continue
    or_m = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
    or_r = float(or_["High"].max()) - float(or_["Low"].min())
    ny_m = float(ny.iloc[-1]["Close"]) - float(ny.iloc[0]["Open"])
    od = "BULL" if or_m > 10 else("BEAR" if or_m < -10 else "FLAT")
    nd = "BULL" if ny_m > 30 else("BEAR" if ny_m < -30 else "FLAT")

    cot = cot_map.get(day, {})
    rows.append({
        "day": day, "or_d": od, "or_r": round(or_r),
        "ny_d": nd, "ny_m": round(ny_m),
        "am_delta": cot.get("am_delta"), "lev": cot.get("lev"),
        "cot_señal": cot.get("señal", "—"),
    })

print(f"Viernes analizados: {len(rows)}\n")

# ══ TABLA 1: AM Delta Positivo vs Negativo vs Viernes ══
print("="*80)
print("  AM DELTA vs VIERNES — ¿correlacionan?")
print("="*80)
print()

pos = [r for r in rows if r["am_delta"] and r["am_delta"] > 0]
neg = [r for r in rows if r["am_delta"] and r["am_delta"] < 0]
strong_pos = [r for r in rows if r["am_delta"] and r["am_delta"] > 5000]
strong_neg = [r for r in rows if r["am_delta"] and r["am_delta"] < -5000]

def stat(group, label):
    n = len(group)
    if n == 0: return
    bull = sum(1 for r in group if r["ny_d"] == "BULL")
    bear = sum(1 for r in group if r["ny_d"] == "BEAR")
    flat = sum(1 for r in group if r["ny_d"] == "FLAT")
    avg  = round(sum(r["ny_m"] for r in group) / n)
    pb   = round(bull/n*100); pbr  = round(bear/n*100)
    print(f"  {label:<35}  n={n:>2}  BULL={bull:>2}({pb:>2}%)  BEAR={bear:>2}({pbr:>2}%)  FLAT={flat}  avg={avg:>+5}pts")

stat(pos,         "AM Delta POSITIVO (AM compra)")
stat(strong_pos,  "AM Delta > +5000 (AM compra fuerte)")
stat(neg,         "AM Delta NEGATIVO (AM vende)")
stat(strong_neg,  "AM Delta < -5000 (AM vende fuerte)")

# ══ TABLA 2: Rango del AM Delta y viernes ══
print()
print("="*80)
print("  RANGO DEL AM DELTA vs VIERNES — impacto en el sesgo")
print("="*80)
print()
ranges = [
    (">+5000 (compra fuerte)",   lambda r: r["am_delta"] and r["am_delta"] > 5000),
    ("+1k a +5k (compra leve)", lambda r: r["am_delta"] and 1000 <= r["am_delta"] <= 5000),
    ("-1k a +1k (neutral)",     lambda r: r["am_delta"] and -1000 <= r["am_delta"] < 1000),
    ("-5k a -1k (vende leve)",  lambda r: r["am_delta"] and -5000 <= r["am_delta"] < -1000),
    ("<-5000 (vende fuerte)",   lambda r: r["am_delta"] and r["am_delta"] < -5000),
]
print(f"  {'AM Delta rango':<30}  {'n':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'avg NY':>7}")
print("  "+"-"*60)
for label, cond in ranges:
    g = [r for r in rows if cond(r)]
    n = len(g)
    if n == 0: continue
    bull = sum(1 for r in g if r["ny_d"]=="BULL")
    bear = sum(1 for r in g if r["ny_d"]=="BEAR")
    avg  = round(sum(r["ny_m"] for r in g) / n)
    icon = "🔥" if bear/n > 0.7 else("✅" if bear/n > 0.5 else("~" if bull/n > 0.4 else""))
    print(f"  {label:<30}  {n:>3}  {round(bull/n*100):>5}%  {round(bear/n*100):>5}%  {avg:>+6}pts  {icon}")

# ══ TABLA 3: LEV% vs Viernes ══
print()
print("="*80)
print("  LEV% (Hedge Funds percentil) vs VIERNES")
print("="*80)
print()
lev_ranges = [
    ("LEV% 0-20%   (HF muy cortos)",  0, 20),
    ("LEV% 21-40%  (HF cortos)",      21, 40),
    ("LEV% 41-60%  (HF neutral)",     41, 60),
    ("LEV% 61-80%  (HF largos)",      61, 80),
    ("LEV% 81-100% (HF muy largos)",  81, 101),
]
print(f"  {'LEV rango':<30}  {'n':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'avg NY':>7}")
print("  "+"-"*60)
for label, lo, hi in lev_ranges:
    g = [r for r in rows if r["lev"] is not None and lo <= r["lev"] < hi]
    n = len(g)
    if n == 0: continue
    bull = sum(1 for r in g if r["ny_d"]=="BULL")
    bear = sum(1 for r in g if r["ny_d"]=="BEAR")
    avg  = round(sum(r["ny_m"] for r in g) / n)
    icon = "🔥" if bear/n > 0.6 else("🟢" if bull/n > 0.5 else "")
    print(f"  {label:<30}  {n:>3}  {round(bull/n*100):>5}%  {round(bear/n*100):>5}%  {avg:>+6}pts  {icon}")

# ══ TABLA 4: Día a día vs COT ══
print()
print("="*80)
print("  VIERNES DIA A DIA — AM Delta + LEV + OR + Resultado")
print("="*80)
print()
print(f"  {'Fecha':>10}  {'AM Delta':>9}  {'LEV%':>5}  {'Señal COT':>10}  {'OR':>5}  {'NY mov':>8}  {'NY dir':>5}  Concuerda?")
print("  "+"-"*82)
s_match = 0; s_total = 0
for r in rows:
    am  = f"{r['am_delta']:>+8}" if r["am_delta"] else "      —"
    lev = f"{r['lev']:>3}%" if r["lev"] is not None else "  —"
    cot_bias = "BEAR" if (r["am_delta"] and r["am_delta"] < -5000) else \
               ("BULL" if (r["am_delta"] and r["am_delta"] > 5000 and r["lev"] is not None and r["lev"] < 40) else "NEUT")
    match = ""
    if cot_bias == "BEAR" and r["ny_d"] == "BEAR": match = "✅ BEAR-BEAR"; s_match+=1; s_total+=1
    elif cot_bias == "BULL" and r["ny_d"] == "BULL": match = "✅ BULL-BULL"; s_match+=1; s_total+=1
    elif cot_bias in ["BEAR","BULL"]: match = "❌"; s_total+=1
    or_bear_icon = "🔥" if r["or_r"] >= 100 else ""
    print(f"  {r['day'].strftime('%d/%m/%Y'):>10}  {am}  {lev}  {r['cot_señal']:>10}  "
          f"{r['or_d']:>5}  {r['ny_m']:>+8}p  {r['ny_d']:>5}  {match}")

print()
print(f"  AM Delta como predictor del viernes: {s_match}/{s_total} señales claras")

# ══ TABLA 5: OR + COT COMBO ══
print()
print("="*80)
print("  COMBO: OR BEAR + AM Delta NEGATIVO vs Viernes")
print("="*80)
print()
combos = [
    ("OR BEAR + AM Delta NEG",     lambda r: r["or_d"]=="BEAR" and r["am_delta"] and r["am_delta"] < 0,     "BEAR"),
    ("OR BEAR + AM Delta POS",     lambda r: r["or_d"]=="BEAR" and r["am_delta"] and r["am_delta"] > 0,     "BEAR"),
    ("OR FLAT + AM Delta NEG",     lambda r: r["or_d"]=="FLAT" and r["am_delta"] and r["am_delta"] < 0,     "BEAR"),
    ("OR FLAT + AM Delta POS",     lambda r: r["or_d"]=="FLAT" and r["am_delta"] and r["am_delta"] > 0,     "BEAR"),
    ("OR BULL + AM Delta < -5000", lambda r: r["or_d"]=="BULL" and r["am_delta"] and r["am_delta"] < -5000, "BEAR"),
    ("OR BULL + AM Delta > +5000 + LEV<40%",
     lambda r: r["or_d"]=="BULL" and r["am_delta"] and r["am_delta"] > 5000 and r["lev"] and r["lev"] < 40, "BULL"),
]
print(f"  {'Combo':<40}  {'n':>3}  {'BEAR NY':>7}  {'BULL NY':>7}  {'Conclusion':>15}")
print("  "+"-"*75)
for label, cond, target in combos:
    g = [r for r in rows if cond(r)]
    n = len(g)
    if n == 0:
        print(f"  {label:<40}  {n:>3}  — (sin datos)")
        continue
    bull = sum(1 for r in g if r["ny_d"]=="BULL")
    bear = sum(1 for r in g if r["ny_d"]=="BEAR")
    pb = round(bull/n*100); pbr = round(bear/n*100)
    conclusion = f"BEAR {pbr}% 🔥" if pbr>=80 else(f"BEAR {pbr}% ✅" if pbr>=65 else(f"BULL {pb}% 🟢" if pb>=65 else f"MIXTO"))
    print(f"  {label:<40}  {n:>3}  {bear:>4}({pbr:>2}%)  {bull:>4}({pb:>2}%)  {conclusion:>15}")

# ══ CONCLUSIÓN ══
print()
print("="*80)
print("  CONCLUSIÓN — ¿ayuda el AM Delta a saber si el viernes es BULL o BEAR?")
print("="*80)
all_bear = [r for r in rows if r["ny_d"]=="BEAR"]
all_bull = [r for r in rows if r["ny_d"]=="BULL"]
neg_delta_viernes = [r for r in all_bear if r["am_delta"] and r["am_delta"] < 0]
pos_delta_viernes = [r for r in all_bull if r["am_delta"] and r["am_delta"] > 0]
print(f"\n  De {len(all_bear)} viernes BEAR: {len(neg_delta_viernes)} tenían AM Delta negativo ({round(len(neg_delta_viernes)/len(all_bear)*100)}%)")
print(f"  De {len(all_bull)} viernes BULL: {len(pos_delta_viernes)} tenían AM Delta positivo ({round(len(pos_delta_viernes)/len(all_bull)*100)}%)")
