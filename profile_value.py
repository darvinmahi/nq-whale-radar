"""
profile_value.py — Value Area como predictor del día
Calcula para cada día:
  - POC  = precio con más actividad (Point of Control)
  - VAH  = Value Area High (70% del volumen)
  - VAL  = Value Area Low  (70% del volumen)

Estudia si abrir por encima/debajo del día anterior predice la dirección
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

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

def compute_value_area(bars, va_pct=0.70):
    """
    Aproxima el Value Area usando distribución de precio en cada barra.
    Cada barra 15min 'pesa' igual (sin volumen real).
    Devuelve: poc, vah, val
    """
    if len(bars) == 0:
        return None, None, None
    # Precio típico de cada barra
    typical = (bars["High"] + bars["Low"] + bars["Close"]) / 3
    lo = float(bars["Low"].min())
    hi = float(bars["High"].max())
    rang = hi - lo
    if rang < 5:
        return float(typical.mean()), hi, lo

    # Bins de 5 puntos
    n_bins = max(int(rang / 5), 10)
    bins = np.linspace(lo, hi, n_bins + 1)
    hist = np.zeros(n_bins)

    for _, row in bars.iterrows():
        b_lo = float(row["Low"]); b_hi = float(row["High"])
        for i in range(n_bins):
            overlap = min(b_hi, bins[i+1]) - max(b_lo, bins[i])
            if overlap > 0:
                hist[i] += overlap

    poc_idx = int(np.argmax(hist))
    poc = float((bins[poc_idx] + bins[poc_idx+1]) / 2)

    # Value Area: expandir desde POC hasta alcanzar va_pct del total
    total = hist.sum()
    target = total * va_pct
    accumulated = hist[poc_idx]
    lo_idx = poc_idx; hi_idx = poc_idx

    while accumulated < target and (lo_idx > 0 or hi_idx < n_bins-1):
        add_lo = hist[lo_idx-1] if lo_idx > 0 else 0
        add_hi = hist[hi_idx+1] if hi_idx < n_bins-1 else 0
        if add_hi >= add_lo and hi_idx < n_bins-1:
            hi_idx += 1; accumulated += add_hi
        elif lo_idx > 0:
            lo_idx -= 1; accumulated += add_lo
        else:
            hi_idx += 1; accumulated += add_hi

    vah = float((bins[hi_idx] + bins[hi_idx+1]) / 2)
    val = float((bins[lo_idx] + bins[lo_idx+1]) / 2)
    return poc, vah, val

ANO2_S = date(2025, 4, 10)
ANO2_E = date(2026, 4, 10)
DIAS   = ["LUNES","MARTES","MIER  ","JUEVES","VIERNES"]

print("Calculando Value Areas...")
va_cache = {}  # day -> {poc, vah, val}

for day in sorted(grouped.keys()):
    d = grouped[day]
    ny = bt(d, "09:30", "16:00")
    if len(ny) < 4: continue
    poc, vah, val = compute_value_area(ny)
    if poc:
        va_cache[day] = {"poc": round(poc), "vah": round(vah), "val": round(val)}

print(f"  {len(va_cache)} dias con Value Area calculado")

# ── Construir días con contexto ───────────────────────────────
print("Construyendo dataset...")
all_rows = []

for day in sorted(grouped.keys()):
    if pd.Timestamp(day).weekday() >= 5: continue
    if not (ANO2_S <= day <= ANO2_E): continue
    d = grouped[day]
    or_ = bt(d,"09:30","09:59"); ny = bt(d,"09:30","16:00")
    if len(or_)<1 or len(ny)<4: continue

    or_m  = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
    ny_m  = float(ny.iloc[-1]["Close"])  - float(ny.iloc[0]["Open"])
    ny_o  = float(ny.iloc[0]["Open"])
    or_d  = "BEAR" if or_m<-10 else("BULL" if or_m>10 else"FLAT")
    ny_d  = "BEAR" if ny_m<-30 else("BULL" if ny_m>30 else"FLAT")
    wd    = pd.Timestamp(day).weekday()

    # Previous day's value area
    prev_days = [d2 for d2 in all_dates if d2 < day]
    prev_va = None
    if prev_days:
        prev_va = va_cache.get(prev_days[-1])

    pos = None   # position of today's open vs yesterday's value area
    if prev_va:
        if ny_o > prev_va["vah"]:   pos = "ABOVE_VA"   # above value area → bullish
        elif ny_o < prev_va["val"]: pos = "BELOW_VA"   # below value area → bearish
        else:                        pos = "INSIDE_VA"  # inside → uncertain

    row = {
        "day": day, "wd": wd,
        "or_d": or_d, "ny_d": ny_d, "ny_m": round(ny_m),
        "ny_open": round(ny_o), "pos_va": pos,
        "prev_vah": prev_va["vah"] if prev_va else None,
        "prev_val": prev_va["val"] if prev_va else None,
        "prev_poc": prev_va["poc"] if prev_va else None,
    }
    all_rows.append(row)

total = len(all_rows)
print(f"  {total} días procesados\n")

def pct(n, d): return round(n/d*100,1) if d>0 else 0
def badge(p, n): 
    if p is None: return f"  —  "
    icon = "🔥" if p>=85 else("✅" if p>=70 else("~~" if p>=60 else"❌"))
    return f"{p:.0f}%{icon}(n={n})"

# ── ANÁLISIS PRINCIPAL ────────────────────────────────────────
print("="*72)
print("  PROFILE VALUE — Apertura vs Value Area del día anterior")
print("  ABOVE_VA = abre sobre el VA → señal BULL")
print("  BELOW_VA = abre bajo el VA  → señal BEAR")
print("  INSIDE_VA = abre dentro del VA → sin señal clara")
print("="*72)

print(f"\n  {'Posición vs VA previo':<22} {'→ NY BULL':>10} {'→ NY BEAR':>10} {'→ FLAT':>8} {'Total':>6}")
print("  "+"─"*58)

for pos in ["ABOVE_VA","INSIDE_VA","BELOW_VA"]:
    sub = [r for r in all_rows if r["pos_va"]==pos]
    n = len(sub)
    if n == 0: continue
    bull = sum(1 for r in sub if r["ny_d"]=="BULL")
    bear = sum(1 for r in sub if r["ny_d"]=="BEAR")
    flat = sum(1 for r in sub if r["ny_d"]=="FLAT")
    p_bull = pct(bull, n); p_bear = pct(bear, n)
    print(f"  {pos:<22}  {p_bull:>5.0f}%({bull})  {p_bear:>5.0f}%({bear})  {pct(flat,n):>4.0f}%({flat})  {n:>5}")

# ── POR DÍA DE LA SEMANA ─────────────────────────────────────
print()
print("="*72)
print("  PROFILE VALUE POR DÍA DE LA SEMANA")
print("="*72)

for wd in range(5):
    rows_wd = [r for r in all_rows if r["wd"]==wd]
    if not rows_wd: continue
    print(f"\n  {DIAS[wd]} — {len(rows_wd)} días:")
    print(f"  {'Posición':<22}  {'→ BULL':>8}  {'→ BEAR':>8}  Total  Mejor señal")
    print("  "+"─"*60)
    for pos, expected in [("ABOVE_VA","BULL"),("INSIDE_VA",None),("BELOW_VA","BEAR")]:
        sub=[r for r in rows_wd if r["pos_va"]==pos]
        n=len(sub)
        if n==0: continue
        bull=sum(1 for r in sub if r["ny_d"]=="BULL")
        bear=sum(1 for r in sub if r["ny_d"]=="BEAR")
        p_bull=pct(bull,n); p_bear=pct(bear,n)
        best=f"BULL {p_bull:.0f}%" if p_bull>p_bear else f"BEAR {p_bear:.0f}%"
        icon="🔥" if max(p_bull,p_bear)>=80 else("✅" if max(p_bull,p_bear)>=65 else"")
        print(f"  {pos:<22}  {p_bull:>5.0f}%({bull})  {p_bear:>5.0f}%({bear})  {n:>5}  {best} {icon}")

# ── OR + PROFILE VALUE COMBO ──────────────────────────────────
print()
print("="*72)
print("  COMBO: OR + PROFILE VALUE — las dos señales juntas")
print("="*72)

combos = [
    ("BELOW_VA + OR BEAR → BEAR",   lambda r: r["pos_va"]=="BELOW_VA" and r["or_d"]=="BEAR",  "BEAR"),
    ("ABOVE_VA + OR BULL → BULL",   lambda r: r["pos_va"]=="ABOVE_VA" and r["or_d"]=="BULL",  "BULL"),
    ("BELOW_VA + OR BULL → BULL",   lambda r: r["pos_va"]=="BELOW_VA" and r["or_d"]=="BULL",  "BULL"),
    ("ABOVE_VA + OR BEAR → BEAR",   lambda r: r["pos_va"]=="ABOVE_VA" and r["or_d"]=="BEAR",  "BEAR"),
    ("INSIDE_VA + OR BEAR → BEAR",  lambda r: r["pos_va"]=="INSIDE_VA" and r["or_d"]=="BEAR", "BEAR"),
    ("INSIDE_VA + OR BULL → BULL",  lambda r: r["pos_va"]=="INSIDE_VA" and r["or_d"]=="BULL", "BULL"),
]

print(f"\n  {'Combo':<40}  {'Dias':>5}  {'Hits':>5}  {'%':>6}")
print("  "+"─"*60)
for label, cond, tgt in combos:
    sub=[r for r in all_rows if cond(r)]
    n=len(sub); hits=sum(1 for r in sub if r["ny_d"]==tgt)
    p=pct(hits,n)
    icon="🔥" if p>=85 else("✅" if p>=70 else("~~" if p>=60 else"❌"))
    print(f"  {label:<40}  {n:>5}  {hits:>5}  {p:>5.1f}% {icon}")

# ── VIERNES específico ────────────────────────────────────────
print()
print("="*72)
print("  VIERNES — OR BEAR + BELOW_VA (triple señal: día+OR+VA)")
print("="*72)
fri_rows = [r for r in all_rows if r["wd"]==4]
print(f"\n  {'Fecha':>12}  {'Pos VA':>10}  {'OR':>5}  {'PrevVAH':>8}  {'PrevVAL':>8}  {'NY open':>8}  {'NY mov':>8}  Resultado")
print("  "+"─"*82)
count=0
for r in fri_rows:
    if r["pos_va"] and r["or_d"]:
        res = "✅" if r["ny_d"]=="BEAR" and r["or_d"]=="BEAR" else("❌" if r["or_d"]=="BEAR" else"—")
        print(f"  {r['day'].strftime('%d/%m/%Y'):>12}  {r['pos_va']:>10}  {r['or_d']:>5}  "
              f"{r['prev_vah'] or 0:>8}  {r['prev_val'] or 0:>8}  {r['ny_open']:>8}  {r['ny_m']:>+8}p  {res}")
        count+=1

print(f"\n  Total Viernes con datos VA: {count}")
below_bear=[r for r in fri_rows if r["pos_va"]=="BELOW_VA" and r["or_d"]=="BEAR"]
above_bear=[r for r in fri_rows if r["pos_va"]=="ABOVE_VA" and r["or_d"]=="BEAR"]
inside_bear=[r for r in fri_rows if r["pos_va"]=="INSIDE_VA" and r["or_d"]=="BEAR"]
if below_bear:
    h=sum(1 for r in below_bear if r["ny_d"]=="BEAR")
    print(f"\n  OR BEAR + BELOW_VAL  → BEAR: {h}/{len(below_bear)} = {pct(h,len(below_bear))}% 🔥")
if above_bear:
    h=sum(1 for r in above_bear if r["ny_d"]=="BEAR")
    print(f"  OR BEAR + ABOVE_VAH  → BEAR: {h}/{len(above_bear)} = {pct(h,len(above_bear))}%")
if inside_bear:
    h=sum(1 for r in inside_bear if r["ny_d"]=="BEAR")
    print(f"  OR BEAR + INSIDE_VA  → BEAR: {h}/{len(inside_bear)} = {pct(h,len(inside_bear))}%")
