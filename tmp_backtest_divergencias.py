"""
backtest_setups_divergencias.py
Corre los 5 setups en TODOS los lunes de las semanas de divergencia COT
Cuenta Apex $50k | 3 MNQ | SL=25pts=$150 | TP1=50pts=$300 | TP2=67pts=$400
"""
import csv, math
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ── SEMANAS DE DIVERGENCIA ────────────────────────────────────────────
# (COT date, señal, lunes de trading real)
DIVERGENCIAS = [
    (date(2025,4,8),  "BEAR", date(2025,4,14)),   # BEAR STRONG -10k LEV 100%
    (date(2025,4,22), "BEAR", date(2025,4,28)),   # BEAR -6k LEV 82%
    (date(2025,5,20), "BULL", date(2025,5,27)),   # BULL +6k LEV 5% (mayo 26=memorial day)
    (date(2025,10,28),"BEAR", date(2025,11,3)),   # BEAR -5.5k LEV 100%
    (date(2025,11,10),"BEAR", date(2025,11,17)),  # BEAR -6k LEV 100%
    (date(2026,2,3),  "BEAR", date(2026,2,9)),    # BEAR -6.9k LEV 66%
]

# Offset UTC por fecha (EDT=UTC-4 Mar-Nov / EST=UTC-5 Nov-Mar)
def get_utc_offset(d):
    # DST 2025: inicia 9 Mar, termina 2 Nov
    # DST 2026: inicia 8 Mar
    dst_start_25 = date(2025,3,9); dst_end_25 = date(2025,11,2)
    dst_start_26 = date(2026,3,8)
    if dst_start_25 <= d < dst_end_25: return 4    # EDT
    if dst_start_26 <= d:              return 4    # EDT
    return 5                                        # EST

# ── PARÁMETROS ────────────────────────────────────────────────────────
CONTRACTS = 3; PT_VAL = 2; TICK_VAL = CONTRACTS * PT_VAL
RISK_USD  = 150; TP1_USD = 300; TP2_USD = 400
SL_PTS    = RISK_USD  / TICK_VAL   # 25 pts
TP1_PTS   = TP1_USD   / TICK_VAL   # 50 pts
TP2_PTS   = TP2_USD   / TICK_VAL   # 66.7 pts

print(f"3 MNQ | SL={SL_PTS:.0f}pts=${RISK_USD} | TP1={TP1_PTS:.0f}pts=${TP1_USD} | TP2={TP2_PTS:.0f}pts=${TP2_USD}")
print(f"RR: 1:{TP1_PTS/SL_PTS:.1f} → 1:{TP2_PTS/SL_PTS:.1f}\n")

# ── CARGAR DATOS ─────────────────────────────────────────────────────
all_bars = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            raw    = datetime.fromisoformat(dt_str)
            # Calcular offset según fecha
            raw_date = raw.date()
            offset   = get_utc_offset(raw_date)
            et       = raw - timedelta(hours=offset)
            d        = et.date()
            all_bars[d].append({
                "et":et, "o":float(r["Open"]), "h":float(r["High"]),
                "l":float(r["Low"]), "c":float(r["Close"]),
                "v":float(r.get("Volume",0) or 0)
            })
        except: pass

def get_ny_session(d):
    """Retorna barras NY 9:30-16:00 ET para una fecha"""
    bars = sorted(all_bars.get(d,[]), key=lambda x: x["et"])
    ny = [b for b in bars if
          (b["et"].hour==9 and b["et"].minute>=30) or
          (10<=b["et"].hour<16)]
    # VWAP
    cum_pv=0; cum_v=0
    for b in ny:
        mid=(b["h"]+b["l"]+b["c"])/3; v=b["v"] if b["v"]>0 else 1
        cum_pv+=mid*v; cum_v+=v
        b["vwap"]=round(cum_pv/cum_v,2)
    return ny

def get_premarket(d):
    bars = sorted(all_bars.get(d,[]), key=lambda x: x["et"])
    return [b for b in bars if
            (3<=b["et"].hour<9) or (b["et"].hour==9 and b["et"].minute<30)]

