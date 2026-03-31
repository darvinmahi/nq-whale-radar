"""
backtest_sl_dinamico_retorno.py

DOS análisis en uno:
1. SL dinámico = rango de la 1ra vela 15m + 5pts buffer
   TP testados: 20, 30, 50, 80, 100 pts (fijos)
   Entrada: cierre de la 1ra vela en su dirección

2. Hipótesis de retorno:
   "El precio SIEMPRE vuelve al rango de la 1ra vela durante la sesión"
   Mide en cuántos viernes el precio regresa al high/low de la 1ra vela
   después de salir de ella (cuántas barras demora, etc.)
"""
import sys, csv
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV = "data/research/nq_15m_intraday.csv"
BUFFER = 5.0   # pts extra al SL dinámico
TP_LIST = [20, 30, 50, 80, 100]

# ── Cargar barras ─────────────────────────────────────────────────────────────
bars = []
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        raw = r.get("Datetime", "")
        if not raw: continue
        try:
            dt = datetime.fromisoformat(raw.replace("+00:00","").strip())
            cl = float(r.get("Close", 0) or 0)
            if cl > 0:
                bars.append({"dt": dt,
                             "open":  float(r.get("Open", 0) or 0),
                             "high":  float(r.get("High", 0) or 0),
                             "low":   float(r.get("Low",  0) or 0),
                             "close": cl})
        except: pass
bars.sort(key=lambda x: x["dt"])

def get_session(date, h_start, m_start, h_end, m_end):
    return [b for b in bars
            if b["dt"].date() == date
            and datetime(date.year, date.month, date.day, h_start, m_start)
            <= b["dt"]
            < datetime(date.year, date.month, date.day, h_end, m_end)]

results = []
fridays = sorted(set(b["dt"].date() for b in bars if b["dt"].weekday() == 4))

for fri in fridays:
    # 1ra vela 14:30 UTC (9:30 ET)
    first = [b for b in bars if b["dt"].date() == fri
             and b["dt"].hour == 14 and b["dt"].minute == 30]
    if not first: continue
    f1 = first[0]

    f1_hi = f1["high"]; f1_lo = f1["low"]
    f1_rng = round(f1_hi - f1_lo, 1)
    if f1_rng <= 0: continue

    is_long = f1["close"] > f1["open"]
    entry   = f1["close"]

    # SL dinámico = rango de la vela + buffer
    sl_pts = round(f1_rng + BUFFER, 1)
    sl_price = (entry - sl_pts) if is_long else (entry + sl_pts)

    # Barras restantes de la sesión (14:45 → 21:00 UTC)
    session = get_session(fri, 14, 45, 21, 0)
    if not session: continue

    # ── 1. Análisis TP/SL dinámico ───────────────────────────────────────────
    tp_results = {}
    for tp_pts in TP_LIST:
        tp_price = (entry + tp_pts) if is_long else (entry - tp_pts)
        hit = None
        for b in session:
            if is_long:
                if b["high"] >= tp_price: hit = "TP"; break
                if b["low"]  <= sl_price: hit = "SL"; break
            else:
                if b["low"]  <= tp_price: hit = "TP"; break
                if b["high"] >= sl_price: hit = "SL"; break
        if hit is None:
            last = session[-1]["close"]
            hit = "EOD_WIN" if ((is_long and last > entry) or
                                (not is_long and last < entry)) else "EOD_LOSS"
        tp_results[tp_pts] = hit

    # ── 2. Hipótesis de retorno al rango de la 1ra vela ─────────────────────
    # ¿El precio vuelve al HIGH o LOW de la 1ra vela en algún momento?
    # Si salió al alza (is_long) → ¿vuelve al LOW (f1_lo)?
    # Si salió a la baja (!is_long) → ¿vuelve al HIGH (f1_hi)?
    retorno_target = f1_lo if is_long else f1_hi
    retorno_mid    = (f1_hi + f1_lo) / 2  # mitad de la vela

    retorno_lo_hi  = False  # toca el extremo opuesto de la vela
    retorno_mid_f1 = False  # vuelve al midpoint
    retorno_bar    = None

    for idx, b in enumerate(session):
        if is_long:
            if b["low"] <= retorno_target:   # volvió al LOW de la 1ra vela
                retorno_lo_hi = True
                if retorno_bar is None: retorno_bar = idx + 1
        else:
            if b["high"] >= retorno_target:  # volvió al HIGH de la 1ra vela
                retorno_lo_hi = True
                if retorno_bar is None: retorno_bar = idx + 1
        # Midpoint
        if not retorno_mid_f1:
            if is_long and b["low"] <= retorno_mid:    retorno_mid_f1 = True
            if not is_long and b["high"] >= retorno_mid: retorno_mid_f1 = True

    results.append({
        "date":     fri,
        "is_long":  is_long,
        "entry":    entry,
        "f1_rng":   f1_rng,
        "sl_pts":   sl_pts,
        "tp":       tp_results,
        "ret_ext":  retorno_lo_hi,   # volvió al extremo opuesto de la 1ra vela
        "ret_mid":  retorno_mid_f1,  # volvió al midpoint
        "ret_bar":  retorno_bar,     # barra en que volvió (x15 = minutos)
    })

