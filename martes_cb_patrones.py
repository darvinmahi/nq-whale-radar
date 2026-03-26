"""
Genera HTML comparativo: Martes CB Consumer Confidence × Patrones
Cruza yfinance (datos diarios) + ny_patterns CSV + backtest_tuesday_3m.json
PATRONES INFERIDOS si no existe dato previo (OHLC daily-based classification)
"""
import json, csv, yfinance as yf, pandas as pd
from pathlib import Path

def infer_pattern_from_ohlc(op, hi, lo, cl, prev_cl=None):
    """
    Clasifica el patrón del día con lógica OHLC similar al sistema:
      NEWS_DRIVE      → cuerpo grande > 60% del rango, una dirección
      EXPANSIÓN_ALC.  → cuerpo alcista medio-grande, cierra cerca del high
      EXPANSIÓN_BAJ.  → cuerpo bajista medio-grande, cierra cerca del low
      MEGÁFONO        → rango grande pero cuerpo pequeño (indecisión)
      TRAMPA_BULL     → sube, cierra abajo del open (fakeout alcista)
      TRAMPA_BEAR     → baja, cierra arriba del open (fakeout bajista)
      RANGO           → rango pequeño, cuerpo pequeño
    """
    rng   = hi - lo if hi > lo else 1
    body  = abs(cl - op)
    body_pct = body / rng
    bull  = cl >= op
    # Dónde cierra dentro del rango
    close_pct = (cl - lo) / rng   # 0=low, 1=high

    if body_pct >= 0.60:
        if bull:
            return "NEWS_DRIVE" if close_pct > 0.80 else "EXPANSIÓN_ALCISTA"
        else:
            return "NEWS_DRIVE" if close_pct < 0.20 else "EXPANSIÓN_BAJISTA"
    elif body_pct >= 0.35:
        if bull:
            return "EXPANSIÓN_ALCISTA" if close_pct > 0.60 else "TRAMPA_BEAR"
        else:
            return "EXPANSIÓN_BAJISTA" if close_pct < 0.40 else "TRAMPA_BULL"
    elif body_pct >= 0.15:
        return "MEGÁFONO"
    else:
        return "RANGO"


# ── 1. FECHAS CB CONSUMER CONFIDENCE ─────────────────────────────────────────
CB_NEWS = {
    "2024-01-16": {"exp": "N/A",     "actual": "N/A"},
    "2024-01-23": {"exp": "N/A",     "actual": "N/A"},
    "2024-01-30": {"exp": "114.8",   "actual": "110.9"},
    "2024-02-20": {"exp": "115.2",   "actual": "106.7"},
    "2024-02-27": {"exp": "107.0",   "actual": "106.7"},
    "2024-03-19": {"exp": "107.0",   "actual": "104.7"},
    "2024-03-26": {"exp": "107.0",   "actual": "104.7"},
    "2024-04-16": {"exp": "104.3",   "actual": "97.0"},
    "2024-04-23": {"exp": "97.0",    "actual": "97.0"},
    "2024-04-30": {"exp": "104.0",   "actual": "97.0"},
    "2024-05-21": {"exp": "96.0",    "actual": "101.3"},
    "2024-05-28": {"exp": "96.0",    "actual": "101.3"},
    "2024-06-18": {"exp": "100.0",   "actual": "100.4"},
    "2024-06-25": {"exp": "100.0",   "actual": "100.4"},
    "2024-07-16": {"exp": "99.7",    "actual": "100.3"},
    "2024-07-23": {"exp": "100.0",   "actual": "100.3"},
    "2024-07-30": {"exp": "99.0",    "actual": "100.3"},
    "2024-08-20": {"exp": "100.5",   "actual": "103.3"},
    "2024-08-27": {"exp": "100.5",   "actual": "103.3"},
    "2024-09-17": {"exp": "103.8",   "actual": "98.7"},
    "2024-09-24": {"exp": "98.7",    "actual": "98.7"},
    "2024-10-15": {"exp": "99.3",    "actual": "99.2"},
    "2024-10-22": {"exp": "99.0",    "actual": "99.2"},
    "2024-10-29": {"exp": "99.5",    "actual": "99.2"},
    "2024-11-19": {"exp": "111.8",   "actual": "111.7"},
    "2024-11-26": {"exp": "111.5",   "actual": "111.7"},
    "2024-12-17": {"exp": "113.8",   "actual": "104.7"},
    "2025-01-21": {"exp": "104.5",   "actual": "105.3"},
    "2025-01-28": {"exp": "105.7",   "actual": "105.3"},
    "2025-02-18": {"exp": "103.3",   "actual": "98.3"},
    "2025-02-25": {"exp": "103.0",   "actual": "98.3"},
    "2025-03-18": {"exp": "94.0",    "actual": "92.9"},
    "2025-03-25": {"exp": "94.0",    "actual": "92.9"},
}

def beat_miss(exp, actual):
    try:
        return "BEAT 🟢" if float(actual) >= float(exp) else "MISS 🔴"
    except:
        return "—"

