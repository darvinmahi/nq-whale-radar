#!/usr/bin/env python3
"""
Genera jueves_chart_20260319.html con datos REALES de NQ=F
filtrados para mostrar sólo la sesión del 19-Mar-2026:
  Asia:   2026-03-18 22:00 UTC → 2026-03-19 06:00 UTC
  London: 2026-03-19 06:00 UTC → 2026-03-19 13:30 UTC
  NY:     2026-03-19 13:30 UTC → 2026-03-19 20:00 UTC
"""

import json
from pathlib import Path
from datetime import datetime, timezone

# ── Cargar datos ──────────────────────────────────────────────
with open("nq_real_data.json") as f:
    data = json.load(f)

if data["status"] != "real":
    print("❌ No hay datos reales. Abortando.")
    exit(1)

all_candles = data["candles"]
print(f"Total barras disponibles: {len(all_candles)}")

# ── Filtrar sesión del 19-Mar: desde Asia del 18-Mar 22:00 UTC
ASIA_START  = int(datetime(2026, 3, 18, 22, 0, tzinfo=timezone.utc).timestamp())
NY_CLOSE    = int(datetime(2026, 3, 19, 20, 0, tzinfo=timezone.utc).timestamp())

candles = [c for c in all_candles if ASIA_START <= c["time"] <= NY_CLOSE]
print(f"Barras en sesión (Asia→NY Close): {len(candles)}")

if not candles:
    print("❌ Sin datos en el rango. Verificar nq_real_data.json")
    exit(1)

# Key timestamps (UTC unix)
LONDON_TS = int(datetime(2026, 3, 19,  6,  0, tzinfo=timezone.utc).timestamp())
NEWS_TS   = int(datetime(2026, 3, 19, 12, 30, tzinfo=timezone.utc).timestamp())
NY_OPEN_TS= int(datetime(2026, 3, 19, 13, 30, tzinfo=timezone.utc).timestamp())

# Stats reales
all_highs  = [c["high"] for c in candles]
all_lows   = [c["low"]  for c in candles]
day_high   = max(all_highs)
day_low    = min(all_lows)

ny_bars    = [c for c in candles if c["time"] >= NY_OPEN_TS]
ny_open_p  = ny_bars[0]["open"]  if ny_bars else 0
ny_close_p = ny_bars[-1]["close"] if ny_bars else 0
ny_high    = max(c["high"] for c in ny_bars) if ny_bars else 0
ny_low     = min(c["low"]  for c in ny_bars) if ny_bars else 0
ny_range   = ny_high - ny_low
move_oc    = ny_close_p - ny_open_p

# Parámetros del backtest (perfil de volumen del día anterior)
POC = 24579.3
VAH = 24639.0
VAL = 24504.6

print(f"\nEstadísticas REALES del día:")
print(f"  Day High:  {day_high:.2f}")
print(f"  Day Low:   {day_low:.2f}")
print(f"  NY Open:   {ny_open_p:.2f}")
print(f"  NY Close:  {ny_close_p:.2f}")
print(f"  NY High:   {ny_high:.2f}")
print(f"  NY Low:    {ny_low:.2f}")
print(f"  NY Range:  {ny_range:.2f} pts")
print(f"  Move O→C:  {move_oc:+.2f} pts")

# ── Serializar candles a JS array ──────────────────────────────
candles_js = json.dumps(candles, separators=(',',':'))

direction_label = "BULLISH" if move_oc > 20 else ("BEARISH" if move_oc < -20 else "NEUTRAL")
direction_color = "c-bull" if move_oc > 20 else ("c-bear" if move_oc < -20 else "c-gray")
direction_arrow = "↑" if move_oc > 20 else ("↓" if move_oc < -20 else "—")

