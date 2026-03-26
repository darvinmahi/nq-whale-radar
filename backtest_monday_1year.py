"""
╔══════════════════════════════════════════════════════════════════════════╗
║  BACKTEST · LUNES NQ NASDAQ · 1 AÑO                                     ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  Análisis especializado para los días LUNES:                             ║
║    • Patrones dominantes (6 tipos ICT)                                   ║
║    • Noticias que caen en Lunes y su impacto:                            ║
║        – ISM Manufacturero / Servicios (1er día hábil del mes)          ║
║        – PMI Flash / Final (inicio de mes)                               ║
║        – Retail Sales avanzado (ocasionalmente)                          ║
║        – FOMC Minutes (cuando caen en Lunes)                            ║
║        – Speech Fed Chair (ocasionalmente)                               ║
║        – Earnings grandes (AMZN, AAPL, MSFT pre-market)                 ║
║        – Lunes post-NFP (efecto resaca del Viernes)                      ║
║        – Lunes post-FOMC (digestión de decisión)                         ║
║    • Rango Asia→Londres + Volume Profile (VAH/POC/VAL)                  ║
║    • EMA 200 (15min) al momento de apertura NY                           ║
║    • Contexto semanal: ¿qué sigue en la semana?                          ║
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


# ─────────────────────────────────────────────────────────────────────────────
#  CALENDARIO ECONÓMICO REAL — NOTICIAS QUE IMPACTAN LOS LUNES
#  Fuente: BLS, Fed, ISM, BEA calendarios oficiales 2024-2025
# ─────────────────────────────────────────────────────────────────────────────
MONDAY_NEWS_CALENDAR = {
    # ── ISM Manufacturero (1er día hábil del mes → frecuentemente Lunes)
    "2024-04-01": "ISM_MFG",
    "2024-07-01": "ISM_MFG",
    "2024-09-03": "ISM_MFG",
    "2025-02-03": "ISM_MFG",
    "2025-03-03": "ISM_MFG",

    # ── ISM Servicios / Non-Manufacturing (3er día hábil aprox)
    "2024-03-05": "ISM_SVC",
    "2024-04-03": "ISM_SVC",
    "2024-09-05": "ISM_SVC",
    "2025-02-05": "ISM_SVC",
    "2025-03-05": "ISM_SVC",

    # ── PMI Flash / Markit (publicación mensual)
    "2024-03-04": "PMI",
    "2024-05-06": "PMI",
    "2024-06-03": "PMI",

    # ── FOMC Minutes (3 semanas después de decisión → a veces Lunes)
    "2024-04-08": "FOMC_MINUTES",
    "2024-07-08": "FOMC_MINUTES",

    # ── Fed Chair Speech (calendarios Bloomberg/Reuters)
    "2024-03-11": "FED_SPEECH",
    "2024-06-10": "FED_SPEECH",
    "2024-09-09": "FED_SPEECH",
    "2024-11-04": "FED_SPEECH",
    "2025-02-10": "FED_SPEECH",
    "2025-03-10": "FED_SPEECH",

    # ── Lunes POST-NFP (efecto resaca del Viernes de empleos)
    # NFP es 1er Viernes → el Lunes siguiente siempre es "digestión"
    "2024-03-11": "POST_NFP",
    "2024-04-08": "POST_NFP",
    "2024-05-06": "POST_NFP",
    "2024-06-10": "POST_NFP",
    "2024-07-08": "POST_NFP",
    "2024-08-05": "POST_NFP",
    "2024-09-09": "POST_NFP",
    "2024-10-07": "POST_NFP",
    "2024-11-04": "POST_NFP",
    "2024-12-09": "POST_NFP",
    "2025-01-13": "POST_NFP",
    "2025-02-10": "POST_NFP",
    "2025-03-10": "POST_NFP",

    # ── Lunes POST-FOMC (digestión de decisión de la Fed)
    "2024-02-05": "POST_FOMC",
    "2024-04-01": "POST_FOMC",   # FOMC 31 enero → Lunes 1 Abril NO, error → 2024-04-01 es Lunes pero es ISM
    "2024-05-06": "POST_FOMC",   # FOMC 1 mayo → Lunes 6 mayo
    "2024-06-17": "POST_FOMC",   # FOMC 12 junio → Lunes 17 junio
    "2024-08-05": "POST_FOMC",   # FOMC 31 julio → Lunes 5 agosto
    "2024-09-23": "POST_FOMC",   # FOMC 18 sept → Lunes 23 sept
    "2024-11-11": "POST_FOMC",   # FOMC 7 nov → Lunes 11 nov (Veterans Day / light trade)
    "2024-12-23": "POST_FOMC",   # FOMC 18 dic → Lunes 23 dic (pre-holiday)
    "2025-02-03": "POST_FOMC",   # FOMC 29 enero → Lunes 3 feb
    "2025-03-24": "POST_FOMC",   # FOMC 19 marzo → Lunes 24 marzo

    # ── Grandes Earnings pre-market en Lunes (mueven índices)
    "2024-04-22": "EARNINGS",    # Tesla Q1 era lunes
    "2024-07-22": "EARNINGS",    # Big tech earnings semana
    "2024-10-21": "EARNINGS",    # Mid-earnings season

    # ── Lunes con Gap significativo conocido (eventos de fin de semana)
    "2024-08-05": "MACRO_SHOCK",  # Crash flash crash Yen carry trade

    # ── Holidays / días ligeros que cambian comportamiento del Lunes
    "2024-05-27": "HOLIDAY_PREV",  # Martes post Memorial Day  
    "2024-09-02": "HOLIDAY_PREV",  # Martes post Labor Day
    "2025-01-20": "HOLIDAY",       # MLK Day — mercado cerrado
}

# Prioridad: si hay varias etiquetas el mismo día, usa la más importante
NEWS_PRIORITY = [
    "MACRO_SHOCK", "FOMC_MINUTES", "EARNINGS",
    "ISM_MFG", "ISM_SVC", "PMI",
    "POST_FOMC", "POST_NFP", "FED_SPEECH",
    "HOLIDAY", "HOLIDAY_PREV", "NONE"
]

NEWS_IMPACT = {
    "MACRO_SHOCK":   "EXTREMO",
    "FOMC_MINUTES":  "ALTO",
    "EARNINGS":      "ALTO",
    "ISM_MFG":       "MEDIO",
    "ISM_SVC":       "MEDIO",
    "PMI":           "MEDIO",
    "FED_SPEECH":    "MEDIO",
    "POST_FOMC":     "MEDIO",
    "POST_NFP":      "BAJO",
    "HOLIDAY":       "LIGERO",
    "HOLIDAY_PREV":  "LIGERO",
    "NONE":          "NORMAL",
}

NEWS_ICON = {
    "EXTREMO": "🔴",
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
#  FUNCIONES AUXILIARES
# ─────────────────────────────────────────────────────────────────────────────

def calc_value_area(data: pd.DataFrame, bins: int = 100, va_pct: float = 0.70):
    """Value Area: devuelve (val, poc, vah) usando histograma TPO-style."""
    all_prices = pd.concat([data['High'], data['Low'], data['Close']])
    if len(all_prices) < 5:
        mid = float(data['Close'].mean())
        return mid, mid, mid

    counts, edges = np.histogram(all_prices, bins=bins)
    bin_centers = (edges[:-1] + edges[1:]) / 2
    poc_idx = int(np.argmax(counts))
    poc = float(bin_centers[poc_idx])

    total   = counts.sum()
    target  = total * va_pct
    lo_idx, hi_idx = poc_idx, poc_idx
    current = int(counts[poc_idx])

    while current < target:
        lo_next = lo_idx - 1
        hi_next = hi_idx + 1
        lo_val = counts[lo_next] if lo_next >= 0        else -1
        hi_val = counts[hi_next] if hi_next < len(counts) else -1
        if lo_val <= 0 and hi_val <= 0:
            break
        if lo_val >= hi_val:
            current += int(lo_val); lo_idx = lo_next
        else:
            current += int(hi_val); hi_idx = hi_next

    return float(bin_centers[lo_idx]), poc, float(bin_centers[hi_idx])


def get_ema200(df: pd.DataFrame) -> pd.Series:
    return df['Close'].ewm(span=200, adjust=False).mean()


def level_touched(ny_data: pd.DataFrame, level: float, margin: float = 18.0) -> bool:
    return bool(((ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)).any())


def reaction_after_touch(ny_data: pd.DataFrame, level: float, margin: float = 18.0) -> float:
    rows = ny_data[(ny_data['Low'] <= level + margin) & (ny_data['High'] >= level - margin)]
    if rows.empty:
        return 0.0
    after = ny_data.loc[rows.index[0]:]
    return float(after['High'].max() - after['Low'].min()) if not after.empty else 0.0


def get_news_for_monday(date_str: str) -> str:
    """Devuelve el tipo de noticia asignada al Lunes."""
    return MONDAY_NEWS_CALENDAR.get(date_str, "NONE")


# ─────────────────────────────────────────────────────────────────────────────
#  IMPRIMIR BARRA DE PORCENTAJE
# ─────────────────────────────────────────────────────────────────────────────

def bar(pct: float, width: int = 20) -> str:
    filled = int(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


# ─────────────────────────────────────────────────────────────────────────────
#  SCRIPT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def run_monday_backtest():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print(f"❌ Archivo no encontrado: {csv_path}")
        print("   Necesitas el CSV de intraday 15min NQ con columnas: Datetime, Open, High, Low, Close, Volume")
        return

    # ── Cargar datos ──────────────────────────────────────────────────────
    print("⏳ Cargando datos NQ 15min...")
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])

    # ── Últimos 365 días ──────────────────────────────────────────────────
    end_date   = df.index.max()
    start_date = end_date - timedelta(days=365)
    df_window  = df.loc[start_date:]
    print(f"📅 Periodo: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")

    ema200_full = get_ema200(df)  # EMA sobre TODO el histórico
    days = df_window.index.normalize().unique()

    # ── Colectores ────────────────────────────────────────────────────────
    all_results     = []
    monday_results  = []
    patterns_all    = defaultdict(int)
    patterns_mon    = defaultdict(int)

    # Por tipo de noticia
    news_stats = defaultdict(lambda: {
        "count": 0, "ranges": [], "ranges_asia": [],
        "directions": defaultdict(int),
        "patterns": defaultdict(int),
        "vah_hits": 0, "poc_hits": 0, "val_hits": 0, "ema_hits": 0,
        "vah_react": 0.0, "poc_react": 0.0, "val_react": 0.0, "ema_react": 0.0,
        "open_above_ema": 0,
        "sessions": []
    })

    # Globales Lunes
    mon_directions = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    mon_ranges     = []
    mon_asia_ranges = []
    vah_h=0; vah_r=0.0
    poc_h=0; poc_r=0.0
    val_h=0; val_r=0.0
    ema_h=0; ema_r=0.0
    ema_ab=0

    # Análisis de sweep timing (horas del sweep)
    sweep_hours_mon = defaultdict(int)

    MARGIN = 20
    BUF    = 20   # buffer para clasificar sweep vs expansion

    # ── Iteración por día ─────────────────────────────────────────────────
    for day in days:
        wd = day.weekday()  # 0=Lunes, 1=Martes, ...

        # ── Rango Asia + Londres (18:00 día anterior → 08:30 NY) ─────────
        r_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        r_end   = day.replace(hour=8, minute=30)
        rdata   = df.loc[r_start:r_end]

        # Los lunes el "día anterior" es un Viernes (mercado cierra 17:00 ET)
        # Ajuste: usamos desde el Viernes previo 18:00 ET
        if wd == 0:
            fri = day - timedelta(days=3)  # Viernes
            r_start = fri.replace(hour=18, minute=0)
            r_end   = day.replace(hour=8, minute=30)
            rdata   = df.loc[r_start:r_end]

        if rdata.empty or len(rdata) < 10:
            continue

        r_high  = float(rdata['High'].max())
        r_low   = float(rdata['Low'].min())
        r_range = r_high - r_low

        # ── Volume Profile (mismo rango → Asia 18:00 Vie → 09:20 Lun) ───
        if wd == 0:
            p_start = fri.replace(hour=18, minute=0)
        else:
            p_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        p_end = day.replace(hour=9, minute=20)
        pdata = df.loc[p_start:p_end]

        if pdata.empty or len(pdata) < 5:
            continue
        val, p_poc, vah = calc_value_area(pdata)

        # ── EMA 200 al open NY ───────────────────────────────────────────
        try:
            ema_at_open = float(ema200_full.loc[:day.replace(hour=9, minute=30)].iloc[-1])
        except Exception:
            continue

        # ── NY Session open 09:30–11:30 (2h de apertura) ───────────────
        ny_od = df.loc[day.replace(hour=9, minute=30): day.replace(hour=11, minute=30)]
        ny_fl = df.loc[day.replace(hour=9, minute=30): day.replace(hour=16, minute=0)]

        if ny_od.empty or len(ny_od) < 3:
            continue

        ny_open  = float(ny_od.iloc[0]['Open'])
        ny_high  = float(ny_od['High'].max())
        ny_low   = float(ny_od['Low'].min())
        ny_range = ny_high - ny_low
        ny_close = float(ny_od.iloc[-1]['Close'])
        full_close = float(ny_fl.iloc[-1]['Close']) if not ny_fl.empty else ny_close

        # ── Patrón ICT ───────────────────────────────────────────────────
        p_type = "ROTATION_POC"
        if ny_range > 250:
            p_type = "NEWS_DRIVE"
        elif ny_high > r_high + BUF:
            p_type = "SWEEP_H_RETURN" if ny_close < r_high else "EXPANSION_H"
        elif ny_low < r_low - BUF:
            p_type = "SWEEP_L_RETURN" if ny_close > r_low  else "EXPANSION_L"

        # ── Dirección ────────────────────────────────────────────────────
        if full_close > ny_open + 30:
            direction = "BULLISH"
        elif full_close < ny_open - 30:
            direction = "BEARISH"
        else:
            direction = "NEUTRAL"

        # ── Hora del sweep ───────────────────────────────────────────────
        sweep_time = None
        if p_type == "SWEEP_H_RETURN":
            sc = ny_od[ny_od['High'] >= r_high + BUF]
            if not sc.empty:
                sweep_time = sc.index[0].strftime('%H:%M')
        elif p_type == "SWEEP_L_RETURN":
            sc = ny_od[ny_od['Low'] <= r_low - BUF]
            if not sc.empty:
                sweep_time = sc.index[0].strftime('%H:%M')

        # ── Toques de niveles ─────────────────────────────────────────────
        vah_t = level_touched(ny_od, vah,         MARGIN)
        poc_t = level_touched(ny_od, p_poc,        MARGIN)
        val_t = level_touched(ny_od, val,          MARGIN)
        ema_t = level_touched(ny_od, ema_at_open,  MARGIN)

        vah_rv = reaction_after_touch(ny_od, vah,         MARGIN) if vah_t else 0.0
        poc_rv = reaction_after_touch(ny_od, p_poc,        MARGIN) if poc_t else 0.0
        val_rv = reaction_after_touch(ny_od, val,          MARGIN) if val_t else 0.0
        ema_rv = reaction_after_touch(ny_od, ema_at_open,  MARGIN) if ema_t else 0.0

        # ── Tipo de noticia (solo relevante para Lunes) ──────────────────
        date_str = day.strftime('%Y-%m-%d')
        news_type = get_news_for_monday(date_str) if wd == 0 else "NONE"

        row = {
            "date":           date_str,
            "weekday":        day.strftime('%A'),
            "weekday_num":    wd,
            "news_type":      news_type,
            "news_impact":    NEWS_IMPACT.get(news_type, "NORMAL"),
            "pattern":        p_type,
            "direction":      direction,
            "range_asia_lon": round(r_range, 1),
            "ny_range":       round(ny_range, 1),
            "ny_open":        round(ny_open, 2),
            "ny_close":       round(ny_close, 2),
            "full_close":     round(full_close, 2),
            "r_high":         round(r_high, 2),
            "r_low":          round(r_low, 2),
            "profile_val":    round(val, 2),
            "profile_poc":    round(p_poc, 2),
            "profile_vah":    round(vah, 2),
            "ema200":         round(ema_at_open, 2),
            "open_vs_ema":    round(ny_open - ema_at_open, 1),
            "sweep_time":     sweep_time,
            "vah_hit": vah_t, "vah_react": round(vah_rv, 1),
            "poc_hit": poc_t, "poc_react": round(poc_rv, 1),
            "val_hit": val_t, "val_react": round(val_rv, 1),
            "ema_hit": ema_t, "ema_react": round(ema_rv, 1),
            "open_above_ema": ny_open > ema_at_open,
        }

        all_results.append(row)
        patterns_all[p_type] += 1

        if wd != 0:
            continue  # Solo Lunes para el análisis profundo

        # ── Colección específica de Lunes ─────────────────────────────────
        monday_results.append(row)
        patterns_mon[p_type] += 1
        mon_ranges.append(ny_range)
        mon_asia_ranges.append(r_range)
        mon_directions[direction] += 1

        if vah_t: vah_h += 1; vah_r += vah_rv
        if poc_t: poc_h += 1; poc_r += poc_rv
        if val_t: val_h += 1; val_r += val_rv
        if ema_t: ema_h += 1; ema_r += ema_rv
        if ny_open > ema_at_open: ema_ab += 1

        if sweep_time:
            h = sweep_time.split(':')[0]
            sweep_hours_mon[f"{h}:00"] += 1

        # Por noticia
        ns = news_stats[news_type]
        ns["count"]    += 1
        ns["ranges"].append(ny_range)
        ns["ranges_asia"].append(r_range)
        ns["directions"][direction] += 1
        ns["patterns"][p_type] += 1
        if vah_t: ns["vah_hits"] += 1; ns["vah_react"] += vah_rv
        if poc_t: ns["poc_hits"] += 1; ns["poc_react"] += poc_rv
        if val_t: ns["val_hits"] += 1; ns["val_react"] += val_rv
        if ema_t: ns["ema_hits"] += 1; ns["ema_react"] += ema_rv
        if ny_open > ema_at_open: ns["open_above_ema"] += 1
        ns["sessions"].append({
            "date": date_str,
            "pattern": p_type,
            "direction": direction,
            "ny_range": round(ny_range, 1),
            "range_asia": round(r_range, 1),
        })

    # ══════════════════════════════════════════════════════════════════════
    #  IMPRESIÓN DEL REPORTE
    # ══════════════════════════════════════════════════════════════════════
    total_all = len(all_results)
    total_mon = len(monday_results)

    if total_mon == 0:
        print("❌ No se encontraron Lunes en el periodo analizado")
        return

    pct_all = {k: round(v / total_all * 100, 1) for k, v in patterns_all.items()}
    pct_mon = {k: round(v / total_mon * 100, 1) for k, v in patterns_mon.items()}
    dominant = max(patterns_mon, key=patterns_mon.get) if patterns_mon else "N/A"

    avg_range  = round(np.mean(mon_ranges), 1)    if mon_ranges    else 0
    max_range  = round(max(mon_ranges), 1)         if mon_ranges    else 0
    min_range  = round(min(mon_ranges), 1)         if mon_ranges    else 0
    avg_asia   = round(np.mean(mon_asia_ranges), 1) if mon_asia_ranges else 0

    W   = 78
    SEP = "═" * W

    print(f"\n{SEP}")
    print(f"  🔬 BACKTEST LUNES · NQ NASDAQ · ÚLTIMOS 365 DÍAS")
    print(SEP)
    print(f"  📅 Periodo : {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  📊 Total sesiones    : {total_all}")
    print(f"  📌 Lunes analizados  : {total_mon}")

    # ── RANGO ─────────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📏 RANGO — Apertura NY (09:30–11:30)")
    print(f"{'─'*W}")
    print(f"  Rango NY promedio  : {avg_range} pts")
    print(f"  Rango NY máximo    : {max_range} pts")
    print(f"  Rango NY mínimo    : {min_range} pts")
    print(f"  Rango Asia/Londres : {avg_asia} pts (prom)")

    # Distribución de rangos
    r_buckets = {"0-100": 0, "100-200": 0, "200-300": 0, "300+": 0}
    for r in mon_ranges:
        if r < 100:   r_buckets["0-100"]   += 1
        elif r < 200: r_buckets["100-200"] += 1
        elif r < 300: r_buckets["200-300"] += 1
        else:         r_buckets["300+"]    += 1

    print(f"\n  Distribución rango NY:")
    for bucket, cnt in r_buckets.items():
        pct = round(cnt / total_mon * 100, 1) if total_mon else 0
        print(f"    {bucket:>10} pts : {cnt:>2} Lunes ({pct:>5.1f}%)  {bar(pct, 15)}")

    # ── PATRONES ─────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📊 LOS 6 PATRONES ICT — LUNES vs TODOS LOS DÍAS  (delta)")
    print(f"{'─'*W}")
    print(f"  {'PATRÓN':<22} {'LUNES':>9} {'TODOS':>9} {'DELTA':>8}")
    print(f"  {'─'*52}")
    for p in PATTERN_NAMES:
        m = pct_mon.get(p, 0)
        a = pct_all.get(p, 0)
        d = round(m - a, 1)
        ds = f"+{d}" if d > 0 else str(d)
        mk = "  ◀ DOMINANTE" if p == dominant else ""
        print(f"  {p:<22} {m:>8.1f}% {a:>8.1f}% {ds:>7}%{mk}")

    dom_pct = pct_mon.get(dominant, 0)
    print(f"\n  🏆 PATRÓN DOMINANTE LOS LUNES: {dominant}  ({dom_pct}%)")

    # ── DIRECCIÓN ─────────────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📈 DIRECCIÓN NY (cierre 16:00 vs apertura 09:30)")
    print(f"{'─'*W}")
    for d, cnt in mon_directions.items():
        pct = round(cnt / total_mon * 100, 1)
        icon = "🟢" if d == "BULLISH" else ("🔴" if d == "BEARISH" else "🟡")
        print(f"  {icon} {d:<10} {cnt:>3} Lunes  ({pct:>5.1f}%)  {bar(pct, 18)}")

    bull_pct = round(mon_directions["BULLISH"] / total_mon * 100, 1) if total_mon else 0
    bear_pct = round(mon_directions["BEARISH"] / total_mon * 100, 1) if total_mon else 0
    print(f"\n  → Sesgo histórico: {'ALCISTA' if bull_pct > bear_pct else 'BAJISTA'} "
          f"({max(bull_pct, bear_pct)}% vs {min(bull_pct, bear_pct)}%)")

    # ── HORA DEL SWEEP ────────────────────────────────────────────────────
    if sweep_hours_mon:
        print(f"\n{'─'*W}")
        print(f"  ⏰ HORA DEL SWEEP (cuando ocurre SWEEP_H/L_RETURN)")
        print(f"{'─'*W}")
        for h, cnt in sorted(sweep_hours_mon.items()):
            pct = round(cnt / total_mon * 100, 1)
            print(f"  {h}   {cnt:>2} sweeps  ({pct:>4.1f}%)")

    # ── VOLUME PROFILE ────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  📐 VOLUME PROFILE  (Rango Asia/Londres → 09:20 NY)")
    print(f"{'─'*W}")

    def lvl_row(name, hits, react_sum, total):
        hp   = round(hits / total * 100, 1) if total else 0
        avgr = round(react_sum / hits, 1) if hits else 0
        print(f"  {name:<14} {hits:>2}/{total}  ({hp:>5.1f}%)   reacción prom: {avgr:>6.1f} pts  {bar(hp, 12)}")

    lvl_row("VAH (techo)",  vah_h, vah_r, total_mon)
    lvl_row("POC (centro)", poc_h, poc_r, total_mon)
    lvl_row("VAL (base)",   val_h, val_r, total_mon)

    print(f"\n  📉 EMA 200 (15min) al momento de apertura NY")
    ep  = round(ema_h / total_mon * 100, 1) if total_mon else 0
    ear = round(ema_r / ema_h, 1) if ema_h else 0
    abp = round(ema_ab / total_mon * 100, 1)
    blp = round((total_mon - ema_ab) / total_mon * 100, 1)
    print(f"  Toca EMA200         : {ema_h}/{total_mon} ({ep}%)   Reacción prom: {ear} pts")
    print(f"  Abre SOBRE  EMA200  : {ema_ab}/{total_mon} ({abp}%)   → contexto alcista")
    print(f"  Abre DEBAJO EMA200  : {total_mon - ema_ab}/{total_mon} ({blp}%)   → contexto bajista")

    # ── ESTADÍSTICAS POR TIPO DE NOTICIA ──────────────────────────────────
    print(f"\n{SEP}")
    print(f"  📰 NOTICIAS QUE CAEN EN LUNES — IMPACTO EN NQ")
    print(f"{'─'*W}")
    print(f"  {'TIPO':<14} {'IMP':<8} {'N':<4} {'RANGO':<10} {'PAT. DOM.':<22} {'BULL%':<8} {'BEAR%':<8} {'EMA%'}")
    print(f"  {'─'*72}")

    for ntype in NEWS_PRIORITY:
        ns = news_stats.get(ntype)
        if not ns or ns["count"] == 0:
            continue
        n    = ns["count"]
        avgr = round(np.mean(ns["ranges"]), 1)
        dom_p = max(ns["patterns"], key=ns["patterns"].get) if ns["patterns"] else "N/A"
        dom_pp = round(ns["patterns"][dom_p] / n * 100, 1)
        bull  = round(ns["directions"]["BULLISH"] / n * 100, 1)
        bear  = round(ns["directions"]["BEARISH"] / n * 100, 1)
        ema_p = round(ns["ema_hits"] / n * 100, 1)
        impact = NEWS_IMPACT.get(ntype, "NORMAL")
        icon   = NEWS_ICON.get(impact, "⚪")
        print(f"  {icon}{ntype:<13} {impact:<8} {n:<4} {avgr:>7.1f}pts   {dom_p:<18} ({dom_pp:.0f}%)  {bull:>5.1f}%  {bear:>5.1f}%  {ema_p:>5.1f}%")

    # ── COMPARATIVA DE RANGO POR TIPO DE NOTICIA ─────────────────────────
    print(f"\n  📊 RANGO PROMEDIO POR TIPO DE NOTICIA vs LUNES SIN EVENTO")
    print(f"  {'─'*55}")
    none_ranges = news_stats["NONE"]["ranges"] if news_stats["NONE"]["count"] > 0 else mon_ranges
    none_avg    = round(np.mean(none_ranges), 1) if none_ranges else avg_range
    print(f"  {'NONE (sin evento)':<20} → {none_avg:>7.1f} pts  (referencia)")
    for ntype in NEWS_PRIORITY:
        ns = news_stats.get(ntype)
        if not ns or ns["count"] == 0 or ntype == "NONE":
            continue
        avgr  = round(np.mean(ns["ranges"]), 1)
        mult  = round(avgr / none_avg, 2) if none_avg else 0
        arrow = "⬆" if mult > 1.1 else ("⬇" if mult < 0.9 else "➡")
        print(f"  {ntype:<20} → {avgr:>7.1f} pts  {arrow} {mult:.2f}x vs NONE")

    # ── DETALLE SESIONES ──────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print(f"  📋 DETALLE CADA LUNES (último año)")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<13} {'NOTICIA':<14} {'PATRÓN':<22} {'DIR':<9} {'RANGO':>7} {'EMA':>8}")
    print(f"  {'─'*74}")
    for r in sorted(monday_results, key=lambda x: x['date']):
        icon = NEWS_ICON.get(r['news_impact'], "⚪")
        ema_mark = "↑" if r['open_above_ema'] else "↓"
        print(
            f"  {r['date']:<13} {icon}{r['news_type']:<13} {r['pattern']:<22} "
            f"{r['direction']:<9} {r['ny_range']:>6.0f}pts {r['ema200']:>7.0f}{ema_mark}"
        )

    # ── CONCLUSIÓN ────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  💡 CONCLUSIONES OPERATIVAS — LUNES NQ")
    print(SEP)

    # Mejor patrón
    if dominant == "NEWS_DRIVE":
        print(f"  ⚡ ALTA VOLATILIDAD — NEWS_DRIVE domina los Lunes ({dom_pct}%)")
        print(f"     → Esperar el impulso inicial (9:30-9:45) antes de entrar")
    elif dominant in ["SWEEP_H_RETURN", "SWEEP_L_RETURN"]:
        print(f"  🎯 SWEEP & RETURN es el patrón estrella ({dom_pct}%)")
        print(f"     → Buscar el barrido del High/Low asiático y entrar en contra")
    elif dominant in ["EXPANSION_H", "EXPANSION_L"]:
        print(f"  🚀 EXPANSION domina ({dom_pct}%) — seguir la ruptura del rango")
        print(f"     → No ir en contra de la tendencia inicial del Lunes")
    else:
        print(f"  🔄 ROTACIÓN POC domina ({dom_pct}%) — mercado en rango")
        print(f"     → Scalp entre VAH y VAL, respetar el POC como pivot")

    # Mejor nivel
    niveles = [("VAH", vah_h, vah_r), ("POC", poc_h, poc_r),
               ("VAL", val_h, val_r), ("EMA200", ema_h, ema_r)]
    mejor = max(niveles, key=lambda x: (x[1], x[2]))
    mejor_react = round(mejor[2] / mejor[1], 1) if mejor[1] else 0

    print(f"\n  🔑 NIVEL MÁS RESPETADO : {mejor[0]}")
    print(f"     Tocado en {mejor[1]}/{total_mon} Lunes | Reacción prom: {mejor_react} pts")

    # Sesgo direccional
    print(f"\n  📈 SESGO DIRECCIONAL LUNES: {bull_pct}% BULLISH | {bear_pct}% BEARISH")
    if bull_pct > 55:
        print(f"     → Los Lunes tienen sesgo ALCISTA histórico — priorizar longs")
    elif bear_pct > 55:
        print(f"     → Los Lunes tienen sesgo BAJISTA histórico — priorizar shorts")
    else:
        print(f"     → Dirección equilibrada — respetar la estructura del día")

    # Noticia con mayor impacto en rango
    news_with_data = [(ntype, round(np.mean(ns["ranges"]), 1))
                      for ntype, ns in news_stats.items()
                      if ns["count"] > 0 and ntype != "NONE"]
    if news_with_data:
        max_news = max(news_with_data, key=lambda x: x[1])
        print(f"\n  📰 NOTICIA CON MAYOR EXPANSIÓN DE RANGO: {max_news[0]}")
        print(f"     Rango promedio cuando aparece: {max_news[1]} pts vs {none_avg} pts (normal)")

    print(SEP)

    # ── GUARDAR JSON ──────────────────────────────────────────────────────
    report = {
        "title":   "Backtest Lunes NQ · 1 Año",
        "period":  f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        "total_days":     total_all,
        "total_mondays":  total_mon,
        "dominant_pattern": dominant,
        "dominant_pct":   dom_pct,
        "avg_ny_range":   avg_range,
        "max_ny_range":   max_range,
        "min_ny_range":   min_range,
        "avg_asia_range": avg_asia,
        "directions": dict(mon_directions),
        "patterns": {k: f"{v:.1f}%" for k, v in pct_mon.items()},
        "patterns_all_days": {k: f"{v:.1f}%" for k, v in pct_all.items()},
        "range_distribution": {k: v for k, v in r_buckets.items()},
        "sweep_hours": dict(sweep_hours_mon),
        "value_area": {
            "vah": {"hit_rate": f"{round(vah_h/total_mon*100,1) if total_mon else 0}%",
                    "avg_reaction": round(vah_r/vah_h, 1) if vah_h else 0},
            "poc": {"hit_rate": f"{round(poc_h/total_mon*100,1) if total_mon else 0}%",
                    "avg_reaction": round(poc_r/poc_h, 1) if poc_h else 0},
            "val": {"hit_rate": f"{round(val_h/total_mon*100,1) if total_mon else 0}%",
                    "avg_reaction": round(val_r/val_h, 1) if val_h else 0},
        },
        "ema200": {
            "hit_rate":        f"{round(ema_h/total_mon*100,1) if total_mon else 0}%",
            "avg_reaction":    round(ema_r/ema_h, 1) if ema_h else 0,
            "open_above_pct":  abp,
            "open_below_pct":  blp,
        },
        "by_news_type": {
            ntype: {
                "count":          ns["count"],
                "avg_range":      round(np.mean(ns["ranges"]), 1) if ns["ranges"] else 0,
                "avg_asia_range": round(np.mean(ns["ranges_asia"]), 1) if ns["ranges_asia"] else 0,
                "impact":         NEWS_IMPACT.get(ntype, "NORMAL"),
                "directions":     dict(ns["directions"]),
                "dominant_pattern": max(ns["patterns"], key=ns["patterns"].get) if ns["patterns"] else "N/A",
                "patterns":       dict(ns["patterns"]),
                "vah_hit_rate":   f"{round(ns['vah_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "poc_hit_rate":   f"{round(ns['poc_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "val_hit_rate":   f"{round(ns['val_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "ema_hit_rate":   f"{round(ns['ema_hits']/ns['count']*100,1) if ns['count'] else 0}%",
                "open_above_ema": f"{round(ns['open_above_ema']/ns['count']*100,1) if ns['count'] else 0}%",
                "sessions":       ns["sessions"],
            }
            for ntype, ns in news_stats.items() if ns["count"] > 0
        },
        "all_mondays": monday_results,
    }

    out_path = "data/research/backtest_monday_1year.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False, default=bool)

    print(f"\n  ✅ Datos guardados → {out_path}\n")
    return report


if __name__ == "__main__":
    run_monday_backtest()
