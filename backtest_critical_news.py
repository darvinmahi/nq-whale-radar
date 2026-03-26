"""
backtest_critical_news.py
Backtest de noticias CRITICAS para NQ: CPI, NFP, FOMC
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

DATES = {
    "CPI": [
        "2024-01-11","2024-02-13","2024-03-12","2024-04-10","2024-05-15",
        "2024-06-12","2024-07-11","2024-08-14","2024-09-11","2024-10-10",
        "2024-11-13","2024-12-11",
        "2025-01-15","2025-02-12","2025-03-12","2025-04-10","2025-05-13",
        "2025-06-11","2025-07-15","2025-08-13","2025-09-10","2025-10-15",
        "2025-11-12","2025-12-10",
        "2026-01-14","2026-02-12","2026-03-12",
    ],
    "NFP": [
        "2024-01-05","2024-02-02","2024-03-08","2024-04-05","2024-05-03",
        "2024-06-07","2024-07-05","2024-08-02","2024-09-06","2024-10-04",
        "2024-11-01","2024-12-06",
        "2025-01-10","2025-02-07","2025-03-07","2025-04-04","2025-05-02",
        "2025-06-06","2025-07-03","2025-08-01","2025-09-05","2025-10-03",
        "2025-11-07","2025-12-05",
        "2026-01-09","2026-02-06","2026-03-07",
    ],
    "FOMC": [
        "2024-01-31","2024-03-20","2024-05-01","2024-06-12",
        "2024-07-31","2024-09-18","2024-11-07","2024-12-18",
        "2025-01-29","2025-03-19","2025-05-07","2025-06-18",
        "2025-07-30","2025-09-17","2025-11-05","2025-12-17",
        "2026-01-29","2026-03-19",
    ],
}

print("Descargando NQ=F datos diarios...")
raw = yf.download("NQ=F", start="2024-01-01", interval="1d", auto_adjust=True, progress=False)

# Aplanar multi-index
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)

raw.index = pd.to_datetime(raw.index).tz_localize(None)
today = pd.Timestamp(datetime.now().date())
print(f"Datos: {len(raw)} filas, {raw.index[0].date()} -> {raw.index[-1].date()}")

def get_session(ds):
    dt = pd.Timestamp(ds)
    if dt > today:
        return None
    mask = raw.index.date == dt.date()
    if not mask.any():
        # prueba dia siguiente
        dt2 = dt + pd.Timedelta(days=1)
        mask = raw.index.date == dt2.date()
    if not mask.any():
        return None
    row = raw[mask]
    o = float(row["Open"].values[0])
    h = float(row["High"].values[0])
    l = float(row["Low"].values[0])
    c = float(row["Close"].values[0])
    rng  = round(h - l, 1)
    move = round(c - o, 1)
    pct  = round((move / o) * 100, 2)
    return {"date": ds, "o": o, "h": h, "l": l, "c": c,
            "rng": rng, "move": move, "pct": pct,
            "bias": "BULL" if move >= 0 else "BEAR"}

all_data = {}
stats    = {}

for nt, dates in DATES.items():
    sessions = [s for ds in dates if (s := get_session(ds)) is not None]
    all_data[nt] = sessions
    if not sessions:
        continue
    ranges = [s["rng"]  for s in sessions]
    moves  = [s["move"] for s in sessions]
    bulls  = sum(1 for s in sessions if s["bias"] == "BULL")
    n      = len(sessions)
    stats[nt] = {
        "n": n, "bull": bulls, "bear": n - bulls,
        "bull_pct": round(bulls / n * 100),
        "avg_range": round(sum(ranges) / n, 1),
        "max_range": round(max(ranges), 1),
        "min_range": round(min(ranges), 1),
        "avg_move":  round(sum(moves) / n, 1),
        "avg_move_abs": round(sum(abs(m) for m in moves) / n, 1),
    }
    s = stats[nt]
    print(f"  {nt}: {n} sesiones | Bull {bulls} Bear {n-bulls} ({s['bull_pct']}% bull) | "
          f"AvgRange {s['avg_range']} | MaxRange {s['max_range']} | AvgMove {s['avg_move']}")

# ─── HTML ──────────────────────────────────────────────────────────────────────

COLOR = {
    "CPI":  {"c":"#ef4444","bg":"#1a0808","bd":"#5a1a1a","lt":"#fca5a5"},
    "NFP":  {"c":"#a855f7","bg":"#130d1f","bd":"#4a1f80","lt":"#d8b4fe"},
    "FOMC": {"c":"#fb923c","bg":"#1a0e04","bd":"#5a3010","lt":"#fcd34d"},
}
LABEL = {
    "CPI":  "CPI — Consumer Price Index",
    "NFP":  "NFP — Non-Farm Payrolls",
    "FOMC": "FOMC — Fed Decision",
}
ICON  = {"CPI":"📊","NFP":"💼","FOMC":"🏦"}
HORA  = {"CPI":"8:30 AM ET","NFP":"8:30 AM ET","FOMC":"2:00 PM ET"}
FREQ  = {"CPI":"Mensual (miércoles)","NFP":"1.er viernes del mes","FOMC":"8× al año (miércoles)"}
DAY_MAP = {"Wednesday":"Miér","Friday":"Vier","Tuesday":"Mar","Thursday":"Juev","Monday":"Lun","Saturday":"Sáb","Sunday":"Dom"}

def day_es(ds):
    return DAY_MAP.get(pd.Timestamp(ds).day_name(), "—")

def make_card(nt):
    s  = stats.get(nt, {})
    cl = COLOR[nt]
    sessions = all_data.get(nt, [])
    n = s.get("n", 0)
    if n == 0:
        return f'<div class="card" style="--c:{cl["c"]}"><p>Sin datos</p></div>'

    bull_pct = s["bull_pct"]
    bear_pct = 100 - bull_pct

    rows = ""
    for ss in sorted(sessions, key=lambda x: x["date"], reverse=True):
        mv_c = "#34d399" if ss["move"] >= 0 else "#f87171"
        mv_s = f'+{ss["move"]}' if ss["move"] >= 0 else str(ss["move"])
        pc_c = "#34d399" if ss["pct"] >= 0 else "#f87171"
        rows += f"""
        <tr>
          <td>{ss['date']}</td>
          <td>{day_es(ss['date'])}</td>
          <td style="color:{mv_c};font-weight:700">{mv_s}</td>
          <td style="color:{pc_c}">{ss['pct']:+.2f}%</td>
          <td>{ss['rng']}</td>
          <td style="color:{mv_c}">{ss['bias']}</td>
        </tr>"""

    return f"""
    <div class="card" style="--c:{cl['c']};--bg:{cl['bg']};--bd:{cl['bd']}">
      <div class="card-hdr">
        <div>
          <div class="card-title">{ICON[nt]} {LABEL[nt]}</div>
          <div class="card-sub">{HORA[nt]} · {FREQ[nt]} · {n} sesiones</div>
        </div>
        <div class="badge" style="color:{cl['c']};border-color:{cl['bd']};background:{cl['bg']}">CRÍTICO</div>
      </div>
      <div class="stats-g">
        <div class="st"><label>Avg Range</label><v style="color:{cl['c']}">{s['avg_range']}</v><u>pts</u></div>
        <div class="st"><label>Max Range</label><v style="color:{cl['lt']}">{s['max_range']}</v><u>pts</u></div>
        <div class="st"><label>Min Range</label><v>{s['min_range']}</v><u>pts</u></div>
        <div class="st"><label>Avg Move</label><v>{s['avg_move']}</v><u>pts</u></div>
        <div class="st"><label>Avg|Move|</label><v>{s['avg_move_abs']}</v><u>pts</u></div>
        <div class="st"><label>Bull/Bear</label><v style="color:#34d399">{s['bull']}</v><u>/ {s['bear']}</u></div>
      </div>
      <div class="bb">
        <div class="bb-bull" style="width:{bull_pct}%">{'BULL '+str(bull_pct)+'%' if bull_pct > 20 else ''}</div>
        <div class="bb-bear" style="flex:1">{'BEAR '+str(bear_pct)+'%' if bear_pct > 20 else ''}</div>
      </div>
      <table class="tbl">
        <thead><tr><th>Fecha</th><th>Día</th><th>Move</th><th>%</th><th>Range</th><th>Bias</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""

