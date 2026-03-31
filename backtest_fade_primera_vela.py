"""
backtest_fade_primera_vela.py

Estrategia FADE (contra-tendencia) de la 1ra vela 15m viernes NY.

Lógica:
- Si 1ra vela es BULL → entramos SHORT al cierre de la vela
- Si 1ra vela es BEAR → entramos LONG al cierre de la vela
- TP1 = midpoint de la 1ra vela
- TP2 = extremo opuesto de la 1ra vela
- TP3 = 1.5x el rango de la vela (más allá del extremo)
- SL  = extremo en la dirección original + 5pts buffer
         (si la vela fue BULL, SL sobre el HIGH + 5pts)
"""
import sys, csv
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV    = "data/research/nq_15m_intraday.csv"
BUFFER = 5.0

# ── Cargar ────────────────────────────────────────────────────────────────────
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
fridays = sorted(set(b["dt"].date() for b in bars if b["dt"].weekday() == 4))

for fri in fridays:
    first = [b for b in bars if b["dt"].date() == fri
             and b["dt"].hour == 14 and b["dt"].minute == 30]
    if not first: continue
    f1 = first[0]

    f1_hi = f1["high"]; f1_lo = f1["low"]
    f1_rng = round(f1_hi - f1_lo, 1)
    if f1_rng <= 2: continue  # ignorar velas casi planas

    orig_bull = f1["close"] > f1["open"]

    # FADE → entramos en CONTRA
    is_long_fade = not orig_bull   # si vela BULL → fade = SHORT → es_long=False
    entry        = f1["close"]     # mismo precio de entrada

    # Niveles de la vela
    mid    = round((f1_hi + f1_lo) / 2, 2)
    ext_op = f1_lo if orig_bull else f1_hi  # extremo opuesto adonde queremos ir
    ext_15 = round(ext_op - f1_rng * 0.5 if orig_bull else ext_op + f1_rng * 0.5, 2)  # 1.5x

    # SL = extremo en dirección original + buffer
    sl_price = (f1_hi + BUFFER) if orig_bull else (f1_lo - BUFFER)
    sl_pts   = round(abs(entry - sl_price), 1)

    # TPs expresados en pts desde entry
    tp_mid_pts = round(abs(entry - mid), 1)
    tp_ext_pts = round(abs(entry - ext_op), 1)
    tp_15x_pts = round(tp_ext_pts + f1_rng * 0.5, 1)

    # Barras de sesión (14:45 → 21:00 UTC)
    session = [b for b in bars
               if b["dt"].date() == fri
               and datetime(fri.year, fri.month, fri.day, 14, 45)
               <= b["dt"]
               < datetime(fri.year, fri.month, fri.day, 21,  0)]
    if not session: continue

    def sim(tp_pts):
        """Simula e indica si tocó TP o SL primero."""
        tp_price = (entry - tp_pts) if orig_bull else (entry + tp_pts)
        for b in session:
            if orig_bull:  # fade = short
                if b["low"]  <= tp_price: return "TP"
                if b["high"] >= sl_price: return "SL"
            else:          # fade = long
                if b["high"] >= tp_price: return "TP"
                if b["low"]  <= sl_price: return "SL"
        last = session[-1]["close"]
        return "EOD_W" if ((orig_bull and last < entry) or
                           (not orig_bull and last > entry)) else "EOD_L"

    results.append({
        "date":     fri,
        "orig_bull": orig_bull,
        "f1_rng":   f1_rng,
        "sl_pts":   sl_pts,
        "tp_mid":   sim(tp_mid_pts),
        "tp_ext":   sim(tp_ext_pts),
        "tp_15x":   sim(tp_15x_pts),
        "tp_mid_pts": tp_mid_pts,
        "tp_ext_pts": tp_ext_pts,
        "tp_15x_pts": tp_15x_pts,
    })

N = len(results)
S = "="*72; sep = "-"*72

avg_sl  = sum(r["sl_pts"] for r in results) / N
avg_rng = sum(r["f1_rng"] for r in results) / N

print()
print(S)
print(f"  BACKTEST FADE 1RA VELA | Viernes NY 9:30 ET | N={N}")
print(f"  Entrada EN CONTRA de la 1ra vela 15m")
print(f"  SL = extremo de la vela + {BUFFER}pts  (SL medio: {avg_sl:.0f}pts)")
print(f"  Rango medio 1ra vela: {avg_rng:.0f}pts")
print(S)
print()

for label, key, pts_key in [
    ("TP1 = MIDPOINT de la vela",     "tp_mid", "tp_mid_pts"),
    ("TP2 = EXTREMO OPUESTO",          "tp_ext", "tp_ext_pts"),
    ("TP3 = 1.5x rango (mas alla)",   "tp_15x", "tp_15x_pts"),
]:
    hit  = sum(1 for r in results if r[key] == "TP")
    sl   = sum(1 for r in results if r[key] == "SL")
    eodw = sum(1 for r in results if r[key] == "EOD_W")
    eodl = sum(1 for r in results if r[key] == "EOD_L")
    avg_tp_pts = sum(r[pts_key] for r in results) / N
    rr   = avg_tp_pts / avg_sl if avg_sl else 0
    print(f"  {label}")
    print(f"  TP medio: {avg_tp_pts:.0f}pts | R:R = {rr:.2f}x")
    print(sep)
    print(f"  Hit TP   : {hit:>5} / {N}  = {hit/N*100:.0f}%")
    print(f"  Hit SL   : {sl:>5} / {N}  = {sl/N*100:.0f}%")
    print(f"  EOD W/L  : {eodw:>3}W / {eodl:>3}L")

    # Expectativa matemática
    # E = (hit/N)*avg_tp - (sl/N)*avg_sl
    e = (hit/N)*avg_tp_pts - (sl/N)*avg_sl
    print(f"  Expected value por trade: {e:+.1f} pts")
    print()

# ─── Desglose por tipo de vela ────────────────────────────────────────────────
print(sep)
print(f"  FADE según si 1ra vela es BULL o BEAR (mirar cuál funciona mejor)")
print(sep)
for label2, cond in [("Fade de BULL (→ short)", True), ("Fade de BEAR (→ long)", False)]:
    sub = [r for r in results if r["orig_bull"] == cond]
    if not sub: continue
    h = sum(1 for r in sub if r["tp_ext"] == "TP")
    s = sum(1 for r in sub if r["tp_ext"] == "SL")
    print(f"  {label2} N={len(sub)}:  TP(ext)={h}/{len(sub)}={h/len(sub)*100:.0f}%  SL={s}/{len(sub)}={s/len(sub)*100:.0f}%")

print()
print(S)
print(f"  COMPARATIVA FINAL:")
print(f"  Estrategia       |  Win%  |  EV/trade")
print(sep)
# Fade TP2
h2 = sum(1 for r in results if r["tp_ext"]=="TP")
s2 = sum(1 for r in results if r["tp_ext"]=="SL")
tp2_avg = sum(r["tp_ext_pts"] for r in results)/N
ev2 = (h2/N)*tp2_avg - (s2/N)*avg_sl
print(f"  Fade TP=extremo  |  {h2/N*100:.0f}%   |  {ev2:+.1f} pts")
# Follow original (del backtest anterior)
print(f"  Follow 1ra vela  |  64%   |  depende del TP")
print()
