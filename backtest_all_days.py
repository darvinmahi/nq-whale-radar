"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  BACKTEST UNIFICADO · NQ NASDAQ · TODOS LOS DÍAS                            ║
║  ────────────────────────────────────────────────────────────────────────── ║
║  Mismo estudio aplicado a cada día de la semana por separado:               ║
║    • Volume Profile (VAH / POC / VAL)  — Asia 18:00 → 09:20 NY             ║
║    • EMA 200 (15 min) al momento de apertura NY 09:30                       ║
║    • 6 patrones ICT: SWEEP_H/L_RETURN, EXPANSION_H/L,                      ║
║                       ROTATION_POC, NEWS_DRIVE                              ║
║    • Dirección de sesión (BULLISH / BEARISH / NEUTRAL)                      ║
║    • Rango NY (09:30 → 16:00)                                               ║
║    • Hora del sweep                                                          ║
║    • Niveles hit + reacción promedio                                         ║
║                                                                             ║
║  Uso:                                                                       ║
║    python backtest_all_days.py              → últimos 365 días              ║
║    python backtest_all_days.py --days 90   → últimos 90 días                ║
║    python backtest_all_days.py --day lun   → solo analiza Lunes             ║
║                                                                             ║
║  Salida: data/research/backtest_all_days.json                               ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json
import os
import argparse
from datetime import datetime, timedelta
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────────────────
CSV_PATH    = "data/research/nq_15m_intraday.csv"
OUTPUT_JSON = "data/research/backtest_all_days.json"
MARGIN      = 20          # margen en puntos para considerar "toca" un nivel
BUF         = 20          # buffer para distinguir sweep vs expansión
NY_RANGE_NEWS_THRESHOLD = 250   # rango > 250 pts = NEWS_DRIVE

DAY_NAMES = {
    0: {"en": "Monday",    "es": "LUNES"},
    1: {"en": "Tuesday",   "es": "MARTES"},
    2: {"en": "Wednesday", "es": "MIÉRCOLES"},
    3: {"en": "Thursday",  "es": "JUEVES"},
    4: {"en": "Friday",    "es": "VIERNES"},
}

DAY_ALIAS = {
    "lun": 0, "monday": 0,    "mon": 0,
    "mar": 1, "tuesday": 1,   "tue": 1,
    "mie": 2, "wednesday": 2, "wed": 2, "mié": 2,
    "jue": 3, "thursday": 3,  "thu": 3,
    "vie": 4, "friday": 4,    "fri": 4,
}

PATTERN_NAMES = [
    "SWEEP_H_RETURN", "SWEEP_L_RETURN",
    "EXPANSION_H",    "EXPANSION_L",
    "ROTATION_POC",   "NEWS_DRIVE",
]


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIONES DE ANÁLISIS
# ─────────────────────────────────────────────────────────────────────────────

def calc_value_area(data: pd.DataFrame, bins: int = 100, va_pct: float = 0.70):
    """Calcula VAL / POC / VAH del rango dado."""
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


def get_ema200(df: pd.DataFrame) -> pd.Series:
    return df['Close'].ewm(span=200, adjust=False).mean()


def level_touched(data: pd.DataFrame, level: float, margin: float = MARGIN) -> bool:
    return bool(((data['Low'] <= level + margin) & (data['High'] >= level - margin)).any())


def reaction_after_touch(data: pd.DataFrame, level: float, margin: float = MARGIN) -> float:
    rows = data[(data['Low'] <= level + margin) & (data['High'] >= level - margin)]
    if rows.empty:
        return 0.0
    after = data.loc[rows.index[0]:]
    return float(after['High'].max() - after['Low'].min()) if not after.empty else 0.0


def classify_pattern(ny_od, r_high, r_low, ny_range) -> str:
    """Clasifica el patrón ICT del día."""
    if ny_range > NY_RANGE_NEWS_THRESHOLD:
        return "NEWS_DRIVE"
    ny_high = float(ny_od['High'].max())
    ny_low  = float(ny_od['Low'].min())
    if ny_high > r_high + BUF:
        return "SWEEP_H_RETURN" if float(ny_od.iloc[-1]['Close']) < r_high else "EXPANSION_H"
    if ny_low < r_low - BUF:
        return "SWEEP_L_RETURN" if float(ny_od.iloc[-1]['Close']) > r_low  else "EXPANSION_L"
    return "ROTATION_POC"


