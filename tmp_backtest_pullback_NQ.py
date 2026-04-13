"""
backtest_pullback_50_NQ.py
Estrategia retroceso 50% usando NQ 15min REAL (nq_15m_intraday.csv)
Primera vela = 9:30-9:45 ET (15min)
Entrada cuando precio retrocede al 50% del cuerpo
SL: debajo del low (LONG) / encima del high (SHORT)
TP: 2R desde el midpoint
"""
import csv, math
from datetime import datetime, timedelta
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ── CARGAR NQ 15MIN ───────────────────────────────────────────────────
print("Cargando NQ 15min real...")
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            # Datetime viene en UTC, convertir a ET (-5h)
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=5)
            o  = float(r["Open"]);  h = float(r["High"])
            l  = float(r["Low"]);   c = float(r["Close"])
            if c > 0:
                bars.append({"et":et,"o":o,"h":h,"l":l,"c":c})
        except: pass

bars.sort(key=lambda x: x["et"])
by_date = defaultdict(list)
for b in bars:
    by_date[b["et"].date()].append(b)

print(f"  → {len(bars)} barras | {min(by_date)} → {max(by_date)}")

# ── PARÁMETROS ────────────────────────────────────────────────────────
TP_RATIO   = 2.0     # 1:2
SL_BUFFER  = 5.0     # 5 puntos NQ de buffer extra en el SL
PULL_BARs  = 8       # máx 8 barras x15min = 2h para esperar retroceso

# ── BACKTEST ──────────────────────────────────────────────────────────
trades    = []
no_trades = []

all_dates = sorted(by_date.keys())

for d in all_dates:
    if d.weekday() >= 5: continue
    bs = by_date[d]
    if len(bs) < 8: continue

    # Primera vela 9:30
    open_bar = [b for b in bs
                if b["et"].hour == 9 and b["et"].minute == 30]
    if not open_bar:
        continue

    ob = open_bar[0]
    O  = ob["o"]; C = ob["c"]; H = ob["h"]; L = ob["l"]
    body = abs(C - O)

    if body < 5:   # vela sin cuerpo relevante (<5pts NQ)
        no_trades.append({"date":str(d),"reason":"doji"})
        continue

    mid = (O + C) / 2

    if C > O:   # BULLISH → LONG
        direction = "LONG"
        sl_price  = L - SL_BUFFER
        risk      = mid - sl_price
        tp_price  = mid + risk * TP_RATIO
    else:        # BEARISH → SHORT
        direction = "SHORT"
        sl_price  = H + SL_BUFFER
        risk      = sl_price - mid
        tp_price  = mid - risk * TP_RATIO

    if risk <= 0:
        continue

    # Barras restantes (después de la primera vela)
    rest = [b for b in bs if b["et"] > ob["et"]
            and b["et"].hour < 16]

    if not rest:
        continue

    # ── Fase 1: esperar retroceso al midpoint ──────────────────────────
    entry_idx = None
    for i, bar in enumerate(rest[:PULL_BARs]):
        if direction == "LONG"  and bar["l"] <= mid:
            entry_idx = i; break
        if direction == "SHORT" and bar["h"] >= mid:
            entry_idx = i; break

    if entry_idx is None:
        no_trades.append({"date":str(d),"reason":"no_pull","dir":direction,"body":round(body,1)})
        continue

    # ── Fase 2: simular desde la barra de entrada ──────────────────────
    after = rest[entry_idx:]
    result = "TIMEOUT"; exit_price = None

    for bar in after:
        if direction == "LONG":
            if bar["l"] <= sl_price: result="SL";  exit_price=sl_price; break
            if bar["h"] >= tp_price: result="TP";  exit_price=tp_price; break
        else:
            if bar["h"] >= sl_price: result="SL";  exit_price=sl_price; break
            if bar["l"] <= tp_price: result="TP";  exit_price=tp_price; break

    if exit_price is None:
        exit_price = after[-1]["c"]

    pts = round((exit_price - mid) if direction=="LONG" else (mid - exit_price), 1)
    win = pts > 0

    trades.append({
        "date":      str(d),
        "dow":       d.weekday(),
        "direction": direction,
        "body":      round(body,1),
        "mid":       round(mid,1),
        "sl":        round(sl_price,1),
        "tp":        round(tp_price,1),
        "exit":      round(exit_price,1),
        "risk":      round(risk,1),
        "pts":       pts,
        "result":    result,
        "win":       win,
        "pull_bar":  entry_idx + 1,
    })

