
# -*- coding: utf-8 -*-
"""
Genera lunes_chart_20260323.html con datos reales 5min NQ.
Design system: dark purple/cyan, translucent candles, session boxes, replay engine.
"""
import yfinance as yf
import json, sys
from datetime import datetime, timezone, timedelta

# ── CONFIG ─────────────────────────────────────────────────────
SESSION_META = {
    "2026-03-09": {
        "label": "09-Mar-26",
        "pattern": "NEWS_DRIVE",
        "direction": "BULL",
        "pts": 337,
        "cot": 65.5,
        "signal": "BULL MODERADO"
    }
}

UTC_OFF = 4  # EDT (DST activo en marzo 2026)
OUT_FILE = r"C:\Users\FxDarvin\Desktop\PAgina\lunes_mar09_2026.html"

# ── HELPERS ────────────────────────────────────────────────────
def et_hour(ts_unix, utc_off=UTC_OFF):
    """UTC timestamp → ET hour (float)."""
    import datetime as dt
    d = dt.datetime.utcfromtimestamp(ts_unix)
    h = (d.hour - utc_off + 24) % 24
    return h + d.minute / 60.0

# ── HORARIOS DE SESION (ET) ─────────────────────────────────────
# Solo Asia y NY (London eliminado)
SESSION_RANGES = {
    "asia": (18.0,  5.0),   # 6PM -> 5AM ET  (overnight, apertura CME)
    "ny":   ( 9.5, 17.0),   # 9:30AM -> 5PM ET (cierre CME NQ)
}

def in_session(et_h, sess):
    """True si et_h esta dentro del rango de la sesion."""
    start_h, end_h = SESSION_RANGES[sess]
    if start_h > end_h:   # overnight (Asia: 20->5)
        return et_h >= start_h or et_h < end_h
    return start_h <= et_h < end_h

def build_blocks(candles):
    """Bloques de sesion: Asia (fondo) -> NY (encima)."""
    blocks = []
    for sess in ["asia", "ny"]:
        sess_c = [c for c in candles if in_session(et_hour(c['time']), sess)]
        if sess_c:
            blocks.append({
                "sess":  sess,
                "start": sess_c[0]["time"],
                "end":   sess_c[-1]["time"],
            })
    return blocks

def session_label(k):
    return {"asia": "Asia", "ny": "NY"}.get(k, k)

def compute_vp(candles):
    """Compute VAH, POC, VAL from candle list."""
    tick = 0.25
    vol_at = {}
    for c in candles:
        lo, hi = c['low'], c['high']
        n = max(1, round((hi - lo) / tick))
        vpk = c['volume'] / n
        p = lo
        while p <= hi + 0.001:
            key = round(round(p / tick) * tick, 2)
            vol_at[key] = vol_at.get(key, 0) + vpk
            p += tick
    if not vol_at:
        return None, None, None
    poc = max(vol_at, key=vol_at.get)
    total = sum(vol_at.values())
    target = total * 0.70
    prices = sorted(vol_at)
    pi = prices.index(poc)
    lo_i, hi_i = pi, pi
    cur = vol_at[poc]
    while cur < target:
        up = vol_at[prices[hi_i+1]] if hi_i+1 < len(prices) else 0
        dn = vol_at[prices[lo_i-1]] if lo_i-1 >= 0 else 0
        if up == 0 and dn == 0:
            break
        if up >= dn and hi_i+1 < len(prices):
            hi_i += 1; cur += vol_at[prices[hi_i]]
        else:
            lo_i -= 1; cur += vol_at[prices[lo_i]]
    return prices[hi_i], poc, prices[lo_i]

# ── SESSION WINDOW (datos) ─────────────────────────────────────
# Asia abre Dom 18:00 ET (apertura CME) -> NY cierra Lun 17:00 ET (cierre CME)
EDT = timezone(timedelta(hours=-4))
ASIA_OPEN_TS = int(datetime(2026, 3,  8, 18, 0, tzinfo=EDT).timestamp())  # Dom 6PM ET
NY_CLOSE_TS  = int(datetime(2026, 3,  9, 17, 0, tzinfo=EDT).timestamp())  # Lun 5PM ET
print(f"Window: {datetime.fromtimestamp(ASIA_OPEN_TS, EDT)} -> {datetime.fromtimestamp(NY_CLOSE_TS, EDT)}", file=sys.stderr)

