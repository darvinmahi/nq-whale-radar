"""
Ultimos 20 lunes: VXN zona + COT + Viernes anterior + prediccion Vie->Lun
"""
import yfinance as yf, pandas as pd, csv
from datetime import datetime, date

PERIOD = "5y"
print("Descargando datos...")
qqq = yf.download("QQQ",  period=PERIOD, auto_adjust=True, progress=False)
vxn = yf.download("^VXN", period=PERIOD, auto_adjust=True, progress=False)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

qqq_o=col(qqq,"Open"); qqq_h=col(qqq,"High")
qqq_l=col(qqq,"Low");  qqq_c=col(qqq,"Close"); vxn_c=col(vxn,"Close")

df = pd.DataFrame({"O":qqq_o,"H":qqq_h,"L":qqq_l,"C":qqq_c,"VXN":vxn_c}).dropna()
df.index = pd.to_datetime(df.index).tz_localize(None)

# COT
cot_rows = []
try:
    with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
                ll = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
                ls = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                nc_l = int(r.get("NonComm_Positions_Long_All",0) or 0)
                nc_s = int(r.get("NonComm_Positions_Short_All",0) or 0)
                cot_rows.append({"date":d,"lev_net":ll-ls,"nc_net":nc_l-nc_s,
                                  "signal":"BULL" if ll>ls else "BEAR"})
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
    print(f"COT: {len(cot_rows)} semanas")
except Exception as e:
    print(f"COT no disponible: {e}")

def get_cot(monday):
    prev = [r for r in cot_rows if r["date"] < monday]
    return prev[-1] if prev else {"lev_net":0,"nc_net":0,"signal":"?"}

def vxn_zona(v):
    if v>=33: return "XFEAR🔴🔴"
    if v>=25: return "FEAR🔴"
    if v>=18: return "NEUTRAL🟡"
    return "GREED🟢"

def dir_label(pct):
    if pct > 0.15: return "BULL"
    if pct < -0.15: return "BEAR"
    return "FLAT"

dates = df.index.tolist()
results = []

for i, dt in enumerate(dates):
    if dt.weekday() != 0: continue
    prev_dates = [d for d in dates[:i]]
    if not prev_dates: continue
    prev = prev_dates[-1]

    vxn_val = float(df.loc[prev,"VXN"])
    zona = vxn_zona(vxn_val)

    # Lunes
    mo = float(df.loc[dt,"O"]); mh=float(df.loc[dt,"H"])
    ml=float(df.loc[dt,"L"]);   mc=float(df.loc[dt,"C"])
    mpc=float(df.loc[prev,"C"])

    gap_pct  = (mo - mpc) / mpc * 100
    move_pct = (mc - mo)  / mo  * 100
    c2c_pct  = (mc - mpc) / mpc * 100   # close-to-close = indice real del dia
    rng_pct  = (mh - ml)  / mo  * 100
    mon_dir  = dir_label(move_pct)
    pos      = (mc-ml)/(mh-ml) if mh!=ml else 0.5

    # Viernes anterior
    fri_dates = [d for d in dates[:i] if d.weekday()==4]
    fri = fri_dates[-1] if fri_dates else prev
    fo=float(df.loc[fri,"O"]); fh=float(df.loc[fri,"H"])
    fl=float(df.loc[fri,"L"]); fc=float(df.loc[fri,"C"])
    fri_move = (fc-fo)/fo*100
    fri_rng  = (fh-fl)/fo*100
    fri_dir  = dir_label(fri_move)
    # VXN del jueves (antes del viernes)
    fri_idx  = dates.index(fri)
    prev_fri = dates[fri_idx-1] if fri_idx>0 else fri
    vxn_fri  = float(df.loc[prev_fri,"VXN"]) if prev_fri in df.index else vxn_val

    # COT
    cot = get_cot(dt.date())

    # Prediccion: Viernes predijo lunes?
    if fri_dir in ("BULL","BEAR") and mon_dir in ("BULL","BEAR"):
        pred = "✅ SÍ" if fri_dir == mon_dir else "❌ NO"
        pred_key = "SI" if fri_dir == mon_dir else "NO"
    else:
        pred = "— FLAT"
        pred_key = "FLAT"

    # COT predijo lunes?
    cot_pred = "?"
    if cot["signal"] in ("BULL","BEAR") and mon_dir in ("BULL","BEAR"):
        cot_pred = "✅" if cot["signal"] == mon_dir else "❌"

    results.append({
        "date":dt, "fri":fri,
        "vxn":round(vxn_val,1), "zona":zona,
        "fri_dir":fri_dir, "fri_move":round(fri_move,2), "fri_rng":round(fri_rng,2),
        "gap_pct":round(gap_pct,2), "move_pct":round(move_pct,2),
        "c2c_pct":round(c2c_pct,2),   # % indice real (cierre vs cierre anterior)
        "rng_pct":round(rng_pct,2), "mon_dir":mon_dir, "pos":round(pos,2),
        "close":round(mc,2),           # precio de cierre del lunes
        "cot_signal":cot["signal"], "lev_net":cot["lev_net"], "nc_net":cot["nc_net"],
        "pred":pred, "pred_key":pred_key, "cot_pred":cot_pred
    })

