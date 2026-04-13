"""
tabla_maestra.py — CUADRO COMPLETO
Columnas: 2Y_combinado | Año1 | Año2 | 6 meses
Filas: cada señal por día de la semana
Muestra => % acierto (n=días que se activó)
"""
import pandas as pd, numpy as np, pytz
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

# PERIODOS
P6M_S  = date(2025, 10, 10)   # Últimos 6 meses
P6M_E  = date(2026,  4, 10)
A1_S   = date(2024,  4, 10)   # Año 1
A1_E   = date(2025,  4,  9)
A2_S   = date(2025,  4, 10)   # Año 2
A2_E   = date(2026,  4, 10)
A12_S  = date(2024,  4, 10)   # 2 años combinados
A12_E  = date(2026,  4, 10)

def get_periodo(day):
    labels = []
    if A12_S <= day <= A12_E: labels.append("2Y")
    if A1_S  <= day <= A1_E:  labels.append("A1")
    if A2_S  <= day <= A2_E:  labels.append("A2")
    if P6M_S <= day <= P6M_E: labels.append("6M")
    return labels

print("Procesando...")
day_st = {}
for day, d in grouped.items():
    if pd.Timestamp(day).weekday() >= 5: continue
    periodos = get_periodo(day)
    if not periodos: continue
    try:
        ny   = bt(d,"09:30","16:00"); or_  = bt(d,"09:30","09:59")
        or45 = bt(d,"09:30","10:14"); pm   = bt(d,"07:00","09:29")
        spk  = bt(d,"08:30","08:44"); pre  = bt(d,"08:00","08:29")
        mid  = bt(d,"12:00","12:59"); h1   = bt(d,"10:00","10:59")
        if len(ny)<4 or len(or_)<1: continue

        ny_m  = float(ny.iloc[-1]["Close"]) - float(ny.iloc[0]["Open"])
        or_m  = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
        or_r  = float(or_["High"].max())    - float(or_["Low"].min())
        or45_m= float(or45.iloc[-1]["Close"])-float(or45.iloc[0]["Open"]) if len(or45)>=1 else 0
        pm_m  = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"])   if len(pm)>=2 else 0

        st = {"day":day,"wd":pd.Timestamp(day).weekday(),"periodos":periodos}
        st["ny_d"]  = "BULL" if ny_m>30  else("BEAR" if ny_m<-30 else"FLAT")
        st["ny_m"]  = round(ny_m)
        st["or_d"]  = "BULL" if or_m>10  else("BEAR" if or_m<-10 else"FLAT")
        st["or_r"]  = round(or_r)
        st["or45_d"]= "BULL" if or45_m>10 else("BEAR" if or45_m<-10 else"FLAT")
        st["pm_d"]  = "BULL" if pm_m>15  else("BEAR" if pm_m<-15 else"FLAT")
        st["or_large"] = or_r >= 100

        if len(mid)>=1:
            mm=float(mid.iloc[-1]["Close"])-float(mid.iloc[0]["Open"])
            st["mid_d"]="BULL" if mm>10 else("BEAR" if mm<-10 else"FLAT")
        if len(h1)>=1:
            hm=float(h1.iloc[-1]["Close"])-float(h1.iloc[0]["Open"])
            st["h1_d"]="BULL" if hm>10 else("BEAR" if hm<-10 else"FLAT")

        vxn=vxn_day.get(day)
        if vxn:
            prev_ds=[d2 for d2 in all_dates if d2<day]
            if prev_ds and prev_ds[-1] in vxn_day:
                delta=vxn-vxn_day[prev_ds[-1]]
                st["vxn_t"]="RISING" if delta>0.5 else("FALLING" if delta<-0.5 else"FLAT")

        prev_ds=[d2 for d2 in all_dates if d2<day]
        if prev_ds:
            ps=day_st.get(prev_ds[-1],{})
            st["prev_d"]=ps.get("ny_d","NONE")

        if len(spk)>=1 and len(pre)>=1:
            sm=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
            st["spike"]="UP" if sm>25 else("DOWN" if sm<-25 else"FLAT")

        day_st[day]=st
    except: pass

print(f"  {len(day_st)} días ok")

# Conteo por periodo/día
for p in ["2Y","A1","A2","6M"]:
    n=len([d for d,s in day_st.items() if p in s.get("periodos",[])])
    print(f"  {p}: {n} días hábiles totales")

DAYS = {0:"LUNES",1:"MARTES",2:"MIER",3:"JUEVES",4:"VIERNES"}

