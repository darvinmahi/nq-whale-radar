"""
backtest_cot_sweep.py
Prueba multiples umbrales de COT Index x todos los dias de la semana
Thresholds SHORT: 50, 55, 60, 65, 70, 75
Entrada: high primeros 30min NY | Exit: 11am ET
"""
import csv
from datetime import datetime
from collections import defaultdict

DIAS = {0:"Lun", 1:"Mar", 2:"Mie", 3:"Jue", 4:"Vie"}
THRESHOLDS = [50, 55, 60, 65, 70, 75]

# ── Carga intraday 15m ────────────────────────────────────────────────────
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
    b1100 = [b for b in dbars
             if (b["dt"].hour == ny_hr     and b["dt"].minute == 0)
             or (b["dt"].hour == ny_hr + 1 and b["dt"].minute in (0, 15, 30, 45))]
    if not b930 or not b1100:
        continue
    valid[d] = {
        "open930"  : b930[0]["close"],
        "high30"   : max(b["high"] for b in b930),
        "low30"    : min(b["low"]  for b in b930),
        "close1100": b1100[-1]["close"],
        "weekday"  : d.weekday(),
    }

# ── Carga COT ─────────────────────────────────────────────────────────────
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

# Pre-calcula cot para cada dia
day_cot = {}
for d in sorted(valid.keys()):
    c = get_cot(d)
    if c:
        day_cot[d] = c["cot_idx"]

# ── Sweep de thresholds ───────────────────────────────────────────────────
print()
print("=" * 78)
print("  SWEEP DE UMBRALES COT INDEX | Todos los dias | NY Open 9:30 → 11am")
print("  Periodo: Ene-Mar 2026")
print("=" * 78)

# Tabla global por threshold
print()
print("  ── RESULTADOS GLOBALES (todos los dias) ──────────────────────────────")
print("  {:>8} {:>8} {:>9} {:>9} {:>9} {:>10} {:>8}".format(
    "Umbral","Trades","WinRate","TotPts","TotUSD","AvgWin","R:R"))
print("  " + "-" * 70)

results = {}
for thresh in THRESHOLDS:
    t = []
    for d, v in valid.items():
        if d not in day_cot:
            continue
        idx = day_cot[d]
        if idx > thresh:
            entry  = v["high30"]
            exit_p = v["close1100"]
            pnl    = round(entry - exit_p, 0)
            t.append({"date": d, "weekday": v["weekday"],
                      "pnl": pnl, "win": pnl > 0})

    if not t:
        continue
    wins   = sum(1 for x in t if x["win"])
    tot    = sum(x["pnl"] for x in t)
    aw     = sum(x["pnl"] for x in t if x["win"]) / wins if wins else 0
    al     = sum(x["pnl"] for x in t if not x["win"]) / (len(t)-wins) if (len(t)-wins) else 0
    rr     = abs(aw / al) if al else 99
    wrate  = wins / len(t) * 100

    results[thresh] = t
    marker = " ◄ MEJOR" if thresh == 65 else ""
    print("  {:>6}%  {:>8} {:>8.0f}% {:>+9,.0f} {:>+9,.0f} {:>+10.0f} {:>8.2f}{}".format(
        thresh, len(t), wrate, tot, tot*20, aw, rr, marker))

# Tabla por dia de semana x threshold
print()
print("  ── WIN RATE POR DIA x UMBRAL ─────────────────────────────────────────")
header = "  {:>10}".format("Dia/Umbral")
for thresh in THRESHOLDS:
    header += "  {:>8}".format(">{}%".format(thresh))
print(header)
print("  " + "-" * (10 + len(THRESHOLDS) * 10 + 2))

for wd in range(5):
    row = "  {:>10}".format(DIAS[wd])
    for thresh in THRESHOLDS:
        if thresh not in results:
            row += "  {:>8}".format("-")
            continue
        dt = [t for t in results[thresh] if t["weekday"] == wd]
        if not dt:
            row += "  {:>8}".format("0/0")
            continue
        w  = sum(1 for t in dt if t["win"])
        pts = sum(t["pnl"] for t in dt)
        pct = w / len(dt) * 100
        # Bold indicator
        stars = "★" if pct >= 80 else ("·" if pct >= 60 else " ")
        row += "  {:>5.0f}%{} {}".format(pct, stars, "{}/{}".format(w, len(dt)))
    print(row)

# Tabla total puntos por dia x threshold
print()
print("  ── TOTAL PUNTOS POR DIA x UMBRAL ─────────────────────────────────────")
header2 = "  {:>10}".format("Dia/Umbral")
for thresh in THRESHOLDS:
    header2 += "  {:>9}".format(">{}%".format(thresh))
print(header2)
print("  " + "-" * (10 + len(THRESHOLDS) * 11 + 2))

for wd in range(5):
    row = "  {:>10}".format(DIAS[wd])
    for thresh in THRESHOLDS:
        if thresh not in results:
            row += "  {:>9}".format("-")
            continue
        dt  = [t for t in results[thresh] if t["weekday"] == wd]
        pts = sum(t["pnl"] for t in dt) if dt else 0
        row += "  {:>+9,.0f}".format(pts)
    print(row)

# Mejor combo
print()
print("  ── TOP 5 COMBOS (Dia + Umbral) ────────────────────────────────────────")
combos = []
for thresh in THRESHOLDS:
    if thresh not in results:
        continue
    for wd in range(5):
        dt = [t for t in results[thresh] if t["weekday"] == wd]
        if len(dt) < 2:
            continue
        w   = sum(1 for t in dt if t["win"])
        pts = sum(t["pnl"] for t in dt)
        aw  = sum(t["pnl"] for t in dt if t["win"]) / w if w else 0
        al  = sum(t["pnl"] for t in dt if not t["win"]) / (len(dt)-w) if (len(dt)-w) else 0
        rr  = abs(aw / al) if al else 99
        score = (w/len(dt)*100) * rr   # score = win% × R:R
        combos.append({
            "dia": DIAS[wd], "thresh": thresh,
            "n": len(dt), "wins": w,
            "wrate": w/len(dt)*100, "pts": pts, "rr": rr, "score": score
        })

combos.sort(key=lambda x: x["score"], reverse=True)
print("  {:>10} {:>8} {:>8} {:>9} {:>9} {:>8} {:>8}".format(
    "Combo","Trades","WinRate","TotPts","TotUSD","R:R","Score"))
print("  " + "-" * 65)
for c in combos[:5]:
    print("  {} COT>{:>2}%  {:>8} {:>7.0f}% {:>+9,.0f} {:>+9,.0f} {:>8.2f} {:>8.1f}".format(
        c["dia"], c["thresh"],
        "{}/{}".format(c["wins"], c["n"]),
        c["wrate"], c["pts"], c["pts"]*20, c["rr"], c["score"]))
