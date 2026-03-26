"""
BACKTEST DEFINITIVO v3 — pm_open_pos Setup (Lógica correcta)
=============================================================
LÓGICA REAL del setup:

El trader observa en la apertura del premarket (3am):
  - Si pm_open > prev_vah   → ABOVE_VA → BIAS ALCISTA para NY
  - Si pm_open < prev_val   → BELOW_VA → BIAS BAJISTA para NY

El trade se ejecuta en ny_open (9:30am):

Para LONG (ABOVE_VA):
  - Solo válido si ny_open <= prev_vah * 1.01 (no se extendió demasiado)
  - O sea: el mercado no se alejó mucho del VA todavía
  - Entrada: ny_open
  - Target: prev_vah + prev_range * 0.5 (si ny_open > prev_vah) 
            o prev_vah (si ny_open < prev_vah)
  - Stop: min(ny_open - prev_range*0.3, prev_val)  → stop debajo de entrada

Para SHORT (BELOW_VA):
  - Solo válido si ny_open >= prev_val * 0.99
  - Entrada: ny_open
  - Target: prev_val - prev_range * 0.5 (si ny_open < prev_val)
            o prev_val (si ny_open > prev_val)
  - Stop: max(ny_open + prev_range*0.3, prev_vah) → stop por encima de entrada

Resultado:
  - WIN: prof_hi >= target (LONG) o prof_lo <= target (SHORT)
  - LOSS: prof_lo <= stop (LONG) o prof_hi >= stop (SHORT)
  - Cierre: close_above/below/inside (resultado real del día)
"""

import csv
from collections import defaultdict

# ─── Cargar datos ────────────────────────────────────────────────────────────
rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv', encoding='utf-8')))
rows.sort(key=lambda r: r['date'])

# ─── Enriquecer con datos del día anterior ────────────────────────────────────
enriched = []
for i, r in enumerate(rows):
    if i == 0:
        continue
    prev = rows[i - 1]
    try:
        prev_val   = float(prev['val'])
        prev_vah   = float(prev['vah'])
        prev_range = float(prev['va_range'])
    except (ValueError, KeyError):
        continue
    if prev_range <= 0:
        continue
    try:
        pm_open_price = float(r['pm_open'])
        ny_open       = float(r['ny_open_price'])
        prof_hi       = float(r['prof_hi'])
        prof_lo       = float(r['prof_lo'])
    except (ValueError, KeyError):
        continue

    if pm_open_price > prev_vah:
        pos = 'ABOVE_VA'
    elif pm_open_price < prev_val:
        pos = 'BELOW_VA'
    else:
        pos = 'INSIDE_VA'

    enriched.append({
        'date':        r['date'],
        'weekday':     r['weekday'],
        'pm_open':     pm_open_price,
        'ny_open':     ny_open,
        'prof_hi':     prof_hi,
        'prof_lo':     prof_lo,
        'prev_val':    prev_val,
        'prev_vah':    prev_vah,
        'prev_range':  prev_range,
        'pm_pos':      pos,
        'trend':       r.get('trend', ''),
        'close_above': r.get('close_above_va', 'False') == 'True',
        'close_below': r.get('close_below_va', 'False') == 'True',
        'close_inside':r.get('close_inside', 'False') == 'True',
    })

SEP = "=" * 72
print(f"\n{SEP}")
print("  BACKTEST v3 — pm_open × VA del Día Anterior (Lógica Corregida)")
print(f"  Período: {enriched[0]['date']} → {enriched[-1]['date']}")
print(f"  Total días: {len(enriched)}")
print(f"{SEP}\n")

# ─── Función de evaluación CORRECTA ──────────────────────────────────────────
def evaluar(r, direc):
    ny_open    = r['ny_open']
    prev_val   = r['prev_val']
    prev_vah   = r['prev_vah']
    prev_range = r['prev_range']
    prof_hi    = r['prof_hi']
    prof_lo    = r['prof_lo']

    if direc == 'LONG':
        entrada = ny_open
        stop    = prev_val - prev_range * 0.10

        # Target: si ny_open ya está por encima de prev_vah, target es extensión
        if ny_open < prev_vah:
            target = prev_vah
        else:
            # ny_open ya superó el VA → target = más arriba
            target = ny_open + prev_range * 0.50

        riesgo = max(entrada - stop, 1)
        potenc = target - entrada  # SIEMPRE positivo ahora

        hit_stop   = prof_lo <= stop
        hit_target = prof_hi >= target

        if hit_stop and hit_target:
            # Usamos close para decidir
            return ('WIN'  if r['close_above'] else 'LOSS',
                    potenc if r['close_above'] else -riesgo, potenc/riesgo)
        elif hit_stop:
            return 'LOSS', -riesgo, potenc/riesgo
        elif hit_target:
            return 'WIN', potenc, potenc/riesgo
        else:
            # Sin tocar ni stop ni target → usamos cierre del día
            if r['close_above']:
                return 'PARTIAL_WIN', prev_range * 0.20, potenc/riesgo
            elif r['close_inside']:
                return 'PARTIAL_WIN', prev_range * 0.10, potenc/riesgo
            else:
                return 'PARTIAL_LOSS', -prev_range * 0.10, potenc/riesgo

    else:  # SHORT
        entrada = ny_open
        stop    = prev_vah + prev_range * 0.10

        if ny_open > prev_val:
            target = prev_val
        else:
            target = ny_open - prev_range * 0.50

        riesgo = max(stop - entrada, 1)
        potenc = entrada - target  # SIEMPRE positivo

        hit_stop   = prof_hi >= stop
        hit_target = prof_lo <= target

        if hit_stop and hit_target:
            return ('WIN'  if r['close_below'] else 'LOSS',
                    potenc if r['close_below'] else -riesgo, potenc/riesgo)
        elif hit_stop:
            return 'LOSS', -riesgo, potenc/riesgo
        elif hit_target:
            return 'WIN', potenc, potenc/riesgo
        else:
            if r['close_below']:
                return 'PARTIAL_WIN', prev_range * 0.20, potenc/riesgo
            elif r['close_inside']:
                return 'PARTIAL_WIN', prev_range * 0.10, potenc/riesgo
            else:
                return 'PARTIAL_LOSS', -prev_range * 0.10, potenc/riesgo