cards = "\n".join(make_card(nt) for nt in ["CPI","NFP","FOMC"])

# Tabla comparativa
def cmp_row(nt, s, cl):
    return (f"<tr><td><span style='color:{cl};font-weight:700'>{ICON.get(nt,'')} {nt}</span></td>"
            f"<td style='font-weight:700;color:{cl}'>{s['avg_range']}</td>"
            f"<td>{s['max_range']}</td><td>{s['avg_move']}</td>"
            f"<td style='color:#34d399'>{s['bull_pct']}%</td><td>{s['n']}</td></tr>")

cmp = ""
for nt in ["CPI","NFP","FOMC"]:
    if nt in stats:
        cmp += cmp_row(nt, stats[nt], COLOR[nt]["c"])

cmp += """
<tr style="opacity:.55;border-top:2px solid #1e293b">
  <td><span style="color:#f97316">🟠 CB Consumer Confidence</span></td>
  <td style="color:#f97316">315</td><td>~580</td><td>~+40</td>
  <td style="color:#34d399">46%</td><td>13</td>
</tr>
<tr style="opacity:.55">
  <td><span style="color:#f97316">🟠 JOLTS Job Openings</span></td>
  <td style="color:#f97316">387</td><td>~620</td><td>~-66</td>
  <td style="color:#f87171">42%</td><td>12</td>
</tr>"""

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Backtest Noticias Criticas NQ</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0b0f1a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:24px 20px;max-width:1040px;margin:0 auto}}
h1{{font-size:1.25rem;color:#7dd3fc;margin-bottom:4px}}
.meta{{font-size:.77rem;color:#475569;margin-bottom:18px}}
.nav{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.nav a{{background:#1e293b;color:#94a3b8;padding:4px 12px;border-radius:8px;text-decoration:none;font-size:.74rem}}
.nav a:hover{{background:#334155;color:#f1f5f9}}
.card{{background:var(--bg,#111827);border:1px solid var(--bd,#1e293b);border-top:3px solid var(--c);border-radius:14px;padding:20px;margin-bottom:20px}}
.card-hdr{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px}}
.card-title{{font-size:.95rem;font-weight:700;color:#f1f5f9;margin-bottom:2px}}
.card-sub{{font-size:.7rem;color:#475569}}
.badge{{padding:3px 12px;border-radius:20px;font-size:.67rem;font-weight:700;border:1px solid}}
.stats-g{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:12px}}
.st{{background:#0f172a;border-radius:8px;padding:9px 6px;text-align:center}}
.st label{{display:block;font-size:.6rem;color:#475569;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}}
.st v{{display:block;font-size:1.05rem;font-weight:700;color:#e2e8f0}}
.st u{{font-size:.62rem;color:#475569;font-style:normal}}
.bb{{display:flex;height:22px;border-radius:8px;overflow:hidden;font-size:.71rem;font-weight:700;margin-bottom:12px}}
.bb-bull{{background:#14532d;color:#4ade80;display:flex;align-items:center;justify-content:center}}
.bb-bear{{background:#450a0a;color:#f87171;display:flex;align-items:center;justify-content:center}}
.tbl{{width:100%;border-collapse:collapse;font-size:.75rem}}
.tbl th{{padding:6px 10px;text-align:left;color:#475569;font-size:.63rem;text-transform:uppercase;border-bottom:1px solid #1e293b;background:#0f172a}}
.tbl td{{padding:6px 10px;border-bottom:1px solid #1e293b33}}
.tbl tr:hover td{{background:#111827}}
.cmp{{width:100%;border-collapse:collapse;font-size:.79rem;margin-bottom:26px;border-radius:10px;overflow:hidden}}
.cmp th{{padding:8px 12px;text-align:left;color:#475569;font-size:.66rem;text-transform:uppercase;letter-spacing:.05em;background:#0f172a;border-bottom:1px solid #1e293b}}
.cmp td{{padding:8px 12px;border-bottom:1px solid #1e293b44}}
</style>
</head>
<body>
<h1>🔴 Backtest Noticias Criticas — NQ Futures</h1>
<p class="meta">CPI · NFP · FOMC — comportamiento real 2024–2026 · Generado {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div class="nav">
  <a href="daily_dashboard.html">🐋 Dashboard</a>
  <a href="news_impact_map.html">📰 Mapa</a>
  <a href="tuesday_calendar.html">🗓️ Martes</a>
  <a href="backtest_CB_confidence.html">CB</a>
  <a href="backtest_JOLTS.html">JOLTS</a>
</div>

<h3 style="font-size:.75rem;color:#475569;text-transform:uppercase;letter-spacing:.05em;margin-bottom:10px">Comparativa General</h3>
<div style="overflow-x:auto;border-radius:10px;margin-bottom:24px">
<table class="cmp">
  <thead><tr><th>Noticia</th><th>Avg Range</th><th>Max Range</th><th>Avg Move</th><th>% Bull</th><th>N</th></tr></thead>
  <tbody>{cmp}</tbody>
</table>
</div>

{cards}

<div style="font-size:.68rem;color:#334155;border-left:2px solid #1e293b;padding-left:10px;margin-top:4px">
  Datos NQ=F via yfinance · Daily OHLC · Rango = High-Low del dia completo · Move = Close-Open
</div>
</body>
</html>"""

out = r"C:\Users\FxDarvin\Desktop\PAgina\backtest_critical_news.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\nGuardado: {out}")
print(f"\nComparativa:")
print(f"{'Noticia':<6}  {'AvgRng':>7}  {'MaxRng':>7}  {'AvgMov':>7}  {'Bull%':>6}  N")
for nt in ["CPI","NFP","FOMC"]:
    s = stats.get(nt,{})
    if s:
        print(f"{nt:<6}  {s['avg_range']:>7}  {s['max_range']:>7}  {s['avg_move']:>7}  {s['bull_pct']:>5}%  {s['n']}")
