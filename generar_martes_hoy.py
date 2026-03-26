"""
generar_martes_hoy.py
======================
Genera martes_chart_HOY.html con velas REALES del Martes más próximo/actual.
Detecta automáticamente la fecha del Martes de esta semana.
Si hoy ES martes → usa hoy. Si ya pasó → usa el más reciente.
Si aún no llegó → usa el próximo.
"""
import yfinance as yf
import json
import sys
from datetime import datetime, timezone, timedelta, date

# ── Detectar fecha del martes ─────────────────────────────────────────────────
today = date.today()
today_wd = today.weekday()  # 0=Mon … 6=Sun

# Días desde el último martes (1=Tuesday)
days_since_tue = (today_wd - 1) % 7
if days_since_tue == 0 and today_wd == 1:
    # Hoy es martes
    tue_date = today
elif days_since_tue <= 3:
    # Pasó hace poco (miérc/juev/viern)
    tue_date = today - timedelta(days=days_since_tue)
else:
    # Lunes o fin de semana → usar próximo martes
    days_to_tue = (1 - today_wd) % 7
    tue_date = today + timedelta(days=days_to_tue)

# Permitir override por CLI: python generar_martes_hoy.py YYYY-MM-DD
if len(sys.argv) > 1:
    try:
        tue_date = date.fromisoformat(sys.argv[1])
        print(f"  Override fecha: {tue_date}")
    except ValueError:
        print(f"  Fecha inválida: {sys.argv[1]}")
        sys.exit(1)

mon_date = tue_date - timedelta(days=1)  # Lunes anterior (Asia start)
print("=" * 60)
print(f"  GENERANDO CHART MARTES: {tue_date}")
print("=" * 60)

# ── Descarga yfinance ─────────────────────────────────────────────────────────
print(f"  Descargando NQ=F 5min {mon_date} → {tue_date + timedelta(days=1)}...")
df = yf.download("NQ=F",
                 start=mon_date.strftime("%Y-%m-%d"),
                 end=(tue_date + timedelta(days=2)).strftime("%Y-%m-%d"),
                 interval="5m", prepost=True, progress=False, auto_adjust=True)

if df.empty:
    print("  ERROR: yfinance no devolvió datos. Puede ser que aún no sea martes.")
    print("  Prueba: python generar_martes_hoy.py 2026-03-18")
    sys.exit(1)

if hasattr(df.columns, 'levels'):
    df.columns = df.columns.get_level_values(0)

df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"vol"})
df = df[["open","high","low","close"]].dropna()
df.index = df.index.tz_convert("UTC")
print(f"  Barras totales: {len(df)}")

# ── Detectar DST ──────────────────────────────────────────────────────────────
def is_dst(d): return 3 <= d.month <= 10
dst = is_dst(tue_date)
tz_offset = 4 if dst else 5  # ET = UTC-4 (DST) o UTC-5

# ── Timestamps clave (UTC) ───────────────────────────────────────────────────
ASIA_START_UTC   = datetime(mon_date.year, mon_date.month, mon_date.day,
                            22 if dst else 23, 0, tzinfo=timezone.utc)
LONDON_START_UTC = datetime(tue_date.year, tue_date.month, tue_date.day,
                            6 if dst else 7, 0, tzinfo=timezone.utc)
NY_OPEN_UTC      = datetime(tue_date.year, tue_date.month, tue_date.day,
                            13 if dst else 14, 30, tzinfo=timezone.utc)
NY_CLOSE_UTC     = datetime(tue_date.year, tue_date.month, tue_date.day,
                            20 if dst else 21, 0, tzinfo=timezone.utc)

# ── Filtrar barras del día ────────────────────────────────────────────────────
def ts_int(dt): return int(dt.timestamp())

candles = []
for ts, row in df.iterrows():
    if ts < ASIA_START_UTC or ts > NY_CLOSE_UTC:
        continue
    candles.append({
        "time" : ts_int(ts),
        "open" : round(float(row["open"]),  2),
        "high" : round(float(row["high"]),  2),
        "low"  : round(float(row["low"]),   2),
        "close": round(float(row["close"]), 2),
    })

