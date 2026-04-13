"""
discovery_engine.py — Motor de descubrimiento automatico
Prueba TODAS las combinaciones de predictores y filtra solo
los hallazgos que son estadisticamente validos Y estan mejorando
en el mercado reciente
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
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if hasattr(vdf.columns,"get_level_values"): vdf.columns = vdf.columns.get_level_values(0)
    vxn_day = {idx.date(): round(float(row["Close"]),2) for idx,row in vdf.iterrows()}
    print(f"  VXN: {len(vxn_day)} dias")
except: vxn_day = {}

def bt(d, t0, t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

def pct(n, d): return round(n/d*100,1) if d>0 else 0

print("Precalculando...")
day_st = {}
for day, d in grouped.items():
    if pd.Timestamp(day).weekday()>=5: continue
    try:
        pm   = bt(d,"07:00","09:29"); ny  = bt(d,"09:30","16:00")
        or_  = bt(d,"09:30","09:59"); mid = bt(d,"12:00","12:59")
        h1   = bt(d,"10:00","10:59"); spk = bt(d,"08:30","08:44")
        pre  = bt(d,"08:00","08:29"); or45= bt(d,"09:30","10:14")

        st = {"day":day, "wd":pd.Timestamp(day).weekday(),
              "month":day.month, "week_of_month":(day.day-1)//7+1}

        if len(ny)>=4:
            ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
            ny_m=ny_c-ny_o; nyr=float(ny["High"].max())-float(ny["Low"].min())
            st["ny_dir"]  = "BULL" if ny_m>30 else("BEAR" if ny_m<-30 else"FLAT")
            st["ny_move"] = round(ny_m); st["ny_range"]=round(nyr)

        if len(or_)>=1:
            or_m=float(or_.iloc[-1]["Close"])-float(or_.iloc[0]["Open"])
            or_r=float(or_["High"].max())-float(or_["Low"].min())
            st["or_dir"]  ="BULL" if or_m>10 else("BEAR" if or_m<-10 else"FLAT")
            st["or_range"]=round(or_r)
            st["or_large"]=or_r>=100
            st["or_size_bin"] = (
                "<30" if or_r<30 else ("30-60" if or_r<60 else
                ("60-100" if or_r<100 else(">100"))))

        if len(or45)>=1:
            m45=float(or45.iloc[-1]["Close"])-float(or45.iloc[0]["Open"])
            st["or45_dir"]="BULL" if m45>10 else("BEAR" if m45<-10 else"FLAT")

        if len(mid)>=1:
            mm=float(mid.iloc[-1]["Close"])-float(mid.iloc[0]["Open"])
            st["mid_dir"]="BULL" if mm>10 else("BEAR" if mm<-10 else"FLAT")

        if len(h1)>=1:
            hm=float(h1.iloc[-1]["Close"])-float(h1.iloc[0]["Open"])
            st["h1_dir"]="BULL" if hm>10 else("BEAR" if hm<-10 else"FLAT")

        if len(pm)>=2:
            pm_m=float(pm.iloc[-1]["Close"])-float(pm.iloc[0]["Open"])
            pm_r=float(pm["High"].max())-float(pm["Low"].min())
            st["pm_dir"]  ="BULL" if pm_m>15 else("BEAR" if pm_m<-15 else"FLAT")
            st["pm_range"]=round(pm_r)

        if len(spk)>=1 and len(pre)>=1:
            sm=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
            st["spike"]="UP" if sm>25 else("DOWN" if sm<-25 else"FLAT")

        vxn=vxn_day.get(day); st["vxn"]=vxn
        if vxn:
            st["vxn_lvl"]="LOW" if vxn<20 else("MID" if vxn<25 else("HIGH" if vxn<30 else"PANIC"))
            prev_days=[d2 for d2 in all_dates if d2<day]
            prev=prev_days[-1] if prev_days else None
            if prev and prev in vxn_day:
                delta=vxn-vxn_day[prev]
                st["vxn_trend"]="RISING" if delta>0.5 else("FALLING" if delta<-0.5 else"FLAT")

        # Previous day
        prev_days=[d2 for d2 in all_dates if d2<day]
        if prev_days:
            prev=prev_days[-1]
            ps=day_st.get(prev,{})
            st["prev_dir"] =ps.get("ny_dir","NONE")
            st["prev_or"]  =ps.get("or_dir","NONE")
            st["prev_range"]=ps.get("ny_range",0)
            st["prev_large"]=ps.get("ny_range",0)>200

        day_st[day]=st
    except: pass

print(f"  {len(day_st)} dias ok")

# Periodos
cutoff_2y = date(2024,4,10); cutoff_1y = date(2025,4,10)

def get_df(wd, since=None):
    rows=[]
    for day,st in day_st.items():
        if st.get("wd")!=wd: continue
        if since and day<since: continue
        if "ny_dir" not in st: continue
        rows.append(st)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

DAYS_MAP={0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES"}

# ================================================================
# MOTOR DE DESCUBRIMIENTO
# Prueba todas las combinaciones posibles
# ================================================================
discoveries = []

print("Buscando hallazgos...")

# Lista de features a combinar
SINGLE_FEATS = [
    ("or_dir",["BULL","BEAR"]),
    ("or45_dir",["BULL","BEAR"]),
    ("mid_dir",["BULL","BEAR"]),
    ("h1_dir",["BULL","BEAR"]),
    ("pm_dir",["BULL","BEAR"]),
    ("spike",["UP","DOWN"]),
    ("vxn_lvl",["LOW","MID","HIGH","PANIC"]),
    ("vxn_trend",["RISING","FALLING"]),
    ("prev_dir",["BULL","BEAR"]),
    ("prev_or",["BULL","BEAR"]),
    ("or_large",[True]),
    ("or_size_bin",["<30","30-60","60-100",">100"]),
]

COMBO_PAIRS = [
    ("or_dir","vxn_lvl"),
    ("or_dir","vxn_trend"),
    ("or_dir","prev_dir"),
    ("or_dir","pm_dir"),
    ("or_dir","spike"),
    ("or_dir","or_large"),
    ("or45_dir","or_dir"),
    ("pm_dir","vxn_lvl"),
    ("spike","or_dir"),
    ("prev_dir","or_dir"),
    ("or_dir","month"),
]

target_map = {"BULL":"BULL","BEAR":"BEAR","UP":"BULL","DOWN":"BEAR"}

for wd, dname in DAYS_MAP.items():
    df9 = get_df(wd); df2 = get_df(wd, cutoff_2y); df1 = get_df(wd, cutoff_1y)
    if df9.empty: continue

    # Single feature tests
    for feat, vals in SINGLE_FEATS:
        if feat not in df9.columns: continue
        for val in vals:
            ny_tgt = target_map.get(str(val)) if isinstance(val,str) else None
            for ny_dir in (["BULL","BEAR"] if ny_tgt is None else [ny_tgt]):
                sub9 = df9[df9[feat]==val]; n9=len(sub9)
                if n9<6: continue
                p9=pct((sub9["ny_dir"]==ny_dir).sum(),n9)
                if p9<58: continue

                sub2=df2[df2[feat]==val] if not df2.empty and feat in df2.columns else pd.DataFrame()
                sub1=df1[df1[feat]==val] if not df1.empty and feat in df1.columns else pd.DataFrame()
                p2=pct((sub2["ny_dir"]==ny_dir).sum(),len(sub2)) if len(sub2)>=4 else None
                p1=pct((sub1["ny_dir"]==ny_dir).sum(),len(sub1)) if len(sub1)>=3 else None

                # Stability score
                vals_present=[v for v in [p9,p2,p1] if v is not None]
                stable = max(vals_present)-min(vals_present)<15 if len(vals_present)>=2 else False
                improving = (p1 or 0)>(p9 or 0) if p1 else False

                discoveries.append({
                    "day":dname,"type":"single","label":f"{feat}={val} -> {ny_dir}",
                    "p9":p9,"n9":n9,"p2":p2,"n2":len(sub2),"p1":p1,"n1":len(sub1),
                    "stable":stable,"improving":improving,
                    "score":p9 + (10 if improving else 0) + (5 if stable else 0)
                })

    # Combo feature tests (2 conditions)
    for f1, f2 in COMBO_PAIRS:
        if f1 not in df9.columns or f2 not in df9.columns: continue
        for v1 in df9[f1].dropna().unique():
            if str(v1) in ("NONE","FLAT"): continue
            for v2 in df9[f2].dropna().unique():
                if str(v2) in ("NONE","FLAT"): continue
                ny_tgt = target_map.get(str(v1)) if isinstance(v1,str) else None
                for ny_dir in (["BULL","BEAR"] if ny_tgt is None else [ny_tgt]):
                    sub9=df9[(df9[f1]==v1)&(df9[f2]==v2)]; n9=len(sub9)
                    if n9<5: continue
                    p9=pct((sub9["ny_dir"]==ny_dir).sum(),n9)
                    if p9<65: continue

                    sub2=df2[(df2[f1]==v1)&(df2[f2]==v2)] if not df2.empty and f1 in df2.columns and f2 in df2.columns else pd.DataFrame()
                    sub1=df1[(df1[f1]==v1)&(df1[f2]==v2)] if not df1.empty and f1 in df1.columns and f2 in df1.columns else pd.DataFrame()
                    p2=pct((sub2["ny_dir"]==ny_dir).sum(),len(sub2)) if len(sub2)>=3 else None
                    p1=pct((sub1["ny_dir"]==ny_dir).sum(),len(sub1)) if len(sub1)>=2 else None

                    improving=(p1 or 0)>(p9 or 0) if p1 else False
                    discoveries.append({
                        "day":dname,"type":"combo","label":f"{f1}={v1}+{f2}={v2} -> {ny_dir}",
                        "p9":p9,"n9":n9,"p2":p2,"n2":len(sub2),"p1":p1,"n1":len(sub1),
                        "stable":True,"improving":improving,
                        "score":p9 + (15 if improving else 0) + (5 if (p1 or 0)>=70 else 0)
                    })

print(f"  {len(discoveries)} combinaciones probadas")

# ================================================================
# FILTRAR Y MOSTRAR SOLO LOS MEJORES
# ================================================================
df_disc = pd.DataFrame(discoveries)
df_disc = df_disc.sort_values("score", ascending=False)

# Top hallazgos por dia
print()
print("="*72)
print("  TOP HALLAZGOS POR DIA — Combinaciones que mejoran en el tiempo")
print("="*72)

for dname in ["LUNES","MARTES","MIERCOLES","JUEVES","VIERNES"]:
    sub = df_disc[df_disc["day"]==dname].head(8)
    if sub.empty: continue
    print(f"\n  {dname}:")
    print(f"  {'Combinacion':<42} {'9Y':>5} {'2Y':>5} {'1Y':>5} {'N':>4}")
    print("  " + "-"*62)
    shown=0
    for _,r in sub.iterrows():
        p2s = f"{r.p2:.0f}%" if r.p2 else " — "
        p1s = f"{r.p1:.0f}%" if r.p1 else " — "
        trend = " ^^" if r.improving else ""
        flag  = " OK" if r.p9>=70 else(" ~~" if r.p9>=62 else"")
        print(f"  {r.label:<42} {r.p9:>4.0f}%{flag} {p2s:>5} {p1s:>5}  {r.n9:>3}{trend}")
        shown+=1
        if shown>=6: break

# HALLAZGOS ESTRELLA — mejoran Y son fuertes
print()
print("="*72)
print("  HALLAZGOS ESTRELLA — Fuertes (>=70%) Y mejorando con el tiempo")  
print("="*72)
stars = df_disc[(df_disc["p9"]>=70)&(df_disc["improving"]==True)&(df_disc["n9"]>=5)]
print(f"\n  {'Dia':<12} {'Combinacion':<40} {'9Y':>5} {'2Y':>5} {'1Y':>5}  N")
print("  "+"-"*70)
for _,r in stars.head(15).iterrows():
    p2s=f"{r.p2:.0f}%" if r.p2 else " — "
    p1s=f"{r.p1:.0f}%" if r.p1 else " — "
    print(f"  {r.day:<12} {r.label:<40} {r.p9:>4.0f}%  {p2s:>5}  {p1s:>5} {r.n9:>3}")

# NUEVAS SEÑALES — solo fuertes en 1Y aunque no en 9Y (mercado nuevo)
print()
print("="*72)
print("  SEÑALES EMERGENTES — Debiles en 9Y pero NUEVAS y FUERTES en 1Y")
print("="*72)
emerging = df_disc[(df_disc["p9"]<65)&(df_disc["p1"]>=70)&(df_disc["n1"]>=4)]
print(f"\n  {'Dia':<12} {'Combinacion':<40} {'9Y':>5} {'2Y':>5} {'1Y':>5}  N1")
print("  "+"-"*70)
for _,r in emerging.sort_values("p1",ascending=False).head(10).iterrows():
    p2s=f"{r.p2:.0f}%" if r.p2 else " — "
    p1s=f"{r.p1:.0f}%" if r.p1 else " — "
    print(f"  {r.day:<12} {r.label:<40} {r.p9:>4.0f}%  {p2s:>5}  {p1s:>5} {r.n1:>3}")
