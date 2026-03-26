"""
╔══════════════════════════════════════════════════════════════════════════╗
║  BACKTEST CON FILTROS DE INVESTIGACIÓN — NQ NASDAQ                      ║
║  Basado en análisis estadístico de 126 días                             ║
║                                                                          ║
║  HALLAZGOS INTEGRADOS:                                                   ║
║  Q1: VA range < 100 pts  → señal limpia (break VAL solo 38%)           ║
║      VA range > 150 pts  → ruidoso (break ambos lados 67%/59%)         ║
║  Q2: NY abre ABOVE_VA    → trampa: 100% de casos cierra abajo          ║
║      NY abre BELOW_VA    → rebote probable hacia VA                     ║
║  Q3: VA estrecho + NY abre INSIDE → buscar breakout limpio             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import yfinance as yf
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── PARÁMETROS DE LA INVESTIGACIÓN ──────────────────────────────────────────
VA_ESTRECHO   = 100   # pts  → VA < 100: señal limpia (38% break VAL)
VA_AMPLIO     = 150   # pts  → VA > 150: mercado ruidoso (skip o reducir size)
VA_PCT        = 0.70  # Value Area = 70% del volumen total
N_BINS        = 30    # bins para el perfil de volumen

print("=" * 70)
print("  BACKTEST CON FILTROS DE INVESTIGACIÓN — 126 DÍAS VALIDADOS")
print("=" * 70)
print(f"\n  Filtros activos:")
print(f"    VA < {VA_ESTRECHO} pts → TIER 1 (máxima confianza, break VAL solo 38%)")
print(f"    VA {VA_ESTRECHO}–{VA_AMPLIO} pts → TIER 2 (normal)")
print(f"    VA > {VA_AMPLIO} pts → TIER 3 (ruidoso, solo con confirmación)")
print(f"    Apertura ABOVE_VA → FADE (trampa, 100% cierra abajo en research)")
print(f"    Apertura BELOW_VA → REBOTE desde VAL")

# ── DATOS ────────────────────────────────────────────────────────────────────
print("\n📡 Descargando NQ=F horario (2 años)...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index   = raw.index.tz_convert('America/New_York')
raw['hour'] = raw.index.hour
raw['date'] = raw.index.date
raw['wd']   = raw.index.dayofweek
raw['vol']  = raw['Volume'].fillna(1).replace(0, 1)
print(f"  ✅ {len(raw)} velas cargadas")

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

# ── VOLUME PROFILE ────────────────────────────────────────────────────────────
def calc_profile(df, n_bins=N_BINS, va_pct=VA_PCT):
    """Retorna (poc, vah, val, va_range)"""
    if len(df) < 2:
        return None, None, None, None
    lo = float(df['Low'].min())
    hi = float(df['High'].max())
    if hi <= lo:
        mid = (hi + lo) / 2
        return mid, hi, lo, hi - lo

    bins   = np.linspace(lo, hi, n_bins + 1)
    vol_by = np.zeros(n_bins)

    for _, row in df.iterrows():
        r_lo  = float(row['Low'])
        r_hi  = float(row['High'])
        r_vol = float(row['vol'])
        r_rng = r_hi - r_lo if r_hi > r_lo else 1e-9
        for b in range(n_bins):
            overlap = min(r_hi, bins[b+1]) - max(r_lo, bins[b])
            if overlap > 0:
                vol_by[b] += r_vol * (overlap / r_rng)

    total = vol_by.sum()
    if total == 0:
        return (hi+lo)/2, hi, lo, hi - lo

    poc_idx = int(np.argmax(vol_by))
    poc     = (bins[poc_idx] + bins[poc_idx + 1]) / 2

    target  = total * va_pct
    accum   = vol_by[poc_idx]
    hi_i, lo_i = poc_idx, poc_idx

    while accum < target:
        can_up   = hi_i + 1 < n_bins
        can_down = lo_i - 1 >= 0
        if not can_up and not can_down:
            break
        v_up   = vol_by[hi_i + 1] if can_up   else -1
        v_down = vol_by[lo_i - 1] if can_down else -1
        if v_up >= v_down:
            hi_i += 1; accum += v_up
        else:
            lo_i -= 1; accum += v_down

    vah      = bins[hi_i + 1]
    val      = bins[lo_i]
    va_range = vah - val
    return poc, vah, val, va_range


# ── CLASIFICAR TIER (hallazgo Q1) ────────────────────────────────────────────
def classify_tier(va_range):
    if va_range < VA_ESTRECHO:
        return "TIER1_CLEAN"    # WR históricamente más limpio
    elif va_range <= VA_AMPLIO:
        return "TIER2_NORMAL"
    else:
        return "TIER3_NOISY"    # Evitar o reducir size


# ── CLASIFICAR APERTURA NY (hallazgo Q2) ─────────────────────────────────────
def classify_ny_open(ny_open, vah, val):
    if ny_open > vah:
        return "ABOVE_VA"   # Research: 100% cierra abajo → FADE
    elif ny_open < val:
        return "BELOW_VA"   # Research: rebote hacia VAL probable
    else:
        return "INSIDE_VA"  # 94.4% de los días


# ── SIMULADOR ────────────────────────────────────────────────────────────────
def sim_trade(entry, target, stop, bars, direction):
    entered = False
    for _, bar in bars.iterrows():
        lo_b = float(bar['Low'])
        hi_b = float(bar['High'])
        if direction == "BUY":
            if not entered and hi_b >= entry: entered = True
            if entered:
                if lo_b <= stop:   return "LOSS", stop
                if hi_b >= target: return "WIN",  target
        else:
            if not entered and lo_b <= entry: entered = True
            if entered:
                if hi_b >= stop:   return "LOSS", stop
                if lo_b <= target: return "WIN",  target
    if not entered:
        return "NO_ENTRY", 0
    return "FLAT", float(bars.iloc[-1]['Close'])


# ── BACKTEST PRINCIPAL ────────────────────────────────────────────────────────
print("\n🔍 Ejecutando backtest con filtros de investigación...")

trades = []
skipped_noisy = 0
no_setup = 0

for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['wd'].iloc[0]) if not day.empty else -1
    if wd not in DAYS:
        continue

    # Perfil overnight: 0:00 → 8:00 (Asia + London combinado)
    pre_ny = day[day['hour'].between(0, 8)]
    ny     = day[day['hour'].between(9, 11)]

    if pre_ny.empty or ny.empty or len(pre_ny) < 3:
        continue

    poc, vah, val, va_range = calc_profile(pre_ny)
    if poc is None or va_range < 5:
        no_setup += 1
        continue

    # ── Clasificación por investigación ──────────────────────────────────
    tier      = classify_tier(va_range)
    ny_open   = float(ny.iloc[0]['Open'])
    open_pos  = classify_ny_open(ny_open, vah, val)

    ny_bars = ny.reset_index(drop=True)

    # ── SETUP 1: INSIDE_VA → buscar breakout (todos los tiers) ──────────
    if open_pos == "INSIDE_VA":
        # BUY setup: entrada en VAH, target = VAH + (va_range * 0.5), stop = VAL
        rr_mult = 0.5 if tier == "TIER3_NOISY" else 1.0  # reducir target en rango amplio
        buy_entry  = vah
        buy_target = vah + va_range * rr_mult
        buy_stop   = val - va_range * 0.15
        res_b, ex_b = sim_trade(buy_entry, buy_target, buy_stop, ny_bars, "BUY")

        # SELL setup: entrada en VAL, target simétrico
        sell_entry  = val
        sell_target = val - va_range * rr_mult
        sell_stop   = vah + va_range * 0.15
        res_s, ex_s = sim_trade(sell_entry, sell_target, sell_stop, ny_bars, "SELL")

        for direction, entry, res, ex in [
            ("BUY",  buy_entry,  res_b, ex_b),
            ("SELL", sell_entry, res_s, ex_s),
        ]:
            if res == "NO_ENTRY":
                continue
            pnl = (ex - entry) if direction == "BUY" else (entry - ex)
            trades.append({
                "date":      str(d),
                "weekday":   DAYS[wd],
                "setup":     f"BREAKOUT_{direction}",
                "tier":      tier,
                "open_pos":  open_pos,
                "result":    res,
                "pnl_pts":   round(pnl, 1),
                "entry":     round(entry, 1),
                "exit":      round(ex, 1),
                "va_range":  round(va_range, 1),
                "poc":       round(poc, 1),
                "vah":       round(vah, 1),
                "val":       round(val, 1),
            })

    # ── SETUP 2: ABOVE_VA → FADE (hallazgo Q2: 100% cierra abajo) ───────
    elif open_pos == "ABOVE_VA":
        # Venta desde apertura hacia VAH (zona de interés de reingreso)
        entry  = ny_open
        target = vah                    # volver al VAH = primer objetivo
        stop   = ny_open + va_range * 0.20
        res, ex = sim_trade(entry, target, stop, ny_bars, "SELL")

        if res != "NO_ENTRY":
            pnl = entry - ex
            trades.append({
                "date":      str(d),
                "weekday":   DAYS[wd],
                "setup":     "FADE_GAP_UP",
                "tier":      tier,
                "open_pos":  open_pos,
                "result":    res,
                "pnl_pts":   round(pnl, 1),
                "entry":     round(entry, 1),
                "exit":      round(ex, 1),
                "va_range":  round(va_range, 1),
                "poc":       round(poc, 1),
                "vah":       round(vah, 1),
                "val":       round(val, 1),
            })

    # ── SETUP 3: BELOW_VA → rebote desde VAL ────────────────────────────
    elif open_pos == "BELOW_VA":
        entry  = val                    # compra al tocar VAL desde abajo
        target = poc                    # target = POC (conservador)
        stop   = val - va_range * 0.20
        res, ex = sim_trade(entry, target, stop, ny_bars, "BUY")

        if res != "NO_ENTRY":
            pnl = ex - entry
            trades.append({
                "date":      str(d),
                "weekday":   DAYS[wd],
                "setup":     "BOUNCE_FROM_VAL",
                "tier":      tier,
                "open_pos":  open_pos,
                "result":    res,
                "pnl_pts":   round(pnl, 1),
                "entry":     round(entry, 1),
                "exit":      round(ex, 1),
                "va_range":  round(va_range, 1),
                "poc":       round(poc, 1),
                "vah":       round(vah, 1),
                "val":       round(val, 1),
            })


# ── RESULTADOS ────────────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  📊 RESULTADOS — BACKTEST CON FILTROS DE INVESTIGACIÓN")
print(f"{'='*70}\n")

t = pd.DataFrame(trades)
if t.empty:
    print("  ❌ Sin trades — revisa los datos.")
    exit()

def print_stats(sub, label):
    c = sub[sub['result'].isin(['WIN', 'LOSS'])]
    if c.empty:
        return
    total = len(c)
    wins  = len(c[c['result'] == 'WIN'])
    wr    = wins / total * 100
    avg_w = c[c['result'] == 'WIN']['pnl_pts'].mean() if wins > 0 else 0
    avg_l = c[c['result'] == 'LOSS']['pnl_pts'].mean() if (total-wins) > 0 else -1
    rr    = abs(avg_w / avg_l) if avg_l != 0 else 0
    pnl   = c['pnl_pts'].sum()
    flag  = " ✅" if wr >= 60 else (" ⚠️" if wr < 40 else "")
    print(f"  {label}")
    print(f"    Trades: {total:>4}  |  WR: {wr:>5.1f}%{flag}  |  RR: 1:{rr:.2f}")
    print(f"    Avg WIN: +{avg_w:>5.1f}pts  |  Avg LOSS: {avg_l:>6.1f}pts")
    print(f"    PnL 2 años: {pnl:+.0f} pts  (~${pnl*20:+,.0f}/contrato)\n")

# Por setup
print("── Por SETUP ─────────────────────────────────────────────────────────")
for setup in t['setup'].unique():
    print_stats(t[t['setup'] == setup], f"🎯 {setup}")

# Por tier (hallazgo Q1)
print("── Por TIER de VA range (Hallazgo Q1) ───────────────────────────────")
for tier in ["TIER1_CLEAN", "TIER2_NORMAL", "TIER3_NOISY"]:
    sub = t[t['tier'] == tier]
    labels = {
        "TIER1_CLEAN":  f"TIER 1 — VA < {VA_ESTRECHO} pts (señal limpia)",
        "TIER2_NORMAL": f"TIER 2 — VA {VA_ESTRECHO}–{VA_AMPLIO} pts (normal)",
        "TIER3_NOISY":  f"TIER 3 — VA > {VA_AMPLIO} pts (ruidoso)",
    }
    if not sub.empty:
        print_stats(sub, labels[tier])

# Por día
print("── Por DÍA ───────────────────────────────────────────────────────────")
print(f"  {'Día':<12} {'WR':>7} {'n':>4} {'PnL':>9}  Tier1_WR")
print("  " + "─" * 52)
for day in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]:
    sub  = t[(t['weekday'] == day) & (t['result'].isin(['WIN','LOSS']))]
    sub1 = t[(t['weekday'] == day) & (t['tier'] == 'TIER1_CLEAN') & (t['result'].isin(['WIN','LOSS']))]
    if sub.empty:
        continue
    w    = len(sub[sub['result'] == 'WIN'])
    n    = len(sub)
    wr   = w / n * 100
    pnl  = sub['pnl_pts'].sum()
    wr1  = f"{len(sub1[sub1['result']=='WIN'])/len(sub1)*100:.1f}%" if not sub1.empty else "—"
    flag = " ✅" if wr >= 60 else (" ⚠️" if wr < 40 else "")
    print(f"  {day:<12} {wr:>6.1f}%{flag} {n:>4} {pnl:>+8.0f}pts  T1:{wr1}")

# Guardar
out_csv  = os.path.join(BASE_DIR, "backtest_research_trades.csv")
out_json = os.path.join(BASE_DIR, "data", "research", "backtest_research_summary.json")
os.makedirs(os.path.dirname(out_json), exist_ok=True)
t.to_csv(out_csv, index=False)

summary = {
    "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "research_filters": {
        "va_estrecho_threshold": VA_ESTRECHO,
        "va_amplio_threshold":   VA_AMPLIO,
        "q1_finding": "VA<100 → break VAL solo 38% (señal limpia); VA>150 → break ambos lados 67%",
        "q2_finding": "ABOVE_VA open → 100% cierra abajo (fade setup)",
        "q3_finding": "pm_direction: 50.8% BULL / 38.9% BEAR en dataset 126 días",
    },
    "total_trades": len(t),
    "by_setup":    {setup: {} for setup in t['setup'].unique()},
}

with open(out_json, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=4, ensure_ascii=False)

print(f"\n  ✅ Trades guardados → backtest_research_trades.csv")
print(f"  ✅ Resumen JSON    → data/research/backtest_research_summary.json")
print(f"  📅 Días sin perfil: {no_setup}")
print("=" * 70)
