"""
setup_finder_lunes.py
Busca los 5 mejores entry setups en el lunes más reciente
Cuenta Apex $50k | Riesgo $150/trade | Target $300-400/trade
NQ: 1 punto = $20 → SL=8pts ($160) | TP1=15pts ($300) | TP2=20pts ($400)
COT actual: BULL divergencia (AM+7133, LEV 35%) → sesgo LONG
"""
import csv, math
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec
import numpy as np

TARGET_DATE = date(2026, 3, 23)   # último lunes con datos

# ── PARÁMETROS CUENTA ────────────────────────────────────────────────
# MNQ (Micro NQ): 1 punto = $2  |  NQ (E-mini): 1 punto = $20
ACCOUNT     = 50_000
CONTRACTS   = 3         # 3 MNQ base (opción escalar a 4)
PT_VAL      = 2         # $/punto por contrato MNQ
TICK_VAL    = CONTRACTS * PT_VAL   # $6/punto (3 MNQ) o $8/punto (4 MNQ)

RISK_USD    = 150       # máx riesgo por trade
TARGET1_USD = 300       # TP1
TARGET2_USD = 400       # TP2

SL_PTS  = round(RISK_USD    / TICK_VAL, 1)  # 25 pts con 3 MNQ
TP1_PTS = round(TARGET1_USD / TICK_VAL, 1)  # 50 pts
TP2_PTS = round(TARGET2_USD / TICK_VAL, 1)  # 67 pts

# Con 4 MNQ → SL=18.75, TP1=37.5, TP2=50
SL_4  = round(150  / (4*PT_VAL), 1)
TP1_4 = round(300  / (4*PT_VAL), 1)
TP2_4 = round(400  / (4*PT_VAL), 1)

print(f"Cuenta Apex: ${ACCOUNT:,}  |  Instrumento: MNQ (Micro NQ)")
print(f"  3 MNQ: ${TICK_VAL}/pt → SL={SL_PTS}pts | TP1={TP1_PTS}pts | TP2={TP2_PTS}pts")
print(f"  4 MNQ: ${4*PT_VAL}/pt → SL={SL_4}pts  | TP1={TP1_4}pts  | TP2={TP2_4}pts")
print(f"  RR (3 MNQ): 1:{TP1_PTS/SL_PTS:.1f} → 1:{TP2_PTS/SL_PTS:.1f}")
print(f"  RR (4 MNQ): 1:{TP1_4/SL_4:.1f} → 1:{TP2_4/SL_4:.1f}")
print(f"COT sesgo: BULL (AM+7133, LEV 35%) → LONG bias")
print()

# ── CARGAR DATOS 15MIN ───────────────────────────────────────────────
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_str = r["Datetime"].replace("+00:00","")
            et = datetime.fromisoformat(dt_str) - timedelta(hours=4)  # EDT (marzo=UTC-4)
            if et.date() != TARGET_DATE: continue
            bars.append({
                "et": et, "o": float(r["Open"]), "h": float(r["High"]),
                "l": float(r["Low"]),  "c": float(r["Close"]),
                "v": float(r.get("Volume", 0))
            })
        except: pass

bars.sort(key=lambda x: x["et"])
print(f"Barras disponibles para {TARGET_DATE}: {len(bars)}")
print(f"Horario: {bars[0]['et'].strftime('%H:%M')} → {bars[-1]['et'].strftime('%H:%M')} ET\n")

# ── SOLO NY SESSION (9:30 - 16:00) ──────────────────────────────────
ny = [b for b in bars if
      (b["et"].hour == 9  and b["et"].minute >= 30) or
      (b["et"].hour >= 10 and b["et"].hour  < 16)]

# ── CALCULAR VWAP ────────────────────────────────────────────────────
cum_pv = 0; cum_v = 0
for b in ny:
    mid = (b["h"] + b["l"] + b["c"]) / 3
    v   = b["v"] if b["v"] > 0 else 1
    cum_pv += mid * v; cum_v += v
    b["vwap"] = round(cum_pv / cum_v, 2)

