"""
research_jueves_completo.py
════════════════════════════════════════════════════════════════
Estudio completo JUEVES — misma metodología que MARTES.

Analiza:
  1. PM direction (7:00-9:29) → NY direction (9:30-16:00)
  2. Volume Profile (VP Asia/PM) → VAH/VAL/POC vs NY movement
  3. Open NY vs VA: abre dentro/sobre/bajo → ¿adónde va?
  4. VXN (volatilidad) → tamaño del rango NY
  5. Spike 8:30 (Jobless Claims) → ¿trampa o confirmación?
  6. Correlaciones generales

Fuente: data/research/nq_15m_intraday.csv + Yahoo Finance ^VXN
"""

import pandas as pd
import numpy as np
import pytz, sys
from datetime import datetime, date, timedelta

ET      = pytz.timezone("America/New_York")
CSV     = "data/research/nq_15m_intraday.csv"
VP_BINS = 50
W       = 65   # ancho consola

def hr(char="═"): print(char * W)
def sec(title): print(f"\n  {title}"); print("  " + "─"*55)

# ════════════════════════════════════════════════════════════════
# 1. CARGAR DATOS
# ════════════════════════════════════════════════════════════════
hr(); print("  ESTUDIO JUEVES NQ — PM → NY + VP + VXN"); hr()

print("\n  Cargando CSV intraday...")
df_raw = pd.read_csv(CSV, skiprows=2)
df_raw.columns = ["Datetime","Close","High","Low","Open","Volume"]
df_raw = df_raw.dropna(subset=["Datetime"])
df_raw["Datetime"] = pd.to_datetime(df_raw["Datetime"], utc=True).dt.tz_convert(ET)
df_raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open","Volume"]:
    df_raw[c] = pd.to_numeric(df_raw[c], errors="coerce")
df_raw["Volume"] = df_raw["Volume"].fillna(1)
df_raw = df_raw.dropna(subset=["Close"]).sort_index()
print(f"  CSV: {df_raw.index.min().date()} → {df_raw.index.max().date()}  ({len(df_raw)} barras 15m)")

# VXN desde Yahoo Finance
print("  Descargando ^VXN (volatilidad)...")
vxn_day = {}
try:
    import yfinance as yf
    vxn_df = yf.download("^VXN", period="12mo", interval="1d", progress=False, auto_adjust=True)
    if isinstance(vxn_df.columns, pd.MultiIndex):
        vxn_df.columns = vxn_df.columns.get_level_values(0)
    for idx, row in vxn_df.iterrows():
        vxn_day[idx.date()] = float(row["Close"])
    print(f"  VXN: {len(vxn_day)} días disponibles")
except Exception as e:
    print(f"  VXN no disponible: {e}")


# ════════════════════════════════════════════════════════════════
# 2. CALCULAR VP
# ════════════════════════════════════════════════════════════════
def calc_vp(df_slice, bins=VP_BINS):
    if df_slice.empty or len(df_slice) < 2:
        return None, None, None
    lo, hi = df_slice["Low"].min(), df_slice["High"].max()
    if hi == lo: return None, None, None
    edges   = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols    = np.zeros(bins)
    for _, row in df_slice.iterrows():
        vol_ = float(row["Volume"]) if row["Volume"] > 0 else 1
        mask = (centers >= float(row["Low"])) & (centers <= float(row["High"]))
        cnt  = mask.sum()
        if cnt > 0: vols[mask] += vol_ / cnt
    poc_idx = int(np.argmax(vols))
    poc     = centers[poc_idx]
    total   = vols.sum(); target = total * 0.70
    lo_i = hi_i = poc_idx; accum = vols[poc_idx]
    while accum < target and (lo_i > 0 or hi_i < bins - 1):
        la = vols[lo_i-1] if lo_i > 0 else 0
        ha = vols[hi_i+1] if hi_i < bins-1 else 0
        if la >= ha and lo_i > 0: lo_i -= 1; accum += la
        elif hi_i < bins-1:       hi_i += 1; accum += ha
        else: break
    return centers[hi_i], poc, centers[lo_i]   # VAH, POC, VAL


def bt(day_df, t0, t1):
    t0_ = datetime.strptime(t0, "%H:%M").time()
    t1_ = datetime.strptime(t1, "%H:%M").time()
    return day_df[(day_df.index.time >= t0_) & (day_df.index.time <= t1_)]


