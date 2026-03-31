"""
backtest_vp_ny.py
==================
BACKTEST VP  — Metodología correcta
─────────────────────────────────────
PERFIL  : 23:00 UTC día anterior  →  13:20 UTC mismo día
          (Asia completo + London, hasta 10 min antes de NY)

ANÁLISIS: solo sesión NEW YORK
          14:30 UTC  →  21:00 UTC

NIVELES : VAH / POC / VAL  (Value Area 70%)

RESULTADO por nivel:
  RESPETO   = precio tocó el nivel pero NO cerró al otro lado
  RUPTURA   = precio cerró >BREAK_MARGIN pts al otro lado del nivel
  NO_TESTEO = precio no llegó al nivel en toda la sesión NY
"""
import csv
from datetime import datetime, timedelta, time
from collections import defaultdict
import math

# ══════════════════════════════════════════════════════════════
#  PARÁMETROS
# ══════════════════════════════════════════════════════════════
CSV_PATH     = "data/research/nq_15m_intraday.csv"
VP_BIN       = 5.0    # tamaño de bin (pts)
VA_PCT       = 0.70   # porcentaje Value Area
TOUCH_MARGIN = 10.0   # margen "tocó" el nivel (pts)
BREAK_MARGIN = 10.0   # cierre más allá del nivel = ruptura (pts)

# ══════════════════════════════════════════════════════════════
#  CARGA DE DATOS
# ══════════════════════════════════════════════════════════════
bars = []
with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        raw = r.get("Price", "")
        if not raw or "Ticker" in raw or raw == "Datetime":
            continue
        try:
            dt_str = raw.replace("+00:00", "").strip()
            dt  = datetime.fromisoformat(dt_str)
            cl  = float(r.get("Close",  0) or 0)
            hi  = float(r.get("High",   0) or 0)
            lo  = float(r.get("Low",    0) or 0)
            op  = float(r.get("Open",   0) or 0)
            vol = float(r.get("Volume", 0) or 0)
            if cl > 0:
                bars.append({"dt": dt, "close": cl, "high": hi,
                             "low": lo, "open": op, "vol": max(vol, 1.0)})
        except Exception:
            continue

bars.sort(key=lambda x: x["dt"])
print(f"Barras cargadas: {len(bars)}")

# ══════════════════════════════════════════════════════════════
#  FUNCIÓN: CALCULAR VAH / POC / VAL
# ══════════════════════════════════════════════════════════════
def calc_vp(session_bars):
    if len(session_bars) < 2:
        return None, None, None
    lo_all = min(b["low"]  for b in session_bars)
    hi_all = max(b["high"] for b in session_bars)
    if hi_all <= lo_all:
        return None, None, None

    n_bins = max(1, int(math.ceil((hi_all - lo_all) / VP_BIN)))
    bins   = [0.0] * n_bins

    for b in session_bars:
        bar_lo, bar_hi = b["low"], b["high"]
        bar_range = bar_hi - bar_lo if bar_hi > bar_lo else VP_BIN
        for i in range(n_bins):
            bin_lo = lo_all + i * VP_BIN
            bin_hi = bin_lo + VP_BIN
            overlap = max(0.0, min(bar_hi, bin_hi) - max(bar_lo, bin_lo))
            bins[i] += b["vol"] * (overlap / bar_range)

    total_vol = sum(bins)
    if total_vol == 0:
        return None, None, None

    poc_idx = bins.index(max(bins))
    poc     = lo_all + poc_idx * VP_BIN + VP_BIN / 2

    # Expandir Value Area desde POC hasta alcanzar 70%
    va_target = total_vol * VA_PCT
    acum   = bins[poc_idx]
    lo_idx = poc_idx
    hi_idx = poc_idx

    while acum < va_target:
        can_lo = lo_idx - 1 >= 0
        can_hi = hi_idx + 1 < n_bins
        v_lo   = bins[lo_idx - 1] if can_lo else -1
        v_hi   = bins[hi_idx + 1] if can_hi else -1
        if v_lo <= 0 and v_hi <= 0:
            break
        if v_hi >= v_lo:
            hi_idx += 1; acum += v_hi
        else:
            lo_idx -= 1; acum += v_lo

    val = lo_all + lo_idx * VP_BIN
    vah = lo_all + hi_idx * VP_BIN + VP_BIN
    return round(vah, 2), round(poc, 2), round(val, 2)

