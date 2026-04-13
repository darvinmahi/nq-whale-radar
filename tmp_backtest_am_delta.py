"""
backtest_am_delta.py
Backtest REGLA 1: AM Delta (Asset Manager Net semanal)
AM_delta = AM_net(N) - AM_net(N-1)
> +5,000  → ¿% sesiones NQ BULL esa semana?
-5k/+5k  → neutral
< -5,000  → ¿% sesiones NQ BEAR?
< -10,000 → ¿más bajista aún?
"""
import csv, math
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

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
            am_net  = al - as_
            lev_net = ll - ls
            cot_weeks.append({
                "date": d, "am_net": am_net, "lev_net": lev_net,
                "am_delta": 0, "lev_pct": 0
            })
        except: pass
cot_weeks.sort(key=lambda x: x["date"])

# Calcular AM Delta y LEV percentil 52 semanas
for i, w in enumerate(cot_weeks):
    if i > 0:
        w["am_delta"] = w["am_net"] - cot_weeks[i-1]["am_net"]
    # LEV percentil 52w
    win = [x["lev_net"] for x in cot_weeks[max(0,i-51):i+1]]
    mn, mx = min(win), max(win)
    w["lev_pct"] = round((w["lev_net"]-mn)/(mx-mn)*100, 1) if mx != mn else 50

print(f"  → {len(cot_weeks)} semanas COT | {cot_weeks[0]['date']} → {cot_weeks[-1]['date']}")

# ── CARGAR NQ 15MIN ───────────────────────────────────────────────────
print("Cargando NQ 15min sesiones NY...")
sessions = {}   # date → {bull, range_pts, open, close}
by_date  = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            by_date[et.date()].append({
                "et":et,
                "o":float(r["Open"]), "h":float(r["High"]),
                "l":float(r["Low"]),  "c":float(r["Close"])
            })
        except: pass

# Calcular dirección NY por día
for d, bs in by_date.items():
    if len(bs) < 8: continue
    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if not opens or not closes: continue
    open_p  = opens[0]["o"]
    close_p = closes[-1]["c"]
    rng_pts = max(b["h"] for b in bs) - min(b["l"] for b in bs)
    sessions[d] = {
        "bull":  close_p > open_p,
        "range": round(rng_pts, 1),
        "open":  open_p,
        "close": close_p,
        "pts":   round(close_p - open_p, 1)
    }

print(f"  → {len(sessions)} sesiones NY calculadas")

# ── ASIGNAR SEMANA COT A CADA SESIÓN ──────────────────────────────────
# COT se publica el martes de la semana siguiente
# La semana de reporte aplica a la siguiente semana de trading
# EJ: COT del martes 7-enero aplica a sesiones del 13-19 enero
def get_cot_for_session(ses_date):
    """Devuelve el COT vigente para una sesión (el que se publicó antes de esa fecha)."""
    applicable = [w for w in cot_weeks
                  if (w["date"] + timedelta(days=3)) <= ses_date]
    return applicable[-1] if applicable else None

# ── SEGMENTAR POR AM DELTA ────────────────────────────────────────────
buckets = {
    "BULL_STRONG":  {"label":"AM Delta > +5k\n🟢 BlackRock compra",  "min":5000,   "max":9e9},
    "NEUTRAL":      {"label":"AM Delta ±5k\n⚪ Neutral",            "min":-5000,  "max":5000},
    "BEAR":         {"label":"AM Delta < -5k\n🔴 Bajista",          "min":-10000, "max":-5000},
    "BEAR_STRONG":  {"label":"AM Delta < -10k\n⛔ Venta agresiva",   "min":-9e9,   "max":-10000},
}

results = {k: {"trades": [], "bull": 0, "bear": 0, "total_pts": 0, "ranges": []} for k in buckets}

for ses_date, ses in sorted(sessions.items()):
    cot = get_cot_for_session(ses_date)
    if not cot: continue
    delta = cot["am_delta"]

    for bkey, bval in buckets.items():
        if bval["min"] <= delta < bval["max"]:
            results[bkey]["trades"].append({
                "date": str(ses_date),
                "bull": ses["bull"],
                "pts":  ses["pts"],
                "range": ses["range"],
                "delta": delta,
            })
            if ses["bull"]:  results[bkey]["bull"] += 1
            else:            results[bkey]["bear"] += 1
            results[bkey]["total_pts"] += ses["pts"]
            results[bkey]["ranges"].append(ses["range"])
            break

