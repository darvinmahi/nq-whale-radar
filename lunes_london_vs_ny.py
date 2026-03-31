"""
lunes_london_vs_ny.py  v2
TODOS los lunes disponibles en NQ 15min
ASIA + LONDON + NY  |  VXN + VIX + COT (validado)
"""
import csv, yfinance as yf, pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict

# ─── 1. NQ 15min ──────────────────────────────────────────────
print("Cargando NQ 15min...")
nq_bars = []
try:
    with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                dt_utc = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
                dt_et  = dt_utc - timedelta(hours=5)   # aprox UTC-5 (EST)
                cl=float(r["Close"]); hi=float(r["High"])
                lo=float(r["Low"]);   op=float(r["Open"])
                if cl > 0:
                    nq_bars.append({"et":dt_et,"c":cl,"h":hi,"l":lo,"o":op})
            except: pass
    nq_bars.sort(key=lambda x: x["et"])
    by_date = defaultdict(list)
    for b in nq_bars: by_date[b["et"].date()].append(b)
    all_dates = sorted(by_date.keys())
    print(f"  {len(nq_bars):,} barras | {all_dates[0]} → {all_dates[-1]}")
except Exception as e:
    print(f"  ERROR NQ 15min: {e}"); exit(1)

# ─── 2. Indicadores diarios (QQQ + VXN + VIX) ─────────────────
print("Descargando QQQ + VXN + VIX (5 anos)...")
qqq = yf.download("QQQ",  period="5y", auto_adjust=True, progress=False)
vxn = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
vix = yf.download("^VIX", period="5y", auto_adjust=True, progress=False)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

dfq = pd.DataFrame({
    "O": col(qqq,"Open"), "H": col(qqq,"High"),
    "L": col(qqq,"Low"),  "C": col(qqq,"Close"),
    "VXN": col(vxn,"Close"),
    "VIX": col(vix,"Close"),
}).dropna()
dfq.index = pd.to_datetime(dfq.index).tz_localize(None)
qdates = dfq.index.tolist()
print(f"  QQQ+VXN+VIX: {dfq.index[0].date()} → {dfq.index[-1].date()}")

# ─── 3. COT (validado: usamos el mas reciente ANTES del lunes) ──
print("Cargando COT...")
cot_rows = []
try:
    with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                # Fecha del reporte COT (publicado viernes, datos de martes)
                d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
                ll  = int(r.get("Lev_Money_Positions_Long_All",0)  or 0)
                ls  = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                ncl = int(r.get("NonComm_Positions_Long_All",0)    or 0)
                ncs = int(r.get("NonComm_Positions_Short_All",0)   or 0)
                cot_rows.append({
                    "date":d,
                    "lev_long":ll, "lev_short":ls, "lev_net":ll-ls,
                    "nc_long":ncl, "nc_short":ncs, "nc_net":ncl-ncs,
                    "sig": "BULL" if ll>ls else "BEAR"
                })
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
    print(f"  COT: {len(cot_rows)} semanas | {cot_rows[0]['date']} → {cot_rows[-1]['date']}")
except Exception as e:
    print(f"  COT no disponible: {e}")

def get_cot(mon_date):
    """Retorna el ultimo reporte COT publicado ANTES del lunes"""
    prev = [r for r in cot_rows if r["date"] <= mon_date]
    return prev[-1] if prev else None

# ─── 4. Helpers ────────────────────────────────────────────────
def vxn_zona(v):
    if v >= 33: return "XFEAR", "🔴🔴"
    if v >= 25: return "FEAR",  "🔴 "
    if v >= 18: return "NEUT",  "🟡 "
    return             "GREED", "🟢 "

def dir_label(pct, thr=0.10):
    if pct >  thr: return "BULL"
    if pct < -thr: return "BEAR"
    return "FLAT"

