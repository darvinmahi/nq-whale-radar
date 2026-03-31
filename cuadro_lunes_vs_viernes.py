"""
cuadro_lunes_vs_viernes.py
Tabla Lunes con Metodología + Comparativa vs Viernes anterior
"""
import yfinance as yf, pandas as pd, csv, json, math, sys
from datetime import datetime, timedelta
from collections import defaultdict

# ─── CONFIG ───────────────────────────────────────────────────
PERIOD  = "5y"    # más histórico que el original (13mo)
BUF_PTS = 20      # pts NQ sweep buffer
VP_BIN  = 5.0     # bin Value Profile

print("📥 Descargando QQQ + VXN + VIX...")
try:
    qqq = yf.download("QQQ",  period=PERIOD, auto_adjust=True, progress=False)
    vxn = yf.download("^VXN", period=PERIOD, auto_adjust=True, progress=False)
    vix = yf.download("^VIX", period=PERIOD, auto_adjust=True, progress=False)
except Exception as e:
    print(f"❌ yfinance error: {e}"); sys.exit(1)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

qqq_o = col(qqq,"Open"); qqq_h = col(qqq,"High")
qqq_l = col(qqq,"Low");  qqq_c = col(qqq,"Close")
vxn_c = col(vxn,"Close"); vix_c = col(vix,"Close")

df = pd.DataFrame({
    "O":qqq_o,"H":qqq_h,"L":qqq_l,"C":qqq_c,
    "VXN":vxn_c,"VIX":vix_c
}).dropna()
df.index = pd.to_datetime(df.index).tz_localize(None)

print(f"   Datos: {df.index[0].date()} → {df.index[-1].date()}  ({len(df)} días)")

# ─── Cargar NQ 15min para Value Profile ───────────────────────
print("📥 Cargando NQ 15min para Value Profile...")
nq_bars = []
try:
    with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                dt = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
                cl,hi,lo,op = (float(r[k]) for k in ["Close","High","Low","Open"])
                vol = float(r.get("Volume",0) or (hi-lo)*100)
                if cl > 0: nq_bars.append({"dt":dt,"close":cl,"high":hi,"low":lo,"open":op,"vol":vol})
            except: pass
    nq_bars.sort(key=lambda x: x["dt"])
    nq_by_date = defaultdict(list)
    for b in nq_bars: nq_by_date[b["dt"].date()].append(b)
    print(f"   NQ 15min: {len(nq_bars):,} barras")
except Exception as e:
    print(f"   ⚠️  NQ 15min no disponible: {e}")
    nq_by_date = {}

# ─── Cargar COT ───────────────────────────────────────────────
print("📥 Cargando COT...")
cot_rows = []
try:
    with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
                ll = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
                ls = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                cot_rows.append({"date":d,"net":ll-ls,"signal":"BULL" if ll>ls else "BEAR"})
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
    print(f"   COT: {len(cot_rows)} semanas")
except Exception as e:
    print(f"   ⚠️  COT no disponible: {e}")

def get_cot(monday):
    prev = [r for r in cot_rows if r["date"] < monday]
    return prev[-1] if prev else {"net":0,"signal":"?"}

# ─── Value Profile ────────────────────────────────────────────
def calc_vp(session_bars):
    if len(session_bars) < 3: return None,None,None
    lo_all = min(b["low"] for b in session_bars)
    hi_all = max(b["high"] for b in session_bars)
    if hi_all <= lo_all: return None,None,None
    n = max(1, int(math.ceil((hi_all-lo_all)/VP_BIN)))
    bins = [0.0]*n
    for b in session_bars:
        vol = b["vol"] if b["vol"]>0 else 1.0
        rng = b["high"]-b["low"] if b["high"]>b["low"] else VP_BIN
        for i in range(n):
            bl = lo_all + i*VP_BIN; bh = bl + VP_BIN
            ov = max(0, min(b["high"],bh)-max(b["low"],bl))
            bins[i] += vol*(ov/rng)
    total = sum(bins)
    if total == 0: return None,None,None
    pi = bins.index(max(bins))
    poc = lo_all + pi*VP_BIN + VP_BIN/2
    va = total*0.70; acc = bins[pi]; li = hi = pi
    while acc < va:
        el = li-1 if li>0 else None; eh = hi+1 if hi<n-1 else None
        vl = bins[el] if el is not None else -1
        vh = bins[eh] if eh is not None else -1
        if vl<=0 and vh<=0: break
        if vh>=vl: hi=eh; acc+=vh
        else: li=el; acc+=vl
    return round(lo_all+hi*VP_BIN+VP_BIN,1), round(poc,1), round(lo_all+li*VP_BIN,1)

