"""
PANEL COMBINADO: Los 3 Tipos de Martes con Noticias Fijas
==========================================================
Genera un panel HTML con estadísticas comparativas de:
  1. CB Consumer Confidence (último martes del mes)
  2. JOLTS Job Openings    (primer martes del mes)
  3. PPI                   (cuando cae en martes)
Genera: tuesday_news_comparison.html
"""
import yfinance as yf, pandas as pd
from pathlib import Path

# ── DATOS ─────────────────────────────────────────────────────────────────────
CB_DATES = {
    "2024-03-26": {"bm": "MISS"},  "2024-04-30": {"bm": "MISS"},
    "2024-05-28": {"bm": "BEAT"},  "2024-06-25": {"bm": "BEAT"},
    "2024-07-30": {"bm": "BEAT"},  "2024-08-27": {"bm": "BEAT"},
    "2024-09-24": {"bm": "MISS"},  "2024-10-29": {"bm": "MISS"},
    "2024-11-26": {"bm": "BEAT"},  "2024-12-17": {"bm": "MISS"},
    "2025-01-28": {"bm": "MISS"},  "2025-02-25": {"bm": "MISS"},
    "2025-03-25": {"bm": "MISS"},
}
JOLTS_DATES = {
    "2024-04-02": {"bm": "BEAT"},  "2024-05-07": {"bm": "MISS"},
    "2024-06-04": {"bm": "MISS"},  "2024-07-30": {"bm": "BEAT"},
    "2024-08-06": {"bm": "MISS"},  "2024-09-04": {"bm": "BEAT"},
    "2024-10-01": {"bm": "MISS"},  "2024-11-05": {"bm": "MISS"},
    "2024-12-03": {"bm": "BEAT"},  "2025-01-07": {"bm": "BEAT"},
    "2025-02-04": {"bm": "MISS"},  "2025-03-11": {"bm": "MISS"},
}
PPI_DATES = {
    "2024-04-11": {"bm": "MISS"},  "2024-06-11": {"bm": "FRIO"},
    "2024-08-13": {"bm": "FRIO"},  "2024-10-08": {"bm": "FRIO"},
    "2024-12-10": {"bm": "CAL"},   "2025-02-11": {"bm": "CAL"},
}

print("📥 Descargando NQ=F...")
df = yf.download("NQ=F", period="2y", interval="1d", auto_adjust=True, progress=False)
if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index).normalize()

def get_stats(dates_dict):
    rows = []
    for d, meta in sorted(dates_dict.items()):
        ts = pd.Timestamp(d)
        if ts not in df.index: continue
        r    = df.loc[ts]
        op   = float(r["Open"]); hi = float(r["High"])
        lo   = float(r["Low"]);  cl = float(r["Close"])
        rng  = round(hi - lo)
        move = round(cl - op)
        bull = cl >= op
        rows.append({"date": d, "rng": rng, "move": move, "bull": bull, "bm": meta["bm"]})
    if not rows: return {}
    n    = len(rows)
    bull_days = sum(1 for r in rows if r["bull"])
    return {
        "n":         n,
        "bull_pct":  round(bull_days / n * 100),
        "avg_rng":   round(sum(r["rng"]  for r in rows) / n),
        "avg_move":  round(sum(r["move"] for r in rows) / n),
        "max_rng":   max(r["rng"] for r in rows),
        "rows":      rows,
    }

cb_s    = get_stats(CB_DATES)
jolts_s = get_stats(JOLTS_DATES)
ppi_s   = get_stats(PPI_DATES)

def stat_rows(rows):
    html = ""
    for r in reversed(rows):
        dc = "▲" if r["bull"] else "▼"
        mc = "#22c55e" if r["bull"] else "#ef4444"
        ms = f"+{r['move']}" if r["move"] >= 0 else str(r["move"])
        html += f"""<tr>
          <td style="color:#94a3b8;font-size:.74rem">{r['date']}</td>
          <td style="text-align:right">{r['rng']}</td>
          <td style="text-align:right;color:{mc}">{ms}</td>
          <td style="text-align:center;color:{mc}">{dc}</td>
        </tr>"""
    return html