# ── ORB (primer candle 9:30) ─────────────────────────────────────────
orb = ny[0]
ORB_HIGH = orb["h"]; ORB_LOW = orb["l"]
ORB_MID  = round((ORB_HIGH + ORB_LOW) / 2, 2)
ORB_RNG  = round(ORB_HIGH - ORB_LOW, 2)

# ── SESIÓN PREVIA (PM del viernes) para niveles ─────────────────────
pm_bars = [b for b in bars if b["et"].hour < 9 or
           (b["et"].hour == 9 and b["et"].minute < 30)]
PM_HIGH = max(b["h"] for b in pm_bars) if pm_bars else None
PM_LOW  = min(b["l"] for b in pm_bars) if pm_bars else None

print(f"ORB 9:30: High={ORB_HIGH:.2f} | Low={ORB_LOW:.2f} | Rango={ORB_RNG:.1f}pts")
print(f"VWAP apertura: {ny[0]['vwap']:.2f}")
print()

# ── IDENTIFICAR SETUPS ───────────────────────────────────────────────
setups = []

def check_outcome(entry_price, direction, sl_pts, tp1_pts, tp2_pts, entry_idx):
    """Simula outcome desde la barra de entrada hacia adelante"""
    sl  = entry_price - sl_pts  if direction=="LONG" else entry_price + sl_pts
    tp1 = entry_price + tp1_pts if direction=="LONG" else entry_price - tp1_pts
    tp2 = entry_price + tp2_pts if direction=="LONG" else entry_price - tp2_pts

    for b in ny[entry_idx+1:]:
        if direction == "LONG":
            if b["l"] <= sl:  return "SL", round(sl-entry_price, 1), b["et"]
            if b["h"] >= tp2: return "TP2",round(tp2-entry_price,1), b["et"]
            if b["h"] >= tp1: return "TP1",round(tp1-entry_price,1), b["et"]
        else:
            if b["h"] >= sl:  return "SL", round(sl-entry_price, 1), b["et"]
            if b["l"] <= tp2: return "TP2",round(tp2-entry_price,1), b["et"]
            if b["l"] <= tp1: return "TP1",round(tp1-entry_price,1), b["et"]
    return "OPEN", round(ny[-1]["c"]-entry_price if direction=="LONG" else entry_price-ny[-1]["c"], 1), ny[-1]["et"]

# SETUP 1: ORB Breakout (breakout del primer candle + COT BULL → solo LONG)
for i, b in enumerate(ny[1:], 1):
    if b["et"].hour == 10 and b["et"].minute == 0:  # segunda hora
        prev = ny[i-1]
        if prev["c"] > ORB_HIGH and prev["o"] < ORB_HIGH:  # breakout
            entry = ORB_HIGH + 0.25  # encima del ORB
            vwap_ok = prev["c"] > prev["vwap"]
            outcome, pts, exit_et = check_outcome(entry, "LONG", SL_PTS, TP1_PTS, TP2_PTS, i)
            pnl = round(pts * TICK_VAL, 0) if outcome != "SL" else -RISK_USD
            setups.append({
                "num":1, "nombre":"ORB Breakout + COT BULL",
                "tipo":"LONG (COT confirma)",
                "entry_bar":ny[i], "entry_price":entry,
                "direction":"LONG",
                "sl":round(entry-SL_PTS,2), "tp1":round(entry+TP1_PTS,2),
                "tp2":round(entry+TP2_PTS,2),
                "vwap_ok":vwap_ok, "outcome":outcome,
                "pts":pts, "pnl":pnl, "exit_et":exit_et,
                "logica": "ORB High roto → breakout válido. COT BULL = sesgo LONG semanal. VWAP abajo = acumulación.",
                "wr_historico":"39.8% puro → 54% con rango <20pts",
                "why": "Funciona en lunes con COT BULL y ORB pequeño (<25pts)"
            })
        break

