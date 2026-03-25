#!/usr/bin/env python3
"""Genera lunes_chart_20260323.html — Lunes 23 Mar 2026 (HOY) — DATOS REALES NQ=F"""
import yfinance as yf, json, os
from datetime import datetime, timezone

DATE_LABEL = "2026-03-23"
DATE_NEXT  = "2026-03-24"
FILENAME   = "lunes_chart_20260323.html"

print(f"Descargando NQ=F 5min para {DATE_LABEL} (HOY)...")
df = yf.download("NQ=F", start=DATE_LABEL, end=DATE_NEXT,
                 interval="5m", prepost=True, progress=False)
if df.empty: raise SystemExit("ERROR: yfinance no devolvió datos.")
if hasattr(df.columns, 'levels'): df.columns = df.columns.get_level_values(0)
df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close"})
df = df[["open","high","low","close"]].dropna()
df.index = df.index.tz_convert("UTC")

candles = [{"time":int(ts.timestamp()),"open":round(float(r["open"]),2),
            "high":round(float(r["high"]),2),"low":round(float(r["low"]),2),
            "close":round(float(r["close"]),2)} for ts,r in df.iterrows()]

print(f"  Barras: {len(candles)} | Rango: {df.index[0]} → {df.index[-1]}")

ASIA_START  = int(datetime(2026,3,22,22,0,tzinfo=timezone.utc).timestamp())  # Domingo 6PM ET
LONDON      = int(datetime(2026,3,23, 6,0,tzinfo=timezone.utc).timestamp())  # 2AM ET
NY_OPEN     = int(datetime(2026,3,23,13,30,tzinfo=timezone.utc).timestamp()) # 9:30AM ET
NY_CLOSE    = int(datetime(2026,3,23,20,0,tzinfo=timezone.utc).timestamp())  # 4PM ET

ny  = [c for c in candles if NY_OPEN <= c["time"] <= NY_CLOSE]
all_c = candles

DAY_HIGH = max(c["high"] for c in candles)
DAY_LOW  = min(c["low"]  for c in candles)

NY_OPEN_P  = ny[0]["open"]  if ny else 0
NY_CLOSE_P = ny[-1]["close"] if ny else 0
NY_HIGH    = max(c["high"] for c in ny) if ny else 0
NY_LOW     = min(c["low"]  for c in ny) if ny else 0
NY_RANGE   = round(NY_HIGH - NY_LOW, 2)
NY_MOVE    = round(NY_CLOSE_P - NY_OPEN_P, 2)

# VP simple
pre_ny = [c for c in candles if c["time"] < NY_OPEN]
if pre_ny:
    pmin = min(c["low"] for c in pre_ny); pmax = max(c["high"] for c in pre_ny)
    B = 25.0; nb = max(1, int((pmax-pmin)/B)+1)
    vp = [0.0]*nb
    for c in pre_ny:
        for i in range(int((c["low"]-pmin)/B), min(int((c["high"]-pmin)/B)+1,nb)): vp[i]+=1
    pi = vp.index(max(vp)); POC = round(pmin+pi*B+B/2, 2)
    tv = sum(vp)*0.70; li=hi=pi; acc=vp[pi]
    while acc<tv:
        el=li>0; eh=hi<nb-1
        if el and eh:
            if vp[li-1]>=vp[hi+1]: li-=1; acc+=vp[li]
            else: hi+=1; acc+=vp[hi]
        elif el: li-=1; acc+=vp[li]
        elif eh: hi+=1; acc+=vp[hi]
        else: break
    VAH = round(pmin+hi*B+B, 2); VAL = round(pmin+li*B, 2)
else:
    mid = (DAY_HIGH+DAY_LOW)/2; POC=round(mid,2); VAH=round(mid+(DAY_HIGH-mid)*0.5,2); VAL=round(mid-(mid-DAY_LOW)*0.5,2)

print(f"  POC={POC} VAH={VAH} VAL={VAL}")
print(f"  NY: Open={NY_OPEN_P} High={NY_HIGH} Low={NY_LOW} Close={NY_CLOSE_P} Range={NY_RANGE}")

