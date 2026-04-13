"""
deep_study_v3.py — Round 2 deep dive NQ Futures
══════════════════════════════════════════════════════════════════
NUEVOS CANDIDATOS para todos los días:

  A. VXN TREND (sube/baja vs día anterior) — no solo el nivel
  B. Opening Range breakout 9:30-10:00 → ¿predice dirección NY?
  C. Ventana reciente 2Y vs 9Y completos (¿cambió el régimen?)
  D. NFP Friday isolation (primer viernes del mes)
  E. Contexto semana completa Lun→Jue → ¿predice Viernes?
  F. Día anterior: ¿fuerza del move (range) predice fade/follow?

Salida: rulebook accionable por día + tabla de regimes
"""

import sys, json
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, date, timedelta

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

print("\n"+"█"*68)
print("  DEEP STUDY v3 — NQ Futures | Round 2")
print("  A.VXN_trend  B.OpenRange  C.Régimen  D.NFP  E.Semana  F.Fade")
print("█"*68+"\n")

# ── CARGA ─────────────────────────────────────────────────────
raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"],utc=True).dt.tz_convert(ET)
raw.set_index("Datetime",inplace=True)
for c in ["Close","High","Low","Open"]: raw[c]=pd.to_numeric(raw[c],errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
print(f"  {len(raw)} barras | {raw.index.min().date()} → {raw.index.max().date()}")

print("  Descargando ^VXN...")
vxn_day = {}
try:
    import yfinance as yf
    vdf = yf.download("^VXN",period="24mo",interval="1d",progress=False,auto_adjust=True)
    if isinstance(vdf.columns,pd.MultiIndex): vdf.columns=vdf.columns.get_level_values(0)
    for idx,row in vdf.iterrows():
        vxn_day[idx.date()]=round(float(row["Close"]),2)
    print(f"  VXN: {len(vxn_day)} días")
except: print("  VXN no disponible")

def bt(d,t0,t1):
    a=datetime.strptime(t0,"%H:%M").time(); b=datetime.strptime(t1,"%H:%M").time()
    return d[(d.index.time>=a)&(d.index.time<=b)]

all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday()<5})
cutoff_2y = date(2024,4,10)   # 2 años hacia atrás desde hoy

# ── PRECOMPUTE FAST (solo lo necesario) ──────────────────────
print("  Precalculando stats...")
day_stats = {}
for day in all_dates:
    s0=ET.localize(datetime(day.year,day.month,day.day,0,0))
    s1=ET.localize(datetime(day.year,day.month,day.day,16,30))
    d=raw[(raw.index>=s0)&(raw.index<=s1)].copy()
    if d.empty: continue

    pm=bt(d,"07:00","09:29"); ny=bt(d,"09:30","16:00"); or_=bt(d,"09:30","09:59")
    spk=bt(d,"08:30","08:44"); pre=bt(d,"08:00","08:29")
    st={"day":day}

    if len(pm)>=2:
        pm_m=float(pm.iloc[-1]["Close"])-float(pm.iloc[0]["Open"])
        pm_r=float(pm["High"].max())-float(pm["Low"].min())
        st.update({"pm_move":round(pm_m),"pm_range":round(pm_r),
            "pm_dir":"BULL" if pm_m>15 else("BEAR" if pm_m<-15 else "FLAT"),
            "pm_size":"SMALL" if pm_r<80 else("MED" if pm_r<160 else "LARGE"),
            "pm_close":float(pm.iloc[-1]["Close"]),"pm_open":float(pm.iloc[0]["Open"])})

    if len(ny)>=4:
        ny_o=float(ny.iloc[0]["Open"]); ny_c=float(ny.iloc[-1]["Close"])
        ny_m=ny_c-ny_o; ny_h=float(ny["High"].max()); ny_l=float(ny["Low"].min())
        ny_r=ny_h-ny_l
        idx_hi=ny["High"].idxmax(); idx_lo=ny["Low"].idxmin()
        st.update({"ny_open":round(ny_o),"ny_close":round(ny_c),"ny_move":round(ny_m),
            "ny_range":round(ny_r),"ny_hi":round(ny_h),"ny_lo":round(ny_l),
            "ny_dir":"BULL" if ny_m>30 else("BEAR" if ny_m<-30 else "FLAT"),
            "ny_hi_h":round(idx_hi.hour+idx_hi.minute/60,2),
            "ny_lo_h":round(idx_lo.hour+idx_lo.minute/60,2),
            "hi_first":idx_hi<idx_lo})

    # Opening range 9:30-10:00
    if len(or_)>=2:
        or_m=float(or_.iloc[-1]["Close"])-float(or_.iloc[0]["Open"])
        or_h=float(or_["High"].max()); or_l=float(or_["Low"].min()); or_r=or_h-or_l
        st.update({"or_dir":"BULL" if or_m>10 else("BEAR" if or_m<-10 else "FLAT"),
                   "or_range":round(or_r),"or_high":round(or_h),"or_low":round(or_l)})

    # Spike
    if len(spk)>=1 and len(pre)>=1:
        sm=float(spk.iloc[-1]["Close"])-float(pre.iloc[-1]["Close"])
        st["spike_dir"]="UP" if sm>25 else("DOWN" if sm<-25 else "FLAT")
    else: st["spike_dir"]="NONE"

    day_stats[day]=st