# ══════════════════════════════════════════════════════════════
#  FUNCIÓN: FILTRAR BARRAS POR VENTANA HORARIA UTC
# ══════════════════════════════════════════════════════════════
def filter_bars(all_bars, dt_from, dt_to):
    """Retorna barras entre dt_from y dt_to (inclusive extremos)."""
    return [b for b in all_bars if dt_from <= b["dt"] < dt_to]

# ══════════════════════════════════════════════════════════════
#  BACKTEST — TODOS LOS DÍAS DISPONIBLES
# ══════════════════════════════════════════════════════════════
results = []
DAYS_ES = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

all_dates = sorted(set(b["dt"].date() for b in bars))

for day_date in all_dates:
    weekday = day_date.weekday()
    if weekday > 4:          # saltar fines de semana
        continue

    # ── Ventana PERFIL ───────────────────────────────────────
    # 23:00 UTC del día ANTERIOR → 13:20 UTC del día actual
    prev_date = day_date - timedelta(days=1)
    prof_start = datetime(prev_date.year, prev_date.month, prev_date.day, 23,  0)
    prof_end   = datetime(day_date.year,  day_date.month,  day_date.day,  13, 20)

    prof_bars = filter_bars(bars, prof_start, prof_end)

    if len(prof_bars) < 4:
        results.append({"date": day_date, "weekday": weekday, "skip": "sin datos perfil"})
        continue

    vah, poc, val = calc_vp(prof_bars)
    if vah is None:
        results.append({"date": day_date, "weekday": weekday, "skip": "VP inválido"})
        continue

    # ── Ventana NY ───────────────────────────────────────────
    # 14:30 UTC → 21:00 UTC del día actual
    ny_start = datetime(day_date.year, day_date.month, day_date.day, 14, 30)
    ny_end   = datetime(day_date.year, day_date.month, day_date.day, 21,  0)

    ny_bars = filter_bars(bars, ny_start, ny_end)

    if len(ny_bars) < 2:
        results.append({"date": day_date, "weekday": weekday, "skip": "sin datos NY",
                       "vah": vah, "poc": poc, "val": val})
        continue

    ny_open  = ny_bars[0]["open"]
    ny_close = ny_bars[-1]["close"]
    ny_high  = max(b["high"] for b in ny_bars)
    ny_low   = min(b["low"]  for b in ny_bars)
    bullish  = ny_close > ny_open

    # ── Análisis por nivel ───────────────────────────────────
    def analyze(level, direction):
        """
        direction = 'up'   → nivel es soporte (VAL), ruptura = cierra DEBAJO
        direction = 'down' → nivel es resistencia (VAH), ruptura = cierra ENCIMA
        direction = 'mid'  → POC, ruptura = cierra al otro lado del open
        """
        if direction == "up":         # VAL
            touched = ny_low <= level + TOUCH_MARGIN
            if touched:
                broke = any(b["close"] < level - BREAK_MARGIN for b in ny_bars)
                status = "RUPTURA" if broke else "RESPETO"
            else:
                status = "NO_TESTEO"
        elif direction == "down":     # VAH
            touched = ny_high >= level - TOUCH_MARGIN
            if touched:
                broke = any(b["close"] > level + BREAK_MARGIN for b in ny_bars)
                status = "RUPTURA" if broke else "RESPETO"
            else:
                status = "NO_TESTEO"
        else:                         # POC
            touched = ny_low <= level + TOUCH_MARGIN and ny_high >= level - TOUCH_MARGIN
            if touched:
                open_above  = ny_open  > level
                close_above = ny_close > level
                broke = (open_above != close_above)
                status = "RUPTURA" if broke else "RESPETO"
            else:
                status = "NO_TESTEO"
        return status, touched

    val_status, touched_val = analyze(val, "up")
    vah_status, touched_vah = analyze(vah, "down")
    poc_status, touched_poc = analyze(poc, "mid")

    results.append({
        "date"       : day_date,
        "weekday"    : weekday,
        "skip"       : None,
        "vah"        : vah,
        "poc"        : poc,
        "val"        : val,
        "ny_open"    : ny_open,
        "ny_close"   : ny_close,
        "ny_high"    : ny_high,
        "ny_low"     : ny_low,
        "bullish"    : bullish,
        "val_status" : val_status,
        "poc_status" : poc_status,
        "vah_status" : vah_status,
        "touched_val": touched_val,
        "touched_poc": touched_poc,
        "touched_vah": touched_vah,
    })

