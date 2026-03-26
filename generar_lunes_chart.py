#!/usr/bin/env python3
"""
Genera lunes_chart_20260317.html con VELAS REALES de NQ=F (2026-03-17)
Usa yfinance para descargar datos de 5 minutos.
"""
import yfinance as yf
import json
import math
from datetime import datetime, timezone

# ── Descargar datos ────────────────────────────────────────────────────────
print("Descargando NQ=F 5min para 2026-03-17...")
df = yf.download("NQ=F", start="2026-03-17", end="2026-03-18",
                 interval="5m", prepost=True, progress=False)

if df.empty:
    raise SystemExit("ERROR: yfinance no devolvió datos.")

# Aplanar MultiIndex si existe
if hasattr(df.columns, 'levels'):
    df.columns = df.columns.get_level_values(0)

df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"vol"})
df = df[["open","high","low","close"]].dropna()

# Convertir index a UTC unix timestamp
df.index = df.index.tz_convert("UTC")

print(f"  Barras descargadas: {len(df)}")
print(f"  Rango: {df.index[0]} → {df.index[-1]}")

# ── Construir array de candles para JS ─────────────────────────────────────
candles = []
for ts, row in df.iterrows():
    candles.append({
        "time": int(ts.timestamp()),
        "open":  round(float(row["open"]),  2),
        "high":  round(float(row["high"]),  2),
        "low":   round(float(row["low"]),   2),
        "close": round(float(row["close"]), 2),
    })

print(f"  Candles listos: {len(candles)}")

# ── Calcular niveles clave ─────────────────────────────────────────────────
# Timestamps ET para Lunes 2026-03-17
# Asia  = 17-Mar 18:00 ET    = 17-Mar 22:00 UTC  = 1773874800? calculamos:
# 2026-03-16 18:00 ET = 2026-03-16 22:00 UTC
import calendar
def et_to_utc(date_str, hour, minute=0):
    """Convierte hora ET (EDT=-4) a unix UTC para March 2026 (EDT en vigor)."""
    dt_local = datetime(2026, 3, int(date_str.split('-')[2]),
                        hour, minute, tzinfo=timezone.utc)
    return int(dt_local.timestamp()) + 4*3600  # ET es UTC-4 en Marzo 2026

# Asia Lunes empieza el Domingo 16 a las 6PM ET
ASIA_START_UTC   = int(datetime(2026,3,16,22,0, tzinfo=timezone.utc).timestamp())
LONDON_START_UTC = int(datetime(2026,3,17, 6,0, tzinfo=timezone.utc).timestamp())  # 2AM ET
NY_OPEN_UTC      = int(datetime(2026,3,17,13,30,tzinfo=timezone.utc).timestamp())  # 9:30AM ET
NY_CLOSE_UTC     = int(datetime(2026,3,17,20,0, tzinfo=timezone.utc).timestamp())  # 4PM ET

# Precio de apertura NY y cierre
ny_candles = [c for c in candles if NY_OPEN_UTC <= c["time"] <= NY_CLOSE_UTC]
all_candles = candles

if ny_candles:
    NY_OPEN_P  = ny_candles[0]["open"]
    NY_CLOSE_P = ny_candles[-1]["close"]
    NY_HIGH    = max(c["high"] for c in ny_candles)
    NY_LOW     = min(c["low"]  for c in ny_candles)
    NY_RANGE   = round(NY_HIGH - NY_LOW, 2)
    NY_MOVE    = round(NY_CLOSE_P - NY_OPEN_P, 2)
else:
    NY_OPEN_P = NY_CLOSE_P = NY_HIGH = NY_LOW = 0
    NY_RANGE = NY_MOVE = 0

DAY_HIGH = max(c["high"] for c in candles)
DAY_LOW  = min(c["low"]  for c in candles)