# ── FETCH DATA ─────────────────────────────────────────────────
print("Fetching 5min NQ (2026-03-08 to 2026-03-10)...", file=sys.stderr)
tk = yf.Ticker("NQ=F")
df = tk.history(start="2026-03-08", end="2026-03-10", interval="5m")
if df.empty:
    print("ERROR: No data returned from yfinance", file=sys.stderr)
    sys.exit(1)

all_candles = []
for ts, row in df.iterrows():
    all_candles.append({
        "time": int(ts.timestamp()),
        "open":  round(float(row["Open"]),  2),
        "high":  round(float(row["High"]),  2),
        "low":   round(float(row["Low"]),   2),
        "close": round(float(row["Close"]), 2),
        "volume": int(row["Volume"])
    })

# ── FILTRAR: solo Dom 6PM ET → Lun 4PM ET ─────────────────────
candles_raw = [c for c in all_candles if ASIA_OPEN_TS <= c['time'] <= NY_CLOSE_TS]
print(f"Got {len(all_candles)} total → {len(candles_raw)} candles in window", file=sys.stderr)
if not candles_raw:
    print("ERROR: no candles in window", file=sys.stderr)
    sys.exit(1)

# ── VOLUME PROFILE: Asia open (18:00 ET) -> 10min antes de NY open ──
# Rango: 18:00 ET (dom) -> 9:20 ET (lun).
VP_START_H = 18.0          # Asia abre a las 6PM ET (apertura CME)
VP_END_H   = 9.333         # 9:20 ET = 10min antes de NY open
pre_ny_candles = [
    c for c in candles_raw
    if et_hour(c['time']) >= VP_START_H or et_hour(c['time']) < VP_END_H
]
print(f"VP candles: {len(pre_ny_candles)} (18:00 ET -> 9:20 ET)", file=sys.stderr)
vah, poc, val = compute_vp(pre_ny_candles or candles_raw)
print(f"VP -> VAH={vah} POC={poc} VAL={val}", file=sys.stderr)

# NY candles for high/low markers only (9:30->17:00 ET, cierre CME)
ny_candles = [c for c in candles_raw if 9.5 <= et_hour(c['time']) < 17]

# NY Open price (first candle at 9:30 ET)
ny_open_price = None
for c in candles_raw:
    h = et_hour(c['time'])
    if 9.49 <= h <= 9.51:
        ny_open_price = c['open']
        break

meta = SESSION_META["2026-03-09"]

# ── BUILD SESSION BLOCKS for canvas overlay ───────────────────
blocks = build_blocks(candles_raw)

# ── MARKERS ───────────────────────────────────────────────────
markers = []
for c in candles_raw:
    h = et_hour(c['time'])
    if 18.0 <= h <= 18.01:
        markers.append({"time": c['time'], "position": "belowBar", "color": "#06b6d4",
                         "shape": "circle", "text": "🌏 Asia"})
    if 2.0 <= h <= 2.01:
        markers.append({"time": c['time'], "position": "aboveBar", "color": "#f59e0b",
                         "shape": "circle", "text": "🇬🇧 Lon"})
    if 9.49 <= h <= 9.51:
        markers.append({"time": c['time'], "position": "aboveBar", "color": "#f59e0b",
                         "shape": "circle", "text": "🔔 NY"})

ny_h = max((c for c in ny_candles), key=lambda x: x['high'], default=None)
ny_l = min((c for c in ny_candles), key=lambda x: x['low'],  default=None)
if ny_h:
    markers.append({"time": ny_h['time'], "position": "aboveBar", "color": "#10b981",
                     "shape": "arrowUp", "text": "↑ H"})
if ny_l:
    markers.append({"time": ny_l['time'], "position": "belowBar", "color": "#ef4444",
                     "shape": "arrowDown", "text": "↓ L"})

markers.sort(key=lambda x: x['time'])

