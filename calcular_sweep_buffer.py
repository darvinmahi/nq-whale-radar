"""
SWEEP EXTENSION CALCULATOR — Últimos 12 Lunes NQ
Medición real de cuántos puntos fue el sweep beyond Range H/L
"""

import yfinance as yf
import pandas as pd

print("📥 Descargando datos...")

nq15 = yf.download("QQQ", period="60d", interval="15m", auto_adjust=True, progress=False)
vxn_d = yf.download("^VXN", period="60d", auto_adjust=True, progress=False)

# Fix multi-index
def get_col(frame, col):
    if isinstance(frame.columns, pd.MultiIndex):
        return frame[col].iloc[:, 0]
    return frame[col]

# Normalize timestamps to ET (UTC-4/5)
# Yahoo 15m data comes in UTC or local, convert to ET
if nq15.index.tz is not None:
    nq15.index = nq15.index.tz_convert("America/New_York").tz_localize(None)
else:
    # Assume UTC, shift to ET (approx -4h)
    nq15.index = pd.to_datetime(nq15.index) - pd.Timedelta(hours=4)

if vxn_d.index.tz is not None:
    vxn_d.index = vxn_d.index.tz_localize(None)
vxn_close = get_col(vxn_d, "Close")

# Debug: show what days we have
print(f"\nDatos 15min: {nq15.index[0]} → {nq15.index[-1]}")
print(f"Total barras: {len(nq15)}")

all_dates = sorted(set(nq15.index.date))
day_counts = {d: 0 for d in all_dates}
for d in nq15.index.date:
    day_counts[d] += 1

lunes_dates = [d for d in all_dates if pd.Timestamp(d).weekday() == 0]
print(f"Lunes encontrados: {len(lunes_dates)} → {[str(d) for d in lunes_dates]}")

if len(lunes_dates) == 0:
    print("❌ 0 lunes detectados. Mostrando días presentes:")
    for d in all_dates[-5:]:
        print(f"  {d} → weekday={pd.Timestamp(d).weekday()}")

nq_open15  = get_col(nq15, "Open")
nq_high15  = get_col(nq15, "High")
nq_low15   = get_col(nq15, "Low")
nq_close15 = get_col(nq15, "Close")

results = []

