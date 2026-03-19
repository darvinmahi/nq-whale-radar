"""
╔══════════════════════════════════════════════════════════════╗
║  BACKTEST · MIÉRCOLES NQ · 3 MESES                         ║
║  + Volume Profile (VAH / POC / VAL)                        ║
║    → Rango: Asia 18:00 → 09:20 NY (10 min antes apertura) ║
║  + EMA 200 (15min) al momento de apertura NY               ║
║  Datos: 15min intraday NQ futures                          ║
╚══════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict


# ── Calcula VAH / POC / VAL desde un DataFrame de precios ────────────
def calc_value_area(data: pd.DataFrame, bins: int = 100, va_pct: float = 0.70):
    """
    Devuelve (val, poc, vah) usando un histograma de precios (TPO-style).
    va_pct = porcentaje de tiempo que define el Value Area (70 % default).
    """
    all_prices = pd.concat([data['High'], data['Low'], data['Close']])
    if len(all_prices) < 5:
        mid = data['Close'].mean()
        return mid, mid, mid

    counts, edges = np.histogram(all_prices, bins=bins)
    bin_centers = (edges[:-1] + edges[1:]) / 2

    # POC = bin con más tiempo/precio
    poc_idx = int(np.argmax(counts))
    poc     = float(bin_centers[poc_idx])

    # Expandir desde el POC hasta cubrir 70 % del volumen
    total   = counts.sum()
    target  = total * va_pct
    lo_idx  = poc_idx
    hi_idx  = poc_idx
    current = int(counts[poc_idx])

    while current < target:
        lo_next = lo_idx - 1
        hi_next = hi_idx + 1
        lo_val  = counts[lo_next] if lo_next >= 0 else -1
        hi_val  = counts[hi_next] if hi_next < len(counts) else -1

        if lo_val <= 0 and hi_val <= 0:
            break
        if lo_val >= hi_val:
            current += int(lo_val)
            lo_idx = lo_next
        else:
            current += int(hi_val)
            hi_idx = hi_next

    val = float(bin_centers[lo_idx])
    vah = float(bin_centers[hi_idx])
    return val, poc, vah


# ── EMA 200 pre-calculada sobre todo el DataFrame ───────────────────
def get_ema200_series(df: pd.DataFrame) -> pd.Series:
    return df['Close'].ewm(span=200, adjust=False).mean()


# ── Verifica si el precio tocó un nivel durante la sesión NY ─────────
def level_touched(ny_data: pd.DataFrame, level: float, margin: float = 15.0) -> bool:
    return bool(((ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)).any())


# ── Fuerza de reacción tras tocar un nivel ───────────────────────────
def reaction_after_touch(ny_data: pd.DataFrame, level: float,
                         margin: float = 15.0) -> float:
    """Devuelve el movimiento máximo (en pts) que ocurrió DESPUÉS del primer toque."""
    touch_rows = ny_data[(ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)]
    if touch_rows.empty:
        return 0.0
    first_touch_time = touch_rows.index[0]
    after = ny_data.loc[first_touch_time:]
    if after.empty:
        return 0.0
    return float(after['High'].max() - after['Low'].min())


# ── Script principal ─────────────────────────────────────────────────
def run_wednesday_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print("❌ Data file not found:", csv_path)
        return

    # ── Cargar datos ──────────────────────────────────────────────
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    # ── Últimos 3 meses ───────────────────────────────────────────
    end_date   = df.index.max()
    start_date = end_date - timedelta(days=90)
    df_window  = df.loc[start_date:]

    # EMA 200 sobre TODO el histórico (necesita las 200 velas previas)
    ema200_full = get_ema200_series(df)

    days = df_window.index.normalize().unique()

    pattern_names = [
        "SWEEP_H_RETURN", "SWEEP_L_RETURN",
        "EXPANSION_H",    "EXPANSION_L",
        "ROTATION_POC",   "NEWS_DRIVE",
    ]

    # ── Colectores ────────────────────────────────────────────────
    all_days_results  = []
    wednesday_results = []
    patterns_all      = defaultdict(int)
    patterns_wed      = defaultdict(int)

    wed_ranges        = []
    wed_directions    = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    wed_sweep_times   = []
    wed_poc_hits      = 0
    wed_poc_reactions = 0

    # ── Colectores de niveles ─────────────────────────────────────
    # Profile
    vah_hits  = 0; vah_react_sum = 0.0
    poc_hits  = 0; poc_react_sum = 0.0
    val_hits  = 0; val_react_sum = 0.0
    # EMA 200
    ema_hits  = 0; ema_react_sum = 0.0
    ema_above = 0   # veces que NY abre POR ENCIMA de la EMA 200

    for day in days:
        # ── Rango Asia+Londres (para clasificar el patrón) ────────
        range_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        range_end   = day.replace(hour=8, minute=30)
        range_data  = df.loc[range_start:range_end]

        if range_data.empty or len(range_data) < 15:
            continue

        r_high  = range_data['High'].max()
        r_low   = range_data['Low'].min()
        r_range = r_high - r_low

        # ── Value Area Profile: Asia 18:00 → 09:20 NY ─────────────
        profile_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        profile_end   = day.replace(hour=9, minute=20)   # 10 min antes apertura
        profile_data  = df.loc[profile_start:profile_end]

        if profile_data.empty or len(profile_data) < 5:
            continue

        val, p_poc, vah = calc_value_area(profile_data)

        # ── EMA 200 al momento de apertura NY ─────────────────────
        ema_at_open = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])

        # ── NY Session ────────────────────────────────────────────
        ny_open_data = df.loc[
            day.replace(hour=9, minute=30): day.replace(hour=11, minute=30)
        ]
        ny_full = df.loc[
            day.replace(hour=9, minute=30): day.replace(hour=16, minute=0)
        ]

        if ny_open_data.empty or len(ny_open_data) < 3:
            continue

        ny_open  = float(ny_open_data.iloc[0]['Open'])
        ny_high  = float(ny_open_data['High'].max())
        ny_low   = float(ny_open_data['Low'].min())
        ny_close = float(ny_open_data.iloc[-1]['Close'])
        ny_range = ny_high - ny_low

        full_close = float(ny_full.iloc[-1]['Close']) if not ny_full.empty else ny_close

        # ── Patrón (vs rango Asia+Londres) ───────────────────────
        buffer = 20
        p_type = "ROTATION_POC"
        if ny_range > 250:
            p_type = "NEWS_DRIVE"
        elif ny_high > r_high + buffer:
            p_type = "SWEEP_H_RETURN" if ny_close < r_high else "EXPANSION_H"
        elif ny_low < r_low - buffer:
            p_type = "SWEEP_L_RETURN" if ny_close > r_low  else "EXPANSION_L"

        # ── Dirección ─────────────────────────────────────────────
        if full_close > ny_open + 30:
            direction = "BULLISH"
        elif full_close < ny_open - 30:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # ── Sweep time ────────────────────────────────────────────
        sweep_time = None
        if p_type == "SWEEP_H_RETURN":
            sc = ny_open_data[ny_open_data['High'] >= r_high + buffer]
            sweep_time = sc.index[0].strftime('%H:%M') if not sc.empty else None
        elif p_type == "SWEEP_L_RETURN":
            sc = ny_open_data[ny_open_data['Low'] <= r_low - buffer]
            sweep_time = sc.index[0].strftime('%H:%M') if not sc.empty else None

        # ── POC clásico (solo del rango, para comparar) ───────────
        prices_range = range_data['Close']
        bins_r = np.linspace(prices_range.min(), prices_range.max(),
                             max(10, min(40, len(prices_range))))
        cnts_r, edg_r = np.histogram(prices_range, bins=bins_r)
        c_poc_range = float(edg_r[np.argmax(cnts_r)])

        classic_poc_hit = level_touched(ny_open_data, c_poc_range)
        classic_react   = reaction_after_touch(ny_open_data, c_poc_range) if classic_poc_hit else 0

        # ── Almacenar resultado ───────────────────────────────────
        day_result = {
            "date":         day.strftime('%Y-%m-%d'),
            "weekday":      day.strftime('%A'),
            "weekday_num":  day.weekday(),
            "pattern":      p_type,
            "direction":    direction,
            "range_asia_lon": round(r_range, 1),
            "ny_range":     round(ny_range, 1),
            "ny_open":      round(ny_open, 2),
            "ny_close":     round(ny_close, 2),
            "full_close":   round(full_close, 2),
            "r_high":       round(r_high, 2),
            "r_low":        round(r_low, 2),
            # --- Profile Value Area ---
            "profile_val":  round(val, 2),
            "profile_poc":  round(p_poc, 2),
            "profile_vah":  round(vah, 2),
            # --- EMA 200 ---
            "ema200":       round(ema_at_open, 2),
            "open_vs_ema":  round(ny_open - ema_at_open, 1),
            "sweep_time":   sweep_time,
            "poc_hit":      classic_poc_hit,
        }

        all_days_results.append(day_result)
        patterns_all[p_type] += 1

        # ── MIÉRCOLES únicamente ──────────────────────────────────
        if day.weekday() == 2:
            wednesday_results.append(day_result)
            patterns_wed[p_type] += 1
            wed_ranges.append(ny_range)
            wed_directions[direction] += 1
            if sweep_time:
                wed_sweep_times.append(sweep_time)
            if classic_poc_hit:
                wed_poc_hits += 1
                if classic_react > 50:
                    wed_poc_reactions += 1

            # -- Level stats --
            MARGIN = 20   # pts de margen para considerar "tocó el nivel"

            # VAH
            if level_touched(ny_open_data, vah, MARGIN):
                vah_hits += 1
                vah_react_sum += reaction_after_touch(ny_open_data, vah, MARGIN)

            # Profile POC
            if level_touched(ny_open_data, p_poc, MARGIN):
                poc_hits += 1
                poc_react_sum += reaction_after_touch(ny_open_data, p_poc, MARGIN)

            # VAL
            if level_touched(ny_open_data, val, MARGIN):
                val_hits += 1
                val_react_sum += reaction_after_touch(ny_open_data, val, MARGIN)

            # EMA 200
            if level_touched(ny_open_data, ema_at_open, MARGIN):
                ema_hits += 1
                ema_react_sum += reaction_after_touch(ny_open_data, ema_at_open, MARGIN)

            if ny_open > ema_at_open:
                ema_above += 1

    # ══════════════════════════════════════════════════════════════
    #  ANÁLISIS
    # ══════════════════════════════════════════════════════════════
    total_all = len(all_days_results)
    total_wed = len(wednesday_results)

    if total_wed == 0:
        print("❌ No Wednesday data found in the last 3 months")
        return

    pct_all = {k: round(v / total_all * 100, 1) for k, v in patterns_all.items()}
    pct_wed = {k: round(v / total_wed * 100, 1) for k, v in patterns_wed.items()}

    dominant_wed = max(patterns_wed, key=patterns_wed.get)
    dominant_pct = pct_wed[dominant_wed]

    avg_wed_range = round(np.mean(wed_ranges), 1) if wed_ranges else 0
    max_wed_range = round(max(wed_ranges), 1)      if wed_ranges else 0
    min_wed_range = round(min(wed_ranges), 1)      if wed_ranges else 0

    sweep_time_counts = defaultdict(int)
    for t in wed_sweep_times:
        h = t.split(':')[0]
        sweep_time_counts[f"{h}:00-{h}:59"] += 1

    # ══════════════════════════════════════════════════════════════
    #  REPORTE
    # ══════════════════════════════════════════════════════════════
    print("\n" + "═" * 72)
    print("  🔬 BACKTEST MIÉRCOLES · NQ NASDAQ · ÚLTIMOS 3 MESES")
    print("═" * 72)
    print(f"  📅 Periodo: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  📊 Total días analizados: {total_all}")
    print(f"  📌 Miércoles analizados:  {total_wed}")

    # -- Patrones --
    print("\n" + "─" * 72)
    print("  📊 LOS 6 PATRONES (MIÉRCOLES vs TODOS LOS DÍAS)")
    print("─" * 72)
    print(f"  {'PATRÓN':<22} {'MIÉRCOLES':>11} {'TODOS':>9} {'DELTA':>9}")
    print("  " + "─" * 54)
    for p in pattern_names:
        w = pct_wed.get(p, 0)
        a = pct_all.get(p, 0)
        d = round(w - a, 1)
        ds = f"+{d}" if d > 0 else str(d)
        mk = " ◀ DOMINANTE" if p == dominant_wed else ""
        print(f"  {p:<22} {w:>9.1f}% {a:>8.1f}% {ds:>8}%{mk}")

    print(f"\n  🏆 DOMINANTE: {dominant_wed}  ({dominant_pct}%)")

    # -- Dirección --
    print("\n" + "─" * 72)
    print("  📈 DIRECCIÓN")
    print("─" * 72)
    for d, cnt in wed_directions.items():
        pct = round(cnt / total_wed * 100, 1)
        bar = "█" * int(pct / 3)
        print(f"  {d:<10} {cnt:>3}  ({pct:>5.1f}%)  {bar}")

    # -- Rango --
    print(f"\n  📏 RANGO NY — Prom: {avg_wed_range} pts | Máx: {max_wed_range} | Mín: {min_wed_range}")

    # -- Sweep times --
    if wed_sweep_times:
        print("\n" + "─" * 72)
        print("  ⏰ HORA DEL SWEEP")
        print("─" * 72)
        for window, cnt in sorted(sweep_time_counts.items()):
            print(f"  {window}: {cnt} sweeps")

    # ──────────────────────────────────────────────────────────────
    # SECCIÓN NUEVA: VALUE AREA PROFILE + EMA 200
    # ──────────────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print("  📐 VOLUME PROFILE VALUE AREA  (Asia 18:00 → 09:20 NY)")
    print("     Nivel más importante del día · 70% del tiempo de precio")
    print("═" * 72)

    def level_row(name, hits, react_sum, total):
        hit_pct  = round(hits / total * 100, 1) if total else 0
        avg_react = round(react_sum / hits, 1) if hits else 0
        bar = "█" * int(hit_pct / 5)
        print(f"  {name:<12} tocado {hits:>2}/{total}  ({hit_pct:>5.1f}%)  "
              f"reacción prom: {avg_react:>6.1f} pts  {bar}")

    level_row("VAH (top)",  vah_hits, vah_react_sum, total_wed)
    level_row("POC (clave)", poc_hits, poc_react_sum, total_wed)
    level_row("VAL (base)", val_hits, val_react_sum, total_wed)

    print("\n" + "─" * 72)
    print("  📉 EMA 200  (15 min) al momento de apertura NY 09:30")
    print("─" * 72)
    ema_pct   = round(ema_hits / total_wed * 100, 1) if total_wed else 0
    ema_avg_r = round(ema_react_sum / ema_hits, 1)   if ema_hits else 0
    above_pct = round(ema_above / total_wed * 100, 1)
    below_pct = round((total_wed - ema_above) / total_wed * 100, 1)
    print(f"  Precio toca EMA200: {ema_hits}/{total_wed}  ({ema_pct}%)  |  "
          f"Reacción prom tras toque: {ema_avg_r} pts")
    print(f"  NY abre SOBRE  EMA200: {ema_above}/{total_wed}  ({above_pct}%)  "
          f"→ sesiones alcistas")
    print(f"  NY abre DEBAJO EMA200: {total_wed - ema_above}/{total_wed}  ({below_pct}%)  "
          f"→ sesiones bajistas")

    # -- Detalle por miércoles --
    print("\n" + "─" * 72)
    print("  📋 DETALLE CADA MIÉRCOLES")
    print("─" * 72)
    print(f"  {'FECHA':<12} {'PATRÓN':<20} {'DIR':<9} "
          f"{'VAL':>7} {'POC':>7} {'VAH':>7} {'EMA200':>7} {'RANGO':>7}")
    print("  " + "─" * 68)
    for r in wednesday_results:
        print(
            f"  {r['date']:<12} {r['pattern']:<20} {r['direction']:<9} "
            f"{r['profile_val']:>7.0f} {r['profile_poc']:>7.0f} "
            f"{r['profile_vah']:>7.0f} {r['ema200']:>7.0f} "
            f"{r['ny_range']:>6.0f}pts"
        )

    # -- Conclusión --
    print("\n" + "═" * 72)
    print("  💡 CONCLUSIÓN")
    print("═" * 72)

    best_level = max(
        [("VAH", vah_hits, vah_react_sum),
         ("POC", poc_hits, poc_react_sum),
         ("VAL", val_hits, val_react_sum),
         ("EMA200", ema_hits, ema_react_sum)],
        key=lambda x: (x[1], x[2])
    )

    if dominant_wed == "NEWS_DRIVE":
        print(f"  ⚡ Los MIÉRCOLES son días de ALTO RANGO ({avg_wed_range} pts prom).")
        print(f"     Patrón DOMINANTE: NEWS_DRIVE ({dominant_pct}%) — reducir tamaño.")
    elif dominant_wed in ["SWEEP_H_RETURN", "SWEEP_L_RETURN"]:
        print(f"  🎯 Los MIÉRCOLES tienden al SWEEP & RETURN ({dominant_pct}%).")
        print(f"     Estrategia: esperar el barrido y entrar en contra.")
    elif dominant_wed in ["EXPANSION_H", "EXPANSION_L"]:
        print(f"  🚀 Los MIÉRCOLES tienden a EXPANSIÓN ({dominant_pct}%).")
        print(f"     Estrategia: seguir la ruptura del rango.")
    else:
        print(f"  🔄 Los MIÉRCOLES rotan alrededor del POC ({dominant_pct}%).")

    print(f"\n  🔑 NIVEL MÁS RESPETADO: {best_level[0]}")
    print(f"     Tocado {best_level[1]}/{total_wed} miércoles  |  "
          f"Reacción prom: {round(best_level[2]/best_level[1], 1) if best_level[1] else 0} pts")
    print("═" * 72)

    # ── Guardar JSON ──────────────────────────────────────────────
    report = {
        "title":            "Backtest Miércoles NQ · 3 Meses + Profile + EMA200",
        "period":           f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "total_days":       total_all,
        "total_wednesdays": total_wed,
        "dominant_pattern": dominant_wed,
        "dominant_pct":     dominant_pct,
        "patterns_wednesday": {k: f"{v:.1f}%" for k, v in pct_wed.items()},
        "patterns_all_days":  {k: f"{v:.1f}%" for k, v in pct_all.items()},
        "direction_wednesday": wed_directions,
        "avg_ny_range_wednesday": avg_wed_range,
        "value_area_profile": {
            "vah": {"hit_rate": f"{round(vah_hits/total_wed*100,1) if total_wed else 0}%",
                    "avg_reaction_pts": round(vah_react_sum/vah_hits, 1) if vah_hits else 0},
            "poc": {"hit_rate": f"{round(poc_hits/total_wed*100,1) if total_wed else 0}%",
                    "avg_reaction_pts": round(poc_react_sum/poc_hits, 1) if poc_hits else 0},
            "val": {"hit_rate": f"{round(val_hits/total_wed*100,1) if total_wed else 0}%",
                    "avg_reaction_pts": round(val_react_sum/val_hits, 1) if val_hits else 0},
        },
        "ema200": {
            "hit_rate":        f"{ema_pct}%",
            "avg_reaction_pts": ema_avg_r,
            "open_above_ema_pct": above_pct,
            "open_below_ema_pct": below_pct,
        },
        "all_wednesdays": wednesday_results,
    }

    output_path = "data/research/backtest_wednesday_3m.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n  ✅ Guardado → {output_path}")


if __name__ == "__main__":
    run_wednesday_backtest()
