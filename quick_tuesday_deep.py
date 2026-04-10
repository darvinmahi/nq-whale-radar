"""
quick_tuesday_deep.py — Estudio rápido MARTES (solo lo necesario)
"""
import pandas as pd, numpy as np, pytz, json
from datetime import datetime, timedelta

ET  = pytz.timezone("America/New_York")
W   = 65

print("\n"+"█"*W)
print("  ESTUDIO PROFUNDO MARTES — NQ Futures")
print("█"*W)

# CSV
raw = pd.read_csv("data/research/nq_15m_intraday.csv", skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]: raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
print(f"  {len(raw)} barras | {raw.index.min().date()} → {raw.index.max().date()}")

# VXN
try:
    import yfinance as yf
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if isinstance(vdf.columns, pd.MultiIndex): vdf.columns = vdf.columns.get_level_values(0)
    vxn_day = {idx.date(): round(float(row["Close"]),2) for idx,row in vdf.iterrows()}
    print(f"  VXN: {len(vxn_day)} días")
except: vxn_day = {}

def bt(d,t0,t1):
    a=datetime.strptime(t0,"%H:%M").time(); b=datetime.strptime(t1,"%H:%M").time()
    return d[(d.index.time>=a)&(d.index.time<=b)]

all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday()<5})
tuesdays  = [d for d in all_dates if pd.Timestamp(d).weekday()==1]
print(f"  Martes a procesar: {len(tuesdays)}")

sessions = []
for day in tuesdays:
    s0=ET.localize(datetime(day.year,day.month,day.day,0,0))
    s1=ET.localize(datetime(day.year,day.month,day.day,16,30))
    d=raw[(raw.index>=s0)&(raw.index<=s1)].copy()
    if d.empty: continue

    pm=bt(d,"07:00","09:29"); ny=bt(d,"09:30","16:00")
    spk=bt(d,"08:30","08:44"); pre=bt(d,"08:00","08:29")
    if len(pm)<2 or len(ny)<4: continue

    pm_m=float(pm.iloc[-1]["Close"])-float(pm.iloc[0]["Open"])
    pm_r=float(pm["High"].max())-float(pm["Low"].min())
    pm_d="BULL" if pm_m>15 else("BEAR" if pm_m<-15 else "FLAT")
    pm_sz="SMALL" if pm_r<80 else("MED" if pm_r<160 else "LARGE")

    ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
    ny_m=ny_c-ny_o; ny_h=float(ny["High"].max()); ny_l=float(ny["Low"].min())
    ny_r=ny_h-ny_l
    ny_d="BULL" if ny_m>30 else("BEAR" if ny_m<-30 else "FLAT")

    idx_hi=ny["High"].idxmax(); idx_lo=ny["Low"].idxmin()
    hi1=idx_hi<idx_lo
    hi_h=round(idx_hi.hour+idx_hi.minute/60,2)
    lo_h=round(idx_lo.hour+idx_lo.minute/60,2)

    spk_m=0
    if len(spk)>=1 and len(pre)>=1:
        spk_m=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
    spk_d="UP" if spk_m>25 else("DOWN" if spk_m<-25 else "FLAT")

    # Max drawdown
    if ny_m>0: max_dd=round(ny_l-ny_o)
    else: max_dd=round(ny_h-ny_o)

    # Prev day
    prev=None
    for td in reversed(all_dates):
        if td<day: prev=td; break
    prev_d="NONE"
    if prev:
        p0=ET.localize(datetime(prev.year,prev.month,prev.day,0,0))
        p1=ET.localize(datetime(prev.year,prev.month,prev.day,16,30))
        dp=raw[(raw.index>=p0)&(raw.index<=p1)].copy()
        pny=bt(dp,"09:30","16:00")
        if len(pny)>=2:
            pm2=float(pny.iloc[-1]["Close"])-float(pny.iloc[0]["Open"])
            prev_d="BULL" if pm2>30 else("BEAR" if pm2<-30 else "FLAT")

    vxn=vxn_day.get(day)
    vxn_lvl=None
    if vxn: vxn_lvl="LOW" if vxn<20 else("MID" if vxn<25 else("HIGH" if vxn<30 else "PANIC"))

    sessions.append({"date":day,"ny_dir":ny_d,"ny_move":round(ny_m),"ny_range":round(ny_r),
        "ny_hi_hour":hi_h,"ny_lo_hour":lo_h,"hi_first":hi1,"max_dd":round(max_dd),
        "pm_dir":pm_d,"pm_move":round(pm_m),"pm_range":round(pm_r),"pm_size":pm_sz,
        "spike_dir":spk_d,"spike_move":round(spk_m),"prev_dir":prev_d,"vxn":vxn,"vxn_lvl":vxn_lvl})

