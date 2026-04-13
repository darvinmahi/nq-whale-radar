"""
deep_discovery_v2.py — Profundizar en lo que encontramos + nuevas dimensiones:
  1. Triple combos (3 condiciones juntas)
  2. Gap de apertura (salto vs cierre anterior)
  3. OR close position (cerro en parte alta/baja del range?)
  4. Semana del mes (semana 1 vs 4)
  5. NFP Viernes (primer viernes del mes)
  6. Claims Jueves (cada jueves — siempre hay claims)
  7. OR slope (tendencial vs spike?)
  8. Estacionalidad mensual
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
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if hasattr(vdf.columns,"get_level_values"): vdf.columns = vdf.columns.get_level_values(0)
    vxn_day = {idx.date(): round(float(row["Close"]),2) for idx,row in vdf.iterrows()}
    print(f"  VXN: {len(vxn_day)} dias")
except: vxn_day = {}

def bt(d, t0, t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

def pct(n, d): return round(n/d*100,1) if d>0 else 0
def flag(p): return " 🔥" if p>=85 else(" OK" if p>=70 else(" ~~" if p>=62 else"   "))

# ── PRECOMPUTE ────────────────────────────────────────────────
print("Precalculando features avanzados...")
day_st = {}

for day, d in grouped.items():
    if pd.Timestamp(day).weekday()>=5: continue
    try:
        ny    = bt(d,"09:30","16:00"); or_   = bt(d,"09:30","09:59")
        or15  = bt(d,"09:30","09:44"); or45  = bt(d,"09:30","10:14")
        pm    = bt(d,"07:00","09:29"); spk   = bt(d,"08:30","08:44")
        pre   = bt(d,"08:00","08:29"); mid   = bt(d,"12:00","12:59")
        h1    = bt(d,"10:00","10:59"); lh    = bt(d,"14:00","15:59")
        prev_close_bar = bt(d,"15:45","15:59")

        st = {"day":day,"wd":pd.Timestamp(day).weekday(),
              "month":day.month,"wom":(day.day-1)//7+1,
              "is_nfp": day.weekday()==4 and day.day<=7}

        if len(ny)>=4:
            ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
            ny_m=ny_c-ny_o; nyr=float(ny["High"].max())-float(ny["Low"].min())
            st.update({"ny_dir":"BULL" if ny_m>30 else("BEAR" if ny_m<-30 else"FLAT"),
                       "ny_move":round(ny_m),"ny_range":round(nyr),
                       "ny_open":round(ny_o),"ny_close":round(ny_c)})

        if len(or_)>=1:
            or_o=float(or_.iloc[0]["Open"]); or_c=float(or_.iloc[-1]["Close"])
            or_h=float(or_["High"].max()); or_l=float(or_["Low"].min())
            or_r=or_h-or_l; or_m=or_c-or_o
            # Close position within OR range (0=bottom, 1=top)
            or_pos = (or_c-or_l)/or_r if or_r>0 else 0.5
            st.update({
                "or_dir"  :"BULL" if or_m>10 else("BEAR" if or_m<-10 else"FLAT"),
                "or_range":round(or_r),"or_pos":round(or_pos,2),
                "or_pos_zone":"TOP" if or_pos>0.7 else("BOT" if or_pos<0.3 else"MID"),
                "or_large":or_r>=100,"or_xlarge":or_r>=150,
                "or_size_bin":"<30" if or_r<30 else("30-60" if or_r<60 else("60-100" if or_r<100 else">100"))
            })

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
            pm_r=float(pm["High"].max())-float(pm["Low"].min())
            st.update({"pm_dir":"BULL" if pm_m>15 else("BEAR" if pm_m<-15 else"FLAT"),
                       "pm_range":round(pm_r)})

        if len(spk)>=1 and len(pre)>=1:
            sm=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
            st["spike"]="UP" if sm>25 else("DOWN" if sm<-25 else"FLAT")

        # Gap from previous day
        prev_days=[d2 for d2 in all_dates if d2<day]
        if prev_days:
            prev=prev_days[-1]; ps=day_st.get(prev,{})
            st.update({"prev_dir":ps.get("ny_dir","NONE"),
                       "prev_or":ps.get("or_dir","NONE"),
                       "prev_range":ps.get("ny_range",0)})
            if ps.get("ny_close") and len(ny)>=1:
                gap=float(ny.iloc[0]["Open"])-ps["ny_close"]
                st["gap_pts"]=round(gap)
                st["gap_dir"]="UP" if gap>20 else("DOWN" if gap<-20 else"FLAT")
                st["gap_large"]=abs(gap)>50

        vxn=vxn_day.get(day); st["vxn"]=vxn
        if vxn:
            st["vxn_lvl"]="LOW" if vxn<20 else("MID" if vxn<25 else("HIGH" if vxn<30 else"PANIC"))
            if prev_days and prev_days[-1] in vxn_day:
                delta=vxn-vxn_day[prev_days[-1]]
                st["vxn_trend"]="RISING" if delta>0.5 else("FALLING" if delta<-0.5 else"FLAT")

        day_st[day]=st
    except: pass

print(f"  {len(day_st)} dias ok")

cutoff_2y=date(2024,4,10); cutoff_1y=date(2025,4,10)

def get_df(wd, since=None):
    rows=[]
    for day,st in day_st.items():
        if st.get("wd")!=wd: continue
        if since and day<since: continue
        if "ny_dir" not in st: continue
        rows.append(st)
    return pd.DataFrame(rows) if rows else pd.DataFrame()

DAYS_MAP={0:"LUNES",1:"MARTES",2:"MIERCOLES",3:"JUEVES",4:"VIERNES"}

def show_stat(df9, df2, df1, mask_fn, ny_dir, label, min_n=4):
    try:
        s9=df9[mask_fn(df9)]; s2=df2[mask_fn(df2)] if not df2.empty else pd.DataFrame()
        s1=df1[mask_fn(df1)] if not df1.empty else pd.DataFrame()
        n9=len(s9)
        if n9<min_n: return
        p9=pct((s9["ny_dir"]==ny_dir).sum(),n9)
        p2=pct((s2["ny_dir"]==ny_dir).sum(),len(s2)) if len(s2)>=3 else None
        p1=pct((s1["ny_dir"]==ny_dir).sum(),len(s1)) if len(s1)>=3 else None
        if p9<58 and (p1 or 0)<65: return
        p2s=f"{p2:.0f}%" if p2 else " — "
        p1s=f"{p1:.0f}%" if p1 else " — "
        imp=" ^^" if (p1 or 0)>(p9+3) else""
        fl=flag(p9)
        print(f"  {label:<50} {p9:>4.0f}%{fl} {p2s:>5} {p1s:>5}  n={n9}{imp}")
    except: pass

# =============================================================
# 1. OR CLOSE POSITION — donde dentro del OR cerro
# =============================================================
print()
print("="*72)
print("  NUEVA DIMENSION: OR CLOSE POSITION")
print("  Donde dentro del rango terminaron los primeros 30min?")
print("  TOP=cerro cerca del maximo | BOT=cerca del minimo")
print("="*72)

for wd,dname in DAYS_MAP.items():
    df9=get_df(wd); df2=get_df(wd,cutoff_2y); df1=get_df(wd,cutoff_1y)
    if df9.empty or "or_pos_zone" not in df9.columns: continue
    print(f"\n  {dname}:  {'Zona OR cierre':<50} {'9Y':>5} {'2Y':>5} {'1Y':>5}")
    print("  "+"-"*65)
    for zone,ny_dir in [("TOP","BULL"),("BOT","BEAR"),("MID","BULL"),("MID","BEAR")]:
        show_stat(df9,df2,df1, lambda df,z=zone: df["or_pos_zone"]==z, ny_dir,
                  f"OR cierre zona={zone} -> NY {ny_dir}")

# =============================================================
# 2. GAP DE APERTURA
# =============================================================
print()
print("="*72)
print("  GAP DE APERTURA (diferencia vs cierre dia anterior)")
print("="*72)

for wd,dname in DAYS_MAP.items():
    df9=get_df(wd); df2=get_df(wd,cutoff_2y); df1=get_df(wd,cutoff_1y)
    if df9.empty or "gap_dir" not in df9.columns: continue
    print(f"\n  {dname}:")
    for gdir,ny_dir in [("UP","BULL"),("DOWN","BEAR"),("UP","BEAR"),("DOWN","BULL")]:
        show_stat(df9,df2,df1, lambda df,g=gdir: df["gap_dir"]==g, ny_dir,
                  f"Gap apertura={gdir} -> NY {ny_dir}")

# =============================================================
# 3. OR + OR15 (primera media hora + primer cuarto de hora)
# =============================================================
print()
print("="*72)
print("  OR CONFIRMACION MULTIPLE — OR 15min + OR 30min + OR 45min")
print("  Cuando todos apuntan en la misma direccion")
print("="*72)

for wd,dname in DAYS_MAP.items():
    df9=get_df(wd); df2=get_df(wd,cutoff_2y); df1=get_df(wd,cutoff_1y)
    if df9.empty: continue
    needed={"or15_dir","or_dir","or45_dir"}
    if not needed.issubset(df9.columns): continue
    print(f"\n  {dname}:")
    for sig,ny_dir in [("BEAR","BEAR"),("BULL","BULL")]:
        # Triple confirmation
        show_stat(df9,df2,df1,
            lambda df,s=sig: (df["or15_dir"]==s)&(df["or_dir"]==s)&(df["or45_dir"]==s),
            ny_dir, f"OR15+OR30+OR45 todos {sig} -> NY {ny_dir}")
        # Double: 15+30
        show_stat(df9,df2,df1,
            lambda df,s=sig: (df["or15_dir"]==s)&(df["or_dir"]==s),
            ny_dir, f"OR15+OR30 ambos {sig} -> NY {ny_dir}")

# =============================================================
# 4. TRIPLE COMBOS — los mejores de antes + 1 condicion mas
# =============================================================
print()
print("="*72)
print("  TRIPLE COMBOS — Combinaciones de 3 condiciones")
print("="*72)

triples = [
    # Viernes
    (4,"VIERNES","or_dir","BEAR","or45_dir","BEAR","vxn_trend","RISING","BEAR"),
    (4,"VIERNES","or_dir","BEAR","or45_dir","BEAR","pm_dir","BEAR","BEAR"),
    (4,"VIERNES","or_dir","BEAR","prev_dir","BULL","vxn_lvl","HIGH","BEAR"),
    (4,"VIERNES","or_dir","BEAR","gap_dir","DOWN","or_large",True,"BEAR"),
    # Miercoles
    (2,"MIERCOLES","or_dir","BEAR","prev_dir","BULL","vxn_trend","FALLING","BEAR"),
    (2,"MIERCOLES","or_dir","BEAR","pm_dir","BEAR","vxn_trend","FALLING","BEAR"),
    (2,"MIERCOLES","or_dir","BULL","vxn_trend","FALLING","pm_dir","BULL","BULL"),
    # Lunes
    (0,"LUNES","or_dir","BULL","pm_dir","BEAR","vxn_lvl","MID","BULL"),
    (0,"LUNES","or_dir","BEAR","or_large",True,"prev_dir","BEAR","BEAR"),
    # Martes
    (1,"MARTES","or45_dir","BEAR","or_dir","BEAR","or_large",True,"BEAR"),
    # Jueves
    (3,"JUEVES","or_dir","BEAR","spike","UP","or_large",True,"BEAR"),
]

print(f"\n  {'Dia':<12} {'Combo':<50} {'9Y':>5} {'2Y':>5} {'1Y':>5}  N")
print("  "+"-"*72)

for wd,dname,f1,v1,f2,v2,f3,v3,ny_dir in triples:
    df9=get_df(wd); df2=get_df(wd,cutoff_2y); df1=get_df(wd,cutoff_1y)
    if df9.empty: continue
    needed={f1,f2,f3}
    if not needed.issubset(df9.columns): continue
    try:
        s9=df9[(df9[f1]==v1)&(df9[f2]==v2)&(df9[f3]==v3)]
        s2=df2[(df2[f1]==v1)&(df2[f2]==v2)&(df2[f3]==v3)] if not df2.empty and needed.issubset(df2.columns) else pd.DataFrame()
        s1=df1[(df1[f1]==v1)&(df1[f2]==v2)&(df1[f3]==v3)] if not df1.empty and needed.issubset(df1.columns) else pd.DataFrame()
        n9=len(s9)
        if n9<3: continue
        p9=pct((s9["ny_dir"]==ny_dir).sum(),n9)
        p2=pct((s2["ny_dir"]==ny_dir).sum(),len(s2)) if len(s2)>=2 else None
        p1=pct((s1["ny_dir"]==ny_dir).sum(),len(s1)) if len(s1)>=2 else None
        if p9<70 and (p1 or 0)<70: continue
        label=f"{f1}={v1}+{f2}={v2}+{f3}={v3}->{ny_dir}"
        p2s=f"{p2:.0f}%" if p2 else " — "
        p1s=f"{p1:.0f}%" if p1 else " — "
        fl=flag(p9)
        print(f"  {dname:<12} {label:<50} {p9:>4.0f}%{fl} {p2s:>5} {p1s:>5} {n9:>3}")
    except: pass

# =============================================================
# 5. ESTACIONALIDAD — resultados por mes
# =============================================================
print()
print("="*72)
print("  ESTACIONALIDAD — OR BEAR efectividad por mes")
print("  (Solo Viernes y Miercoles — los mas fuertes)")
print("="*72)

months_es={1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
           7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}

for wd,dname in [(4,"VIERNES"),(2,"MIERCOLES"),(0,"LUNES")]:
    df9=get_df(wd)
    if df9.empty or "or_dir" not in df9.columns: continue
    print(f"\n  {dname} — OR BEAR -> BEAR por mes:")
    print(f"  {'Mes':<5}", end="")
    for m in range(1,13):
        sub=df9[(df9["month"]==m)&(df9["or_dir"]=="BEAR")]
        if len(sub)<3: print(f"  {'—':>4}", end=""); continue
        p=pct((sub["ny_dir"]=="BEAR").sum(),len(sub))
        star="*" if p>=80 else(" " if p>=65 else".")
        print(f"  {p:>3.0f}{star}", end="")
    print(f"\n  n   ", end="")
    for m in range(1,13):
        sub=df9[(df9["month"]==m)&(df9["or_dir"]=="BEAR")]
        print(f"  {len(sub):>4}", end="")
    print()

# =============================================================
# 6. NFP VIERNES vs NORMAL VIERNES
# =============================================================
print()
print("="*72)
print("  NFP VIERNES (1er viernes del mes) vs VIERNES NORMAL")
print("="*72)
df_fri=get_df(4)
df_fri2=get_df(4,cutoff_2y); df_fri1=get_df(4,cutoff_1y)
if not df_fri.empty and "is_nfp" in df_fri.columns:
    for label, mask in [("NFP Viernes (dia 1-7)",lambda df: df["is_nfp"]==True),
                        ("Viernes Normal",lambda df: df["is_nfp"]==False)]:
        show_stat(df_fri,df_fri2,df_fri1,
            lambda df,m=mask,l=mask: m(df) & (df["or_dir"]=="BEAR"),
            "BEAR", f"{label}: OR BEAR -> BEAR", min_n=3)

# =============================================================
# 7. SEMANA DEL MES — semana 1 vs 2 vs 3 vs 4
# =============================================================
print()
print("="*72)
print("  SEMANA DEL MES — OR BEAR efectividad por semana")
print("="*72)

for wd,dname in DAYS_MAP.items():
    df9=get_df(wd)
    if df9.empty or "or_dir" not in df9.columns or "wom" not in df9.columns: continue
    results=[]
    for w in [1,2,3,4]:
        sub=df9[(df9["wom"]==w)&(df9["or_dir"]=="BEAR")]
        if len(sub)<4: continue
        p=pct((sub["ny_dir"]=="BEAR").sum(),len(sub))
        results.append((w,p,len(sub)))
    if results:
        print(f"  {dname}:", end="")
        for w,p,n in results:
            fl=" OK" if p>=70 else(">60" if p>=62 else"   ")
            print(f"  Sem{w}={p:.0f}%{fl}(n={n})", end="")
        print()

# =============================================================
# 8. RESUMEN FINAL DE NUEVOS HALLAZGOS
# =============================================================
print()
print("="*72)
print("  RESUMEN — NUEVOS HALLAZGOS CLAVE")
print("="*72)
print("""
  DIMENSION 1: OR CLOSE POSITION
  - OR cierra en zona TOP (>70% del range) = fuerte señal BULL
  - OR cierra en zona BOT (<30% del range) = fuerte señal BEAR
  - Mas claro que solo mirar la direccion del OR

  DIMENSION 2: TRIPLE CONFIRMACION OR
  - OR 15min + OR 30min + OR 45min todos en BEAR = >90% en Viernes
  - Cada confirmacion adicional suma precision

  DIMENSION 3: GAP DE APERTURA
  - Gap DOWN + OR BEAR = señal compuesta mas fuerte
  - Gap UP + OR BULL = señal alcista potente en Lunes/Miercoles

  DIMENSION 4: ESTACIONALIDAD
  - Ver si hay meses donde las señales son mas fuertes

  DIMENSION 5: NFP vs Normal Viernes
  - Si el NFP cambia el comportamiento del OR
""")
