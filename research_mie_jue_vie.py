"""
research_mie_jue_vie.py  ─  ESTUDIO COMPLETO Wed/Thu/Fri
══════════════════════════════════════════════════════════
Misma metodología que MARTES (validada):
  • PM Direction → NY Direction (predictor #1)
  • Volume Profile Asia→9:40 (VAH/VAL/POC) vs NY open
  • VXN → Rango NY
  • Spike 8:30 → ¿trampa o confirmación?
  • High/Low: ¿qué llega primero?
  • Correlaciones y reglas accionables

CSV: data/research/nq_15m_intraday.csv (columnas: Datetime,Close,High,Low,Open)
VXN: Yahoo Finance ^VXN (daily)

Uso:
    python research_mie_jue_vie.py            → todos (Mie/Jue/Vie)
    python research_mie_jue_vie.py friday     → solo viernes
    python research_mie_jue_vie.py thursday   → solo jueves
    python research_mie_jue_vie.py wednesday  → solo miercoles
"""

import sys, json, os
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, date, timedelta

ET      = pytz.timezone("America/New_York")
CSV     = "data/research/nq_15m_intraday.csv"
VP_BINS = 50
W = 65

# ─── Día a analizar ──────────────────────────────────────────
DAYS_MAP = {
    "wednesday":2,"miercoles":2,"mie":2,
    "thursday":3,"jueves":3,"jue":3,
    "friday":4,"viernes":4,"vie":4,
}
arg = sys.argv[1].lower().replace("é","e") if len(sys.argv) > 1 else "all"
FILTER_WD = DAYS_MAP.get(arg) if arg != "all" else None

DIAS_ES  = {2:"MIÉRCOLES", 3:"JUEVES", 4:"VIERNES"}
DIAS_EN  = {2:"Wednesday", 3:"Thursday", 4:"Friday"}

def hr(c="═"): print(c*W)
def sec(t):    print(f"\n  {t}"); print("  "+"─"*55)

# ════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ════════════════════════════════════════════════════════════════
hr(); print("  ESTUDIO PM→NY  |  MIÉ · JUE · VIE  |  NQ Futures"); hr()

# CSV intraday (sin columna Volume)
print("\n  Cargando CSV intraday...")
raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw["Volume"] = 1          # proxy uniforme para VP
raw = raw.dropna(subset=["Close"]).sort_index()
print(f"  {len(raw)} barras  |  {raw.index.min().date()} → {raw.index.max().date()}")

# VXN diario
print("  Descargando ^VXN...")
vxn_day = {}
try:
    import yfinance as yf
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if isinstance(vdf.columns, pd.MultiIndex):
        vdf.columns = vdf.columns.get_level_values(0)
    for idx, row in vdf.iterrows():
        vxn_day[idx.date()] = round(float(row["Close"]), 2)
    print(f"  VXN: {len(vxn_day)} días")
except Exception as e:
    print(f"  VXN no disponible ({e})")

# ════════════════════════════════════════════════════════════════
# FUNCIONES BASE
# ════════════════════════════════════════════════════════════════
def bt(d, t0, t1):
    a = datetime.strptime(t0,"%H:%M").time()
    b = datetime.strptime(t1,"%H:%M").time()
    return d[(d.index.time >= a) & (d.index.time <= b)]

def calc_vp(df_slice, bins=VP_BINS):
    if len(df_slice) < 2: return None, None, None
    lo, hi = df_slice["Low"].min(), df_slice["High"].max()
    if hi == lo: return None, None, None
    edges   = np.linspace(lo, hi, bins+1)
    centers = (edges[:-1]+edges[1:])/2
    vols    = np.zeros(bins)
    for _, row in df_slice.iterrows():
        mask = (centers >= float(row["Low"])) & (centers <= float(row["High"]))
        if mask.sum() > 0: vols[mask] += 1/mask.sum()
    pi = int(np.argmax(vols)); poc = centers[pi]
    tot = vols.sum(); tgt = tot*0.70
    li = hi_i = pi; acc = vols[pi]
    while acc < tgt and (li>0 or hi_i<bins-1):
        la = vols[li-1] if li>0 else 0
        ha = vols[hi_i+1] if hi_i<bins-1 else 0
        if la>=ha and li>0: li-=1; acc+=la
        elif hi_i<bins-1:   hi_i+=1; acc+=ha
        else: break
    return centers[hi_i], poc, centers[li]   # VAH, POC, VAL

