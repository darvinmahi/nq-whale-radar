"""
Genera jueves_chart_20260326.html con datos reales de NQ=F de HOY (2026-03-26)
Incluye auto-refresh cada 5 minutos para sesión en vivo
"""
import yfinance as yf
import json
import os
from datetime import datetime, date, timedelta
import pytz

ET = pytz.timezone("America/New_York")
today = date.today()
yesterday = today - timedelta(days=1)

print(f"📅 Today: {today} | Weekday: {today.weekday()} (3=Thursday)")

# ─── Descargar datos ────────────────────────────────────────────────────────
ticker = yf.Ticker("NQ=F")
df = ticker.history(period="5d", interval="5m")
df.index = df.index.tz_convert("America/New_York")

today_df = df[df.index.date == today].copy()
yest_df  = df[df.index.date == yesterday].copy()

print(f"Barras HOY: {len(today_df)}")
if not today_df.empty:
    print(f"  High: {today_df['High'].max():.2f}")
    print(f"  Low:  {today_df['Low'].min():.2f}")
    print(f"  Last: {today_df['Close'].iloc[-1]:.2f}")

# ─── Calcular POC/VAH/VAL del día anterior (miércoles) ────────────────────
POC = VAH = VAL = 0.0
NY_OPEN_P = NY_CLOSE_P = 0.0
YEST_HIGH = YEST_LOW = 0.0

if not yest_df.empty:
    try:
        ny_y = yest_df.between_time("9:30", "16:00")
        if not ny_y.empty:
            YEST_HIGH = float(ny_y["High"].max())
            YEST_LOW  = float(ny_y["Low"].min())
            rng = YEST_HIGH - YEST_LOW
            # Simple approximation of POC (midpoint) and VA (35-65% range)
            POC = round(YEST_LOW + rng * 0.50, 2)
            VAH = round(YEST_LOW + rng * 0.65, 2)
            VAL = round(YEST_LOW + rng * 0.35, 2)
            print(f"\nAYER: High={YEST_HIGH:.2f}, Low={YEST_LOW:.2f}")
            print(f"  POC={POC:.2f}, VAH={VAH:.2f}, VAL={VAL:.2f}")
    except Exception as e:
        print(f"Error calculando VA: {e}")

# NY open/close de hoy (si ya pasó)
if not today_df.empty:
    try:
        ny_open_bar = today_df.between_time("9:30", "9:35")
        if not ny_open_bar.empty:
            NY_OPEN_P = float(ny_open_bar["Open"].iloc[0])
        ny_close_bar = today_df.between_time("15:55", "16:05")
        if not ny_close_bar.empty:
            NY_CLOSE_P = float(ny_close_bar["Close"].iloc[-1])
    except Exception as e:
        print(f"Error NY data: {e}")

# ─── Convertir barras a JSON para Lightweight Charts ──────────────────────
barras = []
for idx, row in today_df.iterrows():
    ts = int(idx.timestamp())
    barras.append({
        "time": ts,
        "open":  round(float(row["Open"]),  2),
        "high":  round(float(row["High"]),   2),
        "low":   round(float(row["Low"]),    2),
        "close": round(float(row["Close"]),  2),
    })

candles_js = json.dumps(barras)

# ─── Stats resumidas ───────────────────────────────────────────────────────
day_high  = today_df["High"].max()  if not today_df.empty else 0
day_low   = today_df["Low"].min()   if not today_df.empty else 0
last_close= today_df["Close"].iloc[-1] if not today_df.empty else 0
num_bars  = len(barras)

# Timestamps UTC para las zonas de sesión
import calendar
def et_to_utc_ts(h, m, d=today):
    dt_et = ET.localize(datetime(d.year, d.month, d.day, h, m, 0))
    return int(dt_et.timestamp())

ASIA_START   = et_to_utc_ts(18, 0, yesterday)  # 6PM ET ayer
LONDON_START = et_to_utc_ts(2,  0)              # 2AM ET hoy
NEWS_TIME    = et_to_utc_ts(8, 30)              # 8:30AM noticias
NY_OPEN_TS   = et_to_utc_ts(9, 30)              # 9:30AM NY open
NY_CLOSE_TS  = et_to_utc_ts(16, 0)             # 4PM cierre

