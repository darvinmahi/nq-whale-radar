"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   BACKTEST  NY SESSION  11:00 AM → 4:00 PM CLOSE                          ║
║   NQ NASDAQ  |  60 DÍAS  |  15 MINUTOS                                    ║
║                                                                              ║
║   LÓGICA:                                                                   ║
║   1. Profile Asia + London del MISMO DÍA  (12:00 AM → 9:20 AM ET)        ║
║   2. Extraer VAH, POC, VAL (Value Area 70%)                               ║
║   3. Operar NY PM (11:00 AM → 4:00 PM) con esos niveles como referencia   ║
║                                                                              ║
║   RESOLUCIÓN: 15 minutos — máx. ~60 días Yahoo Finance                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json, os
from datetime import timedelta
from collections import Counter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════
#  PARÁMETROS
# ══════════════════════════════════════════════════════════
PROFILE_START_H, PROFILE_START_M = 0,  0   # 12:00 AM ET
PROFILE_END_H,   PROFILE_END_M   = 9, 20   #  9:20 AM ET  (10 min antes NY open)

PM_START_H = 11    # 11:00 AM ET
PM_END_H   = 15    # hasta las 15:59 (16:00 close)

MARGIN     = 10    # puntos tolerancia "toca nivel"
SWEEP_BUF  = 8     # puntos para confirmar "rompió"
SL_MULT    = 0.20  # stop = 20% del VA range
RR         = 2.0   # risk reward objetivo
VA_PCT     = 0.70  # Value Area = 70% del volumen

DAYS_ES = {0:"LUNES", 1:"MARTES", 2:"MIÉRCOLES", 3:"JUEVES", 4:"VIERNES"}

print("═"*72)
print("  🗽 BACKTEST NY PM — Profile Asia+London (15 min | 60 días)")
print("  Niveles: VAH / POC / VAL  →  Opera 11 AM → 4 PM Close")
print("═"*72)

# ══════════════════════════════════════════════════════════
#  DESCARGA DE DATOS
# ══════════════════════════════════════════════════════════
print("\n📡 Descargando NQ=F  15m  (60 días)...")
try:
    df_raw = yf.download("NQ=F", period="60d", interval="15m", progress=False)
    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)
    if df_raw.index.tz is None:
        df_raw.index = df_raw.index.tz_localize("UTC")
    df_raw.index = df_raw.index.tz_convert("America/New_York")
    df_raw = df_raw.sort_index()
    print(f"  ✅ {len(df_raw)} velas  ({df_raw.index[0].date()} → {df_raw.index[-1].date()})")
except Exception as e:
    print(f"  ❌ {e}"); raise

print("📡 Descargando NQ=F  diario (EMA200/50)...")
try:
    nq_d = yf.download("NQ=F", period="1y", interval="1d", progress=False)
    if isinstance(nq_d.columns, pd.MultiIndex):
        nq_d.columns = nq_d.columns.get_level_values(0)
    if nq_d.index.tz is None:
        nq_d.index = nq_d.index.tz_localize("UTC")
    nq_d.index = nq_d.index.tz_convert("America/New_York")
    nq_d["EMA200"] = nq_d["Close"].ewm(span=200, adjust=False).mean()
    nq_d["EMA50"]  = nq_d["Close"].ewm(span=50,  adjust=False).mean()
    ema200_map = {d.date(): float(v) for d, v in nq_d["EMA200"].items() if not pd.isna(v)}
    ema50_map  = {d.date(): float(v) for d, v in nq_d["EMA50"].items()  if not pd.isna(v)}
    print(f"  ✅ Diario OK — EMA200/50 calculadas")
except Exception as e:
    print(f"  ⚠️  EMA no disponible: {e}")
    ema200_map, ema50_map = {}, {}

# ══════════════════════════════════════════════════════════
#  PREPARAR DF
# ══════════════════════════════════════════════════════════
df = df_raw.copy()
df["hour"]    = df.index.hour
df["minute"]  = df.index.minute
df["date"]    = df.index.normalize()
df["weekday"] = df.index.dayofweek

