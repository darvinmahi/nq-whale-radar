"""
heatmap_backtest.py
Genera heatmap_backtest.html con 3 heatmaps interactivos:
  1. LEV COT% × VXN zona → Winrate NY BEAR (SELL setups ABOVE VA)
  2. AM%   × VXN zona    → Winrate NY BEAR
  3. LEV COT% × AM%      → Winrate NY direccional
Click en celda = ver casos individuales
"""
import csv, math, json
import yfinance as yf, pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict

# ── CONFIG ──────────────────────────────────────────────────────────
VP_BIN  = 5.0
VA_PCT  = 0.70
WINDOW  = 52   # semanas COT index
FLOW_W  = 156  # 3 años Commercial FLOW

# ── CARGAR NQ 15min ─────────────────────────────────────────────────
print("Cargando NQ 15min...")
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            et = datetime.fromisoformat(r["Datetime"].replace("+00:00","")) - timedelta(hours=5)
            cl = float(r["Close"]); hi = float(r["High"]); lo = float(r["Low"]); op = float(r["Open"])
            vol = float(r.get("Volume",0) or 0)
            if cl > 0:
                bars.append({"et":et,"c":cl,"h":hi,"l":lo,"o":op,
                             "vol": vol if vol>0 else (hi-lo)*10})
        except: pass
bars.sort(key=lambda x: x["et"])
by_date = defaultdict(list)
for b in bars: by_date[b["et"].date()].append(b)

# ── CARGAR VXN/VIX ──────────────────────────────────────────────────
print("Descargando volatilidad...")
vxn = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
vix = yf.download("^VIX", period="5y", auto_adjust=True, progress=False)
def col(df,c): return df[c].iloc[:,0] if isinstance(df.columns, pd.MultiIndex) else df[c]
dfv = pd.DataFrame({"VXN": col(vxn,"Close"), "VIX": col(vix,"Close")}).dropna()
dfv.index = pd.to_datetime(dfv.index).tz_localize(None)
vdates = dfv.index.tolist()

# ── CARGAR COT ──────────────────────────────────────────────────────
print("Cargando COT...")
cot = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            ll = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
            ls = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
            al = int(r.get("Asset_Mgr_Positions_Long_All",0) or 0)
            as_ = int(r.get("Asset_Mgr_Positions_Short_All",0) or 0)
            ds = int(r.get("Dealer_Positions_Short_All",0) or 0)
            cot.append({"date":d, "lev_net":ll-ls, "am_net":al-as_, "com_s":ds})
        except: pass
cot.sort(key=lambda x: x["date"])