# ─── Leer datos COT (Agent 2) ─────────────────────────────────────────────────
def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

a2 = _load_json("agent2_data.json")
a3 = _load_json("agent3_data.json")

# COT
cot       = a2.get("cot", {})
cot_net   = cot.get("current_net", 0)
cot_idx   = cot.get("cot_index", 0)
cot_date  = cot.get("date", "N/A")
cot_sig   = a2.get("signal", "NEUTRAL")
cot_str   = a2.get("strength", 50)
cot_mom   = a2.get("momentum", {})
cot_dir   = cot_mom.get("direction", "PLANO")
cot_weeks = cot_mom.get("consecutive_weeks", 0)
cot_vel   = cot_mom.get("weekly_velocity", 0)
cot_alert = a2.get("insight", {}).get("alert", "")

# VXN / GEX / DIX
raw3      = a3.get("raw_inputs", {})
vxn_val   = raw3.get("VXN", 0)
gex_b     = raw3.get("GEX_B", 0)
dix_val   = raw3.get("DIX", 0)
vxn_ana   = a3.get("vxn_analysis", {})
vxn_lv    = vxn_ana.get("level", "NORMAL")
vol_sig   = a3.get("signal", "NEUTRAL")
vol_score = a3.get("score", 50)

# Helpers de color
def sig_color(s):
    return {"BULLISH":"#10b981","BEARISH":"#ef4444"}.get(s,"#94a3b8")
def sig_bg(s):
    return {"BULLISH":"rgba(16,185,129,.15)","BEARISH":"rgba(239,68,68,.15)"}.get(s,"rgba(148,163,184,.10)")
def sig_border(s):
    return {"BULLISH":"rgba(16,185,129,.4)","BEARISH":"rgba(239,68,68,.4)"}.get(s,"rgba(148,163,184,.3)")
def sig_emoji(s):
    return {"BULLISH":"▲","BEARISH":"▼"}.get(s,"●")

cot_net_str = f"+{cot_net:,}" if cot_net >= 0 else f"{cot_net:,}"
cot_vel_str = f"+{cot_vel:,}/sem" if cot_vel >= 0 else f"{cot_vel:,}/sem"
gex_str     = f"+{gex_b:.2f}B" if gex_b >= 0 else f"{gex_b:.2f}B"
vxn_lv_label = {"COMPLACENCY":"COMPLACENCIA","NORMAL":"NORMAL","ELEVATED":"ELEVADA","PANIC":"PÁNICO","EXTREME_PANIC":"PÁNICO EXTREMO"}.get(vxn_lv, vxn_lv)

print(f"  COT: net={cot_net_str} idx={cot_idx}/100 señal={cot_sig}")
print(f"  VXN: {vxn_val} | GEX: {gex_str} | DIX: {dix_val}%")

direction = "BULLISH ↑" if NY_MOVE>=0 else "BEARISH ↓"
dc = "#10b981" if NY_MOVE>=0 else "#ef4444"
ms = "+" if NY_MOVE>=0 else ""
n  = len(candles)
CJ = json.dumps(candles, separators=(',',':'))