# ── STATS ─────────────────────────────────────────────────────────────
print()
print("═"*70)
print("  BACKTEST AM DELTA — REGLA 1 COT")
print("═"*70)
print(f"  {'Bucket':30} {'N':>5} {'Bull%':>6} {'Avg pts':>9} {'Avg rng':>8}")
print("  "+"-"*65)

stats_table = []
for bkey in ["BULL_STRONG","NEUTRAL","BEAR","BEAR_STRONG"]:
    rd = results[bkey]
    n  = len(rd["trades"])
    if n == 0:
        print(f"  {bkey:30} {'0':>5}")
        stats_table.append((bkey, 0, 50, 0, 0))
        continue
    bull_pct = round(rd["bull"]/n*100,1)
    avg_pts  = round(rd["total_pts"]/n,1)
    avg_rng  = round(sum(rd["ranges"])/n,1)
    print(f"  {bkey:30} {n:>5} {bull_pct:>5.1f}%  {avg_pts:>+8.1f}  {avg_rng:>7.1f}")
    stats_table.append((bkey, n, bull_pct, avg_pts, avg_rng))

# Estadísticas extra
print()
for bkey in ["BULL_STRONG","NEUTRAL","BEAR","BEAR_STRONG"]:
    rd = results[bkey]
    if not rd["trades"]: continue
    n = len(rd["trades"])
    bull_pct = rd["bull"]/n*100
    avg_pts  = rd["total_pts"]/n

    # Distribución por año
    years = defaultdict(lambda: {"bull":0,"bear":0})
    for t in rd["trades"]:
        yr = t["date"][:4]
        if t["bull"]: years[yr]["bull"] += 1
        else:         years[yr]["bear"] += 1
    yr_str = "  ".join([f"{y}: {v['bull']/(v['bull']+v['bear'])*100:.0f}%B"
                        for y, v in sorted(years.items())])
    print(f"  {bkey}: WR={bull_pct:.0f}%  avg={avg_pts:+.1f}pts  [{yr_str}]")

# ── GRÁFICAS ──────────────────────────────────────────────────────────
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLU='#818cf8'; NTR='#94a3b8'

fig = plt.figure(figsize=(16, 12), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.55, wspace=0.35)

def sax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=9)
    for sp in ax.spines.values(): sp.set_color('#2d2d4e')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

labels_short = ["AM >+5k\n🟢BULL", "±5k\n⚪Neutral",
                 "<-5k\n🔴Bear", "<-10k\n⛔Strong"]
ns      = [s[1] for s in stats_table]
bpcts   = [s[2] for s in stats_table]
avgpts  = [s[3] for s in stats_table]
bar_cls = [GRN if b>=52 else (NTR if b>=48 else RED) for b in bpcts]

# 1. Win rate por bucket
ax1 = fig.add_subplot(gs[0,0])
sax(ax1)
bars1 = ax1.bar(labels_short, bpcts, color=bar_cls, alpha=0.85, width=0.5, edgecolor='none')
ax1.axhline(50, color='#475569', lw=1, ls='--', alpha=0.6)
for b, v, n in zip(bars1, bpcts, ns):
    ax1.text(b.get_x()+b.get_width()/2, b.get_height()+1,
             f'{v:.0f}%\n({n}d)', ha='center', va='bottom',
             color='#e2e8f0', fontsize=9, fontweight='bold')
ax1.set_ylim(0,100)
ax1.set_title('% Sesiones BULL por AM Delta', color='#e2e8f0', fontsize=11, fontweight='bold')
ax1.set_ylabel('% Sesiones BULL', color='#64748b', fontsize=9)

# 2. Avg pts por bucket
ax2 = fig.add_subplot(gs[0,1])
sax(ax2)
bar_cls2 = [GRN if v>0 else RED for v in avgpts]
bars2 = ax2.bar(labels_short, avgpts, color=bar_cls2, alpha=0.85, width=0.5, edgecolor='none')
ax2.axhline(0, color='#475569', lw=0.8, ls='--')
for b, v in zip(bars2, avgpts):
    ax2.text(b.get_x()+b.get_width()/2,
             v + (3 if v>=0 else -8),
             f'{v:+.0f}', ha='center', va='bottom',
             color='#e2e8f0', fontsize=10, fontweight='bold')
