"""
BACKTEST FORMAL: pm_open_pos Setup (con columnas correctas)
Columnas disponibles: ny_open_price, pm_hi, pm_lo, pm_close, vah, val, va_range
"""
import csv
from collections import defaultdict

rows = []
with open("ny_profile_asia_london_daily.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        rows.append(r)

SEP = "=" * 65
sep = "-" * 65

print(f"\n{SEP}")
print("  BACKTEST: pm_open_pos → ¿London predice el cierre NY?")
print(f"  Total días: {len(rows)}")
print(f"{SEP}\n")

def evaluar_trade(r, direccion):
    try:
        ny_open  = float(r["ny_open_price"])    # apertura NY 9:30am
        vah      = float(r["vah"])
        val      = float(r["val"])
        va_range = float(r["va_range"])
        pm_hi    = float(r["pm_hi"])            # high del pre-market (asia+london)
        pm_lo    = float(r["pm_lo"])            # low del pre-market
        pm_close = float(r["pm_close"])         # cierre de la sesión PM (≈4pm NY)
    except (ValueError, KeyError):
        return None, 0, 0

    if va_range <= 0:
        return None, 0, 0

    if direccion == "LONG":
        entrada  = ny_open
        target   = vah if ny_open < vah else vah + va_range * 0.5
        stop     = val - va_range * 0.10
        riesgo   = max(entrada - stop, 1)
        potencial= target - entrada

        # ¿Se tocó el stop o el target durante el día?
        # Usamos pm_lo como proxy del low del día NY (incluye tanto PM como NY)
        hit_stop   = pm_lo <= stop
        hit_target = pm_hi >= target

        if hit_stop and hit_target:
            # Ambos; asumimos que el stop se tocó primero si pm_lo < stop
            resultado = "LOSS"; puntos = -riesgo
        elif hit_stop:
            resultado = "LOSS"; puntos = -riesgo
        elif hit_target:
            resultado = "WIN"; puntos = potencial
        else:
            # Por cierre
            if pm_close > entrada:
                resultado = "PARTIAL_WIN"; puntos = pm_close - entrada
            else:
                resultado = "PARTIAL_LOSS"; puntos = pm_close - entrada

    else:  # SHORT
        entrada  = ny_open
        target   = val if ny_open > val else val - va_range * 0.5
        stop     = vah + va_range * 0.10
        riesgo   = max(stop - entrada, 1)
        potencial= entrada - target

        hit_stop   = pm_hi >= stop
        hit_target = pm_lo <= target

        if hit_stop and hit_target:
            resultado = "LOSS"; puntos = -riesgo
        elif hit_stop:
            resultado = "LOSS"; puntos = -riesgo
        elif hit_target:
            resultado = "WIN"; puntos = potencial
        else:
            if pm_close < entrada:
                resultado = "PARTIAL_WIN"; puntos = entrada - pm_close
            else:
                resultado = "PARTIAL_LOSS"; puntos = entrada - pm_close

    return resultado, round(puntos, 1), round(potencial/riesgo, 2)

# ────────────────────────────────────────────────────────────
# BACKTEST PRINCIPAL
# ────────────────────────────────────────────────────────────
configs = [
    ("Sin filtro",   lambda r: True),
    ("TIER1 <100",   lambda r: float(r["va_range"]) < 100),
]

for desc, filtro in configs:
    print(f"\n{'─'*65}")
    print(f"  CONFIGURACIÓN: {desc}")
    print(f"{'─'*65}\n")
    
    total_pts = 0
    total_trades = 0
    
    for pos, direc in [("ABOVE_VA", "LONG"), ("BELOW_VA", "SHORT")]:
        dias = [r for r in rows if r["pm_open_pos"] == pos and filtro(r)]
        if not dias:
            continue
        
        desglose = defaultdict(int)
        puntos_acum = 0
        trades = []
        
        for r in dias:
            res, pts, rr = evaluar_trade(r, direc)
            if res is None:
                continue
            desglose[res] += 1
            puntos_acum += pts
            trades.append((r["date"], float(r["va_range"]), res, pts, rr))
        
        n = sum(desglose.values())
        if n == 0:
            continue
        
        wins      = desglose["WIN"]
        pw        = desglose["PARTIAL_WIN"]
        pl        = desglose["PARTIAL_LOSS"]
        losses    = desglose["LOSS"]
        win_rate  = (wins + pw) / n * 100
        
        print(f"  {pos} → {direc}  |  {n} trades")
        print(f"  {'Fecha':<13} {'VA rng':>7} {'Res':<16} {'Pts':>8}  {'R:R':>5}")
        print(f"  {'─'*55}")
        for fecha, vr, res, pts, rr in trades:
            emoji = "✅ WIN      " if res == "WIN" else \
                    "⚡ PART WIN " if res == "PARTIAL_WIN" else \
                    "⚠️ PART LOSS" if res == "PARTIAL_LOSS" else \
                    "❌ LOSS     "
            print(f"  {fecha:<13} {vr:>7.1f} {emoji} {pts:>+8.1f}  {rr:>5.2f}")
        
        print(f"\n  ┌─ RESUMEN {'─'*42}┐")
        print(f"  │  WIN completo  : {wins:>3} ({wins/n*100:.0f}%)")
        print(f"  │  WIN parcial   : {pw:>3} ({pw/n*100:.0f}%)")
        print(f"  │  LOSS parcial  : {pl:>3} ({pl/n*100:.0f}%)")
        print(f"  │  LOSS completo : {losses:>3} ({losses/n*100:.0f}%)")
        print(f"  │  Win rate total: {win_rate:.0f}%")
        print(f"  │  Pts acumulados: {puntos_acum:>+.1f} pts NQ")
        print(f"  │  Pts por trade : {puntos_acum/n:>+.1f} pts")
        print(f"  │  MNQ ($2/pt)   : ${puntos_acum*2:>+.0f}")
        print(f"  │  NQ  ($20/pt)  : ${puntos_acum*20:>+.0f}")
        print(f"  └{'─'*52}┘\n")
        
        total_pts += puntos_acum
        total_trades += n

    print(f"  COMBINADO ({desc}):")
    print(f"    Total trades: {total_trades}")
    if total_trades:
        print(f"    Pts totales : {total_pts:+.1f}")
        print(f"    Pts/trade   : {total_pts/total_trades:+.1f}")
        print(f"    MNQ total   : ${total_pts*2:+.0f}")
        print(f"    NQ total    : ${total_pts*20:+.0f}")

print(f"\n{SEP}")
print("  FIN DEL BACKTEST")
print(f"{SEP}\n")
