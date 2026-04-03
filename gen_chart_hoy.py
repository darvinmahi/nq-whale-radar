#!/usr/bin/env python3
"""
gen_chart_hoy.py — Generador universal de charts de sesión NQ
Uso: python gen_chart_hoy.py [YYYYMMDD]
     Sin fecha → genera para HOY automáticamente

Genera: {dia}_chart_{YYYYMMDD}.html  compatible con daily_dashboard.html
"""
import sys, json, os
from datetime import datetime, timezone, timedelta, date
import yfinance as yf

# ── Fecha objetivo ─────────────────────────────────────────────────────────
if len(sys.argv) > 1:
    try:
        target = datetime.strptime(sys.argv[1], "%Y%m%d").date()
    except ValueError:
        print(f"ERROR: formato incorrecto '{sys.argv[1]}'. Usa YYYYMMDD"); sys.exit(1)
else:
    target = date.today()

DOW = target.weekday()  # 0=Lun, 1=Mar, 2=Mie, 3=Jue, 4=Vie
DAY_NAMES = {0:"lunes", 1:"martes", 2:"miercoles", 3:"jueves", 4:"viernes", 5:"sabado", 6:"domingo"}
DAY_LABELS = {0:"LUNES", 1:"MARTES", 2:"MIÉRCOLES", 3:"JUEVES", 4:"VIERNES"}
DAY_ES = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

if DOW not in DAY_NAMES:
    print(f"AVISO: {target} es fin de semana. Generando chart de todos modos.")
    
day_name  = DAY_NAMES.get(DOW, "lunes")
day_label = DAY_LABELS.get(DOW, "LUNES")
day_es    = DAY_ES.get(DOW, target.strftime("%A"))

date_str  = target.strftime("%Y-%m-%d")
date_next = (target + timedelta(days=1)).strftime("%Y-%m-%d")
date_prev = (target - timedelta(days=1)).strftime("%Y-%m-%d")
iso8      = target.strftime("%Y%m%d")
filename  = f"{day_name}_chart_{iso8}.html"

print(f"\n📅 Generando chart para {date_str} ({day_label})")
print(f"   Archivo destino: {filename}\n")

# ── Descargar datos NQ ────────────────────────────────────────────────────
print("Descargando NQ=F 5min...")
df = yf.download("NQ=F", start=date_prev, end=date_next,
                 interval="5m", prepost=True, progress=False)
if df.empty:
    print("ERROR: yfinance no devolvió datos. ¿Es día festivo o fin de semana?"); sys.exit(1)
if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close"})
df = df[["open","high","low","close"]].dropna()
df.index = df.index.tz_convert("UTC")

# Filtrar solo el día objetivo (UTC)
target_date_utc = target.strftime("%Y-%m-%d")
df_day = df[df.index.strftime("%Y-%m-%d") == target_date_utc]
if df_day.empty:
    # Tomar previous day data too (pre-market empieza domingo/día anterior)
    df_day = df

candles = [{"time":int(ts.timestamp()),"open":round(float(r["open"]),2),
            "high":round(float(r["high"]),2),"low":round(float(r["low"]),2),
            "close":round(float(r["close"]),2)} for ts,r in df_day.iterrows()]
if not candles:
    print("ERROR: Sin velas para esta fecha."); sys.exit(1)

print(f"  Barras: {len(candles)} | Rango: {df_day.index[0]} a {df_day.index[-1]}")

# ── Sesiones (ET = UTC-4) ─────────────────────────────────────────────────
y,mo,d = target.year, target.month, target.day
prev_day = target - timedelta(days=1)
yp,mp,dp = prev_day.year, prev_day.month, prev_day.day

ASIA_START  = int(datetime(yp,mp,dp,22, 0,tzinfo=timezone.utc).timestamp())
LONDON      = int(datetime(y, mo, d,  6, 0,tzinfo=timezone.utc).timestamp())
NY_OPEN     = int(datetime(y, mo, d, 13,30,tzinfo=timezone.utc).timestamp())
NY_CLOSE    = int(datetime(y, mo, d, 20, 0,tzinfo=timezone.utc).timestamp())