print(f"  {len(day_stats)} días OK\n")

# ── BUILD SESSIONS ────────────────────────────────────────────
def build(weekday):
    days=[d for d in all_dates if pd.Timestamp(d).weekday()==weekday]
    rows=[]
    for day in days:
        if day not in day_stats: continue
        st=day_stats[day]
        if "ny_dir" not in st: continue

        prev=None
        for td in reversed(all_dates):
            if td<day: prev=td; break
        ps=day_stats.get(prev,{})

        # VXN + VXN trend
        vxn=vxn_day.get(day); vxn_prev=vxn_day.get(prev) if prev else None
        vxn_lvl=None; vxn_trend="NONE"
        if vxn: vxn_lvl="LOW" if vxn<20 else("MID" if vxn<25 else("HIGH" if vxn<30 else "PANIC"))
        if vxn and vxn_prev:
            delta=vxn-vxn_prev
            vxn_trend="RISING" if delta>0.5 else("FALLING" if delta<-0.5 else "FLAT")

        # Gap
        gap_d="NONE"
        if "ny_close" in ps and "ny_open" in st:
            g=st["ny_open"]-ps["ny_close"]
            gap_d="GAP_UP" if g>15 else("GAP_DOWN" if g<-15 else "FLAT")

        # Tendencia semanal (todos los días de esta semana antes de hoy)
        ws=day-timedelta(days=day.weekday())
        wdays=[d for d in all_dates if ws<=d<day]
        wdir="NONE"; wpct=0
        if wdays:
            opens=[day_stats[d].get("ny_open",0) for d in wdays if "ny_open" in day_stats.get(d,{})]
            closes=[day_stats[d].get("ny_close",0) for d in wdays if "ny_close" in day_stats.get(d,{})]
            if opens and closes:
                wm=closes[-1]-opens[0]
                wdir="BULL" if wm>50 else("BEAR" if wm<-50 else "FLAT")
                # Cuántos días en la misma dirección
                bulls=sum(1 for d in wdays if day_stats.get(d,{}).get("ny_dir")=="BULL")
                bears=sum(1 for d in wdays if day_stats.get(d,{}).get("ny_dir")=="BEAR")
                wpct=bulls/(len(wdays)+1e-9)

        # NFP: primer viernes de cada mes
        is_nfp=False
        if weekday==4:  # viernes
            is_nfp=day.day<=7  # primer viernes cae entre 1-7

        # FOMC: tercer miércoles/jueves (aprox)
        is_fomc=False
        if weekday in (2,3):
            # heuristic: tercer aparición del día en el mes
            count=sum(1 for d in all_dates if d.month==day.month and d.year==day.year
                      and pd.Timestamp(d).weekday()==weekday and d<=day)
            is_fomc=(count==3)

        # Open range breakout vs PM range
        or_d=st.get("or_dir","NONE")
        pm_d=st.get("pm_dir","NONE")
        
        # OR y PM agreement
        or_pm_agree=False
        if or_d!="NONE" and pm_d!="NONE" and or_d!="FLAT" and pm_d!="FLAT":
            or_pm_agree=(or_d==pm_d)

        rows.append({
            "date":day, "recent":(day>=cutoff_2y),
            "ny_dir":st.get("ny_dir","NONE"), "ny_move":st.get("ny_move",0),
            "ny_range":st.get("ny_range",0),
            "ny_hi_h":st.get("ny_hi_h"), "ny_lo_h":st.get("ny_lo_h"),
            "hi_first":st.get("hi_first",False),
            "pm_dir":pm_d, "pm_range":st.get("pm_range",0),
            "pm_size":st.get("pm_size","NONE"),
            "or_dir":or_d, "or_range":st.get("or_range",0),
            "or_pm_agree":or_pm_agree,
            "spike":st.get("spike_dir","NONE"),
            "prev_dir":ps.get("ny_dir","NONE"),
            "prev_range":ps.get("ny_range",0),
            "prev_big":(ps.get("ny_range",0)>200),
            "gap":gap_d, "weekly":wdir,
            "vxn":vxn, "vxn_lvl":vxn_lvl, "vxn_trend":vxn_trend,
            "is_nfp":is_nfp, "is_fomc":is_fomc,
        })
    return pd.DataFrame(rows)

