"""
backtest_viernes_base_uniforme.py
Todos los porcentajes sobre la misma base N total.
No hay subgrupos con distintos denominadores.
"""
import csv, math, sys
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV   = "data/research/nq_15m_intraday.csv"
BUF   = 20.0; VA_PCT = 0.70; BIN = 5.0

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
                             "open": float(r.get("Open",0) or 0),
                             "high": float(r.get("High",0) or 0),
                             "low":  float(r.get("Low", 0) or 0),
                             "close": cl, "vol": 1.0})
        except: pass
bars.sort(key=lambda x: x["dt"])

def calc_vp(sb):
    if len(sb) < 2: return None, None, None, None, None
    lo = min(b["low"]  for b in sb); hi = max(b["high"] for b in sb)
    if hi <= lo: return None, None, None, None, None
    n = max(1, int(math.ceil((hi-lo)/BIN))); bins = [0.0]*n
    for b in sb:
        br = b["high"]-b["low"] if b["high"] > b["low"] else BIN
        for i in range(n):
            bl = lo+i*BIN; bh = bl+BIN
            bins[i] += b["vol"] * max(0.0, min(b["high"],bh) - max(b["low"],bl)) / br
    tv = sum(bins); pi = bins.index(max(bins)); ac = bins[pi]; li = pi; hi2 = pi
    while ac < tv*VA_PCT:
        vl = bins[li-1] if li>0 else -1; vh = bins[hi2+1] if hi2+1<n else -1
        if vl<=0 and vh<=0: break
        if vh >= vl: hi2 += 1; ac += vh
        else:        li  -= 1; ac += vl
    poc = round(lo+pi*BIN+BIN/2, 2)
    return round(lo+hi2*BIN+BIN,2), round(poc,2), round(lo+li*BIN,2), round(hi,2), round(lo,2)

def filt(b, df, dt): return [x for x in b if df <= x["dt"] < dt]

# ── Loop viernes ──────────────────────────────────────────────────────────────
res = []
fridays = sorted(set(b["dt"].date() for b in bars if b["dt"].weekday() == 4))
for fri in fridays:
    prev = fri - timedelta(days=1)
    vp_b = filt(bars, datetime(prev.year, prev.month, prev.day, 23, 0),
                      datetime(fri.year,  fri.month,  fri.day,  13, 20))
    if len(vp_b) < 4: continue
    vah, poc, val, rng_hi, rng_lo = calc_vp(vp_b)
    if vah is None: continue
    ob_l = [b for b in bars if b["dt"].date()==fri and b["dt"].hour==14 and b["dt"].minute==30]
    if not ob_l: continue
    ob = ob_l[0]
    ny = filt(bars, datetime(fri.year,fri.month,fri.day,14,30),
                    datetime(fri.year,fri.month,fri.day,21, 0))
    if len(ny) < 4: continue

    fb   = ob["close"] > ob["open"]
    ny_hi = max(b["high"] for b in ny); ny_lo = min(b["low"] for b in ny)
    ny_rng = ny_hi - ny_lo; day_bull = ny[-1]["close"] > ny[0]["open"]
    sh = ny_hi > rng_hi+BUF; sl = ny_lo < rng_lo-BUF
    ca = ny[-1]["close"] > rng_hi; cb = ny[-1]["close"] < rng_lo

    if   sh and not ca: pat = "SWEEP_H_RETURN"
    elif sl and not cb: pat = "SWEEP_L_RETURN"
    elif sh and ca:     pat = "EXPANSION_H"
    elif sl and cb:     pat = "EXPANSION_L"
    elif ny_rng > 250:  pat = "NEWS_DRIVE"
    else:               pat = "ROTATION_POC"

    nyo = ob["open"]
    vp  = "BAJO_VAL" if nyo<val else "ARRIBA_VAH" if nyo>vah else "DENTRO_VA"
    res.append({"fb": fb, "db": day_bull, "ok": fb==day_bull, "pat": pat, "vp": vp})

N = len(res)
S = "="*72; sep = "-"*72

# ─── REPORTE ─────────────────────────────────────────────────────────────────
print()
print(S)
print(f"  BACKTEST VIERNES  |  Base uniforme N={N} dias  (2017-2026)")
print(f"  TODOS los porcentajes son  X / {N}")
print(S)

ok_total = sum(1 for r in res if r["ok"])
fb_n = sum(1 for r in res if r["fb"]); sb_n = N - fb_n
ok_b = sum(1 for r in res if r["fb"] and r["ok"])
ok_s = sum(1 for r in res if not r["fb"] and r["ok"])

print()
print(f"  La 1ra vela 15m predice la dir del DIA:")
print(sep)
print(f"  TOTAL aciertos        : {ok_total}/{N} = {ok_total/N*100:.0f}%")
print(f"  -- 1raVela BULL acierta : {ok_b}/{N} = {ok_b/N*100:.0f}%  (hay {fb_n} velas BULL)")
print(f"  -- 1raVela BEAR acierta : {ok_s}/{N} = {ok_s/N*100:.0f}%  (hay {sb_n} velas BEAR)")
print()
print(f"  *Dentro de las BULL: {ok_b}/{fb_n} = {ok_b/fb_n*100:.0f}%  | Dentro de las BEAR: {ok_s}/{sb_n} = {ok_s/sb_n*100:.0f}%")
print()

# Por patron: todo expresado sobre N
print(sep)
print(f"  POR PATRON ICT  |  Dias/185 = cobertura  |  Acierto/185 = aporte al total")
print(sep)
hdr = f"  {'Patron':<18}  {'Dias':>5}  {'%Total':>7}  {'Acierto1raV':>12}  {'%de185':>7}  {'%enPatron':>9}"
print(hdr); print(sep)
for pat in ["ROTATION_POC","EXPANSION_H","EXPANSION_L","NEWS_DRIVE","SWEEP_L_RETURN","SWEEP_H_RETURN"]:
    sub = [r for r in res if r["pat"]==pat]
    if not sub: continue
    n2 = len(sub); ok2 = sum(1 for r in sub if r["ok"])
    print(f"  {pat:<18}  {n2:>5}  {n2/N*100:>6.0f}%  {ok2:>12}  {ok2/N*100:>6.0f}%  {ok2/n2*100:>8.0f}%")

print()
print(f"  Interpretacion: '%de185' = cuanto aporta ese patron al 64% global")
print()

# Por VP pos: todo sobre N
print(sep)
print(f"  POR POSICION VP  |  base uniforme N={N}")
print(sep)
hdr2 = f"  {'VP Pos':<12}  {'Dias':>5}  {'%Total':>7}  {'Acierto1raV':>12}  {'%de185':>7}  {'%enPos':>7}"
print(hdr2); print(sep)
for pos in ["BAJO_VAL","DENTRO_VA","ARRIBA_VAH"]:
    sub = [r for r in res if r["vp"]==pos]
    if not sub: continue
    n2 = len(sub); ok2 = sum(1 for r in sub if r["ok"])
    print(f"  {pos:<12}  {n2:>5}  {n2/N*100:>6.0f}%  {ok2:>12}  {ok2/N*100:>6.0f}%  {ok2/n2*100:>7.0f}%")

print()
print(sep)
print(f"  CHECK: suma aciertos por patron debe ser {ok_total}")
check = sum(sum(1 for r in res if r["pat"]==p and r["ok"])
            for p in ["ROTATION_POC","EXPANSION_H","EXPANSION_L","NEWS_DRIVE","SWEEP_L_RETURN","SWEEP_H_RETURN"])
print(f"  Suma real = {check}  {'OK' if check==ok_total else 'ERROR'}")
print()
