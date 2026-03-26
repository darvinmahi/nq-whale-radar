#!/usr/bin/env python3
"""
UPDATE TODAY SESSION — NQ Whale Radar
═══════════════════════════════════════════════════
Auto-detecta el día actual (ET), descarga NQ=F en vivo,
genera el HTML del chart de hoy y actualiza el JSON histórico.

GitHub Actions lo corre cada 30 min durante el día de trading.
Al final del día, consolida la sesión en el backtest histórico.
"""
import yfinance as yf
import json
import math
import sys
import os
from datetime import datetime, date, timedelta, timezone
import pytz

# ──────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────
ET = pytz.timezone("America/New_York")
now_et = datetime.now(ET)
today_et = now_et.date()
weekday = today_et.weekday()  # 0=lunes, 4=viernes

DAY_NAMES = {0:'monday', 1:'tuesday', 2:'wednesday', 3:'thursday', 4:'friday'}
DAY_ES    = {0:'Lunes', 1:'Martes', 2:'Miércoles', 3:'Jueves', 4:'Viernes'}
DAY_JSON  = {
    0: 'data/research/backtest_monday_results.json',
    1: 'data/research/backtest_tuesday_results.json',
    2: 'data/research/backtest_wednesday_results.json',
    3: 'data/research/backtest_thursday_results.json',
    4: 'data/research/backtest_friday_results.json',
}
DAY_HTML_PREFIX = {
    0:'lunes', 1:'martes', 2:'miercoles', 3:'jueves', 4:'viernes'
}
DAY_SETUP = {
    0: "Lunes: Alta volatilidad pre-gap. VP Asia → NY open.",
    1: "Martes: Bear Trap + ICT LONG reversal 9:30–10:00 AM.",
    2: "Miércoles: FOMC risk. Spike 8:30 → trend rest of day.",
    3: "Jueves: Jobless Claims 8:30 spike + trampa bajista 80%.",
    4: "Viernes: Profit taking + rollover. Range compresión.",
}

if weekday > 4:
    print(f"  Hoy es fin de semana — no hay sesión de trading.")
    sys.exit(0)

day_name  = DAY_NAMES[weekday]
day_es    = DAY_ES[weekday]
day_json  = DAY_JSON[weekday]
html_pre  = DAY_HTML_PREFIX[weekday]
setup_txt = DAY_SETUP[weekday]
date_str  = today_et.strftime('%Y-%m-%d')

print(f"📅 Hoy: {day_es} {date_str} ({now_et.strftime('%H:%M')} ET)")

# ──────────────────────────────────────────────────────────────────────────────
#  DESCARGAR DATOS (período de 2 días para obtener premarket de hoy)
# ──────────────────────────────────────────────────────────────────────────────
# La sesión NQ para MIÉRCOLES empieza el MARTES 6PM ET (etc.)
# Para capturar premarket, descargar desde ayer
yesterday = (today_et - timedelta(days=1)).strftime('%Y-%m-%d')
tomorrow  = (today_et + timedelta(days=1)).strftime('%Y-%m-%d')

print(f"  Descargando NQ=F 5min ({yesterday} → {tomorrow})...")
df = yf.download("NQ=F", start=yesterday, end=tomorrow,
                 interval="5m", prepost=True, progress=False, auto_adjust=True)

if df.empty:
    print("  ERROR: yfinance no devolvió datos — probando MNQ=F...")
    df = yf.download("MNQ=F", start=yesterday, end=tomorrow,
                     interval="5m", prepost=True, progress=False, auto_adjust=True)

if df.empty:
    print("  ERROR: Sin datos de mercado disponibles.")
    sys.exit(1)

# Aplanar MultiIndex
if hasattr(df.columns, 'levels'):
    df.columns = df.columns.get_level_values(0)
df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"vol"})
df = df[["open","high","low","close"]].dropna()
df.index = df.index.tz_convert("UTC")

print(f"  Barras totales: {len(df)}")

