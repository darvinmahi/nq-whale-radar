"""
BACKTEST: PPI (Producer Price Index) — Martes, 8:30 AM ET
===========================================================
El PPI no siempre cae en martes, pero cuando lo hace genera
los movimientos más grandes del mes. Este backtest mapea las
fechas en que el PPI cayó en martes y analiza el NQ.
Genera: backtest_PPI_martes.html
"""
import yfinance as yf, pandas as pd
from pathlib import Path

# ── FECHAS PPI QUE CAYERON EN MARTES (2024-2026) ───────────────────────────────
# PPI = Producer Price Index (cambio mensual MoM)
# exp = expectativa MoM%, actual = publicado MoM%
PPI_DATES = {
    "2024-02-13": {"exp": 0.1,  "actual": 0.3,  "yoy_exp": 0.6,  "yoy_act": 0.9},
    "2024-04-11": {"exp": 0.3,  "actual": 0.2,  "yoy_exp": 2.2,  "yoy_act": 2.1},
    "2024-06-11": {"exp": 0.1,  "actual": -0.2, "yoy_exp": 2.5,  "yoy_act": 2.2},
    "2024-08-13": {"exp": 0.2,  "actual": 0.1,  "yoy_exp": 2.3,  "yoy_act": 2.2},
    "2024-10-08": {"exp": 0.1,  "actual": 0.0,  "yoy_exp": 1.6,  "yoy_act": 1.8},
    "2024-12-10": {"exp": 0.2,  "actual": 0.4,  "yoy_exp": 2.6,  "yoy_act": 3.0},
    "2025-02-11": {"exp": 0.3,  "actual": 0.4,  "yoy_exp": 3.3,  "yoy_act": 3.5},
}

def classify_ppi(exp, actual):
    diff = actual - exp
    if diff >= 0.2:    return "CALIENTE 🔥🔥"   # inflacion > esperada → malo para renta var
    elif diff >= 0:    return "CALIENTE 🔥"
    elif diff >= -0.2: return "FRIO ❄️"
    else:              return "MUY FRIO ❄️❄️"   # inflacion < esperada → bueno para renta var

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

# ── NQ DAILY ──────────────────────────────────────────────────────────────────
print("📥 Descargando NQ=F daily (2y)...")
df = yf.download("NQ=F", period="2y", interval="1d", auto_adjust=True, progress=False)
if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index).normalize()

rows = []
for d_str, p in sorted(PPI_DATES.items()):
    ts = pd.Timestamp(d_str)
    if ts not in df.index:
        print(f"  ⚠ {d_str} sin sesión")
        continue
    r    = df.loc[ts]
    op   = float(r["Open"]);  hi = float(r["High"])
    lo   = float(r["Low"]);   cl = float(r["Close"])
    rng  = round(hi - lo)
    move = round(cl - op)
    exp  = p["exp"]; actual = p["actual"]
    diff = round(actual - exp, 2)
    bm   = classify_ppi(exp, actual)
    pat  = ohlc_pattern(op, hi, lo, cl)
    rows.append({
        "date":    d_str,
        "exp":     exp,
        "actual":  actual,
        "diff":    diff,
        "bm":      bm,
        "yoy_exp": p["yoy_exp"],
        "yoy_act": p["yoy_act"],
        "rng":     rng,
        "move":    move,
        "bull":    cl >= op,
        "pat":     pat,
    })

print(f"✅ {len(rows)} sesiones PPI-Martes")

total     = len(rows)
n_bull    = sum(1 for r in rows if r["bull"])
n_cal     = sum(1 for r in rows if "CALIENTE" in r["bm"])
n_frio    = sum(1 for r in rows if "FRIO" in r["bm"])
avg_rng   = round(sum(r["rng"]  for r in rows) / total) if total else 0
avg_move  = round(sum(r["move"] for r in rows) / total) if total else 0

cal_rows  = [r for r in rows if "CALIENTE" in r["bm"]]
frio_rows = [r for r in rows if "FRIO"     in r["bm"]]
cal_bull  = sum(1 for r in cal_rows  if r["bull"])
frio_bull = sum(1 for r in frio_rows if r["bull"])
cal_rng   = round(sum(r["rng"]  for r in cal_rows)/len(cal_rows))   if cal_rows  else 0
frio_rng  = round(sum(r["rng"]  for r in frio_rows)/len(frio_rows)) if frio_rows else 0
cal_move  = round(sum(r["move"] for r in cal_rows)/len(cal_rows))   if cal_rows  else 0
frio_move = round(sum(r["move"] for r in frio_rows)/len(frio_rows)) if frio_rows else 0

