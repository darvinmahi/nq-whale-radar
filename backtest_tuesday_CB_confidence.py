"""
BACKTEST: CB CONSUMER CONFIDENCE (Martes, 10:00 AM ET)
======================================================
Analiza el movimiento de NQ=F en cada fecha de publicación del CB Consumer Confidence.
Clasifica por Beat/Miss y extrae estadísticas de comportamiento.
Genera: backtest_CB_confidence.html
"""
import yfinance as yf, pandas as pd
from pathlib import Path

# ── FECHAS CB CONSUMER CONFIDENCE (2024-2026) ─────────────────────────────────
# Formato: fecha -> {"exp": expectativa, "actual": valor publicado}
CB_DATES = {
    "2024-01-30": {"exp": 114.8, "actual": 110.9},
    "2024-02-27": {"exp": 107.0, "actual": 106.7},
    "2024-03-26": {"exp": 107.0, "actual": 104.7},
    "2024-04-30": {"exp": 104.0, "actual":  97.0},
    "2024-05-28": {"exp":  96.0, "actual": 101.3},
    "2024-06-25": {"exp": 100.0, "actual": 100.4},
    "2024-07-30": {"exp":  99.0, "actual": 100.3},
    "2024-08-27": {"exp": 100.5, "actual": 103.3},
    "2024-09-24": {"exp":  98.7, "actual":  98.7},
    "2024-10-29": {"exp":  99.5, "actual":  99.2},
    "2024-11-26": {"exp": 111.5, "actual": 111.7},
    "2024-12-17": {"exp": 113.8, "actual": 104.7},
    "2025-01-28": {"exp": 105.7, "actual": 105.3},
    "2025-02-25": {"exp": 103.0, "actual":  98.3},
    "2025-03-25": {"exp":  94.0, "actual":  92.9},
}

def classify(exp, actual):
    diff = actual - exp
    if diff >= 3:   return "BEAT FUERTE 🟢🟢"
    elif diff >= 0: return "BEAT ✅"
    elif diff >= -3:return "MISS ❌"
    else:           return "MISS FUERTE 🔴🔴"

def ohlc_pattern(op, hi, lo, cl):
    rng      = hi - lo if hi > lo else 1
    body     = abs(cl - op)
    body_pct = body / rng
    bull     = cl >= op
    close_pct= (cl - lo) / rng
    if body_pct >= 0.60:
        return ("NEWS_DRIVE ↑" if bull else "NEWS_DRIVE ↓")
    elif body_pct >= 0.35:
        if bull:  return "EXPANSIÓN ↑" if close_pct > 0.60 else "TRAMPA BEAR"
        else:     return "EXPANSIÓN ↓" if close_pct < 0.40 else "TRAMPA BULL"
    elif body_pct >= 0.15:
        return "MEGÁFONO"
    else:
        return "RANGO ESTRECHO"

# ── DESCARGAR NQ DAILY ────────────────────────────────────────────────────────
print("📥 Descargando NQ=F daily (2y)...")
df = yf.download("NQ=F", period="2y", interval="1d", auto_adjust=True, progress=False)
if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index).normalize()

# ── CONSTRUIR FILAS ────────────────────────────────────────────────────────────
rows = []
for d_str, cb in sorted(CB_DATES.items()):
    ts = pd.Timestamp(d_str)
    if ts not in df.index:
        print(f"  ⚠ {d_str} no está en el DataFrame (quizás no hubo sesión)")
        continue
    r   = df.loc[ts]
    op  = float(r["Open"]);  hi = float(r["High"])
    lo  = float(r["Low"]);   cl = float(r["Close"])
    rng = round(hi - lo)
    move= round(cl - op)
    exp = cb["exp"]; actual = cb["actual"]
    diff = round(actual - exp, 1)
    bm   = classify(exp, actual)
    pat  = ohlc_pattern(op, hi, lo, cl)
    rows.append({
        "date":   d_str,
        "exp":    exp,
        "actual": actual,
        "diff":   diff,
        "bm":     bm,
        "op":     round(op),
        "cl":     round(cl),
        "hi":     round(hi),
        "lo":     round(lo),
        "rng":    rng,
        "move":   move,
        "bull":   cl >= op,
        "pat":    pat,
    })

print(f"✅ {len(rows)} sesiones encontradas")

