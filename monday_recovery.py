"""Monday only - quick recovery of truncated data"""
import pandas as pd, numpy as np, pytz, json
from datetime import datetime, date, timedelta

ET = pytz.timezone("America/New_York")
raw = pd.read_csv("data/research/nq_15m_intraday.csv", skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]: raw[c]=pd.to_numeric(raw[c],errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_date"] = raw.index.date
grouped = {d: grp for d, grp in raw.groupby("_date")}
all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday()<5})
print(f"  {len(raw)} barras | {len(grouped)} dias indexados")

try:
    import yfinance as yf
    vdf = yf.download("^VXN",period="24mo",interval="1d",progress=False,auto_adjust=True)
    if isinstance(vdf.columns,pd.MultiIndex): vdf.columns=vdf.columns.get_level_values(0)
    vxn_day={idx.date():round(float(row["Close"]),2) for idx,row in vdf.iterrows()}
    print(f"  VXN: {len(vxn_day)} dias")
except: vxn_day={}

def bt(d,t0,t1):
    a=datetime.strptime(t0,"%H:%M").time(); b=datetime.strptime(t1,"%H:%M").time()
    return d[(d.index.time>=a)&(d.index.time<=b)]

windows=[("w0930_0944","09:30","09:44"),("w0930_0959","09:30","09:59"),
         ("w0930_1029","09:30","10:29"),("w1000_1059","10:00","10:59"),
         ("w1100_1159","11:00","11:59"),("w1200_1259","12:00","12:59"),
         ("w1300_1359","13:00","13:59")]

mondays=[d for d in all_dates if pd.Timestamp(d).weekday()==0]
print(f"  Lunes: {len(mondays)} dias")

rows=[]
for day in mondays:
    d=grouped.get(day)
    if d is None: continue
    pm=bt(d,"07:00","09:29"); ny=bt(d,"09:30","16:00"); asia=bt(d,"00:00","06:59")
    spk=bt(d,"08:30","08:44"); pre=bt(d,"08:00","08:29")
    if len(ny)<4: continue

    ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
    ny_m=ny_c-ny_o; nyr=float(ny["High"].max())-float(ny["Low"].min())
    idx_hi=ny["High"].idxmax(); idx_lo=ny["Low"].idxmin()
    row={"date":day,"ny_dir":"BULL" if ny_m>30 else("BEAR" if ny_m<-30 else"FLAT"),
         "ny_range":round(nyr),"ny_move":round(ny_m),
         "ny_hi_h":round(idx_hi.hour+idx_hi.minute/60,2),
         "ny_lo_h":round(idx_lo.hour+idx_lo.minute/60,2)}

    if len(pm)>=2:
        pm_m=float(pm.iloc[-1]["Close"])-float(pm.iloc[0]["Open"])
        pm_r=float(pm["High"].max())-float(pm["Low"].min())
        row.update({"pm_dir":"BULL" if pm_m>15 else("BEAR" if pm_m<-15 else"FLAT"),
                    "pm_range":round(pm_r),"pm_size":"SMALL" if pm_r<80 else("MED" if pm_r<160 else"LARGE")})
    if len(asia)>=2:
        am=float(asia.iloc[-1]["Close"])-float(asia.iloc[0]["Open"])
        row["asia_dir"]="BULL" if am>20 else("BEAR" if am<-20 else"FLAT")
        row["asia_range"]=round(float(asia["High"].max())-float(asia["Low"].min()))
    if len(spk)>=1 and len(pre)>=1:
        sm=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
        row["spike"]="UP" if sm>25 else("DOWN" if sm<-25 else"FLAT")

    vxn=vxn_day.get(day); row["vxn"]=vxn
    if vxn: row["vxn_lvl"]="LOW" if vxn<20 else("MID" if vxn<25 else("HIGH" if vxn<30 else"PANIC"))

    for wname,t0w,t1w in windows:
        win=bt(d,t0w,t1w)
        if len(win)>=1:
            wm=float(win.iloc[-1]["Close"])-float(win.iloc[0]["Open"])
            wr=float(win["High"].max())-float(win["Low"].min())
            row[wname+"_dir"]="BULL" if wm>10 else("BEAR" if wm<-10 else"FLAT")
            row[wname+"_range"]=round(wr)
        else: row[wname+"_dir"]="NONE"

    prev=None
    for td in reversed(all_dates):
        if td<day: prev=td; break
    if prev:
        pp=grouped.get(prev)
        if pp is not None:
            pny=bt(pp,"09:30","16:00")
            if len(pny)>=2:
                pm2=float(pny.iloc[-1]["Close"])-float(pny.iloc[0]["Open"])
                row["prev_dir"]="BULL" if pm2>30 else("BEAR" if pm2<-30 else"FLAT")
    rows.append(row)

df=pd.DataFrame(rows); n=len(df)
rec=df[df["date"]>=date(2024,4,10)]
bb=(df["ny_dir"]=="BULL").sum(); be=(df["ny_dir"]=="BEAR").sum()

