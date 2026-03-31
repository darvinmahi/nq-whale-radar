"""
lunes_vp_sessions.py  v3
TODOS los lunes - Value Profile Asia+London (18:00→09:20 ET)
Analiza donde abre NY respecto al VA y como reacciona
"""
import csv, math, yfinance as yf, pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict

VP_BIN  = 5.0   # bins NQ en puntos
VA_PCT  = 0.70  # value area 70%

# ─── 1. NQ 15min ──────────────────────────────────────────────
print("Cargando NQ 15min...")
nq_bars = []
try:
    with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                dt_utc = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
                dt_et  = dt_utc - timedelta(hours=5)
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
    all_dates = sorted(by_date.keys())
    print(f"  {len(nq_bars):,} barras | {all_dates[0]} → {all_dates[-1]}")
except Exception as e:
    print(f"  ERROR: {e}"); exit(1)

# ─── 2. Indicadores diarios ────────────────────────────────────
print("Descargando QQQ + VXN + VIX...")
qqq = yf.download("QQQ",  period="5y", auto_adjust=True, progress=False)
vxn = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
vix = yf.download("^VIX", period="5y", auto_adjust=True, progress=False)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

dfq = pd.DataFrame({
    "O":col(qqq,"Open"),"H":col(qqq,"High"),
    "L":col(qqq,"Low"), "C":col(qqq,"Close"),
    "VXN":col(vxn,"Close"),"VIX":col(vix,"Close"),
}).dropna()
dfq.index = pd.to_datetime(dfq.index).tz_localize(None)
qdates = dfq.index.tolist()

# ─── 3. COT ────────────────────────────────────────────────────
print("Cargando COT...")
cot_rows = []
try:
    with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d  = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
                ll = int(r.get("Lev_Money_Positions_Long_All",0)  or 0)
                ls = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                cot_rows.append({"date":d,"lev_net":ll-ls,
                                  "sig":"BULL" if ll>ls else "BEAR"})
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
    print(f"  COT: {len(cot_rows)} semanas")
except Exception as e:
    print(f"  COT no disponible: {e}")

def get_cot(mon_date):
    prev = [r for r in cot_rows if r["date"] <= mon_date]
    return prev[-1] if prev else {"lev_net":0,"sig":"?","date":None}

# ─── 4. Value Profile ─────────────────────────────────────────
def calc_vp(bars):
    """Calcula VAH/POC/VAL usando volume profile de las barras"""
    if len(bars) < 3: return None, None, None
    lo_all = min(b["l"] for b in bars)
    hi_all = max(b["h"] for b in bars)
    if hi_all <= lo_all: return None, None, None

    n = max(1, int(math.ceil((hi_all - lo_all) / VP_BIN)))
    bins = [0.0] * n

    for b in bars:
        vol = b["vol"] if b["vol"] > 0 else 1.0
        rng = b["h"] - b["l"] if b["h"] > b["l"] else VP_BIN
        for i in range(n):
            bl = lo_all + i * VP_BIN
            bh = bl + VP_BIN
            ov = max(0, min(b["h"], bh) - max(b["l"], bl))
            bins[i] += vol * (ov / rng)

    total = sum(bins)
    if total == 0: return None, None, None

    # POC = bin con mas volumen
    pi  = bins.index(max(bins))
    poc = lo_all + pi * VP_BIN + VP_BIN / 2

    # Value Area 70%
    va  = total * VA_PCT
    acc = bins[pi]
    li = hi = pi
    while acc < va:
        el = li - 1 if li > 0     else None
        eh = hi + 1 if hi < n - 1 else None
        vl = bins[el] if el is not None else -1
        vh = bins[eh] if eh is not None else -1
        if vl <= 0 and vh <= 0: break
        if vh >= vl: hi = eh; acc += vh
        else:        li = el; acc += vl

    vah = round(lo_all + hi * VP_BIN + VP_BIN, 1)
    val = round(lo_all + li * VP_BIN, 1)
    poc = round(poc, 1)
    return vah, poc, val

# ─── 5. Helpers ────────────────────────────────────────────────
def vxn_zona(v):
    if v >= 33: return "XFEAR","🔴🔴"
    if v >= 25: return "FEAR", "🔴 "
    if v >= 18: return "NEUT", "🟡 "
    return             "GREED","🟢 "