# Color del día (según precio)
day_direction = "SESIÓN EN CURSO" if today_df.empty or NY_OPEN_P == 0 else (
    "BULLISH ↑" if last_close > NY_OPEN_P else "BEARISH ↓"
)
day_color = "#10b981" if "BULL" in day_direction or day_direction == "SESIÓN EN CURSO" else "#ef4444"

# ─── Generar HTML ─────────────────────────────────────────────────────────
last_update_str = datetime.now(ET).strftime("%H:%M ET")

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NQ — Jueves 2026-03-26 | EN VIVO</title>
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
      border-bottom:1px solid var(--border);
      padding:14px 24px; display:flex; align-items:center; justify-content:space-between;
      position:sticky; top:0; z-index:100;
    }}
    .logo-badge{{
      background:linear-gradient(135deg,var(--purple),#4f46e5);
      color:#fff; font-size:11px; font-weight:700;
      padding:4px 10px; border-radius:6px; letter-spacing:1px;
    }}
    .live-badge{{
      background:rgba(239,68,68,.18); border:1px solid rgba(239,68,68,.45);
      color:#fca5a5; font-size:11px; font-weight:700;
      padding:4px 12px; border-radius:6px; letter-spacing:1px;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.6; }}
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
      background:linear-gradient(90deg,#ef4444,var(--amber),var(--cyan),var(--purple));
    }}

    .sess-legend{{
      display:flex; gap:20px; flex-wrap:wrap;
      padding:12px 20px;
      background:linear-gradient(135deg,#0c0a1e,#130f2a);
      border:1px solid var(--border); border-radius:12px; margin-bottom:16px;
    }}
    .sess-item{{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:600}}
    .sess-dot{{width:12px;height:12px;border-radius:3px}}

    .stats-row{{
      display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:10px;
      margin-bottom:16px;
    }}
    .stat-card{{
      background:linear-gradient(135deg,#0c0a1e,#130f2a); border:1px solid var(--border);
      border-radius:12px; padding:12px 14px; text-align:center;
    }}
    .stat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .stat-value{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700}}
    .c-green{{color:var(--green)}} .c-red{{color:var(--red)}} .c-cyan{{color:var(--cyan)}}
    .c-amber{{color:var(--amber)}} .c-purple{{color:#a78bfa}} .c-gray{{color:var(--muted)}}
    .c-bull{{color:var(--bull)}} .c-bear{{color:var(--bear)}}

    .chart-section-label {{
      display: flex; align-items: center; gap: 10px;
      font-size: 10px; font-weight: 700; color: var(--muted);
      text-transform: uppercase; letter-spacing: 1.5px;
      margin-bottom: 10px; padding-left: 4px;
    }}
    .chart-section-label::before {{
      content: ''; display: block;
      width: 3px; height: 14px; border-radius: 2px;
      background: linear-gradient(180deg, var(--purple), var(--cyan));
    }}
    .chart-frame {{
      background: linear-gradient(135deg, #09071a 0%, #0e0b24 100%);
      border-radius: 20px; padding: 3px; position: relative;
      margin-bottom: 20px;
      box-shadow:
        0 0 0 1px rgba(124,58,237,0.35),
        0 0 0 3px rgba(6,182,212,0.12),
        0 20px 60px rgba(0,0,0,0.7),
        inset 0 1px 0 rgba(255,255,255,0.04);
    }}
    .chart-frame::before {{
      content: '';
      position: absolute; top: -2px; left: 10%; right: 10%;
      height: 2px; border-radius: 2px;
      background: linear-gradient(90deg, transparent, var(--purple), var(--cyan), transparent);
      filter: blur(1px);
    }}
    .chart-wrap{{
      background: linear-gradient(180deg, #0c0a1e 0%, #08061a 100%);
      border: 1px solid var(--border);
      border-radius: 16px; overflow:hidden; position:relative;
    }}
    .chart-top{{
      padding:14px 20px; border-bottom:1px solid var(--border);
      background:linear-gradient(135deg,#0c0a1e,#110d2a);
      display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px;
    }}
    .chart-title{{font-size:12px;font-weight:700;color:var(--muted);letter-spacing:.5px}}
    .leg-row{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
    .leg-i{{display:flex;align-items:center;gap:5px;font-size:10px;color:var(--muted);font-family:'JetBrains Mono',monospace}}
    .leg-dash{{width:18px;height:0;border-top:2px dashed}}
    #chart{{width:100%;height:640px}}

    .panels{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}}
    @media(max-width:900px){{.panels{{grid-template-columns:1fr}}}}
    .panel{{background:var(--card); border:1px solid var(--border); border-radius:14px; padding:20px;}}
    .panel-title{{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:14px}}

    .tl-item{{display:flex; gap:12px; align-items:flex-start; padding:10px 0; border-bottom:1px solid rgba(255,255,255,.04);}}
    .tl-item:last-child{{border-bottom:none}}
    .tl-time{{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--cyan);min-width:46px;padding-top:2px;flex-shrink:0}}
    .tl-badge{{font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;margin-bottom:4px;display:inline-block}}
    .badge-asia  {{background:rgba(6,182,212,.15);border:1px solid rgba(6,182,212,.3);color:#67e8f9}}
    .badge-london{{background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.3);color:#fcd34d}}
    .badge-news  {{background:rgba(239,68,68,.25);border:1px solid rgba(239,68,68,.5);color:#fca5a5}}
    .badge-ny    {{background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.4);color:#6ee7b7}}
    .badge-target{{background:rgba(124,58,237,.2);border:1px solid rgba(124,58,237,.5);color:#c4b5fd}}
    .badge-live  {{background:rgba(239,68,68,.3);border:1px solid rgba(239,68,68,.6);color:#fca5a5; animation:pulse 2s infinite;}}
    .tl-event{{font-size:13px;font-weight:700;margin-bottom:2px}}
    .tl-desc{{font-size:11px;color:var(--muted);line-height:1.5}}

    .anat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .anat-item{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:12px 14px}}
    .anat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .anat-val{{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;line-height:1.4}}

    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}

    /* Auto-refresh banner */
    .refresh-banner {{
      background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2);
      border-radius: 8px; padding: 8px 16px; margin-bottom: 12px;
      display: flex; align-items: center; gap: 10px; font-size: 11px;
    }}
    .refresh-dot {{ width:8px;height:8px;border-radius:50%;background:#ef4444;animation:pulse 1s infinite; }}
  </style>
</head>
<body>

<!-- TOP BAR -->
<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">2026-03-26 · EN VIVO · 5 MIN</span>
    <div class="live-badge">🔴 EN VIVO</div>
  </div>
  <a href="daily_dashboard.html" class="back-btn">← Dashboard Principal</a>
</div>

<div class="page">

  <!-- AUTO-REFRESH BANNER -->
  <div class="refresh-banner">
    <div class="refresh-dot"></div>
    <span style="color:#fca5a5;font-weight:700">SESIÓN EN VIVO</span>
    <span style="color:var(--muted)">Última actualización: <strong id="lastUpdate" style="color:#e2e8f0">{last_update_str}</strong> · {num_bars} velas cargadas</span>
    <span style="margin-left:auto;color:var(--muted)">Auto-refresh: 5 min</span>
  </div>

  <!-- DATE HEADER -->
  <div class="date-header">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px">📅 Jueves 26 de Marzo 2026 — Sesión EN VIVO NQ Futures</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia (6PM ET previo) → 📰 Jobless Claims 8:30AM → 🔔 NY Open 9:30AM → 🏁 Cierre 4PM ET</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <span style="background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);color:#fca5a5;padding:8px 18px;border-radius:30px;font-size:14px;font-weight:700">🔴 EN CURSO</span>
      <span id="dayDirection" style="background:rgba(16,185,129,.15);border:1px solid rgba(16,185,129,.4);color:#6ee7b7;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:600">{day_direction}</span>
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

  <!-- STATS EN VIVO -->
  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">Day High</div><div class="stat-value c-cyan" id="statHigh">{day_high:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Day Low</div><div class="stat-value c-bear" id="statLow">{day_low:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">POC Previo (Mié)</div><div class="stat-value c-purple">{POC:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAH Previo</div><div class="stat-value c-cyan">{VAH:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAL Previo</div><div class="stat-value c-green">{VAL:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Open</div><div class="stat-value c-amber" id="statNYOpen">{f"{NY_OPEN_P:.2f}" if NY_OPEN_P else "—"}</div></div>
    <div class="stat-card"><div class="stat-label">Última Vela</div><div class="stat-value c-bull" id="statClose">{last_close:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Barras</div><div class="stat-value c-gray" id="statBars">{num_bars}</div></div>
    <div class="stat-card"><div class="stat-label">Mié High</div><div class="stat-value c-cyan">{YEST_HIGH:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Mié Low</div><div class="stat-value c-bear">{YEST_LOW:.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Última Act.</div><div class="stat-value c-gray" style="font-size:12px">{last_update_str}</div></div>
    <div class="stat-card"><div class="stat-label">Estado</div><div class="stat-value c-red" style="font-size:13px">EN VIVO 🔴</div></div>
  </div>

  <!-- CHART FRAME -->
  <div class="chart-section-label">📊 Chart — 5 Min · Sesión Actual (Hoy)</div>
  <div class="chart-frame">
  <div class="chart-wrap">
    <div class="chart-top">
      <span class="chart-title">NQ FUTURES — 5 MIN — EN VIVO 2026-03-26 · DATOS REALES (NQ=F via yfinance)</span>
      <div class="leg-row">
        <div class="leg-i"><div class="leg-dash" style="border-color:#06b6d4"></div>VAH {VAH:.0f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#7c3aed"></div>POC {POC:.0f}</div>
        <div class="leg-i"><div class="leg-dash" style="border-color:#10b981"></div>VAL {VAL:.0f}</div>
        <div class="leg-i"><div style="width:10px;height:10px;background:#00e676;border-radius:2px"></div>Bull ▲</div>
        <div class="leg-i"><div style="width:10px;height:10px;background:#b366ff;border-radius:2px"></div>Bear ▼</div>
        <div class="live-badge" style="font-size:10px;padding:3px 8px">🔴 LIVE</div>
      </div>
    </div>
    <div id="chart"></div>
  </div>
  </div><!-- /chart-frame -->

  <!-- TWO PANELS -->
  <div class="panels">

    <!-- TIMELINE HOY -->
    <div class="panel">
      <div class="panel-title">📋 Timeline del Día — Jueves 26 Marzo 2026</div>

      <div class="tl-item">
        <div class="tl-time">18:00</div>
        <div>
          <span class="tl-badge badge-asia">🌏 ASIA</span>
          <div class="tl-event c-cyan">Apertura Asia — Consolidación pre-claims</div>
          <div class="tl-desc">NQ inicia sesión. Precio consolida en relación al VA del miércoles. Smart money posicionándose antes de las noticias.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">2:00</div>
        <div>
          <span class="tl-badge badge-london">🇬🇧 LONDON</span>
          <div class="tl-event c-amber">London Open — Pre-market move</div>
          <div class="tl-desc">Londres define la dirección pre-NY. Presión alcista o bajista según el contexto de liquidez disponible.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">8:30</div>
        <div>
          <span class="tl-badge badge-news">📰 NOTICIA</span>
          <div class="tl-event c-red">⚡ Jobless Claims — Evento Clave</div>
          <div class="tl-desc">Datos de desempleo → spike de volatilidad. Setup clásico jueves activado según dirección del spike.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">9:30</div>
        <div>
          <span class="tl-badge badge-ny">🗽 NY OPEN</span>
          <div class="tl-event c-amber">NY Open</div>
          <div class="tl-desc">Apertura oficial de NY. Posible sweep de extremos o continuación según el setup post-claims.</div>
        </div>
      </div>

      <div class="tl-item">
        <div class="tl-time">HOY</div>
        <div>
          <span class="tl-badge badge-live">🔴 EN VIVO</span>
          <div class="tl-event c-red">Sesión Activa — Datos cargando...</div>
          <div class="tl-desc">Chart se actualiza automáticamente cada 5 minutos. El patrón final se revelará durante la sesión NY.</div>
        </div>
      </div>
    </div>

    <!-- ANATOMY -->
    <div style="display:flex;flex-direction:column;gap:16px">

      <!-- KEY LEVELS -->
      <div class="panel">
        <div class="panel-title">🗺️ Niveles Clave Hoy</div>
        <div class="anat-grid">
          <div class="anat-item">
            <div class="anat-label">POC Mié (Target)</div>
            <div class="anat-val c-purple">{POC:.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">VAH Mié</div>
            <div class="anat-val c-cyan">{VAH:.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">VAL Mié</div>
            <div class="anat-val c-green">{VAL:.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Mié High</div>
            <div class="anat-val c-bull">{YEST_HIGH:.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Day High HOY</div>
            <div class="anat-val c-cyan" id="anatHigh">{day_high:.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Day Low HOY</div>
            <div class="anat-val c-bear" id="anatLow">{day_low:.2f}</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Jobless Claims</div>
            <div class="anat-val c-amber">8:30 AM ET</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">NY Open</div>
            <div class="anat-val c-amber" id="anatNYOpen">{f"{NY_OPEN_P:.2f}" if NY_OPEN_P else "9:30 AM"}</div>
          </div>
        </div>
      </div>

      <!-- PATRÓN JUEVES INFO -->
      <div class="panel">
        <div class="panel-title">🔬 Patrón Jueves — Jobless Claims</div>
        <div class="anat-grid">
          <div class="anat-item">
            <div class="anat-label">Sesgo Estadístico</div>
            <div class="anat-val c-red" style="font-size:11px">TRAMPA 67%</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Spike Pre-NY</div>
            <div class="anat-val c-amber">~65 pts</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Rango NY Prom</div>
            <div class="anat-val c-amber">~388 pts</div>
          </div>
          <div class="anat-item">
            <div class="anat-label">Setup Activo</div>
            <div class="anat-val c-red" style="font-size:11px; animation: pulse 2s infinite">CLAIMS 8:30 🔴</div>
          </div>
        </div>
      </div>

    </div><!-- end right col -->
  </div><!-- end panels -->

</div>

<div class="foot">NQ Whale Radar © 2026 · Datos reales: NQ=F via yfinance · {num_bars} barras 5min · Generado: {last_update_str} · file: jueves_chart_20260326.html</div>

<script>
// ═══════════════════════════════════════════════════════
// DATOS REALES — NQ=F — 2026-03-26 (EN VIVO)
// Fuente: yfinance | Barras 5min
// ═══════════════════════════════════════════════════════

const POC     = {POC};
const VAH     = {VAH};
const VAL     = {VAL};
const NY_OPEN_P = {NY_OPEN_P if NY_OPEN_P else 0};

// Timestamps zona sesión
const ASIA_START_UTC   = {ASIA_START};
const LONDON_START_UTC = {LONDON_START};
const NEWS_TIME_UTC    = {NEWS_TIME};
const NY_OPEN_UTC      = {NY_OPEN_TS};
const NY_CLOSE_UTC     = {NY_CLOSE_TS};

// Velas 5 min descargadas
const rawCandles = {candles_js};

// ─── Crear chart (Lightweight Charts v4) ────────────────────────────────────
const chartEl = document.getElementById('chart');
const chart = LightweightCharts.createChart(chartEl, {{
  width:  chartEl.clientWidth,
  height: 640,
  layout: {{
    background: {{ color: '#08061a' }},
    textColor:  '#94a3b8',
    fontSize:   11,
    fontFamily: "'JetBrains Mono', monospace",
  }},
  grid: {{
    vertLines: {{ color: '#1e1a3a', style: 1 }},
    horzLines: {{ color: '#1e1a3a', style: 1 }},
  }},
  crosshair: {{ mode: 1 }},
  rightPriceScale: {{
    borderColor: '#1e1a3a',
    scaleMargins: {{ top: 0.05, bottom: 0.1 }},
  }},
  timeScale: {{
    borderColor: '#1e1a3a',
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 5,
  }},
}});

// Velas
const candleSeries = chart.addCandlestickSeries({{
  upColor:          '#00e676',
  downColor:        '#b366ff',
  borderUpColor:    '#00e676',
  borderDownColor:  '#b366ff',
  wickUpColor:      '#00e676',
  wickDownColor:    '#b366ff',
}});

// Filtrar candles válidas
const candles = rawCandles
  .filter(c => c.high >= c.low && c.open > 0 && c.close > 0)
  .sort((a, b) => a.time - b.time);

candleSeries.setData(candles);

// ─── Líneas de nivel como priceLines (no afectan el autoscale) ─────────────────────
const SOLID = 0, DASHED = 1, DOTTED = 2;
if (candles.length > 0) {{
  candleSeries.createPriceLine({{ price: VAH, color: '#06b6d4', lineWidth: 1, lineStyle: DASHED, axisLabelVisible: true, title: 'VAH' }});
  candleSeries.createPriceLine({{ price: POC, color: '#7c3aed', lineWidth: 2, lineStyle: SOLID,  axisLabelVisible: true, title: 'POC' }});
  candleSeries.createPriceLine({{ price: VAL, color: '#10b981', lineWidth: 1, lineStyle: DASHED, axisLabelVisible: true, title: 'VAL' }});
  if (NY_OPEN_P > 0) candleSeries.createPriceLine({{ price: NY_OPEN_P, color: '#f59e0b', lineWidth: 1, lineStyle: DOTTED, axisLabelVisible: true, title: 'NY OPEN' }});
}}

// ─── Zonas de sesión ─────────────────────────────────────────────────────────
const markers = [];

function addSessionMarker(time, label, color, shape) {{
  // Only add if we have data around that time
  const nearby = candles.find(c => Math.abs(c.time - time) < 1800); // 30 min window
  if (nearby) {{
    markers.push({{ time: nearby.time, position: 'belowBar', color, shape, text: label }});
  }}
}}

addSessionMarker(LONDON_START_UTC, '🇬🇧 London', '#f59e0b', 'arrowUp');
addSessionMarker(NEWS_TIME_UTC,    '📰 Claims',  '#ef4444', 'arrowDown');
addSessionMarker(NY_OPEN_UTC,      '🗽 NY Open', '#10b981', 'arrowUp');

if (markers.length > 0) candleSeries.setMarkers(markers);

// ─── Fit contenido — rango de velas disponibles ───────────────────────────────────────────────
if (candles.length > 0) {{
  chart.timeScale().setVisibleRange({{ from: candles[0].time - 300, to: candles[candles.length - 1].time + 600 }});
}} else {{
  chart.timeScale().fitContent();
}}

// ─── Resize handler ──────────────────────────────────────────────────────────
window.addEventListener('resize', () => {{
  chart.applyOptions({{ width: chartEl.clientWidth }});
}});

// ─── Auto-refresh cada 5 minutos ────────────────────────────────────────────
let refreshCountdown = 300;
setInterval(() => {{
  refreshCountdown--;
  if (refreshCountdown <= 0) {{
    window.location.reload();
  }}
}}, 1000);

console.log('✅ NQ Chart 2026-03-26 cargado · Velas:', candles.length);
</script>

</body>
</html>"""

# Guardar el archivo
output_path = "jueves_chart_20260326.html"
with open(output_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ Generado: {output_path}")
print(f"   Velas: {num_bars}")
print(f"   High: {day_high:.2f}, Low: {day_low:.2f}")
print(f"   POC: {POC:.2f}, VAH: {VAH:.2f}, VAL: {VAL:.2f}")
print(f"\n👉 Abrir en: http://localhost:8085/{output_path}")