# ── 2. PATRONES DEL CSV ───────────────────────────────────────────────────────
csv_patterns = {}
csv_path = Path("ny_patterns_3months.csv")
if csv_path.exists():
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            csv_patterns[row["Fecha"]] = row["Perfil"]

# ── 3. PATRONES DEL JSON TUESDAY ─────────────────────────────────────────────
json_patterns = {}
json_path = Path("data/research/backtest_tuesday_3m.json")
if json_path.exists():
    with open(json_path, encoding="utf-8") as f:
        tj = json.load(f)
    for sess in tj.get("MARTES", {}).get("sessions", []):
        json_patterns[sess["date"]] = sess.get("pattern", "—")

# ── 4. DATOS DIARIOS YFINANCE ─────────────────────────────────────────────────
print("Descargando NQ=F 2 años daily...")
df = yf.download("NQ=F", period="2y", interval="1d", auto_adjust=True, progress=False)
if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index).normalize()

# ── 5. CONSTRUIR FILAS ────────────────────────────────────────────────────────
rows = []
for d_str, cb in sorted(CB_NEWS.items()):
    ts = pd.Timestamp(d_str)
    if ts not in df.index:
        continue
    r = df.loc[ts]
    hi = float(r["High"]); lo = float(r["Low"])
    op = float(r["Open"]); cl = float(r["Close"])
    rng = round(hi - lo)
    move = round(cl - op)
    bull = cl >= op
    # Patrón: primero JSON (reciente), luego CSV, luego inferir de OHLC
    patron = json_patterns.get(d_str) or csv_patterns.get(d_str)
    inferred = False
    if not patron:
        patron = infer_pattern_from_ohlc(op, hi, lo, cl)
        inferred = True
    bm = beat_miss(cb["exp"], cb["actual"])
    rows.append({
        "date": d_str,
        "exp": cb["exp"],
        "actual": cb["actual"],
        "bm": bm,
        "patron": patron,
        "inferred": inferred,
        "rng": rng,
        "move": move,
        "bull": bull,
        "op": round(op),
        "cl": round(cl),
    })


# Últimas 30
rows = rows[-30:]
print(f"Sesiones encontradas para HTML: {len(rows)}")

# ── 6. ESTADÍSTICAS POR PATRÓN ────────────────────────────────────────────────
pat_stats = {}
for r in rows:
    p = r["patron"]
    if p not in pat_stats:
        pat_stats[p] = {"n": 0, "bull": 0, "rangs": [], "bm": {"BEAT 🟢": 0, "MISS 🔴": 0}}
    pat_stats[p]["n"] += 1
    if r["bull"]:
        pat_stats[p]["bull"] += 1
    pat_stats[p]["rangs"].append(r["rng"])
    if "BEAT" in r["bm"]:
        pat_stats[p]["bm"]["BEAT 🟢"] += 1
    elif "MISS" in r["bm"]:
        pat_stats[p]["bm"]["MISS 🔴"] += 1

def avg(lst):
    return round(sum(lst) / len(lst)) if lst else 0

# ── 7. GENERAR HTML ───────────────────────────────────────────────────────────
PATRON_COLOR = {
    "EXPANSIÓN_ALCISTA": "#22c55e",
    "EXPANSION_H":       "#22c55e",
    "NEWS_DRIVE":        "#f97316",
    "EXPANSIÓN_BAJISTA": "#ef4444",
    "EXPANSION_L":       "#ef4444",
    "MEGÁFONO":          "#a855f7",
    "TRAMPA_BULL":       "#eab308",
    "TRAMPA_BEAR":       "#eab308",
    "RANGO":             "#94a3b8",
    "ROTATION_POC":      "#94a3b8",
    "SWEEP_H_RETURN":    "#38bdf8",
    "SWEEP_L_RETURN":    "#38bdf8",
    "—":                 "#475569",
}

stats_html = ""
for p, s in sorted(pat_stats.items(), key=lambda x: -x[1]["n"]):
    color = PATRON_COLOR.get(p, "#94a3b8")
    bull_pct = round(s["bull"] / s["n"] * 100) if s["n"] else 0
    avg_r = avg(s["rangs"])
    beats = s["bm"].get("BEAT 🟢", 0)
    misses = s["bm"].get("MISS 🔴", 0)
    stats_html += f"""
    <div class="stat-card" style="border-left:4px solid {color}">
      <div class="sc-pat">{p}</div>
      <div class="sc-grid">
        <div><span>Sesiones</span><strong>{s["n"]}</strong></div>
        <div><span>BULL</span><strong style="color:#22c55e">{bull_pct}%</strong></div>
        <div><span>Avg Range</span><strong>{avg_r} pts</strong></div>
        <div><span>BEAT / MISS</span><strong>{beats} / {misses}</strong></div>
      </div>
    </div>"""