ny    = [c for c in candles if NY_OPEN <= c["time"] <= NY_CLOSE]
pre   = [c for c in candles if c["time"] < NY_OPEN]

DAY_HIGH = max(c["high"] for c in candles)
DAY_LOW  = min(c["low"]  for c in candles)

NY_OPEN_P  = ny[0]["open"]   if ny else candles[0]["open"]
NY_CLOSE_P = ny[-1]["close"] if ny else candles[-1]["close"]
NY_HIGH    = max(c["high"] for c in ny) if ny else DAY_HIGH
NY_LOW     = min(c["low"]  for c in ny) if ny else DAY_LOW
NY_RANGE   = round(NY_HIGH - NY_LOW, 2)
NY_MOVE    = round(NY_CLOSE_P - NY_OPEN_P, 2)

# ── Volume Profile (pre-NY) ───────────────────────────────────────────────
src = pre if pre else candles
if src:
    pmin = min(c["low"] for c in src); pmax = max(c["high"] for c in src)
    B = 25.0; nb = max(1, int((pmax-pmin)/B)+1)
    vp = [0.0]*nb
    for c in src:
        for i in range(int((c["low"]-pmin)/B), min(int((c["high"]-pmin)/B)+1,nb)):
            vp[i] += 1
    pi = vp.index(max(vp)); POC = round(pmin+pi*B+B/2, 2)
    tv = sum(vp)*0.70; li=hi=pi; acc=vp[pi]
    while acc < tv:
        el=li>0; eh=hi<nb-1
        if el and eh:
            if vp[li-1]>=vp[hi+1]: li-=1; acc+=vp[li]
            else: hi+=1; acc+=vp[hi]
        elif el: li-=1; acc+=vp[li]
        elif eh: hi+=1; acc+=vp[hi]
        else: break
    VAH = round(pmin+hi*B+B, 2); VAL = round(pmin+li*B, 2)
else:
    mid = (DAY_HIGH+DAY_LOW)/2; POC=round(mid,2); VAH=round(mid+50,2); VAL=round(mid-50,2)

print(f"  VP: POC={POC} VAH={VAH} VAL={VAL}")
print(f"  NY: Open={NY_OPEN_P} High={NY_HIGH} Low={NY_LOW} Close={NY_CLOSE_P} Range={NY_RANGE}")

# ── Leer datos de agentes ─────────────────────────────────────────────────
def _jload(path):
    try:
        with open(path,"r",encoding="utf-8") as f: return json.load(f)
    except: return {}

a2 = _jload("agent2_data.json")
a3 = _jload("agent3_data.json")
a4 = _jload("agent4_data.json")

cot      = a2.get("cot", {})
cot_net  = cot.get("current_net", 0) or 0
cot_idx  = cot.get("cot_index", 0) or 0
cot_date = cot.get("date", "N/A")
cot_sig  = a2.get("signal", "NEUTRAL")
cot_str  = a2.get("strength", 50) or 50

raw3     = a3.get("raw_inputs", {})
vxn_val  = float(raw3.get("VXN", 0) or 0)
gex_b    = float(raw3.get("GEX_B", 0) or 0)
dix_val  = float(raw3.get("DIX", 0) or 0)  # ← Fix: None → 0

ai_score = a4.get("global_score", 50) or 50
ai_label = a4.get("global_label", "NEUTRAL")

cot_mom  = a2.get("momentum", {})
cot_dir  = cot_mom.get("direction", "PLANO")
cot_vel  = cot_mom.get("weekly_velocity", 0) or 0
cot_wks  = cot_mom.get("consecutive_weeks", 0) or 0
cot_alrt = a2.get("insight", {}).get("alert", "")
vol_sig  = a3.get("signal", "NEUTRAL")
vol_scr  = a3.get("score", 50) or 50
vxn_lv   = a3.get("vxn_analysis", {}).get("level", "NORMAL")

