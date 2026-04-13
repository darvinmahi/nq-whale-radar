"""
master_research.py — Análisis maestro en una sola pasada
═══════════════════════════════════════════════════════════════════
Precomputa TODOS los stats por día UNA SOLA VEZ y luego analiza:

 1. LUNES — estudio completo (nunca analizado antes)
 2. MARTES — diferentes ventanas de tiempo para encontrar edge
    (First 15min, 30min, 60min, 10:00-11:00, 11:00-12:00...)
 3. VIERNES — OR granular (tamaño del OR + VXN)
 4. TODOS los días — OR effectiveness by size
 5. TODOS los días — regime analysis (COVID crash, 2022 bear, 2023+)

Salida: hallazgos accionables por día
"""

import pandas as pd
import numpy as np
import pytz
import json
from datetime import datetime, date, timedelta

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

print("\n"+"█"*68)
print("  MASTER RESEARCH — Análisis final completo en una pasada")
print("  Lunes + Martes(ventanas) + OR granular + Regimes")
print("█"*68+"\n")

# ─── CARGA ────────────────────────────────────────────────────
print("  Cargando CSV...")
raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday() < 5})
print(f"  {len(raw)} barras | {len(all_dates)} días de trading")

print("  Indexando por día...")
# Agrupar barra por fecha una sola vez
raw["_date"] = raw.index.date
grouped = {d: grp for d, grp in raw.groupby("_date")}
print(f"  {len(grouped)} días indexados")

print("  Descargando ^VXN...")
vxn_day = {}
try:
    import yfinance as yf
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if isinstance(vdf.columns, pd.MultiIndex): vdf.columns = vdf.columns.get_level_values(0)
    for idx, row in vdf.iterrows():
        vxn_day[idx.date()] = round(float(row["Close"]), 2)
    print(f"  VXN: {len(vxn_day)} días")
except Exception as e:
    print(f"  VXN no disponible: {e}")

def bt(d, t0, t1):
    a = datetime.strptime(t0, "%H:%M").time()
    b = datetime.strptime(t1, "%H:%M").time()
    return d[(d.index.time >= a) & (d.index.time <= b)]

windows_to_measure = [
    ("w0930_0944", "09:30", "09:44"),
    ("w0930_0959", "09:30", "09:59"),
    ("w0930_1029", "09:30", "10:29"),
    ("w1000_1059", "10:00", "10:59"),
    ("w1100_1159", "11:00", "11:59"),
    ("w1200_1259", "12:00", "12:59"),
    ("w1300_1359", "13:00", "13:59"),
]

# ─── PRECOMPUTAR POR DÍA ──────────────────────────────────────
print("  Precalculando stats por día...")
day_st = {}

