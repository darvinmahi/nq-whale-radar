"""
backtest_cot_2anos_sweep.py
Descarga NQ=F 1h (2 años via yfinance) + COT historico
Sweep completo: todos los dias x umbrales COT 50/55/60/65/70/75%
SHORT en high de primera hora NY, EXIT a las 11am ET
"""
import yfinance as yf
import csv
from datetime import datetime
from collections import defaultdict

DIAS      = {0:"Lun", 1:"Mar", 2:"Mie", 3:"Jue", 4:"Vie"}
THRESHOLDS = [50, 55, 60, 65, 70, 75]

# ── 1. Descarga NQ 1h 2 años ──────────────────────────────────────────────
print("Descargando NQ=F 1h (2 anos)...")
df = yf.download("NQ=F", period="730d", interval="1h", progress=False, auto_adjust=True)
df.dropna(inplace=True)
if hasattr(df.columns, 'levels'):
    df.columns = [c[0] for c in df.columns]
print("  Barras: {}  |  {} -> {}".format(len(df), df.index[0].date(), df.index[-1].date()))

# ── 2. Extrae apertura NY por dia ─────────────────────────────────────────
by_date = defaultdict(list)
for dt_idx, row in df.iterrows():
    by_date[dt_idx.date()].append({
        "dt": dt_idx, "open": float(row["Open"]),
        "high": float(row["High"]), "low": float(row["Low"]), "close": float(row["Close"]),
    })

def ny_open_hr(d):
    return 13 if 3 <= d.month <= 10 else 14

valid = {}
for d, bars in by_date.items():
    ny_hr  = ny_open_hr(d)
    # Primera hora: barras en ny_hr (9:30am - 10:30am aprox)
    b_open = [b for b in bars if b["dt"].hour == ny_hr]
    # Segunda hora (~10:30 - 11:30am): ny_hr+1
    b_exit = [b for b in bars if b["dt"].hour == ny_hr + 2]
    if not b_open:
        continue

    high_1h = max(b["high"]  for b in b_open)
    low_1h  = min(b["low"]   for b in b_open)
    open930 = b_open[0]["open"]

    # Exit: primera barra de ny_hr+2 (~11:30am) o la última de ny_hr+1 si no hay
    if b_exit:
        exit_price = b_exit[0]["close"]
    else:
        b_1 = [b for b in bars if b["dt"].hour == ny_hr + 1]
        exit_price = b_1[-1]["close"] if b_1 else b_open[-1]["close"]

    valid[d] = {
        "open930" : open930,
        "high1h"  : high_1h,
        "low1h"   : low_1h,
        "exit"    : exit_price,
        "weekday" : d.weekday(),
    }

print("  Dias con datos NY: {}".format(len(valid)))

# ── 3. COT historico ──────────────────────────────────────────────────────
print("Cargando COT...")
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

def get_cot(d):
    best = None
    for r in cot_rows:
        if r["date"] <= d:
            best = r
        else:
            break
    return best

day_cot = {}
for d in sorted(valid.keys()):
    c = get_cot(d)
    if c:
        day_cot[d] = c["cot_idx"]

print("  Dias con COT: {}".format(len(day_cot)))

# ── 4. Backtest sweep ─────────────────────────────────────────────────────
results = {}
for thresh in THRESHOLDS:
    trades = []
    for d, v in valid.items():
        if d not in day_cot or v["weekday"] == 5 or v["weekday"] == 6:
            continue
        idx = day_cot[d]
        if idx > thresh:
            pnl = round(v["high1h"] - v["exit"], 0)
            trades.append({"date": d, "weekday": v["weekday"], "pnl": pnl, "win": pnl > 0, "cot": idx})
    results[thresh] = trades

# ── 5. Imprime resultados ─────────────────────────────────────────────────
print()
print("=" * 75)
print("  SWEEP COT INDEX | TODOS LOS DIAS | 2 ANOS NQ")
print("  SHORT en high de primera hora NY | Exit ~11am")
print("=" * 75)

print()
print("  ── TOTALES GLOBALES ───────────────────────────────────────────────────")
print("  {:>8}  {:>7}  {:>8}  {:>10}  {:>10}  {:>8}  {:>6}".format(
    "Umbral","Trades","WinRate","TotPts","TotUSD","AvgWin","R:R"))
