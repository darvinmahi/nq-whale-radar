"""
backtest_divergencia_6meses.py
COT Divergencia — Solo últimos 6 meses
Filtra sesiones desde 6 meses atrás hasta hoy
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ── FILTRO: últimos 6 meses ───────────────────────────────────────────
HOY = date.today()
INICIO = date(HOY.year - (1 if HOY.month <= 6 else 0),
              (HOY.month - 6) % 12 or 12, HOY.day)
print(f"Periodo: {INICIO} → {HOY}")

# ── CARGAR COT ────────────────────────────────────────────────────────
print("Cargando COT...")
cot_weeks = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            al  = int(r.get("Asset_Mgr_Positions_Long_All",  0) or 0)
            as_ = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            ll  = int(r.get("Lev_Money_Positions_Long_All",  0) or 0)
            ls  = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
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

# ── CARGAR NQ 15MIN (solo últimos 6 meses) ───────────────────────────
print("Cargando NQ 15min...")
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            if et.date() < INICIO: continue    # ← FILTRO 6 MESES
            by_date[et.date()].append({
                "et":et, "o":float(r["Open"]), "h":float(r["High"]),
                "l":float(r["Low"]),  "c":float(r["Close"])
            })
        except: pass

print(f"  {len(by_date)} días en periodo")

# ── PROCESAR ──────────────────────────────────────────────────────────
DOW = {0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes"}

all_records = []
for d in sorted(by_date.keys()):
    bs = by_date[d]
    if len(bs) < 8: continue
    cot = get_cot(d)
    if not cot: continue
    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if not opens or not closes: continue
    open_p  = opens[0]["o"]; close_p = closes[-1]["c"]
    pts     = round(close_p - open_p, 1)
    bull    = close_p > open_p
    am_d    = cot["am_delta"]; lev_p = cot["lev_pct"]

    if am_d < -5000 and lev_p > 60:
        div_type = "BEAR"; signal = "SHORT"
    elif am_d > 5000 and lev_p < 40:
        div_type = "BULL"; signal = "LONG"
    else:
        div_type = "NEUTRAL"; signal = "NONE"

    all_records.append({
        "date":d, "dow":d.weekday(), "pts":pts, "bull":bull,
        "am_d":am_d, "lev_p":lev_p, "div_type":div_type, "signal":signal,
        "correct": (signal=="SHORT" and not bull) or (signal=="LONG" and bull)
    })

# ── STATS ─────────────────────────────────────────────────────────────
print()
print(f"  {'='*80}")
print(f"  COT DIVERGENCIA — ÚLTIMOS 6 MESES ({INICIO} → {HOY})")
print(f"  {'='*80}")
print(f"  {'DÍA':12} | {'BEAR → SHORT':^28} | {'BULL → LONG':^28} | {'NEUTRAL':^10}")
print(f"  {'':12} | {'N':>3} {'WR%':>6} {'Avg NQ':>8} {'Total':>7} | {'N':>3} {'WR%':>6} {'Avg NQ':>8} {'Total':>7} | {'N':>4}")
print(f"  {'-'*90}")

day_stats = {}
for dw in range(5):
    bear_ses = [r for r in all_records if r["dow"]==dw and r["div_type"]=="BEAR"]
    bull_ses = [r for r in all_records if r["dow"]==dw and r["div_type"]=="BULL"]
    neut_ses = [r for r in all_records if r["dow"]==dw and r["div_type"]=="NEUTRAL"]
    day_stats[dw] = {"bear":bear_ses, "bull":bull_ses, "neut":neut_ses}

    def s(ses):
        if not ses: return 0,0,0,0
        n   = len(ses)
        cor = sum(1 for x in ses if x["correct"])
        avg = sum(x["pts"] for x in ses)/n
        tot = sum(x["pts"] for x in ses)
        return n, cor/n*100, avg, tot

    bn,bwr,bavg,btot = s(bear_ses)
    un,uwr,uavg,utot = s(bull_ses)
    nn = len(neut_ses)

    b_star = " ⭐" if bwr>=62 else ("  " if bwr>0 else "  ")
    u_star = " ⭐" if uwr>=62 else ("  " if uwr>0 else "  ")
    print(f"  {DOW[dw]:12} | {bn:>3} {bwr:>5.0f}%{b_star} {bavg:>+8.0f} {btot:>+7.0f} | "
          f"{un:>3} {uwr:>5.0f}%{u_star} {uavg:>+8.0f} {utot:>+7.0f} | {nn:>4}")

print(f"  {'-'*90}")
print(f"  ⭐ = WR ≥ 62%  |  Avg NQ = promedio puntos NQ de esa sesión")

# ── DETALLE SESIONES CON DIVERGENCIA ─────────────────────────────────
print()
print(f"  DETALLE DE TODAS LAS SESIONES CON DIVERGENCIA (6 meses)")
print()
div_sessions = [r for r in all_records if r["div_type"] != "NEUTRAL"]
div_sessions.sort(key=lambda x: x["date"])

print(f"  {'Fecha':12} {'Día':10} {'Tipo':6} {'AM Delta':>10} {'LEV%':>6} "
      f"{'Dir NQ':>8} {'Pts NQ':>8} {'OK?':>5} {'AM_cot':>8}")
print(f"  {'-'*85}")

for r in div_sessions:
    dir_nq = "BULL" if r["bull"] else "BEAR"
    ok     = "✅" if r["correct"] else "❌"
    sign   = "+" if r["pts"]>0 else ""
    tipo_clr = "BEAR" if r["div_type"]=="BEAR" else "BULL"
    print(f"  {str(r['date']):12} {DOW[r['dow']]:10} {tipo_clr:6} "
          f"{r['am_d']:>+10,} {r['lev_p']:>5.0f}%  "
          f"{dir_nq:>8}  {sign}{r['pts']:>6.1f}  {ok}")

total_div  = len(div_sessions)
correct_div= sum(1 for r in div_sessions if r["correct"])
print()
print(f"  TOTAL: {total_div} sesiones con divergencia | "
      f"Correctas: {correct_div} ({correct_div/total_div*100:.1f}%)")

# ── GRÁFICA ───────────────────────────────────────────────────────────
GRN='#10b981';RED='#ef4444';GOLD='#f59e0b';BLU='#818cf8';NTR='#475569'
DOWS_L=["Lun","Mar","Mie","Jue","Vie"]

fig = plt.figure(figsize=(20, 14), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(3, 5, figure=fig, hspace=0.6, wspace=0.42)

def sax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=8)
    for sp in ax.spines.values(): sp.set_color('#2d2d4e')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# Fila 0: título
ax0 = fig.add_subplot(gs[0, :])
ax0.axis('off')
bear_tot = sum(1 for r in div_sessions if r["div_type"]=="BEAR" and r["correct"])
bull_tot = sum(1 for r in div_sessions if r["div_type"]=="BULL" and r["correct"])
b_all    = [r for r in div_sessions if r["div_type"]=="BEAR"]
u_all    = [r for r in div_sessions if r["div_type"]=="BULL"]
bwr_all  = bear_tot/len(b_all)*100 if b_all else 0
uwr_all  = bull_tot/len(u_all)*100 if u_all else 0

ax0.text(0.5, 0.85,
    f'COT DIVERGENCIA — Ultimos 6 meses ({INICIO} → {HOY})',
    color='#f59e0b', fontsize=14, fontweight='bold', ha='center', va='top')
ax0.text(0.5, 0.45,
    f'BEAR (AM<-5k + LEV>60%): {len(b_all)} sesiones → WR={bwr_all:.0f}%   |   '
    f'BULL (AM>+5k + LEV<40%): {len(u_all)} sesiones → WR={uwr_all:.0f}%   |   '
    f'Total divergencia: {total_div} dias',
    color='#94a3b8', fontsize=10, ha='center', va='top')

# Fila 1: WR por día
for dw in range(5):
    ax = fig.add_subplot(gs[1, dw])
    sax(ax)
    ds = day_stats[dw]

    def wr_n(ses): 
        if not ses: return 0, 0
        return sum(1 for x in ses if x["correct"])/len(ses)*100, len(ses)

    bwr_d, bn_d = wr_n(ds["bear"])
    uwr_d, un_d = wr_n(ds["bull"])

    cats  = ["BEAR\nSHORT", "BULL\nLONG"]
    vals  = [bwr_d, uwr_d]
    ns_d  = [bn_d,  un_d]
    clrs  = [RED   if bwr_d >= 55 else NTR,
             GRN   if uwr_d >= 55 else NTR]

    bars = ax.bar(cats, vals, color=clrs, alpha=0.88, width=0.45, edgecolor='none')
    ax.axhline(50, color='#475569', lw=1, ls='--', alpha=0.5, label='50%')
    ax.axhline(62, color=GOLD, lw=1, ls=':', alpha=0.5, label='62%')

    for b, v, n in zip(bars, vals, ns_d):
        if n > 0:
            ax.text(b.get_x()+b.get_width()/2, b.get_height()+2,
                    f'{v:.0f}%\n({n}d)',
                    ha='center', va='bottom', color='#e2e8f0',
                    fontsize=9, fontweight='bold')
        else:
            ax.text(b.get_x()+b.get_width()/2, 5, 'Sin\ndatos',
                    ha='center', va='bottom', color='#475569', fontsize=8)

    ax.set_ylim(0, 110)
    title_clr = GOLD if max(bwr_d, uwr_d) >= 60 else '#e2e8f0'
    ax.set_title(DOWS_L[dw], color=title_clr, fontsize=13, fontweight='bold', pad=6)
    ax.set_ylabel('WR %' if dw==0 else '', color='#64748b', fontsize=8)
    if dw==0:
        ax.legend(fontsize=7, facecolor='#0d0d1a', labelcolor='#94a3b8',
                  framealpha=0.6, loc='upper right')

# Fila 2: Equity curves + puntos por sesión
for dw in range(5):
    ax = fig.add_subplot(gs[2, dw])
    sax(ax)
    ds = day_stats[dw]

    # Equity SHORT usando sesiones BEAR
    bear_sorted = sorted(ds["bear"], key=lambda x: x["date"])
    eq_b = [0]
    for s in bear_sorted:
        profit = -s["pts"] if not s["bull"] else s["pts"]
        eq_b.append(eq_b[-1] + profit)

    bull_sorted = sorted(ds["bull"], key=lambda x: x["date"])
    eq_u = [0]
    for s in bull_sorted:
        profit = s["pts"] if s["bull"] else -s["pts"]
        eq_u.append(eq_u[-1] + profit)

    if len(eq_b) > 1:
        final_b = eq_b[-1]
        ax.plot(eq_b, color=RED, lw=2, label=f'BEAR:{final_b:+.0f}pt', alpha=0.9)
        ax.fill_between(range(len(eq_b)), eq_b, 0, alpha=0.15, color=RED)
    if len(eq_u) > 1:
        final_u = eq_u[-1]
        ax.plot(range(len(eq_u)), eq_u, color=GRN, lw=2, label=f'BULL:{final_u:+.0f}pt', alpha=0.9)
        ax.fill_between(range(len(eq_u)), eq_u, 0, alpha=0.12, color=GRN)
    ax.axhline(0, color='#475569', lw=0.8, ls='--')

    ax.set_title(f'{DOWS_L[dw]} — Equity (señal)', color='#94a3b8', fontsize=9, fontweight='bold')
    ax.set_ylabel('Pts NQ' if dw==0 else '', color='#64748b', fontsize=8)
    if len(eq_b)>1 or len(eq_u)>1:
        ax.legend(fontsize=7.5, facecolor='#0d0d1a', labelcolor='#94a3b8',
                  framealpha=0.7, loc='upper left')

out = 'backtest_divergencia_6meses.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Grafica guardada: {out}")
plt.close()
