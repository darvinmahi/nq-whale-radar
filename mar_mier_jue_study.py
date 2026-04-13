"""
mar_mier_jue_study.py — Estudio profundo Martes, Miercoles, Jueves
Pregunta: estos dias son de REBOTE? de SWEEP y FADE? de continuar?
Analiza:
  1. Manana (9:30-12:00) vs Tarde (12:00-16:00) — coinciden o se invierten?
  2. Sweep de OR: precio rompe HIGH/LOW del OR y luego vuelve?
  3. Mejor ventana de entrada
  4. Rebote del lunch (12:00-13:00)
"""
import pandas as pd, pytz, sys
from datetime import date, time as dtime

sys.stdout.reconfigure(encoding="utf-8")
ET = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

# Leer ultimas 35000 lineas = ~1 year de datos 15min
with open(CSV, "r") as f:
    lines = f.readlines()
import io
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

def dir3(m, th=15): return "BULL" if m > th else ("BEAR" if m < -th else "FLAT")

START = date(2025, 4, 10)
END   = date(2026, 4, 10)
DIAS  = {1:"MARTES", 2:"MIERCOLES", 3:"JUEVES"}

all_rows = []
for day in sorted(grouped.keys()):
    wd = pd.Timestamp(day).weekday()
    if wd not in [1, 2, 3]: continue
    if not (START <= day <= END): continue
    d = grouped[day]

    or_  = bt(d, "09:30", "09:59")
    or45 = bt(d, "09:30", "10:14")
    man  = bt(d, "09:30", "11:59")   # manana
    lunch= bt(d, "11:45", "12:59")   # lunch/midday
    pm   = bt(d, "13:00", "15:59")   # tarde
    ny   = bt(d, "09:30", "15:59")   # dia completo
    pre  = bt(d, "07:00", "09:29")   # pre-market

    if len(or_) < 1 or len(ny) < 8: continue

    # OR datos
    or_high = float(or_["High"].max())
    or_low  = float(or_["Low"].min())
    or_open = float(or_.iloc[0]["Open"])
    or_close= float(or_.iloc[-1]["Close"])
    or_r    = or_high - or_low
    or_m    = or_close - or_open

    # Manana
    man_m   = float(man.iloc[-1]["Close"]) - float(man.iloc[0]["Open"]) if len(man) >= 2 else 0
    # Tarde
    pm_m    = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"]) if len(pm) >= 2 else 0
    # Lunch
    lunch_m = float(lunch.iloc[-1]["Close"]) - float(lunch.iloc[0]["Open"]) if len(lunch) >= 2 else 0
    # Dia total
    ny_m    = float(ny.iloc[-1]["Close"]) - float(ny.iloc[0]["Open"])
    # Pre-market
    pre_m   = float(pre.iloc[-1]["Close"]) - float(pre.iloc[0]["Open"]) if len(pre) >= 2 else 0

    # OR Sweep: el precio rompió el HIGH del OR y luego bajó?
    # o rompió el LOW del OR y luego subió?
    after_or = bt(d, "10:00", "15:59")
    sweep_high = False; sweep_low = False
    if len(after_or) >= 1:
        if float(after_or["High"].max()) > or_high:
            # Subio sobre el OR HIGH — luego bajo?
            after_sweep = bt(d, "11:00", "15:59")
            if len(after_sweep) >= 1 and float(after_sweep["Close"].iloc[-1]) < or_high:
                sweep_high = True  # sweep del HIGH + reversión bajista
        if float(after_or["Low"].min()) < or_low:
            # Bajo bajo el OR LOW — luego subió?
            after_sweep = bt(d, "11:00", "15:59")
            if len(after_sweep) >= 1 and float(after_sweep["Close"].iloc[-1]) > or_low:
                sweep_low = True  # sweep del LOW + reversión alcista

    # H1-H4 analysis: cual es la mejor hora de entrada
    h10 = bt(d, "10:00", "10:59")
    h11 = bt(d, "11:00", "11:59")
    h12 = bt(d, "12:00", "12:59")
    h13 = bt(d, "13:00", "13:59")
    h14 = bt(d, "14:00", "14:59")

    def seg_m(seg):
        if len(seg) < 2: return 0
        return float(seg.iloc[-1]["Close"]) - float(seg.iloc[0]["Open"])

    all_rows.append({
        "day": day, "wd": wd,
        "or_d":  dir3(or_m, 10),
        "or_r":  round(or_r),
        "man_d": dir3(man_m, 20),
        "pm_d":  dir3(pm_m, 20),
        "lunch_d": dir3(lunch_m, 10),
        "ny_d":  dir3(ny_m, 30),
        "ny_m":  round(ny_m),
        "man_m": round(man_m),
        "pm_m":  round(pm_m),
        "lunch_m": round(lunch_m),
        "pre_m": round(pre_m),
        "sweep_high": sweep_high,
        "sweep_low":  sweep_low,
        "reversal": (dir3(man_m, 20) != dir3(pm_m, 20) and
                     dir3(man_m, 20) != "FLAT" and dir3(pm_m, 20) != "FLAT"),
        "continuation": (dir3(man_m, 20) == dir3(pm_m, 20) and dir3(man_m, 20) != "FLAT"),
        "h10_m": round(seg_m(h10)), "h11_m": round(seg_m(h11)),
        "h12_m": round(seg_m(h12)), "h13_m": round(seg_m(h13)),
        "h14_m": round(seg_m(h14)),
    })

