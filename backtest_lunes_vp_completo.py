"""
backtest_lunes_vp_completo.py
==============================
BACKTEST COMPLETO: TODOS LOS LUNES
Calcula VAH / POC / VAL del perfil de volumen de la sesión ASIA
y mide cuántas veces el precio RESPETÓ vs ROMPIÓ cada nivel
durante la sesión NY del mismo lunes.

METODOLOGÍA:
────────────
• Sesión ASIA  : Dom 23:00 UTC → Lun 10:00 UTC  (equivale a 5PM-5AM aprox NY time)
• Sesión NY    : Lun 14:30 UTC → Lun 21:00 UTC  (9:30AM-5PM ET, DST aprox)

VP (Volume Profile) ASIA:
  - Se divide el rango de Asia en bins de 5 pts
  - POC = precio con mayor volumen acumulado
  - VAH = borde superior de la zona del 70% del volumen
  - VAL = borde inferior de la zona del 70% del volumen

REGLAS respeto / ruptura:
  VAL:  RESPETO = precio tocó VAL±10pts pero no cerró una barra por DEBAJO
        RUPTURA = alguna barra de NY cerró más de 10pts DEBAJO de VAL
  POC:  RESPETO = precio cruzó POC pero volvió mismo lado al cierre NY
        RUPTURA = precio cerró NY opuesto al lado que abrió respecto a POC
  VAH:  RESPETO = precio tocó VAH±10pts pero no cerró una barra por ENCIMA
        RUPTURA = alguna barra de NY cerró más de 10pts ENCIMA de VAH

DIRECCIÓN DEL DÍA (Bullish / Bearish):
  Close NY vs Open NY (primera barra 14:30 UTC)
"""
import csv
from datetime import datetime, timedelta
from collections import defaultdict

# ─── Parámetros ────────────────────────────────────────────────────────────
VP_BIN        = 5.0     # tamaño de bin para VP
VA_PCT        = 0.70    # porcentaje del volumen para el Value Area
TOUCH_MARGIN  = 10.0    # margen en puntos para "tocó" el nivel
BREAK_MARGIN  = 10.0    # deben cerrar N pts más allá del nivel para contar ruptura

# ─── 1. Carga datos 15m ────────────────────────────────────────────────────
bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        raw = r.get("Price", "")
        if "Ticker" in raw or not raw or raw == "Datetime":
            continue
        try:
            # El CSV tiene fechas tipo "2025-12-31 05:00:00+00:00"
            dt_str = raw.replace("+00:00", "").strip()
            dt = datetime.fromisoformat(dt_str)
            cl  = float(r.get("Close",  0) or 0)
            hi  = float(r.get("High",   0) or 0)
            lo  = float(r.get("Low",    0) or 0)
            op  = float(r.get("Open",   0) or 0)
            vol = float(r.get("Volume", 0) or 0)
            if cl > 0:
                bars.append({"dt": dt, "close": cl, "high": hi,
                             "low": lo, "open": op, "vol": vol})
        except Exception:
            continue

bars.sort(key=lambda x: x["dt"])
print(f"  Barras cargadas: {len(bars)}")

# ─── 2. Índice por fecha/hora UTC ─────────────────────────────────────────
by_dt = defaultdict(list)
for b in bars:
    by_dt[b["dt"].date()].append(b)