print(f"  Velas del día: {len(candles)}")
if len(candles) < 5:
    print("  ⚠️  Pocas barras. Verifica que el martes haya cotizado.")

# ── Calcular estadísticas ─────────────────────────────────────────────────────
ny_candles = [c for c in candles if ts_int(NY_OPEN_UTC) <= c["time"] <= ts_int(NY_CLOSE_UTC)]
pre_ny     = [c for c in candles if c["time"] < ts_int(NY_OPEN_UTC)]

NY_OPEN_P  = ny_candles[0]["open"]  if ny_candles else 0
NY_CLOSE_P = ny_candles[-1]["close"] if ny_candles else 0
NY_HIGH    = max(c["high"] for c in ny_candles) if ny_candles else 0
NY_LOW     = min(c["low"]  for c in ny_candles) if ny_candles else 0
NY_RANGE   = round(NY_HIGH - NY_LOW, 2)
NY_MOVE    = round(NY_CLOSE_P - NY_OPEN_P, 2)
DAY_HIGH   = max(c["high"] for c in candles) if candles else 0
DAY_LOW    = min(c["low"]  for c in candles) if candles else 0

# Volume Profile pre-NY
if pre_ny:
    pm_lo = min(c["low"]  for c in pre_ny)
    pm_hi = max(c["high"] for c in pre_ny)
    bucket = 25.0
    nb = max(1, int((pm_hi - pm_lo) / bucket) + 1)
    vp = [0.0] * nb
    for c in pre_ny:
        li = int((c["low"]  - pm_lo) / bucket)
        hi = int((c["high"] - pm_lo) / bucket)
        for i in range(li, min(hi+1, nb)):
            vp[i] += 1
    pi  = vp.index(max(vp))
    POC = round(pm_lo + pi * bucket + bucket/2, 2)
    tv  = sum(vp) * 0.70
    li = hi = pi; acc = vp[pi]
    while acc < tv:
        clo = li > 0; chi = hi < nb-1
        if clo and chi:
            if vp[li-1] >= vp[hi+1]: li -= 1; acc += vp[li]
            else: hi += 1; acc += vp[hi]
        elif clo: li -= 1; acc += vp[li]
        elif chi: hi += 1; acc += vp[hi]
        else: break
    VAH = round(pm_lo + hi * bucket + bucket, 2)
    VAL = round(pm_lo + li * bucket, 2)
else:
    POC = VAH = VAL = NY_OPEN_P

print(f"  POC={POC}  VAH={VAH}  VAL={VAL}")
print(f"  NY Open={NY_OPEN_P}  Close={NY_CLOSE_P}  Range={NY_RANGE} pts")

direction = "BULLISH" if NY_MOVE >= 0 else "BEARISH"
dir_color = "#10b981" if NY_MOVE >= 0 else "#ef4444"
move_sign = "+" if NY_MOVE >= 0 else ""
tue_str   = tue_date.strftime("%Y-%m-%d")
mon_str   = mon_date.strftime("%Y-%m-%d")

# Bug: weekday names to Spanish
DIAS = {0:"Lunes",1:"Martes",2:"Miércoles",3:"Jueves",4:"Viernes",5:"Sábado",6:"Domingo"}
MESES = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
         7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
tue_label = f"Martes {tue_date.day} de {MESES[tue_date.month]} {tue_date.year}"

