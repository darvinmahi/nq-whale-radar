"""
backtest_martes_miercoles.py
Genera backtest_tuesday_3m.json y backtest_wednesday_3m.json
usando los últimos 60 días de NQ 15min disponibles en yfinance.
Schema exacto esperado por daily_dashboard.html.

Ejecutar: python backtest_martes_miercoles.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import pytz

# ── Config ──────────────────────────────────────────────────────────────
ET = pytz.timezone("America/New_York")
NY_OPEN_H, NY_OPEN_M   = 9, 30
NY_CLOSE_H, NY_CLOSE_M = 16, 0
PRE_NY_START_H = 6    # 6 AM ET → inicio de ventana Asia/Londres

# ── Clasificadores ───────────────────────────────────────────────────────
def classify_pattern(ny_open, ny_high, ny_low, pre_high, pre_low, poc):
    """Clasifica el patrón de la sesión NY según ICT/VP."""
    ny_range = ny_high - ny_low
    # Sweep High + Return → SWEEP_H_RETURN
    if ny_high > pre_high and ny_low > pre_low - 10:
        if (ny_high - ny_open) / ny_range > 0.6:
            return "SWEEP_H_RETURN"
    # Sweep Low + Return → SWEEP_L_RETURN
    if ny_low < pre_low and ny_high < pre_high + 10:
        if (ny_open - ny_low) / ny_range > 0.6:
            return "SWEEP_L_RETURN"
    # Expansion H (breakout arriba)
    if ny_high > pre_high and ny_low >= pre_low - 20:
        return "EXPANSION_H"
    # Expansion L (breakout abajo)
    if ny_low < pre_low and ny_high <= pre_high + 20:
        return "EXPANSION_L"
    # Rotation around POC
    if poc and abs(ny_open - poc) < 30:
        return "ROTATION_POC"
    # Default: News Drive
    return "NEWS_DRIVE"

def classify_direction(ny_open, ny_close):
    diff = ny_close - ny_open
    if diff > 15:  return "BULLISH"
    if diff < -15: return "BEARISH"
    return "NEUTRAL"

def range_bucket(r):
    if r < 100:  return "0-100"
    if r < 200:  return "100-200"
    if r < 300:  return "200-300"
    return "300+"

def compute_vp_simple(bars):
    """Volume Profile simplificado: devuelve (poc, vah, val) de las barras dadas."""
    if bars.empty:
        return None, None, None
    try:
        prices = pd.concat([bars['High'], bars['Low']]).values
        mn, mx = prices.min(), prices.max()
        if mx == mn:
            return float(mn), float(mn), float(mn)
        bins = np.linspace(mn, mx, 50)
        vol_per_bin = np.zeros(len(bins)-1)
        for _, row in bars.iterrows():
            bar_bins = np.where((bins[:-1] <= row['High']) & (bins[1:] >= row['Low']))[0]
            v = float(row.get('Volume', 1) or 1)
            if len(bar_bins):
                vol_per_bin[bar_bins] += v / max(len(bar_bins), 1)
        poc_idx = int(np.argmax(vol_per_bin))
        poc = float((bins[poc_idx] + bins[poc_idx+1]) / 2)
        # VA: 70% del volumen total
        total_vol = vol_per_bin.sum()
        target = total_vol * 0.70
        va_vol, vah_idx, val_idx = 0, poc_idx, poc_idx
        lo, hi = poc_idx, poc_idx
        while va_vol < target and (lo > 0 or hi < len(vol_per_bin)-1):
            add_lo = vol_per_bin[lo-1] if lo > 0 else 0
            add_hi = vol_per_bin[hi+1] if hi < len(vol_per_bin)-1 else 0
            if add_hi >= add_lo and hi < len(vol_per_bin)-1:
                hi += 1; va_vol += vol_per_bin[hi]
            elif lo > 0:
                lo -= 1; va_vol += vol_per_bin[lo]
            else:
                break
        vah = float((bins[hi] + bins[hi+1]) / 2)
        val = float((bins[lo] + bins[lo+1]) / 2)
        return poc, vah, val
    except:
        mid = float((bars['High'].max() + bars['Low'].min()) / 2)
        return mid, mid * 1.003, mid * 0.997

def compute_ema200(series):
    """EMA 200 del cierre."""
    if len(series) < 200:
        return float(series.ewm(span=len(series), adjust=False).mean().iloc[-1])
    return float(series.ewm(span=200, adjust=False).mean().iloc[-1])

# ── Descargar datos ──────────────────────────────────────────────────────
def download_nq_60d():
    print("📥 Descargando NQ=F 15min (60d)…")
    df = yf.download("NQ=F", period="60d", interval="15m", progress=False, auto_adjust=True)
    if df.empty:
        raise RuntimeError("yfinance no devolvió datos")
    # Flatten MultiIndex si existe
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.tz_convert(ET)
    print(f"  → {len(df)} barras | {df.index[0].date()} → {df.index[-1].date()}")
    return df

# ── Procesar un día ──────────────────────────────────────────────────────
def process_day(date_str, df_all):
    """Analiza un día concreto (YYYY-MM-DD). Devuelve dict de sesión o None."""
    try:
        day_bars = df_all[df_all.index.date == pd.Timestamp(date_str).date()]
        if day_bars.empty:
            return None

        # Pre-NY: 6am–9:30am
        pre_ny = day_bars[(day_bars.index.hour >= PRE_NY_START_H) &
                          ((day_bars.index.hour < NY_OPEN_H) |
                           ((day_bars.index.hour == NY_OPEN_H) & (day_bars.index.minute < NY_OPEN_M)))]
        # NY: 9:30am–4:00pm
        ny = day_bars[(day_bars.index.hour > NY_OPEN_H) |
                      ((day_bars.index.hour == NY_OPEN_H) & (day_bars.index.minute >= NY_OPEN_M))]
        ny = ny[(ny.index.hour < NY_CLOSE_H) | (ny.index.hour == NY_CLOSE_H)]
        if ny.empty:
            return None

        # --- VP pre-NY ---
        poc, vah, val = compute_vp_simple(pre_ny if not pre_ny.empty else ny)

        # --- Niveles NY ---
        ny_open  = float(ny['Open'].iloc[0])
        ny_close = float(ny['Close'].iloc[-1])
        ny_high  = float(ny['High'].max())
        ny_low   = float(ny['Low'].min())
        ny_range = ny_high - ny_low

        pre_high = float(pre_ny['High'].max()) if not pre_ny.empty else ny_high
        pre_low  = float(pre_ny['Low'].min())  if not pre_ny.empty else ny_low

        # --- EMA200 (calculado sobre toda la serie hasta ese día) ---
        hist = df_all[df_all.index < pd.Timestamp(date_str + "T09:30:00", tz=ET)]
        ema200_val = compute_ema200(hist['Close']) if len(hist) >= 10 else None

        # --- Clasificación ---
        pattern   = classify_pattern(ny_open, ny_high, ny_low, pre_high, pre_low, poc)
        direction = classify_direction(ny_open, ny_close)

        # --- Hits ---
        def hit_and_react(level, bars):
            if level is None: return False, 0.0
            touched = bars[(bars['Low'] <= level + 10) & (bars['High'] >= level - 10)]
            if touched.empty: return False, 0.0
            react = abs(bars['Close'].iloc[-1] - level)
            return True, round(float(react), 2)

        vah_hit, vah_react   = hit_and_react(vah, ny)
        poc_hit, poc_react   = hit_and_react(poc, ny)
        val_hit, val_react   = hit_and_react(val, ny)
        ema_hit, ema_react   = hit_and_react(ema200_val, ny)
        ema_above = (ny_open > ema200_val) if ema200_val else None

        return {
            "date":             date_str,
            "weekday":          pd.Timestamp(date_str).day_name(),
            "pattern":          pattern,
            "direction":        direction,
            "ny_open":          round(ny_open, 2),
            "full_close":       round(ny_close, 2),
            "r_high":           round(ny_high, 2),
            "r_low":            round(ny_low, 2),
            "ny_range":         round(ny_range, 2),
            "range_asia_lon":   round(pre_high - pre_low, 2),
            "profile_poc":      round(poc, 2)  if poc  else None,
            "profile_vah":      round(vah, 2)  if vah  else None,
            "profile_val":      round(val, 2)  if val  else None,
            "ema200":           round(ema200_val, 2) if ema200_val else None,
            "ema_above":        ema_above,
            "vah_hit":          vah_hit,
            "vah_react":        vah_react,
            "profile_poc_hit":  poc_hit,
            "profile_poc_react":poc_react,
            "val_hit":          val_hit,
            "val_react":        val_react,
            "ema_hit":          ema_hit,
            "ema_react":        ema_react,
        }
    except Exception as e:
        print(f"  ⚠️ Error procesando {date_str}: {e}")
        return None

# ── Agregar estadísticas ─────────────────────────────────────────────────
def aggregate_sessions(sessions):
    if not sessions:
        return {}
    total = len(sessions)

    # Dirección
    dirs = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    for s in sessions:
        dirs[s["direction"]] = dirs.get(s["direction"], 0) + 1

    # Patrones (como porcentaje)
    pat_counts = {}
    for s in sessions:
        pat_counts[s["pattern"]] = pat_counts.get(s["pattern"], 0) + 1
    patterns = {k: round(v/total*100, 1) for k, v in sorted(pat_counts.items(), key=lambda x:-x[1])}
    dominant_pattern = max(pat_counts, key=pat_counts.get)
    dominant_pct     = round(pat_counts[dominant_pattern]/total*100, 1)

    # Range distribution
    rd = {"0-100": 0, "100-200": 0, "200-300": 0, "300+": 0}
    for s in sessions:
        rd[range_bucket(s["ny_range"])] += 1

    # Volume Profile hit rates
    def vp_stats(hit_key, react_key):
        hits   = [s for s in sessions if s.get(hit_key)]
        reacts = [s[react_key] for s in sessions if s.get(react_key, 0) > 0]
        return {
            "hit_rate":     round(len(hits)/total*100, 1),
            "avg_reaction": round(np.mean(reacts) if reacts else 0, 1)
        }

    value_area = {
        "vah": vp_stats("vah_hit", "vah_react"),
        "poc": vp_stats("profile_poc_hit", "profile_poc_react"),
        "val": vp_stats("val_hit", "val_react"),
    }

    # EMA200
    ema_hits   = [s for s in sessions if s.get("ema_hit")]
    ema_reacts = [s["ema_react"] for s in sessions if s.get("ema_react", 0) > 0]
    above_cnt  = sum(1 for s in sessions if s.get("ema_above"))
    ema200 = {
        "hit_rate":       round(len(ema_hits)/total*100, 1),
        "avg_reaction":   round(np.mean(ema_reacts) if ema_reacts else 0, 1),
        "open_above_pct": round(above_cnt/total*100, 1),
        "open_below_pct": round((total-above_cnt)/total*100, 1),
    }

    avg_range = round(np.mean([s["ny_range"] for s in sessions]), 1)

    return {
        "total_sessions": total,
        "directions":       dirs,
        "patterns":         patterns,
        "dominant_pattern": dominant_pattern,
        "dominant_pct":     dominant_pct,
        "range_distribution": rd,
        "value_area": value_area,
        "ema200": ema200,
        "avg_ny_range": avg_range,
    }

# ── Main ─────────────────────────────────────────────────────────────────
def main():
    today = datetime.now(ET)
    os.makedirs("data/research", exist_ok=True)

    # Descargar datos
    df = download_nq_60d()

    # Obtener todas las fechas disponibles
    all_dates = sorted(set(str(d) for d in df.index.date))
    print(f"\n📅 Fechas disponibles: {all_dates[0]} → {all_dates[-1]} ({len(all_dates)} días)\n")

    # Filtrar martes (weekday==1) y miércoles (weekday==2)
    tuesdays   = [d for d in all_dates if pd.Timestamp(d).weekday() == 1]
    wednesdays = [d for d in all_dates if pd.Timestamp(d).weekday() == 2]

    print(f"📈 Martes encontrados   : {len(tuesdays)} → {tuesdays}")
    print(f"📈 Miércoles encontrados: {len(wednesdays)} → {wednesdays}\n")

    # ── MARTES ──
    print("🔧 Procesando MARTES…")
    tue_sessions = []
    for d in tuesdays:
        s = process_day(d, df)
        if s:
            tue_sessions.append(s)
            print(f"  ✅ {d} | {s['pattern']} | {s['direction']} | rango: {s['ny_range']:.0f} | POC: {s['profile_poc']}")
        else:
            print(f"  ⚠️ {d}: sin datos suficientes")

    tue_agg = aggregate_sessions(tue_sessions)
    tue_json = {
        "title":   "Backtest MARTES NQ · 3 Meses · Volume Profile + EMA200",
        "period":  f"{all_dates[0]} to {all_dates[-1]}",
        "methodology": "Volume Profile pre-NY, EMA200 15min, patrones ICT",
        **{k: v for k, v in tue_agg.items()},
        "total_tuesdays": len(tue_sessions),
        "all_tuesdays": tue_sessions,
        # alias para compatibilidad con el chart 3M
        "MARTES": {
            "total_sessions": len(tue_sessions),
            "dominant_pattern": tue_agg.get("dominant_pattern"),
            "dominant_pct": tue_agg.get("dominant_pct"),
            "patterns":  tue_agg.get("patterns"),
            "direction": tue_agg.get("directions"),
            "avg_ny_range": tue_agg.get("avg_ny_range"),
            "value_area": tue_agg.get("value_area"),
            "ema200": tue_agg.get("ema200"),
            "sessions": tue_sessions,
        }
    }
    with open("data/research/backtest_tuesday_3m.json", "w") as f:
        json.dump(tue_json, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Guardado: data/research/backtest_tuesday_3m.json ({len(tue_sessions)} martes)\n")

    # ── MIÉRCOLES ──
    print("🔧 Procesando MIÉRCOLES…")
    wed_sessions = []
    for d in wednesdays:
        s = process_day(d, df)
        if s:
            wed_sessions.append(s)
            print(f"  ✅ {d} | {s['pattern']} | {s['direction']} | rango: {s['ny_range']:.0f} | POC: {s['profile_poc']}")
        else:
            print(f"  ⚠️ {d}: sin datos suficientes")

    wed_agg = aggregate_sessions(wed_sessions)

    # Noticias claves del miércoles (CB Consumer Confidence, ADP, etc.)
    wed_json = {
        "title":   "Backtest MIÉRCOLES NQ · 3 Meses · Volume Profile + EMA200",
        "period":  f"{all_dates[0]} to {all_dates[-1]}",
        "methodology": "Volume Profile pre-NY, EMA200 15min, patrones ICT",
        "news_wednesday": ["CB Consumer Confidence (10:00 ET)", "ADP Non-Farm Employment", "EIA Crude Oil Inventories (10:30 ET)", "FOMC Minutes (cuando aplica)"],
        **{k: v for k, v in wed_agg.items()},
        "total_wednesdays": len(wed_sessions),
        "all_wednesdays": wed_sessions,
        "MIERCOLES": {
            "total_sessions": len(wed_sessions),
            "dominant_pattern": wed_agg.get("dominant_pattern"),
            "dominant_pct": wed_agg.get("dominant_pct"),
            "patterns":  wed_agg.get("patterns"),
            "direction": wed_agg.get("directions"),
            "avg_ny_range": wed_agg.get("avg_ny_range"),
            "value_area": wed_agg.get("value_area"),
            "ema200": wed_agg.get("ema200"),
            "sessions": wed_sessions,
        }
    }
    with open("data/research/backtest_wednesday_3m.json", "w") as f:
        json.dump(wed_json, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Guardado: data/research/backtest_wednesday_3m.json ({len(wed_sessions)} miércoles)\n")

    # Resumen
    print("=" * 60)
    print("📊 RESUMEN FINAL")
    print("=" * 60)
    if tue_sessions:
        last_tue = tue_sessions[-1]
        print(f"\n📅 ÚLTIMO MARTES: {last_tue['date']}")
        print(f"  Patrón    : {last_tue['pattern']}")
        print(f"  Dirección : {last_tue['direction']}")
        print(f"  Rango NY  : {last_tue['ny_range']:.0f} pts")
        print(f"  Open NY   : {last_tue['ny_open']:.2f}")
        print(f"  POC pre-NY: {last_tue['profile_poc']}")
        print(f"  VAH/VAL   : {last_tue['profile_vah']} / {last_tue['profile_val']}")

    if wed_sessions:
        last_wed = wed_sessions[-1]
        print(f"\n📅 ÚLTIMO MIÉRCOLES: {last_wed['date']}")
        print(f"  Patrón    : {last_wed['pattern']}")
        print(f"  Dirección : {last_wed['direction']}")
        print(f"  Rango NY  : {last_wed['ny_range']:.0f} pts")
        print(f"  Open NY   : {last_wed['ny_open']:.2f}")
        print(f"  POC pre-NY: {last_wed['profile_poc']}")
        print(f"  VAH/VAL   : {last_wed['profile_vah']} / {last_wed['profile_val']}")

    print("\n✅ Archivos listos para desplegar.")

if __name__ == "__main__":
    main()
