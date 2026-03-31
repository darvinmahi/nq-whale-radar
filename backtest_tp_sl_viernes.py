"""
backtest_tp_sl_viernes.py
Entrada: cierre de la 1ra vela 15m (9:30-9:45 ET = 14:30-14:45 UTC)
Dirección: la de la 1ra vela (bull → long, bear → short)
SL fijo: 50 pts
TP testados: 20, 30, 50, 80, 100, 150 pts
Barra a barra hasta que toca TP o SL (o cierre de sesión 16:00 ET)
"""
import sys, csv, math
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV = "data/research/nq_15m_intraday.csv"

# ── Cargar barras 15m ─────────────────────────────────────────────────────────
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

def filt(b, df, dt): return [x for x in b if df <= x["dt"] < dt]

# ── Parámetros ────────────────────────────────────────────────────────────────
SL_PTS  = 50
TP_LIST = [20, 30, 50, 80, 100, 150]

results = []
detail  = []

fridays = sorted(set(b["dt"].date() for b in bars if b["dt"].weekday() == 4))

for fri in fridays:
    # 1ra vela: 14:30 UTC (9:30 ET)
    first = [b for b in bars if b["dt"].date() == fri
             and b["dt"].hour == 14 and b["dt"].minute == 30]
    if not first: continue
    f1 = first[0]

    is_long = f1["close"] > f1["open"]
    if f1["close"] == f1["open"]: continue   # doji ignorado

    entry = f1["close"]

    # Barras post-entrada: de 14:45 UTC hasta 21:00 UTC (16:00 ET)
    session = filt(bars,
                   datetime(fri.year, fri.month, fri.day, 14, 45),
                   datetime(fri.year, fri.month, fri.day, 21,  0))
    if not session: continue

    # Simular barra a barra
    tp_results = {}   # tp_pts → True/False/None (hit TP / hit SL / no touch)
    tp_bar     = {}   # tp_pts → cuántas barras tardó

    for tp_pts in TP_LIST:
        tp_price = (entry + tp_pts) if is_long else (entry - tp_pts)
        sl_price = (entry - SL_PTS) if is_long else (entry + SL_PTS)
        hit = None
        for idx, b in enumerate(session):
            if is_long:
                if b["high"] >= tp_price:   hit = "TP"; tp_bar[tp_pts] = idx+1; break
                if b["low"]  <= sl_price:   hit = "SL"; tp_bar[tp_pts] = idx+1; break
            else:
                if b["low"]  <= tp_price:   hit = "TP"; tp_bar[tp_pts] = idx+1; break
                if b["high"] >= sl_price:   hit = "SL"; tp_bar[tp_pts] = idx+1; break
        if hit is None:
            tp_bar[tp_pts] = len(session)
            # cierre de sesión: ¿quedó en ganancia o pérdida?
            last_price = session[-1]["close"]
            hit = "EOD_WIN"  if ((is_long and last_price > entry) or
                                 (not is_long and last_price < entry)) else "EOD_LOSS"
        tp_results[tp_pts] = hit

    # Determinar si el día continuó (el cierre de NY supera la 1ra vela)
    last_close = session[-1]["close"]
    day_continues = (is_long and last_close > entry) or (not is_long and last_close < entry)

    results.append({"date": fri, "is_long": is_long, "entry": entry,
                    "tp": tp_results, "bar": tp_bar,
                    "day_cont": day_continues,
                    "f1_rng": round(f1["high"] - f1["low"], 1)})
    detail.append((fri, "LONG" if is_long else "SHORT", round(entry,1), tp_results))

N = len(results)
if N == 0:
    print("Sin datos."); exit()

S = "="*72; sep = "-"*72

print()
print(S)
print(f"  BACKTEST TP/SL | Entrada 1ra vela 15m viernes NY")
print(f"  SL fijo: {SL_PTS} pts | N={N} viernes (2017-2026)")
print(S)
print()
print(f"  {'TP':>6}  {'Hit TP':>8}  {'Hit SL':>8}  {'EOD':>8}  {'Win%':>6}  {'R:R':>6}  {'BarasPromTP':>12}")
print(sep)

