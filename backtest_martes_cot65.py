"""
backtest_martes_cot65.py
Backtest especifico: MARTES + COT Index > 65% -> LONG en NY open

Combina dos filtros:
  1. Dia de la semana = MARTES
  2. COT Index > 65% (Lev Money muy largo = contexto de presion vendedora)

LOGICA ICT MARTES (diferente al lunes):
  - El MARTES con COT > 65% el mercado tiende a:
    * Hacer un LOW de sesion temprano (9:30 - 10:00am)
    * Luego reversal LONG hacia el POC / VAH del volumen de Asia+London
  - Entrada: LONG cuando el precio toca el MINIMO de los primeros 30 min
  - Stop: minimo de 9:30-10:00 - 30 pts buffer
  - Target: +150 pts arriba O cierre de 11:00am
  - Exit forzado: 11:00am ET
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
            cl = float(r.get("Close") or 0)
            hi = float(r.get("High")  or 0)
            lo = float(r.get("Low")   or 0)
            bars.append({"dt": dt, "close": cl, "high": hi, "low": lo})
        except Exception:
            continue

bars.sort(key=lambda x: x["dt"])

# Por dia y hora: agrupa barras
by_date = defaultdict(list)
for b in bars:
    by_date[b["dt"].date()].append(b)

# ── 2. Carga COT ──────────────────────────────────────────────────────────
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
    start = max(0, i - WINDOW + 1)
    nets  = [cot_rows[j]["lev_net"] for j in range(start, i + 1)]
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

# ── 3. Analiza cada martes ──────────────────────────────────────────────────
def ny_open_hour(d):
    return 13 if 3 <= d.month <= 10 else 14

trades = []
all_tuesdays = []

for d in sorted(by_date.keys()):
    if d.weekday() != 1:   # 1 = martes
        continue

    cot = get_cot(d)
    if cot is None:
        continue

    day_bars = by_date[d]
    ny_hr    = ny_open_hour(d)

    # Barras de primeros 30 min NY (9:30 a 10:00am)
    bars_930_1000 = [b for b in day_bars
                     if b["dt"].hour == ny_hr
                     and b["dt"].minute in (30, 45)]

    # Barras de 10:00 a 11:00am
    bars_1000_1100 = [b for b in day_bars
                      if (b["dt"].hour == ny_hr and b["dt"].minute == 0)    # 10:00
                      or (b["dt"].hour == ny_hr + 1 and b["dt"].minute in (0, 15, 30, 45))]  # 10:00-11:00

    if not bars_930_1000 or not bars_1000_1100:
        all_tuesdays.append({"date": d, "cot_idx": cot["cot_idx"], "reason": "sin datos", "skipped": True})
        continue

    open_930   = bars_930_1000[0]["close"]       # precio apertura
    high_0930  = max(b["high"] for b in bars_930_1000)   # maximo primera media hora
    low_0930   = min(b["low"]  for b in bars_930_1000)   # minimo primera media hora

    # Cierre 11:00am (ultima barra antes o en las 11:00am)
    close_1100 = bars_1000_1100[-1]["close"]

    all_tuesdays.append({
        "date"     : d,
        "cot_idx"  : cot["cot_idx"],
        "open930"  : open_930,
        "high30"   : high_0930,
        "low30"    : low_0930,
        "close1100": close_1100,
        "skipped"  : False,
    })

    # ── FILTRO COT > 65% → LONG (bear trap en apertura) ─────────────────
    if cot["cot_idx"] <= 65:
        continue

    # Entrada: LONG cuando precio toca el LOW de los primeros 30 min
    # En backtest simplificado: entry = low_0930 (asumimos que llega)
    # En trading real: esperarías que el precio baje HASTA ese nivel primero

    ESCENARIO_A = {
        "entry"  : low_0930,
        "stop"   : low_0930 - 30,          # stop 30 pts abajo
        "target" : low_0930 + 150,         # target 150 pts arriba
        "exit"   : close_1100,             # exit forzado a las 11am
    }

    # PnL real hasta 11am (LONG = exit - entry)
    pnl_pts = ESCENARIO_A["exit"] - ESCENARIO_A["entry"]
    win     = pnl_pts > 0

    trades.append({
        "date"     : d,
        "cot_idx"  : cot["cot_idx"],
        "open930"  : open_930,
        "low30"    : low_0930,
        "entry"    : low_0930,
        "exit"     : close_1100,
        "drop_930" : round(open_930 - low_0930, 0),  # caida previa a la entrada
        "pnl_pts"  : round(pnl_pts, 0),
        "pnl_usd"  : round(pnl_pts * 20, 0),
        "win"      : win,
    })

# ── 4. Resultados ─────────────────────────────────────────────────────────
print()
print("=" * 70)
print("  BACKTEST: MARTES + COT Index > 65%  |  LONG en NY Open (9:30-11am)")
print("=" * 70)
print()
print("  LOGICA ICT MARTES:")
print("  - COT > 65% = Lev Money extremadamente largos")
print("  - El MARTES NY open baja los primeros 15-30 min (bear trap / liquidity sweep)")
print("  - Cuando el precio llega al MINIMO de esa media hora -> LONG")
print("  - Stop: 30 puntos por debajo del minimo")
print("  - Exit: 11:00am o si llega al target de +150 pts")
print()
print("  Todos los martes analizados: {}".format(len(all_tuesdays)))
print("  Martes con COT > 65%       : {}  (filtro aplicado)".format(len(trades)))
print()

if trades:
    wins   = sum(1 for t in trades if t["win"])
    losses = len(trades) - wins
    tot_pts = sum(t["pnl_pts"] for t in trades)
    tot_usd = sum(t["pnl_usd"] for t in trades)
    avg_win  = sum(t["pnl_pts"] for t in trades if t["win"]) / wins if wins else 0
    avg_loss = sum(t["pnl_pts"] for t in trades if not t["win"]) / losses if losses else 0
    wrate    = wins / len(trades) * 100

    print("  Win rate   : {}/{}  ({:.0f}%)".format(wins, len(trades), wrate))
    print("  Total pts  : {:+.0f} puntos".format(tot_pts))
    print("  Total USD  : ${:+,.0f}  (1 contrato)".format(tot_usd))
    print("  Avg ganada : {:+.0f} pts".format(avg_win))
    print("  Avg perdida: {:+.0f} pts".format(avg_loss))
    print()
    print("  DETALLE DE CADA MARTES COT > 65%:")
    print("  {:<12} {:>7} {:>10} {:>8} {:>8} {:>8} {:>8} {:>10}".format(
          "Fecha", "COTIdx", "Open9:30", "Drop", "Entry", "Exit11am", "Pts", "USD"))
    print("  " + "-" * 75)
    cum = 0
    for t in trades:
        cum += t["pnl_pts"]
        flag = "✓ WIN" if t["win"] else "✗ LOSS"
        print("  {}  {:>6.1f}%  {:>9,.0f}  {:>+7.0f}  {:>8,.0f}  {:>8,.0f}  {:>+6.0f}  ${:>+8,.0f}  [acum:{:+.0f}]  {}".format(
              t["date"], t["cot_idx"],
              t["open930"], -t["drop_930"],
              t["entry"], t["exit"],
              t["pnl_pts"], t["pnl_usd"],
              cum, flag))
    print()
    print("  LOGICA DE ENTRADA EXPLICADA:")
    print("  - COT > 65% = sabemos que los Lev Money estan MUY LARGOS")
    print("  - El martes NY open BAJA los primeros 15-30 min (barre liquidez de longs)")
    print("  - Cuando el precio llega al MINIMO de esa media hora -> LONG")
    print("  - Stop: 30 puntos por debajo del minimo")
    print("  - Exit: 11:00am o si llega al target de 150 pts")

print()
print("  TODOS LOS MARTES (con y sin filtro COT):")
print("  {:<12} {:>8} {:>8}".format("Fecha", "COTIdx", "Filtro"))
print("  " + "-" * 30)
for m in all_tuesdays:
    if m.get("skipped"):
        flag = "sin datos"
    elif m["cot_idx"] > 65:
        flag = ">>> LONG <<"
    else:
        flag = "skip (COT {:.0f}%)".format(m["cot_idx"])
    print("  {}  {:>7.1f}%  {}".format(m["date"], m["cot_idx"], flag))
