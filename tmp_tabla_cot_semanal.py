"""
tabla_cot_semanal.py
Genera tabla visual COT semana por semana (último año)
Muestra AM Delta, LEV%, Divergencia, resultado NQ
Para APRENDER a leer la divergencia en contexto
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ── CARGAR COT ────────────────────────────────────────────────────────
cot_weeks = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            al  = int(r.get("Asset_Mgr_Positions_Long_All",  0) or 0)
            as_ = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            ll  = int(r.get("Lev_Money_Positions_Long_All",  0) or 0)
            ls  = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
            cot_weeks.append({"date":d, "am_net":al-as_, "lev_net":ll-ls,
                               "am_delta":0, "lev_pct":50})
        except: pass
cot_weeks.sort(key=lambda x: x["date"])

for i, w in enumerate(cot_weeks):
    if i > 0:
        w["am_delta"] = w["am_net"] - cot_weeks[i-1]["am_net"]
    win = [x["lev_net"] for x in cot_weeks[max(0,i-51):i+1]]
    mn, mx = min(win), max(win)
    w["lev_pct"] = round((w["lev_net"]-mn)/(mx-mn)*100,1) if mx!=mn else 50

# ── NQ semanal (resultado de la semana) ───────────────────────────────
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            by_date[et.date()].append({
                "et":et, "o":float(r["Open"]), "c":float(r["Close"])
            })
        except: pass

# Calcular retorno NQ por semana ISO
nq_by_isoweek = {}
for d, bs in by_date.items():
    wk = d.isocalendar()[:2]  # (year, week)
    if wk not in nq_by_isoweek:
        nq_by_isoweek[wk] = {"opens": [], "closes": [], "dates": []}
    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if opens:  nq_by_isoweek[wk]["opens"].append((d, opens[0]["o"]))
    if closes: nq_by_isoweek[wk]["closes"].append((d, closes[-1]["c"]))
    nq_by_isoweek[wk]["dates"].append(d)

weekly_nq = {}
for wk, data in nq_by_isoweek.items():
    if data["opens"] and data["closes"]:
        mon_open  = sorted(data["opens"])[0][1]
        fri_close = sorted(data["closes"])[-1][1]
        weekly_nq[wk] = round(fri_close - mon_open, 1)

# ── FILTRAR: último año ───────────────────────────────────────────────
HOY   = date.today()
INICIO = date(HOY.year - 1, HOY.month, HOY.day)
recent = [w for w in cot_weeks if w["date"] >= INICIO]
print(f"Semanas a mostrar: {len(recent)}")

# ── CONSTRUIR FILAS ───────────────────────────────────────────────────
rows = []
for w in recent:
    am_d  = w["am_delta"]
    lev_p = w["lev_pct"]

    # Señal
    if   am_d < -10000 and lev_p > 60:  sig = "BEAR STRONG";  sig_c = "#7f1d1d"
    elif am_d < -5000  and lev_p > 60:  sig = "BEAR";         sig_c = "#ef4444"
    elif am_d > 10000  and lev_p < 40:  sig = "BULL STRONG";  sig_c = "#064e3b"
    elif am_d > 5000   and lev_p < 40:  sig = "BULL";         sig_c = "#10b981"
    else:                                sig = "NEUTRAL";      sig_c = "#334155"

    # NQ esa semana
    cot_pub = w["date"] + timedelta(days=4)   # publicado el viernes
    trading_wk = cot_pub.isocalendar()[:2]
    next_wk    = (cot_pub + timedelta(days=7)).isocalendar()[:2]
    nq_pts = weekly_nq.get(next_wk, None)
    if nq_pts is None: nq_pts = weekly_nq.get(trading_wk, None)

    rows.append({
        "date":   w["date"],
        "am_net": w["am_net"],
        "am_d":   am_d,
        "lev_net": w["lev_net"],
        "lev_p":  lev_p,
        "sig":    sig,
        "sig_c":  sig_c,
        "nq_pts": nq_pts,
    })

# ── GRÁFICA: tabla visual ─────────────────────────────────────────────
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLU='#818cf8'
BG='#0d0d1a'; PANEL='#131325'; BORDER='#2d2d4e'

n_rows = len(rows)
row_h  = 0.38
fig_h  = max(14, n_rows * row_h + 3.5)
fig    = plt.figure(figsize=(22, fig_h), facecolor=BG)
ax     = fig.add_axes([0.01, 0.01, 0.98, 0.96])
ax.set_facecolor(BG); ax.axis('off')

# Columnas
COL_X = [0.01, 0.09, 0.19, 0.305, 0.415, 0.515, 0.60, 0.73, 0.87]
HEADERS = ["Fecha COT", "AM Net", "AM Delta\n(señal semanal)", "LEV Net",
           "LEV %\n(52 semanas)", "SEÑAL\nDIVERGENCIA", "¿Qué sig?",
           "NQ esa\nsemana", "¿Funcionó?"]
HDR_CLR = '#94a3b8'

# Título
ax.text(0.5, 0.99, f'CUADRO COT SEMANAL — Último Año ({INICIO} → {HOY})',
        color=GOLD, fontsize=16, fontweight='bold', ha='center', va='top',
        transform=ax.transAxes)
ax.text(0.5, 0.965,
        'BEAR = AM Delta < -5k + LEV > 60%  |  BULL = AM Delta > +5k + LEV < 40%  |  '
        'Divergencia = BlackRock y Hedge Funds apuntan en direcciones OPUESTAS',
        color='#64748b', fontsize=9, ha='center', va='top', transform=ax.transAxes)

# Total height for data area
HEADER_Y = 0.935
DATA_TOP  = HEADER_Y - 0.03
cell_h    = (DATA_TOP - 0.01) / n_rows

# Headers
for x, h in zip(COL_X, HEADERS):
    ax.text(x + 0.005, HEADER_Y, h, color=HDR_CLR, fontsize=8.5,
            fontweight='bold', va='top', transform=ax.transAxes)

# Línea header
ax.axhline(DATA_TOP, color=BORDER, lw=0.8)

for i, r in enumerate(reversed(rows)):  # más reciente arriba
    y_top = DATA_TOP - i * cell_h
    y_mid = y_top - cell_h * 0.5
    y_bot = y_top - cell_h

    # Background row
    bg_clr = '#0f172a' if i % 2 == 0 else '#131325'
    ax.add_patch(patches.FancyBboxPatch(
        (0.005, y_bot + 0.002), 0.99, cell_h - 0.003,
        boxstyle='round,pad=0.001', facecolor=bg_clr,
        edgecolor=BORDER, linewidth=0.3, transform=ax.transAxes, zorder=1
    ))

    # Highlight si hay divergencia
    if r["sig"] != "NEUTRAL":
        ax.add_patch(patches.FancyBboxPatch(
            (0.005, y_bot + 0.002), 0.005, cell_h - 0.003,
            boxstyle='round,pad=0.001', facecolor=r["sig_c"],
            edgecolor='none', transform=ax.transAxes, zorder=2
        ))

    def txt(x, val, clr='#e2e8f0', fs=8.5, bold=False, align='left'):
        ax.text(x + 0.008, y_mid, str(val), color=clr,
                fontsize=fs, fontweight='bold' if bold else 'normal',
                va='center', ha=align, transform=ax.transAxes, zorder=3)

    # FECHA
    txt(COL_X[0], r["date"].strftime('%d %b %Y'), '#94a3b8', fs=8)

    # AM NET
    am_clr = RED if r["am_net"] < 0 else GRN
    txt(COL_X[1], f'{r["am_net"]:+,.0f}', am_clr, fs=8)

    # AM DELTA ← señal principal
    d_clr = RED if r["am_d"] < -5000 else (GRN if r["am_d"] > 5000 else '#64748b')
    d_bold = abs(r["am_d"]) > 5000
    arrow  = "▼" if r["am_d"] < -5000 else ("▲" if r["am_d"] > 5000 else "—")
    txt(COL_X[2], f'{arrow} {r["am_d"]:+,.0f}', d_clr, fs=8.5, bold=d_bold)

    # LEV NET
    l_clr = GRN if r["lev_net"] > 0 else RED
    txt(COL_X[3], f'{r["lev_net"]:+,.0f}', l_clr, fs=8)

    # LEV PCT
    lp    = r["lev_p"]
    lp_clr= GRN if lp > 60 else (RED if lp < 40 else '#64748b')
    bar_w = lp / 100 * 0.09
    ax.add_patch(patches.Rectangle(
        (COL_X[4] + 0.007, y_mid - 0.006), bar_w, 0.012,
        facecolor=lp_clr, alpha=0.4, transform=ax.transAxes, zorder=3))
    txt(COL_X[4] + 0.01, f'{lp:.0f}%', lp_clr, fs=8.5, bold=(lp>60 or lp<40))

    # SEÑAL
    if r["sig"] != "NEUTRAL":
        ax.add_patch(patches.FancyBboxPatch(
            (COL_X[5] + 0.005, y_mid - 0.009), 0.085, 0.018,
            boxstyle='round,pad=0.002', facecolor=r["sig_c"] + '44',
            edgecolor=r["sig_c"], linewidth=0.8,
            transform=ax.transAxes, zorder=3))
    sig_disp = r["sig"] if r["sig"] != "NEUTRAL" else "—"
    s_clr = r["sig_c"] if r["sig"] != "NEUTRAL" else '#475569'
    txt(COL_X[5] + 0.008, sig_disp, s_clr, fs=8, bold=(r["sig"]!="NEUTRAL"))

    # QUÉ SIGNIFICA
    if "BEAR" in r["sig"]:
        meaning = "SHORT bias"
        m_clr   = RED
    elif "BULL" in r["sig"]:
        meaning = "LONG bias"
        m_clr   = GRN
    else:
        meaning = "Sin edge"
        m_clr   = '#475569'
    txt(COL_X[6], meaning, m_clr, fs=8)

    # NQ pts esa semana
    if r["nq_pts"] is not None:
        nq_clr = GRN if r["nq_pts"] > 0 else RED
        txt(COL_X[7], f'{r["nq_pts"]:+,.0f}pt', nq_clr, fs=8.5,
            bold=abs(r["nq_pts"]) > 50)
    else:
        txt(COL_X[7], "—", '#475569', fs=8)

    # ¿FUNCIONÓ?
    if r["sig"] != "NEUTRAL" and r["nq_pts"] is not None:
        bear_ok  = "BEAR" in r["sig"] and r["nq_pts"] < -10
        bull_ok  = "BULL" in r["sig"] and r["nq_pts"] > 10
        if bear_ok or bull_ok:
            result = "✓ SI"
            r_clr  = GRN
        else:
            result = "✗ NO"
            r_clr  = RED
        txt(COL_X[8], result, r_clr, fs=9, bold=True)
    else:
        txt(COL_X[8], "—", '#475569', fs=8)

    # Línea separadora
    ax.axhline(y_bot + 0.001, color=BORDER, lw=0.3, xmin=0.005, xmax=0.995)

# Leyenda
legend_y = 0.005
legend_items = [
    ("BEAR STRONG: AM Delta < -10k + LEV > 60%", "#7f1d1d"),
    ("BEAR: AM Delta < -5k + LEV > 60%", "#ef4444"),
    ("BULL: AM Delta > +5k + LEV < 40%", "#10b981"),
    ("BULL STRONG: AM Delta > +10k + LEV < 40%", "#064e3b"),
    ("NEUTRAL: Sin divergencia", "#334155"),
]
lx = 0.01
for label, clr in legend_items:
    ax.add_patch(patches.Rectangle((lx, legend_y), 0.012, 0.012,
                 facecolor=clr, transform=ax.transAxes))
    ax.text(lx + 0.014, legend_y + 0.006, label, color='#94a3b8',
            fontsize=7.5, va='center', transform=ax.transAxes)
    lx += 0.19

out = 'tabla_cot_semanal.png'
plt.savefig(out, dpi=140, bbox_inches='tight', facecolor=BG)
print(f"Tabla guardada: {out}")
plt.close()

# ── PRINT RESUMEN ─────────────────────────────────────────────────────
print()
print(f"  SEMANAS CON DIVERGENCIA (últimos 12 meses)")
print(f"  {'='*75}")
print(f"  {'Fecha':12} {'AM Delta':>10} {'LEV%':>6} {'Señal':12} {'NQ semana':>10} {'OK?':>5}")
print(f"  {'-'*75}")
div_rows = [r for r in rows if r["sig"]!="NEUTRAL"]
for r in div_rows:
    nq_str = f'{r["nq_pts"]:+.0f}pt' if r["nq_pts"] else "—"
    if r["nq_pts"] is not None and r["sig"]!="NEUTRAL":
        ok = "✅" if (("BEAR" in r["sig"] and r["nq_pts"]<-10) or
                     ("BULL" in r["sig"] and r["nq_pts"]>10)) else "❌"
    else:
        ok = "—"
    print(f"  {str(r['date']):12} {r['am_d']:>+10,} {r['lev_p']:>5.0f}%  "
          f"{r['sig']:12} {nq_str:>10}  {ok}")

total_div = [r for r in div_rows if r["nq_pts"] is not None]
correct   = sum(1 for r in total_div if
               ("BEAR" in r["sig"] and r["nq_pts"]<-10) or
               ("BULL" in r["sig"] and r["nq_pts"]>10))
print(f"\n  TOTAL divergencias: {len(total_div)}  |  Correctas: {correct} ({correct/len(total_div)*100:.0f}%)")
