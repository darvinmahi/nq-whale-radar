"""
tabla_cot_con_dias.py
Tabla COT semanas + para las semanas de DIVERGENCIA
expande cada día (Lun-Vie) con datos NQ reales
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict

# ── CARGAR COT ────────────────────────────────────────────────────────
cot_weeks = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d    = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            al   = int(r.get("Asset_Mgr_Positions_Long_All",  0) or 0)
            as_  = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            ll   = int(r.get("Lev_Money_Positions_Long_All",  0) or 0)
            ls   = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
            cot_weeks.append({
                "date":d, "am_l":al, "am_s":as_, "am_net":al-as_,
                "lev_l":ll, "lev_s":ls, "lev_net":ll-ls,
                "am_delta":0, "lev_pct":50, "lev_delta":0
            })
        except: pass
cot_weeks.sort(key=lambda x: x["date"])

for i, w in enumerate(cot_weeks):
    if i > 0:
        w["am_delta"]  = w["am_net"] - cot_weeks[i-1]["am_net"]
        w["lev_delta"] = w["lev_net"]- cot_weeks[i-1]["lev_net"]
    win = [x["lev_net"] for x in cot_weeks[max(0,i-51):i+1]]
    mn, mx = min(win), max(win)
    w["lev_pct"] = round((w["lev_net"]-mn)/(mx-mn)*100,1) if mx!=mn else 50

# ── CARGAR NQ DIARIO (15min → open/close diario) ─────────────────────
DOW_NAME = {0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes"}
by_date  = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            by_date[et.date()].append({
                "et":et, "o":float(r["Open"]), "h":float(r["High"]),
                "l":float(r["Low"]), "c":float(r["Close"])
            })
        except: pass

daily_summary = {}
for d, bs in by_date.items():
    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if not opens or not closes: continue
    hi = max(b["h"] for b in bs); lo = min(b["l"] for b in bs)
    daily_summary[d] = {
        "open":  opens[0]["o"],
        "close": closes[-1]["c"],
        "high":  hi, "low": lo,
        "pts":   round(closes[-1]["c"] - opens[0]["o"], 1),
        "bull":  closes[-1]["c"] > opens[0]["o"],
        "dow":   d.weekday()
    }

def get_trading_week(cot_date):
    """Semana de trading que sigue al COT (publicado viernes → lunes siguiente)"""
    pub_fri   = cot_date + timedelta(days=4)   # viernes publicación
    mon_next  = pub_fri  + timedelta(days=3)   # lunes siguiente
    days = []
    for i in range(7):
        d = mon_next + timedelta(days=i)
        if d.weekday() < 5:
            days.append(d)
        if len(days) == 5:
            break
    return days

# ── FILTRAR ÚLTIMO AÑO ────────────────────────────────────────────────
HOY    = date.today()
INICIO = date(HOY.year-1, HOY.month, HOY.day)
recent = [w for w in cot_weeks if w["date"] >= INICIO]

for w in recent:
    am_d  = w["am_delta"]
    lev_p = w["lev_pct"]
    if   am_d < -10000 and lev_p > 60: w["sig"]="BEAR 🔴🔴"; w["div"]="BEAR"
    elif am_d < -5000  and lev_p > 60: w["sig"]="BEAR 🔴";   w["div"]="BEAR"
    elif am_d > 10000  and lev_p < 40: w["sig"]="BULL 🟢🟢"; w["div"]="BULL"
    elif am_d > 5000   and lev_p < 40: w["sig"]="BULL 🟢";   w["div"]="BULL"
    else:                               w["sig"]="—";          w["div"]="NEUTRAL"
    w["trading_week"] = get_trading_week(w["date"])

# ── GENERAR HTML ──────────────────────────────────────────────────────
html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>COT + Días — NQ Whale Radar</title>
<style>
* { box-sizing:border-box; margin:0; padding:0; }
body { background:#0d0d1a; color:#e2e8f0; font-family:'Segoe UI',Arial,sans-serif;
       font-size:12.5px; padding:18px; }
h1  { color:#f59e0b; font-size:19px; text-align:center; margin-bottom:5px; }
.sub{ color:#64748b; font-size:11px; text-align:center; margin-bottom:18px; }

/* Explain box */
.explain { background:#131325; border:1px solid #2d2d4e; border-radius:8px;
            padding:14px 18px; margin-bottom:18px; max-width:980px;
            margin-left:auto; margin-right:auto; }
.explain h2 { color:#f59e0b; font-size:13px; margin-bottom:8px; }
.explain p  { color:#94a3b8; font-size:11.5px; line-height:1.75; margin-bottom:6px; }

/* Legend */
.legend { display:flex; gap:18px; justify-content:center; flex-wrap:wrap; margin-bottom:16px; }
.leg { display:flex; align-items:center; gap:7px; font-size:11px; color:#94a3b8; }
.lb  { width:16px; height:13px; border-radius:3px; }

/* Main table */
table { width:100%; border-collapse:collapse; }

/* COT WEEK header row */
tr.cot-neutral { background:#0f172a; }
tr.cot-bear    { background:#1a0505; border-left:5px solid #ef4444; }
tr.cot-bull    { background:#051a0a; border-left:5px solid #10b981; }

/* DAY rows -- indented inside divergence week */
tr.day-row     { background:#12121e; }
tr.day-row td  { padding:5px 8px 5px 30px; border-bottom:1px solid #1a1a2e; }
tr.day-row.day-bear-ok   { background:#0a1508; }
tr.day-row.day-bear-fail { background:#1a0808; }
tr.day-row.day-bull-ok   { background:#081a10; }
tr.day-row.day-bull-fail { background:#1a0a05; }

thead th { background:#1a1a30; color:#94a3b8; font-size:10.5px; font-weight:600;
            padding:7px 8px; text-align:center; border-bottom:2px solid #312e81;
            position:sticky; top:0; z-index:10; }
th.am  { background:#1a0f0f; color:#fca5a5; }
th.lev { background:#0a1f1a; color:#6ee7b7; }
th.div { background:#1a1a2e; color:#c4b5fd; }
th.nq  { background:#0d1f30; color:#60a5fa; }

td { padding:6px 8px; text-align:right; border-bottom:1px solid #1a1a2e; white-space:nowrap; }
td.left { text-align:left; }

.pos  { color:#10b981; }
.neg  { color:#ef4444; }
.neu  { color:#475569; }
.amb  { font-weight:700; }

/* Delta arrow */
.da-neg  { color:#ef4444; font-weight:700; }
.da-pos  { color:#10b981; font-weight:700; }
.da-zero { color:#475569; }

/* LEV % mini bar */
.bar-wrap { display:inline-flex; align-items:center; gap:5px; }
.bar      { height:10px; border-radius:2px; display:inline-block; }

/* Signal badge */
.sig-bear { background:#7f1d1d44; color:#fca5a5; border:1px solid #ef4444;
             padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; }
.sig-bull { background:#06402b44; color:#6ee7b7; border:1px solid #10b981;
             padding:2px 8px; border-radius:4px; font-weight:700; font-size:11px; }
.sig-none { color:#334155; }

/* Day name */
.dow-name { color:#94a3b8; font-size:11px; width:90px; display:inline-block; }
.dow-date { color:#475569; font-size:10px; }

/* NQ day result */
.nq-bull-ok   { color:#10b981; font-weight:700; }
.nq-bear-ok   { color:#ef4444; font-weight:700; }  /* bajó = short ganó */
.nq-fail      { color:#64748b; }
.ok-check     { color:#10b981; font-weight:700; font-size:14px; }
.ok-x         { color:#ef4444; font-weight:700; font-size:14px; }

/* Section divider for divergence week title */
tr.div-week-header td {
  background:#1e0a0a; color:#fca5a5; font-size:11px; font-weight:700;
  padding:3px 12px; border-top:2px solid #ef4444;
  letter-spacing:0.5px; text-align:left;
}
tr.div-week-header.bull-header td {
  background:#0a1e10; color:#6ee7b7; border-top-color:#10b981;
}

/* Expand button */
.toggle-btn { cursor:pointer; color:#60a5fa; font-size:10px; padding:1px 6px;
               border:1px solid #3b82f6; border-radius:3px; background:none; }
.toggle-btn:hover { background:#1e3a5f; }

/* No data */
.no-data { color:#334155; font-size:11px; }
</style>
</head>
<body>

<h1>📊 COT SEMANAL + DÍAS DE TRADING — NQ Whale Radar</h1>
<p class="sub">Último año · Datos CFTC reales · Semanas de divergencia expandidas Lun→Vie · NQ Futures</p>

<div class="explain">
  <h2>🧠 Cómo leer esta tabla</h2>
  <p><b>Filas COT (una por semana):</b> muestran el posicionamiento de AM (Asset Manager = BlackRock/fondos) y LEV (Hedge Funds).</p>
  <p><b>AM Delta 🔑:</b> cambio en el AM Net semanal. <span style="color:#ef4444;font-weight:700">▼ &lt;−5,000</span> = BlackRock reduciendo posición (señal bajista). <span style="color:#10b981;font-weight:700">▲ &gt;+5,000</span> = acumulando.</p>
  <p><b>LEV % (52 semanas):</b> percentil anual del posicionamiento de Hedge Funds. <span style="color:#10b981">Alto (&gt;60%) = hedge funds muy alcistas</span> = combustible para caída si dan vuelta.</p>
  <p><b>🔴 BEAR divergencia:</b> AM Delta &lt; −5k + LEV &gt; 60% → SHORT bias toda la semana. <b>¿Por qué funciona?</b> BlackRock sale sigilosamente mientras los hedge funds aún están comprados — cuando los HF vendan, el mercado cae.</p>
  <p><b>🟢 BULL divergencia:</b> AM Delta &gt; +5k + LEV &lt; 40% → LONG bias toda la semana. Los grandes acumulan mientras los HF están cortos — rebote cuando los HF cubran shorts.</p>
  <p><b>Filas Lun→Vie (solo en semanas de divergencia):</b> muestran qué hizo el NQ cada día y si el trade direction funcionó.</p>
</div>

<div class="legend">
  <div class="leg"><div class="lb" style="background:#7f1d1d;border:1px solid #ef4444"></div>BEAR STRONG (&lt;-10k)</div>
  <div class="leg"><div class="lb" style="background:#ef444430;border:1px solid #ef4444"></div>BEAR (&lt;-5k)</div>
  <div class="leg"><div class="lb" style="background:#10b98130;border:1px solid #10b981"></div>BULL (&gt;+5k)</div>
  <div class="leg"><div class="lb" style="background:#064e3b;border:1px solid #10b981"></div>BULL STRONG (&gt;+10k)</div>
  <div class="leg"><div class="lb" style="background:#1e293b;border:1px solid #475569"></div>NEUTRAL</div>
  <div class="leg" style="margin-left:20px">
    <span style="color:#10b981;font-weight:700">✓ día correcto</span> &nbsp;
    <span style="color:#ef4444;font-weight:700">✗ día incorrecto</span>
  </div>
</div>

<table>
<thead>
  <tr>
    <th rowspan="2" style="min-width:105px">Fecha COT</th>
    <th colspan="4" class="am">💼 ASSET MANAGER</th>
    <th colspan="5" class="lev">⚡ LEVERAGED MONEY</th>
    <th colspan="2" class="div">🔔 DIVERGENCIA</th>
    <th class="nq" rowspan="2">NQ<br>Semana</th>
    <th class="nq" rowspan="2">WR<br>Semana</th>
  </tr>
  <tr>
    <th class="am">Longs</th>
    <th class="am">Shorts</th>
    <th class="am">Net</th>
    <th class="am">Delta 🔑</th>
    <th class="lev">Longs</th>
    <th class="lev">Shorts</th>
    <th class="lev">Net</th>
    <th class="lev">Delta</th>
    <th class="lev">LEV % 52w</th>
    <th class="div">Señal</th>
    <th class="div">¿Qué hacer?</th>
  </tr>
</thead>
<tbody>
"""