cot_net_str = f"+{cot_net:,}" if cot_net >= 0 else f"{cot_net:,}"
gex_str     = f"+{gex_b:.2f}B" if gex_b >= 0 else f"{gex_b:.2f}B"
cot_vel_str = f"+{cot_vel:,}/sem" if cot_vel >= 0 else f"{cot_vel:,}/sem"
vxn_lbl = {"COMPLACENCY":"COMPLACENCIA","NORMAL":"NORMAL","ELEVATED":"ELEVADA","PANIC":"PÁNICO","EXTREME_PANIC":"PÁNICO EXTREMO"}.get(vxn_lv, vxn_lv)

print(f"  COT: net={cot_net_str} idx={cot_idx}/100 signal={cot_sig}")
print(f"  VXN: {vxn_val:.2f} | GEX: {gex_str} | DIX: {dix_val:.1f}%")
print(f"  AI Score: {ai_score}/100 ({ai_label})")

# ── Colores / estado ──────────────────────────────────────────────────────
direction = "BULLISH" if NY_MOVE >= 0 else "BEARISH"
dc = "#10b981" if NY_MOVE >= 0 else "#ef4444"
ms = "+" if NY_MOVE >= 0 else ""
n  = len(candles)
CJ = json.dumps(candles, separators=(',',':'))

now_utc = int(datetime.now(timezone.utc).timestamp())
market_open = NY_OPEN <= now_utc <= NY_CLOSE
live_badge = "🟢 EN VIVO" if market_open else "🏁 SESIÓN CERRADA"
live_rgb   = "16,185,129" if market_open else "239,68,68"
live_color = "#6ee7b7" if market_open else "#fca5a5"

def sg(s): return {"BULLISH":"#10b981","BEARISH":"#ef4444"}.get(s,"#94a3b8")
def sb(s): return {"BULLISH":"rgba(16,185,129,.15)","BEARISH":"rgba(239,68,68,.15)"}.get(s,"rgba(148,163,184,.10)")
def sbd(s): return {"BULLISH":"rgba(16,185,129,.4)","BEARISH":"rgba(239,68,68,.4)"}.get(s,"rgba(148,163,184,.3)")
def se(s): return {"BULLISH":"▲","BEARISH":"▼"}.get(s,"●")

ai_color = "#10b981" if ai_label == "ALCISTA" else "#ef4444" if ai_label == "BAJISTA" else "#f59e0b"
dir_color = "#10b981" if NY_MOVE >= 0 else "#ef4444"
dir_rgb   = "16,185,129" if NY_MOVE >= 0 else "239,68,68"

