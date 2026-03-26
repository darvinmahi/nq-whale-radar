"""
cot_backtest_3meses.py
Backtest simple: usa COT Index como señal para tradear NY open.

REGLA:
  COT > 60%  → SHORT en 9:30am, cierre 10:30am  (Lev Money muy long → Dealers venden)
  COT < 40%  → LONG  en 9:30am, cierre 10:30am  (Lev Money muy short → Dealers compran)
  COT 40-60% → SIN TRADE (zona neutral)

Datos: nq_15m_intraday.csv (Ene-Mar 2026 ~50 dias)
Un contrato NQ = $20 por punto
"""
import csv
from datetime import datetime, date, timedelta
from collections import defaultdict

# ── 1. Carga intraday 15m ────────────────────────────────────────────────
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        raw = r.get("Price", "")
        if "Ticker" in raw or not raw:
            continue
        try:
            dt = datetime.fromisoformat(raw)
            cl = float(r.get("Close", 0) or 0)
            bars.append({"dt": dt, "close": cl})
        except Exception:
            continue

bars.sort(key=lambda x: x["dt"])

# Extrae NY open 9:30 y NY 10:30 por dia
by_date = {}
for b in bars:
    d  = b["dt"].date()
    hr = b["dt"].hour
    mn = b["dt"].minute
    # NY open: 9:30am ET = 14:30 UTC (invierno) / 13:30 UTC (verano)
    ny_hr = 13 if 3 <= b["dt"].month <= 10 else 14
    if d not in by_date:
        by_date[d] = {}
    if hr == ny_hr and mn == 30:
        by_date[d]["p930"]  = b["close"]
    if hr == (ny_hr + 1) and mn == 30:
        by_date[d]["p1030"] = b["close"]

valid = {d: v for d, v in by_date.items() if "p930" in v and "p1030" in v}

# ── 2. Carga COT y calcula COT Index ────────────────────────────────────
cot_rows = []
with open("data/cot/nasdaq_cot_historical_study.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d  = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            ll = int(float(r.get("Lev_Money_Positions_Long_All",  0) or 0))
            ls = int(float(r.get("Lev_Money_Positions_Short_All", 0) or 0))
            cot_rows.append({"date": d, "lev_net": ll - ls})
        except Exception:
            continue

cot_rows.sort(key=lambda x: x["date"])
WINDOW = 52
for i, r in enumerate(cot_rows):
    start   = max(0, i - WINDOW + 1)
    nets    = [cot_rows[j]["lev_net"] for j in range(start, i + 1)]
    mn, mx  = min(nets), max(nets)
    r["cot_idx"] = round((r["lev_net"] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0

def get_cot(trade_date):
    best = None
    for r in cot_rows:
        if r["date"] <= trade_date:
            best = r
        else:
            break
    return best

# ── 3. Backtest ───────────────────────────────────────────────────────────
DOLARS_PER_PT = 20   # 1 contrato NQ
N_CONTRACTS   = 1

trades = []
for d in sorted(valid.keys()):
    cot = get_cot(d)
    if cot is None:
        continue
    idx    = cot["cot_idx"]
    p930   = valid[d]["p930"]
    p1030  = valid[d]["p1030"]

    if idx > 60:
        # Señal SHORT
        direction = "SHORT"
        pnl_pts   = p930 - p1030          # ganamos si precio baja
    elif idx < 40:
        # Señal LONG
        direction = "LONG"
        pnl_pts   = p1030 - p930          # ganamos si precio sube
    else:
        direction = "SKIP"
        pnl_pts   = 0

    if direction == "SKIP":
        continue

    pnl_usd = pnl_pts * DOLARS_PER_PT * N_CONTRACTS
    trades.append({
        "date"     : d,
        "cot_idx"  : idx,
        "direction": direction,
        "entry"    : p930,
        "exit"     : p1030,
        "pts"      : round(pnl_pts, 1),
        "usd"      : round(pnl_usd, 0),
        "win"      : pnl_pts > 0,
    })

# ── 4. Estadisticas ───────────────────────────────────────────────────────
total      = len(trades)
wins       = sum(1 for t in trades if t["win"])
losses     = total - wins
total_pts  = sum(t["pts"] for t in trades)
total_usd  = sum(t["usd"] for t in trades)
win_rate   = wins / total * 100 if total else 0
avg_win    = sum(t["pts"] for t in trades if t["win"]) / wins if wins else 0
avg_loss   = sum(t["pts"] for t in trades if not t["win"]) / losses if losses else 0

longs  = [t for t in trades if t["direction"] == "LONG"]
shorts = [t for t in trades if t["direction"] == "SHORT"]

print()
print("=" * 65)
print("  BACKTEST COT INDEX -> NY OPEN  |  Ene-Mar 2026  |  1 contrato")
print("  REGLA: COT>60% = SHORT, COT<40% = LONG, 40-60% = sin trade")
print("=" * 65)
print()
print("  Total trades : {}".format(total))
print("  Ganados      : {}  ({:.0f}%)".format(wins, win_rate))
print("  Perdidos     : {}  ({:.0f}%)".format(losses, 100 - win_rate))
print("  Total puntos : {:+.0f} pts".format(total_pts))
print("  Total USD    : ${:+,.0f}  (1 contrato NQ)".format(total_usd))
print("  Avg WIN      : {:+.0f} pts".format(avg_win))
print("  Avg LOSS     : {:+.0f} pts".format(avg_loss))
print()
print("  LONGS  (COT<40%): {} trades, {:.0f}% win, {:+.0f} pts total".format(
    len(longs),
    sum(1 for t in longs if t["win"]) / len(longs) * 100 if longs else 0,
    sum(t["pts"] for t in longs)))
print("  SHORTS (COT>60%): {} trades, {:.0f}% win, {:+.0f} pts total".format(
    len(shorts),
    sum(1 for t in shorts if t["win"]) / len(shorts) * 100 if shorts else 0,
    sum(t["pts"] for t in shorts)))

print()
print("  OPERACIONES DIA A DIA:")
print("  {:<12} {:<8} {:<7} {:>8} {:>8} {:>8} {:>8}".format(
    "Fecha", "COTIdx", "Dir", "Entrada", "Salida", "Pts", "USD"))
print("  " + "-" * 62)
cum = 0
for t in trades:
    cum += t["pts"]
    flag = "✓" if t["win"] else "✗"
    print("  {} {:>6.1f}% {:>6}  {:>8,.0f} {:>8,.0f} {:>+7.0f}  ${:>+7,.0f}  [acum: {:+.0f}] {}".format(
        t["date"], t["cot_idx"], t["direction"],
        t["entry"], t["exit"], t["pts"], t["usd"], cum, flag))
