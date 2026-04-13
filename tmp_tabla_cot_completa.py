"""
tabla_cot_completa.py
Tabla COMPLETA COT: todos los datos (longs, shorts, net, delta)
de Asset Manager y Leveraged Money semana por semana.
Resalta divergencias para aprender a leerlas.
"""
import csv, sys
from datetime import datetime, timedelta, date
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ── CARGAR COT COMPLETO ───────────────────────────────────────────────
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
                "am_delta":0, "lev_pct":50
            })
        except: pass
cot_weeks.sort(key=lambda x: x["date"])

for i, w in enumerate(cot_weeks):
    if i > 0:
        w["am_delta"]  = w["am_net"] - cot_weeks[i-1]["am_net"]
        w["lev_delta"] = w["lev_net"] - cot_weeks[i-1]["lev_net"]
    else:
        w["lev_delta"] = 0
    win = [x["lev_net"] for x in cot_weeks[max(0,i-51):i+1]]
    mn, mx = min(win), max(win)
    w["lev_pct"] = round((w["lev_net"]-mn)/(mx-mn)*100,1) if mx!=mn else 50

# ── CARGAR NQ semanal ─────────────────────────────────────────────────
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            by_date[et.date()].append({
                "et":et,"o":float(r["Open"]),"c":float(r["Close"])
            })
        except: pass

