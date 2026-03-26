"""
backtest_martes_estadistico_5m.py
==================================
FASE 1 — Estudio completo del MARTES (sin filtro COT)
Datos: yfinance 5m, NQ=F, 2 años

Por cada Martes analiza COMPLETO desde Asia (Dom 6PM ET) hasta cierre (4PM ET):
  ─ Asia    : Dom 6PM → 2AM ET
  ─ London  : 2AM → 9:30AM ET
  ─ NY Open : 9:30AM → 11AM ET  (primeros 90 min)
  ─ NY Core : 11AM → 2PM ET
  ─ NY PM   : 2PM → 4PM ET
  ─ Día total

Métricas:
  ✓ Rango, dirección (bull/bear), pts por sesión
  ✓ ¿Qué sesión marca el HIGH y LOW del día?
  ✓ Market Profile pre-NY (POC / VAH / VAL)
  ✓ Correlación Asia → NY (si Asia sube ¿NY sube?)
  ✓ Win rate LONG / SHORT en NY open
  ✓ Estadísticas de distribución de range
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timezone, date, timedelta
from collections import defaultdict

# ── Descarga ─────────────────────────────────────────────────────────────────
print("=" * 70)
print("  DESCARGANDO NQ=F 5min — 2 años...")
print("=" * 70)

# yfinance 5m max ~60 days por llamada, necesitamos 2 años en chunks
all_bars = []
end_dt   = datetime.now(timezone.utc)
start_dt = end_dt - timedelta(days=730)
chunk    = timedelta(days=55)
cur      = start_dt

while cur < end_dt:
    nxt = min(cur + chunk, end_dt)
    try:
        df = yf.download("NQ=F",
                         start=cur.strftime("%Y-%m-%d"),
                         end=nxt.strftime("%Y-%m-%d"),
                         interval="5m", prepost=True,
                         progress=False, auto_adjust=True)
        if not df.empty:
            if hasattr(df.columns, 'levels'):
                df.columns = df.columns.get_level_values(0)
            for ts, row in df.iterrows():
                try:
                    if hasattr(ts, 'tz') and ts.tz is not None:
                        ts_utc = ts.tz_convert("UTC")
                    else:
                        ts_utc = ts.tz_localize("UTC")
                    all_bars.append({
                        "ts"   : ts_utc,
                        "open" : float(row["Open"]),
                        "high" : float(row["High"]),
                        "low"  : float(row["Low"]),
                        "close": float(row["Close"]),
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"  Error chunk {cur.date()} → {nxt.date()}: {e}")
    cur = nxt

# Deduplica y ordena
seen = set()
bars = []
for b in all_bars:
    k = b["ts"]
    if k not in seen:
        seen.add(k)
        bars.append(b)
bars.sort(key=lambda x: x["ts"])
print(f"  Total barras 5m: {len(bars)}")
print(f"  Rango: {bars[0]['ts'].date()} → {bars[-1]['ts'].date()}")
print()

# ── Agrupa por fecha UTC date ─────────────────────────────────────────────────
by_date = defaultdict(list)
for b in bars:
    # Fecha "de trading" = fecha del NY open (UTC-4 aprox)
    et_hour = (b["ts"].hour - 4) % 24
    # Si es antes de 6PM ET del día anterior → pertenece al "lunes" (día de trading)
    # Simplificamos: agrupamos por fecha UTC ajustada
    d = b["ts"].date()
    by_date[d].append(b)

# ── Funciones de sesión ───────────────────────────────────────────────────────
def is_dst(d):
    return 3 <= d.month <= 10  # aproximación DST USA

def session_bars(day_bars, start_utc_h, end_utc_h, offset_days=0):
    """Filtra barras en rango de horas UTC. offset_days=-1 para noche anterior."""
    result = []
    for b in day_bars:
        h = b["ts"].hour
        if start_utc_h < end_utc_h:
            if start_utc_h <= h < end_utc_h:
                result.append(b)
        else:  # overnight
            if h >= start_utc_h or h < end_utc_h:
                result.append(b)
    return result

def stats_session(sbars):
    if not sbars:
        return None
    hi   = max(b["high"]  for b in sbars)
    lo   = min(b["low"]   for b in sbars)
    op   = sbars[0]["open"]
    cl   = sbars[-1]["close"]
    rang = round(hi - lo, 1)
    move = round(cl - op, 1)
    bull = move >= 0
    return {"hi": hi, "lo": lo, "open": op, "close": cl,
            "range": rang, "move": move, "bull": bull}

def market_profile(sbars, bucket=25.0):
    """POC/VAH/VAL con bucket de precio fijo."""
    if not sbars:
        return None
    lo_all = min(b["low"]  for b in sbars)
    hi_all = max(b["high"] for b in sbars)
    nb = max(1, int((hi_all - lo_all) / bucket) + 1)
    vol = [0.0] * nb
    for b in sbars:
        i0 = int((b["low"]  - lo_all) / bucket)
        i1 = int((b["high"] - lo_all) / bucket)
        for i in range(max(0, i0), min(i1 + 1, nb)):
            vol[i] += 1
    pi  = vol.index(max(vol))
    poc = round(lo_all + pi * bucket + bucket / 2, 1)
    # Value Area 70%
    tv  = sum(vol) * 0.70
    li = hi = pi
    acc = vol[pi]
    while acc < tv:
        can_lo = li > 0
        can_hi = hi < nb - 1
        if can_lo and can_hi:
            if vol[li - 1] >= vol[hi + 1]:
                li -= 1; acc += vol[li]
            else:
                hi += 1; acc += vol[hi]
        elif can_lo:
            li -= 1; acc += vol[li]
        elif can_hi:
            hi += 1; acc += vol[hi]
        else:
            break
    vah = round(lo_all + hi * bucket + bucket, 1)
    val = round(lo_all + li * bucket, 1)
    return {"poc": poc, "vah": vah, "val": val}

# ── Análisis por día ──────────────────────────────────────────────────────────
#
# Horarios UTC aproximados (ajuste DST):
#  DST ON  (mar-oct): ET = UTC-4
#    Asia start : 22:00 UTC domingo (6PM ET dom)
#    London     : 06:00 UTC
#    NY open    : 13:30 UTC
#    NY close   : 20:00 UTC
#  DST OFF (nov-feb): ET = UTC-5
#    Asia start : 23:00 UTC
#    London     : 07:00 UTC
#    NY open    : 14:30 UTC
#    NY close   : 21:00 UTC

results = []

for d in sorted(by_date.keys()):
    # Queremos los MARTES (weekday=1)
    if d.weekday() != 1:
        continue

    dst = is_dst(d)
    ny_open_h  = 13 if dst else 14   # 9:30 ET en UTC (ignoramos :30 para simplicidad)
    ny_open_m  = 30
    london_h   = 6  if dst else 7
    asia_start = 22 if dst else 23   # domingo previo

    # Fecha lunes (día anterior = lunes) para buscar barras de Asia/London
    mon = d - timedelta(days=1)  # el lunes antes del martes

    # Agrupamos todas las barras de lunes+martes
    all_day_bars = by_date.get(mon, []) + by_date.get(d, [])
    all_day_bars.sort(key=lambda x: x["ts"])

    if not all_day_bars:
        continue

    # Computa timestamps de referencia para el martes
    import calendar
    asia_start_ts  = datetime(d.year, mon.month, mon.day, asia_start, 0, tzinfo=timezone.utc)
    london_ts      = datetime(d.year, d.month, d.day, london_h, 0, tzinfo=timezone.utc)
    ny_open_ts     = datetime(d.year, d.month, d.day, ny_open_h, ny_open_m, tzinfo=timezone.utc)
    ny_11am_ts     = datetime(d.year, d.month, d.day, ny_open_h + 1, 30, tzinfo=timezone.utc)
    ny_2pm_ts      = datetime(d.year, d.month, d.day, ny_open_h + 4, 30, tzinfo=timezone.utc) if dst else datetime(d.year, d.month, d.day, 19, 30, tzinfo=timezone.utc)
    ny_close_ts    = datetime(d.year, d.month, d.day, 20 if dst else 21, 0, tzinfo=timezone.utc)

    def filt(lo, hi):
        return [b for b in all_day_bars if lo <= b["ts"] < hi]

    asia_bars   = filt(asia_start_ts, london_ts)
    london_bars = filt(london_ts,     ny_open_ts)
    ny1_bars    = filt(ny_open_ts,    ny_11am_ts)   # 9:30–11am
    ny2_bars    = filt(ny_11am_ts,    ny_2pm_ts)    # 11am–2pm
    ny3_bars    = filt(ny_2pm_ts,     ny_close_ts)  # 2pm–4pm
    all_ny      = filt(ny_open_ts,    ny_close_ts)

    if not all_ny or not ny1_bars:
        continue

    asia_s   = stats_session(asia_bars)
    london_s = stats_session(london_bars)
    ny1_s    = stats_session(ny1_bars)
    ny2_s    = stats_session(ny2_bars)
    ny3_s    = stats_session(ny3_bars)
    ny_s     = stats_session(all_ny)

    # Market Profile pre-NY (Asia + London)
    pre_ny = asia_bars + london_bars
    mp = market_profile(pre_ny) if pre_ny else None

    # ¿Qué sesión marca el HIGH/LOW del día?
    all_session_bars = asia_bars + london_bars + all_ny
    if not all_session_bars:
        continue
    day_hi  = max(b["high"] for b in all_session_bars)
    day_lo  = min(b["low"]  for b in all_session_bars)
    day_rng = round(day_hi - day_lo, 1)

    def which_session_hi(hi_val):
        if asia_bars and max(b["high"] for b in asia_bars) >= hi_val - 1:
            return "ASIA"
        if london_bars and max(b["high"] for b in london_bars) >= hi_val - 1:
            return "LONDON"
        if ny1_bars and max(b["high"] for b in ny1_bars) >= hi_val - 1:
            return "NY_OPEN"
        if ny2_bars and max(b["high"] for b in ny2_bars) >= hi_val - 1:
            return "NY_CORE"
        return "NY_PM"

    def which_session_lo(lo_val):
        if asia_bars and min(b["low"] for b in asia_bars) <= lo_val + 1:
            return "ASIA"
        if london_bars and min(b["low"] for b in london_bars) <= lo_val + 1:
            return "LONDON"
        if ny1_bars and min(b["low"] for b in ny1_bars) <= lo_val + 1:
            return "NY_OPEN"
        if ny2_bars and min(b["low"] for b in ny2_bars) <= lo_val + 1:
            return "NY_CORE"
        return "NY_PM"

    results.append({
        "date"       : d,
        "asia"       : asia_s,
        "london"     : london_s,
        "ny1"        : ny1_s,   # 9:30–11am
        "ny2"        : ny2_s,   # 11am–2pm
        "ny3"        : ny3_s,   # 2pm–4pm
        "ny"         : ny_s,
        "mp"         : mp,
        "day_hi"     : day_hi,
        "day_lo"     : day_lo,
        "day_range"  : day_rng,
        "hi_session" : which_session_hi(day_hi),
        "lo_session" : which_session_lo(day_lo),
    })

# ── Estadísticas globales ─────────────────────────────────────────────────────
N = len(results)
print(f"  Martes analizados: {N}")
print()

def pct(count, total):
    return f"{count/total*100:.0f}%" if total else "0%"

def avg(vals):
    return round(sum(vals) / len(vals), 1) if vals else 0

# ── Imprime resumen ───────────────────────────────────────────────────────────
print("=" * 70)
print("  FASE 1 — ESTUDIO COMPLETO MARTES | NQ=F 5m | 2 AÑOS")
print("=" * 70)

# ── ASIA ─────────────────────────────────────────────────────────────────────
asia_bull = [r for r in results if r["asia"] and r["asia"]["bull"]]
asia_bear = [r for r in results if r["asia"] and not r["asia"]["bull"]]
asia_ranges = [r["asia"]["range"] for r in results if r["asia"]]
asia_moves  = [r["asia"]["move"]  for r in results if r["asia"]]
print()
print("  ── 🌏 ASIA (Dom 6PM → 2AM ET) ──────────────────────────────")
print(f"  Alcista : {len(asia_bull)}/{N} ({pct(len(asia_bull), N)})")
print(f"  Bajista : {len(asia_bear)}/{N} ({pct(len(asia_bear), N)})")
print(f"  Avg Range: {avg(asia_ranges)} pts")
print(f"  Avg Move : {avg(asia_moves):+.1f} pts")

# ── LONDON ────────────────────────────────────────────────────────────────────
lon_bull = [r for r in results if r["london"] and r["london"]["bull"]]
lon_bear = [r for r in results if r["london"] and not r["london"]["bull"]]
lon_ranges = [r["london"]["range"] for r in results if r["london"]]
lon_moves  = [r["london"]["move"]  for r in results if r["london"]]
print()
print("  ── 🇬🇧 LONDON (2AM → 9:30AM ET) ───────────────────────────")
print(f"  Alcista : {len(lon_bull)}/{N} ({pct(len(lon_bull), N)})")
print(f"  Bajista : {len(lon_bear)}/{N} ({pct(len(lon_bear), N)})")
print(f"  Avg Range: {avg(lon_ranges)} pts")
print(f"  Avg Move : {avg(lon_moves):+.1f} pts")

# ── NY OPEN (9:30–11am) ───────────────────────────────────────────────────────
ny1_bull = [r for r in results if r["ny1"] and r["ny1"]["bull"]]
ny1_bear = [r for r in results if r["ny1"] and not r["ny1"]["bull"]]
ny1_ranges = [r["ny1"]["range"] for r in results if r["ny1"]]
ny1_moves  = [r["ny1"]["move"]  for r in results if r["ny1"]]
print()
print("  ── 🗽 NY OPEN (9:30 → 11:00AM ET) ─────────────────────────")
print(f"  Alcista : {len(ny1_bull)}/{N} ({pct(len(ny1_bull), N)})")
print(f"  Bajista : {len(ny1_bear)}/{N} ({pct(len(ny1_bear), N)})")
print(f"  Avg Range: {avg(ny1_ranges)} pts")
print(f"  Avg Move : {avg(ny1_moves):+.1f} pts")

# ── NY CORE (11am–2pm) ────────────────────────────────────────────────────────
ny2_bull = [r for r in results if r["ny2"] and r["ny2"]["bull"]]
ny2_ranges = [r["ny2"]["range"] for r in results if r["ny2"]]
print()
print("  ── NY CORE (11AM → 2PM ET) ─────────────────────────────────")
print(f"  Alcista : {len(ny2_bull)}/{N} ({pct(len(ny2_bull), N)})")
print(f"  Avg Range: {avg(ny2_ranges)} pts")

# ── NY PM (2pm–4pm) ───────────────────────────────────────────────────────────
ny3_bull = [r for r in results if r["ny3"] and r["ny3"]["bull"]]
ny3_ranges = [r["ny3"]["range"] for r in results if r["ny3"]]
print()
print("  ── NY PM (2PM → 4PM ET) ────────────────────────────────────")
print(f"  Alcista : {len(ny3_bull)}/{N} ({pct(len(ny3_bull), N)})")
print(f"  Avg Range: {avg(ny3_ranges)} pts")

# ── DÍA COMPLETO ──────────────────────────────────────────────────────────────
ny_bull  = [r for r in results if r["ny"]["bull"]]
ny_bear  = [r for r in results if not r["ny"]["bull"]]
day_ranges = [r["day_range"] for r in results]
ny_ranges  = [r["ny"]["range"] for r in results]
ny_moves   = [r["ny"]["move"]  for r in results]
print()
print("  ── 📊 DÍA COMPLETO (sesión NY) ─────────────────────────────")
print(f"  NY Alcista: {len(ny_bull)}/{N} ({pct(len(ny_bull), N)})")
print(f"  NY Bajista: {len(ny_bear)}/{N} ({pct(len(ny_bear), N)})")
print(f"  Avg Day Range : {avg(day_ranges)} pts")
print(f"  Avg NY Range  : {avg(ny_ranges)} pts")
print(f"  Avg NY Move   : {avg(ny_moves):+.1f} pts")

# ── ¿QUÉ SESIÓN MARCA EL HIGH/LOW DEL DÍA? ──────────────────────────────────
print()
print("  ── 🔍 ¿QUÉ SESIÓN MARCA EL HIGH DEL DÍA? ──────────────────")
for sess in ["ASIA", "LONDON", "NY_OPEN", "NY_CORE", "NY_PM"]:
    cnt = sum(1 for r in results if r["hi_session"] == sess)
    print(f"  {sess:<10}: {cnt:>3}/{N} ({pct(cnt, N)})")

print()
print("  ── 🔍 ¿QUÉ SESIÓN MARCA EL LOW DEL DÍA? ───────────────────")
for sess in ["ASIA", "LONDON", "NY_OPEN", "NY_CORE", "NY_PM"]:
    cnt = sum(1 for r in results if r["lo_session"] == sess)
    print(f"  {sess:<10}: {cnt:>3}/{N} ({pct(cnt, N)})")

# ── CORRELACIÓN ASIA → NY ─────────────────────────────────────────────────────
print()
print("  ── 🔗 CORRELACIÓN: ¿Si Asia sube, NY sube? ────────────────")
both_bull  = sum(1 for r in results if r["asia"] and r["asia"]["bull"] and r["ny"]["bull"])
asia_up    = sum(1 for r in results if r["asia"] and r["asia"]["bull"])
both_bear  = sum(1 for r in results if r["asia"] and not r["asia"]["bull"] and not r["ny"]["bull"])
asia_dn    = sum(1 for r in results if r["asia"] and not r["asia"]["bull"])
print(f"  Asia ↑ → NY ↑: {both_bull}/{asia_up} ({pct(both_bull, asia_up)})")
print(f"  Asia ↓ → NY ↓: {both_bear}/{asia_dn} ({pct(both_bear, asia_dn)})")

# Correlación London → NY
lon_up_ny_up = sum(1 for r in results if r["london"] and r["london"]["bull"] and r["ny"]["bull"])
lon_up = sum(1 for r in results if r["london"] and r["london"]["bull"])
lon_dn_ny_dn = sum(1 for r in results if r["london"] and not r["london"]["bull"] and not r["ny"]["bull"])
lon_dn = sum(1 for r in results if r["london"] and not r["london"]["bull"])
print(f"  London ↑ → NY ↑: {lon_up_ny_up}/{lon_up} ({pct(lon_up_ny_up, lon_up)})")
print(f"  London ↓ → NY ↓: {lon_dn_ny_dn}/{lon_dn} ({pct(lon_dn_ny_dn, lon_dn)})")

# ── MARKET PROFILE PRE-NY ─────────────────────────────────────────────────────
print()
print("  ── 📈 MARKET PROFILE PRE-NY (Asia+London) ──────────────────")
mp_list = [r["mp"] for r in results if r["mp"]]
poc_vals = [m["poc"] for m in mp_list]
print(f"  Martes con VP calculado: {len(mp_list)}")

# ¿Qué pasa cuando NY open está dentro del VA?
in_va = sum(1 for r in results if r["mp"] and
             r["mp"]["val"] <= r["ny1"]["open"] <= r["mp"]["vah"])
print(f"  NY Open inside VA      : {in_va}/{len(mp_list)} ({pct(in_va, len(mp_list))})")

# Si NY open dentro del VA → ¿NY alcista?
va_bull = sum(1 for r in results if r["mp"] and
               r["mp"]["val"] <= r["ny1"]["open"] <= r["mp"]["vah"] and r["ny"]["bull"])
print(f"  (VA in + NY bull)      : {va_bull}/{in_va} ({pct(va_bull, in_va)}) cuando dentro de VA")

# ── DISTRIBUCIÓN RANGE ────────────────────────────────────────────────────────
print()
print("  ── 📊 DISTRIBUCIÓN RANGE NY (total día) ────────────────────")
buckets = [(0,100,"0–100 pts"), (100,200,"100–200 pts"),
           (200,300,"200–300 pts"), (300,400,"300–400 pts"),
           (400,600,"400–600 pts"), (600,9999,"+600 pts")]
for lo, hi, label in buckets:
    cnt = sum(1 for r in results if lo <= r["ny"]["range"] < hi)
    bar = "█" * int(cnt / max(1, N) * 30)
    print(f"  {label:<14}: {cnt:>3}/{N} ({pct(cnt, N)}) {bar}")

# ── TABLA DÍA A DÍA ──────────────────────────────────────────────────────────
print()
print("  ── 📅 DÍA A DÍA (últimos 20 Martes) ───────────────────────")
print(f"  {'Fecha':<13} {'AsiaRng':>8} {'LonRng':>8} {'NY1Mov':>8} {'NYMov':>8} {'DayRng':>8} {'Dir':<8} {'HiSes':<8} {'LoSes':<8}")
print("  " + "-" * 80)
for r in results[-20:]:
    a_rng = f"{r['asia']['range']:>7.0f}" if r["asia"] else "   N/A"
    l_rng = f"{r['london']['range']:>7.0f}" if r["london"] else "   N/A"
    ny1m  = f"{r['ny1']['move']:>+7.0f}" if r["ny1"] else "   N/A"
    nym   = f"{r['ny']['move']:>+7.0f}"
    drng  = f"{r['day_range']:>7.0f}"
    dir_  = "↑ BULL" if r["ny"]["bull"] else "↓ BEAR"
    print(f"  {str(r['date']):<13} {a_rng} {l_rng} {ny1m} {nym} {drng} {dir_:<8} {r['hi_session']:<8} {r['lo_session']:<8}")

print()
print("=" * 70)
print("  ✅ FASE 1 COMPLETA — Resultado guardado en terminal")
print("  → Siguiente: python backtest_martes_cot_estudio.py  (Fase 2)")
print("=" * 70)
