"""
check_cot_flow.py
Verifica columnas COT disponibles y calcula:
  1. LEV MONEY COT Index %  (lo que usamos hasta ahora)
  2. COMMERCIAL FLOW Index  (formula: (Max - Delta) / (Max - Min) * 100)
  3. ASSET MANAGER Net      (el mas importante segun teoria)
"""
import csv
from datetime import datetime

rows = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    all_cols = reader.fieldnames
    for r in reader:
        try:
            d = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            lev_l = int(r.get("Lev_Money_Positions_Long_All", 0) or 0)
            lev_s = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
            com_l = int(r.get("Dealer_Positions_Long_All", 0) or 0)
            com_s = int(r.get("Dealer_Positions_Short_All", 0) or 0)
            am_l  = int(r.get("Asset_Mgr_Positions_Long_All", 0) or 0)
            am_s  = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            rows.append({
                "date":   d,
                "lev_l":  lev_l, "lev_s": lev_s, "lev_net": lev_l - lev_s,
                "com_l":  com_l, "com_s": com_s, "com_net": com_l - com_s,
                "am_l":   am_l,  "am_s":  am_s,  "am_net":  am_l  - am_s,
            })
        except:
            pass

rows.sort(key=lambda x: x["date"])
N = len(rows)
print(f"Total filas COT disponibles: {N}")
print()

# Filtrar columnas relevantes
rel = [c for c in all_cols if any(k in c for k in
    ["Dealer","Asset_Mgr","Lev_Money","Asset_Mgr_Positions"])]
print("Columnas Dealer / Asset_Mgr / Lev_Money disponibles:")
for c in rel: print(" ", c)
print()

# ─── 1. LEV MONEY COT Index % (ventana 52 semanas) ───────────────────
WINDOW = 52
lev_nets = [r["lev_net"] for r in rows]
for i, r in enumerate(rows):
    w = lev_nets[max(0, i-WINDOW+1):i+1]
    mn, mx = min(w), max(w)
    r["lev_idx"] = round((r["lev_net"] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0

# ─── 2. COMMERCIAL FLOW Index ─────────────────────────────────────────
# Delta = cambio semanal en COM_SHORT (positivo = comerciales vendieron mas)
# Flow  = (Max_delta - Delta_actual) / (Max_delta - Min_delta) * 100
# > 70  → Comerciales comprando fuerte → señal alcista
# < 30  → Comerciales vendiendo fuerte → señal bajista
FLOW_WIN = 156  # 3 años de semanas

for i, r in enumerate(rows):
    if i == 0:
        r["com_delta"] = 0
    else:
        r["com_delta"] = rows[i]["com_s"] - rows[i-1]["com_s"]  # cambio en shorts

com_deltas = [r["com_delta"] for r in rows]
for i, r in enumerate(rows):
    w = com_deltas[max(0, i-FLOW_WIN+1):i+1]
    mx, mn = max(w), min(w)
    if mx != mn:
        r["flow"] = round((mx - r["com_delta"]) / (mx - mn) * 100, 1)
    else:
        r["flow"] = 50.0

# ─── 3. ASSET MANAGER COT Index % ────────────────────────────────────
am_nets = [r["am_net"] for r in rows]
for i, r in enumerate(rows):
    w = am_nets[max(0, i-WINDOW+1):i+1]
    mn, mx = min(w), max(w)
    r["am_idx"] = round((r["am_net"] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0

# ─── TABLA COMPARATIVA ───────────────────────────────────────────────
SEP = "=" * 105
print(SEP)
print("  COMPARATIVA: LEV MONEY vs COMMERCIAL FLOW vs ASSET MANAGER")
print("  Ultimas 20 semanas")
print(SEP)
print(f"  {'Fecha':12} {'LEV_NET':>9} {'LEV%':>6}  {'COM_S_Δ':>8} {'FLOW%':>6}  {'AM_NET':>9} {'AM%':>6}  {'LEV_ZONA':8} {'FLOW_ZONA':8} {'AM_ZONA'}")
print("  " + "-"*100)

for r in rows[-20:]:
    lz = "XBEAR" if r["lev_idx"] < 20 else ("BEAR" if r["lev_idx"] < 40 else
         ("NEUT" if r["lev_idx"] < 60 else ("BULL" if r["lev_idx"] < 80 else "XBULL")))
    fz = "SHORT" if r["flow"] < 30 else ("NEUT" if r["flow"] < 70 else "LONG")
    az = "XBEAR" if r["am_idx"] < 20 else ("BEAR" if r["am_idx"] < 40 else
         ("NEUT" if r["am_idx"] < 60 else ("BULL" if r["am_idx"] < 80 else "XBULL")))
    print(f"  {str(r['date']):12} {r['lev_net']:>9,} {r['lev_idx']:>5.1f}%  {r['com_delta']:>+8,} {r['flow']:>5.1f}%  {r['am_net']:>9,} {r['am_idx']:>5.1f}%  {lz:8} {fz:8} {az}")

print()
print(SEP)
print("  DIFERENCIA CLAVE:")
print("  LEV MONEY COT%: posicion absoluta normalizada 52 semanas")
print("                  0% = max bearish, 100% = max bullish")
print("  COMMERCIAL FLOW: velocidad del cambio en shorts comerciales 3 años")
print("                  >70 = comprando fuerte (alcista), <30 = vendiendo (bajista)")
print("  ASSET MANAGER%: institucionales (pensiones/ETFs) normalizado 52 sem")
print("                  el MAS IMPORTANTE por volumen — mueven el mercado de verdad")
print()

# Verificar si valores de AM son 0 (no disponibles en CSV)
am_nonzero = sum(1 for r in rows if r["am_net"] != 0)
print(f"  Asset Manager con datos: {am_nonzero}/{N} filas")
com_nonzero = sum(1 for r in rows if r["com_net"] != 0)
print(f"  Dealer/Commercial con datos: {com_nonzero}/{N} filas")