# ── EVALUATE ──────────────────────────────────────────────────
def ev(df,feat,min_n=6):
    res=[]
    for v in df[feat].dropna().unique():
        if v in(None,"NONE","FLAT",False): continue
        sub=df[df[feat]==v]
        if len(sub)<min_n: continue
        for d in ["BULL","BEAR"]:
            nc=(sub["ny_dir"]==d).sum(); pct=nc/len(sub)*100
            res.append({"feat":feat,"val":v,"dir":d,"pct":pct,"n":len(sub),"nc":nc})
    return sorted(res,key=lambda x:x["pct"],reverse=True)

def banner(txt): print("\n"+"═"*68); print(f"  {txt}"); print("═"*68)
def W(n): return "█"*int(n/5)
def flag(pct): return " ✅" if pct>=65 else(" ⚠️" if pct>=57 else"")

# ══════════════════════════════════════════════════════════════
def analyze_day(wd, name):
    df=build(wd); n=len(df)
    if n<10: return
    rec=df[df["recent"]]; old=df[~df["recent"]]
    print(f"\n\n{'█'*68}")
    print(f"  📅  {name.upper()}  — {n} sesiones total  |  {len(rec)} recientes (2024-2026)")
    print(f"{'█'*68}")

    bb=(df["ny_dir"]=="BULL").sum(); be=(df["ny_dir"]=="BEAR").sum()
    print(f"  Base 9Y: BULL {bb}({bb/n*100:.0f}%) BEAR {be}({be/n*100:.0f}%) FLAT {n-bb-be}({(n-bb-be)/n*100:.0f}%)")
    if len(rec)>=5:
        rb=(rec["ny_dir"]=="BULL").sum(); re=(rec["ny_dir"]=="BEAR").sum()
        print(f"  Base 2Y: BULL {rb}({rb/len(rec)*100:.0f}%) BEAR {re}({re/len(rec)*100:.0f}%) FLAT {len(rec)-rb-re}({(len(rec)-rb-re)/len(rec)*100:.0f}%) ← RECIENTE")

    # ── A. VXN TREND ──────────────────────────────────────────
    banner(f"A. VXN TREND (subiendo/bajando día a día) — {name}")
    hv=df[df["vxn"].notna()]
    if len(hv)>=10:
        print(f"\n  {'VXN Tendencia':<16} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'Med Rng':>8}")
        print("  "+"─"*42)
        for trend in ["RISING","FLAT","FALLING"]:
            sub=hv[hv["vxn_trend"]==trend]
            if len(sub)<4: continue
            bl=(sub["ny_dir"]=="BULL").sum(); be=(sub["ny_dir"]=="BEAR").sum()
            mr=sub["ny_range"].median()
            f=flag(max(bl/len(sub),be/len(sub))*100)
            print(f"  {trend:<16}{len(sub):>3}  {bl/len(sub)*100:>5.0f}%  {be/len(sub)*100:>5.0f}%  {mr:>8.0f}{f}")

        # VXN nivel + trend
        print(f"\n  VXN nivel + tendencia:")
        print(f"  {'Nivel+Trend':<22} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'Med Rng':>8}")
        print("  "+"─"*46)
        for lvl in ["LOW","MID","HIGH","PANIC"]:
            for tr in ["RISING","FALLING"]:
                sub=hv[(hv["vxn_lvl"]==lvl)&(hv["vxn_trend"]==tr)]
                if len(sub)<4: continue
                bl=(sub["ny_dir"]=="BULL").sum(); be=(sub["ny_dir"]=="BEAR").sum()
                mr=sub["ny_range"].median()
                fl=flag(max(bl/len(sub),be/len(sub))*100)
                print(f"  {lvl} {tr:<14}{len(sub):>3}  {bl/len(sub)*100:>5.0f}%  {be/len(sub)*100:>5.0f}%  {mr:>8.0f}{fl}")

    # ── B. OPENING RANGE 9:30-10:00 ──────────────────────────
    banner(f"B. OPENING RANGE BREAKOUT (9:30-10:00) — {name}")
    print(f"\n  {'OR Dir':<12} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}  {'Follows':>8}  {'Med Rng':>8}")
    print("  "+"─"*50)
    for d in ["BULL","BEAR","FLAT"]:
        sub=df[df["or_dir"]==d]
        if len(sub)<4: continue
        bl=(sub["ny_dir"]=="BULL").sum(); be=(sub["ny_dir"]=="BEAR").sum()
        follows=bl if d=="BULL" else(be if d=="BEAR" else"-")
        f_pct=follows/len(sub)*100 if isinstance(follows,int) else 0
        fl=flag(f_pct)
        mr=sub["ny_range"].median()
        print(f"  OR {d:<9}{len(sub):>3}  {bl/len(sub)*100:>5.0f}%  {be/len(sub)*100:>5.0f}%  {f_pct:>7.0f}%{fl}  {mr:>8.0f}")

    # OR + PM agreement
    agree=df[df["or_pm_agree"]==True]
    if len(agree)>=6:
        ab=(agree["ny_dir"]=="BULL").sum(); ae=(agree["ny_dir"]=="BEAR").sum()
        print(f"\n  OR+PM MISMO SENTIDO: {len(agree)} sess → segue dirección: {max(ab,ae)}/{len(agree)} = {max(ab,ae)/len(agree)*100:.0f}%")
        agree_bull=agree[agree["or_dir"]=="BULL"]
        agree_bear=agree[agree["or_dir"]=="BEAR"]
        if len(agree_bull)>=5:
            nc=(agree_bull["ny_dir"]=="BULL").sum()
            print(f"    OR+PM BULL: {nc}/{len(agree_bull)} = {nc/len(agree_bull)*100:.0f}% → NY BULL{flag(nc/len(agree_bull)*100)}")
        if len(agree_bear)>=5:
            nc=(agree_bear["ny_dir"]=="BEAR").sum()
            print(f"    OR+PM BEAR: {nc}/{len(agree_bear)} = {nc/len(agree_bear)*100:.0f}% → NY BEAR{flag(nc/len(agree_bear)*100)}")

    # ── C. RÉGIMEN RECIENTE (2Y) VS HISTORIA ─────────────────
    if len(rec)>=10:
        banner(f"C. RÉGIMEN: Últimos 2 años vs 9 años — {name}")
        print(f"\n  {'Feature':<30} {'9Y':>6}  {'2Y reciente':>12}")
        print("  "+"─"*52)
        for feat,v,d in [("pm_dir","BULL","BULL"),("pm_dir","BEAR","BEAR"),
                          ("or_dir","BULL","BULL"),("or_dir","BEAR","BEAR"),
                          ("vxn_lvl","HIGH","BEAR"),("vxn_trend","RISING","BEAR")]:
            # 9Y
            sub9=df[df[feat]==v]; nc9=(sub9["ny_dir"]==d).sum()
            pct9=nc9/len(sub9)*100 if len(sub9)>=4 else 0
            # 2Y
            sub2=rec[rec[feat]==v]; nc2=(sub2["ny_dir"]==d).sum()
            pct2=nc2/len(sub2)*100 if len(sub2)>=3 else 0
            if len(sub9)<4: continue
            changed="⚠️ CAMBIÓ" if abs(pct2-pct9)>15 else("")
            print(f"  {feat}={v}→{d:<12} {pct9:>5.0f}%  {pct2:>10.0f}%  {changed}")

    # ── E. CONTEXTO SEMANAL ────────────────────────────────────
    banner(f"E. CONTEXTO SEMANAL (lunes→prev day) — {name}")
    print(f"\n  {'Semana Previa':<14} {'N':>3}  {'BULL%':>6}  {'BEAR%':>6}")
    print("  "+"─"*34)
    for wv in ["BULL","BEAR","FLAT"]:
        sub=df[df["weekly"]==wv]
        if len(sub)<4: continue
        bl=(sub["ny_dir"]=="BULL").sum(); be=(sub["ny_dir"]=="BEAR").sum()
        print(f"  Semana {wv:<8}{len(sub):>3}  {bl/len(sub)*100:>5.0f}%  {be/len(sub)*100:>5.0f}%")

    # ── F. FADE / FOLLOW (día anterior range grande) ──────────
    banner(f"F. FADE vs FOLLOW — Día anterior grande → ¿rebote o continuación?")
    prev_big=df[df["prev_big"]==True]
    prev_small=df[df["prev_range"]<100]
    if len(prev_big)>=5:
        pb=(prev_big["ny_dir"]=="BULL").sum(); pe=(prev_big["ny_dir"]=="BEAR").sum()
        pb_dir=prev_big["prev_dir"]
        # Fade analysis
        fade=prev_big.apply(lambda r: r["ny_dir"]!=r["prev_dir"] if r["prev_dir"] in("BULL","BEAR") and r["ny_dir"] in("BULL","BEAR") else None, axis=1)
        fade_n=fade.dropna().sum()
        print(f"\n  Día anterior range >200pts ({len(prev_big)} sess):")
        print(f"    → NY BULL {pb}({pb/len(prev_big)*100:.0f}%)  BEAR {pe}({pe/len(prev_big)*100:.0f}%)")
        if len(fade.dropna())>0:
            print(f"    → FADE (va vs dirección previa): {fade_n}/{len(fade.dropna())} = {fade_n/len(fade.dropna())*100:.0f}%")

    # ── D. NFP / FOMC special ─────────────────────────────────
    nfp=df[df["is_nfp"]==True]
    fomc=df[df["is_fomc"]==True]
    if len(nfp)>=4:
        banner(f"D. NFP / FOMC EFFECTS — {name}")
        nb=(nfp["ny_dir"]=="BULL").sum(); ne=(nfp["ny_dir"]=="BEAR").sum()
        nr=nfp["ny_range"].median()
        print(f"\n  NFP ({len(nfp)} sess): BULL {nb}({nb/len(nfp)*100:.0f}%) BEAR {ne}({ne/len(nfp)*100:.0f}%)  Rng med:{nr:.0f}")
        non_nfp=df[df["is_nfp"]==False]
        if len(non_nfp)>=5:
            nnb=(non_nfp["ny_dir"]=="BULL").sum(); nne=(non_nfp["ny_dir"]=="BEAR").sum()
            nnr=non_nfp["ny_range"].median()
            print(f"  no-NFP ({len(non_nfp)} sess): BULL {nnb}({nnb/len(non_nfp)*100:.0f}%) BEAR {nne}({nne/len(non_nfp)*100:.0f}%)  Rng med:{nnr:.0f}")
            # NFP con VXN HIGH
            nfp_vxn=nfp[nfp["vxn_lvl"]=="HIGH"]
            if len(nfp_vxn)>=3:
                nv=(nfp_vxn["ny_dir"]=="BEAR").sum()
                print(f"  NFP + VXN HIGH ({len(nfp_vxn)} sess): BEAR {nv}/{len(nfp_vxn)} = {nv/len(nfp_vxn)*100:.0f}%")
    if len(fomc)>=4:
        fb=(fomc["ny_dir"]=="BULL").sum(); fe=(fomc["ny_dir"]=="BEAR").sum()
        fr=fomc["ny_range"].median()
        print(f"\n  FOMC semana ({len(fomc)} sess): BULL {fb}({fb/len(fomc)*100:.0f}%) BEAR {fe}({fe/len(fomc)*100:.0f}%)  Rng med:{fr:.0f}")

    # ── RULEBOOK FINAL ────────────────────────────────────────
    banner(f"📋 RULEBOOK — {name} | Reglas validadas ≥60%")
    rules=[]
    all_feats=["pm_dir","pm_size","or_dir","or_pm_agree","vxn_lvl","vxn_trend","gap","weekly","spike","prev_dir","prev_big","is_nfp","is_fomc"]
    seen=set()
    for feat in all_feats:
        if feat not in df.columns: continue
        for r in ev(df,feat):
            if r["pct"]>=60 and r["n"]>=6:
                key=(feat,r["val"],r["dir"])
                if key not in seen:
                    seen.add(key); rules.append(r)
    # Combos entre top feats
    top_feats=list(dict.fromkeys([r["feat"] for r in rules[:5]]))
    for i in range(min(4,len(top_feats))):
        for j in range(i+1,min(5,len(top_feats))):
            f1=top_feats[i]; f2=top_feats[j]
            for v1 in df[f1].dropna().unique():
                for v2 in df[f2].dropna().unique():
                    if v1 in(None,"NONE","FLAT",False) or v2 in(None,"NONE","FLAT",False): continue
                    sub=df[(df[f1]==v1)&(df[f2]==v2)]
                    if len(sub)<6: continue
                    for d in ["BULL","BEAR"]:
                        nc=(sub["ny_dir"]==d).sum(); pct=nc/len(sub)*100
                        if pct>=65:
                            key=(f"COMBO:{f1}={v1}+{f2}={v2}",d)
                            if key not in seen:
                                seen.add(key)
                                rules.append({"feat":f"COMBO:{f1}={v1}","val":f"{f2}={v2}","dir":d,"pct":pct,"n":len(sub),"nc":nc})

    rules.sort(key=lambda x:(x["pct"],-x["n"]),reverse=True)
    print()
    for i,r in enumerate(rules[:10]):
        m="🥇" if i==0 else("🥈" if i==1 else("🥉" if i==2 else f"  {i+1}."))
        print(f"  {m} {r['feat']}={r['val']} → NY {r['dir']}: {r['nc']}/{r['n']} = {r['pct']:.1f}%  {W(r['pct'])}{flag(r['pct'])}")
    if not rules: print("  (ninguna regla ≥60%)")

    return {"sessions":n,"recent":len(rec),
            "rules":[f"{r['feat']}={r['val']} → {r['dir']}: {r['pct']:.0f}%" for r in rules[:5]]}

