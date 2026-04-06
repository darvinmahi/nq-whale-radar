"""
va_vxn_day_backtest.py
═══════════════════════════════════════════════════════════════
BACKTEST DEFINITIVO: VA Position × VXN × Día de semana
Contra cada sesión NY en el histórico de 15min NQ
═══════════════════════════════════════════════════════════════
"""
import csv, math
from datetime import datetime, date, timedelta
from collections import defaultdict
import yfinance as yf, pandas as pd

VP_BIN = 5.0
VA_PCT = 0.70

# ── NQ 15min ─────────────────────────────────────────────────────────
print("Cargando NQ 15min...")
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            et = datetime.fromisoformat(r["Datetime"].replace("+00:00","")) - timedelta(hours=5)
            cl = float(r["Close"]); hi = float(r["High"]); lo = float(r["Low"]); op = float(r["Open"])
            vol = float(r.get("Volume",0) or 0)
            if cl > 0:
                bars.append({"et":et,"c":cl,"h":hi,"l":lo,"o":op,
                             "vol":vol if vol>0 else (hi-lo)*10})
        except: pass
bars.sort(key=lambda x: x["et"])
by_date = defaultdict(list)
for b in bars: by_date[b["et"].date()].append(b)
print(f"  → {len(by_date)} días con datos ({min(by_date):%Y-%m-%d} → {max(by_date):%Y-%m-%d})")

# ── VXN DIARIO ───────────────────────────────────────────────────────
print("Cargando VXN...")
vxn_raw = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
def col(df,c): return df[c].iloc[:,0] if isinstance(df.columns,pd.MultiIndex) else df[c]
dfv = pd.DataFrame({"v":col(vxn_raw,"Close")}).dropna()
dfv.index = pd.to_datetime(dfv.index).tz_localize(None)

def get_vxn(d):
    prev = dfv[dfv.index.date <= d]
    return float(prev["v"].iloc[-1]) if len(prev) else None

def vxn_zone(v):
    if v is None: return "?"
    if v >= 35: return "XFEAR(>35)"
    if v >= 25: return "FEAR(25-35)"
    if v >= 18: return "NEUT(18-25)"
    return              "GREED(<18)"

# ── VP HELPERS ────────────────────────────────────────────────────────
def calc_vp(bs):
    if len(bs) < 4: return None, None, None
    la = min(b["l"] for b in bs); ha = max(b["h"] for b in bs)
    if ha <= la: return None, None, None
    n = max(1, int(math.ceil((ha-la)/VP_BIN)))
    bins = [0.0]*n
    for b in bs:
        v = b["vol"] if b["vol"]>0 else 1.0
        r = b["h"]-b["l"] if b["h"]>b["l"] else VP_BIN
        for i in range(n):
            bl=la+i*VP_BIN; bh=bl+VP_BIN
            ov=max(0,min(b["h"],bh)-max(b["l"],bl))
            bins[i]+=v*(ov/r)
    total = sum(bins)
    if total == 0: return None, None, None
    pi = bins.index(max(bins)); poc = la+pi*VP_BIN+VP_BIN/2
    va = total*VA_PCT; acc=bins[pi]; li=hi=pi
    while acc < va:
        el=li-1 if li>0 else None; eh=hi+1 if hi<n-1 else None
        vl=bins[el] if el is not None else -1; vh=bins[eh] if eh is not None else -1
        if vl<=0 and vh<=0: break
        if vh >= vl: hi=eh; acc+=vh
        else: li=el; acc+=vl
    return round(la+hi*VP_BIN+VP_BIN,1), round(poc,1), round(la+li*VP_BIN,1)