for day, d in grouped.items():
    if pd.Timestamp(day).weekday() >= 5: continue    # skip weekends
    try:
        pm   = bt(d, "07:00", "09:29")
        ny   = bt(d, "09:30", "16:00")
        asia = bt(d, "00:00", "06:59")
        spk  = bt(d, "08:30", "08:44")
        pre  = bt(d, "08:00", "08:29")

        st = {"day": day, "weekday": pd.Timestamp(day).weekday()}

        if len(pm) >= 2:
            pm_m = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"])
            pm_r = float(pm["High"].max()) - float(pm["Low"].min())
            st["pm_dir"]   = "BULL" if pm_m > 15 else ("BEAR" if pm_m < -15 else "FLAT")
            st["pm_range"] = round(pm_r)
            st["pm_size"]  = "SMALL" if pm_r < 80 else ("MED" if pm_r < 160 else "LARGE")
            st["pm_close"] = float(pm.iloc[-1]["Close"])

        if len(asia) >= 2:
            am = float(asia.iloc[-1]["Close"]) - float(asia.iloc[0]["Open"])
            st["asia_dir"]   = "BULL" if am > 20 else ("BEAR" if am < -20 else "FLAT")
            st["asia_range"] = round(float(asia["High"].max()) - float(asia["Low"].min()))

        if len(spk) >= 1 and len(pre) >= 1:
            sm = float(spk.iloc[-1]["Close"]) - float(pre.iloc[-1]["Close"])
            st["spike_dir"] = "UP" if sm > 25 else ("DOWN" if sm < -25 else "FLAT")
        else:
            st["spike_dir"] = "NONE"

        if len(ny) >= 4:
            ny_o = float(ny.iloc[0]["Open"]); ny_c = float(ny.iloc[-1]["Close"])
            ny_m = ny_c - ny_o; nyr = float(ny["High"].max()) - float(ny["Low"].min())
            idx_hi = ny["High"].idxmax(); idx_lo = ny["Low"].idxmin()
            st["ny_dir"]   = "BULL" if ny_m > 30 else ("BEAR" if ny_m < -30 else "FLAT")
            st["ny_move"]  = round(ny_m);  st["ny_range"] = round(nyr)
            st["ny_open"]  = round(ny_o);  st["ny_close"] = round(ny_c)
            st["ny_hi_h"]  = round(idx_hi.hour + idx_hi.minute / 60, 2)
            st["ny_lo_h"]  = round(idx_lo.hour + idx_lo.minute / 60, 2)
            st["hi_first"] = idx_hi < idx_lo

        for wname, t0w, t1w in windows_to_measure:
            win = bt(d, t0w, t1w)
            if len(win) >= 1:
                wm = float(win.iloc[-1]["Close"]) - float(win.iloc[0]["Open"])
                wr = float(win["High"].max())      - float(win["Low"].min())
                st[wname + "_dir"]   = "BULL" if wm > 10 else ("BEAR" if wm < -10 else "FLAT")
                st[wname + "_range"] = round(wr)
            else:
                st[wname + "_dir"] = "NONE"

        vxn = vxn_day.get(day)
        st["vxn"] = vxn
        if vxn:
            st["vxn_lvl"] = "LOW" if vxn < 20 else ("MID" if vxn < 25 else ("HIGH" if vxn < 30 else "PANIC"))

        if day < date(2020, 3, 1):    st["regime"] = "PRE_COVID"
        elif day < date(2021, 1, 1):  st["regime"] = "COVID_CRASH"
        elif day < date(2022, 1, 1):  st["regime"] = "BULL_2021"
        elif day < date(2023, 1, 1):  st["regime"] = "BEAR_2022"
        elif day < date(2024, 4, 1):  st["regime"] = "RECOVERY_2023"
        else:                          st["regime"] = "RECENT_2024"

        day_st[day] = st
    except Exception as e:
        pass  # skip bad days


print(f"  {len(day_st)} días precalculados")


# ─── FUNCIÓN BASE ─────────────────────────────────────────────
def get_sessions(weekday):
    days = [d for d in all_dates if pd.Timestamp(d).weekday() == weekday]
    rows = []
    for day in days:
        if day not in day_st or "ny_dir" not in day_st[day]: continue
        st = day_st[day]
        prev = None
        for td in reversed(all_dates):
            if td < day: prev = td; break
        ps = day_st.get(prev, {}) if prev else {}

        vxn_prev = vxn_day.get(prev) if prev else None
        vxn = st.get("vxn")
        vxn_trend = "NONE"
        if vxn and vxn_prev:
            delta = vxn - vxn_prev
            vxn_trend = "RISING" if delta > 0.5 else ("FALLING" if delta < -0.5 else "FLAT")

        ws = day - timedelta(days=day.weekday())
        wdays = [d for d in all_dates if ws <= d < day]
        wdir = "NONE"
        if wdays:
            opens  = [day_st[d].get("ny_open", 0) for d in wdays if "ny_open" in day_st.get(d, {})]
            closes = [day_st[d].get("ny_close", 0) for d in wdays if "ny_close" in day_st.get(d, {})]
            if opens and closes:
                wm = closes[-1] - opens[0]
                wdir = "BULL" if wm > 50 else ("BEAR" if wm < -50 else "FLAT")

        row = {
            "date": day, "ny_dir": st.get("ny_dir"), "ny_range": st.get("ny_range", 0),
            "ny_move": st.get("ny_move", 0), "ny_hi_h": st.get("ny_hi_h"),
            "ny_lo_h": st.get("ny_lo_h"), "hi_first": st.get("hi_first", False),
            "pm_dir": st.get("pm_dir","NONE"), "pm_size": st.get("pm_size","NONE"),
            "pm_range": st.get("pm_range",0), "pm_close": st.get("pm_close"),
            "asia_dir": st.get("asia_dir","NONE"), "asia_range": st.get("asia_range",0),
            "spike": st.get("spike_dir","NONE"),
            "prev_dir": ps.get("ny_dir","NONE"), "prev_range": ps.get("ny_range",0),
            "vxn": vxn, "vxn_lvl": st.get("vxn_lvl"), "vxn_trend": vxn_trend,
            "weekly": wdir, "regime": st.get("regime","UNK"),
            "recent": (day >= date(2024, 4, 10)),
        }
        for wname, _, _ in windows_to_measure:
            row[wname + "_dir"]   = st.get(wname + "_dir", "NONE")
            row[wname + "_range"] = st.get(wname + "_range", 0)
        rows.append(row)
    return pd.DataFrame(rows)