# ── Volume Profile simple (Asia + London) → POC / VAH / VAL ───────────────
pre_ny = [c for c in candles if c["time"] < NY_OPEN_UTC]
if pre_ny:
    price_min = min(c["low"]  for c in pre_ny)
    price_max = max(c["high"] for c in pre_ny)
    bucket_size = 25.0  # NQ tick bucket de 25pts
    n_buckets = max(1, int((price_max - price_min) / bucket_size) + 1)
    vp = [0.0] * n_buckets
    for c in pre_ny:
        lo_i = int((c["low"]  - price_min) / bucket_size)
        hi_i = int((c["high"] - price_min) / bucket_size)
        for i in range(lo_i, min(hi_i+1, n_buckets)):
            vp[i] += 1
    poc_i = vp.index(max(vp))
    POC = round(price_min + poc_i * bucket_size + bucket_size/2, 2)
    # VA: 70% del volumen alrededor del POC
    total_vol = sum(vp)
    target_vol = total_vol * 0.70
    lo_i = hi_i = poc_i
    acc = vp[poc_i]
    while acc < target_vol:
        expand_lo = (lo_i > 0)
        expand_hi = (hi_i < n_buckets - 1)
        if expand_lo and expand_hi:
            if vp[lo_i-1] >= vp[hi_i+1]:
                lo_i -= 1; acc += vp[lo_i]
            else:
                hi_i += 1; acc += vp[hi_i]
        elif expand_lo:
            lo_i -= 1; acc += vp[lo_i]
        elif expand_hi:
            hi_i += 1; acc += vp[hi_i]
        else:
            break
    VAH = round(price_min + hi_i * bucket_size + bucket_size, 2)
    VAL = round(price_min + lo_i * bucket_size, 2)
else:
    POC = DAY_HIGH - (DAY_HIGH - DAY_LOW)*0.5
    VAH = DAY_HIGH - (DAY_HIGH - DAY_LOW)*0.25
    VAL = DAY_LOW  + (DAY_HIGH - DAY_LOW)*0.25

print(f"  POC={POC}  VAH={VAH}  VAL={VAL}")
print(f"  NY Open={NY_OPEN_P}  Close={NY_CLOSE_P}  Range={NY_RANGE}")

direction = "BULLISH" if NY_MOVE > 0 else "BEARISH"
dir_color = "#10b981" if NY_MOVE > 0 else "#ef4444"
move_sign = "+" if NY_MOVE > 0 else ""

CANDLES_JSON = json.dumps(candles, separators=(',',':'))
n_candles = len(candles)

# ── Noticias del Lunes 2026-03-17 ─────────────────────────────────────────
# No hay noticias tier-1 programadas para ese Lunes (FED silencio pre-FOMC)
# Marcaremos: Asia Open, London Open, NY Open
# (ajusta si tienes datos de noticias reales)
NEWS_TS = 0  # sin noticia tier-1 ese día

