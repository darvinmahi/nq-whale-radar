"""
estudio_completo.py — Estructura final:

  ÚLTIMOS MESES  →  AÑO 1  →  AÑO 2  →  AÑOS 1+2 COMBINADOS

  Últimos meses : Enero 2026 - Abril 2026  (~3 meses, el mercado MÁS reciente)
  Año 1         : Abril 2024 - Abril 2025
  Año 2         : Abril 2025 - Abril 2026
  1+2 combinados: Abril 2024 - Abril 2026  (los dos años juntos = muestra grande)
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
    print(f"  VXN: {len(vxn_day)} dias")
except: vxn_day={}

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

def pct(n,d): return round(n/d*100,1) if d>0 else 0

# ── PERIODOS ─────────────────────────────────────────────────
MESES_START = date(2026,  1,  1)   # Últimos ~3 meses
MESES_END   = date(2026,  4, 10)

ANO1_START  = date(2024,  4, 10)
ANO1_END    = date(2025,  4,  9)

ANO2_START  = date(2025,  4, 10)
ANO2_END    = date(2026,  4, 10)

COMBO_START = date(2024,  4, 10)   # 1+2 juntos
COMBO_END   = date(2026,  4, 10)

print("Precalculando...")
day_st = {}
for day, d in grouped.items():
    if pd.Timestamp(day).weekday()>=5: continue
    try:
        ny   = bt(d,"09:30","16:00"); or_  = bt(d,"09:30","09:59")
        or15 = bt(d,"09:30","09:44"); or45 = bt(d,"09:30","10:14")
        pm   = bt(d,"07:00","09:29"); spk  = bt(d,"08:30","08:44")
        pre  = bt(d,"08:00","08:29"); mid  = bt(d,"12:00","12:59")
        h1   = bt(d,"10:00","10:59")

        st = {"day":day,"wd":pd.Timestamp(day).weekday()}

        # Periodo
        if   MESES_START<=day<=MESES_END:  st["p"]="MESES"
        elif ANO1_START <=day<=ANO1_END:   st["p"]="ANO1"
        elif ANO2_START <=day<=ANO2_END:   st["p"]="ANO2"
        else:                              st["p"]="HIST"

        if len(ny)>=4:
            ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
            ny_m=ny_c-ny_o; nyr=float(ny["High"].max())-float(ny["Low"].min())
            st["ny_dir"]  ="BULL" if ny_m>30 else("BEAR" if ny_m<-30 else"FLAT")
            st["ny_move"] =round(ny_m); st["ny_range"]=round(nyr)
            st["ny_open"] =round(ny_o); st["ny_close"]=round(ny_c)

        if len(or_)>=1:
            or_m=float(or_.iloc[-1]["Close"])-float(or_.iloc[0]["Open"])
            or_r=float(or_["High"].max())-float(or_["Low"].min())
            or_c=float(or_.iloc[-1]["Close"]); or_l=float(or_["Low"].min())
            or_pos=(or_c-or_l)/or_r if or_r>0 else 0.5
            st["or_dir"]     ="BULL" if or_m>10 else("BEAR" if or_m<-10 else"FLAT")
            st["or_range"]   =round(or_r)
            st["or_large"]   =or_r>=100
            st["or_pos_zone"]="TOP" if or_pos>0.7 else("BOT" if or_pos<0.3 else"MID")

        if len(or15)>=1:
            m15=float(or15.iloc[-1]["Close"])-float(or15.iloc[0]["Open"])
            st["or15_dir"]="BULL" if m15>10 else("BEAR" if m15<-10 else"FLAT")

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
            st["prev_or"] =ps.get("or_dir","NONE")

        day_st[day]=st
    except: pass

print(f"  {len(day_st)} dias ok")
for p in ["MESES","ANO1","ANO2","HIST"]:
    n=len([d for d,s in day_st.items() if s.get("p")==p])
    print(f"  {p}: {n} dias hábiles")

DAYS={0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES"}

def get_df(wd, periodos):
    rows=[]
    for day,st in day_st.items():
        if st.get("wd")!=wd: continue
        if st.get("p") not in periodos: continue
        if "ny_dir" not in st: continue
        rows.append(st)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

def stat(df, feat, val, ny_dir, min_n=3):
    if df.empty or feat not in df.columns: return None,0
    sub=df[df[feat]==val]
    n=len(sub)
    if n<min_n: return None,n
    return pct((sub["ny_dir"]==ny_dir).sum(),n),n

def badge(p,n):
    if p is None: return f"  — ({n})" if n>0 else "   —  "
    if p>=90: return f"{p:.0f}%🔥(n={n})"
    if p>=75: return f"{p:.0f}%OK(n={n})"
    if p>=62: return f"{p:.0f}%~~(n={n})"
    return     f"{p:.0f}%  (n={n})"

def verdict(pM,p1,p2,pC):
    vals=[v for v in [p1,p2] if v is not None]
    if not vals: return "sin datos"
    if all(v>=65 for v in vals): icon="✅ CONFIABLE"
    elif any(v>=65 for v in vals): icon="⚠️ PARCIAL"
    else: icon="❌ SIN EDGE"
    if (pM or 0)>=75: icon+=" 🔥HOY"
    return icon

RULES = [
    # (wd, feat, val, ny_dir, label)
    (0,"or_dir","BEAR","BEAR","LUNES   — OR BEAR → BEAR"),
    (0,"or_dir","BULL","BULL","LUNES   — OR BULL → BULL"),
    (0,"or45_dir","BEAR","BEAR","LUNES   — OR 45min BEAR → BEAR"),
    (0,"pm_dir","BEAR","BEAR","LUNES   — PreMkt BEAR → BEAR"),
    (0,"vxn_trend","RISING","BEAR","LUNES   — VXN Sube → BEAR"),
    (1,"or_dir","BEAR","BEAR","MARTES  — OR BEAR → BEAR"),
    (1,"or_dir","BULL","BULL","MARTES  — OR BULL → BULL"),
    (1,"or45_dir","BEAR","BEAR","MARTES  — OR 45min BEAR → BEAR"),
    (1,"h1_dir","BULL","BULL","MARTES  — 10-11h BULL → BULL"),
    (2,"or_dir","BEAR","BEAR","MIER    — OR BEAR → BEAR"),
    (2,"or_dir","BULL","BULL","MIER    — OR BULL → BULL"),
    (2,"mid_dir","BULL","BULL","MIER    — Midday BULL → BULL"),
    (2,"vxn_trend","FALLING","BULL","MIER    — VXN Baja → BULL"),
    (2,"pm_dir","BEAR","BEAR","MIER    — PreMkt BEAR → BEAR"),
    (3,"or_dir","BEAR","BEAR","JUEVES  — OR BEAR → BEAR"),
    (3,"or_dir","BULL","BULL","JUEVES  — OR BULL → BULL"),
    (3,"or45_dir","BEAR","BEAR","JUEVES  — OR 45min BEAR → BEAR"),
    (3,"mid_dir","BEAR","BEAR","JUEVES  — Midday BEAR → BEAR"),
    (4,"or_dir","BEAR","BEAR","VIERNES — OR BEAR → BEAR"),
    (4,"or_dir","BULL","BULL","VIERNES — OR BULL → BULL"),
    (4,"or45_dir","BEAR","BEAR","VIERNES — OR 45min BEAR → BEAR"),
    (4,"vxn_trend","RISING","BEAR","VIERNES — VXN Sube → BEAR"),
    (4,"vxn_lvl","HIGH","BEAR","VIERNES — VXN Alto → BEAR"),
    (4,"pm_dir","BEAR","BEAR","VIERNES — PreMkt BEAR → BEAR"),
    (4,"prev_dir","BULL","BEAR","VIERNES — Dia prev BULL → BEAR"),
]

print()
print("▓"*80)
print("  ESTUDIO COMPLETO POR PERIODOS — NQ Futures OR Strategy")
print("  Últ.Meses=Ene-Abr2026  |  Año1=Abr24-Abr25  |  Año2=Abr25-Abr26  |  1+2=2años")
print("▓"*80)
print()
print(f"  {'Señal':<30} {'ÚLT.MESES':>14} {'AÑO 1':>14} {'AÑO 2':>14} {'AÑOS 1+2':>14}  Veredicto")
print("  "+"─"*90)

prev_day_label=""
for wd, feat, val, ny_dir, label in RULES:
    day_label=label.split("—")[0].strip()
    dfM=get_df(wd,["MESES"])
    dfA1=get_df(wd,["ANO1"])
    dfA2=get_df(wd,["ANO2"])
    dfC =get_df(wd,["ANO1","ANO2"])

    pM,nM=stat(dfM,feat,val,ny_dir,min_n=2)
    pA1,nA1=stat(dfA1,feat,val,ny_dir)
    pA2,nA2=stat(dfA2,feat,val,ny_dir)
    pC,nC =stat(dfC, feat,val,ny_dir)

    if (pA1 or 0)<50 and (pA2 or 0)<50 and (pC or 0)<55: continue

    if day_label!=prev_day_label:
        if prev_day_label: print()
        prev_day_label=day_label

    v=verdict(pM,pA1,pA2,pC)
    short_label=label.split("—")[1].strip()
    print(f"  {short_label:<30} {badge(pM,nM):>14} {badge(pA1,nA1):>14} {badge(pA2,nA2):>14} {badge(pC,nC):>14}  {v}")

# COMBOS
print()
print("▓"*80)
print("  COMBOS DOBLES — Por periodo")
print("▓"*80)
print()
print(f"  {'Combo':<35} {'ÚLT.MESES':>14} {'AÑO 1':>14} {'AÑO 2':>14} {'AÑOS 1+2':>14}  Veredicto")
print("  "+"─"*95)

COMBOS=[
    (4,"VIERNES","or_dir","BEAR","or45_dir","BEAR","BEAR","VIE: OR+OR45 BEAR → BEAR"),
    (4,"VIERNES","or_dir","BEAR","pm_dir","BEAR","BEAR","VIE: OR+PM BEAR → BEAR"),
    (4,"VIERNES","or_dir","BEAR","prev_dir","BULL","BEAR","VIE: OR BEAR+Prev BULL → BEAR"),
    (4,"VIERNES","or_dir","BEAR","vxn_trend","RISING","BEAR","VIE: OR BEAR+VXN sube → BEAR"),
    (2,"MIERCOLES","or_dir","BEAR","prev_dir","BULL","BEAR","MIER: OR BEAR+Prev BULL → BEAR"),
    (2,"MIERCOLES","or_dir","BULL","vxn_trend","FALLING","BULL","MIER: OR BULL+VXN baja → BULL"),
    (0,"LUNES","or_dir","BEAR","prev_dir","BEAR","BEAR","LUN: OR BEAR+Prev BEAR → BEAR"),
    (0,"LUNES","or_dir","BULL","pm_dir","BEAR","BULL","LUN: OR BULL+PM BEAR → BULL"),
    (3,"JUEVES","or_dir","BEAR","or_large",True,"BEAR","JUE: OR BEAR+OR >100pts → BEAR"),
    (1,"MARTES","or45_dir","BEAR","or_dir","BEAR","BEAR","MAR: OR45+OR BEAR → BEAR"),
]

for wd,dname,f1,v1,f2,v2,ny_dir,label in COMBOS:
    dfM=get_df(wd,["MESES"]); dfA1=get_df(wd,["ANO1"])
    dfA2=get_df(wd,["ANO2"]); dfC=get_df(wd,["ANO1","ANO2"])

    def cs(df,min_n=2):
        if df.empty or f1 not in df.columns or f2 not in df.columns: return None,0
        sub=df[(df[f1]==v1)&(df[f2]==v2)]; n=len(sub)
        if n<min_n: return None,n
        return pct((sub["ny_dir"]==ny_dir).sum(),n),n

    pM,nM=cs(dfM,1); pA1,nA1=cs(dfA1); pA2,nA2=cs(dfA2); pC,nC=cs(dfC)
    if (pA1 or 0)<60 and (pA2 or 0)<60 and (pC or 0)<65: continue
    v=verdict(pM,pA1,pA2,pC)
    print(f"  {label:<35} {badge(pM,nM):>14} {badge(pA1,nA1):>14} {badge(pA2,nA2):>14} {badge(pC,nC):>14}  {v}")

# RESUMEN FINAL
print()
print("▓"*80)
print("  RESUMEN FINAL — Solo las señales CONFIABLES en AMBOS años")
print("▓"*80)
print()
print("  🏆 SEÑALES PROBADAS EN AÑO 1 Y AÑO 2 (doble validación):")
print()

keeps=[]
for wd, feat, val, ny_dir, label in RULES:
    dfA1=get_df(wd,["ANO1"]); dfA2=get_df(wd,["ANO2"]); dfC=get_df(wd,["ANO1","ANO2"])
    pA1,nA1=stat(dfA1,feat,val,ny_dir); pA2,nA2=stat(dfA2,feat,val,ny_dir); pC,nC=stat(dfC,feat,val,ny_dir)
    if (pA1 or 0)>=65 and (pA2 or 0)>=65:
        keeps.append((label,pA1,nA1,pA2,nA2,pC,nC))

print(f"  {'Señal':<35} {'Año1':>10} {'Año2':>10} {'1+2':>10}")
print("  "+"─"*65)
for label,pA1,nA1,pA2,nA2,pC,nC in sorted(keeps,key=lambda x:-x[5] if x[5] else 0):
    short=label.split("—")[1].strip() if "—" in label else label
    day=label.split("—")[0].strip()
    print(f"  {day:<9} {short:<27} {badge(pA1,nA1):>10} {badge(pA2,nA2):>10} {badge(pC,nC):>10}")