days_list = sorted(df["date"].unique())
print(f"\n  📅 Período: {days_list[0].date()} → {days_list[-1].date()}")
print(f"  📊 Días con datos: {len(days_list)}")


# ══════════════════════════════════════════════════════════
#  FUNCIONES
# ══════════════════════════════════════════════════════════
def build_profile(data, n_bins=120):
    """Construye Volume Profile y devuelve (VAL, POC, VAH)."""
    if len(data) < 2:
        mid = float(data["Close"].mean()) if not data.empty else 0
        return mid, mid, mid

    lo = float(data["Low"].min())
    hi = float(data["High"].max())
    if hi <= lo:
        m = (hi + lo) / 2; return m, m, m

    bins   = np.linspace(lo, hi, n_bins + 1)
    vol_at = np.zeros(n_bins)

    for _, row in data.iterrows():
        rlo  = float(row["Low"])
        rhi  = float(row["High"])
        rvol = float(row.get("Volume", 1)) or 1
        span = rhi - rlo if rhi > rlo else 1e-9
        for b in range(n_bins):
            ov = min(rhi, bins[b+1]) - max(rlo, bins[b])
            if ov > 0:
                vol_at[b] += rvol * (ov / span)

    if vol_at.sum() == 0:
        m = (hi + lo) / 2; return m, m, m

    poc_idx = int(np.argmax(vol_at))
    poc     = (bins[poc_idx] + bins[poc_idx + 1]) / 2.0

    target = vol_at.sum() * VA_PCT
    acc    = vol_at[poc_idx]
    hi_i   = poc_idx
    lo_i   = poc_idx

    while acc < target:
        can_up = hi_i + 1 < n_bins
        can_dn = lo_i - 1 >= 0
        if not can_up and not can_dn: break
        v_up = vol_at[hi_i + 1] if can_up else -1.0
        v_dn = vol_at[lo_i - 1] if can_dn else -1.0
        if v_up >= v_dn: hi_i += 1; acc += v_up
        else:            lo_i -= 1; acc += v_dn

    vah = (bins[hi_i] + bins[hi_i + 1]) / 2.0
    val = (bins[lo_i] + bins[lo_i + 1]) / 2.0
    return val, poc, vah


def sim_trade(bars, entry, target, stop, direction):
    """Simula trade barra a barra en 15m. Devuelve (resultado, pnl_pts)."""
    entered = False
    for _, b in bars.iterrows():
        lo_b = float(b["Low"])
        hi_b = float(b["High"])

        if direction == "BUY":
            if not entered and lo_b <= entry <= hi_b:
                entered = True
            if entered:
                if lo_b <= stop:   return "LOSS", round(stop   - entry, 1)
                if hi_b >= target: return "WIN",  round(target - entry, 1)
        else:  # SELL
            if not entered and lo_b <= entry <= hi_b:
                entered = True
            if entered:
                if hi_b >= stop:   return "LOSS", round(stop   - entry, 1)
                if lo_b <= target: return "WIN",  round(target - entry, 1)

    if not entered: return "NO_ENTRY", 0.0
    last = float(bars.iloc[-1]["Close"]) if not bars.empty else entry
    pnl  = (last - entry) if direction == "BUY" else (entry - last)
    return "FLAT", round(pnl, 1)


def first_touch_bar(bars, level, direction="up", margin=10):
    """
    Devuelve la primera barra donde el precio toca 'level'.
    direction='up' → busca que High >= level-margin
    direction='dn' → busca que Low  <= level+margin
    """
    for i, (_, b) in enumerate(bars.iterrows()):
        if direction == "up" and float(b["High"]) >= level - margin:
            return i, b
        if direction == "dn" and float(b["Low"])  <= level + margin:
            return i, b
    return None, None


# ══════════════════════════════════════════════════════════
#  BUCLE PRINCIPAL
# ══════════════════════════════════════════════════════════
print("\n🔍 Analizando sesiones dia a dia (15 min)...")

