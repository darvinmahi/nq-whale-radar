"""
╔══════════════════════════════════════════════════════════════════════╗
║  BACKTEST SEMANAL SECUENCIAL · NQ NASDAQ · 6 MESES                 ║
║  Análisis día por día: Lun / Mar / Mié / Jue / Vie                 ║
║  + Contexto: qué pasó el día ANTERIOR (dirección y patrón)         ║
║  Datos: 15min intraday NQ futures (Asia+Londres como rango base)   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

# ── Constantes ──────────────────────────────────────────────────────
PATTERN_NAMES = [
    "SWEEP_H_RETURN",  # Barre high, vuelve al rango  → VENDER
    "SWEEP_L_RETURN",  # Barre low,  vuelve al rango  → COMPRAR
    "EXPANSION_H",     # Rompe arriba y NO vuelve     → TENDENCIA ALCISTA
    "EXPANSION_L",     # Rompe abajo  y NO vuelve     → TENDENCIA BAJISTA
    "ROTATION_POC",    # Se queda en rango / POC       → SCALP interno
    "NEWS_DRIVE",      # Movimiento errático gran vela → EVITAR / REDUCIR SZ
]

DAYS_ES = {
    0: "LUNES",
    1: "MARTES",
    2: "MIÉRCOLES",
    3: "JUEVES",
    4: "VIERNES",
}

DAYS_EN = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday"}

NEWS_THRESHOLD   = 250   # pts  → clasifica NEWS_DRIVE
SWEEP_BUFFER     = 20    # pts  → margen para considerar "barrió el nivel"
DIRECTION_THRESH = 30    # pts  → umbral BUY/SELL vs NEUTRAL
POC_TOUCH_MARGIN = 15    # pts  → rango de contacto con el POC
POC_REACT_MIN    = 50    # pts  → reacción mínima para contar "reacción real"

# ── Carga de datos ───────────────────────────────────────────────────
def load_data(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ["Datetime", "Close", "High", "Low", "Open", "Volume"]
    df = df.dropna(subset=["Datetime"])
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
    df.set_index("Datetime", inplace=True)
    df.index = df.index.tz_convert("America/New_York")
    df = df.sort_index()
    # Últimos 6 meses
    cutoff = df.index.max() - timedelta(days=180)
    return df.loc[cutoff:]


# ── Cálculo POC ──────────────────────────────────────────────────────
def calc_poc(prices: pd.Series) -> float:
    if len(prices) < 5:
        return float(prices.mean())
    bins = np.linspace(prices.min(), prices.max(), max(10, min(40, len(prices))))
    counts, edges = np.histogram(prices, bins=bins)
    return float(edges[np.argmax(counts)])


# ── Clasificar patrón ────────────────────────────────────────────────
def classify_pattern(ny_high, ny_low, ny_close, r_high, r_low) -> str:
    ny_range = ny_high - ny_low
    if ny_range > NEWS_THRESHOLD:
        return "NEWS_DRIVE"
    if ny_high > r_high + SWEEP_BUFFER:
        return "SWEEP_H_RETURN" if ny_close < r_high else "EXPANSION_H"
    if ny_low < r_low - SWEEP_BUFFER:
        return "SWEEP_L_RETURN" if ny_close > r_low else "EXPANSION_L"
    return "ROTATION_POC"


# ── Clasificar dirección ─────────────────────────────────────────────
def classify_direction(full_close, ny_open) -> str:
    delta = full_close - ny_open
    if delta > DIRECTION_THRESH:
        return "BULLISH"
    if delta < -DIRECTION_THRESH:
        return "BEARISH"
    return "NEUTRAL"


# ── Análisis principal ───────────────────────────────────────────────
def run_weekly_sequence():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print("❌ Archivo no encontrado:", csv_path)
        return

    df = load_data(csv_path)
    days = df.index.normalize().unique()

    all_results = []

    for day in days:
        wd = day.weekday()
        if wd not in DAYS_ES:          # ignorar sábado/domingo
            continue

        # ── Rango Asia + Londres (18:00 día anterior → 08:30 hoy) ──
        start_range = (day - timedelta(days=1)).replace(hour=18, minute=0)
        end_range   = day.replace(hour=8, minute=30)
        range_data  = df.loc[start_range:end_range]

        if range_data.empty or len(range_data) < 15:
            continue

        r_high = range_data["High"].max()
        r_low  = range_data["Low"].min()
        r_range = r_high - r_low
        c_poc  = calc_poc(range_data["Close"])

        # ── Sesión NY (09:30 – 11:30 apertura + 16:00 cierre) ──────
        ny_open_data = df.loc[
            day.replace(hour=9, minute=30): day.replace(hour=11, minute=30)
        ]
        ny_full = df.loc[
            day.replace(hour=9, minute=30): day.replace(hour=16, minute=0)
        ]

        if ny_open_data.empty or len(ny_open_data) < 3:
            continue

        ny_open  = float(ny_open_data.iloc[0]["Open"])
        ny_high  = float(ny_open_data["High"].max())
        ny_low   = float(ny_open_data["Low"].min())
        ny_close = float(ny_open_data.iloc[-1]["Close"])
        ny_range = ny_high - ny_low

        full_close = float(ny_full.iloc[-1]["Close"]) if not ny_full.empty else ny_close

        # ── Sweep time ──────────────────────────────────────────────
        p_type = classify_pattern(ny_high, ny_low, ny_close, r_high, r_low)
        sweep_time = None
        if p_type == "SWEEP_H_RETURN":
            sc = ny_open_data[ny_open_data["High"] >= r_high + SWEEP_BUFFER]
            sweep_time = sc.index[0].strftime("%H:%M") if not sc.empty else None
        elif p_type == "SWEEP_L_RETURN":
            sc = ny_open_data[ny_open_data["Low"] <= r_low - SWEEP_BUFFER]
            sweep_time = sc.index[0].strftime("%H:%M") if not sc.empty else None

        # ── POC hit ─────────────────────────────────────────────────
        hits_poc = ny_open_data[
            (ny_open_data["Low"] <= c_poc + POC_TOUCH_MARGIN) &
            (ny_open_data["High"] >= c_poc - POC_TOUCH_MARGIN)
        ]
        poc_hit      = not hits_poc.empty
        poc_reaction = max(ny_high - c_poc, c_poc - ny_low) if poc_hit else 0

        direction = classify_direction(full_close, ny_open)

        all_results.append({
            "date":         day.strftime("%Y-%m-%d"),
            "weekday_num":  wd,
            "weekday_es":   DAYS_ES[wd],
            "pattern":      p_type,
            "direction":    direction,
            "r_range":      round(r_range, 1),
            "ny_range":     round(ny_range, 1),
            "ny_open":      round(ny_open, 2),
            "full_close":   round(full_close, 2),
            "r_high":       round(r_high, 2),
            "r_low":        round(r_low, 2),
            "c_poc":        round(c_poc, 2),
            "sweep_time":   sweep_time,
            "poc_hit":      poc_hit,
            "poc_reaction": round(poc_reaction, 1),
        })

    if not all_results:
        print("❌ Sin resultados — revisa los datos.")
        return

    # ── Añadir contexto: qué hizo el día ANTERIOR ───────────────────
    df_all = pd.DataFrame(all_results).sort_values("date").reset_index(drop=True)
    df_all["prev_direction"] = df_all["direction"].shift(1).fillna("—")
    df_all["prev_pattern"]   = df_all["pattern"].shift(1).fillna("—")
    df_all["prev_weekday"]   = df_all["weekday_es"].shift(1).fillna("—")

    # ══════════════════════════════════════════════════════════════════
    #  REPORTE POR DÍA
    # ══════════════════════════════════════════════════════════════════

    print("\n" + "═" * 72)
    print("  📅  BACKTEST SEMANAL SECUENCIAL · NQ NASDAQ · ÚLTIMOS 6 MESES")
    print("═" * 72)

    full_report = {}

    for wd_num in range(5):   # Lunes=0 … Viernes=4
        day_name = DAYS_ES[wd_num]
        subset   = df_all[df_all["weekday_num"] == wd_num].copy()
        total    = len(subset)

        if total == 0:
            continue

        # -- Patrón dominante --
        pat_counts = subset["pattern"].value_counts()
        pat_pcts   = (pat_counts / total * 100).round(1)
        dominant   = pat_counts.idxmax()
        dom_pct    = pat_pcts[dominant]

        # -- Dirección --
        dir_counts = subset["direction"].value_counts()
        dir_pcts   = (dir_counts / total * 100).round(1)

        # -- Rango --
        avg_range = subset["ny_range"].mean()
        max_range = subset["ny_range"].max()
        min_range = subset["ny_range"].min()

        # -- POC --
        poc_hits  = subset["poc_hit"].sum()
        poc_react = (subset["poc_reaction"] > POC_REACT_MIN).sum()

        # -- Sweep time breakdown --
        sweep_rows = subset[subset["sweep_time"].notna()]
        sweep_hour_counts = defaultdict(int)
        for st in sweep_rows["sweep_time"]:
            h = st.split(":")[0]
            sweep_hour_counts[f"{h}:00-{h}:59"] += 1

        # ── Contexto día anterior ───────────────────────────────────
        prev_ctx = {}
        for prev_dir in ["BULLISH", "BEARISH", "NEUTRAL"]:
            ctx_sub = subset[subset["prev_direction"] == prev_dir]
            if len(ctx_sub) == 0:
                continue
            ctx_pat = ctx_sub["pattern"].value_counts()
            ctx_dir = ctx_sub["direction"].value_counts()
            prev_ctx[prev_dir] = {
                "n":            len(ctx_sub),
                "dom_pattern":  ctx_pat.idxmax() if not ctx_pat.empty else "—",
                "dom_pat_pct":  round(ctx_pat.max() / len(ctx_sub) * 100, 1) if not ctx_pat.empty else 0,
                "bullish_pct":  round(ctx_dir.get("BULLISH", 0) / len(ctx_sub) * 100, 1),
                "bearish_pct":  round(ctx_dir.get("BEARISH", 0) / len(ctx_sub) * 100, 1),
            }

        # == PRINT ==
        print(f"\n{'─'*72}")
        print(f"  📌  {day_name} — {total} sesiones analizadas")
        print(f"{'─'*72}")

        # Patrones
        print(f"  {'PATRÓN':<22} {'VECES':>6}  {'%':>7}")
        print(f"  {'─'*38}")
        for p in PATTERN_NAMES:
            cnt = pat_counts.get(p, 0)
            pct = pat_pcts.get(p, 0.0)
            mark = " ◀ DOMINANTE" if p == dominant else ""
            print(f"  {p:<22} {cnt:>6}  {pct:>6.1f}%{mark}")

        # Dirección
        print()
        print(f"  📈 DIRECCIÓN DEL DÍA")
        for d in ["BULLISH", "BEARISH", "NEUTRAL"]:
            cnt = dir_counts.get(d, 0)
            pct = dir_pcts.get(d, 0.0)
            bar = "█" * int(pct / 4)
            print(f"  {d:<10} {cnt:>3}  ({pct:>5.1f}%)  {bar}")

        # Rango
        print(f"\n  📏 RANGO NY  — Prom: {avg_range:.0f} pts  |  Máx: {max_range:.0f}  |  Mín: {min_range:.0f}")

        # POC
        poc_rate = round(poc_hits / total * 100, 1) if total else 0
        print(f"  🎯 POC Hit: {poc_hits}/{total} ({poc_rate}%)  |  Reacción >50pts: {poc_react}")

        # Sweep times
        if sweep_hour_counts:
            hours_sorted = sorted(sweep_hour_counts.items())
            print(f"  ⏰ Sweep hours: {' | '.join(f'{h}:{c}x' for h,c in hours_sorted)}")

        # Contexto día anterior
        if prev_ctx:
            print(f"\n  🔗 CONDICIONAL — según dirección del día ANTERIOR:")
            for prev_dir, data in prev_ctx.items():
                arrow = "↑" if prev_dir == "BULLISH" else ("↓" if prev_dir == "BEARISH" else "→")
                print(
                    f"  Si ayer fue {arrow} {prev_dir:<8} ({data['n']:>2} veces) → "
                    f"Hoy dom: {data['dom_pattern']:<20} ({data['dom_pat_pct']}%)  "
                    f"[BULL {data['bullish_pct']}% / BEAR {data['bearish_pct']}%]"
                )

        # Guardar en reporte
        full_report[day_name] = {
            "total_sessions":    total,
            "dominant_pattern":  dominant,
            "dominant_pct":      float(dom_pct),
            "patterns":          {p: float(pat_pcts.get(p, 0)) for p in PATTERN_NAMES},
            "direction":         {d: float(dir_pcts.get(d, 0.0)) for d in ["BULLISH", "BEARISH", "NEUTRAL"]},
            "avg_ny_range":      round(avg_range, 1),
            "poc_hit_rate_pct":  poc_rate,
            "poc_reactions":     int(poc_react),
            "conditional_prev":  prev_ctx,
            "day_records":       subset[["date", "pattern", "direction", "ny_range", "sweep_time", "prev_direction", "prev_pattern"]].to_dict(orient="records"),
        }

    # ══════════════════════════════════════════════════════════════════
    #  RESUMEN GLOBAL: tabla comparativa
    # ══════════════════════════════════════════════════════════════════
    print("\n" + "═" * 72)
    print("  📊  RESUMEN COMPARATIVO — DOMINANTE POR DÍA")
    print("═" * 72)
    print(f"  {'DÍA':<12} {'DOMINANTE':<22} {'%':>6}  {'AVG RANGE':>10}  {'BULL%':>6}  {'BEAR%':>6}")
    print(f"  {'─'*68}")
    for day_name, data in full_report.items():
        bull = data["direction"].get("BULLISH", 0)
        bear = data["direction"].get("BEARISH", 0)
        print(
            f"  {day_name:<12} {data['dominant_pattern']:<22} {data['dominant_pct']:>5.1f}%"
            f"  {data['avg_ny_range']:>8.0f}pts"
            f"  {bull:>5.1f}%"
            f"  {bear:>5.1f}%"
        )

    # ══════════════════════════════════════════════════════════════════
    #  GUARDAR JSON
    # ══════════════════════════════════════════════════════════════════
    output_path = "data/research/backtest_weekly_sequence.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title":    "Backtest Semanal Secuencial NQ · 6 Meses",
                "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "days":     full_report,
            },
            f, indent=4, ensure_ascii=False,
        )

    print(f"\n  ✅ JSON guardado → {output_path}")
    print("═" * 72)


if __name__ == "__main__":
    run_weekly_sequence()