# ──────────────────────────────────────────────────────────────────────────────
#  CALCULAR TIMESTAMPS DE SESIONES (UTC)
# ──────────────────────────────────────────────────────────────────────────────
# Offset EDT(verano) = UTC-4, EST(invierno) = UTC-5
# Usamos ET para calcular UTC correcto
def et_to_utc_ts(date_obj, hour, minute=0):
    """Convierte hora ET (auto-DST) a UTC unix timestamp."""
    dt_et = ET.localize(datetime(date_obj.year, date_obj.month, date_obj.day, hour, minute))
    return int(dt_et.astimezone(timezone.utc).timestamp())

# Asia empieza la noche anterior a las 6PM ET
prev_day = today_et - timedelta(days=1)
ASIA_START_UTC   = et_to_utc_ts(prev_day, 18, 0)   # Día anterior 6PM ET
LONDON_START_UTC = et_to_utc_ts(today_et,  2, 0)   # Hoy 2AM ET
NY_OPEN_UTC      = et_to_utc_ts(today_et,  9, 30)  # Hoy 9:30AM ET
NY_CLOSE_UTC     = et_to_utc_ts(today_et, 16, 0)   # Hoy 4PM ET

# Filtrar barras relevantes: desde Asia START hasta ahora (o cierre)
now_utc_ts = int(datetime.now(timezone.utc).timestamp())
end_ts = min(now_utc_ts, NY_CLOSE_UTC)

df_filtered = df[(df.index.map(lambda x: int(x.timestamp())) >= ASIA_START_UTC) &
                 (df.index.map(lambda x: int(x.timestamp())) <= end_ts)]

print(f"  Barras de sesión de hoy: {len(df_filtered)}")

if len(df_filtered) < 3:
    print("  No hay suficientes datos de sesión. Saliendo.")
    sys.exit(0)

# ──────────────────────────────────────────────────────────────────────────────
#  CONSTRUIR CANDLES JSON
# ──────────────────────────────────────────────────────────────────────────────
candles = []
for ts, row in df_filtered.iterrows():
    candles.append({
        "time": int(ts.timestamp()),
        "open":  round(float(row["open"]),  2),
        "high":  round(float(row["high"]),  2),
        "low":   round(float(row["low"]),   2),
        "close": round(float(row["close"]), 2),
    })

# ──────────────────────────────────────────────────────────────────────────────
#  CALCULAR ESTADÍSTICAS
# ──────────────────────────────────────────────────────────────────────────────
DAY_HIGH = max(c["high"] for c in candles)
DAY_LOW  = min(c["low"]  for c in candles)

# NY session (lo que hay hasta ahora)
ny_candles = [c for c in candles if NY_OPEN_UTC <= c["time"] <= end_ts]
pre_ny     = [c for c in candles if c["time"] < NY_OPEN_UTC]

# Cerró o sigue abierto?
session_closed = now_utc_ts >= NY_CLOSE_UTC
status_badge   = "✅ SESIÓN CERRADA" if session_closed else f"🔴 LIVE · {now_et.strftime('%H:%M')} ET"

if ny_candles:
    NY_OPEN_P  = ny_candles[0]["open"]
    NY_CLOSE_P = ny_candles[-1]["close"]
    NY_HIGH    = max(c["high"] for c in ny_candles)
    NY_LOW     = min(c["low"]  for c in ny_candles)
    NY_RANGE   = round(NY_HIGH - NY_LOW, 2)
    NY_MOVE    = round(NY_CLOSE_P - NY_OPEN_P, 2)
else:
    # Antes de NY Open — usar precio actual
    NY_OPEN_P = NY_CLOSE_P = candles[-1]["close"]
    NY_HIGH = NY_LOW = NY_RANGE = NY_MOVE = 0