# ─── Zona VXN ─────────────────────────────────────────────────
def vxn_zona(v):
    if v>=33: return "🔴🔴 XFEAR","#ff2d55","xfear",50
    if v>=25: return "🔴 FEAR",   "#ff6b35","fear", 30
    if v>=18: return "🟡 NEUTRAL","#f59e0b","neut", 15
    return          "🟢 GREED",  "#10b981","greed",10

def patron_ict(vxn_val, gap_pct):
    if vxn_val>=33: return "SWEEP + RETURN (alta amplitud)"
    if abs(gap_pct)>1.5: return "NEWS_DRIVE / GAP"
    if vxn_val>=25: return "SWEEP + RETURN"
    if vxn_val>=18: return "ROTATION_POC / EXPANSION"
    return "SWEEP_H_RETURN (short bias)"

# ─── Analizar lunes ───────────────────────────────────────────
dates = df.index.tolist()
results = []

for i, date in enumerate(dates):
    if date.weekday() != 0: continue

    prev_dates = [d for d in dates[:i]]
    if not prev_dates: continue
    prev = prev_dates[-1]

    vxn_val  = float(df.loc[prev,"VXN"])
    vix_val  = float(df.loc[prev,"VIX"])
    zona, color, zona_key, buf_pts = vxn_zona(vxn_val)

    # Datos del lunes
    nq_o  = float(df.loc[date,"O"])
    nq_h  = float(df.loc[date,"H"])
    nq_l  = float(df.loc[date,"L"])
    nq_c  = float(df.loc[date,"C"])
    nq_pc = float(df.loc[prev,"C"])

    gap_pct   = (nq_o - nq_pc) / nq_pc * 100
    move_pct  = (nq_c - nq_o)  / nq_o  * 100
    range_pct = (nq_h - nq_l)  / nq_o  * 100

    mon_dir = "BULL" if move_pct>0.15 else ("BEAR" if move_pct<-0.15 else "FLAT")

    # Datos del VIERNES anterior (buscar el viernes de esa semana)
    fri_dates = [d for d in dates[:i] if d.weekday()==4]  # 4=viernes
    fri = fri_dates[-1] if fri_dates else prev

    fri_o = float(df.loc[fri,"O"])
    fri_c = float(df.loc[fri,"C"])
    fri_h = float(df.loc[fri,"H"])
    fri_l = float(df.loc[fri,"L"])
    fri_move = (fri_c - fri_o) / fri_o * 100
    fri_dir  = "BULL" if fri_move>0.1 else ("BEAR" if fri_move<-0.1 else "FLAT")
    fri_range_pct = (fri_h - fri_l) / fri_o * 100

    # Value Profile Asia (desde NQ 15min si disponible)
    vah = poc = val = None
    if nq_by_date:
        dom = date.date() - timedelta(days=1)
        asia_bars = []
        for b in nq_by_date.get(dom, []):
            if b["dt"].hour >= 23: asia_bars.append(b)
        for b in nq_by_date.get(date.date(), []):
            if b["dt"].hour < 9 or (b["dt"].hour==9 and b["dt"].minute<20):
                asia_bars.append(b)
        if not asia_bars:
            for b in nq_by_date.get(fri.date() if hasattr(fri,"date") else fri, []):
                if b["dt"].hour >= 21: asia_bars.append(b)
        if len(asia_bars) >= 3:
            vah, poc, val = calc_vp(asia_bars)

    # COT
    cot = get_cot(date.date())
    cot_signal = cot["signal"]
    cot_net    = cot["net"]

    patron = patron_ict(vxn_val, gap_pct)

    # Match viernes vs lunes
    match = ""
    match_key = ""
    if fri_dir in ("BULL","BEAR") and mon_dir in ("BULL","BEAR"):
        if fri_dir == mon_dir:
            match = "✅ IGUAL"; match_key = "IGUAL"
        else:
            match = "🔄 INVERTIDO"; match_key = "INVERTIDO"

    results.append({
        "date": date, "fri": fri,
        "vxn": round(vxn_val,1), "vix": round(vix_val,1),
        "zona": zona, "color": color, "zona_key": zona_key, "buf_pts": buf_pts,
        "gap_pct": round(gap_pct,2), "move_pct": round(move_pct,2), "range_pct": round(range_pct,2),
        "mon_dir": mon_dir, "patron": patron,
        "fri_dir": fri_dir, "fri_move": round(fri_move,2), "fri_range": round(fri_range_pct,2),
        "vah": vah, "poc": poc, "val": val,
        "cot_signal": cot_signal, "cot_net": cot_net,
        "match": match, "match_key": match_key,
    })

