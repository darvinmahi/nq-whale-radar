"""
backtest_viernes_primera_vela.py
METODOLOGIA: METODOLOGIA.md — Whale Radar NQ

VP Asia: 18:00 ET prev → 09:20 ET (= 23:00 UTC prev → 13:20 UTC)
NY Open: 09:30 ET = 14:30 UTC
Primera vela 15m: 14:30-14:45 UTC

Patrones ICT:
  SWEEP_H_RETURN : NY sube > Range High + 20pts y vuelve  → SELL
  SWEEP_L_RETURN : NY baja < Range Low  - 20pts y vuelve  → BUY
  EXPANSION_H    : Rompe Range High y cierra arriba        → BUY
  EXPANSION_L    : Rompe Range Low  y cierra abajo         → SELL
  ROTATION_POC   : Se queda dentro del rango               → Scalp bidireccional
  NEWS_DRIVE     : Rango >250 pts en 1ras 2hr              → Seguir dirección

BUF    = 20  puntos
"""
import csv, math
from datetime import datetime, timedelta, time

CSV   = "data/research/nq_15m_intraday.csv"
BUF   = 20.0
VA_PCT= 0.70
BIN   = 5.0

# ── Cargar CSV ──────────────────────────────────────────────────────────────
bars = []
with open(CSV, encoding="utf-8") as f:
    for r in csv.DictReader(f):
        raw = r.get("Datetime","") or r.get("Price","")
        if not raw or "Ticker" in raw or raw == "Datetime": continue
        try:
            dt = datetime.fromisoformat(raw.replace("+00:00","").strip())
            cl = float(r.get("Close",0) or 0)
            if cl > 0:
                bars.append({"dt": dt,
                             "open":  float(r.get("Open",0)  or 0),
                             "high":  float(r.get("High",0)  or 0),
                             "low":   float(r.get("Low",0)   or 0),
                             "close": cl,
                             "vol":   1.0})  # CSV sin vol, usar peso=1
        except: pass
bars.sort(key=lambda x: x["dt"])

# ── Volume Profile ───────────────────────────────────────────────────────────
def calc_vp(sb):
    if len(sb) < 2: return None, None, None, None, None
    lo = min(b["low"]  for b in sb)
    hi = max(b["high"] for b in sb)
    if hi <= lo: return None, None, None, None, None
    n    = max(1, int(math.ceil((hi - lo) / BIN)))
    bins = [0.0] * n
    for b in sb:
        br = b["high"] - b["low"] if b["high"] > b["low"] else BIN
        for i in range(n):
            bl = lo + i * BIN; bh = bl + BIN
            bins[i] += b["vol"] * max(0.0, min(b["high"], bh) - max(b["low"], bl)) / br
    tv   = sum(bins)
    pi   = bins.index(max(bins))
    poc  = round(lo + pi * BIN + BIN / 2, 2)
    ac   = bins[pi]; li = pi; hi2 = pi
    while ac < tv * VA_PCT:
        vl = bins[li-1]   if li  > 0   else -1
        vh = bins[hi2+1]  if hi2+1 < n else -1
        if vl <= 0 and vh <= 0: break
        if vh >= vl: hi2 += 1; ac += vh
        else:        li  -= 1; ac += vl
    vah = round(lo + hi2 * BIN + BIN, 2)
    val = round(lo + li  * BIN,        2)
    rng_hi = round(hi, 2)
    rng_lo = round(lo, 2)
    return vah, poc, val, rng_hi, rng_lo

def filt(b, df, dt): return [x for x in b if df <= x["dt"] < dt]

# ── Loop viernes ─────────────────────────────────────────────────────────────
results = []
fridays = sorted(set(b["dt"].date() for b in bars if b["dt"].weekday() == 4))

for fri in fridays:
    # VP: 23:00 UTC prev → 13:20 UTC del viernes
    prev  = fri - timedelta(days=1)
    vp_s  = datetime(prev.year, prev.month, prev.day, 23, 0)
    vp_e  = datetime(fri.year,  fri.month,  fri.day,  13, 20)
    vp_b  = filt(bars, vp_s, vp_e)
    if len(vp_b) < 4: continue

    vah, poc, val, rng_hi, rng_lo = calc_vp(vp_b)
    if vah is None: continue

    # Primera vela NY: 14:30 UTC
    ob_list = [b for b in bars if b["dt"].date() == fri
               and b["dt"].hour == 14 and b["dt"].minute == 30]
    if not ob_list: continue
    ob = ob_list[0]

    # Sesión NY completa: 14:30 → 21:00 UTC
    ny = filt(bars,
              datetime(fri.year, fri.month, fri.day, 14, 30),
              datetime(fri.year, fri.month, fri.day, 21,  0))
    if len(ny) < 4: continue

    # Métricas primera vela
    first_bull  = ob["close"] > ob["open"]
    first_pts   = round(ob["close"] - ob["open"], 1)
    first_rng   = round(ob["high"]  - ob["low"],  1)

    # Métricas día NY
    ny_open  = ny[0]["open"];   ny_close = ny[-1]["close"]
    ny_hi    = max(b["high"] for b in ny)
    ny_lo    = min(b["low"]  for b in ny)
    ny_rng   = round(ny_hi - ny_lo, 1)
    day_bull = ny_close > ny_open
    day_pts  = round(ny_close - ny_open, 1)

    # Clasificar patrón ICT
    swept_hi = ny_hi > rng_hi + BUF
    swept_lo = ny_lo < rng_lo - BUF
    close_above = ny_close > rng_hi
    close_below = ny_close < rng_lo

    if   swept_hi and not close_above:  pat = "SWEEP_H_RETURN"
    elif swept_lo and not close_below:  pat = "SWEEP_L_RETURN"
    elif swept_hi and close_above:      pat = "EXPANSION_H"
    elif swept_lo and close_below:      pat = "EXPANSION_L"
    elif ny_rng > 250:                  pat = "NEWS_DRIVE"
    else:                               pat = "ROTATION_POC"

    # ¿Primera vela predice el día?
    continues = first_bull == day_bull

    # Posición 1ra vela respecto al VP
    nyo = ob["open"]
    vp_pos = ("BAJO_VAL"  if nyo < val
              else "ARRIBA_VAH" if nyo > vah
              else "DENTRO_VA")

    results.append({
        "date": fri, "first_bull": first_bull, "first_pts": first_pts,
        "first_rng": first_rng, "day_bull": day_bull, "day_pts": day_pts,
        "ny_rng": ny_rng, "continues": continues, "pat": pat,
        "vp_pos": vp_pos, "vah": vah, "poc": poc, "val": val,
        "rng_hi": rng_hi, "rng_lo": rng_lo,
    })

