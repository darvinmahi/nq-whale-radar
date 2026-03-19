"""
╔══════════════════════════════════════════════════════════════════════╗
║  BACKTEST  LUNES→VIERNES · NQ · 6 MESES · POR SESIÓN              ║
║                                                                      ║
║  SESIONES (hora NY / ET):                                           ║
║  ·  ASIA     → prev 18:00  →  02:59                                ║
║  ·  LONDON   →  03:00  →  08:29                                    ║
║  ·  NY AM    →  09:30  →  12:00                                    ║
║  ·  NY PM    →  12:01  →  16:00                                    ║
║                                                                      ║
║  PROFILE REFERENCIA: Asia 18:00 → 09:20 NY                        ║
║  EMA 200 (15 min) al open de cada sesión                           ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import json, os
from datetime import timedelta
from collections import defaultdict

# ── Constantes ────────────────────────────────────────────────────────
NEWS_THR  = 200
SWEEP_BUF = 20
MARGIN    = 20
MARGIN_E  = 25
DAYS_ES   = {0: "LUNES", 1: "MARTES", 2: "MIÉRCOLES", 3: "JUEVES", 4: "VIERNES"}
PATTERNS  = ["SWEEP_H_RETURN", "SWEEP_L_RETURN",
             "EXPANSION_H",    "EXPANSION_L",
             "ROTATION_POC",   "NEWS_DRIVE"]

SESSIONS = {
    "LONDON":  ("03:00", "08:29"),
    "NY_AM":   ("09:30", "12:00"),
    "NY_PM":   ("12:01", "16:00"),
}
SESSION_LABELS = {
    "LONDON": "🇬🇧 LONDON   (03:00-08:29 ET)",
    "NY_AM":  "🗽 NY MORNING (09:30-12:00 ET)",
    "NY_PM":  "🇺🇸 NY AFTERNOON (12:01-16:00 ET)",
}


# ── Helpers ───────────────────────────────────────────────────────────
def calc_value_area(data: pd.DataFrame, bins: int = 120, va_pct: float = 0.70):
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
        lv = cnts[lo - 1] if lo > 0         else -1
        hv = cnts[hi + 1] if hi < len(cnts)-1 else -1
        if lv <= 0 and hv <= 0:
            break
        if lv >= hv:
            cur += int(lv); lo -= 1
        else:
            cur += int(hv); hi += 1
    return float(centers[lo]), float(centers[poc_idx]), float(centers[hi])


def touched(sl, level, margin):
    return bool(((sl['Low'] <= level + margin) & (sl['High'] >= level - margin)).any())


def react_after(sl, level, margin):
    rows = sl[(sl['Low'] <= level + margin) & (sl['High'] >= level - margin)]
    if rows.empty:
        return 0.0
    after = sl.loc[rows.index[0]:]
    return float(after['High'].max() - after['Low'].min()) if not after.empty else 0.0


def classify_pattern(sl, r_high, r_low, buf=SWEEP_BUF, news_thr=NEWS_THR):
    if sl.empty:
        return "ROTATION_POC", "NEUTRAL", 0.0
    h = float(sl['High'].max())
    l = float(sl['Low'].min())
    rng = h - l
    o = float(sl.iloc[0]['Open'])
    c = float(sl.iloc[-1]['Close'])
    if rng > news_thr:
        pat = "NEWS_DRIVE"
    elif h > r_high + buf:
        pat = "SWEEP_H_RETURN" if c < r_high else "EXPANSION_H"
    elif l < r_low - buf:
        pat = "SWEEP_L_RETURN" if c > r_low  else "EXPANSION_L"
    else:
        pat = "ROTATION_POC"
    if   c > o + 20: direction = "BULLISH"
    elif c < o - 20: direction = "BEARISH"
    else:             direction = "NEUTRAL"
    return pat, direction, rng


def sweep_hour(sl, r_high, r_low, buf=SWEEP_BUF):
    up = sl[sl['High'] >= r_high + buf]
    dn = sl[sl['Low']  <= r_low  - buf]
    if not up.empty:
        return up.index[0].strftime('%H:%M')
    if not dn.empty:
        return dn.index[0].strftime('%H:%M')
    return None


# ── Sección de reporte por sesión ─────────────────────────────────────
def print_session_report(sess_name, recs, val_all, poc_all, vah_all, ema_at_open_all):
    n = len(recs)
    if n == 0:
        print(f"  (sin datos suficientes)")
        return {}

    # Patrones
    p_cnt = defaultdict(int)
    for r in recs:
        p_cnt[r['pattern']] += 1
    p_pct    = {k: round(v / n * 100, 1) for k, v in p_cnt.items()}
    dominant = max(p_cnt, key=p_cnt.get) if p_cnt else "—"

    # Dirección
    dir_cnt = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0}
    for r in recs:
        dir_cnt[r['direction']] += 1

    ranges = [r['range'] for r in recs]

    # Nivel hits
    def ls(key_h, key_r):
        hits = [r for r in recs if r.get(key_h)]
        hn   = len(hits)
        hp   = round(hn / n * 100, 1)
        hr   = round(sum(r.get(key_r, 0) for r in hits) / hn, 1) if hn else 0.0
        return hn, hp, hr

    vah_n, vah_p, vah_r = ls('vah_hit', 'vah_react')
    poc_n, poc_p, poc_r = ls('poc_hit', 'poc_react')
    val_n, val_p, val_r = ls('val_hit', 'val_react')
    ema_n, ema_p, ema_r = ls('ema_hit', 'ema_react')
    ema_ab  = sum(1 for r in recs if r.get('ema_above'))
    ema_abp = round(ema_ab / n * 100, 1)

    sweep_times = [r.get('sweep_time') for r in recs if r.get('sweep_time')]
    sh = defaultdict(int)
    for t in sweep_times:
        sh[t.split(':')[0] + ":xx"] += 1

    # ── Imprimir ──────────────────────────────────────────────────
    label = SESSION_LABELS.get(sess_name, sess_name)
    print(f"\n  {'─'*68}")
    print(f"  {label}   [{n} sesiones]")
    print(f"  {'─'*68}")

    print(f"  {'PATRÓN':<22} {'N':>5} {'%':>7}  BAR")
    for p in PATTERNS:
        cnt = p_cnt.get(p, 0)
        pct = p_pct.get(p, 0)
        bar = "█" * int(pct / 5)
        mk  = " ← DOM" if p == dominant else ""
        print(f"  {p:<22} {cnt:>5} {pct:>6.1f}%  {bar}{mk}")

    dirb = max(dir_cnt, key=dir_cnt.get)
    dirp = round(dir_cnt[dirb] / n * 100, 1)
    print(f"\n  Dirección dominante: {dirb} ({dirp:.0f}%)  "
          f"| Rango prom: {round(np.mean(ranges),1)} pts"
          f" | Máx: {round(max(ranges),1)} | Mín: {round(min(ranges),1)}")

    if sh:
        print(f"  Sweeps: " + "  ".join(f"{h}×{c}" for h, c in sorted(sh.items())))

    print(f"\n  Volume Profile (VAH/POC/VAL referencia Asia→09:20 NY):")
    print(f"  {'NIVEL':<14} {'TOCADO':>8} {'HIT%':>6} {'REACT PROM':>12}")
    for label2, hn, hp, hr in [("VAH", vah_n, vah_p, vah_r),
                                ("POC", poc_n, poc_p, poc_r),
                                ("VAL", val_n, val_p, val_r)]:
        bar = "█" * int(hp / 5)
        print(f"  {label2:<14} {hn:>4}/{n:<3} {hp:>5.1f}%  {hr:>8.1f} pts  {bar}")

    print(f"\n  EMA 200 al open de sesión:")
    bar_e = "█" * int(ema_p / 5)
    print(f"  Toca EMA200:    {ema_n:>3}/{n}  ({ema_p:>5.1f}%)  "
          f"reacción: {ema_r:>6.1f} pts  {bar_e}")
    print(f"  Sobre EMA200:   {ema_ab:>3}/{n}  ({ema_abp:>5.1f}%)  "
          f"Debajo: {n-ema_ab}/{n}  ({100-ema_abp:.1f}%)")

    best = max(
        [("VAH", vah_n, vah_r), ("POC", poc_n, poc_r),
         ("VAL", val_n, val_r), ("EMA200", ema_n, ema_r)],
        key=lambda x: (x[1], x[2])
    )
    best_avg = round(best[2] / best[1], 1) if best[1] else 0
    print(f"\n  ★ NIVEL MÁS RESPETADO: {best[0]} "
          f"({best[1]}/{n} → {round(best[1]/n*100,1)}%) | react: {best_avg} pts")

    return {
        "sessions": n,
        "dominant_pattern": dominant,
        "dominant_pct": f"{p_pct.get(dominant, 0)}%",
        "patterns": {k: f"{p_pct.get(k, 0)}%" for k in PATTERNS},
        "direction": dir_cnt,
        "dir_dominant": dirb,
        "avg_range": round(np.mean(ranges), 1),
        "best_level": best[0],
        "value_area": {
            "vah": {"hit_rate": f"{vah_p}%", "avg_react": vah_r},
            "poc": {"hit_rate": f"{poc_p}%", "avg_react": poc_r},
            "val": {"hit_rate": f"{val_p}%", "avg_react": val_r},
        },
        "ema200": {"hit_rate": f"{ema_p}%", "avg_react": ema_r,
                   "pct_above": f"{ema_abp}%"},
    }


# ── Main ─────────────────────────────────────────────────────────────
def run():
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

    ema200    = df['Close'].ewm(span=200, adjust=False).mean()
    end_date  = df.index.max()
    start_date = end_date - timedelta(days=180)
    df_w      = df.loc[start_date:]
    days      = df_w.index.normalize().unique()

    print(f"\n{'═'*70}")
    print(f"  📅 BACKTEST 5 DÍAS × 6 MESES · POR SESIÓN · NQ NASDAQ")
    print(f"  Período: {start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}")
    print(f"  Días: {len(days)}  |  Sesiones: London · NY AM · NY PM")
    print(f"{'═'*70}")

    # Estructura de datos por día y sesión
    # by_day[wd][sess_name] = list of records
    by_day = {d: {s: [] for s in SESSIONS} for d in range(5)}

    for day in days:
        wd = day.weekday()
        if wd > 4:
            continue

        # ── Profile (Asia 18:00 prev → 09:20 NY) ─────────────────
        p_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        p_end   = day.replace(hour=9, minute=20)
        pdata   = df.loc[p_start:p_end]
        if pdata.empty or len(pdata) < 6:
            continue
        val, poc, vah = calc_value_area(pdata)

        # ── Rango Asia + London (referencia para patrón) ──────────
        r_start = (day - timedelta(days=1)).replace(hour=18, minute=0)
        r_end   = day.replace(hour=8, minute=30)
        rdata   = df.loc[r_start:r_end]
        if rdata.empty or len(rdata) < 8:
            continue
        r_high = float(rdata['High'].max())
        r_low  = float(rdata['Low'].min())

        # ── Analizar cada sesión ──────────────────────────────────
        for sess_name, (t0_str, t1_str) in SESSIONS.items():
            h0, m0 = map(int, t0_str.split(':'))
            h1, m1 = map(int, t1_str.split(':'))
            ts0 = day.replace(hour=h0, minute=m0)
            ts1 = day.replace(hour=h1, minute=m1)
            sl  = df.loc[ts0:ts1]

            if sl.empty or len(sl) < 2:
                continue

            # EMA al open DE ESTA sesión
            ema_open = float(ema200.loc[:ts0].iloc[-1])

            pat, direction, rng = classify_pattern(sl, r_high, r_low)
            sw_time = sweep_hour(sl, r_high, r_low)

            # Nivel hits vs profile
            t_vah = touched(sl, vah,      MARGIN)
            t_poc = touched(sl, poc,      MARGIN)
            t_val = touched(sl, val,      MARGIN)
            t_ema = touched(sl, ema_open, MARGIN_E)

            rec = {
                "date":        day.strftime('%Y-%m-%d'),
                "wd":          wd,
                "session":     sess_name,
                "pattern":     pat,
                "direction":   direction,
                "range":       round(rng, 1),
                "open":        round(float(sl.iloc[0]['Open']), 2),
                "close":       round(float(sl.iloc[-1]['Close']), 2),
                "high":        round(float(sl['High'].max()), 2),
                "low":         round(float(sl['Low'].min()), 2),
                "val":         round(val, 2),
                "poc":         round(poc, 2),
                "vah":         round(vah, 2),
                "ema200":      round(ema_open, 2),
                "ema_above":   float(sl.iloc[0]['Open']) > ema_open,
                "sweep_time":  sw_time,
                "vah_hit":     t_vah, "vah_react": react_after(sl, vah, MARGIN)     if t_vah else 0.0,
                "poc_hit":     t_poc, "poc_react": react_after(sl, poc, MARGIN)     if t_poc else 0.0,
                "val_hit":     t_val, "val_react": react_after(sl, val, MARGIN)     if t_val else 0.0,
                "ema_hit":     t_ema, "ema_react": react_after(sl, ema_open, MARGIN_E) if t_ema else 0.0,
            }
            by_day[wd][sess_name].append(rec)

    # ═══════════════════════════════════════════════════════════════
    #  REPORTE POR DÍA DE SEMANA
    # ═══════════════════════════════════════════════════════════════
    export_all = {}
    summary_rows = []   # para tabla final

    for wd in range(5):
        d_es = DAYS_ES[wd]
        total_sess = sum(len(by_day[wd][s]) for s in SESSIONS)
        if total_sess == 0:
            continue

        print(f"\n\n{'═'*70}")
        print(f"  🗓️  {d_es}  ·  6 meses")
        print(f"{'═'*70}")

        export_day = {}
        for sess_name in SESSIONS:
            recs = by_day[wd][sess_name]
            result = print_session_report(
                sess_name, recs,
                [r['val'] for r in recs],
                [r['poc'] for r in recs],
                [r['vah'] for r in recs],
                [r['ema200'] for r in recs],
            )
            export_day[sess_name] = result
            summary_rows.append({
                "day": d_es,
                "session": sess_name,
                **result,
            })
        export_all[d_es] = export_day

    # ═══════════════════════════════════════════════════════════════
    #  TABLA RESUMEN FINAL
    # ═══════════════════════════════════════════════════════════════
    print(f"\n\n{'═'*70}")
    print("  📊 TABLA RESUMEN FINAL — DÍAS × SESIONES × 6 MESES")
    print(f"{'═'*70}")
    print(f"  {'DÍA':<10} {'SESIÓN':<12} {'N':>4} {'PATRÓN DOM':<22} {'%':>6} "
          f"{'RNG':>6} {'VAL%':>6} {'EMA%':>6} {'DIR':>10}")
    print("  " + "─" * 74)
    for row in summary_rows:
        if not row.get('dominant_pattern'):
            continue
        val_pct = row.get('value_area', {}).get('val', {}).get('hit_rate', '—')
        ema_pct = row.get('ema200', {}).get('hit_rate', '—')
        dirb    = row.get('dir_dominant', '—')
        dir_cnt = row.get('direction', {})
        n_sess  = row.get('sessions', 1)
        dirp    = round(dir_cnt.get(dirb, 0) / max(n_sess, 1) * 100, 0) if n_sess else 0
        avg_r   = row.get('avg_range', 0)
        print(f"  {row['day']:<10} {row['session']:<12} {n_sess:>4} "
              f"{row['dominant_pattern']:<22} {row['dominant_pct']:>6} "
              f"{avg_r:>5.0f}p {val_pct:>6} {ema_pct:>6}  "
              f"{dirb[:5]:>5}({dirp:.0f}%)")

    # ── Observaciones claves ──────────────────────────────────────
    print(f"\n{'─'*70}")
    print("  💡 OBSERVACIONES ESTRATÉGICAS")
    print(f"{'─'*70}")
    for row in summary_rows:
        if row.get('sessions', 0) < 5:
            continue
        d, s = row['day'], row['session']
        p = row.get('dominant_pattern', '—')
        pct = row.get('dominant_pct', '0%')
        bl  = row.get('best_level', '—')
        print(f"  {d:<10} {s:<12} → DOM: {p} ({pct})  |  Nivel: {bl}")

    # ── Guardar JSON ──────────────────────────────────────────────
    out = {
        "title":  "Backtest 5 Días × Sesión NQ · 6 Meses",
        "period": f"{start_date.strftime('%Y-%m-%d')} → {end_date.strftime('%Y-%m-%d')}",
        "sessions_analyzed": ["LONDON 03-08:29 ET", "NY_AM 09:30-12:00 ET", "NY_PM 12:01-16:00 ET"],
        "by_day": export_all,
    }
    path = "data/research/backtest_5dias_sesiones_6m.json"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=4, ensure_ascii=False, default=str)

    print(f"\n  ✅  Guardado → {path}")
    print(f"{'═'*70}\n")


if __name__ == "__main__":
    run()
