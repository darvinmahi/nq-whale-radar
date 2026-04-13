"""
backtest_cot_divergencia_orb.py
Test 1: COT Divergencia (AM<-5k + LEV zona BULL >60%) → ¿62% BEAR?
Test 2: ORB 15min (breakout del rango 9:30-9:45) → ¿62% WR?
Datos: NQ 15min real CSV + COT histórico CSV
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
            d    = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
            al   = int(r.get("Asset_Mgr_Positions_Long_All", 0) or 0)
            as_  = int(r.get("Asset_Mgr_Positions_Short_All", 0) or 0)
            ll   = int(r.get("Lev_Money_Positions_Long_All", 0) or 0)
            ls   = int(r.get("Lev_Money_Positions_Short_All", 0) or 0)
            cot_weeks.append({"date": d, "am_net": al-as_, "lev_net": ll-ls,
                               "am_delta": 0, "lev_pct": 50})
        except: pass
cot_weeks.sort(key=lambda x: x["date"])

for i, w in enumerate(cot_weeks):
    if i > 0:
        w["am_delta"] = w["am_net"] - cot_weeks[i-1]["am_net"]
    win = [x["lev_net"] for x in cot_weeks[max(0, i-51):i+1]]
    mn, mx = min(win), max(win)
    w["lev_pct"] = round((w["lev_net"]-mn)/(mx-mn)*100, 1) if mx != mn else 50

print(f"  {len(cot_weeks)} semanas | {cot_weeks[0]['date']} → {cot_weeks[-1]['date']}")

def get_cot(ses_date):
    ap = [w for w in cot_weeks if (w["date"] + timedelta(days=3)) <= ses_date]
    return ap[-1] if ap else None

# ── CARGAR NQ 15MIN ───────────────────────────────────────────────────
print("Cargando NQ 15min...")
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00", "")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            if et.weekday() >= 5: continue
            by_date[et.date()].append({
                "et": et,
                "o": float(r["Open"]), "h": float(r["High"]),
                "l": float(r["Low"]),  "c": float(r["Close"])
            })
        except: pass

print(f"  {len(by_date)} días")

# ══════════════════════════════════════════════════════════════════════
# TEST 1: COT DIVERGENCIA (AM_delta < -5k AND LEV_pct > 60%)
# ══════════════════════════════════════════════════════════════════════
print("\n--- TEST 1: COT Divergencia ---")
div_trades = []   # AM bearish + LEV bullish → claim: 62% BEAR

for d in sorted(by_date.keys()):
    bs = by_date[d]
    if len(bs) < 8: continue
    cot = get_cot(d)
    if not cot: continue

    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if not opens or not closes: continue

    open_p  = opens[0]["o"]
    close_p = closes[-1]["c"]
    pts     = round(close_p - open_p, 1)
    bull    = close_p > open_p
    rng     = round(max(b["h"] for b in bs) - min(b["l"] for b in bs), 1)

    am_d    = cot["am_delta"]
    lev_p   = cot["lev_pct"]

    # DIVERGENCIA: AM vendiendo + LEV aún alcista
    if am_d < -5000 and lev_p > 60:
        div_trades.append({"date": str(d), "bull": bull, "pts": pts,
                           "rng": rng, "am_d": am_d, "lev_p": lev_p,
                           "dow": d.weekday()})

total_div = len(div_trades)
bull_div  = sum(1 for t in div_trades if t["bull"])
bear_div  = total_div - bull_div
bear_pct  = bear_div/total_div*100 if total_div else 0
avg_pts   = sum(t["pts"] for t in div_trades)/total_div if total_div else 0

print(f"  Sesiones con divergencia: {total_div}")
print(f"  BULL: {bull_div} ({bull_div/total_div*100:.1f}%) | BEAR: {bear_div} ({bear_pct:.1f}%)")
print(f"  Avg pts NQ: {avg_pts:+.1f}")
print(f"  Claim '62% BEAR': {'✅ CONFIRMADO' if bear_pct >= 58 else '❌ NO CONFIRMADO'}")

# También: divergencia inversa (AM >+5k AND LEV <40%) → BULL?
div_bull = []
for d in sorted(by_date.keys()):
    bs = by_date[d]
    if len(bs) < 8: continue
    cot = get_cot(d)
    if not cot: continue
    opens  = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    closes = [b for b in bs if b["et"].hour==15 and b["et"].minute<=59]
    if not opens or not closes: continue
    pts  = round(closes[-1]["c"] - opens[0]["o"], 1)
    bull = closes[-1]["c"] > opens[0]["o"]
    if cot["am_delta"] > 5000 and cot["lev_pct"] < 40:
        div_bull.append({"bull": bull, "pts": pts})

if div_bull:
    db_bull_pct = sum(1 for t in div_bull if t["bull"])/len(div_bull)*100
    print(f"\n  Divergencia BULL (AM>5k + LEV<40%): {len(div_bull)} sesiones → {db_bull_pct:.1f}% BULL")

# ══════════════════════════════════════════════════════════════════════
# TEST 2: ORB 15MIN (Opening Range Breakout 9:30-9:45)
# ══════════════════════════════════════════════════════════════════════
print("\n--- TEST 2: ORB 15min ---")
orb_trades = []
SL_BUFFER  = 5.0
TP_RATIO   = 2.0

for d in sorted(by_date.keys()):
    bs = by_date[d]
    if len(bs) < 8: continue

    # Rango 9:30-9:45 (primera vela 15min)
    orb = [b for b in bs if b["et"].hour==9 and b["et"].minute==30]
    if not orb: continue
    ob = orb[0]
    orb_high = ob["h"]; orb_low = ob["l"]; orb_mid = (orb_high+orb_low)/2

    if orb_high - orb_low < 15:   # rango mínimo 15pts NQ
        continue

    # Barras siguientes: esperar breakout
    rest = [b for b in bs if b["et"] > ob["et"] and b["et"].hour < 16]
    if not rest: continue

    result = None; direction = None; entry = None
    sl = None; tp = None

    for bar in rest[:12]:  # máx 3 horas para el breakout (12 x 15min)
        if bar["h"] > orb_high and direction is None:
            direction = "LONG"
            entry     = orb_high
            sl        = orb_low - SL_BUFFER
            risk      = entry - sl
            tp        = entry + risk * TP_RATIO
        elif bar["l"] < orb_low and direction is None:
            direction = "SHORT"
            entry     = orb_low
            sl        = orb_high + SL_BUFFER
            risk      = sl - entry
            tp        = entry - risk * TP_RATIO

        if direction and entry:
            if direction == "LONG":
                if bar["l"] <= sl:    result="SL";  break
                if bar["h"] >= tp:    result="TP";  break
            else:
                if bar["h"] >= sl:    result="SL";  break
                if bar["l"] <= tp:    result="TP";  break

    if not direction:
        continue   # no hubo breakout

    if not result:
        # timeout
        result = "TIMEOUT"
        last_c = rest[-1]["c"]
        pts = round((last_c - entry) if direction=="LONG" else (entry - last_c), 1)
    else:
        pts = round(risk*TP_RATIO if result=="TP" else -risk, 1)

    win  = pts > 0
    rng  = orb_high - orb_low
    orb_trades.append({
        "date": str(d), "direction": direction, "result": result,
        "pts": pts, "win": win, "rng": round(rng,1), "dow": d.weekday(),
        "entry": round(entry,1)
    })

total_orb = len(orb_trades)
wins_orb  = [t for t in orb_trades if t["win"]]
tp_orb    = [t for t in orb_trades if t["result"]=="TP"]
sl_orb    = [t for t in orb_trades if t["result"]=="SL"]
tout_orb  = [t for t in orb_trades if t["result"]=="TIMEOUT"]

wr_orb    = len(wins_orb)/total_orb*100 if total_orb else 0
tot_pts   = sum(t["pts"] for t in orb_trades)
exp_orb   = tot_pts/total_orb if total_orb else 0

DOW = {0:"Lun",1:"Mar",2:"Mie",3:"Jue",4:"Vie"}
print(f"  Total ORB trades: {total_orb}")
print(f"  Winrate: {wr_orb:.1f}%  (claim: 62-65%)")
print(f"  Total pts: {tot_pts:+,.0f}  Avg: {exp_orb:+.1f}pts/trade")
print(f"  TP: {len(tp_orb)} ({len(tp_orb)/total_orb*100:.0f}%)  SL: {len(sl_orb)} ({len(sl_orb)/total_orb*100:.0f}%)  Timeout: {len(tout_orb)} ({len(tout_orb)/total_orb*100:.0f}%)")
print()
print("  Por día:")
for dw in range(5):
    sub = [t for t in orb_trades if t["dow"]==dw]
    if sub:
        wr_s = sum(1 for t in sub if t["win"])/len(sub)*100
        avg_s = sum(t["pts"] for t in sub)/len(sub)
        print(f"    {DOW[dw]}: {len(sub)}t  WR={wr_s:.0f}%  avg={avg_s:+.0f}pts")
print()
print("  Por rango ORB:")
for rmin, rmax, label in [(0,20,"<20pts pequeño"), (20,50,"20-50pts medio"), (50,999,">50pts grande")]:
    sub = [t for t in orb_trades if rmin <= t["rng"] < rmax]
    if sub:
        wr_s = sum(1 for t in sub if t["win"])/len(sub)*100
        avg_s= sum(t["pts"] for t in sub)/len(sub)
        print(f"    {label}: {len(sub)}t  WR={wr_s:.0f}%  avg={avg_s:+.0f}pts")

# ── GRÁFICAS ──────────────────────────────────────────────────────────
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLU='#818cf8'; NTR='#94a3b8'

fig = plt.figure(figsize=(18, 13), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.55, wspace=0.38)

def sax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=9)
    for sp in ax.spines.values(): sp.set_color('#2d2d4e')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# --- TEST 1: COT Divergencia ---
# 1a. Pie BULL/BEAR en divergencia
ax1 = fig.add_subplot(gs[0, 0])
sax(ax1)
if total_div > 0:
    ax1.pie([bull_div, bear_div],
            labels=[f'BULL\n{bull_div}', f'BEAR\n{bear_div}'],
            colors=[GRN, RED], autopct='%1.0f%%', startangle=90,
            textprops={'color':'#e2e8f0','fontsize':11,'fontweight':'bold'},
            wedgeprops={'edgecolor':'#131325','linewidth':2})
ax1.set_title(f'COT Divergencia\nAM<-5k + LEV>60%\n{total_div} sesiones',
              color='#e2e8f0', fontsize=10, fontweight='bold')

# 1b. Equity curve divergencia
ax2 = fig.add_subplot(gs[0, 1:])
sax(ax2)
eq_div = [0]
for t in sorted(div_trades, key=lambda x: x["date"]):
    eq_div.append(eq_div[-1] + t["pts"])
clr_eq = GRN if eq_div[-1] > 0 else RED
ax2.plot(eq_div, color=clr_eq, lw=2.2)
ax2.fill_between(range(len(eq_div)), eq_div, 0, alpha=0.12, color=clr_eq)
ax2.axhline(0, color='#475569', lw=0.8, ls='--')
claim_right = bear_pct >= 58
claim_str = f"BEAR {bear_pct:.1f}% — {'CLAIM CONFIRMADO' if claim_right else 'CLAIM EXAGERADO'}"
ax2.set_title(f'Equity COT Divergencia (AM<-5k + LEV>60%) — {claim_str}',
              color=GRN if claim_right else GOLD, fontsize=11, fontweight='bold')
ax2.set_ylabel('Pts NQ acumulados', color='#64748b', fontsize=9)

# --- TEST 2: ORB ---
# 2a. ORB Winrate overview
ax3 = fig.add_subplot(gs[1, 0])
sax(ax3)
ax3.pie([len(wins_orb), total_orb-len(wins_orb)],
        labels=[f'WIN\n{len(wins_orb)}', f'LOSS\n{total_orb-len(wins_orb)}'],
        colors=[GRN, RED], autopct='%1.0f%%', startangle=90,
        textprops={'color':'#e2e8f0','fontsize':11,'fontweight':'bold'},
        wedgeprops={'edgecolor':'#131325','linewidth':2})
orb_claim = wr_orb >= 60
ax3.set_title(f'ORB 15min Breakout\nWR={wr_orb:.1f}%\n{"CLAIM OK (62-65%)" if orb_claim else f"WR real: {wr_orb:.0f}%"}',
              color=GRN if orb_claim else GOLD, fontsize=10, fontweight='bold')

# 2b. Equity ORB
ax4 = fig.add_subplot(gs[1, 1:])
sax(ax4)
eq_orb = [0]
for t in sorted(orb_trades, key=lambda x: x["date"]):
    eq_orb.append(eq_orb[-1] + t["pts"])
clr_orb = GRN if eq_orb[-1] > 0 else RED
ax4.plot(eq_orb, color=clr_orb, lw=2.2)
ax4.fill_between(range(len(eq_orb)), eq_orb, 0, alpha=0.12, color=clr_orb)
ax4.axhline(0, color='#475569', lw=0.8, ls='--')
ax4.set_title(f'Equity ORB 15min — {total_orb} trades · {tot_pts:+,.0f}pts · exp={exp_orb:+.1f}pts/trade',
              color='#e2e8f0', fontsize=11, fontweight='bold')
ax4.set_ylabel('Pts NQ acumulados', color='#64748b', fontsize=9)

# 2c. WR por día ORB
ax5 = fig.add_subplot(gs[2, 0])
sax(ax5)
dow_wr = [sum(1 for t in orb_trades if t["win"] and t["dow"]==d)/
          max(1,sum(1 for t in orb_trades if t["dow"]==d))*100 for d in range(5)]
dow_n  = [sum(1 for t in orb_trades if t["dow"]==d) for d in range(5)]
dow_cls= [GRN if w>=55 else RED for w in dow_wr]
bars5  = ax5.bar(["Lun","Mar","Mie","Jue","Vie"], dow_wr, color=dow_cls, alpha=0.85, width=0.5)
ax5.axhline(50, color='#475569', lw=1, ls='--', alpha=0.6)
ax5.axhline(62, color=GOLD, lw=1, ls='--', alpha=0.6, label='Claim 62%')
for b, w, n in zip(bars5, dow_wr, dow_n):
    ax5.text(b.get_x()+b.get_width()/2, b.get_height()+1,
             f'{w:.0f}%\n({n})', ha='center', va='bottom',
             color='#e2e8f0', fontsize=8.5, fontweight='bold')
ax5.set_ylim(0,100)
ax5.set_title('ORB — WR por día', color='#e2e8f0', fontsize=10, fontweight='bold')
ax5.set_ylabel('Win Rate %', color='#64748b', fontsize=9)
ax5.legend(fontsize=8, facecolor='#1a1a2e', labelcolor='#94a3b8')

# 2d. WR por tamaño rango ORB
ax6 = fig.add_subplot(gs[2, 1])
sax(ax6)
rng_bins = [("<20pts", 0, 20), ("20-50pts", 20, 50), (">50pts", 50, 9999)]
rb_labels = [r[0] for r in rng_bins]
rb_wr = []
rb_n  = []
for _, rmin, rmax in rng_bins:
    sub = [t for t in orb_trades if rmin<=t["rng"]<rmax]
    rb_n.append(len(sub))
    rb_wr.append(sum(1 for t in sub if t["win"])/len(sub)*100 if sub else 0)
rb_cls = [GRN if w>=55 else RED for w in rb_wr]
bars6 = ax6.bar(rb_labels, rb_wr, color=rb_cls, alpha=0.85, width=0.5)
ax6.axhline(50, color='#475569', lw=1, ls='--', alpha=0.6)
ax6.axhline(62, color=GOLD, lw=1, ls='--', alpha=0.5)
for b, w, n in zip(bars6, rb_wr, rb_n):
    ax6.text(b.get_x()+b.get_width()/2, b.get_height()+1,
             f'{w:.0f}%\n({n}t)', ha='center', va='bottom',
             color='#e2e8f0', fontsize=8.5, fontweight='bold')
ax6.set_ylim(0,100)
ax6.set_title('ORB — WR por tamaño rango', color='#e2e8f0', fontsize=10, fontweight='bold')

# 2e. Summary box
ax7 = fig.add_subplot(gs[2, 2])
ax7.set_facecolor('#131325'); ax7.axis('off')
ax7.set_xlim(0,1); ax7.set_ylim(0,1)
summary = [
    ("RESUMEN FINAL", "", '#f59e0b'),
    ("", "", ''),
    ("COT Divergencia", "", '#818cf8'),
    (f"  AM<-5k + LEV>60%", f"{total_div}d", '#e2e8f0'),
    (f"  BEAR%:", f"{bear_pct:.1f}%  {'OK' if claim_right else 'EXAG.'}", GRN if claim_right else GOLD),
    (f"  Avg pts:", f"{avg_pts:+.1f}/sesion", GRN if avg_pts>0 else RED),
    ("", "", ''),
    ("ORB 15min Breakout", "", '#818cf8'),
    (f"  Trades:", f"{total_orb}", '#e2e8f0'),
    (f"  Winrate:", f"{wr_orb:.1f}%  {'OK' if orb_claim else 'BAJO'}", GRN if orb_claim else GOLD),
    (f"  Expectancy:", f"{exp_orb:+.1f} pts/trade", GRN if exp_orb>0 else RED),
    (f"  Total:", f"{tot_pts:+,.0f} pts NQ", GRN if tot_pts>0 else RED),
]
y = 0.97
for lbl, val, clr in summary:
    if not lbl:
        y -= 0.03; continue
    if lbl.startswith("RESUMEN"):
        ax7.text(0.1, y, lbl, color=clr, fontsize=11, fontweight='bold', va='top')
    elif lbl.endswith(":") or lbl.startswith("  "):
        ax7.text(0.05, y, lbl, color='#64748b', fontsize=9, va='top')
        ax7.text(0.55, y, val, color=clr, fontsize=9, va='top', fontweight='bold')
    else:
        ax7.text(0.05, y, lbl, color=clr, fontsize=10, fontweight='bold', va='top')
    y -= 0.075

fig.suptitle('VALIDACION CON NQ REAL: COT Divergencia vs ORB 15min',
             color='#e2e8f0', fontsize=14, fontweight='bold', y=1.01)

out = 'backtest_cot_divergencia_orb.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Grafica guardada: {out}")
plt.close()