# ── REPORT ───────────────────────────────────────────────────────────────────
S=("="*64); sep=("-"*64)
bull1 = [r for r in results if r["first_bull"]]
bear1 = [r for r in results if not r["first_bull"]]
cont  = [r for r in results if r["continues"]]

def pct(a,b): return f"{a/b*100:.0f}%" if b else "n/a"
def bar_(p):
    v = int(p.replace("%","")) if "%" in p else 0
    return "█"*(v//10) + "░"*(10-v//10)

print(); print(S)
print("  BACKTEST VIERNES — 1ra Vela 15m NY (Metodología Whale Radar)")
print(S)
print(f"  Viernes analizados : {len(results)}")
print(f"  1ra vela BULL 🟢   : {len(bull1)}  ({pct(len(bull1),len(results))})")
print(f"  1ra vela BEAR 🔴   : {len(bear1)}  ({pct(len(bear1),len(results))})")
print()
print(sep)
print("  ¿La 1ra vela predice la dirección del día?")
print(sep)
b1c=[r for r in bull1 if r["continues"]]
b2c=[r for r in bear1 if r["continues"]]
print(f"  TOTAL continúa dir : {len(cont)}/{len(results)}  {pct(len(cont),len(results))}  {bar_(pct(len(cont),len(results)))}")
print(f"  1raVELA BULL → DIA BULL : {len(b1c)}/{len(bull1)}  {pct(len(b1c),len(bull1))}  {bar_(pct(len(b1c),len(bull1)))}")
print(f"  1raVELA BEAR → DIA BEAR : {len(b2c)}/{len(bear1)}  {pct(len(b2c),len(bear1))}  {bar_(pct(len(b2c),len(bear1)))}")
print()
print(sep)
print("  POR PATRÓN ICT (METODOLOGIA.md)")
print(sep)
for pat in ["SWEEP_H_RETURN","SWEEP_L_RETURN","EXPANSION_H","EXPANSION_L","ROTATION_POC","NEWS_DRIVE"]:
    sub=[r for r in results if r["pat"]==pat]
    if not sub: continue
    bu=sum(1 for r in sub if r["day_bull"])
    print(f"  {pat:<18}: N={len(sub):2}  🟢{pct(bu,len(sub)):>4}  🔴{pct(len(sub)-bu,len(sub)):>4}  rng:{sum(r['ny_rng'] for r in sub)/len(sub):.0f}pts")
print()
print(sep)
print("  POSICIÓN APERTURA vs VALUE AREA")
print(sep)
for pos in ["BAJO_VAL","DENTRO_VA","ARRIBA_VAH"]:
    sub=[r for r in results if r["vp_pos"]==pos]
    if not sub: continue
    bu=sum(1 for r in sub if r["day_bull"])
    cont_=[r for r in sub if r["continues"]]
    print(f"  {pos:<12}: N={len(sub):2}  DIA BULL:{pct(bu,len(sub)):>4}  DIA BEAR:{pct(len(sub)-bu,len(sub)):>4}  1raVela→Dia:{pct(len(cont_),len(sub)):>4}")
print()
print(sep)
print("  RANGOS PROMEDIO")
print(sep)
print(f"  1ra vela rango medio : {sum(r['first_rng'] for r in results)/len(results):.0f} pts")
print(f"  Día NY rango medio   : {sum(r['ny_rng'] for r in results)/len(results):.0f} pts")
if bull1: print(f"  Día BULL rango medio : {sum(r['ny_rng'] for r in bull1)/len(bull1):.0f} pts")
if bear1: print(f"  Día BEAR rango medio : {sum(r['ny_rng'] for r in bear1)/len(bear1):.0f} pts")
print()
print(sep)
print(f"  {'Fecha':<12} {'1raV':<5} {'Pts1':>6} {'Rng1':>6} {'Day':>5} {'DayPts':>8} {'NYRng':>7} {'Pat':<18} {'VP_Pos':<12} {'OK'}")
print(sep)
for r in results:
    e1 = "🟢" if r["first_bull"] else "🔴"
    ed = "🟢" if r["day_bull"]   else "🔴"
    c  = "✅" if r["continues"]  else "❌"
    print(f"  {str(r['date']):<12} {e1}{'B' if r['first_bull'] else 'S':<4} {r['first_pts']:>+6.0f} {r['first_rng']:>6.0f} {ed}{'B' if r['day_bull'] else 'S':<4} {r['day_pts']:>+7.0f} {r['ny_rng']:>7.0f} {r['pat']:<18} {r['vp_pos']:<12} {c}")