print("  " + "-" * 66)
for thresh in THRESHOLDS:
    t = results[thresh]
    if not t:
        continue
    w   = sum(1 for x in t if x["win"])
    tot = sum(x["pnl"] for x in t)
    aw  = sum(x["pnl"] for x in t if x["win"]) / w if w else 0
    al  = sum(x["pnl"] for x in t if not x["win"]) / (len(t)-w) if (len(t)-w) else 0
    rr  = abs(aw / al) if al else 99
    print("  {:>6}%  {:>7}  {:>7.0f}%  {:>+10,.0f}  {:>+10,.0f}  {:>+8.0f}  {:>6.2f}".format(
        thresh, len(t), w/len(t)*100, tot, tot*20, aw, rr))

print()
print("  ── WIN RATE POR DIA x UMBRAL (★=80%+ / ·=60%+) ──────────────────────")
hdr = "  {:>10}".format("Dia")
for th in THRESHOLDS:
    hdr += "  {:>11}".format(">{}%".format(th))
print(hdr)
print("  " + "-" * (10 + len(THRESHOLDS)*13 + 2))

for wd in range(5):
    row = "  {:>10}".format(DIAS[wd])
    for thresh in THRESHOLDS:
        dt = [t for t in results[thresh] if t["weekday"] == wd]
        if not dt:
            row += "  {:>11}".format("- ")
            continue
        w   = sum(1 for t in dt if t["win"])
        pct = w / len(dt) * 100
        star = "★" if pct >= 80 else ("·" if pct >= 60 else " ")
        row += "  {:>5.0f}%{} {:>4}".format(pct, star, "{}/{}".format(w, len(dt)))
    print(row)

print()
print("  ── TOTAL PUNTOS POR DIA x UMBRAL ─────────────────────────────────────")
hdr2 = "  {:>10}".format("Dia")
for th in THRESHOLDS:
    hdr2 += "  {:>10}".format(">{}%".format(th))
print(hdr2)
print("  " + "-" * (10 + len(THRESHOLDS)*12 + 2))

for wd in range(5):
    row = "  {:>10}".format(DIAS[wd])
    for thresh in THRESHOLDS:
        dt  = [t for t in results[thresh] if t["weekday"] == wd]
        pts = sum(t["pnl"] for t in dt) if dt else 0
        row += "  {:>+10,.0f}".format(pts)
    print(row)

# Top combos
print()
print("  ── TOP 10 COMBOS (Dia + Umbral) ──────────────────────────────────────")
combos = []
for thresh in THRESHOLDS:
    for wd in range(5):
        dt = [t for t in results[thresh] if t["weekday"] == wd]
        if len(dt) < 3:
            continue
        w   = sum(1 for t in dt if t["win"])
        pts = sum(t["pnl"] for t in dt)
        aw  = sum(t["pnl"] for t in dt if t["win"]) / w if w else 0
        al  = sum(t["pnl"] for t in dt if not t["win"]) / (len(dt)-w) if (len(dt)-w) else 0
        rr  = abs(aw / al) if al else 99
        score = (w/len(dt)) * rr * (len(dt)**0.5)  # ajustado por muestra
        combos.append({"dia": DIAS[wd], "thresh": thresh,
                       "n": len(dt), "wins": w, "wrate": w/len(dt)*100,
                       "pts": pts, "rr": rr, "score": score})

combos.sort(key=lambda x: x["score"], reverse=True)
print("  {:>14}  {:>7}  {:>8}  {:>10}  {:>10}  {:>6}".format(
    "Combo","Trades","WinRate","TotPts","TotUSD","R:R"))
print("  " + "-" * 60)
for c in combos[:10]:
    print("  {} COT>{:>2}%  {:>7}  {:>7.0f}%  {:>+10,.0f}  {:>+10,.0f}  {:>6.2f}".format(
        c["dia"], c["thresh"],
        "{}/{}".format(c["wins"], c["n"]),
        c["wrate"], c["pts"], c["pts"]*20, c["rr"]))

print()
print("  Datos: {} dias habiles con COT y precio NY".format(len(day_cot)))
