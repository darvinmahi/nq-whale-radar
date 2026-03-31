"""
Daily Bias Analysis — NQ Futures (NQ=F)
¿Qué días son BULLISH y qué días son BEARISH?
Métricas:
  1. % sesiones que cierran arriba del open (green candle)
  2. Promedio de puntos ganados/perdidos por día
  3. % que contribuye al High semanal (già calculado)
  4. "Gap up" por día (open vs prev close)
"""
import yfinance as yf
import pandas as pd
import collections

# ─── Descargar 3 años para más muestra ──────────────────────────────────────
print("📥 Descargando 3 años NQ=F (diario)...")
df = yf.Ticker("NQ=F").history(period="3y", interval="1d")
df.index = pd.to_datetime(df.index)
df = df[df["High"] > 0].copy()
df["weekday"]   = df.index.day_name()
df["daynum"]    = df.index.dayofweek          # 0=Mon, 4=Fri
df["move_pts"]  = df["Close"] - df["Open"]   # positivo = bullish
df["move_pct"]  = df["move_pts"] / df["Open"] * 100
df["is_bull"]   = df["move_pts"] > 0
df["prev_close"]= df["Close"].shift(1)
df["gap_pts"]   = df["Open"] - df["prev_close"]  # gap vs cierre anterior

ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
EMO   = ["🟡", "🔵", "⚪", "🟠", "🟢"]   # colores por día

print(f"✅ Datos: {df.index[0].date()} → {df.index[-1].date()} | {len(df)} sesiones\n")

# ─── Estadísticas por día ─────────────────────────────────────────────────────
stats = {}
for d in ORDER:
    sub = df[df["weekday"] == d]
    bull_rate = sub["is_bull"].mean() * 100
    avg_move  = sub["move_pts"].mean()
    avg_gap   = sub["gap_pts"].mean()
    win_days  = (sub["is_bull"].sum())
    total_d   = len(sub)
    stats[d] = {
        "total":     total_d,
        "bull_pct":  bull_rate,
        "avg_move":  avg_move,
        "avg_gap":   avg_gap,
        "wins":      win_days,
    }

# Weekly high/low por día (usando mismos datos)
df["week_id"] = df.index.isocalendar().week.astype(str) + "_" + df.index.year.astype(str)
high_day_counts = collections.Counter()
low_day_counts  = collections.Counter()
for wid, grp in df.groupby("week_id"):
    if len(grp) < 3: continue
    high_day_counts[grp.loc[grp["High"].idxmax(), "weekday"]] += 1
    low_day_counts[grp.loc[grp["Low"].idxmin(),  "weekday"]] += 1
total_weeks = sum(high_day_counts.values())

# ─── Output principal ─────────────────────────────────────────────────────────
print("=" * 72)
print("  📊 SESGO POR DÍA — NQ FUTURES (3 años · sesión diaria)")
print("=" * 72)
hdr = f"{'Día':<12} {'SESGO':^10} {'Bull%':>6} {'AvgPts':>8} {'AvgGap':>8} {'WeekHigh%':>10} {'WeekLow%':>9}"
print(hdr)
print("-" * 72)

for i, d in enumerate(ORDER):
    s     = stats[d]
    bp    = s["bull_pct"]
    ap    = s["avg_move"]
    gap   = s["avg_gap"]
    wh    = high_day_counts.get(d, 0) / total_weeks * 100
    wl    = low_day_counts.get(d, 0) / total_weeks * 100

    if bp >= 55:
        sesgo = "🟢 BULL "
    elif bp <= 45:
        sesgo = "🔴 BEAR "
    else:
        sesgo = "⚪ NEUTRO"

    sign_ap = "+" if ap >= 0 else ""
    sign_gp = "+" if gap >= 0 else ""
    print(f"{EMO[i]} {d:<10} {sesgo:^10}  {bp:>5.1f}%  {sign_ap}{ap:>6.1f}  {sign_gp}{gap:>6.1f}  {wh:>8.1f}%  {wl:>7.1f}%")

print()
print("=" * 72)
print("  LEYENDA: Bull% = % sesiones que cierran arriba del open")
print("           AvgPts = movimiento promedio (Close - Open)")
print("           AvgGap = gap promedio vs cierre anterior")
print("           WeekHigh% = frecuencia de ser el máximo semanal")
print("           WeekLow%  = frecuencia de ser el mínimo semanal")
print("=" * 72)

# ─── Resumen para estrategia ─────────────────────────────────────────────────
print()
print("▶ ESTRATEGIA RECOMENDADA:")
bulls = [d for d in ORDER if stats[d]["bull_pct"] >= 52]
bears = [d for d in ORDER if stats[d]["bull_pct"] < 48]
print(f"  ✅ Días BULLISH (buscar LONGS): {', '.join(bulls) if bulls else 'Ninguno claro'}")
print(f"  ❌ Días BEARISH (buscar SHORTS o evitar): {', '.join(bears) if bears else 'Ninguno claro'}")