# ══════════════════════════════════════════════════════════════
#  ESTADÍSTICAS
# ══════════════════════════════════════════════════════════════
valid   = [r for r in results if r["skip"] is None]
skipped = [r for r in results if r["skip"]]

def stats(days, nivel):
    key_t = f"touched_{nivel}"
    key_s = f"{nivel}_status"
    tot   = len(days)
    test  = [d for d in days if d[key_t]]
    resp  = [d for d in test  if d[key_s] == "RESPETO"]
    rupt  = [d for d in test  if d[key_s] == "RUPTURA"]
    no_t  = tot - len(test)
    pct   = round(len(resp)/len(test)*100,1) if test else 0
    return len(test), len(resp), len(rupt), no_t, pct

SEP = "─" * 72

def print_table(titulo, days):
    n = len(days)
    if n == 0: return
    bull = sum(1 for d in days if d["bullish"])
    bear = n - bull
    print(f"\n  {SEP}")
    print(f"  {titulo}  (N={n}  |  🟢 Bull={bull}  🔴 Bear={bear})")
    print(f"  {SEP}")
    print(f"  {'Nivel':<6}  {'Testeó':>7}  {'Respetó':>9}  {'Rompió':>8}  {'NoTest':>7}  {'%Respeto':>9}")
    print(f"  {SEP}")
    for nivel in ["val", "poc", "vah"]:
        t, r, rp, nt, pct = stats(days, nivel)
        print(f"  {nivel.upper():<6}  {t:>7}  {r:>9}  {rp:>8}  {nt:>7}  {pct:>8.1f}%")

# ── Global ──────────────────────────────────────────────────
print()
print("═" * 72)
print("  BACKTEST VP  |  Perfil Asia+London → Sesión NY  |  NQ 15m")
print("═" * 72)
print(f"\n  Perfil  : 23:00 UTC (día prev) → 13:20 UTC")
print(f"  NY      : 14:30 UTC → 21:00 UTC")
print(f"  Datos   : {valid[0]['date'] if valid else '?'}  →  {valid[-1]['date'] if valid else '?'}")
print(f"  Días OK : {len(valid)}   |   Omitidos: {len(skipped)}")

print_table("📊 TODOS LOS DÍAS", valid)

# ── Por día de semana ────────────────────────────────────────
for wd in range(5):
    dias_wd = [r for r in valid if r["weekday"] == wd]
    print_table(f"📅 {DAYS_ES[wd].upper()}", dias_wd)

# ── Bullish vs Bearish (global) ──────────────────────────────
print_table("🟢 DÍAS BULLISH (NY cierra > NY abre)", [r for r in valid if r["bullish"]])
print_table("🔴 DÍAS BEARISH (NY cierra < NY abre)", [r for r in valid if not r["bullish"]])

# ── Detalle día a día ────────────────────────────────────────
print(f"\n  {SEP}")
print(f"  DETALLE  DÍA A DÍA")
print(f"  {SEP}")
print(f"  {'Fecha':<12} {'Día':<10} {'Dir':<6}  {'VAL':>8} {'POC':>8} {'VAH':>8}  {'VAL':^10} {'POC':^10} {'VAH':^10}")
print(f"  {SEP}")
for r in valid:
    dia = DAYS_ES.get(r["weekday"], "?")
    dir_s = "🟢" if r["bullish"] else "🔴"
    print(f"  {str(r['date']):<12} {dia:<10} {dir_s:<6}"
          f"  {r['val']:>8.0f} {r['poc']:>8.0f} {r['vah']:>8.0f}"
          f"  {r['val_status']:<10} {r['poc_status']:<10} {r['vah_status']:<10}")

print(f"\n  {SEP}")
print(f"  LEYENDA:")
print(f"  RESPETO   = precio tocó el nivel pero no cerró al otro lado")
print(f"  RUPTURA   = precio cerró >{BREAK_MARGIN:.0f}pts al otro lado del nivel")
print(f"  NO_TESTEO = precio no llegó al nivel durante NY")
print(f"  Touch margin: ±{TOUCH_MARGIN:.0f}pts   Break margin: {BREAK_MARGIN:.0f}pts")
print()
