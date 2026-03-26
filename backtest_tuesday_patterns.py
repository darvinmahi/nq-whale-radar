"""
BACKTEST PATRONES MARTES — Por Tipo de Noticia
================================================
Para cada tipo de noticia de martes, calcula qué patrón OHLC
se da con mayor frecuencia. El objetivo NO es bull/bear,
sino identificar el patrón dominante de precio.

Genera: tuesday_patterns.html
"""
import yfinance as yf, pandas as pd
from collections import Counter
from pathlib import Path

# ── FECHAS ────────────────────────────────────────────────────────────────────
CB_DATES = [
    "2024-03-26","2024-04-30","2024-05-28","2024-06-25","2024-07-30",
    "2024-08-27","2024-09-24","2024-10-29","2024-11-26","2024-12-17",
    "2025-01-28","2025-02-25","2025-03-25",
]
JOLTS_DATES = [
    "2024-04-02","2024-05-07","2024-06-04","2024-07-30","2024-08-06",
    "2024-09-04","2024-10-01","2024-11-05","2024-12-03","2025-01-07",
    "2025-02-04","2025-03-11",
]
PPI_DATES = [
    "2024-04-11","2024-06-11","2024-08-13","2024-10-08","2024-12-10","2025-02-11",
]

# ── CLASIFICADOR DE PATRÓN (más granular) ─────────────────────────────────────
def classify_pattern(op, hi, lo, cl):
    if hi == lo:
        return "RANGO ESTRECHO"
    rng        = hi - lo
    body       = abs(cl - op)
    body_pct   = body / rng
    bull       = cl >= op
    upper_wick = hi - max(op, cl)
    lower_wick = min(op, cl) - lo
    close_pct  = (cl - lo) / rng   # 0=cierra en mínimo, 1=cierra en máximo

    # Vela de impulso fuerte (cuerpo >= 60%)
    if body_pct >= 0.60:
        return "NEWS_DRIVE ↑" if bull else "NEWS_DRIVE ↓"

    # Cuerpo medio (35-60%)
    if body_pct >= 0.35:
        if bull:
            return "EXPANSIÓN ↑" if close_pct >= 0.65 else "TRAMPA BULL"
        else:
            return "EXPANSIÓN ↓" if close_pct <= 0.35 else "TRAMPA BEAR"

    # Cuerpo pequeño (15-35%)
    if body_pct >= 0.15:
        # Sombras largas en ambos lados = megáfono / indecisión
        if upper_wick > rng * 0.25 and lower_wick > rng * 0.25:
            return "MEGÁFONO"
        return "DOJI SESGADO ↑" if bull else "DOJI SESGADO ↓"

    # Cuerpo muy pequeño < 15%
    return "RANGO ESTRECHO"

# ── DESCARGAR NQ ──────────────────────────────────────────────────────────────
print("📥 Descargando NQ=F...")
df = yf.download("NQ=F", period="2y", interval="1d", auto_adjust=True, progress=False)
if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index).normalize()

def compute_patterns(dates):
    results = []
    for d in dates:
        ts = pd.Timestamp(d)
        if ts not in df.index:
            print(f"  ⚠ {d} sin sesión")
            continue
        r   = df.loc[ts]
        op  = float(r["Open"]); hi = float(r["High"])
        lo  = float(r["Low"]);  cl = float(r["Close"])
        pat = classify_pattern(op, hi, lo, cl)
        rng = round(hi - lo)
        results.append({"date": d, "pat": pat, "rng": rng,
                         "op": round(op), "hi": round(hi),
                         "lo": round(lo), "cl": round(cl)})
    return results

cb_rows    = compute_patterns(CB_DATES)
jolts_rows = compute_patterns(JOLTS_DATES)
ppi_rows   = compute_patterns(PPI_DATES)

PAT_COLOR = {
    "NEWS_DRIVE ↑":  "#f97316",
    "NEWS_DRIVE ↓":  "#f97316",
    "EXPANSIÓN ↑":   "#22c55e",
    "EXPANSIÓN ↓":   "#ef4444",
    "TRAMPA BULL":   "#eab308",
    "TRAMPA BEAR":   "#eab308",
    "MEGÁFONO":      "#a855f7",
    "RANGO ESTRECHO":"#64748b",
    "DOJI SESGADO ↑":"#38bdf8",
    "DOJI SESGADO ↓":"#38bdf8",
}