df=pd.DataFrame(sessions); n=len(df)
print(f"  Sesiones procesadas: {n}\n")

bull_df=df[df["ny_dir"]=="BULL"]; bear_df=df[df["ny_dir"]=="BEAR"]; flat_df=df[df["ny_dir"]=="FLAT"]

# ── 1. SESGO BASE
print("═"*W); print("  1️⃣  SESGO BASE"); print("═"*W)
print(f"  BULL: {len(bull_df)}/{n} = {len(bull_df)/n*100:.0f}%")
print(f"  BEAR: {len(bear_df)}/{n} = {len(bear_df)/n*100:.0f}%")
print(f"  FLAT: {len(flat_df)}/{n} = {len(flat_df)/n*100:.0f}%")
print(f"  Rango→ P25:{df['ny_range'].quantile(.25):.0f} Median:{df['ny_range'].median():.0f} Avg:{df['ny_range'].mean():.0f} P75:{df['ny_range'].quantile(.75):.0f} Max:{df['ny_range'].max():.0f}")

# ── 2. PM → NY
print("\n"+"═"*W); print("  2️⃣  PM DIRECTION → NY"); print("═"*W)
for pm_d in ["BULL","BEAR","FLAT"]:
    sub=df[df["pm_dir"]==pm_d];
    if sub.empty: continue
    ns=len(sub); bull=(sub["ny_dir"]=="BULL").sum(); bear=(sub["ny_dir"]=="BEAR").sum()
    same=bull if pm_d=="BULL" else(bear if pm_d=="BEAR" else ns-bull-bear)
    pct=same/ns*100; bar="█"*int(pct/5)
    arrow="▲" if pm_d=="BULL" else("▼" if pm_d=="BEAR" else"▬")
    print(f"\n  PM {pm_d} {arrow} → {ns} sess:  BULL {bull}({bull/ns*100:.0f}%)  BEAR {bear}({bear/ns*100:.0f}%)")
    if pm_d in("BULL","BEAR"): print(f"    CORRELACIÓN: {same}/{ns} = {pct:.1f}%  {bar}")
    if pm_d in("BULL","BEAR"):
        for sz in ["SMALL","MED","LARGE"]:
            s2=sub[sub["pm_size"]==sz]
            if len(s2)<3: continue
            nc=(s2["ny_dir"]==pm_d).sum()
            print(f"      {sz}: {nc}/{len(s2)} = {nc/len(s2)*100:.0f}%")

# ── 3. VXN GRANULAR
hv=df[df["vxn"].notna()]
if len(hv)>=5:
    print("\n"+"═"*W); print(f"  3️⃣  VXN GRANULAR  ({len(hv)} sess)"); print("═"*W)
    corr=hv["vxn"].corr(hv["ny_range"])
    print(f"  VXN→Range: r={corr:.3f}\n")
    print(f"  {'Nivel':<16} {'N':>3} {'BULL%':>6} {'BEAR%':>6} {'Med Rng':>8} {'Avg Rng':>8}")
    print("  "+"─"*50)
    for lo,hi,lbl in [(0,18,"<18"),(18,20,"18-20"),(20,22,"20-22"),(22,25,"22-25"),(25,28,"25-28"),(28,32,"28-32"),(32,99,">32")]:
        sub=hv[(hv["vxn"]>=lo)&(hv["vxn"]<hi)]
        if len(sub)<3: continue
        bull=(sub["ny_dir"]=="BULL").sum(); bear=(sub["ny_dir"]=="BEAR").sum()
        flag=" ✅" if bull/len(sub)>=0.60 else(" 🔴" if bear/len(sub)>=0.60 else"")
        print(f"  {lbl:<16}{len(sub):>3} {bull/len(sub)*100:>5.0f}% {bear/len(sub)*100:>5.0f}% {sub['ny_range'].median():>8.0f} {sub['ny_range'].mean():>8.0f}{flag}")

# ── 4. COMBOS
print("\n"+"═"*W); print("  4️⃣  MEJORES COMBOS 2 PREDICTORES (≥65%)"); print("═"*W)
feat_pairs=[("pm_dir","vxn_lvl"),("pm_dir","spike_dir"),("pm_dir","prev_dir"),
            ("pm_size","pm_dir"),("pm_size","vxn_lvl"),("vxn_lvl","spike_dir")]