results    = []
all_trades = []
skipped    = 0
analyzed   = 0

for day in days_list:
    wd = pd.Timestamp(day).weekday()
    if wd > 4: continue

    day_data = df[df["date"] == day]
    if day_data.empty: skipped += 1; continue

    date_obj = pd.Timestamp(day).date()

    # ── 1. PROFILE: 12:00 AM → 9:19 AM ─────────────────────────────
    prof_data = day_data[
        (
            (day_data["hour"] > PROFILE_START_H) |
            ((day_data["hour"] == PROFILE_START_H) & (day_data["minute"] >= PROFILE_START_M))
        ) &
        (
            (day_data["hour"] < PROFILE_END_H) |
            ((day_data["hour"] == PROFILE_END_H) & (day_data["minute"] < PROFILE_END_M))
        )
    ]

    if len(prof_data) < 4:
        skipped += 1; continue

    val, poc, vah = build_profile(prof_data)
    va_range      = vah - val

    if va_range < 8:
        skipped += 1; continue

    prof_hi = float(prof_data["High"].max())
    prof_lo = float(prof_data["Low"].min())

    # ── 2. NY OPEN: 1ª barra de las 9:30 ────────────────────────────
    ny_open_bars = day_data[
        (day_data["hour"] == 9) & (day_data["minute"] >= 30)
    ]
    if ny_open_bars.empty:
        skipped += 1; continue

    ny_open_price = float(ny_open_bars.iloc[0]["Open"])

    if   ny_open_price > vah + MARGIN: ny_open_pos = "ABOVE_VA"
    elif ny_open_price < val - MARGIN: ny_open_pos = "BELOW_VA"
    else:                              ny_open_pos = "INSIDE_VA"

    # ── 3. AM SESSION: 9:30 → 10:59 ─────────────────────────────────
    am_data = day_data[
        ((day_data["hour"] == 9)  & (day_data["minute"] >= 30)) |
         (day_data["hour"] == 10)
    ]
    if am_data.empty: skipped += 1; continue

    am_hi    = float(am_data["High"].max())
    am_lo    = float(am_data["Low"].min())
    am_open  = float(am_data.iloc[0]["Open"])
    am_close = float(am_data.iloc[-1]["Close"])

    # ── 4. NY PM SESSION: 11:00 → 15:59 (barras exactas) ───────────
    pm_data = day_data[
        (day_data["hour"] >= PM_START_H) & (day_data["hour"] <= PM_END_H)
    ]
    if len(pm_data) < 4: skipped += 1; continue

    pm_hi    = float(pm_data["High"].max())
    pm_lo    = float(pm_data["Low"].min())
    pm_open  = float(pm_data.iloc[0]["Open"])
    pm_close = float(pm_data.iloc[-1]["Close"])
    pm_range = pm_hi - pm_lo

    # ── 5. INTERACCIONES PM vs PROFILE ──────────────────────────────
    # Toca = precio pasó por esa zona
    touches_vah = pm_hi >= vah - MARGIN
    touches_val = pm_lo <= val + MARGIN
    touches_poc = (pm_lo <= poc + MARGIN) and (pm_hi >= poc - MARGIN)

    # Rompe = superó claramente el nivel
    breaks_vah  = pm_hi > vah + SWEEP_BUF
    breaks_val  = pm_lo < val - SWEEP_BUF

    # Tipo de acción en VAH (bounce o breakout)
    vah_bounce   = touches_vah and not breaks_vah
    val_bounce   = touches_val and not breaks_val
    vah_breakout = breaks_vah
    val_breakout = breaks_val

    # Cierre vs value area
    close_above_va = pm_close > vah
    close_below_va = pm_close < val
    close_inside   = val <= pm_close <= vah

    # Dirección PM general
    pm_dir = ("BULLISH"  if pm_close > pm_open + 20
              else "BEARISH" if pm_close < pm_open - 20
              else "NEUTRAL")

    # Open PM respecto al profile
    if   pm_open > vah + MARGIN: pm_open_pos = "ABOVE_VA"
    elif pm_open < val - MARGIN: pm_open_pos = "BELOW_VA"
    else:                        pm_open_pos = "INSIDE_VA"

    # Macro
    e200  = ema200_map.get(date_obj, poc)
    e50   = ema50_map.get(date_obj, poc)
    trend = ("BULL"  if poc > e200 and poc > e50
             else "BEAR" if poc < e200 and poc < e50
             else "MIXED")

    # ══════════════════════════════════════════════════════════════
    #  ESTRATEGIAS  (simulación barra a barra en 15 min)
    # ══════════════════════════════════════════════════════════════
    sl_pts = va_range * SL_MULT

    def add_trade(strat, entry, target, stop, direction, touch_bar_idx=0):
        exec_bars = pm_data.iloc[touch_bar_idx:]
        r, pnl = sim_trade(exec_bars, entry, target, stop, direction)
        if r == "NO_ENTRY": return
        all_trades.append({
            "date": str(date_obj), "weekday": DAYS_ES[wd], "wd_num": wd,
            "strategy": strat, "direction": direction,
            "result": r, "pnl_pts": pnl,
            "entry": round(entry, 1), "target": round(target, 1), "stop": round(stop, 1),
            "va_range": round(va_range, 1), "pm_range": round(pm_range, 1),
            "vah": round(vah, 1), "poc": round(poc, 1), "val": round(val, 1),
            "ny_open_pos": ny_open_pos, "pm_open_pos": pm_open_pos, "trend": trend,
        })

    # ── A) VAH Rejection → SHORT ─────────────────────────────────────
    # Setup: precio sube a VAH, no lo rompe, vende en el rechazo
    if touches_vah and not breaks_vah:
        idx_vah, _ = first_touch_bar(pm_data, vah, direction="up", margin=MARGIN)
        if idx_vah is not None:
            entry  = vah - MARGIN / 2
            stop   = vah + sl_pts
            target = entry - sl_pts * RR
            add_trade("VAH_REJ_SHORT", entry, target, stop, "SELL", idx_vah)

    # ── B) VAH Breakout Retest → LONG ────────────────────────────────
    # Setup: precio rompe VAH, retestea desde arriba, compra el retest
    if breaks_vah:
        idx_bo, _ = first_touch_bar(pm_data, vah, direction="up", margin=MARGIN)
        if idx_bo is not None:
            # Busca retest (precio baja de vuelta al VAH)
            post_bo = pm_data.iloc[idx_bo+1:]
            idx_rt, _ = first_touch_bar(post_bo, vah, direction="dn", margin=MARGIN)
            if idx_rt is not None:
                entry  = vah + MARGIN / 2
                stop   = vah - sl_pts
                target = entry + sl_pts * RR
                add_trade("VAH_BO_RETEST_LONG", entry, target, stop, "BUY",
                          idx_bo + 1 + idx_rt)
            else:
                # Sin retest → entrada directa tras BO
                entry  = vah + SWEEP_BUF
                stop   = vah - sl_pts
                target = entry + sl_pts * RR
                add_trade("VAH_BO_DIRECT_LONG", entry, target, stop, "BUY", idx_bo)

    # ── C) VAL Rejection → LONG ──────────────────────────────────────
    # Setup: precio baja a VAL, no lo rompe, compra el rebote
    if touches_val and not breaks_val:
        idx_val, _ = first_touch_bar(pm_data, val, direction="dn", margin=MARGIN)
        if idx_val is not None:
            entry  = val + MARGIN / 2
            stop   = val - sl_pts
            target = entry + sl_pts * RR
            add_trade("VAL_REJ_LONG", entry, target, stop, "BUY", idx_val)

    # ── D) VAL Breakdown Retest → SHORT ──────────────────────────────
    # Setup: precio rompe VAL, retestea desde abajo, vende el retest
    if breaks_val:
        idx_bd, _ = first_touch_bar(pm_data, val, direction="dn", margin=MARGIN)
        if idx_bd is not None:
            post_bd = pm_data.iloc[idx_bd+1:]
            idx_rt, _ = first_touch_bar(post_bd, val, direction="up", margin=MARGIN)
            if idx_rt is not None:
                entry  = val - MARGIN / 2
                stop   = val + sl_pts
                target = entry - sl_pts * RR
                add_trade("VAL_BD_RETEST_SHORT", entry, target, stop, "SELL",
                          idx_bd + 1 + idx_rt)
            else:
                entry  = val - SWEEP_BUF
                stop   = val + sl_pts
                target = entry - sl_pts * RR
                add_trade("VAL_BD_DIRECT_SHORT", entry, target, stop, "SELL", idx_bd)

    # ── E) POC como SOPORTE → LONG ───────────────────────────────────
    # Setup: precio en VA, cae al POC desde arriba, compra el rebote
    if touches_poc and pm_open_pos == "ABOVE_VA" or (touches_poc and pm_open > poc + MARGIN):
        idx_poc, _ = first_touch_bar(pm_data, poc, direction="dn", margin=MARGIN)
        if idx_poc is not None:
            entry  = poc + MARGIN / 2
            stop   = poc - sl_pts
            target = entry + sl_pts * RR
            add_trade("POC_SUPPORT_LONG", entry, target, stop, "BUY", idx_poc)

    # ── F) POC como RESISTENCIA → SHORT ──────────────────────────────
    # Setup: precio debajo del POC, sube al POC, vende el rechazo
    if touches_poc and (pm_open_pos == "BELOW_VA" or pm_open < poc - MARGIN):
        idx_poc, _ = first_touch_bar(pm_data, poc, direction="up", margin=MARGIN)
        if idx_poc is not None:
            entry  = poc - MARGIN / 2
            stop   = poc + sl_pts
            target = entry - sl_pts * RR
            add_trade("POC_RESIST_SHORT", entry, target, stop, "SELL", idx_poc)

    # ── Registro del día ────────────────────────────────────────────
    results.append({
        "date": str(date_obj), "weekday": DAYS_ES[wd], "wd_num": wd,
        # Profile
        "val": round(val,2), "poc": round(poc,2), "vah": round(vah,2),
        "va_range": round(va_range,1),
        "prof_hi": round(prof_hi,2), "prof_lo": round(prof_lo,2),
        "prof_range": round(prof_hi - prof_lo,1),
        "prof_bars": len(prof_data),
        # NY open
        "ny_open_price": round(ny_open_price,2), "ny_open_pos": ny_open_pos,
        # AM
        "am_hi": round(am_hi,2), "am_lo": round(am_lo,2),
        "am_range": round(am_hi - am_lo,1),
        # PM
        "pm_open": round(pm_open,2), "pm_close": round(pm_close,2),
        "pm_hi": round(pm_hi,2), "pm_lo": round(pm_lo,2),
        "pm_range": round(pm_range,1), "pm_dir": pm_dir,
        "pm_open_pos": pm_open_pos,
        # Interacciones
        "touches_vah": touches_vah, "breaks_vah": breaks_vah, "vah_bounce": vah_bounce,
        "touches_val": touches_val, "breaks_val": breaks_val, "val_bounce": val_bounce,
        "touches_poc": touches_poc,
        "close_above_va": close_above_va, "close_inside": close_inside,
        "close_below_va": close_below_va,
        # Macro
        "trend": trend, "ema200": round(e200,2),
    })
    analyzed += 1

