"""
deep_study_mar_vie.py
══════════════════════════════════════════════════════════════════
ESTUDIO PROFUNDO — MARTES y VIERNES

Para cada día expande el análisis hacia:
  ✦ ¿A QUÉ HORA ocurre el high/low en NY?
  ✦ Filtros adicionales (VXN + PM combo, Thursday→Friday, etc.)
  ✦ Granularidad — ¿qué nivel de VXN mejora las odds?
  ✦ Drawdown máximo / expectancy del setup
  ✦ Casos especiales: conflicto de señales, PM extremo, etc.
  ✦ Estructura típica del día: ¿dónde entra la reversión?

Uso:
    python deep_study_mar_vie.py           → ambos días
    python deep_study_mar_vie.py tuesday   → solo martes
    python deep_study_mar_vie.py friday    → solo viernes
"""

import sys, json
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, date, timedelta

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

print("\n" + "█"*68)
print("  ESTUDIO PROFUNDO — MARTES & VIERNES | NQ Futures")
print("  " + "─"*64)
print("  Análisis expandido: timing, filtros, expectancy, estructura")
print("█"*68)

# ─── CARGA ────────────────────────────────────────────────────
print("\n  Cargando CSV...")
raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
print(f"  {len(raw)} barras | {raw.index.min().date()} → {raw.index.max().date()}")

print("  Descargando ^VXN...")
vxn_day = {}
try:
    import yfinance as yf
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if isinstance(vdf.columns, pd.MultiIndex):
        vdf.columns = vdf.columns.get_level_values(0)
    for idx, row in vdf.iterrows():
        vxn_day[idx.date()] = round(float(row["Close"]),2)
    print(f"  VXN: {len(vxn_day)} días")
except Exception as e:
    print(f"  VXN no disponible ({e})")

def bt(d, t0, t1):
    a = datetime.strptime(t0,"%H:%M").time()
    b = datetime.strptime(t1,"%H:%M").time()
    return d[(d.index.time >= a) & (d.index.time <= b)]

all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday()<5})

# ─── PRECOMPUTAR STATS DIARIAS ────────────────────────────────
print("  Precalculando stats diarias...")
day_stats = {}
for day in all_dates:
    s0 = ET.localize(datetime(day.year,day.month,day.day,0,0))
    s1 = ET.localize(datetime(day.year,day.month,day.day,16,30))
    d  = raw[(raw.index>=s0)&(raw.index<=s1)].copy()
    if d.empty: continue

    pm  = bt(d,"07:00","09:29")
    ny  = bt(d,"09:30","16:00")
    spk = bt(d,"08:30","08:44")
    pre = bt(d,"08:00","08:29")

    st = {"day": day}

    if len(pm) >= 2:
        pm_m = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"])
        pm_r = float(pm["High"].max()) - float(pm["Low"].min())
        st["pm_move"]  = round(pm_m)
        st["pm_range"] = round(pm_r)
        st["pm_dir"]   = "BULL" if pm_m>15 else ("BEAR" if pm_m<-15 else "FLAT")
        st["pm_size"]  = "SMALL" if pm_r<80 else ("MED" if pm_r<160 else "LARGE")
        st["pm_close"] = float(pm.iloc[-1]["Close"])

    if len(ny) >= 4:
        ny_o = float(ny.iloc[0]["Open"])
        ny_c = float(ny.iloc[-1]["Close"])
        ny_m = ny_c - ny_o
        ny_h = float(ny["High"].max())
        ny_l = float(ny["Low"].min())
        ny_r = ny_h - ny_l
        st["ny_open"]  = round(ny_o)
        st["ny_close"] = round(ny_c)
        st["ny_move"]  = round(ny_m)
        st["ny_range"] = round(ny_r)
        st["ny_hi"]    = round(ny_h)
        st["ny_lo"]    = round(ny_l)
        st["ny_dir"]   = "BULL" if ny_m>30 else ("BEAR" if ny_m<-30 else "FLAT")

        # Hora del HIGH y LOW en NY
        idx_hi = ny["High"].idxmax()
        idx_lo = ny["Low"].idxmin()
        st["ny_hi_hour"]  = round(idx_hi.hour + idx_hi.minute/60, 2)  # hora decimal
        st["ny_lo_hour"]  = round(idx_lo.hour + idx_lo.minute/60, 2)
        st["hi_first"]    = idx_hi < idx_lo

        # Máx drawdown contra la dirección
        if ny_m > 0:  # día bull → cuánto bajó antes de subir
            st["max_dd"] = round(float(ny["Low"].min()) - ny_o)   # negativo = cuánto cedió
        else:
            st["max_dd"] = round(float(ny["High"].max()) - ny_o)  # positivo = cuánto subió antes de bajar

    if len(spk)>=1 and len(pre)>=1:
        sm = float(spk.iloc[-1]["Close"]) - float(pre.iloc[-1]["Close"])
        st["spike_move"] = round(sm)
        st["spike_dir"]  = "UP" if sm>25 else ("DOWN" if sm<-25 else "FLAT")
    else:
        st["spike_dir"] = "NONE"

    day_stats[day] = st