print(f"\n{'='*60}")
print(f"  LUNES - {n} sesiones | {len(rec)} recientes (2024+)")
print(f"{'='*60}")
print(f"  Base 9Y: BULL {bb}({bb/n*100:.0f}%) BEAR {be}({be/n*100:.0f}%) FLAT {n-bb-be}({(n-bb-be)/n*100:.0f}%)")
print(f"  Base 2Y: BULL {(rec['ny_dir']=='BULL').sum()}({(rec['ny_dir']=='BULL').sum()/len(rec)*100:.0f}%) "
      f"BEAR {(rec['ny_dir']=='BEAR').sum()}({(rec['ny_dir']=='BEAR').sum()/len(rec)*100:.0f}%)")
print(f"  Rango: Med={df['ny_range'].median():.0f}  Avg={df['ny_range'].mean():.0f}  P75={df['ny_range'].quantile(.75):.0f}")

print(f"\n  VENTANAS DE TIEMPO - LUNES:")
print(f"  {'Ventana':<20} {'BULL->BULL':>10}  {'BEAR->BEAR':>10}  n_bull  n_bear")
print("  "+"-"*58)
for wname,_,_ in windows:
    feat=wname+"_dir"
    if feat not in df.columns: continue
    bull_s=df[df[feat]=="BULL"]; bear_s=df[df[feat]=="BEAR"]
    if len(bull_s)<3 and len(bear_s)<3: continue
    bp=(bull_s["ny_dir"]=="BULL").sum()/max(len(bull_s),1)*100
    ep=(bear_s["ny_dir"]=="BEAR").sum()/max(len(bear_s),1)*100
    lbl=wname.replace("w","").replace("_"," ")
    bfl=" OK" if bp>=60 else""; efl=" OK" if ep>=60 else""
    print(f"  {lbl:<20} {bp:>9.1f}%{bfl}  {ep:>9.1f}%{efl}  {len(bull_s):>6}  {len(bear_s):>6}")

print(f"\n  OR SIZE LUNES (size->efectividad):")
hv=df[df["w0930_0959_range"]>0]
for lo,hi,lbl in [(0,30,"<30"),(30,60,"30-60"),(60,100,"60-100"),(100,999,">100")]:
    bull_or=hv[(hv["w0930_0959_range"]>=lo)&(hv["w0930_0959_range"]<hi)&(hv["w0930_0959_dir"]=="BULL")]
    bear_or=hv[(hv["w0930_0959_range"]>=lo)&(hv["w0930_0959_range"]<hi)&(hv["w0930_0959_dir"]=="BEAR")]
    if len(bull_or)<2 and len(bear_or)<2: continue
    bp=(bull_or["ny_dir"]=="BULL").sum()/max(len(bull_or),1)*100
    ep=(bear_or["ny_dir"]=="BEAR").sum()/max(len(bear_or),1)*100
    print(f"  {lbl:<8}OR BULL={bp:.0f}%(n={len(bull_or)})  OR BEAR={ep:.0f}%(n={len(bear_or)})")

print(f"\n  TODOS LOS PREDICTORES LUNES >=55%:")
feats=[("pm_dir","PM dir"),("asia_dir","Asia dir"),("spike","Spike 8:30"),("prev_dir","Prev(vie)"),
       ("vxn_lvl","VXN nivel")]
feats+=[(w+"_dir","Window "+w.replace("w","").replace("_"," ")) for w,_,_ in windows]
for feat,label in feats:
    if feat not in df.columns: continue
    for v in df[feat].dropna().unique():
        if v in("NONE","FLAT"): continue
        sub=df[df[feat]==v]
        if len(sub)<5: continue
        for d2 in["BULL","BEAR"]:
            nc=(sub["ny_dir"]==d2).sum(); p=nc/len(sub)*100
            if p>=55:
                fl=" OK" if p>=65 else(" meh" if p>=60 else"")
                print(f"  {label}={v} -> {d2}: {p:.1f}% (n={len(sub)}){fl}")

print(f"\n  TIMING LUNES:")
for direction,col in[("BULL","ny_hi_h"),("BEAR","ny_lo_h")]:
    sub=df[(df["ny_dir"]==direction)&df[col].notna()]; hours=sub[col]
    if len(sub)<5: continue
    lbl="HIGH" if direction=="BULL" else"LOW"
    print(f"  {direction} ({len(sub)} sess) - {lbl}: Med={hours.median():.1f}h Avg={hours.mean():.1f}h")
    for lo,hi,lh in[(9.5,10.5,"9:30-10:30"),(10.5,11.5,"10:30-11:30"),(11.5,12.5,"11:30-12:30"),(12.5,14,"12:30-14:00"),(14,16.5,"14:00-16:00")]:
        cnt=(hours>=lo)&(hours<hi); nk=cnt.sum()
        print(f"    {lh}: {nk} ({nk/len(sub)*100:.0f}%)")

print("\n  DONE LUNES")
