"""
cot_recorrido_claro.py
Muestra el COT semana a semana de Nov 2025 a Feb 2026 de forma MUY CLARA:
- COMERCIAL (Dealer): Long, Short, Net, cambio vs semana anterior
- NON-COMERCIAL especulador (Lev Money): idem
- NON-COMERCIAL institucional (Asset Manager): idem
- Precio NQ de la semana
"""
import csv, requests
from datetime import datetime, date, timedelta

COT_CSV = "data/cot/nasdaq_cot_historical_study.csv"

# ── Carga COT ──────────────────────────────────────────────────────────
rows = []
with open(COT_CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            rows.append({
                "date"      : d,
                "com_long"  : int(float(r.get("Dealer_Positions_Long_All",    0) or 0)),
                "com_short" : int(float(r.get("Dealer_Positions_Short_All",   0) or 0)),
                "lev_long"  : int(float(r.get("Lev_Money_Positions_Long_All", 0) or 0)),
                "lev_short" : int(float(r.get("Lev_Money_Positions_Short_All",0) or 0)),
                "am_long"   : int(float(r.get("Asset_Mgr_Positions_Long_All", 0) or 0)),
                "am_short"  : int(float(r.get("Asset_Mgr_Positions_Short_All",0) or 0)),
            })
        except Exception:
            continue

rows.sort(key=lambda x: x["date"])

# ── Precios NQ semanales via Yahoo Finance API ──────────────────────────
def get_nq_prices():
    t1 = int(datetime.strptime("2025-10-27", "%Y-%m-%d").timestamp())
    t2 = int(datetime.strptime("2026-02-14", "%Y-%m-%d").timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F"
        "?period1={t1}&period2={t2}&interval=1wk&events=history"
    ).format(t1=t1, t2=t2)
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    data = resp.json()["chart"]["result"][0]
    out = {}
    for ts, cl in zip(data["timestamp"], data["indicators"]["quote"][0]["close"]):
        if cl is not None:
            out[datetime.utcfromtimestamp(ts).date()] = int(cl)
    return out

print("Descargando precios NQ...")
prices = get_nq_prices()
print("OK - {} semanas de precios".format(len(prices)))

def get_px(cot_d):
    for off in range(10):
        d2 = cot_d + timedelta(days=off)
        if d2 in prices:
            return prices[d2]
    return None

# ── Agrega deltas semana anterior ──────────────────────────────────────
prev = None
for r in rows:
    if prev:
        r["d_com_long"]   = r["com_long"]  - prev["com_long"]
        r["d_com_short"]  = r["com_short"] - prev["com_short"]
        r["d_lev_long"]   = r["lev_long"]  - prev["lev_long"]
        r["d_lev_short"]  = r["lev_short"] - prev["lev_short"]
        r["d_am_long"]    = r["am_long"]   - prev["am_long"]
        r["d_am_short"]   = r["am_short"]  - prev["am_short"]
    else:
        for k in ["d_com_long","d_com_short","d_lev_long","d_lev_short","d_am_long","d_am_short"]:
            r[k] = 0
    prev = r

# ── Filtra periodo ───────────────────────────────────────────────────────
period = [r for r in rows if date(2025, 11, 4) <= r["date"] <= date(2026, 2, 3)]

# ── Imprime de forma clara ───────────────────────────────────────────────
EVENTS = {
    date(2025, 11, 18): "<<< GIRO ARRIBA — precio hizo MINIMO y empezo a subir",
    date(2026, 1, 27) : "<<< GIRO ABAJO  — precio hizo MAXIMO y empezo a bajar",
}

def sig(n):
    return "+" if n >= 0 else ""

for r in period:
    px  = get_px(r["date"])
    ev  = EVENTS.get(r["date"], "")
    com_net = r["com_long"] - r["com_short"]
    lev_net = r["lev_long"] - r["lev_short"]
    am_net  = r["am_long"]  - r["am_short"]
    px_s = "{:,}".format(px) if px else "---"

    print("")
    print("=" * 70)
    if ev:
        print("  ***  {}  ***".format(ev))
    print("  SEMANA: {}      NQ PRECIO: {}".format(r["date"], px_s))
    print("  " + "-" * 60)

    print("  [COMERCIAL — Dealers / Smart Money]")
    print("       LONG  (contratos comprados): {:>10,}   cambio: {}{:,}".format(
          r["com_long"], sig(r["d_com_long"]), r["d_com_long"]))
    print("       SHORT (contratos vendidos):  {:>10,}   cambio: {}{:,}".format(
          r["com_short"], sig(r["d_com_short"]), r["d_com_short"]))
    print("       NET (Long - Short):          {:>+10,}  → {} presion".format(
          com_net, "BAJISTA" if com_net < 0 else "ALCISTA"))

    print("")
    print("  [NON-COMERCIAL Especuladores — Hedge Funds / Lev Money]")
    print("       LONG  (contratos comprados): {:>10,}   cambio: {}{:,}".format(
          r["lev_long"], sig(r["d_lev_long"]), r["d_lev_long"]))
    print("       SHORT (contratos vendidos):  {:>10,}   cambio: {}{:,}".format(
          r["lev_short"], sig(r["d_lev_short"]), r["d_lev_short"]))
    print("       NET (Long - Short):          {:>+10,}  → {} presion".format(
          lev_net, "BAJISTA" if lev_net < 0 else "ALCISTA"))

    print("")
    print("  [NON-COMERCIAL Institucionales — Asset Managers / Fondos]")
    print("       LONG  (contratos comprados): {:>10,}   cambio: {}{:,}".format(
          r["am_long"], sig(r["d_am_long"]), r["d_am_long"]))
    print("       SHORT (contratos vendidos):  {:>10,}   cambio: {}{:,}".format(
          r["am_short"], sig(r["d_am_short"]), r["d_am_short"]))
    print("       NET (Long - Short):          {:>+10,}  → {} presion".format(
          am_net, "BAJISTA" if am_net < 0 else "ALCISTA"))

print("")
print("=" * 70)
print("FIN DEL RECORRIDO")
print("=" * 70)