df_r = pd.DataFrame(results).sort_values("date", ascending=False)
n = len(df_r)
print(f"✅ {n} lunes analizados")

# ─── Estadísticas ─────────────────────────────────────────────
def pct(a,b): return f"{round(a/b*100)}%" if b else "—"

n_bull = len(df_r[df_r.mon_dir=="BULL"])
n_bear = len(df_r[df_r.mon_dir=="BEAR"])

# Matriz Viernes → Lunes
mat = df_r[(df_r.fri_dir.isin(["BULL","BEAR"])) & (df_r.mon_dir.isin(["BULL","BEAR"]))]
bb = len(mat[(mat.fri_dir=="BULL")&(mat.mon_dir=="BULL")])
bn = len(mat[(mat.fri_dir=="BULL")&(mat.mon_dir=="BEAR")])
rb = len(mat[(mat.fri_dir=="BEAR")&(mat.mon_dir=="BULL")])
rn = len(mat[(mat.fri_dir=="BEAR")&(mat.mon_dir=="BEAR")])

n_igual = len(df_r[df_r.match_key=="IGUAL"])
n_inv   = len(df_r[df_r.match_key=="INVERTIDO"])

# Por zona VXN
def zona_stats(key, lo, hi):
    z = df_r[(df_r.vxn>=lo)&(df_r.vxn<hi)]
    if z.empty: return None
    zb = len(z[z.mon_dir=="BULL"])
    ze = len(z[z.mon_dir=="BEAR"])
    zm = z[(z.fri_dir.isin(["BULL","BEAR"]))&(z.mon_dir.isin(["BULL","BEAR"]))]
    frb_bb = len(zm[(zm.fri_dir=="BULL")&(zm.mon_dir=="BULL")])
    frb_bt = len(zm[zm.fri_dir=="BULL"])
    frr_rb = len(zm[(zm.fri_dir=="BEAR")&(zm.mon_dir=="BULL")])
    frr_rt = len(zm[zm.fri_dir=="BEAR"])
    return {
        "n": len(z), "bull": zb, "bear": ze,
        "bull_pct": pct(zb,len(z)), "bear_pct": pct(ze,len(z)),
        "avg_rng":  round(z.range_pct.mean()*100,2),
        "fri_bull_bull": pct(frb_bb, frb_bt),
        "fri_bear_bull": pct(frr_rb, frr_rt),
    }

zs = {
    "xfear": zona_stats("xfear", 33, 999),
    "fear":  zona_stats("fear",  25, 33),
    "neut":  zona_stats("neut",  18, 25),
    "greed": zona_stats("greed", 0,  18),
}

# ─── Badges ───────────────────────────────────────────────────
def dbadge(d):
    if d=="BULL": return '<span class="bull-b">🟢 BULL</span>'
    if d=="BEAR": return '<span class="bear-b">🔴 BEAR</span>'
    return '<span class="flat-b">— FLAT</span>'