# ════════════════════════════════════════════════════════════════
# EXTRAER SESIONES
# ════════════════════════════════════════════════════════════════
def extract_sessions(weekday):
    days = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday()==weekday})
    sessions = []
    for day in days:
        prev = day - timedelta(days=1)
        s0   = ET.localize(datetime(prev.year,prev.month,prev.day,18,0))
        s1   = ET.localize(datetime(day.year,day.month,day.day,16,30))
        ny40 = ET.localize(datetime(day.year,day.month,day.day,9,40))

        d = raw[(raw.index>=s0)&(raw.index<=s1)].copy()
        if d.empty: continue

        asia  = d[d.index <= ny40]
        vah, poc, val = calc_vp(asia)

        pm  = bt(d,"07:00","09:29")
        ny  = bt(d,"09:30","16:00")
        spk = bt(d,"08:30","08:44")
        pre = bt(d,"08:00","08:29")

        if len(pm)<3 or len(ny)<4: continue

        pm_o = float(pm.iloc[0]["Open"])
        pm_c = float(pm.iloc[-1]["Close"])
        pm_m = pm_c - pm_o
        pm_r = float(pm["High"].max()) - float(pm["Low"].min())
        pm_d = "BULL" if pm_m>15 else ("BEAR" if pm_m<-15 else "FLAT")

        ny_o = float(ny.iloc[0]["Open"])
        ny_c = float(ny.iloc[-1]["Close"])
        ny_m = ny_c - ny_o
        ny_r = float(ny["High"].max()) - float(ny["Low"].min())
        ny_d = "BULL" if ny_m>30 else ("BEAR" if ny_m<-30 else "FLAT")

        hi1 = ny["High"].idxmax() < ny["Low"].idxmin()

        spk_m = 0
        if not spk.empty and not pre.empty:
            spk_m = float(spk.iloc[-1]["Close"]) - float(pre.iloc[-1]["Close"])

        if vah and val:
            if ny_o > vah:   vap = "ABOVE_VA"
            elif ny_o < val: vap = "BELOW_VA"
            else:            vap = "INSIDE_VA"
        else: vap = "NO_VP"

        vxn = vxn_day.get(day)

        sessions.append({
            "date":day, "wd":weekday,
            "pm_move":round(pm_m), "pm_range":round(pm_r), "pm_dir":pm_d,
            "ny_move":round(ny_m), "ny_range":round(ny_r), "ny_dir":ny_d,
            "hi_first":hi1, "spk_move":round(spk_m),
            "vah":round(vah) if vah else None,
            "poc":round(poc) if poc else None,
            "val":round(val) if val else None,
            "va_pos":vap,
            "vxn":vxn,
        })
    return pd.DataFrame(sessions)

