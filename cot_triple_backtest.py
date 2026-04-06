"""
cot_triple_backtest.py
═══════════════════════════════════════════════════════════════
Backtest completo del COT Triple Signal (222 semanas)
Formula: SCORE = (AM_idx × 0.50) + (LEV_idx × 0.35) + (FLOW × 0.15)

Para cada semana:
  - Calcula el SCORE con datos COT del martes
  - Mide la dirección NQ de la semana SIGUIENTE (más realista: COT se publica viernes)
  - Clasifica: BULL (>0.5%), BEAR (<-0.5%), FLAT (entre)
  - Calcula winrate por bucket de score

Además:
  - Test de pesos óptimos (grid search)
  - Alerta de liquidación (AM caída >20pts en 4 semanas)
  - Detalle semana a semana de los últimos 52
═══════════════════════════════════════════════════════════════
"""
import csv, json
from datetime import datetime, date, timedelta
from collections import defaultdict
import yfinance as yf, pandas as pd
import itertools

WINDOW   = 52    # semanas para LEV/AM index
FLOW_W   = 156   # 3 años para Commercial FLOW
BULL_TH  = 0.005  # >0.5% = BULL week
BEAR_TH  = -0.005 # <-0.5% = BEAR week

# ── THRESHOLDS A TESTEAR ─────────────────────────────────────────────
THRESHOLDS = [
    (70, "ALCISTA FUERTE"),
    (55, "ALCISTA"),
    (45, "NEUTRAL"),
    (35, "PRECAUCIÓN"),
    (0,  "BAJISTA FUERTE"),
]

SEP = "=" * 90

# ── 1. CARGAR COT ─────────────────────────────────────────────────────
print("Cargando COT (222 semanas)...")
cot = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            ll  = int(r.get("Lev_Money_Positions_Long_All",  0) or 0)
            ls  = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
            al  = int(r.get("Asset_Mgr_Positions_Long_All",  0) or 0)
            as_ = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            ds  = int(r.get("Dealer_Positions_Short_All",    0) or 0)
            cot.append({"date":d, "lev_net":ll-ls, "am_net":al-as_, "com_s":ds})
        except:
            pass
cot.sort(key=lambda x: x["date"])
N_COT = len(cot)
print(f"  → {N_COT} semanas cargadas ({cot[0]['date']} → {cot[-1]['date']})")

# ── 2. CALCULAR ÍNDICES ───────────────────────────────────────────────
lev_nets = [r["lev_net"] for r in cot]
am_nets  = [r["am_net"]  for r in cot]

for i, r in enumerate(cot):
    # LEV Index %
    w = lev_nets[max(0,i-WINDOW+1):i+1]
    r["lev_idx"] = round((r["lev_net"]-min(w))/(max(w)-min(w))*100,2) if max(w)!=min(w) else 50.0
    # AM Index %
    w = am_nets[max(0,i-WINDOW+1):i+1]
    r["am_idx"] = round((r["am_net"]-min(w))/(max(w)-min(w))*100,2) if max(w)!=min(w) else 50.0
    # AM caída 4 semanas
    if i >= 4:
        r["am_drop4"] = r["am_idx"] - cot[i-4]["am_idx"]
    else:
        r["am_drop4"] = 0.0
    # Commercial FLOW
    delta = (cot[i]["com_s"] - cot[i-1]["com_s"]) if i>0 else 0
    r["com_delta"] = delta

com_deltas = [r["com_delta"] for r in cot]
for i, r in enumerate(cot):
    w = com_deltas[max(0,i-FLOW_W+1):i+1]
    mx,mn = max(w),min(w)
    r["flow"] = round((mx-r["com_delta"])/(mx-mn)*100,2) if mx!=mn else 50.0

def calc_score(r, w_am=0.50, w_lev=0.35, w_flow=0.15):
    return round(r["am_idx"]*w_am + r["lev_idx"]*w_lev + r["flow"]*w_flow, 1)

for r in cot:
    r["score"] = calc_score(r)

# ── 3. CARGAR NQ SEMANAL ──────────────────────────────────────────────
print("Descargando NQ semanal...")
nq = yf.download("NQ=F", period="5y", interval="1wk", auto_adjust=True, progress=False)
def col(df,c): return df[c].iloc[:,0] if isinstance(df.columns,pd.MultiIndex) else df[c]
nq_w = pd.DataFrame({"open":col(nq,"Open"),"close":col(nq,"Close")}).dropna()
nq_w.index = pd.to_datetime(nq_w.index).tz_localize(None)
nq_w["ret"] = (nq_w["close"] - nq_w["open"]) / nq_w["open"]
# Dirección de la semana
def nq_dir(ret):
    if ret > BULL_TH: return "BULL"
    if ret < BEAR_TH: return "BEAR"
    return "FLAT"