# Volume Profile pre-NY (Asia + London)
if pre_ny:
    price_min = min(c["low"]  for c in pre_ny)
    price_max = max(c["high"] for c in pre_ny)
    bucket_size = 25.0
    n_buckets = max(1, int((price_max - price_min) / bucket_size) + 1)
    vp = [0.0] * n_buckets
    for c in pre_ny:
        lo_i = max(0, int((c["low"]  - price_min) / bucket_size))
        hi_i = min(n_buckets-1, int((c["high"] - price_min) / bucket_size))
        for i in range(lo_i, hi_i+1):
            vp[i] += 1
    poc_i = vp.index(max(vp))
    POC = round(price_min + poc_i * bucket_size + bucket_size/2, 2)
    total_vol = sum(vp); target_vol = total_vol * 0.70
    lo_i = hi_i = poc_i; acc = vp[poc_i]
    while acc < target_vol:
        exp_lo = lo_i > 0; exp_hi = hi_i < n_buckets - 1
        if exp_lo and exp_hi:
            if vp[lo_i-1] >= vp[hi_i+1]: lo_i -= 1; acc += vp[lo_i]
            else: hi_i += 1; acc += vp[hi_i]
        elif exp_lo: lo_i -= 1; acc += vp[lo_i]
        elif exp_hi: hi_i += 1; acc += vp[hi_i]
        else: break
    VAH = round(price_min + hi_i * bucket_size + bucket_size, 2)
    VAL = round(price_min + lo_i * bucket_size, 2)
else:
    POC = DAY_HIGH - (DAY_HIGH - DAY_LOW)*0.5
    VAH = DAY_HIGH - (DAY_HIGH - DAY_LOW)*0.25
    VAL = DAY_LOW  + (DAY_HIGH - DAY_LOW)*0.25

direction = "BULLISH" if NY_MOVE > 0 else ("BEARISH" if NY_MOVE < 0 else "NEUTRAL")
dir_color = "#10b981" if direction == "BULLISH" else ("#ef4444" if direction == "BEARISH" else "#f59e0b")
dir_emoji = "↑" if direction == "BULLISH" else ("↓" if direction == "BEARISH" else "→")
move_sign = "+" if NY_MOVE > 0 else ""

n_candles = len(candles)
CANDLES_JSON = json.dumps(candles, separators=(',',':'))

print(f"  POC={POC}  VAH={VAH}  VAL={VAL}")
print(f"  NY Open={NY_OPEN_P}  Close={NY_CLOSE_P}  Range={NY_RANGE}  Move={NY_MOVE}")
print(f"  Dirección: {direction} | Estado: {status_badge}")

# ──────────────────────────────────────────────────────────────────────────────
#  GENERAR HTML DEL CHART
# ──────────────────────────────────────────────────────────────────────────────
date_display = today_et.strftime('%d de %B %Y').replace(
    'January','Enero').replace('February','Febrero').replace('March','Marzo').replace(
    'April','Abril').replace('May','Mayo').replace('June','Junio').replace(
    'July','Julio').replace('August','Agosto').replace('September','Septiembre').replace(
    'October','Octubre').replace('November','Noviembre').replace('December','Diciembre')