# ════════════════════════════════════════════════════════════════
# 3. EXTRAER SESIONES DE JUEVES
# ════════════════════════════════════════════════════════════════
thursdays = sorted({d for d in (df_raw.index.date) if pd.Timestamp(d).weekday() == 3})
print(f"\n  Jueves encontrados en CSV: {len(thursdays)}")

CLAIMS = {
    date(2026,1,8):  (201_000,215_000,201_000),
    date(2026,1,15): (217_000,212_000,201_000),
    date(2026,1,22): (223_000,215_000,217_000),
    date(2026,1,29): (209_000,206_000,223_000),
    date(2026,2,5):  (231_000,212_000,209_000),
    date(2026,2,12): (227_000,222_000,232_000),
    date(2026,2,19): (206_000,223_000,229_000),
    date(2026,2,26): (213_000,215_000,208_000),
    date(2026,3,5):  (213_000,215_000,213_000),
    date(2026,3,12): (213_000,214_000,213_000),
}

sessions = []
for thu in thursdays:
    prev = thu - timedelta(days=1)
    start_ts = ET.localize(datetime(prev.year, prev.month, prev.day, 18, 0))
    end_ts   = ET.localize(datetime(thu.year, thu.month, thu.day, 16, 30))
    ny40_ts  = ET.localize(datetime(thu.year, thu.month, thu.day, 9, 40))

    day_df = df_raw[(df_raw.index >= start_ts) & (df_raw.index <= end_ts)].copy()
    if day_df.empty: continue

    # VP del período Asia→9:40
    asia_df = day_df[day_df.index <= ny40_ts]
    vah, poc, val = calc_vp(asia_df)

    # Sesiones
    pm    = bt(day_df, "07:00", "09:29")
    ny    = bt(day_df, "09:30", "16:00")
    spike = bt(day_df, "08:30", "08:44")
    pre8  = bt(day_df, "08:00", "08:29")

    if len(pm) < 3 or len(ny) < 4: continue

    pm_open  = float(pm.iloc[0]["Open"])
    pm_close = float(pm.iloc[-1]["Close"])
    pm_move  = pm_close - pm_open
    pm_range = float(pm["High"].max()) - float(pm["Low"].min())
    pm_dir   = "BULL" if pm_move > 15 else ("BEAR" if pm_move < -15 else "FLAT")

    ny_open  = float(ny.iloc[0]["Open"])
    ny_close = float(ny.iloc[-1]["Close"])
    ny_move  = ny_close - ny_open
    ny_range = float(ny["High"].max()) - float(ny["Low"].min())
    ny_dir   = "BULL" if ny_move > 30 else ("BEAR" if ny_move < -30 else "FLAT")

    # ¿Máximo o mínimo primero en NY?
    idx_hi = ny["High"].idxmax()
    idx_lo = ny["Low"].idxmin()
    hi_first = idx_hi < idx_lo

    # Spike 8:30 vs Claims
    spk_move = 0
    if not spike.empty and not pre8.empty:
        spk_move = float(spike.iloc[-1]["Close"]) - float(pre8.iloc[-1]["Close"])

    # Relación NY Open vs VA
    if vah and val:
        if ny_open > vah:   va_pos = "ABOVE_VA"
        elif ny_open < val: va_pos = "BELOW_VA"
        else:               va_pos = "INSIDE_VA"
    else:
        va_pos = "NO_VP"

    # VXN del día
    vxn = vxn_day.get(thu)

    # Claims
    cl = CLAIMS.get(thu, (None,None,None))
    act, fct, prv = cl
    cl_surprise = None
    if act and fct: cl_surprise = act - fct  # negativo = mejor (menos claims)

    sessions.append({
        "date":       thu,
        "pm_move":    round(pm_move),
        "pm_range":   round(pm_range),
        "pm_dir":     pm_dir,
        "ny_move":    round(ny_move),
        "ny_range":   round(ny_range),
        "ny_dir":     ny_dir,
        "hi_first":   hi_first,
        "spk_move":   round(spk_move),
        "vah":        round(vah) if vah else None,
        "poc":        round(poc) if poc else None,
        "val":        round(val) if val else None,
        "va_pos":     va_pos,
        "vxn":        round(vxn, 1) if vxn else None,
        "claims_act": act,
        "claims_fct": fct,
        "cl_surprise":cl_surprise,
    })

