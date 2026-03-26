"""
╔══════════════════════════════════════════════════════════════════════════╗
║  BACKTEST · MARTES NQ NASDAQ · 1 AÑO                                    ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  Metodología exacta de trading aplicada a los MARTES:                   ║
║                                                                          ║
║  VOLUME PROFILE:                                                         ║
║    Asia 18:00 ET (Lunes) → 09:20 ET (Martes)   ← ANTES del open        ║
║    Niveles: VAH / POC / VAL  (70% del volumen)                          ║
║                                                                          ║
║  SESIONES:                                                               ║
║    • Asia      : 18:00 ET (Lun) → 01:00 ET (Mar)                       ║
║    • Londres   : 03:00 ET       → 08:30 ET                              ║
║    • NY Open   : 09:30 ET       → 16:00 ET                              ║
║                                                                          ║
║  MOVIMIENTO NY:                                                          ║
║    ny_move = close(16:00) − open(09:30)                                  ║
║                                                                          ║
║  NOTICIAS DEL MARTES (10:00 ET):                                        ║
║    • CB Consumer Confidence (mensual)                                   ║
║    • JOLTS Job Openings     (mensual)                                   ║
║    • PPI (ocasional, 08:30 ET)                                          ║
║    • Retail Sales advance   (ocasional)                                  ║
║    • Martes sin evento      (NONE)                                       ║
║                                                                          ║
║  Datos: data/research/nq_15m_intraday.csv                               ║
║  Periodo: últimos 365 días                                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
import pytz

ET = pytz.timezone("America/New_York")

# ─────────────────────────────────────────────────────────────────────────────
#  CALENDARIO ECONÓMICO — NOTICIAS QUE CAEN EN MARTES
#  Fuente: BLS, Fed, Conference Board, calendarios oficiales 2024-2025
# ─────────────────────────────────────────────────────────────────────────────
TUESDAY_NEWS = {
    # ── CB Consumer Confidence (último martes hábil del mes, ~10:00 ET)
    "2024-03-26": "CB_CONF",
    "2024-04-30": "CB_CONF",
    "2024-05-28": "CB_CONF",
    "2024-06-25": "CB_CONF",
    "2024-07-30": "CB_CONF",
    "2024-08-27": "CB_CONF",
    "2024-09-24": "CB_CONF",
    "2024-10-29": "CB_CONF",
    "2024-11-26": "CB_CONF",
    "2024-12-17": "CB_CONF",  # diciembre a veces cae antes
    "2025-01-28": "CB_CONF",
    "2025-02-25": "CB_CONF",
    "2025-03-25": "CB_CONF",

    # ── JOLTS Job Openings (~primer martes del mes, 10:00 ET)
    "2024-03-12": "JOLTS",
    "2024-04-02": "JOLTS",
    "2024-05-07": "JOLTS",
    "2024-06-04": "JOLTS",
    "2024-07-02": "JOLTS",
    "2024-08-06": "JOLTS",
    "2024-09-04": "JOLTS",  # próximo a Labor Day
    "2024-10-01": "JOLTS",
    "2024-11-05": "JOLTS",
    "2024-12-03": "JOLTS",
    "2025-01-07": "JOLTS",
    "2025-02-04": "JOLTS",
    "2025-03-11": "JOLTS",

    # ── PPI (Producer Price Index, 08:30 ET, cae en martes ocasionalmente)
    "2024-03-14": "PPI",    # PPI febr publicado en marzo
    "2024-06-11": "PPI",
    "2024-09-10": "PPI",
    "2024-12-10": "PPI",
    "2025-01-14": "PPI",
    "2025-02-13": "PPI",
    "2025-03-13": "PPI",

    # ── Retail Sales advance (08:30 ET, cae en martes ocasionalmente)
    "2024-04-16": "RETAIL_SALES",
    "2024-07-16": "RETAIL_SALES",
    "2024-10-17": "RETAIL_SALES",
    "2025-01-16": "RETAIL_SALES",

    # ── FOMC inicio de decisión (martes previo al miércoles de anuncio)
    "2024-04-30": "FOMC_DAY1",
    "2024-06-11": "FOMC_DAY1",
    "2024-07-30": "FOMC_DAY1",
    "2024-09-17": "FOMC_DAY1",
    "2024-11-05": "FOMC_DAY1",
    "2024-12-17": "FOMC_DAY1",
    "2025-01-28": "FOMC_DAY1",
    "2025-03-18": "FOMC_DAY1",

    # ── Martes post-NFP (lunes fue el siguiente y martes continúa digestión)
    "2024-03-12": "POST_NFP",
    "2024-05-07": "POST_NFP",
    "2024-07-09": "POST_NFP",

    # ── Earnings grandes (muevan índices pre-market)
    "2024-04-23": "EARNINGS",  # Google, MSFT
    "2024-07-23": "EARNINGS",  # GOOGL, TSLA
    "2024-10-22": "EARNINGS",  # Big tech semana

    # ── Días con Holiday previo (volumen alterado)
    "2024-05-28": "HOLIDAY_PREV",  # Martes después de Memorial Day
    "2024-09-03": "HOLIDAY_PREV",  # Martes después de Labor Day
    "2024-11-12": "HOLIDAY_PREV",  # Martes después de Veterans Day
    "2025-01-21": "HOLIDAY_PREV",  # Martes después de MLK Day
}

# Prioridad cuando hay conflicto de etiquetas el mismo día
NEWS_PRIORITY = [
    "EARNINGS", "FOMC_DAY1", "PPI", "RETAIL_SALES",
    "CB_CONF", "JOLTS", "POST_NFP", "HOLIDAY_PREV", "NONE"
]

NEWS_IMPACT = {
    "EARNINGS":    "ALTO",
    "FOMC_DAY1":   "ALTO",
    "PPI":         "MEDIO",
    "RETAIL_SALES":"MEDIO",
    "CB_CONF":     "MEDIO",
    "JOLTS":       "MEDIO",
    "POST_NFP":    "BAJO",
    "HOLIDAY_PREV":"LIGERO",
    "NONE":        "NORMAL",
}

NEWS_TIME = {
    "PPI":          "08:30",
    "RETAIL_SALES": "08:30",
    "CB_CONF":      "10:00",
    "JOLTS":        "10:00",
    "FOMC_DAY1":    "14:00",
    "EARNINGS":     "pre-mkt",
    "POST_NFP":     "—",
    "HOLIDAY_PREV": "—",
    "NONE":         "—",
}

NEWS_ICON = {
    "ALTO":    "🟠",
    "MEDIO":   "🟡",
    "BAJO":    "🔵",
    "LIGERO":  "⚫",
    "NORMAL":  "⚪",
}

PATTERN_NAMES = [
    "SWEEP_H_RETURN", "SWEEP_L_RETURN",
    "EXPANSION_H",    "EXPANSION_L",
    "ROTATION_POC",   "NEWS_DRIVE",
]

# ─────────────────────────────────────────────────────────────────────────────
#  VOLUME PROFILE — VP = Asia 18:00 ET (Lun) → 09:20 ET (Mar)
# ─────────────────────────────────────────────────────────────────────────────

def calc_vp(df_slice: pd.DataFrame, bins: int = 50, va_pct: float = 0.70):
    """
    Calcula VAH, POC, VAL distribuyendo volumen uniformemente en rango H-L
    de cada barra de 15 min.
    Returns: (vah, poc, val)
    """
    if df_slice.empty or len(df_slice) < 2:
        return None, None, None

    lo = df_slice["Low"].min()
    hi = df_slice["High"].max()
    if hi == lo:
        return None, None, None

    edges   = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols    = np.zeros(bins)

    for _, row in df_slice.iterrows():
        bar_lo, bar_hi = row["Low"], row["High"]
        bar_vol = row["Volume"] if row["Volume"] > 0 else 1
        mask  = (centers >= bar_lo) & (centers <= bar_hi)
        count = mask.sum()
        if count > 0:
            vols[mask] += bar_vol / count

    poc_idx = int(np.argmax(vols))
    poc     = float(centers[poc_idx])

    total_vol = vols.sum()
    target    = total_vol * va_pct
    lo_i, hi_i = poc_idx, poc_idx
    accum = float(vols[poc_idx])

    while accum < target and (lo_i > 0 or hi_i < bins - 1):
        lo_add = float(vols[lo_i - 1]) if lo_i > 0       else 0.0
        hi_add = float(vols[hi_i + 1]) if hi_i < bins - 1 else 0.0
        if lo_add >= hi_add and lo_i > 0:
            lo_i  -= 1; accum += lo_add
        elif hi_i < bins - 1:
            hi_i  += 1; accum += hi_add
        else:
            break

    return float(centers[hi_i]), poc, float(centers[lo_i])   # (vah, poc, val)


def get_ema200(df: pd.DataFrame) -> pd.Series:
    return df["Close"].ewm(span=200, adjust=False).mean()


def level_touched(data: pd.DataFrame, level: float, margin: float = 18.0) -> bool:
    return bool(((data["Low"] <= level + margin) & (data["High"] >= level - margin)).any())


def reaction_after_touch(data: pd.DataFrame, level: float, margin: float = 18.0) -> float:
    rows = data[(data["Low"] <= level + margin) & (data["High"] >= level - margin)]
    if rows.empty:
        return 0.0
    after = data.loc[rows.index[0]:]
    return float(after["High"].max() - after["Low"].min()) if not after.empty else 0.0


def bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


def get_news(date_str: str) -> str:
    """Retorna la etiqueta de noticia para ese Martes (prioridad más alta)."""
    raw = TUESDAY_NEWS.get(date_str, "NONE")
    return raw


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────────────────────

def run_tuesday_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Archivo no encontrado: {csv_path}")
        print("   Necesitas el CSV 15min NQ con columnas: Datetime, Open, High, Low, Close, Volume")
        return

    print("⏳ Cargando datos NQ 15min...")
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ["Datetime", "Close", "High", "Low", "Open", "Volume"]
    df = df.dropna(subset=["Datetime"])
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True).dt.tz_convert(ET)
    df.set_index("Datetime", inplace=True)
    df = df.sort_index()
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Volume"] = df["Volume"].fillna(1)
    df = df.dropna(subset=["Open", "High", "Low", "Close"])

    # Últimos 365 días
    end_date   = df.index.max()
    start_date = end_date - timedelta(days=365)
    df_window  = df.loc[start_date:]
    print(f"📅 Periodo: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")

    # EMA 200 sobre todo el histórico (más precisa)
    ema200_full = get_ema200(df)

    # Todos los días únicos en la ventana
    all_days = sorted(set(df_window.index.normalize().unique()))

    # ── Colectores ────────────────────────────────────────────────────────────
    all_results  = []
    tue_results  = []
    patterns_all = defaultdict(int)
    patterns_tue = defaultdict(int)

    news_stats = defaultdict(lambda: {
        "count": 0, "ranges": [], "asia_ranges": [],
        "directions": defaultdict(int),
        "patterns":   defaultdict(int),
        "vah_hits": 0, "poc_hits": 0, "val_hits": 0, "ema_hits": 0,
        "vah_react": 0.0, "poc_react": 0.0, "val_react": 0.0, "ema_react": 0.0,
        "open_above_ema": 0,
        "sessions": [],
    })

    tue_directions  = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    tue_ny_ranges   = []
    tue_asia_ranges = []
    vah_h=0; vah_r=0.0
    poc_h=0; poc_r=0.0
    val_h=0; val_r=0.0
    ema_h=0; ema_r=0.0
    ema_ab=0

    MARGIN = 20
    BUF    = 20

    for day_ts in all_days:
        day = day_ts.date()
        wd  = pd.Timestamp(day).weekday()   # 0=Lun … 4=Vie

        # ── Día anterior (Lunes si es Martes) ───────────────────────────────
        prev_day = day - timedelta(days=1)

        # ── Volume Profile: Asia 18:00 ET (Lun) → 09:20 ET (Mar) ────────────
        vp_start = ET.localize(datetime(prev_day.year, prev_day.month, prev_day.day, 18, 0))
        vp_end   = ET.localize(datetime(day.year,      day.month,      day.day,      9, 20))
        vp_data  = df[(df.index >= vp_start) & (df.index <= vp_end)]

        if vp_data.empty or len(vp_data) < 5:
            continue

        vah, poc, val = calc_vp(vp_data)

        # ── Rango Asia (18:00 Lun → 08:30 Mar) para medir extensión ─────────
        asia_start = vp_start
        asia_end   = ET.localize(datetime(day.year, day.month, day.day, 8, 30))
        asia_data  = df[(df.index >= asia_start) & (df.index <= asia_end)]
        if asia_data.empty:
            continue
        asia_high  = float(asia_data["High"].max())
        asia_low   = float(asia_data["Low"].min())
        asia_range = asia_high - asia_low

        # ── EMA 200 al open NY ───────────────────────────────────────────────
        try:
            ema_key = ET.localize(datetime(day.year, day.month, day.day, 9, 30))
            ema_at_open = float(ema200_full.loc[:ema_key].iloc[-1])
        except Exception:
            continue

        # ── NY Session ───────────────────────────────────────────────────────
        ny_start  = ET.localize(datetime(day.year, day.month, day.day, 9, 30))
        ny_end    = ET.localize(datetime(day.year, day.month, day.day, 16, 0))
        ny_early_end = ET.localize(datetime(day.year, day.month, day.day, 11, 30))

        ny_full  = df[(df.index >= ny_start)  & (df.index <= ny_end)]
        ny_early = df[(df.index >= ny_start)  & (df.index <= ny_early_end)]

        if ny_full.empty or len(ny_full) < 3:
            continue

        ny_open   = float(ny_full.iloc[0]["Open"])
        ny_close  = float(ny_full.iloc[-1]["Close"])
        ny_move   = ny_close - ny_open

        # Rango para clasificar patrón: usamos primera hora de NY
        if not ny_early.empty:
            ny_high = float(ny_early["High"].max())
            ny_low  = float(ny_early["Low"].min())
        else:
            ny_high = float(ny_full["High"].max())
            ny_low  = float(ny_full["Low"].min())
        ny_range = ny_high - ny_low

        # ── Dirección final (move completo del día) ──────────────────────────
        if ny_move > 30:
            direction = "BULLISH"
        elif ny_move < -30:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # ── Patrón ICT ───────────────────────────────────────────────────────
        p_type = "ROTATION_POC"
        if ny_range > 250:
            p_type = "NEWS_DRIVE"
        elif ny_high > asia_high + BUF:
            p_type = "SWEEP_H_RETURN" if ny_close < asia_high else "EXPANSION_H"
        elif ny_low < asia_low - BUF:
            p_type = "SWEEP_L_RETURN" if ny_close > asia_low else "EXPANSION_L"

        # ── Toques de niveles VP y EMA ───────────────────────────────────────
        vah_t = level_touched(ny_early, vah,         MARGIN) if vah is not None else False
        poc_t = level_touched(ny_early, poc,         MARGIN) if poc is not None else False
        val_t = level_touched(ny_early, val,         MARGIN) if val is not None else False
        ema_t = level_touched(ny_early, ema_at_open, MARGIN)

        vah_rv = reaction_after_touch(ny_early, vah,         MARGIN) if vah_t else 0.0
        poc_rv = reaction_after_touch(ny_early, poc,         MARGIN) if poc_t else 0.0
        val_rv = reaction_after_touch(ny_early, val,         MARGIN) if val_t else 0.0
        ema_rv = reaction_after_touch(ny_early, ema_at_open, MARGIN) if ema_t else 0.0

        # ── Noticia ──────────────────────────────────────────────────────────
        date_str  = str(day)
        news_type = get_news(date_str) if wd == 1 else "NONE"

        row = {
            "date":           date_str,
            "weekday":        pd.Timestamp(day).strftime("%A"),
            "weekday_num":    wd,
            "news_type":      news_type,
            "news_impact":    NEWS_IMPACT.get(news_type, "NORMAL"),
            "news_time":      NEWS_TIME.get(news_type, "—"),
            "pattern":        p_type,
            "direction":      direction,
            "ny_move":        round(ny_move, 1),
            "ny_range":       round(ny_range, 1),
            "ny_open":        round(ny_open, 2),
            "ny_close":       round(ny_close, 2),
            "asia_high":      round(asia_high, 2),
            "asia_low":       round(asia_low, 2),
            "asia_range":     round(asia_range, 1),
            "vp_vah":         round(vah, 2)  if vah else None,
            "vp_poc":         round(poc, 2)  if poc else None,
            "vp_val":         round(val, 2)  if val else None,
            "ema200":         round(ema_at_open, 2),
            "open_vs_ema":    round(ny_open - ema_at_open, 1),
            "open_above_ema": ny_open > ema_at_open,
            "vah_hit": vah_t, "vah_react": round(vah_rv, 1),
            "poc_hit": poc_t, "poc_react": round(poc_rv, 1),
            "val_hit": val_t, "val_react": round(val_rv, 1),
            "ema_hit": ema_t, "ema_react": round(ema_rv, 1),
        }

        all_results.append(row)
        patterns_all[p_type] += 1

        if wd != 1:
            continue   # Solo Martes

        # ── Colección específica Martes ───────────────────────────────────────
        tue_results.append(row)
        patterns_tue[p_type] += 1
        tue_ny_ranges.append(ny_range)
        tue_asia_ranges.append(asia_range)
        tue_directions[direction] += 1

        if vah_t: vah_h += 1; vah_r += vah_rv
        if poc_t: poc_h += 1; poc_r += poc_rv
        if val_t: val_h += 1; val_r += val_rv
        if ema_t: ema_h += 1; ema_r += ema_rv
        if ny_open > ema_at_open: ema_ab += 1

        # Por noticia
        ns = news_stats[news_type]
        ns["count"]     += 1
        ns["ranges"].append(ny_range)
        ns["asia_ranges"].append(asia_range)
        ns["directions"][direction] += 1
        ns["patterns"][p_type]      += 1
        if vah_t: ns["vah_hits"] += 1; ns["vah_react"] += vah_rv
        if poc_t: ns["poc_hits"] += 1; ns["poc_react"] += poc_rv
        if val_t: ns["val_hits"] += 1; ns["val_react"] += val_rv
        if ema_t: ns["ema_hits"] += 1; ns["ema_react"] += ema_rv
        if ny_open > ema_at_open: ns["open_above_ema"] += 1
        ns["sessions"].append({
            "date":       date_str,
            "pattern":    p_type,
            "direction":  direction,
            "ny_range":   round(ny_range, 1),
            "ny_move":    round(ny_move, 1),
            "asia_range": round(asia_range, 1),
        })

    # ══════════════════════════════════════════════════════════════════════════
    #  REPORTE
    # ══════════════════════════════════════════════════════════════════════════
    total_all = len(all_results)
    total_tue = len(tue_results)

    if total_tue == 0:
        print("❌ No se encontraron Martes en el periodo")
        return

    pct_all  = {k: round(v / total_all * 100, 1) for k, v in patterns_all.items()}
    pct_tue  = {k: round(v / total_tue * 100, 1) for k, v in patterns_tue.items()}
    dominant = max(patterns_tue, key=patterns_tue.get) if patterns_tue else "N/A"
    dom_pct  = pct_tue.get(dominant, 0)

    avg_range  = round(np.mean(tue_ny_ranges), 1)   if tue_ny_ranges   else 0
    max_range  = round(max(tue_ny_ranges), 1)        if tue_ny_ranges   else 0
    min_range  = round(min(tue_ny_ranges), 1)        if tue_ny_ranges   else 0
    avg_asia   = round(np.mean(tue_asia_ranges), 1)  if tue_asia_ranges else 0

    bull_pct = round(tue_directions["BULLISH"] / total_tue * 100, 1)
    bear_pct = round(tue_directions["BEARISH"] / total_tue * 100, 1)
    abp      = round(ema_ab / total_tue * 100, 1)
    blp      = round((total_tue - ema_ab) / total_tue * 100, 1)

    W   = 78
    SEP = "═" * W

    print(f"\n{SEP}")
    print(f"  🔬 BACKTEST MARTES · NQ NASDAQ · ÚLTIMOS 365 DÍAS")
    print(SEP)
    print(f"  📅 Periodo  : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  📊 Total sesiones    : {total_all}")
    print(f"  📌 Martes analizados : {total_tue}")

    # ── VP Metodología ───────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  🎯 METODOLOGÍA VOLUME PROFILE")
    print(f"{'─'*W}")
    print(f"  VP calculado: Asia 18:00 ET (Lun) → 09:20 ET (Mar)   ← ANTES del open")
    print(f"  Niveles usados: VAH (techo) / POC (centro) / VAL (base)")
    print(f"  Zona de valor  : 70% del volumen alrededor del POC")
    print(f"  Margen de toque: ±{MARGIN} puntos")

    # ── RANGO ────────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📏 RANGO — Primera hora NY (09:30–11:30)")
    print(f"{'─'*W}")
    print(f"  Rango NY promedio  : {avg_range} pts")
    print(f"  Rango NY máximo    : {max_range} pts")
    print(f"  Rango NY mínimo    : {min_range} pts")
    print(f"  Rango Asia/Londres : {avg_asia} pts (promedio)")

    r_buckets = {"0-100": 0, "100-200": 0, "200-300": 0, "300+": 0}
    for r in tue_ny_ranges:
        if   r <  100: r_buckets["0-100"]   += 1
        elif r <  200: r_buckets["100-200"] += 1
        elif r <  300: r_buckets["200-300"] += 1
        else:          r_buckets["300+"]    += 1

    print(f"\n  Distribución rango NY (primera hora):")
    for bucket, cnt in r_buckets.items():
        pct = round(cnt / total_tue * 100, 1)
        print(f"    {bucket:>10} pts : {cnt:>2} Martes ({pct:>5.1f}%)  {bar(pct, 15)}")

    # ── PATRONES ─────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📊 LOS 6 PATRONES ICT — MARTES vs TODOS LOS DÍAS  (delta)")
    print(f"{'─'*W}")
    print(f"  {'PATRÓN':<22} {'MARTES':>9} {'TODOS':>9} {'DELTA':>8}")
    print(f"  {'─'*52}")
    for p in PATTERN_NAMES:
        m  = pct_tue.get(p, 0)
        a  = pct_all.get(p, 0)
        d  = round(m - a, 1)
        ds = f"+{d}" if d > 0 else str(d)
        mk = "  ◀ DOMINANTE" if p == dominant else ""
        print(f"  {p:<22} {m:>8.1f}% {a:>8.1f}% {ds:>7}%{mk}")

    print(f"\n  🏆 PATRÓN DOMINANTE LOS MARTES: {dominant}  ({dom_pct}%)")

    # ── DIRECCIÓN ────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📈 DIRECCIÓN NY — cierre 16:00 vs apertura 09:30")
    print(f"{'─'*W}")
    for d, cnt in tue_directions.items():
        pct  = round(cnt / total_tue * 100, 1)
        icon = "🟢" if d == "BULLISH" else ("🔴" if d == "BEARISH" else "🟡")
        print(f"  {icon} {d:<10} {cnt:>3} Martes  ({pct:>5.1f}%)  {bar(pct, 18)}")

    print(f"\n  → Sesgo histórico: {'ALCISTA' if bull_pct > bear_pct else 'BAJISTA'} "
          f"({max(bull_pct, bear_pct)}% vs {min(bull_pct, bear_pct)}%)")

    # ── VOLUME PROFILE ───────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  📐 VOLUME PROFILE  (Asia 18:00 ET Lun → 09:20 ET Mar)")
    print(f"{'─'*W}")

    def lvl_row(name, hits, react_sum, total):
        hp   = round(hits / total * 100, 1) if total else 0
        avgr = round(react_sum / hits, 1)   if hits  else 0
        print(f"  {name:<14} {hits:>2}/{total}  ({hp:>5.1f}%)   reacción prom: {avgr:>6.1f} pts  {bar(hp, 12)}")

    lvl_row("VAH (techo)",  vah_h, vah_r, total_tue)
    lvl_row("POC (centro)", poc_h, poc_r, total_tue)
    lvl_row("VAL (base)",   val_h, val_r, total_tue)

    print(f"\n  📉 EMA 200 (15min) al momento de apertura NY")
    ep  = round(ema_h / total_tue * 100, 1) if total_tue else 0
    ear = round(ema_r / ema_h, 1)           if ema_h    else 0
    print(f"  Toca EMA200         : {ema_h}/{total_tue} ({ep}%)   Reacción prom: {ear} pts")
    print(f"  Abre SOBRE  EMA200  : {ema_ab}/{total_tue} ({abp}%)   → contexto alcista")
    print(f"  Abre DEBAJO EMA200  : {total_tue - ema_ab}/{total_tue} ({blp}%)   → contexto bajista")

    # ── NOTICIAS ─────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  📰 NOTICIAS QUE CAEN EN MARTES — IMPACTO EN NQ")
    print(f"{'─'*W}")
    print(f"  {'TIPO':<14} {'HORA':<8} {'IMP':<8} {'N':<4} {'RANGO':<10} {'PAT.DOM.':<22} {'BULL%':<8} {'BEAR%'}")
    print(f"  {'─'*76}")

    for ntype in NEWS_PRIORITY:
        ns = news_stats.get(ntype)
        if not ns or ns["count"] == 0:
            continue
        n     = ns["count"]
        avgr  = round(np.mean(ns["ranges"]), 1)
        dom_p = max(ns["patterns"], key=ns["patterns"].get) if ns["patterns"] else "N/A"
        dom_pp= round(ns["patterns"][dom_p] / n * 100, 1)
        bull  = round(ns["directions"]["BULLISH"] / n * 100, 1)
        bear  = round(ns["directions"]["BEARISH"] / n * 100, 1)
        impact= NEWS_IMPACT.get(ntype, "NORMAL")
        icon  = NEWS_ICON.get(impact, "⚪")
        hora  = NEWS_TIME.get(ntype, "—")
        print(f"  {icon}{ntype:<13} {hora:<8} {impact:<8} {n:<4} {avgr:>7.1f}pts   "
              f"{dom_p:<18} ({dom_pp:.0f}%)  {bull:>5.1f}%  {bear:>5.1f}%")

    # ── RANGO POR TIPO DE NOTICIA ────────────────────────────────────────────
    print(f"\n  📊 RANGO PROMEDIO POR TIPO DE NOTICIA vs MARTES SIN EVENTO")
    print(f"  {'─'*55}")
    none_ranges = news_stats["NONE"]["ranges"] if news_stats["NONE"]["count"] > 0 else tue_ny_ranges
    none_avg    = round(np.mean(none_ranges), 1) if none_ranges else avg_range
    print(f"  {'NONE (sin evento)':<20} → {none_avg:>7.1f} pts  (referencia base)")
    for ntype in NEWS_PRIORITY:
        ns = news_stats.get(ntype)
        if not ns or ns["count"] == 0 or ntype == "NONE":
            continue
        avgr  = round(np.mean(ns["ranges"]), 1)
        mult  = round(avgr / none_avg, 2) if none_avg else 0
        arrow = "⬆" if mult > 1.1 else ("⬇" if mult < 0.9 else "➡")
        print(f"  {ntype:<20} → {avgr:>7.1f} pts  {arrow} {mult:.2f}x vs NONE")

    # ── VP: comportamiento por noticia ───────────────────────────────────────
    print(f"\n  🎯 RESPETO AL VP POR TIPO DE NOTICIA")
    print(f"  {'─'*55}")
    print(f"  {'TIPO':<14} {'VAH%':>6} {'POC%':>6} {'VAL%':>6} {'EMA%':>6}")
    print(f"  {'─'*44}")
    for ntype in NEWS_PRIORITY:
        ns = news_stats.get(ntype)
        if not ns or ns["count"] == 0:
            continue
        n = ns["count"]
        print(f"  {ntype:<14} "
              f"{round(ns['vah_hits']/n*100,1):>5.1f}%  "
              f"{round(ns['poc_hits']/n*100,1):>5.1f}%  "
              f"{round(ns['val_hits']/n*100,1):>5.1f}%  "
              f"{round(ns['ema_hits']/n*100,1):>5.1f}%")

    # ── DETALLE CADA MARTES ──────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📋 DETALLE CADA MARTES (último año)")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<13} {'NOTICIA':<14} {'HORA':<7} {'PATRÓN':<22} {'DIR':<9} {'MOVE':>7} {'RANGO':>7} {'EMA'}")
    print(f"  {'─'*84}")
    for r in sorted(tue_results, key=lambda x: x["date"]):
        icon    = NEWS_ICON.get(r["news_impact"], "⚪")
        ema_mk  = "↑" if r["open_above_ema"] else "↓"
        move_mk = f"{r['ny_move']:+.0f}"
        print(f"  {r['date']:<13} {icon}{r['news_type']:<13} {r['news_time']:<7} "
              f"{r['pattern']:<22} {r['direction']:<9} {move_mk:>6}pts "
              f"{r['ny_range']:>5.0f}pts  {r['ema200']:>7.0f}{ema_mk}")

    # ── CONCLUSIONES ─────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  💡 CONCLUSIONES OPERATIVAS — MARTES NQ")
    print(SEP)

    if dominant == "NEWS_DRIVE":
        print(f"  ⚡ ALTA VOLATILIDAD — NEWS_DRIVE domina los Martes ({dom_pct}%)")
        print(f"     → Esperar confirmación tras la noticia de las 10:00 ET")
    elif dominant in ["SWEEP_H_RETURN", "SWEEP_L_RETURN"]:
        print(f"  🎯 SWEEP & RETURN es el patrón dominante ({dom_pct}%)")
        print(f"     → Buscar barrido del High/Low asiático y entrar en contra")
    elif dominant in ["EXPANSION_H", "EXPANSION_L"]:
        print(f"  🚀 EXPANSION domina ({dom_pct}%) — seguir la ruptura del rango")
        print(f"     → No ir en contra de la tendencia inicial del Martes")
    else:
        print(f"  🔄 ROTACIÓN POC domina ({dom_pct}%) — mercado en rango")
        print(f"     → Scalp entre VAH y VAL, respetar POC como pivot")

    niveles = [("VAH", vah_h, vah_r), ("POC", poc_h, poc_r),
               ("VAL", val_h, val_r), ("EMA200", ema_h, ema_r)]
    mejor = max(niveles, key=lambda x: (x[1], x[2]))
    mejor_react = round(mejor[2] / mejor[1], 1) if mejor[1] else 0

    print(f"\n  🔑 NIVEL MÁS RESPETADO: {mejor[0]}")
    print(f"     Tocado en {mejor[1]}/{total_tue} Martes | Reacción prom: {mejor_react} pts")

    print(f"\n  📈 SESGO MARTES: {bull_pct}% BULLISH | {bear_pct}% BEARISH")
    if bull_pct > 55:
        print(f"     → Los Martes tienen sesgo ALCISTA — priorizar longs")
    elif bear_pct > 55:
        print(f"     → Los Martes tienen sesgo BAJISTA — priorizar shorts")
    else:
        print(f"     → Dirección equilibrada — respetar la estructura del día")

    news_with_data = [(ntype, round(np.mean(ns["ranges"]), 1))
                      for ntype, ns in news_stats.items()
                      if ns["count"] > 0 and ntype != "NONE"]
    if news_with_data:
        max_news = max(news_with_data, key=lambda x: x[1])
        print(f"\n  📰 NOTICIA CON MAYOR EXPANSIÓN: {max_news[0]}")
        print(f"     Rango prom con esa noticia: {max_news[1]} pts vs {none_avg} pts (NONE)")

    print(f"\n  ⏰ NOTA OPERATIVA MARTES:")
    print(f"     • 09:30 ET — NY abre: posicionarse respecto a VAH/POC/VAL del VP")
    print(f"     • 10:00 ET — Noticia (CB Conf / JOLTS): spike + retesteo de niveles VP")
    print(f"     • 11:00 ET — Segundo movimiento tras digestión de la noticia")
    print(SEP)

    # ── GUARDAR JSON ──────────────────────────────────────────────────────────
    report = {
        "title":            "Backtest Martes NQ · 1 Año · Metodología VP",
        "period":           f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        "methodology": {
            "vp_window":    "Asia 18:00 ET (Lun) → 09:20 ET (Mar)",
            "va_pct":       "70%",
            "ny_move":      "close(16:00) - open(09:30)",
            "range_window": "09:30-11:30 ET (primera hora)",
        },
        "total_days":       total_all,
        "total_tuesdays":   total_tue,
        "dominant_pattern": dominant,
        "dominant_pct":     dom_pct,
        "avg_ny_range":     avg_range,
        "max_ny_range":     max_range,
        "min_ny_range":     min_range,
        "avg_asia_range":   avg_asia,
        "directions":       dict(tue_directions),
        "patterns": {k: f"{v:.1f}%" for k, v in pct_tue.items()},
        "patterns_all_days":{k: f"{v:.1f}%" for k, v in pct_all.items()},
        "range_distribution": dict(r_buckets),
        "value_area": {
            "vah": {"hit_rate": f"{round(vah_h/total_tue*100,1) if total_tue else 0}%",
                    "avg_reaction": round(vah_r/vah_h,1) if vah_h else 0},
            "poc": {"hit_rate": f"{round(poc_h/total_tue*100,1) if total_tue else 0}%",
                    "avg_reaction": round(poc_r/poc_h,1) if poc_h else 0},
            "val": {"hit_rate": f"{round(val_h/total_tue*100,1) if total_tue else 0}%",
                    "avg_reaction": round(val_r/val_h,1) if val_h else 0},
        },
        "ema200": {
            "hit_rate":       f"{round(ema_h/total_tue*100,1) if total_tue else 0}%",
            "avg_reaction":   round(ema_r/ema_h,1) if ema_h else 0,
            "open_above_pct": abp,
            "open_below_pct": blp,
        },
        "by_news_type": {
            ntype: {
                "count":           ns["count"],
                "avg_ny_range":    round(np.mean(ns["ranges"]),1)      if ns["ranges"]      else 0,
                "avg_asia_range":  round(np.mean(ns["asia_ranges"]),1) if ns["asia_ranges"] else 0,
                "news_time_et":    NEWS_TIME.get(ntype, "—"),
                "impact":          NEWS_IMPACT.get(ntype, "NORMAL"),
                "directions":      dict(ns["directions"]),
                "dominant_pattern":max(ns["patterns"], key=ns["patterns"].get) if ns["patterns"] else "N/A",
                "patterns":        dict(ns["patterns"]),
                "vah_hit_rate":    f"{round(ns['vah_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "poc_hit_rate":    f"{round(ns['poc_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "val_hit_rate":    f"{round(ns['val_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "ema_hit_rate":    f"{round(ns['ema_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "open_above_ema":  f"{round(ns['open_above_ema']/ns['count']*100,1) if ns['count'] else 0}%",
                "sessions":        ns["sessions"],
            }
            for ntype, ns in news_stats.items() if ns["count"] > 0
        },
        "all_tuesdays": tue_results,
    }

    out_path = "data/research/backtest_martes_vp.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False, default=str)

    print(f"\n  ✅ JSON guardado → {out_path}\n")
    return report


if __name__ == "__main__":
    run_tuesday_backtest()
