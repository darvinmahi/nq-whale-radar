"""
backtest_remaining_news.py
Backtest: ISM Mfg, ISM Services, Core PCE, Retail Sales
+ Estudio completo del MARTES por tipo (A=JOLTS, B=CB, C=PPI, D=Normal)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# ─── FECHAS ───────────────────────────────────────────────────────────────────

DATES = {
    "ISM_MFG": [
        "2024-01-02","2024-02-01","2024-03-01","2024-04-01","2024-05-01",
        "2024-06-03","2024-07-01","2024-08-01","2024-09-03","2024-10-01",
        "2024-11-01","2024-12-02",
        "2025-01-02","2025-02-03","2025-03-03","2025-04-01","2025-05-01",
        "2025-06-02","2025-07-01","2025-08-01","2025-09-02","2025-10-01",
        "2025-11-03","2025-12-01",
        "2026-01-02","2026-02-03","2026-03-03",
    ],
    "ISM_SVC": [
        "2024-01-05","2024-02-05","2024-03-05","2024-04-03","2024-05-03",
        "2024-06-05","2024-07-03","2024-08-05","2024-09-05","2024-10-03",
        "2024-11-05","2024-12-04",
        "2025-01-07","2025-02-05","2025-03-05","2025-04-03","2025-05-05",
        "2025-06-04","2025-07-07","2025-08-06","2025-09-04","2025-10-03",
        "2025-11-05","2025-12-03",
        "2026-01-07","2026-02-05","2026-03-05",
    ],
    "PCE": [
        "2024-01-26","2024-02-29","2024-03-29","2024-04-26","2024-05-31",
        "2024-06-28","2024-07-26","2024-08-30","2024-09-27","2024-10-31",
        "2024-11-27","2024-12-20",
        "2025-01-31","2025-02-28","2025-03-28","2025-04-30","2025-05-30",
        "2025-06-27","2025-07-25","2025-08-29","2025-09-26","2025-10-31",
        "2025-11-26","2025-12-19",
        "2026-01-30","2026-02-27","2026-03-27",
    ],
    "RETAIL": [
        "2024-01-17","2024-02-15","2024-03-14","2024-04-15","2024-05-15",
        "2024-06-18","2024-07-16","2024-08-15","2024-09-17","2024-10-17",
        "2024-11-15","2024-12-17",
        "2025-01-16","2025-02-14","2025-03-17","2025-04-16","2025-05-15",
        "2025-06-17","2025-07-16","2025-08-15","2025-09-17","2025-10-16",
        "2025-11-14","2025-12-16",
        "2026-01-15","2026-02-18","2026-03-17",
    ],
}

# Martes con noticias conocidas (ya estudiados)
TUESDAY_NEWS = {
    "JOLTS": [
        "2024-01-09","2024-02-06","2024-03-05","2024-04-02","2024-05-07",
        "2024-06-04","2024-07-02","2024-08-06","2024-09-03","2024-10-01",
        "2024-11-05","2024-12-03",
        "2025-01-07","2025-02-04","2025-03-11","2025-04-01","2025-05-06",
        "2025-06-03","2025-07-01","2025-08-05","2025-09-02","2025-10-07",
        "2025-11-04","2025-12-02",
        "2026-01-06","2026-02-03","2026-03-10",
    ],
    "CB": [
        "2024-01-30","2024-02-27","2024-03-26","2024-04-30","2024-05-28",
        "2024-06-25","2024-07-30","2024-08-27","2024-09-24","2024-10-29",
        "2024-11-19","2024-12-17",  # algunas mueven a martes
        "2025-01-28","2025-02-25","2025-03-25","2025-04-29","2025-05-27",
        "2025-06-24","2025-07-29","2025-08-26","2025-09-30","2025-10-28",
        "2025-11-18","2025-12-16","2026-01-27","2026-02-24","2026-03-24",
    ],
    "PPI": [
        "2024-02-13","2024-05-14","2024-08-13","2024-11-12",
        "2025-02-13","2025-05-13","2025-08-12","2025-11-11",
    ],
}

ALL_NEWS_TUESDAYS = set()
for v in TUESDAY_NEWS.values():
    ALL_NEWS_TUESDAYS.update(v)

# ─── DATOS ────────────────────────────────────────────────────────────────────

print("Descargando NQ=F...")
raw = yf.download("NQ=F", start="2024-01-01", interval="1d", auto_adjust=True, progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = pd.to_datetime(raw.index).tz_localize(None)
today = pd.Timestamp(datetime.now().date())
print(f"Datos: {len(raw)} filas | {raw.index[0].date()} -> {raw.index[-1].date()}")

def get_session(ds):
    dt = pd.Timestamp(ds)
    if dt > today:
        return None
    for try_dt in [dt, dt + pd.Timedelta(days=1)]:
        mask = raw.index.date == try_dt.date()
        if mask.any():
            row = raw[mask]
            o = float(row["Open"].values[0])
            h = float(row["High"].values[0])
            l = float(row["Low"].values[0])
            c = float(row["Close"].values[0])
            return {"date": ds, "o": o, "h": h, "l": l, "c": c,
                    "rng": round(h - l, 1), "move": round(c - o, 1),
                    "pct": round((c - o) / o * 100, 2),
                    "bias": "BULL" if c >= o else "BEAR"}
    return None

# ─── NOTICIAS RESTANTES ───────────────────────────────────────────────────────

all_data = {}
stats    = {}

for nt, dates in DATES.items():
    sessions = [s for ds in dates if (s := get_session(ds)) is not None]
    all_data[nt] = sessions
    if not sessions:
        continue
    ranges = [s["rng"] for s in sessions]
    moves  = [s["move"] for s in sessions]
    bulls  = sum(1 for s in sessions if s["bias"] == "BULL")
    n      = len(sessions)
    stats[nt] = {
        "n": n, "bull": bulls, "bear": n - bulls,
        "bull_pct": round(bulls / n * 100),
        "avg_range": round(sum(ranges) / n, 1),
        "max_range": round(max(ranges), 1),
        "avg_move": round(sum(moves) / n, 1),
        "avg_move_abs": round(sum(abs(m) for m in moves) / n, 1),
    }

# ─── ESTUDIO DEL MARTES ──────────────────────────────────────────────────────

# Recolectar todos los martes en el dataset
tuesdays_all = [(str(dt.date()), raw.index[i])
                for i, dt in enumerate(raw.index) if dt.dayofweek == 1]

tuesday_groups = {"JOLTS": [], "CB": [], "PPI": [], "NORMAL": []}

for ds, dt in tuesdays_all:
    s = get_session(ds)
    if s is None:
        continue
    if ds in TUESDAY_NEWS.get("JOLTS", []):
        tuesday_groups["JOLTS"].append(s)
    elif ds in TUESDAY_NEWS.get("CB", []):
        tuesday_groups["CB"].append(s)
    elif ds in TUESDAY_NEWS.get("PPI", []):
        tuesday_groups["PPI"].append(s)
    else:
        tuesday_groups["NORMAL"].append(s)

tue_stats = {}
for typ, sessions in tuesday_groups.items():
    if not sessions:
        continue
    ranges = [s["rng"] for s in sessions]
    moves  = [s["move"] for s in sessions]
    bulls  = sum(1 for s in sessions if s["bias"] == "BULL")
    n      = len(sessions)
    tue_stats[typ] = {
        "n": n, "bull": bulls, "bear": n - bulls,
        "bull_pct": round(bulls / n * 100),
        "avg_range": round(sum(ranges) / n, 1),
        "max_range": round(max(ranges), 1),
        "min_range": round(min(ranges), 1),
        "avg_move": round(sum(moves) / n, 1),
        "avg_move_abs": round(sum(abs(m) for m in moves) / n, 1),
    }

# ─── PRINT RESULTADOS ─────────────────────────────────────────────────────────

print("\n--- NOTICIAS RESTANTES ---")
print(f"{'Noticia':<10} {'AvgRng':>7} {'MaxRng':>7} {'AvgMov':>7} {'Bull%':>6}  N")
for nt in ["ISM_MFG","ISM_SVC","PCE","RETAIL"]:
    s = stats.get(nt, {})
    if s:
        print(f"{nt:<10} {s['avg_range']:>7} {s['max_range']:>7} {s['avg_move']:>7} {s['bull_pct']:>5}%  {s['n']}")

print("\n--- ESTUDIO DEL MARTES POR TIPO ---")
print(f"{'Tipo':<8} {'AvgRng':>7} {'MaxRng':>7} {'MinRng':>7} {'AvgMov':>7} {'Bull%':>6}  N")
for typ in ["JOLTS","CB","PPI","NORMAL"]:
    s = tue_stats.get(typ, {})
    if s:
        print(f"{typ:<8} {s['avg_range']:>7} {s['max_range']:>7} {s['min_range']:>7} {s['avg_move']:>7} {s['bull_pct']:>5}%  {s['n']}")

# ─── HTML ─────────────────────────────────────────────────────────────────────

COLOR_NT = {
    "ISM_MFG": {"c":"#22d3ee","bg":"#061a20","bd":"#0e4050","lt":"#67e8f9"},
    "ISM_SVC": {"c":"#4ade80","bg":"#061a10","bd":"#14532d","lt":"#86efac"},
    "PCE":     {"c":"#f472b6","bg":"#1a0614","bd":"#701a5a","lt":"#f9a8d4"},
    "RETAIL":  {"c":"#fbbf24","bg":"#1a1400","bd":"#5a4500","lt":"#fde68a"},
}
LABEL_NT = {
    "ISM_MFG": "🏭 ISM Manufacturing PMI",
    "ISM_SVC": "🛎️ ISM Services PMI",
    "PCE":     "💰 Core PCE",
    "RETAIL":  "🛒 Retail Sales",
}
HORA_NT = {
    "ISM_MFG": "10:00 AM ET · 1.er día del mes",
    "ISM_SVC": "10:00 AM ET · ~3.er día del mes",
    "PCE":     "8:30 AM ET · Último viernes del mes",
    "RETAIL":  "8:30 AM ET · ~día 15 del mes",
}

COLOR_TUE = {
    "JOLTS":  "#67e8f9",
    "CB":     "#fb923c",
    "PPI":    "#c084fc",
    "NORMAL": "#94a3b8",
}
TUE_LABEL = {
    "JOLTS":  "Tipo A — JOLTS Job Openings",
    "CB":     "Tipo B — CB Consumer Confidence",
    "PPI":    "Tipo C — PPI (cuando cae martes)",
    "NORMAL": "Tipo D — Martes sin noticia mayor",
}
TUE_DESC = {
    "JOLTS":  "1.er martes del mes · 10:00 AM ET",
    "CB":     "Último martes del mes · 10:00 AM ET",
    "PPI":    "Variable — 8:30 AM ET",
    "NORMAL": "Sin catalizador claro",
}

def row_html(ss):
    c = "#34d399" if ss["move"] >= 0 else "#f87171"
    mv = f'+{ss["move"]}' if ss["move"] >= 0 else str(ss["move"])
    return (f'<tr><td>{ss["date"]}</td>'
            f'<td style="color:{c};font-weight:700">{mv}</td>'
            f'<td style="color:{c}">{ss["pct"]:+.2f}%</td>'
            f'<td>{ss["rng"]}</td>'
            f'<td style="color:{c}">{ss["bias"]}</td></tr>')

def news_card(nt):
    s  = stats.get(nt, {})
    cl = COLOR_NT[nt]
    sessions = all_data.get(nt, [])
    n = s.get("n", 0)
    if n == 0:
        return f'<div class="card" style="--c:{cl["c"]}"><p>Sin datos</p></div>'
    bull_pct = s["bull_pct"]
    rows = "".join(row_html(ss) for ss in sorted(sessions, key=lambda x: x["date"], reverse=True))
    return f"""
    <div class="card" style="--c:{cl['c']};--bg:{cl['bg']};--bd:{cl['bd']}">
      <div class="card-hdr">
        <div>
          <div class="card-title">{LABEL_NT[nt]}</div>
          <div class="card-sub">{HORA_NT[nt]} · {n} sesiones</div>
        </div>
        <div class="badge" style="color:{cl['c']};border-color:{cl['bd']};background:{cl['bg']}">ALTO</div>
      </div>
      <div class="stats-g">
        <div class="st"><label>Avg Range</label><v style="color:{cl['c']}">{s['avg_range']}</v><u>pts</u></div>
        <div class="st"><label>Max Range</label><v>{s['max_range']}</v><u>pts</u></div>
        <div class="st"><label>Avg Move</label><v>{s['avg_move']}</v><u>pts</u></div>
        <div class="st"><label>Avg|Move|</label><v>{s['avg_move_abs']}</v><u>pts</u></div>
        <div class="st"><label>Bull</label><v style="color:#34d399">{s['bull']}</v><u>/{n}</u></div>
        <div class="st"><label>%Bull</label><v style="color:#34d399">{bull_pct}%</v><u></u></div>
      </div>
      <div class="bb">
        <div class="bb-bull" style="width:{bull_pct}%">{'BULL '+str(bull_pct)+'%' if bull_pct > 20 else ''}</div>
        <div class="bb-bear" style="flex:1">{'BEAR '+str(100-bull_pct)+'%' if 100-bull_pct > 20 else ''}</div>
      </div>
      <table class="tbl"><thead><tr><th>Fecha</th><th>Move</th><th>%</th><th>Range</th><th>Bias</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>"""

def tue_card(typ):
    s  = tue_stats.get(typ, {})
    c  = COLOR_TUE[typ]
    sessions = tuesday_groups.get(typ, [])
    n = s.get("n", 0)
    if n == 0:
        return f'<div class="card" style="--c:{c}"><p>Sin datos</p></div>'
    bull_pct = s["bull_pct"]
    rows = "".join(row_html(ss) for ss in sorted(sessions, key=lambda x: x["date"], reverse=True))
    insight = ""
    if typ == "JOLTS":
        insight = "⚠️ El más silencioso — bajo rango, sin dirección clara"
    elif typ == "CB":
        insight = "✅ El más predecible — tendencia alcista dominante"
    elif typ == "PPI":
        insight = "🚨 El más explosivo — impulso fuerte 50% de las veces"
    elif typ == "NORMAL":
        pred = "alcista" if s['avg_move'] > 0 else "bajista"
        insight = f"Martes 'tranquilo' — sigue tendencia, sesgo {pred}"
    return f"""
    <div class="card" style="--c:{c};--bg:#0d1117;--bd:#1e293b">
      <div class="card-hdr">
        <div>
          <div class="card-title" style="color:{c}">{TUE_LABEL[typ]}</div>
          <div class="card-sub">{TUE_DESC[typ]} · {n} sesiones</div>
        </div>
        <div class="badge" style="color:{c};border-color:{c}33;background:{c}11">MARTES</div>
      </div>
      <div class="insight">{insight}</div>
      <div class="stats-g">
        <div class="st"><label>Avg Range</label><v style="color:{c}">{s['avg_range']}</v><u>pts</u></div>
        <div class="st"><label>Max Range</label><v>{s['max_range']}</v><u>pts</u></div>
        <div class="st"><label>Min Range</label><v>{s['min_range']}</v><u>pts</u></div>
        <div class="st"><label>Avg Move</label><v style="color:{'#34d399' if s['avg_move']>=0 else '#f87171'}">{s['avg_move']}</v><u>pts</u></div>
        <div class="st"><label>Avg|Move|</label><v>{s['avg_move_abs']}</v><u>pts</u></div>
        <div class="st"><label>%Bull</label><v style="color:{'#34d399' if bull_pct>=50 else '#f87171'}">{bull_pct}%</v><u></u></div>
      </div>
      <div class="bb">
        <div class="bb-bull" style="width:{bull_pct}%">{'BULL '+str(bull_pct)+'%' if bull_pct > 20 else ''}</div>
        <div class="bb-bear" style="flex:1">{'BEAR '+str(100-bull_pct)+'%' if 100-bull_pct > 20 else ''}</div>
      </div>
      <table class="tbl"><thead><tr><th>Fecha</th><th>Move</th><th>%</th><th>Range</th><th>Bias</th></tr></thead>
      <tbody>{rows}</tbody></table>
    </div>"""

# Tabla comparativa martes
tue_cmp = ""
for typ in ["JOLTS","CB","PPI","NORMAL"]:
    s = tue_stats.get(typ, {})
    if not s:
        continue
    c = COLOR_TUE[typ]
    tue_cmp += (f"<tr><td style='color:{c};font-weight:700'>{TUE_LABEL[typ]}</td>"
                f"<td style='color:{c}'>{s['avg_range']}</td>"
                f"<td>{s['max_range']}</td><td>{s['min_range']}</td>"
                f"<td>{s['avg_move']}</td>"
                f"<td style='color:#34d399'>{s['bull_pct']}%</td>"
                f"<td>{s['n']}</td></tr>")

# Tabla comparativa noticias
news_cmp = ""
all_news_summary = [
    ("CPI","📊 CPI","#ef4444",431.8,1464.5,-5.7,56,27),
    ("NFP","💼 NFP","#a855f7",450.6,1325.5,-2.1,58,26),
    ("FOMC","🏦 FOMC","#fb923c",467.0,1049.5,5.9,50,18),
]
for nt, label, c, avg_r, max_r, avg_m, bull_p, n in all_news_summary:
    news_cmp += (f"<tr><td style='color:{c};font-weight:700'>{label}</td>"
                 f"<td style='color:{c}'>{avg_r}</td><td>{max_r}</td>"
                 f"<td>{avg_m}</td><td style='color:#34d399'>{bull_p}%</td><td>{n}</td></tr>")
for nt in ["ISM_MFG","ISM_SVC","PCE","RETAIL"]:
    s = stats.get(nt, {})
    if not s:
        continue
    cl = COLOR_NT[nt]
    news_cmp += (f"<tr><td style='color:{cl['c']};font-weight:700'>{LABEL_NT[nt]}</td>"
                 f"<td style='color:{cl['c']}'>{s['avg_range']}</td>"
                 f"<td>{s['max_range']}</td><td>{s['avg_move']}</td>"
                 f"<td style='color:#34d399'>{s['bull_pct']}%</td><td>{s['n']}</td></tr>")

news_cards = "\n".join(news_card(nt) for nt in ["ISM_MFG","ISM_SVC","PCE","RETAIL"])
tue_cards  = "\n".join(tue_card(typ) for typ in ["CB","JOLTS","PPI","NORMAL"])

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Estudio Noticias + Martes — NQ Whale Radar</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0b0f1a;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:24px 20px;max-width:1060px;margin:0 auto}}
h1{{font-size:1.2rem;color:#7dd3fc;margin-bottom:3px}}
h2{{font-size:.9rem;color:#cbd5e1;margin:28px 0 12px;padding-bottom:6px;border-bottom:1px solid #1e293b;text-transform:uppercase;letter-spacing:.06em}}
.meta{{font-size:.74rem;color:#475569;margin-bottom:16px}}
.nav{{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}}
.nav a{{background:#1e293b;color:#94a3b8;padding:4px 12px;border-radius:8px;text-decoration:none;font-size:.72rem}}
.nav a:hover{{background:#334155;color:#f1f5f9}}
.card{{background:var(--bg,#0d1117);border:1px solid var(--bd,#1e293b);border-top:3px solid var(--c);border-radius:14px;padding:18px;margin-bottom:16px}}
.card-hdr{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}}
.card-title{{font-size:.9rem;font-weight:700;color:#f1f5f9;margin-bottom:2px}}
.card-sub{{font-size:.68rem;color:#475569}}
.badge{{padding:2px 10px;border-radius:20px;font-size:.65rem;font-weight:700;border:1px solid}}
.insight{{background:#0f172a;border-left:3px solid var(--c,#3b82f6);padding:8px 12px;border-radius:6px;font-size:.76rem;color:#94a3b8;margin-bottom:12px}}
.stats-g{{display:grid;grid-template-columns:repeat(6,1fr);gap:7px;margin-bottom:10px}}
.st{{background:#0f172a;border-radius:8px;padding:8px 5px;text-align:center}}
.st label{{display:block;font-size:.58rem;color:#475569;text-transform:uppercase;letter-spacing:.04em;margin-bottom:3px}}
.st v{{display:block;font-size:1rem;font-weight:700;color:#e2e8f0}}
.st u{{font-size:.6rem;color:#475569;font-style:normal}}
.bb{{display:flex;height:20px;border-radius:8px;overflow:hidden;font-size:.69rem;font-weight:700;margin-bottom:10px}}
.bb-bull{{background:#14532d;color:#4ade80;display:flex;align-items:center;justify-content:center}}
.bb-bear{{background:#450a0a;color:#f87171;display:flex;align-items:center;justify-content:center}}
.tbl{{width:100%;border-collapse:collapse;font-size:.73rem}}
.tbl th{{padding:5px 8px;text-align:left;color:#475569;font-size:.61rem;text-transform:uppercase;border-bottom:1px solid #1e293b;background:#0f172a}}
.tbl td{{padding:5px 8px;border-bottom:1px solid #1e293b22}}
.tbl tr:hover td{{background:#111827}}
.cmp{{width:100%;border-collapse:collapse;font-size:.77rem;margin-bottom:22px;overflow:hidden;border-radius:10px}}
.cmp th{{padding:7px 10px;background:#0f172a;border-bottom:1px solid #1e293b;color:#475569;font-size:.63rem;text-transform:uppercase;text-align:left}}
.cmp td{{padding:7px 10px;border-bottom:1px solid #1e293b33}}
.two-col{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
@media(max-width:700px){{.two-col{{grid-template-columns:1fr}}.stats-g{{grid-template-columns:repeat(3,1fr)}}}}
</style>
</head>
<body>
<h1>📰 Estudio Completo: Noticias + Martes — NQ Futures</h1>
<p class="meta">ISM · PCE · Retail Sales + Desglose completo del Martes por tipo · Generado {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
<div class="nav">
  <a href="daily_dashboard.html">🐋 Dashboard</a>
  <a href="backtest_critical_news.html">🔴 CPI/NFP/FOMC</a>
  <a href="backtest_CB_confidence.html">CB</a>
  <a href="backtest_JOLTS.html">JOLTS</a>
</div>

<h2>🔴 Mapa Completo de Noticias</h2>
<div style="overflow-x:auto;border-radius:10px;margin-bottom:6px">
<table class="cmp">
  <thead><tr><th>Noticia</th><th>Avg Range</th><th>Max Range</th><th>Avg Move</th><th>%Bull</th><th>N</th></tr></thead>
  <tbody>{news_cmp}</tbody>
</table>
</div>

<h2>🟠 Noticias de Impacto Alto</h2>
<div class="two-col">{news_cards}</div>

<h2>📅 Estudio del MARTES por Tipo</h2>
<div style="overflow-x:auto;border-radius:10px;margin-bottom:6px">
<table class="cmp">
  <thead><tr><th>Tipo de Martes</th><th>Avg Range</th><th>Max Range</th><th>Min Range</th><th>Avg Move</th><th>%Bull</th><th>N</th></tr></thead>
  <tbody>{tue_cmp}</tbody>
</table>
</div>
<div class="two-col">{tue_cards}</div>

<div style="font-size:.67rem;color:#334155;border-left:2px solid #1e293b;padding-left:10px;margin-top:8px">
  NQ=F daily OHLC via yfinance · Range=High-Low del día · Move=Close-Open
</div>
</body>
</html>"""

out = r"C:\Users\FxDarvin\Desktop\PAgina\backtest_remaining_news.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"\nGuardado: {out}")
