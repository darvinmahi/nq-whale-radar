"""
backtest_pullback_primera_vela.py

Estrategia: PULLBACK a la 1ra vela (la vela como imán/sesgo)

Lógica barra a barra:
1. 1ra vela 15m (9:30-9:45 ET) establece SESGO y RANGO
2. Esperamos que el precio SALGA del rango de la 1ra vela
   (al menos MIN_BREAKOUT pts fuera del high/low)
3. Cuando el precio REGRESA al rango de la 1ra vela:
   → Entramos en la MISMA DIRECCIÓN de la 1ra vela
4. TP = el extremo que rompió antes del pullback (máximo/mínimo alcanzado)
   y continuación: TP también en 1x, 1.5x, 2x rango de la vela
5. SL = extremo opuesto de la vela + buffer

Fases del trade:
  BULL 1ra vela:
    - Precio sale por ARRIBA del HIGH
    - Precio vuelve a tocar zona de HIGH / CLOSE de la vela → ENTRY LONG
    - SL = LOW de la vela - 5pts
    - TP = máximo alcanzado antes del retorno (y más)
"""
import sys, csv
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV          = "data/research/nq_15m_intraday.csv"
BUFFER_SL    = 5.0    # pts debajo/encima del extremo opuesto de la vela
MIN_BREAKOUT = 10.0   # pts mínimos que debe salir del rango para contar el breakout
ENTRY_ZONE   = 5.0    # pts de tolerancia alrededor del close/high de la vela para entrar

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
                             "open":  float(r.get("Open",  0) or 0),
                             "high":  float(r.get("High",  0) or 0),
                             "low":   float(r.get("Low",   0) or 0),
                             "close": cl})
        except: pass
bars.sort(key=lambda x: x["dt"])

results = []
no_breakout   = 0
no_return     = 0
fridays = sorted(set(b["dt"].date() for b in bars if b["dt"].weekday() == 4))

for fri in fridays:
    first = [b for b in bars if b["dt"].date() == fri
             and b["dt"].hour == 14 and b["dt"].minute == 30]
    if not first: continue
    f1 = first[0]

    f1_hi  = f1["high"]; f1_lo = f1["low"]
    f1_rng = f1_hi - f1_lo
    if f1_rng <= 2: continue

    orig_bull = f1["close"] > f1["open"]

    # Sesión restante (barra 2 en adelante)
    session = [b for b in bars
               if b["dt"].date() == fri
               and datetime(fri.year, fri.month, fri.day, 14, 45)
               <= b["dt"]
               < datetime(fri.year, fri.month, fri.day, 21,  0)]
    if len(session) < 2: continue

    # ─── Fase 1: detectar Breakout del rango ─────────────────────────────────
    # Si vela BULL → esperamos que el precio suba al menos MIN_BREAKOUT pts sobre el HIGH
    # Si vela BEAR → esperamos que el precio baje al menos MIN_BREAKOUT pts bajo el LOW
    breakout_level = None   # máximo/mínimo alcanzado durante el breakout
    breakout_bar   = None

    phase = "WAITING_BREAK"
    for idx, b in enumerate(session):
        if phase == "WAITING_BREAK":
            if orig_bull and b["high"] >= f1_hi + MIN_BREAKOUT:
                breakout_level = b["high"]
                breakout_bar   = idx
                phase = "WAITING_RETURN"
            elif not orig_bull and b["low"] <= f1_lo - MIN_BREAKOUT:
                breakout_level = b["low"]
                breakout_bar   = idx
                phase = "WAITING_RETURN"
        elif phase == "WAITING_RETURN":
            # Actualizar el extremo del breakout
            if orig_bull:
                if b["high"] > breakout_level:
                    breakout_level = b["high"]
            else:
                if b["low"] < breakout_level:
                    breakout_level = b["low"]
            # ¿El precio regresó al rango de la 1ra vela?
            entry_zone_hi = f1_hi + ENTRY_ZONE
            entry_zone_lo = f1_lo - ENTRY_ZONE
            if orig_bull:
                # Volvió al high/close de la vela (zona de entry)
                if b["low"] <= entry_zone_hi:
                    phase = "ENTRY"
                    entry_bar = idx
                    entry = f1_hi  # entramos en el high de la vela cuando toca
                    break
            else:
                # Volvió al low/close de la vela
                if b["high"] >= entry_zone_lo:
                    phase = "ENTRY"
                    entry_bar = idx
                    entry = f1_lo
                    break

    if phase != "ENTRY":
        if breakout_bar is None:
            no_breakout += 1
        else:
            no_return += 1
        continue

    # ─── Fase 2: simular el trade ────────────────────────────────────────────
    sl_price = (f1_lo - BUFFER_SL) if orig_bull else (f1_hi + BUFFER_SL)
    sl_pts   = round(abs(entry - sl_price), 1)

    # TPs: el extremo del breakout + extensiones
    tp_breakout = breakout_level   # volver al máximo/mínimo previo
    tp_1x = (entry + f1_rng)  if orig_bull else (entry - f1_rng)
    tp_2x = (entry + f1_rng*2) if orig_bull else (entry - f1_rng*2)

    post_session = session[entry_bar:]
    def sim_trade(tp_target):
        for b in post_session:
            if orig_bull:
                if b["high"] >= tp_target: return "TP"
                if b["low"]  <= sl_price:  return "SL"
            else:
                if b["low"]  <= tp_target: return "TP"
                if b["high"] >= sl_price:  return "SL"
        last = post_session[-1]["close"] if post_session else entry
        return "EOD_W" if ((orig_bull and last > entry) or
                           (not orig_bull and last < entry)) else "EOD_L"

    res_bo  = sim_trade(tp_breakout)
    res_1x  = sim_trade(tp_1x)
    res_2x  = sim_trade(tp_2x)

    tp_bo_pts = round(abs(tp_breakout - entry), 1)
    tp_1x_pts = round(f1_rng, 1)
    tp_2x_pts = round(f1_rng * 2, 1)

    results.append({
        "date":       fri,
        "orig_bull":  orig_bull,
        "f1_rng":     round(f1_rng, 1),
        "sl_pts":     sl_pts,
        "bo_pts":     tp_bo_pts,
        "tp_bo":      res_bo,
        "tp_1x":      res_1x,
        "tp_2x":      res_2x,
    })

