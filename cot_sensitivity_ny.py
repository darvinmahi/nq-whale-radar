"""
cot_sensitivity_ny.py
Estudia la SENSIBILIDAD del COT en la sesion NY de los lunes:
  - Cuanto mas negativo el COT (mas shorts institucionales)
  - Cuanto mas rapido y agresivo es el movimiento bajista en NY
  - Cuando el precio llega al VAH (punto de interes), con que fuerza cae
Analiza: primeros 30min / 1H / 2H / NY completo
"""
import csv, math, yfinance as yf, pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict

VP_BIN = 5.0
VA_PCT = 0.70

# ─── 1. NQ 15min ──────────────────────────────────────────────
print("Cargando NQ 15min...")
nq_bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_et = datetime.fromisoformat(r["Datetime"].replace("+00:00","")) - timedelta(hours=5)
            cl=float(r["Close"]); hi=float(r["High"])
            lo=float(r["Low"]);   op=float(r["Open"])
            vol=float(r.get("Volume",0) or 0)
            if cl > 0:
                nq_bars.append({"et":dt_et,"c":cl,"h":hi,"l":lo,"o":op,
                                "vol":vol if vol>0 else (hi-lo)*10})
        except: pass
nq_bars.sort(key=lambda x: x["et"])
by_date = defaultdict(list)
for b in nq_bars: by_date[b["et"].date()].append(b)
print(f"  {len(nq_bars):,} barras")

# ─── 2. VXN + VIX ─────────────────────────────────────────────
print("Descargando VXN + VIX...")
vxn = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
vix = yf.download("^VIX", period="5y", auto_adjust=True, progress=False)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

dfv = pd.DataFrame({"VXN":col(vxn,"Close"),"VIX":col(vix,"Close")}).dropna()
dfv.index = pd.to_datetime(dfv.index).tz_localize(None)
vdates = dfv.index.tolist()

def get_vol(day):
    prev = [d for d in vdates if d < pd.Timestamp(day)]
    if not prev: return None, None
    pd_ = prev[-1]
    return float(dfv.loc[pd_,"VXN"]), float(dfv.loc[pd_,"VIX"])

# ─── 3. COT ────────────────────────────────────────────────────
print("Cargando COT...")
cot_rows = []
try:
    with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d  = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
                ll = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
                ls = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                cot_rows.append({"date":d,"lev_net":ll-ls,"sig":"BULL" if ll>ls else "BEAR"})
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
except: pass

def get_cot(d):
    prev = [r for r in cot_rows if r["date"] <= d]
    return prev[-1] if prev else {"lev_net":0,"sig":"?"}

# ─── 4. ValueProfile ──────────────────────────────────────────
def calc_vp(bars):
    if len(bars) < 3: return None, None, None
    lo_a=min(b["l"] for b in bars); hi_a=max(b["h"] for b in bars)
    if hi_a<=lo_a: return None,None,None
    n=max(1,int(math.ceil((hi_a-lo_a)/VP_BIN)))
    bins=[0.0]*n
    for b in bars:
        vol=b["vol"] if b["vol"]>0 else 1.0
        rng=b["h"]-b["l"] if b["h"]>b["l"] else VP_BIN
        for i in range(n):
            bl=lo_a+i*VP_BIN; bh=bl+VP_BIN
            ov=max(0,min(b["h"],bh)-max(b["l"],bl))
            bins[i]+=vol*(ov/rng)
    total=sum(bins)
    if total==0: return None,None,None
    pi=bins.index(max(bins)); poc=lo_a+pi*VP_BIN+VP_BIN/2
    va=total*VA_PCT; acc=bins[pi]; li=hi=pi
    while acc<va:
        el=li-1 if li>0 else None; eh=hi+1 if hi<n-1 else None
        vl=bins[el] if el is not None else -1
        vh=bins[eh] if eh is not None else -1
        if vl<=0 and vh<=0: break
        if vh>=vl: hi=eh; acc+=vh
        else: li=el; acc+=vl
    return round(lo_a+hi*VP_BIN+VP_BIN,1), round(poc,1), round(lo_a+li*VP_BIN,1)

def dir_label(pct, thr=0.08):
    if pct > thr: return "BULL"
    if pct <-thr: return "BEAR"
    return "FLAT"

