"""
recent_study.py — OR Analysis: 9Y vs 2Y vs 1Y
Compara si las reglas son más fuertes o más débiles en el mercado reciente
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
print(f"  {len(raw)} barras | {len(grouped)} dias")

# Periodos
today = date(2026, 4, 10)
cutoff_1y = date(2025, 4, 10)
cutoff_2y = date(2024, 4, 10)

def bt(d, t0, t1):
    a = dtime(*map(int, t0.split(":")))
    b = dtime(*map(int, t1.split(":")))
    return d[(d.index.time >= a) & (d.index.time <= b)]

def pct(n, d): return round(n / d * 100, 1) if d > 0 else 0

# ── Precompute ────────────────────────────────────────────────
print("Precalculando...")
day_st = {}
for day, d in grouped.items():
    if pd.Timestamp(day).weekday() >= 5: continue
    try:
        pm  = bt(d, "07:00", "09:29")
        ny  = bt(d, "09:30", "16:00")
        or_ = bt(d, "09:30", "09:59")
        mid = bt(d, "12:00", "12:59")
        h1  = bt(d, "10:00", "10:59")

        st = {"day": day, "wd": pd.Timestamp(day).weekday()}
        if len(ny) >= 4:
            ny_o = float(ny.iloc[0]["Open"]); ny_c = float(ny.iloc[-1]["Close"])
            ny_m = ny_c - ny_o
            st["ny_dir"] = "BULL" if ny_m > 30 else ("BEAR" if ny_m < -30 else "FLAT")
            st["ny_move"] = round(ny_m)
            st["ny_range"] = round(float(ny["High"].max()) - float(ny["Low"].min()))
        if len(or_) >= 1:
            or_m = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
            or_r = float(or_["High"].max()) - float(or_["Low"].min())
            st["or_dir"]   = "BULL" if or_m > 10 else ("BEAR" if or_m < -10 else "FLAT")
            st["or_range"] = round(or_r)
            st["or_size"]  = "SMALL" if or_r < 30 else ("MED" if or_r < 60 else ("LARGE" if or_r < 100 else "XLARGE"))
        if len(mid) >= 1:
            mm = float(mid.iloc[-1]["Close"]) - float(mid.iloc[0]["Open"])
            st["mid_dir"] = "BULL" if mm > 10 else ("BEAR" if mm < -10 else "FLAT")
        if len(h1) >= 1:
            hm = float(h1.iloc[-1]["Close"]) - float(h1.iloc[0]["Open"])
            st["h1_dir"] = "BULL" if hm > 10 else ("BEAR" if hm < -10 else "FLAT")
        if len(pm) >= 2:
            pm_m = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"])
            st["pm_dir"] = "BULL" if pm_m > 15 else ("BEAR" if pm_m < -15 else "FLAT")
        day_st[day] = st
    except: pass

print(f"  {len(day_st)} dias ok")

DAYS = [(0,"LUNES"),(1,"MARTES"),(2,"MIERCOLES"),(3,"JUEVES"),(4,"VIERNES")]

def get_df(wd, since=None):
    rows = []
    for day, st in day_st.items():
        if st.get("wd") != wd: continue
        if since and day < since: continue
        if "ny_dir" not in st: continue
        rows.append(st)
    return pd.DataFrame(rows)

def acc(df, feat, val, ny_dir):
    sub = df[df.get(feat, pd.Series()) == val] if feat in df.columns else pd.DataFrame()
    if len(sub) < 3: return None, 0
    return pct((sub["ny_dir"] == ny_dir).sum(), len(sub)), len(sub)

# ── ANÁLISIS POR DÍA Y PERIODO ────────────────────────────────
print()
print("=" * 70)
print("  COMPARATIVA: OR BEAR -> NY BEAR por dia y periodo")
print("=" * 70)
print(f"\n  Dia          9 ANOS          2 ANOS          1 ANO")
print(f"  {'-'*60}")

for wd, dname in DAYS:
    df_9y = get_df(wd)
    df_2y = get_df(wd, cutoff_2y)
    df_1y = get_df(wd, cutoff_1y)

    def row_stat(df):
        if "or_dir" not in df.columns or len(df) == 0: return "  —  ", 0
        sub = df[df["or_dir"] == "BEAR"]
        if len(sub) < 3: return "  —  ", 0
        p = pct((sub["ny_dir"] == "BEAR").sum(), len(sub))
        flag = " OK" if p >= 65 else (" ~~" if p >= 55 else "   ")
        return f"{p:>4.0f}%{flag}(n={len(sub)})", len(sub)

    r9, n9 = row_stat(df_9y)
    r2, n2 = row_stat(df_2y)
    r1, n1 = row_stat(df_1y)
    print(f"  {dname:<12} {r9:<18} {r2:<18} {r1}")

print()
print("=" * 70)
print("  OR BULL -> NY BULL por dia y periodo")
print("=" * 70)
print(f"\n  Dia          9 ANOS          2 ANOS          1 ANO")
print(f"  {'-'*60}")

for wd, dname in DAYS:
    df_9y = get_df(wd)
    df_2y = get_df(wd, cutoff_2y)
    df_1y = get_df(wd, cutoff_1y)

    def row_bull(df):
        if "or_dir" not in df.columns or len(df) == 0: return "  —  ", 0
        sub = df[df["or_dir"] == "BULL"]
        if len(sub) < 3: return "  —  ", 0
        p = pct((sub["ny_dir"] == "BULL").sum(), len(sub))
        flag = " OK" if p >= 65 else (" ~~" if p >= 55 else "   ")
        return f"{p:>4.0f}%{flag}(n={len(sub)})", len(sub)

    r9, _ = row_bull(df_9y)
    r2, _ = row_bull(df_2y)
    r1, _ = row_bull(df_1y)
    print(f"  {dname:<12} {r9:<18} {r2:<18} {r1}")

# ── OR SIZE XLARGE especifico ─────────────────────────────────
print()
print("=" * 70)
print("  OR MUY GRANDE (>100pts) -> efectividad por periodo")
print("=" * 70)
print(f"\n  Dia         Dir   9 ANOS          2 ANOS          1 ANO")
print(f"  {'-'*65}")

for wd, dname in DAYS:
    for signal_dir, ny_dir in [("BEAR","BEAR"),("BULL","BULL")]:
        df_9y = get_df(wd)
        df_2y = get_df(wd, cutoff_2y)
        df_1y = get_df(wd, cutoff_1y)

        def xlarge_stat(df):
            if "or_size" not in df.columns: return "  —  "
            sub = df[(df["or_size"] == "XLARGE") & (df["or_dir"] == signal_dir)]
            if len(sub) < 3: return f"  — (n={len(sub)})"
            p = pct((sub["ny_dir"] == ny_dir).sum(), len(sub))
            flag = " OK" if p >= 70 else "   "
            return f"{p:>4.0f}%{flag}(n={len(sub)})"

        r9 = xlarge_stat(df_9y)
        r2 = xlarge_stat(df_2y)
        r1 = xlarge_stat(df_1y)
        print(f"  {dname:<10} {signal_dir:<5} {r9:<18} {r2:<18} {r1}")

# ── MIDDAY SIGNAL por periodo ─────────────────────────────────
print()
print("=" * 70)
print("  MIDDAY (12-13h) por dia y periodo")
print("=" * 70)
print(f"\n  Dia         Sig   9 ANOS          2 ANOS          1 ANO")
print(f"  {'-'*65}")

for wd, dname in DAYS:
    for signal_dir, ny_dir in [("BULL","BULL"),("BEAR","BEAR")]:
        df_9y = get_df(wd)
        df_2y = get_df(wd, cutoff_2y)
        df_1y = get_df(wd, cutoff_1y)

        def mid_stat(df):
            if "mid_dir" not in df.columns: return "  —  "
            sub = df[df["mid_dir"] == signal_dir]
            if len(sub) < 4: return f"  — (n={len(sub)})"
            p = pct((sub["ny_dir"] == ny_dir).sum(), len(sub))
            flag = " OK" if p >= 65 else (" ~~" if p >= 57 else "   ")
            return f"{p:>4.0f}%{flag}(n={len(sub)})"

        r9 = mid_stat(df_9y)
        r2 = mid_stat(df_2y)
        r1 = mid_stat(df_1y)
        if r9 != "  —  " or r2 != "  —  ":
            print(f"  {dname:<10} {signal_dir:<5} {r9:<18} {r2:<18} {r1}")

# ── RESUMEN FINAL ─────────────────────────────────────────────
print()
print("=" * 70)
print("  RESUMEN — Tendencia de cada senyals (mejora o empeora?)")
print("=" * 70)
print()
print("  Regla               9Y    2Y    1Y    Tendencia")
print("  " + "-" * 55)

summary = []
checks = [
    (0, "LUNES OR BEAR",    "or_dir", "BEAR", "ny_dir", "BEAR"),
    (1, "MARTES OR BEAR",   "or_dir", "BEAR", "ny_dir", "BEAR"),
    (1, "MARTES OR BULL",   "or_dir", "BULL", "ny_dir", "BULL"),
    (2, "MIER OR BEAR",     "or_dir", "BEAR", "ny_dir", "BEAR"),
    (2, "MIER MIDDAY BULL", "mid_dir","BULL", "ny_dir", "BULL"),
    (3, "JUEVES OR BEAR",   "or_dir", "BEAR", "ny_dir", "BEAR"),
    (3, "JUEVES MID BEAR",  "mid_dir","BEAR", "ny_dir", "BEAR"),
    (4, "VIE OR BEAR",      "or_dir", "BEAR", "ny_dir", "BEAR"),
    (4, "VIE OR BULL",      "or_dir", "BULL", "ny_dir", "BULL"),
]

for wd, label, feat, fval, tgt, tval in checks:
    def calc(df):
        if feat not in df.columns: return None, 0
        sub = df[df[feat] == fval]
        if len(sub) < 3: return None, len(sub)
        return pct((sub[tgt] == tval).sum(), len(sub)), len(sub)

    df_9y = get_df(wd); df_2y = get_df(wd, cutoff_2y); df_1y = get_df(wd, cutoff_1y)
    p9, n9 = calc(df_9y); p2, n2 = calc(df_2y); p1, n1 = calc(df_1y)

    if p9 is None: continue
    p2s = f"{p2:.0f}%" if p2 else " — "
    p1s = f"{p1:.0f}%" if p1 else " — "

    if p1 and p9:
        diff = p1 - p9
        trend = "SUBIENDO  +" if diff > 5 else ("BAJANDO   -" if diff < -5 else "ESTABLE    ")
        trend_icon = "^^" if diff > 5 else ("vv" if diff < -5 else "==")
    else:
        trend = "poco datos"; trend_icon = "??"

    print(f"  {label:<20} {p9:>4.0f}% {p2s:>5} {p1s:>5}   {trend_icon} {trend}")

print()
print("  Leyenda: OK = senyals >=65%, ~~ = moderado, -- = sin edge")
print()