# ── HTML ───────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NQ — Lunes 2026-03-17 | DATOS REALES</title>
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

    .top-bar{{
      background:linear-gradient(135deg,#0c0a1e 0%,#110d2a 100%);
      border-bottom:1px solid var(--border);padding:14px 24px;
      display:flex;align-items:center;justify-content:space-between;
      position:sticky;top:0;z-index:100;
    }}
    .logo-badge{{background:linear-gradient(135deg,var(--purple),#4f46e5);color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:1px;}}
    .real-badge{{background:rgba(16,185,129,.18);border:1px solid rgba(16,185,129,.45);color:#6ee7b7;font-size:11px;font-weight:700;padding:4px 12px;border-radius:6px;letter-spacing:1px;}}
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

    .chart-section-label{{display:flex;align-items:center;gap:10px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:10px;padding-left:4px;}}
    .chart-section-label::before{{content:'';display:block;width:3px;height:14px;border-radius:2px;background:linear-gradient(180deg,var(--purple),var(--cyan));}}

    .chart-frame{{background:linear-gradient(135deg,#09071a 0%,#0e0b24 100%);border:2px solid transparent;border-radius:20px;padding:3px;position:relative;margin-bottom:20px;box-shadow:0 0 0 1px rgba(124,58,237,0.35),0 0 0 3px rgba(6,182,212,0.12),0 20px 60px rgba(0,0,0,0.7),inset 0 1px 0 rgba(255,255,255,0.04);}}
    .chart-frame::before{{content:'';position:absolute;top:-2px;left:10%;right:10%;height:2px;border-radius:2px;background:linear-gradient(90deg,transparent,var(--purple),var(--cyan),transparent);filter:blur(1px);}}

    .chart-wrap{{background:linear-gradient(180deg,#0c0a1e 0%,#08061a 100%);border:1px solid var(--border);border-radius:16px;overflow:hidden;position:relative;box-shadow:0 0 0 1px rgba(124,58,237,0.1) inset,0 30px 80px rgba(0,0,0,0.8);}}
    .chart-top{{padding:14px 20px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,#0c0a1e,#110d2a);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}}
    .chart-title{{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.5px}}
    .leg-row{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
    .leg-i{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace}}
    .leg-dash{{width:18px;height:0;border-top:2px dashed}}
    #chart{{width:100%;height:680px}}

    /* Replay bar */
    #replay-bar{{max-height:0;overflow:hidden;opacity:0;transition:max-height .35s ease,opacity .3s ease;background:rgba(6,182,212,.06);border-top:1px solid rgba(6,182,212,.18);border-radius:0 0 10px 10px;}}
    #replay-bar.visible{{max-height:200px;opacity:1;}}
    .rp-row{{display:flex;align-items:center;gap:10px;padding:10px 14px;flex-wrap:wrap;}}
    .rp-btn{{background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:6px 14px;border-radius:8px;cursor:pointer;transition:all .2s;white-space:nowrap;}}
    .rp-btn:hover{{background:rgba(6,182,212,.28);}}
    .rp-btn.pause{{background:rgba(245,158,11,.15);border-color:rgba(245,158,11,.4);color:#fcd34d;}}
    .rp-speed-group{{display:flex;gap:3px;}}
    .rp-speed{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);color:var(--muted);font-size:10px;padding:4px 8px;border-radius:6px;cursor:pointer;transition:all .15s;font-family:'JetBrains Mono',monospace;}}
    .rp-speed.active{{background:rgba(6,182,212,.25);border-color:#06b6d4;color:#e0f2fe;font-weight:700;}}
    .rp-time{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#67e8f9;min-width:160px;font-weight:600;}}
    .rp-progress-wrap{{flex:1;min-width:120px;}}
    .rp-track{{position:relative;height:6px;background:rgba(255,255,255,.08);border-radius:3px;}}
    .rp-fill{{position:absolute;left:0;top:0;height:100%;background:linear-gradient(90deg,#06b6d4,#7c3aed);border-radius:3px;transition:width .15s;}}
    .rp-scrubber{{position:absolute;left:0;top:-5px;width:100%;height:16px;opacity:0;cursor:pointer;margin:0;-webkit-appearance:none;appearance:none;}}
    #rp-narrative{{display:flex;align-items:flex-start;gap:10px;padding:8px 14px 10px;border-top:1px solid rgba(255,255,255,.04);}}
    .rp-step-badge{{font-size:10px;font-weight:700;padding:3px 8px;border-radius:12px;white-space:nowrap;font-family:'JetBrains Mono',monospace;}}
    #rp-narrative-text{{font-size:11px;color:var(--muted);line-height:1.6;flex:1;}}
    .rp-candle-count{{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);white-space:nowrap;}}

    .replay-launch-btn{{background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.35);color:#67e8f9;font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:6px 14px;border-radius:20px;cursor:pointer;letter-spacing:.5px;transition:all .2s;}}
    .replay-launch-btn:hover{{background:rgba(6,182,212,.22);}}
    .replay-launch-btn.active{{background:rgba(6,182,212,.25);border-color:#06b6d4;color:#e0f2fe;}}

    .panels{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
    @media(max-width:900px){{.panels{{grid-template-columns:1fr}}}}
    .panel{{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;}}
    .panel-title{{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}}

    .tl-item{{display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.04);}}
    .tl-item:last-child{{border-bottom:none}}
    .tl-time{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--cyan);min-width:46px;padding-top:2px;flex-shrink:0}}
    .tl-badge{{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;margin-bottom:4px;display:inline-block}}
    .badge-asia{{background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9}}
    .badge-london{{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);color:#fcd34d}}
    .badge-ny{{background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.4);color:#6ee7b7}}
    .badge-target{{background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.5);color:#c4b5fd}}
    .tl-event{{font-size:13px;font-weight:700;margin-bottom:2px}}
    .tl-desc{{font-size:11px;color:var(--muted);line-height:1.5}}

    .anat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .anat-item{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:12px 14px}}
    .anat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .anat-val{{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;line-height:1.4}}

    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}
  </style>
</head>
<body>

<!-- TOP BAR -->
<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">2026-03-17 · DÍA COMPLETO · 5 MIN</span>
    <div class="real-badge">✅ DATOS REALES NQ=F</div>
  </div>
  <a href="index.html" class="back-btn">← Panel Principal</a>
</div>

<div class="page">

  <!-- DATE HEADER -->
  <div class="date-header">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px">📅 Lunes 17 de Marzo 2026 — Sesión Real NQ Futures</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia (6PM ET Dom) → 🇬🇧 London 2AM → 🗽 NY Open 9:30AM → 🏁 Cierre 4PM ET</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <span style="background:rgba({('16,185,129' if NY_MOVE>0 else '239,68,68')},.15);border:1px solid rgba({('16,185,129' if NY_MOVE>0 else '239,68,68')},.4);color:{dir_color};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700">{'↑ BULLISH' if NY_MOVE>0 else '↓ BEARISH'}</span>
    </div>
  </div>

  <!-- STATS -->
  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">Day High</div><div class="stat-value c-cyan">{DAY_HIGH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Day Low</div><div class="stat-value c-bear">{DAY_LOW:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">POC Previo</div><div class="stat-value c-purple">{POC:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAH</div><div class="stat-value c-cyan">{VAH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAL</div><div class="stat-value c-green">{VAL:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Open</div><div class="stat-value c-amber">{NY_OPEN_P:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Low</div><div class="stat-value c-bear">{NY_LOW:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY High</div><div class="stat-value c-bull">{NY_HIGH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Close</div><div class="stat-value c-{'bull' if NY_MOVE>0 else 'bear'}">{NY_CLOSE_P:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Range</div><div class="stat-value c-amber">{NY_RANGE:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Move O→C</div><div class="stat-value c-{'bull' if NY_MOVE>0 else 'bear'}">{move_sign}{NY_MOVE:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Dirección</div><div class="stat-value c-{'bull' if NY_MOVE>0 else 'bear'}">{direction}</div></div>
  </div>

  <!-- CHART -->
  <div class="chart-section-label">📊 Chart — 5 Min · Día Completo (2026-03-17)</div>
  <div class="chart-frame">
  <div class="chart-wrap">
    <div class="chart-top">
      <span class="chart-title">NQ FUTURES — 5 MIN — 2026-03-17 · {n_candles} VELAS REALES (NQ=F via yfinance)</span>
      <div class="leg-row">
        <div class="leg-i"><div class="leg-dash" style="border-color:#06b6d4"></div>VAH {VAH:,.2f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#7c3aed"></div>POC {POC:,.2f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#10b981"></div>VAL {VAL:,.2f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#f59e0b"></div>NY OPEN {NY_OPEN_P:,.2f}</div>
        <div class="leg-i"><div style="width:10px;height:10px;background:#10b981;border-radius:2px"></div>Bull ▲</div>
        <div class="leg-i"><div style="width:10px;height:10px;background:#8b5cf6;border-radius:2px"></div>Bear ▼</div>
      </div>
      <button class="replay-launch-btn" id="replayLaunchBtn" onclick="toggleReplayBar()">⏪ REPLAY</button>
    </div>
    <div id="chart"></div>
    <!-- REPLAY BAR -->
    <div id="replay-bar">
      <div class="rp-row">
        <button class="rp-btn" id="rpPlayBtn" onclick="replayToggle()">▶ PLAY</button>
        <button class="rp-btn" style="background:rgba(255,0,85,0.1);border-color:rgba(255,0,85,0.3);color:#ff0055" onclick="replayReset()">⟲ Reset</button>
        <div class="rp-speed-group">
          <button class="rp-speed active" data-spd="1"  onclick="setSpeed(1,this)">1×</button>
          <button class="rp-speed"        data-spd="3"  onclick="setSpeed(3,this)">3×</button>
          <button class="rp-speed"        data-spd="8"  onclick="setSpeed(8,this)">8×</button>
          <button class="rp-speed"        data-spd="20" onclick="setSpeed(20,this)">20×</button>
          <button class="rp-speed"        data-spd="50" onclick="setSpeed(50,this)">50×</button>
        </div>
        <div class="rp-time" id="rpTimeDisplay">-- -- : -- --</div>
        <div class="rp-progress-wrap">
          <div class="rp-track" id="rpTrack">
            <div class="rp-fill" id="rpFill" style="width:0%"></div>
            <input type="range" class="rp-scrubber" id="rpScrubber" min="0" max="100" value="0" oninput="replayScrub(this.value)">
          </div>
        </div>
      </div>
      <div id="rp-narrative">
        <span class="rp-step-badge" id="rpStepBadge" style="background:rgba(6,182,212,0.15);border:1px solid rgba(6,182,212,0.3);color:#67e8f9">🌏 ASIA</span>
        <div id="rp-narrative-text">Presiona PLAY para iniciar el replay del Lunes 2026-03-17</div>
        <div class="rp-candle-count" id="rpCandleCount">Vela 0 / 0</div>
      </div>
    </div>
  </div>
  </div>

  <!-- PANELS -->
  <div class="panels">
    <div class="panel">
      <div class="panel-title">📋 Timeline del Lunes 2026-03-17</div>
      <div class="tl-item">
        <div class="tl-time">18:00</div>
        <div>
          <span class="tl-badge badge-asia">🌏 ASIA</span>
          <div class="tl-event c-cyan">Apertura Asia — Consolidación</div>
          <div class="tl-desc">NQ inicia sesión Asia el Domingo 16 a las 6PM ET. Smart money posicionándose para la semana.</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">2:00</div>
        <div>
          <span class="tl-badge badge-london">🇬🇧 LONDON</span>
          <div class="tl-event c-amber">London Open — Formación del perfil</div>
          <div class="tl-desc">London construye el rango de volumen. VAH={VAH:,.0f} · POC={POC:,.0f} · VAL={VAL:,.0f}</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">9:30</div>
        <div>
          <span class="tl-badge badge-ny">🗽 NY OPEN</span>
          <div class="tl-event c-amber">NY Open: <strong>{NY_OPEN_P:,.2f}</strong></div>
          <div class="tl-desc">Apertura NY. Distance al POC: {abs(NY_OPEN_P-POC):,.0f} pts. Dirección: {direction}.</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">9:30+</div>
        <div>
          <span class="tl-badge badge-ny">NY SESSION</span>
          <div class="tl-event {'c-bull' if NY_MOVE>0 else 'c-bear'}">{'↑ Rally' if NY_MOVE>0 else '↓ Sell-off'} — High: <strong>{NY_HIGH:,.2f}</strong> · Low: <strong>{NY_LOW:,.2f}</strong></div>
          <div class="tl-desc">NY Range real: <strong>{NY_RANGE:,.2f} pts</strong>. Move Open→Close: {move_sign}{NY_MOVE:,.2f} pts.</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">16:00</div>
        <div>
          <span class="tl-badge badge-ny">CIERRE</span>
          <div class="tl-event c-{'bull' if NY_MOVE>0 else 'bear'}">Cierre: <strong>{NY_CLOSE_P:,.2f}</strong> ({move_sign}{NY_MOVE:,.2f} pts)</div>
          <div class="tl-desc">Cierre real de sesión NY. Day High: {DAY_HIGH:,.2f} · Day Low: {DAY_LOW:,.2f}</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-title">🔬 Anatomía del Día</div>
      <div class="anat-grid">
        <div class="anat-item"><div class="anat-label">Day Range</div><div class="anat-val c-amber">{round(DAY_HIGH-DAY_LOW,2):,.2f} pts</div></div>
        <div class="anat-item"><div class="anat-label">NY Range</div><div class="anat-val c-amber">{NY_RANGE:,.2f} pts</div></div>
        <div class="anat-item"><div class="anat-label">POC (Asia+Lon)</div><div class="anat-val c-purple">{POC:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">Open vs POC</div><div class="anat-val {'c-red' if NY_OPEN_P<POC else 'c-green'}">{('BELOW' if NY_OPEN_P<POC else 'ABOVE')} POC<br>{abs(NY_OPEN_P-POC):,.0f} pts</div></div>
        <div class="anat-item"><div class="anat-label">VAH</div><div class="anat-val c-cyan">{VAH:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">VAL</div><div class="anat-val c-green">{VAL:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">NY High</div><div class="anat-val c-bull">{NY_HIGH:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">NY Low</div><div class="anat-val c-bear">{NY_LOW:,.2f}</div></div>
      </div>
    </div>
  </div>

</div>

<div class="foot">NQ Whale Radar © 2026 · Datos reales: NQ=F via yfinance · {n_candles} barras de 5 min · file: lunes_chart_20260317.html</div>

<script>
// ═══════════════════════════════════════════════
// DATOS REALES DE MERCADO — NQ=F — 2026-03-17
// Fuente: yfinance | {n_candles} barras de 5min
// ═══════════════════════════════════════════════

const POC      = {POC};
const VAH      = {VAH};
const VAL      = {VAL};
const NY_OPEN_P  = {NY_OPEN_P};
const NY_CLOSE_P = {NY_CLOSE_P};

const ASIA_START_UTC   = {ASIA_START_UTC};
const LONDON_START_UTC = {LONDON_START_UTC};
const NY_OPEN_UTC      = {NY_OPEN_UTC};
const NY_CLOSE_UTC     = {NY_CLOSE_UTC};

// ── VELAS REALES ─────────────────────────────────────────────────────────
const candles = {CANDLES_JSON};

// ── CHART ─────────────────────────────────────────────────────────────────
const chartEl = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartEl, {{
  width:  chartEl.offsetWidth,
  height: 680,
  layout: {{
    background: {{ color: '#08061a' }},
    textColor:  '#64748b',
    fontSize:   11,
    fontFamily: 'JetBrains Mono, monospace',
  }},
  grid: {{
    vertLines: {{ color: 'rgba(124,58,237,0.06)' }},
    horzLines: {{ color: 'rgba(124,58,237,0.06)' }},
  }},
  crosshair: {{
    mode:     LightweightCharts.CrosshairMode.Normal,
    vertLine: {{ color: 'rgba(6,182,212,0.5)', width: 1, style: 2 }},
    horzLine: {{ color: 'rgba(6,182,212,0.5)', width: 1, style: 2 }},
  }},
  rightPriceScale: {{
    borderColor:  'rgba(30,26,58,0.8)',
    textColor:    '#64748b',
    scaleMargins: {{ top: 0.05, bottom: 0.05 }},
  }},
  timeScale: {{
    borderColor:    'rgba(30,26,58,0.8)',
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

// CANDLESTICKS — hollow neon style
const series = chart.addCandlestickSeries({{
  upColor:         'rgba(16,185,129,0.08)',
  downColor:       'rgba(139,92,246,0.08)',
  borderUpColor:   '#10b981',
  borderDownColor: '#8b5cf6',
  wickUpColor:     '#10b981',
  wickDownColor:   '#8b5cf6',
  borderVisible:   true,
  wickVisible:     true,
  priceFormat:     {{ type: 'price', precision: 2, minMove: 0.25 }},
}});
series.setData(candles);

// PRICE LINES
series.createPriceLine({{ price: VAH, color: 'rgba(0,255,128,0.6)',  lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `VAH ${{VAH.toLocaleString()}}` }});
series.createPriceLine({{ price: POC, color: '#00ff80',              lineWidth: 2, lineStyle: 0, axisLabelVisible: true, title: `POC ${{POC.toLocaleString()}}` }});
series.createPriceLine({{ price: VAL, color: 'rgba(0,255,128,0.6)',  lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: `VAL ${{VAL.toLocaleString()}}` }});
series.createPriceLine({{ price: NY_OPEN_P, color: 'rgba(245,158,11,0.8)', lineWidth: 1, lineStyle: 3, axisLabelVisible: true, title: `NY OPEN ${{NY_OPEN_P.toLocaleString()}}` }});

// SESSION BANDS
const bandHigh = Math.max(...candles.map(c => c.high)) + 300;
function addBand(startTs, endTs, topColor, botColor) {{
  const band = chart.addAreaSeries({{
    topColor, bottomColor: botColor, lineColor: 'rgba(0,0,0,0)',
    priceScaleId: 'left', crosshairMarkerVisible: false,
  }});
  band.setData([{{ time: startTs, value: bandHigh }}, {{ time: endTs, value: bandHigh }}]);
}}
addBand(ASIA_START_UTC,   LONDON_START_UTC, 'rgba(6,182,212,0.10)',  'rgba(6,182,212,0.03)');
addBand(LONDON_START_UTC, NY_OPEN_UTC,      'rgba(245,158,11,0.10)', 'rgba(245,158,11,0.03)');
addBand(NY_OPEN_UTC,      NY_CLOSE_UTC,     'rgba(0,255,128,0.08)',  'rgba(0,255,128,0.02)');

// SESSION H/L LINES
function sessionHL(fromTs, toTs) {{
  const s = candles.filter(c => c.time >= fromTs && c.time <= toTs);
  return s.length ? {{ high: Math.max(...s.map(c=>c.high)), low: Math.min(...s.map(c=>c.low)) }} : null;
}}
const asiaHL = sessionHL(ASIA_START_UTC, LONDON_START_UTC-1);
if (asiaHL) {{
  series.createPriceLine({{ price: asiaHL.high, color: 'rgba(6,182,212,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`ASIA H ${{asiaHL.high.toLocaleString()}}` }});
  series.createPriceLine({{ price: asiaHL.low,  color: 'rgba(6,182,212,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`ASIA L ${{asiaHL.low.toLocaleString()}}` }});
}}
const lonHL = sessionHL(LONDON_START_UTC, NY_OPEN_UTC-1);
if (lonHL) {{
  series.createPriceLine({{ price: lonHL.high, color: 'rgba(245,158,11,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`LON H ${{lonHL.high.toLocaleString()}}` }});
  series.createPriceLine({{ price: lonHL.low,  color: 'rgba(245,158,11,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`LON L ${{lonHL.low.toLocaleString()}}` }});
}}
const nyHL = sessionHL(NY_OPEN_UTC, NY_CLOSE_UTC);
if (nyHL) {{
  series.createPriceLine({{ price: nyHL.high, color: 'rgba(0,255,128,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`NY H ${{nyHL.high.toLocaleString()}}` }});
  series.createPriceLine({{ price: nyHL.low,  color: 'rgba(0,255,128,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`NY L ${{nyHL.low.toLocaleString()}}` }});
}}

// MARKERS
function nearestCandle(targetTs) {{
  return candles.reduce((best,c) => Math.abs(c.time-targetTs)<Math.abs(best.time-targetTs)?c:best);
}}
const londonC = nearestCandle(LONDON_START_UTC);
const nyOpenC = nearestCandle(NY_OPEN_UTC);
const nyLowC  = candles.filter(c=>c.time>=NY_OPEN_UTC&&c.time<=NY_CLOSE_UTC).reduce((a,b)=>b.low<a.low?b:a, candles[candles.length-1]);
const nyHighC = candles.filter(c=>c.time>=NY_OPEN_UTC&&c.time<=NY_CLOSE_UTC).reduce((a,b)=>b.high>a.high?b:a, candles[0]);

series.setMarkers([
  {{ time: candles[0].time, position:'belowBar', color:'#06b6d4', shape:'circle',    text:'🌏 Asia 6PM ET' }},
  {{ time: londonC.time,    position:'aboveBar', color:'#f59e0b', shape:'circle',    text:'🇬🇧 London 2AM' }},
  {{ time: nyOpenC.time,    position:'aboveBar', color:'#f59e0b', shape:'circle',    text:`🔔 NY Open ${{NY_OPEN_P.toLocaleString()}}` }},
  {{ time: nyLowC.time,     position:'belowBar', color:'#ef4444', shape:'arrowDown', text:`↓ Day Low ${{nyLowC.low.toLocaleString()}}` }},
  {{ time: nyHighC.time,    position:'aboveBar', color:'#10b981', shape:'arrowUp',   text:`↑ Day High ${{nyHighC.high.toLocaleString()}}` }},
]);

// FIT
chart.timeScale().fitContent();
window.addEventListener('resize', () => chart.applyOptions({{ width: chartEl.offsetWidth }}));

// ── REPLAY ────────────────────────────────────────────────────────────────
let rpIndex = 0, rpTimer = null, rpSpeed = 1, rpRunning = false;
const TICK_MS = 300;

function stageFor(ts) {{
  if (ts < LONDON_START_UTC) return ['🌏 ASIA',    'rgba(6,182,212,0.15)','1px solid rgba(6,182,212,0.3)','#67e8f9'];
  if (ts < NY_OPEN_UTC)      return ['🇬🇧 LONDON',  'rgba(245,158,11,0.15)','1px solid rgba(245,158,11,0.3)','#fcd34d'];
  return                            ['🗽 NY',       'rgba(16,185,129,0.15)','1px solid rgba(16,185,129,0.4)','#6ee7b7'];
}}

function rpUpdateUI(i) {{
  const pct = candles.length>1 ? (i/(candles.length-1)*100).toFixed(1) : 0;
  document.getElementById('rpFill').style.width = pct+'%';
  document.getElementById('rpScrubber').value = pct;
  const c = candles[i];
  const d = new Date(c.time*1000);
  const h = ((d.getUTCHours()-4+24)%24).toString().padStart(2,'0');
  const m = d.getUTCMinutes().toString().padStart(2,'0');
  document.getElementById('rpTimeDisplay').textContent = `Mar 17  ${{h}}:${{m}} ET  C=${{c.close.toLocaleString()}}`;
  document.getElementById('rpCandleCount').textContent = `Vela ${{i+1}} / ${{candles.length}}`;
  const [label,bg,border,color] = stageFor(c.time);
  const badge = document.getElementById('rpStepBadge');
  badge.textContent = label; badge.style.background=bg; badge.style.border=border; badge.style.color=color;
  document.getElementById('rp-narrative-text').textContent =
    `${{label}} — ${{h}}:${{m}} ET · Close: ${{c.close.toLocaleString()}} · High: ${{c.high.toLocaleString()}} · Low: ${{c.low.toLocaleString()}}`;
}}

function replayTick() {{
  if (rpIndex >= candles.length) {{ replayStop(); return; }}
  series.setData(candles.slice(0, rpIndex+1));
  rpUpdateUI(rpIndex);
  chart.timeScale().scrollToRealTime();
  rpIndex++;
  rpTimer = setTimeout(replayTick, TICK_MS / rpSpeed);
}}

function replayToggle() {{
  if (rpRunning) replayStop(); else replayStart();
}}
function replayStart() {{
  if (rpIndex >= candles.length) replayReset();
  rpRunning = true;
  document.getElementById('rpPlayBtn').textContent = '⏸ PAUSE';
  document.getElementById('rpPlayBtn').classList.add('pause');
  replayTick();
}}
function replayStop() {{
  rpRunning = false;
  clearTimeout(rpTimer);
  document.getElementById('rpPlayBtn').textContent = '▶ PLAY';
  document.getElementById('rpPlayBtn').classList.remove('pause');
  if (rpIndex >= candles.length) series.setData(candles);
}}
function replayReset() {{
  replayStop();
  rpIndex = 0;
  series.setData(candles);
  document.getElementById('rpFill').style.width = '0%';
  document.getElementById('rpScrubber').value = 0;
  document.getElementById('rpTimeDisplay').textContent = '-- -- : -- --';
  document.getElementById('rpCandleCount').textContent = 'Vela 0 / 0';
  chart.timeScale().fitContent();
}}
function replayScrub(val) {{
  replayStop();
  rpIndex = Math.round((val/100)*(candles.length-1));
  series.setData(candles.slice(0, rpIndex+1));
  rpUpdateUI(rpIndex);
}}
function setSpeed(s, btn) {{
  rpSpeed = s;
  document.querySelectorAll('.rp-speed').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
}}
function toggleReplayBar() {{
  const bar = document.getElementById('replay-bar');
  const btn = document.getElementById('replayLaunchBtn');
  bar.classList.toggle('visible');
  btn.classList.toggle('active');
}}
</script>

</body>
</html>"""

output_file = "lunes_chart_20260317.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ Generado: {output_file}")
print(f"   Velas: {n_candles} barras de 5min")
print(f"   Day Range: {DAY_HIGH:,.2f} - {DAY_LOW:,.2f} ({round(DAY_HIGH-DAY_LOW,2):,.2f} pts)")
print(f"   NY:  Open={NY_OPEN_P}  High={NY_HIGH}  Low={NY_LOW}  Close={NY_CLOSE_P}")
print(f"   VP:  POC={POC}  VAH={VAH}  VAL={VAL}")