PAT_DESC = {
    "NEWS_DRIVE ↑":   "Vela de impulso alcista fuerte (body ≥60%). Precio abrió y se fue directo arriba sin retroceso significativo.",
    "NEWS_DRIVE ↓":   "Vela de impulso bajista fuerte (body ≥60%). Precio abrió y cayó sin retroceso.",
    "EXPANSIÓN ↑":    "Cuerpo medio-grande alcista (35-60%). Cierre cerca del máximo. Sesión controlada por compradores.",
    "EXPANSIÓN ↓":    "Cuerpo medio-grande bajista (35-60%). Cierre cerca del mínimo. Sesión controlada por vendedores.",
    "TRAMPA BULL":    "Cuerpo alcista con cierre lejos del máximo. Compras iniciales que no se sostienen.",
    "TRAMPA BEAR":    "Cuerpo bajista con cierre lejos del mínimo. Ventas iniciales que no se sostienen.",
    "MEGÁFONO":       "Sombras largas arriba y abajo con cuerpo chico. Alta volatilidad en ambas direcciones. Session sin dirección clara.",
    "RANGO ESTRECHO": "Cuerpo y sombras pequeños. La noticia no generó movimiento. Esperar directional signal.",
    "DOJI SESGADO ↑": "Cuerpo pequeño, sesgo comprador. Sombras asimétricas. Posible continuación pero débil.",
    "DOJI SESGADO ↓": "Cuerpo pequeño, sesgo vendedor. Sombras asimétricas. Señal débil.",
}

def build_section(news_name, color, badge_text, rows, extra_note=""):
    if not rows:
        return ""
    total = len(rows)
    cnt   = Counter(r["pat"] for r in rows)
    top   = cnt.most_common()

    # Tabla de frecuencias (barras)
    max_count = top[0][1]
    bar_html  = ""
    for pat, n in top:
        pct  = round(n / total * 100)
        c    = PAT_COLOR.get(pat, "#64748b")
        w    = round(n / max_count * 100)
        desc = PAT_DESC.get(pat, "")
        bar_html += f"""
        <div class="pat-row">
          <div class="pat-name" style="color:{c}">{pat}</div>
          <div class="bar-wrap">
            <div class="bar-fill" style="width:{w}%;background:{c}"></div>
          </div>
          <div class="pat-count">{n}/{total} &nbsp;<span class="pct">{pct}%</span></div>
        </div>
        <div class="pat-desc">{desc}</div>"""

    # Tabla detalle de sesiones
    det = ""
    for r in reversed(rows):
        c   = PAT_COLOR.get(r["pat"], "#64748b")
        rng = r["rng"]
        det += f"""<tr>
          <td class="dt">{r['date']}</td>
          <td class="num grey">{r['op']}</td>
          <td class="num">{r['hi']}</td>
          <td class="num">{r['lo']}</td>
          <td class="num">{r['cl']}</td>
          <td class="num">{rng}</td>
          <td><span class="badge" style="background:{c}22;color:{c};border:1px solid {c}44">{r['pat']}</span></td>
        </tr>"""

    top1_pat   = top[0][0] if top else "—"
    top1_c     = PAT_COLOR.get(top1_pat, "#64748b")
    top1_pct   = round(top[0][1]/total*100) if top else 0
    avg_rng    = round(sum(r["rng"] for r in rows)/total)

    return f"""
<div class="section">
  <div class="section-header" style="border-left:4px solid {color}">
    <div>
      <h2 style="color:{color}">{news_name}</h2>
      <span class="badge-timing">{badge_text}</span>
    </div>
    <div class="top-pat" style="background:{top1_c}15;border:1px solid {top1_c}33">
      Patrón más frecuente:<br>
      <b style="color:{top1_c};font-size:1rem">{top1_pat}</b>
      <span style="color:{top1_c};font-size:.8rem"> {top1_pct}%</span>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1.4fr;gap:20px;margin-top:16px">
    <div>
      <h3 class="sub-title">Ranking de Patrones ({total} sesiones · Avg Range {avg_rng} pts)</h3>
      <div class="bar-container">{bar_html}</div>
      {"<div class='note'>" + extra_note + "</div>" if extra_note else ""}
    </div>
    <div>
      <h3 class="sub-title">Detalle por Sesión</h3>
      <div class="tw">
      <table>
        <thead><tr><th>Fecha</th><th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Range</th><th>Patrón</th></tr></thead>
        <tbody>{det}</tbody>
      </table>
      </div>
    </div>
  </div>
</div>"""