# SETUP 2: VWAP Reclaim (precio cae bajo VWAP → regresa y lo reclama)
for i, b in enumerate(ny[2:], 2):
    prev = ny[i-1]
    prev2= ny[i-2]
    # Precio cayó bajo VWAP y ahora cierra encima
    if (prev["c"] < prev["vwap"] and
        b["c"] > b["vwap"] and
        b["et"].hour <= 11):
        entry = b["vwap"] + 0.5
        outcome, pts, exit_et = check_outcome(entry, "LONG", SL_PTS, TP1_PTS, TP2_PTS, i)
        pnl = round(pts * TICK_VAL, 0) if outcome != "SL" else -RISK_USD
        setups.append({
            "num":2, "nombre":"VWAP Reclaim",
            "tipo":"LONG (reclaim alcista)",
            "entry_bar":b, "entry_price":round(entry,2),
            "direction":"LONG",
            "sl":round(entry-SL_PTS,2), "tp1":round(entry+TP1_PTS,2),
            "tp2":round(entry+TP2_PTS,2),
            "vwap_ok":True, "outcome":outcome,
            "pts":pts, "pnl":pnl, "exit_et":exit_et,
            "logica": f"Precio bajo VWAP ({prev['vwap']:.0f}) en {prev['et'].strftime('%H:%M')}, reclaim en {b['et'].strftime('%H:%M')}. Confirmación alcista.",
            "wr_historico":"63% en días de tendencia clara",
            "why":"Mayor WR cuando COT BULL + premarket sin gaps extremos"
        })
        break

# SETUP 3: Pullback 50% ORB + VWAP Support
orb_50 = round(ORB_MID, 2)
for i, b in enumerate(ny[1:], 1):
    if b["et"].hour >= 10 and b["et"].hour <= 11:
        # Precio toca el 50% del ORB desde arriba
        if (ny[i-1]["c"] > orb_50 and
            b["l"] <= orb_50 + 2 and
            b["c"] > orb_50 and
            b["vwap"] <= b["h"]):
            entry = orb_50 + 1
            outcome, pts, exit_et = check_outcome(entry, "LONG", SL_PTS, TP1_PTS, TP2_PTS, i)
            pnl = round(pts * TICK_VAL, 0) if outcome != "SL" else -RISK_USD
            setups.append({
                "num":3, "nombre":"Pullback 50% ORB + Soporte",
                "tipo":"LONG (pullback buy)",
                "entry_bar":b, "entry_price":round(entry,2),
                "direction":"LONG",
                "sl":round(entry-SL_PTS,2), "tp1":round(entry+TP1_PTS,2),
                "tp2":round(entry+TP2_PTS,2),
                "vwap_ok":b["c"] > b["vwap"], "outcome":outcome,
                "pts":pts, "pnl":pnl, "exit_et":exit_et,
                "logica": f"Pullback al midpoint del ORB ({orb_50:.0f}). Zona de equilibrio. COT BULL confirma longs.",
                "wr_historico":"29.4% puro → mejora con COT y VA filter",
                "why":"Requiere COT BULL + precio debajo VA para ser setup válido"
            })
            break

# SETUP 4: London High/Low break confirmation en NY
premarket = [b for b in bars if
             (b["et"].hour >= 3 and b["et"].hour < 9) or
             (b["et"].hour == 9 and b["et"].minute < 30)]