# ─── 3. Función VP ─────────────────────────────────────────────────────────
def calc_vp(session_bars):
    """Calcula VAH, POC, VAL del perfil de volumen de una lista de barras."""
    if not session_bars:
        return None, None, None

    lo_all = min(b["low"]  for b in session_bars)
    hi_all = max(b["high"] for b in session_bars)
    if hi_all <= lo_all:
        return None, None, None

    # Construir bins
    import math
    n_bins = max(1, int(math.ceil((hi_all - lo_all) / VP_BIN)))
    bins   = [0.0] * n_bins

    for b in session_bars:
        # Distribuye el volumen uniformemente entre todos los bins que toca la barra
        bar_lo = b["low"]
        bar_hi = b["high"]
        bar_vol = b["vol"] if b["vol"] > 0 else 1.0

        for i in range(n_bins):
            bin_lo = lo_all + i * VP_BIN
            bin_hi = bin_lo + VP_BIN
            overlap = max(0, min(bar_hi, bin_hi) - max(bar_lo, bin_lo))
            bar_range = bar_hi - bar_lo if bar_hi > bar_lo else VP_BIN
            bins[i] += bar_vol * (overlap / bar_range)

    total_vol = sum(bins)
    if total_vol == 0:
        return None, None, None

    # POC = bin con mayor volumen
    poc_idx = bins.index(max(bins))
    poc = lo_all + poc_idx * VP_BIN + VP_BIN / 2

    # Value Area = 70% del volumen partiendo del POC
    va_vol = total_vol * VA_PCT
    acum   = bins[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx

    while acum < va_vol:
        ext_lo = lo_idx - 1 if lo_idx > 0 else None
        ext_hi = hi_idx + 1 if hi_idx < n_bins - 1 else None

        vol_lo = bins[ext_lo] if ext_lo is not None else -1
        vol_hi = bins[ext_hi] if ext_hi is not None else -1

        if vol_lo <= 0 and vol_hi <= 0:
            break
        if vol_hi >= vol_lo:
            hi_idx = ext_hi
            acum  += vol_hi
        else:
            lo_idx = ext_lo
            acum  += vol_lo

    val = lo_all + lo_idx * VP_BIN
    vah = lo_all + hi_idx * VP_BIN + VP_BIN

    return round(vah, 2), round(poc, 2), round(val, 2)

# ─── 4. Función para detectar barras de una sesión (UTC) ──────────────────
def get_session_bars(all_bars, date_utc, h_start, h_end, cross_midnight=False):
    """Devuelve barras entre h_start y h_end del día dado (en UTC).
    Si cross_midnight=True, la sesión empieza el día anterior a medianoche."""
    result = []
    if cross_midnight:
        # Sesión empieza día anterior
        prev_date = date_utc - timedelta(days=1)
        for b in all_bars:
            dt = b["dt"]
            if dt.date() == prev_date and dt.hour >= h_start:
                result.append(b)
            elif dt.date() == date_utc and dt.hour < h_end:
                result.append(b)
    else:
        for b in all_bars:
            dt = b["dt"]
            if dt.date() == date_utc and h_start <= dt.hour < h_end:
                result.append(b)
    return result

# ─── 5. Análisis de cada LUNES ────────────────────────────────────────────
results = []

# Obtener todos los lunes únicos en los datos
all_dates = sorted(set(b["dt"].date() for b in bars))
mondays   = [d for d in all_dates if d.weekday() == 0]

for mon in mondays:
    # ── Sesión ASIA: Dom 23:00 UTC → Lun 10:00 UTC ──────────────────────
    asia_bars = get_session_bars(bars, mon, h_start=23, h_end=10, cross_midnight=True)

    if len(asia_bars) < 4:
        results.append({"date": mon, "skip": "sin datos ASIA"})
        continue

    vah, poc, val = calc_vp(asia_bars)
    if vah is None:
        results.append({"date": mon, "skip": "VP inválido"})
        continue

    # ── Sesión NY: Lun 14:30 UTC → Lun 21:00 UTC ────────────────────────
    ny_bars = [b for b in bars
               if b["dt"].date() == mon
               and (b["dt"].hour > 14
                    or (b["dt"].hour == 14 and b["dt"].minute >= 30))
               and b["dt"].hour < 21]

    if len(ny_bars) < 2:
        results.append({"date": mon, "skip": "sin datos NY", "vah": vah, "poc": poc, "val": val})
        continue

    ny_open_price  = ny_bars[0]["open"]
    ny_close_price = ny_bars[-1]["close"]
    ny_high        = max(b["high"] for b in ny_bars)
    ny_low         = min(b["low"]  for b in ny_bars)

    # ── Dirección ────────────────────────────────────────────────────────
    bullish = ny_close_price > ny_open_price

    # ── Análisis VAL ─────────────────────────────────────────────────────
    # "Tocó" VAL: el low del día bajó a VAL ± TOUCH_MARGIN
    touched_val = ny_low <= val + TOUCH_MARGIN

    if touched_val:
        # Ruptura: alguna barra cerró > BREAK_MARGIN por DEBAJO de VAL
        broke_val = any(b["close"] < val - BREAK_MARGIN for b in ny_bars)
        val_status = "RUPTURA" if broke_val else "RESPETO"
    else:
        val_status = "NO_TESTEO"

    # ── Análisis VAH ─────────────────────────────────────────────────────
    touched_vah = ny_high >= vah - TOUCH_MARGIN
    if touched_vah:
        broke_vah = any(b["close"] > vah + BREAK_MARGIN for b in ny_bars)
        vah_status = "RUPTURA" if broke_vah else "RESPETO"
    else:
        vah_status = "NO_TESTEO"

    # ── Análisis POC ─────────────────────────────────────────────────────
    # Tocó POC: el rango high-low cruzó POC
    touched_poc = ny_low <= poc + TOUCH_MARGIN and ny_high >= poc - TOUCH_MARGIN
    if touched_poc:
        # Ruptura bidireccional: el close NY está en el lado contrario al que abrió
        open_above_poc  = ny_open_price > poc
        close_above_poc = ny_close_price > poc
        broke_poc = (open_above_poc != close_above_poc)  # cruzó de lado
        poc_status = "RUPTURA" if broke_poc else "RESPETO"
    else:
        poc_status = "NO_TESTEO"

    results.append({
        "date"        : mon,
        "skip"        : None,
        "vah"         : vah,
        "poc"         : poc,
        "val"         : val,
        "ny_open"     : ny_open_price,
        "ny_close"    : ny_close_price,
        "ny_high"     : ny_high,
        "ny_low"      : ny_low,
        "bullish"     : bullish,
        "val_status"  : val_status,
        "poc_status"  : poc_status,
        "vah_status"  : vah_status,
        "touched_val" : touched_val,
        "touched_poc" : touched_poc,
        "touched_vah" : touched_vah,
    })

# ─── 6. Estadísticas ──────────────────────────────────────────────────────
valid = [r for r in results if r.get("skip") is None]
skipped = [r for r in results if r.get("skip")]

bullish_days  = [r for r in valid if r["bullish"]]
bearish_days  = [r for r in valid if not r["bullish"]]

def stats_nivel(days, nivel):
    """Cuenta respeto/ruptura/no_testeo para un nivel en un conjunto de días."""
    key = f"{nivel}_status"
    testeo   = [d for d in days if d[f"touched_{nivel}"]]
    respeto  = [d for d in testeo if d[key] == "RESPETO"]
    ruptura  = [d for d in testeo if d[key] == "RUPTURA"]
    no_test  = [d for d in days if not d[f"touched_{nivel}"]]
    return {
        "testeo" : len(testeo),
        "respeto": len(respeto),
        "ruptura": len(ruptura),
        "no_test": len(no_test),
        "pct_respeto": round(len(respeto)/len(testeo)*100, 1) if testeo else 0,
    }

# ─── 7. Print resultados ───────────────────────────────────────────────────
print()
print("=" * 75)
print("  BACKTEST COMPLETO LUNES  |  VAL / POC / VAH  |  Respeto vs Ruptura")
print("=" * 75)
print(f"\n  Lunes analizados : {len(mondays)}")
print(f"  Con datos válidos: {len(valid)}    Omitidos: {len(skipped)}")
print(f"\n  Dirección del día:")
print(f"    🟢 Bullish : {len(bullish_days)}  ({len(bullish_days)/len(valid)*100:.0f}%)")
print(f"    🔴 Bearish : {len(bearish_days)}  ({len(bearish_days)/len(valid)*100:.0f}%)")

def print_block(titulo, days):
    n  = len(days)
    if n == 0:
        return
    print(f"\n  {'─'*70}")
    print(f"  {titulo}  (N={n})")
    print(f"  {'─'*70}")
    print(f"  {'Nivel':<6}  {'Testeó':<7}  {'Respetó':<10}  {'Rompió':<10}  {'No testeó':<11}  {'%Respeto'}")
    print(f"  {'─'*70}")
    for nivel in ["val", "poc", "vah"]:
        s = stats_nivel(days, nivel)
        pct = f"{s['pct_respeto']:.0f}%" if s['testeo'] > 0 else "n/a"
        print(f"  {nivel.upper():<6}  {s['testeo']:<7}  {s['respeto']:<10}  {s['ruptura']:<10}  {s['no_test']:<11}  {pct}")

print_block("📊 TODOS LOS LUNES", valid)
print_block("🟢 LUNES BULLISH", bullish_days)
print_block("🔴 LUNES BEARISH", bearish_days)

# ─── 8. Detalle día a día ──────────────────────────────────────────────────
print(f"\n\n  DETALLE DÍA A DÍA:")
print(f"  {'Fecha':<12} {'Dir':<8} {'VAL':>8} {'POC':>8} {'VAH':>8}  {'VAL_st':<10} {'POC_st':<10} {'VAH_st'}")
print(f"  {'─'*80}")
for r in valid:
    d   = r["date"]
    dir_s = "🟢 BULL" if r["bullish"] else "🔴 BEAR"
    print(f"  {str(d):<12} {dir_s:<8} {r['val']:>8.0f} {r['poc']:>8.0f} {r['vah']:>8.0f}"
          f"  {r['val_status']:<10} {r['poc_status']:<10} {r['vah_status']}")

print()
print("  LEYENDA:")
print("  RESPETO   = precio tocó el nivel pero NO cerró por encima/debajo")
print("  RUPTURA   = precio cerró al otro lado del nivel (>10pts)")
print("  NO_TESTEO = precio no llegó al nivel en ningún momento de NY")
print(f"\n  Margen para 'tocó': ±{TOUCH_MARGIN} pts  |  Margen ruptura: {BREAK_MARGIN} pts")
print()