cb_section    = build_section(
    "📊 CB Consumer Confidence",
    "#60a5fa",
    "Último martes del mes · 10:00 AM ET",
    cb_rows,
    "Noticia del consumidor — suele impactar más tarde en la sesión."
)
jolts_section = build_section(
    "💼 JOLTS Job Openings",
    "#34d399",
    "Primer martes del mes · 10:00 AM ET",
    jolts_rows,
    "Dato de empleo — paradoja: BEAT implica Fed más hawkish → más volátil."
)
ppi_section   = build_section(
    "🌡️ PPI (cuando cae en martes)",
    "#fb923c",
    "Variable · 8:30 AM ET (afecta GAP de apertura)",
    ppi_rows,
    "PPI publica a las 8:30 AM — el patrón se forma desde el GAP de apertura."
)

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Patrones Martes por Noticia — NQ</title>
<style>
  *{{ margin:0; padding:0; box-sizing:border-box }}
  body{{ background:#0b0f1a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:24px 20px; max-width:1100px; margin:0 auto }}
  h1{{ font-size:1.35rem; color:#7dd3fc; margin-bottom:4px }}
  .meta{{ font-size:.8rem; color:#475569; margin-bottom:8px }}
  .nav{{ display:flex; gap:10px; margin-bottom:24px; flex-wrap:wrap }}
  .nav a{{ background:#1e293b; color:#94a3b8; padding:6px 14px; border-radius:8px; text-decoration:none; font-size:.78rem }}
  .nav a:hover{{ background:#334155; color:#e2e8f0 }}

  .section{{ background:#111827; border-radius:14px; padding:22px; margin-bottom:24px }}
  .section-header{{
    display:flex; justify-content:space-between; align-items:flex-start;
    flex-wrap:wrap; gap:12px; padding-left:12px
  }}
  .section-header h2{{ font-size:1rem; margin-bottom:4px }}
  .badge-timing{{ display:inline-block; background:#1e293b; color:#64748b; padding:3px 10px; border-radius:12px; font-size:.7rem; margin-top:4px }}
  .top-pat{{ padding:10px 16px; border-radius:10px; text-align:right; min-width:180px; line-height:1.6; font-size:.78rem; color:#94a3b8 }}

  .sub-title{{ font-size:.72rem; color:#475569; text-transform:uppercase; letter-spacing:.04em; margin-bottom:10px }}

  /* frecuencia bars */
  .bar-container{{ display:flex; flex-direction:column; gap:4px }}
  .pat-row{{ display:grid; grid-template-columns:150px 1fr 70px; align-items:center; gap:8px; margin-top:8px }}
  .pat-name{{ font-size:.78rem; font-weight:600; white-space:nowrap }}
  .bar-wrap{{ background:#1e293b; border-radius:4px; height:10px; overflow:hidden }}
  .bar-fill{{ height:100%; border-radius:4px; transition:width .3s }}
  .pat-count{{ font-size:.78rem; text-align:right; color:#94a3b8 }}
  .pct{{ color:#f1f5f9; font-weight:700 }}
  .pat-desc{{ font-size:.69rem; color:#475569; padding-left:158px; margin-bottom:4px; line-height:1.4 }}
  .note{{ margin-top:12px; font-size:.71rem; color:#475569; border-left:2px solid #234; padding-left:8px }}

  /* tabla */
  .tw{{ overflow-x:auto }}
  table{{ width:100%; border-collapse:collapse; font-size:.75rem }}
  thead tr{{ background:#0f172a }}
  th{{ padding:7px 10px; text-align:left; color:#475569; font-size:.65rem; text-transform:uppercase; letter-spacing:.04em; border-bottom:1px solid #1e293b; white-space:nowrap }}
  tbody tr{{ border-bottom:1px solid #1e293b44 }}
  tbody tr:hover{{ background:#1e293b44 }}
  td{{ padding:6px 10px; vertical-align:middle }}
  .dt{{ color:#94a3b8; font-size:.73rem; white-space:nowrap }}
  .num{{ text-align:right; font-variant-numeric:tabular-nums }}
  .grey{{ color:#64748b }}
  .badge{{ display:inline-block; padding:2px 8px; border-radius:14px; font-size:.68rem; font-weight:700; white-space:nowrap }}

  @media(max-width:680px){{
    .section-header{{ flex-direction:column }}
    .top-pat{{ text-align:left; min-width:auto }}
    div[style*="grid-template-columns:1fr 1.4fr"]{{ display:block }}
    div[style*="grid-template-columns:1fr 1.4fr"] > div:first-child{{ margin-bottom:20px }}
  }}
</style>
</head>
<body>

<h1>🗓️ Patrones NQ por Tipo de Noticia — Martes</h1>
<p class="meta">Para cada noticia: qué patrón OHLC ocurre con más frecuencia · 2024–2026 · NQ=F</p>

<div class="nav">
  <a href="daily_dashboard.html">🐋 Dashboard</a>
  <a href="backtest_CB_confidence.html">CB Stats</a>
  <a href="backtest_JOLTS.html">JOLTS Stats</a>
  <a href="backtest_PPI_martes.html">PPI Stats</a>
</div>

{cb_section}
{jolts_section}
{ppi_section}

<div style="margin-top:8px;font-size:.7rem;color:#334155;border-left:2px solid #1e293b;padding-left:10px">
  Clasificación OHLC: NEWS_DRIVE body ≥60% · EXPANSIÓN 35-60% · MEGÁFONO sombras largas en ambos lados · RANGO ESTRECHO body &lt;15%<br>
  Datos: yfinance NQ=F OHLC diario · Solo sesiones donde la noticia cayó en día martes.
</div>
</body>
</html>"""

out = Path("tuesday_patterns.html")
out.write_text(html, encoding="utf-8")
print(f"\n✅ Guardado: {out.resolve()}")
print("\nResumen de patrones:")
for name, rows in [("CB", cb_rows), ("JOLTS", jolts_rows), ("PPI", ppi_rows)]:
    if not rows: continue
    cnt = Counter(r["pat"] for r in rows)
    top = cnt.most_common(3)
    print(f"\n  {name} ({len(rows)} sesiones):")
    for pat, n in top:
        print(f"    [{n}/{len(rows)}] {pat}")