def pct(n, d): return round(n / d * 100, 1) if d > 0 else 0
def bar(v): return "█" * int(v / 5)
def sec(t): print(f"\n{'═'*68}\n  {t}\n{'═'*68}")
def flag(v): return " ✅" if v >= 65 else (" ⚠️" if v >= 57 else "")

# ══════════════════════════════════════════════════════════════
#  ANÁLISIS LUNES
# ══════════════════════════════════════════════════════════════
print("\n\n"+"█"*68)
print("  📅  LUNES — Primer análisis completo")
print("█"*68)

df_mon = get_sessions(0)
n = len(df_mon)
rec = df_mon[df_mon["recent"]]
print(f"  {n} sesiones | {len(rec)} recientes (2024+)")
bb=(df_mon["ny_dir"]=="BULL").sum(); be=(df_mon["ny_dir"]=="BEAR").sum()
print(f"  Base 9Y: BULL {bb}({pct(bb,n)}%) BEAR {be}({pct(be,n)}%) FLAT {n-bb-be}({pct(n-bb-be,n)}%)")
if len(rec)>=5:
    rb=(rec["ny_dir"]=="BULL").sum(); re=(rec["ny_dir"]=="BEAR").sum()
    print(f"  Base 2Y: BULL {rb}({pct(rb,len(rec))}%) BEAR {re}({pct(re,len(rec))}%)")

print(f"\n  Rango NY — Med:{df_mon['ny_range'].median():.0f}  Avg:{df_mon['ny_range'].mean():.0f}  P25:{df_mon['ny_range'].quantile(.25):.0f}  P75:{df_mon['ny_range'].quantile(.75):.0f}")

sec("PREDICTORES LUNES — todos los candidatos")
feats_to_test = [("pm_dir","PM direction"),("asia_dir","Asia direction"),
                 ("w0930_0959_dir","OR 9:30-10:00"),("w0930_1029_dir","First 60min"),
                 ("vxn_lvl","VXN nivel"),("vxn_trend","VXN trend"),
                 ("spike","Spike 8:30"),("prev_dir","Día anterior (viernes)"),("weekly","Semana pasada")]
print(f"\n  {'Predictor':<30} {'Signal':<12} → {'Dir':<5} {'Acc':>6}  N")
print("  " + "─" * 60)
best_rules = []
for feat, label in feats_to_test:
    if feat not in df_mon.columns: continue
    for v in df_mon[feat].dropna().unique():
        if v in ("NONE","FLAT",None,False): continue
        sub = df_mon[df_mon[feat]==v]
        if len(sub) < 6: continue
        for d in ["BULL","BEAR"]:
            nc = (sub["ny_dir"]==d).sum(); p = pct(nc, len(sub))
            if p >= 55:
                fl = flag(p)
                print(f"  {label:<30} [{v:<10}] → {d:<5} {p:>5.1f}%{fl}  n={len(sub)}  {bar(p)}")
                if p >= 60: best_rules.append({"feat":feat,"val":v,"dir":d,"pct":p,"n":len(sub),"nc":nc})

if not best_rules: print("  (ningún predictor ≥60%)")