def fc(v, threshold=0):
    """Format number with color"""
    if v is None: return '<span class="neu">—</span>'
    clr = "pos" if v > threshold else ("neg" if v < -threshold else "neu")
    sign = "+" if v > 0 else ""
    return f'<span class="{clr}">{sign}{int(v):,}</span>'

def fd(v, threshold=5000):
    """Format delta with arrow + bold if significant"""
    if v is None: return '<span class="neu">—</span>'
    if v < -threshold:
        return f'<span class="da-neg">▼ {int(v):,}</span>'
    elif v > threshold:
        return f'<span class="da-pos">▲ +{int(v):,}</span>'
    elif v < 0:
        return f'<span class="neg">{int(v):,}</span>'
    elif v > 0:
        return f'<span class="pos">+{int(v):,}</span>'
    else:
        return f'<span class="neu">0</span>'

div_weeks_total = [w for w in recent if w["div"]!="NEUTRAL"]
correct_weeks   = 0
total_weeks_nq  = 0

for w in reversed(recent):
    is_bear = w["div"]=="BEAR"
    is_bull = w["div"]=="BULL"
    is_div  = is_bear or is_bull

    row_cls = "cot-bear" if is_bear else ("cot-bull" if is_bull else "cot-neutral")

    # LEV % bar
    lp    = w["lev_pct"]
    lp_c  = "#10b981" if lp>60 else ("#ef4444" if lp<40 else "#f59e0b")
    lp_w  = int(lp * 0.55)
    lp_html = (f'<div class="bar-wrap">'
               f'<div class="bar" style="width:{lp_w}px;background:{lp_c};opacity:0.65"></div>'
               f'<span style="color:{lp_c};font-weight:700">{lp:.0f}%</span></div>')

    # Signal
    if is_bear:
        sig_html = f'<span class="sig-bear">{w["sig"]}</span>'
        action   = '<span style="color:#fca5a5">SHORT bias</span>'
    elif is_bull:
        sig_html = f'<span class="sig-bull">{w["sig"]}</span>'
        action   = '<span style="color:#6ee7b7">LONG bias</span>'
    else:
        sig_html = '<span class="sig-none">—</span>'
        action   = '<span class="neu">Sin señal</span>'

    # NQ week result
    tdays  = w["trading_week"]
    available = [daily_summary.get(d) for d in tdays if daily_summary.get(d)]
    if available:
        wk_open  = available[0]["open"]
        wk_close = available[-1]["close"]
        wk_pts   = round(wk_close - wk_open, 1)
        wk_bull  = wk_pts > 0
        nq_sign  = "+" if wk_pts > 0 else ""
        nq_clr   = "pos" if wk_pts>0 else "neg"
        nq_html  = f'<span class="{nq_clr}">{nq_sign}{wk_pts:,.0f}pt</span>'

        if is_div:
            total_weeks_nq += 1
            ok = (is_bear and wk_pts < -10) or (is_bull and wk_pts > 10)
            if ok: correct_weeks += 1
            wr_html = '<span class="ok-check">✓</span>' if ok else '<span class="ok-x">✗</span>'
        else:
            wr_html = '<span class="neu">—</span>'
    else:
        nq_html = '<span class="neu">—</span>'
        wr_html = '<span class="neu">—</span>'

    date_clr = "#fca5a5" if is_bear else ("#6ee7b7" if is_bull else "#64748b")
    bullet   = "🔴 " if is_bear else ("🟢 " if is_bull else "")

    html += f"""<tr class="{row_cls}">
  <td class="left" style="color:{date_clr};font-weight:{'700' if is_div else '400'}">
    {bullet}{w['date'].strftime('%d %b %Y')}
  </td>
  <td>{fc(w['am_l'])}</td>
  <td>{fc(-w['am_s'])}</td>
  <td>{fc(w['am_net'])}</td>
  <td>{fd(w['am_delta'])}</td>
  <td>{fc(w['lev_l'])}</td>
  <td>{fc(-w['lev_s'])}</td>
  <td>{fc(w['lev_net'])}</td>
  <td>{fd(w['lev_delta'], 3000)}</td>
  <td>{lp_html}</td>
  <td style="text-align:center">{sig_html}</td>
  <td style="text-align:center">{action}</td>
  <td style="text-align:center">{nq_html}</td>
  <td style="text-align:center">{wr_html}</td>
</tr>\n"""

    # ── EXPANDIR DÍAS si hay divergencia ─────────────────────────────
    if is_div:
        # Header de sección días
        hdr_cls = "bull-header" if is_bull else ""
        dir_txt = "SHORT" if is_bear else "LONG"
        dir_clr = "#fca5a5" if is_bear else "#6ee7b7"
        html += f"""<tr class="div-week-header {hdr_cls}">
  <td colspan="14" style="color:{dir_clr}">
    📅 Semana de trading: {tdays[0].strftime('%d %b')} → {tdays[-1].strftime('%d %b %Y')} &nbsp;|&nbsp;
    Sesgo: <b>{dir_txt}</b> &nbsp;|&nbsp;
    ¿Qué hizo el NQ cada día?
  </td>
</tr>\n"""

        days_correct = 0; days_total = 0
        for td in tdays:
            ds = daily_summary.get(td)
            dow = td.weekday()
            dow_n = DOW_NAME.get(dow,"—")

            if ds:
                days_total += 1
                pts   = ds["pts"]
                bull  = ds["bull"]
                sign  = "+" if pts>0 else ""
                ok    = (is_bear and not bull) or (is_bull and bull)
                if ok: days_correct += 1
                # Color de fila
                if is_bear:
                    row_day_cls = "day-row day-bear-ok" if ok else "day-row day-bear-fail"
                else:
                    row_day_cls = "day-row day-bull-ok" if ok else "day-row day-bull-fail"

                pts_clr = "nq-bull-ok" if (is_bull and bull and ok) else \
                          ("nq-bear-ok" if (is_bear and not bull and ok) else "nq-fail")
                ok_sym  = '<span class="ok-check">✓</span>' if ok else '<span class="ok-x">✗</span>'
                dir_nq  = "▲ BULL" if bull else "▼ BEAR"
                dir_c   = "#10b981" if bull else "#ef4444"
                rng     = round(ds["high"] - ds["low"], 1)

                html += f"""<tr class="{row_day_cls}">
  <td class="left" colspan="2">
    &nbsp;&nbsp;&nbsp;&nbsp;
    <span class="dow-name">{dow_n}</span>
    <span class="dow-date">{td.strftime('%d %b %Y')}</span>
  </td>
  <td colspan="2" style="text-align:left;color:#64748b;font-size:11px">
    Apertura: <b style="color:#e2e8f0">{ds['open']:,.0f}</b> &nbsp;
    Cierre: <b style="color:#e2e8f0">{ds['close']:,.0f}</b>
  </td>
  <td colspan="2" style="text-align:left;color:#64748b;font-size:11px">
    Rango: <b style="color:#e2e8f0">{rng:.0f}pts</b>
  </td>
  <td colspan="3" style="text-align:center">
    <span style="color:{dir_c};font-weight:700">{dir_nq}</span>
  </td>
  <td colspan="2" style="text-align:center">
    <span class="{pts_clr}">{sign}{pts:,.0f}pt</span>
  </td>
  <td colspan="2" style="text-align:center">{ok_sym} {"Señal correcta" if ok else "Contra señal"}</td>
  <td></td>
</tr>\n"""
            else:
                html += f"""<tr class="day-row">
  <td class="left" colspan="2">
    &nbsp;&nbsp;&nbsp;&nbsp;
    <span class="dow-name">{dow_n}</span>
    <span class="dow-date">{td.strftime('%d %b %Y')}</span>
  </td>
  <td colspan="12" class="no-data">Sin datos (mercado cerrado o datos no disponibles)</td>
</tr>\n"""

        # Resumen de la semana
        if days_total > 0:
            day_wr = days_correct/days_total*100
            wr_c   = "#10b981" if day_wr>=60 else ("#ef4444" if day_wr<50 else "#f59e0b")
            html += f"""<tr style="background:#0d0d1a;">
  <td colspan="14" style="text-align:right;padding:4px 16px;
      color:{wr_c};font-size:11px;font-weight:700;border-bottom:2px solid #2d2d4e;">
    📊 Resumen semana: {days_correct}/{days_total} días correctos →
    WR = {day_wr:.0f}%
    {"✓ SEMANA VÁLIDA" if day_wr>=60 else ("✗ Semana mixta" if day_wr<60 else "")}
  </td>
</tr>\n"""

html += f"""</tbody>
</table>

<div style="text-align:center;margin-top:16px;color:#475569;font-size:11px">
  Semanas con divergencia en período: {len(div_weeks_total)} &nbsp;|&nbsp;
  Correctas (NQ en dirección señal): {correct_weeks}/{total_weeks_nq}
  ({int(correct_weeks/total_weeks_nq*100) if total_weeks_nq else 0}%) &nbsp;|&nbsp;
  Fuente: CFTC COT Disaggregated + NQ Futures 15min
</div>
</body></html>"""

out = "tabla_cot_con_dias.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)

print(f"HTML generado: {out}")
print(f"Semanas divergencia: {len(div_weeks_total)} | OK: {correct_weeks}/{total_weeks_nq}")