live_label = "" if session_closed else f"""
<div style="display:flex;align-items:center;gap:8px;background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.4);padding:6px 14px;border-radius:20px">
  <span style="width:8px;height:8px;background:#ef4444;border-radius:50%;animation:pulse 1.2s ease-in-out infinite"></span>
  <span style="color:#fca5a5;font-size:12px;font-weight:700">LIVE · {now_et.strftime('%H:%M')} ET</span>
</div>
"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="{"" if session_closed else "120"}">
  <title>NQ — {day_es} {date_str} | {"LIVE" if not session_closed else "CERRADO"}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      --bg:#04020c; --card:#0c0a1e; --border:#1e1a3a;
      --purple:#7c3aed; --cyan:#06b6d4; --green:#10b981;
      --red:#ef4444; --amber:#f59e0b; --gray:#64748b;
      --text:#e2e8f0; --muted:#94a3b8;
      --bull:#10b981; --bear:#ef4444;
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}}
    .mono{{font-family:'JetBrains Mono',monospace}}
    @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.5;transform:scale(1.2)}}}}

    .top-bar{{background:linear-gradient(135deg,#0c0a1e,#110d2a);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}}
    .logo-badge{{background:linear-gradient(135deg,var(--purple),#4f46e5);color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:1px;}}
    .back-btn{{background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.35);color:#a78bfa;font-size:13px;font-weight:600;padding:7px 16px;border-radius:8px;cursor:pointer;text-decoration:none;transition:all .2s;}}
    .back-btn:hover{{background:rgba(124,58,237,.28)}}

    .page{{max-width:1500px;margin:0 auto;padding:20px 18px}}

    .date-header{{background:linear-gradient(135deg,#0c0a1e,#130f2a);border:1px solid var(--border);border-radius:16px;padding:18px 24px;position:relative;overflow:hidden;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;}}
    .date-header::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#f59e0b,var(--green),var(--cyan),var(--purple));}}

    .stats-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-bottom:16px;}}
    .stat-card{{background:linear-gradient(135deg,#0c0a1e,#130f2a);border:1px solid var(--border);border-radius:12px;padding:12px 14px;text-align:center;transition:border-color .2s;}}
    .stat-card:hover{{border-color:rgba(124,58,237,.4);}}
    .stat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .stat-value{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700}}
    .c-green{{color:var(--green)}} .c-red{{color:var(--red)}} .c-cyan{{color:var(--cyan)}}
    .c-amber{{color:var(--amber)}} .c-purple{{color:#a78bfa}} .c-gray{{color:var(--muted)}}
    .c-bull{{color:var(--bull)}} .c-bear{{color:var(--bear)}}

    .setup-box{{background:linear-gradient(135deg,rgba(245,158,11,.08),rgba(124,58,237,.08));border:1px solid rgba(245,158,11,.3);border-radius:14px;padding:16px 20px;margin-bottom:16px;}}
    .setup-title{{font-size:11px;font-weight:700;color:#fcd34d;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;}}
    .setup-text{{font-size:13px;color:var(--muted);line-height:1.7}}

    .chart-section-label{{display:flex;align-items:center;gap:10px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;padding-left:4px;}}
    .chart-section-label::before{{content:'';display:block;width:3px;height:14px;border-radius:2px;background:linear-gradient(180deg,var(--purple),var(--cyan));}}

    .chart-frame{{background:linear-gradient(135deg,#09071a,#0e0b24);border:2px solid transparent;border-radius:20px;padding:3px;position:relative;margin-bottom:20px;box-shadow:0 0 0 1px rgba(124,58,237,0.35),0 20px 60px rgba(0,0,0,0.7);}}
    .chart-wrap{{background:linear-gradient(180deg,#0c0a1e,#08061a);border:1px solid var(--border);border-radius:16px;overflow:hidden;position:relative;}}
    .chart-top{{padding:14px 20px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,#0c0a1e,#110d2a);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}}
    .chart-title{{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.5px}}
    .leg-row{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
    .leg-i{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace}}
    .leg-dash{{width:18px;height:0;border-top:2px dashed}}
    #chart{{width:100%;height:680px}}
    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}
  </style>
</head>
<body>

<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">{date_str} · {day_es.upper()} · 5 MIN</span>
    <div style="background:rgba(16,185,129,.18);border:1px solid rgba(16,185,129,.45);color:#6ee7b7;font-size:11px;font-weight:700;padding:4px 12px;border-radius:6px">✅ DATOS REALES NQ=F</div>
  </div>
  <a href="index.html" class="back-btn">← Panel Principal</a>
</div>

<div class="page">

  <div class="date-header">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px">📅 {day_es} {date_display} — Sesión NQ Futures</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia (6PM ET {DAY_ES.get(weekday-1 if weekday>0 else 6, 'Dom')}) → 🇬🇧 London 2AM → 🗽 NY Open 9:30AM → 🏁 Cierre 4PM ET</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      {live_label}
      <span style="background:rgba({('16,185,129' if direction=='BULLISH' else ('239,68,68' if direction=='BEARISH' else '245,158,11'))},.15);border:1px solid rgba({('16,185,129' if direction=='BULLISH' else ('239,68,68' if direction=='BEARISH' else '245,158,11'))},.4);color:{dir_color};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700">{dir_emoji} {direction}</span>
    </div>
  </div>

  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">Day High</div><div class="stat-value c-cyan">{DAY_HIGH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Day Low</div><div class="stat-value c-bear">{DAY_LOW:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">POC Pre-NY</div><div class="stat-value c-purple">{POC:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAH</div><div class="stat-value c-cyan">{VAH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAL</div><div class="stat-value c-green">{VAL:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Open</div><div class="stat-value c-amber">{NY_OPEN_P:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Low</div><div class="stat-value c-bear">{NY_LOW:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY High</div><div class="stat-value c-bull">{NY_HIGH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY {"Close" if session_closed else "Precio"}</div><div class="stat-value c-{'bull' if NY_MOVE>0 else ('bear' if NY_MOVE<0 else 'amber')}">{NY_CLOSE_P:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Range</div><div class="stat-value c-amber">{NY_RANGE:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Move O→C</div><div class="stat-value c-{'bull' if NY_MOVE>0 else ('bear' if NY_MOVE<0 else 'amber')}">{move_sign}{NY_MOVE:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Velas</div><div class="stat-value c-gray">{n_candles}</div></div>
  </div>

  <div class="setup-box">
    <div class="setup-title">🎯 Setup del {day_es}</div>
    <div class="setup-text">{setup_txt}</div>
  </div>

  <div class="chart-section-label">📊 Chart — 5 Min · {day_es} {date_str} {"(CERRADO)" if session_closed else "(EN VIVO · auto-refresh 2min)"}</div>
  <div class="chart-frame">
  <div class="chart-wrap">
    <div class="chart-top">
      <span class="chart-title">NQ FUTURES — 5 MIN — {date_str} {day_es.upper()} · {n_candles} VELAS (NQ=F via yfinance)</span>
      <div class="leg-row">
        <div class="leg-i"><div class="leg-dash" style="border-color:#06b6d4"></div>VAH {VAH:,.2f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#7c3aed"></div>POC {POC:,.2f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#10b981"></div>VAL {VAL:,.2f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#f59e0b"></div>NY OPEN {NY_OPEN_P:,.2f}</div>
      </div>
    </div>
    <div id="chart"></div>
  </div>
  </div>

</div>

<div class="foot">NQ Whale Radar © 2026 · {date_str} · {day_es} · {n_candles} barras 5min · NQ=F via yfinance · Actualizado: {now_et.strftime('%H:%M')} ET</div>

<script>
const POC       = {POC};
const VAH       = {VAH};
const VAL       = {VAL};
const NY_OPEN_P = {NY_OPEN_P};
const ASIA_START_UTC   = {ASIA_START_UTC};
const LONDON_START_UTC = {LONDON_START_UTC};
const NY_OPEN_UTC      = {NY_OPEN_UTC};
const NY_CLOSE_UTC     = {NY_CLOSE_UTC};
const candles = {CANDLES_JSON};

const chartEl = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartEl, {{
  width: chartEl.offsetWidth, height: 680,
  layout: {{ background: {{ color: '#08061a' }}, textColor: '#64748b', fontSize: 11, fontFamily: 'JetBrains Mono, monospace' }},
  grid: {{ vertLines: {{ color: 'rgba(124,58,237,0.06)' }}, horzLines: {{ color: 'rgba(124,58,237,0.06)' }} }},
  crosshair: {{ mode: LightweightCharts.CrosshairMode.Normal, vertLine: {{ color: 'rgba(6,182,212,0.5)', width: 1, style: 2 }}, horzLine: {{ color: 'rgba(6,182,212,0.5)', width: 1, style: 2 }} }},
  rightPriceScale: {{ borderColor: 'rgba(30,26,58,0.8)', textColor: '#64748b', scaleMargins: {{ top: 0.05, bottom: 0.05 }} }},
  timeScale: {{
    borderColor: 'rgba(30,26,58,0.8)', timeVisible: true, secondsVisible: false,
    tickMarkFormatter: (t) => {{
      const d = new Date(t*1000), h=((d.getUTCHours()-4+24)%24), m=d.getUTCMinutes();
      return m===0 ? `${{h}}:00` : `${{h}}:${{m.toString().padStart(2,'0')}}`;
    }},
  }},
  handleScroll: {{ mouseWheel:true, pressedMouseMove:true }},
  handleScale:  {{ mouseWheel:true, pinch:true }},
}});

const series = chart.addCandlestickSeries({{
  upColor:'rgba(16,185,129,0.08)', downColor:'rgba(139,92,246,0.08)',
  borderUpColor:'#10b981', borderDownColor:'#8b5cf6',
  wickUpColor:'#10b981', wickDownColor:'#8b5cf6',
  borderVisible:true, wickVisible:true,
  priceFormat: {{ type:'price', precision:2, minMove:0.25 }},
}});
series.setData(candles);

// Price lines
series.createPriceLine({{ price:VAH,      color:'rgba(0,255,128,0.6)',   lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`VAH ${{VAH.toLocaleString()}}` }});
series.createPriceLine({{ price:POC,      color:'#00ff80',               lineWidth:2, lineStyle:0, axisLabelVisible:true, title:`POC ${{POC.toLocaleString()}}` }});
series.createPriceLine({{ price:VAL,      color:'rgba(0,255,128,0.6)',   lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`VAL ${{VAL.toLocaleString()}}` }});
series.createPriceLine({{ price:NY_OPEN_P, color:'rgba(245,158,11,0.8)', lineWidth:1, lineStyle:3, axisLabelVisible:true, title:`NY OPEN ${{NY_OPEN_P.toLocaleString()}}` }});

// Session banners
const topPrice = Math.max(...candles.map(c=>c.high)) + 300;
function addBand(s,e,tc,bc) {{
  const b = chart.addAreaSeries({{ topColor:tc, bottomColor:bc, lineColor:'rgba(0,0,0,0)', crosshairMarkerVisible:false }});
  b.setData([{{time:s,value:topPrice}},{{time:e,value:topPrice}}]);
}}
addBand(ASIA_START_UTC,   LONDON_START_UTC, 'rgba(6,182,212,0.10)',  'rgba(6,182,212,0.03)');
addBand(LONDON_START_UTC, NY_OPEN_UTC,      'rgba(245,158,11,0.10)', 'rgba(245,158,11,0.03)');
addBand(NY_OPEN_UTC,      NY_CLOSE_UTC,     'rgba(0,255,128,0.08)',  'rgba(0,255,128,0.02)');

// Session H/L
function shL(from,to) {{
  const s=candles.filter(c=>c.time>=from&&c.time<=to);
  return s.length?{{h:Math.max(...s.map(c=>c.high)),l:Math.min(...s.map(c=>c.low))}}:null;
}}
const aHL=shL(ASIA_START_UTC, LONDON_START_UTC-1);
if(aHL) {{
  series.createPriceLine({{price:aHL.h,color:'rgba(6,182,212,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`ASIA H`}});
  series.createPriceLine({{price:aHL.l,color:'rgba(6,182,212,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`ASIA L`}});
}}
const lHL=shL(LONDON_START_UTC, NY_OPEN_UTC-1);
if(lHL) {{
  series.createPriceLine({{price:lHL.h,color:'rgba(245,158,11,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`LON H`}});
  series.createPriceLine({{price:lHL.l,color:'rgba(245,158,11,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`LON L`}});
}}
const nyHL=shL(NY_OPEN_UTC, NY_CLOSE_UTC);
if(nyHL) {{
  series.createPriceLine({{price:nyHL.h,color:'rgba(0,255,128,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`NY H`}});
  series.createPriceLine({{price:nyHL.l,color:'rgba(0,255,128,0.9)',lineWidth:1,lineStyle:2,axisLabelVisible:true,title:`NY L`}});
}}

chart.timeScale().fitContent();
window.addEventListener('resize', ()=>chart.applyOptions({{width:chartEl.offsetWidth}}));
</script>

</body>
</html>"""