combos=[]; seen=set()
for f1,f2 in feat_pairs:
    for v1 in df[f1].dropna().unique():
        for v2 in df[f2].dropna().unique():
            if v1 in("NONE","FLAT") or v2 in("NONE","FLAT"): continue
            sub=df[(df[f1]==v1)&(df[f2]==v2)]
            if len(sub)<6: continue
            for direction in ["BULL","BEAR"]:
                nc=(sub["ny_dir"]==direction).sum(); pct=nc/len(sub)*100
                if pct>=65:
                    key=(f1,v1,f2,v2,direction)
                    if key not in seen:
                        seen.add(key); combos.append({"f1":f1,"v1":v1,"f2":f2,"v2":v2,"dir":direction,"pct":pct,"n":len(sub),"nc":nc})
combos.sort(key=lambda x:(x["pct"],-x["n"]),reverse=True)
print()
for i,c in enumerate(combos[:6]):
    m="🥇" if i==0 else("🥈" if i==1 else("🥉" if i==2 else"  "))
    bar="█"*int(c["pct"]/5)
    print(f"  {m} {c['f1']}={c['v1']} + {c['f2']}={c['v2']}")
    print(f"     → NY {c['dir']}: {c['nc']}/{c['n']} = {c['pct']:.1f}%  {bar}")
if not combos: print("  (ninguna ≥65%)")

# ── 5. TIMING
print("\n"+"═"*W); print("  5️⃣  TIMING — ¿A QUÉ HORA SE FORMA EL HIGH/LOW?"); print("═"*W)
for direction,col in [("BULL","ny_hi_hour"),("BEAR","ny_lo_hour")]:
    sub=df[(df["ny_dir"]==direction)&df[col].notna()]; hours=sub[col]
    if len(sub)<5: continue
    lbl="HIGH" if direction=="BULL" else "LOW"
    print(f"\n  Días {direction} ({len(sub)}) — hora del {lbl}:")
    print(f"    Median: {hours.median():.2f}h | Avg: {hours.mean():.2f}h | P25-P75: {hours.quantile(.25):.2f}-{hours.quantile(.75):.2f}h")
    for lo,hi,lh in [(9.5,10.5,"9:30-10:30"),(10.5,11.5,"10:30-11:30"),(11.5,12.5,"11:30-12:30"),(12.5,14,"12:30-14:00"),(14,16.5,"14:00-16:00")]:
        cnt=(hours>=lo)&(hours<hi); nk=cnt.sum()
        bar="█"*nk; print(f"      {lh}: {nk:>3} ({nk/len(sub)*100:.0f}%)  {bar}")

# ── 6. EXPECTANCY
print("\n"+"═"*W); print("  6️⃣  DRAWDOWN & EXPECTANCY"); print("═"*W)
for direction in ["BULL","BEAR"]:
    sub=df[(df["ny_dir"]==direction)&df["max_dd"].notna()]
    if len(sub)<5: continue
    moves=sub["ny_move"].abs(); dds=sub["max_dd"].abs(); ratio=moves.mean()/max(dds.mean(),1)
    print(f"\n  {direction} ({len(sub)} sess):")
    print(f"    Move NY → Med:{moves.median():.0f}  Avg:{moves.mean():.0f}  P75:{moves.quantile(.75):.0f} pts")
    print(f"    Max DD  → Med:{dds.median():.0f}  Avg:{dds.mean():.0f}  P75:{dds.quantile(.75):.0f} pts")
    print(f"    Ratio Move/DD: {ratio:.1f}x")

# ── 7. CONFLICTOS
print("\n"+"═"*W); print("  7️⃣  CASOS ESPECIALES"); print("═"*W)
big=df[df["pm_range"]>=200]
if len(big)>=4:
    b=(big["ny_dir"]=="BULL").sum(); be=(big["ny_dir"]=="BEAR").sum()
    print(f"\n  PM_RANGE>200: {len(big)} sess → BULL {b}({b/len(big)*100:.0f}%) BEAR {be}({be/len(big)*100:.0f}%)")
conf1=df[(df["pm_dir"]=="BULL")&(df["spike_dir"]=="DOWN")]
if len(conf1)>=3:
    nc=(conf1["ny_dir"]=="BULL").sum()
    print(f"  PM BULL + SPIKE DOWN ({len(conf1)} sess): NY BULL {nc}/{len(conf1)} = {nc/len(conf1)*100:.0f}%")
conf2=df[(df["pm_dir"]=="BEAR")&(df["spike_dir"]=="UP")]
if len(conf2)>=3:
    nc=(conf2["ny_dir"]=="BEAR").sum()
    print(f"  PM BEAR + SPIKE UP ({len(conf2)} sess trampa): NY BEAR {nc}/{len(conf2)} = {nc/len(conf2)*100:.0f}%")

print("\n"+"█"*W); print("  MARTES — COMPLETADO"); print("█"*W+"\n")
