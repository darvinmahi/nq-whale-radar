"""
PATRON 40 JUEVES — Metodología NQ
=====================================
VP Profile : Asia (18:00 ET miércoles) → 9:20 ET jueves
Spike      : 8:30-8:44 ET (Jobless Claims)
NY Sesión  : 9:30-16:00 ET
BULL       : NY move > +50 pts
BEAR       : NY move < -50 pts
FLAT       : entre -50 y +50 pts
Trampa     : Spike alcista (>+20) + día BEAR
"""

import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

ET       = pytz.timezone("America/New_York")
CSV      = "data/research/nq_15m_intraday.csv"
VP_BINS  = 50

# ── Cargar CSV ────────────────────────────────────────────────────────────────
df = pd.read_csv(CSV, index_col=0, parse_dates=True)
df.index = pd.to_datetime(df.index, utc=True).tz_convert(ET)
df = df.sort_index()
df.columns = [c.strip() for c in df.columns]

# ── Jueves disponibles ────────────────────────────────────────────────────────
all_days = df.index.normalize().unique()
thursdays = sorted([d for d in all_days if d.weekday() == 3])
last_40   = [t for t in thursdays[-40:] if len(df[df.index.normalize() == t]) >= 50]
print(f"Jueves válidos (últimos 40): {len(last_40)}\n")

