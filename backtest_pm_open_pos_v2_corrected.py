"""
BACKTEST CORREGIDO — Sin Look-Ahead Bias
========================================
Corrección principal:
  - En lugar de usar val/vah del MISMO DÍA, usamos val/vah del DÍA ANTERIOR
  - pm_open_pos se reclasifica con el VA previo (lo que el trader realmente veía)
  - El target/stop se calculan con el VA previo (no con info del futuro)

Además:
  - pm_lo / pm_hi SON datos pre-market (3am-9:30am) → no hay look-ahead ahí
  - ny_open_price es la apertura real 9:30am → OK

La lógica del trade es:
  Si pm_open (apertura 3am) está BELOW del VA del día anterior
  → SHORT desde ny_open hacia prev_val (= VAL del día anterior)
  Stop = prev_vah + 10% del prev_va_range
"""

import csv

# ─── Cargar datos ────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv', encoding='utf-8')))
rows.sort(key=lambda r: r['date'])

# ─── Agregar datos del día ANTERIOR a cada fila ───────────────────────────────
# Para cada día, el VA que el trader usaría es el del día anterior
enriched = []
for i, r in enumerate(rows):
    if i == 0:
        continue  # no hay "día anterior" para el primer registro
    prev = rows[i - 1]
    r['prev_val']      = float(prev['val'])
    r['prev_vah']      = float(prev['vah'])
    r['prev_va_range'] = float(prev['va_range'])
    r['prev_date']     = prev['date']

    # Reclasificar pm_open_pos usando el VA del día ANTERIOR
    pm_open_val = float(r['pm_open'])
    if pm_open_val > r['prev_vah']:
        r['pm_open_pos_corrected'] = 'ABOVE_VA'
    elif pm_open_val < r['prev_val']:
        r['pm_open_pos_corrected'] = 'BELOW_VA'
    else:
        r['pm_open_pos_corrected'] = 'INSIDE_VA'

    enriched.append(r)

SEP = "=" * 70
sep = "-" * 70

print(f"\n{SEP}")
print("  BACKTEST CORREGIDO — pm_open vs VA del DÍA ANTERIOR")
print(f"  Total días con datos previos: {len(enriched)}")
print(f"  Período: {enriched[0]['date']} → {enriched[-1]['date']}")
print(f"{SEP}\n")

# ─── Función evaluar trade (ahora con prev_vah/val) ──────────────────────────
def evaluar_trade(r, direccion):
    try:
        ny_open      = float(r['ny_open_price'])
        prev_vah     = r['prev_vah']
        prev_val     = r['prev_val']
        prev_range   = r['prev_va_range']
        pm_hi        = float(r['pm_hi'])   # high del pre-market
        pm_lo        = float(r['pm_lo'])   # low del pre-market
        pm_close     = float(r['pm_close'])
    except (ValueError, KeyError):
        return None, 0, 0

    if prev_range <= 0:
        return None, 0, 0

    if direccion == 'SHORT':
        target    = prev_val
        stop      = prev_vah + prev_range * 0.10
        entrada   = ny_open
        riesgo    = max(stop - entrada, 1)
        potencial = entrada - target

        hit_stop   = pm_hi >= stop
        hit_target = pm_lo <= target

        if hit_stop and hit_target:
            # Asumimos LOSS si ambos (stop primero es el peor caso conservador)
            resultado = 'LOSS'; puntos = -riesgo
        elif hit_stop:
            resultado = 'LOSS'; puntos = -riesgo
        elif hit_target:
            resultado = 'WIN'; puntos = potencial
        else:
            if pm_close < entrada:
                resultado = 'PARTIAL_WIN'; puntos = entrada - pm_close
            else:
                resultado = 'PARTIAL_LOSS'; puntos = entrada - pm_close

    else:  # LONG
        target    = prev_vah
        stop      = prev_val - prev_range * 0.10
        entrada   = ny_open
        riesgo    = max(entrada - stop, 1)
        potencial = target - entrada

        hit_stop   = pm_lo <= stop
        hit_target = pm_hi >= target

        if hit_stop and hit_target:
            resultado = 'LOSS'; puntos = -riesgo
        elif hit_stop:
            resultado = 'LOSS'; puntos = -riesgo
        elif hit_target:
            resultado = 'WIN'; puntos = potencial
        else:
            if pm_close > entrada:
                resultado = 'PARTIAL_WIN'; puntos = pm_close - entrada
            else:
                resultado = 'PARTIAL_LOSS'; puntos = pm_close - entrada

    rr = potencial / riesgo if riesgo > 0 else 0
    return resultado, round(puntos, 1), round(rr, 2)

