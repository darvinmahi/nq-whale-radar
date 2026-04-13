"""
365_combos.py — Los combos estudiados sobre los 237 días completos del año
Muestra cuántas veces se activó cada combo y qué pasó cada vez
"""
import pandas as pd, pytz
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
    vxn_day = {idx.date(): round(float(row["Close"]),2) for idx,row in vdf.iterrows()}
except: vxn_day = {}

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

ANO2_S = date(2025, 4, 10)
ANO2_E = date(2026, 4, 10)
DIAS   = ["LUNES","MARTES","MIER","JUEVES","VIERNES"]

# ── Construir todos los días ──────────────────────────────────
print("Procesando 237 días...")
all_rows = []
for day in sorted(grouped.keys()):
    if pd.Timestamp(day).weekday() >= 5: continue
    if not (ANO2_S <= day <= ANO2_E): continue
    d = grouped[day]
    or_  = bt(d,"09:30","09:59"); ny   = bt(d,"09:30","16:00")
    or45 = bt(d,"09:30","10:14"); pm   = bt(d,"07:00","09:29")
    spk  = bt(d,"08:30","08:44"); pre  = bt(d,"08:00","08:29")
    if len(or_)<1 or len(ny)<4: continue

    or_m  = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
    or_r  = float(or_["High"].max()) - float(or_["Low"].min())
    ny_m  = float(ny.iloc[-1]["Close"]) - float(ny.iloc[0]["Open"])
    or45_m= float(or45.iloc[-1]["Close"]) - float(or45.iloc[0]["Open"]) if len(or45)>=1 else 0
    pm_m  = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"]) if len(pm)>=2 else 0

    or_d  = "BEAR" if or_m  < -10 else ("BULL" if or_m  > 10 else "FLAT")
    or45_d= "BEAR" if or45_m< -10 else ("BULL" if or45_m> 10 else "FLAT")
    ny_d  = "BEAR" if ny_m  < -30 else ("BULL" if ny_m  > 30 else "FLAT")
    pm_d  = "BEAR" if pm_m  < -15 else ("BULL" if pm_m  > 15 else "FLAT")

    vxn   = vxn_day.get(day)
    vxn_t = None
    if vxn:
        prev=[d2 for d2 in all_dates if d2<day]
        if prev and prev[-1] in vxn_day:
            delta=vxn-vxn_day[prev[-1]]
            vxn_t="RISING" if delta>0.5 else("FALLING" if delta<-0.5 else"FLAT")

    prev=[d2 for d2 in all_dates if d2<day]
    prev_dir=None
    if prev:
        pd_st=[r for r in all_rows if r["day"]==prev[-1]]
        if pd_st: prev_dir=pd_st[0]["ny_d"]

    all_rows.append({
        "day":day,"wd":pd.Timestamp(day).weekday(),
        "or_d":or_d,"or45_d":or45_d,"pm_d":pm_d,
        "or_r":round(or_r),"or_large":or_r>=100,
        "ny_m":round(ny_m),"ny_d":ny_d,
        "vxn":vxn,"vxn_t":vxn_t,"prev_dir":prev_dir
    })

total_dias = len(all_rows)
print(f"  {total_dias} días procesados\n")

# ── Función para analizar un combo ──────────────────────────
def analizar_combo(titulo, wd_filter, cond_fn, target_ny):
    if wd_filter is not None:
        dias_base = [r for r in all_rows if r["wd"]==wd_filter]
        dia_nombre = DIAS[wd_filter]
    else:
        dias_base = all_rows
        dia_nombre = "TODOS"

    dias_cumplen = [r for r in dias_base if cond_fn(r)]
    hits = [r for r in dias_cumplen if r["ny_d"]==target_ny]
    fails = [r for r in dias_cumplen if r["ny_d"]!=target_ny]

    n_base   = len(dias_base)
    n_cumple = len(dias_cumplen)
    n_hits   = len(hits)
    pct      = round(n_hits/n_cumple*100,1) if n_cumple>0 else 0
    freq     = round(n_cumple/n_base*100,1) if n_base>0 else 0

    print("─"*78)
    print(f"  📋 {titulo}")
    print(f"     {dia_nombre}: {n_base} días totales en el año")
    print(f"     Combo se activó: {n_cumple} veces = {freq}% de los {dia_nombre}s")
    print(f"     Aciertos: {n_hits}/{n_cumple} = {pct}%")
    print()
    print(f"  {'#':>3}  {'Fecha':>12}  {'OR':>5}  {'OR45':>5}  {'PM':>5}  {'OR pts':>6}  {'NY mov':>8}  Resultado")
    print("  "+"·"*70)

    for i, r in enumerate(dias_cumplen, 1):
        star = "🔥" if r["or_large"] else "  "
        res  = "✅ ACIERTO" if r["ny_d"]==target_ny else "❌ FALLO  "
        print(f"  {i:>3}  {r['day'].strftime('%d/%m/%Y'):>12}  "
              f"{r['or_d']:>5}  {r['or45_d']:>5}  {r['pm_d']:>5}  "
              f"{r['or_r']:>4}p{star}  {r['ny_m']:>+8}p  {res}")

    if fails:
        print(f"\n  ⚠️  Los {len(fails)} días que FALLARON:")
        for r in fails:
            print(f"       {r['day'].strftime('%d/%m/%Y')} — OR={r['or_d']} OR_range={r['or_r']}pts → NY fue {r['ny_d']} ({r['ny_m']:+}pts)")

    print(f"\n  RESULTADO: {n_hits}/{n_cumple} = {pct}%  (activado {n_cumple}/{n_base} días = {freq}% del tiempo)\n")