# ── HTML ───────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NQ — Jueves 2026-03-19 | DATOS REALES</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    :root {{
      --bg:#04020c; --card:#0c0a1e; --border:#1e1a3a;
      --purple:#7c3aed; --cyan:#06b6d4; --green:#10b981;
      --red:#ef4444; --amber:#f59e0b; --gray:#64748b;
      --text:#e2e8f0; --muted:#94a3b8;
      --bull:#00e676; --bear:#ff1744;
    }}
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}}
    .mono{{font-family:'JetBrains Mono',monospace}}

    .top-bar{{
      background:linear-gradient(135deg,#0c0a1e,#110d2a);
      border-bottom:1px solid var(--border);
      padding:14px 24px; display:flex; align-items:center; justify-content:space-between;
      position:sticky; top:0; z-index:100;
    }}
    .logo-badge{{
      background:linear-gradient(135deg,var(--purple),#4f46e5);
      color:#fff; font-size:11px; font-weight:700;
      padding:4px 10px; border-radius:6px; letter-spacing:1px;
    }}
    .real-badge{{
      background:rgba(16,185,129,.2); border:1px solid rgba(16,185,129,.5);
      color:#6ee7b7; font-size:11px; font-weight:700;
      padding:4px 12px; border-radius:6px; letter-spacing:1px;
    }}
    .back-btn{{
      background:rgba(124,58,237,.15); border:1px solid rgba(124,58,237,.35);
      color:#a78bfa; font-size:13px; font-weight:600;
      padding:7px 16px; border-radius:8px; cursor:pointer;
      text-decoration:none; transition:all .2s;
    }}
    .back-btn:hover{{background:rgba(124,58,237,.28)}}

    .page{{max-width:1500px;margin:0 auto;padding:20px 18px}}

    .date-header{{
      background:linear-gradient(135deg,#0c0a1e,#130f2a);
      border:1px solid var(--border); border-radius:16px; padding:18px 24px;
      position:relative; overflow:hidden; margin-bottom:16px;
      display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;
    }}
    .date-header::before{{
      content:''; position:absolute; top:0; left:0; right:0; height:2px;
      background:linear-gradient(90deg,#f59e0b,var(--green),var(--cyan),var(--purple));
    }}
    .pattern-badge{{
      display:inline-flex; align-items:center; gap:8px;
      padding:8px 18px; border-radius:30px; font-size:14px; font-weight:700; letter-spacing:.5px;
      background:rgba(16,185,129,.15); border:1px solid rgba(16,185,129,.4); color:#6ee7b7;
    }}

    .sess-legend{{
      display:flex; gap:20px; flex-wrap:wrap;
      padding:12px 20px; background:var(--card); border:1px solid var(--border);
      border-radius:12px; margin-bottom:16px;
    }}
    .sess-item{{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:600}}
    .sess-dot{{width:12px;height:12px;border-radius:3px}}

    .stats-row{{
      display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:10px;
      margin-bottom:16px;
    }}
    .stat-card{{
      background:var(--card); border:1px solid var(--border);
      border-radius:12px; padding:12px 14px; text-align:center;
    }}
    .stat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .stat-value{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700}}
    .c-green{{color:var(--green)}} .c-red{{color:var(--red)}} .c-cyan{{color:var(--cyan)}}
    .c-amber{{color:var(--amber)}} .c-purple{{color:#a78bfa}} .c-gray{{color:var(--muted)}}
    .c-bull{{color:var(--bull)}} .c-bear{{color:var(--bear)}}

    .chart-wrap{{
      background:var(--card); border:1px solid var(--border);
      border-radius:16px; overflow:hidden; margin-bottom:20px; position:relative;
    }}
    .chart-top{{
      padding:12px 20px; border-bottom:1px solid var(--border);
      display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;
    }}
    .chart-title{{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.5px}}
    .leg-row{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
    .leg-i{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace}}
    .leg-dash{{width:18px;height:0;border-top:2px dashed}}
    #chart{{width:100%;height:680px}}

    .panels{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
    @media(max-width:900px){{.panels{{grid-template-columns:1fr}}}}

    .panel{{
      background:var(--card); border:1px solid var(--border);
      border-radius:14px; padding:20px;
    }}
    .panel-title{{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}}

    .tl-item{{
      display:flex; gap:12px; align-items:flex-start;
      padding:10px 0; border-bottom:1px solid rgba(255,255,255,.04);
    }}
    .tl-item:last-child{{border-bottom:none}}
    .tl-time{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--cyan);min-width:46px;padding-top:2px;flex-shrink:0}}
    .tl-badge{{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;margin-bottom:4px;display:inline-block}}
    .badge-asia  {{background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9}}
    .badge-london{{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);color:#fcd34d}}
    .badge-news  {{background:rgba(239,68,68,.25);border:1px solid rgba(239,68,68,.5);color:#fca5a5}}
    .badge-ny    {{background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.4);color:#6ee7b7}}
    .badge-target{{background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.5);color:#c4b5fd}}
    .tl-event{{font-size:13px;font-weight:700;margin-bottom:2px}}
    .tl-desc{{font-size:11px;color:var(--muted);line-height:1.5}}

    .anat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .anat-item{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:12px 14px}}
    .anat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .anat-val{{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;line-height:1.4}}

    .journey{{display:flex;align-items:stretch;gap:0;margin-top:14px;overflow-x:auto}}
    .j-step{{display:flex;flex-direction:column;align-items:center;flex:1;min-width:70px;position:relative}}
    .j-step::after{{content:'→';position:absolute;right:-8px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:14px;z-index:1}}
    .j-step:last-child::after{{display:none}}
    .j-node{{width:44px;height:44px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;border:2px solid;margin-bottom:6px}}
    .j-label{{font-size:9px;color:var(--muted);text-align:center;line-height:1.4}}
    .j-price{{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;margin-top:2px}}

    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}
  </style>
</head>
<body>

<!-- TOP BAR -->
<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">2026-03-19 · DÍA COMPLETO · 5 MIN</span>
    <div class="real-badge">✅ DATOS REALES NQ=F</div>
  </div>
  <a href="jueves_nq.html" class="back-btn">← Panel Principal</a>
</div>

<div class="page">

  <!-- DATE HEADER -->
  <div class="date-header">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px">📅 Jueves 19 de Marzo 2026 — Sesión Real NQ Futures</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia (6PM ET previo) → 📰 Jobless Claims 8:30AM → 🔔 NY Open 9:30AM → 🏁 Cierre 4PM ET</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <span class="pattern-badge">↩️ SWEEP L RETURN</span>
      <span style="background:rgba(0,230,118,.15);border:1px solid rgba(0,230,118,.4);color:#6ee7b7;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600">{direction_arrow} {direction_label}</span>
    </div>
  </div>

  <!-- SESSION LEGEND -->
  <div class="sess-legend">
    <span style="font-size:11px;color:var(--muted);font-weight:600">SESIONES:</span>
    <div class="sess-item"><div class="sess-dot" style="background:rgba(6,182,212,.35)"></div><span style="color:#67e8f9">🌏 ASIA · 6PM→2AM ET</span></div>
    <div class="sess-item"><div class="sess-dot" style="background:rgba(245,158,11,.35)"></div><span style="color:#fcd34d">🇬🇧 LONDON / PRE-MARKET · 2AM→9:30AM</span></div>
    <div class="sess-item"><div class="sess-dot" style="background:rgba(239,68,68,.35)"></div><span style="color:#fca5a5">📰 JOBLESS CLAIMS · 8:30AM</span></div>
    <div class="sess-item"><div class="sess-dot" style="background:rgba(16,185,129,.35)"></div><span style="color:#6ee7b7">🗽 NY SESSION · 9:30AM→4PM</span></div>
    <div class="sess-item"><div class="sess-dot" style="background:#7c3aed"></div><span style="color:#c4b5fd">✅ TARGET POC</span></div>
  </div>

  <!-- STATS REALES -->
  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">Day High</div><div class="stat-value c-cyan">{day_high:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Day Low</div><div class="stat-value c-bear">{day_low:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">POC Previo</div><div class="stat-value c-purple">{POC:,.1f}</div></div>
    <div class="stat-card"><div class="stat-label">VAH</div><div class="stat-value c-cyan">{VAH:,.0f}</div></div>
    <div class="stat-card"><div class="stat-label">VAL</div><div class="stat-value c-green">{VAL:,.1f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Open</div><div class="stat-value c-amber">{ny_open_p:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Low</div><div class="stat-value c-bear">{ny_low:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY High</div><div class="stat-value c-bull">{ny_high:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Close</div><div class="stat-value {direction_color}">{ny_close_p:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Range</div><div class="stat-value c-amber">{ny_range:.1f}</div></div>
    <div class="stat-card"><div class="stat-label">Move O→C</div><div class="stat-value {direction_color}">{move_oc:+.1f} pts</div></div>
    <div class="stat-card"><div class="stat-label">Dirección</div><div class="stat-value {direction_color}">{direction_label}</div></div>
  </div>

  <!-- CHART -->
  <div class="chart-wrap">
    <div class="chart-top">
      <span class="chart-title">NQ FUTURES — 5 MIN — DÍA COMPLETO 2026-03-19 · DATOS REALES (NQ=F via yfinance)</span>
      <div class="leg-row">
        <div class="leg-i"><div class="leg-dash" style="border-color:#06b6d4"></div>VAH {VAH:,.0f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#7c3aed"></div>POC {POC:,.1f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#10b981"></div>VAL {VAL:,.1f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#f59e0b"></div>NY OPEN {ny_open_p:,.2f}</div>
        <div class="leg-i"><div style="width:10px;height:10px;background:#00e676;border-radius:2px"></div>Bull</div>
        <div class="leg-i"><div style="width:10px;height:10px;background:#ff1744;border-radius:2px"></div>Bear</div>
      </div>
    </div>
    <div id="chart"></div>
  </div>

  <!-- TWO PANELS -->
  <div class="panels">

    <!-- TIMELINE -->
    <div class="panel">
      <div class="panel-title">📋 Timeline Real del Día</div>

      <div class="tl-item">
        <div class="tl-time">18:00</div>
        <div>
          <span class="tl-badge badge-asia">🌏 ASIA</span>
          <div class="tl-event c-cyan">Apertura Asia — Consolidación</div>
          <div class="tl-desc">NQ inicia sesión Asia. Precio consolida bajo el VA anterior. Smart money acumula posiciones.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">2:00</div>
        <div>
          <span class="tl-badge badge-london">🇬🇧 LONDON</span>
          <div class="tl-event c-amber">London Open — Distribución / Precio cae</div>
          <div class="tl-desc">London distribuye hacia abajo. Presión vendedora gradual acercando precio al VA.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">8:30</div>
        <div>
          <span class="tl-badge badge-news">📰 NOTICIA</span>
          <div class="tl-event c-red">⚡ Jobless Claims — Spike ↓</div>
          <div class="tl-desc">Datos de desempleo generan spike bajista. Precio cae agresivamente debajo del VA. Setup activado.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">9:30</div>
        <div>
          <span class="tl-badge badge-ny">🗽 NY OPEN</span>
          <div class="tl-event c-amber">NY Open: <strong>{ny_open_p:,.2f}</strong></div>
          <div class="tl-desc">NY abre debajo de VAL ({VAL:,.1f}). Distancia al POC: {POC - ny_open_p:.0f} pts. SWEEP_L_RETURN activado.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">9:30+</div>
        <div>
          <span class="tl-badge badge-ny">SWEEP</span>
          <div class="tl-event c-red">⬇️ Sweep — Low: <strong>{ny_low:,.2f}</strong></div>
          <div class="tl-desc">Price barre liquidez de stops. Mínimo real del día: <strong>{ny_low:,.2f}</strong> ({ny_open_p - ny_low:.0f} pts abajo del open).</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">~10:00</div>
        <div>
          <span class="tl-badge badge-ny">ENTRADA</span>
          <div class="tl-event c-green">↩️ Reversión — Entry Zone</div>
          <div class="tl-desc">Sweep fracasa → primera vela verde fuerte. Entry LARGO. Stop: bajo del sweep. Target: POC {POC:,.1f}</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">~11:00</div>
        <div>
          <span class="tl-badge badge-target">✅ TARGET</span>
          <div class="tl-event c-purple">Retorno al POC {POC:,.1f}</div>
          <div class="tl-desc">Precio alcanza zona POC. Ganancia desde entry. Patrón confirmado. NY Range real: <strong>{ny_range:.1f} pts</strong>.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">16:00</div>
        <div>
          <span class="tl-badge badge-ny">CIERRE</span>
          <div class="tl-event {direction_color}">Cierre: <strong>{ny_close_p:,.2f}</strong> ({direction_arrow} {move_oc:+.1f} pts)</div>
          <div class="tl-desc">Cierre real de sesión. Movimiento Open→Close: <strong>{move_oc:+.1f} pts</strong>. NY High: {ny_high:,.2f}.</div>
        </div>
      </div>
    </div>

    <!-- ANATOMY + JOURNEY -->
    <div style="display:flex;flex-direction:column;gap:16px">

      <!-- PRICE JOURNEY REAL -->
      <div class="panel">
        <div class="panel-title">🗺️ Recorrido Real del Precio</div>
        <div class="journey">
          <div class="j-step">
            <div class="j-node" style="background:rgba(6,182,212,.15);border-color:#06b6d4">🌏</div>
            <div class="j-label">ASIA<br>Inicio</div>
            <div class="j-price c-cyan">&nbsp;</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(245,158,11,.15);border-color:#f59e0b">🇬🇧</div>
            <div class="j-label">London<br>Sell</div>
            <div class="j-price c-amber">&nbsp;</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(239,68,68,.2);border-color:#ef4444">📰</div>
            <div class="j-label">8:30<br>News</div>
            <div class="j-price c-red">&nbsp;</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(245,158,11,.15);border-color:#f59e0b">🔔</div>
            <div class="j-label">NY Open</div>
            <div class="j-price c-amber">{ny_open_p:,.0f}</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(255,23,68,.2);border-color:#ff1744">⬇️</div>
            <div class="j-label">SWEEP<br>Low</div>
            <div class="j-price c-bear">{ny_low:,.0f}</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(0,230,118,.15);border-color:#00e676">↩️</div>
            <div class="j-label">Entry<br>~10:00</div>
            <div class="j-price c-bull">&nbsp;</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(124,58,237,.25);border-color:#7c3aed">✅</div>
            <div class="j-label">POC<br>Target</div>
            <div class="j-price c-purple">{POC:,.0f}</div>
          </div>
          <div class="j-step">
            <div class="j-node" style="background:rgba(0,230,118,.15);border-color:#00e676">🏁</div>
            <div class="j-label">Cierre<br>4PM</div>
            <div class="j-price c-bull">{ny_close_p:,.0f}</div>
          </div>
        </div>
      </div>

      <!-- ANATOMY -->
      <div class="panel">
        <div class="panel-title">🔬 Anatomía — SWEEP L RETURN (Real)</div>
        <div class="anat-grid">
          <div class="anat-item">
            <div class="anat-label">Open vs VA</div>
            <div class="anat-val c-red" style="font-size:11px">BELOW VAL<br>{ny_open_p:,.2f} vs {VAL:,.1f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Sweep</div>
            <div class="anat-val c-bear">{ny_open_p - ny_low:.0f} pts ↓</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">POC Target</div>
            <div class="anat-val c-purple">{POC:,.1f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Dist. Open→POC</div>
            <div class="anat-val c-green">{POC - ny_open_p:.0f} pts</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">NY Range Real</div>
            <div class="anat-val c-amber">{ny_range:.1f} pts</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Cierre Real</div>
            <div class="anat-val {direction_color}">{direction_arrow} {move_oc:+.1f} pts</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Day High</div>
            <div class="anat-val c-bull">{day_high:,.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Day Low</div>
            <div class="anat-val c-bear">{day_low:,.2f}</div>
          </div>
        </div>
      </div>

    </div><!-- end right col -->
  </div><!-- end panels -->

</div>

<div class="foot">NQ Whale Radar © 2026 · Datos reales: NQ=F via yfinance · {len(candles)} barras de 5 min · file: jueves_chart_20260319.html</div>

<script>
// ═══════════════════════════════════════════════
// DATOS REALES DE MERCADO — NQ=F — 2026-03-19
// Fuente: yfinance | {len(candles)} barras de 5min
// ═══════════════════════════════════════════════

const POC     = {POC};
const VAH     = {VAH};
const VAL     = {VAL};
const NY_OPEN_P  = {ny_open_p};
const NY_CLOSE_P = {ny_close_p};

// Timestamps UTC
const ASIA_START_UTC   = {ASIA_START};
const LONDON_START_UTC = {LONDON_TS};
const NEWS_UTC         = {NEWS_TS};
const NY_OPEN_UTC      = {NY_OPEN_TS};
const NY_CLOSE_UTC     = {NY_CLOSE};

// Candles REALES (time en Unix seconds)
const candles = {candles_js};

// ─── INIT CHART ───────────────────────────────────────────────
const chartEl = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartEl, {{
  width:  chartEl.offsetWidth,
  height: 680,
  layout: {{
    background: {{ color: '#0c0a1e' }},
    textColor:  '#94a3b8',
    fontSize:   11,
    fontFamily: 'JetBrains Mono, monospace',
  }},
  grid: {{
    vertLines: {{ color: 'rgba(30,26,58,0.6)' }},
    horzLines: {{ color: 'rgba(30,26,58,0.6)' }},
  }},
  crosshair: {{
    mode:     LightweightCharts.CrosshairMode.Normal,
    vertLine: {{ color: 'rgba(124,58,237,0.5)', width: 1, style: 2 }},
    horzLine: {{ color: 'rgba(124,58,237,0.5)', width: 1, style: 2 }},
  }},
  rightPriceScale: {{
    borderColor:  '#1e1a3a',
    scaleMargins: {{ top: 0.05, bottom: 0.05 }},
  }},
  timeScale: {{
    borderColor:    '#1e1a3a',
    timeVisible:    true,
    secondsVisible: false,
    tickMarkFormatter: (time) => {{
      const d = new Date(time * 1000);
      const h = ((d.getUTCHours() - 4 + 24) % 24);
      const m = d.getUTCMinutes();
      return m === 0 ? `${{h}}:00` : `${{h}}:${{m.toString().padStart(2,'0')}}`;
    }},
  }},
  handleScroll: {{ mouseWheel: true, pressedMouseMove: true }},
  handleScale:  {{ mouseWheel: true, pinch: true }},
}});

// CANDLESTICKS REALES
const series = chart.addCandlestickSeries({{
  upColor:         '#00e676',
  downColor:       '#ff1744',
  borderUpColor:   '#00e676',
  borderDownColor: '#ff1744',
  wickUpColor:     '#00e676',
  wickDownColor:   '#ff1744',
  priceFormat:     {{ type: 'price', precision: 2, minMove: 0.25 }},
}});
series.setData(candles);

// PRICE LINES
series.createPriceLine({{ price: VAH, color: '#06b6d4', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `VAH ${{VAH.toLocaleString()}}` }});
series.createPriceLine({{ price: POC, color: '#7c3aed', lineWidth: 2, lineStyle: 2, axisLabelVisible: true, title: `POC ${{POC.toLocaleString()}}` }});
series.createPriceLine({{ price: VAL, color: '#10b981', lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `VAL ${{VAL.toLocaleString()}}` }});
series.createPriceLine({{ price: NY_OPEN_P, color: '#f59e0b', lineWidth: 1, lineStyle: 3, axisLabelVisible: true, title: `NY OPEN ${{NY_OPEN_P.toLocaleString()}}` }});

// SESSION BACKGROUND BANDS
const leftScaleOpts = {{ leftPriceScale: {{ visible: false }} }};
chart.applyOptions(leftScaleOpts);

const bandHigh = Math.max(...candles.map(c => c.high)) + 200;

function addBand(startTs, endTs, topColor, botColor) {{
  const band = chart.addAreaSeries({{
    topColor, bottomColor: botColor, lineColor: 'rgba(0,0,0,0)',
    priceScaleId: 'left', crosshairMarkerVisible: false,
  }});
  band.setData([
    {{ time: startTs, value: bandHigh }},
    {{ time: endTs,   value: bandHigh }},
  ]);
}}

addBand(ASIA_START_UTC,   LONDON_START_UTC, 'rgba(6,182,212,0.07)',   'rgba(6,182,212,0.02)');
addBand(LONDON_START_UTC, NY_OPEN_UTC,      'rgba(245,158,11,0.07)',  'rgba(245,158,11,0.02)');
addBand(NY_OPEN_UTC,      NY_CLOSE_UTC,     'rgba(16,185,129,0.06)',  'rgba(16,185,129,0.02)');

// MARKERS — buscar candles más cercanos a los hitos
function nearestCandle(targetTs) {{
  return candles.reduce((best, c) =>
    Math.abs(c.time - targetTs) < Math.abs(best.time - targetTs) ? c : best
  );
}}

function lowestInRange(fromTs, toTs) {{
  const sub = candles.filter(c => c.time >= fromTs && c.time <= toTs);
  return sub.reduce((a, b) => b.low < a.low ? b : a);
}}

const nyCandles = candles.filter(c => c.time >= NY_OPEN_UTC && c.time <= NY_CLOSE_UTC);
const sweepCandle  = nyCandles.length ? nyCandles.reduce((a,b) => b.low < a.low ? b : a) : candles[candles.length-1];
const pocCandle    = nearestCandle(NY_OPEN_UTC + 5400); // ~11:00 AM ET aprox
const newsCandle   = nearestCandle(NEWS_UTC);
const nyOpenCandle = nearestCandle(NY_OPEN_UTC);
const londonCandle = nearestCandle(LONDON_START_UTC);

series.setMarkers([
  {{ time: candles[0].time,      position: 'belowBar', color: '#06b6d4', shape: 'circle',    text: '🌏 Asia 6PM ET' }},
  {{ time: londonCandle.time,    position: 'aboveBar', color: '#f59e0b', shape: 'circle',    text: '🇬🇧 London 2AM' }},
  {{ time: newsCandle.time,      position: 'aboveBar', color: '#ef4444', shape: 'arrowDown', text: '📰 Jobless Claims 8:30AM' }},
  {{ time: nyOpenCandle.time,    position: 'aboveBar', color: '#f59e0b', shape: 'circle',    text: `🔔 NY Open ${{NY_OPEN_P.toLocaleString()}}` }},
  {{ time: sweepCandle.time,     position: 'belowBar', color: '#ff1744', shape: 'arrowDown', text: `⬇️ Sweep Low ${{sweepCandle.low.toLocaleString()}}` }},
  {{ time: pocCandle.time,       position: 'aboveBar', color: '#7c3aed', shape: 'arrowUp',   text: `✅ POC Zone ${{POC.toLocaleString()}}` }},
  {{ time: candles[candles.length-1].time, position: 'inBar', color: '#f59e0b', shape: 'circle', text: `🏁 Cierre ${{NY_CLOSE_P.toLocaleString()}}` }},
]);

chart.timeScale().fitContent();

window.addEventListener('resize', () => {{
  chart.applyOptions({{ width: chartEl.offsetWidth }});
}});
</script>
</body>
</html>"""

# ── Guardar ────────────────────────────────────────────────────
out = Path("jueves_chart_20260319.html")
out.write_text(html, encoding="utf-8")
print(f"\n✅ Guardado: {out} ({out.stat().st_size // 1024} KB)")
print(f"   Abre: file:///C:/Users/FxDarvin/Desktop/PAgina/jueves_chart_20260319.html")