for tp in TP_LIST:
    hit_tp  = sum(1 for r in results if r["tp"][tp] == "TP")
    hit_sl  = sum(1 for r in results if r["tp"][tp] == "SL")
    eod_win = sum(1 for r in results if r["tp"][tp] == "EOD_WIN")
    eod_los = sum(1 for r in results if r["tp"][tp] == "EOD_LOSS")
    total_win = hit_tp + eod_win          # todo lo que no tocó SL y ganó
    win_pct = (hit_tp) / N * 100         # sólo los que tocaron TP limpio
    rr = tp / SL_PTS
    # Barras hasta tocar TP (solo los que tocaron TP)
    bars_tp = [r["bar"][tp] for r in results if r["tp"][tp] == "TP"]
    avg_bar = sum(bars_tp)/len(bars_tp)*15 if bars_tp else 0  # en minutos
    print(f"  {tp:>5}pts  {hit_tp:>6} ({hit_tp/N*100:.0f}%)  {hit_sl:>6} ({hit_sl/N*100:.0f}%)  {eod_win:>3}W/{eod_los:>3}L  {win_pct:>5.0f}%  {rr:>5.1f}x  {avg_bar:>8.0f}min")

print()
print(sep)
print(f"  NOTA: Win% = solo los que tocaron TP limpio antes del SL")
print(f"        EOD  = sesion cerro sin tocar TP ni SL")
print()

# ── Breakdown por VP position ──────────────────────────────────────────────────
BIN=5.0; VA_PCT=0.70; BUF=20.0

def calc_vp_simple(sb):
    if len(sb) < 2: return None, None, None
    lo = min(b["low"] for b in sb); hi = max(b["high"] for b in sb)
    if hi <= lo: return None, None, None
    n = max(1, int(math.ceil((hi-lo)/BIN))); bins=[0.0]*n
    for b in sb:
        br = b["high"]-b["low"] if b["high"]>b["low"] else BIN
        for i in range(n):
            bl=lo+i*BIN; bh=bl+BIN
            bins[i] += max(0.0, min(b["high"],bh)-max(b["low"],bl))/br
    tv=sum(bins); pi=bins.index(max(bins)); ac=bins[pi]; li=pi; hi2=pi
    while ac < tv*VA_PCT:
        vl=bins[li-1] if li>0 else -1; vh=bins[hi2+1] if hi2+1<n else -1
        if vl<=0 and vh<=0: break
        if vh>=vl: hi2+=1; ac+=vh
        else:      li-=1;  ac+=vl
    return round(lo+hi2*BIN+BIN,2), round(lo+li*BIN,2), round(lo,2)

# Clasificar por VP pos y recalcular TP@50 hit rate
vp_classified = []
for r in results:
    fri = r["date"]
    prev = fri - timedelta(days=1)
    vp_b = [b for b in bars if datetime(prev.year,prev.month,prev.day,23,0)
            <= b["dt"] < datetime(fri.year,fri.month,fri.day,13,20)]
    if len(vp_b) < 4: continue
    vah, val, _ = calc_vp_simple(vp_b)
    if vah is None: continue
    nyo = r["entry"]
    pos = "BAJO_VAL" if nyo < val else "ARRIBA_VAH" if nyo > vah else "DENTRO_VA"
    vp_classified.append({"vp": pos, "tp": r["tp"], "date": fri})

print(sep)
print(f"  HIT TP vs SL por POSICION VP (TP=50pts, SL=50pts) | N_clasificados={len(vp_classified)}")
print(sep)
print(f"  {'VP Pos':<12}  {'N':>5}  {'TP50 hit':>10}  {'SL50 hit':>10}  {'Win%':>7}")
print(sep)
for pos in ["BAJO_VAL","DENTRO_VA","ARRIBA_VAH"]:
    sub = [r for r in vp_classified if r["vp"]==pos]
    if not sub: continue
    n2 = len(sub)
    tp_h = sum(1 for r in sub if r["tp"][50]=="TP")
    sl_h = sum(1 for r in sub if r["tp"][50]=="SL")
    print(f"  {pos:<12}  {n2:>5}  {tp_h:>7} ({tp_h/n2*100:.0f}%)  {sl_h:>7} ({sl_h/n2*100:.0f}%)  {tp_h/n2*100:>6.0f}%")

print()
print(S)
print(f"  CONCLUSION:")
print(f"  La 1ra vela de 9:30 viernes NY:", end=" ")
best_tp = max(TP_LIST, key=lambda t: sum(1 for r in results if r["tp"][t]=="TP")/N)
best_n  = sum(1 for r in results if r["tp"][best_tp]=="TP")
print(f"toca TP={best_tp}pts el {best_n/N*100:.0f}% ({best_n}/{N})")
print(f"  con SL={SL_PTS}pts")
print()
