"""
Weekly High Day Analysis — NQ Futures (NQ=F)
¿Qué día de la semana tiene más frecuencia de ser el HIGH de la semana?
Período: 2 años de datos diarios
"""
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import collections

# ─── Descargar 2 años de datos diarios ──────────────────────────────────────
print("📥 Descargando datos NQ=F (2 años, diario)...")
ticker = yf.Ticker("NQ=F")
df = ticker.history(period="2y", interval="1d")
df.index = pd.to_datetime(df.index)

# Usar solo días hábiles con datos reales
df = df[df["High"] > 0].copy()
df["date"] = df.index.date
df["weekday"] = df.index.day_name()
df["week_num"] = df.index.isocalendar().week.astype(int)
df["year"]     = df.index.year

print(f"✅ Datos: {df.index[0].date()} → {df.index[-1].date()} | {len(df)} sesiones\n")

# ─── Por cada semana: ¿qué día fue el HIGH? ──────────────────────────────────
weekly_highs  = []
weekly_lows   = []

for (yr, wk), grp in df.groupby(["year", "week_num"]):
    if len(grp) < 3:          # semanas incompletas → skip
        continue
    # HIGH de la semana
    idx_h = grp["High"].idxmax()
    high_day = grp.loc[idx_h, "weekday"]
    weekly_highs.append(high_day)

    # LOW de la semana (bonus)
    idx_l = grp["Low"].idxmin()
    low_day = grp.loc[idx_l, "weekday"]
    weekly_lows.append(low_day)

# ─── Conteo y porcentaje ──────────────────────────────────────────────────────
ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
total = len(weekly_highs)

high_counts = collections.Counter(weekly_highs)
low_counts  = collections.Counter(weekly_lows)

print("=" * 56)
print(f"  📈 WEEKLY HIGH — DÍA DE LA SEMANA  ({total} semanas)")
print("=" * 56)
print(f"{'Día':<14} {'Veces':>6} {'%':>7}  {'Barra'}")
print("-" * 56)
for d in ORDER:
    cnt = high_counts.get(d, 0)
    pct = cnt / total * 100
    bar = "█" * int(pct / 2)
    print(f"{d:<14} {cnt:>6}   {pct:>5.1f}%  {bar}")

print()
print("=" * 56)
print(f"  📉 WEEKLY LOW  — DÍA DE LA SEMANA  ({total} semanas)")
print("=" * 56)
print(f"{'Día':<14} {'Veces':>6} {'%':>7}  {'Barra'}")
print("-" * 56)
for d in ORDER:
    cnt = low_counts.get(d, 0)
    pct = cnt / total * 100
    bar = "█" * int(pct / 2)
    print(f"{d:<14} {cnt:>6}   {pct:>5.1f}%  {bar}")

# ─── Top día para el High ────────────────────────────────────────────────────
top_high = max(ORDER, key=lambda d: high_counts.get(d, 0))
top_low  = max(ORDER, key=lambda d: low_counts.get(d, 0))
print()
print(f"🏆 WEEKLY HIGH más frecuente : {top_high}  ({high_counts[top_high]}x  ·  {high_counts[top_high]/total*100:.1f}%)")
print(f"🏆 WEEKLY LOW  más frecuente : {top_low}   ({low_counts[top_low]}x  ·  {low_counts[top_low]/total*100:.1f}%)")