# ── STATS ─────────────────────────────────────────────────────────────
DOW_N = {0:"Lun",1:"Mar",2:"Mie",3:"Jue",4:"Vie"}
total = len(trades)
print(f"\n  Días totales: {len(all_dates)} | Trades: {total} | Sin trade: {len(no_trades)}")

if total == 0:
    print("Sin trades"); exit()

wins   = [t for t in trades if t["win"]]
losses = [t for t in trades if not t["win"]]
tp_h   = [t for t in trades if t["result"]=="TP"]
sl_h   = [t for t in trades if t["result"]=="SL"]
tout   = [t for t in trades if t["result"]=="TIMEOUT"]

wr    = len(wins)/total*100
tot_pts = sum(t["pts"] for t in trades)
avg_w = sum(t["pts"] for t in wins)/len(wins)   if wins   else 0
avg_l = sum(t["pts"] for t in losses)/len(losses) if losses else 0
exp   = wr/100*avg_w + (1-wr/100)*avg_l

print()
print("═"*65)
print(f"  RETROCESO 50% — NQ 15MIN REAL — {total} trades")
print("═"*65)
print(f"  Winrate:              {wr:.1f}%")
print(f"  Expectancy/trade:     {exp:+.1f} pts NQ")
print(f"  Total pts:            {tot_pts:+.0f} pts NQ")
print(f"  Avg WIN:              {avg_w:+.1f} pts  ({len(wins)} trades)")
print(f"  Avg LOSS:             {avg_l:+.1f} pts  ({len(losses)} trades)")
print(f"  TP: {len(tp_h)} ({len(tp_h)/total*100:.0f}%)  SL: {len(sl_h)} ({len(sl_h)/total*100:.0f}%)  Timeout: {len(tout)} ({len(tout)/total*100:.0f}%)")

def seg(sub, label):
    if not sub: return f"  {label}: 0 trades"
    w = sum(1 for t in sub if t["win"])
    wr_s = w/len(sub)*100
    avg  = sum(t["pts"] for t in sub)/len(sub)
    return f"  {label}: {len(sub)} trades  WR={wr_s:.0f}%  avg={avg:+.1f}pts"

print()
print("  Por dirección:")
print(seg([t for t in trades if t["direction"]=="LONG"],  "  LONG "))
print(seg([t for t in trades if t["direction"]=="SHORT"], "  SHORT"))
print()
print("  Por día de semana:")
for d in range(5):
    sub = [t for t in trades if t["dow"]==d]
    print(seg(sub, f"  {DOW_N[d]}  "))
print()
print("  Por tamaño de vela apertura (pts NQ):")
print(seg([t for t in trades if t["body"] >= 50],          "  Grande ≥50pts "))
print(seg([t for t in trades if 20 <= t["body"] < 50],     "  Media 20-50pts"))
print(seg([t for t in trades if t["body"] < 20],           "  Pequeña <20pts"))
print()
print("  Por velocidad retroceso:")
print(seg([t for t in trades if t["pull_bar"] <= 2],  "  Rápido ≤2bars"))
print(seg([t for t in trades if t["pull_bar"] >= 4],  "  Lento  ≥4bars"))

# Últimos 20 trades
print()
print(f"  {'Fecha':12} {'Día':4} {'Dir':6} {'Vela':6} {'   Pts':>8}  Res       Acum")
print("  "+"-"*65)
acum=0
for t in trades[-20:]:
    acum += t["pts"]
    ic = "✅" if t["win"] else "❌"
    print(f"  {t['date']:12} {DOW_N[t['dow']]:4} {t['direction']:6} "
          f"{t['body']:5.0f}pt  {t['pts']:>+7.1f}  {ic}{t['result']:7}  {acum:>+7.1f}")

# ── GRÁFICAS ──────────────────────────────────────────────────────────
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLU='#818cf8'; CYN='#06b6d4'

fig = plt.figure(figsize=(16,12), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.55, wspace=0.38)

def sax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=9)
    for sp in ax.spines.values(): sp.set_color('#2d2d4e')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 1. Equity curve