# ──────────────────────────────────────────────────────────────────────────────
#  GUARDAR HTML
# ──────────────────────────────────────────────────────────────────────────────
html_filename = f"{html_pre}_chart_{date_str.replace('-','')}.html"
with open(html_filename, "w", encoding="utf-8") as f:
    f.write(html)
print(f"  ✅ HTML generado: {html_filename}")

# ──────────────────────────────────────────────────────────────────────────────
#  ACTUALIZAR JSON HISTÓRICO (solo si la sesión cerró o tenemos datos NY)
# ──────────────────────────────────────────────────────────────────────────────
if not ny_candles:
    print("  ⏭ Aún no abrió NY — no se actualiza el JSON histórico.")
elif not session_closed:
    print("  ⏳ Sesión en curso — JSON histórico se actualiza al cierre.")
else:
    # Sesión cerrada — agregar o actualizar entrada de hoy en el JSON
    if not os.path.exists(day_json):
        print(f"  ⚠ JSON {day_json} no existe — creando desde cero.")
        os.makedirs(os.path.dirname(day_json), exist_ok=True)
        existing = {"total_sessions": 0, "sessions": [], "directions": {"BULLISH":0,"BEARISH":0,"NEUTRAL":0}}
    else:
        with open(day_json, 'r', encoding='utf-8') as f:
            existing = json.load(f)

    # Clave estándar para la key de sesiones
    sess_key = 'sessions'
    for k in ['all_mondays','all_tuesdays','all_wednesdays','all_thursdays','all_fridays']:
        if k in existing:
            sess_key = k
            break

    sessions = existing.get(sess_key, existing.get('sessions', []))

    # Buscar si ya existe la sesión de hoy
    today_str = date_str
    existing_idx = None
    for i, s in enumerate(sessions):
        if s.get('date','') == today_str:
            existing_idx = i
            break

    session_entry = {
        "date": today_str,
        "day":  day_es,
        "direction": direction,
        "ny_open":   NY_OPEN_P,
        "ny_close":  NY_CLOSE_P,
        "ny_high":   NY_HIGH,
        "ny_low":    NY_LOW,
        "ny_range":  NY_RANGE,
        "ny_move":   NY_MOVE,
        "poc":       POC,
        "vah":       VAH,
        "val":       VAL,
        "chart_url": html_filename,
    }

    if existing_idx is not None:
        sessions[existing_idx] = session_entry
        print(f"  🔄 Actualizada sesión {today_str} en el histórico.")
    else:
        sessions.append(session_entry)
        print(f"  ➕ Añadida nueva sesión {today_str} al histórico.")

    # Recalcular stats
    existing[sess_key] = sessions
    total_s = len(sessions)
    dirs    = {"BULLISH":0,"BEARISH":0,"NEUTRAL":0}
    for s in sessions:
        d = s.get('direction','NEUTRAL')
        dirs[d] = dirs.get(d, 0) + 1

    # Detectar la clave correcta de total para el día
    total_key = f"total_{day_name}s"
    existing[total_key]    = total_s
    existing['total_sessions'] = total_s
    existing['directions'] = dirs
    existing['updated_at'] = now_et.strftime('%Y-%m-%dT%H:%M:%S ET')

    with open(day_json, 'w', encoding='utf-8') as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"  ✅ JSON histórico actualizado: {day_json}")
    print(f"     Total sesiones: {total_s} | BULL:{dirs['BULLISH']} BEAR:{dirs['BEARISH']} NEU:{dirs['NEUTRAL']}")

# ──────────────────────────────────────────────────────────────────────────────
#  GENERAR today_chart.json para que el dashboard lo lea directamente
# ──────────────────────────────────────────────────────────────────────────────
today_live = {
    "date":      date_str,
    "day":       day_name,
    "day_es":    day_es,
    "status":    "closed" if session_closed else "live",
    "updated_at": now_et.strftime('%Y-%m-%dT%H:%M:%S'),
    "chart_url": html_filename,
    "direction": direction,
    "ny_open":   NY_OPEN_P,
    "ny_close":  NY_CLOSE_P,
    "ny_high":   NY_HIGH,
    "ny_low":    NY_LOW,
    "ny_range":  NY_RANGE,
    "ny_move":   NY_MOVE,
    "day_high":  DAY_HIGH,
    "day_low":   DAY_LOW,
    "poc":       POC,
    "vah":       VAH,
    "val":       VAL,
    "n_candles": n_candles,
}
with open("data/research/today_live.json", "w", encoding="utf-8") as f:
    json.dump(today_live, f, ensure_ascii=False, indent=2)

print(f"\n✅ DONE — {day_es} {date_str}")
print(f"   Chart: {html_filename}")
print(f"   Live:  data/research/today_live.json")