def check_outcome(ny, entry_idx, entry_price, direction):
    sl  = entry_price - SL_PTS  if direction=="LONG" else entry_price + SL_PTS
    tp1 = entry_price + TP1_PTS if direction=="LONG" else entry_price - TP1_PTS
    tp2 = entry_price + TP2_PTS if direction=="LONG" else entry_price - TP2_PTS
    for b in ny[entry_idx+1:]:
        if direction=="LONG":
            if b["l"]<=sl:  return "SL",  round(sl-entry_price,1), b["et"]
            if b["h"]>=tp2: return "TP2", round(tp2-entry_price,1), b["et"]
            if b["h"]>=tp1: return "TP1", round(tp1-entry_price,1), b["et"]
        else:
            if b["h"]>=sl:  return "SL",  round(sl-entry_price,1), b["et"]
            if b["l"]<=tp2: return "TP2", round(tp2-entry_price,1), b["et"]
            if b["l"]<=tp1: return "TP1", round(tp1-entry_price,1), b["et"]
    last = ny[-1]
    final_pts = round(last["c"]-entry_price,1) if direction=="LONG" else round(entry_price-last["c"],1)
    return "OPEN", final_pts, last["et"]

def find_setups(cot_date, signal, monday):
    """Encuentra setups en el lunes de la semana de divergencia"""
    direction = "LONG" if signal=="BULL" else "SHORT"
    ny = get_ny_session(monday)
    pm = get_premarket(monday)

    if not ny:
        # Prueba martes si lunes no hay datos (ej: festivo)
        tuesday = monday + timedelta(days=1)
        ny = get_ny_session(tuesday)
        pm = get_premarket(tuesday)
        if ny: monday = tuesday

    if not ny:
        return [], monday, direction

    setups = []
    ORB_H = ny[0]["h"]; ORB_L = ny[0]["l"]
    ORB_MID = (ORB_H+ORB_L)/2; ORB_RNG = ORB_H-ORB_L

    # ── SETUP 1: ORB Breakout/Breakdown ──────────────────────────────
    for i in range(1, min(6, len(ny))):
        b = ny[i]; prev = ny[i-1]
        if direction=="LONG" and prev["c"]>ORB_H and b["et"].hour<=10:
            entry = ORB_H + 0.25
            out, pts, exit_et = check_outcome(ny, i, entry, direction)
            pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
            ok  = out in ("TP1","TP2")
            setups.append({"num":1,"nombre":"ORB Breakout","entry_bar":b,
                "entry_price":entry,"direction":direction,"out":out,
                "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                "logica":f"ORB H={ORB_H:.0f} roto @ {b['et'].strftime('%H:%M')} | Rango ORB={ORB_RNG:.0f}pts"})
            break
        elif direction=="SHORT" and prev["c"]<ORB_L and b["et"].hour<=10:
            entry = ORB_L - 0.25
            out, pts, exit_et = check_outcome(ny, i, entry, direction)
            pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
            ok  = out in ("TP1","TP2")
            setups.append({"num":1,"nombre":"ORB Breakdown","entry_bar":b,
                "entry_price":entry,"direction":direction,"out":out,
                "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                "logica":f"ORB L={ORB_L:.0f} roto @ {b['et'].strftime('%H:%M')} | Rango ORB={ORB_RNG:.0f}pts"})
            break

    # ── SETUP 2: VWAP Reclaim/Rejection ──────────────────────────────
    for i in range(1, min(10, len(ny))):
        b = ny[i]; prev = ny[i-1]
        if direction=="LONG":
            if prev["c"]<prev["vwap"] and b["c"]>b["vwap"] and b["et"].hour<=11:
                entry = b["vwap"] + 0.5
                out, pts, exit_et = check_outcome(ny, i, entry, direction)
                # PnL: SHORT TP = precio cae = ganancia → flipped sign
                if direction=="SHORT":
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                else:
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                ok  = out in ("TP1","TP2")
                setups.append({"num":2,"nombre":"VWAP Reclaim","entry_bar":b,
                    "entry_price":round(entry,2),"direction":direction,"out":out,
                    "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                    "logica":f"Reclaim VWAP={b['vwap']:.0f} @ {b['et'].strftime('%H:%M')}"})
                break
        else:
            if prev["c"]>prev["vwap"] and b["c"]<b["vwap"] and b["et"].hour<=11:
                entry = b["vwap"] - 0.5
                out, pts, exit_et = check_outcome(ny, i, entry, direction)
                # PnL: SHORT TP = precio cae = ganancia → flipped sign
                if direction=="SHORT":
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                else:
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                ok  = out in ("TP1","TP2")
                setups.append({"num":2,"nombre":"VWAP Rejection","entry_bar":b,
                    "entry_price":round(entry,2),"direction":direction,"out":out,
                    "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                    "logica":f"Rechazo VWAP={b['vwap']:.0f} @ {b['et'].strftime('%H:%M')}"})
                break

    # ── SETUP 3: Pullback 50% ORB ────────────────────────────────────
    for i in range(1, min(12, len(ny))):
        b = ny[i]
        if direction=="LONG":
            if b["et"].hour>=10 and b["l"]<=ORB_MID+3 and b["c"]>ORB_MID:
                entry = round(ORB_MID+1, 2)
                out, pts, exit_et = check_outcome(ny, i, entry, direction)
                # PnL: SHORT TP = precio cae = ganancia → flipped sign
                if direction=="SHORT":
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                else:
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                ok  = out in ("TP1","TP2")
                setups.append({"num":3,"nombre":"Pullback 50% ORB","entry_bar":b,
                    "entry_price":entry,"direction":direction,"out":out,
                    "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                    "logica":f"Pullback al midpoint {ORB_MID:.0f} @ {b['et'].strftime('%H:%M')}"})
                break
        else:
            if b["et"].hour>=10 and b["h"]>=ORB_MID-3 and b["c"]<ORB_MID:
                entry = round(ORB_MID-1, 2)
                out, pts, exit_et = check_outcome(ny, i, entry, direction)
                # PnL: SHORT TP = precio cae = ganancia → flipped sign
                if direction=="SHORT":
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                else:
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                ok  = out in ("TP1","TP2")
                setups.append({"num":3,"nombre":"Rechazo 50% ORB","entry_bar":b,
                    "entry_price":entry,"direction":direction,"out":out,
                    "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                    "logica":f"Rechazo en midpoint {ORB_MID:.0f} @ {b['et'].strftime('%H:%M')}"})
                break

    # ── SETUP 4: London Level ────────────────────────────────────────
    if pm:
        LDN_H = max(b["h"] for b in pm); LDN_L = min(b["l"] for b in pm)
        for i in range(1, min(8, len(ny))):
            b = ny[i]
            if direction=="LONG" and b["l"]<=LDN_H+3 and b["c"]>LDN_H and b["et"].hour<=10:
                entry = round(LDN_H+0.5, 2)
                out, pts, exit_et = check_outcome(ny, i, entry, direction)
                # PnL: SHORT TP = precio cae = ganancia → flipped sign
                if direction=="SHORT":
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                else:
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                ok  = out in ("TP1","TP2")
                setups.append({"num":4,"nombre":"London High + NY","entry_bar":b,
                    "entry_price":entry,"direction":direction,"out":out,
                    "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                    "logica":f"London H={LDN_H:.0f} confirmado en NY @ {b['et'].strftime('%H:%M')}"})
                break
            elif direction=="SHORT" and b["h"]>=LDN_L-3 and b["c"]<LDN_L and b["et"].hour<=10:
                entry = round(LDN_L-0.5, 2)
                out, pts, exit_et = check_outcome(ny, i, entry, direction)
                # PnL: SHORT TP = precio cae = ganancia → flipped sign
                if direction=="SHORT":
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                else:
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                ok  = out in ("TP1","TP2")
                setups.append({"num":4,"nombre":"London Low + NY","entry_bar":b,
                    "entry_price":entry,"direction":direction,"out":out,
                    "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                    "logica":f"London L={LDN_L:.0f} break en NY @ {b['et'].strftime('%H:%M')}"})
                break

    # ── SETUP 5: FVG ────────────────────────────────────────────────
    all_pre = sorted(pm, key=lambda x: x["et"]) if pm else []
    already_s5 = False  # evitar setup duplicado
    for j in range(1, len(all_pre)-1):
        if already_s5: break
        b1,b2,b3 = all_pre[j-1],all_pre[j],all_pre[j+1]
        bull_fvg = b3["l"] > b1["h"]
        bear_fvg = b3["h"] < b1["l"]
        if direction=="LONG" and bull_fvg:
            fvg_mid = (b3["l"]+b1["h"])/2
            for i,b in enumerate(ny):
                if b["et"].hour<=10 and b["l"]<=fvg_mid+3 and b["c"]>fvg_mid:
                    entry = round(fvg_mid+0.25, 2)
                    out, pts, exit_et = check_outcome(ny, i, entry, direction)
                    pnl = round(pts*TICK_VAL) if out!="SL" else -RISK_USD
                    ok  = out in ("TP1","TP2")
                    setups.append({"num":5,"nombre":"FVG Bull Premarket","entry_bar":b,
                        "entry_price":entry,"direction":direction,"out":out,
                        "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                        "logica":f"FVG:{b1['h']:.0f}-{b3['l']:.0f} mid={fvg_mid:.0f} @ {b['et'].strftime('%H:%M')}"})
                    already_s5 = True
                    break
        elif direction=="SHORT" and bear_fvg:
            fvg_mid = (b1["l"]+b3["h"])/2
            for i,b in enumerate(ny):
                if b["et"].hour<=10 and b["h"]>=fvg_mid-3 and b["c"]<fvg_mid:
                    entry = round(fvg_mid-0.25, 2)
                    out, pts, exit_et = check_outcome(ny, i, entry, direction)
                    pnl = round(-pts*TICK_VAL) if out!="SL" else -RISK_USD
                    ok  = out in ("TP1","TP2")
                    setups.append({"num":5,"nombre":"FVG Bear Premarket","entry_bar":b,
                        "entry_price":entry,"direction":direction,"out":out,
                        "pts":pts,"pnl":pnl,"ok":ok,"exit_et":exit_et,
                        "logica":f"FVG:{b3['h']:.0f}-{b1['l']:.0f} mid={fvg_mid:.0f} @ {b['et'].strftime('%H:%M')}"})
                    already_s5 = True
                    break

    return setups, monday, direction

# ── RUN TODOS LOS LUNES ───────────────────────────────────────────────
BG='#0d0d1a'; PANEL='#131325'; GRN='#10b981'; RED='#ef4444'
GOLD='#f59e0b'; BLU='#60a5fa'; PRP='#a78bfa'
SETUP_COLORS = [BLU, PRP, '#f97316', '#06b6d4', '#ec4899']

all_results = []
print(f"{'='*78}")
print(f"  BACKTEST GLOBAL — 6 SEMANAS DIVERGENCIA COT — 3 MNQ")
print(f"{'='*78}")

fig, axes = plt.subplots(3, 2, figsize=(24, 22), facecolor=BG)
axes = axes.flatten()
fig.suptitle("BACKTEST 6 SEMANAS DIVERGENCIA COT | 3 MNQ | $50k Apex\nSL=25pts=$150 | TP1=50pts=$300 | TP2=67pts=$400",
             color=GOLD, fontsize=14, fontweight='bold', y=0.98)

total_setups = 0; total_wins = 0; total_pnl = 0
setup_stats = {1:[],2:[],3:[],4:[],5:[]}

for ax_idx, (cot_d, sig, monday) in enumerate(DIVERGENCIAS):
    setups, actual_monday, direction = find_setups(cot_d, sig, monday)
    ny = get_ny_session(actual_monday)

    week_pnl  = sum(s["pnl"] for s in setups)
    week_wins = sum(1 for s in setups if s["ok"])
    total_setups += len(setups)
    total_wins   += week_wins
    total_pnl    += week_pnl
    for s in setups:
        setup_stats[s["num"]].append(s["ok"])

    all_results.append({
        "cot":cot_d,"sig":sig,"monday":actual_monday,
        "direction":direction,"setups":setups,
        "week_pnl":week_pnl,"week_wins":week_wins
    })

    dir_arrow = "🟢 LONG" if direction=="LONG" else "🔴 SHORT"
    print(f"\n  COT {cot_d} [{sig}] → Lunes {actual_monday} | {dir_arrow}")
    print(f"  ORB rango: {(ny[0]['h']-ny[0]['l']):.0f}pts | Setups encontrados: {len(setups)}")
    for s in setups:
        sym = {"TP1":"✅","TP2":"✅✅","SL":"❌","OPEN":"⏳"}[s["out"]]
        pnl_s = f"+${s['pnl']}" if s["pnl"]>0 else f"-${abs(s['pnl'])}"
        print(f"    #{s['num']} {s['nombre']:<22} {s['direction']:<5} @ {s['entry_bar']['et'].strftime('%H:%M')} "
              f"→ {sym} {s['out']} {s['pts']:+.0f}pt {pnl_s}")
    print(f"  → Semana: {week_wins}/{len(setups)} ganadores | P&L: $+{week_pnl}" if week_pnl>=0
          else f"  → Semana: {week_wins}/{len(setups)} ganadores | P&L: ${week_pnl}")

    # ── GRÁFICA DE ESTA SEMANA ────────────────────────────────────────
    ax = axes[ax_idx]
    ax.set_facecolor(PANEL)

    if ny:
        xs = list(range(len(ny)))
        for i,b in enumerate(ny):
            clr = GRN if b["c"]>=b["o"] else RED
            body_lo = min(b["o"],b["c"]); body_hi = max(b["o"],b["c"])
            ax.add_patch(patches.Rectangle((i-0.3,body_lo),0.6,max(body_hi-body_lo,0.5),
                         facecolor=clr,alpha=0.8,zorder=3))
            ax.plot([i,i],[b["l"],b["h"]],color=clr,lw=0.7,zorder=2)
        ax.plot(xs,[b["vwap"] for b in ny],color=BLU,lw=1.3,ls='--',alpha=0.8,zorder=4)
        ORB_H = ny[0]["h"]; ORB_L = ny[0]["l"]
        ax.axhline(ORB_H,color=GOLD,lw=1,ls=':',alpha=0.6)
        ax.axhline(ORB_L,color=GOLD,lw=1,ls=':',alpha=0.6)

        for s in setups:
            et  = s["entry_bar"]["et"]
            idx = next((i for i,b in enumerate(ny) if b["et"]==et), None)
            if idx is None: continue
            clr = SETUP_COLORS[s["num"]-1]
            ok  = s["ok"]
            mrk = "^" if direction=="LONG" else "v"
            ep  = s["entry_price"]
            offset_arrow = 20 if direction=="LONG" else -20
            ax.scatter(idx, ep, marker=mrk, color=clr, s=100, zorder=6)
            ax.annotate(f'#{s["num"]} {s["out"]}',
                        xy=(idx, ep), xytext=(idx, ep+offset_arrow),
                        color=clr, fontsize=7.5, ha='center', fontweight='bold',
                        arrowprops=dict(arrowstyle='->', color=clr, lw=0.8))
            # TP1 line
            tp1 = ep+TP1_PTS if direction=="LONG" else ep-TP1_PTS
            sl  = ep-SL_PTS  if direction=="LONG" else ep+SL_PTS
            ax.hlines(tp1, idx, min(idx+5,len(ny)-1), colors=GRN, lw=0.7, ls='--', alpha=0.5)
            ax.hlines(sl,  idx, min(idx+5,len(ny)-1), colors=RED, lw=0.7, ls='--', alpha=0.5)

        tick_idx = [i for i,b in enumerate(ny) if b["et"].minute==0]
        ax.set_xticks(tick_idx)
        ax.set_xticklabels([ny[i]["et"].strftime('%H:%M') for i in tick_idx],
                            color='#64748b',fontsize=7)

    dir_clr = GRN if direction=="LONG" else RED
    sig_txt = f"{'🟢' if sig=='BULL' else '🔴'} {sig}"
    pnl_clr = GRN if week_pnl>=0 else RED
    ax.set_title(f"Lunes {actual_monday} | COT {cot_d} [{sig_txt}] → {direction}\n"
                 f"Setups: {len(setups)} | WR: {week_wins}/{len(setups)} | "
                 f"P&L: ${week_pnl:+}",
                 color=GOLD, fontsize=9, fontweight='bold', pad=5)
    ax.tick_params(colors='#64748b')
    for sp in ['top','right']: ax.spines[sp].set_visible(False)
    ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')

# Colorea el P&L en el título de cada subplot
for ax in axes[:len(DIVERGENCIAS)]:
    ax.title.set_color(GOLD)

plt.tight_layout(rect=[0,0,1,0.96])
out = "backtest_divergencias_6semanas.png"
plt.savefig(out, dpi=120, bbox_inches='tight', facecolor=BG)
plt.close()
print(f"\nGráfica: {out}")

# ── RESUMEN GLOBAL ────────────────────────────────────────────────────
print(f"\n{'='*78}")
print(f"  RESUMEN GLOBAL — 6 SEMANAS DE DIVERGENCIA COT")
print(f"{'='*78}")
global_wr = total_wins/total_setups*100 if total_setups else 0
print(f"  Setups encontrados: {total_setups}")
print(f"  Ganadores:          {total_wins} ({global_wr:.0f}%)")
print(f"  Perdedores:         {total_setups-total_wins}")
print(f"  P&L total:          ${total_pnl:+}")
print(f"  Riesgo total:       ${total_setups*RISK_USD}")
print(f"  RoR (retorno/riesgo): {total_pnl/(total_setups*RISK_USD)*100:.0f}%")
print()
print(f"  POR SETUP:")
for num in range(1,6):
    res = setup_stats[num]
    if not res: print(f"  #{num}: sin datos"); continue
    wr = sum(res)/len(res)*100
    print(f"  #{num}: {sum(res)}/{len(res)} OK = {wr:.0f}% WR")
print(f"\n  ✅ P&L esperado por semana de divergencia: ${total_pnl//len(DIVERGENCIAS):+}")
print(f"  Con SL=$150 x setup → máx pérdida semana si todos fallan: -$750")
print(f"  Con el WR observado el scenario esperado es +${total_pnl//len(DIVERGENCIAS)}/semana")
print(f"{'='*78}")
