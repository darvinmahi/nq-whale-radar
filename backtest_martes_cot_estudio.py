"""
backtest_martes_cot_estudio.py
================================
FASE 2 — COT Index vs Reacción del Precio en Martes

Combina datos 5m de NQ con COT histórico semanal.
Segmenta por rango de COT Index y estudia:
  → Win rate LONG vs SHORT en NY del Martes
  → Avg pts ganados/perdidos
  → Bias óptimo: ¿COT > X% → COMPRA o VENTA?

COT Index = posición relativa de los Non-Commercial (0–100)
  0–30%  : Dealers muy cortos → suben → LONG bias
  30–65% : Zona neutra
  65–85% : Lev Money muy largos → Dealers compraron todo → SHORT bias
  85–100%: Extremo — reversión fuerte posible
"""
import yfinance as yf
import pandas as pd
import json
import os
from datetime import datetime, timezone, timedelta
from collections import defaultdict

print("=" * 70)
print("  FASE 2 — COT INDEX vs MARTES NY | NQ=F 5m + COT histórico")
print("=" * 70)

# ── Cargar COT histórico ──────────────────────────────────────────────────────
COT_FILE = os.path.join(os.path.dirname(__file__), "data", "research", "cot_history_nq.json")
cot_hist = {}
if os.path.exists(COT_FILE):
    with open(COT_FILE, "r") as f:
        raw = json.load(f)
    for entry in raw:
        try:
            d = datetime.strptime(entry["date"], "%Y-%m-%d").date()
            cot_hist[d] = float(entry.get("cot_index", entry.get("index", 0)))
        except Exception:
            pass
    print(f"  COT histórico: {len(cot_hist)} semanas | "
          f"{min(cot_hist)} → {max(cot_hist)}")
else:
    # Fallback: cargar desde agent2_data.json solo para hoy
    try:
        with open("agent2_data.json") as f:
            a2 = json.load(f)
        idx = a2.get("cot", {}).get("cot_index", 0)
        from datetime import date as dt_date
        cot_hist[dt_date.today()] = idx
        print(f"  ⚠️  Solo COT actual disponible ({idx}/100). "
              f"Para estudio completo necesitas cot_history_nq.json")
    except Exception:
        print("  ⚠️  No se encontró COT histórico ni agent2_data.json")

# ── Descarga 5m (igual que Fase 1) ───────────────────────────────────────────
print("\n  Descargando NQ=F 5m (2 años en chunks)...")
all_bars = []
end_dt   = datetime.now(timezone.utc)
start_dt = end_dt - timedelta(days=730)
chunk    = timedelta(days=55)
cur      = start_dt

while cur < end_dt:
    nxt = min(cur + chunk, end_dt)
    try:
        df = yf.download("NQ=F",
                         start=cur.strftime("%Y-%m-%d"),
                         end=nxt.strftime("%Y-%m-%d"),
                         interval="5m", prepost=True,
                         progress=False, auto_adjust=True)
        if not df.empty:
            if hasattr(df.columns, 'levels'):
                df.columns = df.columns.get_level_values(0)
            for ts, row in df.iterrows():
                try:
                    if hasattr(ts, 'tz') and ts.tz is not None:
                        ts_utc = ts.tz_convert("UTC")
                    else:
                        ts_utc = ts.tz_localize("UTC")
                    all_bars.append({
                        "ts"   : ts_utc,
                        "open" : float(row["Open"]),
                        "high" : float(row["High"]),
                        "low"  : float(row["Low"]),
                        "close": float(row["Close"]),
                    })
                except Exception:
                    pass
    except Exception as e:
        pass
    cur = nxt

seen = set(); bars = []
for b in all_bars:
    if b["ts"] not in seen:
        seen.add(b["ts"]); bars.append(b)
bars.sort(key=lambda x: x["ts"])
print(f"  Barras: {len(bars)}")

# ── Agrupa por fecha ──────────────────────────────────────────────────────────
by_date = defaultdict(list)
for b in bars:
    by_date[b["ts"].date()].append(b)

# ── Función: buscar COT de la semana del martes (buscamos hacia atrás 7 días) ─
def get_cot_for_tuesday(tue_date):
    """Busca el COT index más reciente disponible antes del martes."""
    for delta in range(0, 8):
        d = tue_date - timedelta(days=delta)
        if d in cot_hist:
            return cot_hist[d]
    return None

# ── Analiza cada Martes ───────────────────────────────────────────────────────
def is_dst(d): return 3 <= d.month <= 10

tuesday_results = []

for d in sorted(by_date.keys()):
    if d.weekday() != 1:
        continue

    cot_idx = get_cot_for_tuesday(d)
    if cot_idx is None:
        continue  # sin COT no podemos

    dst = is_dst(d)
    ny_open_h = 13 if dst else 14
    ny_close_h = 20 if dst else 21

    ny_open_ts  = datetime(d.year, d.month, d.day, ny_open_h, 30, tzinfo=timezone.utc)
    ny_11am_ts  = datetime(d.year, d.month, d.day, ny_open_h + 1, 30, tzinfo=timezone.utc)
    ny_close_ts = datetime(d.year, d.month, d.day, ny_close_h, 0, tzinfo=timezone.utc)

    # Barras del lunes también (para pre-NY)
    mon = d - timedelta(days=1)
    all_day = by_date.get(mon, []) + by_date.get(d, [])

    ny_bars  = [b for b in all_day if ny_open_ts  <= b["ts"] < ny_close_ts]
    ny1_bars = [b for b in all_day if ny_open_ts  <= b["ts"] < ny_11am_ts]

    if not ny_bars or not ny1_bars:
        continue

    ny_open_p  = ny1_bars[0]["open"]
    ny_close_p = ny_bars[-1]["close"]
    ny_hi      = max(b["high"] for b in ny_bars)
    ny_lo      = min(b["low"]  for b in ny_bars)
    ny_move    = round(ny_close_p - ny_open_p, 1)
    ny_range   = round(ny_hi - ny_lo, 1)
    ny_bull    = ny_move >= 0

    # NY Open 1h direction (9:30–10:30)
    ny1_move = round(ny1_bars[-1]["close"] - ny1_bars[0]["open"], 1)
    ny1_bull = ny1_move >= 0

    tuesday_results.append({
        "date"     : d,
        "cot_idx"  : cot_idx,
        "ny_bull"  : ny_bull,
        "ny_move"  : ny_move,
        "ny_range" : ny_range,
        "ny1_bull" : ny1_bull,
        "ny1_move" : ny1_move,
    })

