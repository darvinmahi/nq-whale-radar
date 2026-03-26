"""
backtest_martes_sinCOT_2anos.py
Descarga NQ=F 1h (~2 years) y hace backtest completo:
  TODOS LOS MARTES → LONG entry en low de primeros 30 min (SIN filtro COT)
"""
import yfinance as yf
import csv
from datetime import datetime, date, timedelta
from collections import defaultdict

# ── 1. Descarga 1h de NQ 2 años ──────────────────────────────────────────
print("Descargando NQ=F 1h (2 años)...")
df = yf.download("NQ=F", period="730d", interval="1h", progress=False, auto_adjust=True)
df.dropna(inplace=True)

if hasattr(df.columns, 'levels'):
    df.columns = [c[0] for c in df.columns]

print("  Total barras 1h: {}".format(len(df)))
print("  Rango: {} -> {}".format(df.index[0].date(), df.index[-1].date()))

# ── 2. Agrupa por fecha, extrae datos NY open ─────────────────────────────
by_date = defaultdict(list)
for dt_idx, row in df.iterrows():
    d = dt_idx.date()
    by_date[d].append({
        "dt"   : dt_idx,
        "open" : float(row["Open"]),
        "high" : float(row["High"]),
        "low"  : float(row["Low"]),
        "close": float(row["Close"]),
    })

def ny_open_hour_utc(d):
    return 13 if 3 <= d.month <= 10 else 14

valid_days = {}
for d, bars in by_date.items():
    ny_hr = ny_open_hour_utc(d)
    open_bars   = [b for b in bars if b["dt"].hour == ny_hr]
    plus1_bars  = [b for b in bars if b["dt"].hour == ny_hr + 1]
    plus15_bars = [b for b in bars if b["dt"].hour == ny_hr + 2]

    if not open_bars:
        continue

    ob = open_bars[0]
    high_firsthalf = max(b["high"] for b in bars if b["dt"].hour == ny_hr)
    low_firsthalf  = min(b["low"]  for b in bars if b["dt"].hour == ny_hr)

    exit_bar = (plus15_bars[0] if plus15_bars else
                plus1_bars[0]  if plus1_bars  else ob)

    valid_days[d] = {
        "open930"   : ob["open"],
        "high30"    : high_firsthalf,
        "low30"     : low_firsthalf,
        "close1100" : exit_bar["close"],
    }

print("  Dias con datos NY open: {}".format(len(valid_days)))

# ── 3. Backtest: TODOS LOS MARTES (sin filtro COT) ────────────────────────
print("Corriendo backtest...")
trades = []

for d in sorted(valid_days.keys()):
    if d.weekday() != 1:
        continue

    v       = valid_days[d]
    drop    = v["open930"] - v["low30"]

    # Entry = LONG en low de la primera hora NY
    entry   = v["low30"]
    exit_p  = v["close1100"]
    pnl_pts = round(exit_p - entry, 0)

    trades.append({
        "date"    : d,
        "open930" : v["open930"],
        "low30"   : v["low30"],
        "drop"    : round(drop, 0),
        "entry"   : entry,
        "exit"    : exit_p,
        "pnl_pts" : pnl_pts,
        "pnl_usd" : pnl_pts * 20,
        "win"     : pnl_pts > 0,
    })

# ── 4. Estadísticas ───────────────────────────────────────────────────────
total = len(trades)
wins  = sum(1 for t in trades if t["win"])
loss  = total - wins
tot_pts = sum(t["pnl_pts"] for t in trades)
tot_usd = sum(t["pnl_usd"] for t in trades)
avg_w   = sum(t["pnl_pts"] for t in trades if t["win"]) / wins if wins else 0
avg_l   = sum(t["pnl_pts"] for t in trades if not t["win"]) / loss if loss else 0
wrate   = wins / total * 100 if total else 0

print()
print("=" * 72)
print("  BACKTEST MARTES (SIN COT) → LONG NY Open | 2 Años NQ=F")
print("=" * 72)
print()
print("  Martes totales           : {}".format(total))
print()
print("  ── RESULTADOS ──────────────────────────────────────")
print("  Win rate   : {}/{} ({:.0f}%)".format(wins, total, wrate))
print("  Total pts  : {:+,.0f} puntos".format(tot_pts))
print("  Total USD  : ${:+,.0f}  (1 contrato NQ)".format(tot_usd))
print("  Avg ganada : {:+.0f} pts".format(avg_w))
print("  Avg perdida: {:+.0f} pts".format(avg_l))
if avg_l != 0:
    print("  Ratio R:R  : {:.2f}".format(abs(avg_w / avg_l)))
print()

# Sub-filtro: drop > 80 pts
t80 = [t for t in trades if t["drop"] > 80]
if t80:
    w80   = sum(1 for t in t80 if t["win"])
    pts80 = sum(t["pnl_pts"] for t in t80)
    print("  ── CON FILTRO DROP > 80 pts ────────────────────────")
    print("  Trades     : {}".format(len(t80)))
    print("  Win rate   : {}/{} ({:.0f}%)".format(w80, len(t80), w80/len(t80)*100))
    print("  Total pts  : {:+,.0f}".format(pts80))
    print("  Total USD  : ${:+,.0f}".format(pts80 * 20))

print()
print("  DIA A DIA:")
print("  {:<12} {:>8} {:>9} {:>9} {:>8} {:>10}".format(
    "Fecha","Drop","Entry","Exit11am","Pts","USD"))
print("  " + "-" * 65)
cum = 0
for t in trades:
    cum += t["pnl_pts"]
    f = "✓" if t["win"] else "✗"
    print("  {}  {:>+7.0f}  {:>9,.0f}  {:>9,.0f}  {:>+7.0f}  ${:>+8,.0f}  [acum:{:+,.0f}] {}".format(
        t["date"], -t["drop"],
        t["entry"], t["exit"], t["pnl_pts"], t["pnl_usd"], cum, f))
