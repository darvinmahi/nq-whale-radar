"""
por_ano.py — Estudio organizado por:
  - 9 años completo (base histórica)
  - Año 1: Abril 2024 - Abril 2025
  - Año 2: Abril 2025 - Abril 2026 (el mercado MAS reciente)

Lógica: si una señal funciona en AÑO 1 Y AÑO 2 separados = confiable
Si solo funciona en uno = puede ser suerte
"""
import pandas as pd, numpy as np, pytz
from datetime import datetime, date, time as dtime

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

print("Cargando datos...")
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

# Periodos exactos
ANO1_START = date(2024, 4, 10)   # Año 1 empieza
ANO1_END   = date(2025, 4,  9)   # Año 1 termina
ANO2_START = date(2025, 4, 10)   # Año 2 empieza
ANO2_END   = date(2026, 4, 10)   # Año 2 = hoy

print("Precalculando...")
day_st = {}
for day, d in grouped.items():
    if pd.Timestamp(day).weekday()>=5: continue
    try:
        ny  = bt(d,"09:30","16:00"); or_ = bt(d,"09:30","09:59")
        or15= bt(d,"09:30","09:44"); or45= bt(d,"09:30","10:14")
        pm  = bt(d,"07:00","09:29"); spk = bt(d,"08:30","08:44")
        pre = bt(d,"08:00","08:29"); mid = bt(d,"12:00","12:59")
        h1  = bt(d,"10:00","10:59")

        st={"day":day,"wd":pd.Timestamp(day).weekday()}

        # Periodo
        if ANO1_START<=day<=ANO1_END:   st["periodo"]="ANO1"
        elif ANO2_START<=day<=ANO2_END: st["periodo"]="ANO2"
        else:                           st["periodo"]="HIST"

        if len(ny)>=4:
            ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
            ny_m=ny_c-ny_o; nyr=float(ny["High"].max())-float(ny["Low"].min())
            st["ny_dir"]  ="BULL" if ny_m>30 else("BEAR" if ny_m<-30 else"FLAT")
            st["ny_move"] =round(ny_m); st["ny_range"]=round(nyr)
            st["ny_open"] =round(ny_o); st["ny_close"]=round(ny_c)

        if len(or_)>=1:
            or_m=float(or_.iloc[-1]["Close"])-float(or_.iloc[0]["Open"])
            or_r=float(or_["High"].max())-float(or_["Low"].min())
            or_h=float(or_["High"].max()); or_l=float(or_["Low"].min())
            or_c=float(or_.iloc[-1]["Close"])
            or_pos=(or_c-or_l)/or_r if or_r>0 else 0.5
            st["or_dir"]     ="BULL" if or_m>10 else("BEAR" if or_m<-10 else"FLAT")
            st["or_range"]   =round(or_r)
            st["or_pos_zone"]="TOP" if or_pos>0.7 else("BOT" if or_pos<0.3 else"MID")
            st["or_large"]   =or_r>=100

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

# Conteo por periodo
for p in ["ANO1","ANO2","HIST"]:
    n=len([d for d,s in day_st.items() if s.get("periodo")==p])
    print(f"  {p}: {n} dias hábiles")

def get_df(wd, periodo=None):
    rows=[]
    for day,st in day_st.items():
        if st.get("wd")!=wd: continue
        if periodo and st.get("periodo")!=periodo: continue
        if "ny_dir" not in st: continue
        rows.append(st)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