ax1 = fig.add_subplot(gs[0,:])
sax(ax1)
equity=[0]
for t in trades: equity.append(equity[-1]+t["pts"])
col_eq = GRN if equity[-1]>0 else RED
ax1.plot(equity, color=col_eq, lw=2.2)
ax1.fill_between(range(len(equity)), equity, 0, alpha=0.12, color=col_eq)
ax1.axhline(0, color='#475569', lw=0.8, ls='--')
ax1.set_title(
    f'Equity Curve NQ Real — {total} trades · {tot_pts:+,.0f}pts  (expectancy {exp:+.1f}pts/trade)',
    color='#e2e8f0', fontsize=12, fontweight='bold', pad=10)
ax1.set_ylabel('Puntos NQ', color='#64748b', fontsize=10)

# 2. Winrate pie
ax2 = fig.add_subplot(gs[1,2])
sax(ax2)
ax2.pie([len(wins), len(losses)],
        labels=[f'WIN\n{len(wins)}', f'LOSS\n{len(losses)}'],
        colors=[GRN, RED], autopct='%1.0f%%', startangle=90,
        textprops={'color':'#e2e8f0','fontsize':11,'fontweight':'bold'},
        wedgeprops={'edgecolor':'#131325','linewidth':2})
ax2.set_title(f'Winrate {wr:.1f}%', color='#e2e8f0', fontsize=12, fontweight='bold')

# 3. WR por día
ax3 = fig.add_subplot(gs[1,:2])
sax(ax3)
dow_labels = [DOW_N[d] for d in range(5)]
dow_wr     = []
dow_n      = []
for d in range(5):
    sub = [t for t in trades if t["dow"]==d]
    dow_n.append(len(sub))
    dow_wr.append(sum(1 for t in sub if t["win"])/len(sub)*100 if sub else 0)
colors3 = [GRN if w>=50 else RED for w in dow_wr]
bars3 = ax3.bar(dow_labels, dow_wr, color=colors3, alpha=0.85, width=0.5, edgecolor='none')
ax3.axhline(50, color='#475569', lw=1, ls='--', alpha=0.6)
for bar, w, n in zip(bars3, dow_wr, dow_n):
    ax3.text(bar.get_x()+bar.get_width()/2, bar.get_height()+1,
             f'{w:.0f}%\n({n}t)', ha='center', va='bottom',
             color='#e2e8f0', fontsize=9, fontweight='bold')
ax3.set_ylim(0,100)
ax3.set_title('Winrate por Día de Semana', color='#e2e8f0', fontsize=11, fontweight='bold')
ax3.set_ylabel('Win Rate %', color='#64748b', fontsize=9)

# 4. Scatter body vs pts
ax4 = fig.add_subplot(gs[2,:2])
sax(ax4)
ax4.scatter([t["body"] for t in trades],
            [t["pts"]  for t in trades],
            c=[GRN if t["win"] else RED for t in trades],
            s=50, alpha=0.7, edgecolor='none')
ax4.axhline(0, color='#475569', lw=0.8, ls='--')
ax4.set_xlabel('Tamaño vela apertura (pts NQ)', color='#64748b', fontsize=9)
ax4.set_ylabel('Resultado (pts NQ)', color='#64748b', fontsize=9)
ax4.set_title('Tamaño vela apertura vs Resultado', color='#e2e8f0', fontsize=11, fontweight='bold')

# 5. TP/SL/Timeout
ax5 = fig.add_subplot(gs[2,2])
sax(ax5)
cats=['TP','SL','Timeout']; vals=[len(tp_h),len(sl_h),len(tout)]
cols5=[GRN,RED,GOLD]
bars5=ax5.bar(cats,vals,color=cols5,alpha=0.85,width=0.5,edgecolor='none')
for b,v in zip(bars5,vals):
    ax5.text(b.get_x()+b.get_width()/2, b.get_height()+0.5, str(v),
             ha='center',va='bottom',color='#e2e8f0',fontsize=11,fontweight='bold')
ax5.set_title('Distribución Resultados', color='#e2e8f0', fontsize=11, fontweight='bold')
ax5.set_ylabel('N° trades', color='#64748b', fontsize=9)

fig.suptitle(
    f'Backtest: Retroceso 50% Vela Apertura 15min — NQ REAL · {min(by_date)} → {max(by_date)}',
    color='#e2e8f0', fontsize=14, fontweight='bold', y=1.01)

out = 'backtest_pullback_50_NQ_result.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Gráfica guardada: {out}")
plt.close()