nq_w["dir"] = nq_w["ret"].apply(nq_dir)
print(f"  → NQ semanas: {len(nq_w)} ({nq_w.index[0].date()} → {nq_w.index[-1].date()})")

# ── 4. MATCHEAR COT → SIGUIENTE SEMANA NQ ────────────────────────────
# COT se publica el viernes después del martes de reporte
# → usamos la siguente semana del lunes siguiente al reporte
matched = []
nq_dates = nq_w.index.tolist()

for i, r in enumerate(cot[WINDOW:], start=WINDOW):
    cot_date = r["date"]
    # Lunes siguiente al report date
    days_to_mon = (7 - cot_date.weekday()) % 7
    if days_to_mon == 0: days_to_mon = 7
    next_mon = cot_date + timedelta(days=days_to_mon)
    next_mon_ts = pd.Timestamp(next_mon)
    # Buscar semana NQ más cercana a ese lunes
    valid = [d for d in nq_dates if d >= next_mon_ts - timedelta(days=3)]
    if not valid: continue
    nq_date = min(valid, key=lambda d: abs((d - next_mon_ts).days))
    if abs((nq_date - next_mon_ts).days) > 7: continue
    row = nq_w.loc[nq_date]
    am_alert = r["am_drop4"] < -20
    matched.append({
        "cot_date":  cot_date,
        "nq_date":   nq_date.date(),
        "lev_idx":   r["lev_idx"],
        "am_idx":    r["am_idx"],
        "flow":      r["flow"],
        "score":     r["score"],
        "am_drop4":  r["am_drop4"],
        "am_alert":  am_alert,
        "nq_ret":    round(row["ret"]*100, 2),
        "nq_dir":    row["dir"],
    })

print(f"  → Semanas matcheadas: {len(matched)}")
print()

# ── 5. ANÁLISIS POR BUCKET ────────────────────────────────────────────
def score_bucket(s):
    if s > 70: return "A: >70 ALCISTA FUERTE"
    if s > 55: return "B: 55-70 ALCISTA"
    if s > 45: return "C: 45-55 NEUTRAL"
    if s > 35: return "D: 35-45 PRECAUCIÓN"
    return              "E: <35 BAJISTA FUERTE"

buckets = defaultdict(lambda: {"n":0,"bull":0,"bear":0,"flat":0,"rets":[]})
for m in matched:
    b = score_bucket(m["score"])
    buckets[b]["n"]    += 1
    buckets[b][m["nq_dir"].lower()] += 1
    buckets[b]["rets"].append(m["nq_ret"])

print(SEP)
print("  RESULTADO POR BUCKET DE SCORE → DIRECCIÓN SEMANA SIGUIENTE NQ")
print(SEP)
print(f"  {'Bucket':30} {'N':>4} {'BULL%':>7} {'BEAR%':>7} {'FLAT%':>7} {'RetAvg':>8}  Señal correcta")
print("  " + "-"*80)

SIGNAL_CORRECT = {
    "A: >70 ALCISTA FUERTE":  "BULL",
    "B: 55-70 ALCISTA":       "BULL",
    "C: 45-55 NEUTRAL":       None,
    "D: 35-45 PRECAUCIÓN":    "BEAR",
    "E: <35 BAJISTA FUERTE":  "BEAR",
}

total_correct = 0; total_signals = 0
for b in sorted(buckets.keys()):
    d = buckets[b]
    n = d["n"]
    if n == 0: continue
    bp = d["bull"]/n*100
    rp = d["bear"]/n*100
    fp = d["flat"]/n*100
    avg = sum(d["rets"])/n
    target = SIGNAL_CORRECT[b]
    if target == "BULL":
        correct = d["bull"]; marker = "✅" if bp>=50 else "❌"
    elif target == "BEAR":
        correct = d["bear"]; marker = "✅" if rp>=50 else "❌"
    else:
        correct = d["flat"]; marker = "⚪"
    if target:
        pct_correct = correct/n*100
        total_correct += correct; total_signals += n
        print(f"  {b:30} {n:>4} {bp:>6.0f}% {rp:>6.0f}% {fp:>6.0f}% {avg:>+7.2f}%  {marker} {pct_correct:.0f}%")
    else:
        print(f"  {b:30} {n:>4} {bp:>6.0f}% {rp:>6.0f}% {fp:>6.0f}% {avg:>+7.2f}%  {marker} neutral")