def sbars(bs, h0, m0, h1, m1):
    return [b for b in bs if
            (b["et"].hour>h0 or (b["et"].hour==h0 and b["et"].minute>=m0)) and
            (b["et"].hour<h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]

# ── CALCULAR SESIONES ─────────────────────────────────────────────────
print("Calculando sesiones NY...")
sessions = []
all_dates = sorted(by_date.keys())

for idx, d in enumerate(all_dates):
    if d.weekday() >= 5: continue
    bs = by_date[d]
    if len(bs) < 8: continue

    prev_d = all_dates[idx-1] if idx > 0 else None
    # VP de referencia: sesión Asia+London del mismo dia + sesión anterior
    ref = []
    if prev_d:
        ref += [b for b in by_date[prev_d] if b["et"].hour >= 15]  # PM anterior
    ref += [b for b in bs if b["et"].hour < 9 or (b["et"].hour==9 and b["et"].minute<25)]  # Pre-market
    ref.sort(key=lambda x: x["et"])
    if len(ref) < 5: continue

    vah, poc, val = calc_vp(ref)
    if vah is None or poc is None or val is None: continue

    # NY session
    ny = sbars(bs, 9, 30, 15, 59)
    if len(ny) < 8: continue

    ny_o = ny[0]["o"]; ny_c = ny[-1]["c"]
    ny_h = max(b["h"] for b in ny); ny_l = min(b["l"] for b in ny)
    ny_pts  = round(ny_c - ny_o, 0)
    ny_rng  = round(ny_h - ny_l, 0)
    ny_pct  = round((ny_c - ny_o) / ny_o * 100, 2)
    ny_dir  = "BULL" if ny_pts > 15 else ("BEAR" if ny_pts < -15 else "FLAT")

    # 30min opening
    ny30 = sbars(bs, 9, 30, 10, 0)
    m30_pts = round(ny30[-1]["c"] - ny_o, 0) if ny30 else 0
    m30_dir = "UP" if m30_pts > 10 else ("DN" if m30_pts < -10 else "FLAT")

    # VA position
    if ny_o > vah:    va_p = "ABOVE"
    elif ny_o < val:  va_p = "BELOW"
    else:             va_p = "INSIDE"

    # Distancia al POC
    poc_dist = round(ny_o - poc, 0)

    vxn_v = get_vxn(d)
    vz    = vxn_zone(vxn_v)

    sessions.append({
        "date": d, "dow": d.weekday(),
        "vah": vah, "poc": poc, "val": val,
        "ny_o": ny_o, "ny_c": ny_c, "ny_h": ny_h, "ny_l": ny_l,
        "ny_pts": ny_pts, "ny_rng": ny_rng, "ny_pct": ny_pct, "ny_dir": ny_dir,
        "m30_pts": m30_pts, "m30_dir": m30_dir,
        "va_p": va_p, "poc_dist": poc_dist,
        "vxn": vxn_v, "vz": vz,
    })

N = len(sessions)
print(f"  → {N} sesiones NY calculadas\n")
SEP = "═" * 86

# ── STATS HELPER ─────────────────────────────────────────────────────
def stats(slist):
    n = len(slist)
    if n == 0: return None
    bull = [s for s in slist if s["ny_dir"]=="BULL"]
    bear = [s for s in slist if s["ny_dir"]=="BEAR"]
    flat = n - len(bull) - len(bear)
    avg_bull_pts = sum(s["ny_pts"] for s in bull)/len(bull) if bull else 0
    avg_bear_pts = sum(s["ny_pts"] for s in bear)/len(bear) if bear else 0
    avg_rng      = sum(s["ny_rng"] for s in slist)/n
    big300 = sum(1 for s in slist if s["ny_rng"]>=300)
    bp = len(bull)/n*100; rp = len(bear)/n*100
    return {"n":n,"bull":len(bull),"bear":len(bear),"flat":flat,
            "bp":bp,"rp":rp,"fp":flat/n*100,
            "avg_bull":avg_bull_pts,"avg_bear":avg_bear_pts,
            "avg_rng":avg_rng,"big300_pct":big300/n*100}

DOW = ["Lun","Mar","Mié","Jue","Vie"]
VA_ORDER  = ["ABOVE","INSIDE","BELOW"]
VXN_ORDER = ["GREED(<18)","NEUT(18-25)","FEAR(25-35)","XFEAR(>35)"]

# ═══════════════════════════════════════════════════════════════════
# 1. VA POSITION SOLO
# ═══════════════════════════════════════════════════════════════════
print(SEP)
print("  1. VA POSITION → DIRECCIÓN SESIÓN NY")
print("     (¿Dónde abre el precio respecto al VA de Asia/London?)")
print(SEP)
baseline = stats(sessions)
print(f"\n  BASELINE {N} sesiones: BULL={baseline['bp']:.0f}%  BEAR={baseline['rp']:.0f}%  avg rng={baseline['avg_rng']:.0f}pt")
print()
print(f"  {'VA':8} {'N':>4}  {'BULL%':>6}  {'BEAR%':>6}  {'FLAT%':>5}  {'UP-pts':>7}  {'DN-pts':>7}  {'Rng':>6}  {'>300':>5}  Señal")
print("  " + "─"*80)
for va in VA_ORDER:
    sl = [s for s in sessions if s["va_p"]==va]
    st = stats(sl)
    if not st: continue
    exp = "BEAR" if va=="ABOVE" else ("BULL" if va=="BELOW" else None)
    if exp=="BEAR": ok = "✅SELL" if st["rp"]>=55 else ("🟡sell" if st["rp"]>=50 else "❌")
    elif exp=="BULL": ok = "✅BUY " if st["bp"]>=55 else ("🟡buy " if st["bp"]>=50 else "❌")
    else: ok = "⚪NEUT"
    print(f"  {va:8} {st['n']:>4}  {st['bp']:>5.0f}%  {st['rp']:>5.0f}%  {st['fp']:>4.0f}%  {st['avg_bull']:>+6.0f}pt  {st['avg_bear']:>+6.0f}pt  {st['avg_rng']:>5.0f}pt  {st['big300_pct']:>4.0f}%  {ok}")

# ═══════════════════════════════════════════════════════════════════
# 2. VXN SOLO
# ═══════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  2. VXN NIVEL → MAGNITUD Y DIRECCIÓN SESIÓN NY")
print(SEP)
print(f"\n  {'VXN':14} {'N':>4}  {'BULL%':>6}  {'BEAR%':>6}  {'UP-pts':>7}  {'DN-pts':>7}  {'Rng AVG':>8}  {'>200pt':>6}  {'>300pt':>6}")
print("  " + "─"*78)
for vz in VXN_ORDER:
    sl = [s for s in sessions if s["vz"]==vz]
    st = stats(sl)
    if not st: continue
    big200 = sum(1 for s in sl if s["ny_rng"]>=200)
    print(f"  {vz:14} {st['n']:>4}  {st['bp']:>5.0f}%  {st['rp']:>5.0f}%  {st['avg_bull']:>+6.0f}pt  {st['avg_bear']:>+6.0f}pt  {st['avg_rng']:>7.0f}pt  {big200/st['n']*100:>5.0f}%  {st['big300_pct']:>5.0f}%")

# ═══════════════════════════════════════════════════════════════════
# 3. DÍA DE SEMANA SOLO
# ═══════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  3. DÍA DE SEMANA → SESIÓN NY")
print(SEP)
print(f"\n  {'Día':5} {'N':>4}  {'BULL%':>6}  {'BEAR%':>6}  {'UP-pts':>7}  {'DN-pts':>7}  {'Rng':>6}  Bias")
print("  " + "─"*65)
for d in range(5):
    sl = [s for s in sessions if s["dow"]==d]
    st = stats(sl)
    if not st: continue
    bias = "📈" if st["bp"]>=53 else ("📉" if st["rp"]>=53 else "⚪")
    print(f"  {DOW[d]:5} {st['n']:>4}  {st['bp']:>5.0f}%  {st['rp']:>5.0f}%  {st['avg_bull']:>+6.0f}pt  {st['avg_bear']:>+6.0f}pt  {st['avg_rng']:>5.0f}pt  {bias}")

# ═══════════════════════════════════════════════════════════════════
# 4. VA × VXN (el combo clave)
# ═══════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  4. VA POSITION × VXN → DIRECCIÓN + MAGNITUD SESIÓN NY")
print("     (El combo más importante para un trader NY)")
print(SEP)
print(f"\n  {'VA':8} {'VXN':14} {'N':>4}  {'BULL%':>6}  {'BEAR%':>6}  {'UP-pts':>7}  {'DN-pts':>7}  {'Rng':>6}  Señal")
print("  " + "─"*82)
for va in VA_ORDER:
    for vz in VXN_ORDER:
        sl = [s for s in sessions if s["va_p"]==va and s["vz"]==vz]
        if len(sl) < 5: continue
        st = stats(sl)
        exp = "BEAR" if va=="ABOVE" else ("BULL" if va=="BELOW" else None)
        if exp=="BEAR": ok = "✅SELL" if st["rp"]>=58 else ("🟡sell" if st["rp"]>=52 else "❌")
        elif exp=="BULL": ok = "✅BUY " if st["bp"]>=58 else ("🟡buy " if st["bp"]>=52 else "❌")
        else: ok = "⚪"
        print(f"  {va:8} {vz:14} {st['n']:>4}  {st['bp']:>5.0f}%  {st['rp']:>5.0f}%  {st['avg_bull']:>+6.0f}pt  {st['avg_bear']:>+6.0f}pt  {st['avg_rng']:>5.0f}pt  {ok}")
    print()

# ═══════════════════════════════════════════════════════════════════
# 5. VA × DÍA DE SEMANA
# ═══════════════════════════════════════════════════════════════════
print(SEP)
print("  5. VA POSITION × DÍA DE SEMANA → SESIÓN NY")
print(SEP)
print(f"\n  {'VA':8} {'Día':5} {'N':>4}  {'BULL%':>6}  {'BEAR%':>6}  {'UP-pts':>7}  {'DN-pts':>7}  Señal")
print("  " + "─"*68)
for va in VA_ORDER:
    for d in range(5):
        sl = [s for s in sessions if s["va_p"]==va and s["dow"]==d]
        if len(sl) < 5: continue
        st = stats(sl)
        exp = "BEAR" if va=="ABOVE" else ("BULL" if va=="BELOW" else None)
        if exp=="BEAR": ok = "✅SELL" if st["rp"]>=60 else ("🟡sell" if st["rp"]>=55 else "❌")
        elif exp=="BULL": ok = "✅BUY " if st["bp"]>=60 else ("🟡buy " if st["bp"]>=55 else "❌")
        else: ok = "⚪"
        print(f"  {va:8} {DOW[d]:5} {st['n']:>4}  {st['bp']:>5.0f}%  {st['rp']:>5.0f}%  {st['avg_bull']:>+6.0f}pt  {st['avg_bear']:>+6.0f}pt  {ok}")
    print()

# ═══════════════════════════════════════════════════════════════════
# 6. TRIPLE: VA × VXN × DÍA (setups de alta probabilidad)
# ═══════════════════════════════════════════════════════════════════
print(SEP)
print("  6. TRIPLE: VA × VXN × DÍA → TOP SETUPS (n>=8)")
print(SEP)
top = []
for va in VA_ORDER:
    for vz in VXN_ORDER:
        for d in range(5):
            sl = [s for s in sessions if s["va_p"]==va and s["vz"]==vz and s["dow"]==d]
            if len(sl) < 8: continue
            st = stats(sl)
            exp = "BEAR" if va=="ABOVE" else ("BULL" if va=="BELOW" else None)
            if exp=="BEAR": wr = st["rp"]; signal="SELL"
            elif exp=="BULL": wr = st["bp"]; signal="BUY "
            else: wr = max(st["bp"],st["rp"]); signal="NEUT"
            top.append((wr, va, vz, DOW[d], st, signal))

top.sort(reverse=True)
print(f"\n  {'Rank':>4}  {'VA':8} {'VXN':14} {'Día':5} {'N':>4}  {'WR%':>5}  {'Señal':5}  {'avg pts':>8}  {'Rng':>6}")
print("  " + "─"*78)
for rank,(wr,va,vz,day,st,sig) in enumerate(top[:20],1):
    if sig=="SELL": ap=st["avg_bear"]; n_ok=st["bear"]
    elif sig=="BUY ": ap=st["avg_bull"]; n_ok=st["bull"]
    else: ap=0; n_ok=0
    mark = "🔥" if wr>=65 else ("✅" if wr>=58 else "🟡")
    print(f"  {rank:>4}  {va:8} {vz:14} {day:5} {st['n']:>4}  {mark}{wr:>4.0f}%  {sig}  {ap:>+7.0f}pt  {st['avg_rng']:>5.0f}pt")

# ═══════════════════════════════════════════════════════════════════
# 7. RESUMEN EJECUTIVO
# ═══════════════════════════════════════════════════════════════════
print()
print(SEP)
print("  RESUMEN EJECUTIVO — LOS NÚMEROS QUE IMPORTAN")
print(SEP)

above_all = stats([s for s in sessions if s["va_p"]=="ABOVE"])
below_all = stats([s for s in sessions if s["va_p"]=="BELOW"])
inside_all= stats([s for s in sessions if s["va_p"]=="INSIDE"])
fear_above= stats([s for s in sessions if s["va_p"]=="ABOVE" and s["vz"] in ["FEAR(25-35)","XFEAR(>35)"]])
fear_below= stats([s for s in sessions if s["va_p"]=="BELOW" and s["vz"] in ["FEAR(25-35)","XFEAR(>35)"]])

print(f"""
  VARIABLE MÁS PODEROSA: VA POSITION
  ────────────────────────────────────────────────────────
  NY abre ABOVE VA:  BULL={above_all['bp']:.0f}%  BEAR={above_all['rp']:.0f}%  avg={above_all['avg_bear']:+.0f}pt cuando baja  (n={above_all['n']})
  NY abre INSIDE VA: BULL={inside_all['bp']:.0f}%  BEAR={inside_all['rp']:.0f}%  (n={inside_all['n']})
  NY abre BELOW VA:  BULL={below_all['bp']:.0f}%  BEAR={below_all['rp']:.0f}%  avg={below_all['avg_bull']:+.0f}pt cuando sube  (n={below_all['n']})

  VXN AMPLIFICA LA MAGNITUD (no cambia dirección):
  ────────────────────────────────────────────────────────
  Con FEAR/XFEAR + ABOVE VA: BEAR={fear_above['rp']:.0f}%  avg bajada={fear_above['avg_bear']:+.0f}pt  (n={fear_above['n']})
  Con FEAR/XFEAR + BELOW VA: BULL={fear_below['bp']:.0f}%  avg subida={fear_below['avg_bull']:+.0f}pt  (n={fear_below['n']})
""")

print("  REGLAS DE TRADING CONFIRMADAS CON DATOS:")
print("  ────────────────────────────────────────────────────────")
# Top 5 setup SELL
sell_tops = [(wr,va,vz,day,st) for wr,va,vz,day,st,sig in top if sig=="SELL"][:5]
print("  TOP SETUPS VENTA (ABOVE VA):")
for wr,va,vz,day,st in sell_tops:
    print(f"    {day} + {vz:14} → BEAR {wr:.0f}% | avg {st['avg_bear']:+.0f}pt | rng {st['avg_rng']:.0f}pt (n={st['n']})")
buy_tops = [(wr,va,vz,day,st) for wr,va,vz,day,st,sig in top if sig=="BUY "][:5]
print()
print("  TOP SETUPS COMPRA (BELOW VA):")
for wr,va,vz,day,st in buy_tops:
    print(f"    {day} + {vz:14} → BULL {wr:.0f}% | avg {st['avg_bull']:+.0f}pt | rng {st['avg_rng']:.0f}pt (n={st['n']})")
print()
print(SEP)