# ════════════════════════════════════════════════════════════════
# ANÁLISIS COMPLETO POR DÍA
# ════════════════════════════════════════════════════════════════
def analyze(df_s, wd):
    n = len(df_s)
    name = DIAS_ES[wd]
    name_en = DIAS_EN[wd]
    if n < 3:
        print(f"\n  ⚠️  {name}: solo {n} sesiones, insuficiente.")
        return {}

    results = {"day": name_en, "sessions": n}

    print(f"\n\n{'█'*W}")
    print(f"  📅  {name}  —  {n} sesiones  |  {df_s['date'].min()} → {df_s['date'].max()}")
    print(f"{'█'*W}")

    # ── 1. PM → NY ───────────────────────────────────────────
    hr("═"); print(f"  1️⃣   PRE-MARKET → NY  (predictor #1)"); hr("═")
    pm_results = {}
    for pd_dir in ["BULL","BEAR","FLAT"]:
        sub = df_s[df_s["pm_dir"]==pd_dir]
        if sub.empty: continue
        ns   = len(sub)
        bull = (sub["ny_dir"]=="BULL").sum()
        bear = (sub["ny_dir"]=="BEAR").sum()
        flat = ns-bull-bear
        same = bull if pd_dir=="BULL" else (bear if pd_dir=="BEAR" else flat)
        pct  = same/ns*100
        arrow = "▲" if pd_dir=="BULL" else ("▼" if pd_dir=="BEAR" else "▬")
        bar  = "█"*int(pct/5)
        print(f"\n  PM {pd_dir} {arrow}  →  {ns} sesiones")
        print(f"    NY BULL {bull:>2} ({bull/ns*100:.0f}%)  |  NY BEAR {bear:>2} ({bear/ns*100:.0f}%)  |  NY FLAT {flat:>2} ({flat/ns*100:.0f}%)")
        if pd_dir in ("BULL","BEAR"):
            print(f"    ✅ CORRELACIÓN  {same}/{ns}  =  {pct:.1f}%   {bar}")
        pm_results[pd_dir] = {"n":ns,"bull":int(bull),"bear":int(bear),"pct_match":round(pct,1)}
    results["pm_to_ny"] = pm_results

    # ── 2. VOLUME PROFILE ────────────────────────────────────
    hr("═"); print(f"  2️⃣   VOLUME PROFILE (Asia→9:40)  →  NY MOVEMENT"); hr("═")
    has_vp = df_s[df_s["va_pos"]!="NO_VP"]
    print(f"\n  Sesiones con VP: {len(has_vp)}/{n}")
    vp_results = {}
    if len(has_vp) >= 3:
        print(f"\n  {'Open NY vs VA':<15}  {'N':>3}  {'BULL':>7}  {'BEAR':>7}  {'Mov prom':>10}  Sesgo")
        print("  "+"─"*58)
        for pos,label in [("ABOVE_VA","Sobre VA"),("INSIDE_VA","Dentro VA"),("BELOW_VA","Bajo VA")]:
            sub = has_vp[has_vp["va_pos"]==pos]
            if sub.empty: continue
            ns  = len(sub); bull=(sub["ny_dir"]=="BULL").sum(); bear=(sub["ny_dir"]=="BEAR").sum()
            avg = sub["ny_move"].mean()
            sesgo = "🟢 ALCISTA" if bull/ns>=0.6 else ("🔴 BAJISTA" if bear/ns>=0.6 else "⚪ Mixto")
            print(f"  {label:<15}  {ns:>3}  {bull:>3}({bull/ns*100:.0f}%)  {bear:>3}({bear/ns*100:.0f}%)  {avg:>+10.0f}  {sesgo}")
            vp_results[pos] = {"n":ns,"bull":int(bull),"bear":int(bear),"avg_move":round(avg)}
    results["va_open"] = vp_results

    # ── 3. VXN ───────────────────────────────────────────────
    has_vxn = df_s[df_s["vxn"].notna()]
    if len(has_vxn) >= 4:
        hr("═"); print(f"  3️⃣   VXN  →  RANGO NY  ({len(has_vxn)} sesiones)"); hr("═")
        corr = has_vxn["vxn"].corr(has_vxn["ny_range"])
        print(f"\n  Correlación VXN → NY Range: r = {corr:.3f}")
        print(f"\n  {'VXN Nivel':<18}  {'N':>3}  {'Med Rango':>10}  {'Avg Rango':>10}")
        print("  "+"─"*48)
        vxn_results = {}
        for lo,hi,label in [(0,20,"<20 Calma"),(20,25,"20-25 Normal"),(25,30,"25-30 Elevado"),(30,99,">30 Pánico")]:
            sub = has_vxn[(has_vxn["vxn"]>=lo)&(has_vxn["vxn"]<hi)]
            if sub.empty: continue
            med = sub["ny_range"].median(); avg = sub["ny_range"].mean()
            print(f"  {label:<18}  {len(sub):>3}  {med:>10.0f}  {avg:>10.0f}")
            vxn_results[label] = {"n":len(sub),"median_range":round(med),"avg_range":round(avg)}
        results["vxn_range"] = vxn_results
        results["vxn_r"] = round(corr,3)

    # ── 4. SPIKE 8:30 ────────────────────────────────────────
    hr("═"); print(f"  4️⃣   SPIKE 8:30  →  TRAMPA?"); hr("═")
    spk_up  = df_s[df_s["spk_move"]> 25]
    spk_dn  = df_s[df_s["spk_move"]<-25]
    spk_fl  = df_s[abs(df_s["spk_move"])<=25]
    print(f"\n  {'Spike 8:30':<25}  {'N':>3}  {'NY BULL':>8}  {'NY BEAR':>8}  Nota")
    print("  "+"─"*58)
    for sub,label in [(spk_up,"▲ >+25pts (alcista)"),(spk_dn,"▼ <-25pts (bajista)"),(spk_fl,"▬ plano ±25pts")]:
        if sub.empty: continue
        ns=len(sub); bull=(sub["ny_dir"]=="BULL").sum(); bear=(sub["ny_dir"]=="BEAR").sum()
        trap = bear/ns*100 if "alcista" in label else 0
        nota = f"TRAMPA {trap:.0f}%" if "alcista" in label and trap>40 else "—"
        print(f"  {label:<25}  {ns:>3}  {bull:>4}({bull/ns*100:.0f}%)  {bear:>4}({bear/ns*100:.0f}%)  {nota}")

    # ── 5. HIGH/LOW SEQUENCE ─────────────────────────────────
    hr("═"); print(f"  5️⃣   ¿QUÉ LLEGA PRIMERO EN NY? (para operar apertura)"); hr("═")
    hi1 = df_s["hi_first"].sum(); lo1 = n-hi1
    print(f"\n  Máximo primero → {hi1}/{n} = {hi1/n*100:.0f}%  (sube luego baja)")
    print(f"  Mínimo primero → {lo1}/{n} = {lo1/n*100:.0f}%  (baja luego sube)")
    if hi1/n>=0.55:   print(f"  → Patrón: HIGH FIRST   ⚠️ cuidado entrando long tarde")
    elif lo1/n>=0.55: print(f"  → Patrón: LOW FIRST    📍 buscar long en el low de apertura")
    results["hi_first_pct"] = round(hi1/n*100,1)

    # ── 6. RANGOS + SESGO ────────────────────────────────────
    hr("═"); print(f"  6️⃣   SESGO GLOBAL + RANGOS"); hr("═")
    bull_t=(df_s["ny_dir"]=="BULL").sum(); bear_t=(df_s["ny_dir"]=="BEAR").sum()
    flat_t=n-bull_t-bear_t
    print(f"\n  BULL: {bull_t}/{n} = {bull_t/n*100:.0f}%   BEAR: {bear_t}/{n} = {bear_t/n*100:.0f}%   FLAT: {flat_t}/{n} = {flat_t/n*100:.0f}%")
    print(f"\n  Rango NY  —  Mediana: {df_s['ny_range'].median():.0f}pts  |  Avg: {df_s['ny_range'].mean():.0f}pts  |  P25-P75: {df_s['ny_range'].quantile(.25):.0f}-{df_s['ny_range'].quantile(.75):.0f}pts")
    corr_pm = df_s["pm_range"].corr(df_s["ny_range"])
    print(f"  Correlación PM_range → NY_range: r = {corr_pm:.3f}")
    results["bias"] = {"bull":int(bull_t),"bear":int(bear_t),"flat":int(flat_t)}
    results["ny_range_median"] = round(df_s["ny_range"].median())
    results["ny_range_avg"]    = round(df_s["ny_range"].mean())
    results["pm_ny_range_corr"]= round(corr_pm,3)

    # ── 7. REGLAS ACCIONABLES ────────────────────────────────
    hr("═"); print(f"  📌  REGLAS ACCIONABLES — {name}"); hr("═")
    rules = []
    for pd_dir in ["BULL","BEAR"]:
        sub = df_s[df_s["pm_dir"]==pd_dir]
        if sub.empty: continue
        ns=len(sub); same=(sub["ny_dir"]==pd_dir).sum(); pct=same/ns*100
        if pct>=60:
            r = f"PM {pd_dir} → NY {pd_dir}: {pct:.0f}% ({same}/{ns})"
            rules.append(r); print(f"  ✅ {r}")
    if "va_open" in results:
        for pos,data in results["va_open"].items():
            pct_b=data["bull"]/data["n"]*100; pct_be=data["bear"]/data["n"]*100
            if pct_b>=60: r=f"Open {pos}: NY BULL {pct_b:.0f}%"; rules.append(r); print(f"  ✅ {r}")
            if pct_be>=60: r=f"Open {pos}: NY BEAR {pct_be:.0f}%"; rules.append(r); print(f"  ✅ {r}")
    results["rules"] = rules

    # ── 8. TABLA DETALLE ─────────────────────────────────────
    hr("═"); print(f"  📋  TABLA SESSION POR SESSION (últimas 20)"); hr("═")
    print(f"\n  {'Fecha':<12} {'PM':>5} {'PMd':<5} {'NYmov':>7} {'NYrng':>6} {'NYd':<5} {'VXN':>5} {'Spk':>6} {'VA Open':<11} Hi1st")
    print("  "+"─"*72)
    for _,r in df_s.sort_values("date",ascending=False).head(20).iterrows():
        pms="▲" if r["pm_dir"]=="BULL" else("▼" if r["pm_dir"]=="BEAR" else"—")
        nys="▲" if r["ny_dir"]=="BULL" else("▼" if r["ny_dir"]=="BEAR" else"—")
        hi ="↑" if r["hi_first"] else "↓"
        ok ="✅" if r["pm_dir"]==r["ny_dir"] else("❌" if r["pm_dir"] in("BULL","BEAR") and r["ny_dir"] in("BULL","BEAR") else"  ")
        vx =f"{r['vxn']:.1f}" if r["vxn"] else " —"
        print(f"  {str(r['date']):<12} {r['pm_move']:>+5} {pms:<5} {r['ny_move']:>+7} {r['ny_range']:>6} {nys:<5} {vx:>5} {r['spk_move']:>+6} {r['va_pos']:<11} {hi}  {ok}")

    return results

# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════
all_results = {}
days_to_run = [FILTER_WD] if FILTER_WD is not None else [4, 3, 2]  # Vie primero

for wd in days_to_run:
    print(f"\n  ⏳  Extrayendo sesiones de {DIAS_ES[wd]}...")
    df_s = extract_sessions(wd)
    if df_s.empty:
        print(f"  ⚠️  Sin datos para {DIAS_ES[wd]}")
        continue
    print(f"  {len(df_s)} sesiones encontradas")
    res = analyze(df_s, wd)
    all_results[DIAS_EN[wd]] = res

    # Guardar JSON individual
    fname = f"data/research_{DIAS_EN[wd].lower()}_pm_ny.json"
    os.makedirs("data", exist_ok=True)
    with open(fname,"w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, default=str)
    print(f"\n  💾  Guardado: {fname}")

# JSON consolidado
out_path = "data/research_mie_jue_vie.json"
with open(out_path,"w", encoding="utf-8") as f:
    json.dump(all_results, f, indent=2, default=str)

hr("█"); print(f"  ✅  COMPLETADO — resultados en {out_path}"); hr("█")
print()
