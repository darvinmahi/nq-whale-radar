"""
BACKTEST: JOLTS JOB OPENINGS (Martes, 10:00 AM ET)
===================================================
JOLTS = Job Openings and Labor Turnover Survey
Se publica el PRIMER MARTES de cada mes (datos del mes anterior).
Analiza el movimiento de NQ=F en cada fecha de publicación.
Genera: backtest_JOLTS.html
"""
import yfinance as yf, pandas as pd
from pathlib import Path

# ── FECHAS JOLTS (2024-2026) ───────────────────────────────────────────────────
# exp = expectativa en millones, actual = valor publicado
JOLTS_DATES = {
    # 2024
    "2024-01-09": {"exp": 8.75,  "actual": 9.03},
    "2024-02-06": {"exp": 8.75,  "actual": 9.03},  # revisado
    "2024-03-12": {"exp": 8.79,  "actual": 8.75},
    "2024-04-02": {"exp": 8.75,  "actual": 8.76},
    "2024-05-07": {"exp": 8.68,  "actual": 8.49},
    "2024-06-04": {"exp": 8.37,  "actual": 8.14},
    "2024-07-30": {"exp": 8.00,  "actual": 8.18},
    "2024-08-06": {"exp": 8.10,  "actual": 7.67},
    "2024-09-04": {"exp": 7.65,  "actual": 7.71},
    "2024-10-01": {"exp": 7.66,  "actual": 7.44},
    "2024-11-05": {"exp": 7.50,  "actual": 7.44},
    "2024-12-03": {"exp": 7.48,  "actual": 7.74},
    # 2025
    "2025-01-07": {"exp": 7.70,  "actual": 8.10},
    "2025-02-04": {"exp": 7.90,  "actual": 7.74},
    "2025-03-11": {"exp": 7.75,  "actual": 7.57},
}

def classify_jolts(exp, actual):
    diff = actual - exp
    if diff >= 0.3:    return "BEAT FUERTE 🟢🟢"
    elif diff >= 0:    return "BEAT ✅"
    elif diff >= -0.3: return "MISS ❌"
    else:              return "MISS FUERTE 🔴🔴"

def ohlc_pattern(op, hi, lo, cl):
    rng       = hi - lo if hi > lo else 1
    body      = abs(cl - op)
    body_pct  = body / rng
    bull      = cl >= op
    close_pct = (cl - lo) / rng
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
for d_str, j in sorted(JOLTS_DATES.items()):
    ts = pd.Timestamp(d_str)
    if ts not in df.index:
        print(f"  ⚠ {d_str} sin sesión en yfinance")
        continue
    r    = df.loc[ts]
    op   = float(r["Open"]);  hi = float(r["High"])
    lo   = float(r["Low"]);   cl = float(r["Close"])
    rng  = round(hi - lo)
    move = round(cl - op)
    exp  = j["exp"]; actual = j["actual"]
    diff = round(actual - exp, 2)
    bm   = classify_jolts(exp, actual)
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
total     = len(rows)
n_bull    = sum(1 for r in rows if r["bull"])
n_beat    = sum(1 for r in rows if "BEAT" in r["bm"])
n_miss    = sum(1 for r in rows if "MISS" in r["bm"])
n_bfuerte = sum(1 for r in rows if "FUERTE" in r["bm"] and "BEAT" in r["bm"])
n_mfuerte = sum(1 for r in rows if "FUERTE" in r["bm"] and "MISS" in r["bm"])
avg_rng   = round(sum(r["rng"]  for r in rows) / total) if total else 0
avg_move  = round(sum(r["move"] for r in rows) / total) if total else 0

beat_rows = [r for r in rows if "BEAT" in r["bm"]]
miss_rows = [r for r in rows if "MISS" in r["bm"]]
beat_bull  = sum(1 for r in beat_rows if r["bull"])
miss_bull  = sum(1 for r in miss_rows if r["bull"])
beat_rng   = round(sum(r["rng"]  for r in beat_rows)/len(beat_rows)) if beat_rows else 0
miss_rng   = round(sum(r["rng"]  for r in miss_rows)/len(miss_rows)) if miss_rows else 0
beat_move  = round(sum(r["move"] for r in beat_rows)/len(beat_rows)) if beat_rows else 0
miss_move  = round(sum(r["move"] for r in miss_rows)/len(miss_rows)) if miss_rows else 0

# ── COLORES ───────────────────────────────────────────────────────────────────
BM_COLOR = {
    "BEAT FUERTE 🟢🟢": "#16a34a",
    "BEAT ✅":           "#22c55e",
    "MISS ❌":           "#ef4444",
    "MISS FUERTE 🔴🔴":  "#991b1b",
}
PAT_COLOR = {
    "NEWS_DRIVE ↑":   "#f97316",
    "NEWS_DRIVE ↓":   "#f97316",
    "EXPANSIÓN ↑":    "#22c55e",
    "EXPANSIÓN ↓":    "#ef4444",
    "TRAMPA BULL":    "#eab308",
    "TRAMPA BEAR":    "#eab308",
    "MEGÁFONO":       "#a855f7",
    "RANGO ESTRECHO": "#64748b",
}