def get_df(wd, periodo):
    return [s for d,s in day_st.items()
            if s["wd"]==wd and periodo in s.get("periodos",[]) and "ny_d" in s]

def stat(rows, feat, val, ny_target):
    sub=[r for r in rows if r.get(feat)==val]
    n=len(sub)
    if n<2: return None,n
    hits=sum(1 for r in sub if r["ny_d"]==ny_target)
    return round(hits/n*100), n

def cell(p,n,total_dias):
    if p is None: return f"  — ({n})" if n>0 else "    —    "
    freq=round(n/total_dias*100) if total_dias>0 else 0
    icon="🔥" if p>=90 else("✅" if p>=75 else("~" if p>=62 else"✗"))
    return f"{p:>3}%{icon} {n}d"

# SEÑALES A ESTUDIAR POR DÍA
SIGNALS = {
    0: [  # LUNES
        ("OR BEAR → BEAR",    "or_d","BEAR","BEAR"),
        ("OR BULL → BULL",    "or_d","BULL","BULL"),
        ("OR45 BEAR → BEAR",  "or45_d","BEAR","BEAR"),
        ("PM BEAR → BEAR",    "pm_d","BEAR","BEAR"),
        ("VXN Sube → BEAR",   "vxn_t","RISING","BEAR"),
        ("PrevDay BEAR→BEAR", "prev_d","BEAR","BEAR"),
    ],
    1: [  # MARTES
        ("OR BEAR → BEAR",    "or_d","BEAR","BEAR"),
        ("OR BULL → BULL",    "or_d","BULL","BULL"),
        ("OR45 BEAR → BEAR",  "or45_d","BEAR","BEAR"),
        ("10-11h BULL→BULL",  "h1_d","BULL","BULL"),
        ("PM BEAR → BEAR",    "pm_d","BEAR","BEAR"),
    ],
    2: [  # MIÉRCOLES
        ("OR BEAR → BEAR",    "or_d","BEAR","BEAR"),
        ("OR BULL → BULL",    "or_d","BULL","BULL"),
        ("Midday BULL→BULL",  "mid_d","BULL","BULL"),
        ("Midday BEAR→BEAR",  "mid_d","BEAR","BEAR"),
        ("VXN Baja → BULL",   "vxn_t","FALLING","BULL"),
        ("PM BEAR → BEAR",    "pm_d","BEAR","BEAR"),
    ],
    3: [  # JUEVES
        ("OR BEAR → BEAR",    "or_d","BEAR","BEAR"),
        ("OR BULL → BULL",    "or_d","BULL","BULL"),
        ("OR45 BEAR → BEAR",  "or45_d","BEAR","BEAR"),
        ("Midday BEAR→BEAR",  "mid_d","BEAR","BEAR"),
        ("Claims DOWN→BEAR",  "spike","DOWN","BEAR"),
    ],
    4: [  # VIERNES
        ("OR BEAR → BEAR",    "or_d","BEAR","BEAR"),
        ("OR BULL → BULL",    "or_d","BULL","BULL"),
        ("OR45 BEAR → BEAR",  "or45_d","BEAR","BEAR"),
        ("PM BEAR  → BEAR",   "pm_d","BEAR","BEAR"),
        ("VXN Sube → BEAR",   "vxn_t","RISING","BEAR"),
        ("PrevDay BULL→BEAR", "prev_d","BULL","BEAR"),
    ],
}

print()
print("▓"*84)
print("  CUADRO MAESTRO — NQ Futures Opening Range Study")
print("  Señal: % acierto  (n=días activado de total del periodo)")
print("▓"*84)