def zs_card(label, color, s):
    if not s: return ""
    return f"""
<div class="zcard" style="border-color:{color}44">
  <div style="color:{color};font-weight:900;font-size:12px;margin-bottom:8px">{label}</div>
  <div class="zg">
    <div><span class="zn">{s['n']}</span><span class="zl">lunes</span></div>
    <div><span class="zn" style="color:#00ff80">{s['bull_pct']}</span><span class="zl">BULL</span></div>
    <div><span class="zn" style="color:#ff2d55">{s['bear_pct']}</span><span class="zl">BEAR</span></div>
  </div>
  <div style="margin-top:8px;font-size:10px;color:#888;border-top:1px solid rgba(255,255,255,0.06);padding-top:8px;line-height:1.8">
    <b style="color:#ccc">Viernes→Lunes</b><br>
    Vie 🟢 → Lun BULL: <b style="color:#00ff80">{s['fri_bull_bull']}</b><br>
    Vie 🔴 → Lun BULL: <b style="color:#f59e0b">{s['fri_bear_bull']}</b>
  </div>
</div>"""

# ─── Filas HTML ───────────────────────────────────────────────
rows = ""
for _, r in df_r.iterrows():
    d = r["date"]
    cot_c = "#00ff80" if r["cot_signal"]=="BULL" else ("#ff2d55" if r["cot_signal"]=="BEAR" else "#888")
    vp_html = ""
    if r["vah"]:
        vp_html = f'<span style="color:#ff6b35">▲{r["vah"]}</span> <span style="color:#f59e0b">●{r["poc"]}</span> <span style="color:#60a5fa">▼{r["val"]}</span>'
    else:
        vp_html = '<span style="color:#444">Sin datos</span>'
    match_c = "#34d399" if r["match_key"]=="IGUAL" else ("#f59e0b" if r["match_key"]=="INVERTIDO" else "#555")
    rows += f"""<tr class="lr" data-vxn="{r['vxn']}" data-res="{r['mon_dir']}" data-fri="{r['fri_dir']}">
<td class="fc"><div style="font-weight:700">{d.strftime('%d %b %Y')}</div><div style="color:#555;font-size:10px">S{d.isocalendar()[1]}</div></td>
<td>{dbadge(r['fri_dir'])}<div style="color:#666;font-size:10px;margin-top:2px">{r['fri_move']:+.2f}% · Rng {r['fri_range']:.2f}%</div></td>
<td><div style="color:{r['color']};font-weight:700;font-size:12px">{r['zona']}</div><div style="color:#666;font-size:10px">VXN {r['vxn']} / VIX {r['vix']}</div></td>
<td><span style="color:{cot_c};font-weight:700">{r['cot_signal']}</span><div style="color:#444;font-size:10px">{r['cot_net']:,}</div></td>
<td style="font-size:11px">{vp_html}</td>
<td style="color:#a78bfa;font-size:11px;max-width:180px">{r['patron']}</td>
<td><div style="color:{'#10b981' if r['gap_pct']>0 else '#ff2d55'};font-weight:700">{r['gap_pct']:+.2f}%</div></td>
<td>{dbadge(r['mon_dir'])}<div style="color:#666;font-size:10px;margin-top:2px">{r['move_pct']:+.2f}% · Rng {r['range_pct']:.2f}%</div></td>
<td style="color:{match_c};font-weight:700;font-size:12px">{r['match']}</td>
</tr>"""

