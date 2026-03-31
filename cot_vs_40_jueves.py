"""
COT INDEX × 40 JUEVES MÁS RECIENTES
VP Asia→9:20 ET | NY 9:30-16:00 ET | BULL>+50 BEAR<-50
"""
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, timedelta

ET      = pytz.timezone("America/New_York")
CSV_PX  = "data/research/nq_15m_intraday.csv"
CSV_COT = "data/cot/nasdaq_cot_historical.csv"
VP_BINS = 50
LOOKBACK = 52   # semanas para calcular COT Index %

# ── Cargar precio ─────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_PX, index_col=0, parse_dates=True)
df.index = pd.to_datetime(df.index, utc=True).tz_convert(ET)
df = df.sort_index()

# ── Cargar COT ────────────────────────────────────────────────────────────────
cot_raw = pd.read_csv(CSV_COT)
# Detectar columna fecha
date_col = [c for c in cot_raw.columns if 'Date' in c or 'date' in c][0]
cot_raw[date_col] = pd.to_datetime(cot_raw[date_col], errors='coerce')
cot_raw = cot_raw.dropna(subset=[date_col]).sort_values(date_col)

# Detectar columnas long/short non-commercial o asset manager
long_col  = [c for c in cot_raw.columns if 'Long'  in c and ('NonComm' in c or 'Asset' in c or 'Mgr' in c)][0]
short_col = [c for c in cot_raw.columns if 'Short' in c and ('NonComm' in c or 'Asset' in c or 'Mgr' in c)][0]

cot = cot_raw[[date_col, long_col, short_col]].copy()
cot.columns = ['Date', 'Long', 'Short']
cot['Net'] = cot['Long'] - cot['Short']

# COT Index (percentil 52 semanas)
cot['COT_raw_index'] = cot['Net'].rolling(LOOKBACK).apply(
    lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) * 100
    if (x.max() - x.min()) > 0 else 50
)

def cot_regime(v):
    if pd.isna(v):  return "SIN_DATO"
    if v <= 30:     return "LARGO"       # Comerciales/Asset Mgr muy largos → bullish
    if v >= 70:     return "CORTO"       # Comerciales/Asset Mgr muy cortos → bearish
    return "NEUTRO"

cot['Regime'] = cot['COT_raw_index'].apply(cot_regime)
print(f"COT cargado: {cot['Date'].min().date()} → {cot['Date'].max().date()}")
print(f"Columnas usadas: Net = {long_col} - {short_col}\n")