# Day range
day_range = max(c['high'] for c in candles_raw) - min(c['low'] for c in candles_raw)
open_p  = candles_raw[0]['open']
close_p = candles_raw[-1]['close']
chg     = close_p - open_p

# ── HTML TEMPLATE ──────────────────────────────────────────────
CANDLES_JS  = json.dumps(candles_raw)
BLOCKS_JS   = json.dumps(blocks)
MARKERS_JS  = json.dumps(markers)
VAH_JS      = json.dumps(vah)
POC_JS      = json.dumps(poc)
VAL_JS      = json.dumps(val)
NYOPEN_JS   = json.dumps(ny_open_price)

DIRECTION_COLOR = "#10b981" if meta['direction'] == "BULL" else "#ef4444"
DIRECTION_ICON  = "📈" if meta['direction'] == "BULL" else "📉"
CHG_COLOR = "#10b981" if chg >= 0 else "#ef4444"
CHG_SIGN  = "+" if chg >= 0 else ""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NQ Lunes {meta['label']} · 5min · Whale Radar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
/* ── RESET ── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

/* ── TOKENS ── */
:root{{
  --bg:#04020c;
  --card-bg:#0c0a1e;
  --card-border:#1a1530;
  --text:#e2e8f0;
  --muted:#64748b;
  --purple:#7c3aed;
  --cyan:#06b6d4;
  --green:#10b981;
  --red:#ef4444;
  --amber:#f59e0b;
  --white:rgba(255,255,255,0.88);
  --font-ui:'Inter',sans-serif;
  --font-mono:'JetBrains Mono',monospace;
}}

body{{background:var(--bg);color:var(--text);font-family:var(--font-ui);min-height:100vh;padding:24px 20px 48px}}

/* ── PAGE HEADER ── */
.page-header{{max-width:1280px;margin:0 auto 28px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}}
.page-header h1{{font-size:1.35rem;font-weight:700;letter-spacing:-0.5px}}
.page-header h1 span{{color:var(--cyan)}}
.badge{{display:inline-flex;align-items:center;gap:5px;font-size:.72rem;font-weight:600;padding:3px 10px;border-radius:20px;border:1px solid;letter-spacing:.4px;text-transform:uppercase}}
.badge.bull{{color:var(--green);border-color:rgba(16,185,129,.35);background:rgba(16,185,129,.08)}}
.badge.bear{{color:var(--red);border-color:rgba(239,68,68,.35);background:rgba(239,68,68,.08)}}

/* ── STATS ROW ── */
.stats{{max-width:1280px;margin:0 auto 24px;display:flex;gap:12px;flex-wrap:wrap}}
.stat{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:12px 18px;flex:1 1 140px}}
.stat label{{font-size:.68rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:4px}}
.stat value{{font-family:var(--font-mono);font-size:1.05rem;font-weight:600}}