N = len(tuesday_results)
print(f"  Martes con COT: {N}")
print()

# ── Segmentar por COT range ───────────────────────────────────────────────────
def pct(c, t): return f"{c/t*100:.0f}%" if t else "N/A"
def avg(vals): return round(sum(vals) / len(vals), 1) if vals else 0

ranges = [
    (0,   30,  "COT  0–30%  (BAJISTA extremo)"),
    (30,  50,  "COT 30–50%  (Bajista moderado)"),
    (50,  65,  "COT 50–65%  (Neutral-alcista)"),
    (65,  80,  "COT 65–80%  (ALCISTA modrado)"),
    (80,  100, "COT 80–100% (ALCISTA extremo)"),
]

print("=" * 70)
print("  ANÁLISIS COT INDEX vs MOVIMIENTO NY DEL MARTES")
print("=" * 70)
print()
print(f"  {'Rango COT':<30} {'N':>4} {'NY↑':>5} {'WR↑':>6} {'AvgMv':>8} {'AvgRng':>8} {'Bias':<10}")
print("  " + "-" * 75)

conclusions = []

for lo, hi, label in ranges:
    sub = [r for r in tuesday_results if lo <= r["cot_idx"] < hi]
    if not sub:
        print(f"  {label:<30} {'0':>4}")
        continue
    bull = [r for r in sub if r["ny_bull"]]
    wr   = len(bull) / len(sub) * 100
    moves = [r["ny_move"] for r in sub]
    ranges_ = [r["ny_range"] for r in sub]

    bias = "LONG 🟢" if wr >= 55 else "SHORT 🔴" if wr <= 45 else "NEUTRO ⚪"
    if wr >= 60:
        bias = "LONG FUERTE 🟢"
    if wr <= 40:
        bias = "SHORT FUERTE 🔴"

    print(f"  {label:<30} {len(sub):>4} {len(bull):>5} {wr:>5.0f}% {avg(moves):>+8.0f} {avg(ranges_):>8.0f} {bias:<14}")
    conclusions.append((lo, hi, label, len(sub), wr, avg(moves), bias))

# ── UMBRAL ÓPTIMO ─────────────────────────────────────────────────────────────
print()
print("  ── 🎯 UMBRAL ÓPTIMO DE SEÑAL ───────────────────────────────")
best_long  = max(conclusions, key=lambda x: x[4] if x[4] >= 50  else 0)
best_short = min(conclusions, key=lambda x: x[4])

print(f"  Mejor LONG  : {best_long[2]}  → WR {best_long[4]:.0f}% ({best_long[3]} martes)")
print(f"  Mejor SHORT : {best_short[2]} → WR {100 - best_short[4]:.0f}% SHORT ({best_short[3]} martes)")

# ── COMPARATIVA SIMPLE: COT < 50 vs COT > 65 ──────────────────────────────────
low_cot  = [r for r in tuesday_results if r["cot_idx"] < 50]
high_cot = [r for r in tuesday_results if r["cot_idx"] >= 65]

print()
print("  ── 📊 RESUMEN: COT bajo (<50) vs COT alto (≥65) ───────────")
if low_cot:
    lc_bull = sum(1 for r in low_cot if r["ny_bull"])
    lc_wr   = lc_bull / len(low_cot) * 100
    print(f"  COT <50 (bajista): N={len(low_cot)} → NY bull {lc_wr:.0f}%  (bias {'LONG' if lc_wr>55 else 'SHORT' if lc_wr<45 else 'NEUTRAL'})")
if high_cot:
    hc_bull = sum(1 for r in high_cot if r["ny_bull"])
    hc_wr   = hc_bull / len(high_cot) * 100
    print(f"  COT ≥65 (alcista): N={len(high_cot)} → NY bull {hc_wr:.0f}%  (bias {'LONG' if hc_wr>55 else 'SHORT' if hc_wr<45 else 'NEUTRAL'})")

# ── DETALLE + ÚLTIMOS MARTES ──────────────────────────────────────────────────
print()
print("  ── 📅 ÚLTIMOS 15 MARTES con COT ───────────────────────────")
print(f"  {'Fecha':<13} {'COT':>5} {'NY Move':>9} {'NYRange':>9} {'Dir':<10}")
print("  " + "-" * 52)
for r in tuesday_results[-15:]:
    dir_ = "↑ BULL" if r["ny_bull"] else "↓ BEAR"
    print(f"  {str(r['date']):<13} {r['cot_idx']:>5.0f} {r['ny_move']:>+9.0f} {r['ny_range']:>9.0f} {dir_}")

print()
print("=" * 70)
print("  ✅ FASE 2 COMPLETA")
print("  → Siguiente: python backtest_martes_cot65_2anos.py  (validación COT>65%)")
print("=" * 70)