# ── VP helper ─────────────────────────────────────────────────────────────────
def calc_vp(sl):
    if sl.empty or len(sl) < 2: return None, None, None
    lo, hi = sl["Low"].min(), sl["High"].max()
    if hi == lo: return None, None, None
    edges = np.linspace(lo, hi, VP_BINS + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols = np.zeros(VP_BINS)
    for _, row in sl.iterrows():
        mask = (centers >= float(row["Low"])) & (centers <= float(row["High"]))
        cnt = mask.sum()
        if cnt > 0: vols[mask] += 1.0 / cnt
    poc_i = int(np.argmax(vols))
    poc = centers[poc_i]
    total = vols.sum(); target = total * 0.70
    lo_i = hi_i = poc_i; accum = vols[poc_i]
    while accum < target and (lo_i > 0 or hi_i < VP_BINS-1):
        la = vols[lo_i-1] if lo_i > 0 else 0
        ha = vols[hi_i+1] if hi_i < VP_BINS-1 else 0
        if la >= ha and lo_i > 0: lo_i -= 1; accum += la
        elif hi_i < VP_BINS-1:   hi_i += 1; accum += ha
        else: break
    return centers[hi_i], poc, centers[lo_i]

# ── 40 jueves ────────────────────────────────────────────────────────────────
all_days  = df.index.normalize().unique()
thursdays = sorted([d for d in all_days if d.weekday() == 3])
last_40   = [t for t in thursdays[-40:] if len(df[df.index.normalize() == t]) >= 50]

results = []
for thu in last_40:
    day_date = thu.date()
    prev     = thu - timedelta(days=1)

    # COT de la semana del jueves (usar semana anterior más reciente)
    cot_week = cot[cot['Date'] <= pd.Timestamp(day_date)]
    if cot_week.empty:
        cot_val, cot_reg = np.nan, "SIN_DATO"
    else:
        last_cot = cot_week.iloc[-1]
        cot_val  = last_cot['COT_raw_index']
        cot_reg  = last_cot['Regime']

    # VP Asia → 9:20 ET
    try:
        start_vp = ET.localize(datetime(prev.year, prev.month, prev.day, 18, 0))
        end_vp   = ET.localize(datetime(thu.year,  thu.month,  thu.day,  9, 20))
        vp_df    = df[(df.index >= start_vp) & (df.index <= end_vp)]
    except: vp_df = pd.DataFrame()
    vah, poc, val = calc_vp(vp_df)

    # Spike 8:30
    day_df   = df[df.index.normalize() == thu]
    spike_df = day_df[(day_df.index.hour == 8) & (day_df.index.minute >= 30) & (day_df.index.minute < 45)]
    pre_df   = day_df[(day_df.index.hour == 8) & (day_df.index.minute < 30)]
    spike_move = 0
    if not spike_df.empty and not pre_df.empty:
        spike_move = round(float(spike_df.iloc[-1]["Close"]) - float(pre_df.iloc[-1]["Close"]), 0)
    spike_dir = "UP" if spike_move > 20 else ("DOWN" if spike_move < -20 else "FLAT")

    # NY 9:30-16:00
    ny_df = day_df[(day_df.index.hour >= 9) &
                   ~((day_df.index.hour == 9) & (day_df.index.minute < 30)) &
                   (day_df.index.hour < 16)]
    if len(ny_df) < 4: continue
    ny_open  = float(ny_df.iloc[0]["Open"])
    ny_close = float(ny_df.iloc[-1]["Close"])
    ny_high  = float(ny_df["High"].max())
    ny_low   = float(ny_df["Low"].min())
    ny_move  = round(ny_close - ny_open, 0)
    ny_range = round(ny_high - ny_low, 0)
    ny_dir   = "BULL" if ny_move > 50 else ("BEAR" if ny_move < -50 else "FLAT")

    # Trampa
    trampa = ""
    if spike_dir == "UP"   and ny_dir == "BEAR": trampa = "TRAMPA↑"
    if spike_dir == "DOWN" and ny_dir == "BULL": trampa = "TRAMPA↓"

    # Posición vs VP
    pos_vp = "-"
    if poc and vah and val:
        if ny_open > vah:          pos_vp = "SOBRE_VAH"
        elif ny_open >= poc:       pos_vp = "POC-VAH"
        elif ny_open >= val:       pos_vp = "VAL-POC"
        else:                      pos_vp = "BAJO_VAL"

    results.append({
        "Date": str(day_date),
        "COT_idx": round(cot_val, 1) if not pd.isna(cot_val) else None,
        "COT_Reg": cot_reg,
        "NY_Move": ny_move,
        "NY_Range": ny_range,
        "NY_Dir": ny_dir,
        "Spike": spike_move,
        "Spike_Dir": spike_dir,
        "Pos_VP": pos_vp,
        "Trampa": trampa,
    })

res = pd.DataFrame(results)
n   = len(res)

# ── TABLA COMPLETA ────────────────────────────────────────────────────────────
print("=" * 110)
print("TABLA COMPLETA — COT × 40 JUEVES")
print("=" * 110)
print(res.to_string(index=False))

# ── ESTADÍSTICAS POR RÉGIMEN COT ──────────────────────────────────────────────
print("\n" + "=" * 80)
print("EFECTO COT EN DIRECCIÓN JUEVES")
print("=" * 80)

for reg in ["LARGO", "NEUTRO", "CORTO", "SIN_DATO"]:
    sub = res[res["COT_Reg"] == reg]
    if sub.empty: continue
    bull = (sub["NY_Dir"] == "BULL").sum()
    bear = (sub["NY_Dir"] == "BEAR").sum()
    flat = (sub["NY_Dir"] == "FLAT").sum()
    nn   = len(sub)
    trap_up  = ((sub["Trampa"] == "TRAMPA↑")).sum()
    trap_dn  = ((sub["Trampa"] == "TRAMPA↓")).sum()
    avg_rng  = sub["NY_Range"].mean()
    label = {"LARGO":"📈 LARGO (<30)","NEUTRO":"⬛ NEUTRO","CORTO":"📉 CORTO (>70)","SIN_DATO":"❓ Sin dato"}[reg]
    print(f"\n  {label}  —  {nn} jueves")
    print(f"    BULL: {bull:2d} ({bull/nn*100:.0f}%)  |  BEAR: {bear:2d} ({bear/nn*100:.0f}%)  |  FLAT: {flat:2d} ({flat/nn*100:.0f}%)")
    print(f"    Trampa ↑: {trap_up}  |  Trampa ↓: {trap_dn}")
    print(f"    Rango promedio NY: {avg_rng:.0f} pts")
    # Barras
    bar_b = "█" * bull + "░" * (nn - bull)
    bar_r = "█" * bear + "░" * (nn - bear)
    print(f"    BULL [{bar_b}]")
    print(f"    BEAR [{bar_r}]")

# ── TRAMPA POR RÉGIMEN ────────────────────────────────────────────────────────
print("\n── FIABILIDAD SPIKE + COT ───────────────────────────────────────")
for reg in ["LARGO", "NEUTRO", "CORTO"]:
    sub = res[res["COT_Reg"] == reg]
    if sub.empty: continue
    sp_up   = (sub["Spike_Dir"] == "UP").sum()
    sp_dn   = (sub["Spike_Dir"] == "DOWN").sum()
    tr_up   = (sub["Trampa"] == "TRAMPA↑").sum()
    tr_dn   = (sub["Trampa"] == "TRAMPA↓").sum()
    print(f"  {reg:8s}  Spike↑={sp_up} (Trampa:{tr_up}/{sp_up if sp_up else 1})  Spike↓={sp_dn} (Trampa:{tr_dn}/{sp_dn if sp_dn else 1})")

print("\nDone.")
