"""
ultimos_3m.py — Lista de los últimos 3 meses (Ene-Abr 2026) por día de semana
"""
import pandas as pd, pytz
from datetime import date, time as dtime

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

# Carga solo las últimas filas necesarias (más rápido)
raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)

# Filtrar solo los últimos 3 meses ANTES de todo lo demás
START_DT = pd.Timestamp("2026-01-01", tz="America/New_York")
raw = raw[raw["Datetime"] >= START_DT]  # ← esto hace todo más rápido

raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_date"] = raw.index.date
grouped = {d: grp for d, grp in raw.groupby("_date")}

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

START = date(2026, 1, 5)
END   = date(2026, 4, 10)
DIAS  = ["LUNES","MARTES","MIER  ","JUEVES","VIERNES"]

rows = []
for day in sorted(grouped.keys()):
    wd = pd.Timestamp(day).weekday()
    if wd >= 5 or not (START <= day <= END): continue
    d = grouped[day]
    or_  = bt(d,"09:30","09:59")
    or45 = bt(d,"09:30","10:14")
    ny   = bt(d,"09:30","16:00")
    pm   = bt(d,"07:00","09:29")
    if len(or_)<1 or len(ny)<4: continue

    or_m  = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
    or45_m= float(or45.iloc[-1]["Close"])- float(or45.iloc[0]["Open"]) if len(or45)>=1 else 0
    ny_m  = float(ny.iloc[-1]["Close"])  - float(ny.iloc[0]["Open"])
    or_r  = float(or_["High"].max()) - float(or_["Low"].min())
    pm_m  = float(pm.iloc[-1]["Close"])  - float(pm.iloc[0]["Open"]) if len(pm)>=2 else 0

    or_d  = "BULL" if or_m>10  else("BEAR" if or_m<-10  else"FLAT")
    or45_d= "BULL" if or45_m>10 else("BEAR" if or45_m<-10 else"FLAT")
    ny_d  = "BULL" if ny_m>30  else("BEAR" if ny_m<-30  else"FLAT")
    pm_d  = "BULL" if pm_m>15  else("BEAR" if pm_m<-15  else"FLAT")
    ok    = "✅" if (or_d==ny_d and or_d!="FLAT") else("❌" if or_d!="FLAT" else"—")

    rows.append({"day":day,"wd":wd,"or_d":or_d,"or45_d":or45_d,"pm_d":pm_d,
                 "or_r":round(or_r),"ny_m":round(ny_m),"ny_d":ny_d,"ok":ok})

print(f"Total días: {len(rows)}\n")

for wd in range(5):
    wd_rows = [r for r in rows if r["wd"]==wd]
    if not wd_rows: continue
    print()
    print(f"══ {DIAS[wd]} — {len(wd_rows)} días (Ene-Abr 2026) ══")
    print(f"  {'#':>2}  {'Fecha':>12}  {'OR':>5}  {'OR45':>5}  {'PM':>5}  {'OR rng':>6}  {'NY mov':>8}  OR acertó?")
    print("  "+"-"*68)
    hit=0; signal=0
    for i, r in enumerate(wd_rows, 1):
        star="🔥" if r["or_r"]>=100 else"  "
        print(f"  {i:>2}  {r['day'].strftime('%d/%m/%Y'):>12}  {r['or_d']:>5}  "
              f"{r['or45_d']:>5}  {r['pm_d']:>5}  {r['or_r']:>4}p{star}  "
              f"{r['ny_m']:>+7}p  {r['ok']}")
        if r["ok"]=="✅": hit+=1
        if r["ok"]!="—": signal+=1

    bull=sum(1 for r in wd_rows if r["or_d"]=="BULL")
    bear=sum(1 for r in wd_rows if r["or_d"]=="BEAR")
    flat=sum(1 for r in wd_rows if r["or_d"]=="FLAT")
    ny_bull=sum(1 for r in wd_rows if r["ny_d"]=="BULL")
    ny_bear=sum(1 for r in wd_rows if r["ny_d"]=="BEAR")
    ny_flat=sum(1 for r in wd_rows if r["ny_d"]=="FLAT")

    print(f"\n  ┌─ RESUMEN {DIAS[wd]} ─────────────────────────────────────────┐")
    print(f"  │ OR señal : BULL={bull}d  BEAR={bear}d  FLAT={flat}d (sin señal)               │")
    print(f"  │ NY cierre: BULL={ny_bull}d  BEAR={ny_bear}d  FLAT={ny_flat}d                        │")
    acc = round(hit/signal*100) if signal else 0
    icon= "🔥" if acc>=90 else("✅" if acc>=75 else("~" if acc>=62 else"✗"))
    print(f"  │ OR acertó: {hit}/{signal} días con señal = {acc}%{icon}                       │")
    print(f"  └──────────────────────────────────────────────────────────────┘")