df_r = pd.DataFrame(results).sort_values("date", ascending=False)
last20 = df_r.head(20)

# ═══════════════════════════════════════════
print(f"\n{'═'*118}")
print(f"  ÚLTIMOS 20 LUNES — VXN + COT + VIERNES + % ÍNDICE REAL")
print(f"{'═'*118}")
print(f"  {'Lunes':12} {'VXN':5} {'Zona':12} {'COT':5} {'LevNet':>9} │ {'Vie':4} {'Vie%':>6} │ {'Gap%':>6} {'O→C%':>6} {'%C2C':>6} {'Cierre':>7} {'Rng%':>5} {'Dir':4} │ {'Vie→Lun':8} {'COT':4}")
print(f"  {'-'*116}")

for _, r in last20.iterrows():
    today_mark = " ◄HOY" if r["date"].date()==date(2026,3,30) else ""
    c_signal = r["cot_signal"]
    # Color markers en texto
    c2c_sign = "+" if r["c2c_pct"] >= 0 else ""
    print(
        f"  {r['date'].strftime('%d %b %Y'):12} "
        f"{r['vxn']:5.1f} {r['zona']:12} "
        f"{c_signal:5} {r['lev_net']:>9,} │ "
        f"{r['fri_dir']:4} {r['fri_move']:>+5.2f}% │ "
        f"{r['gap_pct']:>+5.2f}% {r['move_pct']:>+5.2f}% "
        f"{c2c_sign}{r['c2c_pct']:>5.2f}% {r['close']:>7.2f} "
        f"{r['rng_pct']:>5.2f}% {r['mon_dir']:4} │ "
        f"{r['pred']:9}{r['cot_pred']:3}{today_mark}"
    )

# ═══════════════════════════════════════════
print(f"\n{'═'*60}")
print(f"  ESTADÍSTICAS — últimos 20 lunes")
print(f"{'═'*60}")

n = len(last20)
n_bull = (last20.mon_dir=="BULL").sum()
n_bear = (last20.mon_dir=="BEAR").sum()
n_flat = (last20.mon_dir=="FLAT").sum()

# Prediccion Viernes
pred_si  = (last20.pred_key=="SI").sum()
pred_no  = (last20.pred_key=="NO").sum()
pred_tot = pred_si + pred_no

# COT prediccion
cot_si  = (last20.cot_pred=="✅").sum()
cot_no  = (last20.cot_pred=="❌").sum()
cot_tot = cot_si + cot_no

print(f"\n  Resultado lunes:  BULL {n_bull} ({n_bull/n*100:.0f}%)  BEAR {n_bear} ({n_bear/n*100:.0f}%)  FLAT {n_flat}")
print(f"\n  Viernes predice lunes (misma dirección):")
print(f"    SÍ: {pred_si}/{pred_tot} = {pred_si/pred_tot*100:.0f}%")
print(f"    NO: {pred_no}/{pred_tot} = {pred_no/pred_tot*100:.0f}%")

print(f"\n  COT predice lunes (misma dirección):")
print(f"    SÍ: {cot_si}/{cot_tot} = {cot_si/cot_tot*100:.0f}%")
print(f"    NO: {cot_no}/{cot_tot} = {cot_no/cot_tot*100:.0f}%")

# Desglose Viernes por zona VXN
print(f"\n  Viernes→Lunes por zona VXN (últimos 20):")
for zona_key, lo, hi in [("XFEAR",33,99),("FEAR",25,33),("NEUTRAL",18,25),("GREED",0,18)]:
    sub = last20[(last20.vxn>=lo)&(last20.vxn<hi)]
    if sub.empty: continue
    sp = sub[sub.pred_key=="SI"]
    sn = sub[sub.pred_key=="NO"]
    tot = len(sp)+len(sn)
    pct = f"{len(sp)/tot*100:.0f}%" if tot else "—"
    print(f"    {zona_key:8} (n={len(sub):2d}):  Vie acierta {pct}  ({len(sp)}/{tot})")

print(f"\n  Rango medio últimos 20 lunes:  {last20.rng_pct.mean():.2f}% = ~{last20.rng_pct.mean()*230:.0f} pts NQ")
print(f"  % índice medio (C2C):          {last20.c2c_pct.mean():+.2f}%")
print(f"  % índice días BULL (C2C):      {last20[last20.mon_dir=='BULL'].c2c_pct.mean():+.2f}%")
print(f"  % índice días BEAR (C2C):      {last20[last20.mon_dir=='BEAR'].c2c_pct.mean():+.2f}%")
hoy = last20[last20['date'].dt.date==date(2026,3,30)]
if not hoy.empty:
    print(f"\n  HOY 30 Mar: C2C={hoy.c2c_pct.values[0]:+.2f}%  O→C={hoy.move_pct.values[0]:+.2f}%  Cierre={hoy.close.values[0]:.2f}")
