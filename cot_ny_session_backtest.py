"""
cot_ny_session_backtest.py
═══════════════════════════════════════════════════════════════
Para cada sesión NY (9:30-16:00 ET) desde 2022:
  - Lee el COT de esa semana (zona: XBEAR/BEAR/NEUT/BULL/XBULL)
  - Lee la VA position pre-NY (ABOVE / BELOW / INSIDE)
  - Mide el resultado de NY ese día
  
Pregunta clave: ¿Cuándo CLF está en zona X y precio está Y, 
cómo se comporta la sesión NY?
═══════════════════════════════════════════════════════════════
"""
import csv, math
from datetime import datetime, date, timedelta
from collections import defaultdict
import yfinance as yf, pandas as pd

VP_BIN  = 5.0
VA_PCT  = 0.70
WINDOW  = 52
FLOW_W  = 156
BULL_TH = 0.003   # >0.3% open→close = BULL NY session
BEAR_TH = -0.003  # <-0.3%           = BEAR NY session

# ── COT ───────────────────────────────────────────────────────────────
print("Cargando COT...")
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
        except: pass
cot.sort(key=lambda x: x["date"])

lev_nets = [r["lev_net"] for r in cot]
am_nets  = [r["am_net"]  for r in cot]
for i, r in enumerate(cot):
    w = lev_nets[max(0,i-WINDOW+1):i+1]
    r["lev_idx"] = round((r["lev_net"]-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0
    w = am_nets[max(0,i-WINDOW+1):i+1]
    r["am_idx"]  = round((r["am_net"]-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0
    delta = (cot[i]["com_s"]-cot[i-1]["com_s"]) if i>0 else 0
    r["com_delta"] = delta

com_deltas = [r["com_delta"] for r in cot]
for i, r in enumerate(cot):
    w = com_deltas[max(0,i-FLOW_W+1):i+1]
    mx,mn = max(w),min(w)
    r["flow"] = round((mx-r["com_delta"])/(mx-mn)*100,1) if mx!=mn else 50.0

def get_cot(d):
    prev = [r for r in cot if r["date"] <= d]
    return prev[-1] if prev else None

def lev_zone(v):
    if v < 20: return "XBEAR"
    if v < 40: return "BEAR"
    if v < 60: return "NEUT"
    if v < 80: return "BULL"
    return "XBULL"

def am_zone(v):
    if v < 20: return "XBEAR"
    if v < 40: return "BEAR"
    if v < 60: return "NEUT"
    if v < 80: return "BULL"
    return "XBULL"

# ── NQ 15min ─────────────────────────────────────────────────────────
print("Cargando NQ 15min...")
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            et = datetime.fromisoformat(r["Datetime"].replace("+00:00","")) - timedelta(hours=5)
            cl = float(r["Close"]); hi = float(r["High"]); lo = float(r["Low"])
            op = float(r["Open"]); vol = float(r.get("Volume",0) or 0)
            if cl > 0: bars.append({"et":et,"c":cl,"h":hi,"l":lo,"o":op,
                                    "vol": vol if vol>0 else (hi-lo)*10})
        except: pass
bars.sort(key=lambda x: x["et"])
by_date = defaultdict(list)
for b in bars: by_date[b["et"].date()].append(b)
print(f"  → Días con datos: {len(by_date)}")

# ── VXN ──────────────────────────────────────────────────────────────
print("Cargando VXN...")
vxn = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
def col(df,c): return df[c].iloc[:,0] if isinstance(df.columns,pd.MultiIndex) else df[c]
dfv = pd.DataFrame({"vxn": col(vxn,"Close")}).dropna()
dfv.index = pd.to_datetime(dfv.index).tz_localize(None)
def get_vxn(d):
    prev = [v for v in dfv.index if v.date() <= d]
    return float(dfv.loc[prev[-1],"vxn"]) if prev else None

def vxn_zone(v):
    if v is None: return "?"
    if v >= 33: return "XFEAR"
    if v >= 25: return "FEAR"
    if v >= 18: return "NEUT"
    return "GREED"

# ── VP helpers ────────────────────────────────────────────────────────
def calc_vp(bs):
    if len(bs)<3: return None,None,None
    la=min(b["l"] for b in bs); ha=max(b["h"] for b in bs)
    if ha<=la: return None,None,None
    n=max(1,int(math.ceil((ha-la)/VP_BIN))); bins=[0.0]*n
    for b in bs:
        vol=b["vol"] if b["vol"]>0 else 1.0; rng=b["h"]-b["l"] if b["h"]>b["l"] else VP_BIN
        for i in range(n):
            bl=la+i*VP_BIN; bh=bl+VP_BIN; ov=max(0,min(b["h"],bh)-max(b["l"],bl))
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

def sbars(bs,h0,m0,h1,m1):
    return [b for b in bs if (b["et"].hour>h0 or (b["et"].hour==h0 and b["et"].minute>=m0))
            and (b["et"].hour<h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]

# ── MAIN LOOP — TODOS LOS DÍAS ────────────────────────────────────────
print("Calculando sesiones NY...")
sessions = []
all_dates = sorted(by_date.keys())
DOW = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"]

for d in all_dates:
    if d.weekday() >= 5: continue   # Skip fin de semana
    bs = by_date[d]
    if len(bs) < 6: continue

    # Pre-market VP (18:00 día anterior — 9:20 ET)
    prev = d - timedelta(days=1)
    # buscar sesión Asia/Londres previa
    vp_b = [b for b in by_date.get(prev,[]) if b["et"].hour >= 18]
    vp_b += [b for b in bs if b["et"].hour < 9 or (b["et"].hour==9 and b["et"].minute < 20)]
    vp_b.sort(key=lambda x: x["et"])

    vah,poc,val = calc_vp(vp_b)
    if vah is None: continue

    # NY session
    ny = sbars(bs, 9, 30, 15, 59)
    if len(ny) < 8: continue
    ny_o = ny[0]["o"]
    ny_c = ny[-1]["c"]
    ny_h = max(b["h"] for b in ny)
    ny_l = min(b["l"] for b in ny)
    ny_ret = (ny_c - ny_o) / ny_o * 100
    ny_range = round(ny_h - ny_l, 0)

    # 30 min NY
    ny30 = sbars(bs, 9, 30, 10, 0)
    m30 = ((ny30[-1]["c"] - ny_o) / ny_o * 100) if ny30 else 0

    ny_dir = "BULL" if ny_ret > BULL_TH*100 else ("BEAR" if ny_ret < BEAR_TH*100 else "FLAT")
    va_p = "ABOVE" if ny_o > vah else ("BELOW" if ny_o < val else "INSIDE")
    poc_dist = round(ny_o - poc, 0)

    c = get_cot(d)
    if not c: continue
    vxn_v = get_vxn(d)
    vxn_z = vxn_zone(vxn_v)

    sessions.append({
        "date": d, "dow": d.weekday(),
        "lev_idx": c["lev_idx"], "am_idx": c["am_idx"],
        "lev_z": lev_zone(c["lev_idx"]), "am_z": am_zone(c["am_idx"]),
        "vxn": vxn_v, "vxn_z": vxn_z,
        "va_p": va_p, "poc_dist": poc_dist,
        "ny_dir": ny_dir, "ny_ret": round(ny_ret,2),
        "ny_range": ny_range, "m30": round(m30,2),
    })

print(f"  → Sesiones NY analizadas: {len(sessions)}")
N = len(sessions)

SEP = "=" * 85

# ── 1. ZONA LEV × VA POSITION → NY DIRECTION ─────────────────────────
print()
print(SEP)
print("  LEV MONEY ZONA × VA POSITION → DIRECCIÓN SESIÓN NY")
print("  (Esto es lo que importa para tu trading real)")
print(SEP)

LEV_ZONES = ["XBEAR","BEAR","NEUT","BULL","XBULL"]
VA_POSITIONS = ["ABOVE","INSIDE","BELOW"]

# Header
print(f"\n  {'LEV ZONA':10}  {'VA POS':7}  {'N':>5}  {'BULL%':>6}  {'BEAR%':>6}  {'BullPts':>8}  {'BearPts':>8}  {'>200pt':>6}  Señal")
print("  " + "-"*82)

for lz in LEV_ZONES:
    for va in VA_POSITIONS:
        rows = [s for s in sessions if s["lev_z"]==lz and s["va_p"]==va]
        if len(rows) < 3: continue
        n = len(rows)
        bull_rows = [r for r in rows if r["ny_dir"]=="BULL"]
        bear_rows = [r for r in rows if r["ny_dir"]=="BEAR"]
        bull = len(bull_rows); bear = len(bear_rows)
        # Puntos promedio cuando sube/baja
        bull_pts = round(sum(r["ny_range"] for r in bull_rows)/len(bull_rows)) if bull_rows else 0
        bear_pts = round(sum(r["ny_range"] for r in bear_rows)/len(bear_rows)) if bear_rows else 0
        # Dias con movimiento >200pts
        big200 = sum(1 for r in rows if r["ny_range"]>=200)
        bp = bull/n*100; rp = bear/n*100
        if va=="ABOVE":
            signal = "✅SELL" if rp>=55 else ("🟡sell" if rp>=50 else "❌")
        elif va=="BELOW":
            signal = "✅BUY " if bp>=55 else ("🟡buy " if bp>=50 else "❌")
        else:
            signal = "⚪NEUT"
        print(f"  {lz:10}  {va:7}  {n:>5}  {bp:>5.0f}%  {rp:>5.0f}%  {bull_pts:>7}pt  {bear_pts:>7}pt  {big200/n*100:>5.0f}%  {signal}")
    print()

# ── 2. VXN ZONA × VA POSITION ─────────────────────────────────────────
print(SEP)
print("  VXN ZONA × VA POSITION → DIRECCIÓN SESIÓN NY")
print(SEP)
VXN_ZONES = ["GREED","NEUT","FEAR","XFEAR"]
print(f"\n  {'VXN ZONA':10}  {'VA POS':7}  {'N':>5}  {'BULL%':>6}  {'BEAR%':>6}  {'RngAVG':>7}  {'BullPts':>8}  {'BearPts':>8}  {'>300pt':>6}  Señal")
print("  " + "-"*92)
for vz in VXN_ZONES:
    for va in VA_POSITIONS:
        rows = [s for s in sessions if s["vxn_z"]==vz and s["va_p"]==va]
        if len(rows) < 3: continue
        n = len(rows)
        bull_rows = [r for r in rows if r["ny_dir"]=="BULL"]
        bear_rows = [r for r in rows if r["ny_dir"]=="BEAR"]
        bull = len(bull_rows); bear = len(bear_rows)
        avg_range = sum(r["ny_range"] for r in rows)/n
        bull_pts  = round(sum(r["ny_range"] for r in bull_rows)/len(bull_rows)) if bull_rows else 0
        bear_pts  = round(sum(r["ny_range"] for r in bear_rows)/len(bear_rows)) if bear_rows else 0
        big300 = sum(1 for r in rows if r["ny_range"]>=300)
        bp = bull/n*100; rp = bear/n*100
        if va=="ABOVE":
            signal = "✅SELL" if rp>=55 else ("🟡sell" if rp>=50 else "❌")
        elif va=="BELOW":
            signal = "✅BUY " if bp>=55 else ("🟡buy " if bp>=50 else "❌")
        else:
            signal = "⚪NEUT"
        print(f"  {vz:10}  {va:7}  {n:>5}  {bp:>5.0f}%  {rp:>5.0f}%  {avg_range:>6.0f}pt  {bull_pts:>7}pt  {bear_pts:>7}pt  {big300/n*100:>5.0f}%  {signal}")
    print()

# ── 3. TRIPLE — LEV × VXN × VA ────────────────────────────────────────
print(SEP)
print("  TRIPLE SIGNAL: LEV ZONA + VXN ZONA + VA POSITION → SESIÓN NY")
print("  (Solo combos con n>=5 — los setups más repetibles)")
print(SEP)
print(f"\n  {'LEV':7} {'VXN':6} {'VA':7}  {'N':>4}  {'BULL%':>7}  {'BEAR%':>7}  {'Rng':>6}  Señal")
print("  " + "-"*70)

triple = defaultdict(lambda:{"n":0,"bull":0,"bear":0,"flat":0,"rets":[],"ranges":[]})
for s in sessions:
    k = (s["lev_z"], s["vxn_z"], s["va_p"])
    triple[k]["n"] += 1
    triple[k][s["ny_dir"].lower()] += 1
    triple[k]["rets"].append(s["ny_ret"])
    triple[k]["ranges"].append(s["ny_range"])

rows_t = [(k,v) for k,v in triple.items() if v["n"]>=5]
rows_t.sort(key=lambda x: -x[1]["n"])

for (lz,vz,va), d in rows_t:
    n = d["n"]; bp = d["bull"]/n*100; rp = d["bear"]/n*100
    avg_r = sum(d["ranges"])/n
    if va=="ABOVE":
        ok = rp>=55; signal = ("✅SELL" if rp>=60 else "🟡sell") if rp>=50 else "❌"
    elif va=="BELOW":
        ok = bp>=55; signal = ("✅BUY " if bp>=60 else "🟡buy ") if bp>=50 else "❌"
    else:
        signal = "⚪"
    if d["n"]>=8:  # Solo mostrar los más frecuentes
        print(f"  {lz:7} {vz:6} {va:7}  {n:>4}  {bp:>6.0f}%  {rp:>6.0f}%  {avg_r:>5.0f}pt  {signal}")

# ── 4. RESUMEN EJECUTIVO ──────────────────────────────────────────────
print()
print(SEP)
print("  RESUMEN EJECUTIVO — REGLAS QUE FUNCIONAN EN SESIÓN NY")
print(SEP)

# Calcular los mejores y peores setups
sell_setups = [(k,v) for k,v in triple.items() if k[2]=="ABOVE" and v["n"]>=8]
sell_setups.sort(key=lambda x: -x[1]["bear"]/x[1]["n"])
buy_setups  = [(k,v) for k,v in triple.items() if k[2]=="BELOW" and v["n"]>=8]
buy_setups.sort(key=lambda x: -x[1]["bull"]/x[1]["n"])

print("\n  TOP SETUPS DE VENTA (NYC abre ABOVE VA):")
for (lz,vz,va),d in sell_setups[:5]:
    n=d["n"]; rp=d["bear"]/n*100; bp=d["bull"]/n*100
    print(f"    {lz:7} + {vz:6} → BEAR {rp:.0f}% / BULL {bp:.0f}% (n={n})")

print("\n  TOP SETUPS DE COMPRA (NYC abre BELOW VA):")
for (lz,vz,va),d in buy_setups[:5]:
    n=d["n"]; bp=d["bull"]/n*100; rp=d["bear"]/n*100
    print(f"    {lz:7} + {vz:6} → BULL {bp:.0f}% / BEAR {rp:.0f}% (n={n})")

# Stat actual
# ── 5. MAGNITUD DETALLADA POR ZONA ────────────────────────────────────
print()
print(SEP)
print("  MAGNITUD DE MOVIMIENTOS POR ZONA LEV — ¿Cuántos puntos sube/baja NY?")
print(SEP)
print(f"\n  {'LEV ZONA':10}  {'N':>4}  {'Rng AVG':>8}  {'Rng <100':>9}  {'100-200':>8}  {'200-300':>8}  {'>300pt':>8}  {'BullMax':>8}  {'BearMax':>8}")
print("  " + "-"*85)
for lz in LEV_ZONES:
    rows = [s for s in sessions if s["lev_z"]==lz]
    if not rows: continue
    n = len(rows)
    ranges = [r["ny_range"] for r in rows]
    avg_r = sum(ranges)/n
    lt100  = sum(1 for r in ranges if r<100)/n*100
    r100   = sum(1 for r in ranges if 100<=r<200)/n*100
    r200   = sum(1 for r in ranges if 200<=r<300)/n*100
    r300   = sum(1 for r in ranges if r>=300)/n*100
    bull_max = max((r["ny_range"] for r in rows if r["ny_dir"]=="BULL"), default=0)
    bear_max = max((r["ny_range"] for r in rows if r["ny_dir"]=="BEAR"), default=0)
    print(f"  {lz:10}  {n:>4}  {avg_r:>7.0f}pt  {lt100:>7.0f}%  {r100:>7.0f}%  {r200:>7.0f}%  {r300:>7.0f}%  {bull_max:>7.0f}pt  {bear_max:>7.0f}pt")

print()
print(SEP)
print("  MAGNITUD POR VXN — ¿Más volátil = más puntos?")
print(SEP)
print(f"\n  {'VXN ZONA':10}  {'N':>4}  {'Rng AVG':>8}  {'<100':>7}  {'100-200':>8}  {'200-300':>8}  {'>300':>7}  {'MaxMove':>8}")
print("  " + "-"*78)
for vz in VXN_ZONES:
    rows = [s for s in sessions if s["vxn_z"]==vz]
    if not rows: continue
    n = len(rows); ranges = [r["ny_range"] for r in rows]; avg_r = sum(ranges)/n
    lt100 = sum(1 for r in ranges if r<100)/n*100
    r100  = sum(1 for r in ranges if 100<=r<200)/n*100
    r200  = sum(1 for r in ranges if 200<=r<300)/n*100
    r300  = sum(1 for r in ranges if r>=300)/n*100
    maxmv = max(ranges)
    print(f"  {vz:10}  {n:>4}  {avg_r:>7.0f}pt  {lt100:>6.0f}%  {r100:>7.0f}%  {r200:>7.0f}%  {r300:>6.0f}%  {maxmv:>7.0f}pt")

print()
print(SEP)
print("  TUS CONDICIONES ACTUALES (semana 31 Mar 2026):")
last_cot = cot[-1]
print(f"  LEV Index: {last_cot['lev_idx']:.1f}% → {lev_zone(last_cot['lev_idx'])}")
print(f"  AM Index:  {last_cot['am_idx']:.1f}% → {am_zone(last_cot['am_idx'])}")
# Filtrar sesiones parecidas
sim = [s for s in sessions if s["lev_z"]==lev_zone(last_cot["lev_idx"])]
for va in ["ABOVE","INSIDE","BELOW"]:
    s2 = [s for s in sim if s["va_p"]==va]
    if not s2: continue
    n=len(s2); bull=sum(1 for s in s2 if s["ny_dir"]=="BULL"); bear=sum(1 for s in s2 if s["ny_dir"]=="BEAR")
    avg=sum(s["ny_ret"] for s in s2)/n
    print(f"    Si NY abre {va} VA → BULL {bull/n*100:.0f}% / BEAR {bear/n*100:.0f}% (n={n}, ret avg {avg:+.2f}%)")
print(SEP)