# COT Index %
lev_nets = [r["lev_net"] for r in cot]
am_nets  = [r["am_net"]  for r in cot]
com_ss   = [r["com_s"]   for r in cot]
for i, r in enumerate(cot):
    # LEV %
    w = lev_nets[max(0,i-WINDOW+1):i+1]; r["lev_idx"] = round((r["lev_net"]-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0
    # AM %
    w = am_nets[max(0,i-WINDOW+1):i+1];  r["am_idx"]  = round((r["am_net"]-min(w))/(max(w)-min(w))*100,1)  if max(w)!=min(w) else 50.0
    # FLOW
    delta = (cot[i]["com_s"] - cot[i-1]["com_s"]) if i>0 else 0
    r["com_delta"] = delta
com_deltas = [r["com_delta"] for r in cot]
for i, r in enumerate(cot):
    w = com_deltas[max(0,i-FLOW_W+1):i+1]; mx,mn = max(w),min(w)
    r["flow"] = round((mx-r["com_delta"])/(mx-mn)*100,1) if mx!=mn else 50.0

def get_cot(d):
    prev = [r for r in cot if r["date"] <= d]
    return prev[-1] if prev else {"lev_idx":50,"am_idx":50,"flow":50}

# ── HELPERS VP ──────────────────────────────────────────────────────
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

# ── CALCULAR TODOS LOS LUNES ─────────────────────────────────────────
mondays = sorted([d for d in by_date if d.weekday()==0], reverse=True)
rows = []
for mon in mondays:
    bs = by_date[mon]
    if len(bs)<8: continue
    sun = mon - timedelta(days=1)
    vp_b = [b for b in by_date.get(sun,[]) if b["et"].hour>=18]
    vp_b += [b for b in bs if b["et"].hour<9 or (b["et"].hour==9 and b["et"].minute<20)]
    vp_b.sort(key=lambda x: x["et"])
    vah,poc,val = calc_vp(vp_b)
    if vah is None: continue
    ny30  = sbars(bs,9,30,10,0)
    ny1h  = sbars(bs,9,30,10,30)
    nyall = sbars(bs,9,30,15,59)
    if not nyall or len(nyall)<2: continue
    ny_o = nyall[0]["o"]
    def ms(sb):
        if not sb: return None
        return {"move": round((sb[-1]["c"]-ny_o)/ny_o*100,2),
                "range": round((max(b["h"] for b in sb)-min(b["l"] for b in sb))/ny_o*100,2)}
    s30=ms(ny30); s1h=ms(ny1h); sall=ms(nyall)
    if not sall: continue
    va_p = "ABOVE" if ny_o>vah else ("BELOW" if ny_o<val else "INSIDE")
    poc_dist = round(ny_o-poc,0)
    mon_ts = pd.Timestamp(mon)
    prev_q = [d for d in vdates if d<mon_ts]
    if not prev_q: continue
    pq = prev_q[-1]; vxn_v=float(dfv.loc[pq,"VXN"]); vix_v=float(dfv.loc[pq,"VIX"])
    vxn_z = "XFEAR" if vxn_v>=33 else ("FEAR" if vxn_v>=25 else ("NEUT" if vxn_v>=18 else "GREED"))
    c = get_cot(mon)
    ny_dir = "BULL" if sall["move"]>0.08 else ("BEAR" if sall["move"]<-0.08 else "FLAT")
    rows.append({
        "date": str(mon), "va_p": va_p, "poc_dist": poc_dist,
        "vxn": round(vxn_v,1), "vxn_z": vxn_z,
        "lev_idx": c["lev_idx"], "am_idx": c["am_idx"], "flow": c["flow"],
        "ny_dir": ny_dir, "ny_move": sall["move"],
        "ny_range": round(sall["range"]*230,0),
        "m30": s30["move"] if s30 else 0,
        "m1h": s1h["move"] if s1h else 0,
    })

print(f"Lunes calculados: {len(rows)}")

# ── BUCKETS ──────────────────────────────────────────────────────────
def lev_bucket(v): 
    if v<20: return "0-20%\n(XBEAR)"
    if v<40: return "20-40%\n(BEAR)"
    if v<60: return "40-60%\n(NEUT)"
    if v<80: return "60-80%\n(BULL)"
    return "80-100%\n(XBULL)"

def am_bucket(v):
    if v<20: return "0-20%\n(XBEAR)"
    if v<40: return "20-40%\n(BEAR)"
    if v<60: return "40-60%\n(NEUT)"
    if v<80: return "60-80%\n(BULL)"
    return "80-100%\n(XBULL)"

def vxn_bucket(z): return z  # ya es string

# ── BUILD HEATMAP DATA ───────────────────────────────────────────────
def build_hm(rows, x_fn, y_fn, target_dir, filter_fn=None):
    """Retorna dict: { (x_label, y_label): {n, wins, cases} }"""
    cells = defaultdict(lambda: {"n":0,"wins":0,"cases":[]})
    for r in rows:
        if filter_fn and not filter_fn(r): continue
        x = x_fn(r); y = y_fn(r)
        cells[(x,y)]["n"] += 1
        if r["ny_dir"] == target_dir:
            cells[(x,y)]["wins"] += 1
        cells[(x,y)]["cases"].append(r)
    return cells

LEV_BUCKETS = ["0-20%\n(XBEAR)","20-40%\n(BEAR)","40-60%\n(NEUT)","60-80%\n(BULL)","80-100%\n(XBULL)"]
AM_BUCKETS  = ["0-20%\n(XBEAR)","20-40%\n(BEAR)","40-60%\n(NEUT)","60-80%\n(BULL)","80-100%\n(XBULL)"]
VXN_BUCKETS = ["GREED","NEUT","FEAR","XFEAR"]

# HM1: LEV × VXN → SELL (ABOVE VA, WIN=BEAR)
hm1 = build_hm(rows, lambda r: lev_bucket(r["lev_idx"]), lambda r: r["vxn_z"],
                "BEAR", lambda r: r["va_p"]=="ABOVE")

# HM2: AM × VXN → SELL (ABOVE VA, WIN=BEAR)
hm2 = build_hm(rows, lambda r: am_bucket(r["am_idx"]), lambda r: r["vxn_z"],
                "BEAR", lambda r: r["va_p"]=="ABOVE")

# HM3: LEV × AM → NY direction (todos los ABOVE VA)
hm3 = build_hm(rows, lambda r: lev_bucket(r["lev_idx"]), lambda r: am_bucket(r["am_idx"]),
                "BEAR", lambda r: r["va_p"]=="ABOVE")

# HM4: LEV × VXN → BUY (BELOW VA, WIN=BULL)
hm4 = build_hm(rows, lambda r: lev_bucket(r["lev_idx"]), lambda r: r["vxn_z"],
                "BULL", lambda r: r["va_p"]=="BELOW")

def cells_to_json(cells, x_labels, y_labels):
    out = []
    for x in x_labels:
        for y in y_labels:
            c = cells.get((x,y), {"n":0,"wins":0,"cases":[]})
            winrate = round(c["wins"]/c["n"]*100) if c["n"]>0 else None
            cases = [{"d":cs["date"],"move":cs["ny_move"],"m30":cs["m30"],
                      "vxn":cs["vxn"],"lev":cs["lev_idx"],"am":cs["am_idx"],
                      "dir":cs["ny_dir"],"poc":cs["poc_dist"]} for cs in c["cases"]]
            out.append({"x":x,"y":y,"n":c["n"],"wins":c["wins"],"wr":winrate,"cases":cases[:20]})
    return out

data_js = {
    "hm1": cells_to_json(hm1, LEV_BUCKETS, VXN_BUCKETS),
    "hm2": cells_to_json(hm2, AM_BUCKETS,  VXN_BUCKETS),
    "hm3": cells_to_json(hm3, LEV_BUCKETS, AM_BUCKETS),
    "hm4": cells_to_json(hm4, LEV_BUCKETS, VXN_BUCKETS),
    "lev_buckets": LEV_BUCKETS,
    "am_buckets":  AM_BUCKETS,
    "vxn_buckets": VXN_BUCKETS,
    "total_mondays": len(rows),
}

# ── GENERAR HTML ─────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔥 Heatmap Backtest · NQ COT Setups</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  :root {{
    --bg:#0b0e1a; --bg2:#111420; --bg3:#181d2e;
    --border:rgba(99,130,255,0.18); --accent:#6382ff; --accent2:#38c9e8;
    --green:#22d98a; --red:#f0485a; --orange:#f5a623; --yellow:#f5d623;
    --text:#e4e8ff; --text2:#8898bb;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Inter',sans-serif; }}
  .header {{
    background:linear-gradient(135deg,#0e1228,#131830);
    border-bottom:1px solid var(--border);
    padding:18px 32px; display:flex; align-items:center; gap:16px;
    position:sticky; top:0; z-index:200; backdrop-filter:blur(12px);
  }}
  .header-logo {{ font-size:1.8rem; }}
  .header-title h1 {{ font-size:1.2rem; font-weight:800; letter-spacing:-0.5px; }}
  .header-title p  {{ font-size:0.75rem; color:var(--text2); margin-top:2px; }}
  .header-badge {{
    margin-left:auto; background:rgba(99,130,255,0.15); color:var(--accent);
    padding:5px 14px; border-radius:20px; font-size:0.78rem; font-weight:700;
    font-family:'JetBrains Mono',monospace;
  }}
  .page {{ max-width:1400px; margin:0 auto; padding:24px 20px; }}

  /* TABS */
  .tabs {{ display:flex; gap:0; border-bottom:1px solid var(--border); margin-bottom:24px; }}
  .tab-btn {{
    padding:12px 24px; font-size:0.82rem; font-weight:600; cursor:pointer;
    border:none; background:transparent; color:var(--text2);
    border-bottom:2px solid transparent; transition:all .2s; font-family:'Inter',sans-serif;
  }}
  .tab-btn.active {{ color:var(--accent2); border-bottom-color:var(--accent2); }}
  .tab-btn:hover {{ color:var(--text); }}
  .tab-pane {{ display:none; }}
  .tab-pane.active {{ display:block; }}

  /* HEATMAP */
  .hm-wrap {{ overflow-x:auto; }}
  .hm-title {{
    font-size:0.72rem; text-transform:uppercase; letter-spacing:1px;
    color:var(--accent); font-weight:700; margin-bottom:16px;
    display:flex; align-items:center; gap:8px;
  }}
  .hm-subtitle {{ font-size:0.78rem; color:var(--text2); margin-bottom:20px; line-height:1.5; }}
  table.hm {{ border-collapse:collapse; }}
  table.hm th {{
    padding:8px 12px; font-size:0.65rem; text-transform:uppercase; letter-spacing:0.8px;
    color:var(--text2); font-weight:600; text-align:center; white-space:pre-line;
    background:var(--bg2);
  }}
  table.hm th.row-header {{ text-align:right; min-width:90px; }}
  table.hm td {{
    padding:3px;
  }}
  .hm-cell {{
    width:110px; height:80px; border-radius:10px; cursor:pointer;
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    border:2px solid transparent; transition:all .15s; position:relative;
    user-select:none;
  }}
  .hm-cell:hover {{ transform:scale(1.05); border-color:white; z-index:10; }}
  .hm-cell.active {{ border-color:var(--accent2) !important; transform:scale(1.05); }}
  .hm-wr {{ font-size:1.4rem; font-weight:800; line-height:1; }}
  .hm-n  {{ font-size:0.62rem; color:rgba(255,255,255,0.6); margin-top:4px; }}
  .hm-empty {{ width:110px; height:80px; border-radius:10px; background:rgba(99,130,255,0.04); border:1px dashed rgba(99,130,255,0.15); display:flex; align-items:center; justify-content:center; color:rgba(136,152,187,0.4); font-size:0.7rem; }}

  /* LEGEND */
  .legend {{ display:flex; gap:12px; align-items:center; margin-bottom:20px; flex-wrap:wrap; }}
  .leg-item {{ display:flex; align-items:center; gap:6px; font-size:0.72rem; color:var(--text2); }}
  .leg-box {{ width:20px; height:14px; border-radius:4px; }}

  /* CASOS PANEL */
  .cases-panel {{
    background:var(--bg2); border:1px solid var(--border); border-radius:14px;
    padding:20px; margin-top:20px; display:none;
  }}
  .cases-panel.show {{ display:block; }}
  .cp-title {{ font-size:0.72rem; text-transform:uppercase; letter-spacing:1px; color:var(--accent2); font-weight:700; margin-bottom:14px; }}
  .cp-stats {{ display:flex; gap:20px; margin-bottom:14px; flex-wrap:wrap; }}
  .cp-stat {{ text-align:center; }}
  .cp-stat .v {{ font-size:1.5rem; font-weight:800; }}
  .cp-stat .l {{ font-size:0.62rem; color:var(--text2); margin-top:2px; text-transform:uppercase; }}
  table.ct {{ width:100%; border-collapse:collapse; font-size:0.74rem; font-family:'JetBrains Mono',monospace; }}
  table.ct th {{ background:var(--bg3); color:var(--text2); padding:7px 10px; text-align:left; font-size:0.62rem; text-transform:uppercase; letter-spacing:0.8px; }}
  table.ct td {{ padding:7px 10px; border-bottom:1px solid rgba(99,130,255,0.06); }}
  table.ct tr:hover td {{ background:rgba(99,130,255,0.04); }}
  .dir-bull {{ color:var(--green); font-weight:700; }}
  .dir-bear {{ color:var(--red); font-weight:700; }}
  .dir-flat {{ color:var(--text2); }}

  /* INFO CARD */
  .info-card {{
    background:linear-gradient(135deg,rgba(99,130,255,0.08),rgba(56,201,232,0.04));
    border:1px solid rgba(99,130,255,0.25); border-radius:14px; padding:18px 20px;
    margin-bottom:24px; font-size:0.82rem; line-height:1.7;
  }}
  .info-card strong {{ color:var(--accent2); }}

  /* Pill */
  .pill {{ display:inline-flex; padding:2px 8px; border-radius:6px; font-size:0.68rem; font-weight:700; }}
  .pill-green  {{ background:rgba(34,217,138,0.15); color:var(--green); }}
  .pill-red    {{ background:rgba(240,72,90,0.15); color:var(--red); }}
  .pill-yellow {{ background:rgba(245,214,35,0.15); color:var(--yellow); }}
  .pill-gray   {{ background:rgba(136,152,187,0.12); color:var(--text2); }}
</style>
</head>
<body>

<div class="header">
  <div class="header-logo">🔥</div>
  <div class="header-title">
    <h1>HEATMAP BACKTEST · NQ NASDAQ SETUPS</h1>
    <p>COT Leveraged · Asset Manager · VXN — Winrate por combinación de condiciones</p>
  </div>
  <div class="header-badge" id="total-badge">— lunes</div>
</div>

<div class="page">

  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('sell')" id="tbtn-sell">📉 SELL Setup (ABOVE VA)</button>
    <button class="tab-btn" onclick="switchTab('buy')" id="tbtn-buy">📈 BUY Setup (BELOW VA)</button>
    <button class="tab-btn" onclick="switchTab('double')" id="tbtn-double">🎯 Doble Filtro (LEV × AM)</button>
  </div>

  <!-- TAB SELL -->
  <div class="tab-pane active" id="tab-sell">
    <div class="info-card">
      <strong>Setup estudiado:</strong> NY abre <strong>ABOVE VA</strong> (precio en zona premium) — buscamos si el mercado baja.
      El heatmap muestra el <strong>% de veces que NY cerró BAJISTA</strong> para cada combinación COT × VXN.
      <br>Celdas <span style="color:var(--red)">rojas=mas bajista</span> · <span style="color:var(--green)">verdes=mas alcista</span> · Click en celda = ver casos.
    </div>
    <div>
      <div class="hm-title">📊 HM1 — LEV MONEY COT% × VXN Zona → % NY BAJISTA (SELL)</div>
      <div class="hm-subtitle">Cada celda = % de lunes donde NY cerró BEAR. Más rojo = mejor setup de venta.</div>
      <div class="legend">
        <div class="leg-item"><div class="leg-box" style="background:#7f1d1d"></div>>80% BEAR</div>
        <div class="leg-item"><div class="leg-box" style="background:#b91c1c"></div>60-80%</div>
        <div class="leg-item"><div class="leg-box" style="background:#4d7c0f"></div>40-60%</div>
        <div class="leg-item"><div class="leg-box" style="background:#166534"></div><60% BEAR</div>
        <div class="leg-item" style="margin-left:12px;"><span class="pill pill-gray">n=X = número de ocurrencias</span></div>
      </div>
      <div class="hm-wrap"><div id="hm1"></div></div>
    </div>
    <div class="cases-panel" id="cp1">
      <div class="cp-title" id="cp1-title">Casos seleccionados</div>
      <div class="cp-stats" id="cp1-stats"></div>
      <table class="ct"><thead><tr>
        <th>Fecha</th><th>LEV%</th><th>AM%</th><th>VXN</th><th>Dist POC</th><th>30min</th><th>NY Move</th><th>Resultado</th>
      </tr></thead><tbody id="cp1-body"></tbody></table>
    </div>

    <div style="margin-top:36px;">
      <div class="hm-title">📊 HM2 — ASSET MANAGER% × VXN Zona → % NY BAJISTA (SELL)</div>
      <div class="hm-subtitle">Asset Managers mueven más volumen. Esta celda muestra si su posicionamiento predice el movimiento.</div>
      <div class="hm-wrap"><div id="hm2"></div></div>
    </div>
    <div class="cases-panel" id="cp2">
      <div class="cp-title" id="cp2-title">Casos seleccionados</div>
      <div class="cp-stats" id="cp2-stats"></div>
      <table class="ct"><thead><tr>
        <th>Fecha</th><th>LEV%</th><th>AM%</th><th>VXN</th><th>Dist POC</th><th>30min</th><th>NY Move</th><th>Resultado</th>
      </tr></thead><tbody id="cp2-body"></tbody></table>
    </div>
  </div>

  <!-- TAB BUY -->
  <div class="tab-pane" id="tab-buy">
    <div class="info-card">
      <strong>Setup estudiado:</strong> NY abre <strong>BELOW VA</strong> (precio en zona descuento) — buscamos si el mercado sube.
    </div>
    <div class="hm-title">📊 HM4 — LEV MONEY COT% × VXN Zona → % NY ALCISTA (BUY)</div>
    <div class="hm-subtitle">% de lunes donde NY cerró BULL cuando abrió BELOW VA. Más verde = mejor setup de compra.</div>
    <div class="hm-wrap"><div id="hm4"></div></div>
    <div class="cases-panel" id="cp4">
      <div class="cp-title" id="cp4-title">Casos seleccionados</div>
      <div class="cp-stats" id="cp4-stats"></div>
      <table class="ct"><thead><tr>
        <th>Fecha</th><th>LEV%</th><th>AM%</th><th>VXN</th><th>Dist POC</th><th>30min</th><th>NY Move</th><th>Resultado</th>
      </tr></thead><tbody id="cp4-body"></tbody></table>
    </div>
  </div>

  <!-- TAB DOUBLE -->
  <div class="tab-pane" id="tab-double">
    <div class="info-card">
      <strong>Doble Filtro:</strong> ¿Cuándo LEV y AM coinciden en zona bajista, qué winrate tiene el SELL setup?<br>
      Esta es la combinación más poderosa — cuando ambos apuntan a lo mismo.
    </div>
    <div class="hm-title">🎯 HM3 — LEV MONEY% × ASSET MANAGER% → % NY BAJISTA (ABOVE VA)</div>
    <div class="hm-subtitle">La celda más potente: LEV BEAR + AM BEAR = máxima presión bajista institucional.</div>
    <div class="hm-wrap"><div id="hm3"></div></div>
    <div class="cases-panel" id="cp3">
      <div class="cp-title" id="cp3-title">Casos seleccionados</div>
      <div class="cp-stats" id="cp3-stats"></div>
      <table class="ct"><thead><tr>
        <th>Fecha</th><th>LEV%</th><th>AM%</th><th>VXN</th><th>Dist POC</th><th>30min</th><th>NY Move</th><th>Resultado</th>
      </tr></thead><tbody id="cp3-body"></tbody></table>
    </div>
  </div>

</div><!-- /page -->

<script>
const D = JSONDATA_PLACEHOLDER;

document.getElementById('total-badge').textContent = D.total_mondays + ' lunes analizados';

// ── COLORES ──────────────────────────────────────────────────────────
function wrColor(wr, isBear) {{
  if (wr === null) return '#181d2e';
  // Para SELL: alto % BEAR = rojo (bueno)
  // Para BUY:  alto % BULL = verde (bueno)
  if (isBear) {{
    if (wr >= 80) return '#7f1d1d';
    if (wr >= 65) return '#b91c1c';
    if (wr >= 55) return '#dc2626';
    if (wr >= 45) return '#374151';
    if (wr >= 35) return '#166534';
    return '#14532d';
  }} else {{
    if (wr >= 80) return '#14532d';
    if (wr >= 65) return '#166534';
    if (wr >= 55) return '#15803d';
    if (wr >= 45) return '#374151';
    if (wr >= 35) return '#b45309';
    return '#7c2d12';
  }}
}}

function wrTextColor(wr) {{
  if (wr === null) return '#4b5563';
  return '#ffffff';
}}

// ── BUILD HEATMAP ────────────────────────────────────────────────────
function buildHeatmap(containerId, data, xLabels, yLabels, isBear, cpId) {{
  const wrap = document.getElementById(containerId);
  const xL = xLabels.map(l => l.replace('\\n','<br>'));
  const yL = yLabels.map(l => l.replace('\\n','<br>'));

  let html = '<table class="hm"><thead><tr><th class="row-header"></th>';
  xL.forEach(l => {{ html += `<th>${{l}}</th>`; }});
  html += '</tr></thead><tbody>';

  yLabels.forEach((y, yi) => {{
    html += `<tr><th class="row-header" style="text-align:right;white-space:pre-line;font-size:0.65rem;">${{yL[yi]}}</th>`;
    xLabels.forEach((x, xi) => {{
      const cell = data.find(c => c.x===x && c.y===y);
      if (!cell || cell.n === 0) {{
        html += `<td><div class="hm-empty">—</div></td>`;
      }} else {{
        const bg = wrColor(cell.wr, isBear);
        const wrStr = cell.wr !== null ? cell.wr + '%' : '—';
        html += `<td><div class="hm-cell" style="background:${{bg}}"
          onclick="showCases('${{cpId}}', ${{JSON.stringify(cell).replace(/'/g,"\\'")}}, '${{x.replace(/\\n/,' ')}}', '${{y}}')">
          <div class="hm-wr">${{wrStr}}</div>
          <div class="hm-n">n=${{cell.n}}</div>
        </div></td>`;
      }}
    }});
    html += '</tr>';
  }});
  html += '</tbody></table>';
  wrap.innerHTML = html;
}}

// ── SHOW CASES ───────────────────────────────────────────────────────
function showCases(cpId, cell, x, y) {{
  const panel = document.getElementById(cpId);
  const title = document.getElementById(cpId+'-title');
  const stats = document.getElementById(cpId+'-stats');
  const tbody = document.getElementById(cpId+'-body');

  // Cerrar si ya estaba abierto con misma celda
  if (panel.classList.contains('show') && panel.dataset.key === x+'|'+y) {{
    panel.classList.remove('show'); return;
  }}
  panel.dataset.key = x+'|'+y;
  panel.classList.add('show');

  const wr = cell.wr !== null ? cell.wr+'%' : '—';
  title.textContent = `${{x}} × ${{y}} → ${{cell.wins}}/${{cell.n}} WIN (${{wr}})`;

  const avgMove = cell.cases.length
    ? (cell.cases.reduce((s,c)=>s+c.move,0)/cell.cases.length).toFixed(2)
    : '—';
  const avg30 = cell.cases.length
    ? (cell.cases.reduce((s,c)=>s+Math.abs(c.m30),0)/cell.cases.length*230).toFixed(0)
    : '—';

  stats.innerHTML = `
    <div class="cp-stat"><div class="v" style="color:var(--accent2)">${{cell.n}}</div><div class="l">Casos</div></div>
    <div class="cp-stat"><div class="v" style="color:var(--red)">${{cell.wins}}</div><div class="l">Wins</div></div>
    <div class="cp-stat"><div class="v" style="color:${{cell.wr>=55?'var(--red)':'var(--green)'}}">${{wr}}</div><div class="l">Winrate</div></div>
    <div class="cp-stat"><div class="v" style="color:var(--orange)">${{avgMove}}%</div><div class="l">NY Move avg</div></div>
    <div class="cp-stat"><div class="v" style="color:var(--yellow)">${{avg30}} pts</div><div class="l">30min avg</div></div>
  `;

  const rows = cell.cases.sort((a,b)=>b.move-a.move);
  tbody.innerHTML = rows.map(r => {{
    const dc = r.dir==='BULL'?'dir-bull':r.dir==='BEAR'?'dir-bear':'dir-flat';
    const m30c = r.m30<0 ? 'var(--red)' : 'var(--green)';
    const pts30 = Math.abs(r.m30*230).toFixed(0);
    return `<tr>
      <td>${{r.d}}</td>
      <td style="color:var(--accent)">${{r.lev.toFixed(1)}}%</td>
      <td style="color:var(--accent2)">${{r.am.toFixed(1)}}%</td>
      <td style="color:var(--yellow)">${{r.vxn}}</td>
      <td>${{r.poc>0?'+':''}}${{r.poc}} pts</td>
      <td style="color:${{m30c}}">${{r.m30>0?'+':''}}${{(r.m30).toFixed(2)}}% (~${{pts30}}pts)</td>
      <td>${{r.move>0?'+':''}}${{r.move.toFixed(2)}}%</td>
      <td class="${{dc}}">${{r.dir}}</td>
    </tr>`;
  }}).join('');
}}

// ── TABS ─────────────────────────────────────────────────────────────
function switchTab(t) {{
  ['sell','buy','double'].forEach(id => {{
    document.getElementById('tab-'+id).classList.toggle('active', id===t);
    document.getElementById('tbtn-'+id).classList.toggle('active', id===t);
  }});
}}

// ── INIT ─────────────────────────────────────────────────────────────
buildHeatmap('hm1', D.hm1, D.lev_buckets, D.vxn_buckets, true, 'cp1');
buildHeatmap('hm2', D.hm2, D.am_buckets,  D.vxn_buckets, true, 'cp2');
buildHeatmap('hm3', D.hm3, D.lev_buckets, D.am_buckets,  true, 'cp3');
buildHeatmap('hm4', D.hm4, D.lev_buckets, D.vxn_buckets, false,'cp4');
</script>
</body>
</html>"""

html = html.replace("JSONDATA_PLACEHOLDER", json.dumps(data_js, ensure_ascii=False))

with open("heatmap_backtest.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ heatmap_backtest.html generado!")
print(f"   Lunes analizados: {len(rows)}")
