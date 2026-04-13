"""
backtest_divergencia_por_dia.py
COT Divergencia (AM<-5k + LEV>60% = BEAR | AM>+5k + LEV<40% = BULL)
Desglosado por día de semana — tabla detallada + gráficas
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches

# ── CARGAR COT ────────────────────────────────────────────────────────
print("Cargando COT...")
cot_weeks = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d    = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            al   = int(r.get("Asset_Mgr_Positions_Long_All",  0) or 0)
            as_  = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            ll   = int(r.get("Lev_Money_Positions_Long_All",  0) or 0)
            ls   = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
            cot_weeks.append({"date":d, "am_net":al-as_,
                               "lev_net":ll-ls, "am_delta":0, "lev_pct":50})
        except: pass
cot_weeks.sort(key=lambda x: x["date"])

for i, w in enumerate(cot_weeks):
    if i > 0:
        w["am_delta"] = w["am_net"] - cot_weeks[i-1]["am_net"]
    win = [x["lev_net"] for x in cot_weeks[max(0,i-51):i+1]]
    mn, mx = min(win), max(win)
    w["lev_pct"] = round((w["lev_net"]-mn)/(mx-mn)*100,1) if mx!=mn else 50

def get_cot(ses_date):
    ap = [w for w in cot_weeks if (w["date"]+timedelta(days=3)) <= ses_date]
    return ap[-1] if ap else None

# ── CARGAR NQ 15MIN ───────────────────────────────────────────────────
print("Cargando NQ 15min...")
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            by_date[et.date()].append({
                "et":et, "o":float(r["Open"]), "h":float(r["High"]),
                "l":float(r["Low"]),  "c":float(r["Close"])
            })
        except: pass

# ── PROCESAR SESIONES ─────────────────────────────────────────────────
DOW = {0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes"}
DOW_SHORT = {0:"Lun",1:"Mar",2:"Mie",3:"Jue",4:"Vie"}

all_records = []

for d in sorted(by_date.keys()):
    bs = by_date[d]
    if len(bs) < 8: continue
    cot = get_cot(d)
    if not cot: continue

    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if not opens or not closes: continue

    open_p  = opens[0]["o"];  close_p = closes[-1]["c"]
    pts     = round(close_p - open_p, 1)
    bull    = close_p > open_p
    rng     = round(max(b["h"] for b in bs) - min(b["l"] for b in bs), 1)
    am_d    = cot["am_delta"]
    lev_p   = cot["lev_pct"]

    # Clasificar divergencia
    if am_d < -5000 and lev_p > 60:
        div_type = "BEAR"
        signal   = "SHORT"
    elif am_d > 5000 and lev_p < 40:
        div_type = "BULL"
        signal   = "LONG"
    else:
        div_type = "NEUTRAL"
        signal   = "NONE"

    all_records.append({
        "date":     d, "dow": d.weekday(), "pts": pts,
        "bull":     bull, "rng": rng,
        "am_d":     am_d, "lev_p": lev_p,
        "div_type": div_type, "signal": signal,
        # ¿La señal fue correcta?
        "correct":  (signal=="SHORT" and not bull) or (signal=="LONG" and bull)
    })

# ── STATS POR DÍA ─────────────────────────────────────────────────────
print()
print("═"*90)
print(f"  {'DÍA':10} | {'BEAR Div':^25} | {'BULL Div':^25} | {'Sin señal':^15}")
print(f"  {'':10} | {'N':>4} {'WR Bear':>8} {'avg':>8} | {'N':>4} {'WR Bull':>8} {'avg':>8} | {'N':>4} {'WR':>5}")
print("  "+"-"*90)

day_stats = {}

for dw in range(5):
    # BEAR divergence en este día
    bear_ses = [r for r in all_records if r["dow"]==dw and r["div_type"]=="BEAR"]
    # BULL divergence en este día
    bull_ses = [r for r in all_records if r["dow"]==dw and r["div_type"]=="BULL"]
    # Neutral
    neut_ses = [r for r in all_records if r["dow"]==dw and r["div_type"]=="NEUTRAL"]

    def stats(ses, correct_key="correct"):
        if not ses: return 0, 0, 0
        n   = len(ses)
        cor = sum(1 for s in ses if s["correct"])
        avg = sum(s["pts"] for s in ses)/n
        return n, cor/n*100, avg

    bn, bwr, bavg = stats(bear_ses)
    un, uwr, uavg = stats(bull_ses)
    nn, nwr, navg = stats(neut_ses)

    day_stats[dw] = {
        "bear": {"n":bn,"wr":bwr,"avg":bavg,"ses":bear_ses},
        "bull": {"n":un,"wr":uwr,"avg":uavg,"ses":bull_ses},
        "neut": {"n":nn,"wr":nwr,"avg":navg,"ses":neut_ses},
    }

    print(f"  {DOW[dw]:10} | {bn:>4} {bwr:>7.1f}% {bavg:>+8.1f} | "
          f"{un:>4} {uwr:>7.1f}% {uavg:>+8.1f} | {nn:>4} {nwr:>5.1f}%")

print()
# ── TABLA DETALLADA DE CADA SESIÓN CON DIVERGENCIA ────────────────────
print("  DETALLE SESIONES POR DÍA (CON DIVERGENCIA)")
print()

for dw in range(5):
    ds = day_stats[dw]
    print(f"  {'='*70}")
    print(f"  {DOW[dw].upper()}")
    print(f"  {'='*70}")

    for dtype, dname in [("bear","BEAR"), ("bull","BULL")]:
        ses_list = ds[dtype]["ses"]
        if not ses_list:
            print(f"    {dname}: Sin sesiones de divergencia")
            continue
        n   = ds[dtype]["n"]
        wr  = ds[dtype]["wr"]
        avg = ds[dtype]["avg"]
        print(f"\n    {dname} Divergencia ({n} sesiones | WR={wr:.0f}% | avg={avg:+.0f}pts)")
        print(f"    {'Fecha':12} {'AM Delta':>10} {'LEV%':>6} {'Dir NQ':>8} {'Pts':>8} {'OK?':>5}")
        print(f"    {'-'*60}")
        for s in sorted(ses_list, key=lambda x:x["date"]):
            dir_nq = "BULL" if s["bull"] else "BEAR"
            ok = "✅" if s["correct"] else "❌"
            sign = "+" if s["pts"]>0 else ""
            print(f"    {str(s['date']):12} {s['am_d']:>+10,} {s['lev_p']:>5.0f}%  "
                  f"{dir_nq:>8}  {sign}{s['pts']:>6.1f}  {ok}")
    print()

# ── GRÁFICAS ──────────────────────────────────────────────────────────
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLU='#818cf8'; NTR='#475569'
DOWS_L = ["Lun","Mar","Mie","Jue","Vie"]

fig = plt.figure(figsize=(20, 14), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(3, 5, figure=fig, hspace=0.6, wspace=0.4)

def sax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#2d2d4e')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# ── Fila 1: WR por día (BEAR) ──────────────────────────────────────────
ax_title1 = fig.add_subplot(gs[0, :])
ax_title1.axis('off')
ax_title1.text(0.5, 0.8, 'COT DIVERGENCIA — WR por Día de Semana',
               color='#f59e0b', fontsize=14, fontweight='bold', ha='center', va='top')
ax_title1.text(0.5, 0.2,
               'BEAR: AM Delta < -5,000 + LEV > 60%  |  BULL: AM Delta > +5,000 + LEV < 40%',
               color='#94a3b8', fontsize=10, ha='center', va='top')

# ── Fila 2: Mini charts por día (BEAR) ────────────────────────────────
for dw in range(5):
    ax = fig.add_subplot(gs[1, dw])
    sax(ax)
    ds = day_stats[dw]
    bn = ds["bear"]["n"]; bwr = ds["bear"]["wr"]; bavg = ds["bear"]["avg"]
    un = ds["bull"]["n"]; uwr = ds["bull"]["wr"]; uavg = ds["bull"]["avg"]

    cats = ["BEAR\nDiv", "BULL\nDiv", "Sin\nsenal"]
    wrs  = [bwr, uwr, ds["neut"]["wr"]]
    ns   = [bn, un, ds["neut"]["n"]]
    clrs = [RED if bwr>=55 else NTR,
            GRN if uwr>=55 else NTR,
            NTR]

    bars = ax.bar(cats, wrs, color=clrs, alpha=0.85, width=0.5, edgecolor='none')
    ax.axhline(50, color='#475569', lw=1, ls='--', alpha=0.6)
    for b, w, n in zip(bars, wrs, ns):
        if n > 0:
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+2,
                    f'{w:.0f}%\n({n}d)', ha='center', va='bottom',
                    color='#e2e8f0', fontsize=7.5, fontweight='bold')
    ax.set_ylim(0, 105)
    title_clr = GOLD if max(bwr, uwr) >= 60 else '#94a3b8'
    ax.set_title(f'{DOWS_L[dw]}', color=title_clr, fontsize=12, fontweight='bold', pad=6)
    ax.set_ylabel('WR %' if dw==0 else '', color='#64748b', fontsize=8)

# ── Fila 3: Equity per day (BEAR div) ─────────────────────────────────
for dw in range(5):
    ax = fig.add_subplot(gs[2, dw])
    sax(ax)
    ds = day_stats[dw]

    # Equity BEAR div
    bear_ses_sorted = sorted(ds["bear"]["ses"], key=lambda x:x["date"])
    eq_b = [0]
    for s in bear_ses_sorted:
        # si señal BEAR y NQ baja → ganamos (pts negativos = beneficio para short)
        profit = -s["pts"] if not s["bull"] else s["pts"]
        eq_b.append(eq_b[-1] + profit)

    bull_ses_sorted = sorted(ds["bull"]["ses"],  key=lambda x:x["date"])
    eq_u = [0]
    for s in bull_ses_sorted:
        profit = s["pts"] if s["bull"] else -s["pts"]
        eq_u.append(eq_u[-1] + profit)

    if len(eq_b) > 1:
        clr_b = GRN if eq_b[-1]>0 else RED
        ax.plot(eq_b, color=RED, lw=1.8, label=f'BEAR div ({eq_b[-1]:+.0f})', alpha=0.9)
        ax.fill_between(range(len(eq_b)), eq_b, 0, alpha=0.12, color=RED)
    if len(eq_u) > 1:
        ax.plot(range(len(eq_u)), eq_u, color=GRN, lw=1.8,
                label=f'BULL div ({eq_u[-1]:+.0f})', alpha=0.9)
        ax.fill_between(range(len(eq_u)), eq_u, 0, alpha=0.1, color=GRN)

    ax.axhline(0, color='#475569', lw=0.8, ls='--')
    ax.set_title(f'{DOWS_L[dw]} — Equity', color='#94a3b8', fontsize=9, fontweight='bold')
    ax.set_ylabel('Pts NQ' if dw==0 else '', color='#64748b', fontsize=8)
    if dw == 0:
        ax.legend(fontsize=6.5, facecolor='#0d0d1a', labelcolor='#94a3b8',
                  framealpha=0.7, loc='upper left')

fig.suptitle(f'BACKTEST COT DIVERGENCIA — Por Dia de Semana — NQ Real',
             color='#e2e8f0', fontsize=15, fontweight='bold', y=1.01)

out = 'backtest_divergencia_por_dia.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Grafica guardada: {out}")
plt.close()

# ── RESUMEN FINAL IMPRESO ──────────────────────────────────────────────
print()
print("  RESUMEN EJECUTIVO — COT DIVERGENCIA POR DIA")
print("  " + "="*65)
print(f"  {'Dia':10} {'BEAR➜SHORT':^20} {'BULL➜LONG':^20}")
print(f"  {'':10} {'N':>3} {'WR':>6} {'Avg':>7} | {'N':>3} {'WR':>6} {'Avg':>7}")
print("  "+"-"*65)
for dw in range(5):
    ds = day_stats[dw]
    b = ds["bear"]; u = ds["bull"]
    star_b = " ⭐" if b["wr"]>=62 else ""
    star_u = " ⭐" if u["wr"]>=62 else ""
    print(f"  {DOW[dw]:10} {b['n']:>3} {b['wr']:>5.0f}% {b['avg']:>+7.0f} |"
          f" {u['n']:>3} {u['wr']:>5.0f}% {u['avg']:>+7.0f}{star_u}")
print("  "+"-"*65)
print("  ⭐ = WR >= 62% (señal fuerte)")