def bull_bar(pct):
    return f"""<div style="background:#1e293b;border-radius:4px;height:8px;overflow:hidden;margin-top:4px">
      <div style="background:#22c55e;width:{pct}%;height:100%;border-radius:4px"></div></div>"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Comparativa: Tipos de Martes NQ</title>
<style>
  *{{ margin:0; padding:0; box-sizing:border-box }}
  body{{ background:#0b0f1a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:24px 18px }}
  h1{{ font-size:1.35rem; color:#7dd3fc; margin-bottom:4px }}
  .sub{{ font-size:.8rem; color:#475569; margin-bottom:24px }}

  /* 3-col grid */
  .grid3{{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; margin-bottom:28px }}
  @media(max-width:700px){{ .grid3{{ grid-template-columns:1fr }} }}

  .card{{ background:#111827; border-radius:12px; padding:18px; border-top:3px solid var(--c) }}
  .card h2{{ font-size:.9rem; color:var(--c); margin-bottom:14px }}
  .card .lbl{{ font-size:.65rem; color:#64748b; text-transform:uppercase; letter-spacing:.05em; margin-top:10px }}
  .card .val{{ font-size:1.4rem; font-weight:700; color:#f1f5f9 }}
  .card .small{{ font-size:.72rem; color:#94a3b8 }}

  /* Timing badges */
  .badge{{ display:inline-block; padding:2px 8px; border-radius:12px; font-size:.68rem; font-weight:600 }}

  /* Mini table */
  .mini-table{{ width:100%; border-collapse:collapse; font-size:.76rem; margin-top:12px }}
  .mini-table th{{ color:#475569; font-size:.63rem; text-transform:uppercase; padding:3px 6px; border-bottom:1px solid #1e293b; text-align:left }}
  .mini-table td{{ padding:4px 6px; border-bottom:1px solid #1e293b44 }}

  /* insight */
  .insight{{ margin-top:28px; background:#111827; border-radius:12px; padding:18px }}
  .insight h3{{ font-size:.85rem; color:#94a3b8; margin-bottom:12px }}
  .rows{{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:8px }}
  .insight-row{{ background:#0f172a; border-radius:8px; padding:10px 14px; font-size:.79rem }}
  .insight-row .title{{ color:#64748b; font-size:.67rem; text-transform:uppercase; margin-bottom:4px }}

  .nav{{ display:flex; gap:10px; margin-bottom:20px; flex-wrap:wrap }}
  .nav a{{ background:#1e293b; color:#94a3b8; padding:6px 14px; border-radius:8px; text-decoration:none; font-size:.78rem; transition:background .15s }}
  .nav a:hover{{ background:#334155; color:#e2e8f0 }}
</style>
</head>
<body>
<h1>📅 Comparativa: Tipos de Martes × NQ Futures</h1>
<p class="sub">Backtest de las 3 noticias económicas que SIEMPRE caen en martes — 2024/2026</p>

<div class="nav">
  <a href="backtest_CB_confidence.html">📊 CB Consumer Confidence</a>
  <a href="backtest_JOLTS.html">💼 JOLTS Job Openings</a>
  <a href="backtest_PPI_martes.html">🌡️ PPI (Martes)</a>
  <a href="martes_cb_patrones.html">🔬 Martes CB Patrones</a>
</div>

<div class="grid3">

  <!-- CB -->
  <div class="card" style="--c:#60a5fa">
    <h2>📊 CB Consumer Confidence</h2>
    <span class="badge" style="background:#1e3a5f;color:#60a5fa">Último martes del mes · 10:00 AM ET</span>
    <div class="lbl">Sesiones</div><div class="val">{cb_s['n']}</div>
    <div class="lbl">% Días BULL</div>
    <div class="val" style="color:#22c55e">{cb_s['bull_pct']}%</div>
    {bull_bar(cb_s['bull_pct'])}
    <div class="lbl">Avg Range</div><div class="val">{cb_s['avg_rng']} <span style="font-size:.8rem;color:#64748b">pts</span></div>
    <div class="lbl">Avg Move (O→C)</div><div class="val" style="color:{'#22c55e' if cb_s['avg_move']>=0 else '#ef4444'}">{cb_s['avg_move']:+}</div>
    <div class="lbl">Max Range</div><div class="small">{cb_s['max_rng']} pts</div>
    <table class="mini-table">
      <thead><tr><th>Fecha</th><th>Range</th><th>Move</th><th></th></tr></thead>
      <tbody>{stat_rows(cb_s['rows'])}</tbody>
    </table>
  </div>

  <!-- JOLTS -->
  <div class="card" style="--c:#34d399">
    <h2>💼 JOLTS Job Openings</h2>
    <span class="badge" style="background:#0f2d22;color:#34d399">Primer martes del mes · 10:00 AM ET</span>
    <div class="lbl">Sesiones</div><div class="val">{jolts_s['n']}</div>
    <div class="lbl">% Días BULL</div>
    <div class="val" style="color:#22c55e">{jolts_s['bull_pct']}%</div>
    {bull_bar(jolts_s['bull_pct'])}
    <div class="lbl">Avg Range</div><div class="val">{jolts_s['avg_rng']} <span style="font-size:.8rem;color:#64748b">pts</span></div>
    <div class="lbl">Avg Move (O→C)</div><div class="val" style="color:{'#22c55e' if jolts_s['avg_move']>=0 else '#ef4444'}">{jolts_s['avg_move']:+}</div>
    <div class="lbl">Max Range</div><div class="small">{jolts_s['max_rng']} pts</div>
    <table class="mini-table">
      <thead><tr><th>Fecha</th><th>Range</th><th>Move</th><th></th></tr></thead>
      <tbody>{stat_rows(jolts_s['rows'])}</tbody>
    </table>
  </div>

  <!-- PPI -->
  <div class="card" style="--c:#fb923c">
    <h2>🌡️ PPI (cuando cae martes)</h2>
    <span class="badge" style="background:#2d1a0b;color:#fb923c">Variable · 8:30 AM ET</span>
    <div class="lbl">Sesiones</div><div class="val">{ppi_s['n']}</div>
    <div class="lbl">% Días BULL</div>
    <div class="val" style="color:#22c55e">{ppi_s['bull_pct']}%</div>
    {bull_bar(ppi_s['bull_pct'])}
    <div class="lbl">Avg Range</div><div class="val">{ppi_s['avg_rng']} <span style="font-size:.8rem;color:#64748b">pts</span></div>
    <div class="lbl">Avg Move (O→C)</div><div class="val" style="color:{'#22c55e' if ppi_s['avg_move']>=0 else '#ef4444'}">{ppi_s['avg_move']:+}</div>
    <div class="lbl">Max Range</div><div class="small">{ppi_s['max_rng']} pts</div>
    <table class="mini-table">
      <thead><tr><th>Fecha</th><th>Range</th><th>Move</th><th></th></tr></thead>
      <tbody>{stat_rows(ppi_s['rows'])}</tbody>
    </table>
  </div>

</div>

<div class="insight">
  <h3>🔍 Insights Comparativos</h3>
  <div class="rows">
    <div class="insight-row">
      <div class="title">Mayor Range Promedio</div>
      <div style="color:#f97316;font-size:1rem;font-weight:700">
        {'PPI' if ppi_s['avg_rng']>=cb_s['avg_rng'] and ppi_s['avg_rng']>=jolts_s['avg_rng'] else 'JOLTS' if jolts_s['avg_rng']>=cb_s['avg_rng'] else 'CB'}
        — {max(cb_s['avg_rng'], jolts_s['avg_rng'], ppi_s['avg_rng'])} pts
      </div>
    </div>
    <div class="insight-row">
      <div class="title">Más Alcista (% Bull)</div>
      <div style="color:#22c55e;font-size:1rem;font-weight:700">
        {'PPI' if ppi_s['bull_pct']>=cb_s['bull_pct'] and ppi_s['bull_pct']>=jolts_s['bull_pct'] else 'CB' if cb_s['bull_pct']>=jolts_s['bull_pct'] else 'JOLTS'}
        — {max(cb_s['bull_pct'], jolts_s['bull_pct'], ppi_s['bull_pct'])}%
      </div>
    </div>
    <div class="insight-row">
      <div class="title">CB — Dato clave</div>
      <div style="font-size:.82rem">BEAT → <span style="color:#22c55e">83% Bull · +48 pts</span><br>MISS → <span style="color:#ef4444">43% Bull · -38 pts</span></div>
    </div>
    <div class="insight-row">
      <div class="title">JOLTS — Dato clave</div>
      <div style="font-size:.82rem">BEAT → <span style="color:#ef4444">20% Bull · -168 pts</span> ⚠️<br>MISS → <span style="color:#22c55e">71% Bull · +7 pts</span></div>
    </div>
    <div class="insight-row">
      <div class="title">JOLTS Paradoja 🤔</div>
      <div style="font-size:.79rem;color:#94a3b8">Más trabajos disponibles (BEAT) → mercado cae. Menos empleos (MISS) → mercado sube. Posible: BEAT JOLTS = Fed más hawkish = NQ baja.</div>
    </div>
    <div class="insight-row">
      <div class="title">PPI 8:30 AM ET</div>
      <div style="font-size:.82rem">PPI cae <b>antes</b> que CB/JOLTS → afecta el gap de apertura más que la sesión completa.</div>
    </div>
  </div>
</div>

<div style="margin-top:14px;font-size:.71rem;color:#334155;border-left:2px solid #1e293b;padding-left:10px">
  Datos: yfinance · NQ=F OHLC diario · 2024-2026<br>
  Move = Close − Open (sesión completa) · Range = High − Low
</div>
</body>
</html>"""

out = Path("tuesday_news_comparison.html")
out.write_text(html, encoding="utf-8")
print(f"✅ Panel combinado: {out.resolve()}")