print(f"  {len(day_stats)} días OK")


# ══════════════════════════════════════════════════════════════════
#  FUNCIÓN: ANÁLISIS PROFUNDO POR DÍA
# ══════════════════════════════════════════════════════════════════
def deep_analysis(weekday, day_name):
    days = [d for d in all_dates if pd.Timestamp(d).weekday()==weekday]
    sessions = []
    for day in days:
        if day not in day_stats: continue
        st = day_stats[day]
        if "ny_dir" not in st or st["ny_dir"] == "NONE": continue

        # Día anterior
        prev = None
        for td in reversed(all_dates):
            if td < day: prev = td; break
        prev_st = day_stats.get(prev, {}) if prev else {}

        # Tendencia semanal
        ws = day - timedelta(days=day.weekday())
        wdays = [d for d in all_dates if ws<=d<day]
        wdir = "NONE"
        if wdays and "ny_close" in day_stats.get(wdays[-1],{}):
            wm = day_stats[wdays[-1]]["ny_close"] - day_stats[wdays[0]].get("ny_open",
                 day_stats[wdays[-1]]["ny_close"])
            wdir = "BULL" if wm>50 else ("BEAR" if wm<-50 else "FLAT")

        vxn = vxn_day.get(day)
        vxn_lvl = None
        if vxn: vxn_lvl = "LOW" if vxn<20 else ("MID" if vxn<25 else "HIGH" if vxn<30 else "PANIC")

        rec = {
            "date":       day,
            "ny_dir":     st.get("ny_dir","NONE"),
            "ny_move":    st.get("ny_move",0),
            "ny_range":   st.get("ny_range",0),
            "ny_hi_hour": st.get("ny_hi_hour"),
            "ny_lo_hour": st.get("ny_lo_hour"),
            "hi_first":   st.get("hi_first",False),
            "max_dd":     st.get("max_dd",0),
            "pm_dir":     st.get("pm_dir","NONE"),
            "pm_move":    st.get("pm_move",0),
            "pm_range":   st.get("pm_range",0),
            "pm_size":    st.get("pm_size","NONE"),
            "spike_dir":  st.get("spike_dir","NONE"),
            "spike_move": st.get("spike_move",0),
            "prev_dir":   prev_st.get("ny_dir","NONE"),
            "weekly":     wdir,
            "vxn":        vxn,
            "vxn_lvl":    vxn_lvl,
        }
        sessions.append(rec)

    df = pd.DataFrame(sessions)
    n  = len(df)
    if n < 10: return

    print(f"\n\n{'█'*68}")
    print(f"  📅  {day_name.upper()}  —  {n} sesiones  |  {df['date'].min()} → {df['date'].max()}")
    print(f"{'█'*68}")

    bull_df = df[df["ny_dir"]=="BULL"]
    bear_df = df[df["ny_dir"]=="BEAR"]
    flat_df = df[df["ny_dir"]=="FLAT"]

    def hr(c="═"): print(c*68)
    def sec(t): print(f"\n  {t}"); print("  "+"─"*60)

    # ── 1. SESGO BASE
    hr("═"); print(f"  1️⃣   SESGO BASE  ({n} sesiones)"); hr("═")
    print(f"\n  BULL: {len(bull_df):>3}/{n} = {len(bull_df)/n*100:.0f}%")
    print(f"  BEAR: {len(bear_df):>3}/{n} = {len(bear_df)/n*100:.0f}%")
    print(f"  FLAT: {len(flat_df):>3}/{n} = {len(flat_df)/n*100:.0f}%")
    print(f"\n  Rango NY — P25: {df['ny_range'].quantile(.25):.0f}  Med: {df['ny_range'].median():.0f}  Avg: {df['ny_range'].mean():.0f}  P75: {df['ny_range'].quantile(.75):.0f}  Max: {df['ny_range'].max():.0f} pts")

    # ── 2. PM → NY (base + por tamaño)
    hr("═"); print(f"  2️⃣   PM DIRECTION → NY  (predictor principal)"); hr("═")
    for pm_dir in ["BULL","BEAR","FLAT"]:
        sub = df[df["pm_dir"]==pm_dir]
        if sub.empty: continue
        ns=len(sub); bull=(sub["ny_dir"]=="BULL").sum(); bear=(sub["ny_dir"]=="BEAR").sum()
        same = bull if pm_dir=="BULL" else (bear if pm_dir=="BEAR" else (ns-bull-bear))
        pct  = same/ns*100
        arrow = "▲" if pm_dir=="BULL" else("▼" if pm_dir=="BEAR" else "▬")
        bar   = "█"*int(pct/5)
        print(f"\n  PM {pm_dir} {arrow}  →  {ns} sess")
        print(f"    BULL {bull}({bull/ns*100:.0f}%) / BEAR {bear}({bear/ns*100:.0f}%) / FLAT {ns-bull-bear}({(ns-bull-bear)/ns*100:.0f}%)")
        if pm_dir in ("BULL","BEAR"):
            print(f"    CORRELACIÓN: {same}/{ns} = {pct:.1f}%  {bar}")

        # Por PM size
        if pm_dir in ("BULL","BEAR"):
            print(f"    Breakdown por tamaño PM:")
            for sz in ["SMALL","MED","LARGE"]:
                s2 = sub[sub["pm_size"]==sz]
                if len(s2)<3: continue
                nc = (s2["ny_dir"]==pm_dir).sum()
                print(f"      PM {sz}: {nc}/{len(s2)} = {nc/len(s2)*100:.0f}%")

    # ── 3. VXN GRANULAR → DIRECCIÓN Y RANGO
    has_vxn = df[df["vxn"].notna()]
    if len(has_vxn) >= 5:
        hr("═"); print(f"  3️⃣   VXN GRANULAR → DIRECCIÓN + RANGO  ({len(has_vxn)} sess)"); hr("═")
        corr = has_vxn["vxn"].corr(has_vxn["ny_range"])
        print(f"\n  VXN → NY Range: r = {corr:.3f}")
        print(f"\n  {'VXN Nivel':<18} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'Med Rango':>10}  {'Avg Rango':>10}")
        print("  "+"─"*60)
        for lo,hi,label in [(0,18,"<18 Muy bajo"),(18,20,"18-20"),(20,22,"20-22"),(22,25,"22-25"),(25,28,"25-28"),(28,32,"28-32"),(32,99,">32 Pánico")]:
            sub = has_vxn[(has_vxn["vxn"]>=lo)&(has_vxn["vxn"]<hi)]
            if len(sub)<3: continue
            bull=(sub["ny_dir"]=="BULL").sum(); bear=(sub["ny_dir"]=="BEAR").sum()
            med=sub["ny_range"].median(); avg=sub["ny_range"].mean()
            flag = " ✅" if bear/len(sub)>=0.60 else (" 🟢" if bull/len(sub)>=0.60 else "")
            print(f"  {label:<18} {len(sub):>3}  {bull/len(sub)*100:>5.0f}%  {bear/len(sub)*100:>5.0f}%  {med:>10.0f}  {avg:>10.0f}{flag}")

    # ── 4. COMBOS DE 2 PREDICTORES
    hr("═"); print(f"  4️⃣   MEJORES COMBINACIONES DE 2 PREDICTORES"); hr("═")
    combos = []
    feat_pairs = [
        ("pm_dir","vxn_lvl"),("pm_dir","spike_dir"),("pm_dir","prev_dir"),
        ("pm_dir","weekly"),("vxn_lvl","spike_dir"),("vxn_lvl","prev_dir"),
        ("pm_size","pm_dir"),("pm_size","vxn_lvl"),("prev_dir","weekly"),
    ]
    for f1,f2 in feat_pairs:
        for v1 in df[f1].dropna().unique():
            for v2 in df[f2].dropna().unique():
                if v1 in ("NONE","FLAT") or v2 in ("NONE","FLAT"): continue
                sub = df[(df[f1]==v1)&(df[f2]==v2)]
                if len(sub)<6: continue
                for direction in ["BULL","BEAR"]:
                    nc=(sub["ny_dir"]==direction).sum(); pct=nc/len(sub)*100
                    if pct>=65:
                        combos.append({"f1":f1,"v1":v1,"f2":f2,"v2":v2,
                                       "dir":direction,"pct":pct,"n":len(sub),"nc":nc})

    combos.sort(key=lambda x: (x["pct"],-x["n"]), reverse=True)
    seen = set()
    shown=0
    print()
    for c in combos:
        key = (c["f1"],c["v1"],c["f2"],c["v2"],c["dir"])
        if key in seen: continue
        seen.add(key)
        bar = "█"*int(c["pct"]/5)
        medal = "🥇" if shown==0 else ("🥈" if shown==1 else ("🥉" if shown==2 else "  "))
        print(f"  {medal} {c['f1']}={c['v1']} + {c['f2']}={c['v2']}")
        print(f"     → NY {c['dir']}: {c['nc']}/{c['n']} = {c['pct']:.1f}%  {bar}")
        shown+=1
        if shown>=8: break
    if shown==0: print("  (ninguna combo ≥65%)")

    # ── 5. TIMING: ¿A QUÉ HORA SE FORMA EL HIGH/LOW?
    hr("═"); print(f"  5️⃣   TIMING — ¿A QUÉ HORA SE FORMA EL HIGH/LOW EN NY?"); hr("═")

    for direction, label, hour_col in [("BULL","Días BULL", "ny_hi_hour"),("BEAR","Días BEAR","ny_lo_hour")]:
        sub = df[(df["ny_dir"]==direction) & df[hour_col].notna()]
        if len(sub)<5: continue
        hours = sub[hour_col]
        print(f"\n  {label} ({len(sub)} sess) — hora del {'HIGH' if direction=='BULL' else 'LOW'} extremo NY:")
        print(f"    Mediana: {hours.median():.2f}h  |  Avg: {hours.mean():.2f}h  |  P25-P75: {hours.quantile(.25):.2f}-{hours.quantile(.75):.2f}h")

        # Distribución por horas
        bins = [(9.5,10.5,"9:30-10:30"),(10.5,11.5,"10:30-11:30"),
                (11.5,12.5,"11:30-12:30"),(12.5,14.0,"12:30-14:00"),(14.0,16.5,"14:00-16:00")]
        print(f"    Distribución:")
        for lo,hi,label_h in bins:
            cnt=(hours>=lo)&(hours<hi); n_=cnt.sum()
            bar = "█"*n_
            print(f"      {label_h}: {n_:>3} ({n_/len(sub)*100:.0f}%)  {bar}")

    # ── 6. DRAWDOWN / EXPECTANCY
    hr("═"); print(f"  6️⃣   DRAWDOWN MÁXIMO & EXPECTANCY"); hr("═")

    for direction, label in [("BULL","BULL"), ("BEAR","BEAR")]:
        sub = df[(df["ny_dir"]==direction) & df["max_dd"].notna()]
        if len(sub)<5: continue
        moves  = sub["ny_move"].abs()
        dds    = sub["max_dd"].abs()
        print(f"\n  Días {label}  ({len(sub)} sess):")
        print(f"    Movimiento NY  — Med: {moves.median():.0f}  Avg: {moves.mean():.0f}  P75: {moves.quantile(.75):.0f} pts")
        print(f"    Drawdown antes — Med: {dds.median():.0f}  Avg: {dds.mean():.0f}  P75: {dds.quantile(.75):.0f} pts")
        ratio = moves.mean() / max(dds.mean(),1)
        print(f"    Ratio Move/DD:  {ratio:.1f}x  → R:R del setup sin SL activo")

    # ── 7. CASOS ESPECIALES / CONFLICTO DE SEÑALES
    hr("═"); print(f"  7️⃣   CASOS ESPECIALES — conflicto de señales & filtros de riesgo"); hr("═")

    # PM muy grande (>200pts) — ¿agota el move?
    big_pm = df[df["pm_range"]>=200]
    if len(big_pm)>=4:
        bull_b=(big_pm["ny_dir"]=="BULL").sum(); bear_b=(big_pm["ny_dir"]=="BEAR").sum()
        print(f"\n  PM RANGE >200pts  ({len(big_pm)} sess): BULL {bull_b}({bull_b/len(big_pm)*100:.0f}%) / BEAR {bear_b}({bear_b/len(big_pm)*100:.0f}%)")
        print(f"    ⚠️  PM muy activo puede AGOTAR el movimiento antes de NY")

    # PM alcista + spike bajista (conflicto)
    conflict_bull = df[(df["pm_dir"]=="BULL")&(df["spike_dir"]=="DOWN")]
    if len(conflict_bull)>=4:
        nc=(conflict_bull["ny_dir"]=="BULL").sum()
        print(f"\n  PM BULL + SPIKE DOWN  ({len(conflict_bull)} sess): NY BULL {nc}/{len(conflict_bull)} = {nc/len(conflict_bull)*100:.0f}%")

    # PM bajista + spike alcista (trampa clásica)
    conflict_bear = df[(df["pm_dir"]=="BEAR")&(df["spike_dir"]=="UP")]
    if len(conflict_bear)>=4:
        nc=(conflict_bear["ny_dir"]=="BEAR").sum()
        print(f"\n  PM BEAR + SPIKE UP  ({len(conflict_bear)} sess — trampa clásica): NY BEAR {nc}/{len(conflict_bear)} = {nc/len(conflict_bear)*100:.0f}%")

    # Dos semanas seguidas en la misma dirección
    pm_dir_col = df.set_index("date")["pm_dir"]
    consec = 0
    for i in range(1,len(df)):
        curr = df.iloc[i]; prev_r = df.iloc[i-1]
        if prev_r["ny_dir"]==curr["pm_dir"] and curr["pm_dir"] in ("BULL","BEAR"):
            consec+=1
    print(f"\n  Semanas donde NY anterior = PM actual (momentum): {consec} de {len(df)-1} ({consec/(len(df)-1)*100:.0f}%)")

    # ── 8. TABLA DETALLE ÚLTIMAS 25 SESIONES
    hr("═"); print(f"  8️⃣   ÚLTIMAS 25 SESIONES (detail)"); hr("═")
    print(f"\n  {'Fecha':<12} {'PM':>5} {'PMd':<5} {'PMsz':<6} {'NYmov':>7} {'NYrng':>6} {'NYd':<5} {'VXN':>5} {'Spk':>6} {'Prev':<5} Hi1st  Timing")
    print("  "+"─"*78)
    for _,r in df.sort_values("date",ascending=False).head(25).iterrows():
        pms="▲" if r["pm_dir"]=="BULL" else("▼" if r["pm_dir"]=="BEAR" else"▬")
        nys="▲" if r["ny_dir"]=="BULL" else("▼" if r["ny_dir"]=="BEAR" else"▬")
        hi ="↑HI" if r["hi_first"] else "↓LO"
        ok ="✅" if r["pm_dir"]==r["ny_dir"] else("❌" if r["pm_dir"] in("BULL","BEAR") and r["ny_dir"] in("BULL","BEAR") else"  ")
        vx =f"{r['vxn']:.1f}" if r["vxn"] else "  —"
        prev_s=r["prev_dir"][0] if r["prev_dir"] not in("NONE",None) else "?"
        hi_h  = f"{r['ny_hi_hour']:.1f}h" if r["ny_hi_hour"] else "  —"
        lo_h  = f"{r['ny_lo_hour']:.1f}h" if r["ny_lo_hour"] else "  —"
        timing= f"H{hi_h}/L{lo_h}"
        print(f"  {str(r['date']):<12} {r['pm_move']:>+5} {pms:<5} {r['pm_size']:<6} {r['ny_move']:>+7} {r['ny_range']:>6} {nys:<5} {vx:>5} {r['spike_move']:>+6} {prev_s:<5} {hi:<5} {ok}  {timing}")

    print()


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
arg = sys.argv[1].lower() if len(sys.argv)>1 else "all"

if arg in ("tuesday","martes","tue"):
    deep_analysis(1, "MARTES")
elif arg in ("friday","viernes","fri"):
    deep_analysis(4, "VIERNES")
else:
    deep_analysis(1, "MARTES")
    deep_analysis(4, "VIERNES")

print("█"*68)
print("  ESTUDIO PROFUNDO COMPLETADO")
print("█"*68 + "\n")
