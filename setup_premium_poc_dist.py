"""
setup_premium_poc_dist.py
Filtra los mejores setups: FEAR/XFEAR + ABOVE VA + COT BEAR + distancia POC grande
Mide la velocidad y fuerza del movimiento bajista en NY
"""
import csv, math, yfinance as yf, pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict

VP_BIN=5.0; VA_PCT=0.70
nq_bars=[]
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_et=datetime.fromisoformat(r["Datetime"].replace("+00:00",""))-timedelta(hours=5)
            cl=float(r["Close"]); hi=float(r["High"]); lo=float(r["Low"]); op=float(r["Open"])
            vol=float(r.get("Volume",0) or 0)
            if cl>0: nq_bars.append({"et":dt_et,"c":cl,"h":hi,"l":lo,"o":op,
                                     "vol":vol if vol>0 else (hi-lo)*10})
        except: pass
nq_bars.sort(key=lambda x: x["et"])
by_date=defaultdict(list)
for b in nq_bars: by_date[b["et"].date()].append(b)

print("Descargando volatilidad...")
vxn=yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
vix=yf.download("^VIX", period="5y", auto_adjust=True, progress=False)
def col(df,c): return df[c].iloc[:,0] if isinstance(df.columns,pd.MultiIndex) else df[c]
dfv=pd.DataFrame({"VXN":col(vxn,"Close"),"VIX":col(vix,"Close")}).dropna()
dfv.index=pd.to_datetime(dfv.index).tz_localize(None)
vdates=dfv.index.tolist()

cot_rows=[]
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d=datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
            ll=int(r.get("Lev_Money_Positions_Long_All",0) or 0)
            ls=int(r.get("Lev_Money_Positions_Short_All",0) or 0)
            cot_rows.append({"date":d,"lev_net":ll-ls,"sig":"BULL" if ll>ls else "BEAR"})
        except: pass
cot_rows.sort(key=lambda x: x["date"])