N = len(results)
if N == 0:
    print("Sin datos."); exit()

S = "="*72; sep = "-"*72

# ═══════════════════════════════════════════════════════════════════
print()
print(S)
print(f"  BACKTEST SL DINAMICO | Entrada 1ra vela 15m viernes NY")
print(f"  SL = rango de la vela + {BUFFER}pts buffer  | N={N} viernes")
print(f"  SL promedio dinamico: {sum(r['sl_pts'] for r in results)/N:.0f} pts")
print(f"  Rango 1ra vela medio: {sum(r['f1_rng'] for r in results)/N:.0f} pts")
print(S)
print()
print(f"  {'TP':>6}  {'Hit TP':>10}  {'Hit SL':>10}  {'EOD':>10}  {'Win%':>6}  {'R:R medio':>10}")
print(sep)

for tp in TP_LIST:
    hit_tp  = sum(1 for r in results if r["tp"][tp] == "TP")
    hit_sl  = sum(1 for r in results if r["tp"][tp] == "SL")
    eod_w   = sum(1 for r in results if r["tp"][tp] == "EOD_WIN")
    eod_l   = sum(1 for r in results if r["tp"][tp] == "EOD_LOSS")
    win_pct = hit_tp / N * 100
    # R:R = TP / SL dinámico (promedio)
    avg_sl  = sum(r["sl_pts"] for r in results) / N
    rr      = tp / avg_sl
    print(f"  {tp:>5}pts  {hit_tp:>5} ({hit_tp/N*100:.0f}%)  {hit_sl:>5} ({hit_sl/N*100:.0f}%)  {eod_w:>3}W/{eod_l:>2}L  {win_pct:>5.0f}%  {rr:>9.1f}x")

# ═══════════════════════════════════════════════════════════════════
print()
print(S)
print(f"  HIPOTESIS: El precio vuelve al rango de la 1ra vela durante el dia")
print(S)
print()

ret_ext = sum(1 for r in results if r["ret_ext"])
ret_mid = sum(1 for r in results if r["ret_mid"])
bars_ret = [r["ret_bar"]*15 for r in results if r["ret_bar"] is not None]  # en minutos
avg_r = sum(bars_ret)/len(bars_ret) if bars_ret else 0

print(f"  Vuelve al EXTREMO opuesto de la 1ra vela : {ret_ext}/{N} = {ret_ext/N*100:.0f}%")
print(f"  Vuelve al MIDPOINT de la 1ra vela        : {ret_mid}/{N} = {ret_mid/N*100:.0f}%")
print(f"  Tiempo promedio en volver al extremo     : {avg_r:.0f} min ({avg_r/60:.1f} horas)")
print()

# Desglose por dirección
for label, cond in [("cuando BULL", True), ("cuando BEAR", False)]:
    sub = [r for r in results if r["is_long"] == cond]
    if not sub: continue
    re  = sum(1 for r in sub if r["ret_ext"])
    rm  = sum(1 for r in sub if r["ret_mid"])
    print(f"  {label} (N={len(sub)}):  extremo={re}/{len(sub)}={re/len(sub)*100:.0f}%  mid={rm}/{len(sub)}={rm/len(sub)*100:.0f}%")

print()
print(sep)
print(f"  DETALLE: cuándo vuelve (barras * 15min = minutos transcurridos)")
print(sep)
brackets = [(1,2,"0-30min"),(3,4,"30-60min"),(5,8,"60-120min"),(9,16,"2-4hrs"),(17,99,"4hrs+")]
for (a,b2,label) in brackets:
    c = sum(1 for r in results if r["ret_bar"] and a<=r["ret_bar"]<=b2)
    perc = c/ret_ext*100 if ret_ext else 0
    bar_ = "#"*int(perc//5) + "."*(20-int(perc//5))
    print(f"  {label:<10}: {c:>4} ({perc:.0f}%)  {bar_}")

print()
print(S)
print(f"  CONCLUSION:")
best = max(TP_LIST, key=lambda t: sum(1 for r in results if r["tp"][t]=="TP")/N)
b_n  = sum(1 for r in results if r["tp"][best]=="TP")
b_sl = sum(1 for r in results if r["tp"][best]=="SL")
avg_sl2 = sum(r["sl_pts"] for r in results)/N
print(f"  TP optimo con SL dinamico: TP={best}pts hit {b_n/N*100:.0f}% | SL hit {b_sl/N*100:.0f}%")
print(f"  SL medio dinamico: {avg_sl2:.0f}pts  vs SL fijo anterior: 50pts")
print(f"  El precio vuelve al rango 1ra vela (extremo): {ret_ext/N*100:.0f}% de los viernes")
print(f"  El precio vuelve al midpoint 1ra vela       : {ret_mid/N*100:.0f}% de los viernes")
print()