print(f"Total dias analizados: {len(all_rows)}\n")

SEP = "=" * 80
for wd in [1, 2, 3]:
    wr = [r for r in all_rows if r["wd"] == wd]
    n  = len(wr)
    dname = DIAS[wd]

    print(SEP)
    print(f"  {dname} — {n} dias (Abr 2025 - Abr 2026)")
    print(SEP)

    # 1. REVERSAL vs CONTINUATION
    rev  = sum(1 for r in wr if r["reversal"])
    cont = sum(1 for r in wr if r["continuation"])
    flat = n - rev - cont
    print(f"\n  1. TARDE vs MANANA — Invierte o Continua?")
    print(f"     Manana BEAR → Tarde BULL (Rebote):  {sum(1 for r in wr if r['man_d']=='BEAR' and r['pm_d']=='BULL')} dias")
    print(f"     Manana BULL → Tarde BEAR (Fade):    {sum(1 for r in wr if r['man_d']=='BULL' and r['pm_d']=='BEAR')} dias")
    print(f"     Continuacion (mismo sentido):        {cont} dias")
    print(f"     Sin patron claro (FLAT):             {flat} dias")
    total_dir = rev + cont
    pct_rev = round(rev/total_dir*100) if total_dir else 0
    print(f"     => {pct_rev}% de los dias con direccion clara INVIERTEN en la tarde")

    # 2. SWEEP patterns
    sh = sum(1 for r in wr if r["sweep_high"])
    sl = sum(1 for r in wr if r["sweep_low"])
    print(f"\n  2. SWEEP DE LIQUIDEZ del OR")
    print(f"     Sweep HIGH + reversal bajista:  {sh} dias ({round(sh/n*100)}%)")
    print(f"     Sweep LOW  + reversal alcista:  {sl} dias ({round(sl/n*100)}%)")
    print(f"     Total dias con sweep:           {sh+sl} dias ({round((sh+sl)/n*100)}%)")

    # 3. Manana BEAR → que pasa en la tarde?
    man_bear = [r for r in wr if r["man_d"] == "BEAR"]
    man_bull = [r for r in wr if r["man_d"] == "BULL"]
    print(f"\n  3. Si la MANANA va BEAR ({len(man_bear)} dias):")
    if man_bear:
        rb = sum(1 for r in man_bear if r["pm_d"]=="BULL")
        rc = sum(1 for r in man_bear if r["pm_d"]=="BEAR")
        rf = sum(1 for r in man_bear if r["pm_d"]=="FLAT")
        avg_pm = round(sum(r["pm_m"] for r in man_bear) / len(man_bear))
        print(f"     Tarde BULL (rebote):   {rb}/{len(man_bear)} = {round(rb/len(man_bear)*100)}%")
        print(f"     Tarde BEAR (continua): {rc}/{len(man_bear)} = {round(rc/len(man_bear)*100)}%")
        print(f"     Tarde FLAT:            {rf}/{len(man_bear)}")
        print(f"     Movimiento promedio tarde: {avg_pm:+}pts")

    print(f"\n  4. Si la MANANA va BULL ({len(man_bull)} dias):")
    if man_bull:
        rb = sum(1 for r in man_bull if r["pm_d"]=="BEAR")
        rc = sum(1 for r in man_bull if r["pm_d"]=="BULL")
        avg_pm = round(sum(r["pm_m"] for r in man_bull) / len(man_bull))
        print(f"     Tarde BEAR (fade):     {rb}/{len(man_bull)} = {round(rb/len(man_bull)*100)}%")
        print(f"     Tarde BULL (continua): {rc}/{len(man_bull)} = {round(rc/len(man_bull)*100)}%")
        print(f"     Movimiento promedio tarde: {avg_pm:+}pts")

    # 4. MEJOR HORA por dia
    print(f"\n  5. MOVIMIENTO PROMEDIO POR HORA (positivo=alcista, negativo=bajista)")
    for hname, hkey in [("10:00-11:00","h10_m"),("11:00-12:00","h11_m"),
                         ("12:00-13:00 (lunch)","h12_m"),("13:00-14:00","h13_m"),
                         ("14:00-15:00","h14_m")]:
        avg = round(sum(r[hkey] for r in wr) / n)
        bull_h = sum(1 for r in wr if r[hkey] > 15)
        bear_h = sum(1 for r in wr if r[hkey] < -15)
        bias = "BULL" if avg > 10 else ("BEAR" if avg < -10 else "NEUTRAL")
        print(f"     {hname:25}: avg={avg:>+5}pts  BULL={bull_h}d BEAR={bear_h}d  [{bias}]")

    # 5. LUNCH REVERSAL — si lunch baja, sube a las 14h?
    lunch_bear = [r for r in wr if r["lunch_d"] == "BEAR"]
    lunch_bull = [r for r in wr if r["lunch_d"] == "BULL"]
    print(f"\n  6. LUNCH REVERSAL (12:00-13:00)")
    if lunch_bear:
        after_bull = sum(1 for r in lunch_bear if r["h13_m"] > 15 or r["h14_m"] > 15)
        print(f"     Lunch BEAR ({len(lunch_bear)}d) → hora 13-15 BULL: {after_bull}/{len(lunch_bear)} = {round(after_bull/len(lunch_bear)*100)}%")
    if lunch_bull:
        after_bear = sum(1 for r in lunch_bull if r["h13_m"] < -15 or r["h14_m"] < -15)
        print(f"     Lunch BULL ({len(lunch_bull)}d) → hora 13-15 BEAR: {after_bear}/{len(lunch_bull)} = {round(after_bear/len(lunch_bull)*100)}%")

    # 6. NY total — con que OR pattern
    print(f"\n  7. RESULTADO DIA COMPLETO vs SEÑAL OR")
    for or_sig in ["BULL","BEAR","FLAT"]:
        sub = [r for r in wr if r["or_d"]==or_sig]
        if not sub: continue
        bull_d = sum(1 for r in sub if r["ny_d"]=="BULL")
        bear_d = sum(1 for r in sub if r["ny_d"]=="BEAR")
        flat_d = sum(1 for r in sub if r["ny_d"]=="FLAT")
        avg_ny = round(sum(r["ny_m"] for r in sub)/len(sub))
        print(f"     OR {or_sig:4} ({len(sub)}d): NY=>BULL={bull_d} BEAR={bear_d} FLAT={flat_d}  | avg NY={avg_ny:+}pts")

print()
print(SEP)
print("  RESUMEN EJECUTIVO — ESTRATEGIAS PARA MAR/MIER/JUE")
print(SEP)
# Quick summary
for wd in [1,2,3]:
    wr = [r for r in all_rows if r["wd"]==wd]
    n = len(wr)
    rev = sum(1 for r in wr if r["reversal"])
    cont = sum(1 for r in wr if r["continuation"])
    sh = sum(1 for r in wr if r["sweep_high"])
    sl = sum(1 for r in wr if r["sweep_low"])
    print(f"\n  {DIAS[wd]}:")
    print(f"    Dias que invierten (tarde vs manana): {round(rev/(rev+cont)*100) if rev+cont else 0}%")
    print(f"    Dias con sweep de OR:                 {round((sh+sl)/n*100)}%")
    manb = [r for r in wr if r["man_d"]=="BEAR"]
    if manb: print(f"    Manana BEAR → Tarde BULL:             {round(sum(1 for r in manb if r['pm_d']=='BULL')/len(manb)*100)}%")
    manB = [r for r in wr if r["man_d"]=="BULL"]
    if manB: print(f"    Manana BULL → Tarde BEAR:             {round(sum(1 for r in manB if r['pm_d']=='BEAR')/len(manB)*100)}%")