# ── Volume Profile ────────────────────────────────────────────────────────────
def calc_vp(sl):
    if sl.empty or len(sl) < 2:
        return None, None, None
    lo, hi = sl["Low"].min(), sl["High"].max()
    if hi == lo:
        return None, None, None
    edges   = np.linspace(lo, hi, VP_BINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols    = np.zeros(VP_BINS)
    for _, row in sl.iterrows():
        mask = (centers >= float(row["Low"])) & (centers <= float(row["High"]))
        cnt  = mask.sum()
        if cnt > 0:
            vols[mask] += 1.0 / cnt
    poc_idx = int(np.argmax(vols))
    poc     = centers[poc_idx]
    total   = vols.sum(); target = total * 0.70
    lo_i = hi_i = poc_idx; accum = vols[poc_idx]
    while accum < target and (lo_i > 0 or hi_i < VP_BINS - 1):
        la = vols[lo_i-1] if lo_i > 0 else 0
        ha = vols[hi_i+1] if hi_i < VP_BINS-1 else 0
        if la >= ha and lo_i > 0:
            lo_i -= 1; accum += la
        elif hi_i < VP_BINS - 1:
            hi_i += 1; accum += ha
        else:
            break
    return centers[hi_i], poc, centers[lo_i]  # VAH, POC, VAL

# ── Analizar cada jueves ──────────────────────────────────────────────────────
results = []
pattern_counts = {
    "BULL_sobre_VAH": 0, "BULL_desde_POC": 0, "BULL_rebote_VAL": 0,
    "BEAR_bajo_VAL":  0, "BEAR_desde_POC": 0, "BEAR_falla_VAH": 0,
    "TRAMPA_spike_bull": 0, "TRAMPA_spike_bear": 0,
    "SPIKE_bull_y_NY_bull": 0, "SPIKE_bear_y_NY_bear": 0,
    "FLAT": 0,
}

for thu in last_40:
    day_date = thu.date()
    prev     = thu - timedelta(days=1)

    # Ventana completa del día
    day_df = df[df.index.normalize() == thu]

    # VP: desde 18:00 ET del miércoles hasta 9:20 ET del jueves
    try:
        start_vp = ET.localize(datetime(prev.year, prev.month, prev.day, 18, 0))
        end_vp   = ET.localize(datetime(thu.year,  thu.month,  thu.day,  9, 20))
        vp_df    = df[(df.index >= start_vp) & (df.index <= end_vp)]
    except Exception:
        vp_df = pd.DataFrame()

    vah, poc, val = calc_vp(vp_df)

    # Spike 8:30-8:44 ET
    spike_df = day_df[(day_df.index.hour == 8) & (day_df.index.minute.isin([30,45]))]
    pre_df   = day_df[(day_df.index.hour == 8) & (day_df.index.minute < 30)]
    spike_move = 0
    if not spike_df.empty and not pre_df.empty:
        spike_move = round(float(spike_df.iloc[-1]["Close"]) - float(pre_df.iloc[-1]["Close"]), 0)
    spike_dir = "UP" if spike_move > 20 else ("DOWN" if spike_move < -20 else "FLAT")

    # NY 9:30-16:00 ET
    ny_df = day_df[(day_df.index.hour >= 9) & 
                   ~((day_df.index.hour == 9) & (day_df.index.minute < 30)) &
                   (day_df.index.hour < 16)]
    if len(ny_df) < 4:
        continue

    ny_open  = float(ny_df.iloc[0]["Open"])
    ny_high  = float(ny_df["High"].max())
    ny_low   = float(ny_df["Low"].min())
    ny_close = float(ny_df.iloc[-1]["Close"])
    ny_move  = round(ny_close - ny_open, 0)
    ny_range = round(ny_high - ny_low, 0)

    if ny_move > 50:
        ny_dir = "BULL"
    elif ny_move < -50:
        ny_dir = "BEAR"
    else:
        ny_dir = "FLAT"

    # ── Detectar patrones VP ──────────────────────────────────────────────────
    patron = []
    if poc and vah and val:
        if ny_dir == "BULL":
            if ny_open > vah:
                patron.append("BULL_sobre_VAH")
                pattern_counts["BULL_sobre_VAH"] += 1
            elif val <= ny_open <= vah:
                patron.append("BULL_desde_POC")
                pattern_counts["BULL_desde_POC"] += 1
            elif ny_open < val:
                patron.append("BULL_rebote_VAL")
                pattern_counts["BULL_rebote_VAL"] += 1
        elif ny_dir == "BEAR":
            if ny_open < val:
                patron.append("BEAR_bajo_VAL")
                pattern_counts["BEAR_bajo_VAL"] += 1
            elif val <= ny_open <= vah:
                patron.append("BEAR_desde_POC")
                pattern_counts["BEAR_desde_POC"] += 1
            elif ny_open > vah:
                patron.append("BEAR_falla_VAH")
                pattern_counts["BEAR_falla_VAH"] += 1
        else:
            pattern_counts["FLAT"] += 1
            patron.append("FLAT")

    # ── Trampa Spike ──────────────────────────────────────────────────────────
    if spike_dir == "UP" and ny_dir == "BEAR":
        patron.append("TRAMPA_spike_bull")
        pattern_counts["TRAMPA_spike_bull"] += 1
    elif spike_dir == "DOWN" and ny_dir == "BULL":
        patron.append("TRAMPA_spike_bear")
        pattern_counts["TRAMPA_spike_bear"] += 1
    elif spike_dir == "UP" and ny_dir == "BULL":
        pattern_counts["SPIKE_bull_y_NY_bull"] += 1
    elif spike_dir == "DOWN" and ny_dir == "BEAR":
        pattern_counts["SPIKE_bear_y_NY_bear"] += 1

    results.append({
        "Date":        str(day_date),
        "VAH":         round(vah, 2) if vah else None,
        "POC":         round(poc, 2) if poc else None,
        "VAL":         round(val, 2) if val else None,
        "NY_Open":     round(ny_open, 2),
        "NY_Close":    round(ny_close, 2),
        "NY_Move":     ny_move,
        "NY_Range":    ny_range,
        "Spike":       spike_move,
        "Spike_Dir":   spike_dir,
        "NY_Dir":      ny_dir,
        "Patrones":    ", ".join(patron) if patron else "-",
        "NY_vs_VAH":   round(ny_open - vah, 1) if vah else None,
        "NY_vs_POC":   round(ny_open - poc, 1) if poc else None,
    })

# ── Mostrar tabla ─────────────────────────────────────────────────────────────
res = pd.DataFrame(results)
pd.set_option("display.max_columns", 20)
pd.set_option("display.width", 160)
pd.set_option("display.max_rows", 50)

print("=" * 130)
print("TABLA COMPLETA — 40 JUEVES MÁS RECIENTES")
print("=" * 130)
cols_show = ["Date","POC","VAH","VAL","NY_Open","NY_Move","NY_Range","Spike","Spike_Dir","NY_Dir","Patrones"]
print(res[cols_show].to_string(index=False))

n   = len(res)
bull = (res["NY_Dir"] == "BULL").sum()
bear = (res["NY_Dir"] == "BEAR").sum()
flat = (res["NY_Dir"] == "FLAT").sum()

print("\n" + "=" * 80)
print("RESUMEN ESTADÍSTICO")
print("=" * 80)
print(f"  Total jueves analizados : {n}")
print(f"  BULL (NY_move > +50)    : {bull:2d} ({bull/n*100:.0f}%)")
print(f"  BEAR (NY_move < -50)    : {bear:2d} ({bear/n*100:.0f}%)")
print(f"  FLAT                    : {flat:2d} ({flat/n*100:.0f}%)")
print(f"  Rango NY promedio       : {res['NY_Range'].mean():.1f} pts")
print(f"  Rango NY mediana        : {res['NY_Range'].median():.1f} pts")

print("\n── PATRONES VP MÁS FRECUENTES ──────────────────────")
patron_rows = [
    ("BULL abre sobre VAH (tendencia)",      pattern_counts["BULL_sobre_VAH"]),
    ("BULL desde zona POC/Valor",            pattern_counts["BULL_desde_POC"]),
    ("BULL rebote desde VAL (soportado)",    pattern_counts["BULL_rebote_VAL"]),
    ("BEAR abre bajo VAL (debilidad)",       pattern_counts["BEAR_bajo_VAL"]),
    ("BEAR desde zona POC/Valor",            pattern_counts["BEAR_desde_POC"]),
    ("BEAR falla VAH (rechazo)",             pattern_counts["BEAR_falla_VAH"]),
    ("FLAT (sin dirección clara)",           pattern_counts["FLAT"]),
]
for nombre, cnt in sorted(patron_rows, key=lambda x: -x[1]):
    pct = cnt/n*100
    bar = "█" * cnt
    print(f"  {nombre:<40} : {cnt:2d} ({pct:.0f}%)  {bar}")

print("\n── FIABILIDAD SPIKE CLAIMS ──────────────────────────")
s_bull_bull = pattern_counts["SPIKE_bull_y_NY_bull"]
s_bull_bear = pattern_counts["TRAMPA_spike_bull"]
s_bear_bear = pattern_counts["SPIKE_bear_y_NY_bear"]
s_bear_bull = pattern_counts["TRAMPA_spike_bear"]
total_up   = s_bull_bull + s_bull_bear
total_down = s_bear_bear + s_bear_bull
print(f"  Spike ↑ → día BULL (confirmado) : {s_bull_bull:2d}  /  Trampa (día BEAR): {s_bull_bear:2d}  → fiabilidad {s_bull_bull/total_up*100:.0f}%" if total_up else "  Spike UP: sin datos")
print(f"  Spike ↓ → día BEAR (confirmado) : {s_bear_bear:2d}  /  Trampa (día BULL): {s_bear_bull:2d}  → fiabilidad {s_bear_bear/total_down*100:.0f}%" if total_down else "  Spike DOWN: sin datos")

print("\n── TOP 5 PATRONES POR BULL/BEAR ─────────────────────")
print("  BULL dias por posición respecto VP:")
bull_df = res[res["NY_Dir"]=="BULL"]
if not bull_df.empty and "NY_vs_VAH" in bull_df.columns:
    above_vah = (bull_df["NY_vs_VAH"] >= 0).sum()
    in_value  = ((bull_df["NY_vs_VAH"] < 0) & (bull_df["NY_vs_POC"] >= 0)).sum()
    below_poc = (bull_df["NY_vs_POC"] < 0).sum() if "NY_vs_POC" in bull_df else 0
    print(f"    Abrió sobre VAH  : {above_vah} ({above_vah/bull:.0%})")
    print(f"    Abrió POC-VAH    : {in_value}  ({in_value/bull:.0%})")
    print(f"    Abrió bajo POC   : {below_poc} ({below_poc/bull:.0%})")

print("  BEAR dias por posición respecto VP:")
bear_df = res[res["NY_Dir"]=="BEAR"]
if not bear_df.empty and "NY_vs_VAH" in bear_df.columns:
    above_vah = (bear_df["NY_vs_VAH"] >= 0).sum()
    in_value  = ((bear_df["NY_vs_VAH"] < 0) & (bear_df["NY_vs_POC"] >= 0)).sum()
    below_poc = (bear_df["NY_vs_POC"] < 0).sum() if "NY_vs_POC" in bear_df else 0
    print(f"    Abrió sobre VAH  : {above_vah} ({above_vah/bear:.0%})")
    print(f"    Abrió POC-VAH    : {in_value}  ({in_value/bear:.0%})")
    print(f"    Abrió bajo POC   : {below_poc} ({below_poc/bear:.0%})")

print("\nDone.")
