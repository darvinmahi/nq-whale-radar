"""
cot_vs_nyopen_v2.py
Cruza COT Index semanal con el movimiento NY open de esa semana
usando datos intraday 15m del archivo local.

NY Open = primer bar disponible entre 13:30-14:45 UTC (9:30-10:45am ET)
Mide: precio a las 9:30am vs precio 60 minutos despues (10:30am)
"""
import csv
from datetime import datetime, date, timedelta
from collections import defaultdict

# ── 1. Carga datos intraday 15m ────────────────────────────────────────────
print("Cargando intraday 15m...")
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
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
print("  {} barras de 15m cargadas".format(len(bars)))
if bars:
    print("  Rango: {} -> {}".format(bars[0]["dt"].date(), bars[-1]["dt"].date()))

# ── 2. Extrae NY open y NY +60min por dia ─────────────────────────────────
# NY open = 13:30 UTC en verano / 14:30 UTC en invierno
# Para meses Oct-Mar usamos 14:30 UTC; Abr-Sep usamos 13:30 UTC
def is_summer(dt):
    # EDT: segunda semana Mar -> primera semana Nov
    return 3 <= dt.month <= 10

def ny_open_hour(dt):
    return 13 if is_summer(dt) else 14

by_date = {}
for b in bars:
    d  = b["dt"].date()
    hr = b["dt"].hour
    mn = b["dt"].minute
    ny_hr = ny_open_hour(b["dt"])

    if d not in by_date:
        by_date[d] = {}

    # Barra de apertura NY (9:30am ET)
    if hr == ny_hr and mn == 30:
        by_date[d]["open_930"] = b["close"]
    # 60 minutos despues (10:30am ET)
    if hr == ny_hr + 1 and mn == 30:
        by_date[d]["close_1030"] = b["close"]

# Dias con ambos precios
valid_days = {d: v for d, v in by_date.items()
              if "open_930" in v and "close_1030" in v}
print("  Dias validos con apertura/cierre NY: {}".format(len(valid_days)))

# ── 3. Carga COT y calcula COT Index ───────────────────────────────────────
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

WINDOW = 52
for i, r in enumerate(cot_rows):
    start   = max(0, i - WINDOW + 1)
    nets    = [cot_rows[j]["lev_net"] for j in range(start, i + 1)]
    mn, mx  = min(nets), max(nets)
    r["cot_idx"] = round((r["lev_net"] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0

# ── 4. Asigna COT Index a cada dia de trading ──────────────────────────────
# Cada martes COT aplica a la semana siguiente (mie-mar)
# Simplificacion: la semana laboral siguiente al report date del martes

def get_cot_for_date(trade_date):
    best = None
    for r in cot_rows:
        if r["date"] <= trade_date:
            best = r
        else:
            break
    return best

# ── 5. Cruza y calcula estadisticas ───────────────────────────────────────
cross = []
for d, v in sorted(valid_days.items()):
    cot = get_cot_for_date(d)
    if cot is None:
        continue
    move_pts = v["close_1030"] - v["open_930"]
    cross.append({
        "date"     : d,
        "cot_date" : cot["date"],
        "cot_idx"  : cot["cot_idx"],
        "lev_net"  : cot["lev_net"],
        "open930"  : v["open_930"],
        "close1030": v["close_1030"],
        "move_pts" : round(move_pts, 1),
        "direction": "UP" if move_pts > 0 else "DOWN",
    })

print("  Dias cruzados COT+NQ: {}".format(len(cross)))

# ── 6. Agrupa por COT Index y calcula estadisticas ────────────────────────
def bucket(idx):
    if idx < 10:  return "< 10%"
    if idx < 25:  return "10-25%"
    if idx < 40:  return "25-40%"
    if idx < 60:  return "40-60%"
    if idx < 75:  return "60-75%"
    if idx < 90:  return "75-90%"
    return              "> 90%"

groups = defaultdict(list)
for r in cross:
    groups[bucket(r["cot_idx"])].append(r)

print()
print("=" * 85)
print("  RESULTADO: COT INDEX vs PRIMERA HORA NY OPEN  (9:30 -> 10:30am ET)")
print("  NQ Nasdaq 100 Futuros | {} dias analizados".format(len(cross)))
print("=" * 85)
print()

BUCK_ORDER = ["< 10%","10-25%","25-40%","40-60%","60-75%","75-90%","> 90%"]
# Descripcion del significado contrarian
DESC = {
    "< 10%" : "LEV MUY SHORT -> DLR compra -> esperas subida",
    "10-25%": "LEV bastante short -> sesgo alcista",
    "25-40%": "LEV levemente short",
    "40-60%": "NEUTRAL sin sesgo claro",
    "60-75%": "LEV levemente long",
    "75-90%": "LEV bastante long -> sesgo bajista",
    "> 90%" : "LEV MUY LONG -> DLR vende -> esperas caida",
}

print("{:<9} {:<38} {:>5} {:>8} {:>8} {:>12} {:>12}".format(
      "COT Idx", "Que significa", "N", "%Sube", "%Baja", "AvgPts", "Consistency"))
print("-" * 95)

for bk in BUCK_ORDER:
    data = groups.get(bk, [])
    if not data:
        continue
    n      = len(data)
    up     = sum(1 for x in data if x["move_pts"] > 0)
    dn     = sum(1 for x in data if x["move_pts"] < 0)
    avg    = sum(x["move_pts"] for x in data) / n
    pct_up = up / n * 100
    pct_dn = dn / n * 100
    consist = pct_up if pct_up > 50 else pct_dn
    arrow  = "↑" if pct_up > pct_dn else "↓"
    print("{:<9} {:<38} {:>5} {:>7.0f}% {:>7.0f}% {:>+11.0f}  {:>10.0f}% {}".format(
          bk, DESC[bk], n, pct_up, pct_dn, avg, consist, arrow))

print()
print("DETALLE dia a dia (ultimas 8 semanas):")
print("{:<13} {:>8} {:>9} {:>10} {:>10} {:>8}".format(
      "Fecha", "COTIdx", "LevNet", "Open930", "Close1030", "Move"))
print("-" * 62)
recent = [r for r in cross if r["date"] >= date(2026, 1, 1)]
for r in recent:
    print("{} {:>8.1f}% {:>+9,} {:>10,.0f} {:>10,.0f} {:>+8.0f}pts".format(
          r["date"], r["cot_idx"], r["lev_net"],
          r["open930"], r["close1030"], r["move_pts"]))
