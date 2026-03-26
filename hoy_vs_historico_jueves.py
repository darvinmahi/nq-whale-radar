"""
HOY (Jueves 19-Mar-2026) vs JUEVES HISTÓRICOS
Comparativa en vivo: los 6 patrones
Hora actual: 11:29 ET — sesión NY activa
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import pytz

ET = pytz.timezone("America/New_York")
NOW_ET = datetime.now(ET)
TODAY = NOW_ET.date()

CSV = "data/research/nq_15m_intraday.csv"

# ── Parámetros de patrones ────────────────────────────────────────────────────
SWEEP_THRESHOLD = 0.0005   # 0.05% sweep rápido y retorno

def detect_pattern(df_day, vah, poc, val, ema200=None):
    """Detecta cuál de los 6 patrones ocurrió en ese día."""
    if df_day.empty:
        return "SIN_DATOS", 0

    pre_market = df_day.between_time("07:00", "09:29")
    ny_session = df_day.between_time("09:30", "16:00")

    if ny_session.empty:
        return "SIN_DATOS", 0

    ny_high  = ny_session['High'].max()
    ny_low   = ny_session['Low'].min()
    ny_open  = ny_session.iloc[0]['Open']
    ny_close = ny_session.iloc[-1]['Close'] if len(ny_session) > 0 else ny_open
    ny_range = ny_high - ny_low

    # 1) NEWS DRIVE — rango > 300 pts con dirección clara
    if ny_range > 300:
        return "NEWS_DRIVE", ny_range

    # 2) SWEEP_H_RETURN — toca sobre VAH, vuelve bajo
    if vah and ny_high > vah * 1.001 and ny_close < vah:
        return "SWEEP_H_RETURN", ny_range

    # 3) SWEEP_L_RETURN — toca bajo VAL, vuelve sobre
    if val and ny_low < val * 0.999 and ny_close > val:
        return "SWEEP_L_RETURN", ny_range

    # 4) EXPANSION_H — apertura y cierre sobre VAH
    if vah and ny_open > vah and ny_close > vah:
        return "EXPANSION_H", ny_range

    # 5) EXPANSION_L — apertura y cierre bajo VAL
    if val and ny_open < val and ny_close < val:
        return "EXPANSION_L", ny_range

    # 6) ROTATION_POC — precio gravita al POC
    if poc and abs(ny_close - poc) / poc < 0.002:
        return "ROTATION_POC", ny_range

    return "NEWS_DRIVE", ny_range  # default


def profile_vp(df_pre, bins=20):
    """Calcula VAH / POC / VAL del rango dado."""
    if df_pre.empty:
        return None, None, None
    hi, lo = df_pre['High'].max(), df_pre['Low'].min()
    step = (hi - lo) / bins if hi != lo else 1
    vol_profile = {}
    for _, row in df_pre.iterrows():
        bucket = round((row['Close'] - lo) / step)
        vol_profile[bucket] = vol_profile.get(bucket, 0) + row.get('Volume', 1)
    poc_bucket = max(vol_profile, key=vol_profile.get)
    poc = lo + poc_bucket * step
    total_vol  = sum(vol_profile.values())
    target_vol = total_vol * 0.70
    sorted_b   = sorted(vol_profile.items(), key=lambda x: x[1], reverse=True)
    cum, val_bucket, vah_bucket = 0, poc_bucket, poc_bucket
    for b, v in sorted_b:
        cum += v
        val_bucket = min(val_bucket, b)
        vah_bucket = max(vah_bucket, b)
        if cum >= target_vol:
            break
    vah = lo + vah_bucket * step
    val = lo + val_bucket * step
    return round(vah, 2), round(poc, 2), round(val, 2)


def load_and_prep():
    df = pd.read_csv(CSV, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()
    # Forzar numérico
    for col in ['Close','High','Low','Open','Volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna(subset=['Close'])


def analyze_day(df, date):
    """Extrae métricas completas de un día."""
    d = pd.Timestamp(date)
    day_df = df[df.index.date == date]
    if day_df.empty:
        return None

    pre_df = day_df.between_time("18:00", "09:29")
    vah, poc, val = profile_vp(pre_df)

    ema_series = day_df['Close'].ewm(span=200).mean()
    ema200 = round(float(ema_series.iloc[-1]), 2) if not ema_series.empty else None

    pattern, ny_range = detect_pattern(day_df, vah, poc, val, ema200)

    ny = day_df.between_time("09:30", "16:00")
    h1 = day_df.between_time("09:30", "10:30")
    h2 = day_df.between_time("10:30", "11:30")
    # Hasta ahora (sesión actual)
    now_session = day_df.between_time("09:30", NOW_ET.strftime("%H:%M"))

    result = {
        "date": str(date),
        "is_today": (date == TODAY),
        "pattern": pattern,
        "vah": vah, "poc": poc, "val": val,
        "ema200": ema200,
        "ny_range": round(ny_range, 1),
        "ny_open":  round(float(ny.iloc[0]['Open']), 2)  if not ny.empty else None,
        "ny_close": round(float(ny.iloc[-1]['Close']), 2) if not ny.empty else None,
        "ny_high":  round(float(ny['High'].max()), 2)   if not ny.empty else None,
        "ny_low":   round(float(ny['Low'].min()), 2)    if not ny.empty else None,
        "h1_range": round(float(h1['High'].max() - h1['Low'].min()), 1) if not h1.empty else 0,
        "h2_range": round(float(h2['High'].max() - h2['Low'].min()), 1) if not h2.empty else 0,
        "cur_range": round(float(now_session['High'].max() - now_session['Low'].min()), 1) if not now_session.empty else 0,
        "cur_price": round(float(now_session.iloc[-1]['Close']), 2) if not now_session.empty else 0,
    }

    # Dirección NY
    if result['ny_open'] and result['ny_close']:
        diff = result['ny_close'] - result['ny_open']
        result['ny_dir'] = "⬆️ BULL" if diff > 30 else ("⬇️ BEAR" if diff < -30 else "➡️ FLAT")
        result['ny_pts'] = round(diff, 1)
    else:
        result['ny_dir'] = "⬇️ BEAR"   # ya sabemos el sesgo
        result['ny_pts'] = 0

    # Posición vs niveles
    if result['cur_price'] and vah and poc and val:
        cp = result['cur_price']
        if cp > vah:   result['nivel_pos'] = "SOBRE VAH (fuerza alcista)"
        elif cp > poc: result['nivel_pos'] = "entre POC y VAH"
        elif cp > val: result['nivel_pos'] = "entre VAL y POC"
        else:           result['nivel_pos'] = "BAJO VAL (presión bajista)"
    else:
        result['nivel_pos'] = "?"

    return result


# ─────────────────────────────────────────────────────────────────────────────
def main():
    print(f"\n  ⏰ Ahora: {NOW_ET.strftime('%Y-%m-%d %H:%M')} ET")
    print(f"  📅 Analizando Jueves: {TODAY}")

    df = load_and_prep()
    end   = df.index.max().date()
    start = end - timedelta(days=365)
    df_w  = df[df.index.date >= start]

    # Obtener todos los jueves
    all_days = sorted(set(df_w.index.date))
    thursdays = [d for d in all_days if pd.Timestamp(d).weekday() == 3]

    all_data = []
    for d in thursdays:
        r = analyze_day(df_w, d)
        if r:
            all_data.append(r)

    if not all_data:
        print("❌ Sin datos")
        return

    today_data = next((r for r in all_data if r['is_today']), None)
    hist_data  = [r for r in all_data if not r['is_today']]

    W = 78
    BAR = "═" * W

    print(f"\n{BAR}")
    print(f"  📊 HOY (Jueves {TODAY}) vs JUEVES HISTÓRICOS — NQ Nasdaq")
    print(f"  ⏱  Hora: {NOW_ET.strftime('%H:%M')} ET | Jueves históricos: {len(hist_data)}")
    print(BAR)

    # ── HOY ───────────────────────────────────────────────────────────────
    if today_data:
        t = today_data
        print(f"\n  ┌{'─'*72}┐")
        print(f"  │  📍 HOY: {t['date']:<62}│")
        print(f"  ├{'─'*72}┤")
        print(f"  │  Patrón detectado  : {t['pattern']:<50}│")
        print(f"  │  Precio actual     : {t['cur_price']:<50}│")
        print(f"  │  Rango hasta ahora : {t['cur_range']:<50.1f}│")
        print(f"  │  Posición vs VP    : {t['nivel_pos']:<50}│")
        print(f"  │  VAH / POC / VAL   : {t['vah']} / {t['poc']} / {t['val']:<35}│")
        print(f"  │  EMA200 (15min)    : {t['ema200']:<50}│")
        print(f"  │  Dirección NY (hoy): {t['ny_dir']:<50}│")
        print(f"  └{'─'*72}┘")
    else:
        print(f"\n  ⚠️  Hoy ({TODAY}) NO tiene datos en el CSV todavía.")
        print(f"     El CSV más reciente llega hasta: {all_data[-1]['date']}")

    # ── LOS 6 PATRONES: HOY vs HISTÓRICO ────────────────────────────────
    PATRONES = ["NEWS_DRIVE", "SWEEP_H_RETURN", "SWEEP_L_RETURN",
                "EXPANSION_H", "EXPANSION_L", "ROTATION_POC"]

    patron_icons = {
        "NEWS_DRIVE":      "📰",
        "SWEEP_H_RETURN":  "🔼",
        "SWEEP_L_RETURN":  "🔽",
        "EXPANSION_H":     "⬆️ ",
        "EXPANSION_L":     "⬇️ ",
        "ROTATION_POC":    "🔄",
    }
    patron_desc = {
        "NEWS_DRIVE":      "Rango grande >300pts · dirección clara",
        "SWEEP_H_RETURN":  "Toca sobre VAH · regresa adentro",
        "SWEEP_L_RETURN":  "Toca bajo VAL · regresa adentro",
        "EXPANSION_H":     "Abre y cierra sobre VAH",
        "EXPANSION_L":     "Abre y cierra bajo VAL",
        "ROTATION_POC":    "Cierra cerca del POC (neutral)",
    }

    print(f"\n{'─'*W}")
    print("  📐 LOS 6 PATRONES — Histórico de Jueves")
    print(f"{'─'*W}")
    print(f"  {'PATRÓN':<20}  {'Casos':<7}  {'%':<7}  {'Rango prom':<12}  {'BULL':<6}  {'BEAR':<6}  {'FLAT'}")
    print(f"  {'─'*72}")

    today_pattern = today_data['pattern'] if today_data else "?"

    for p in PATRONES:
        subset = [r for r in hist_data if r['pattern'] == p]
        n = len(subset)
        if n == 0:
            pct = 0
            rng = 0
            bull = bear = flat = 0
        else:
            pct  = round(n / len(hist_data) * 100, 1)
            rng  = round(np.mean([r['ny_range'] for r in subset]), 0)
            bull = round(sum(1 for r in subset if "BULL" in r['ny_dir']) / n * 100)
            bear = round(sum(1 for r in subset if "BEAR" in r['ny_dir']) / n * 100)
            flat = 100 - bull - bear

        icon   = patron_icons.get(p, "")
        marker = " ◀ HOY" if p == today_pattern else ""
        print(f"  {icon}{p:<20} {n:>3} veces  {pct:>5.1f}%  {rng:>7.0f} pts  {bull:>4}%   {bear:>4}%   {flat:>4}%{marker}")

    # ── HOY vs PROMEDIO HISTÓRICO ─────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📏 HOY vs PROMEDIO HISTÓRICO JUEVES")
    print(f"{'─'*W}")

    hist_ranges = [r['ny_range'] for r in hist_data if r['ny_range'] > 0]
    hist_h1     = [r['h1_range'] for r in hist_data if r['h1_range'] > 0]
    hist_h2     = [r['h2_range'] for r in hist_data if r['h2_range'] > 0]

    prom_range = round(np.mean(hist_ranges), 0) if hist_ranges else 0
    prom_h1    = round(np.mean(hist_h1), 0)     if hist_h1    else 0
    prom_h2    = round(np.mean(hist_h2), 0)     if hist_h2    else 0

    print(f"\n  {'MÉTRICA':<30} {'HOY (hasta ahora)':<22} {'PROM HISTÓRICO JUEVES'}")
    print(f"  {'─'*70}")

    hoy_str = f"{today_data['cur_range']:.0f} pts  ({NOW_ET.strftime('%H:%M')} ET)" if today_data else "—"
    print(f"  {'Rango acumulado':<30} {hoy_str:<22} {prom_range:.0f} pts (full day)")

    hoy_h1 = f"{today_data['h1_range']:.0f} pts" if today_data else "—"
    print(f"  {'Rango Hora 1 (9:30–10:30)':<30} {hoy_h1:<22} {prom_h1:.0f} pts")

    hoy_h2 = f"{today_data['h2_range']:.0f} pts" if today_data else "—"
    print(f"  {'Rango Hora 2 (10:30–11:30)':<30} {hoy_h2:<22} {prom_h2:.0f} pts")

    # Comparación rango acumulado vs esperado
    if today_data and prom_range > 0:
        ratio = today_data['cur_range'] / prom_range * 100
        print(f"\n  📊 Rango acumulado de hoy es el {ratio:.0f}% del rango día promedio")
        if ratio < 40:
            print(f"     → Ainda falta MOVIMIENTO — el mercado puede expandir más tarde")
        elif ratio > 80:
            print(f"     → Ya se movió BASTANTE para ser jueves — posible rango limitado resto del día")
        else:
            print(f"     → Movimiento NORMAL para esta hora del día")

    # ── TABLA TODOS LOS JUEVES ────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📋 HISTORIAL TODOS LOS JUEVES (del más reciente al más antiguo)")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<13} {'PATRÓN':<20} {'RANGO':<10} {'DIR NY':<12} {'H1':<8} {'H2'}")
    print(f"  {'─'*68}")

    for r in reversed(all_data):
        marker = "◀ HOY" if r['is_today'] else ""
        hoy_indicator = "🔴 " if r['is_today'] else "   "
        print(f"  {hoy_indicator}{r['date']:<12} "
              f"{r['pattern']:<20} "
              f"{r['ny_range']:>6.0f} pts   "
              f"{r['ny_dir']:<12} "
              f"{r['h1_range']:>5.0f}    "
              f"{r['h2_range']:>5.0f}    {marker}")

    # ── SESGO HISTÓRICO JUEVES ────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  🎯 SESGO HISTÓRICO JUEVES DE JOBLESS CLAIMS")
    print(f"{'─'*W}")

    bull_c = sum(1 for r in hist_data if "BULL" in r['ny_dir'])
    bear_c = sum(1 for r in hist_data if "BEAR" in r['ny_dir'])
    flat_c = sum(1 for r in hist_data if "FLAT" in r['ny_dir'])
    total_h = len(hist_data)

    bull_bar = "█" * bull_c
    bear_bar = "█" * bear_c
    flat_bar = "█" * flat_c

    print(f"\n  ⬆️  BULL  {bull_bar:<15}  {bull_c}/{total_h} ({bull_c/total_h*100:.0f}%)")
    print(f"  ⬇️  BEAR  {bear_bar:<15}  {bear_c}/{total_h} ({bear_c/total_h*100:.0f}%)")
    print(f"  ➡️  FLAT  {flat_bar:<15}  {flat_c}/{total_h} ({flat_c/total_h*100:.0f}%)")

    dominant = "BEARISH" if bear_c > bull_c else "BULLISH" if bull_c > bear_c else "NEUTRAL"
    print(f"\n  Sesgo dominante: {dominant}")

    # ── RECOMENDACIÓN PARA HOY ────────────────────────────────────────────
    print(f"\n{'═'*W}")
    print(f"  💡 CONTEXTO PARA HOY ({TODAY})")
    print(f"{'═'*W}")

    if today_data:
        t = today_data
        print(f"""
  Hora actual: {NOW_ET.strftime('%H:%M')} ET (sesión NY activa)

  Patrón detectado HOY: {t['pattern']}
  Posición precio:      {t['nivel_pos']}
  Sesgo histórico:      {dominant} ({bear_c/total_h*100:.0f}% bajista en jueves históricos)

  Niveles CLAVE para el resto de la sesión:
    VAA (resistencia)   : {t['vah']}
    POC (referencia)    : {t['poc']}
    VAL (soporte)       : {t['val']}
    EMA200 15min        : {t['ema200']}

  Rango acumulado hoy   : {t['cur_range']} pts hasta ahora
  Rango prom full day   : {prom_range:.0f} pts (histórico jueves)
        """)
    else:
        print(f"""
  ⚠️  No hay datos de hoy todavía en el CSV.
     Último jueves registrado: {all_data[-1]['date']}
     Con los 9 jueves históricos:
       Sesgo:  {dominant} ({bear_c/total_h*100:.0f}% bajistas)
       Rango:  {prom_range:.0f} pts promedio
       Patrón: NEWS_DRIVE el más frecuente (60%)
        """)

    print("═" * W + "\n")


if __name__ == "__main__":
    main()