# ── ESTADÍSTICAS ──────────────────────────────────────────────────────────────
total   = len(rows)
n_bull  = sum(1 for r in rows if r["bull"])
n_beat  = sum(1 for r in rows if "BEAT" in r["bm"])
n_miss  = sum(1 for r in rows if "MISS" in r["bm"])
n_bfuerte = sum(1 for r in rows if "FUERTE" in r["bm"] and "BEAT" in r["bm"])
n_mfuerte = sum(1 for r in rows if "FUERTE" in r["bm"] and "MISS" in r["bm"])
avg_rng = round(sum(r["rng"] for r in rows) / total) if total else 0
avg_move= round(sum(r["move"] for r in rows) / total) if total else 0

# stats por bm category
beat_rows = [r for r in rows if "BEAT" in r["bm"]]
miss_rows = [r for r in rows if "MISS" in r["bm"]]
beat_bull = sum(1 for r in beat_rows if r["bull"])
miss_bull = sum(1 for r in miss_rows if r["bull"])
beat_rng  = round(sum(r["rng"] for r in beat_rows)/len(beat_rows)) if beat_rows else 0
miss_rng  = round(sum(r["rng"] for r in miss_rows)/len(miss_rows)) if miss_rows else 0
beat_move = round(sum(r["move"] for r in beat_rows)/len(beat_rows)) if beat_rows else 0
miss_move = round(sum(r["move"] for r in miss_rows)/len(miss_rows)) if miss_rows else 0

# ── COLORES ───────────────────────────────────────────────────────────────────
BM_COLOR = {
    "BEAT FUERTE 🟢🟢": "#16a34a",
    "BEAT ✅":          "#22c55e",
    "MISS ❌":          "#ef4444",
    "MISS FUERTE 🔴🔴": "#991b1b",
}
PAT_COLOR = {
    "NEWS_DRIVE ↑":    "#f97316",
    "NEWS_DRIVE ↓":    "#f97316",
    "EXPANSIÓN ↑":     "#22c55e",
    "EXPANSIÓN ↓":     "#ef4444",
    "TRAMPA BULL":     "#eab308",
    "TRAMPA BEAR":     "#eab308",
    "MEGÁFONO":        "#a855f7",
    "RANGO ESTRECHO":  "#64748b",
}

