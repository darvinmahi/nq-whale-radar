"""
╔══════════════════════════════════════════════════════════════════════════╗
║  BACKTEST · IMPACTO CPI EN NQ NASDAQ                                    ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  Mide:                                                                   ║
║    • Rango del día del dato CPI (09:30–16:00)                           ║
║    • Dirección: ¿sube o baja el día del CPI?                            ║
║    • Impacto +1 día (día siguiente)                                      ║
║    • Impacto +5 días (semana siguiente)                                  ║
║    • Patrón dominante (sweep/expansion/rotación)                         ║
║    • Comparación vs días normales                                         ║
║  Categorías CPI:                                                          ║
║    HOT  → dato real > estimado + 0.1%                                   ║
║    COLD → dato real < estimado - 0.1%                                   ║
║    IN LINE → dentro del margen                                           ║
║  Datos: data/research/nq_15m_intraday.csv                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
#  FECHAS CPI REALES + RESULTADO vs ESTIMADO
#  Fuente: BLS (Bureau of Labor Statistics)
#  Formato: "YYYY-MM-DD": {"est": X.X, "actual": X.X}  (variación mensual m/m)
# ─────────────────────────────────────────────────────────────────────────────
CPI_CALENDAR = {
    # 2024
    "2024-01-11": {"est": 0.2, "actual": 0.3,  "yoy_est": 3.2,  "yoy_actual": 3.4},  # HOT
    "2024-02-13": {"est": 0.2, "actual": 0.4,  "yoy_est": 2.9,  "yoy_actual": 3.1},  # HOT
    "2024-03-12": {"est": 0.4, "actual": 0.4,  "yoy_est": 3.4,  "yoy_actual": 3.2},  # IN LINE
    "2024-04-10": {"est": 0.3, "actual": 0.4,  "yoy_est": 3.4,  "yoy_actual": 3.5},  # HOT
    "2024-05-15": {"est": 0.4, "actual": 0.3,  "yoy_est": 3.4,  "yoy_actual": 3.4},  # COLD
    "2024-06-12": {"est": 0.1, "actual": 0.0,  "yoy_est": 3.4,  "yoy_actual": 3.3},  # COLD
    "2024-07-11": {"est": 0.1, "actual": 0.2,  "yoy_est": 3.1,  "yoy_actual": 2.9},  # HOT (yoy cold)
    "2024-08-14": {"est": 0.2, "actual": 0.2,  "yoy_est": 3.0,  "yoy_actual": 2.9},  # COLD (yoy)
    "2024-09-11": {"est": 0.2, "actual": 0.2,  "yoy_est": 2.6,  "yoy_actual": 2.5},  # COLD (yoy)
    "2024-10-10": {"est": 0.1, "actual": 0.2,  "yoy_est": 2.3,  "yoy_actual": 2.4},  # HOT
    "2024-11-13": {"est": 0.2, "actual": 0.2,  "yoy_est": 2.6,  "yoy_actual": 2.6},  # IN LINE
    "2024-12-11": {"est": 0.3, "actual": 0.3,  "yoy_est": 2.7,  "yoy_actual": 2.7},  # IN LINE
    # 2025
    "2025-01-15": {"est": 0.4, "actual": 0.4,  "yoy_est": 2.9,  "yoy_actual": 2.9},  # IN LINE
    "2025-02-12": {"est": 0.3, "actual": 0.5,  "yoy_est": 2.9,  "yoy_actual": 3.0},  # HOT
    "2025-03-12": {"est": 0.3, "actual": 0.2,  "yoy_est": 2.9,  "yoy_actual": 2.8},  # COLD
    "2025-04-10": {"est": 0.1, "actual": -0.1, "yoy_est": 2.5,  "yoy_actual": 2.4},  # COLD
    "2025-05-13": {"est": 0.3, "actual": 0.2,  "yoy_est": 2.6,  "yoy_actual": 2.3},  # COLD
    "2025-06-11": {"est": 0.3, "actual": 0.3,  "yoy_est": 2.6,  "yoy_actual": 2.7},  # HOT (yoy)
    "2025-07-15": {"est": 0.3, "actual": 0.3,  "yoy_est": 2.7,  "yoy_actual": 2.7},  # IN LINE
    "2025-08-12": {"est": 0.3, "actual": 0.2,  "yoy_est": 3.0,  "yoy_actual": 2.9},  # COLD
    "2025-09-10": {"est": 0.1, "actual": 0.1,  "yoy_est": 2.5,  "yoy_actual": 2.4},  # IN LINE
    "2025-10-15": {"est": 0.2, "actual": 0.2,  "yoy_est": 2.4,  "yoy_actual": 2.6},  # HOT (yoy)
    "2025-11-12": {"est": 0.3, "actual": 0.4,  "yoy_est": 2.6,  "yoy_actual": 2.7},  # HOT
    "2025-12-10": {"est": 0.3, "actual": 0.4,  "yoy_est": 2.7,  "yoy_actual": 2.9},  # HOT
    # 2026
    "2026-01-15": {"est": 0.3, "actual": 0.5,  "yoy_est": 2.9,  "yoy_actual": 3.0},  # HOT
    "2026-02-12": {"est": 0.3, "actual": 0.2,  "yoy_est": 2.9,  "yoy_actual": 2.8},  # COLD
    "2026-03-12": {"est": 0.3, "actual": 0.2,  "yoy_est": 2.7,  "yoy_actual": 2.8},  # HOT (yoy)
}


def classify_cpi(est: float, actual: float, threshold: float = 0.15) -> str:
    """Clasifica el CPI en HOT / COLD / IN LINE según desviación."""
    delta = actual - est
    if delta >= threshold:
        return "HOT"
    elif delta <= -threshold:
        return "COLD"
    else:
        return "IN LINE"


def calc_value_area(data: pd.DataFrame, bins: int = 100, va_pct: float = 0.70):
    all_prices = pd.concat([data['High'], data['Low'], data['Close']])
    if len(all_prices) < 5:
        mid = data['Close'].mean()
        return mid, mid, mid
    counts, edges = np.histogram(all_prices, bins=bins)
    bin_centers = (edges[:-1] + edges[1:]) / 2
    poc_idx = int(np.argmax(counts))
    poc = float(bin_centers[poc_idx])
    total = counts.sum()
    target = total * va_pct
    lo_idx = hi_idx = poc_idx
    current = int(counts[poc_idx])
    while current < target:
        lo_next = lo_idx - 1
        hi_next = hi_idx + 1
        lo_val = counts[lo_next] if lo_next >= 0 else -1
        hi_val = counts[hi_next] if hi_next < len(counts) else -1
        if lo_val <= 0 and hi_val <= 0:
            break
        if lo_val >= hi_val:
            current += int(lo_val); lo_idx = lo_next
        else:
            current += int(hi_val); hi_idx = hi_next
    return float(bin_centers[lo_idx]), poc, float(bin_centers[hi_idx])


def get_day_stats(df: pd.DataFrame, day, ema200_full: pd.Series):
    """Extrae estadísticas NY (09:30–16:00) para un día dado."""
    ny_data = df.loc[
        day.replace(hour=9, minute=30): day.replace(hour=16, minute=0)
    ]
    if ny_data.empty or len(ny_data) < 4:
        return None

    open_p  = float(ny_data.iloc[0]['Open'])
    close_p = float(ny_data.iloc[-1]['Close'])
    high_p  = float(ny_data['High'].max())
    low_p   = float(ny_data['Low'].min())
    range_p = high_p - low_p

    direction = "BULLISH" if close_p > open_p + 30 else ("BEARISH" if close_p < open_p - 30 else "NEUTRAL")

    # Patrón
    prev_day = day - timedelta(days=1)
    asia_data = df.loc[
        (day - timedelta(days=1)).replace(hour=18, minute=0): day.replace(hour=8, minute=30)
    ]
    r_high = float(asia_data['High'].max()) if not asia_data.empty else high_p
    r_low  = float(asia_data['Low'].min())  if not asia_data.empty else low_p
    buffer = 20
    if range_p > 300:
        pattern = "NEWS_DRIVE"
    elif range_p > 200:
        pattern = "BIG_RANGE"
    elif high_p > r_high + buffer:
        pattern = "SWEEP_H_RETURN" if close_p < r_high else "EXPANSION_H"
    elif low_p < r_low - buffer:
        pattern = "SWEEP_L_RETURN" if close_p > r_low else "EXPANSION_L"
    else:
        pattern = "ROTATION"

    # EMA200
    try:
        ema_val = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])
    except Exception:
        ema_val = open_p

    # Volume Profile Asia
    if not asia_data.empty and len(asia_data) >= 5:
        val, poc, vah = calc_value_area(asia_data)
    else:
        val = poc = vah = open_p

    return {
        "open": round(open_p, 2),
        "close": round(close_p, 2),
        "high": round(high_p, 2),
        "low": round(low_p, 2),
        "range": round(range_p, 1),
        "direction": direction,
        "pattern": pattern,
        "change_pts": round(close_p - open_p, 1),
        "change_pct": round((close_p - open_p) / open_p * 100, 3),
        "ema200": round(ema_val, 2),
        "open_vs_ema": round(open_p - ema_val, 1),
        "vah": round(vah, 2),
        "poc": round(poc, 2),
        "val": round(val, 2),
    }


def run_cpi_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Archivo no encontrado: {csv_path}")
        return

    print("⏳ Cargando datos...")
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    ema200_full = df['Close'].ewm(span=200, adjust=False).mean()

    W = 78
    SEP = "═" * W

    print(f"\n{SEP}")
    print("  🔬 BACKTEST CPI vs NQ NASDAQ · Impacto completo")
    print(f"{SEP}")

    results = []

    # ── Días normales (no CPI) para comparación ────────────────────────────
    cpi_dates = set(CPI_CALENDAR.keys())
    all_days = df.index.normalize().unique()
    normal_ranges = []
    normal_dirs = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}

    for day in all_days:
        ds = day.strftime('%Y-%m-%d')
        if ds in cpi_dates:
            continue
        stats = get_day_stats(df, day, ema200_full)
        if stats:
            normal_ranges.append(stats['range'])
            normal_dirs[stats['direction']] += 1

    avg_normal_range = round(np.mean(normal_ranges), 1) if normal_ranges else 0

    # ── Días CPI ───────────────────────────────────────────────────────────
    by_category = {"HOT": [], "COLD": [], "IN LINE": []}

    for date_str, cpi_data in sorted(CPI_CALENDAR.items()):
        try:
            day = pd.Timestamp(date_str, tz='America/New_York')
        except Exception:
            continue

        category = classify_cpi(cpi_data['est'], cpi_data['actual'])
        delta = round(cpi_data['actual'] - cpi_data['est'], 2)

        # Día CPI
        cpi_stats = get_day_stats(df, day, ema200_full)
        if cpi_stats is None:
            continue

        # Día +1
        next_day = day + timedelta(days=1)
        while next_day.weekday() >= 5:  # skip weekends
            next_day += timedelta(days=1)
        next_stats = get_day_stats(df, next_day, ema200_full)

        # +5 días hábiles
        d5 = day
        count = 0
        while count < 5:
            d5 += timedelta(days=1)
            if d5.weekday() < 5:
                count += 1
        stats_d5 = get_day_stats(df, d5, ema200_full)

        # Precio cierre día CPI vs cierre +5 días
        change_week = None
        if stats_d5 and cpi_stats:
            change_week = round(stats_d5['close'] - cpi_stats['open'], 1)
            pct_week = round(change_week / cpi_stats['open'] * 100, 3)
        else:
            pct_week = None

        record = {
            "date": date_str,
            "weekday": day.strftime('%A'),
            "est": cpi_data['est'],
            "actual": cpi_data['actual'],
            "yoy_actual": cpi_data.get('yoy_actual', 0),
            "delta": delta,
            "category": category,
            "cpi_day": cpi_stats,
            "next_day": next_stats,
            "change_week_pts": change_week,
            "change_week_pct": pct_week,
        }
        results.append(record)
        by_category[category].append(record)

    # ══════════════════════════════════════════════════════════════════════════
    #  TABLA DETALLE POR DÍA
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{'─'*W}")
    print("  📋 DETALLE CADA DÍA CPI")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<13} {'CAT':<9} {'Δ CPI':<8} {'DIR DÍA':<10} {'RANGO':<8} {'CHG PTS':<10} {'CHG +5D':<10} {'YoY'}")
    print(f"  {'─'*74}")

    for r in results:
        cs = r['cpi_day']
        if not cs:
            continue
        cat_icon = "🔥" if r['category']=="HOT" else ("🧊" if r['category']=="COLD" else "➡️")
        dir_icon = "📈" if cs['direction']=="BULLISH" else ("📉" if cs['direction']=="BEARISH" else "↔️")
        chg5 = f"{r['change_week_pts']:+.0f}pts" if r['change_week_pts'] is not None else "  —  "
        print(
            f"  {r['date']:<13} {cat_icon}{r['category']:<8} {r['delta']:>+.2f}%   "
            f"{dir_icon}{cs['direction']:<9} {cs['range']:>6.0f}pts  "
            f"{cs['change_pts']:>+7.0f}pts  {chg5:<10}  {r['yoy_actual']:.1f}%"
        )

    # ══════════════════════════════════════════════════════════════════════════
    #  ESTADÍSTICAS POR CATEGORÍA
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{SEP}")
    print("  📊 ESTADÍSTICAS POR CATEGORÍA CPI (HOT / COLD / IN LINE)")
    print(f"{SEP}")

    all_cpi_ranges = []
    all_cpi_dirs = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}

    for cat, cat_icon in [("HOT","🔥"), ("COLD","🧊"), ("IN LINE","➡️")]:
        items = by_category[cat]
        if not items:
            continue

        n = len(items)
        ranges = [r['cpi_day']['range'] for r in items if r['cpi_day']]
        changes = [r['cpi_day']['change_pts'] for r in items if r['cpi_day']]
        dirs = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
        for r in items:
            if r['cpi_day']:
                dirs[r['cpi_day']['direction']] += 1
                all_cpi_dirs[r['cpi_day']['direction']] += 1

        week_changes = [r['change_week_pts'] for r in items if r['change_week_pts'] is not None]
        next_changes = [r['next_day']['change_pts'] for r in items if r['next_day']]

        avg_range = round(np.mean(ranges), 1) if ranges else 0
        avg_chg   = round(np.mean(changes), 1) if changes else 0
        avg_week  = round(np.mean(week_changes), 1) if week_changes else 0
        avg_next  = round(np.mean(next_changes), 1) if next_changes else 0

        bull_pct = round(dirs['BULLISH'] / n * 100, 1)
        bear_pct = round(dirs['BEARISH'] / n * 100, 1)
        neut_pct = round(dirs['NEUTRAL'] / n * 100, 1)

        all_cpi_ranges.extend(ranges)

        print(f"\n  {cat_icon} {cat}  ({n} eventos)")
        print(f"  {'─'*50}")
        print(f"  Rango promedio día CPI     : {avg_range:>7.1f} pts  (normal: {avg_normal_range:.1f} pts, ×{avg_range/avg_normal_range:.2f})")
        print(f"  Cambio promedio día CPI    : {avg_chg:>+7.1f} pts")
        print(f"  Cambio promedio día +1     : {avg_next:>+7.1f} pts")
        print(f"  Cambio acumulado en 5 días : {avg_week:>+7.1f} pts")
        print(f"  Dirección día CPI → BULL {bull_pct:.0f}% | BEAR {bear_pct:.0f}% | NEUTRAL {neut_pct:.0f}%")

        # Distribución cambio día
        pos = sum(1 for c in changes if c > 30)
        neg = sum(1 for c in changes if c < -30)
        neu = n - pos - neg
        bar_pos = "█" * pos
        bar_neg = "█" * neg
        print(f"  Sube >30pts  : {pos}/{n} {bar_pos}")
        print(f"  Baja >30pts  : {neg}/{n} {bar_neg}")
        print(f"  Neutral      : {neu}/{n}")

    # ══════════════════════════════════════════════════════════════════════════
    #  COMPARACIÓN CPI vs DÍAS NORMALES
    # ══════════════════════════════════════════════════════════════════════════
    avg_cpi_range = round(np.mean(all_cpi_ranges), 1) if all_cpi_ranges else 0
    total_cpi = len([r for r in results if r['cpi_day']])

    print(f"\n{SEP}")
    print("  ⚡ COMPARACIÓN CPI vs DÍAS NORMALES")
    print(f"{SEP}")
    print(f"  Rango promedio días CPI     : {avg_cpi_range:.1f} pts")
    print(f"  Rango promedio días normales: {avg_normal_range:.1f} pts")
    print(f"  Multiplicador de volatilidad: ×{avg_cpi_range/avg_normal_range:.2f}")
    print(f"\n  Dirección días CPI (TODOS):")
    for d, icon in [("BULLISH","📈"), ("BEARISH","📉"), ("NEUTRAL","↔️")]:
        cnt = all_cpi_dirs[d]
        pct = round(cnt / total_cpi * 100, 1) if total_cpi else 0
        bar = "█" * int(pct / 4)
        print(f"  {icon} {d:<9}: {cnt:>2}/{total_cpi} ({pct:>5.1f}%) {bar}")

    n_dirs = sum(normal_dirs.values())
    print(f"\n  Dirección días NORMALES:")
    for d, icon in [("BULLISH","📈"), ("BEARISH","📉"), ("NEUTRAL","↔️")]:
        cnt = normal_dirs[d]
        pct = round(cnt / n_dirs * 100, 1) if n_dirs else 0
        bar = "█" * int(pct / 4)
        print(f"  {icon} {d:<9}: {cnt:>3}/{n_dirs} ({pct:>5.1f}%) {bar}")

    # ══════════════════════════════════════════════════════════════════════════
    #  CONCLUSIONES
    # ══════════════════════════════════════════════════════════════════════════
    print(f"\n{SEP}")
    print("  💡 CONCLUSIONES OPERATIVAS")
    print(f"{SEP}")

    hot_items   = [r for r in by_category["HOT"]     if r['cpi_day']]
    cold_items  = [r for r in by_category["COLD"]    if r['cpi_day']]
    line_items  = [r for r in by_category["IN LINE"] if r['cpi_day']]

    if hot_items:
        hot_bull = sum(1 for r in hot_items if r['cpi_day']['direction']=="BULLISH")
        hot_bear = sum(1 for r in hot_items if r['cpi_day']['direction']=="BEARISH")
        hot_pct  = round(hot_bear / len(hot_items) * 100, 1)
        print(f"\n  🔥 CPI HOT  → NQ BAJA el {hot_pct:.0f}% de las veces el mismo día")
        hot_w = [r['change_week_pts'] for r in hot_items if r['change_week_pts'] is not None]
        if hot_w:
            print(f"     Cambio promedio +5 días: {np.mean(hot_w):+.0f} pts")

    if cold_items:
        cold_bull = sum(1 for r in cold_items if r['cpi_day']['direction']=="BULLISH")
        cold_pct  = round(cold_bull / len(cold_items) * 100, 1)
        print(f"\n  🧊 CPI COLD → NQ SUBE el {cold_pct:.0f}% de las veces el mismo día")
        cold_w = [r['change_week_pts'] for r in cold_items if r['change_week_pts'] is not None]
        if cold_w:
            print(f"     Cambio promedio +5 días: {np.mean(cold_w):+.0f} pts")

    if line_items:
        line_ranges = [r['cpi_day']['range'] for r in line_items]
        print(f"\n  ➡️  CPI IN LINE → Rango promedio {np.mean(line_ranges):.0f} pts (menor volatilidad)")

    mult = avg_cpi_range / avg_normal_range if avg_normal_range else 1
    print(f"\n  📏 Los días CPI tienen {mult:.1f}x más rango que días normales.")
    if mult > 1.3:
        print(f"     → REDUCE TAMAÑO DE POSICIÓN o espera confirmación 15-30 min post-dato.")
    print(f"\n  🕐 Estrategia recomendada:")
    print(f"     1. NO entrar 30 min antes del dato (08:30 ET)")
    print(f"     2. Esperar primer cierre de 15min post-dato")
    print(f"     3. Si HOT → buscar SHORTS desde VAH / resistencia previa")
    print(f"     4. Si COLD → buscar LONGS desde VAL / soporte previo")
    print(f"     5. Si IN LINE → operar el setup del día normalmente")
    print(f"\n{SEP}")

    # ── GUARDAR JSON ──────────────────────────────────────────────────────────
    report = {
        "title": "Backtest CPI Impact en NQ",
        "total_cpi_events": total_cpi,
        "avg_cpi_range_pts": avg_cpi_range,
        "avg_normal_range_pts": avg_normal_range,
        "volatility_multiplier": round(mult, 2),
        "by_category": {
            cat: {
                "count": len(items),
                "avg_range": round(np.mean([r['cpi_day']['range'] for r in items if r['cpi_day']]), 1) if items else 0,
                "avg_change_day": round(np.mean([r['cpi_day']['change_pts'] for r in items if r['cpi_day']]), 1) if items else 0,
                "avg_change_5d": round(np.mean([r['change_week_pts'] for r in items if r['change_week_pts'] is not None]), 1) if items else 0,
                "bull_pct": round(sum(1 for r in items if r['cpi_day'] and r['cpi_day']['direction']=="BULLISH") / len(items) * 100, 1) if items else 0,
                "bear_pct": round(sum(1 for r in items if r['cpi_day'] and r['cpi_day']['direction']=="BEARISH") / len(items) * 100, 1) if items else 0,
            }
            for cat, items in by_category.items()
        },
        "all_events": [
            {
                "date": r['date'],
                "category": r['category'],
                "delta_vs_est": r['delta'],
                "yoy": r['yoy_actual'],
                "range_pts": r['cpi_day']['range'] if r['cpi_day'] else None,
                "change_pts": r['cpi_day']['change_pts'] if r['cpi_day'] else None,
                "direction": r['cpi_day']['direction'] if r['cpi_day'] else None,
                "change_5d_pts": r['change_week_pts'],
            }
            for r in results
        ]
    }

    out_path = "data/research/backtest_cpi_impact.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n  ✅ JSON guardado → {out_path}\n")


if __name__ == "__main__":
    run_cpi_backtest()