CANDLES_JSON = json.dumps(candles, separators=(',',':'))
n_candles = len(candles)

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NQ — {tue_label} | DATOS REALES</title>
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
    .chart-wrap{{background:linear-gradient(180deg,#0c0a1e 0%,#08061a 100%);border:1px solid var(--border);border-radius:16px;overflow:hidden;position:relative;}}
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
    .rp-time{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#67e8f9;min-width:180px;font-weight:600;}}
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

    .ict-box{{background:linear-gradient(135deg,rgba(245,158,11,.08),rgba(124,58,237,.08));border:1px solid rgba(245,158,11,.3);border-radius:14px;padding:16px 20px;margin-bottom:16px;}}
    .ict-title{{font-size:11px;font-weight:700;color:#fcd34d;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;}}
    .ict-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;}}
    .ict-item{{font-size:12px;color:var(--muted);line-height:1.7;}}
    .ict-item strong{{color:var(--text);}}

    .foot{{text-align:center;padding:20px;color:var(--muted);font-size:11px}}
    .anat-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
    .anat-item{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:10px;padding:12px 14px}}
    .anat-label{{font-size:9px;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}}
    .anat-val{{font-family:'JetBrains Mono',monospace;font-size:13px;font-weight:700;line-height:1.4}}
  </style>
</head>
<body>

<!-- TOP BAR -->
<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px">
    <div class="logo-badge">NQ RADAR</div>
    <span style="color:var(--muted);font-size:13px;font-family:'JetBrains Mono',monospace">{tue_str} · MARTES · 5 MIN</span>
    <div class="real-badge">✅ DATOS REALES NQ=F</div>
  </div>
  <a href="index.html" class="back-btn">← Panel Principal</a>
</div>

<div class="page">

  <!-- DATE HEADER -->
  <div class="date-header">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px">📅 {tue_label} — Sesión Real NQ Futures</div>
      <div style="color:var(--muted);font-size:12px">🌏 Asia (6PM ET {mon_str}) → 🇬🇧 London 2AM → 🗽 NY Open 9:30AM → 🏁 Cierre 4PM ET</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
      <span style="background:rgba({'16,185,129' if NY_MOVE>=0 else '239,68,68'},.15);border:1px solid rgba({'16,185,129' if NY_MOVE>=0 else '239,68,68'},.4);color:{dir_color};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700">{'↑ BULLISH' if NY_MOVE>=0 else '↓ BEARISH'}</span>
    </div>
  </div>

  <!-- STATS -->
  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">Day High</div><div class="stat-value c-cyan">{DAY_HIGH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Day Low</div><div class="stat-value c-bear">{DAY_LOW:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">POC Pre-NY</div><div class="stat-value c-purple">{POC:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAH</div><div class="stat-value c-cyan">{VAH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">VAL</div><div class="stat-value c-green">{VAL:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Open</div><div class="stat-value c-amber">{NY_OPEN_P:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Low</div><div class="stat-value c-bear">{NY_LOW:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY High</div><div class="stat-value c-bull">{NY_HIGH:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Close</div><div class="stat-value c-{'bull' if NY_MOVE>=0 else 'bear'}">{NY_CLOSE_P:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">NY Range</div><div class="stat-value c-amber">{NY_RANGE:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Move O→C</div><div class="stat-value c-{'bull' if NY_MOVE>=0 else 'bear'}">{move_sign}{NY_MOVE:,.2f}</div></div>
    <div class="stat-card"><div class="stat-label">Open vs POC</div><div class="stat-value c-{'bull' if NY_OPEN_P>=POC else 'bear'}">{'ABOVE' if NY_OPEN_P>=POC else 'BELOW'}<br>{abs(NY_OPEN_P-POC):,.0f} pts</div></div>
  </div>

  <!-- ICT BOX -->
  <div class="ict-box">
    <div class="ict-title">🎯 Setup ICT — MARTES | Bear Trap + LONG Reversal</div>
    <div class="ict-grid">
      <div class="ict-item"><strong>Lógica:</strong> Martes NY open cae los primeros 30 min barriendo liquidez → reversal al alza</div>
      <div class="ict-item"><strong>Entry:</strong> LONG en mínimo de 9:30–10:00 AM ET</div>
      <div class="ict-item"><strong>Stop:</strong> Mínimo − 30 pts</div>
      <div class="ict-item"><strong>Target:</strong> +150 pts ó cierre 11:00 AM</div>
      <div class="ict-item"><strong>POC Asia+Lon:</strong> {POC:,.2f}</div>
      <div class="ict-item"><strong>VAH / VAL:</strong> {VAH:,.2f} / {VAL:,.2f}</div>
    </div>
  </div>

  <!-- CHART -->
  <div class="chart-section-label">📊 Chart — 5 Min · {tue_label}</div>
  <div class="chart-frame">
  <div class="chart-wrap">
    <div class="chart-top">
      <span class="chart-title">NQ FUTURES — 5 MIN — {tue_str} MARTES · {n_candles} VELAS REALES</span>
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
        <div id="rp-narrative-text">Presiona PLAY para iniciar el replay del {tue_label}</div>
        <div class="rp-candle-count" id="rpCandleCount">Vela 0 / 0</div>
      </div>
    </div>
  </div>
  </div>

  <!-- PANELS -->
  <div class="panels">
    <div class="panel">
      <div class="panel-title">📋 Timeline del {tue_label}</div>
      <div class="tl-item">
        <div class="tl-time">18:00</div>
        <div>
          <span class="tl-badge badge-asia">🌏 ASIA</span>
          <div class="tl-event c-cyan">Apertura Asia (Lun 6PM ET) — Acumulación</div>
          <div class="tl-desc">NQ inicia sesión Asia el Lunes {mon_date.day} a las 6PM ET. Smart money construye posición para el Martes.</div>
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
          <div class="tl-desc">Apertura NY. Distance al POC: {abs(NY_OPEN_P-POC):,.0f} pts.</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">9:30+</div>
        <div>
          <span class="tl-badge badge-target">🎯 ICT SETUP</span>
          <div class="tl-event c-amber">Bear Trap → NY Low: <strong>{NY_LOW:,.2f}</strong></div>
          <div class="tl-desc">Setup: caída inicial barre liquidez → LONG desde low de primera media hora.</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">NY</div>
        <div>
          <span class="tl-badge badge-ny">NY SESSION</span>
          <div class="tl-event {'c-bull' if NY_MOVE>=0 else 'c-bear'}">{'↑ Rally' if NY_MOVE>=0 else '↓ Sell-off'} — High: <strong>{NY_HIGH:,.2f}</strong> · Low: <strong>{NY_LOW:,.2f}</strong></div>
          <div class="tl-desc">NY Range: <strong>{NY_RANGE:,.2f} pts</strong> | Move Open→Close: {move_sign}{NY_MOVE:,.2f} pts</div>
        </div>
      </div>
      <div class="tl-item">
        <div class="tl-time">16:00</div>
        <div>
          <span class="tl-badge badge-ny">CIERRE</span>
          <div class="tl-event c-{'bull' if NY_MOVE>=0 else 'bear'}">Cierre: <strong>{NY_CLOSE_P:,.2f}</strong> ({move_sign}{NY_MOVE:,.2f} pts)</div>
          <div class="tl-desc">Day High: {DAY_HIGH:,.2f} · Day Low: {DAY_LOW:,.2f}</div>
        </div>
      </div>
    </div>

    <div class="panel">
      <div class="panel-title">🔬 Anatomía del Día</div>
      <div class="anat-grid">
        <div class="anat-item"><div class="anat-label">Day Range</div><div class="anat-val c-amber">{round(DAY_HIGH-DAY_LOW,2):,.2f} pts</div></div>
        <div class="anat-item"><div class="anat-label">NY Range</div><div class="anat-val c-amber">{NY_RANGE:,.2f} pts</div></div>
        <div class="anat-item"><div class="anat-label">POC (Asia+Lon)</div><div class="anat-val c-purple">{POC:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">Open vs POC</div><div class="anat-val {'c-red' if NY_OPEN_P<POC else 'c-green'}">{'BELOW' if NY_OPEN_P<POC else 'ABOVE'} POC<br>{abs(NY_OPEN_P-POC):,.0f} pts</div></div>
        <div class="anat-item"><div class="anat-label">VAH</div><div class="anat-val c-cyan">{VAH:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">VAL</div><div class="anat-val c-green">{VAL:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">NY High</div><div class="anat-val c-bull">{NY_HIGH:,.2f}</div></div>
        <div class="anat-item"><div class="anat-label">NY Low</div><div class="anat-val c-bear">{NY_LOW:,.2f}</div></div>
      </div>
    </div>
  </div>

</div>

<div class="foot">NQ Whale Radar · Datos reales: NQ=F via yfinance · {n_candles} barras 5min · {tue_str}</div>

<script>
// ═══════════════════════════════════════════════════
// DATOS REALES NQ=F · {tue_str} · {n_candles} barras 5min
// ═══════════════════════════════════════════════════

const POC        = {POC};
const VAH        = {VAH};
const VAL        = {VAL};
const NY_OPEN_P  = {NY_OPEN_P};
const NY_CLOSE_P = {NY_CLOSE_P};
const TZ_OFFSET  = {tz_offset};

const ASIA_START_UTC   = {ts_int(ASIA_START_UTC)};
const LONDON_START_UTC = {ts_int(LONDON_START_UTC)};
const NY_OPEN_UTC      = {ts_int(NY_OPEN_UTC)};
const NY_CLOSE_UTC     = {ts_int(NY_CLOSE_UTC)};

const candles = {CANDLES_JSON};

// ── CHART ─────────────────────────────────────────────────────────────
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
      const h = ((d.getUTCHours() - TZ_OFFSET + 24) % 24);
      const m = d.getUTCMinutes();
      return m === 0 ? `${{h}}:00` : `${{h}}:${{m.toString().padStart(2,'0')}}`;
    }},
  }},
  handleScroll: {{ mouseWheel: true, pressedMouseMove: true }},
  handleScale:  {{ mouseWheel: true, pinch: true }},
}});

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

// Price lines
series.createPriceLine({{ price: VAH, color: 'rgba(0,255,128,0.6)',  lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`VAH ${{VAH.toLocaleString()}}` }});
series.createPriceLine({{ price: POC, color: '#00ff80',              lineWidth:2, lineStyle:0, axisLabelVisible:true, title:`POC ${{POC.toLocaleString()}}` }});
series.createPriceLine({{ price: VAL, color: 'rgba(0,255,128,0.6)',  lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`VAL ${{VAL.toLocaleString()}}` }});
series.createPriceLine({{ price: NY_OPEN_P, color:'rgba(245,158,11,0.8)', lineWidth:1, lineStyle:3, axisLabelVisible:true, title:`NY OPEN ${{NY_OPEN_P.toLocaleString()}}` }});

// Session bands
const bandHigh = Math.max(...candles.map(c => c.high)) + 300;
function addBand(startTs, endTs, topColor, botColor) {{
  const s = chart.addAreaSeries({{ topColor, bottomColor: botColor, lineColor:'rgba(0,0,0,0)', priceScaleId:'left', crosshairMarkerVisible:false }});
  s.setData([{{ time: startTs, value: bandHigh }}, {{ time: endTs, value: bandHigh }}]);
}}
addBand(ASIA_START_UTC,   LONDON_START_UTC, 'rgba(6,182,212,0.10)',  'rgba(6,182,212,0.03)');
addBand(LONDON_START_UTC, NY_OPEN_UTC,      'rgba(245,158,11,0.10)', 'rgba(245,158,11,0.03)');
addBand(NY_OPEN_UTC,      NY_CLOSE_UTC,     'rgba(0,255,128,0.08)',  'rgba(0,255,128,0.02)');

// Session H/L
function sessionHL(from, to) {{
  const s = candles.filter(c => c.time >= from && c.time <= to);
  return s.length ? {{ high: Math.max(...s.map(c=>c.high)), low: Math.min(...s.map(c=>c.low)) }} : null;
}}
const asiaHL = sessionHL(ASIA_START_UTC, LONDON_START_UTC-1);
if (asiaHL) {{
  series.createPriceLine({{ price: asiaHL.high, color:'rgba(6,182,212,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`ASIA H ${{asiaHL.high.toLocaleString()}}` }});
  series.createPriceLine({{ price: asiaHL.low,  color:'rgba(6,182,212,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`ASIA L ${{asiaHL.low.toLocaleString()}}` }});
}}
const lonHL = sessionHL(LONDON_START_UTC, NY_OPEN_UTC-1);
if (lonHL) {{
  series.createPriceLine({{ price: lonHL.high, color:'rgba(245,158,11,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`LON H ${{lonHL.high.toLocaleString()}}` }});
  series.createPriceLine({{ price: lonHL.low,  color:'rgba(245,158,11,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`LON L ${{lonHL.low.toLocaleString()}}` }});
}}
const nyHL = sessionHL(NY_OPEN_UTC, NY_CLOSE_UTC);
if (nyHL) {{
  series.createPriceLine({{ price: nyHL.high, color:'rgba(0,255,128,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`NY H ${{nyHL.high.toLocaleString()}}` }});
  series.createPriceLine({{ price: nyHL.low,  color:'rgba(0,255,128,0.9)', lineWidth:1, lineStyle:2, axisLabelVisible:true, title:`NY L ${{nyHL.low.toLocaleString()}}` }});
}}

// Markers
function nearestCandle(ts) {{
  return candles.reduce((a,b)=>Math.abs(b.time-ts)<Math.abs(a.time-ts)?b:a);
}}
const londonC = nearestCandle(LONDON_START_UTC);
const nyOpenC = nearestCandle(NY_OPEN_UTC);
const nyLowC  = candles.filter(c=>c.time>=NY_OPEN_UTC&&c.time<=NY_CLOSE_UTC).reduce((a,b)=>b.low<a.low?b:a, candles[candles.length-1]);
const nyHighC = candles.filter(c=>c.time>=NY_OPEN_UTC&&c.time<=NY_CLOSE_UTC).reduce((a,b)=>b.high>a.high?b:a, candles[0]);

series.setMarkers([
  {{ time: candles[0].time, position:'belowBar', color:'#06b6d4', shape:'circle',    text:'🌏 Asia 6PM ET' }},
  {{ time: londonC.time,    position:'aboveBar', color:'#f59e0b', shape:'circle',    text:'🇬🇧 London 2AM' }},
  {{ time: nyOpenC.time,    position:'aboveBar', color:'#f59e0b', shape:'circle',    text:`🔔 NY Open ${{NY_OPEN_P.toLocaleString()}}` }},
  {{ time: nyLowC.time,     position:'belowBar', color:'#ef4444', shape:'arrowDown', text:`🎯 LONG Entry ${{nyLowC.low.toLocaleString()}}` }},
  {{ time: nyHighC.time,    position:'aboveBar', color:'#10b981', shape:'arrowUp',   text:`↑ Day High ${{nyHighC.high.toLocaleString()}}` }},
]);

chart.timeScale().fitContent();
window.addEventListener('resize', () => chart.applyOptions({{ width: chartEl.offsetWidth }}));

// ── REPLAY ──────────────────────────────────────────────────────────────────
let rpIndex=0, rpTimer=null, rpSpeed=1, rpRunning=false;
const TICK_MS = 300;

function stageFor(ts) {{
  if (ts < LONDON_START_UTC) return ['🌏 ASIA',   'rgba(6,182,212,0.15)','1px solid rgba(6,182,212,0.3)','#67e8f9'];
  if (ts < NY_OPEN_UTC)      return ['🇬🇧 LONDON','rgba(245,158,11,0.15)','1px solid rgba(245,158,11,0.3)','#fcd34d'];
  return                            ['🗽 NY',      'rgba(16,185,129,0.15)','1px solid rgba(16,185,129,0.4)','#6ee7b7'];
}}
function rpUpdateUI(i) {{
  const pct = candles.length>1?(i/(candles.length-1)*100).toFixed(1):0;
  document.getElementById('rpFill').style.width=pct+'%';
  document.getElementById('rpScrubber').value=pct;
  const c=candles[i];
  const d=new Date(c.time*1000);
  const h=((d.getUTCHours()-TZ_OFFSET+24)%24).toString().padStart(2,'0');
  const m=d.getUTCMinutes().toString().padStart(2,'0');
  document.getElementById('rpTimeDisplay').textContent=`{tue_date.strftime('%b %d')}  ${{h}}:${{m}} ET  C=${{c.close.toLocaleString()}}`;
  document.getElementById('rpCandleCount').textContent=`Vela ${{i+1}} / ${{candles.length}}`;
  const [label,bg,border,color]=stageFor(c.time);
  const badge=document.getElementById('rpStepBadge');
  badge.textContent=label;badge.style.background=bg;badge.style.border=border;badge.style.color=color;
  document.getElementById('rp-narrative-text').textContent=
    `${{label}} — ${{h}}:${{m}} ET · Close: ${{c.close.toLocaleString()}} · H: ${{c.high.toLocaleString()}} · L: ${{c.low.toLocaleString()}}`;
}}
function replayTick() {{
  if (rpIndex>=candles.length){{replayStop();return;}}
  series.setData(candles.slice(0,rpIndex+1));
  rpUpdateUI(rpIndex);
  chart.timeScale().scrollToRealTime();
  rpIndex++;
  rpTimer=setTimeout(replayTick,TICK_MS/rpSpeed);
}}
function replayToggle() {{ if(rpRunning) replayStop(); else replayStart(); }}
function replayStart() {{
  if(rpIndex>=candles.length) replayReset();
  rpRunning=true;
  document.getElementById('rpPlayBtn').textContent='⏸ PAUSE';
  document.getElementById('rpPlayBtn').classList.add('pause');
  replayTick();
}}
function replayStop() {{
  rpRunning=false; clearTimeout(rpTimer);
  document.getElementById('rpPlayBtn').textContent='▶ PLAY';
  document.getElementById('rpPlayBtn').classList.remove('pause');
  if(rpIndex>=candles.length) series.setData(candles);
}}
function replayReset() {{
  replayStop(); rpIndex=0; series.setData(candles);
  document.getElementById('rpFill').style.width='0%';
  document.getElementById('rpScrubber').value=0;
  document.getElementById('rpTimeDisplay').textContent='-- -- : -- --';
  document.getElementById('rpCandleCount').textContent='Vela 0 / 0';
  chart.timeScale().fitContent();
}}
function replayScrub(val) {{
  replayStop();
  rpIndex=Math.round((val/100)*(candles.length-1));
  series.setData(candles.slice(0,rpIndex+1));
  rpUpdateUI(rpIndex);
}}
function setSpeed(s,btn) {{
  rpSpeed=s;
  document.querySelectorAll('.rp-speed').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
}}
function toggleReplayBar() {{
  const bar=document.getElementById('replay-bar');
  const btn=document.getElementById('replayLaunchBtn');
  bar.classList.toggle('visible');
  btn.classList.toggle('active');
}}
</script>

</body>
</html>"""

# ── Guardar ───────────────────────────────────────────────────────────────────
output_file = f"martes_chart_{tue_str.replace('-','')}.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ Generado: {output_file}")
print(f"   Velas: {n_candles}")
print(f"   Day Range: {DAY_HIGH:,.2f} – {DAY_LOW:,.2f} ({round(DAY_HIGH-DAY_LOW,2):,.2f} pts)")
print(f"   NY:  Open={NY_OPEN_P}  High={NY_HIGH}  Low={NY_LOW}  Close={NY_CLOSE_P}")
print(f"   VP:  POC={POC}  VAH={VAH}  VAL={VAL}")
print(f"\n  Uso: python generar_martes_hoy.py")
print(f"       python generar_martes_hoy.py 2026-03-18  (fecha específica)")