for lunes in lunes_dates:
    lunes_ts = pd.Timestamp(lunes)

    # VXN del día hábil previo al lunes
    vxn_before = vxn_close[vxn_close.index < lunes_ts]
    if len(vxn_before) == 0:
        continue
    vxn_prev = float(vxn_before.iloc[-1])

    # Barras del lunes
    day_bars = nq15[nq15.index.date == lunes]
    if len(day_bars) < 5:
        continue

    # Pre-NY: antes de 09:30 ET
    pre_ny_bars = day_bars[day_bars.index.hour < 9]
    if len(pre_ny_bars) < 2:
        # Tomar primero 30% del día
        pre_ny_bars = day_bars.iloc[:max(2, len(day_bars)//3)]

    # Range de pre-NY
    range_h = float(nq_high15[pre_ny_bars.index].max())
    range_l = float(nq_low15[pre_ny_bars.index].min())
    range_size = range_h - range_l

    # NY: 09:30–11:30 ET
    ny_bars = day_bars[
        ((day_bars.index.hour == 9) & (day_bars.index.minute >= 30)) |
        (day_bars.index.hour == 10) |
        ((day_bars.index.hour == 11) & (day_bars.index.minute <= 30))
    ]

    if len(ny_bars) < 2:
        ny_bars = day_bars.iloc[len(pre_ny_bars):]

    if len(ny_bars) == 0:
        continue

    ny_high      = float(nq_high15[ny_bars.index].max())
    ny_low       = float(nq_low15[ny_bars.index].min())
    ny_close_val = float(nq_close15[ny_bars.index].iloc[-1])
    ny_open_val  = float(nq_open15[ny_bars.index].iloc[0])

    # SWEEP: cuánto fue MÁS ALLÁ del range
    sweep_h = max(0.0, ny_high - range_h)
    sweep_l = max(0.0, range_l - ny_low)

    if sweep_h > sweep_l and sweep_h > 0.0:
        pattern   = "SWEEP_H"
        sweep_pts = round(sweep_h, 2)
        returned  = ny_close_val < range_h
    elif sweep_l > sweep_h and sweep_l > 0.0:
        pattern   = "SWEEP_L"
        sweep_pts = round(sweep_l, 2)
        returned  = ny_close_val > range_l
    else:
        pattern   = "EXPANSION"
        sweep_pts = 0.0
        returned  = True

    total_pct = (ny_close_val - ny_open_val) / ny_open_val * 100
    resultado = "BULLISH" if total_pct > 0.15 else ("BEARISH" if total_pct < -0.15 else "FLAT")

    if vxn_prev >= 33:   zona = "XFEAR >33"
    elif vxn_prev >= 25: zona = "FEAR 25-33"
    elif vxn_prev >= 18: zona = "NEUTRAL 18-25"
    else:                zona = "GREED <18"

    results.append({
        "Lunes":    lunes_ts.strftime("%Y-%m-%d"),
        "VXN":      round(vxn_prev, 1),
        "Zona":     zona,
        "Rng_H":    round(range_h, 2),
        "Rng_L":    round(range_l, 2),
        "Rng_Size": round(range_size, 2),
        "NY_H":     round(ny_high, 2),
        "NY_L":     round(ny_low, 2),
        "Patron":   pattern,
        "Sweep":    sweep_pts,
        "Returned": "✅" if returned else "❌",
        "Dir":      resultado,
        "Mov%":     round(total_pct, 2),
    })

if not results:
    print("❌ Sin resultados válidos.")
    exit()

df = pd.DataFrame(results).sort_values("Lunes", ascending=False)
print(f"\n✅ {len(df)} lunes procesados")

# ─── TABLA COMPLETA ───
print("\n" + "═"*95)
print("  SWEEP EXTENSION — ÚLTIMOS LUNES NQ (QQQ proxy 15min)")
print("  Sweep = cuántos pts fue el sweep más allá del Range High/Low")
print("═"*95)
print(f"{'Lunes':<12} {'VXN':>5} {'Zona':<15} {'RngSz':>6} {'PatrOn':<12} {'Sweep':>7} {'Volvió':>7} {'Dir':>8}")
print("─"*95)
for _, r in df.iterrows():
    print(f"{r['Lunes']:<12} {r['VXN']:>5} {r['Zona']:<15} {r['Rng_Size']:>6.2f} "
          f"{r['Patron']:<12} {r['Sweep']:>7.2f} {r['Returned']:>7} {r['Dir']:>8}")

# ─── BUFFER POR ZONA VXN ───
print("\n" + "═"*60)
print("  BUFFER RECOMENDADO POR ZONA VXN (en puntos QQQ/NQ proxy)")
print("═"*60)
for zona in ["XFEAR >33", "FEAR 25-33", "NEUTRAL 18-25", "GREED <18"]:
    sub = df[df["Zona"] == zona]
    if len(sub) == 0:
        continue
    avg_sw = sub["Sweep"].mean()
    max_sw = sub["Sweep"].max()
    p75_sw = sub["Sweep"].quantile(0.75)
    n = len(sub)
    buf = max(0.3, round(p75_sw * 1.3, 2))
    print(f"  {zona:<15} n={n}  avg={avg_sw:.2f}  p75={p75_sw:.2f}  max={max_sw:.2f}  → Buffer: {buf:.2f} pts")

# ─── ANÁLISIS ESPECÍFICO MAÑANA LUNES VXN 33.5 ───
print("\n" + "═"*60)
print("  ⚠️  MAÑANA LUNES 31 MAR — VXN ~33.5 (ZONA XFEAR)")
print("═"*60)
xfear = df[df["VXN"] >= 30]  # ampliar a >30 si <3 datos con >33
fear_p = df[df["VXN"] >= 25]
if len(xfear) > 0:
    avg = xfear["Sweep"].mean()
    mx  = xfear["Sweep"].max()
    p75 = xfear["Sweep"].quantile(0.75)
    buf = max(0.4, round(p75 * 1.5, 2))
    print(f"  Lunes con VXN≥30: n={len(xfear)}")
    print(f"  Sweep promedio:   {avg:.2f} pts (QQQ)")
    print(f"  Sweep máximo:     {mx:.2f} pts")
    print(f"  Sweep p75:        {p75:.2f} pts")
    print(f"  Buffer sugerido:  {buf:.2f} pts QQQ")
    # Conversión aproximada QQQ → NQ futures (NQ ≈ QQQ × 7.5 pts/1pt)
    nq_buf = round(buf * 7.5, 0)
    nq_avg = round(avg * 7.5, 0)
    nq_max = round(mx  * 7.5, 0)
    print(f"\n  ─── CONVERSIÓN A NQ FUTURES (×7.5 aprox) ───")
    print(f"  Sweep promedio NQ: ~{nq_avg:.0f} pts")
    print(f"  Sweep máximo NQ:   ~{nq_max:.0f} pts")
    print(f"  Buffer seguro NQ:  ~{nq_buf:.0f} pts")
    print(f"\n  REGLA MAÑANA:")
    print(f"  - Range High/Low definido antes de 09:30 ET")
    print(f"  - Si hay sweep: esperar que vuelva AL RANGO (cierre vela 15min dentro)")
    print(f"  - NO entrar en el pico del sweep — puede ir {nq_buf:.0f}+ pts más")
    print(f"  - Entry SOLO cuando price regresa y cierra bajo Range_H o sobre Range_L")