for wd in range(5):
    rows_2Y = get_df(wd,"2Y")
    rows_A1 = get_df(wd,"A1")
    rows_A2 = get_df(wd,"A2")
    rows_6M = get_df(wd,"6M")

    n2Y=len(rows_2Y); nA1=len(rows_A1); nA2=len(rows_A2); n6M=len(rows_6M)

    print()
    print(f"  ╔{'═'*80}╗")
    print(f"  ║  {DAYS[wd]:<10} │ Total días: 2Y={n2Y}  A1={nA1}  A2={nA2}  6M={n6M}{' '*(37-len(str(n2Y))-len(str(nA1))-len(str(nA2))-len(str(n6M)))}║")
    print(f"  ╠{'═'*80}╣")
    print(f"  ║  {'Señal':<22}  {'2 AÑOS':>12}  {'AÑO 1':>12}  {'AÑO 2':>12}  {'6 MESES':>12}  ║")
    print(f"  ╠{'─'*80}╣")

    for label, feat, val, tgt in SIGNALS[wd]:
        p2Y,n_2Y = stat(rows_2Y,feat,val,tgt)
        pA1,n_A1 = stat(rows_A1,feat,val,tgt)
        pA2,n_A2 = stat(rows_A2,feat,val,tgt)
        p6M,n_6M = stat(rows_6M,feat,val,tgt)

        # Solo mostrar si al menos un periodo tiene señal >= 60%
        vals=[v for v in [p2Y,pA1,pA2,p6M] if v is not None]
        if not vals or max(vals)<55: continue

        c2Y=cell(p2Y,n_2Y,n2Y); cA1=cell(pA1,n_A1,nA1)
        cA2=cell(pA2,n_A2,nA2); c6M=cell(p6M,n_6M,n6M)

        print(f"  ║  {label:<22}  {c2Y:>12}  {cA1:>12}  {cA2:>12}  {c6M:>12}  ║")

    print(f"  ╚{'═'*80}╝")

# COMBOS
print()
print("▓"*84)
print("  COMBOS — Dos condiciones juntas")
print("▓"*84)

COMBOS = [
    (4,"VIERNES","OR+OR45 BEAR→BEAR",   "or_d","BEAR","or45_d","BEAR","BEAR"),
    (4,"VIERNES","OR+PM BEAR→BEAR",     "or_d","BEAR","pm_d","BEAR","BEAR"),
    (0,"LUNES",  "OR BULL+PM BEAR→BULL","or_d","BULL","pm_d","BEAR","BULL"),
    (0,"LUNES",  "OR BEAR+Prev BEAR",   "or_d","BEAR","prev_d","BEAR","BEAR"),
    (2,"MIER",   "OR BEAR+Prev BULL",   "or_d","BEAR","prev_d","BULL","BEAR"),
    (2,"MIER",   "OR BULL+VXN baja",    "or_d","BULL","vxn_t","FALLING","BULL"),
    (3,"JUEVES", "OR BEAR+>100pts",     "or_d","BEAR","or_large",True,"BEAR"),
    (1,"MARTES", "OR45+OR BEAR",        "or45_d","BEAR","or_d","BEAR","BEAR"),
]

def stat_combo(rows, f1,v1,f2,v2,tgt):
    sub=[r for r in rows if r.get(f1)==v1 and r.get(f2)==v2]
    n=len(sub)
    if n<2: return None,n
    hits=sum(1 for r in sub if r["ny_d"]==tgt)
    return round(hits/n*100),n

print(f"\n  {'Día':<8}  {'Combo':<25}  {'2 AÑOS':>12}  {'AÑO 1':>12}  {'AÑO 2':>12}  {'6 MESES':>12}")
print("  "+"─"*80)

for wd,dname,label,f1,v1,f2,v2,tgt in COMBOS:
    rows_2Y=get_df(wd,"2Y"); rows_A1=get_df(wd,"A1")
    rows_A2=get_df(wd,"A2"); rows_6M=get_df(wd,"6M")
    n2Y=len(rows_2Y); nA1=len(rows_A1); nA2=len(rows_A2); n6M=len(rows_6M)

    p2Y,n_2Y=stat_combo(rows_2Y,f1,v1,f2,v2,tgt)
    pA1,n_A1=stat_combo(rows_A1,f1,v1,f2,v2,tgt)
    pA2,n_A2=stat_combo(rows_A2,f1,v1,f2,v2,tgt)
    p6M,n_6M=stat_combo(rows_6M,f1,v1,f2,v2,tgt)

    vals=[v for v in [p2Y,pA1,pA2,p6M] if v is not None]
    if not vals or max(vals)<60: continue

    c2Y=cell(p2Y,n_2Y,n2Y); cA1=cell(pA1,n_A1,nA1)
    cA2=cell(pA2,n_A2,nA2); c6M=cell(p6M,n_6M,n6M)
    print(f"  {dname:<8}  {label:<25}  {c2Y:>12}  {cA1:>12}  {cA2:>12}  {c6M:>12}")

# LEYENDA
print()
print("  LEYENDA:")
print("  🔥=90%+  ✅=75%+  ~=62%+  ✗=<62%")
print("  n=días que se activó la señal  |  d=días totales del periodo")
print("  Ejemplo: '78%✅ 9d' = señal se activó 9 días, acertó 78% de esas veces")