BM_COLOR = {
    "CALIENTE 🔥🔥": "#dc2626",
    "CALIENTE 🔥":   "#ef4444",
    "FRIO ❄️":       "#22c55e",
    "MUY FRIO ❄️❄️": "#16a34a",
}
PAT_COLOR = {
    "NEWS_DRIVE ↑": "#f97316",  "NEWS_DRIVE ↓": "#f97316",
    "EXPANSIÓN ↑":  "#22c55e",  "EXPANSIÓN ↓":  "#ef4444",
    "TRAMPA BULL":  "#eab308",  "TRAMPA BEAR":  "#eab308",
    "MEGÁFONO":     "#a855f7",  "RANGO ESTRECHO": "#64748b",
}

table_rows = ""
for r in reversed(rows):
    bm_c  = BM_COLOR.get(r["bm"], "#64748b")
    pat_c = PAT_COLOR.get(r["pat"], "#64748b")
    dc    = "bull" if r["bull"] else "bear"
    ms    = f"+{r['move']}" if r["move"] >= 0 else str(r["move"])
    ds    = f"+{r['diff']}" if r["diff"] >= 0 else str(r["diff"])
    # PPI caliente = inflacion alta = malo para NQ (color invertido a lo normal)
    hot   = "CALIENTE" in r["bm"]
    table_rows += f"""
    <tr>
      <td class="dt">{r['date']}</td>
      <td class="num">{r['exp']}%</td>
      <td class="num">{r['actual']}%</td>
      <td><span class="badge" style="background:{bm_c}22;color:{bm_c};border:1px solid {bm_c}44">{r['bm']}</span></td>
      <td class="num {'neg' if hot else 'pos'}">{ds}%</td>
      <td class="num grey">YoY {r['yoy_exp']}→{r['yoy_act']}%</td>
      <td><span class="badge pat" style="background:{pat_c}22;color:{pat_c};border:1px solid {pat_c}44">{r['pat']}</span></td>
      <td class="num">{r['rng']}</td>
      <td class="num {dc}">{ms}</td>
      <td class="dir {dc}">{'▲' if r['bull'] else '▼'}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Backtest PPI Martes — NQ</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box }}
  body {{ background:#0b0f1a; color:#e2e8f0; font-family:'Segoe UI',sans-serif; padding:28px 20px }}
  h1 {{ font-size:1.4rem; color:#fb923c; margin-bottom:4px }}
  .sub {{ font-size:.82rem; color:#475569; margin-bottom:26px }}
  .alert {{ background:#1a0f0b; border:1px solid #f97316; border-radius:8px; padding:12px 16px; margin-bottom:20px; font-size:.8rem; color:#fb923c }}
  .kpi-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:12px; margin-bottom:28px }}
  .kpi {{ background:#111827; border-radius:10px; padding:14px 18px; border-left:3px solid #f97316 }}
  .kpi.green {{ border-color:#22c55e }} .kpi.red {{ border-color:#ef4444 }}
  .kpi label {{ font-size:.7rem; color:#64748b; text-transform:uppercase; letter-spacing:.05em }}
  .kpi value {{ display:block; font-size:1.5rem; font-weight:700; margin-top:4px }}
  .kpi small  {{ font-size:.72rem; color:#94a3b8 }}
  .compare-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:28px }}
  .compare-box {{ background:#111827; border-radius:10px; padding:16px }}
  .compare-box h3 {{ font-size:.85rem; margin-bottom:12px }}
  .cstat {{ display:flex; justify-content:space-between; padding:4px 0; font-size:.82rem; border-bottom:1px solid #1e293b }}
  .cstat:last-child {{ border-bottom:none }}
  .tw {{ overflow-x:auto; border-radius:10px }}
  table {{ width:100%; border-collapse:collapse; font-size:.8rem }}
  thead tr {{ background:#0f172a }}
  th {{ padding:9px 12px; text-align:left; color:#64748b; font-size:.68rem; text-transform:uppercase; letter-spacing:.05em; border-bottom:1px solid #1e293b }}
  tbody tr {{ border-bottom:1px solid #1e293b }}
  tbody tr:hover {{ background:#111827 }}
  td {{ padding:8px 10px; vertical-align:middle }}
  .dt {{ color:#94a3b8; font-size:.75rem; white-space:nowrap }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums }}
  .grey {{ color:#64748b; font-size:.73rem }}
  .bull {{ color:#22c55e }} .bear {{ color:#ef4444 }}
  .pos {{ color:#22c55e }}  .neg  {{ color:#ef4444 }}
  .dir {{ text-align:center }}
  .badge {{ display:inline-block; padding:3px 9px; border-radius:20px; font-size:.71rem; font-weight:700; white-space:nowrap }}
  .pat {{ font-size:.67rem }}
  .note {{ margin-top:18px; font-size:.73rem; color:#475569; border-left:2px solid #334155; padding-left:10px }}
</style>
</head>
<body>
<h1>🌡️ Backtest: PPI (Martes) × NQ Futures</h1>
<p class="sub">Noticia: Martes, 8:30 AM ET · Solo fechas donde PPI cayó en martes · {total} sesiones (2024–2026)</p>

<div class="alert">
  ⚠️ <b>Lógica invertida:</b> En PPI, <span style="color:#ef4444">CALIENTE</span> = inflación alta = malo para NQ · <span style="color:#22c55e">FRIO</span> = inflación baja = bueno para NQ
</div>

<div class="kpi-grid">
  <div class="kpi"><label>Sesiones</label><value>{total}</value><small>PPI en martes</small></div>
  <div class="kpi"><label>Días BULL</label><value>{round(n_bull/total*100) if total else 0}%</value><small>{n_bull}/{total}</small></div>
  <div class="kpi red"><label>CALIENTE</label><value>{n_cal}</value><small>PPI > esperado</small></div>
  <div class="kpi green"><label>FRIO</label><value>{n_frio}</value><small>PPI ≤ esperado</small></div>
  <div class="kpi"><label>Avg Range</label><value>{avg_rng}</value><small>puntos NQ</small></div>
  <div class="kpi"><label>Avg Move</label><value>{avg_move:+}</value><small>Open→Close</small></div>
</div>

<div class="compare-grid">
  <div class="compare-box">
    <h3 style="color:#ef4444">CALIENTE 🔥 ({n_cal} sesiones)</h3>
    <div class="cstat"><span>% Días BULL</span><span><b>{round(cal_bull/len(cal_rows)*100) if cal_rows else 0}%</b></span></div>
    <div class="cstat"><span>Avg Range</span><span><b>{cal_rng} pts</b></span></div>
    <div class="cstat"><span>Avg Move O→C</span><span style="color:#ef4444"><b>{cal_move:+} pts</b></span></div>
  </div>
  <div class="compare-box">
    <h3 style="color:#22c55e">FRIO ❄️ ({n_frio} sesiones)</h3>
    <div class="cstat"><span>% Días BULL</span><span><b>{round(frio_bull/len(frio_rows)*100) if frio_rows else 0}%</b></span></div>
    <div class="cstat"><span>Avg Range</span><span><b>{frio_rng} pts</b></span></div>
    <div class="cstat"><span>Avg Move O→C</span><span style="color:#22c55e"><b>{frio_move:+} pts</b></span></div>
  </div>
</div>

<div class="tw">
<table>
  <thead><tr>
    <th>Fecha</th><th>Exp MoM</th><th>Real MoM</th>
    <th>Clasificación</th><th>Δ MoM</th><th>YoY Trend</th>
    <th>Patrón</th><th>Range</th><th>Move</th><th>Dir</th>
  </tr></thead>
  <tbody>{table_rows}</tbody>
</table>
</div>
<div class="note">
  ★ PPI = Producer Price Index · MoM = cambio mensual · YoY = cambio anual.<br>
  ★ Caliente = inflación mayor a lo esperado (negativo para NQ como regla general).<br>
  ★ Move = Close − Open, basado en OHLC diario de NQ=F.
</div>
</body>
</html>"""

out = Path("backtest_PPI_martes.html")
out.write_text(html, encoding="utf-8")
print(f"✅ Guardado: {out.resolve()}")
