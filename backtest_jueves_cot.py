"""
╔══════════════════════════════════════════════════════════════════════════╗
║  BACKTEST · JUEVES + COT INDEX · NQ NASDAQ · 1 AÑO                     ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  Hereda el engine completo de backtest_thursday_noticias_1year.py y     ║
║  añade el COT Index (Leveraged Money 52-week percentile) por semana     ║
║                                                                          ║
║  Regímenes COT:                                                          ║
║    • EXTREMO_LARGO  → COT < 30   (Lev Money MUY largo → Dealers         ║
║                                   presionan ABAJO → sesgo BEARISH)      ║
║    • NEUTRO         → 30–70      (Sin sesgo fuerte)                     ║
║    • EXTREMO_CORTO  → COT > 70   (Lev Money MUY corto → Dealers        ║
║                                   cubren SHORT → sesgo BULLISH)         ║
║                                                                          ║
║  Fuente COT : data/cot_index_weekly.json                                ║
║  Datos OHLC : data/research/nq_15m_intraday.csv                         ║
║  Salida     : data/research/backtest_jueves_cot.json                    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  CALENDARIO ECONÓMICO (idéntico al engine original)
# ─────────────────────────────────────────────────────────────────────────────
NEWS_CALENDAR = {
    # ── CPI 2024
    "2024-03-12": "CPI", "2024-04-10": "CPI", "2024-05-15": "CPI",
    "2024-06-12": "CPI", "2024-07-11": "CPI", "2024-08-14": "CPI",
    "2024-09-11": "CPI", "2024-10-10": "CPI", "2024-11-13": "CPI",
    "2024-12-11": "CPI",
    # ── CPI 2025
    "2025-01-15": "CPI", "2025-02-12": "CPI", "2025-03-12": "CPI",
    # ── PPI 2024
    "2024-03-14": "PPI", "2024-04-11": "PPI", "2024-05-16": "PPI",
    "2024-06-13": "PPI", "2024-07-12": "PPI", "2024-08-15": "PPI",
    "2024-09-12": "PPI", "2024-10-11": "PPI", "2024-11-14": "PPI",
    "2024-12-12": "PPI",
    # ── PPI 2025
    "2025-01-16": "PPI", "2025-02-13": "PPI", "2025-03-13": "PPI",
    # ── NFP 2024
    "2024-03-07": "NFP", "2024-04-05": "NFP", "2024-05-03": "NFP",
    "2024-06-07": "NFP", "2024-07-05": "NFP", "2024-08-02": "NFP",
    "2024-09-06": "NFP", "2024-10-04": "NFP", "2024-11-01": "NFP",
    "2024-12-06": "NFP",
    # ── NFP 2025
    "2025-01-10": "NFP", "2025-02-07": "NFP", "2025-03-07": "NFP",
    # ── FOMC 2024
    "2024-01-31": "FOMC", "2024-03-20": "FOMC", "2024-05-01": "FOMC",
    "2024-06-12": "FOMC", "2024-07-31": "FOMC", "2024-09-18": "FOMC",
    "2024-11-07": "FOMC", "2024-12-18": "FOMC",
    # ── FOMC 2025
    "2025-01-29": "FOMC", "2025-03-19": "FOMC",
    # ── GDP
    "2024-01-25": "GDP", "2024-04-25": "GDP", "2024-07-25": "GDP",
    "2024-10-30": "GDP", "2025-01-30": "GDP",
    # ── PCE
    "2024-03-29": "PCE", "2024-04-26": "PCE", "2024-05-31": "PCE",
    "2024-06-28": "PCE", "2024-07-26": "PCE", "2024-08-30": "PCE",
    "2024-09-27": "PCE", "2024-10-31": "PCE", "2024-11-27": "PCE",
    "2024-12-20": "PCE", "2025-01-31": "PCE", "2025-02-28": "PCE",
    # ── ISM
    "2024-03-01": "ISM", "2024-04-01": "ISM", "2024-05-01": "ISM",
    "2024-06-03": "ISM", "2024-07-01": "ISM", "2024-08-01": "ISM",
    "2024-09-03": "ISM", "2024-10-01": "ISM", "2024-11-01": "ISM",
    "2024-12-02": "ISM", "2025-01-02": "ISM", "2025-02-03": "ISM",
    "2025-03-03": "ISM",
    # ── RETAIL SALES
    "2024-03-15": "RETAIL", "2024-04-15": "RETAIL", "2024-05-15": "RETAIL",
    "2024-06-18": "RETAIL", "2024-07-16": "RETAIL", "2024-08-15": "RETAIL",
    "2024-09-17": "RETAIL", "2024-10-17": "RETAIL", "2024-11-15": "RETAIL",
    "2024-12-17": "RETAIL", "2025-01-16": "RETAIL", "2025-02-14": "RETAIL",
    "2025-03-17": "RETAIL",
}

NEWS_PRIORITY = ["FOMC", "NFP", "CPI", "GDP", "PPI", "PCE", "ISM", "RETAIL", "JOBLESS"]
NEWS_IMPACT = {
    "FOMC": "ALTO", "NFP": "ALTO", "CPI": "ALTO",
    "GDP": "MEDIO", "PPI": "MEDIO", "PCE": "MEDIO", "ISM": "MEDIO",
    "RETAIL": "BAJO", "JOBLESS": "BAJO",
}

# ── COT Umbrales ─────────────────────────────────────────────────────────────
COT_EXTREMO_LARGO_MAX = 30    # < 30 = Lev Money MUY LARGO → sesgo bajista
COT_EXTREMO_CORTO_MIN = 70    # > 70 = Lev Money MUY CORTO → sesgo alcista


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIONES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def calc_value_area(data: pd.DataFrame, bins: int = 100, va_pct: float = 0.70):
    """Devuelve (val, poc, vah) usando histograma de precios (TPO-style)."""
    all_prices = pd.concat([data['High'], data['Low'], data['Close']])
    if len(all_prices) < 5:
        mid = data['Close'].mean()
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
        lo_val  = counts[lo_next] if lo_next >= 0         else -1
        hi_val  = counts[hi_next] if hi_next < len(counts) else -1
        if lo_val <= 0 and hi_val <= 0:
            break
        if lo_val >= hi_val:
            current += int(lo_val); lo_idx = lo_next
        else:
            current += int(hi_val); hi_idx = hi_next

    return float(bin_centers[lo_idx]), poc, float(bin_centers[hi_idx])


def get_ema200_series(df: pd.DataFrame) -> pd.Series:
    return df['Close'].ewm(span=200, adjust=False).mean()


def level_touched(ny_data: pd.DataFrame, level: float, margin: float = 15.0) -> bool:
    return bool(((ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)).any())


def reaction_after_touch(ny_data: pd.DataFrame, level: float, margin: float = 15.0) -> float:
    touch_rows = ny_data[(ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)]
    if touch_rows.empty:
        return 0.0
    first_touch_time = touch_rows.index[0]
    after = ny_data.loc[first_touch_time:]
    return float(after['High'].max() - after['Low'].min()) if not after.empty else 0.0


def get_news_for_day(date_str: str, weekday: int) -> str:
    if date_str in NEWS_CALENDAR:
        return NEWS_CALENDAR[date_str]
    if weekday == 3:   # jueves
        return "JOBLESS"
    return "NONE"


# ─────────────────────────────────────────────────────────────────────────────
#  CARGA COT — data/cot_index_weekly.json
#  Formato: [{"week": "2024-01-02", "cot_index": 50.0}, ...]
# ─────────────────────────────────────────────────────────────────────────────

def load_cot_weekly(path: str = "data/cot_index_weekly.json") -> list:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    for r in raw:
        d = datetime.strptime(r["week"], "%Y-%m-%d").date()
        rows.append({"week": d, "cot_index": float(r["cot_index"])})
    rows.sort(key=lambda x: x["week"])
    return rows


def get_cot_for_date(cot_rows: list, trade_date) -> dict | None:
    """Devuelve la última fila COT cuya semana sea ≤ trade_date."""
    if hasattr(trade_date, "date"):
        trade_date = trade_date.date()
    best = None
    for r in cot_rows:
        if r["week"] <= trade_date:
            best = r
        else:
            break
    return best


def classify_cot(cot_index: float) -> str:
    if cot_index < COT_EXTREMO_LARGO_MAX:
        return "EXTREMO_LARGO"
    if cot_index > COT_EXTREMO_CORTO_MIN:
        return "EXTREMO_CORTO"
    return "NEUTRO"


# ─────────────────────────────────────────────────────────────────────────────
#  SCRIPT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_jueves_cot_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    cot_path = "data/cot_index_weekly.json"

    if not os.path.exists(csv_path):
        print(f"❌ No encontrado: {csv_path}")
        return
    if not os.path.exists(cot_path):
        print(f"❌ No encontrado: {cot_path}")
        return

    # ── Cargar OHLC ──────────────────────────────────────────────────────────
    print("⏳ Cargando OHLC 15min…")
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    end_date   = df.index.max()
    start_date = df.index.min()
    df_window  = df

    print(f"📅 Periodo OHLC : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")

    # ── Cargar COT ───────────────────────────────────────────────────────────
    print("⏳ Cargando COT weekly…")
    cot_rows = load_cot_weekly(cot_path)
    print(f"📊 Semanas COT cargadas: {len(cot_rows)}  ({cot_rows[0]['week']} → {cot_rows[-1]['week']})")

    # ── EMA 200 sobre todo el histórico ──────────────────────────────────────
    ema200_full = get_ema200_series(df)

    days = df_window.index.normalize().unique()

    pattern_names = [
        "SWEEP_H_RETURN", "SWEEP_L_RETURN",
        "EXPANSION_H",    "EXPANSION_L",
        "ROTATION_POC",   "NEWS_DRIVE",
    ]

    # ── Colectores ───────────────────────────────────────────────────────────
    thursday_results = []

    # Stats globales por jueves
    patterns_thu   = defaultdict(int)
    thu_directions = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    thu_ranges     = []
    vah_hits=0; vah_react_sum=0.0
    poc_hits=0; poc_react_sum=0.0
    val_hits=0; val_react_sum=0.0
    ema_hits=0; ema_react_sum=0.0
    ema_above=0

    # Stats por régimen COT
    cot_regime_stats = {
        regime: {
            "count": 0,
            "directions": defaultdict(int),
            "patterns": defaultdict(int),
            "ranges": [],
            "news_types": defaultdict(int),
        }
        for regime in ("EXTREMO_LARGO", "NEUTRO", "EXTREMO_CORTO")
    }

    # Stats por combinación COT × NEWS_TYPE
    cot_news_matrix = defaultdict(
        lambda: {"count": 0, "directions": defaultdict(int), "patterns": defaultdict(int)}
    )

    # Stats por tipo de noticia (para el reporte)
    news_type_stats = defaultdict(lambda: {
        "count": 0, "ranges": [], "directions": defaultdict(int),
        "patterns": defaultdict(int),
        "vah_hits": 0, "poc_hits": 0, "val_hits": 0, "ema_hits": 0,
        "vah_react": 0.0, "poc_react": 0.0, "val_react": 0.0, "ema_react": 0.0,
    })

    # ── Iterar días ───────────────────────────────────────────────────────────
    for day in days:
        weekday = day.weekday()
        if weekday != 3:   # Solo jueves
            continue

        # ── Rango Asia + Londres ────────────────────────────────────────────
        range_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        range_end   = day.replace(hour=8, minute=30)
        range_data  = df.loc[range_start:range_end]
        if range_data.empty or len(range_data) < 15:
            continue

        r_high  = range_data['High'].max()
        r_low   = range_data['Low'].min()
        r_range = r_high - r_low

        # ── Volume Profile ───────────────────────────────────────────────────
        profile_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        profile_end   = day.replace(hour=9, minute=20)
        profile_data  = df.loc[profile_start:profile_end]
        if profile_data.empty or len(profile_data) < 5:
            continue
        val, p_poc, vah = calc_value_area(profile_data)

        # ── EMA 200 ──────────────────────────────────────────────────────────
        try:
            ema_at_open = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])
        except Exception:
            continue

        # ── NY Session ───────────────────────────────────────────────────────
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

        # ── Tipo de noticia ──────────────────────────────────────────────────
        date_str  = day.strftime('%Y-%m-%d')
        news_type = get_news_for_day(date_str, weekday)

        # ── Patrón ───────────────────────────────────────────────────────────
        buffer = 20
        p_type = "ROTATION_POC"
        if ny_range > 250:
            p_type = "NEWS_DRIVE"
        elif ny_high > r_high + buffer:
            p_type = "SWEEP_H_RETURN" if ny_close < r_high else "EXPANSION_H"
        elif ny_low < r_low - buffer:
            p_type = "SWEEP_L_RETURN" if ny_close > r_low  else "EXPANSION_L"

        # ── Dirección ────────────────────────────────────────────────────────
        if full_close > ny_open + 30:
            direction = "BULLISH"
        elif full_close < ny_open - 30:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # ── Toques de niveles ────────────────────────────────────────────────
        MARGIN = 20
        vah_t = level_touched(ny_open_data, vah, MARGIN)
        poc_t = level_touched(ny_open_data, p_poc, MARGIN)
        val_t = level_touched(ny_open_data, val, MARGIN)
        ema_t = level_touched(ny_open_data, ema_at_open, MARGIN)
        vah_r = reaction_after_touch(ny_open_data, vah, MARGIN)    if vah_t else 0
        poc_r = reaction_after_touch(ny_open_data, p_poc, MARGIN)  if poc_t else 0
        val_r = reaction_after_touch(ny_open_data, val, MARGIN)    if val_t else 0
        ema_r = reaction_after_touch(ny_open_data, ema_at_open, MARGIN) if ema_t else 0

        # ── COT para este día ─────────────────────────────────────────────────
        cot_row = get_cot_for_date(cot_rows, day)
        cot_index  = round(cot_row["cot_index"], 1) if cot_row else None
        cot_week   = str(cot_row["week"])            if cot_row else None
        cot_regime = classify_cot(cot_index)         if cot_index is not None else "SIN_DATOS"

        # ── Registro día ─────────────────────────────────────────────────────
        day_result = {
            "date":         date_str,
            "news_type":    news_type,
            "news_impact":  NEWS_IMPACT.get(news_type, "NONE"),
            "pattern":      p_type,
            "direction":    direction,
            "range_asia_lon": round(r_range, 1),
            "ny_range":     round(ny_range, 1),
            "ny_open":      round(ny_open, 2),
            "ny_close":     round(ny_close, 2),
            "full_close":   round(full_close, 2),
            "r_high":       round(r_high, 2),
            "r_low":        round(r_low, 2),
            "profile_val":  round(val, 2),
            "profile_poc":  round(p_poc, 2),
            "profile_vah":  round(vah, 2),
            "ema200":       round(ema_at_open, 2),
            "open_vs_ema":  round(ny_open - ema_at_open, 1),
            "vah_hit":      vah_t,
            "poc_hit":      poc_t,
            "val_hit":      val_t,
            "ema_hit":      ema_t,
            # ── COT FIELDS ──
            "cot_index":    cot_index,
            "cot_week":     cot_week,
            "cot_regime":   cot_regime,
        }

        thursday_results.append(day_result)

        # ── Acumuladores globales ────────────────────────────────────────────
        patterns_thu[p_type] += 1
        thu_directions[direction] += 1
        thu_ranges.append(ny_range)
        if vah_t: vah_hits += 1; vah_react_sum += vah_r
        if poc_t: poc_hits += 1; poc_react_sum += poc_r
        if val_t: val_hits += 1; val_react_sum += val_r
        if ema_t: ema_hits += 1; ema_react_sum += ema_r
        if ny_open > ema_at_open: ema_above += 1

        # ── Por tipo de noticia ──────────────────────────────────────────────
        ns = news_type_stats[news_type]
        ns["count"] += 1; ns["ranges"].append(ny_range)
        ns["directions"][direction] += 1; ns["patterns"][p_type] += 1
        if vah_t: ns["vah_hits"] += 1; ns["vah_react"] += vah_r
        if poc_t: ns["poc_hits"] += 1; ns["poc_react"] += poc_r
        if val_t: ns["val_hits"] += 1; ns["val_react"] += val_r
        if ema_t: ns["ema_hits"] += 1; ns["ema_react"] += ema_r

        # ── Por régimen COT ──────────────────────────────────────────────────
        if cot_regime != "SIN_DATOS":
            rs = cot_regime_stats[cot_regime]
            rs["count"] += 1
            rs["directions"][direction] += 1
            rs["patterns"][p_type] += 1
            rs["ranges"].append(ny_range)
            rs["news_types"][news_type] += 1

        # ── Matriz COT × Noticia ─────────────────────────────────────────────
        key = f"{cot_regime}×{news_type}"
        cot_news_matrix[key]["count"] += 1
        cot_news_matrix[key]["directions"][direction] += 1
        cot_news_matrix[key]["patterns"][p_type] += 1

    # ══════════════════════════════════════════════════════════════════════════
    #  REPORTE
    # ══════════════════════════════════════════════════════════════════════════

    total_thu = len(thursday_results)
    if total_thu == 0:
        print("❌ No se encontraron jueves en el periodo.")
        return

    avg_thu_range = round(np.mean(thu_ranges), 1)
    dominant_thu  = max(patterns_thu, key=patterns_thu.get) if patterns_thu else "N/A"

    W   = 78
    SEP = "═" * W

    print(f"\n{SEP}")
    print("  🔬 BACKTEST JUEVES + COT INDEX · NQ NASDAQ · 1 AÑO")
    print(SEP)
    print(f"  📅 Periodo : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  📌 Jueves totales  : {total_thu}")
    print(f"  📊 Rango NY prom   : {avg_thu_range} pts")
    print(f"  🏆 Patrón dominante: {dominant_thu}  "
          f"({round(patterns_thu.get(dominant_thu, 0)/total_thu*100, 1)}%)")

    # ── COT resumen ──────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  🧭 RÉGIMEN COT  (umbral LARGO<{COT_EXTREMO_LARGO_MAX} / CORTO>{COT_EXTREMO_CORTO_MIN})")
    print(f"{'─'*W}")
    header = f"  {'RÉGIMEN':<18} {'N':>4}  {'BULL%':>7}  {'BEAR%':>7}  {'NEUT%':>7}  {'RNG PROM':>10}  {'PATRÓN DOM'}"
    print(header)
    print(f"  {'─'*74}")

    for regime in ("EXTREMO_LARGO", "NEUTRO", "EXTREMO_CORTO"):
        rs = cot_regime_stats[regime]
        n  = rs["count"]
        if n == 0:
            print(f"  {regime:<18} {'0':>4}  — sin datos —")
            continue
        bull = round(rs["directions"]["BULLISH"] / n * 100, 1)
        bear = round(rs["directions"]["BEARISH"] / n * 100, 1)
        neut = round(rs["directions"]["NEUTRAL"] / n * 100, 1)
        avg_r  = round(np.mean(rs["ranges"]), 1)
        dom_p  = max(rs["patterns"], key=rs["patterns"].get) if rs["patterns"] else "N/A"
        dom_pp = round(rs["patterns"].get(dom_p, 0) / n * 100, 1)

        # iconos rápidos
        bias_icon = ""
        if regime == "EXTREMO_LARGO"  and bear > 50: bias_icon = " ▼ SESGO BAJISTA ✓"
        if regime == "EXTREMO_CORTO"  and bull > 50: bias_icon = " ▲ SESGO ALCISTA ✓"

        print(f"  {regime:<18} {n:>4}  {bull:>6.1f}%  {bear:>6.1f}%  {neut:>6.1f}%  "
              f"{avg_r:>9.1f}  {dom_p} ({dom_pp:.0f}%){bias_icon}")

    # ── Dirección general ────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📈 DIRECCIÓN GLOBAL (todos los jueves)")
    print(f"{'─'*W}")
    for d in ["BULLISH", "BEARISH", "NEUTRAL"]:
        ct  = thu_directions[d]
        pt  = round(ct / total_thu * 100, 1)
        bar = "█" * int(pt / 4)
        print(f"  {d:<10} {ct:>4} ({pt:>5.1f}%)   {bar}")

    # ── Desglose COT × Noticia (sólo combinaciones con ≥ 3 ocurrencias) ─────
    print(f"\n{'─'*W}")
    print("  🔀 MATRIZ COT × NOTICIA (combinaciones con ≥ 3 ocurrencias)")
    print(f"{'─'*W}")
    print(f"  {'COMBINACIÓN':<35} {'N':>4}  {'BULL%':>7}  {'BEAR%':>7}  {'NEUT%':>7}  {'PATRÓN DOM'}")
    print(f"  {'─'*72}")

    sorted_combos = sorted(
        [(k, v) for k, v in cot_news_matrix.items() if v["count"] >= 3],
        key=lambda x: -x[1]["count"]
    )
    for key, v in sorted_combos:
        n    = v["count"]
        bull = round(v["directions"]["BULLISH"] / n * 100, 1)
        bear = round(v["directions"]["BEARISH"] / n * 100, 1)
        neut = round(v["directions"]["NEUTRAL"] / n * 100, 1)
        dp   = max(v["patterns"], key=v["patterns"].get) if v["patterns"] else "N/A"
        dpp  = round(v["patterns"].get(dp, 0) / n * 100, 1)
        print(f"  {key:<35} {n:>4}  {bull:>6.1f}%  {bear:>6.1f}%  {neut:>6.1f}%  {dp} ({dpp:.0f}%)")

    # ── Detalle cada jueves ──────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📋 DETALLE CADA JUEVES (cron. ascendente)")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<13} {'COT':>6} {'RÉGIMEN':<16} {'NOTICIA':<9} {'DIR':<9} {'PATRÓN':<20} {'RANGO':>6}")
    print(f"  {'─'*74}")

    for r in sorted(thursday_results, key=lambda x: x["date"]):
        cot_str = f"{r['cot_index']:.1f}%" if r["cot_index"] is not None else "  N/A"
        impact_icon = {"ALTO": "🔴", "MEDIO": "🟡", "BAJO": "🟢", "NONE": "⚪"}.get(r["news_impact"], "⚪")
        regime_short = {"EXTREMO_LARGO": "EXT_LARGO", "EXTREMO_CORTO": "EXT_CORTO",
                        "NEUTRO": "NEUTRO", "SIN_DATOS": "---"}.get(r["cot_regime"], "---")
        dir_icon = {"BULLISH": "▲", "BEARISH": "▼", "NEUTRAL": "—"}.get(r["direction"], "—")
        print(
            f"  {r['date']:<13} {cot_str:>6} {regime_short:<16} "
            f"{impact_icon}{r['news_type']:<8} {dir_icon}{r['direction']:<8} "
            f"{r['pattern']:<20} {r['ny_range']:>5.0f}pts"
        )

    # ── Volume Profile ───────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  📐 VOLUME PROFILE · EMA200 (todos los jueves)")
    print(f"{'─'*W}")

    def level_row(name, hits, react_sum, total):
        hp   = round(hits / total * 100, 1) if total else 0
        avgr = round(react_sum / hits, 1) if hits else 0
        bar  = "█" * int(hp / 5)
        print(f"  {name:<14} {hits:>2}/{total} ({hp:>5.1f}%)  reac prom: {avgr:>6.1f} pts  {bar}")

    level_row("VAH (techo)",  vah_hits, vah_react_sum, total_thu)
    level_row("POC (clave)",  poc_hits, poc_react_sum, total_thu)
    level_row("VAL (base)",   val_hits, val_react_sum, total_thu)

    ep  = round(ema_hits / total_thu * 100, 1) if total_thu else 0
    ear = round(ema_react_sum / ema_hits, 1)   if ema_hits else 0
    abp = round(ema_above / total_thu * 100, 1)
    bep = round((total_thu - ema_above) / total_thu * 100, 1)
    print(f"\n  EMA 200  toca: {ema_hits}/{total_thu} ({ep}%)  reac: {ear} pts")
    print(f"  Abre sobre EMA: {ema_above}/{total_thu} ({abp}%)  |  Abre bajo: {total_thu-ema_above}/{total_thu} ({bep}%)")

    # ── Conclusiones COT ─────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  💡 CONCLUSIONES OPERATIVAS COT")
    print(SEP)

    for regime in ("EXTREMO_LARGO", "NEUTRO", "EXTREMO_CORTO"):
        rs = cot_regime_stats[regime]
        n  = rs["count"]
        if n == 0:
            continue
        bear_pct = round(rs["directions"]["BEARISH"] / n * 100, 1)
        bull_pct = round(rs["directions"]["BULLISH"] / n * 100, 1)
        dom_p    = max(rs["patterns"], key=rs["patterns"].get) if rs["patterns"] else "N/A"
        avg_r    = round(np.mean(rs["ranges"]), 1)

        label = {
            "EXTREMO_LARGO": f"COT < {COT_EXTREMO_LARGO_MAX}% — Lev Money MUY LARGO",
            "NEUTRO":        f"COT {COT_EXTREMO_LARGO_MAX}–{COT_EXTREMO_CORTO_MIN}% — Posición NEUTRA",
            "EXTREMO_CORTO": f"COT > {COT_EXTREMO_CORTO_MIN}% — Lev Money MUY CORTO",
        }[regime]

        print(f"\n  📍 {label}  ({n} jueves)")
        print(f"     BEARISH {bear_pct}%  |  BULLISH {bull_pct}%")
        print(f"     Patrón dominante: {dom_p}  |  Rango prom: {avg_r} pts")

        if regime == "EXTREMO_LARGO" and bear_pct >= 55:
            print(f"     → ✅ SESGO BAJISTA CONFIRMADO: {bear_pct}% de los jueves cerraron a la baja.")
        elif regime == "EXTREMO_CORTO" and bull_pct >= 55:
            print(f"     → ✅ SESGO ALCISTA CONFIRMADO: {bull_pct}% de los jueves cerraron al alza.")
        else:
            print(f"     → ⚠️  Sesgo no es suficientemente direccional para filtrar solos.")

    print(f"\n{SEP}\n")

    # ── GUARDAR JSON ─────────────────────────────────────────────────────────
    def serialize_defaultdict(d):
        """Convierte defaultdicts anidados a dicts normales."""
        if isinstance(d, defaultdict):
            return {k: serialize_defaultdict(v) for k, v in d.items()}
        return d

    report = {
        "title":  "Backtest Jueves + COT Index NQ · 1 Año",
        "period": f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        "config": {
            "cot_extremo_largo_max": COT_EXTREMO_LARGO_MAX,
            "cot_extremo_corto_min": COT_EXTREMO_CORTO_MIN,
        },
        "total_thursdays": total_thu,
        "avg_range_all":   avg_thu_range,
        "directions_all":  dict(thu_directions),
        "patterns_all":    {k: round(v / total_thu * 100, 1) for k, v in patterns_thu.items()},
        "cot_regime_stats": {
            regime: {
                "count": rs["count"],
                "avg_range": round(np.mean(rs["ranges"]), 1) if rs["ranges"] else 0,
                "directions": serialize_defaultdict(rs["directions"]),
                "patterns":   serialize_defaultdict(rs["patterns"]),
                "news_types": serialize_defaultdict(rs["news_types"]),
            }
            for regime, rs in cot_regime_stats.items()
        },
        "cot_news_matrix": {
            k: {
                "count": v["count"],
                "directions": serialize_defaultdict(v["directions"]),
                "dominant_pattern": max(v["patterns"], key=v["patterns"].get) if v["patterns"] else "N/A",
            }
            for k, v in cot_news_matrix.items()
        },
        "value_area": {
            "vah": {"hit_rate": f"{round(vah_hits/total_thu*100,1) if total_thu else 0}%",
                    "avg_reaction": round(vah_react_sum/vah_hits, 1) if vah_hits else 0},
            "poc": {"hit_rate": f"{round(poc_hits/total_thu*100,1) if total_thu else 0}%",
                    "avg_reaction": round(poc_react_sum/poc_hits, 1) if poc_hits else 0},
            "val": {"hit_rate": f"{round(val_hits/total_thu*100,1) if total_thu else 0}%",
                    "avg_reaction": round(val_react_sum/val_hits, 1) if val_hits else 0},
        },
        "ema200": {
            "hit_rate":          f"{round(ema_hits/total_thu*100,1) if total_thu else 0}%",
            "avg_reaction":      round(ema_react_sum/ema_hits, 1) if ema_hits else 0,
            "open_above_ema_pct": round(ema_above/total_thu*100, 1) if total_thu else 0,
        },
        "all_thursdays": thursday_results,
    }

    out_path = "data/research/backtest_jueves_cot.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False, default=str)

    print(f"  ✅ JSON guardado → {out_path}\n")


if __name__ == "__main__":
    run_jueves_cot_backtest()