def s_bars(bars, h0, m0, h1, m1):
    return [b for b in bars if
            (b["et"].hour>h0 or (b["et"].hour==h0 and b["et"].minute>=m0)) and
            (b["et"].hour<h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]

# ─── 5. Calcular todos los lunes ──────────────────────────────
mondays = sorted([d for d in by_date.keys() if d.weekday()==0], reverse=True)
rows = []

for mon in mondays:
    bars = by_date[mon]
    if len(bars) < 8: continue

    # VP: Asia + London
    sun = mon - timedelta(days=1)
    vp_bars  = [b for b in by_date.get(sun,[]) if b["et"].hour>=18]
    vp_bars += [b for b in bars if b["et"].hour<9 or (b["et"].hour==9 and b["et"].minute<20)]
    vp_bars.sort(key=lambda x: x["et"])
    vah, poc, val = calc_vp(vp_bars)
    if vah is None: continue

    # NY barras por sub-sesion
    ny_30  = s_bars(bars, 9,30, 10, 0)   # 09:30-10:00 (30 min)
    ny_1h  = s_bars(bars, 9,30, 10,30)   # 09:30-10:30 (1H)
    ny_2h  = s_bars(bars, 9,30, 11,30)   # 09:30-11:30 (2H)
    ny_all = s_bars(bars, 9,30, 15,59)   # NY completo

    if not ny_all or len(ny_all)<2: continue
    ny_o = ny_all[0]["o"]

    def sub_stats(sb):
        if not sb: return None
        c=sb[-1]["c"]
        h=max(b["h"] for b in sb); l=min(b["l"] for b in sb)
        mv=(c-ny_o)/ny_o*100  # siempre relativo al open de NY
        rg=(h-l)/ny_o*100
        return {"move":round(mv,2),"range":round(rg,2),
                "hi":round(h,0),"lo":round(l,0),"c":round(c,0)}

    s30  = sub_stats(ny_30)
    s1h  = sub_stats(ny_1h)
    s2h  = sub_stats(ny_2h)
    sall = sub_stats(ny_all)
    if not sall: continue

    # VA position
    if ny_o > vah:   va_p = "ABOVE"
    elif ny_o < val: va_p = "BELOW"
    else:            va_p = "INSIDE"

    # COT + VXN
    cot = get_cot(mon)
    vxn_val, vix_val = get_vol(mon)
    if vxn_val is None: continue

    def vxn_z(v):
        if v>=33: return "XFEAR"
        if v>=25: return "FEAR"
        if v>=18: return "NEUT"
        return "GREED"

    rows.append({
        "mon":mon,
        "vxn":round(vxn_val,1), "vix":round(vix_val,1) if vix_val else 0,
        "zona":vxn_z(vxn_val),
        "lev_net":cot["lev_net"], "cot_sig":cot["sig"],
        "vah":vah, "poc":poc, "val":val,
        "ny_o":ny_o, "va_p":va_p,
        "poc_dist":round(ny_o-poc,0),
        "s30":s30, "s1h":s1h, "s2h":s2h, "sall":sall,
        "ny_dir":dir_label(sall["move"]),
    })

n = len(rows)
print(f"Lunes calculados: {n}")

# ─── 6. COT BUCKETS ───────────────────────────────────────────
# Rangos de COT net (Leveraged Money)
COT_BUCKETS = [
    ("ULTRA BEAR  (< -25k)", lambda x: x < -25000),
    ("BEAR        (-10k→-25k)", lambda x: -25000<=x<-10000),
    ("LEVE BEAR   (-5k→-10k)", lambda x: -10000<=x<-5000),
    ("NEUTRAL     (-5k→+5k)", lambda x: -5000<=x<=5000),
    ("BULL        (>+5k)", lambda x: x > 5000),
]

SEP = "="*95

print(f"\n{SEP}")
print(f"  SENSIBILIDAD COT → MOVIMIENTO NY (todos los lunes, {n} casos)")
print(f"  Pregunta: Cuanto mas bearish el COT, mas agresivo/rapido es el movimiento bajista en NY?")
print(f"{SEP}")

# ─── Tabla principal: NY open ABOVE VA (sell setups) ──────────
print(f"\n  🔴 SELL SETUP: NY abre ABOVE del Value Area pre-NY")
print(f"  (logica: precio sube a zona premium, institucionales venden → ¿como de rapido/fuerte cae?)")
print(f"\n  {'COT Bucket':28} {'n':4}  {'NY BEAR':>7}  {'30min':>7}  {'1H':>7}  {'2H':>7}  {'NY Full':>8}  {'Rango':>7}  {'Pts NQ':>7}")
print(f"  {'─'*90}")

above_all = [r for r in rows if r["va_p"]=="ABOVE"]
for label, fn in COT_BUCKETS:
    sub = [r for r in above_all if fn(r["lev_net"])]
    if not sub: continue
    n_bear = sum(1 for r in sub if r["ny_dir"]=="BEAR")
    avg_30  = sum(r["s30"]["move"]  for r in sub if r["s30"])  / max(1,sum(1 for r in sub if r["s30"]))
    avg_1h  = sum(r["s1h"]["move"]  for r in sub if r["s1h"])  / max(1,sum(1 for r in sub if r["s1h"]))
    avg_2h  = sum(r["s2h"]["move"]  for r in sub if r["s2h"])  / max(1,sum(1 for r in sub if r["s2h"]))
    avg_all = sum(r["sall"]["move"] for r in sub)              / len(sub)
    avg_rng = sum(r["sall"]["range"] for r in sub)             / len(sub)
    pts_nq  = avg_rng * 230
    pct_b   = n_bear/len(sub)*100
    print(f"  {label:28} {len(sub):4d}  {n_bear:4d} {pct_b:3.0f}%  {avg_30:>+6.2f}%  {avg_1h:>+6.2f}%  {avg_2h:>+6.2f}%  {avg_all:>+7.2f}%  {avg_rng:>6.2f}%  {pts_nq:>6.0f}pts")

# ─── Tabla: BUY setups ────────────────────────────────────────
print(f"\n\n  🟢 BUY SETUP: NY abre BELOW del Value Area pre-NY")
print(f"  (logica: precio baja a zona discount, institucionales compran → ¿como de rapido/fuerte sube?)")
print(f"\n  {'COT Bucket':28} {'n':4}  {'NY BULL':>7}  {'30min':>7}  {'1H':>7}  {'2H':>7}  {'NY Full':>8}  {'Rango':>7}  {'Pts NQ':>7}")
print(f"  {'─'*90}")

below_all = [r for r in rows if r["va_p"]=="BELOW"]
for label, fn in COT_BUCKETS:
    sub = [r for r in below_all if fn(r["lev_net"])]
    if not sub: continue
    n_bull = sum(1 for r in sub if r["ny_dir"]=="BULL")
    avg_30  = sum(r["s30"]["move"]  for r in sub if r["s30"])  / max(1,sum(1 for r in sub if r["s30"]))
    avg_1h  = sum(r["s1h"]["move"]  for r in sub if r["s1h"])  / max(1,sum(1 for r in sub if r["s1h"]))
    avg_2h  = sum(r["s2h"]["move"]  for r in sub if r["s2h"])  / max(1,sum(1 for r in sub if r["s2h"]))
    avg_all = sum(r["sall"]["move"] for r in sub)              / len(sub)
    avg_rng = sum(r["sall"]["range"] for r in sub)             / len(sub)
    pts_nq  = avg_rng * 230
    pct_b   = n_bull/len(sub)*100
    print(f"  {label:28} {len(sub):4d}  {n_bull:4d} {pct_b:3.0f}%  {avg_30:>+6.2f}%  {avg_1h:>+6.2f}%  {avg_2h:>+6.2f}%  {avg_all:>+7.2f}%  {avg_rng:>6.2f}%  {pts_nq:>6.0f}pts")

# ─── 7. VELOCIDAD: cuantos puntos en los primeros 30min ───────
print(f"\n{SEP}")
print(f"  VELOCIDAD NY — Puntos NQ en primeros 30min (09:30→10:00)")
print(f"  Comparando SELL setups por nivel COT")
print(f"{'─'*60}")
print(f"  {'COT':28} {'n':4} {'30min pts(abs)':>15} {'30min dir BEAR':>15}")
print(f"  {'─'*60}")

for label, fn in COT_BUCKETS:
    sub = [r for r in above_all if fn(r["lev_net"]) and r["s30"]]
    if not sub: continue
    pts_abs = sum(abs(r["s30"]["move"])*230 for r in sub) / len(sub)
    dir_bear= sum(1 for r in sub if r["s30"]["move"]<-0.05)
    print(f"  {label:28} {len(sub):4d} {pts_abs:>14.0f}pts  {dir_bear:4d}/{len(sub)} = {dir_bear/len(sub)*100:.0f}%")

# ─── 8. CASOS INDIVIDUALES: setups mas limpios ────────────────
print(f"\n{SEP}")
print(f"  CASOS INDIVIDUALES — SELL SETUPS + COT MUY BEARISH (< -10k)")
print(f"  (los movimientos mas agresivos esperados)")
print(f"{'─'*100}")
print(f"  {'Fecha':11} {'VXN':5} {'VIX':5} {'Zona':6} {'LevNet':>9}"
      f"  {'VAH':>6} {'NYo':>6} {'Dist':>5}"
      f"  {'30m':>6} {'1H':>6} {'2H':>6} {'NYfull':>7}"
      f"  {'Dir':4} {'Pts':>5}")

strong_bear = [r for r in above_all if r["lev_net"] < -10000]
strong_bear.sort(key=lambda x: x["lev_net"])  # ordenar por mas bearish

for r in strong_bear:
    s30  = r["s30"]["move"]  if r["s30"]  else 0
    s1h  = r["s1h"]["move"]  if r["s1h"]  else 0
    s2h  = r["s2h"]["move"]  if r["s2h"]  else 0
    sall = r["sall"]["move"]
    pts_30 = round(abs(s30) * 230)
    dist_poc = r["poc_dist"]
    today = " ◄" if r["mon"]==date(2026,3,30) else ""
    win  = "WIN" if r["ny_dir"]=="BEAR" else ("LOSS" if r["ny_dir"]=="BULL" else "FLAT")
    print(
        f"  {r['mon'].strftime('%d %b %Y'):11} {r['vxn']:5.1f} {r['vix']:5.1f} {r['zona']:6} {r['lev_net']:>9,}"
        f"  {r['vah']:>6.0f} {r['ny_o']:>6.0f} {dist_poc:>+5.0f}"
        f"  {s30:>+5.2f}% {s1h:>+5.2f}% {s2h:>+5.2f}% {sall:>+6.2f}%"
        f"  {win:4} ~{pts_30:>4}pts{today}"
    )

# ─── 9. RESUMEN EJECUTIVO ─────────────────────────────────────
print(f"\n{SEP}")
print(f"  CONCLUSION: Sensibilidad COT → Movimiento NY")
print(f"{'─'*70}")

ultra_bear = [r for r in above_all if r["lev_net"] < -25000]
bear_mid   = [r for r in above_all if -25000<=r["lev_net"]<-10000]
neutral    = [r for r in above_all if -10000<=r["lev_net"]<=5000]

def avg_m(lst, key="sall"):
    vals = [r[key]["move"] for r in lst if r[key]]
    return sum(vals)/len(vals) if vals else 0

def avg_pts_30(lst):
    vals = [abs(r["s30"]["move"])*230 for r in lst if r["s30"]]
    return sum(vals)/len(vals) if vals else 0

def bear_pct(lst):
    return sum(1 for r in lst if r["ny_dir"]=="BEAR") / len(lst) * 100 if lst else 0

if ultra_bear:
    print(f"\n  COT ULTRA BEAR (<-25k): n={len(ultra_bear)}")
    print(f"    NY move medio:  {avg_m(ultra_bear):+.2f}%  ({avg_m(ultra_bear)*230:.0f} pts NQ)")
    print(f"    Primeros 30min: {avg_pts_30(ultra_bear):.0f} pts medios")
    print(f"    NY BEAR:        {bear_pct(ultra_bear):.0f}%")
if bear_mid:
    print(f"\n  COT BEAR (-10k a -25k): n={len(bear_mid)}")
    print(f"    NY move medio:  {avg_m(bear_mid):+.2f}%  ({avg_m(bear_mid)*230:.0f} pts NQ)")
    print(f"    Primeros 30min: {avg_pts_30(bear_mid):.0f} pts medios")
    print(f"    NY BEAR:        {bear_pct(bear_mid):.0f}%")
if neutral:
    print(f"\n  COT NEUTRAL (-10k a +5k): n={len(neutral)}")
    print(f"    NY move medio:  {avg_m(neutral):+.2f}%  ({avg_m(neutral)*230:.0f} pts NQ)")
    print(f"    Primeros 30min: {avg_pts_30(neutral):.0f} pts medios")
    print(f"    NY BEAR:        {bear_pct(neutral):.0f}%")

print(f"\n  REGLA: Cuanto mas negativo el COT + ABOVE VA = mas fuerza bajista esperada en NY")
print(f"  Velocidad = primeros 30min son el indicador de intensidad del movimiento")