ax2.set_title('Avg Puntos NQ por Sesión (AM Delta)', color='#e2e8f0', fontsize=11, fontweight='bold')
ax2.set_ylabel('Avg pts NQ', color='#64748b', fontsize=9)

# 3. Equity curve BULL_STRONG vs BEAR_STRONG
ax3 = fig.add_subplot(gs[1,:])
sax(ax3)
for bkey, clr, lbl in [
    ("BULL_STRONG", GRN, "AM >+5k (BULL)"),
    ("BEAR_STRONG", RED, "AM <-10k (BEAR)"),
    ("NEUTRAL",     NTR, "NEUTRAL ±5k"),
]:
    trades_sorted = sorted(results[bkey]["trades"], key=lambda x: x["date"])
    eq = [0]
    for t in trades_sorted: eq.append(eq[-1]+t["pts"])
    ax3.plot(eq, color=clr, lw=2 if bkey!="NEUTRAL" else 1.2,
             label=f'{lbl} ({len(trades_sorted)}d · {eq[-1]:+.0f}pts)', alpha=0.9)

ax3.axhline(0, color='#475569', lw=0.8, ls='--')
ax3.set_title('Equity Curve acumulada NQ por Zona AM Delta',
              color='#e2e8f0', fontsize=11, fontweight='bold')
ax3.set_ylabel('Puntos NQ acumulados', color='#64748b', fontsize=9)
leg = ax3.legend(fontsize=9, facecolor='#1a1a2e', labelcolor='#94a3b8',
                 framealpha=0.8, edgecolor='#2d2d4e')

# 4. Distribución AM delta (histogram)
ax4 = fig.add_subplot(gs[2,0])
sax(ax4)
all_deltas = [w["am_delta"] for w in cot_weeks if w["am_delta"] != 0]
ax4.hist(all_deltas, bins=40, color=BLU, alpha=0.7, edgecolor='none')
ax4.axvline(5000,  color=GRN,  lw=2, ls='--', label='+5k threshold')
ax4.axvline(-5000, color=RED,  lw=2, ls='--', label='-5k threshold')
ax4.axvline(-10000,color=GOLD, lw=2, ls='--', label='-10k threshold')
ax4.set_title('Distribución histórica AM Delta', color='#e2e8f0', fontsize=11, fontweight='bold')
ax4.set_xlabel('AM Delta (contratos)', color='#64748b', fontsize=9)
ax4.set_ylabel('Frecuencia (semanas)', color='#64748b', fontsize=9)
ax4.legend(fontsize=8, facecolor='#1a1a2e', labelcolor='#94a3b8', framealpha=0.6)

# 5. AM Delta en el tiempo reciente
ax5 = fig.add_subplot(gs[2,1])
sax(ax5)
recent = cot_weeks[-52:]   # último año
x = range(len(recent))
bar_cs5 = [GRN if w["am_delta"]>5000 else (RED if w["am_delta"]<-5000 else NTR)
           for w in recent]
ax5.bar(x, [w["am_delta"] for w in recent], color=bar_cs5, alpha=0.8, edgecolor='none')
ax5.axhline(5000,   color=GRN,  lw=1.2, ls='--', alpha=0.6)
ax5.axhline(-5000,  color=RED,  lw=1.2, ls='--', alpha=0.6)
ax5.axhline(-10000, color=GOLD, lw=1.2, ls='--', alpha=0.6)
ax5.axhline(0, color='#475569', lw=0.6)
ax5.set_title('AM Delta — Último año', color='#e2e8f0', fontsize=11, fontweight='bold')
ax5.set_ylabel('AM Delta', color='#64748b', fontsize=9)
ax5.set_xticks([])

fig.suptitle('BACKTEST REGLA 1: AM Delta (Asset Manager) → Sesiones NQ Real',
             color='#e2e8f0', fontsize=14, fontweight='bold', y=1.01)

out = 'backtest_am_delta_result.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Gráfica guardada: {out}")
plt.close()