print(f"  ✅ Días analizados: {analyzed} | Saltados: {skipped}")
print(f"  📈 Trades simulados: {len(all_trades)}")


# ══════════════════════════════════════════════════════════
#  REPORTE POR DÍA
# ══════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  📊 RESULTADOS POR DÍA — 15 MIN — PROFILE ASIA+LONDON")
print("═"*72)

day_summary = {}

for wd in range(5):
    recs = [r for r in results if r["wd_num"] == wd]
    n    = len(recs)
    if n == 0: continue

    dn = DAYS_ES[wd]
    print(f"\n  {'─'*70}")
    print(f"  🗓️  {dn}  [{n} días]")
    print(f"  {'─'*70}")

    # Rangos
    va_avg  = np.mean([r["va_range"]   for r in recs])
    pm_avg  = np.mean([r["pm_range"]   for r in recs])
    pr_avg  = np.mean([r["prof_range"] for r in recs])
    am_avg  = np.mean([r["am_range"]   for r in recs])
    print(f"  Rango Profile A+L : {pr_avg:6.0f} pts  (VA={va_avg:.0f} pts)")
    print(f"  Rango AM 9:30-11  : {am_avg:6.0f} pts")
    print(f"  Rango PM 11-Close : {pm_avg:6.0f} pts")

    # NY Open vs Profile
    pos_c = Counter(r["ny_open_pos"] for r in recs)
    print(f"\n  🎯 NY Open vs Profile:")
    for pos, cnt in pos_c.most_common():
        bar = "█" * int(cnt/n*100/5)
        print(f"     {pos:<14} {cnt:>2}/{n} = {cnt/n*100:5.1f}%  {bar}")

    # Interacciones con niveles
    tv  = sum(1 for r in recs if r["touches_vah"])
    bkv = sum(1 for r in recs if r["breaks_vah"])
    bnv = sum(1 for r in recs if r["vah_bounce"])
    tl  = sum(1 for r in recs if r["touches_val"])
    bkl = sum(1 for r in recs if r["breaks_val"])
    bnl = sum(1 for r in recs if r["val_bounce"])
    tp  = sum(1 for r in recs if r["touches_poc"])

    print(f"\n  📍 Interacción PM con niveles Profile (15 min exactos):")
    print(f"  {'NIVEL':<24} {'Toca':>5}{'%':>5}  {'Rompe':>6}{'%':>5}  {'Bounce':>7}{'%':>5}  {'Señal':>6}")
    print(f"  {'─'*65}")

    def row(name, toca, rompe, bounce, tot):
        pt = toca/tot*100   if tot   else 0
        pr = rompe/toca*100 if toca  else 0
        pb = bounce/toca*100 if toca else 0
        sig = "🔥 REVERTS" if pb >= 65 else ("💥 BREAKS" if pr >= 65 else "⚠️ Mixto")
        print(f"  {name:<24} {toca:>5}{pt:>4.0f}%  {rompe:>5}{pr:>4.0f}%  {bounce:>6}{pb:>4.0f}%  {sig}")

    row("VAH (Value Area High)", tv, bkv, bnv, n)
    row("VAL (Value Area Low)",  tl, bkl, bnl, n)
    print(f"  {'POC (Point Control)':<24} {tp:>5}{tp/n*100:>4.0f}%  {'—':>5}{'—':>4}  {'—':>6}{'—':>4}  —")

    # Dirección PM según posición NY Open
    print(f"\n  🧭 Dirección PM (11-Close) según posición en NY Open:")
    for pos in ["ABOVE_VA", "INSIDE_VA", "BELOW_VA"]:
        sub = [r for r in recs if r["ny_open_pos"] == pos]
        if not sub: continue
        sn = len(sub)
        sb = sum(1 for r in sub if r["pm_dir"] == "BULLISH")
        sr = sum(1 for r in sub if r["pm_dir"] == "BEARISH")
        sn2 = sn - sb - sr
        lbl = {"ABOVE_VA": "Precio > VAH", "INSIDE_VA": "Dentro VA ", "BELOW_VA": "Precio < VAL"}[pos]
        bias = "→ LONG BIAS 🟢"  if sb/sn >= .6 else ("→ SHORT BIAS 🔴" if sr/sn >= .6 else "→ SIN SESGO ⚪")
        print(f"  {lbl:<15} n={sn:>2}  BULL:{sb:>2}({sb/sn*100:.0f}%) "
              f"BEAR:{sr:>2}({sr/sn*100:.0f}%) FLAT:{sn2}  {bias}")

    # Cierre PM vs VA
    ca = sum(1 for r in recs if r["close_above_va"])
    ci = sum(1 for r in recs if r["close_inside"])
    cb = sum(1 for r in recs if r["close_below_va"])
    print(f"\n  🔚 Cierre PM vs Value Area:")
    print(f"     Encima  : {ca:>2}/{n} = {ca/n*100:.0f}%  {'▲'*int(ca/n*20)}")
    print(f"     Dentro  : {ci:>2}/{n} = {ci/n*100:.0f}%  {'─'*int(ci/n*20)}")
    print(f"     Debajo  : {cb:>2}/{n} = {cb/n*100:.0f}%  {'▼'*int(cb/n*20)}")

    day_summary[dn] = {
        "n": n,
        "va_avg": round(va_avg, 0), "pm_avg": round(pm_avg, 0),
        "tv": tv, "bkv": bkv, "bnv": bnv,
        "tl": tl, "bkl": bkl, "bnl": bnl,
        "tp": tp,
        "vah_bounce_pct": round(bnv/tv*100, 0) if tv else 0,
        "val_bounce_pct": round(bnl/tl*100, 0) if tl else 0,
        "vah_break_pct":  round(bkv/tv*100, 0) if tv else 0,
        "val_break_pct":  round(bkl/tl*100, 0) if tl else 0,
    }