# OR Size for Monday
sec("OR SIZE LUNES — ¿el tamaño del OR importa?")
hv_mon = df_mon[df_mon["w0930_0959_range"]>0]
bins_or = [(0,30,"Tiny <30"),(30,60,"Small 30-60"),(60,100,"Med 60-100"),(100,200,">100")]
print(f"\n  {'OR Size':<15} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  Rng_med")
print("  "+"─"*40)
for lo,hi,lbl in bins_or:
    sub = hv_mon[(hv_mon["w0930_0959_range"]>=lo)&(hv_mon["w0930_0959_range"]<hi)]
    if len(sub)<4: continue
    bl=(sub["ny_dir"]=="BULL").sum(); be=(sub["ny_dir"]=="BEAR").sum()
    mr=sub["ny_range"].median()
    print(f"  {lbl:<15}{len(sub):>3}  {pct(bl,len(sub)):>5.0f}%  {pct(be,len(sub)):>5.0f}%  {mr:>7.0f}")

# Timing Lunes
sec("TIMING LUNES — ¿A qué hora se forma el HIGH/LOW?")
for direction, col in [("BULL","ny_hi_h"),("BEAR","ny_lo_h")]:
    sub = df_mon[(df_mon["ny_dir"]==direction)&df_mon[col].notna()]; hours=sub[col]
    if len(sub)<5: continue
    lbl="HIGH" if direction=="BULL" else "LOW"
    print(f"\n  {direction} ({len(sub)} sess) — {lbl} hora:")
    print(f"    Med:{hours.median():.1f}h  Avg:{hours.mean():.1f}h  P25-P75:{hours.quantile(.25):.1f}-{hours.quantile(.75):.1f}h")
    for lo,hi,lh in [(9.5,10.5,"9:30-10:30"),(10.5,11.5,"10:30-11:30"),
                     (11.5,12.5,"11:30-12:30"),(12.5,14,"12:30-14:00"),(14,16.5,"14:00-16:00")]:
        cnt=(hours>=lo)&(hours<hi); nk=cnt.sum()
        print(f"      {lh}: {nk:>3} ({pct(nk,len(sub)):.0f}%)  {bar(pct(nk,len(sub)))}")

# ══════════════════════════════════════════════════════════════
#  MARTES — VENTANAS DE TIEMPO
# ══════════════════════════════════════════════════════════════
print("\n\n"+"█"*68)
print("  📅  MARTES — Búsqueda exhaustiva de ventana predictora")
print("█"*68)

df_tue = get_sessions(1)
n_tue = len(df_tue)
print(f"  {n_tue} sesiones")

sec("TODAS LAS VENTANAS DE TIEMPO → PREDICCIÓN NY")
print(f"\n  {'Ventana':<26} {'DIR=BULL→NY BULL':>16}  {'DIR=BEAR→NY BEAR':>16}  {'n_bull':>6}  {'n_bear':>6}")
print("  " + "─" * 72)
for wname, _, _ in windows_to_measure:
    feat = wname + "_dir"
    if feat not in df_tue.columns: continue
    bull_sub = df_tue[df_tue[feat]=="BULL"]; bear_sub = df_tue[df_tue[feat]=="BEAR"]
    if len(bull_sub)<4 and len(bear_sub)<4: continue
    bb_p = pct((bull_sub["ny_dir"]=="BULL").sum(), len(bull_sub)) if len(bull_sub)>0 else 0
    be_p = pct((bear_sub["ny_dir"]=="BEAR").sum(), len(bear_sub)) if len(bear_sub)>0 else 0
    label = wname.replace("w","").replace("_dir","").replace("_"," ")
    bfl = flag(bb_p); befl = flag(be_p)
    print(f"  {label:<26} {bb_p:>14.1f}%{bfl}  {be_p:>14.1f}%{befl}  {len(bull_sub):>6}  {len(bear_sub):>6}")