# Determinar si mercado todavía abierto (ET = UTC-4)
now_utc = int(datetime.now(timezone.utc).timestamp())
market_open = now_utc < NY_CLOSE
live_badge = '🟢 EN VIVO' if market_open else '🏁 SESIÓN CERRADA'

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <title>NQ — Lunes 2026-03-23 HOY | DATOS REALES</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root{{--bg:#04020c;--card:#0c0a1e;--border:#1e1a3a;--purple:#7c3aed;--cyan:#06b6d4;
          --green:#10b981;--red:#ef4444;--amber:#f59e0b;--muted:#94a3b8;--text:#e2e8f0}}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}}
    .mono{{font-family:'JetBrains Mono',monospace}}
    .top-bar{{background:linear-gradient(135deg,#0c0a1e,#110d2a);border-bottom:1px solid var(--border);
              padding:14px 24px;display:flex;align-items:center;justify-content:space-between;
              position:sticky;top:0;z-index:100}}
    .logo-badge{{background:linear-gradient(135deg,var(--purple),#4f46e5);color:#fff;font-size:11px;
                 font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:1px}}
    .live-badge{{background:rgba({'16,185,129' if market_open else '239,68,68'},.2);border:1px solid rgba({'16,185,129' if market_open else '239,68,68'},.5);
                 color:{'#6ee7b7' if market_open else '#fca5a5'};font-size:12px;font-weight:700;padding:4px 12px;border-radius:20px}}
    .page{{max-width:1500px;margin:0 auto;padding:20px 18px}}
    .dh{{background:linear-gradient(135deg,#0c0a1e,#130f2a);border:1px solid var(--border);border-radius:16px;
         padding:18px 24px;position:relative;overflow:hidden;margin-bottom:16px;display:flex;
         align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}}
    .dh::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
                 background:linear-gradient(90deg,var(--amber),var(--green),var(--cyan),var(--purple))}}
    .stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px}}
    .sc{{background:linear-gradient(135deg,#0c0a1e,#130f2a);border:1px solid var(--border);border-radius:12px;
         padding:12px 14px;text-align:center}}
    .sl{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .sv{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700}}
    .cg{{color:#10b981}}.cr{{color:#ef4444}}.cc{{color:#06b6d4}}.ca{{color:#f59e0b}}.cp{{color:#a78bfa}}.cm{{color:var(--muted)}}
    .cf{{background:linear-gradient(135deg,#09071a,#0e0b24);border:2px solid transparent;border-radius:20px;padding:3px;
         margin-bottom:20px;box-shadow:0 0 0 1px rgba(124,58,237,0.35),0 0 0 3px rgba(6,182,212,0.12),0 20px 60px rgba(0,0,0,0.7)}}
    .cw{{background:linear-gradient(180deg,#0c0a1e 0%,#08061a 100%);border:1px solid var(--border);border-radius:16px;overflow:hidden}}
    .ct{{padding:14px 20px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,#0c0a1e,#110d2a);
         display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px}}
    .ctitle{{font-size:12px;font-weight:700;color:var(--muted)}}
    .lr{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
    .li{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace}}
    .ld{{width:18px;height:0;border-top:2px dashed}}
    #chart{{width:100%;height:680px}}
    /* REPLAY */
    #rb{{max-height:0;overflow:hidden;opacity:0;transition:max-height .35s,opacity .3s;
         background:rgba(6,182,212,.06);border-top:1px solid rgba(6,182,212,.18);border-radius:0 0 10px 10px}}
    #rb.v{{max-height:200px;opacity:1}}
    .rr{{display:flex;align-items:center;gap:10px;padding:10px 14px;flex-wrap:wrap}}
    .rb2{{background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9;
          font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:6px 14px;border-radius:8px;cursor:pointer;transition:all .2s}}
    .rb2:hover{{background:rgba(6,182,212,.28)}}
    .rb2.pause{{background:rgba(245,158,11,.15);border-color:rgba(245,158,11,.4);color:#fcd34d}}
    .spg{{display:flex;gap:3px}}
    .sp{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:var(--muted);font-size:10px;padding:4px 8px;border-radius:6px;cursor:pointer;transition:all .15s;font-family:'JetBrains Mono',monospace}}
    .sp.a{{background:rgba(6,182,212,.25);border-color:#06b6d4;color:#e0f2fe;font-weight:700}}
    .rt{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#67e8f9;min-width:160px;font-weight:600}}
    .rpw{{flex:1;min-width:120px}}
    .rtr{{position:relative;height:6px;background:rgba(255,255,255,.08);border-radius:3px}}
    .rf{{position:absolute;left:0;top:0;height:100%;background:linear-gradient(90deg,#06b6d4,#7c3aed);border-radius:3px;transition:width .15s}}
    .rs{{position:absolute;left:0;top:-5px;width:100%;height:16px;opacity:0;cursor:pointer;margin:0;-webkit-appearance:none;appearance:none}}
    #rn{{display:flex;align-items:flex-start;gap:10px;padding:8px 14px 10px;border-top:1px solid rgba(255,255,255,.04)}}
    .rl-btn{{background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.35);color:#67e8f9;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:6px 14px;border-radius:20px;cursor:pointer;transition:all .2s}}
    .rl-btn.a{{background:rgba(6,182,212,.25);border-color:#06b6d4;color:#e0f2fe}}
    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}
    /* ── MACRO INDICATORS ─────────────────────────────────────── */
    .macro-section{{margin-bottom:18px}}
    .macro-header{{display:flex;align-items:center;gap:10px;font-size:10px;font-weight:700;
                   color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;
                   margin-bottom:10px;padding-left:4px}}
    .macro-header::before{{content:'';display:block;width:3px;height:14px;border-radius:2px;
                           background:linear-gradient(180deg,var(--purple),var(--cyan))}}
    .macro-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}
    .macro-card{{background:linear-gradient(135deg,#0c0a1e,#110d2a);border:1px solid var(--border);
                 border-radius:14px;padding:16px 18px;position:relative;overflow:hidden;
                 transition:border-color .25s,transform .2s}}
    .macro-card:hover{{border-color:rgba(124,58,237,.45);transform:translateY(-1px)}}
    .macro-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
                          border-radius:2px 2px 0 0}}
    .mc-cot::before{{background:linear-gradient(90deg,#7c3aed,#06b6d4)}}
    .mc-vol::before{{background:linear-gradient(90deg,#f59e0b,#ef4444)}}
    .mc-gex::before{{background:linear-gradient(90deg,#10b981,#06b6d4)}}
    .macro-card-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}}
    .mc-label{{font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1.2px}}
    .mc-signal{{font-size:10px;font-weight:700;padding:3px 10px;border-radius:20px}}
    .mc-main{{display:flex;align-items:baseline;gap:8px;margin-bottom:10px}}
    .mc-value{{font-family:'JetBrains Mono',monospace;font-size:22px;font-weight:700}}
    .mc-unit{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted)}}
    .mc-bar-wrap{{background:rgba(255,255,255,.06);border-radius:4px;height:5px;margin-bottom:10px}}
    .mc-bar{{height:100%;border-radius:4px;transition:width .6s}}
    .mc-meta{{display:flex;gap:16px;flex-wrap:wrap}}
    .mc-meta-item{{display:flex;flex-direction:column;gap:2px}}
    .mc-meta-label{{font-size:8px;color:var(--muted);text-transform:uppercase;letter-spacing:.8px}}
    .mc-meta-val{{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:600}}
    .mc-alert{{margin-top:10px;padding:7px 10px;border-radius:8px;font-size:10px;
               background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.25);color:#fcd34d;
               line-height:1.5}}
  </style>
</head>
<body>
<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">2026-03-23 · LUNES HOY · 5 MIN</span>
    <div class="live-badge">{live_badge}</div>
  </div>
  <a href="index.html" style="background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.35);color:#a78bfa;font-size:13px;font-weight:600;padding:7px 16px;border-radius:8px;cursor:pointer;text-decoration:none">← Panel Principal</a>
</div>

<div class="page">
  <div class="dh">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px">📅 Lunes 23 de Marzo 2026 — HOY · NQ Futures Real</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia (Dom 6PM ET) → 🇬🇧 London 2AM → 🗽 NY Open 9:30AM → 🏁 Cierre 4PM ET</div>
    </div>
    <span style="background:rgba({'16,185,129' if NY_MOVE>=0 else '239,68,68'},.15);border:1px solid rgba({'16,185,129' if NY_MOVE>=0 else '239,68,68'},.4);color:{dc};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700">{direction}</span>
  </div>

  <div class="stats">
    <div class="sc"><div class="sl">Day High</div><div class="sv cc">{DAY_HIGH:,.2f}</div></div>
    <div class="sc"><div class="sl">Day Low</div><div class="sv cr">{DAY_LOW:,.2f}</div></div>
    <div class="sc"><div class="sl">POC Asia+Lon</div><div class="sv cp">{POC:,.2f}</div></div>
    <div class="sc"><div class="sl">VAH</div><div class="sv cc">{VAH:,.2f}</div></div>
    <div class="sc"><div class="sl">VAL</div><div class="sv cg">{VAL:,.2f}</div></div>
    <div class="sc"><div class="sl">NY Open</div><div class="sv ca">{NY_OPEN_P:,.2f}</div></div>
    <div class="sc"><div class="sl">NY High</div><div class="sv cg">{NY_HIGH:,.2f}</div></div>
    <div class="sc"><div class="sl">NY Low</div><div class="sv cr">{NY_LOW:,.2f}</div></div>
    <div class="sc"><div class="sl">NY Range</div><div class="sv ca">{NY_RANGE:,.2f}</div></div>
    <div class="sc"><div class="sl">Move O→C</div><div class="sv {'cg' if NY_MOVE>=0 else 'cr'}">{ms}{NY_MOVE:,.2f}</div></div>
    <div class="sc"><div class="sl">Velas</div><div class="sv cm">{n}</div></div>
    <div class="sc"><div class="sl">Dirección</div><div class="sv {'cg' if NY_MOVE>=0 else 'cr'}">{direction}</div></div>
  </div>

  <!-- ══ MACRO INDICATORS ══════════════════════════════════════════════════ -->
  <div class="macro-section">
    <div class="macro-header">📊 Indicadores Macro · COT / VXN / GEX / DIX — {cot_date}</div>
    <div class="macro-grid">

      <!-- COT Card -->
      <div class="macro-card mc-cot">
        <div class="macro-card-header">
          <span class="mc-label">🐳 COT Non-Commercial</span>
          <span class="mc-signal" style="background:{sig_bg(cot_sig)};border:1px solid {sig_border(cot_sig)};color:{sig_color(cot_sig)}">{sig_emoji(cot_sig)} {cot_sig}</span>
        </div>
        <div class="mc-main">
          <span class="mc-value" style="color:{sig_color(cot_sig)}">{cot_net_str}</span>
          <span class="mc-unit">contratos netos</span>
        </div>
        <div class="mc-bar-wrap"><div class="mc-bar" style="width:{cot_idx}%;background:linear-gradient(90deg,{'#ef4444' if cot_idx<35 else '#f59e0b' if cot_idx<60 else '#10b981'},{sig_color(cot_sig)})"></div></div>
        <div style="font-size:9px;color:var(--muted);margin-bottom:10px;font-family:'JetBrains Mono',monospace">COT Index: {cot_idx}/100 &nbsp;·&nbsp; Fuerza: {cot_str}/100</div>
        <div class="mc-meta">
          <div class="mc-meta-item"><span class="mc-meta-label">Momentum</span><span class="mc-meta-val" style="color:{'#ef4444' if cot_dir=='BAJANDO' else '#10b981' if cot_dir=='SUBIENDO' else '#94a3b8'}">{cot_dir}</span></div>
          <div class="mc-meta-item"><span class="mc-meta-label">Semanas</span><span class="mc-meta-val cp">{cot_weeks} consec.</span></div>
          <div class="mc-meta-item"><span class="mc-meta-label">Velocidad</span><span class="mc-meta-val" style="color:{'#ef4444' if cot_vel<0 else '#10b981'}">{cot_vel_str}</span></div>
        </div>
        {f'<div class="mc-alert">⚡ {cot_alert}</div>' if cot_alert else ''}
      </div>

      <!-- VXN Card -->
      <div class="macro-card mc-vol">
        <div class="macro-card-header">
          <span class="mc-label">🌡️ VXN — Volatilidad NQ</span>
          <span class="mc-signal" style="background:{sig_bg(vol_sig)};border:1px solid {sig_border(vol_sig)};color:{sig_color(vol_sig)}">{sig_emoji(vol_sig)} {vol_sig}</span>
        </div>
        <div class="mc-main">
          <span class="mc-value" style="color:{'#ef4444' if vxn_val>25 else '#f59e0b' if vxn_val>18 else '#10b981'}">{vxn_val:.2f}</span>
          <span class="mc-unit">puntos · {vxn_lv_label}</span>
        </div>
        <div class="mc-bar-wrap"><div class="mc-bar" style="width:{min(vxn_val/50*100,100):.1f}%;background:linear-gradient(90deg,#10b981,{'#ef4444' if vxn_val>25 else '#f59e0b'})"></div></div>
        <div style="font-size:9px;color:var(--muted);margin-bottom:10px;font-family:'JetBrains Mono',monospace">Score Volatilidad: {vol_score}/100 &nbsp;·&nbsp; Umbrales: &lt;18 Complacencia · 18–25 Normal · &gt;25 Elevada</div>
        <div class="mc-meta">
          <div class="mc-meta-item"><span class="mc-meta-label">Nivel</span><span class="mc-meta-val" style="color:{'#ef4444' if vxn_val>25 else '#f59e0b' if vxn_val>18 else '#10b981'}">{vxn_lv_label}</span></div>
          <div class="mc-meta-item"><span class="mc-meta-label">Score</span><span class="mc-meta-val cc">{vol_score}/100</span></div>
        </div>
      </div>

      <!-- GEX + DIX Card -->
      <div class="macro-card mc-gex">
        <div class="macro-card-header">
          <span class="mc-label">⚙️ GEX &amp; DIX — Dealers</span>
          <span class="mc-signal" style="background:rgba({'16,185,129' if gex_b>0 else '239,68,68'},.15);border:1px solid rgba({'16,185,129' if gex_b>0 else '239,68,68'},.4);color:{'#10b981' if gex_b>0 else '#ef4444'}">{'▲ POSITIVO' if gex_b>0 else '▼ NEGATIVO'}</span>
        </div>
        <div class="mc-main">
          <span class="mc-value" style="color:{'#10b981' if gex_b>0 else '#ef4444'}">{gex_str}</span>
          <span class="mc-unit">Gamma Exposure</span>
        </div>
        <div class="mc-bar-wrap"><div class="mc-bar" style="width:{min(abs(gex_b)/5*100,100):.1f}%;background:linear-gradient(90deg,{'#10b981,#06b6d4' if gex_b>0 else '#ef4444,#f59e0b'})"></div></div>
        <div style="font-size:9px;color:var(--muted);margin-bottom:10px;font-family:'JetBrains Mono',monospace">GEX {'positivo → dealers frenan vol · mercado amortiguado' if gex_b>0 else 'negativo → dealers amplifican movimiento'}</div>
        <div class="mc-meta">
          <div class="mc-meta-item"><span class="mc-meta-label">DIX (Dark Pool)</span><span class="mc-meta-val" style="color:{'#10b981' if dix_val>42 else '#94a3b8'}">{dix_val:.1f}%</span></div>
          <div class="mc-meta-item"><span class="mc-meta-label">Interpretación DIX</span><span class="mc-meta-val cc">{'Compra institucional ↑' if dix_val>45 else 'Neutral' if dix_val>38 else 'Presión bajista ↓'}</span></div>
        </div>
      </div>

    </div>
  </div>
  <!-- ═══════════════════════════════════════════════════════════════════════ -->

  <div class="cf"><div class="cw">
    <div class="ct">
      <span class="ctitle">NQ FUTURES — 5 MIN — 2026-03-23 · {n} VELAS REALES · yfinance</span>
      <div class="lr">
        <div class="li"><div class="ld" style="border-color:#ffffff"></div>VAH {VAH:,.2f}</div>
        <div class="li"><div class="ld" style="border-color:#ef4444"></div>POC {POC:,.2f}</div>
        <div class="li"><div class="ld" style="border-color:#ffffff"></div>VAL {VAL:,.2f}</div>
        <div class="li"><div class="ld" style="border-color:#f59e0b"></div>NY OPEN {NY_OPEN_P:,.2f}</div>
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
      <div id="rn">
        <span id="rbg" style="font-size:10px;font-weight:700;padding:3px 8px;border-radius:12px;background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9;font-family:'JetBrains Mono',monospace">🌏 ASIA</span>
        <div id="rnt" style="font-size:11px;color:var(--muted);line-height:1.6;flex:1">Presiona PLAY para replay del Lunes 23 Mar 2026</div>
      </div>
    </div>
  </div></div>
</div>
<div class="foot">NQ Whale Radar © 2026 · NQ=F yfinance · {n} barras 5min · lunes_chart_20260323.html</div>

<script>
const POC={POC},VAH={VAH},VAL={VAL},NY_OPEN_P={NY_OPEN_P};
const ASIA_START={ASIA_START},LONDON={LONDON},NY_OPEN={NY_OPEN},NY_CLOSE={NY_CLOSE};
const candles={CJ};

const el=document.getElementById('chart');
const chart=LightweightCharts.createChart(el,{{
  width:el.offsetWidth,height:680,
  layout:{{background:{{color:'#08061a'}},textColor:'#64748b',fontSize:11,fontFamily:'JetBrains Mono,monospace'}},
  grid:{{vertLines:{{color:'rgba(124,58,237,0.06)'}},horzLines:{{color:'rgba(124,58,237,0.06)'}}}},
  crosshair:{{mode:LightweightCharts.CrosshairMode.Normal,vertLine:{{color:'rgba(6,182,212,0.5)',width:1,style:2}},horzLine:{{color:'rgba(6,182,212,0.5)',width:1,style:2}}}},
  rightPriceScale:{{borderColor:'rgba(30,26,58,0.8)',textColor:'#64748b',scaleMargins:{{top:0.05,bottom:0.05}}}},
  timeScale:{{borderColor:'rgba(30,26,58,0.8)',timeVisible:true,secondsVisible:false,
    tickMarkFormatter:(t)=>{{const d=new Date(t*1000);const h=((d.getUTCHours()-4+24)%24);const m=d.getUTCMinutes();return m===0?h+':00':h+':'+(m+'').padStart(2,'0');}}}},
  handleScroll:{{mouseWheel:true,pressedMouseMove:true}},handleScale:{{mouseWheel:true,pinch:true}}
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

// Session H/L
function sHL(from,to){{const s=candles.filter(c=>c.time>=from&&c.time<=to);return s.length?{{h:Math.max(...s.map(c=>c.high)),l:Math.min(...s.map(c=>c.low))}}:null}}
const aHL=sHL(ASIA_START,LONDON-1);
if(aHL){{
  ser.createPriceLine({{price:aHL.h,color:'rgba(6,182,212,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'ASIA H '+aHL.h.toLocaleString()}});
  ser.createPriceLine({{price:aHL.l,color:'rgba(6,182,212,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'ASIA L '+aHL.l.toLocaleString()}});
}}
const lHL=sHL(LONDON,NY_OPEN-1);
if(lHL){{
  ser.createPriceLine({{price:lHL.h,color:'rgba(245,158,11,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'LON H '+lHL.h.toLocaleString()}});
  ser.createPriceLine({{price:lHL.l,color:'rgba(245,158,11,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'LON L '+lHL.l.toLocaleString()}});
}}
const nHL=sHL(NY_OPEN,NY_CLOSE);
if(nHL){{
  ser.createPriceLine({{price:nHL.h,color:'rgba(0,255,128,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'NY H '+nHL.h.toLocaleString()}});
  ser.createPriceLine({{price:nHL.l,color:'rgba(0,255,128,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:'NY L '+nHL.l.toLocaleString()}});
}}

function near(t){{return candles.reduce((b,c)=>Math.abs(c.time-t)<Math.abs(b.time-t)?c:b)}}
const lonC=near(LONDON),nyC=near(NY_OPEN);
const mks=[{{time:candles[0].time,position:'belowBar',color:'#06b6d4',shape:'circle',text:'🌏 Asia Domingo 6PM'}},
           {{time:lonC.time,position:'aboveBar',color:'#f59e0b',shape:'circle',text:'🇬🇧 London 2AM'}},
           {{time:nyC.time,position:'aboveBar',color:'#f59e0b',shape:'circle',text:'🔔 NY Open '+NY_OPEN_P.toLocaleString()}}];
if(nHL){{
  const nh=candles.filter(c=>c.time>=NY_OPEN&&c.time<=NY_CLOSE).reduce((a,b)=>b.high>a.high?b:a,candles[0]);
  const nl=candles.filter(c=>c.time>=NY_OPEN&&c.time<=NY_CLOSE).reduce((a,b)=>b.low<a.low?b:a,candles[candles.length-1]);
  mks.push({{time:nh.time,position:'aboveBar',color:'#10b981',shape:'arrowUp',text:'↑ High '+nh.high.toLocaleString()}});
  mks.push({{time:nl.time,position:'belowBar',color:'#ef4444',shape:'arrowDown',text:'↓ Low '+nl.low.toLocaleString()}});
}}
ser.setMarkers(mks);
chart.timeScale().fitContent();
window.addEventListener('resize',()=>chart.applyOptions({{width:el.offsetWidth}}));

// REPLAY
let ri=0,rt=null,rs=1,rr=false;
function stg(t){{
  if(t<LONDON) return['🌏 ASIA','rgba(6,182,212,.15)','1px solid rgba(6,182,212,.3)','#67e8f9'];
  if(t<NY_OPEN) return['🇬🇧 LONDON','rgba(245,158,11,.15)','1px solid rgba(245,158,11,.3)','#fcd34d'];
  return['🗽 NY','rgba(16,185,129,.15)','1px solid rgba(16,185,129,.4)','#6ee7b7'];
}}
function rpUI(i){{
  const pct=candles.length>1?(i/(candles.length-1)*100).toFixed(1):0;
  document.getElementById('rfl').style.width=pct+'%';
  document.getElementById('rscr').value=pct;
  const c=candles[i],d=new Date(c.time*1000);
  const h=((d.getUTCHours()-4+24)%24).toString().padStart(2,'0'),m=d.getUTCMinutes().toString().padStart(2,'0');
  document.getElementById('rtime').textContent='Mar 23  '+h+':'+m+' ET  C='+c.close.toLocaleString();
  const[lb,bg,bd,cl]=stg(c.time);
  const b=document.getElementById('rbg');b.textContent=lb;b.style.background=bg;b.style.border=bd;b.style.color=cl;
  document.getElementById('rnt').textContent=lb+' — '+h+':'+m+' ET · C='+c.close.toLocaleString()+' H='+c.high.toLocaleString()+' L='+c.low.toLocaleString();
}}
function rpTick(){{
  if(ri>=candles.length){{rpStop();return}}
  ser.setData(candles.slice(0,ri+1));rpUI(ri);
  chart.timeScale().scrollToRealTime();ri++;
  rt=setTimeout(rpTick,300/rs);
}}
function rpToggle(){{if(rr)rpStop();else rpStart()}}
function rpStart(){{if(ri>=candles.length)rpReset();rr=true;document.getElementById('rpb').textContent='⏸ PAUSE';document.getElementById('rpb').classList.add('pause');rpTick()}}
function rpStop(){{rr=false;clearTimeout(rt);document.getElementById('rpb').textContent='▶ PLAY';document.getElementById('rpb').classList.remove('pause');if(ri>=candles.length)ser.setData(candles)}}
function rpReset(){{rpStop();ri=0;ser.setData(candles);document.getElementById('rfl').style.width='0%';document.getElementById('rscr').value=0;document.getElementById('rtime').textContent='-- : --';chart.timeScale().fitContent()}}
function rpScrub(v){{rpStop();ri=Math.round((v/100)*(candles.length-1));ser.setData(candles.slice(0,ri+1));rpUI(ri)}}
function setSp(s,b){{rs=s;document.querySelectorAll('.sp').forEach(x=>x.classList.remove('a'));b.classList.add('a')}}
function toggleRB(){{document.getElementById('rb').classList.toggle('v');document.getElementById('rlb').classList.toggle('a')}}
</script>
</body></html>"""

with open(FILENAME,"w",encoding="utf-8") as f: f.write(html)
print(f"\n✅ {FILENAME}")
print(f"   Link: http://localhost:8765/{FILENAME}")
print(f"   Velas: {n} | POC={POC} | VAH={VAH} | VAL={VAL}")
print(f"   NY: Open={NY_OPEN_P} High={NY_HIGH} Low={NY_LOW} Close={NY_CLOSE_P} Range={NY_RANGE}")
