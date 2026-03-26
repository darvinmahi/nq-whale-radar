"""
╔══════════════════════════════════════════════════════════════════════════╗
║  BACKTEST · JUEVES CON NOTICIAS · NQ NASDAQ · 1 AÑO                    ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  Noticias analizadas:                                                    ║
║    • NFP       (1er Viernes → impacta Jueves previo + día noticia)      ║
║    • CPI       (2a semana Martes/Miércoles)                              ║
║    • FOMC      (6 semanas aprox, típico Miércoles)                       ║
║    • GDP       (fin de mes, típico Jueves)                               ║
║    • PPI       (día después del CPI, suele ser Jueves)                  ║
║    • JOBLESS   (Claims semanales → TODOS los jueves)                    ║
║    • PMI/ISM   (inicio de mes)                                           ║
║                                                                          ║
║  Engine: Volume Profile (VAH/POC/VAL) + EMA 200 (15min)                ║
║  Rango: últimos 365 días                                                 ║
║  Datos: data/research/nq_15m_intraday.csv (15min intraday NQ)           ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
#  CALENDARIO ECONÓMICO REAL 2024-2025 (Jueves relevantes + días de noticia)
#  Formato: "YYYY-MM-DD": "TIPO_NOTICIA"
#  Fuente: BLS, Fed, BEA calendarios oficiales
# ─────────────────────────────────────────────────────────────────────────────
NEWS_CALENDAR = {
    # ── JOBLESS CLAIMS (todos los jueves aprox) → se detectan automáticamente
    # ── CPI 2024
    "2024-03-12": "CPI",
    "2024-04-10": "CPI",
    "2024-05-15": "CPI",
    "2024-06-12": "CPI",
    "2024-07-11": "CPI",
    "2024-08-14": "CPI",
    "2024-09-11": "CPI",
    "2024-10-10": "CPI",
    "2024-11-13": "CPI",
    "2024-12-11": "CPI",
    # ── CPI 2025
    "2025-01-15": "CPI",
    "2025-02-12": "CPI",
    "2025-03-12": "CPI",

    # ── PPI 2024 (día después del CPI → suele ser Jueves)
    "2024-03-14": "PPI",
    "2024-04-11": "PPI",
    "2024-05-16": "PPI",
    "2024-06-13": "PPI",
    "2024-07-12": "PPI",
    "2024-08-15": "PPI",
    "2024-09-12": "PPI",
    "2024-10-11": "PPI",
    "2024-11-14": "PPI",
    "2024-12-12": "PPI",
    # ── PPI 2025
    "2025-01-16": "PPI",
    "2025-02-13": "PPI",
    "2025-03-13": "PPI",

    # ── NFP 2024 (primer Viernes de cada mes — impacto el Jueves previo)
    "2024-03-07": "NFP",
    "2024-04-05": "NFP",
    "2024-05-03": "NFP",
    "2024-06-07": "NFP",
    "2024-07-05": "NFP",
    "2024-08-02": "NFP",
    "2024-09-06": "NFP",
    "2024-10-04": "NFP",
    "2024-11-01": "NFP",
    "2024-12-06": "NFP",
    # ── NFP 2025
    "2025-01-10": "NFP",
    "2025-02-07": "NFP",
    "2025-03-07": "NFP",

    # ── FOMC 2024 (fechas reales de reunión — día de la decisión)
    "2024-01-31": "FOMC",
    "2024-03-20": "FOMC",
    "2024-05-01": "FOMC",
    "2024-06-12": "FOMC",
    "2024-07-31": "FOMC",
    "2024-09-18": "FOMC",
    "2024-11-07": "FOMC",
    "2024-12-18": "FOMC",
    # ── FOMC 2025
    "2025-01-29": "FOMC",
    "2025-03-19": "FOMC",

    # ── GDP (trimestral, avance → suele ser Jueves o Miércoles)
    "2024-01-25": "GDP",
    "2024-04-25": "GDP",
    "2024-07-25": "GDP",
    "2024-10-30": "GDP",
    "2025-01-30": "GDP",

    # ── PCE (Personal Consumption Expenditures — core inflation → Viernes)
    "2024-03-29": "PCE",
    "2024-04-26": "PCE",
    "2024-05-31": "PCE",
    "2024-06-28": "PCE",
    "2024-07-26": "PCE",
    "2024-08-30": "PCE",
    "2024-09-27": "PCE",
    "2024-10-31": "PCE",
    "2024-11-27": "PCE",
    "2024-12-20": "PCE",
    "2025-01-31": "PCE",
    "2025-02-28": "PCE",

    # ── ISM / PMI Manufacturero (1er día hábil del mes)
    "2024-03-01": "ISM",
    "2024-04-01": "ISM",
    "2024-05-01": "ISM",
    "2024-06-03": "ISM",
    "2024-07-01": "ISM",
    "2024-08-01": "ISM",
    "2024-09-03": "ISM",
    "2024-10-01": "ISM",
    "2024-11-01": "ISM",
    "2024-12-02": "ISM",
    "2025-01-02": "ISM",
    "2025-02-03": "ISM",
    "2025-03-03": "ISM",

    # ── RETAIL SALES (mitad de mes, Miércoles/Jueves)
    "2024-03-15": "RETAIL",
    "2024-04-15": "RETAIL",
    "2024-05-15": "RETAIL",
    "2024-06-18": "RETAIL",
    "2024-07-16": "RETAIL",
    "2024-08-15": "RETAIL",
    "2024-09-17": "RETAIL",
    "2024-10-17": "RETAIL",
    "2024-11-15": "RETAIL",
    "2024-12-17": "RETAIL",
    "2025-01-16": "RETAIL",
    "2025-02-14": "RETAIL",
    "2025-03-17": "RETAIL",
}

# Prioridad de noticias (si coinciden en el mismo día)
NEWS_PRIORITY = ["FOMC", "NFP", "CPI", "GDP", "PPI", "PCE", "ISM", "RETAIL", "JOBLESS"]

# Impacto esperado por tipo de noticia (clasificación)
NEWS_IMPACT = {
    "FOMC":   "ALTO",
    "NFP":    "ALTO",
    "CPI":    "ALTO",
    "GDP":    "MEDIO",
    "PPI":    "MEDIO",
    "PCE":    "MEDIO",
    "ISM":    "MEDIO",
    "RETAIL": "BAJO",
    "JOBLESS":"BAJO",
}


# ─────────────────────────────────────────────────────────────────────────────
#  FUNCIONES AUXILIARES (idénticas al engine de wednesday)
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
        lo_val  = counts[lo_next] if lo_next >= 0        else -1
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
    """
    Retorna el tipo de noticia para ese día.
    Los JUEVES siempre tienen Jobless Claims como mínimo.
    Si hay noticia de mayor prioridad en el calendario, la usa.
    """
    # Verificar si hay noticia hardcodeada
    if date_str in NEWS_CALENDAR:
        return NEWS_CALENDAR[date_str]

    # Los jueves siempre tienen Jobless Claims
    if weekday == 3:
        return "JOBLESS"

    return "NONE"


# ─────────────────────────────────────────────────────────────────────────────
#  SCRIPT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_thursday_news_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Archivo de datos no encontrado: {csv_path}")
        print("   Asegúrate de tener el CSV con columnas: Datetime, Open, High, Low, Close, Volume")
        return

    # ── Cargar datos ──────────────────────────────────────────────────────
    print("⏳ Cargando datos...")
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    # ── Últimos 365 días (1 año) ──────────────────────────────────────────
    end_date   = df.index.max()
    start_date = end_date - timedelta(days=365)
    df_window  = df.loc[start_date:]

    print(f"📅 Periodo: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")

    # EMA 200 sobre TODO el histórico (necesita datos previos)
    ema200_full = get_ema200_series(df)

    days = df_window.index.normalize().unique()

    pattern_names = [
        "SWEEP_H_RETURN", "SWEEP_L_RETURN",
        "EXPANSION_H",    "EXPANSION_L",
        "ROTATION_POC",   "NEWS_DRIVE",
    ]

    # ── Colectores ────────────────────────────────────────────────────────
    all_days_results   = []
    thursday_results   = []
    thu_news_results   = []   # Jueves CON noticia de alto/medio impacto
    thu_jobless_only   = []   # Jueves solo con Jobless Claims

    patterns_thu       = defaultdict(int)
    patterns_thu_news  = defaultdict(int)

    thu_ranges         = []
    thu_news_ranges    = []
    thu_directions     = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    thu_news_directions= {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}

    news_type_stats    = defaultdict(lambda: {
        "count": 0, "ranges": [], "directions": defaultdict(int),
        "patterns": defaultdict(int),
        "vah_hits": 0, "poc_hits": 0, "val_hits": 0, "ema_hits": 0,
        "vah_react": 0.0, "poc_react": 0.0, "val_react": 0.0, "ema_react": 0.0,
    })

    # Niveles globales (todos los jueves)
    vah_hits=0; vah_react_sum=0.0
    poc_hits=0; poc_react_sum=0.0
    val_hits=0; val_react_sum=0.0
    ema_hits=0; ema_react_sum=0.0
    ema_above=0

    # ── Iterar días ───────────────────────────────────────────────────────
    for day in days:
        weekday = day.weekday()  # 0=Mon … 3=Thu … 6=Sun

        # ── Rango Asia+Londres ────────────────────────────────────────
        range_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        range_end   = day.replace(hour=8, minute=30)
        range_data  = df.loc[range_start:range_end]

        if range_data.empty or len(range_data) < 15:
            continue

        r_high  = range_data['High'].max()
        r_low   = range_data['Low'].min()
        r_range = r_high - r_low

        # ── Volume Profile (Asia 18:00 → 09:20 NY) ───────────────────
        profile_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        profile_end   = day.replace(hour=9, minute=20)
        profile_data  = df.loc[profile_start:profile_end]

        if profile_data.empty or len(profile_data) < 5:
            continue

        val, p_poc, vah = calc_value_area(profile_data)

        # ── EMA 200 al momento de apertura NY ─────────────────────────
        try:
            ema_at_open = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])
        except Exception:
            continue

        # ── NY Session ────────────────────────────────────────────────
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

        # ── Tipo de noticia ───────────────────────────────────────────
        date_str = day.strftime('%Y-%m-%d')
        news_type = get_news_for_day(date_str, weekday)

        # ── Patrón ────────────────────────────────────────────────────
        buffer = 20
        p_type = "ROTATION_POC"
        if ny_range > 250:
            p_type = "NEWS_DRIVE"
        elif ny_high > r_high + buffer:
            p_type = "SWEEP_H_RETURN" if ny_close < r_high else "EXPANSION_H"
        elif ny_low < r_low - buffer:
            p_type = "SWEEP_L_RETURN" if ny_close > r_low  else "EXPANSION_L"

        # ── Dirección ─────────────────────────────────────────────────
        if full_close > ny_open + 30:
            direction = "BULLISH"
        elif full_close < ny_open - 30:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # ── Toques de niveles ──────────────────────────────────────────
        MARGIN = 20
        vah_t = level_touched(ny_open_data, vah, MARGIN)
        poc_t = level_touched(ny_open_data, p_poc, MARGIN)
        val_t = level_touched(ny_open_data, val, MARGIN)
        ema_t = level_touched(ny_open_data, ema_at_open, MARGIN)

        vah_r = reaction_after_touch(ny_open_data, vah, MARGIN)   if vah_t else 0
        poc_r = reaction_after_touch(ny_open_data, p_poc, MARGIN) if poc_t else 0
        val_r = reaction_after_touch(ny_open_data, val, MARGIN)   if val_t else 0
        ema_r = reaction_after_touch(ny_open_data, ema_at_open, MARGIN) if ema_t else 0

        # ── Resultado del día ─────────────────────────────────────────
        day_result = {
            "date":        date_str,
            "weekday":     day.strftime('%A'),
            "weekday_num": weekday,
            "news_type":   news_type,
            "news_impact": NEWS_IMPACT.get(news_type, "NONE"),
            "pattern":     p_type,
            "direction":   direction,
            "range_asia_lon": round(r_range, 1),
            "ny_range":    round(ny_range, 1),
            "ny_open":     round(ny_open, 2),
            "ny_close":    round(ny_close, 2),
            "full_close":  round(full_close, 2),
            "r_high":      round(r_high, 2),
            "r_low":       round(r_low, 2),
            "profile_val": round(val, 2),
            "profile_poc": round(p_poc, 2),
            "profile_vah": round(vah, 2),
            "ema200":      round(ema_at_open, 2),
            "open_vs_ema": round(ny_open - ema_at_open, 1),
            "vah_hit":     vah_t,
            "poc_hit":     poc_t,
            "val_hit":     val_t,
            "ema_hit":     ema_t,
        }

        all_days_results.append(day_result)

        # ── JUEVES únicamente ─────────────────────────────────────────
        if weekday != 3:
            continue

        thursday_results.append(day_result)
        patterns_thu[p_type] += 1
        thu_ranges.append(ny_range)
        thu_directions[direction] += 1

        # Niveles globales jueves
        if vah_t: vah_hits += 1; vah_react_sum += vah_r
        if poc_t: poc_hits += 1; poc_react_sum += poc_r
        if val_t: val_hits += 1; val_react_sum += val_r
        if ema_t: ema_hits += 1; ema_react_sum += ema_r
        if ny_open > ema_at_open: ema_above += 1

        # Por tipo de noticia
        ns = news_type_stats[news_type]
        ns["count"]      += 1
        ns["ranges"].append(ny_range)
        ns["directions"][direction] += 1
        ns["patterns"][p_type] += 1
        if vah_t: ns["vah_hits"] += 1; ns["vah_react"] += vah_r
        if poc_t: ns["poc_hits"] += 1; ns["poc_react"] += poc_r
        if val_t: ns["val_hits"] += 1; ns["val_react"] += val_r
        if ema_t: ns["ema_hits"] += 1; ns["ema_react"] += ema_r

        # Separar noticias de alto/medio impacto vs solo Jobless
        if news_type in ["FOMC", "NFP", "CPI", "GDP", "PPI", "PCE", "ISM", "RETAIL"]:
            thu_news_results.append(day_result)
            patterns_thu_news[p_type] += 1
            thu_news_ranges.append(ny_range)
            thu_news_directions[direction] += 1
        else:
            thu_jobless_only.append(day_result)

    # ══════════════════════════════════════════════════════════════════════
    #  ANÁLISIS Y REPORTE
    # ══════════════════════════════════════════════════════════════════════
    total_all   = len(all_days_results)
    total_thu   = len(thursday_results)
    total_news  = len(thu_news_results)
    total_job   = len(thu_jobless_only)

    if total_thu == 0:
        print("❌ No se encontraron jueves en el periodo analizado")
        return

    pct_thu      = {k: round(v / total_thu * 100, 1) for k, v in patterns_thu.items()}
    pct_thu_news = {k: round(v / total_news * 100, 1) for k, v in patterns_thu_news.items()} if total_news else {}

    dominant_thu  = max(patterns_thu, key=patterns_thu.get) if patterns_thu else "N/A"
    dominant_news = max(patterns_thu_news, key=patterns_thu_news.get) if patterns_thu_news else "N/A"

    avg_thu_range  = round(np.mean(thu_ranges), 1)   if thu_ranges  else 0
    avg_news_range = round(np.mean(thu_news_ranges), 1) if thu_news_ranges else 0

    # ── IMPRIMIR REPORTE ──────────────────────────────────────────────────
    W = 76
    SEP = "═" * W

    print("\n" + SEP)
    print("  🔬 BACKTEST JUEVES CON NOTICIAS · NQ NASDAQ · 1 AÑO")
    print(SEP)
    print(f"  📅 Periodo : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  📊 Total días analizados : {total_all}")
    print(f"  📌 Jueves totales         : {total_thu}")
    print(f"  📣 Jueves CON noticia alta/media : {total_news}")
    print(f"  📋 Jueves solo Jobless Claims    : {total_job}")

    # ── ESTADÍSTICAS POR TIPO DE NOTICIA ─────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📰 ESTADÍSTICAS POR TIPO DE NOTICIA (cuando cae en Jueves)")
    print(f"{'─'*W}")
    print(f"  {'TIPO':<10} {'N':<5} {'RANGO PROM':<13} {'PATRÓN DOM':<22} {'BULL%':<8} {'BEAR%':<8} {'NEUTRAL%'}")
    print(f"  {'─'*70}")

    for ntype in NEWS_PRIORITY + ["JOBLESS"]:
        ns = news_type_stats.get(ntype)
        if not ns or ns["count"] == 0:
            continue
        n  = ns["count"]
        avg_r = round(np.mean(ns["ranges"]), 1)
        dom_p = max(ns["patterns"], key=ns["patterns"].get) if ns["patterns"] else "N/A"
        dom_pct = round(ns["patterns"][dom_p] / n * 100, 1) if dom_p != "N/A" else 0
        bull = round(ns["directions"]["BULLISH"] / n * 100, 1)
        bear = round(ns["directions"]["BEARISH"] / n * 100, 1)
        neut = round(ns["directions"]["NEUTRAL"] / n * 100, 1)
        impact = NEWS_IMPACT.get(ntype, "?")
        impact_icon = "🔴" if impact == "ALTO" else ("🟡" if impact == "MEDIO" else "🟢")
        print(f"  {impact_icon}{ntype:<9} {n:<5} {avg_r:>8.1f} pts   {dom_p:<18}({dom_pct:.0f}%)  {bull:>5.1f}%  {bear:>5.1f}%  {neut:>5.1f}%")

    # ── PATRONES TODOS LOS JUEVES ─────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📊 PATRONES — TODOS LOS JUEVES vs JUEVES CON NOTICIA")
    print(f"{'─'*W}")
    print(f"  {'PATRÓN':<22} {'TODOS JUE':<12} {'JUE+NOTICIA':<14} {'DELTA'}")
    print(f"  {'─'*60}")
    for p in pattern_names:
        t  = pct_thu.get(p, 0)
        n  = pct_thu_news.get(p, 0)
        d  = round(n - t, 1)
        ds = f"+{d}" if d > 0 else str(d)
        mk = " ◀" if p == dominant_news else ""
        print(f"  {p:<22} {t:>8.1f}%    {n:>8.1f}%    {ds:>6}%{mk}")

    print(f"\n  🏆 Patrón dominante TODOS los jueves      : {dominant_thu}  ({pct_thu.get(dominant_thu, 0):.1f}%)")
    print(f"  🏆 Patrón dominante JUEVES CON NOTICIA   : {dominant_news}  ({pct_thu_news.get(dominant_news, 0) if pct_thu_news else 0:.1f}%)")

    # ── DIRECCIÓN ─────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📈 DIRECCIÓN NY (cierre vs apertura 09:30)")
    print(f"{'─'*W}")
    print(f"  {'Dir':<10} {'Todos Jue':>12} {'Jue+Noticia':>14}")
    print(f"  {'─'*38}")
    for d in ["BULLISH", "BEARISH", "NEUTRAL"]:
        ct = thu_directions[d]
        pt = round(ct / total_thu * 100, 1)
        cn = thu_news_directions[d]
        pn = round(cn / total_news * 100, 1) if total_news else 0
        bar = "█" * int(pt / 4)
        print(f"  {d:<10} {ct:>4} ({pt:>5.1f}%)  {cn:>4} ({pn:>5.1f}%)   {bar}")

    # ── RANGO ─────────────────────────────────────────────────────────────
    print(f"\n  📏 RANGO NY (09:30–11:30)")
    print(f"     Todos los jueves : prom {avg_thu_range} pts  |  máx {max(thu_ranges, default=0):.0f}  |  mín {min(thu_ranges, default=0):.0f}")
    if thu_news_ranges:
        print(f"     Con noticia A/M  : prom {avg_news_range} pts  |  máx {max(thu_news_ranges):.0f}  |  mín {min(thu_news_ranges):.0f}")
        print(f"     Multiplicador rango noticia vs sin noticia: {round(avg_news_range / avg_thu_range, 2) if avg_thu_range else 0}x")

    # ── VOLUME PROFILE (solo jueves) ──────────────────────────────────────
    print(f"\n{'═'*W}")
    print("  📐 VOLUME PROFILE  (Asia 18:00 → 09:20 NY) · Solo Jueves")
    print(f"{'─'*W}")
    def level_row(name, hits, react_sum, total):
        hp   = round(hits / total * 100, 1) if total else 0
        avgr = round(react_sum / hits, 1) if hits else 0
        bar  = "█" * int(hp / 5)
        print(f"  {name:<14} tocado {hits:>2}/{total}  ({hp:>5.1f}%)   reacción prom: {avgr:>6.1f} pts  {bar}")

    level_row("VAH (techo)",  vah_hits, vah_react_sum, total_thu)
    level_row("POC (clave)",  poc_hits, poc_react_sum, total_thu)
    level_row("VAL (base)",   val_hits, val_react_sum, total_thu)

    print(f"\n  📉 EMA 200 (15min) al momento de apertura NY")
    ep  = round(ema_hits / total_thu * 100, 1) if total_thu else 0
    ear = round(ema_react_sum / ema_hits, 1)   if ema_hits else 0
    abp = round(ema_above / total_thu * 100, 1)
    bep = round((total_thu - ema_above) / total_thu * 100, 1)
    print(f"  Toca EMA200  : {ema_hits}/{total_thu} ({ep}%)  |  Reac. prom: {ear} pts")
    print(f"  Abre SOBRE   : {ema_above}/{total_thu} ({abp}%)  → sesiones alcistas")
    print(f"  Abre DEBAJO  : {total_thu - ema_above}/{total_thu} ({bep}%)  → sesiones bajistas")

    # ── DETALLE POR TIPO DE NOTICIA Y NIVEL ───────────────────────────────
    print(f"\n{'═'*W}")
    print("  🎯 NIVELES POR TIPO DE NOTICIA (Jueves)")
    print(f"{'─'*W}")
    print(f"  {'TIPO':<10} {'VAH%':<8} {'POC%':<8} {'VAL%':<8} {'EMA%':<8} {'Rango prom'}")
    print(f"  {'─'*55}")
    for ntype in NEWS_PRIORITY + ["JOBLESS"]:
        ns = news_type_stats.get(ntype)
        if not ns or ns["count"] == 0:
            continue
        n   = ns["count"]
        vhp = round(ns["vah_hits"] / n * 100, 1)
        php = round(ns["poc_hits"] / n * 100, 1)
        lhp = round(ns["val_hits"] / n * 100, 1)
        ehp = round(ns["ema_hits"] / n * 100, 1)
        ar  = round(np.mean(ns["ranges"]), 1)
        print(f"  {ntype:<10} {vhp:>5.1f}%  {php:>5.1f}%  {lhp:>5.1f}%  {ehp:>5.1f}%  {ar:>8.1f} pts")

    # ── DETALLE CADA JUEVES ───────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📋 DETALLE CADA JUEVES (último año)")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<13} {'NOTICIA':<10} {'PATRÓN':<20} {'DIR':<9} {'RANGO':>7} {'EMA':>7}")
    print(f"  {'─'*70}")
    for r in sorted(thursday_results, key=lambda x: x['date']):
        impact_icon = {"ALTO": "🔴", "MEDIO": "🟡", "BAJO": "🟢", "NONE": "⚪"}.get(r['news_impact'], "⚪")
        print(
            f"  {r['date']:<13} {impact_icon}{r['news_type']:<9} {r['pattern']:<20} "
            f"{r['direction']:<9} {r['ny_range']:>6.0f}pts {r['ema200']:>7.0f}"
        )

    # ── CONCLUSIÓN ────────────────────────────────────────────────────────
    print(f"\n{'═'*W}")
    print("  💡 CONCLUSIONES OPERATIVAS")
    print(f"{'═'*W}")

    if avg_news_range > avg_thu_range * 1.2:
        print(f"  ⚡ Los jueves CON noticia tienen un rango {round(avg_news_range/avg_thu_range, 2)}x mayor.")
        print(f"     → Reducir tamaño de posición o esperar confirmación post-noticia.")
    else:
        print(f"  📊 Los jueves con noticia no tienen rango significativamente mayor.")

    best_level = max(
        [("VAH", vah_hits, vah_react_sum),
         ("POC", poc_hits, poc_react_sum),
         ("VAL", val_hits, val_react_sum),
         ("EMA200", ema_hits, ema_react_sum)],
        key=lambda x: (x[1], x[2])
    )
    print(f"\n  🔑 NIVEL MÁS RESPETADO los Jueves: {best_level[0]}")
    print(f"     Tocado {best_level[1]}/{total_thu} jueves | "
          f"Reacción prom: {round(best_level[2]/best_level[1], 1) if best_level[1] else 0} pts")

    if dominant_news == "NEWS_DRIVE":
        print(f"\n  ⚡ En días de noticia: RANGO EXPANSION domina → no tradear en contra.")
    elif dominant_news in ["SWEEP_H_RETURN", "SWEEP_L_RETURN"]:
        print(f"\n  🎯 En días de noticia: SWEEP & RETURN domina → fade the spike.")
    elif dominant_news in ["EXPANSION_H", "EXPANSION_L"]:
        print(f"\n  🚀 En días de noticia: EXPANSION → seguir la ruptura del rango Asia.")
    print(f"\n  📋 Sesgo Jobless Claims (Jueves normales): "
          f"BULL {round(news_type_stats.get('JOBLESS', {}).get('directions', {}).get('BULLISH', 0) / max(news_type_stats.get('JOBLESS', {}).get('count', 1), 1) * 100, 1)}% | "
          f"BEAR {round(news_type_stats.get('JOBLESS', {}).get('directions', {}).get('BEARISH', 0) / max(news_type_stats.get('JOBLESS', {}).get('count', 1), 1) * 100, 1)}%")

    print(SEP)

    # ── GUARDAR JSON ──────────────────────────────────────────────────────
    report = {
        "title":   "Backtest Jueves con Noticias NQ · 1 Año completo",
        "period":  f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        "total_days":          total_all,
        "total_thursdays":     total_thu,
        "total_thu_with_news": total_news,
        "total_thu_jobless":   total_job,
        "dominant_pattern_all_thu":  dominant_thu,
        "dominant_pattern_thu_news": dominant_news,
        "avg_range_all_thursdays":   avg_thu_range,
        "avg_range_thu_news":        avg_news_range,
        "directions_all_thursdays":  dict(thu_directions),
        "directions_thu_news":       dict(thu_news_directions),
        "patterns_all_thursdays":    {k: f"{v:.1f}%" for k, v in pct_thu.items()},
        "patterns_thu_news":         {k: f"{v:.1f}%" for k, v in pct_thu_news.items()},
        "by_news_type": {
            ntype: {
                "count":        ns["count"],
                "avg_range":    round(np.mean(ns["ranges"]), 1) if ns["ranges"] else 0,
                "directions":   dict(ns["directions"]),
                "dominant_pattern": max(ns["patterns"], key=ns["patterns"].get) if ns["patterns"] else "N/A",
                "vah_hit_rate": f"{round(ns['vah_hits']/ns['count']*100, 1)}%" if ns["count"] else "0%",
                "poc_hit_rate": f"{round(ns['poc_hits']/ns['count']*100, 1)}%" if ns["count"] else "0%",
                "val_hit_rate": f"{round(ns['val_hits']/ns['count']*100, 1)}%" if ns["count"] else "0%",
                "ema_hit_rate": f"{round(ns['ema_hits']/ns['count']*100, 1)}%" if ns["count"] else "0%",
            }
            for ntype, ns in news_type_stats.items()
        },
        "value_area_all_thursdays": {
            "vah": {"hit_rate": f"{round(vah_hits/total_thu*100, 1) if total_thu else 0}%",
                    "avg_reaction_pts": round(vah_react_sum/vah_hits, 1) if vah_hits else 0},
            "poc": {"hit_rate": f"{round(poc_hits/total_thu*100, 1) if total_thu else 0}%",
                    "avg_reaction_pts": round(poc_react_sum/poc_hits, 1) if poc_hits else 0},
            "val": {"hit_rate": f"{round(val_hits/total_thu*100, 1) if total_thu else 0}%",
                    "avg_reaction_pts": round(val_react_sum/val_hits, 1) if val_hits else 0},
        },
        "ema200_all_thursdays": {
            "hit_rate":            f"{round(ema_hits/total_thu*100, 1) if total_thu else 0}%",
            "avg_reaction_pts":    round(ema_react_sum/ema_hits, 1) if ema_hits else 0,
            "open_above_ema_pct":  round(ema_above/total_thu*100, 1) if total_thu else 0,
        },
        "all_thursdays": thursday_results,
    }

    out_path = "data/research/backtest_thursday_noticias_1year.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n  ✅ Guardado → {out_path}\n")


if __name__ == "__main__":
    run_thursday_news_backtest()
