"""
lista_dias.py — Lista TODOS los dias de cada combo uno por uno
Para que puedas verificar fecha a fecha que el backtest es real
"""
import pandas as pd, numpy as np, pytz
from datetime import datetime, date, time as dtime

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

print("Cargando...")
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
all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday() < 5})

try:
    import yfinance as yf
    vdf = yf.download("^VXN", period="30mo", interval="1d", progress=False, auto_adjust=True)
    if hasattr(vdf.columns,"get_level_values"): vdf.columns=vdf.columns.get_level_values(0)
    vxn_day={idx.date():round(float(row["Close"]),2) for idx,row in vdf.iterrows()}
except: vxn_day={}

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

ANO1_START=date(2024,4,10); ANO1_END=date(2025,4,9)
ANO2_START=date(2025,4,10); ANO2_END=date(2026,4,10)
MESES_START=date(2026,1,1)

DAY_NAMES=["Lun","Mar","Mie","Jue","Vie"]

print("Precalculando...")
day_st={}
for day,d in grouped.items():
    if pd.Timestamp(day).weekday()>=5: continue
    try:
        ny=bt(d,"09:30","16:00"); or_=bt(d,"09:30","09:59")
        or15=bt(d,"09:30","09:44"); or45=bt(d,"09:30","10:14")
        pm=bt(d,"07:00","09:29"); spk=bt(d,"08:30","08:44")
        pre=bt(d,"08:00","08:29")

        st={"day":day,"wd":pd.Timestamp(day).weekday()}
        if day>=MESES_START: st["p"]="Meses"
        elif ANO1_START<=day<=ANO1_END: st["p"]="Año1"
        elif ANO2_START<=day<=ANO2_END: st["p"]="Año2"
        else: st["p"]="Hist"

        if len(ny)>=4:
            ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
            ny_m=ny_c-ny_o; ny_h=float(ny["High"].max()); ny_l=float(ny["Low"].min())
            st["ny_dir"]="BULL" if ny_m>30 else("BEAR" if ny_m<-30 else"FLAT")
            st["ny_move"]=round(ny_m); st["ny_open"]=round(ny_o); st["ny_close"]=round(ny_c)
            st["ny_high"]=round(ny_h); st["ny_low"]=round(ny_l)

        if len(or_)>=1:
            or_m=float(or_.iloc[-1]["Close"])-float(or_.iloc[0]["Open"])
            or_r=float(or_["High"].max())-float(or_["Low"].min())
            or_o=float(or_.iloc[0]["Open"]); or_c=float(or_.iloc[-1]["Close"])
            st["or_dir"]="BULL" if or_m>10 else("BEAR" if or_m<-10 else"FLAT")
            st["or_range"]=round(or_r); st["or_large"]=or_r>=100
            st["or_open"]=round(or_o); st["or_close"]=round(or_c)

        if len(or15)>=1:
            m15=float(or15.iloc[-1]["Close"])-float(or15.iloc[0]["Open"])
            st["or15_dir"]="BULL" if m15>10 else("BEAR" if m15<-10 else"FLAT")

        if len(or45)>=1:
            m45=float(or45.iloc[-1]["Close"])-float(or45.iloc[0]["Open"])
            st["or45_dir"]="BULL" if m45>10 else("BEAR" if m45<-10 else"FLAT")

        if len(pm)>=2:
            pm_m=float(pm.iloc[-1]["Close"])-float(pm.iloc[0]["Open"])
            st["pm_dir"]="BULL" if pm_m>15 else("BEAR" if pm_m<-15 else"FLAT")

        if len(spk)>=1 and len(pre)>=1:
            sm=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
            st["spike"]="UP" if sm>25 else("DOWN" if sm<-25 else"FLAT")

        vxn=vxn_day.get(day); st["vxn"]=vxn
        if vxn:
            st["vxn_lvl"]="LOW" if vxn<20 else("MID" if vxn<25 else("HIGH" if vxn<30 else"PANIC"))
            prev_ds=[d2 for d2 in all_dates if d2<day]
            if prev_ds and prev_ds[-1] in vxn_day:
                delta=vxn-vxn_day[prev_ds[-1]]
                st["vxn_trend"]="RISING" if delta>0.5 else("FALLING" if delta<-0.5 else"FLAT")

        prev_ds=[d2 for d2 in all_dates if d2<day]
        if prev_ds:
            ps=day_st.get(prev_ds[-1],{})
            st["prev_dir"]=ps.get("ny_dir","NONE")

        day_st[day]=st
    except: pass

print(f"  {len(day_st)} dias ok\n")