# ── HTML ──────────────────────────────────────────────────────────────────────
table_rows = ""
for r in reversed(rows):
    bm_c  = BM_COLOR.get(r["bm"], "#64748b")
    pat_c = PAT_COLOR.get(r["pat"], "#64748b")
    dc    = "bull" if r["bull"] else "bear"
    ms    = f"+{r['move']}" if r["move"] >= 0 else str(r["move"])
    ds    = f"+{r['diff']}" if r["diff"] >= 0 else str(r["diff"])
    table_rows += f"""
    <tr>
      <td class="dt">{r['date']}</td>
      <td class="num">{r['exp']}M</td>
      <td class="num">{r['actual']}M</td>
      <td><span class="badge" style="background:{bm_c}22;color:{bm_c};border:1px solid {bm_c}44">{r['bm']}</span></td>
      <td class="num {'pos' if r['diff']>=0 else 'neg'}">{ds}M</td>
      <td><span class="badge pat" style="background:{pat_c}22;color:{pat_c};border:1px solid {pat_c}44">{r['pat']}</span></td>
      <td class="num">{r['rng']}</td>
      <td class="num {dc}">{ms}</td>
      <td class="dir {dc}">{'▲' if r['bull'] else '▼'}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Backtest JOLTS Job Openings — NQ</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:#0b0f1a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:28px 20px }}
  h1 {{ font-size:1.4rem; color:#34d399; margin-bottom:4px }}
  .sub {{ font-size:.82rem; color:#475569; margin-bottom:26px }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:12px; margin-bottom:28px }}
  .kpi {{ background:#111827; border-radius:10px; padding:14px 18px; border-left:3px solid #34d399 }}
  .kpi.green {{ border-color:#22c55e }}
  .kpi.red   {{ border-color:#ef4444 }}
  .kpi.orange{{ border-color:#f97316 }}
  .kpi label {{ font-size:.7rem; color:#64748b; text-transform:uppercase; letter-spacing:.05em }}
  .kpi value {{ display:block; font-size:1.5rem; font-weight:700; margin-top:4px; color:#f1f5f9 }}
  .kpi small  {{ font-size:.72rem; color:#94a3b8 }}
  .compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:28px }}
  .compare-box {{ background:#111827; border-radius:10px; padding:16px }}
  .compare-box h3 {{ font-size:.85rem; margin-bottom:12px }}
  .compare-box .cstat {{ display:flex; justify-content:space-between; padding:4px 0; font-size:.82rem; border-bottom:1px solid #1e293b }}
  .compare-box .cstat:last-child {{ border-bottom:none }}
  .tw {{ overflow-x:auto; border-radius:10px }}
  table {{ width:100%; border-collapse:collapse; font-size:.81rem }}
  thead tr {{ background:#0f172a }}
  th {{ padding:9px 12px; text-align:left; color:#64748b; font-size:.7rem; text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid #1e293b }}
  tbody tr {{ border-bottom:1px solid #1e293b }}
  tbody tr:hover {{ background:#111827 }}
  td {{ padding:8px 12px; vertical-align:middle }}
  .dt {{ color:#94a3b8; font-size:.75rem; white-space:nowrap }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums }}
  .bull {{ color:#22c55e }} .bear {{ color:#ef4444 }}
  .pos  {{ color:#22c55e }} .neg  {{ color:#ef4444 }}
  .dir  {{ text-align:center }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:20px; font-size:.71rem; font-weight:700; white-space:nowrap }}
  .pat {{ font-size:.68rem }}
  .note {{ margin-top:18px; font-size:.73rem; color:#475569; border-left:2px solid #334155; padding-left:10px }}
</style>
</head>
<body>
<h1>💼 Backtest: JOLTS Job Openings × NQ Futures</h1>
<p class="sub">Noticia: Martes, 10:00 AM ET · Primer martes del mes · {total} sesiones analizadas (2024–2026)</p>

<div class="kpi-grid">
  <div class="kpi"><label>Sesiones</label><value>{total}</value><small>Total analizadas</small></div>
  <div class="kpi green"><label>Días BULL</label><value>{round(n_bull/total*100) if total else 0}%</value><small>{n_bull}/{total}</small></div>
  <div class="kpi green"><label>BEAT</label><value>{n_beat}</value><small>{round(n_beat/total*100) if total else 0}% · FUERTE: {n_bfuerte}</small></div>
  <div class="kpi red"><label>MISS</label><value>{n_miss}</value><small>{round(n_miss/total*100) if total else 0}% · FUERTE: {n_mfuerte}</small></div>
  <div class="kpi orange"><label>Avg Range</label><value>{avg_rng}</value><small>puntos NQ</small></div>
  <div class="kpi"><label>Avg Move</label><value>{avg_move:+}</value><small>Open→Close</small></div>
</div>

<div class="compare-grid">
  <div class="compare-box">
    <h3 style="color:#22c55e">BEAT ({n_beat} sesiones)</h3>
    <div class="cstat"><span>% Días BULL</span><span style="color:#22c55e"><b>{round(beat_bull/len(beat_rows)*100) if beat_rows else 0}%</b></span></div>
    <div class="cstat"><span>Avg Range</span><span><b>{beat_rng} pts</b></span></div>
    <div class="cstat"><span>Avg Move O→C</span><span><b>{beat_move:+} pts</b></span></div>
  </div>
  <div class="compare-box">
    <h3 style="color:#ef4444">MISS ({n_miss} sesiones)</h3>
    <div class="cstat"><span>% Días BULL</span><span style="color:#22c55e"><b>{round(miss_bull/len(miss_rows)*100) if miss_rows else 0}%</b></span></div>
    <div class="cstat"><span>Avg Range</span><span><b>{miss_rng} pts</b></span></div>
    <div class="cstat"><span>Avg Move O→C</span><span><b>{miss_move:+} pts</b></span></div>
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
  ★ JOLTS = Job Openings and Labor Turnover Survey (en millones de puestos).<br>
  ★ Beat: Actual ≥ Expectativa · FUERTE: diferencia ≥ 0.3M<br>
  ★ Patrón y Move basados en OHLC diario de NQ=F (yfinance).
</div>
</body>
</html>"""

out = Path("backtest_JOLTS.html")
out.write_text(html, encoding="utf-8")
print(f"✅ Guardado: {out.resolve()}")