# ── COMBOS PRINCIPALES ────────────────────────────────────────
print("="*78)
print("  COMBOS — TODOS LOS DÍAS DEL AÑO 2 (237 días)")
print("="*78)
print()

analizar_combo(
    "VIERNES — OR BEAR → BEAR  (señal simple)",
    4,
    lambda r: r["or_d"]=="BEAR",
    "BEAR"
)

analizar_combo(
    "VIERNES — OR BEAR + OR45 BEAR → BEAR  (doble confirmación)",
    4,
    lambda r: r["or_d"]=="BEAR" and r["or45_d"]=="BEAR",
    "BEAR"
)

analizar_combo(
    "VIERNES — OR BEAR + PM BEAR → BEAR",
    4,
    lambda r: r["or_d"]=="BEAR" and r["pm_d"]=="BEAR",
    "BEAR"
)

analizar_combo(
    "LUNES — OR BEAR → BEAR",
    0,
    lambda r: r["or_d"]=="BEAR",
    "BEAR"
)

analizar_combo(
    "LUNES — OR BULL + PM BEAR → BULL  (fade del pre-market)",
    0,
    lambda r: r["or_d"]=="BULL" and r["pm_d"]=="BEAR",
    "BULL"
)

analizar_combo(
    "MIÉRCOLES — OR BEAR → BEAR",
    2,
    lambda r: r["or_d"]=="BEAR",
    "BEAR"
)

analizar_combo(
    "MIÉRCOLES — OR BEAR + Día anterior BULL → BEAR",
    2,
    lambda r: r["or_d"]=="BEAR" and r.get("prev_dir")=="BULL",
    "BEAR"
)

analizar_combo(
    "JUEVES — OR BEAR + OR >100pts → BEAR",
    3,
    lambda r: r["or_d"]=="BEAR" and r["or_large"],
    "BEAR"
)

analizar_combo(
    "MARTES — OR BEAR → BEAR  (sin edge esperado)",
    1,
    lambda r: r["or_d"]=="BEAR",
    "BEAR"
)

# ── RESUMEN FINAL ─────────────────────────────────────────────
print()
print("="*78)
print("  TABLA RESUMEN — Todos los combos sobre 237 días del año")
print("="*78)
print(f"\n  {'Combo':<45}  {'Activ.':>7}  {'Hits':>6}  {'%':>6}")
print("  "+"─"*65)

combos_resumen = [
    ("VIERNES OR BEAR→BEAR",            4, lambda r: r["or_d"]=="BEAR",                              "BEAR"),
    ("VIERNES OR+OR45 BEAR→BEAR",       4, lambda r: r["or_d"]=="BEAR" and r["or45_d"]=="BEAR",     "BEAR"),
    ("VIERNES OR+PM BEAR→BEAR",         4, lambda r: r["or_d"]=="BEAR" and r["pm_d"]=="BEAR",       "BEAR"),
    ("LUNES OR BEAR→BEAR",              0, lambda r: r["or_d"]=="BEAR",                              "BEAR"),
    ("LUNES OR BULL+PM BEAR→BULL",      0, lambda r: r["or_d"]=="BULL" and r["pm_d"]=="BEAR",       "BULL"),
    ("MIER OR BEAR→BEAR",               2, lambda r: r["or_d"]=="BEAR",                              "BEAR"),
    ("MIER OR BEAR+PrevBULL→BEAR",      2, lambda r: r["or_d"]=="BEAR" and r.get("prev_dir")=="BULL","BEAR"),
    ("JUEVES OR BEAR+>100pts→BEAR",     3, lambda r: r["or_d"]=="BEAR" and r["or_large"],            "BEAR"),
    ("MARTES OR BEAR→BEAR (sin edge)",  1, lambda r: r["or_d"]=="BEAR",                              "BEAR"),
]

for label, wd_f, cond, tgt in combos_resumen:
    base = [r for r in all_rows if r["wd"]==wd_f]
    sub  = [r for r in base if cond(r)]
    hits = sum(1 for r in sub if r["ny_d"]==tgt)
    n    = len(sub)
    p    = round(hits/n*100,1) if n>0 else 0
    freq = round(n/len(base)*100,1) if base else 0
    icon = "🔥" if p>=90 else("✅" if p>=70 else("⚠️" if p>=60 else"❌"))
    print(f"  {label:<45}  {n:>4}d({freq:.0f}%)  {hits:>4}/{n:<2}  {p:>5.1f}% {icon}")