# ── MAIN ──────────────────────────────────────────────────────
arg=sys.argv[1].lower() if len(sys.argv)>1 else "all"
results={}

DIAS={
    "tuesday":(1,"MARTES"),
    "wednesday":(2,"MIÉRCOLES"),
    "thursday":(3,"JUEVES"),
    "friday":(4,"VIERNES"),
}
if arg=="all":
    for k,(wd,name) in DIAS.items():
        results[name]=analyze_day(wd,name)
else:
    for k,(wd,name) in DIAS.items():
        if arg in k or arg in name.lower():
            results[name]=analyze_day(wd,name); break
    if not results:
        print(f"  Día '{arg}' no reconocido. Opciones: tuesday/wednesday/thursday/friday/all")

# ── RESUMEN EJECUTIVO ─────────────────────────────────────────
print("\n\n"+"═"*68)
print("  📊  RULEBOOK FINAL — Reglas validadas por día")
print("═"*68)
for day_name,res in results.items():
    print(f"\n  {day_name}  ({res['sessions']}sess 9Y / {res['recent']}sess 2Y reciente)")
    for r in res.get("rules",[]):
        print(f"    ✅ {r}")
    if not res.get("rules"): print("    ⚠️  Sin reglas ≥60%")

out={"timestamp":str(datetime.now()),"rulebook":results}
with open("data/deep_rulebook_v3.json","w",encoding="utf-8") as f:
    json.dump(out,f,indent=2,ensure_ascii=False,default=str)
print(f"\n  💾 Guardado: data/deep_rulebook_v3.json")
print("█"*68+"\n")