def dir_label(pct, thr=0.10):
    if pct >  thr: return "BULL"
    if pct < -thr: return "BEAR"
    return "FLAT"

def session_bars(bars, h0, m0, h1, m1):
    return [b for b in bars if
            (b["et"].hour > h0 or (b["et"].hour==h0 and b["et"].minute>=m0)) and
            (b["et"].hour < h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]

def session_stats(sb):
    if not sb: return None
    o=sb[0]["o"]; c=sb[-1]["c"]
    h=max(x["h"] for x in sb); l=min(x["l"] for x in sb)
    return {"o":round(o,0),"c":round(c,0),"h":round(h,0),"l":round(l,0),
            "move":round((c-o)/o*100,2),"range":round((h-l)/o*100,2),"n":len(sb)}

def va_position(price, vah, val):
    """Donde esta el precio respecto al Value Area"""
    if vah is None: return "?"
    if price > vah:  return "ABOVE"    # Premium - señal de venta
    if price < val:  return "BELOW"    # Discount - señal de compra
    return "INSIDE"                     # Dentro del VA - esperar

# ─── 6. Calcular TODOS los lunes ──────────────────────────────
mondays_all = sorted([d for d in by_date.keys() if d.weekday()==0], reverse=True)
print(f"\nTotal lunes: {len(mondays_all)}")

results = []
for mon in mondays_all:
    bars = by_date[mon]
    if len(bars) < 8: continue

    # ── Value Profile: Asia + London hasta 09:20 ET ──────────
    # Asia: Dom 18:00 → Lun 02:59 ET
    sun = mon - timedelta(days=1)
    asia_bars_raw = [b for b in by_date.get(sun,[]) if b["et"].hour >= 18]
    asia_bars_raw += [b for b in bars if b["et"].hour < 3]
    asia_bars_raw.sort(key=lambda x: x["et"])

    # London: 03:00 → 09:19 ET
    lon_bars_raw = session_bars(bars, 3, 0, 9, 19)

    # VP session completa: Asia + London (18:00 Dom → 09:20 Lun)
    vp_bars = asia_bars_raw + lon_bars_raw
    vah, poc, val = calc_vp(vp_bars)

    # Stats de sesiones individuales
    asia_s = session_stats(asia_bars_raw)
    lon_s  = session_stats(lon_bars_raw)
    ny_s   = session_stats(session_bars(bars, 9, 30, 15, 59))
    if not ny_s: continue

    # ── VXN + VIX del viernes previo ──
    mon_ts  = pd.Timestamp(mon)
    prev_qs = [d for d in qdates if d < mon_ts]
    if not prev_qs: continue
    prev_qd = prev_qs[-1]
    vxn_val = float(dfq.loc[prev_qd,"VXN"])
    vix_val = float(dfq.loc[prev_qd,"VIX"])
    zona_key, zona_ico = vxn_zona(vxn_val)

    # ── Viernes (QQQ daily) ──
    fri_qs = [d for d in qdates if d.weekday()==4 and d < mon_ts]
    if not fri_qs: continue
    fri_qd   = fri_qs[-1]
    fri_o    = float(dfq.loc[fri_qd,"O"]); fri_c = float(dfq.loc[fri_qd,"C"])
    fri_move = (fri_c - fri_o) / fri_o * 100
    fri_dir  = dir_label(fri_move)

    # ── COT ──
    cot      = get_cot(mon)
    lev_net  = cot["lev_net"]
    cot_sig  = cot["sig"]

    # ── NY Open vs Value Area ──
    ny_open     = ny_s["o"]
    ny_close    = ny_s["c"]
    ny_move     = ny_s["move"]
    ny_dir      = dir_label(ny_move)
    va_pos_open = va_position(ny_open, vah, val)   # donde abre NY
    va_pos_close= va_position(ny_close, vah, val)  # donde cierra NY

    # ── Predicciones ──
    # ¿VA position correctamente predice NY direction?
    # Lógica ICT: ABOVE VA → NY debería BEAR (sell premium)
    #             BELOW VA → NY debería BULL (buy discount)
    #             INSIDE   → sin sesgo claro
    vp_pred_dir = "BEAR" if va_pos_open=="ABOVE" else ("BULL" if va_pos_open=="BELOW" else "?")
    vp_pred     = "—"
    if vp_pred_dir in ("BULL","BEAR") and ny_dir in ("BULL","BEAR"):
        vp_pred = "✅" if vp_pred_dir==ny_dir else "❌"

    vie_pred = "—"
    if fri_dir in ("BULL","BEAR") and ny_dir in ("BULL","BEAR"):
        vie_pred = "✅" if fri_dir==ny_dir else "❌"

    # ── Distancia NY open al POC (en pts NQ) ──
    poc_dist = round(ny_open - poc, 0) if poc else None

    # ── Sweep del VP: did NY sweep VAH or VAL? ──
    swept_vah = ny_s["h"] >= vah if vah else False
    swept_val = ny_s["l"] <= val if val else False

    results.append({
        "mon":mon,
        "vxn":round(vxn_val,1),"vix":round(vix_val,1),
        "zona_key":zona_key,"zona_ico":zona_ico,
        "fri_dir":fri_dir,"fri_move":round(fri_move,2),
        "lev_net":lev_net,"cot_sig":cot_sig,
        "asia":asia_s,"lon":lon_s,"ny":ny_s,
        "asia_dir":dir_label(asia_s["move"]) if asia_s else "?",
        "lon_dir": dir_label(lon_s["move"])  if lon_s  else "?",
        "ny_dir":ny_dir,
        "vah":vah,"poc":poc,"val":val,
        "va_pos_open":va_pos_open,"va_pos_close":va_pos_close,
        "poc_dist":poc_dist,
        "swept_vah":swept_vah,"swept_val":swept_val,
        "vp_pred":vp_pred,"vie_pred":vie_pred,
        "ny_open":ny_open,"ny_close":ny_close,
    })

n = len(results)
print(f"Lunes calculados: {n}")

# ─── 7. OUTPUT ────────────────────────────────────────────────
SEP = "═" * 155
sep = "─" * 155

print(f"\n{SEP}")
print(f"  TODOS LOS LUNES — VALUE PROFILE (Asia+Lon→09:20) + SESIONES + VXN+VIX+COT")
print(f"{SEP}")
print(
    f"  {'Lunes':11} {'VXN':5} {'VIX':5} {'Zona':9} {'COT':4} {'LevNet':>9}"
    f" │ {'VIE':4} {'VieM':>6}"
    f" │ {'VAH':>7} {'POC':>7} {'VAL':>7} {'NOpen':>6} {'VaPos':>6} {'PocDst':>7}"
    f" │ {'NY M%':>6} {'ND':>4} {'VcPos':>6} │ 🔮{'VP→NY':>5} {'V→NY':>5}"
    f" │ {'SwVAH':>5} {'SwVAL':>5}"
)
print(sep)

# Acumuladores
vp_stats = {"ABOVE":{"bull":0,"bear":0,"flat":0},
            "BELOW":{"bull":0,"bear":0,"flat":0},
            "INSIDE":{"bull":0,"bear":0,"flat":0}}
vp_pred_si=0; vp_pred_no=0
vie_si=0; vie_no=0
swept_vah_count=0; swept_val_count=0
zona_vp = {}

for r in results:
    today = " ◄HOY" if r["mon"]==date(2026,3,30) else ""
    vah_s = f"{r['vah']:.0f}" if r["vah"] else "  — "
    poc_s = f"{r['poc']:.0f}" if r["poc"] else "  — "
    val_s = f"{r['val']:.0f}" if r["val"] else "  — "
    pd_s  = f"{r['poc_dist']:+.0f}" if r["poc_dist"] is not None else "  — "

    # Color VA position
    vap = r["va_pos_open"]
    vap_ico = "⬆️ABV" if vap=="ABOVE" else ("⬇️BLW" if vap=="BELOW" else "↔️IN ")
    vcp_ico = "⬆️ABV" if r["va_pos_close"]=="ABOVE" else ("⬇️BLW" if r["va_pos_close"]=="BELOW" else "↔️IN ")

    sv_h = "✅" if r["swept_vah"] else "  "
    sv_l = "✅" if r["swept_val"] else "  "

    print(
        f"  {r['mon'].strftime('%d %b %Y'):11}"
        f" {r['vxn']:5.1f} {r['vix']:5.1f} {r['zona_ico']}{r['zona_key']:5}"
        f" {r['cot_sig']:4} {r['lev_net']:>9,}"
        f" │ {r['fri_dir']:4} {r['fri_move']:>+5.2f}%"
        f" │ {vah_s:>7} {poc_s:>7} {val_s:>7} {r['ny_open']:>6.0f} {vap_ico:>6} {pd_s:>7}"
        f" │ {r['ny']['move']:>+5.2f}% {r['ny_dir']:>4} {vcp_ico:>6}"
        f" │ {r['vp_pred']:>5} {r['vie_pred']:>5}"
        f" │ {sv_h:>5} {sv_l:>5}{today}"
    )

    # Acumular stats VP
    vd = r["ny_dir"]
    key = vap if vap in vp_stats else "INSIDE"
    if vd=="BULL": vp_stats[key]["bull"]+=1
    elif vd=="BEAR": vp_stats[key]["bear"]+=1
    else: vp_stats[key]["flat"]+=1

    if r["vp_pred"]=="✅": vp_pred_si+=1
    elif r["vp_pred"]=="❌": vp_pred_no+=1
    if r["vie_pred"]=="✅": vie_si+=1
    elif r["vie_pred"]=="❌": vie_no+=1
    if r["swept_vah"]: swept_vah_count+=1
    if r["swept_val"]: swept_val_count+=1

    # Por zona
    zk = r["zona_key"]
    if zk not in zona_vp:
        zona_vp[zk] = {"n":0,
                        "above":{"bull":0,"bear":0,"flat":0},
                        "below":{"bull":0,"bear":0,"flat":0},
                        "inside":{"bull":0,"bear":0,"flat":0},
                        "vp_si":0,"vp_no":0}
    z = zona_vp[zk]; z["n"]+=1
    zkey = vap.lower() if vap.lower() in ("above","below","inside") else "inside"
    if vd=="BULL": z[zkey]["bull"]+=1
    elif vd=="BEAR": z[zkey]["bear"]+=1
    else: z[zkey]["flat"]+=1
    if r["vp_pred"]=="✅": z["vp_si"]+=1
    elif r["vp_pred"]=="❌": z["vp_no"]+=1

# ─── 8. ESTADÍSTICAS VP ───────────────────────────────────────
print(f"\n{SEP}")
print(f"  ANÁLISIS VALUE PROFILE — {n} lunes")
print(f"{'='*90}")

print(f"\n  ¿Donde abre NY respecto al VA (Asia+London)? → ¿Qué hace NY?")
print(f"  {'VA Position':10} {'n':4}  {'NY BULL':>8}  {'NY BEAR':>8}  {'NY FLAT':>8}  {'BEAR%':>6}")
print(f"  {'─'*55}")
for pos, ico in [("ABOVE","⬆️  Premium"),("BELOW","⬇️  Discount"),("INSIDE","↔️  Dentro")]:
    s = vp_stats[pos]
    tot = s["bull"]+s["bear"]+s["flat"]
    if tot == 0: continue
    bear_pct = s["bear"]/tot*100
    bull_pct = s["bull"]/tot*100
    print(f"  {ico:12} {tot:4d}  {s['bull']:>5} ({bull_pct:4.0f}%)  {s['bear']:>5} ({bear_pct:4.0f}%)  {s['flat']:>5} ({s['flat']/tot*100:4.0f}%)  {bear_pct:5.0f}%")

vp_tot = vp_pred_si+vp_pred_no
vie_tot = vie_si+vie_no
print(f"\n  🔮 VP predice NY (ABOVE→BEAR, BELOW→BULL): {vp_pred_si}/{vp_tot} = {vp_pred_si/vp_tot*100:.0f}%" if vp_tot else "")
print(f"  📅 Viernes predice NY:                      {vie_si}/{vie_tot} = {vie_si/vie_tot*100:.0f}%" if vie_tot else "")

print(f"\n  Sweeps del Value Area en NY:")
print(f"    NY barre VAH (sube a VAH o más): {swept_vah_count}/{n} = {swept_vah_count/n*100:.0f}%")
print(f"    NY barre VAL (baja a VAL o más): {swept_val_count}/{n} = {swept_val_count/n*100:.0f}%")

# ── Por zona VXN ──
print(f"\n  {'─'*100}")
print(f"  VP por Zona VXN:")
print(f"  {'Zona':8} {'n':3}  NY abre ABOVE:{'BULL%':>5}/{'BEAR%':>5}  NY abre BELOW:{'BULL%':>5}/{'BEAR%':>5}  NY abre INSIDE:{'BULL%':>5}/{'BEAR%':>5}  VP acierta")
print(f"  {'─'*100}")
for zk in ["XFEAR","FEAR","NEUT","GREED"]:
    if zk not in zona_vp: continue
    z = zona_vp[zk]
    def pct_str(d):
        t=d["bull"]+d["bear"]+d["flat"]
        if t==0: return "  — /  — "
        return f"{d['bull']/t*100:3.0f}%/{d['bear']/t*100:3.0f}%"
    vt=z["vp_si"]+z["vp_no"]
    vp_acc = f"{z['vp_si']/vt*100:.0f}%" if vt else "—"
    print(f"  {zk:8} {z['n']:3d}  ABOVE: {pct_str(z['above'])}  BELOW: {pct_str(z['below'])}  INSIDE: {pct_str(z['inside'])}  {vp_acc}")

# ── Análisis adicional: NY open ABOVE VA → tendencia bajista ──
above_data = [r for r in results if r["va_pos_open"]=="ABOVE" and r["ny_dir"]=="BEAR"]
below_data = [r for r in results if r["va_pos_open"]=="BELOW" and r["ny_dir"]=="BULL"]
print(f"\n  {'─'*70}")
print(f"  🎯 Escenario PREMIUM (NY abre ABOVE VA → NY BEAR = venta en tope):")
if above_data:
    avg_move = sum(r["ny"]["move"] for r in above_data)/len(above_data)
    avg_rng  = sum(r["ny"]["range"] for r in above_data)/len(above_data)
    print(f"     Casos: {len(above_data)} | Move medio: {avg_move:+.2f}% | Rango medio: {avg_rng:.2f}% ≈ {avg_rng*230:.0f} pts NQ")
    print(f"     Sweeps VAH cuando abre ABOVE: {sum(1 for r in above_data if r['swept_vah'])} casos")

print(f"\n  🎯 Escenario DISCOUNT (NY abre BELOW VA → NY BULL = compra en suelo):")
if below_data:
    avg_move = sum(r["ny"]["move"] for r in below_data)/len(below_data)
    avg_rng  = sum(r["ny"]["range"] for r in below_data)/len(below_data)
    print(f"     Casos: {len(below_data)} | Move medio: {avg_move:+.2f}% | Rango medio: {avg_rng:.2f}% ≈ {avg_rng*230:.0f} pts NQ")

# ── Regla de trading: VA position + VXN ──
print(f"\n  {'─'*70}")
print(f"  🧠 REGLA COMPUESTA: VA Position + Zona VXN → predicción NY:")
for zk in ["XFEAR","FEAR","NEUT","GREED"]:
    sub_ab = [r for r in results if r["zona_key"]==zk and r["va_pos_open"]=="ABOVE"]
    sub_bl = [r for r in results if r["zona_key"]==zk and r["va_pos_open"]=="BELOW"]
    if not sub_ab and not sub_bl: continue
    print(f"\n  {zk}:")
    if sub_ab:
        bear_ab = sum(1 for r in sub_ab if r["ny_dir"]=="BEAR")
        print(f"    ABOVE VA ({len(sub_ab):2d} casos) → NY BEAR: {bear_ab}/{len(sub_ab)} = {bear_ab/len(sub_ab)*100:.0f}%  ← SELL SETUP")
    if sub_bl:
        bull_bl = sum(1 for r in sub_bl if r["ny_dir"]=="BULL")
        print(f"    BELOW VA ({len(sub_bl):2d} casos) → NY BULL: {bull_bl}/{len(sub_bl)} = {bull_bl/len(sub_bl)*100:.0f}%  ← BUY SETUP")