# COT Index % — ventana 52 semanas (normalizado 0-100)
COT_WINDOW = 52
nets = [r["lev_net"] for r in cot_rows]
for i, r in enumerate(cot_rows):
    start = max(0, i - COT_WINDOW + 1)
    window = nets[start:i+1]
    mn = min(window); mx = max(window)
    r["cot_idx"] = round((r["lev_net"] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0

def cot_zona(idx):
    # Escala estandar COT Index 0-100%
    # 0%   = max bearish historico  (todos en shorts)
    # 100% = max bullish historico  (todos en longs)
    if idx < 20:  return "XBEAR"   # <20%  zona muy bearish
    if idx < 40:  return "BEAR "   # 20-40%
    if idx < 60:  return "NEUT "   # 40-60%
    if idx < 80:  return "BULL "   # 60-80%
    return                "XBULL"  # >80%  zona muy bullish

def get_cot_full(d):
    prev = [r for r in cot_rows if r["date"] <= d]
    return prev[-1] if prev else {"lev_net":0, "sig":"?", "cot_idx":50.0}

def calc_vp(bars):
    if len(bars)<3: return None,None,None
    la=min(b["l"] for b in bars); ha=max(b["h"] for b in bars)
    if ha<=la: return None,None,None
    n=max(1,int(math.ceil((ha-la)/VP_BIN))); bins=[0.0]*n
    for b in bars:
        vol=b["vol"] if b["vol"]>0 else 1.0
        rng=b["h"]-b["l"] if b["h"]>b["l"] else VP_BIN
        for i in range(n):
            bl=la+i*VP_BIN; bh=bl+VP_BIN
            ov=max(0,min(b["h"],bh)-max(b["l"],bl))
            bins[i]+=vol*(ov/rng)
    total=sum(bins)
    if total==0: return None,None,None
    pi=bins.index(max(bins)); poc=la+pi*VP_BIN+VP_BIN/2
    va=total*VA_PCT; acc=bins[pi]; li=hi=pi
    while acc<va:
        el=li-1 if li>0 else None; eh=hi+1 if hi<n-1 else None
        vl=bins[el] if el is not None else -1; vh=bins[eh] if eh is not None else -1
        if vl<=0 and vh<=0: break
        if vh>=vl: hi=eh; acc+=vh
        else: li=el; acc+=vl
    return round(la+hi*VP_BIN+VP_BIN,1), round(poc,1), round(la+li*VP_BIN,1)

def s_bars(bars, h0, m0, h1, m1):
    return [b for b in bars if
            (b["et"].hour>h0 or (b["et"].hour==h0 and b["et"].minute>=m0)) and
            (b["et"].hour<h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]

mondays=sorted([d for d in by_date.keys() if d.weekday()==0], reverse=True)
rows=[]
for mon in mondays:
    bars=by_date[mon]
    if len(bars)<8: continue
    sun=mon-timedelta(days=1)
    vp_b=[b for b in by_date.get(sun,[]) if b["et"].hour>=18]
    vp_b+=[b for b in bars if b["et"].hour<9 or (b["et"].hour==9 and b["et"].minute<20)]
    vp_b.sort(key=lambda x: x["et"])
    vah,poc,val=calc_vp(vp_b)
    if vah is None: continue
    ny30 =s_bars(bars, 9,30, 10, 0)
    ny1h =s_bars(bars, 9,30, 10,30)
    ny2h =s_bars(bars, 9,30, 11,30)
    nyall=s_bars(bars, 9,30, 15,59)
    if not nyall or len(nyall)<2: continue
    ny_o=nyall[0]["o"]
    def ms(sb):
        if not sb: return None
        c=sb[-1]["c"]; h=max(b["h"] for b in sb); l=min(b["l"] for b in sb)
        return {"move":round((c-ny_o)/ny_o*100,2),"range":round((h-l)/ny_o*100,2),
                "lo":round(l,0),"hi":round(h,0)}
    s30=ms(ny30); s1h=ms(ny1h); s2h=ms(ny2h); sall=ms(nyall)
    if not sall: continue
    va_p="ABOVE" if ny_o>vah else ("BELOW" if ny_o<val else "INSIDE")
    poc_dist=round(ny_o-poc,0)
    mon_ts=pd.Timestamp(mon)
    prev_q=[d for d in vdates if d<mon_ts]
    if not prev_q: continue
    pq=prev_q[-1]; vxn_v=float(dfv.loc[pq,"VXN"]); vix_v=float(dfv.loc[pq,"VIX"])
    zona="XFEAR" if vxn_v>=33 else ("FEAR" if vxn_v>=25 else ("NEUT" if vxn_v>=18 else "GREED"))
    cot = get_cot_full(mon)
    ny_dir="BULL" if sall["move"]>0.08 else ("BEAR" if sall["move"]<-0.08 else "FLAT")
    rows.append({"mon":mon,"vxn":round(vxn_v,1),"vix":round(vix_v,1),"zona":zona,
                 "lev_net":cot["lev_net"],"cot_sig":cot["sig"],
                 "cot_idx":cot["cot_idx"],"cot_zona":cot_zona(cot["cot_idx"]),
                 "vah":vah,"poc":poc,"val":val,
                 "ny_o":ny_o,"va_p":va_p,"poc_dist":poc_dist,
                 "s30":s30,"s1h":s1h,"s2h":s2h,"sall":sall,"ny_dir":ny_dir})

print(f"Lunes calculados: {len(rows)}")

# ── ANALISIS PRINCIPAL ──────────────────────────────────────────
SEP="="*95
# Filtros usando COT Index %: BEAR = <40%, BULL = >60%
above=[r for r in rows if r["va_p"]=="ABOVE" and r["zona"] in ("FEAR","XFEAR") and r["cot_idx"]<40]
below=[r for r in rows if r["va_p"]=="BELOW" and r["zona"] in ("FEAR","XFEAR") and r["cot_idx"]>60]


print(f"\n{SEP}")
print(f"  FILTRO PREMIUM: FEAR/XFEAR + VA Position + COT alineado")
print(f"  Viendo como la DISTANCIA AL POC afecta la velocidad y fuerza del movimiento")
print(f"{SEP}")

for titulo, dataset, win_dir in [
    ("SELL SETUP (ABOVE VA + FEAR/XFEAR + COT idx<40% = BEAR)", above, "BEAR"),
    ("BUY  SETUP (BELOW VA + FEAR/XFEAR + COT idx>60% = BULL)", below, "BULL"),
]:
    print(f"\n  {titulo}")
    print(f"  {'Umbral DistPOC':18} {'n':4}  {'WIN%':>5}  {'30m avg':>7}  {'1H avg':>7}  {'NYfull':>8}  {'Rng':>7}  {'Reac. rapida':>13}  {'Frec/mes':>9}")
    print(f"  {'─'*90}")
    for umbral in [0, 50, 100, 150, 200, 300]:
        sub=[r for r in dataset if abs(r["poc_dist"])>umbral]
        if not sub: continue
        wins=sum(1 for r in sub if r["ny_dir"]==win_dir)
        avg_30=sum(abs(r["s30"]["move"])*230 for r in sub if r["s30"]) / max(1,sum(1 for r in sub if r["s30"]))
        avg_1h=sum(r["s1h"]["move"]*230     for r in sub if r["s1h"]) / max(1,sum(1 for r in sub if r["s1h"]))
        avg_ny=sum(r["sall"]["move"] for r in sub) / len(sub)
        avg_rg=sum(r["sall"]["range"]*230   for r in sub) / len(sub)
        # Reaccion rapida: 30min ya mueve >25 pts en la direccion correcta
        if win_dir=="BEAR":
            fast=sum(1 for r in sub if r["s30"] and r["s30"]["move"]<-0.11)
        else:
            fast=sum(1 for r in sub if r["s30"] and r["s30"]["move"]>+0.11)
        meses=len(set((r["mon"].year,r["mon"].month) for r in sub))
        freq=len(sub)/meses if meses>0 else 0
        print(f"  > {umbral:4} pts             {len(sub):4d}  {wins/len(sub)*100:4.0f}%  {avg_30:>6.0f}pts  {avg_1h:>+6.0f}pts  {avg_ny:>+7.2f}%  {avg_rg:>6.0f}pts  {fast:3d}/{len(sub)} ({fast/len(sub)*100:.0f}%)  {freq:>7.1f}/mes")

# ── CASOS INDIVIDUALES ELITE (>150 pts) ────────────────────────
print(f"\n{SEP}")
print(f"  CASOS INDIVIDUALES SELL ELITE: dist POC >150 pts + FEAR/XFEAR + COT BEAR")
print(f"  Estos son los movimientos mas rapidos y agresivos")
print(f"{'─'*105}")
print(f"  {'#':3} {'Fecha':11} {'VXN':5} {'VIX':5} {'Zona':6} {'LevNet':>9}  {'DistPOC':>8}  {'30m':>6} {'1H':>6} {'2H':>6}  {'NYfull':>7}  {'Pts30m':>7}  {'Result':>6}")

ultra=[r for r in above if r["poc_dist"]>150]
ultra.sort(key=lambda x: x["poc_dist"], reverse=True)
for i,r in enumerate(ultra,1):
    s30m=r["s30"]["move"] if r["s30"] else 0
    s1hm=r["s1h"]["move"] if r["s1h"] else 0
    s2hm=r["s2h"]["move"] if r["s2h"] else 0
    pts30=abs(s30m)*230
    today=" <HOY" if r["mon"]==date(2026,3,30) else ""
    win="WIN " if r["ny_dir"]=="BEAR" else ("LOSS" if r["ny_dir"]=="BULL" else "FLAT")
    reac="FAST" if s30m<-0.11 else ("SLOW" if s30m<0 else "NO  ")
    print(f"  {i:3d} {r['mon'].strftime('%d %b %Y'):11} {r['vxn']:5.1f} {r['vix']:5.1f} {r['zona']:6} {r['cot_idx']:>4.1f}% {r['cot_zona']:6} {r['lev_net']:>8,}  +{r['poc_dist']:>6.0f}pts  {s30m:>+5.2f}% {s1hm:>+5.2f}% {s2hm:>+5.2f}%  {r['sall']['move']:>+6.2f}%  ~{pts30:>5.0f}pts  {win} {reac}{today}")

# ── DISTRIBUCION DE VELOCIDAD ───────────────────────────────────
print(f"\n{SEP}")
print(f"  DISTRIBUCION: En cuantos casos hay reaccion RAPIDA en primeros 30min?")
print(f"  (definicion: NY mueve >25 pts en los primeros 30min en la direccion correcta)")
print(f"{'─'*70}")

for umbral, label in [(0,"TODOS"),(100,"dist>100"),(150,"dist>150"),(200,"dist>200")]:
    sub=[r for r in above if r["poc_dist"]>umbral]
    if not sub: continue
    fast_big  =sum(1 for r in sub if r["s30"] and r["s30"]["move"]<-0.20)  # >46 pts
    fast_med  =sum(1 for r in sub if r["s30"] and -0.20<=r["s30"]["move"]<-0.10)  # 23-46 pts
    slow      =sum(1 for r in sub if r["s30"] and -0.10<=r["s30"]["move"]<0)      # 0-23 pts
    wrong     =sum(1 for r in sub if r["s30"] and r["s30"]["move"]>=0)             # sube
    meses=len(set((r["mon"].year,r["mon"].month) for r in sub))
    semanas=len(set((r["mon"].year,r["mon"].isocalendar()[1]) for r in sub))
    print(f"\n  {label} (n={len(sub)}, ~{len(sub)/meses:.1f}/mes, 1 cada {semanas/len(sub):.1f} semanas):")
    print(f"    Reaccion FUERTE (>46pts 30min): {fast_big:2d} = {fast_big/len(sub)*100:.0f}%  <- ENTRADA AGRESIVA")
    print(f"    Reaccion MEDIA  (23-46pts):     {fast_med:2d} = {fast_med/len(sub)*100:.0f}%  <- ENTRADA CONFIRMADA")
    print(f"    Reaccion LENTA  (<23pts baja):  {slow:2d}  = {slow/len(sub)*100:.0f}%  <- ESPERAR")
    print(f"    Sube en 30min (no hay setup):   {wrong:2d}  = {wrong/len(sub)*100:.0f}%  <- LOSS potencial")