def classify_direction(full_close, ny_open, threshold=30) -> str:
    if full_close > ny_open + threshold:
        return "BULLISH"
    if full_close < ny_open - threshold:
        return "BEARISH"
    return "NEUTRAL"


def get_sweep_time(ny_od, pattern, r_high, r_low) -> str | None:
    if pattern == "SWEEP_H_RETURN":
        sc = ny_od[ny_od['High'] >= r_high + BUF]
        return sc.index[0].strftime('%H:%M') if not sc.empty else None
    if pattern == "SWEEP_L_RETURN":
        sc = ny_od[ny_od['Low'] <= r_low - BUF]
        return sc.index[0].strftime('%H:%M') if not sc.empty else None
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  ANÁLISIS DE UN DÍA
# ─────────────────────────────────────────────────────────────────────────────

def analyze_day(day_num: int, day_results: list, all_results: list,
                patterns_day: dict, patterns_all: dict) -> dict:
    """Genera el reporte completo para un día de la semana."""
    day_es   = DAY_NAMES[day_num]["es"]
    total_d  = len(day_results)
    total_a  = len(all_results)

    if total_d == 0:
        print(f"\n  ⚠️  Sin datos para {day_es}")
        return {}

    pct_all = {k: round(v / total_a * 100, 1) if total_a else 0 for k, v in patterns_all.items()}
    pct_day = {k: round(v / total_d * 100, 1) if total_d else 0 for k, v in patterns_day.items()}
    dominant = max(patterns_day, key=patterns_day.get) if patterns_day else "N/A"
    dom_pct  = pct_day.get(dominant, 0)

    ranges     = [r['ny_range'] for r in day_results]
    directions = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    for r in day_results:
        directions[r['direction']] += 1

    sweep_times = [r['sweep_time'] for r in day_results if r['sweep_time']]
    sweep_hours = defaultdict(int)
    for t in sweep_times:
        h = t.split(':')[0]
        sweep_hours[f"{h}:00-{h}:59"] += 1

    vah_hits  = sum(1 for r in day_results if r.get('vah_hit'))
    vah_react = sum(r.get('vah_react', 0) for r in day_results)
    poc_hits  = sum(1 for r in day_results if r.get('poc_hit'))
    poc_react = sum(r.get('poc_react', 0) for r in day_results)
    val_hits  = sum(1 for r in day_results if r.get('val_hit'))
    val_react = sum(r.get('val_react', 0) for r in day_results)
    ema_hits  = sum(1 for r in day_results if r.get('ema_hit'))
    ema_react = sum(r.get('ema_react', 0) for r in day_results)
    ema_above = sum(1 for r in day_results if r.get('ema_above'))

    avg_range = round(float(np.mean(ranges)), 1) if ranges else 0
    max_range = round(float(max(ranges)), 1)      if ranges else 0
    min_range = round(float(min(ranges)), 1)      if ranges else 0

    # ── PRINT ─────────────────────────────────────────────────────────────────
    print("\n" + "═" * 72)
    print(f"  🔬 {day_es} · NQ NASDAQ · {total_d} sesiones")
    print("═" * 72)

    print(f"\n  {'PATRÓN':<22} {'DÍA':>8} {'TODOS':>8} {'DELTA':>8}")
    print("  " + "─" * 54)
    for p in PATTERN_NAMES:
        w  = pct_day.get(p, 0)
        a  = pct_all.get(p, 0)
        d  = round(w - a, 1)
        ds = f"+{d}" if d > 0 else str(d)
        mk = " ◀ DOM." if p == dominant else ""
        print(f"  {p:<22} {w:>7.1f}% {a:>7.1f}% {ds:>7}%{mk}")
    print(f"\n  🏆 DOMINANTE: {dominant}  ({dom_pct}%)")

    print("\n  📈 DIRECCIÓN")
    for d, cnt in directions.items():
        pct = round(cnt / total_d * 100, 1)
        bar = "█" * int(pct / 3)
        print(f"  {d:<10} {cnt:>3}  ({pct:>5.1f}%)  {bar}")

    print(f"\n  📏 RANGO NY — Prom: {avg_range} pts | Máx: {max_range} | Mín: {min_range}")

    if sweep_hours:
        print("\n  ⏰ HORA DEL SWEEP")
        for sw, cnt in sorted(sweep_hours.items()):
            print(f"  {sw}: {cnt} sweeps")

    print("\n  📐 VOLUME PROFILE VALUE AREA  (Asia 18:00 → 09:20 NY)")
    for name, hits, react in [("VAH (techo)", vah_hits, vah_react),
                               ("POC (centro)", poc_hits, poc_react),
                               ("VAL (base)", val_hits, val_react)]:
        hp = round(hits / total_d * 100, 1) if total_d else 0
        ar = round(react / hits, 1) if hits else 0
        bar = "█" * int(hp / 5)
        print(f"  {name:<14} {hits:>2}/{total_d}  ({hp:>5.1f}%)  reacción prom: {ar:>6.1f} pts  {bar}")

    ep  = round(ema_hits / total_d * 100, 1) if total_d else 0
    ear = round(ema_react / ema_hits, 1) if ema_hits else 0
    abp = round(ema_above / total_d * 100, 1) if total_d else 0
    blp = round((total_d - ema_above) / total_d * 100, 1) if total_d else 0
    print("\n  📉 EMA 200 (15 min) al open NY 09:30")
    print(f"  Toca EMA200:        {ema_hits}/{total_d}  ({ep}%)  | Reacción prom: {ear} pts")
    print(f"  Abre SOBRE  EMA200: {ema_above}/{total_d}  ({abp}%)  → contexto alcista")
    print(f"  Abre DEBAJO EMA200: {total_d - ema_above}/{total_d}  ({blp}%)  → contexto bajista")

    # Detalle sesiones
    print("\n  📋 DETALLE CADA SESIÓN")
    print(f"  {'FECHA':<12} {'PATRÓN':<20} {'DIR':<9} "
          f"{'VAL':>7} {'POC':>7} {'VAH':>7} {'EMA200':>7} {'RANGO':>7}")
    print("  " + "─" * 72)
    for r in day_results:
        print(
            f"  {r['date']:<12} {r['pattern']:<20} {r['direction']:<9} "
            f"{r['val']:>7.0f} {r['poc']:>7.0f} {r['vah']:>7.0f} "
            f"{r['ema200']:>7.0f} {r['ny_range']:>6.0f}pts"
        )

    # Conclusión
    best = max(
        [("VAH", vah_hits, vah_react), ("POC", poc_hits, poc_react),
         ("VAL", val_hits, val_react), ("EMA200", ema_hits, ema_react)],
        key=lambda x: (x[1], x[2])
    )
    best_react = round(best[2] / best[1], 1) if best[1] else 0
    print("═" * 72)
    print("  💡 CONCLUSIÓN")
    if dominant == "NEWS_DRIVE":
        print(f"  ⚡ Alta volatilidad — NEWS_DRIVE {dom_pct}% | Rango prom {avg_range} pts")
    elif dominant in ("SWEEP_H_RETURN", "SWEEP_L_RETURN"):
        print(f"  🎯 SWEEP & RETURN dominante ({dom_pct}%) — entrada en contra del sweep")
    elif dominant in ("EXPANSION_H", "EXPANSION_L"):
        print(f"  🚀 EXPANSIÓN dominante ({dom_pct}%) — seguir la ruptura")
    else:
        print(f"  🔄 ROTACIÓN POC dominante ({dom_pct}%) — scalp interno")
    print(f"  🔑 NIVEL MÁS RESPETADO: {best[0]}  "
          f"({best[1]}/{total_d} ses | reacción prom: {best_react} pts)")
    print("═" * 72)

    return {
        "day":             day_es,
        "total_sessions":  total_d,
        "dominant_pattern": dominant,
        "dominant_pct":    dom_pct,
        "patterns":        {p: f"{pct_day.get(p, 0):.1f}%" for p in PATTERN_NAMES},
        "direction":       directions,
        "avg_ny_range":    avg_range,
        "max_ny_range":    max_range,
        "min_ny_range":    min_range,
        "sweep_hours":     dict(sweep_hours),
        "value_area": {
            "vah": {"hit_rate": f"{round(vah_hits/total_d*100,1) if total_d else 0}%",
                    "avg_reaction": round(vah_react/vah_hits, 1) if vah_hits else 0},
            "poc": {"hit_rate": f"{round(poc_hits/total_d*100,1) if total_d else 0}%",
                    "avg_reaction": round(poc_react/poc_hits, 1) if poc_hits else 0},
            "val": {"hit_rate": f"{round(val_hits/total_d*100,1) if total_d else 0}%",
                    "avg_reaction": round(val_react/val_hits, 1) if val_hits else 0},
        },
        "ema200": {
            "hit_rate": f"{ep}%",
            "avg_reaction": ear,
            "open_above_pct": abp,
            "open_below_pct": blp,
        },
        "best_level": best[0],
        "sessions":   day_results,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_all_days_backtest(days_window: int = 365, filter_day: int | None = None):
    if not os.path.exists(CSV_PATH):
        print(f"❌ No se encuentra {CSV_PATH}")
        print("   Ejecuta: python update_nq_data.py")
        return

    # ── Cargar datos ──────────────────────────────────────────────────────────
    df = pd.read_csv(CSV_PATH, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    end_date   = df.index.max()
    start_date = end_date - timedelta(days=days_window)
    df_window  = df.loc[start_date:]

    print(f"\n{'═'*72}")
    print(f"  🔬 NQ INTELLIGENCE — BACKTEST TODOS LOS DÍAS")
    print(f"  Periodo: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}  ({days_window}d)")
    print(f"  CSV: {len(df)} velas totales | ventana: {len(df_window)} velas")
    print(f"{'═'*72}")

    ema200_full = get_ema200(df)   # EMA200 sobre TODO el histórico
    days = df_window.index.normalize().unique()

    # Colectores por día
    all_results  = []
    day_results  = {i: [] for i in range(5)}
    patterns_all = defaultdict(int)
    patterns_day = {i: defaultdict(int) for i in range(5)}

    # ── Iterar días ───────────────────────────────────────────────────────────
    for day in days:
        wd = day.weekday()
        if wd > 4:               # fin de semana → skip
            continue
        if filter_day is not None and wd != filter_day:
            continue

        # Rango Asia+Londres (18:00 día anterior → 08:30 NY)
        r_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        r_end   = day.replace(hour=8, minute=30)
        rdata   = df.loc[r_start:r_end]
        if rdata.empty or len(rdata) < 15:
            continue

        r_high = float(rdata['High'].max())
        r_low  = float(rdata['Low'].min())
        r_range = r_high - r_low

        # Value Area: Asia 18:00 → 09:20 NY
        p_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        p_end   = day.replace(hour=9, minute=20)
        pdata   = df.loc[p_start:p_end]
        if pdata.empty or len(pdata) < 5:
            continue
        val, poc, vah = calc_value_area(pdata)

        # EMA200 al momento de apertura NY
        try:
            ema_at_open = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])
        except (IndexError, KeyError):
            continue

        # Sesión NY: opening drive (09:30→11:30) y cierre (→16:00)
        ny_od = df.loc[day.replace(hour=9, minute=30) : day.replace(hour=11, minute=30)]
        ny_fl = df.loc[day.replace(hour=9, minute=30) : day.replace(hour=16, minute=0)]
        if ny_od.empty or len(ny_od) < 3:
            continue

        ny_open    = float(ny_od.iloc[0]['Open'])
        ny_high    = float(ny_od['High'].max())
        ny_low     = float(ny_od['Low'].min())
        ny_range   = ny_high - ny_low
        full_close = float(ny_fl.iloc[-1]['Close']) if not ny_fl.empty else float(ny_od.iloc[-1]['Close'])

        # Patrón, dirección, sweep time
        pattern   = classify_pattern(ny_od, r_high, r_low, ny_range)
        direction = classify_direction(full_close, ny_open)
        sw_time   = get_sweep_time(ny_od, pattern, r_high, r_low)

        # Nivel hits + reacciones
        vah_hit   = level_touched(ny_od, vah)
        poc_hit   = level_touched(ny_od, poc)
        val_hit   = level_touched(ny_od, val)
        ema_hit   = level_touched(ny_od, ema_at_open)

        row = {
            "date":        day.strftime('%Y-%m-%d'),
            "weekday_num": wd,
            "weekday_en":  DAY_NAMES[wd]["en"],
            "pattern":     pattern,
            "direction":   direction,
            "range_asia":  round(r_range, 1),
            "ny_range":    round(ny_range, 1),
            "ny_open":     round(ny_open, 2),
            "full_close":  round(full_close, 2),
            "r_high":      round(r_high, 2),
            "r_low":       round(r_low, 2),
            "val":         round(val, 2),
            "poc":         round(poc, 2),
            "vah":         round(vah, 2),
            "ema200":      round(ema_at_open, 2),
            "open_vs_ema": round(ny_open - ema_at_open, 1),
            "sweep_time":  sw_time,
            "vah_hit":     vah_hit,
            "vah_react":   reaction_after_touch(ny_od, vah)         if vah_hit else 0.0,
            "poc_hit":     poc_hit,
            "poc_react":   reaction_after_touch(ny_od, poc)         if poc_hit else 0.0,
            "val_hit":     val_hit,
            "val_react":   reaction_after_touch(ny_od, val)         if val_hit else 0.0,
            "ema_hit":     ema_hit,
            "ema_react":   reaction_after_touch(ny_od, ema_at_open) if ema_hit else 0.0,
            "ema_above":   ny_open > ema_at_open,
        }

        all_results.append(row)
        patterns_all[pattern] += 1

        day_results[wd].append(row)
        patterns_day[wd][pattern] += 1

    day_counts = ", ".join(
        f"{DAY_NAMES[d]['es']}: {len(v)}" for d, v in day_results.items() if v
    )
    print(f"\n  ✅ Sesiones procesadas: {len(all_results)} ({day_counts})")

    # ── Generar reportes por día ───────────────────────────────────────────────
    days_to_analyze = [filter_day] if filter_day is not None else list(range(5))
    reports = {}

    for d in days_to_analyze:
        if not day_results[d]:
            continue
        report = analyze_day(d, day_results[d], all_results,
                             patterns_day[d], patterns_all)
        reports[DAY_NAMES[d]["es"]] = report

    # ── Guardar JSON ──────────────────────────────────────────────────────────
    output = {
        "title":          "Backtest NQ NASDAQ — Todos los días",
        "period_days":    days_window,
        "period_start":   start_date.strftime('%Y-%m-%d'),
        "period_end":     end_date.strftime('%Y-%m-%d'),
        "total_sessions": len(all_results),
        "generated_at":   datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "methodology": {
            "volume_profile":  "Asia 18:00 → NY 09:20",
            "ema":             "EMA200 (15min)",
            "patterns":        PATTERN_NAMES,
            "ny_session":      "09:30 → 16:00",
            "opening_drive":   "09:30 → 11:30",
        },
        "days": reports,
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False, default=str)

    print(f"\n  💾 Guardado → {OUTPUT_JSON}")
    return output


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NQ Backtest — mismo estudio para los 5 días de la semana"
    )
    parser.add_argument(
        "--days", type=int, default=365,
        help="Ventana de datos en días (default: 365)"
    )
    parser.add_argument(
        "--day", type=str, default=None,
        help="Analiza solo un día: lun|mar|mie|jue|vie"
    )
    args = parser.parse_args()

    filter_day = None
    if args.day:
        key = args.day.lower().strip()
        if key not in DAY_ALIAS:
            print(f"❌ Día no reconocido: '{args.day}'")
            print(f"   Opciones: {', '.join(DAY_ALIAS.keys())}")
            raise SystemExit(1)
        filter_day = DAY_ALIAS[key]

    run_all_days_backtest(days_window=args.days, filter_day=filter_day)