# ── TABLA HTML ────────────────────────────────────────────────────────────────
table_rows = ""
for r in reversed(rows):
    bm_color  = BM_COLOR.get(r["bm"], "#64748b")
    pat_color = PAT_COLOR.get(r["pat"], "#64748b")
    dir_sym   = "▲" if r["bull"] else "▼"
    dir_cls   = "bull" if r["bull"] else "bear"
    msign     = f"+{r['move']}" if r["move"] >= 0 else str(r["move"])
    dsign     = f"+{r['diff']}" if r["diff"] >= 0 else str(r["diff"])
    table_rows += f"""
    <tr>
      <td class="dt">{r['date']}</td>
      <td class="num">{r['exp']}</td>
      <td class="num">{r['actual']}</td>
      <td><span class="badge" style="background:{bm_color}22;color:{bm_color};border:1px solid {bm_color}44">{r['bm']}</span></td>
      <td class="num {'pos' if r['diff']>=0 else 'neg'}">{dsign}</td>
      <td><span class="badge pat" style="background:{pat_color}22;color:{pat_color};border:1px solid {pat_color}44">{r['pat']}</span></td>
      <td class="num">{r['rng']}</td>
      <td class="num {dir_cls}">{msign}</td>
      <td class="dir {dir_cls}">{dir_sym}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Backtest CB Consumer Confidence — NQ</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:#0b0f1a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:28px 20px }}
  h1 {{ font-size:1.4rem; color:#60a5fa; margin-bottom:4px }}
  .sub {{ font-size:.82rem; color:#475569; margin-bottom:26px }}

  /* KPI CARDS */
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:12px; margin-bottom:28px }}
  .kpi {{ background:#111827; border-radius:10px; padding:14px 18px; border-left:3px solid #3b82f6 }}
  .kpi.green {{ border-color:#22c55e }}
  .kpi.red   {{ border-color:#ef4444 }}
  .kpi.orange{{ border-color:#f97316 }}
  .kpi label {{ font-size:.7rem; color:#64748b; text-transform:uppercase; letter-spacing:.05em }}
  .kpi value {{ display:block; font-size:1.5rem; font-weight:700; margin-top:4px; color:#f1f5f9 }}
  .kpi small  {{ font-size:.72rem; color:#94a3b8 }}

  /* COMPARATIVA */
  .compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:28px }}
  .compare-box {{ background:#111827; border-radius:10px; padding:16px }}
  .compare-box h3 {{ font-size:.85rem; margin-bottom:12px }}
  .compare-box .cstat {{ display:flex; justify-content:space-between; padding:4px 0; font-size:.82rem; border-bottom:1px solid #1e293b }}
  .compare-box .cstat:last-child {{ border-bottom:none }}

  /* TABLE */
  .tw {{ overflow-x:auto; border-radius:10px }}
  table {{ width:100%; border-collapse:collapse; font-size:.81rem }}
  thead tr {{ background:#0f172a }}
  th {{ padding:9px 12px; text-align:left; color:#64748b; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid #1e293b }}
  tbody tr {{ border-bottom:1px solid #1e293b; transition:background .15s }}
  tbody tr:hover {{ background:#111827 }}
  td {{ padding:8px 12px; vertical-align:middle }}
  .dt {{ color:#94a3b8; font-size:.75rem; white-space:nowrap }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums }}
  .bull {{ color:#22c55e }}
  .bear {{ color:#ef4444 }}
  .pos  {{ color:#22c55e }}
  .neg  {{ color:#ef4444 }}
  .dir  {{ text-align:center }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:20px; font-size:.71rem; font-weight:700; white-space:nowrap }}
  .pat  {{ font-size:.68rem }}

  /* NOTA */
  .note {{ margin-top:18px; font-size:.73rem; color:#475569; border-left:2px solid #334155; padding-left:10px }}
</style>
</head>
<body>
<h1>📊 Backtest: CB Consumer Confidence × NQ Futures</h1>
<p class="sub">Noticia: Martes, 10:00 AM ET · Último martes hábil del mes · {total} sesiones analizadas (2024–2026)</p>

<div class="kpi-grid">
  <div class="kpi"><label>Sesiones</label><value>{total}</value><small>Total analizadas</small></div>
  <div class="kpi green"><label>Días BULL</label><value>{round(n_bull/total*100)}%</value><small>{n_bull}/{total}</small></div>
  <div class="kpi green"><label>BEAT</label><value>{n_beat}</value><small>{round(n_beat/total*100)}% · FUERTE: {n_bfuerte}</small></div>
  <div class="kpi red"><label>MISS</label><value>{n_miss}</value><small>{round(n_miss/total*100)}% · FUERTE: {n_mfuerte}</small></div>
  <div class="kpi orange"><label>Avg Range</label><value>{avg_rng}</value><small>puntos NQ</small></div>
  <div class="kpi"><label>Avg Move</label><value>{avg_move:+}</value><small>Open→Close</small></div>
</div>

<div class="compare-grid">
  <div class="compare-box">
    <h3 style="color:#22c55e">BEAT ({n_beat} sesiones)</h3>
    <div class="cstat"><span>% Días BULL</span><span style="color:#22c55e"><b>{round(beat_bull/len(beat_rows)*100) if beat_rows else 0}%</b></span></div>
    <div class="cstat"><span>Avg Range</span><span><b>{beat_rng} pts</b></span></div>
    <div class="cstat"><span>Avg Move</span><span><b>{beat_move:+} pts</b></span></div>
    <div class="cstat"><span>BEAT FUERTE</span><span><b>{n_bfuerte} sesiones</b></span></div>
  </div>
  <div class="compare-box">
    <h3 style="color:#ef4444">MISS ({n_miss} sesiones)</h3>
    <div class="cstat"><span>% Días BULL</span><span style="color:#22c55e"><b>{round(miss_bull/len(miss_rows)*100) if miss_rows else 0}%</b></span></div>
    <div class="cstat"><span>Avg Range</span><span><b>{miss_rng} pts</b></span></div>
    <div class="cstat"><span>Avg Move</span><span><b>{miss_move:+} pts</b></span></div>
    <div class="cstat"><span>MISS FUERTE</span><span><b>{n_mfuerte} sesiones</b></span></div>
  </div>
</div>

<div class="tw">
<table>
  <thead><tr>
    <th>Fecha</th><th>Exp</th><th>Actual</th>
    <th>Beat/Miss</th><th>Δ</th>
    <th>Patrón del Día</th>
    <th>Range</th><th>Move</th><th>Dir</th>
  </tr></thead>
  <tbody>{table_rows}</tbody>
</table>
</div>

<div class="note">
  ★ Patrón del día basado en OHLC diario de NQ=F (yfinance).<br>
  ★ Beat/Miss: Actual ≥ Exp = BEAT · Diferencia ≥ 3 puntos = FUERTE.<br>
  ★ Move = Close − Open (sesión completa).
</div>
</body>
</html>"""

out = Path("backtest_CB_confidence.html")
out.write_text(html, encoding="utf-8")
print(f"✅ Guardado: {out.resolve()}")
