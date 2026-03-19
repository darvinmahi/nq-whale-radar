"""
ESTRATEGIA PURA ICT — BACKTEST
================================
Regla simple ICT de Sesiones:

  1. Asia (00:00 - 04:00 NY): Define el rango High/Low
  2. Londres (04:00 - 09:00 NY): ¿Barre el Low o el High de Asia?
  3. New York (09:30 - 12:00 NY): Opera LA REVERSIÓN del sweep

SETUP BUY:
  - Londres barrió el LOW de Asia (Judas Swing bajista)
  - NY abre → espera que el precio suba de vuelta al equilibrio de Asia
  - Entrada: primer retroceso al Low de Asia
  - Target: High de Asia
  - Stop: Low del sweep de Londres

SETUP SELL:
  - Londres barrió el HIGH de Asia (Judas Swing alcista)
  - NY abre → espera que el precio baje de vuelta
  - Entrada: primer retroceso al High de Asia
  - Target: Low de Asia
  - Stop: High del sweep de Londres

Sin mezclas. ICT puro.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

print("="*60)
print("  ICT PURO — SESIONES ASIA → LONDRES → NY")
print("  Judas Swing + Reversión en New York")
print("="*60)

# --- DATOS ---
print("\n📡 Descargando NQ=F horario (2 años)...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')
raw['hour'] = raw.index.hour
raw['date'] = raw.index.date
print(f"  ✅ {len(raw)} velas cargadas.")

# --- BACKTEST ---
print("\n🔍 Ejecutando backtest ICT puro...")

trades = []
dates  = sorted(raw['date'].unique())

for d in dates:
    day = raw[raw['date'] == d]

    asia   = day[day['hour'].between(0, 3)]
    london = day[day['hour'].between(4, 8)]
    ny     = day[day['hour'].between(9, 11)]

    if asia.empty or london.empty or ny.empty:
        continue

    # Rango Asia
    asia_hi = float(asia['High'].max())
    asia_lo = float(asia['Low'].min())
    asia_rng = asia_hi - asia_lo
    if asia_rng < 10:  # Filtro: días sin rango (festivos, etc.)
        continue

    # ¿Qué hizo Londres?
    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())

    swept_lo = lon_lo < asia_lo  # Londres bajó del Low de Asia
    swept_hi = lon_hi > asia_hi  # Londres subió del High de Asia

    # Solo interesa cuando Londres hizo UN sweep limpio (no ambos)
    if swept_lo == swept_hi:  # Ambos o ninguno → ignorar
        continue

    ny_bars = ny.reset_index(drop=False)
    if ny_bars.empty:
        continue

    ny_open = float(ny_bars.iloc[0]['Open'])

    # ─── SETUP BUY: Londres sweepó el LOW de Asia ─────────────────────────
    if swept_lo:
        entry  = asia_lo          # Entrada: vuelve al Low de Asia (nivel anterior)
        target = asia_hi          # Target: High de Asia (rango completo)
        stop   = lon_lo - (asia_lo - lon_lo) * 0.5  # Stop: debajo del sweep

        result = "NO_TRADE"
        exit_p = 0.0

        # Simular barra a barra en NY
        for _, bar in ny_bars.iterrows():
            lo_b = float(bar['Low'])
            hi_b = float(bar['High'])

            if lo_b <= stop:
                result = "LOSS"
                exit_p = stop
                break
            if hi_b >= entry and result == "NO_TRADE":
                # Precio llegó a la zona de entrada
                result = "IN"
            if result == "IN":
                if lo_b <= stop:
                    result = "LOSS"
                    exit_p = stop
                    break
                if hi_b >= target:
                    result = "WIN"
                    exit_p = target
                    break

        if result in ("NO_TRADE", "IN"):
            last = float(ny_bars.iloc[-1]['Close'])
            result = "FLAT"
            exit_p = last if result == "IN" else 0.0

        if result != "NO_TRADE":
            pnl = exit_p - entry if result != "FLAT" else float(ny_bars.iloc[-1]['Close']) - entry
            trades.append({
                "date":      str(d),
                "setup":     "BUY",
                "result":    result,
                "entry":     round(entry, 2),
                "exit":      round(exit_p, 2),
                "stop":      round(stop, 2),
                "target":    round(target, 2),
                "pnl_pts":   round(pnl, 2),
                "asia_rng":  round(asia_rng, 2),
                "lon_sweep": round(asia_lo - lon_lo, 2), # cuánto barrió
            })

    # ─── SETUP SELL: Londres sweepó el HIGH de Asia ────────────────────────
    elif swept_hi:
        entry  = asia_hi
        target = asia_lo
        stop   = lon_hi + (lon_hi - asia_hi) * 0.5

        result = "NO_TRADE"
        exit_p = 0.0

        for _, bar in ny_bars.iterrows():
            lo_b = float(bar['Low'])
            hi_b = float(bar['High'])

            if hi_b >= stop:
                result = "LOSS"
                exit_p = stop
                break
            if lo_b <= entry and result == "NO_TRADE":
                result = "IN"
            if result == "IN":
                if hi_b >= stop:
                    result = "LOSS"
                    exit_p = stop
                    break
                if lo_b <= target:
                    result = "WIN"
                    exit_p = target
                    break

        if result in ("NO_TRADE", "IN"):
            last = float(ny_bars.iloc[-1]['Close'])
            result = "FLAT"
            exit_p = last

        if result != "NO_TRADE":
            pnl = entry - exit_p if result != "FLAT" else entry - float(ny_bars.iloc[-1]['Close'])
            trades.append({
                "date":      str(d),
                "setup":     "SELL",
                "result":    result,
                "entry":     round(entry, 2),
                "exit":      round(exit_p, 2),
                "stop":      round(stop, 2),
                "target":    round(target, 2),
                "pnl_pts":   round(pnl, 2),
                "asia_rng":  round(asia_rng, 2),
                "lon_sweep": round(lon_hi - asia_hi, 2),
            })

# --- RESULTADOS ---
print(f"\n{'='*60}")
print(f"  📊 RESULTADOS — ICT PURO (ASIA→LONDRES SWEEP→NY)")
print(f"{'='*60}\n")

if not trades:
    print("  ❌ Sin trades generados.")
else:
    t = pd.DataFrame(trades)
    t.to_csv(os.path.join(BASE_DIR, "ict_pure_trades.csv"), index=False)

    total  = len(t)
    wins   = len(t[t['result'] == 'WIN'])
    losses = len(t[t['result'] == 'LOSS'])
    flats  = len(t[t['result'] == 'FLAT'])
    wr     = wins / (wins + losses) * 100 if (wins + losses) > 0 else 0

    buy_t  = t[t['setup'] == 'BUY']
    sell_t = t[t['setup'] == 'SELL']
    buy_wr  = len(buy_t[buy_t['result']  == 'WIN']) / len(buy_t[buy_t['result'].isin(['WIN','LOSS'])]) * 100 if len(buy_t) > 0 else 0
    sell_wr = len(sell_t[sell_t['result'] == 'WIN']) / len(sell_t[sell_t['result'].isin(['WIN','LOSS'])]) * 100 if len(sell_t) > 0 else 0

    closed  = t[t['result'].isin(['WIN', 'LOSS'])]
    avg_win  = closed[closed['result'] == 'WIN']['pnl_pts'].mean()
    avg_loss = closed[closed['result'] == 'LOSS']['pnl_pts'].mean()
    rr       = abs(avg_win / avg_loss) if avg_loss and avg_loss != 0 else 0

    print(f"  🎯 Días con setup válido:  {total}")
    print(f"  ✅ Wins:   {wins}  |  ❌ Losses: {losses}  |  ↔️  Flat: {flats}")
    print(f"  📊 Win Rate (sin flats):  {wr:.1f}%")
    print(f"\n  📈 BUY  setups: {len(buy_t)}  → WR: {buy_wr:.1f}%")
    print(f"  📉 SELL setups: {len(sell_t)} → WR: {sell_wr:.1f}%")
    print(f"\n  💰 Avg WIN:    +{avg_win:.0f} pts NQ  (~${avg_win*20:.0f} /contrato)")
    print(f"  💸 Avg LOSS:   {avg_loss:.0f} pts NQ  (~${avg_loss*20:.0f} /contrato)")
    print(f"  ⚖️  RR Real:    1:{rr:.2f}")

    # Profit total simulado (1 contrato)
    total_pnl_pts = closed['pnl_pts'].sum()
    print(f"\n  💵 PnL Total (1 contrato): {total_pnl_pts:+.0f} pts  (~${total_pnl_pts*20:+.0f})")

    print(f"\n✅ Trades guardados: ict_pure_trades.csv")

    # Guardar JSON
    summary = {
        "strategy": "ICT Puro — Asia Range + Londres Sweep + NY Reversion",
        "total_setups": int(total),
        "wins": int(wins), "losses": int(losses), "flats": int(flats),
        "win_rate": round(wr, 1),
        "buy_wr": round(buy_wr, 1),
        "sell_wr": round(sell_wr, 1),
        "avg_win_pts": round(float(avg_win), 1),
        "avg_loss_pts": round(float(avg_loss), 1),
        "rr_ratio": round(rr, 2),
        "total_pnl_pts": round(float(total_pnl_pts), 1),
    }
    with open(os.path.join(BASE_DIR, "ict_pure_strategy.json"), "w") as f:
        json.dump(summary, f, indent=4)