table_rows = ""
for r in reversed(rows):
    dir_sym = "▲" if r["bull"] else "▼"
    dir_cls = "bull" if r["bull"] else "bear"
    color = PATRON_COLOR.get(r["patron"], "#94a3b8")
    move_sign = f"+{r['move']}" if r["move"] >= 0 else str(r["move"])
    beat_cls = "beat" if "BEAT" in r["bm"] else ("miss" if "MISS" in r["bm"] else "")
    inf_mark = ' <span title="Patrón inferido de OHLC diario" style="opacity:.5;font-size:.65rem">★</span>' if r["inferred"] else ""
    table_rows += f"""
    <tr>
      <td class="date">{r['date']}</td>
      <td class="exp">{r['exp']}</td>
      <td class="actual {beat_cls}">{r['actual']}</td>
      <td class="{beat_cls} bm-cell">{r['bm']}</td>
      <td><span class="patron-badge" style="background:{color}22;color:{color};border:1px solid {color}44">{r['patron']}</span>{inf_mark}</td>
      <td class="num">{r['rng']}</td>
      <td class="num {dir_cls}">{move_sign}</td>
      <td class="dir {dir_cls}">{dir_sym}</td>
    </tr>"""


html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Martes CB Consumer Confidence × Patrones</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:#0b0f1a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:24px }}
  h1 {{ font-size:1.4rem; color:#60a5fa; margin-bottom:6px }}
  .subtitle {{ font-size:.85rem; color:#64748b; margin-bottom:24px }}

  /* STAT CARDS */
  .stats-grid {{ display:flex; flex-wrap:wrap; gap:12px; margin-bottom:28px }}
  .stat-card {{ background:#111827; border-radius:10px; padding:14px 18px; min-width:200px; flex:1 }}
  .sc-pat {{ font-size:.8rem; font-weight:700; color:#94a3b8; text-transform:uppercase; letter-spacing:.05em; margin-bottom:10px }}
  .sc-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:8px }}
  .sc-grid div {{ display:flex; flex-direction:column }}
  .sc-grid span {{ font-size:.7rem; color:#64748b }}
  .sc-grid strong {{ font-size:1rem; color:#e2e8f0 }}

  /* TABLE */
  .table-wrap {{ overflow-x:auto; border-radius:10px }}
  table {{ width:100%; border-collapse:collapse; font-size:.82rem }}
  thead tr {{ background:#0f172a }}
  thead th {{ padding:10px 12px; text-align:left; color:#64748b; font-weight:600; font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid #1e293b }}
  tbody tr {{ border-bottom:1px solid #1e293b; transition:background .15s }}
  tbody tr:hover {{ background:#111827 }}
  td {{ padding:9px 12px; vertical-align:middle }}
  .date {{ color:#94a3b8; font-size:.77rem }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums }}
  .bull {{ color:#22c55e }}
  .bear {{ color:#ef4444 }}
  .dir {{ text-align:center; font-size:1rem }}
  .beat {{ color:#22c55e; font-weight:700 }}
  .miss {{ color:#ef4444; font-weight:700 }}
  .bm-cell {{ font-size:.78rem }}
  .patron-badge {{ display:inline-block; padding:3px 10px; border-radius:20px; font-size:.72rem; font-weight:700; white-space:nowrap }}
  .exp {{ color:#64748b; font-size:.78rem }}
  .actual {{ font-weight:600 }}
  caption {{ caption-side:bottom; padding-top:8px; font-size:.72rem; color:#475569 }}

  /* LEGEND */
  .legend {{ margin-top:20px; display:flex; flex-wrap:wrap; gap:8px }}
  .legend-item {{ display:flex; align-items:center; gap:6px; font-size:.74rem; color:#94a3b8 }}
  .legend-dot {{ width:10px; height:10px; border-radius:50% }}
</style>
</head>
<body>
<h1>🗂️ Martes CB Consumer Confidence × Patrones — NQ Futures</h1>
<p class="subtitle">Últimas {len(rows)} sesiones · Cruza dato económico (Beat/Miss) con el patrón intraday del día</p>

<div class="stats-grid">
{stats_html}
</div>

<div class="table-wrap">
<table>
  <caption>Datos diarios NQ=F · Patrones de ny_patterns_3months.csv y backtest_tuesday_3m.json</caption>
  <thead>
    <tr>
      <th>Fecha</th>
      <th>Exp.</th>
      <th>Actual</th>
      <th>Beat/Miss</th>
      <th>Patrón del Día</th>
      <th>Range</th>
      <th>Move</th>
      <th>Dir</th>
    </tr>
  </thead>
  <tbody>
{table_rows}
  </tbody>
</table>
</div>

<div class="legend">
  <span style="font-size:.75rem;color:#475569;margin-right:4px">Patrones:</span>
  {"".join(f'<div class="legend-item"><div class="legend-dot" style="background:{v}"></div>{k}</div>' for k,v in PATRON_COLOR.items() if k != "—")}
</div>
</body>
</html>"""

out = Path("martes_cb_patrones.html")
out.write_text(html, encoding="utf-8")
print(f"Guardado: {out.resolve()}")