df_s = pd.DataFrame(sessions)
n = len(df_s)
print(f"  Sesiones válidas procesadas: {n}")

if n == 0:
    print("  Sin datos suficientes."); sys.exit(0)


# ════════════════════════════════════════════════════════════════
# 4. ANÁLISIS PM → NY (PREDICTOR PRINCIPAL)
# ════════════════════════════════════════════════════════════════
hr("═")
print(f"  1️⃣  PRE-MARKET → NY SESSION  (predictor principal)")
hr("═")

for pm_dir in ["BULL","BEAR","FLAT"]:
    sub = df_s[df_s["pm_dir"] == pm_dir]
    if sub.empty: continue
    ns = len(sub)
    ny_bull = (sub["ny_dir"] == "BULL").sum()
    ny_bear = (sub["ny_dir"] == "BEAR").sum()
    ny_flat = (sub["ny_dir"] == "FLAT").sum()
    pct_match = (ny_bull if pm_dir=="BULL" else ny_bear if pm_dir=="BEAR" else ny_flat) / ns * 100
    arrow = "▲" if pm_dir=="BULL" else ("▼" if pm_dir=="BEAR" else "▬")
    bar = "█" * int(pct_match/5)
    print(f"\n  PM {pm_dir} ({arrow}) → {ns} sesiones")
    print(f"    NY BULL: {ny_bull:>2} ({ny_bull/ns*100:.0f}%)")
    print(f"    NY BEAR: {ny_bear:>2} ({ny_bear/ns*100:.0f}%)")
    print(f"    NY FLAT: {ny_flat:>2} ({ny_flat/ns*100:.0f}%)")
    if pm_dir in ("BULL","BEAR"):
        same = ny_bull if pm_dir=="BULL" else ny_bear
        print(f"    → CORRELACIÓN: {same}/{ns} = {same/ns*100:.1f}%  {bar}")

# ════════════════════════════════════════════════════════════════
# 5. VOLUME PROFILE → NY MOVEMENT
# ════════════════════════════════════════════════════════════════
hr("═")
print(f"  2️⃣  VOLUME PROFILE (Asia→9:40) vs NY MOVEMENT")
hr("═")

has_vp = df_s[df_s["va_pos"] != "NO_VP"]
print(f"\n  Sesiones con VP calculado: {len(has_vp)}/{n}")

sec("Open NY vs Value Area → dirección NY")
print(f"  {'Posición Open':<15} {'N':>3}  {'BULL':>5}  {'BEAR':>5}  {'FLAT':>5}  {'Mov prom':>9}  {'Sesgo'}")
print("  " + "─"*60)
for pos, label in [("ABOVE_VA","Sobre VA"), ("INSIDE_VA","Dentro VA"), ("BELOW_VA","Bajo VA")]:
    sub = has_vp[has_vp["va_pos"] == pos]
    if sub.empty: continue
    ns   = len(sub)
    bull = (sub["ny_dir"]=="BULL").sum()
    bear = (sub["ny_dir"]=="BEAR").sum()
    flat = ns - bull - bear
    avg  = sub["ny_move"].mean()
    sesgo = "🟢 ALCISTA" if bull/ns>=0.6 else ("🔴 BAJISTA" if bear/ns>=0.6 else "⚪ Mixto")
    print(f"  {label:<15} {ns:>3}  {bull:>3}({bull/ns*100:.0f}%)  {bear:>3}({bear/ns*100:.0f}%)  {flat:>3}({flat/ns*100:.0f}%)  {avg:>+9.0f}  {sesgo}")

sec("¿POC como imán? — ¿precio cierra cerca del POC?")
close_to_poc = has_vp[has_vp["poc"].notna()].copy()
close_to_poc["ny_end_dist"] = abs(
    close_to_poc.apply(lambda r: 
        df_raw[(df_raw.index.date == r["date"]) & 
               (df_raw.index.time >= datetime.strptime("15:45","%H:%M").time())]["Close"].iloc[-1]
        if not df_raw[(df_raw.index.date == r["date"]) & 
               (df_raw.index.time >= datetime.strptime("15:45","%H:%M").time())].empty
        else float('nan'), axis=1) - close_to_poc["poc"]
)
valid_poc = close_to_poc.dropna(subset=["ny_end_dist"])
if len(valid_poc) > 0:
    near_poc = (valid_poc["ny_end_dist"] < 50).sum()
    print(f"  Sesiones donde cierre NY está a <50pts del POC: {near_poc}/{len(valid_poc)} = {near_poc/len(valid_poc)*100:.0f}%")
    print(f"  Distancia media al cierre: {valid_poc['ny_end_dist'].mean():.0f} pts")


