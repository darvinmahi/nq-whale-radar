"""
backtest_cot65_todos_dias.py
COT Index > 65% → SHORT en NY open | Todos los dias de la semana
Muestra resultados globales + desglose por dia (Lun, Mar, Mie, Jue, Vie)
"""
import csv
from datetime import datetime
from collections import defaultdict

DIAS = {0:"Lunes", 1:"Martes", 2:"Miercoles", 3:"Jueves", 4:"Viernes"}

# ── 1. Intraday 15m ──────────────────────────────────────────────────────
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        raw = r.get("Price", "")
        if "Ticker" in raw or not raw:
            continue
        try:
            dt = datetime.fromisoformat(raw)
            bars.append({
                "dt"   : dt,
                "close": float(r.get("Close") or 0),
                "high" : float(r.get("High")  or 0),
                "low"  : float(r.get("Low")   or 0),
            })
        except Exception:
            continue

bars.sort(key=lambda x: x["dt"])

by_date = defaultdict(list)
for b in bars:
    by_date[b["dt"].date()].append(b)

valid = {}
for d, dbars in by_date.items():
    ny_hr = 13 if 3 <= d.month <= 10 else 14
    b930  = [b for b in dbars if b["dt"].hour == ny_hr and b["dt"].minute in (30, 45)]
    b1030 = [b for b in dbars
             if (b["dt"].hour == ny_hr     and b["dt"].minute == 0)
             or (b["dt"].hour == ny_hr + 1 and b["dt"].minute in (0, 15, 30, 45))]
    if not b930 or not b1030:
        continue
    valid[d] = {
        "open930"  : b930[0]["close"],
        "high30"   : max(b["high"] for b in b930),
        "low30"    : min(b["low"]  for b in b930),
        "close1100": b1030[-1]["close"],
        "weekday"  : d.weekday(),
    }

# ── 2. COT ───────────────────────────────────────────────────────────────
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
for i, r in enumerate(cot_rows):
    s = max(0, i - 52 + 1)
    nets = [cot_rows[j]["lev_net"] for j in range(s, i + 1)]
    mn, mx = min(nets), max(nets)
    r["cot_idx"] = round((r["lev_net"] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0

def get_cot(trade_date):
    best = None
    for r in cot_rows:
        if r["date"] <= trade_date:
            best = r
        else:
            break
    return best

# ── 3. Backtest todos los dias ───────────────────────────────────────────
trades = []
for d in sorted(valid.keys()):
    cot = get_cot(d)
    if cot is None:
        continue
    idx = cot["cot_idx"]
    v   = valid[d]

    if idx > 65:
        direction = "SHORT"
        entry     = v["high30"]
        exit_p    = v["close1100"]
        pnl_pts   = round(entry - exit_p, 0)
    elif idx < 35:
        direction = "LONG"
        entry     = v["low30"]
        exit_p    = v["close1100"]
        pnl_pts   = round(exit_p - entry, 0)
    else:
        continue

    trades.append({
        "date"     : d,
        "weekday"  : v["weekday"],
        "cot_idx"  : idx,
        "direction": direction,
        "entry"    : entry,
        "exit"     : exit_p,
        "rally"    : round(v["high30"] - v["open930"], 0),
        "pnl_pts"  : pnl_pts,
        "pnl_usd"  : pnl_pts * 20,
        "win"      : pnl_pts > 0,
    })

# ── 4. Resultados ─────────────────────────────────────────────────────────
total = len(trades)
wins  = sum(1 for t in trades if t["win"])
loss  = total - wins
tot_pts = sum(t["pnl_pts"] for t in trades)
avg_w   = sum(t["pnl_pts"] for t in trades if t["win"]) / wins if wins else 0
avg_l   = sum(t["pnl_pts"] for t in trades if not t["win"]) / loss if loss else 0

print()
print("=" * 70)
print("  COT INDEX > 65% → SHORT  |  COT < 35% → LONG")
print("  Todos los dias | NY Open (entrada high/low 30min, exit 11am)")
print("  Periodo: Ene-Mar 2026 ({} dias operados)".format(total))
print("=" * 70)
print()
print("  Total trades : {}".format(total))
print("  Win rate     : {}/{} ({:.0f}%)".format(wins, total, wins/total*100 if total else 0))
print("  Total puntos : {:+,.0f}".format(tot_pts))
print("  Total USD    : ${:+,.0f}  (1 contrato)".format(tot_pts * 20))
print("  Avg ganada   : {:+.0f} pts".format(avg_w))
print("  Avg perdida  : {:+.0f} pts".format(avg_l))
if avg_l: print("  Ratio R:R    : {:.2f}".format(abs(avg_w / avg_l)))
print()

# Desglose por dia
print("  POR DIA DE LA SEMANA:")
print("  {:<12} {:>8} {:>8} {:>10} {:>10} {:>10}".format(
    "Dia", "Trades", "WinRate", "TotPts", "AvgWin", "AvgLoss"))
print("  " + "-" * 60)
for wd in range(5):
    dt = [t for t in trades if t["weekday"] == wd]
    if not dt:
        print("  {:<12} {:>8}".format(DIAS[wd], 0))
        continue
    dw = sum(1 for t in dt if t["win"])
    dp = sum(t["pnl_pts"] for t in dt)
    daw = sum(t["pnl_pts"] for t in dt if t["win"])     / dw     if dw else 0
    dal = sum(t["pnl_pts"] for t in dt if not t["win"]) / (len(dt)-dw) if (len(dt)-dw) else 0
    print("  {:<12} {:>8} {:>7.0f}% {:>+10,.0f} {:>+10.0f} {:>+10.0f}".format(
        DIAS[wd], len(dt), dw/len(dt)*100, dp, daw, dal))

print()
print("  DIA A DIA COMPLETO:")
print("  {:<12} {:>5} {:>7} {:>6} {:>9} {:>9} {:>7} {:>9}".format(
    "Fecha","Dia","COTIdx","Dir","Entry","Exit11am","Pts","USD"))
print("  " + "-" * 72)
cum = 0
for t in trades:
    cum += t["pnl_pts"]
    f = "✓" if t["win"] else "✗"
    print("  {}  {:>3}  {:>6.1f}%  {:>5}  {:>9,.0f}  {:>9,.0f}  {:>+6.0f}  ${:>+7,.0f} [acum:{:+,.0f}] {}".format(
        t["date"], DIAS[t["weekday"]][:3],
        t["cot_idx"], t["direction"],
        t["entry"], t["exit"], t["pnl_pts"], t["pnl_usd"], cum, f))