/* ── CHART CARD ── */
.card{{max-width:1280px;margin:0 auto;background:var(--card-bg);border:1px solid var(--card-border);border-radius:14px;overflow:hidden}}
.card-header{{padding:14px 18px;border-bottom:1px solid var(--card-border);display:flex;align-items:center;gap:12px;flex-wrap:wrap}}
.card-header h2{{font-size:.95rem;font-weight:600;color:var(--text)}}
.legend{{display:flex;gap:14px;margin-left:auto;flex-wrap:wrap}}
.leg{{display:flex;align-items:center;gap:5px;font-size:.7rem;color:var(--muted)}}
.leg-line{{width:20px;height:2px}}
.leg-line.vah,.leg-line.val{{background:rgba(255,255,255,.7);opacity:.7;border-top:2px dashed rgba(255,255,255,.7);height:0}}
.leg-line.poc{{background:#ef4444;height:2px}}
.leg-line.nyo{{border-top:2px dotted #f59e0b;height:0;width:20px}}

/* ── CHART WRAPPER (position:relative for canvas overlay) ── */
.chart-wrap{{position:relative;height:520px}}
.chart-wrap > div{{height:100%!important}}

/* ── SESSION CANVAS OVERLAY ── */
.sess-canvas{{position:absolute;top:0;left:0;pointer-events:none;z-index:2}}

/* ── REPLAY BAR ── */
.replay-bar{{display:flex;align-items:center;gap:10px;padding:9px 14px;background:#08061a;border-top:1px solid var(--card-border)}}
.rp-play{{width:30px;height:30px;border-radius:50%;background:var(--purple);border:none;color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:.9rem;flex-shrink:0;transition:background .15s}}
.rp-play:hover{{background:#6d28d9}}
.rp-scrub{{flex:1;height:4px;accent-color:var(--cyan);cursor:pointer}}
.rp-speeds{{display:flex;gap:4px}}
.rp-spd{{padding:3px 8px;border-radius:6px;border:1px solid var(--card-border);background:transparent;color:var(--muted);font-size:.68rem;font-family:var(--font-mono);cursor:pointer;transition:all .15s}}
.rp-spd.active,.rp-spd:hover{{background:rgba(124,58,237,.3);color:var(--cyan);border-color:var(--purple)}}
.rp-sess{{font-size:.7rem;font-weight:600;padding:3px 9px;border-radius:12px;border:1px solid;white-space:nowrap}}
.rp-sess.asia{{color:var(--cyan);border-color:rgba(6,182,212,.3);background:rgba(6,182,212,.08)}}
.rp-sess.london{{color:var(--amber);border-color:rgba(245,158,11,.3);background:rgba(245,158,11,.08)}}
.rp-sess.ny{{color:var(--green);border-color:rgba(16,185,129,.3);background:rgba(16,185,129,.08)}}
.rp-counter{{font-family:var(--font-mono);font-size:.68rem;color:var(--muted);white-space:nowrap}}

/* ── TOOLTIP ── */
.tt{{position:fixed;display:none;background:rgba(8,6,26,.95);border:1px solid rgba(124,58,237,.4);border-radius:10px;padding:10px 13px;font-size:.73rem;line-height:1.7;z-index:999;pointer-events:none;backdrop-filter:blur(6px)}}
.tt b{{color:var(--cyan);font-family:var(--font-mono)}}
</style>
</head>
<body>

<!-- PAGE HEADER -->
<header class="page-header">
  <h1>🐋 NQ Lunes <span>{meta['label']}</span> · 5min</h1>
  <div class="badge {'bull' if meta['direction'] == 'BULL' else 'bear'}">{DIRECTION_ICON} {meta['direction']}</div>
  <div class="badge" style="color:var(--cyan);border-color:rgba(6,182,212,.3);background:rgba(6,182,212,.08)">
    {meta['pattern']}
  </div>
  <div class="badge" style="color:var(--muted);border-color:rgba(100,116,139,.2)">
    COT {meta['cot']} · {meta['signal']}
  </div>
</header>

<!-- STATS -->
<div class="stats">
  <div class="stat">
    <label>Apertura</label>
    <value style="font-family:var(--font-mono)">{open_p:.2f}</value>
  </div>
  <div class="stat">
    <label>Cierre</label>
    <value style="font-family:var(--font-mono);color:{CHG_COLOR}">{close_p:.2f}</value>
  </div>
  <div class="stat">
    <label>Movimiento Día</label>
    <value style="font-family:var(--font-mono);color:{CHG_COLOR}">{CHG_SIGN}{chg:.0f} pts</value>
  </div>
  <div class="stat">
    <label>Rango Total</label>
    <value style="font-family:var(--font-mono)">{day_range:.0f} pts</value>
  </div>
  <div class="stat">
    <label>Candles 5min</label>
    <value style="font-family:var(--font-mono)">{len(candles_raw)}</value>
  </div>
</div>

<!-- CHART CARD -->
<div class="card">
  <div class="card-header">
    <h2>📊 5min · NQ Futures · {meta['label']}</h2>
    <div class="legend">
      <div class="leg"><div class="leg-line vah"></div> VAH</div>
      <div class="leg"><div class="leg-line poc"></div> POC</div>
      <div class="leg"><div class="leg-line val"></div> VAL</div>
      <div class="leg"><div class="leg-line nyo"></div> NY Open</div>
    </div>
  </div>

  <!-- Chart wrapper (canvas overlay will be appended here) -->
  <div class="chart-wrap" id="chart-wrap">
    <div id="chart"></div>
  </div>

  <!-- Replay Bar -->
  <div class="replay-bar" id="rp-bar">
    <button class="rp-play" id="rp-play" title="Play/Pause">&#9654;</button>
    <input type="range" class="rp-scrub" id="rp-scrub" min="0" value="0">
    <div class="rp-speeds">
      <button class="rp-spd active" data-spd="1">1x</button>
      <button class="rp-spd" data-spd="3">3x</button>
      <button class="rp-spd" data-spd="8">8x</button>
      <button class="rp-spd" data-spd="20">20x</button>
      <button class="rp-spd" data-spd="50">50x</button>
    </div>
    <span class="rp-sess asia" id="rp-sess">🌏 Asia</span>
    <span class="rp-counter" id="rp-cnt">0 / {len(candles_raw)}</span>
  </div>
</div>

<!-- Tooltip -->
<div class="tt" id="tt"></div>

<script>
/* ── DATA ───────────────────────────────────────── */
const CANDLES = {CANDLES_JS};
const BLOCKS  = {BLOCKS_JS};
const MARKERS = {MARKERS_JS};
const VAH     = {VAH_JS};
const POC     = {POC_JS};
const VAL     = {VAL_JS};
const NY_OPEN = {NYOPEN_JS};
const TOTAL   = CANDLES.length;

/* ── SESSION COLORS & LABELS ────────────────────── */
const SESS_CFG = {{
  asia: {{ fill:'rgba(6,182,212,0.04)',  stroke:'rgba(6,182,212,0.45)',  label:'🌏 Asia  6PM–5AM ET'   }},
  ny:   {{ fill:'rgba(16,185,129,0.04)', stroke:'rgba(16,185,129,0.45)', label:'🗽 NY    9:30AM–5PM ET' }}
}};

/* ── BUILD LIGHTWEIGHT-CHART ──────────────────────── */
const wrap = document.getElementById('chart-wrap');
const el   = document.getElementById('chart');
el.style.height = '100%';

const chart = LightweightCharts.createChart(el, {{
  width:  wrap.clientWidth,
  height: wrap.clientHeight,
  layout: {{
    background: {{ type: LightweightCharts.ColorType.Solid, color: '#0c0a1e' }},
    textColor: '#94a3b8',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: 11
  }},
  grid: {{
    vertLines: {{ color: 'rgba(124,58,237,0.06)' }},
    horzLines: {{ color: 'rgba(124,58,237,0.06)' }}
  }},
  crosshair: {{
    mode: LightweightCharts.CrosshairMode.Normal,
    vertLine: {{ color: 'rgba(6,182,212,0.5)', style: LightweightCharts.LineStyle.Dashed, width: 1 }},
    horzLine: {{ color: 'rgba(6,182,212,0.5)', style: LightweightCharts.LineStyle.Dashed, width: 1 }}
  }},
  rightPriceScale: {{
    borderColor: '#1a1530',
    scaleMargins: {{ top: 0.08, bottom: 0.08 }}
  }},
  timeScale: {{
    borderColor: '#1a1530',
    timeVisible: true,
    secondsVisible: false,
    tickMarkFormatter: (t) => {{
      const d = new Date(t * 1000);
      const etH = ((d.getUTCHours() - 4) + 24) % 24;
      const m   = String(d.getUTCMinutes()).padStart(2,'0');
      return `${{etH}}:${{m}}`;
    }}
  }}
}});

/* ── CANDLESTICK SERIES ──────────────────────────── */
const cs = chart.addCandlestickSeries({{
  upColor:         'rgba(16,185,129,0.08)',
  downColor:       'rgba(139,92,246,0.08)',
  borderUpColor:   '#10b981',
  borderDownColor: '#8b5cf6',
  wickUpColor:     '#10b981',
  wickDownColor:   '#8b5cf6',
  borderVisible: true,
  wickVisible: true
}});

/* ── PRICE LINES ──────────────────────────────────── */
const t0 = CANDLES[0].time;
const tN = CANDLES[CANDLES.length-1].time;

function addHorizLine(price, color, style, width, title) {{
  if (!price) return;
  const s = chart.addLineSeries({{
    color, lineStyle: style, lineWidth: width,
    priceLineVisible: false, lastValueVisible: true, title
  }});
  s.setData([{{time:t0,value:price}},{{time:tN,value:price}}]);
}}

// VAH / VAL — white rgba dashed
addHorizLine(VAH, 'rgba(255,255,255,0.85)', LightweightCharts.LineStyle.Dashed, 1, 'VAH');
addHorizLine(VAL, 'rgba(255,255,255,0.85)', LightweightCharts.LineStyle.Dashed, 1, 'VAL');
// POC — red solid
addHorizLine(POC, '#ef4444', LightweightCharts.LineStyle.Solid, 2, 'POC');
// NY Open — amber dotted
addHorizLine(NY_OPEN, '#f59e0b', LightweightCharts.LineStyle.Dotted, 1, 'NY Open');

/* ── MARKERS ─────────────────────────────────────── */
cs.setMarkers(MARKERS);

/* ── CANVAS OVERLAY: SESSION BOXES ───────────────── */
const canvas = document.createElement('canvas');
canvas.className = 'sess-canvas';
wrap.appendChild(canvas);

function drawSessBg() {{
  const rect = wrap.getBoundingClientRect();
  canvas.width  = wrap.clientWidth;
  canvas.height = wrap.clientHeight;
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  BLOCKS.forEach(b => {{
    const cfg = SESS_CFG[b.sess];
    if (!cfg) return;
    const x1 = chart.timeScale().timeToCoordinate(b.start);
    // +300s = un bar de 5min → right edge cubre la última vela completa
    // Esto hace que las sesiones queden pegadas sin gap entre ellas
    const endTs = b.end + 300;
    const x2raw = chart.timeScale().timeToCoordinate(endTs);
    // Fallback: si endTs está fuera del rango visible, usar b.end
    const x2 = x2raw ?? chart.timeScale().timeToCoordinate(b.end);
    if (x1 == null || x2 == null) return;
    const left  = Math.min(x1, x2);
    const width = Math.abs(x2 - x1);
    const h     = canvas.height;

    // Session background fill
    ctx.fillStyle = cfg.fill;
    ctx.fillRect(left, 0, width, h);

    // Left edge (dashed vertical line)
    ctx.save();
    ctx.strokeStyle = cfg.stroke;
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(left, 0);
    ctx.lineTo(left, h);
    ctx.stroke();

    // Right edge
    ctx.beginPath();
    ctx.moveTo(left + width, 0);
    ctx.lineTo(left + width, h);
    ctx.stroke();
    ctx.restore();

    // Session label badge (top of box)
    const badgeX = left + 8;
    const badgeY = 8;
    const text   = cfg.label;
    ctx.font = '11px Inter, sans-serif';
    const tw = ctx.measureText(text).width;
    const bw = tw + 14;
    const bh = 20;

    // Badge background
    ctx.fillStyle = cfg.fill.replace('0.03)', '0.25)');
    ctx.beginPath();
    ctx.roundRect(badgeX, badgeY, bw, bh, 4);
    ctx.fill();

    // Badge border
    ctx.strokeStyle = cfg.stroke;
    ctx.lineWidth = 0.5;
    ctx.setLineDash([]);
    ctx.stroke();

    // Badge text
    ctx.fillStyle = cfg.stroke;
    ctx.fillText(text, badgeX + 7, badgeY + 14);
  }});
}}

chart.timeScale().subscribeVisibleTimeRangeChange(drawSessBg);
window.addEventListener('resize', () => {{
  chart.applyOptions({{ width: wrap.clientWidth, height: wrap.clientHeight }});
  drawSessBg();
}});

/* ── REPLAY ENGINE ──────────────────────────────── */
let rpIdx    = 0;
let rpPlaying = false;
let rpSpeed   = 1;
let rpTimer   = null;
const BASE_MS = 300;

const playBtn = document.getElementById('rp-play');
const scrub   = document.getElementById('rp-scrub');
const sessBdg = document.getElementById('rp-sess');
const cntEl   = document.getElementById('rp-cnt');

scrub.max = TOTAL - 1;

function sessClass(t) {{
  const d = new Date(t * 1000);
  const h = ((d.getUTCHours() - 4) + 24) % 24 + d.getUTCMinutes()/60;
  // NY: 9:30 – 17:00 ET (priority)
  if (h >= 9.5 && h < 17) return ['ny',   '🗽 NY  9:30AM–5PM ET'];
  // Asia: 18:00 – 5:00 ET
  return ['asia', '🌏 Asia 6PM–5AM ET'];
}}

function rpRender(idx) {{
  if (idx < 0 || idx >= TOTAL) return;
  const slice = CANDLES.slice(0, idx + 1);
  cs.setData(slice);
  // Redraw canvas overlay
  drawSessBg();

  const [cls, lbl] = sessClass(CANDLES[idx].time);
  sessBdg.className = `rp-sess ${{cls}}`;
  sessBdg.textContent = lbl;
  cntEl.textContent = `${{idx + 1}} / ${{TOTAL}}`;
  scrub.value = idx;
}}

function rpStep() {{
  if (rpIdx < TOTAL - 1) {{
    rpIdx++;
    rpRender(rpIdx);
  }} else {{
    rpStop();
  }}
}}

function rpStop() {{
  rpPlaying = false;
  playBtn.innerHTML = '&#9654;';
  clearInterval(rpTimer);
  rpTimer = null;
}}

function rpStart() {{
  if (rpIdx >= TOTAL - 1) rpIdx = 0;
  rpPlaying = true;
  playBtn.innerHTML = '&#9646;&#9646;';
  rpTimer = setInterval(rpStep, BASE_MS / rpSpeed);
}}

playBtn.addEventListener('click', () => {{
  if (rpPlaying) {{ rpStop(); }} else {{ rpStart(); }}
}});

scrub.addEventListener('input', () => {{
  rpIdx = parseInt(scrub.value);
  rpRender(rpIdx);
}});

document.querySelectorAll('.rp-spd').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.rp-spd').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    rpSpeed = parseInt(btn.dataset.spd);
    if (rpPlaying) {{
      clearInterval(rpTimer);
      rpTimer = setInterval(rpStep, BASE_MS / rpSpeed);
    }}
  }});
}});

/* ── TOOLTIP ─────────────────────────────────────── */
const tt = document.getElementById('tt');
chart.subscribeCrosshairMove(param => {{
  if (!param || !param.point || !param.time) {{ tt.style.display='none'; return; }}
  const cv = param.seriesData.get(cs);
  if (!cv) {{ tt.style.display='none'; return; }}
  const d = new Date(param.time * 1000);
  const etH = ((d.getUTCHours()-4)+24)%24;
  const etM = String(d.getUTCMinutes()).padStart(2,'0');
  const [,slbl] = sessClass(param.time);
  const chg2 = cv.close - cv.open;
  const c2 = chg2>=0?'#10b981':'#ef4444';
  const sign2 = chg2>=0?'+':'';
  tt.innerHTML = `
    <div style="color:#94a3b8;margin-bottom:4px">${{slbl}} · ${{etH}}:${{etM}} ET</div>
    <div>O <b>${{cv.open.toFixed(2)}}</b> H <b>${{cv.high.toFixed(2)}}</b></div>
    <div>L <b>${{cv.low.toFixed(2)}}</b>  C <b>${{cv.close.toFixed(2)}}</b></div>
    <div style="color:${{c2}}">${{sign2}}${{chg2.toFixed(2)}} pts</div>
  `;
  tt.style.display='block';
  const rect = el.getBoundingClientRect();
  tt.style.left = Math.min(param.point.x+rect.left+18, window.innerWidth-180)+'px';
  tt.style.top  = Math.max(param.point.y+rect.top-90,  8)+'px';
}});

/* ── INIT ────────────────────────────────────────── */
// Show all candles initially
cs.setData(CANDLES);
chart.timeScale().fitContent();
setTimeout(drawSessBg, 200);
</script>
</body>
</html>"""

with open(OUT_FILE, "w", encoding="utf-8") as f:
    f.write(html)

print(f"✅ Written: {OUT_FILE}")
print(f"   Candles: {len(candles_raw)}")
print(f"   VP: VAH={vah} POC={poc} VAL={val}")
print(f"   NY Open: {ny_open_price}")