# ─── COMPARACION: original vs corregido ──────────────────────────────────────
print("COMPARACIÓN: Clasificación ORIGINAL (same-day VA) vs CORREGIDA (prev-day VA)\n")
diff_count = 0
for r in enriched:
    orig = r['pm_open_pos']
    corr = r['pm_open_pos_corrected']
    if orig != corr:
        diff_count += 1
        if diff_count <= 10:  # mostrar solo primeros 10 cambios
            print(f"  {r['date']} ({r['weekday']:<8}): {orig} → {corr}  "
                  f"[pm_open={float(r['pm_open']):.1f}  prev_val={r['prev_val']:.1f}  "
                  f"prev_vah={r['prev_vah']:.1f}  same_day_val={r['val']}]")
print(f"\n  Total días con clasificación DIFERENTE: {diff_count}/{len(enriched)} "
      f"({diff_count/len(enriched)*100:.1f}%)\n")

# ─── BACKTEST CORREGIDO ───────────────────────────────────────────────────────
configs = [
    ("Sin filtro",           lambda r: True),
    ("TIER1 prev_range<100", lambda r: r['prev_va_range'] < 100),
    ("Trend=BULL",           lambda r: r.get('trend','') == 'BULL'),
]

for desc, filtro in configs:
    print(f"\n{'─'*70}")
    print(f"  FILTRO: {desc}")
    print(f"{'─'*70}\n")

    total_pts = 0
    total_trades = 0

    for pos, direc in [('ABOVE_VA', 'LONG'), ('BELOW_VA', 'SHORT')]:
        dias = [r for r in enriched if r['pm_open_pos_corrected'] == pos and filtro(r)]
        if not dias:
            continue

        wins = pw = pl = losses = 0
        puntos_acum = 0
        trades = []

        for r in dias:
            res, pts, rr = evaluar_trade(r, direc)
            if res is None:
                continue
            if res == 'WIN':          wins += 1
            elif res == 'PARTIAL_WIN':   pw += 1
            elif res == 'PARTIAL_LOSS':  pl += 1
            elif res == 'LOSS':          losses += 1
            puntos_acum += pts
            trades.append((r['date'], r['weekday'], r['prev_va_range'], res, pts, rr))

        n = wins + pw + pl + losses
        if n == 0:
            continue

        win_rate = (wins + pw) / n * 100

        print(f"  {pos} → {direc}  |  {n} trades")
        print(f"  {'Fecha':<13} {'Day':<9} {'VA_prev':>8} {'Resultado':<14} {'Pts':>8}  {'R:R':>5}")
        print(f"  {'─'*58}")
        for fecha, day, vr, res, pts, rr in trades:
            sym = ("✅ WIN      " if res == 'WIN' else
                   "⚡ PART WIN " if res == 'PARTIAL_WIN' else
                   "⚠️ PART LOSS" if res == 'PARTIAL_LOSS' else
                   "❌ LOSS     ")
            print(f"  {fecha:<13} {day:<9} {vr:>8.1f} {sym} {pts:>+8.1f}  {rr:>5.2f}")

        print(f"\n  ┌─ RESUMEN ─────────────────────────────────────────────────┐")
        print(f"  │  WIN completo  : {wins:>3} ({wins/n*100:.0f}%)")
        print(f"  │  WIN parcial   : {pw:>3} ({pw/n*100:.0f}%)")
        print(f"  │  LOSS parcial  : {pl:>3} ({pl/n*100:.0f}%)")
        print(f"  │  LOSS completo : {losses:>3} ({losses/n*100:.0f}%)")
        print(f"  │  Win rate total: {win_rate:.0f}%")
        print(f"  │  Pts acumulados: {puntos_acum:>+.1f} pts NQ")
        print(f"  │  Pts por trade : {puntos_acum/n:>+.1f} pts")
        print(f"  │  MNQ ($2/pt)   : ${puntos_acum*2:>+.0f}")
        print(f"  │  NQ  ($20/pt)  : ${puntos_acum*20:>+.0f}")
        print(f"  └────────────────────────────────────────────────────────────┘\n")

        total_pts    += puntos_acum
        total_trades += n

    print(f"  COMBINADO ({desc}):")
    print(f"    Total trades: {total_trades}")
    if total_trades:
        print(f"    Pts totales : {total_pts:+.1f}")
        print(f"    Pts/trade   : {total_pts/total_trades:+.1f}")
        print(f"    MNQ total   : ${total_pts*2:+.0f}")
        print(f"    NQ total    : ${total_pts*20:+.0f}")

print(f"\n{SEP}")
print("  FIN DEL BACKTEST CORREGIDO — Sin Look-Ahead Bias")
print(f"{SEP}\n")