DAYS={0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES"}

def p_stat(df,feat,val,ny_dir):
    if df.empty or feat not in df.columns: return None,0
    sub=df[df[feat]==val]
    if len(sub)<3: return None,len(sub)
    return pct((sub["ny_dir"]==ny_dir).sum(),len(sub)),len(sub)

def badge(p):
    if p is None: return "  —  "
    if p>=90: return f"{p:.0f}% 🔥"
    if p>=75: return f"{p:.0f}% OK"
    if p>=62: return f"{p:.0f}% ~~"
    return     f"{p:.0f}%   "

def verdict(ph,p1,p2):
    if p1 is None or p2 is None: return "pocos datos"
    if p1>=65 and p2>=65: return "AMBOS ANOS OK  ✅ CONFIABLE"
    if p1>=65 and p2<60:  return "Solo Ano1      ⚠️  DEBILITANDO"
    if p1<60  and p2>=65: return "Solo Ano2      🆕 NUEVA SENAL"
    if p1<60  and p2<60:  return "Ninguno        ❌ SIN EDGE"
    return "mixto"

# ================================================================
# TABLA PRINCIPAL — todas las señales organizadas por año
# ================================================================
print()
print("█"*72)
print("  ESTUDIO POR AÑOS SEPARADOS — NQ Futures")
print(f"  Año 1: Abr 2024 → Abr 2025  |  Año 2: Abr 2025 → Abr 2026")
print("█"*72)

RULES = [
    # (weekday, feat, val, ny_dir, label)
    # LUNES
    (0,"or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (0,"or_dir","BULL","BULL","OR BULL → BULL"),
    (0,"or15_dir","BEAR","BEAR","OR 15min BEAR → BEAR"),
    (0,"pm_dir","BEAR","BEAR","PM BEAR → BEAR"),
    (0,"vxn_trend","RISING","BEAR","VXN SUBIENDO → BEAR"),
    (0,"prev_dir","BEAR","BEAR","Dia anterior BEAR → BEAR"),
    # MARTES
    (1,"or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (1,"or_dir","BULL","BULL","OR BULL → BULL"),
    (1,"or45_dir","BEAR","BEAR","OR 45min BEAR → BEAR"),
    (1,"h1_dir","BULL","BULL","10-11h BULL → BULL"),
    (1,"pm_dir","BEAR","BEAR","PM BEAR → BEAR"),
    # MIERCOLES
    (2,"or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (2,"or_dir","BULL","BULL","OR BULL → BULL"),
    (2,"mid_dir","BULL","BULL","Midday BULL → BULL"),
    (2,"vxn_trend","FALLING","BULL","VXN BAJANDO → BULL"),
    (2,"pm_dir","BEAR","BEAR","PM BEAR → BEAR"),
    # JUEVES
    (3,"or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (3,"or_dir","BULL","BULL","OR BULL → BULL"),
    (3,"mid_dir","BEAR","BEAR","Midday BEAR → BEAR"),
    (3,"spike","DOWN","BEAR","Claims spike DOWN → BEAR"),
    (3,"prev_dir","BEAR","BEAR","Dia anterior BEAR → BEAR"),
    # VIERNES
    (4,"or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (4,"or_dir","BULL","BULL","OR BULL → BULL"),
    (4,"or45_dir","BEAR","BEAR","OR 45min BEAR → BEAR"),
    (4,"vxn_trend","RISING","BEAR","VXN SUBIENDO → BEAR"),
    (4,"vxn_lvl","HIGH","BEAR","VXN ALTO → BEAR"),
    (4,"spike","UP","BULL","Spike 8:30 UP → BULL"),
    (4,"prev_dir","BULL","BEAR","Dia anterior BULL → BEAR"),
]

current_day=""
for wd, feat, val, ny_dir, label in RULES:
    dname=DAYS[wd]
    dfH=get_df(wd)
    dfA1=get_df(wd,"ANO1")
    dfA2=get_df(wd,"ANO2")

    pH,nH=p_stat(dfH,feat,val,ny_dir)
    pA1,nA1=p_stat(dfA1,feat,val,ny_dir)
    pA2,nA2=p_stat(dfA2,feat,val,ny_dir)

    if pH is None and pA1 is None and pA2 is None: continue
    if (pH or 0)<55 and (pA1 or 0)<60 and (pA2 or 0)<60: continue

    if dname!=current_day:
        current_day=dname
        print(f"\n  {'─'*68}")
        print(f"  {dname}")
        print(f"  {'Señal':<30} {'9 AÑOS':>9} {'AÑO 1':>9} {'AÑO 2':>9} {'N1/N2':>7}  Veredicto")
        print(f"  {'─'*68}")

    verd=verdict(pH,pA1,pA2)
    bH =badge(pH); bA1=badge(pA1); bA2=badge(pA2)
    print(f"  {label:<30} {bH:>9} {bA1:>9} {bA2:>9}  {nA1}/{nA2}   {verd}")

# ================================================================
# COMBOS — confirmaciones dobles por año
# ================================================================
print()
print()
print("█"*72)
print("  COMBOS DOBLES — Por año separados")
print("█"*72)

COMBOS = [
    (0,"LUNES",   "or_dir","BEAR","prev_dir","BEAR","BEAR","OR BEAR + Prev BEAR"),
    (0,"LUNES",   "or_dir","BULL","pm_dir",  "BEAR","BULL","OR BULL + PM BEAR"),
    (2,"MIERCOLES","or_dir","BEAR","prev_dir","BULL","BEAR","OR BEAR + Prev BULL"),
    (2,"MIERCOLES","or_dir","BULL","vxn_trend","FALLING","BULL","OR BULL + VXN baja"),
    (2,"MIERCOLES","or_dir","BEAR","pm_dir", "BEAR","BEAR","OR BEAR + PM BEAR"),
    (3,"JUEVES",  "or_dir","BEAR","or_large",True,"BEAR","OR BEAR + OR >100pts"),
    (4,"VIERNES", "or_dir","BEAR","or45_dir","BEAR","BEAR","OR BEAR + OR45 BEAR"),
    (4,"VIERNES", "or_dir","BEAR","prev_dir","BULL","BEAR","OR BEAR + Prev BULL"),
    (4,"VIERNES", "or_dir","BEAR","vxn_trend","RISING","BEAR","OR BEAR + VXN sube"),
    (4,"VIERNES", "or_dir","BEAR","pm_dir",  "BEAR","BEAR","OR BEAR + PM BEAR"),
    (1,"MARTES",  "or45_dir","BEAR","or_dir","BEAR","BEAR","OR45 BEAR + OR BEAR"),
]

print(f"\n  {'Día':<10} {'Combo':<30} {'9 AÑOS':>9} {'AÑO 1':>9} {'AÑO 2':>9}  N1/N2  Veredicto")
print("  "+"─"*80)

for wd,dname,f1,v1,f2,v2,ny_dir,label in COMBOS:
    dfH=get_df(wd); dfA1=get_df(wd,"ANO1"); dfA2=get_df(wd,"ANO2")
    if dfH.empty: continue
    needed={f1,f2}

    def calc(df):
        if df.empty or not needed.issubset(df.columns): return None,0
        sub=df[(df[f1]==v1)&(df[f2]==v2)]
        if len(sub)<2: return None,len(sub)
        return pct((sub["ny_dir"]==ny_dir).sum(),len(sub)),len(sub)

    pH,nH=calc(dfH); pA1,nA1=calc(dfA1); pA2,nA2=calc(dfA2)
    if (pH or 0)<60 and (pA1 or 0)<60 and (pA2 or 0)<60: continue

    verd=verdict(pH,pA1,pA2)
    bH=badge(pH); bA1=badge(pA1); bA2=badge(pA2)
    print(f"  {dname:<10} {label:<30} {bH:>9} {bA1:>9} {bA2:>9}  {nA1}/{nA2}  {verd}")

# ================================================================
# RESUMEN EJECUTIVO — solo las más confiables
# ================================================================
print()
print()
print("█"*72)
print("  RESUMEN EJECUTIVO — Señales CONFIABLES (buenas en Año 1 Y Año 2)")
print("█"*72)
print()
print("  ESTAS SON LAS REGLAS REALES DE TRADING:")
print()
print("  Día         Señal                          Año1   Año2   Conclusión")
print("  "+"─"*72)

executive = [
    (0,"LUNES",   "or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (0,"LUNES",   "or_dir","BULL","BULL","OR BULL → BULL"),
    (2,"MIERCOLES","or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (2,"MIERCOLES","mid_dir","BULL","BULL","Midday BULL → BULL"),
    (3,"JUEVES",  "or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (3,"mid_dir","BEAR","BEAR","na","skip"),
    (4,"VIERNES", "or_dir","BEAR","BEAR","OR BEAR → BEAR"),
    (4,"VIERNES", "or45_dir","BEAR","BEAR","OR 45min BEAR → BEAR"),
    (4,"VIERNES", "vxn_trend","RISING","BEAR","VXN Subiendo → BEAR"),
    (1,"MARTES",  "or45_dir","BEAR","BEAR","OR 45min BEAR → BEAR"),
    (1,"MARTES",  "h1_dir","BULL","BULL","10-11h BULL → BULL"),
]

for item in executive:
    if len(item)==6:
        wd,dname,feat,val,ny_dir,label=item
        if label=="skip": continue
    else: continue
    dfA1=get_df(wd,"ANO1"); dfA2=get_df(wd,"ANO2")
    pA1,nA1=p_stat(dfA1,feat,val,ny_dir)
    pA2,nA2=p_stat(dfA2,feat,val,ny_dir)
    if pA1 is None or pA2 is None: continue
    v=verdict(None,pA1,pA2)
    print(f"  {dname:<12} {label:<30} {badge(pA1):>9} {badge(pA2):>9}  {v}")