if premarket:
    LDN_HIGH = max(b["h"] for b in premarket)
    LDN_LOW  = min(b["l"] for b in premarket)
    # Buscar test de London High en NY → rechazo → LONG
    for i, b in enumerate(ny[1:], 1):
        if b["et"].hour == 9 and b["et"].minute >= 45:
            # Precio toca o supera London High y cierra arriba
            if b["l"] <= LDN_HIGH + 3 and b["c"] > LDN_HIGH:
                entry = LDN_HIGH + 0.5
                outcome, pts, exit_et = check_outcome(entry, "LONG", SL_PTS, TP1_PTS, TP2_PTS, i)
                pnl = round(pts * TICK_VAL, 0) if outcome != "SL" else -RISK_USD
                setups.append({
                    "num":4, "nombre":"London High Breakout NY Confirm",
                    "tipo":"LONG (Killzone London→NY)",
                    "entry_bar":b, "entry_price":round(entry,2),
                    "direction":"LONG",
                    "sl":round(entry-SL_PTS,2), "tp1":round(entry+TP1_PTS,2),
                    "tp2":round(entry+TP2_PTS,2),
                    "vwap_ok":b["c"]>b["vwap"], "outcome":outcome,
                    "pts":pts, "pnl":pnl, "exit_et":exit_et,
                    "logica": f"London High={LDN_HIGH:.0f}. NY confirma break al inicio. COT BULL = momentum alcista.",
                    "wr_historico":"~65% con filtro de estructura COT",
                    "why":"Setup más robusto: NY confirm de London level + COT direction"
                })
                break

# SETUP 5: FVG (Fair Value Gap) detection en premarket → NYreclaim
# FVG: 3 velas donde gap entre vela1.high y vela3.low (bullish FVG)
fvg_zones = []
all_pre = sorted(premarket, key=lambda x: x["et"])
for i in range(1, len(all_pre)-1):
    b1, b2, b3 = all_pre[i-1], all_pre[i], all_pre[i+1]
    if b3["l"] > b1["h"]:  # bullish FVG
        fvg_zones.append({"top": b3["l"], "bot": b1["h"], "mid": (b3["l"]+b1["h"])/2, "type":"BULL"})
    if b3["h"] < b1["l"]:  # bearish FVG
        fvg_zones.append({"top": b1["l"], "bot": b3["h"], "mid": (b1["l"]+b3["h"])/2, "type":"BEAR"})

for fvg in fvg_zones:
    if fvg["type"] == "BULL":  # COT BULL → solo BULL FVG
        for i, b in enumerate(ny[1:], 1):
            if b["et"].hour >= 9 and b["et"].hour <= 10:
                # Price returns to FVG midpoint
                if b["l"] <= fvg["mid"] + 3 and b["c"] > fvg["mid"]:
                    entry = round(fvg["mid"] + 0.25, 2)
                    outcome, pts, exit_et = check_outcome(entry, "LONG", SL_PTS, TP1_PTS, TP2_PTS, i)
                    pnl = round(pts * TICK_VAL, 0) if outcome != "SL" else -RISK_USD
                    setups.append({
                        "num":5, "nombre":"FVG Premarket + COT BULL",
                        "tipo":"LONG (Fair Value Gap reclaim)",
                        "entry_bar":b, "entry_price":entry,
                        "direction":"LONG",
                        "sl":round(entry-SL_PTS,2), "tp1":round(entry+TP1_PTS,2),
                        "tp2":round(entry+TP2_PTS,2),
                        "vwap_ok":b["c"]>b["vwap"], "outcome":outcome,
                        "pts":pts, "pnl":pnl, "exit_et":exit_et,
                        "logica": f"FVG bullish premarket: {fvg['bot']:.0f}–{fvg['top']:.0f}. Precio regresa al midpoint en NY. COT BULL confirma.",
                        "wr_historico":"63-67% según backtests públicos con COT filter",
                        "why":"Precio busca equilibrio → FVG = imán de precio. COT eleva probabilidad."
                    })
                    break
        if len(setups) >= 5: break