# ════════════════════════════════════════════════════════════════
# 6. VXN → RANGO NY
# ════════════════════════════════════════════════════════════════
has_vxn = df_s[df_s["vxn"].notna()]
if len(has_vxn) >= 3:
    hr("═")
    print(f"  3️⃣  VXN → RANGO NY  ({len(has_vxn)} sesiones con VXN)")
    hr("═")
    corr = has_vxn["vxn"].corr(has_vxn["ny_range"])
    print(f"\n  Correlación VXN → NY Range: r = {corr:.3f}")

    sec("Rangos NY por nivel de VXN")
    print(f"  {'VXN Nivel':<18} {'N':>3}  {'Med Rango':>10}  {'Avg Rango':>10}")
    print("  " + "─"*50)
    for lo, hi, label in [(0,20,"<20 (Calma)"),(20,25,"20-25 (Normal)"),(25,30,"25-30 (Elevado)"),(30,99,">30 (Pánico)")]:
        sub = has_vxn[(has_vxn["vxn"]>=lo) & (has_vxn["vxn"]<hi)]
        if sub.empty: continue
        print(f"  {label:<18} {len(sub):>3}  {sub['ny_range'].median():>10.0f}  {sub['ny_range'].mean():>10.0f}")

    sec("Dirección NY por nivel VXN")
    for lo, hi, label in [(0,20,"VXN <20"),(20,25,"VXN 20-25"),(25,99,"VXN >25")]:
        sub = has_vxn[(has_vxn["vxn"]>=lo) & (has_vxn["vxn"]<hi)]
        if sub.empty: continue
        ns   = len(sub)
        bull = (sub["ny_dir"]=="BULL").sum()
        bear = (sub["ny_dir"]=="BEAR").sum()
        print(f"  {label:<12}: BULL {bull}({bull/ns*100:.0f}%) / BEAR {bear}({bear/ns*100:.0f}%)")
else:
    print(f"\n  ⚠️  VXN: pocos datos ({len(has_vxn)} sesiones) — ejecuta en días de mercado para más historial")


# ════════════════════════════════════════════════════════════════
# 7. SPIKE 8:30 (CLAIMS) → NY DIRECTION
# ════════════════════════════════════════════════════════════════
hr("═")
print(f"  4️⃣  SPIKE 8:30 (Jobless Claims) → TRAMPA?")
hr("═")

spk_up   = df_s[df_s["spk_move"] > 25]
spk_dn   = df_s[df_s["spk_move"] < -25]
spk_flat = df_s[abs(df_s["spk_move"]) <= 25]

def spk_stats(sub, label):
    if sub.empty: return
    ns = len(sub)
    bull = (sub["ny_dir"]=="BULL").sum()
    bear = (sub["ny_dir"]=="BEAR").sum()
    trap = sub[(sub["spk_move"]>25) & (sub["ny_dir"]=="BEAR")].shape[0] if label == "SPIKE ▲" else 0
    print(f"\n  {label} ({ns} sesiones)")
    print(f"    NY BULL: {bull} ({bull/ns*100:.0f}%)")
    print(f"    NY BEAR: {bear} ({bear/ns*100:.0f}%)")
    if label == "SPIKE ▲" and ns > 0:
        print(f"    TRAMPA (spike up → NY baja): {bear}/{ns} = {bear/ns*100:.0f}% 🎯")

spk_stats(spk_up,   "SPIKE ▲ (Claims MEJOR de lo esperado o alcista)")
spk_stats(spk_dn,   "SPIKE ▼ (Claims PEOR o bajista)")
spk_stats(spk_flat, "SPIKE ─ (plano, ≤25pts)")