# Martes: ventana óptima granular
sec("MARTES — OR 9:30-10:00 por size (¿OR grande es más predictivo?)")
hv_tue = df_tue[df_tue["w0930_0959_range"]>0]
print(f"\n  {'OR Size':<15} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  Sigue_dir")
print("  "+"─"*42)
for lo,hi,lbl in [(0,30,"<30"),(30,60,"30-60"),(60,100,"60-100"),(100,200,"100-200"),(200,999,">200")]:
    sub = hv_tue[(hv_tue["w0930_0959_range"]>=lo)&(hv_tue["w0930_0959_range"]<hi)]
    if len(sub)<4: continue
    bull_or=sub[sub["w0930_0959_dir"]=="BULL"]; bear_or=sub[sub["w0930_0959_dir"]=="BEAR"]
    b_pct=pct((bull_or["ny_dir"]=="BULL").sum(),len(bull_or)) if len(bull_or)>0 else 0
    e_pct=pct((bear_or["ny_dir"]=="BEAR").sum(),len(bear_or)) if len(bear_or)>0 else 0
    print(f"  {lbl:<15}{len(sub):>3}  {b_pct:>5.0f}%  {e_pct:>5.0f}%  max={max(b_pct,e_pct):.0f}%{flag(max(b_pct,e_pct))}")

# Martes: ¿Lunes UP predice Martes UP?
sec("MARTES — contexto día anterior LUNES")
for prev_val in ["BULL","BEAR","FLAT"]:
    sub = df_tue[df_tue["prev_dir"]==prev_val]
    if len(sub)<5: continue
    bl=(sub["ny_dir"]=="BULL").sum(); be=(sub["ny_dir"]=="BEAR").sum()
    print(f"  Lunes {prev_val} ({len(sub)} sess) → Martes: BULL {bl}({pct(bl,len(sub)):.0f}%)  BEAR {be}({pct(be,len(sub)):.0f}%){flag(max(pct(bl,len(sub)),pct(be,len(sub))))}")

# ══════════════════════════════════════════════════════════════
#  OR GRANULAR — TODOS LOS DÍAS
# ══════════════════════════════════════════════════════════════
print("\n\n"+"█"*68)
print("  📊  OR GRANULAR — Tamaño del Opening Range × Efectividad")
print("      ¿Un OR grande es más predictivo que uno pequeño?")
print("█"*68)

DIAS_WD = [(0,"LUNES"),(1,"MARTES"),(2,"MIÉRCOLES"),(3,"JUEVES"),(4,"VIERNES")]
all_dfs  = {wd: get_sessions(wd) for wd,_ in DIAS_WD}

print(f"\n  OR BEAR → NY BEAR por tamaño de OR:")
print(f"\n  {'Día':<12} {'<30':>6}  {'30-60':>6}  {'60-100':>6}  {'>100':>6}  {'total':>6}")
print("  " + "─" * 50)
for wd, dname in DIAS_WD:
    df = all_dfs[wd]
    row = f"  {dname:<12}"
    for lo, hi in [(0,30),(30,60),(60,100),(100,999)]:
        sub = df[(df["w0930_0959_range"]>=lo)&(df["w0930_0959_range"]<hi)&(df["w0930_0959_dir"]=="BEAR")]
        if len(sub)<3: row += f"  {'  —':>6}"; continue
        p = pct((sub["ny_dir"]=="BEAR").sum(), len(sub))
        row += f" {p:>5.0f}%{' ✅' if p>=65 else '  '}"
    total = df[df["w0930_0959_dir"]=="BEAR"]
    if len(total)>0:
        tp=pct((total["ny_dir"]=="BEAR").sum(),len(total))
        row += f" {tp:>5.0f}%"
    print(row)

print(f"\n  OR BULL → NY BULL por tamaño de OR:")
print(f"\n  {'Día':<12} {'<30':>6}  {'30-60':>6}  {'60-100':>6}  {'>100':>6}  {'total':>6}")
print("  " + "─" * 50)
for wd, dname in DIAS_WD:
    df = all_dfs[wd]
    row = f"  {dname:<12}"
    for lo, hi in [(0,30),(30,60),(60,100),(100,999)]:
        sub = df[(df["w0930_0959_range"]>=lo)&(df["w0930_0959_range"]<hi)&(df["w0930_0959_dir"]=="BULL")]
        if len(sub)<3: row += f"  {'  —':>6}"; continue
        p = pct((sub["ny_dir"]=="BULL").sum(), len(sub))
        row += f" {p:>5.0f}%{' ✅' if p>=65 else '  '}"
    total = df[df["w0930_0959_dir"]=="BULL"]
    if len(total)>0:
        tp=pct((total["ny_dir"]=="BULL").sum(),len(total))
        row += f" {tp:>5.0f}%"
    print(row)

