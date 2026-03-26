"""
backtest_martes_cot65_2anos.py
Descarga NQ=F 1h (~2 years) y hace backtest completo:
  MARTES + COT > 65% → LONG entry en low de primeros 30 min
"""
import yfinance as yf
import csv
from datetime import datetime, date, timedelta
from collections import defaultdict

# ── 1. Descarga 1h de NQ 2 años ──────────────────────────────────────────
print("Descargando NQ=F 1h (2 años)...")
df = yf.download("NQ=F", period="730d", interval="1h", progress=False, auto_adjust=True)
df.dropna(inplace=True)

# Aplana columnas si hay MultiIndex
if hasattr(df.columns, 'levels'):
    df.columns = [c[0] for c in df.columns]

print("  Total barras 1h: {}".format(len(df)))
print("  Rango: {} -> {}".format(df.index[0].date(), df.index[-1].date()))

# ── 2. Agrupa por fecha, extrae datos NY open ─────────────────────────────
# En 1h bars: NY open 9:30am ET = 14:30 UTC (invierno) / 13:30 UTC (verano)
# Bar de 1h YF normalmente al inicio del periodo: 14:00 UTC = 9am ET
# Vamos a tomar la barra que abre más cerca de las 9:30am ET

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
    # EDT (verano): NY 9:30am = 13:30 UTC → barra de 13:00 o 14:00
    # EST (invierno): NY 9:30am = 14:30 UTC → barra de 14:00
    return 13 if 3 <= d.month <= 10 else 14

valid_days = {}
for d, bars in by_date.items():
    ny_hr = ny_open_hour_utc(d)
    # Barra apertura NY (~9:30am): primera barra entre ny_hr y ny_hr+1
    open_bars = [b for b in bars if b["dt"].hour == ny_hr]
    # Barra 1h después (~10:30am)
    plus1_bars = [b for b in bars if b["dt"].hour == ny_hr + 1]
    # Barra 1.5h después (~11:00am)
    plus15_bars = [b for b in bars if b["dt"].hour == ny_hr + 2]

    if not open_bars:
        continue

    ob = open_bars[0]
    # High y Low de la primera hora
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

# ── 3. Carga COT ──────────────────────────────────────────────────────────
print("Cargando COT historico...")
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
    s = max(0, i - WINDOW + 1)
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

# ── 4. Backtest: TODOS LOS MARTES ─────────────────────────────────────────
print("Corriendo backtest...")
trades   = []
all_tue  = []

for d in sorted(valid_days.keys()):
    if d.weekday() != 1:
        continue
    cot = get_cot(d)
    if cot is None:
        continue

    v       = valid_days[d]
    cot_idx = cot["cot_idx"]
    drop    = v["open930"] - v["low30"]

    all_tue.append({"date": d, "cot_idx": cot_idx})

    if cot_idx <= 65:
        continue

    # Entry = LONG en low de la primera hora (bear trap → reversión alcista)
    entry   = v["low30"]
    exit_p  = v["close1100"]
    pnl_pts = round(exit_p - entry, 0)

    trades.append({
        "date"    : d,
        "cot_idx" : cot_idx,
        "open930" : v["open930"],
        "low30"   : v["low30"],
        "drop"    : round(drop, 0),
        "entry"   : entry,
        "exit"    : exit_p,
        "pnl_pts" : pnl_pts,
        "pnl_usd" : pnl_pts * 20,
        "win"     : pnl_pts > 0,
    })

# ── 5. Estadísticas ───────────────────────────────────────────────────────
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
print("  BACKTEST MARTES + COT > 65% → LONG NY Open | 2 Años NQ=F")
print("=" * 72)
print()
print("  Martes totales analizados  : {}".format(len(all_tue)))
print("  Martes con COT > 65%       : {}  ({:.0f}%)".format(total, total/len(all_tue)*100 if all_tue else 0))
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

# Sub-filtro: con drop > 80 pts
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
print("  {:<12} {:>7} {:>8} {:>9} {:>9} {:>8} {:>10}".format(
    "Fecha","COTIdx","Drop","Entry","Exit11am","Pts","USD"))
print("  " + "-" * 70)
cum = 0
for t in trades:
    cum += t["pnl_pts"]
    f = "✓" if t["win"] else "✗"
    print("  {}  {:>6.1f}%  {:>+7.0f}  {:>9,.0f}  {:>9,.0f}  {:>+7.0f}  ${:>+8,.0f}  [acum:{:+,.0f}] {}".format(
        t["date"], t["cot_idx"], -t["drop"],
        t["entry"], t["exit"], t["pnl_pts"], t["pnl_usd"], cum, f))