def session_stats(bars, h0, m0, h1, m1):
    sb = [b for b in bars if
          (b["et"].hour > h0 or (b["et"].hour==h0 and b["et"].minute>=m0)) and
          (b["et"].hour < h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]
    if not sb: return None
    o=sb[0]["o"]; c=sb[-1]["c"]
    h=max(x["h"] for x in sb); l=min(x["l"] for x in sb)
    return {"o":round(o,0),"c":round(c,0),"h":round(h,0),"l":round(l,0),
            "move":round((c-o)/o*100,2),"range":round((h-l)/o*100,2),"n":len(sb)}

# ─── 5. Calcular TODOS los lunes disponibles ──────────────────
mondays_all = sorted([d for d in by_date.keys() if d.weekday()==0], reverse=True)
print(f"\nTotal lunes en NQ 15min: {len(mondays_all)}")

results = []
skipped = 0

for mon in mondays_all:
    bars = by_date[mon]
    if len(bars) < 8:
        skipped += 1; continue

    # ── ASIA: Dom 18:00 → Lun 02:59 ET ──
    sun = mon - timedelta(days=1)
    asia_bars = [b for b in by_date.get(sun,[]) if b["et"].hour >= 18]
    asia_bars += [b for b in bars if b["et"].hour < 3]
    asia_bars.sort(key=lambda x: x["et"])
    asia = None
    if len(asia_bars) >= 3:
        ao=asia_bars[0]["o"]; ac=asia_bars[-1]["c"]
        ah=max(b["h"] for b in asia_bars); al=min(b["l"] for b in asia_bars)
        asia = {"o":round(ao,0),"c":round(ac,0),"move":round((ac-ao)/ao*100,2),
                "range":round((ah-al)/ao*100,2)}

    # ── LONDON: 03:00 → 09:14 ET ──
    lon = session_stats(bars, 3, 0, 9, 14)

    # ── NY: 09:30 → 15:59 ET ──
    ny = session_stats(bars, 9, 30, 15, 59)
    if not ny:
        skipped += 1; continue

    # ── VXN + VIX del viernes previo ──
    mon_ts = pd.Timestamp(mon)
    prev_q = [d for d in qdates if d < mon_ts]
    if not prev_q:
        skipped += 1; continue
    prev_qd = prev_q[-1]
    vxn_val = float(dfq.loc[prev_qd, "VXN"])
    vix_val = float(dfq.loc[prev_qd, "VIX"])
    zona_key, zona_ico = vxn_zona(vxn_val)

    # ── Viernes anterior (QQQ daily) ──
    fri_q = [d for d in qdates if d.weekday()==4 and d < mon_ts]
    if not fri_q:
        skipped += 1; continue
    fri_qd = fri_q[-1]
    fri_date = fri_qd.date()
    fri_o = float(dfq.loc[fri_qd,"O"]); fri_c = float(dfq.loc[fri_qd,"C"])
    fri_h = float(dfq.loc[fri_qd,"H"]); fri_l = float(dfq.loc[fri_qd,"L"])
    fri_move = (fri_c-fri_o)/fri_o*100
    fri_rng  = (fri_h-fri_l)/fri_o*100
    fri_dir  = dir_label(fri_move)

    # ── COT (validado) ──
    cot = get_cot(mon)
    if cot:
        lev_net = cot["lev_net"]
        nc_net  = cot["nc_net"]
        cot_sig = cot["sig"]
        cot_date= cot["date"]
        # Gap de dias entre COT y lunes (para saber si está obsoleto)
        cot_age = (mon - cot_date).days
    else:
        lev_net=0; nc_net=0; cot_sig="?"; cot_date=None; cot_age=999

    # ── Direcciones ──
    asia_dir = dir_label(asia["move"]) if asia else "?"
    lon_dir  = dir_label(lon["move"])  if lon  else "?"
    ny_dir   = dir_label(ny["move"])

    # ── Predicciones ──
    vie_pred = "—"
    if fri_dir in ("BULL","BEAR") and ny_dir in ("BULL","BEAR"):
        vie_pred = "✅" if fri_dir==ny_dir else "❌"

    cot_pred = "—"
    if cot_sig in ("BULL","BEAR") and ny_dir in ("BULL","BEAR"):
        cot_pred = "✅" if cot_sig==ny_dir else "❌"

    results.append({
        "mon":mon, "fri":fri_date,
        "vxn":round(vxn_val,1), "vix":round(vix_val,1),
        "zona_key":zona_key, "zona_ico":zona_ico,
        "fri_dir":fri_dir,"fri_move":round(fri_move,2),"fri_rng":round(fri_rng,2),
        "asia":asia, "asia_dir":asia_dir,
        "lon":lon,   "lon_dir":lon_dir,
        "ny":ny,     "ny_dir":ny_dir,
        "lev_net":lev_net,"nc_net":nc_net,"cot_sig":cot_sig,
        "cot_date":cot_date,"cot_age":cot_age,
        "vie_pred":vie_pred,"cot_pred":cot_pred,
    })

n = len(results)
print(f"Lunes calculados: {n}  |  Saltados: {skipped}")

# ─── 6. OUTPUT ────────────────────────────────────────────────
SEP = "═"*145
sep = "─"*145

print(f"\n{SEP}")
print(f"  TODOS LOS LUNES NQ — ASIA + LONDON + NY  |  VXN + VIX + COT")
print(f"{SEP}")
print(
    f"  {'Lunes':11} {'VXN':5} {'VIX':5} {'Zona':9}"
    f" {'COT':4} {'LevNet':>9} {'COTAge':>6}"
    f" │ {'VIE':4} {'VieM%':>6}"
    f" │ {'ASIA M%':>7} {'ARng%':>5} {'AD':>4}"
    f" │ {'LON M%':>6} {'LRng%':>5} {'LD':>4}"
    f" │ {'NY M%':>6} {'NRng%':>5} {'ND':>4} {'NYO':>6} {'NYC':>6}"
    f" │ {'V→NY':>4} {'C→NY':>4}"
)
print(sep)

# Contadores para estadísticas
stats = {
    "asia":{"bull":0,"bear":0,"flat":0,"moves":[],"rngs":[]},
    "lon": {"bull":0,"bear":0,"flat":0,"moves":[],"rngs":[]},
    "ny":  {"bull":0,"bear":0,"flat":0,"moves":[],"rngs":[]},
    "vie_si":0,"vie_no":0,"cot_si":0,"cot_no":0,
}
# Por zona
zona_stats = {}

for r in results:
    today = " ◄HOY" if r["mon"]==date(2026,3,30) else ""
    asia=r["asia"]; lon=r["lon"]; ny=r["ny"]

    am = f"{asia['move']:+.2f}%" if asia else "  —  "
    ar = f"{asia['range']:.2f}%" if asia else "  — "
    ad = r["asia_dir"]

    lm = f"{lon['move']:+.2f}%" if lon else "  — "
    lr = f"{lon['range']:.2f}%" if lon else "  — "
    ld = r["lon_dir"]

    nm = f"{ny['move']:+.2f}%"
    nr = f"{ny['range']:.2f}%"
    nd = r["ny_dir"]

    cot_age_str = f"{r['cot_age']}d" if r["cot_age"]<99 else "?"

    print(
        f"  {r['mon'].strftime('%d %b %Y'):11}"
        f" {r['vxn']:5.1f} {r['vix']:5.1f} {r['zona_ico']}{r['zona_key']:5}"
        f" {r['cot_sig']:4} {r['lev_net']:>9,} {cot_age_str:>6}"
        f" │ {r['fri_dir']:4} {r['fri_move']:>+5.2f}%"
        f" │ {am:>7} {ar:>5} {ad:>4}"
        f" │ {lm:>6} {lr:>5} {ld:>4}"
        f" │ {nm:>6} {nr:>5} {nd:>4} {ny['o']:>6.0f} {ny['c']:>6.0f}"
        f" │ {r['vie_pred']:>4} {r['cot_pred']:>4}{today}"
    )

    # Acumular stats
    if asia:
        stats["asia"]["moves"].append(asia["move"])
        stats["asia"]["rngs"].append(asia["range"])
        stats["asia"][{"BULL":"bull","BEAR":"bear"}.get(ad,"flat")] += 1
    if lon:
        stats["lon"]["moves"].append(lon["move"])
        stats["lon"]["rngs"].append(lon["range"])
        stats["lon"][{"BULL":"bull","BEAR":"bear"}.get(ld,"flat")] += 1
    stats["ny"]["moves"].append(ny["move"])
    stats["ny"]["rngs"].append(ny["range"])
    stats["ny"][{"BULL":"bull","BEAR":"bear"}.get(nd,"flat")] += 1

    if r["vie_pred"]=="✅": stats["vie_si"]+=1
    elif r["vie_pred"]=="❌": stats["vie_no"]+=1
    if r["cot_pred"]=="✅": stats["cot_si"]+=1
    elif r["cot_pred"]=="❌": stats["cot_no"]+=1

    zk = r["zona_key"]
    if zk not in zona_stats:
        zona_stats[zk] = {"n":0,"asia_bull":0,"lon_bull":0,"ny_bull":0,"ny_bear":0,"ny_flat":0,
                          "vie_si":0,"vie_no":0,"cot_si":0,"cot_no":0}
    z = zona_stats[zk]
    z["n"] += 1
    if ad=="BULL": z["asia_bull"]+=1
    if ld=="BULL": z["lon_bull"]+=1
    if nd=="BULL": z["ny_bull"]+=1
    elif nd=="BEAR": z["ny_bear"]+=1
    else: z["ny_flat"]+=1
    if r["vie_pred"]=="✅": z["vie_si"]+=1
    elif r["vie_pred"]=="❌": z["vie_no"]+=1
    if r["cot_pred"]=="✅": z["cot_si"]+=1
    elif r["cot_pred"]=="❌": z["cot_no"]+=1

# ─── 7. ESTADÍSTICAS ──────────────────────────────────────────
print(f"\n{SEP}")
print(f"  ESTADÍSTICAS GLOBALES — {n} lunes")
print(f"{'='*80}")

def show_session(name, s):
    m = s["moves"]; r = s["rngs"]
    tot = len(m)
    if not tot: return
    bull=s["bull"]; bear=s["bear"]; flat=s["flat"]
    print(f"\n  {name} ({tot} sesiones):")
    print(f"    BULL {bull:3d} ({bull/tot*100:4.0f}%)  BEAR {bear:3d} ({bear/tot*100:4.0f}%)  FLAT {flat:3d} ({flat/tot*100:4.0f}%)")
    print(f"    Move medio:  {sum(m)/tot:+.2f}%   Mediana: {sorted(m)[tot//2]:+.2f}%")
    print(f"    Rango medio: {sum(r)/tot:.2f}%  ≈ {sum(r)/tot*230:.0f} pts NQ")

show_session("🌏 ASIA    (Dom 18:00→Lun 02:59 ET)", stats["asia"])
show_session("🌍 LONDON  (03:00→09:19 ET)",          stats["lon"])
show_session("🗽 NY      (09:30→16:00 ET)",           stats["ny"])

vie_tot = stats["vie_si"]+stats["vie_no"]
cot_tot = stats["cot_si"]+stats["cot_no"]
print(f"\n  📅 VIERNES → NY Lunes:  {stats['vie_si']}/{vie_tot} = {stats['vie_si']/vie_tot*100:.0f}% acierta" if vie_tot else "")
print(f"  📜 COT     → NY Lunes:  {stats['cot_si']}/{cot_tot} = {stats['cot_si']/cot_tot*100:.0f}% acierta" if cot_tot else "")

# ── Por zona VXN ──
print(f"\n  {'─'*78}")
print(f"  {'Por Zona VXN':14} {'n':3}  {'ASIA%B':>7}  {'LON%B':>6}  {'NY%B':>6}  {'NY%E':>6}  {'Vie→NY':>7}  {'COT→NY':>7}")
print(f"  {'─'*78}")
for zk in ["XFEAR","FEAR","NEUT","GREED"]:
    if zk not in zona_stats: continue
    z = zona_stats[zk]; nn = z["n"]
    vt = z["vie_si"]+z["vie_no"]
    ct = z["cot_si"]+z["cot_no"]
    print(
        f"  {zk:14} {nn:3d}"
        f"  {z['asia_bull']/nn*100:5.0f}%B"
        f"  {z['lon_bull']/nn*100:4.0f}%B"
        f"  {z['ny_bull']/nn*100:4.0f}%B"
        f"  {z['ny_bear']/nn*100:4.0f}%E"
        f"  {z['vie_si']/vt*100:5.0f}%" if vt else f"  {'—':>7}"
        +
        f"  {z['cot_si']/ct*100:5.0f}%" if ct else f"  {'—':>7}"
    )

# ── London→NY correlacion global ──
print(f"\n  {'─'*50}")
print(f"  Correlacion LONDON → NY Session:")
lb_nb = sum(1 for r in results if r["lon_dir"]=="BULL" and r["ny_dir"]=="BULL")
lb_ne = sum(1 for r in results if r["lon_dir"]=="BULL" and r["ny_dir"]=="BEAR")
le_nb = sum(1 for r in results if r["lon_dir"]=="BEAR" and r["ny_dir"]=="BULL")
le_ne = sum(1 for r in results if r["lon_dir"]=="BEAR" and r["ny_dir"]=="BEAR")
lbt=lb_nb+lb_ne; let=le_nb+le_ne
print(f"    LON BULL → NY BULL: {lb_nb}/{lbt} = {lb_nb/lbt*100:.0f}%  |  LON BULL → NY BEAR: {lb_ne}/{lbt} = {lb_ne/lbt*100:.0f}%" if lbt else "")
print(f"    LON BEAR → NY BULL: {le_nb}/{let} = {le_nb/let*100:.0f}%  |  LON BEAR → NY BEAR: {le_ne}/{let} = {le_ne/let*100:.0f}%" if let else "")

# ── Asia→NY correlacion global ──
print(f"\n  Correlacion ASIA → NY Session:")
ab_nb = sum(1 for r in results if r["asia_dir"]=="BULL" and r["ny_dir"]=="BULL")
ab_ne = sum(1 for r in results if r["asia_dir"]=="BULL" and r["ny_dir"]=="BEAR")
ae_nb = sum(1 for r in results if r["asia_dir"]=="BEAR" and r["ny_dir"]=="BULL")
ae_ne = sum(1 for r in results if r["asia_dir"]=="BEAR" and r["ny_dir"]=="BEAR")
abt=ab_nb+ab_ne; aet=ae_nb+ae_ne
print(f"    ASIA BULL → NY BULL: {ab_nb}/{abt} = {ab_nb/abt*100:.0f}%  |  ASIA BULL → NY BEAR: {ab_ne}/{abt} = {ab_ne/abt*100:.0f}%" if abt else "")
print(f"    ASIA BEAR → NY BULL: {ae_nb}/{aet} = {ae_nb/aet*100:.0f}%  |  ASIA BEAR → NY BEAR: {ae_ne}/{aet} = {ae_ne/aet*100:.0f}%" if aet else "")