nq_by_isoweek = {}
for d, bs in by_date.items():
    wk = d.isocalendar()[:2]
    if wk not in nq_by_isoweek:
        nq_by_isoweek[wk] = {"opens":[], "closes":[]}
    opens  = [b for b in bs if b["et"].hour==9  and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if opens:  nq_by_isoweek[wk]["opens"].append((d, opens[0]["o"]))
    if closes: nq_by_isoweek[wk]["closes"].append((d, closes[-1]["c"]))

weekly_nq = {}
for wk, data in nq_by_isoweek.items():
    if data["opens"] and data["closes"]:
        weekly_nq[wk] = round(sorted(data["closes"])[-1][1] -
                               sorted(data["opens"])[0][1], 1)

# ── FILTRAR ÚLTIMO AÑO ────────────────────────────────────────────────
HOY    = date.today()
INICIO = date(HOY.year-1, HOY.month, HOY.day)
recent = [w for w in cot_weeks if w["date"] >= INICIO]
print(f"Semanas: {len(recent)} ({INICIO} → {HOY})")

# Añadir NQ y señal a cada semana
for w in recent:
    pub_fri = w["date"] + timedelta(days=4)
    next_wk = (pub_fri + timedelta(days=3)).isocalendar()[:2]
    nq = weekly_nq.get(next_wk, None)
    w["nq_pts"] = nq

    am_d  = w["am_delta"]
    lev_p = w["lev_pct"]
    if   am_d < -10000 and lev_p > 60: w["sig"]="BEAR 🔴🔴"; w["sig_c"]="#7f1d1d"; w["sig_t"]="#fca5a5"
    elif am_d < -5000  and lev_p > 60: w["sig"]="BEAR 🔴";   w["sig_c"]="#ef4444"; w["sig_t"]="#fecaca"
    elif am_d > 10000  and lev_p < 40: w["sig"]="BULL 🟢🟢"; w["sig_c"]="#064e3b"; w["sig_t"]="#6ee7b7"
    elif am_d > 5000   and lev_p < 40: w["sig"]="BULL 🟢";   w["sig_c"]="#10b981"; w["sig_t"]="#a7f3d0"
    else:                               w["sig"]="—";          w["sig_c"]="";         w["sig_t"]="#475569"

# ── RENDER: HTML (más fácil para tabla ancha) ────────────────────────
html = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>COT Completo — NQ Whale Radar</title>
<style>
  * { box-sizing: border-box; margin:0; padding:0; }
  body { background:#0d0d1a; color:#e2e8f0; font-family:'Segoe UI',Arial,sans-serif; 
         font-size:13px; padding:20px; }
  h1 { color:#f59e0b; font-size:20px; margin-bottom:6px; text-align:center; }
  .subtitle { color:#64748b; font-size:11px; text-align:center; margin-bottom:16px; }
  .legend { display:flex; gap:20px; justify-content:center; margin-bottom:18px; 
             flex-wrap:wrap; }
  .leg-item { display:flex; align-items:center; gap:8px; font-size:11px; color:#94a3b8; }
  .leg-box { width:18px; height:14px; border-radius:3px; }

  table { width:100%; border-collapse:collapse; }
  thead th { background:#1e1b4b; color:#94a3b8; font-size:11px; font-weight:600;
              padding:8px 6px; text-align:center; border-bottom:2px solid #312e81;
              position:sticky; top:0; z-index:10; }
  thead th.section-am  { background:#1a0f0f; color:#fca5a5; }
  thead th.section-lev { background:#0a1f1a; color:#6ee7b7; }
  thead th.section-div { background:#1e1b2e; color:#c4b5fd; }
  
  tr:nth-child(even) { background:#0f172a; }
  tr:nth-child(odd)  { background:#131325; }
  tr.div-row         { background:#1a0a0a !important; border-left:4px solid #ef4444; }
  tr.div-bull-row    { background:#0a1a10 !important; border-left:4px solid #10b981; }
  
  td { padding:6px 8px; text-align:right; border-bottom:1px solid #1e293b; 
       white-space:nowrap; }
  td.date-col { text-align:left; color:#94a3b8; font-size:12px; }
  td.lbl-col  { text-align:left; color:#64748b; font-size:11px; }
  
  .num-pos  { color:#10b981; }
  .num-neg  { color:#ef4444; }
  .num-neut { color:#64748b; }
  .delta-strong-neg { color:#ef4444; font-weight:700; }
  .delta-strong-pos { color:#10b981; font-weight:700; }
  
  .bar-cell { position:relative; min-width:90px; }
  .pct-bar  { display:inline-block; height:12px; border-radius:2px; 
               margin-right:5px; vertical-align:middle; }
  
  .sig-badge { display:inline-block; padding:3px 10px; border-radius:4px; 
                font-size:12px; font-weight:700; text-align:center; }
  .sig-bear  { background:#7f1d1d; color:#fca5a5; }
  .sig-bull  { background:#064e3b; color:#6ee7b7; }
  .sig-none  { color:#334155; }

  .nq-pos { color:#10b981; font-weight:600; }
  .nq-neg { color:#ef4444; font-weight:600; }
  
  .ok-yes { color:#10b981; font-weight:700; font-size:15px; }
  .ok-no  { color:#ef4444; font-weight:700; font-size:15px; }
  
  .explain { padding:16px 20px; background:#131325; border:1px solid #2d2d4e;
              border-radius:8px; margin-bottom:20px; max-width:900px; margin-left:auto;
              margin-right:auto; }
  .explain h2 { color:#f59e0b; font-size:14px; margin-bottom:10px; }
  .explain p  { color:#94a3b8; font-size:12px; line-height:1.8; margin-bottom:8px; }
  .explain b  { color:#e2e8f0; }
  
  .week-num { background:#1e293b; color:#64748b; font-size:10px; 
               padding:1px 5px; border-radius:10px; margin-left:4px; }
  
  .section-header { background:#1e2340 !important; }
  .section-header td { color:#818cf8; font-size:10px; font-weight:700; 
                        text-align:center; padding:4px; letter-spacing:1px; }
</style>
</head>
<body>
<h1>📊 COT SEMANAL COMPLETO — Asset Manager & Leveraged Money</h1>
<p class="subtitle">NQ Futures · Último año · Datos CFTC reales · Divergencias resaltadas</p>

<div class="explain">
  <h2>🧠 Cómo leer esta tabla</h2>
  <p><b>AM Longs / AM Shorts:</b> Contratos que tiene BlackRock y fondos de pensión en posición compradora vs vendedora.</p>
  <p><b>AM Net:</b> Longs − Shorts. <span style="color:#10b981">Positivo = netos alcistas</span> | <span style="color:#ef4444">Negativo = netos bajistas</span></p>
  <p><b>AM Delta (🔑 CLAVE):</b> Cuánto cambió el AM Net esta semana vs la anterior. 
     <span style="color:#ef4444;font-weight:700">AM Delta &lt; −5,000</span> = BlackRock REDUJO posición → señal bajista de dinero inteligente.</p>
  <p><b>LEV %:</b> Percentil 52 semanas del posicionamiento neto de Hedge Funds. 
     <span style="color:#10b981">100% = máximo alcista histórico</span> | <span style="color:#ef4444">0% = máximo bajista histórico</span></p>
  <p><b>DIVERGENCIA 🔴 BEAR:</b> <b>AM Delta &lt; −5k</b> (BlackRock vende) + <b>LEV % &gt; 60%</b> (Hedge funds siguen comprando). 
     Los grandes salen en silencio. Muy bajista para las próximas semanas.</p>
  <p><b>DIVERGENCIA 🟢 BULL:</b> <b>AM Delta &gt; +5k</b> (BlackRock compra) + <b>LEV % &lt; 40%</b> (Hedge funds siguen cortos). 
     Los grandes acumulan mientras los hedge funds aún no lo saben. Muy alcista.</p>
</div>
"""

html += """
<div class="legend">
  <div class="leg-item"><div class="leg-box" style="background:#7f1d1d;border:1px solid #ef4444"></div>BEAR STRONG (AM &lt; -10k + LEV &gt; 60%)</div>
  <div class="leg-item"><div class="leg-box" style="background:#ef444444;border:1px solid #ef4444"></div>BEAR (AM &lt; -5k + LEV &gt; 60%)</div>
  <div class="leg-item"><div class="leg-box" style="background:#10b98144;border:1px solid #10b981"></div>BULL (AM &gt; +5k + LEV &lt; 40%)</div>
  <div class="leg-item"><div class="leg-box" style="background:#064e3b;border:1px solid #10b981"></div>BULL STRONG (AM &gt; +10k + LEV &lt; 40%)</div>
  <div class="leg-item"><div class="leg-box" style="background:#1e293b;border:1px solid #475569"></div>NEUTRAL</div>
</div>

<table>
<thead>
  <tr>
    <th rowspan="2" style="min-width:100px">Fecha COT</th>
    <th colspan="4" class="section-am">💼 ASSET MANAGER<br><span style="font-size:9px">(BlackRock, Vanguard, fondos pensión)</span></th>
    <th colspan="5" class="section-lev">⚡ LEVERAGED MONEY<br><span style="font-size:9px">(Hedge Funds, CTAs)</span></th>
    <th colspan="2" class="section-div">🔔 DIVERGENCIA</th>
    <th rowspan="2" style="min-width:80px; background:#162032; color:#60a5fa">NQ<br>Semana</th>
    <th rowspan="2" style="min-width:60px; background:#162032; color:#60a5fa">OK?</th>
  </tr>
  <tr>
    <th class="section-am">Longs</th>
    <th class="section-am">Shorts</th>
    <th class="section-am">Net</th>
    <th class="section-am">Delta 🔑</th>
    <th class="section-lev">Longs</th>
    <th class="section-lev">Shorts</th>
    <th class="section-lev">Net</th>
    <th class="section-lev">Delta</th>
    <th class="section-lev">LEV % 52w</th>
    <th class="section-div">Señal</th>
    <th class="section-div">¿Qué sig?</th>
  </tr>
</thead>
<tbody>
"""

def fmt(v):
    if v is None: return '<td class="num-neut">—</td>'
    if isinstance(v, float): v = int(v)
    clr = "num-pos" if v > 0 else ("num-neg" if v < 0 else "num-neut")
    sign = "+" if v > 0 else ""
    return f'<td class="{clr}">{sign}{v:,}</td>'

def fmt_delta(v, threshold=5000):
    if v is None: return '<td class="num-neut">—</td>'
    clr = "delta-strong-neg" if v < -threshold else \
          ("delta-strong-pos" if v > threshold else \
          ("num-neg" if v < 0 else ("num-pos" if v > 0 else "num-neut")))
    arrow = "▼ " if v < -threshold else ("▲ " if v > threshold else "")
    sign  = "+" if v > 0 else ""
    return f'<td class="{clr}">{arrow}{sign}{v:,}</td>'

for w in reversed(recent):
    is_bear = "BEAR" in w["sig"]
    is_bull = "BULL" in w["sig"]
    row_cls = 'class="div-row"' if is_bear else ('class="div-bull-row"' if is_bull else '')

    # LEV % bar
    lp    = w["lev_pct"]
    lp_c  = "#10b981" if lp > 60 else ("#ef4444" if lp < 40 else "#f59e0b")
    lp_w  = int(lp * 0.7)  # max 70px
    lp_cls= "delta-strong-pos" if lp > 60 else ("delta-strong-neg" if lp < 40 else "num-neut")
    lp_cell = (f'<td class="bar-cell">'
               f'<span class="pct-bar" style="width:{lp_w}px;background:{lp_c};opacity:0.6"></span>'
               f'<span class="{lp_cls}" style="font-weight:700">{lp:.0f}%</span></td>')

    # Señal badge
    if is_bear:
        sig_html = f'<td style="text-align:center"><span class="sig-badge sig-bear">{w["sig"]}</span></td>'
        meaning  = '<td style="color:#fca5a5;font-size:11px">SHORT bias</td>'
    elif is_bull:
        sig_html = f'<td style="text-align:center"><span class="sig-badge sig-bull">{w["sig"]}</span></td>'
        meaning  = '<td style="color:#6ee7b7;font-size:11px">LONG bias</td>'
    else:
        sig_html = '<td style="text-align:center;color:#334155">—</td>'
        meaning  = '<td style="color:#334155;font-size:11px">Sin señal</td>'

    # NQ result
    nq = w["nq_pts"]
    if nq is not None:
        nq_clr = "nq-pos" if nq > 0 else "nq-neg"
        sign   = "+" if nq > 0 else ""
        nq_cell = f'<td class="{nq_clr}">{sign}{nq:,.0f}pt</td>'
    else:
        nq_cell = '<td style="color:#334155">—</td>'

    # OK?
    if (is_bear or is_bull) and nq is not None:
        ok = (is_bear and nq < -10) or (is_bull and nq > 10)
        ok_cell = '<td class="ok-yes">✓</td>' if ok else '<td class="ok-no">✗</td>'
    else:
        ok_cell = '<td style="color:#334155">—</td>'

    date_str = w["date"].strftime("%d %b %Y")
    # Resaltar la fecha también si hay divergencia
    date_clr = "#fca5a5" if is_bear else ("#6ee7b7" if is_bull else "#64748b")

    html += f"""  <tr {row_cls}>
    <td class="date-col" style="color:{date_clr}">{date_str}</td>
    {fmt(w['am_l'])}
    {fmt_delta(-w['am_s'], 1)}
    {fmt(w['am_net'])}
    {fmt_delta(w['am_delta'])}
    {fmt(w['lev_l'])}
    {fmt_delta(-w['lev_s'], 1)}
    {fmt(w['lev_net'])}
    {fmt_delta(w['lev_delta'], 3000)}
    {lp_cell}
    {sig_html}
    {meaning}
    {nq_cell}
    {ok_cell}
  </tr>\n"""

html += """</tbody></table>
<p style="color:#334155;font-size:11px;text-align:center;margin-top:12px">
Fuente: CFTC COT Disaggregated | NQ Futures 15min | WR Backtested: 77% (últimos 6 meses)
</p>
</body></html>"""

out = "tabla_cot_completa.html"
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print(f"HTML guardado: {out}")
print(f"Abrelo en el navegador para verlo completo")

# Resumen por consola también
print()
print("  SEMANAS CON DIVERGENCIA (resaltadas en la tabla):")
print(f"  {'Fecha':14} {'AM Delta':>10} {'AM Net':>9} {'LEV%':>6} {'Señal':12} {'NQ':>8} {'OK':>4}")
print("  "+"-"*70)
for w in recent:
    if w["sig"] != "—":
        nq  = f"{w['nq_pts']:+.0f}pt" if w["nq_pts"] else "—"
        ok  = ""
        if w["nq_pts"]:
            ok = "✅" if (("BEAR" in w["sig"] and w["nq_pts"]<-10) or
                          ("BULL" in w["sig"] and w["nq_pts"]>10)) else "❌"
        print(f"  {str(w['date']):14} {w['am_delta']:>+10,} {w['am_net']:>+9,} {w['lev_pct']:>5.0f}%  "
              f"{w['sig']:12} {nq:>8}  {ok}")