# ══════════════════════════════════════════════════════════
#  BACKTEST — WIN RATE POR ESTRATEGIA
# ══════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  📈 BACKT. ESTRATEGIAS (15 min — barra a barra)")
print("═"*72)

STRAT_LABELS = {
    "VAH_REJ_SHORT":     "🔻 VAH Rejection  → SHORT",
    "VAH_BO_RETEST_LONG":"🔺 VAH BO + Retest → LONG",
    "VAH_BO_DIRECT_LONG":"🔺 VAH BO Directo  → LONG",
    "VAL_REJ_LONG":      "🔺 VAL Rejection  → LONG",
    "VAL_BD_RETEST_SHORT":"🔻 VAL BD + Retest → SHORT",
    "VAL_BD_DIRECT_SHORT":"🔻 VAL BD Directo  → SHORT",
    "POC_SUPPORT_LONG":  "🎯 POC Soporte    → LONG",
    "POC_RESIST_SHORT":  "🎯 POC Resistencia → SHORT",
}

df_t = pd.DataFrame(all_trades) if all_trades else pd.DataFrame()
best_overall = []

if not df_t.empty:
    for strat, label in STRAT_LABELS.items():
        sub    = df_t[df_t["strategy"] == strat]
        closed = sub[sub["result"].isin(["WIN", "LOSS"])]
        if closed.empty: continue

        n    = len(closed)
        wins = (closed["result"] == "WIN").sum()
        wr   = wins / n * 100
        avg_w = closed[closed["result"] == "WIN"]["pnl_pts"].mean()  if wins   else 0
        avg_l = closed[closed["result"] == "LOSS"]["pnl_pts"].mean() if n-wins else 0
        rr    = abs(avg_w / avg_l) if avg_l != 0 else 0
        tot_pnl   = closed["pnl_pts"].sum()
        dollar    = tot_pnl * 20

        flag = "🔥" if wr >= 65 else ("✅" if wr >= 55 else ("⚠️" if wr >= 45 else "❌"))
        print(f"\n  {flag} {label}")
        print(f"     Trades:{n:3d} | WR:{wr:5.1f}% | RR:1:{rr:.2f} | "
              f"PnL:{tot_pnl:+.0f}pts (~${dollar:+,.0f})")

        dia_rows = []
        for wn in ["LUNES","MARTES","MIÉRCOLES","JUEVES","VIERNES"]:
            s  = closed[closed["weekday"] == wn]
            if len(s) == 0: continue
            ww = (s["result"] == "WIN").sum()
            nn = len(s)
            fl = " 🔥" if ww/nn >= 0.70 else (" ✅" if ww/nn >= 0.60 else "")
            row_str = f"     {wn:<12} WR:{ww/nn*100:5.1f}% n={nn:2d} PnL:{s['pnl_pts'].sum():+.0f}pts{fl}"
            print(row_str)
            dia_rows.append({"day": wn, "wr": ww/nn*100, "n": nn, "pnl": s["pnl_pts"].sum()})

        best_overall.append({
            "strategy": strat, "label": label, "n": n,
            "wr": round(wr, 1), "rr": round(rr, 2),
            "total_pnl": tot_pnl, "dollar": dollar,
            "by_day": dia_rows
        })

    # Top estrategias
    best_wr  = sorted(best_overall, key=lambda x: x["wr"],  reverse=True)[:3]
    best_pnl = sorted(best_overall, key=lambda x: x["dollar"], reverse=True)[:3]

    print(f"\n  {'═'*60}")
    print(f"  🏆 TOP 3 POR WIN RATE:")
    for i, s in enumerate(best_wr, 1):
        print(f"  {i}. {s['label']:<35} WR={s['wr']}% | n={s['n']}")

    print(f"\n  💰 TOP 3 POR PnL TOTAL:")
    for i, s in enumerate(best_pnl, 1):
        print(f"  {i}. {s['label']:<35} ${s['dollar']:+,.0f} | WR={s['wr']}%")