# VXN + OR combo todos los días
sec("VXN + OR COMBINACIÓN — efectividad por día")
print(f"\n  OR BEAR + VXN HIGH(>25) → NY BEAR:")
print(f"  {'Día':<12} {'n':>4}  {'BEAR%':>7}  {'All VXN BEAR%':>14}")
print("  " + "─" * 42)
for wd, dname in DIAS_WD:
    df = all_dfs[wd]
    hv = df[(df["vxn"].notna())&(df["vxn"]>=25)]
    or_bear_vxn = hv[hv["w0930_0959_dir"]=="BEAR"]
    or_bear_all = df[df["w0930_0959_dir"]=="BEAR"]
    vxn_high_all = hv
    if len(or_bear_vxn)>=3:
        p1 = pct((or_bear_vxn["ny_dir"]=="BEAR").sum(), len(or_bear_vxn))
    else: p1=0
    p2 = pct((or_bear_all["ny_dir"]=="BEAR").sum(),len(or_bear_all)) if len(or_bear_all)>0 else 0
    fl=flag(p1)
    print(f"  {dname:<12}{len(or_bear_vxn):>4}  {p1:>6.0f}%{fl}  {p2:>13.0f}%")

# ══════════════════════════════════════════════════════════════
#  REGIME ANALYSIS
# ══════════════════════════════════════════════════════════════
sec("ANÁLISIS DE REGIMENES — ¿Cambiaron las reglas según el mercado?")
print(f"\n  OR BEAR → NY BEAR por régimen (viernes, la señal más fuerte):")
regimes = ["PRE_COVID","COVID_CRASH_REC","BULL_2021","BEAR_2022","RECOVERY_2023","RECENT_2024"]
df_fri = all_dfs[4]
print(f"\n  {'Régimen':<18} {'N OR_BEAR':>10}  {'BEAR%':>7}")
print("  "+"─"*38)
for reg in regimes:
    sub = df_fri[(df_fri["regime"]==reg)&(df_fri["w0930_0959_dir"]=="BEAR")]
    if len(sub)<3: continue
    p=pct((sub["ny_dir"]=="BEAR").sum(), len(sub))
    print(f"  {reg:<18}{len(sub):>10}  {p:>6.0f}%{flag(p)}")

# ══════════════════════════════════════════════════════════════
#  RESUMEN EJECUTIVO FINAL
# ══════════════════════════════════════════════════════════════
print("\n\n"+"═"*68)
print("  📋  RULEBOOK MAESTRO — Todas las reglas validadas ≥60%")
print("═"*68+"\n")

RULEBOOK = {}
for wd, dname in DIAS_WD:
    df = all_dfs[wd]
    rules = []
    # Test all windows and features
    all_feats = [(f+"_dir", f) for f,_,_ in windows_to_measure] + \
                [("pm_dir","pm"),("asia_dir","asia"),("vxn_lvl","vxn"),
                 ("spike","spike"),("prev_dir","prev"),("vxn_trend","vxn_trend")]
    for feat, label in all_feats:
        if feat not in df.columns: continue
        for v in df[feat].dropna().unique():
            if v in ("NONE","FLAT",None,False): continue
            sub = df[df[feat]==v]
            if len(sub)<6: continue
            for d in ["BULL","BEAR"]:
                nc=(sub["ny_dir"]==d).sum(); p=pct(nc,len(sub))
                if p>=60:
                    rules.append(f"{feat}={v} → {d}: {p:.0f}% (n={len(sub)})")
    RULEBOOK[dname] = rules
    print(f"  {dname}:")
    if rules:
        for r in sorted(rules, key=lambda x:-float(x.split(": ")[1].split("%")[0]))[:5]:
            print(f"    ✅ {r}")
    else:
        print(f"    ⚠️  Sin reglas ≥60%")
    print()

# Save
with open("data/master_rulebook.json","w",encoding="utf-8") as f:
    json.dump({"timestamp":str(datetime.now()),"rulebook":RULEBOOK}, f, indent=2, ensure_ascii=False, default=str)
print(f"  💾 Guardado: data/master_rulebook.json")
print("█"*68+"\n")