# ─── BACKTEST ─────────────────────────────────────────────────────────────────
configs = [
    ("Sin filtro",          lambda r: True),
    ("prev_range < 100",    lambda r: r['prev_range'] < 100),
    ("prev_range 100-200",  lambda r: 100 <= r['prev_range'] < 200),
    ("Solo LUN-JUE",        lambda r: r['weekday'] not in ('VIERNES',)),
]

for desc, filtro in configs:
    print(f"\n{'─'*72}")
    print(f"  FILTRO: {desc}")
    print(f"{'─'*72}\n")

    total_pts = 0
    total_trades = 0

    for pos, direc in [('ABOVE_VA', 'LONG'), ('BELOW_VA', 'SHORT')]:
        dias = [r for r in enriched if r['pm_pos'] == pos and filtro(r)]
        if not dias:
            continue

        wins = pw = pl = losses = 0
        puntos_acum = 0
        trades_list = []

        for r in dias:
            res, pts, rr = evaluar(r, direc)
            pts = round(pts, 1)
            if res == 'WIN':           wins   += 1
            elif res == 'PARTIAL_WIN': pw     += 1
            elif res == 'PARTIAL_LOSS':pl     += 1
            elif res == 'LOSS':        losses += 1
            puntos_acum += pts
            trades_list.append((r['date'], r['weekday'], r['prev_range'], res, pts, rr))

        n = wins + pw + pl + losses
        if n == 0:
            continue

        wr = (wins + pw) / n * 100

        print(f"  {pos} → {direc}  |  {n} trades")
        print(f"  {'Fecha':<13} {'Día':<11} {'VA_prev':>8} {'Resultado':<14} {'Pts':>9}  {'R:R':>5}")
        print(f"  {'─'*64}")
        for fecha, day, vr, res, pts, rr in trades_list:
            sym = ("✅ WIN      " if res == 'WIN'          else
                   "⚡ PART WIN " if res == 'PARTIAL_WIN'  else
                   "⚠️ PART LOSS" if res == 'PARTIAL_LOSS' else
                   "❌ LOSS     ")
            print(f"  {fecha:<13} {day:<11} {vr:>8.1f} {sym} {pts:>+9.1f}  {rr:>5.2f}")

        print(f"\n  ┌─ RESUMEN {'─'*52}┐")
        print(f"  │  WIN completo  : {wins:>3} ({wins/n*100:.0f}%)")
        print(f"  │  WIN parcial   : {pw:>3} ({pw/n*100:.0f}%)")
        print(f"  │  LOSS parcial  : {pl:>3} ({pl/n*100:.0f}%)")
        print(f"  │  LOSS completo : {losses:>3} ({losses/n*100:.0f}%)")
        print(f"  │  Win rate      : {wr:.0f}%")
        print(f"  │  Pts acumulados: {puntos_acum:>+.1f} pts NQ")
        print(f"  │  Pts/trade     : {puntos_acum/n:>+.1f} pts")
        print(f"  │  MNQ ($2/pt)   : ${puntos_acum*2:>+.0f}")
        print(f"  │  NQ  ($20/pt)  : ${puntos_acum*20:>+.0f}")
        print(f"  └{'─'*64}┘\n")

        total_pts += puntos_acum
        total_trades += n

    if total_trades:
        print(f"  COMBINADO ({desc}): {total_trades} trades  |  {total_pts:+.1f} pts  "
              f"|  ${total_pts*2:+.0f} MNQ  |  ${total_pts*20:+.0f} NQ")

print(f"\n{SEP}")
print("  FIN — BACKTEST v3 DEFINITIVO")
print(f"{SEP}\n")
