"""
lista_lunes_completa.py
Lista definitiva de TODOS los lunes disponibles con:
VXN + VIX + COT + Viernes + Asia + London + VP (VAH/POC/VAL) + NY
Para verificacion manual en TradingView
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
print(f"  {len(nq_bars):,} barras | {min(by_date)} → {max(by_date)}")

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
                ll = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
                ls = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                nc_l = int(r.get("NonComm_Positions_Long_All",0) or 0)
                nc_s = int(r.get("NonComm_Positions_Short_All",0) or 0)
                cot_rows.append({"date":d,
                                  "lev_net":ll-ls, "lev_sig":"BULL" if ll>ls else "BEAR",
                                  "nc_net":nc_l-nc_s,"nc_sig":"BULL" if nc_l>nc_s else "BEAR"})
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
    print(f"  COT: {len(cot_rows)} semanas | {cot_rows[0]['date']} → {cot_rows[-1]['date']}")
except: print("  COT no disponible")

def get_cot(mon_date):
    prev = [r for r in cot_rows if r["date"] <= mon_date]
    return prev[-1] if prev else None

# ─── 4. Value Profile ─────────────────────────────────────────
def calc_vp(bars):
    if len(bars) < 3: return None, None, None
    lo_a = min(b["l"] for b in bars); hi_a = max(b["h"] for b in bars)
    if hi_a <= lo_a: return None, None, None
    n = max(1, int(math.ceil((hi_a-lo_a)/VP_BIN)))
    bins = [0.0]*n
    for b in bars:
        vol = b["vol"] if b["vol"]>0 else 1.0
        rng = b["h"]-b["l"] if b["h"]>b["l"] else VP_BIN
        for i in range(n):
            bl=lo_a+i*VP_BIN; bh=bl+VP_BIN
            ov=max(0,min(b["h"],bh)-max(b["l"],bl))
            bins[i]+=vol*(ov/rng)
    total=sum(bins)
    if total==0: return None, None, None
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

# ─── 5. Helpers ────────────────────────────────────────────────
def vxn_zona(v):
    if v>=33: return "XFEAR","🔴🔴"
    if v>=25: return "FEAR", "🔴  "
    if v>=18: return "NEUT", "🟡  "
    return             "GREED","🟢  "

def dir_label(pct, thr=0.10):
    if pct >  thr: return "BULL"
    if pct < -thr: return "BEAR"
    return "FLAT"

def s_bars(bars, h0, m0, h1, m1):
    return [b for b in bars if
            (b["et"].hour>h0 or (b["et"].hour==h0 and b["et"].minute>=m0)) and
            (b["et"].hour<h1 or (b["et"].hour==h1 and b["et"].minute<=m1))]

def s_stats(sb):
    if not sb: return None
    o=sb[0]["o"]; c=sb[-1]["c"]
    h=max(x["h"] for x in sb); l=min(x["l"] for x in sb)
    return {"o":o,"c":c,"h":h,"l":l,
            "move":round((c-o)/o*100,2),"range":round((h-l)/o*100,2)}

def va_pos(price, vah, val):
    if vah is None: return " ? "
    if price>vah: return "ABOVE"
    if price<val: return "BELOW"
    return "IN   "

def setup_label(va_p, zona_k, vxn_v):
    """Clasifica el setup y su calidad"""
    if va_p=="ABOVE":
        if zona_k=="XFEAR": return "SELL★★", "67%"
        if zona_k=="FEAR":  return "SELL★★", "67%"
        if zona_k=="NEUT":  return "SELL★ ", "53%"
        return "SELL  ", "40%"
    elif va_p=="BELOW":
        if zona_k=="XFEAR": return "BUY★★ ", "67%"
        if zona_k=="FEAR":  return "BUY★  ", "38%"
        if zona_k=="NEUT":  return "BUY   ", "50%"
        return "BUY   ", "25%"
    return "INSIDE", " — "

# ─── 6. Calcular TODOS los lunes ──────────────────────────────
mondays_all = sorted([d for d in by_date.keys() if d.weekday()==0], reverse=True)
print(f"\nTotal lunes disponibles: {len(mondays_all)}")

rows = []
for mon in mondays_all:
    bars = by_date[mon]
    if len(bars) < 8: continue

    # ── Sesiones ──
    sun = mon - timedelta(days=1)
    asia_b = [b for b in by_date.get(sun,[]) if b["et"].hour>=18]
    asia_b += [b for b in bars if b["et"].hour<3]
    asia_b.sort(key=lambda x: x["et"])
    asia = s_stats(asia_b)

    lon_b  = s_bars(bars, 3, 0, 9, 19)
    lon    = s_stats(lon_b)

    ny_b   = s_bars(bars, 9, 30, 15, 59)
    ny     = s_stats(ny_b)
    if not ny: continue

    # ── VP: Asia + London + hasta 09:20 ──
    vp_b = asia_b + lon_b
    vah, poc, val = calc_vp(vp_b)

    # ── VXN + VIX del viernes previo ──
    mon_ts  = pd.Timestamp(mon)
    prev_qs = [d for d in qdates if d < mon_ts]
    if not prev_qs: continue
    prev_qd  = prev_qs[-1]
    vxn_val  = float(dfq.loc[prev_qd,"VXN"])
    vix_val  = float(dfq.loc[prev_qd,"VIX"])
    zona_key, zona_ico = vxn_zona(vxn_val)

    # ── Viernes anterior ──
    fri_qs = [d for d in qdates if d.weekday()==4 and d < mon_ts]
    if not fri_qs: continue
    fri_qd   = fri_qs[-1]
    fri_o    = float(dfq.loc[fri_qd,"O"]); fri_c = float(dfq.loc[fri_qd,"C"])
    fri_h    = float(dfq.loc[fri_qd,"H"]); fri_l = float(dfq.loc[fri_qd,"L"])
    fri_move = (fri_c-fri_o)/fri_o*100
    fri_rng  = (fri_h-fri_l)/fri_o*100
    fri_dir  = dir_label(fri_move)

    # ── COT ──
    cot      = get_cot(mon)
    lev_net  = cot["lev_net"] if cot else 0
    nc_net   = cot["nc_net"]  if cot else 0
    lev_sig  = cot["lev_sig"] if cot else "?"
    nc_sig   = cot["nc_sig"]  if cot else "?"
    cot_date = cot["date"]    if cot else None
    cot_age  = (mon - cot_date).days if cot_date else 999

    # ── Análisis ──
    asia_dir = dir_label(asia["move"]) if asia else "?"
    lon_dir  = dir_label(lon["move"])  if lon  else "?"
    ny_dir   = dir_label(ny["move"])

    va_p     = va_pos(ny["o"], vah, val)
    poc_dist = round(ny["o"]-poc, 0) if poc else None
    setup, setup_win_pct = setup_label(va_p.strip(), zona_key, vxn_val)

    # ¿Sweepea VAH o VAL?
    sw_vah = "✅" if vah and ny["h"]>=vah else "  "
    sw_val = "✅" if val and ny["l"]<=val else "  "

    # Predicciones
    vp_expected = "BEAR" if va_p.strip()=="ABOVE" else ("BULL" if va_p.strip()=="BELOW" else "?")
    vp_result   = "✅" if vp_expected==ny_dir else ("❌" if vp_expected in ("BULL","BEAR") and ny_dir in ("BULL","BEAR") else "—")

    vie_result = "—"
    if fri_dir in ("BULL","BEAR") and ny_dir in ("BULL","BEAR"):
        vie_result = "✅" if fri_dir==ny_dir else "❌"

    cot_result = "—"
    if lev_sig in ("BULL","BEAR") and ny_dir in ("BULL","BEAR"):
        cot_result = "✅" if lev_sig==ny_dir else "❌"

    rows.append({
        "mon":mon, "vxn":round(vxn_val,1), "vix":round(vix_val,1),
        "zona_key":zona_key, "zona_ico":zona_ico,
        "lev_net":lev_net, "lev_sig":lev_sig,
        "nc_net":nc_net,   "nc_sig":nc_sig,
        "cot_age":cot_age,
        "fri_dir":fri_dir, "fri_move":round(fri_move,2), "fri_rng":round(fri_rng,2),
        "asia":asia, "asia_dir":asia_dir,
        "lon":lon,   "lon_dir":lon_dir,
        "vah":vah, "poc":poc, "val":val,
        "va_pos":va_p, "poc_dist":poc_dist,
        "setup":setup, "setup_win_pct":setup_win_pct,
        "ny":ny, "ny_dir":ny_dir,
        "sw_vah":sw_vah, "sw_val":sw_val,
        "vp_result":vp_result, "vie_result":vie_result, "cot_result":cot_result,
    })

n = len(rows)
print(f"Lunes calculados: {n}")

# ─── 7. IMPRIMIR ──────────────────────────────────────────────
SEP = "═"*170

# Encabezado explicativo
print(f"\n{SEP}")
print(f"  LISTA DEFINITIVA — {n} LUNES | TODOS LOS INDICADORES")
print(f"  Para verificar en TradingView uno por uno")
print(f"{SEP}")
print(f"  COLUMNAS:")
print(f"  [1]Fecha  [2]VXN [3]VIX [4]Zona  [5]COT-Lev [6]LevNet  [7]NC  [8]NCNet")
print(f"  [9]VieDir [10]VieM%  [11]AsiaDir [12]AsiaM%  [13]LonDir [14]LonM%")
print(f"  [15]VAH [16]POC [17]VAL  [18]NYopen [19]VaPos [20]PocDist")
print(f"  [21]Setup [22]WinPct  [23]NYmove% [24]NYdir  [25]SwVAH [26]SwVAL")
print(f"  [27]VP✓ [28]Vie✓ [29]COT✓")
print(f"{'─'*170}")

for i, r in enumerate(rows, 1):
    today = " ◄HOY" if r["mon"]==date(2026,3,30) else ""
    asia  = r["asia"]
    lon   = r["lon"]
    ny    = r["ny"]

    am = f"{asia['move']:+.2f}%" if asia else "  —  "
    lm = f"{lon['move']:+.2f}%"  if lon  else "  —  "
    vah_s= f"{r['vah']:.0f}" if r["vah"] else "   —"
    poc_s= f"{r['poc']:.0f}" if r["poc"] else "   —"
    val_s= f"{r['val']:.0f}" if r["val"] else "   —"
    pd_s = f"{r['poc_dist']:+.0f}" if r["poc_dist"] is not None else "  —"

    print(
        f"  #{i:3d} {r['mon'].strftime('%d %b %Y'):11}"
        f"  VXN={r['vxn']:5.1f} VIX={r['vix']:5.1f} {r['zona_ico']}{r['zona_key']:5}"
        f"  COT:{r['lev_sig']:4}({r['lev_net']:>+8,}) NC:{r['nc_sig']:4}({r['nc_net']:>+7,}) [{r['cot_age']}d]"
        f"  │ Vie:{r['fri_dir']:4}{r['fri_move']:>+5.2f}%"
        f"  │ Asia:{r['asia_dir']:4}{am:>7}"
        f"  Lon:{r['lon_dir']:4}{lm:>7}"
        f"  │ VP:{vah_s:>6}/{poc_s:>6}/{val_s:>6}"
        f"  NYo:{ny['o']:>6.0f} {r['va_pos']:>6} dist{pd_s:>5}"
        f"  │ [{r['setup']:8}{r['setup_win_pct']:>4}]"
        f"  NY:{ny['move']:>+5.2f}% {r['ny_dir']:4} SwH:{r['sw_vah']} SwL:{r['sw_val']}"
        f"  │VP:{r['vp_result']:>2} Vie:{r['vie_result']:>2} COT:{r['cot_result']:>2}"
        f"{today}"
    )

# ─── 8. ESTADÍSTICAS AGRUPADAS ────────────────────────────────
print(f"\n{SEP}")
print(f"  RESUMEN ESTADÍSTICO")
print(f"{'='*90}")

# Contadores
n_bull = sum(1 for r in rows if r["ny_dir"]=="BULL")
n_bear = sum(1 for r in rows if r["ny_dir"]=="BEAR")
n_flat = sum(1 for r in rows if r["ny_dir"]=="FLAT")

print(f"\n  NY Session Lunes: BULL={n_bull} ({n_bull/n*100:.0f}%)  BEAR={n_bear} ({n_bear/n*100:.0f}%)  FLAT={n_flat} ({n_flat/n*100:.0f}%)")

# VP accuracy
vp_si = sum(1 for r in rows if r["vp_result"]=="✅")
vp_no = sum(1 for r in rows if r["vp_result"]=="❌")
vie_si= sum(1 for r in rows if r["vie_result"]=="✅")
vie_no= sum(1 for r in rows if r["vie_result"]=="❌")
cot_si= sum(1 for r in rows if r["cot_result"]=="✅")
cot_no= sum(1 for r in rows if r["cot_result"]=="❌")

print(f"\n  Indicadores predictivos (solo NY session):")
print(f"    VP (ABOVE→BEAR / BELOW→BULL):  {vp_si}/{vp_si+vp_no} = {vp_si/(vp_si+vp_no)*100:.0f}%")
print(f"    Viernes predice NY:             {vie_si}/{vie_si+vie_no} = {vie_si/(vie_si+vie_no)*100:.0f}%")
print(f"    COT (Lev Money) predice NY:     {cot_si}/{cot_si+cot_no} = {cot_si/(cot_si+cot_no)*100:.0f}%")

# Sweeps
sw_vah = sum(1 for r in rows if r["sw_vah"]=="✅")
sw_val = sum(1 for r in rows if r["sw_val"]=="✅")
print(f"\n  Sweeps en NY:")
print(f"    Barre VAH (sube hasta VAH+): {sw_vah}/{n} = {sw_vah/n*100:.0f}%")
print(f"    Barre VAL (baja hasta VAL-): {sw_val}/{n} = {sw_val/n*100:.0f}%")

# Por zona VXN y VA position
print(f"\n  Setup calidad por zona + VA Position:")
print(f"  {'Setup':20} {'n':4} {'BULL':>5} {'BEAR':>5} {'FLAT':>5} {'VP%acc':>7}")
for zona_k in ["XFEAR","FEAR","NEUT","GREED"]:
    for va_p in ["ABOVE","BELOW","IN"]:
        sub = [r for r in rows if r["zona_key"]==zona_k and r["va_pos"].strip()==va_p]
        if not sub: continue
        sb = sum(1 for r in sub if r["ny_dir"]=="BULL")
        se = sum(1 for r in sub if r["ny_dir"]=="BEAR")
        sf = sum(1 for r in sub if r["ny_dir"]=="FLAT")
        vp_acc = sum(1 for r in sub if r["vp_result"]=="✅")
        vp_tot = sum(1 for r in sub if r["vp_result"] in ("✅","❌"))
        acc_s  = f"{vp_acc/vp_tot*100:.0f}%" if vp_tot else "—"
        label  = f"{zona_k} + {va_p}"
        print(f"    {label:20} {len(sub):4}  {sb:>4}  {se:>4}  {sf:>4}  {acc_s:>7}")

# Regla compuesta: VP + COT + VIE
print(f"\n  Regla triple (VP + COT + Viernes alineados):")
triple_sell = [r for r in rows if
               r["va_pos"].strip()=="ABOVE" and
               r["lev_sig"]=="BEAR" and
               r["fri_dir"]=="BEAR"]
triple_buy  = [r for r in rows if
               r["va_pos"].strip()=="BELOW" and
               r["lev_sig"]=="BULL" and
               r["fri_dir"]=="BULL"]

if triple_sell:
    ts_win = sum(1 for r in triple_sell if r["ny_dir"]=="BEAR")
    print(f"    SELL triple (ABOVE + COT BEAR + Vie BEAR): {ts_win}/{len(triple_sell)} = {ts_win/len(triple_sell)*100:.0f}%")
else:
    print(f"    SELL triple: 0 casos")

if triple_buy:
    tb_win = sum(1 for r in triple_buy if r["ny_dir"]=="BULL")
    print(f"    BUY triple  (BELOW + COT BULL + Vie BULL):  {tb_win}/{len(triple_buy)}  = {tb_win/len(triple_buy)*100:.0f}%")
else:
    print(f"    BUY triple: 0 casos")

print(f"\n{SEP}")
print(f"  Total lunes en lista: {n} | Rango: {rows[-1]['mon']} → {rows[0]['mon']}")
print(f"  CADA FILA = 1 LUNES. Verificar en TradingView buscando la fecha.")
print(f"  Columnas VP: VAH/POC/VAL son niveles NQ 15min pre-NY del lunes.")