print("  " + "-"*80)
print(f"  WIN RATE TOTAL (sin neutral): {total_correct}/{total_signals} = {total_correct/total_signals*100:.1f}%")
print()

# ── 6. ALERTA LIQUIDACIÓN ─────────────────────────────────────────────
alerts = [m for m in matched if m["am_alert"]]
bull_after_alert = sum(1 for m in alerts if m["nq_dir"]=="BULL")
bear_after_alert = sum(1 for m in alerts if m["nq_dir"]=="BEAR")
print(SEP)
print("  ALERTA LIQUIDACIÓN — AM cayó >20 pts en 4 semanas")
print(SEP)
print(f"  Total alertas activadas: {len(alerts)}")
if alerts:
    print(f"  NQ semana siguiente → BULL: {bull_after_alert} ({bull_after_alert/len(alerts)*100:.0f}%)")
    print(f"  NQ semana siguiente → BEAR: {bear_after_alert} ({bear_after_alert/len(alerts)*100:.0f}%)")
    print(f"  → {'BAJISTA' if bear_after_alert>bull_after_alert else 'ALCISTA'} (alerta es {('útil' if bear_after_alert>bull_after_alert else 'no útil')} como señal bajista)")
print()

# ── 7. GRID SEARCH — PESOS ÓPTIMOS ───────────────────────────────────
print(SEP)
print("  GRID SEARCH: mejores pesos (AM, LEV, FLOW) → maximizar winrate")
print(SEP)

best = []
for w_am in [x/10 for x in range(2,8)]:      # 0.2 a 0.7
    for w_lev in [x/10 for x in range(1,6)]:  # 0.1 a 0.5
        w_flow = round(1 - w_am - w_lev, 1)
        if w_flow < 0 or w_flow > 0.5: continue

        tot_ok = 0; tot_n = 0
        for m in matched:
            r_score = m["am_idx"]*w_am + m["lev_idx"]*w_lev + m["flow"]*w_flow
            b = score_bucket(r_score)
            target = SIGNAL_CORRECT[b]
            if target is None: continue
            tot_n += 1
            if m["nq_dir"] == target: tot_ok += 1

        if tot_n > 0:
            wr = tot_ok/tot_n*100
            best.append((wr, w_am, w_lev, w_flow, tot_ok, tot_n))

best.sort(reverse=True)
print(f"  {'AM':>6} {'LEV':>6} {'FLOW':>6} {'Correct':>9} {'WinRate':>8}")
print("  " + "-"*45)
for wr, wa, wl, wf, ok, n in best[:10]:
    marker = " ← ACTUAL" if (wa==0.50 and wl==0.35) else ""
    print(f"  {wa:>5.0%} {wl:>5.0%} {wf:>5.0%} {ok:>4}/{n:<4} {wr:>7.1f}%{marker}")
print()

# ── 8. ÚLTIMAS 20 SEMANAS DETALLE ────────────────────────────────────
print(SEP)
print("  DETALLE — ÚLTIMAS 20 SEMANAS COT vs NQ")
print(SEP)
print(f"  {'COT Fecha':12} {'AM%':>6} {'LEV%':>6} {'FLOW':>6} {'SCORE':>6} {'Señal':20} {'NQ Dir':6} {'NQ Ret':>8} {'Alert':6} OK?")
print("  " + "-"*100)

for m in matched[-20:]:
    b = score_bucket(m["score"])
    label = b.split(" ",1)[1]  # quitar la letra
    target = SIGNAL_CORRECT[b]
    if target:
        ok = "✅" if m["nq_dir"]==target else "❌"
    else:
        ok = "⚪"
    alert_str = "⚠️ LIQ" if m["am_alert"] else ""
    dc = m["nq_dir"]
    print(f"  {str(m['cot_date']):12} {m['am_idx']:>5.1f}% {m['lev_idx']:>5.1f}% {m['flow']:>5.1f} {m['score']:>6.1f} {label:20} {dc:6} {m['nq_ret']:>+7.2f}% {alert_str:6} {ok}")

print()
print(SEP)
print("  SCORE HOY (última semana COT disponible):")
last = cot[-1]
print(f"  AM Index:  {last['am_idx']:.1f}%")
print(f"  LEV Index: {last['lev_idx']:.1f}%")
print(f"  FLOW:      {last['flow']:.1f}")
print(f"  SCORE:     {last['score']:.1f}")
print(f"  SEÑAL:     {score_bucket(last['score']).split(' ',1)[1]}")
if last.get("am_drop4",0) < -20:
    print(f"  ⚠️  ALERTA LIQUIDACIÓN: AM cayó {last['am_drop4']:.1f}pts en 4 semanas")
print(SEP)
