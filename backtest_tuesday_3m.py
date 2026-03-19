"""
╔══════════════════════════════════════════════════════════════╗
║  BACKTEST · LUNES & MARTES NQ · 3 MESES                    ║
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


# ── Value Area: VAL / POC / VAH ──────────────────────────────────────
def calc_value_area(data: pd.DataFrame, bins: int = 100, va_pct: float = 0.70):
    all_prices = pd.concat([data['High'], data['Low'], data['Close']])
    if len(all_prices) < 5:
        mid = float(data['Close'].mean())
        return mid, mid, mid
    counts, edges = np.histogram(all_prices, bins=bins)
    bin_centers = (edges[:-1] + edges[1:]) / 2
    poc_idx = int(np.argmax(counts))
    poc     = float(bin_centers[poc_idx])
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
    return float(bin_centers[lo_idx]), poc, float(bin_centers[hi_idx])


def get_ema200_series(df: pd.DataFrame) -> pd.Series:
    return df['Close'].ewm(span=200, adjust=False).mean()


def level_touched(ny_data: pd.DataFrame, level: float, margin: float = 15.0) -> bool:
    return bool(((ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)).any())


def reaction_after_touch(ny_data: pd.DataFrame, level: float, margin: float = 15.0) -> float:
    rows = ny_data[(ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)]
    if rows.empty:
        return 0.0
    after = ny_data.loc[rows.index[0]:]
    return float(after['High'].max() - after['Low'].min()) if not after.empty else 0.0


# ── Función para analizar UN día de la semana ────────────────────────
def analyze_day(day_name_es: str, day_num: int,
                all_results: list, target_results: list,
                patterns_all: dict, patterns_day: dict):
    """Imprime el reporte completo para el día indicado."""
    total_all = len(all_results)
    total_day = len(target_results)

    if total_day == 0:
        print(f"❌ Sin datos para {day_name_es}")
        return {}

    pattern_names = [
        "SWEEP_H_RETURN", "SWEEP_L_RETURN",
        "EXPANSION_H",    "EXPANSION_L",
        "ROTATION_POC",   "NEWS_DRIVE",
    ]

    pct_all = {k: round(v / total_all * 100, 1) for k, v in patterns_all.items()}
    pct_day = {k: round(v / total_day * 100, 1) for k, v in patterns_day.items()}
    dominant = max(patterns_day, key=patterns_day.get)
    dom_pct  = pct_day[dominant]

    ranges     = [r['ny_range']  for r in target_results]
    directions = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    for r in target_results:
        directions[r['direction']] += 1

    sweep_times = [r['sweep_time'] for r in target_results if r['sweep_time']]
    sweep_hours = defaultdict(int)
    for t in sweep_times:
        h = t.split(':')[0]
        sweep_hours[f"{h}:00-{h}:59"] += 1

    # Nivel stats
    vah_hits  = sum(1 for r in target_results if r.get('vah_hit'))
    vah_react = sum(r.get('vah_react', 0) for r in target_results)
    poc_hits  = sum(1 for r in target_results if r.get('profile_poc_hit'))
    poc_react = sum(r.get('profile_poc_react', 0) for r in target_results)
    val_hits  = sum(1 for r in target_results if r.get('val_hit'))
    val_react = sum(r.get('val_react', 0) for r in target_results)
    ema_hits  = sum(1 for r in target_results if r.get('ema_hit'))
    ema_react = sum(r.get('ema_react', 0) for r in target_results)
    ema_above = sum(1 for r in target_results if r.get('ema_above'))

    avg_range = round(np.mean(ranges), 1) if ranges else 0
    max_range = round(max(ranges), 1)     if ranges else 0
    min_range = round(min(ranges), 1)     if ranges else 0

    # ── PRINT ─────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print(f"  🔬 BACKTEST {day_name_es} · NQ NASDAQ · ÚLTIMOS 3 MESES")
    print("═" * 72)
    print(f"  📌 Sesiones analizadas: {total_day}")

    print("\n" + "─" * 72)
    print(f"  📊 LOS 6 PATRONES ({day_name_es} vs TODOS LOS DÍAS)")
    print("─" * 72)
    print(f"  {'PATRÓN':<22} {day_name_es[:6]:>9} {'TODOS':>9} {'DELTA':>9}")
    print("  " + "─" * 54)
    for p in pattern_names:
        w  = pct_day.get(p, 0)
        a  = pct_all.get(p, 0)
        d  = round(w - a, 1)
        ds = f"+{d}" if d > 0 else str(d)
        mk = " ◀ DOMINANTE" if p == dominant else ""
        print(f"  {p:<22} {w:>8.1f}% {a:>8.1f}% {ds:>8}%{mk}")

    print(f"\n  🏆 DOMINANTE: {dominant}  ({dom_pct}%)")

    print("\n" + "─" * 72)
    print("  📈 DIRECCIÓN")
    print("─" * 72)
    for d, cnt in directions.items():
        pct = round(cnt / total_day * 100, 1)
        bar = "█" * int(pct / 3)
        print(f"  {d:<10} {cnt:>3}  ({pct:>5.1f}%)  {bar}")

    print(f"\n  📏 RANGO NY — Prom: {avg_range} pts | Máx: {max_range} | Mín: {min_range}")

    if sweep_times:
        print("\n" + "─" * 72)
        print("  ⏰ HORA DEL SWEEP")
        print("─" * 72)
        for w, cnt in sorted(sweep_hours.items()):
            print(f"  {w}: {cnt} sweeps")

    # Value Area
    print("\n" + "═" * 72)
    print(f"  📐 VOLUME PROFILE VALUE AREA  (Asia 18:00 → 09:20 NY)")
    print("═" * 72)

    def lvl_row(name, hits, react, total):
        hp = round(hits / total * 100, 1) if total else 0
        ar = round(react / hits, 1) if hits else 0
        bar = "█" * int(hp / 5)
        print(f"  {name:<14} {hits:>2}/{total}  ({hp:>5.1f}%)  reacción prom: {ar:>6.1f} pts  {bar}")

    lvl_row("VAH (techo)",   vah_hits, vah_react, total_day)
    lvl_row("POC (centro)",  poc_hits, poc_react, total_day)
    lvl_row("VAL (base)",    val_hits, val_react, total_day)

    print("\n" + "─" * 72)
    print("  📉 EMA 200  (15 min) al momento de apertura NY 09:30")
    print("─" * 72)
    ep  = round(ema_hits / total_day * 100, 1)
    ear = round(ema_react / ema_hits, 1) if ema_hits else 0
    abp = round(ema_above / total_day * 100, 1)
    blp = round((total_day - ema_above) / total_day * 100, 1)
    print(f"  Toca EMA200:       {ema_hits}/{total_day}  ({ep}%)  | Reacción prom: {ear} pts")
    print(f"  Abre SOBRE  EMA200: {ema_above}/{total_day}  ({abp}%)  → contexto alcista")
    print(f"  Abre DEBAJO EMA200: {total_day - ema_above}/{total_day}  ({blp}%)  → contexto bajista")

    # Detalle
    print("\n" + "─" * 72)
    print("  📋 DETALLE CADA SESIÓN")
    print("─" * 72)
    print(f"  {'FECHA':<12} {'PATRÓN':<20} {'DIR':<9} "
          f"{'VAL':>7} {'POC':>7} {'VAH':>7} {'EMA200':>7} {'RANGO':>7}")
    print("  " + "─" * 70)
    for r in target_results:
        print(
            f"  {r['date']:<12} {r['pattern']:<20} {r['direction']:<9} "
            f"{r['profile_val']:>7.0f} {r['profile_poc']:>7.0f} "
            f"{r['profile_vah']:>7.0f} {r['ema200']:>7.0f} "
            f"{r['ny_range']:>6.0f}pts"
        )

    # Conclusión
    best = max(
        [("VAH", vah_hits, vah_react), ("POC", poc_hits, poc_react),
         ("VAL", val_hits, val_react), ("EMA200", ema_hits, ema_react)],
        key=lambda x: (x[1], x[2])
    )
    print("\n" + "═" * 72)
    print("  💡 CONCLUSIÓN")
    print("═" * 72)
    if dominant == "NEWS_DRIVE":
        print(f"  ⚡ Alta volatilidad — NEWS_DRIVE {dom_pct}% | Rango prom {avg_range} pts")
    elif dominant in ["SWEEP_H_RETURN", "SWEEP_L_RETURN"]:
        print(f"  🎯 SWEEP & RETURN dominante ({dom_pct}%) — entrada en contra del sweep")
    elif dominant in ["EXPANSION_H", "EXPANSION_L"]:
        print(f"  🚀 EXPANSIÓN dominante ({dom_pct}%) — seguir la ruptura")
    else:
        print(f"  🔄 ROTACIÓN POC dominante ({dom_pct}%) — scalp interno")

    best_react = round(best[2] / best[1], 1) if best[1] else 0
    print(f"  🔑 NIVEL MÁS RESPETADO: {best[0]}  "
          f"({best[1]}/{total_day} sesiones | reacción prom: {best_react} pts)")
    print("═" * 72)

    return {
        "total_sessions": total_day,
        "dominant_pattern": dominant,
        "dominant_pct": dom_pct,
        "patterns": {k: f"{v:.1f}%" for k, v in pct_day.items()},
        "direction": directions,
        "avg_ny_range": avg_range,
        "value_area": {
            "vah": {"hit_rate": f"{round(vah_hits/total_day*100,1) if total_day else 0}%",
                    "avg_reaction": round(vah_react/vah_hits, 1) if vah_hits else 0},
            "poc": {"hit_rate": f"{round(poc_hits/total_day*100,1) if total_day else 0}%",
                    "avg_reaction": round(poc_react/poc_hits, 1) if poc_hits else 0},
            "val": {"hit_rate": f"{round(val_hits/total_day*100,1) if total_day else 0}%",
                    "avg_reaction": round(val_react/val_hits, 1) if val_hits else 0},
        },
        "ema200": {
            "hit_rate": f"{ep}%",
            "avg_reaction": ear,
            "open_above_pct": abp,
            "open_below_pct": blp,
        },
        "sessions": target_results,
    }


# ── Main ─────────────────────────────────────────────────────────────
def run_mon_tue_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print("❌ Data file not found:", csv_path)
        return

    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    end_date   = df.index.max()
    start_date = end_date - timedelta(days=90)
    df_window  = df.loc[start_date:]

    ema200_full = get_ema200_series(df)   # sobre TODO el histórico
    days = df_window.index.normalize().unique()

    # Colectores
    all_results = []
    mon_results = []
    tue_results = []
    patterns_all = defaultdict(int)
    patterns_mon = defaultdict(int)
    patterns_tue = defaultdict(int)

    MARGIN = 20

    for day in days:
        wd = day.weekday()
        if wd not in (0, 1):       # solo Lunes y Martes
            # aun así acumulamos "todos" para el delta
            pass

        # ── Rango Asia+Londres (para patrón) ─────────────────────
        r_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        r_end   = day.replace(hour=8, minute=30)
        rdata   = df.loc[r_start:r_end]
        if rdata.empty or len(rdata) < 15:
            continue

        r_high  = rdata['High'].max()
        r_low   = rdata['Low'].min()
        r_range = r_high - r_low

        # ── Value Area Profile: Asia 18:00 → 09:20 NY ────────────
        p_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        p_end   = day.replace(hour=9, minute=20)
        pdata   = df.loc[p_start:p_end]
        if pdata.empty or len(pdata) < 5:
            continue
        val, p_poc, vah = calc_value_area(pdata)

        # ── EMA 200 al open ───────────────────────────────────────
        ema_at_open = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])

        # ── Sesiones NY ───────────────────────────────────────────
        ny_od = df.loc[day.replace(hour=9, minute=30): day.replace(hour=11, minute=30)]
        ny_fl = df.loc[day.replace(hour=9, minute=30): day.replace(hour=16, minute=0)]
        if ny_od.empty or len(ny_od) < 3:
            continue

        ny_open  = float(ny_od.iloc[0]['Open'])
        ny_high  = float(ny_od['High'].max())
        ny_low   = float(ny_od['Low'].min())
        ny_range = ny_high - ny_low
        full_close = float(ny_fl.iloc[-1]['Close']) if not ny_fl.empty else float(ny_od.iloc[-1]['Close'])

        # ── Patrón ───────────────────────────────────────────────
        buf    = 20
        p_type = "ROTATION_POC"
        if ny_range > 250:
            p_type = "NEWS_DRIVE"
        elif ny_high > r_high + buf:
            p_type = "SWEEP_H_RETURN" if float(ny_od.iloc[-1]['Close']) < r_high else "EXPANSION_H"
        elif ny_low < r_low - buf:
            p_type = "SWEEP_L_RETURN" if float(ny_od.iloc[-1]['Close']) > r_low  else "EXPANSION_L"

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
            sc = ny_od[ny_od['High'] >= r_high + buf]
            sweep_time = sc.index[0].strftime('%H:%M') if not sc.empty else None
        elif p_type == "SWEEP_L_RETURN":
            sc = ny_od[ny_od['Low'] <= r_low - buf]
            sweep_time = sc.index[0].strftime('%H:%M') if not sc.empty else None

        # ── Nivel hits ────────────────────────────────────────────
        vah_hit   = level_touched(ny_od, vah,        MARGIN)
        poc_hit   = level_touched(ny_od, p_poc,      MARGIN)
        val_hit   = level_touched(ny_od, val,        MARGIN)
        ema_hit   = level_touched(ny_od, ema_at_open, MARGIN)

        row = {
            "date":            day.strftime('%Y-%m-%d'),
            "weekday":         day.strftime('%A'),
            "weekday_num":     wd,
            "pattern":         p_type,
            "direction":       direction,
            "range_asia_lon":  round(r_range, 1),
            "ny_range":        round(ny_range, 1),
            "ny_open":         round(ny_open, 2),
            "full_close":      round(full_close, 2),
            "r_high":          round(r_high, 2),
            "r_low":           round(r_low, 2),
            "profile_val":     round(val, 2),
            "profile_poc":     round(p_poc, 2),
            "profile_vah":     round(vah, 2),
            "ema200":          round(ema_at_open, 2),
            "open_vs_ema":     round(ny_open - ema_at_open, 1),
            "sweep_time":      sweep_time,
            "vah_hit":         vah_hit,
            "vah_react":       reaction_after_touch(ny_od, vah, MARGIN)   if vah_hit else 0.0,
            "profile_poc_hit": poc_hit,
            "profile_poc_react": reaction_after_touch(ny_od, p_poc, MARGIN) if poc_hit else 0.0,
            "val_hit":         val_hit,
            "val_react":       reaction_after_touch(ny_od, val, MARGIN)   if val_hit else 0.0,
            "ema_hit":         ema_hit,
            "ema_react":       reaction_after_touch(ny_od, ema_at_open, MARGIN) if ema_hit else 0.0,
            "ema_above":       ny_open > ema_at_open,
        }

        all_results.append(row)
        patterns_all[p_type] += 1

        if wd == 0:
            mon_results.append(row)
            patterns_mon[p_type] += 1
        elif wd == 1:
            tue_results.append(row)
            patterns_tue[p_type] += 1

    # ── Reporte ───────────────────────────────────────────────────
    print(f"\n📅 Periodo: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"Total sesiones: {len(all_results)}")

    mon_report = analyze_day("LUNES",  0, all_results, mon_results, patterns_all, patterns_mon)
    tue_report = analyze_day("MARTES", 1, all_results, tue_results, patterns_all, patterns_tue)

    # ── Guardar JSON ──────────────────────────────────────────────
    report = {
        "title":   "Backtest Lunes & Martes NQ · 3 Meses + Profile + EMA200",
        "period":  f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "total_sessions": len(all_results),
        "LUNES":   mon_report,
        "MARTES":  tue_report,
    }

    for path in ["data/research/backtest_mon_tue_3m.json",
                 "data/research/backtest_tuesday_3m.json"]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n  ✅ Guardado → data/research/backtest_mon_tue_3m.json")


if __name__ == "__main__":
    run_mon_tue_backtest()