# ════════════════════════════════════════════════════════════════
# 8. ¿MÁXIMO O MÍNIMO PRIMERO?
# ════════════════════════════════════════════════════════════════
hr("═")
print(f"  5️⃣  ¿QUÉ LLEGA PRIMERO EN NY? (para operar la apertura)")
hr("═")
hi_1st = df_s["hi_first"].sum()
lo_1st = n - hi_1st
print(f"\n  Máximo primero (sube luego baja): {hi_1st}/{n} = {hi_1st/n*100:.0f}%")
print(f"  Mínimo primero (baja luego sube): {lo_1st}/{n} = {lo_1st/n*100:.0f}%")
if hi_1st/n >= 0.55:
    print(f"  → JUEVES tiende a hacer HIGH primero (cuidado con longs tarde)")
elif lo_1st/n >= 0.55:
    print(f"  → JUEVES tiende a hacer LOW primero — patrón TRAMPA ALCISTA")

# Por PM direction
sec("¿Primero High o Low según PM direction?")
for pm_dir in ["BULL","BEAR"]:
    sub = df_s[df_s["pm_dir"] == pm_dir]
    if sub.empty: continue
    h1  = sub["hi_first"].sum()
    print(f"  PM {pm_dir}: High 1st = {h1}/{len(sub)} ({h1/len(sub)*100:.0f}%)  Low 1st = {len(sub)-h1}/{len(sub)} ({(len(sub)-h1)/len(sub)*100:.0f}%)")


# ════════════════════════════════════════════════════════════════
# 9. RESUMEN Y REGLAS VALIDADAS
# ════════════════════════════════════════════════════════════════
hr("═")
print(f"  6️⃣  SESGO GLOBAL + RANGOS JUEVES")
hr("═")
bull_tot = (df_s["ny_dir"]=="BULL").sum()
bear_tot = (df_s["ny_dir"]=="BEAR").sum()
flat_tot = (df_s["ny_dir"]=="FLAT").sum()
print(f"\n  BULL: {bull_tot}/{n} = {bull_tot/n*100:.0f}%")
print(f"  BEAR: {bear_tot}/{n} = {bear_tot/n*100:.0f}%")
print(f"  FLAT: {flat_tot}/{n} = {flat_tot/n*100:.0f}%")

sec("Rangos NY (High - Low del día)")
print(f"  Mediana  : {df_s['ny_range'].median():.0f} pts")
print(f"  Promedio : {df_s['ny_range'].mean():.0f} pts")
print(f"  P25-P75  : {df_s['ny_range'].quantile(0.25):.0f} - {df_s['ny_range'].quantile(0.75):.0f} pts")
print(f"  Máximo   : {df_s['ny_range'].max():.0f} pts")

corr_pm_ny = df_s["pm_range"].corr(df_s["ny_range"])
print(f"\n  Correlación PM_range → NY_range: r = {corr_pm_ny:.3f}")


# ════════════════════════════════════════════════════════════════
# 10. TABLA DETALLE
# ════════════════════════════════════════════════════════════════
hr("═")
print(f"  📋  TABLA DETALLE — todas las sesiones")
hr("═")
print(f"\n  {'Fecha':<12} {'PM':>5} {'PMd':<5} {'NYmov':>6} {'NYrng':>6} {'NYd':<5} {'VXN':>5} {'Spk':>5} {'VA_Open':<11} {'Hi1st'}")
print("  " + "─"*75)
for _, r in df_s.sort_values("date", ascending=False).iterrows():
    pm_s = "▲" if r["pm_dir"]=="BULL" else ("▼" if r["pm_dir"]=="BEAR" else "—")
    ny_s = "▲" if r["ny_dir"]=="BULL" else ("▼" if r["ny_dir"]=="BEAR" else "—")
    hi  = "↑" if r["hi_first"] else "↓"
    match = "✅" if r["pm_dir"]==r["ny_dir"] else ("❌" if r["pm_dir"] in ("BULL","BEAR") and r["ny_dir"] in ("BULL","BEAR") else "  ")
    vxn_s = f"{r['vxn']:.0f}" if r["vxn"] else " —"
    print(f"  {str(r['date']):<12} {r['pm_move']:>+5} {pm_s:<5} {r['ny_move']:>+6} {r['ny_range']:>6} {ny_s:<5} {vxn_s:>5} {r['spk_move']:>+5} {r['va_pos']:<11} {hi}  {match}")

hr("═")
print(f"  ANÁLISIS JUEVES COMPLETADO — {n} sesiones")
hr("═")
print()