# ── PRINT RESULTADOS ─────────────────────────────────────────────────
DIAS = {0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes"}
print(f"{'='*75}")
print(f"  ANÁLISIS LUNES {TARGET_DATE} — NY SESSION — APEX $50k")
print(f"  COT Sesgo: BULL  |  SL={SL_PTS}pts=${RISK_USD}  |  TP1={TP1_PTS}pts=${TARGET1_USD}  |  TP2={TP2_PTS}pts=${TARGET2_USD}")
print(f"{'='*75}")

total_pnl = 0
wins = 0
for s in setups:
    et  = s["entry_bar"]["et"]
    win_sym = {"TP1":"✅ TP1","TP2":"✅✅TP2","SL":"❌  SL ","OPEN":"⏳"}
    pnl_str = f"+${s['pnl']}" if s['pnl']>0 else f"-${abs(s['pnl'])}"
    total_pnl += s["pnl"]
    if s["outcome"] in ("TP1","TP2"): wins += 1

    print(f"\n  SETUP #{s['num']}: {s['nombre']}")
    print(f"  Tipo:    {s['tipo']}")
    print(f"  Entrada: {et.strftime('%H:%M ET')} @ {s['entry_price']:.2f}")
    print(f"  SL:      {s['sl']:.2f}  |  TP1: {s['tp1']:.2f}  |  TP2: {s['tp2']:.2f}")
    print(f"  VCAP:    VWAP {'✓ confirmado' if s['vwap_ok'] else '✗ no confirma'}")
    print(f"  Lógica:  {s['logica']}")
    print(f"  WR hist: {s['wr_historico']}")
    print(f"  Resultado: {win_sym[s['outcome']]} → {s['pts']:+.1f}pts  {pnl_str}")
    print(f"  Salida:  {s['exit_et'].strftime('%H:%M ET')}")

print(f"\n{'='*75}")
print(f"  RESUMEN: {wins}/{len(setups)} ganadores | P&L total: ${total_pnl:+.0f}")
print(f"  (sobre 5 trades con riesgo $150 cada uno = exposición $750)")
print(f"{'='*75}")

# ── GRÁFICA ─────────────────────────────────────────────────────────
BG='#0d0d1a'; PANEL='#131325'; GRN='#10b981'; RED='#ef4444'
GOLD='#f59e0b'; BLU='#60a5fa'; PRP='#a78bfa'

fig, axes = plt.subplots(2, 1, figsize=(20, 14), facecolor=BG,
                          gridspec_kw={'height_ratios':[3,1], 'hspace':0.08})
ax  = axes[0]; ax2 = axes[1]
for a in [ax, ax2]: a.set_facecolor(PANEL)

# --- VELAS NY ---
xs = list(range(len(ny)))
for i, b in enumerate(ny):
    clr  = GRN if b["c"] >= b["o"] else RED
    body_lo = min(b["o"], b["c"]); body_hi = max(b["o"], b["c"])
    ax.add_patch(patches.Rectangle((i-0.3, body_lo), 0.6, max(body_hi-body_lo, 0.5),
                                    facecolor=clr, alpha=0.85, zorder=3))
    ax.plot([i,i],[b["l"],b["h"]], color=clr, lw=0.8, zorder=2)

# VWAP
ax.plot(xs, [b["vwap"] for b in ny], color=BLU, lw=1.5,
        label=f'VWAP', zorder=4, ls='--', alpha=0.9)

# ORB
ax.axhline(ORB_HIGH, color=GOLD, lw=1.2, ls=':', alpha=0.7, xmin=0, xmax=1)
ax.axhline(ORB_LOW,  color=GOLD, lw=1.2, ls=':', alpha=0.7, xmin=0, xmax=1)
ax.fill_between(xs, ORB_LOW, ORB_HIGH, alpha=0.06, color=GOLD)
ax.text(len(ny)-1, ORB_HIGH+1, f'ORB H {ORB_HIGH:.0f}', color=GOLD, fontsize=8, ha='right')
ax.text(len(ny)-1, ORB_LOW-3,  f'ORB L {ORB_LOW:.0f}',  color=GOLD, fontsize=8, ha='right')

# Setups
colors_setup = [BLU, PRP, '#f97316', '#06b6d4', '#ec4899']
for s in setups:
    et  = s["entry_bar"]["et"]
    idx = next((i for i,b in enumerate(ny) if b["et"]==et), None)
    if idx is None: continue
    clr  = colors_setup[s["num"]-1]
    ep   = s["entry_price"]
    ok   = s["outcome"] in ("TP1","TP2")
    mrk  = "^" if s["direction"]=="LONG" else "v"
    ax.scatter(idx, ep - (SL_PTS if s["direction"]=="LONG" else -SL_PTS),
               marker=mrk, color=clr, s=120, zorder=6)
    ax.annotate(f'#{s["num"]}\n{et.strftime("%H:%M")}',
                xy=(idx, ep), xytext=(idx, ep + (12 if s["direction"]=="LONG" else -12)),
                color=clr, fontsize=8, ha='center', fontweight='bold',
                arrowprops=dict(arrowstyle='->', color=clr, lw=1))
    # TP/SL lines (cortas)
    ax.hlines(s["tp1"], idx, min(idx+6, len(ny)-1), colors=GRN, lw=0.8, ls='--', alpha=0.6)
    ax.hlines(s["sl"],  idx, min(idx+6, len(ny)-1), colors=RED, lw=0.8, ls='--', alpha=0.6)
    # Resultado badge
    res_clr = GRN if ok else RED
    res_txt = f'{"✓" if ok else "✗"} {s["outcome"]} {s["pts"]:+.0f}pt'
    ax2.barh(s["num"]-1, s["pnl"], color=res_clr, alpha=0.8, height=0.6)
    ax2.text(0, s["num"]-1, f' #{s["num"]} {s["nombre"][:30]}', color='#94a3b8',
             va='center', fontsize=9)

# X ticks
tick_idx = [i for i,b in enumerate(ny) if b["et"].minute==0]
ax.set_xticks(tick_idx)
ax.set_xticklabels([ny[i]["et"].strftime('%H:%M') for i in tick_idx],
                    color='#64748b', fontsize=8)
ax.tick_params(colors='#64748b'); ax.spines['bottom'].set_color('#2d2d4e')
for sp in ['top','right']: ax.spines[sp].set_visible(False)
ax.spines['left'].set_color('#2d2d4e')

ax.set_title(f'LUNES {TARGET_DATE} — NY Session — 5 Setups Apex $50k | COT BULL',
             color='#f59e0b', fontsize=14, fontweight='bold', pad=10)
ax.legend(fontsize=9, facecolor=BG, labelcolor='#94a3b8', framealpha=0.8,
          loc='upper left')
ax.set_ylabel('Precio NQ', color='#64748b', fontsize=9)

# P&L bar chart
ax2.axvline(0, color='#475569', lw=0.8)
ax2.set_xlim(-RISK_USD*1.5, TARGET2_USD*1.5)
ax2.set_yticks(range(len(setups)))
ax2.set_yticklabels([f"#{s['num']}" for s in setups], color='#64748b', fontsize=8)
ax2.set_xlabel('P&L por trade ($)', color='#64748b', fontsize=9)
ax2.tick_params(colors='#64748b')
for sp in ['top','right']: ax2.spines[sp].set_visible(False)
ax2.spines['left'].set_color('#2d2d4e'); ax2.spines['bottom'].set_color('#2d2d4e')
ax2.text(0.98, 0.85, f'Total: ${total_pnl:+.0f}\n{wins}/{len(setups)} ganadores',
         transform=ax2.transAxes, color=GRN if total_pnl>0 else RED,
         fontsize=11, fontweight='bold', ha='right', va='top')

out = f'setups_lunes_{TARGET_DATE}.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor=BG)
print(f"\nGráfica guardada: {out}")
plt.close()