N = len(results)
S = "="*72; sep = "-"*72
avg_sl  = sum(r["sl_pts"] for r in results) / N if N else 1
avg_rng = sum(r["f1_rng"] for r in results) / N if N else 0
avg_bo  = sum(r["bo_pts"] for r in results) / N if N else 0

print()
print(S)
print(f"  BACKTEST PULLBACK A 1RA VELA | Viernes NY | N={N} trades")
print(f"  Rango mínimo breakout: {MIN_BREAKOUT}pts | Entrada zona: HIGH/LOW ± {ENTRY_ZONE}pts")
print(f"  Rango medio 1ra vela: {avg_rng:.0f}pts | SL medio: {avg_sl:.0f}pts")
print(f"  Días sin breakout   : {no_breakout}")
print(f"  Días sin retorno    : {no_return}")
print(S)
print()
print(f"  {'TP Objetivo':<28}  {'TP medio':>8}  {'Hit TP':>10}  {'Hit SL':>10}  {'Win%':>6}  {'EV':>8}")
print(sep)

for label, key, pts_key_val in [
    ("TP = Extremo del breakout",   "tp_bo",  avg_bo),
    ("TP = 1x rango 1ra vela",      "tp_1x",  avg_rng),
    ("TP = 2x rango 1ra vela",      "tp_2x",  avg_rng*2),
]:
    hit = sum(1 for r in results if r[key] == "TP")
    sl  = sum(1 for r in results if r[key] == "SL")
    eodw= sum(1 for r in results if r[key] == "EOD_W")
    eodl= sum(1 for r in results if r[key] == "EOD_L")
    wp  = hit/N*100
    ev  = (hit/N)*pts_key_val - (sl/N)*avg_sl
    rr  = pts_key_val / avg_sl
    print(f"  {label:<28}  {pts_key_val:>7.0f}pts  {hit:>5}({wp:.0f}%)  {sl:>5}({sl/N*100:.0f}%)  {wp:>5.0f}%  {ev:>+7.1f}pts")

print()
print(sep)
print(f"  BULL vs BEAR (TP = extremo breakout):")
for label, cond in [("1ra vela BULL → entry LONG", True), ("1ra vela BEAR → entry SHORT", False)]:
    sub = [r for r in results if r["orig_bull"] == cond]
    if not sub: continue
    h = sum(1 for r in sub if r["tp_bo"]=="TP")
    s = sum(1 for r in sub if r["tp_bo"]=="SL")
    print(f"  {label}: N={len(sub)}  TP={h}({h/len(sub)*100:.0f}%)  SL={s}({s/len(sub)*100:.0f}%)")

print()
print(S)
print(f"  RESUMEN vs estrategias anteriores:")
best = max(["tp_bo","tp_1x","tp_2x"],
           key=lambda k: sum(1 for r in results if r[k]=="TP")/N)
bh = sum(1 for r in results if r[best]=="TP")
bs = sum(1 for r in results if r[best]=="SL")
best_ev = {"tp_bo": (bh/N)*avg_bo - (bs/N)*avg_sl,
           "tp_1x": (bh/N)*avg_rng - (bs/N)*avg_sl,
           "tp_2x": (bh/N)*avg_rng*2 - (bs/N)*avg_sl}
print(f"  Follow 1ra vela (TP20, SL50)  : 46% Win  EV negativo")
print(f"  Fade midpoint   (TP23, SL12)  : 55% Win  EV +7.7pts")
print(f"  Pullback + TP extremo         : {bh/N*100:.0f}% Win  EV {best_ev[best]:+.1f}pts")
print()
