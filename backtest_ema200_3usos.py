"""
backtest_ema200_3usos.py
========================================================================
NQ EMA 200 (1m) -- 3 USOS ANALIZADOS

A) IMAN: price far from EMA -> probability it reaches EMA in next N bars
B) DIRECCION: position relative to EMA as trend filter (next N bars drift)
C) RECHAZO: CHoCH real + primer retest (SHORT setup) -- version refinada
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

SYMBOL    = "NQ=F"
DAYS_BACK = 30

SESSIONS = {"Asia":(0,7),"London":(7,13),"NY-AM":(13,17),
            "NY-PM":(17,21),"After":(21,24)}
def sess(h):
    for n,(a,b) in SESSIONS.items():
        if a<=h<b: return n
    return "After"

# ─── Descarga ─────────────────────────────────────────────────────────────────
def download():
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=DAYS_BACK)
    chunks, cur = [], start
    print("  Descargando datos...", flush=True)
    while cur < end:
        ce = min(cur + timedelta(days=6), end)
        try:
            raw = yf.download(SYMBOL,
                              start=cur.strftime("%Y-%m-%d"),
                              end=ce.strftime("%Y-%m-%d"),
                              interval="1m", progress=False, auto_adjust=True)
            if not raw.empty:
                def c(n): return (raw[n].iloc[:,0] if isinstance(raw[n], pd.DataFrame) else raw[n]).values.astype(float)
                chunks.append(pd.DataFrame(
                    {"O":c("Open"),"H":c("High"),"L":c("Low"),"C":c("Close"),"V":c("Volume")},
                    index=raw.index))
                print(f"    {cur.date()} -> {ce.date()} : {len(chunks[-1])} velas")
        except: pass
        cur = ce + timedelta(minutes=1)
    df = pd.concat(chunks).sort_index()
    return df[~df.index.duplicated(keep="first")]

def rsi14(s):
    d=s.diff(); g=d.clip(lower=0).rolling(14).mean()
    l=(-d.clip(upper=0)).rolling(14).mean()
    return 100-100/(1+g/l.replace(0,np.nan))

# ─── Load ─────────────────────────────────────────────────────────────────────
print("\n" + "="*70)
print("  NQ EMA 200 -- 3 USOS (A=Iman / B=Direccion / C=Rechazo)")
print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
print("="*70)

df = download()
n  = len(df)
df["ema"] = df["C"].ewm(span=200,adjust=False).mean()
df["rsi"] = rsi14(df["C"])
df["atr"] = (df["H"]-df["L"]).rolling(14).mean()

C = df["C"].values; H = df["H"].values; L = df["L"].values
O = df["O"].values; E = df["ema"].values
R = df["rsi"].values; ATR = df["atr"].values
IDX = df.index
print(f"\n  Total: {n} velas  ({IDX[0].date()} -> {IDX[-1].date()})\n")

# ========================================================================
# A) IMAN: cuando el precio esta lejos de la EMA, ¿llega a tocarla?
# ========================================================================
print("="*70)
print("  A) EMA COMO IMAN / TARGET")
print("="*70)

LOOK_AHEAD = [15, 30, 60, 120]  # barras para ver si toca la EMA

# Distancia relativa al precio
rows_a = []
warmup = 250
for i in range(warmup, n - 130):
    if np.isnan(E[i]) or E[i]==0: continue
    pct_dist = (C[i] - E[i]) / E[i] * 100  # positivo = sobre EMA
    if abs(pct_dist) < 0.1: continue        # muy cerca, no cuenta

    # bucket de distancia
    ap = abs(pct_dist)
    if   ap < 0.2: bucket = "0.1-0.2%"
    elif ap < 0.4: bucket = "0.2-0.4%"
    elif ap < 0.6: bucket = "0.4-0.6%"
    elif ap < 1.0: bucket = "0.6-1.0%"
    else:          bucket = ">1.0%"

    side = "SOBRE" if pct_dist > 0 else "BAJO"
    hour = IDX[i].hour
    session = sess(hour)

    touched = {}
    for la in LOOK_AHEAD:
        sl = slice(i+1, min(i+la+1, n))
        fut_h = H[sl]; fut_l = L[sl]
        ema_f = E[sl]
        if pct_dist > 0:  # sobre EMA, la EMA es soporte hacia abajo
            hit = any(fut_l[j] <= ema_f[j] for j in range(len(fut_l)))
        else:             # bajo EMA, la EMA es resistencia hacia arriba
            hit = any(fut_h[j] >= ema_f[j] for j in range(len(fut_h)))
        touched[la] = int(hit)

    pts_dist = abs(C[i] - E[i])
    rows_a.append({"bucket":bucket,"side":side,"session":session,
                   "pts_dist":round(pts_dist,1),
                   **{f"hit_{la}b": touched[la] for la in LOOK_AHEAD}})

da = pd.DataFrame(rows_a)

print(f"\n  Muestras analizadas: {len(da)}")
print(f"\n  PROBABILIDAD DE TOCAR EMA segun DISTANCIA:")
print(f"  {'Bucket':<12} {'n':>5} {'15b%':>6} {'30b%':>6} {'60b%':>6} {'120b%':>6}  {'Pts dist':>8}")
for bk in ["0.1-0.2%","0.2-0.4%","0.4-0.6%","0.6-1.0%",">1.0%"]:
    g = da[da["bucket"]==bk]
    if len(g)<5: continue
    h15=g["hit_15b"].mean()*100; h30=g["hit_30b"].mean()*100
    h60=g["hit_60b"].mean()*100; h120=g["hit_120b"].mean()*100
    pd_=g["pts_dist"].mean()
    print(f"  {bk:<12} {len(g):>5} {h15:>5.1f}% {h30:>5.1f}% {h60:>5.1f}% {h120:>5.1f}%  {pd_:>7.1f}pts")

print(f"\n  POR LADO (SOBRE vs BAJO EMA):")
for side in ["SOBRE","BAJO"]:
    g = da[da["side"]==side]
    if len(g)<5: continue
    h60=g["hit_60b"].mean()*100; h120=g["hit_120b"].mean()*100
    print(f"  {side:<6} n={len(g):>4}  60b: {h60:.1f}%  120b: {h120:.1f}%")

print(f"\n  POR SESION (prob de tocar EMA en 60 barras):")
for s in ["Asia","London","NY-AM","NY-PM","After"]:
    g = da[da["session"]==s]
    if len(g)<10: continue
    h60=g["hit_60b"].mean()*100; h120=g["hit_120b"].mean()*100
    print(f"  {s:<8} n={len(g):>4}  60b: {h60:.1f}%  120b: {h120:.1f}%")

# ========================================================================
# B) DIRECCION: EMA como filtro de sesgo
# ========================================================================
print(f"\n{'='*70}")
print("  B) EMA COMO FILTRO DE DIRECCION")
print("="*70)

# Para cada barra: si precio > EMA, ¿cuanto sube en las siguientes N barras?
# Mide el EDGE direccional de estar en el lado correcto de la EMA
FWDS = [5, 15, 30, 60]

rows_b = []
for i in range(warmup, n - 70):
    if np.isnan(E[i]): continue
    above = C[i] > E[i]
    hour = IDX[i].hour
    session = sess(hour)
    pct_dist = abs(C[i] - E[i]) / E[i] * 100

    for fw in FWDS:
        if i + fw >= n: continue
        ret = (C[i+fw] - C[i]) / C[i] * 100  # retorno % en fw barras

        # si estoy SOBRE la EMA el retorno positivo es "correcto"
        # si estoy BAJO  la EMA el retorno negativo es "correcto"
        dir_ret = ret if above else -ret

        rows_b.append({"above":int(above), "session":session, "hour":hour,
                       "fw":fw, "dir_ret":dir_ret, "pct_dist":pct_dist})

db = pd.DataFrame(rows_b)

print(f"\n  Retorno PROMEDIO en la DIRECCION de la EMA (positivo = correcto)")
print(f"\n  {'Horizon':<10} {'SOBRE EMA':>12} {'BAJO EMA':>12} {'DIFERENCIA':>12}")
for fw in FWDS:
    g = db[db["fw"]==fw]
    ab = g[g["above"]==1]["dir_ret"].mean()
    bl = g[g["above"]==0]["dir_ret"].mean()
    print(f"  {fw} barras  {ab:>+10.3f}%  {bl:>+10.3f}%  {ab-bl:>+10.3f}%")

print(f"\n  WIN RATE que el precio CONTINUE en la direccion de la EMA:")
print(f"\n  {'Horizon':<10} {'SOBRE EMA':>12} {'BAJO EMA':>12}")
for fw in FWDS:
    g = db[db["fw"]==fw]
    ab = (g[g["above"]==1]["dir_ret"]>0).mean()*100
    bl = (g[g["above"]==0]["dir_ret"]>0).mean()*100
    print(f"  {fw} barras  {ab:>10.1f}%  {bl:>10.1f}%")

print(f"\n  WIN RATE por SESION (continua en direccion EMA -- 30 barras):")
g30 = db[db["fw"]==30]
for s in ["Asia","London","NY-AM","NY-PM","After"]:
    gs = g30[g30["session"]==s]
    if len(gs)<50: continue
    ab = (gs[gs["above"]==1]["dir_ret"]>0).mean()*100
    bl = (gs[gs["above"]==0]["dir_ret"]>0).mean()*100
    print(f"  {s:<8}  SOBRE={ab:.1f}%  BAJO={bl:.1f}%  n={len(gs)}")

# ========================================================================
# C) RECHAZO: CHoCH real + primer retest (SHORT)
# ========================================================================
print(f"\n{'='*70}")
print("  C) EMA COMO RESISTENCIA (CHoCH REAL + FLIP)")
print("="*70)

MIN_CONSEC    = 3
SWING_LBK     = 30
SWING_SIDE    = 5
BODY_ATR_MULT = 0.35
TOUCH_PTS     = 10
MAX_PB        = 80
MAX_RES       = 60
R_TGTS        = [1,2,3]

def last_sl(lo, before, lbk=30, ns=5):
    s = max(ns, before-lbk); e = before-ns
    bi, bv = -1, np.inf
    for k in range(s,e):
        wl=lo[k-ns:k]; wr=lo[k+1:k+ns+1]
        if len(wl)<ns or len(wr)<ns: continue
        if lo[k]<wl.min() and lo[k]<wr.min() and lo[k]<bv:
            bv=lo[k]; bi=k
    return bi,bv

chochs = []; i=max(SWING_LBK+SWING_SIDE+5,250)
while i < n-MAX_RES-5:
    if not (C[i-1]>E[i-1] and C[i]<E[i]): i+=1; continue
    atr_v = ATR[i] if not np.isnan(ATR[i]) else 10.
    if abs(C[i]-O[i]) < BODY_ATR_MULT*atr_v: i+=1; continue
    consec=sum(1 for k in range(i,min(i+20,n)) if C[k]<E[k] and not (k>i and C[k]>=E[k]))
    # count consecutive properly
    consec=0
    for k in range(i,min(i+20,n)):
        if C[k]<E[k]: consec+=1
        else: break
    if consec<MIN_CONSEC: i+=1; continue
    sl_i, sl_p = last_sl(L, i, SWING_LBK, SWING_SIDE)
    if sl_i<0 or C[i]>=sl_p: i+=1; continue
    chochs.append({"idx":i,"ema":E[i],"consec":consec})
    i+=consec+1

print(f"\n  CHoCH reales: {len(chochs)}")

recs=[]
for ch in chochs:
    ci=ch["idx"]
    for j in range(ci+1,min(ci+MAX_PB,n-MAX_RES-2)):
        if C[j]>E[j]: break
        dist=E[j]-H[j]
        if not (-2<=dist<=TOUCH_PTS): continue
        if C[j]>=E[j]: continue
        entry=C[j]; stop=max(H[j],E[j])+5
        r1=stop-entry
        if r1<6 or r1>100: continue
        hour=IDX[j].hour; session=sess(hour)
        dow=IDX[j].weekday()
        rsi_v=float(R[j]) if not np.isnan(R[j]) else 50.
        is_bear=int(C[j]<O[j])
        f_lo=L[j+1:j+MAX_RES+1]; f_hi=H[j+1:j+MAX_RES+1]
        hit_stop=False; r_hit={r:False for r in R_TGTS}
        for bi in range(len(f_lo)):
            if f_hi[bi]>=stop: hit_stop=True; break
            for r in R_TGTS:
                if not r_hit[r] and f_lo[bi]<=entry-r*r1: r_hit[r]=True
        recs.append({"session":session,"hour":hour,
                     "dow":["Lun","Mar","Mie","Jue","Vie","Sab","Dom"][dow],
                     "rsi14":round(rsi_v,1),"r1_pts":round(r1,1),
                     "choch_consec":ch["consec"],"is_bear":is_bear,
                     "hit_stop":int(hit_stop),
                     **{f"hit_{r}R":int(r_hit[r]) for r in R_TGTS}})
        break  # solo primer retest

dc=pd.DataFrame(recs)
N=len(dc)
print(f"  Setups con retest: {N}")
if N>=3:
    b2=dc["hit_2R"].mean()*100; bs=dc["hit_stop"].mean()*100
    print(f"\n  GLOBAL  1R:{dc['hit_1R'].mean()*100:.1f}%  "
          f"2R:{b2:.1f}%  3R:{dc['hit_3R'].mean()*100:.1f}%  Stop:{bs:.1f}%")

    print(f"\n  POR SESION:")
    for s in ["Asia","London","NY-AM","NY-PM","After"]:
        g=dc[dc["session"]==s]
        if len(g)<2: continue
        print(f"  {s:<8} n={len(g):>3}  "
              f"1R:{g['hit_1R'].mean()*100:>5.1f}%  "
              f"2R:{g['hit_2R'].mean()*100:>5.1f}%  "
              f"Stop:{g['hit_stop'].mean()*100:>5.1f}%")

    print(f"\n  POR DIA:")
    for d in ["Lun","Mar","Mie","Jue","Vie"]:
        g=dc[dc["dow"]==d]
        if len(g)<2: continue
        print(f"  {d}  n={len(g):>3}  "
              f"1R:{g['hit_1R'].mean()*100:>5.1f}%  "
              f"2R:{g['hit_2R'].mean()*100:>5.1f}%  "
              f"Stop:{g['hit_stop'].mean()*100:>5.1f}%")

    print(f"\n  MEJOR COMBO (CHoCH consec>=5 + vela bajista + stop<20):")
    combo=dc[(dc["choch_consec"]>=5)&(dc["is_bear"]==1)&(dc["r1_pts"]<20)]
    if len(combo)>=3:
        print(f"  n={len(combo)}  "
              f"1R:{combo['hit_1R'].mean()*100:.1f}%  "
              f"2R:{combo['hit_2R'].mean()*100:.1f}%  "
              f"3R:{combo['hit_3R'].mean()*100:.1f}%  "
              f"Stop:{combo['hit_stop'].mean()*100:.1f}%")
    else:
        print(f"  n={len(combo)} (pocos datos con ese filtro)")

print("\n" + "="*70)
print("  RESUMEN EJECUTIVO")
print("="*70)
if len(da)>0:
    hobj=da[da["bucket"].isin(["0.2-0.4%","0.4-0.6%"])]["hit_60b"].mean()*100
    print(f"  A) IMAN   : Distancia 0.2-0.6% -> probabilidad tocar EMA en 60b = {hobj:.0f}%")
g30s=db[(db["fw"]==30)&(db["above"]==0)]
if len(g30s)>0:
    wr=( g30s["dir_ret"]>0).mean()*100
    print(f"  B) SESGO  : Bajo EMA -> precio baja en 30b = {wr:.0f}% de las veces")
if N>=3:
    print(f"  C) RECHAZO: CHoCH real -> 2R win = {b2:.0f}%  (stop={dc['r1_pts'].mean():.0f}pts)")
print()