# ── HTML ──────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NQ — {day_label} {date_str} | Whale Radar</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root{{--bg:#04020c;--card:#0c0a1e;--border:#1e1a3a;--purple:#7c3aed;--cyan:#06b6d4;
          --green:#10b981;--red:#ef4444;--amber:#f59e0b;--muted:#94a3b8;--text:#e2e8f0}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}}
    .top-bar{{background:linear-gradient(135deg,#0c0a1e,#110d2a);border-bottom:1px solid var(--border);
              padding:14px 24px;display:flex;align-items:center;justify-content:space-between;
              position:sticky;top:0;z-index:100}}
    .logo-badge{{background:linear-gradient(135deg,var(--purple),#4f46e5);color:#fff;font-size:11px;
                 font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:1px}}
    .live-badge{{background:rgba({live_rgb},.2);border:1px solid rgba({live_rgb},.5);
                 color:{live_color};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px}}
    .page{{max-width:1500px;margin:0 auto;padding:20px 18px}}
    .dh{{background:linear-gradient(135deg,#0c0a1e,#130f2a);border:1px solid var(--border);border-radius:16px;
         padding:18px 24px;position:relative;overflow:hidden;margin-bottom:16px;display:flex;
         align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
    .dh::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
                 background:linear-gradient(90deg,var(--amber),var(--green),var(--cyan),var(--purple))}}
    .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px}}
    .sc{{background:#0c0a1e;border:1px solid var(--border);border-radius:12px;padding:12px 14px;text-align:center}}
    .sl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .sv{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700}}
    .cg{{color:#10b981}}.cr{{color:#ef4444}}.cc{{color:#06b6d4}}.ca{{color:#f59e0b}}.cp{{color:#a78bfa}}.cm{{color:var(--muted)}}
    .macro-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;margin-bottom:18px}}
    .macro-card{{background:#0c0a1e;border:1px solid var(--border);border-radius:14px;padding:16px 18px;position:relative;overflow:hidden}}
    .macro-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:2px 2px 0 0}}
    .mc-cot::before{{background:linear-gradient(90deg,#7c3aed,#06b6d4)}}
    .mc-vol::before{{background:linear-gradient(90deg,#f59e0b,#ef4444)}}
    .mc-gex::before{{background:linear-gradient(90deg,#10b981,#06b6d4)}}
    .mc-ai::before{{background:linear-gradient(90deg,{ai_color},{ai_color}80)}}
    .mc-label{{font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1.2px}}
    .mc-hdr{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
    .mc-sig{{font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px}}
    .mc-main{{font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700;margin-bottom:8px}}
    .mc-bar-w{{background:rgba(255,255,255,.06);border-radius:4px;height:5px;margin-bottom:10px}}
    .mc-bar{{height:100%;border-radius:4px}}
    .mc-meta{{display:flex;gap:16px;flex-wrap:wrap;font-size:10px}}
    .mc-meta-k{{color:var(--muted);text-transform:uppercase;letter-spacing:.8px;font-size:8px}}
    .mc-meta-v{{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600}}
    .chart-wrap{{background:#09071a;border:2px solid rgba(124,58,237,.3);border-radius:20px;overflow:hidden;margin-bottom:16px}}
    .chart-hdr{{padding:14px 20px;border-bottom:1px solid var(--border);background:#0c0a1e;
                display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
    .rl-btn{{background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.35);color:#67e8f9;
             font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:6px 14px;
             border-radius:20px;cursor:pointer}}
    #chart{{width:100%;height:680px}}
    #rb{{max-height:0;overflow:hidden;opacity:0;transition:max-height .35s,opacity .3s;
         background:rgba(6,182,212,.06);border-top:1px solid rgba(6,182,212,.18)}}
    #rb.v{{max-height:200px;opacity:1}}
    .rr{{display:flex;align-items:center;gap:10px;padding:10px 14px;flex-wrap:wrap}}
    .rb2{{background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9;
          font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:6px 14px;
          border-radius:8px;cursor:pointer}}
    .rb2.pause{{background:rgba(245,158,11,.15);border-color:rgba(245,158,11,.4);color:#fcd34d}}
    .spg{{display:flex;gap:3px}}
    .sp{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:var(--muted);
         font-size:10px;padding:4px 8px;border-radius:6px;cursor:pointer;font-family:'JetBrains Mono',monospace}}
    .sp.a{{background:rgba(6,182,212,.25);border-color:#06b6d4;color:#e0f2fe;font-weight:700}}
    .rt{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#67e8f9;min-width:140px;font-weight:600}}
    .rpw{{flex:1;min-width:120px}}
    .rtr{{position:relative;height:6px;background:rgba(255,255,255,.08);border-radius:3px}}
    .rf{{position:absolute;left:0;top:0;height:100%;background:linear-gradient(90deg,#06b6d4,#7c3aed);border-radius:3px}}
    .rs{{position:absolute;left:0;top:-5px;width:100%;height:16px;opacity:0;cursor:pointer;-webkit-appearance:none;appearance:none}}
    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}
  </style>
</head>
<body>
<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">{date_str} · {day_label} · 5 MIN</span>
    <div class="live-badge">{live_badge}</div>
  </div>
  <a href="daily_dashboard.html" style="background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.35);color:#a78bfa;font-size:13px;font-weight:600;padding:7px 16px;border-radius:8px;text-decoration:none">← Daily Dashboard</a>
</div>

<div class="page">
  <div class="dh">
    <div>
      <div style="font-size:18px;font-weight:900;margin-bottom:4px">📅 {day_es} {date_str} · NQ Futures Real</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia → 🇬🇧 London 2AM ET → 🗽 NY Open 9:30AM → 🏁 4PM ET</div>
    </div>
    <span style="background:rgba({dir_rgb},.15);border:1px solid rgba({dir_rgb},.4);color:{dc};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700">{direction} {ms}{NY_MOVE:,.2f} pts</span>
  </div>

  <div class="stats">
    <div class="sc"><div class="sl">Day High</div><div class="sv cc">{DAY_HIGH:,.2f}</div></div>
    <div class="sc"><div class="sl">Day Low</div><div class="sv cr">{DAY_LOW:,.2f}</div></div>
    <div class="sc"><div class="sl">POC pre-NY</div><div class="sv cp">{POC:,.2f}</div></div>
    <div class="sc"><div class="sl">VAH</div><div class="sv cc">{VAH:,.2f}</div></div>
    <div class="sc"><div class="sl">VAL</div><div class="sv cg">{VAL:,.2f}</div></div>
    <div class="sc"><div class="sl">NY Open</div><div class="sv ca">{NY_OPEN_P:,.2f}</div></div>
    <div class="sc"><div class="sl">NY High</div><div class="sv cg">{NY_HIGH:,.2f}</div></div>
    <div class="sc"><div class="sl">NY Low</div><div class="sv cr">{NY_LOW:,.2f}</div></div>
    <div class="sc"><div class="sl">NY Range</div><div class="sv ca">{NY_RANGE:,.0f} pts</div></div>
    <div class="sc"><div class="sl">Move O→C</div><div class="sv {'cg' if NY_MOVE>=0 else 'cr'}">{ms}{NY_MOVE:,.2f}</div></div>
    <div class="sc"><div class="sl">Velas</div><div class="sv cm">{n}</div></div>
    <div class="sc"><div class="sl">AI Score</div><div class="sv" style="color:{ai_color}">{ai_score}/100</div></div>
  </div>

  <div class="macro-grid">
    <div class="macro-card mc-cot">
      <div class="mc-hdr"><span class="mc-label">🐳 COT Non-Commercial</span>
        <span class="mc-sig" style="background:{sb(cot_sig)};border:1px solid {sbd(cot_sig)};color:{sg(cot_sig)}">{se(cot_sig)} {cot_sig}</span>
      </div>
      <div class="mc-main" style="color:{sg(cot_sig)}">{cot_net_str}</div>
      <div style="font-size:9px;color:var(--muted);margin-bottom:8px;font-family:'JetBrains Mono',monospace">COT Index: {cot_idx}/100 · Data: {cot_date}</div>
      <div class="mc-bar-w"><div class="mc-bar" style="width:{cot_idx}%;background:linear-gradient(90deg,{'#ef4444' if cot_idx<35 else '#f59e0b' if cot_idx<60 else '#10b981'},{sg(cot_sig)})"></div></div>
      <div class="mc-meta">
        <div><div class="mc-meta-k">Momentum</div><div class="mc-meta-v" style="color:{'#ef4444' if cot_dir=='BAJANDO' else '#10b981' if cot_dir=='SUBIENDO' else '#94a3b8'}">{cot_dir}</div></div>
        <div><div class="mc-meta-k">Semanas</div><div class="mc-meta-v cp">{cot_wks} consec.</div></div>
        <div><div class="mc-meta-k">Velocidad</div><div class="mc-meta-v" style="color:{'#ef4444' if cot_vel<0 else '#10b981'}">{cot_vel_str}</div></div>
      </div>
      {f'<div style="margin-top:10px;padding:7px 10px;border-radius:8px;font-size:10px;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.25);color:#fcd34d">⚡ {cot_alrt}</div>' if cot_alrt else ''}
    </div>
    <div class="macro-card mc-vol">
      <div class="mc-hdr"><span class="mc-label">🌡️ VXN — Volatilidad NQ</span>
        <span class="mc-sig" style="background:{sb(vol_sig)};border:1px solid {sbd(vol_sig)};color:{sg(vol_sig)}">{se(vol_sig)} {vol_sig}</span>
      </div>
      <div class="mc-main" style="color:{'#ef4444' if vxn_val>25 else '#f59e0b' if vxn_val>18 else '#10b981'}">{vxn_val:.2f}</div>
      <div style="font-size:9px;color:var(--muted);margin-bottom:8px;font-family:'JetBrains Mono',monospace">Score: {vol_scr}/100 · Nivel: {vxn_lbl}</div>
      <div class="mc-bar-w"><div class="mc-bar" style="width:{min(vxn_val/50*100,100):.1f}%;background:linear-gradient(90deg,#10b981,{'#ef4444' if vxn_val>25 else '#f59e0b'})"></div></div>
    </div>
    <div class="macro-card mc-gex">
      <div class="mc-hdr"><span class="mc-label">⚙️ GEX / DIX — Dealers</span>
        <span class="mc-sig" style="background:rgba({'16,185,129' if gex_b>0 else '239,68,68'},.15);border:1px solid rgba({'16,185,129' if gex_b>0 else '239,68,68'},.4);color:{'#10b981' if gex_b>0 else '#ef4444'}">{'▲ POSITIVO' if gex_b>0 else '▼ NEGATIVO'}</span>
      </div>
      <div class="mc-main" style="color:{'#10b981' if gex_b>0 else '#ef4444'}">{gex_str}</div>
      <div style="font-size:9px;color:var(--muted);margin-bottom:8px;font-family:'JetBrains Mono',monospace">GEX {'positivo → mercado amortiguado' if gex_b>0 else 'negativo → amplifica movimiento'}</div>
      <div class="mc-meta">
        <div><div class="mc-meta-k">DIX Dark Pool</div><div class="mc-meta-v" style="color:{'#10b981' if dix_val>42 else '#94a3b8'}">{dix_val:.1f}%</div></div>
        <div><div class="mc-meta-k">Interpretación</div><div class="mc-meta-v cc">{'Compra inst. ↑' if dix_val>45 else 'Neutral' if dix_val>38 else 'Presión bajista ↓'}</div></div>
      </div>
    </div>
    <div class="macro-card mc-ai">
      <div class="mc-hdr"><span class="mc-label">🤖 AI Score — Antigravity</span>
        <span class="mc-sig" style="background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.4);color:#a78bfa">{ai_label}</span>
      </div>
      <div class="mc-main" style="color:{ai_color}">{ai_score}/100</div>
      <div style="font-size:9px;color:var(--muted);margin-bottom:8px">COT+VXN+DIX+GEX · 11 agentes IA</div>
      <div class="mc-bar-w"><div class="mc-bar" style="width:{ai_score}%;background:linear-gradient(90deg,{ai_color}80,{ai_color})"></div></div>
    </div>
  </div>

  <div class="chart-wrap">
    <div class="chart-hdr">
      <span style="font-size:12px;font-weight:700;color:var(--muted)">NQ FUTURES — 5 MIN — {date_str} · {n} VELAS</span>
      <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace">
        <span style="color:rgba(255,255,255,.8)">VAH {VAH:,.2f}</span>
        <span style="color:#ef4444">POC {POC:,.2f}</span>
        <span style="color:rgba(255,255,255,.8)">VAL {VAL:,.2f}</span>
        <span style="color:#f59e0b">NY OPEN {NY_OPEN_P:,.2f}</span>
      </div>
      <button class="rl-btn" id="rlb" onclick="toggleRB()">⏪ REPLAY</button>
    </div>
    <div id="chart"></div>
    <div id="rb">
      <div class="rr">
        <button class="rb2" id="rpb" onclick="rpToggle()">▶ PLAY</button>
        <button class="rb2" style="background:rgba(255,0,85,.1);border-color:rgba(255,0,85,.3);color:#ff0055" onclick="rpReset()">⟲ Reset</button>
        <div class="spg">
          <button class="sp a" onclick="setSp(1,this)">1×</button>
          <button class="sp"   onclick="setSp(3,this)">3×</button>
          <button class="sp"   onclick="setSp(8,this)">8×</button>
          <button class="sp"   onclick="setSp(20,this)">20×</button>
          <button class="sp"   onclick="setSp(50,this)">50×</button>
        </div>
        <div class="rt" id="rtime">-- : --</div>
        <div class="rpw"><div class="rtr"><div class="rf" id="rfl" style="width:0%"></div><input type="range" class="rs" id="rscr" min="0" max="100" value="0" oninput="rpScrub(this.value)"></div></div>
      </div>
    </div>
  </div>
</div>
<div class="foot">NQ Whale Radar © 2026 · {filename} · {n} barras 5min · yfinance</div>

<script>
const POC={POC},VAH={VAH},VAL={VAL},NY_OPEN_P={NY_OPEN_P};
const ASIA_START={ASIA_START},LONDON={LONDON},NY_OPEN={NY_OPEN},NY_CLOSE={NY_CLOSE};
const candles={CJ};

const el=document.getElementById('chart');
const chart=LightweightCharts.createChart(el,{{
  width:el.offsetWidth,height:680,
  layout:{{background:{{color:'#08061a'}},textColor:'#64748b',fontSize:11,fontFamily:'JetBrains Mono,monospace'}},
  grid:{{vertLines:{{color:'rgba(124,58,237,0.06)'}},horzLines:{{color:'rgba(124,58,237,0.06)'}}}},
  crosshair:{{mode:LightweightCharts.CrosshairMode.Normal}},
  rightPriceScale:{{borderColor:'rgba(30,26,58,0.8)',scaleMargins:{{top:0.05,bottom:0.05}}}},
  timeScale:{{borderColor:'rgba(30,26,58,0.8)',timeVisible:true,secondsVisible:false,
    tickMarkFormatter:(t)=>{{const d=new Date(t*1000);const h=((d.getUTCHours()-4+24)%24);const m=d.getUTCMinutes();return m===0?h+':00':h+':'+(m+'').padStart(2,'0');}}}},
  handleScroll:{{mouseWheel:true}},handleScale:{{mouseWheel:true}}
}});
const ser=chart.addCandlestickSeries({{
  upColor:'rgba(16,185,129,0.08)',downColor:'rgba(139,92,246,0.08)',
  borderUpColor:'#10b981',borderDownColor:'#8b5cf6',wickUpColor:'#10b981',wickDownColor:'#8b5cf6',
  priceFormat:{{type:'price',precision:2,minMove:0.25}}
}});
ser.setData(candles);
ser.createPriceLine({{price:VAH,color:'rgba(255,255,255,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'VAH '+VAH.toLocaleString()}});
ser.createPriceLine({{price:POC,color:'#ef4444',lineWidth:2,lineStyle:0,axisLabelVisible:true,title:'POC '+POC.toLocaleString()}});
ser.createPriceLine({{price:VAL,color:'rgba(255,255,255,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'VAL '+VAL.toLocaleString()}});
ser.createPriceLine({{price:NY_OPEN_P,color:'rgba(245,158,11,0.85)',lineWidth:1,lineStyle:3,axisLabelVisible:true,title:'NY OPEN '+NY_OPEN_P.toLocaleString()}});
function sHL(from,to){{const s=candles.filter(c=>c.time>=from&&c.time<=to);return s.length?{{h:Math.max(...s.map(c=>c.high)),l:Math.min(...s.map(c=>c.low))}}:null}}
const aHL=sHL(ASIA_START,LONDON-1);
if(aHL){{ser.createPriceLine({{price:aHL.h,color:'rgba(6,182,212,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'ASIA H'}});ser.createPriceLine({{price:aHL.l,color:'rgba(6,182,212,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'ASIA L'}});}}
const lHL=sHL(LONDON,NY_OPEN-1);
if(lHL){{ser.createPriceLine({{price:lHL.h,color:'rgba(245,158,11,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'LON H'}});ser.createPriceLine({{price:lHL.l,color:'rgba(245,158,11,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'LON L'}});}}
function near(t){{return candles.reduce((b,c)=>Math.abs(c.time-t)<Math.abs(b.time-t)?c:b)}}
const mks=[{{time:candles[0].time,position:'belowBar',color:'#06b6d4',shape:'circle',text:'🌏 Asia'}}];
if(candles.some(c=>c.time>=LONDON))mks.push({{time:near(LONDON).time,position:'aboveBar',color:'#f59e0b',shape:'circle',text:'🇬🇧 London'}});
if(candles.some(c=>c.time>=NY_OPEN))mks.push({{time:near(NY_OPEN).time,position:'aboveBar',color:'#f59e0b',shape:'circle',text:'🔔 NY Open '+NY_OPEN_P.toLocaleString()}});
ser.setMarkers(mks);
chart.timeScale().fitContent();
window.addEventListener('resize',()=>chart.applyOptions({{width:el.offsetWidth}}));
let ri=0,rt=null,rs=1,rr=false;
function stg(t){{if(t<LONDON)return['🌏 ASIA','rgba(6,182,212,.15)','1px solid rgba(6,182,212,.3)','#67e8f9'];if(t<NY_OPEN)return['🇬🇧 LONDON','rgba(245,158,11,.15)','1px solid rgba(245,158,11,.3)','#fcd34d'];return['🗽 NY','rgba(16,185,129,.15)','1px solid rgba(16,185,129,.4)','#6ee7b7'];}}
function rpUI(i){{const pct=candles.length>1?(i/(candles.length-1)*100).toFixed(1):0;document.getElementById('rfl').style.width=pct+'%';document.getElementById('rscr').value=pct;const c=candles[i],d=new Date(c.time*1000);const h=((d.getUTCHours()-4+24)%24).toString().padStart(2,'0'),m=d.getUTCMinutes().toString().padStart(2,'0');document.getElementById('rtime').textContent='{day_es}  '+h+':'+m+' ET  C='+c.close.toLocaleString();}}
function rpTick(){{if(ri>=candles.length){{rpStop();return}}ser.setData(candles.slice(0,ri+1));rpUI(ri);chart.timeScale().scrollToRealTime();ri++;rt=setTimeout(rpTick,300/rs);}}
function rpToggle(){{if(rr)rpStop();else rpStart()}}
function rpStart(){{if(ri>=candles.length)rpReset();rr=true;document.getElementById('rpb').textContent='⏸ PAUSE';document.getElementById('rpb').classList.add('pause');rpTick()}}
function rpStop(){{rr=false;clearTimeout(rt);document.getElementById('rpb').textContent='▶ PLAY';document.getElementById('rpb').classList.remove('pause');if(ri>=candles.length)ser.setData(candles);}}
function rpReset(){{rpStop();ri=0;ser.setData(candles);document.getElementById('rfl').style.width='0%';document.getElementById('rscr').value=0;document.getElementById('rtime').textContent='-- : --';chart.timeScale().fitContent();}}
function rpScrub(v){{rpStop();ri=Math.round((v/100)*(candles.length-1));ser.setData(candles.slice(0,ri+1));rpUI(ri);}}
function setSp(s,b){{rs=s;document.querySelectorAll('.sp').forEach(x=>x.classList.remove('a'));b.classList.add('a');}}
function toggleRB(){{document.getElementById('rb').classList.toggle('v');document.getElementById('rlb').classList.toggle('a');}}
</script>
</body></html>"""

with open(filename, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\n✅ {filename} generado")
print(f"   Velas: {n} | POC={POC} | VAH={VAH} | VAL={VAL}")
print(f"   NY: Open={NY_OPEN_P} Range={NY_RANGE} pts | AI={ai_score}/100 ({ai_label})")
