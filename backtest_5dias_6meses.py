"""
╔══════════════════════════════════════════════════════════════════╗
║  BACKTEST  LUNES→VIERNES · NQ NASDAQ · ÚLTIMOS 6 MESES        ║
║  6 Patrones · Value Area Profile (VAH/POC/VAL)                 ║
║  → Profile: Asia 18:00 → 09:20 NY (10 min antes apertura)     ║
║  EMA 200 (15 min) al momento de apertura NY                    ║
║  Datos: 15min intraday NQ futures                              ║
╚══════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json, os
from datetime import timedelta
from collections import defaultdict

MARGIN   = 20     # pts para considerar que el precio "tocó" un nivel
MARGIN_E = 25     # margen para EMA 200 (más amplio)
NEWS_THR = 250    # puntos de rango para clasificar como NEWS_DRIVE
SWEEP_BUF = 20    # buffer para detección de sweep

DAYS_ES  = {0: "LUNES", 1: "MARTES", 2: "MIÉRCOLES", 3: "JUEVES", 4: "VIERNES"}
PATTERNS = ["SWEEP_H_RETURN", "SWEEP_L_RETURN",
            "EXPANSION_H",    "EXPANSION_L",
            "ROTATION_POC",   "NEWS_DRIVE"]


# ── Helpers ───────────────────────────────────────────────────────────
def calc_value_area(data: pd.DataFrame, bins: int = 120, va_pct: float = 0.70):
    """VAL, POC, VAH usando histograma de High+Low+Close."""
    all_p = pd.concat([data['High'], data['Low'], data['Close']])
    if len(all_p) < 6:
        mid = float(data['Close'].mean())
        return mid, mid, mid
    cnts, edges = np.histogram(all_p, bins=bins)
    centers     = (edges[:-1] + edges[1:]) / 2
    poc_idx     = int(np.argmax(cnts))
    total       = cnts.sum()
    target      = total * va_pct
    lo, hi      = poc_idx, poc_idx
    cur         = int(cnts[poc_idx])
    while cur < target:
        lv = cnts[lo - 1] if lo > 0 else -1
        hv = cnts[hi + 1] if hi < len(cnts) - 1 else -1
        if lv <= 0 and hv <= 0:
            break
        if lv >= hv:
            cur += int(lv); lo -= 1
        else:
            cur += int(hv); hi += 1
    return float(centers[lo]), float(centers[poc_idx]), float(centers[hi])


def touched(df_slice, level, margin):
    return bool(((df_slice['Low'] <= level + margin) &
                 (df_slice['High'] >= level - margin)).any())


def react(df_slice, level, margin):
    rows = df_slice[(df_slice['Low'] <= level + margin) &
                    (df_slice['High'] >= level - margin)]
    if rows.empty:
        return 0.0
    after = df_slice.loc[rows.index[0]:]
    return float(after['High'].max() - after['Low'].min()) if not after.empty else 0.0


# ── Main ─────────────────────────────────────────────────────────────
def run_full_backtest():
    csv = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv):
        print("❌ No se encontró:", csv); return

    df = pd.read_csv(csv, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    # EMA 200 en TODO el histórico (necesita historia previa)
    ema200 = df['Close'].ewm(span=200, adjust=False).mean()

    end_date   = df.index.max()
    start_date = end_date - timedelta(days=180)   # ← 6 MESES
    df_w       = df.loc[start_date:]
    days       = df_w.index.normalize().unique()

    print(f"\n{'═'*72}")
    print(f"  📅 Período: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  🗓️  Días de trading detectados: {len(days)}")
    print(f"{'═'*72}")

    # Estructura de colectores por día de la semana
    by_day = {d: [] for d in range(5)}
    all_recs = []

    for day in days:
        wd = day.weekday()
        if wd > 4:   # saltar fin de semana
            continue

        # ── Rango Asia+Londres ────────────────────────────────────
        r0 = (day - timedelta(days=1)).replace(hour=18, minute=0)
        r1 = day.replace(hour=8, minute=30)
        rd = df.loc[r0:r1]
        if rd.empty or len(rd) < 10:
            continue

        r_high  = float(rd['High'].max())
        r_low   = float(rd['Low'].min())

        # ── Value Area Profile (Asia 18:00 → 09:20 NY) ───────────
        p1  = day.replace(hour=9, minute=20)
        pd_ = df.loc[r0:p1]
        if pd_.empty or len(pd_) < 6:
            continue
        val, poc, vah = calc_value_area(pd_)

        # ── EMA 200 al open NY ────────────────────────────────────
        open_ts  = day.replace(hour=9, minute=30)
        ema_open = float(ema200.loc[:open_ts].iloc[-1])

        # ── Sesión NY ─────────────────────────────────────────────
        ny  = df.loc[open_ts : day.replace(hour=11, minute=30)]
        nf  = df.loc[open_ts : day.replace(hour=16, minute=0)]
        if ny.empty or len(ny) < 3:
            continue

        ny_o = float(ny.iloc[0]['Open'])
        ny_h = float(ny['High'].max())
        ny_l = float(ny['Low'].min())
        ny_r = ny_h - ny_l
        fc   = float(nf.iloc[-1]['Close']) if not nf.empty else float(ny.iloc[-1]['Close'])

        # ── Patrón de los 6 ──────────────────────────────────────
        ny_close_early = float(ny.iloc[-1]['Close'])
        if ny_r > NEWS_THR:
            pat = "NEWS_DRIVE"
        elif ny_h > r_high + SWEEP_BUF:
            pat = "SWEEP_H_RETURN" if ny_close_early < r_high else "EXPANSION_H"
        elif ny_l < r_low - SWEEP_BUF:
            pat = "SWEEP_L_RETURN" if ny_close_early > r_low  else "EXPANSION_L"
        else:
            pat = "ROTATION_POC"

        # ── Dirección ─────────────────────────────────────────────
        if   fc > ny_o + 30: direction = "BULLISH"
        elif fc < ny_o - 30: direction = "BEARISH"
        else:                 direction = "NEUTRAL"

        # ── Sweep time ────────────────────────────────────────────
        stime = None
        if pat == "SWEEP_H_RETURN":
            sc = ny[ny['High'] >= r_high + SWEEP_BUF]
            stime = sc.index[0].strftime('%H:%M') if not sc.empty else None
        elif pat == "SWEEP_L_RETURN":
            sc = ny[ny['Low'] <= r_low - SWEEP_BUF]
            stime = sc.index[0].strftime('%H:%M') if not sc.empty else None

        # ── Nivel hits ────────────────────────────────────────────
        t_vah = touched(ny, vah,      MARGIN)
        t_poc = touched(ny, poc,      MARGIN)
        t_val = touched(ny, val,      MARGIN)
        t_ema = touched(ny, ema_open, MARGIN_E)

        rec = {
            "date":       day.strftime('%Y-%m-%d'),
            "wd":         wd,
            "day_es":     DAYS_ES[wd],
            "pattern":    pat,
            "direction":  direction,
            "ny_range":   round(ny_r, 1),
            "ny_open":    round(ny_o, 2),
            "full_close": round(fc, 2),
            "r_high":     round(r_high, 2),
            "r_low":      round(r_low, 2),
            "val":        round(val, 2),
            "poc":        round(poc, 2),
            "vah":        round(vah, 2),
            "ema200":     round(ema_open, 2),
            "ema_above":  ny_o > ema_open,
            "sweep_time": stime,
            # hits + reactions
            "vah_hit":    t_vah,  "vah_react":  react(ny, vah, MARGIN)      if t_vah else 0.0,
            "poc_hit":    t_poc,  "poc_react":  react(ny, poc, MARGIN)      if t_poc else 0.0,
            "val_hit":    t_val,  "val_react":  react(ny, val, MARGIN)      if t_val else 0.0,
            "ema_hit":    t_ema,  "ema_react":  react(ny, ema_open, MARGIN_E) if t_ema else 0.0,
        }
        all_recs.append(rec)
        by_day[wd].append(rec)

    total_all = len(all_recs)

    # ═══════════════════════════════════════════════════════════════
    #  REPORTE POR DÍA
    # ═══════════════════════════════════════════════════════════════
    results_export = {}

    for wd in range(5):
        recs  = by_day[wd]
        n     = len(recs)
        d_es  = DAYS_ES[wd]

        if n == 0:
            print(f"\n❌ Sin datos para {d_es}")
            continue

        # Conteos de patrón
        p_cnt  = defaultdict(int)
        for r in recs:
            p_cnt[r['pattern']] += 1

        # Porcentajes
        p_pct = {k: round(v / n * 100, 1) for k, v in p_cnt.items()}
        dominant = max(p_cnt, key=p_cnt.get)

        # Dirección
        dir_cnt = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
        for r in recs:
            dir_cnt[r['direction']] += 1

        ranges = [r['ny_range'] for r in recs]

        # Level stats
        def ls(key_hit, key_react):
            hits   = [r for r in recs if r[key_hit]]
            h_n    = len(hits)
            h_pct  = round(h_n / n * 100, 1)
            h_avg  = round(sum(r[key_react] for r in hits) / h_n, 1) if h_n else 0
            return h_n, h_pct, h_avg

        vah_n, vah_p, vah_r = ls('vah_hit', 'vah_react')
        poc_n, poc_p, poc_r = ls('poc_hit', 'poc_react')
        val_n, val_p, val_r = ls('val_hit', 'val_react')
        ema_n, ema_p, ema_r = ls('ema_hit', 'ema_react')
        ema_ab  = sum(1 for r in recs if r['ema_above'])
        ema_abp = round(ema_ab / n * 100, 1)

        # Sweep hours
        sh = defaultdict(int)
        for r in recs:
            if r['sweep_time']:
                h = r['sweep_time'].split(':')[0]
                sh[f"{h}:xx"] += 1

        # ── PRINT ─────────────────────────────────────────────────
        print(f"\n{'═'*72}")
        print(f"  🗓️  {d_es}  ·  {n} sesiones  ·  6 meses")
        print(f"{'═'*72}")

        # Patrones
        print(f"\n  {'PATRÓN':<22} {'SESIONES':>9} {'%':>7}  BAR")
        print("  " + "─" * 55)
        for p in PATTERNS:
            cnt = p_cnt.get(p, 0)
            pct = p_pct.get(p, 0)
            bar = "█" * int(pct / 4)
            mk  = "  ← DOMINANTE" if p == dominant else ""
            print(f"  {p:<22} {cnt:>6}    {pct:>5.1f}%  {bar}{mk}")

        # Dirección
        print(f"\n  Dirección:")
        for d, c in dir_cnt.items():
            pct = round(c / n * 100, 1)
            print(f"    {d:<10} {c:>3} ({pct:>5.1f}%)  {'█'*int(pct/4)}")

        # Rango
        print(f"\n  Rango NY — Prom: {round(np.mean(ranges),1)} pts"
              f" | Máx: {round(max(ranges),1)} | Mín: {round(min(ranges),1)}")

        # Sweeps
        if sh:
            hrs = ", ".join(f"{h}:{c}" for h, c in sorted(sh.items()))
            print(f"  Sweeps por hora: {hrs}")

        # Value Area
        print(f"\n  {'─'*72}")
        print(f"  📐 VOLUME PROFILE VALUE AREA  (Asia 18:00 → 09:20 NY)")
        print(f"  {'─'*72}")
        print(f"  {'NIVEL':<16} {'TOCADO':>9} {'HIT%':>7} {'REACCIÓN PROM':>15}  BAR")
        print("  " + "─" * 58)
        for label, hn, hp, hr in [
            ("VAH (techo)",  vah_n, vah_p, vah_r),
            ("POC (centro)", poc_n, poc_p, poc_r),
            ("VAL (base)",   val_n, val_p, val_r),
        ]:
            bar = "█" * int(hp / 5)
            print(f"  {label:<16} {hn:>4}/{n:<4} {hp:>6.1f}%  {hr:>10.1f} pts  {bar}")

        # EMA 200
        print(f"\n  {'─'*72}")
        print(f"  📉 EMA 200 (15 min) al open NY 09:30")
        print(f"  {'─'*72}")
        bar_e = "█" * int(ema_p / 5)
        print(f"  Toca EMA200:        {ema_n:>3}/{n}  ({ema_p:>5.1f}%)  "
              f"reacción prom: {ema_r:>6.1f} pts  {bar_e}")
        print(f"  Abre SOBRE  EMA200: {ema_ab:>3}/{n}  ({ema_abp:>5.1f}%)  → alcista")
        print(f"  Abre DEBAJO EMA200: {n-ema_ab:>3}/{n}  ({100-ema_abp:>5.1f}%)  → bajista")

        # Detalle tabla
        print(f"\n  {'─'*72}")
        print(f"  {'FECHA':<12} {'PATRÓN':<22} {'DIR':<9} "
              f"{'VAL':>7} {'POC':>7} {'VAH':>7} {'EMA200':>7} {'RNG':>7}")
        print("  " + "─" * 72)
        for r in recs:
            print(f"  {r['date']:<12} {r['pattern']:<22} {r['direction']:<9} "
                  f"{r['val']:>7.0f} {r['poc']:>7.0f} {r['vah']:>7.0f} "
                  f"{r['ema200']:>7.0f} {r['ny_range']:>6.0f}p")

        # Conclusión
        best_level = max(
            [("VAH", vah_n, vah_r), ("POC", poc_n, poc_r),
             ("VAL", val_n, val_r), ("EMA200", ema_n, ema_r)],
            key=lambda x: (x[1], x[2])
        )
        print(f"\n  💡 NIVEL MÁS RESPETADO: {best_level[0]}")
        print(f"     {best_level[1]}/{n} sesiones ({round(best_level[1]/n*100,1)}%) "
              f"| reacción prom: {round(best_level[2]/best_level[1],1) if best_level[1] else 0} pts")
        print(f"  🏆 PATRÓN DOMINANTE: {dominant} ({p_pct.get(dominant,0)}%)")

        # Guardar para export
        results_export[d_es] = {
            "sessions": n,
            "dominant_pattern": dominant,
            "dominant_pct": f"{p_pct.get(dominant,0)}%",
            "patterns": {k: f"{p_pct.get(k,0)}%" for k in PATTERNS},
            "direction": dir_cnt,
            "avg_range": round(np.mean(ranges), 1),
            "value_area": {
                "vah": {"hit_rate": f"{vah_p}%", "avg_reaction": vah_r},
                "poc": {"hit_rate": f"{poc_p}%", "avg_reaction": poc_r},
                "val": {"hit_rate": f"{val_p}%", "avg_reaction": val_r},
            },
            "ema200": {
                "hit_rate":       f"{ema_p}%",
                "avg_reaction":   ema_r,
                "pct_above_ema":  f"{ema_abp}%",
                "pct_below_ema":  f"{100-ema_abp}%",
            },
            "best_level": best_level[0],
            "sessions_detail": recs,
        }

    # ═══════════════════════════════════════════════════════════════
    #  TABLA COMPARATIVA FINAL
    # ═══════════════════════════════════════════════════════════════
    print(f"\n\n{'═'*72}")
    print("  📊 RESUMEN COMPARATIVO · 5 DÍAS · 6 MESES")
    print(f"{'═'*72}")
    print(f"  {'DÍA':<12} {'N':>4} {'DOMINANTE':<22} {'%':>6} "
          f"{'RANGO':>7} {'VAL%':>7} {'EMA%':>7} {'DIR':>9}")
    print("  " + "─" * 72)
    for wd in range(5):
        d_es = DAYS_ES[wd]
        if d_es not in results_export:
            continue
        e   = results_export[d_es]
        # Best dir
        dirb = max(e['direction'], key=e['direction'].get)
        dirp = round(e['direction'][dirb] / e['sessions'] * 100, 1)
        val_h = e['value_area']['val']['hit_rate']
        ema_h = e['ema200']['hit_rate']
        print(f"  {d_es:<12} {e['sessions']:>4} {e['dominant_pattern']:<22} "
              f"{e['dominant_pct']:>6} {e['avg_range']:>6.0f}p "
              f"{val_h:>7} {ema_h:>7}  {dirb[:4]:>4}({dirp:.0f}%)")

    # ── Guardar JSON ──────────────────────────────────────────────
    out = {
        "title":  "Backtest 5 Días NQ · 6 Meses + Profile VA + EMA200",
        "period": f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        "total_sessions": total_all,
        "by_day": results_export,
    }
    path = "data/research/backtest_5dias_6meses.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False, default=str)

    print(f"\n  ✅  Guardado → {path}")
    print(f"{'═'*72}\n")


if __name__ == "__main__":
    run_full_backtest()