else:
    print("  ⚠️  Sin trades para reportar")


# ══════════════════════════════════════════════════════════
#  TABLA RESUMEN EJECUTIVA
# ══════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  📊 RESUMEN EJECUTIVO — PROFILE ASIA+LONDON × DÍA")
print("═"*72)
print(f"  {'DÍA':<12} {'N':>3} {'VA':>6} {'PM':>6}  {'VAH Bounce%':>12}  {'VAH Break%':>11}  {'VAL Bounce%':>12}  {'VAL Break%':>11}")
print("  " + "─"*72)
for dn, s in day_summary.items():
    print(f"  {dn:<12} {s['n']:>3} {s['va_avg']:>5.0f}p {s['pm_avg']:>5.0f}p  "
          f"{s['vah_bounce_pct']:>11.0f}%  {s['vah_break_pct']:>10.0f}%  "
          f"{s['val_bounce_pct']:>11.0f}%  {s['val_break_pct']:>10.0f}%")


# ══════════════════════════════════════════════════════════
#  EXPORTAR
# ══════════════════════════════════════════════════════════
print("\n" + "═"*72)
print("  💾 EXPORTANDO...")
pd.DataFrame(results).to_csv(
    os.path.join(BASE_DIR, "ny_profile_15m_daily.csv"), index=False)
print(f"  ✅ ny_profile_15m_daily.csv ({len(results)} filas)")

if all_trades:
    pd.DataFrame(all_trades).to_csv(
        os.path.join(BASE_DIR, "ny_profile_15m_trades.csv"), index=False)
    print(f"  ✅ ny_profile_15m_trades.csv ({len(all_trades)} trades)")

with open(os.path.join(BASE_DIR, "ny_profile_15m_summary.json"), "w", encoding="utf-8") as f:
    json.dump({
        "title":  "NY PM — Profile Asia+London 15min VAH/POC/VAL",
        "period": f"{days_list[0].date()} → {days_list[-1].date()}",
        "bars":   "15m", "days": analyzed, "trades": len(all_trades),
        "por_dia": day_summary,
        "strategies": best_overall,
    }, f, indent=4, ensure_ascii=False, default=str)
print(f"  ✅ ny_profile_15m_summary.json")

print(f"\n{'═'*72}")
print(f"  🏆 COMPLETADO — {analyzed} días | {len(all_trades)} trades | 15 min")
print(f"{'═'*72}\n")