def get_days(wd, periodos=None):
    return [st for day,st in sorted(day_st.items())
            if st.get("wd")==wd and "ny_dir" in st
            and (periodos is None or st.get("p") in periodos)]

def result_icon(actual, target):
    return "✅ ACIERTO" if actual==target else "❌ FALLO  "

sep = "─"*80

# ================================================================
# COMBOS PRINCIPALES — DIA A DIA
# ================================================================

combos = [
    # (wd, label, periodos, condicion_fn, target_ny)
    (4, "VIERNES — OR BEAR → BEAR  [Solo Año1 + Año2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BEAR",
     "BEAR"),

    (4, "VIERNES — OR+OR45 BEAR → BEAR  [1+2 combinados]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BEAR" and s.get("or45_dir")=="BEAR",
     "BEAR"),

    (4, "VIERNES — OR+PM BEAR → BEAR  [1+2 combinados]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BEAR" and s.get("pm_dir")=="BEAR",
     "BEAR"),

    (0, "LUNES — OR BEAR → BEAR  [Año1 + Año2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BEAR",
     "BEAR"),

    (0, "LUNES — OR BULL + PM BEAR → BULL  [1+2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BULL" and s.get("pm_dir")=="BEAR",
     "BULL"),

    (2, "MIÉRCOLES — Midday BULL → BULL  [Año1 + Año2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("mid_dir")=="BULL" if "mid_dir" in s else False,
     "BULL"),

    (2, "MIÉRCOLES — OR BEAR + Prev BULL → BEAR  [1+2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BEAR" and s.get("prev_dir")=="BULL",
     "BEAR"),

    (3, "JUEVES — OR BEAR + OR >100pts → BEAR  [1+2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("or_dir")=="BEAR" and s.get("or_large")==True,
     "BEAR"),

    (1, "MARTES — 10-11h BULL → BULL  [Año1 + Año2]",
     ["Año1","Año2","Meses"],
     lambda s: s.get("h1_dir")=="BULL" if "h1_dir" in s else False,
     "BULL"),
]

# Recalculo h1 para martes
for day,d in grouped.items():
    if pd.Timestamp(day).weekday()!=1: continue
    if day not in day_st: continue
    try:
        h1=bt(d,"10:00","10:59")
        if len(h1)>=1:
            hm=float(h1.iloc[-1]["Close"])-float(h1.iloc[0]["Open"])
            day_st[day]["h1_dir"]="BULL" if hm>10 else("BEAR" if hm<-10 else"FLAT")
    except: pass

# Recalculo mid para miercoles
for day,d in grouped.items():
    if pd.Timestamp(day).weekday()!=2: continue
    if day not in day_st: continue
    try:
        mid=bt(d,"12:00","12:59")
        if len(mid)>=1:
            mm=float(mid.iloc[-1]["Close"])-float(mid.iloc[0]["Open"])
            day_st[day]["mid_dir"]="BULL" if mm>10 else("BEAR" if mm<-10 else"FLAT")
    except: pass

for wd, title, periodos, cond_fn, target in combos:
    days=get_days(wd, periodos)
    match=[s for s in days if cond_fn(s)]
    hits=[s for s in match if s["ny_dir"]==target]
    total=len(match); acertos=len(hits)
    pct_val=round(acertos/total*100,1) if total>0 else 0

    print(sep)
    print(f"  📋 {title}")
    print(f"  Total dias que cumplen condicion: {total}  |  Aciertos: {acertos}  |  Accuracy: {pct_val}%")
    print(sep)
    print(f"  {'#':>3}  {'Fecha':>12}  {'Periodo':>6}  {'OR':>5}  {'OR45':>5}  {'PM':>5}  {'OR rng':>6}  {'NY mov':>7}  {'Resultado'}")
    print("  "+"-"*78)

    for i,s in enumerate(match,1):
        fecha=s["day"].strftime("%d/%m/%Y")
        per=s.get("p","—")
        or_d=s.get("or_dir","—")[:1]
        or45_d=s.get("or45_dir","—")[:1]
        pm_d=s.get("pm_dir","—")[:1]
        or_r=s.get("or_range",0)
        ny_m=s.get("ny_move",0)
        res=result_icon(s["ny_dir"],target)
        large="🔥" if s.get("or_large") else "  "
        print(f"  {i:>3}  {fecha:>12}  {per:>6}  {or_d:>5}  {or45_d:>5}  {pm_d:>5}  {or_r:>5}p{large}  {ny_m:>+7}p  {res}")

    print(f"\n  TOTAL: {acertos}/{total} = {pct_val}%\n")