now_str = datetime.now().strftime("%d/%m/%Y %H:%M")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>📅 Lunes vs Viernes — NQ Whale Radar</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#07070f;color:#e2e8f0;padding:24px;min-height:100vh}}
h1{{font-size:24px;font-weight:900;background:linear-gradient(135deg,#a78bfa,#60a5fa,#34d399);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.sub{{color:#444;font-size:12px;margin:6px 0 28px}}

/* ALERTA */
.alert{{background:linear-gradient(135deg,rgba(255,45,85,0.1),rgba(167,139,250,0.08));border:1px solid #ff2d5555;border-radius:16px;padding:20px;margin-bottom:24px}}
.alert h2{{color:#ff2d55;font-size:17px;font-weight:900;margin-bottom:12px}}
.ag{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;font-size:13px}}

/* TOP STATS */
.ts{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:20px}}
.tc{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;text-align:center}}
.tn{{font-size:24px;font-weight:900;color:#a78bfa}}
.tl{{font-size:10px;color:#555;margin-top:3px;text-transform:uppercase;letter-spacing:.05em}}

/* MATRIZ */
.ms{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:22px}}
.mc{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:16px}}
.mc h3{{font-size:11px;font-weight:700;color:#a78bfa;text-transform:uppercase;letter-spacing:.07em;margin-bottom:12px}}
.mt{{width:100%;border-collapse:collapse;font-size:12px}}
.mt th{{color:#444;font-size:10px;text-transform:uppercase;padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.05);text-align:center}}
.mt td{{padding:8px;text-align:center;font-weight:700}}
.bnum{{font-size:20px;font-weight:900;display:block}}
.bpct{{font-size:10px;color:#888;display:block}}

/* ZONAS */
.zg4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:22px}}
.zcard{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px}}
.zg{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:6px}}
.zn{{display:block;font-size:18px;font-weight:900}}
.zl{{display:block;font-size:9px;color:#555;text-transform:uppercase}}

/* FILTROS */
.filters{{display:flex;gap:7px;margin-bottom:14px;flex-wrap:wrap}}
.fb{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:#e2e8f0;padding:6px 14px;border-radius:20px;cursor:pointer;font-size:11px;font-family:'Inter',sans-serif;transition:all .2s}}
.fb.active,.fb:hover{{background:rgba(167,139,250,0.15);border-color:#a78bfa;color:#a78bfa}}

/* TABLA */
.tw{{overflow-x:auto;border-radius:12px;border:1px solid rgba(255,255,255,0.06)}}
table.mt2{{width:100%;border-collapse:collapse;font-size:12px}}
.mt2 thead th{{background:rgba(255,255,255,0.04);padding:10px 12px;text-align:left;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#555;border-bottom:1px solid rgba(255,255,255,0.06);white-space:nowrap}}
.lr{{border-bottom:1px solid rgba(255,255,255,0.03);transition:background .15s}}
.lr:hover{{background:rgba(167,139,250,0.04)}}
.lr td{{padding:9px 12px;vertical-align:top}}
.lr.hidden{{display:none}}
.fc{{white-space:nowrap}}

/* BADGES */
.bull-b{{display:inline-block;padding:2px 8px;border-radius:7px;font-size:11px;font-weight:700;background:rgba(0,255,128,.1);color:#00ff80;border:1px solid rgba(0,255,128,.3)}}
.bear-b{{display:inline-block;padding:2px 8px;border-radius:7px;font-size:11px;font-weight:700;background:rgba(255,45,85,.1);color:#ff2d55;border:1px solid rgba(255,45,85,.3)}}
.flat-b{{display:inline-block;padding:2px 8px;border-radius:7px;font-size:11px;font-weight:700;background:rgba(148,163,184,.1);color:#94a3b8;border:1px solid rgba(148,163,184,.3)}}

@media(max-width:900px){{
  .ts{{grid-template-columns:repeat(3,1fr)}}.ms{{grid-template-columns:1fr}}.zg4{{grid-template-columns:1fr 1fr}}.ag{{grid-template-columns:1fr}}
}}
</style>
</head>
<body>

<h1>📅 Lunes vs Viernes — NQ Whale Radar</h1>
<p class="sub">Metodología: ICT + VXN + COT + Value Profile Asia · {n} lunes · {now_str}</p>

<!-- ALERTA MAÑANA -->
<div class="alert">
  <h2>⚡ LUNES 31 MARZO 2026 — Contexto Pre-Mercado</h2>
  <div class="ag">
    <div>
      <div style="color:#666;font-size:10px;text-transform:uppercase;margin-bottom:4px">VXN Viernes 28 Mar</div>
      <div style="font-size:32px;font-weight:900;color:#ff2d55">33.5</div>
      <div style="color:#ff6b35;font-weight:700;font-size:13px">🔴🔴 XFEAR</div>
    </div>
    <div>
      <div style="color:#666;font-size:10px;text-transform:uppercase;margin-bottom:4px">Histórico XFEAR (VXN≥33)</div>
      <div style="font-size:22px;font-weight:900;color:#00ff80">{zs['xfear']['bull_pct'] if zs['xfear'] else '?'} BULL</div>
      <div style="color:#888;font-size:12px">en {zs['xfear']['n'] if zs['xfear'] else '?'} lunes con VXN≥33</div>
      <div style="color:#a78bfa;font-size:12px;margin-top:4px">Vie🔴→Lun BULL: {zs['xfear']['fri_bear_bull'] if zs['xfear'] else '?'}</div>
    </div>
    <div style="font-size:12px;color:#888;line-height:1.8">
      <div style="color:#ccc;font-weight:700;margin-bottom:6px">Guía ICT para mañana:</div>
      → Esperar sweep del Range Hi/Lo<br>
      → Buffer entrada: ~50 pts NQ<br>
      → Amplitud mayor (+60-100 pts)<br>
      → NO entrar en el pico del sweep<br>
      → Sesión NY 09:30–11:30 ET
    </div>
  </div>
</div>

<!-- TOP STATS -->
<div class="ts">
  <div class="tc"><div class="tn">{n}</div><div class="tl">Lunes totales</div></div>
  <div class="tc"><div class="tn" style="color:#00ff80">{pct(n_bull,n)}</div><div class="tl">Lunes BULL</div></div>
  <div class="tc"><div class="tn" style="color:#ff2d55">{pct(n_bear,n)}</div><div class="tl">Lunes BEAR</div></div>
  <div class="tc"><div class="tn" style="color:#34d399">{pct(n_igual,n_igual+n_inv)}</div><div class="tl">Vie=Lun (misma dir.)</div></div>
  <div class="tc"><div class="tn" style="color:#f59e0b">{pct(n_inv,n_igual+n_inv)}</div><div class="tl">Vie≠Lun (invertido)</div></div>
</div>

<!-- MATRIZ VIERNES → LUNES -->
<div class="ms">
  <div class="mc">
    <h3>📊 Matriz Viernes → Lunes (dirección)</h3>
    <table class="mt">
      <tr><th>Viernes</th><th>→ Lunes 🟢 BULL</th><th>→ Lunes 🔴 BEAR</th><th>% BULL</th></tr>
      <tr>
        <td style="color:#00ff80;font-weight:700;text-align:left">🟢 Vie BULL</td>
        <td><span class="bnum" style="color:#00ff80">{bb}</span><span class="bpct">{pct(bb,bb+bn)} del total</span></td>
        <td><span class="bnum" style="color:#ff2d55">{bn}</span></td>
        <td style="color:#a78bfa;font-weight:900">{pct(bb,bb+bn)}</td>
      </tr>
      <tr>
        <td style="color:#ff2d55;font-weight:700;text-align:left">🔴 Vie BEAR</td>
        <td><span class="bnum" style="color:#00ff80">{rb}</span><span class="bpct">{pct(rb,rb+rn)} del total</span></td>
        <td><span class="bnum" style="color:#ff2d55">{rn}</span></td>
        <td style="color:#a78bfa;font-weight:900">{pct(rb,rb+rn)}</td>
      </tr>
    </table>
    <div style="margin-top:12px;font-size:11px;color:#555;line-height:1.7">
      Total pares comparables: {bb+bn+rb+rn} · Igual dirección: {n_igual} ({pct(n_igual,n_igual+n_inv)}) · Invertido: {n_inv} ({pct(n_inv,n_igual+n_inv)})
    </div>
  </div>

  <div class="mc">
    <h3>🌡️ Condicionado por Zona VXN</h3>
    <table class="mt">
      <tr><th>Zona VXN</th><th>Vie🟢→Lun BULL</th><th>Vie🔴→Lun BULL</th><th>Total Lunes</th></tr>
      {''.join([
        f'''<tr>
          <td style="font-weight:700;text-align:left;color:{c}">{lab}</td>
          <td style="color:#00ff80">{zs[k]['fri_bull_bull'] if zs[k] else '—'}</td>
          <td style="color:#f59e0b">{zs[k]['fri_bear_bull'] if zs[k] else '—'}</td>
          <td style="color:#888">{zs[k]['n'] if zs[k] else '—'}</td>
        </tr>'''
        for lab,c,k in [
          ("🔴🔴 XFEAR ≥33","#ff2d55","xfear"),
          ("🔴 FEAR 25-33", "#ff6b35","fear"),
          ("🟡 NEUTRAL 18-25","#f59e0b","neut"),
          ("🟢 GREED <18","#10b981","greed"),
        ]
      ])}
    </table>
  </div>
</div>

<!-- ZONAS VXN CARDS -->
<div class="zg4">
  {zs_card("🔴🔴 XFEAR — VXN ≥33","#ff2d55",zs["xfear"])}
  {zs_card("🔴 FEAR — VXN 25-33","#ff6b35",zs["fear"])}
  {zs_card("🟡 NEUTRAL — VXN 18-25","#f59e0b",zs["neut"])}
  {zs_card("🟢 GREED — VXN <18","#10b981",zs["greed"])}
</div>

<!-- FILTROS -->
<div class="filters">
  <button class="fb active" onclick="fa('ALL',this)">Todos ({n})</button>
  <button class="fb" onclick="fr('BULL',this)">🟢 Lunes BULL ({n_bull})</button>
  <button class="fb" onclick="fr('BEAR',this)">🔴 Lunes BEAR ({n_bear})</button>
  <button class="fb" onclick="fxn(33,999,this)">🔴🔴 XFEAR VXN≥33</button>
  <button class="fb" onclick="fxn(25,33,this)">🔴 FEAR 25–33</button>
  <button class="fb" onclick="fxn(18,25,this)">🟡 NEUTRAL 18–25</button>
  <button class="fb" onclick="fxn(0,18,this)">🟢 GREED &lt;18</button>
  <button class="fb" onclick="fv('BULL',this)">Vie 🟢 BULL</button>
  <button class="fb" onclick="fv('BEAR',this)">Vie 🔴 BEAR</button>
</div>

<!-- TABLA PRINCIPAL -->
<div class="tw">
<table class="mt2">
  <thead><tr>
    <th>📅 Lunes</th>
    <th>📊 Viernes</th>
    <th>🌡️ VXN / Zona</th>
    <th>📜 COT</th>
    <th>📐 Value Profile Asia</th>
    <th>🎯 Patrón ICT Esperado</th>
    <th>↕️ Gap Apertura</th>
    <th>📈 Resultado Lunes</th>
    <th>🔄 Vie→Lun</th>
  </tr></thead>
  <tbody id="tb">{rows}</tbody>
</table>
</div>

<div style="text-align:center;margin-top:18px;color:#333;font-size:11px">
  Whale Radar v2.2 · QQQ proxy NQ · Value Profile NQ 15min · VXN viernes · COT semanal · {now_str}
</div>

<script>
function fa(t,b){{setA(b);document.querySelectorAll('.lr').forEach(r=>r.classList.remove('hidden'))}}
function fr(t,b){{setA(b);document.querySelectorAll('.lr').forEach(r=>r.classList.toggle('hidden',r.dataset.res!==t))}}
function fxn(lo,hi,b){{setA(b);document.querySelectorAll('.lr').forEach(r=>{{const v=+r.dataset.vxn;r.classList.toggle('hidden',!(v>=lo&&v<hi))}})}}
function fv(t,b){{setA(b);document.querySelectorAll('.lr').forEach(r=>r.classList.toggle('hidden',r.dataset.fri!==t))}}
function setA(b){{document.querySelectorAll('.fb').forEach(x=>x.classList.remove('active'));b.classList.add('active')}}
</script>
</body>
</html>"""

with open("cuadro_lunes_vs_viernes.html","w",encoding="utf-8") as f:
    f.write(html)
print("\n✅ cuadro_lunes_vs_viernes.html  →  http://localhost:8765/cuadro_lunes_vs_viernes.html")
print(f"   {n} lunes · BULL {pct(n_bull,n)} · BEAR {pct(n_bear,n)}")
print(f"   Vie🟢→Lun BULL: {pct(bb,bb+bn)}  ·  Vie🔴→Lun BULL: {pct(rb,rb+rn)}")
