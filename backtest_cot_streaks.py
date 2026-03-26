"""
backtest_cot_streaks.py
═══════════════════════════════════════════════════════════════════════════════
COT PROFESIONAL: Cómo los traders realmente usan el COT

MÉTRICAS CORRECTAS:
  1. COT INDEX (percentil 52 semanas)
     · 0%   = mínimo histórico de Net Position (extremo bajista → posible SUELO)
     · 100% = máximo histórico de Net Position (extremo alcista → posible TECHO)
     · Señal real: extremo <15% o >85%

  2. RACHAS CONSECUTIVAS
     · 3+ semanas seguidas de longs SUBIENDO = acumulación institucional
     · 3+ semanas seguidas de longs BAJANDO  = distribución institucional

  3. CRUCE DE CERO DEL NET
     · Net pasa de positivo a negativo (Lev Money se vuelve neto short) = BEARISH ESTRUCTURAL

PREGUNTAS DEL BACKTEST:
  a) Cuando COT Index < 15% (extremo bajista) → ¿NQ sube en las sig. semanas?
  b) Cuando COT Index > 85% (extremo alcista) → ¿NQ baja en las sig. semanas?
  c) Cuando hay racha ≥3 semanas de longs subiendo → ¿NQ sube?
  d) Cuando hay racha ≥3 semanas de longs bajando → ¿NQ baja?
  e) Cuando Net cruza de + a - → ¿NQ baja Y por cuánto?

SALIDA: data/backtest_cot_streaks_results.json + _summary.json
"""

import json, csv, os
from datetime import datetime, timedelta

BASE    = os.path.dirname(os.path.abspath(__file__))
COT_CSV = os.path.join(BASE, 'data', 'cot', 'nasdaq_cot_historical_study.csv')
OUT_DIR = os.path.join(BASE, 'data')

START_DATE     = '2022-01-01'
NQ_TICKER      = 'NQ=F'
INDEX_WINDOW   = 52    # semanas para calcular COT Index
EXTREME_LOW    = 15    # COT Index ≤ 15% = extremo bajista (señal BULLISH)
EXTREME_HIGH   = 85    # COT Index ≥ 85% = extremo alcista (señal BEARISH)
STREAK_MIN     = 3     # semanas consecutivas mínimas para contar racha
WEEKS_FWD      = 6     # semanas hacia el futuro que medimos


# ─── Descarga NQ ─────────────────────────────────────────────────────────────
def download_nq(ticker, start):
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
        prices = {}
        for idx, row in df.iterrows():
            prices[idx.date()] = {'open': float(row['Open']), 'close': float(row['Close'])}
        print(f'[yf] {ticker}: {len(prices)} días')
        return prices
    except Exception as e:
        print(f'[ERROR] {e}')
        return {}


# ─── Carga COT ────────────────────────────────────────────────────────────────
def load_cot():
    rows = []
    with open(COT_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                d   = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
                ll  = int(float(r.get('Lev_Money_Positions_Long_All',  0) or 0))
                ls  = int(float(r.get('Lev_Money_Positions_Short_All', 0) or 0))
                aml = int(float(r.get('Asset_Mgr_Positions_Long_All',  0) or 0))
                ams = int(float(r.get('Asset_Mgr_Positions_Short_All', 0) or 0))
                rows.append({'date': d, 'll': ll, 'ls': ls,
                             'net': ll - ls, 'aml': aml, 'ams': ams})
            except Exception:
                continue
    rows.sort(key=lambda x: x['date'])
    print(f'[COT] {len(rows)} semanas ({rows[0]["date"]} → {rows[-1]["date"]})')
    return rows


# ─── Calcula COT Index para cada semana ───────────────────────────────────────
def add_cot_index(rows, window=52):
    """Agrega cot_index (0-100%) basado en net position últimas 'window' semanas."""
    for i, r in enumerate(rows):
        start = max(0, i - window + 1)
        window_rows = rows[start : i + 1]
        nets = [w['net'] for w in window_rows]
        mn, mx = min(nets), max(nets)
        if mx == mn:
            r['cot_index'] = 50.0
        else:
            r['cot_index'] = round((r['net'] - mn) / (mx - mn) * 100, 1)
        # También agrega delta Long vs semana previa
        r['delta_ll'] = r['ll'] - rows[i-1]['ll'] if i > 0 else 0
        r['delta_ls'] = r['ls'] - rows[i-1]['ls'] if i > 0 else 0
        r['streak_sign'] = 1 if r['delta_ll'] > 0 else (-1 if r['delta_ll'] < 0 else 0)
    return rows


# ─── Calcula rachas consecutivas ─────────────────────────────────────────────
def add_streaks(rows):
    """Agrega streak_len: cuántas semanas seguidas llevan subiendo o bajando longs."""
    for i, r in enumerate(rows):
        if i == 0:
            r['streak_len'] = 0
            continue
        prev = rows[i - 1]
        if r['streak_sign'] == prev['streak_sign'] and r['streak_sign'] != 0:
            r['streak_len'] = prev['streak_len'] + 1
        else:
            r['streak_len'] = (1 if r['streak_sign'] != 0 else 0)
    return rows


# ─── NQ precio en semana +N después de una fecha ─────────────────────────────
def nq_after_n_weeks(monday_base, prices, n_weeks):
    """Precio de cierre del NQ N semanas después del monday_base."""
    from datetime import timedelta
    target = monday_base + timedelta(weeks=n_weeks)
    for off in range(5):
        d = target + timedelta(days=off)
        if d in prices:
            return prices[d]['close']
    return None


def next_monday_after(d):
    """Lunes de la semana siguiente al date d (día del COT = martes/miércoles)."""
    days_ahead = 7 - d.weekday()  # días hasta el próximo lunes
    if d.weekday() == 0:          # si ya es lunes, siguiente
        days_ahead = 7
    return d + timedelta(days=days_ahead)


# ─── Evalúa el efecto forward de una señal ───────────────────────────────────
def measure_forward(monday_base, nq_prices, expected_dir, n_weeks=WEEKS_FWD):
    """
    Devuelve dict con dirección y puntos NQ en cada semana futura.
    expected_dir: 'BULLISH' o 'BEARISH'
    """
    base_price = nq_after_n_weeks(monday_base, nq_prices, 0)
    if base_price is None:
        return None

    weeks = []
    for w in range(1, n_weeks + 1):
        price = nq_after_n_weeks(monday_base, nq_prices, w)
        if price is None:
            weeks.append(None)
            continue
        delta_pts = round(price - base_price, 2)
        delta_pct = round((price - base_price) / base_price * 100, 3)
        mkt_dir   = 'BULLISH' if delta_pct >= 0 else 'BEARISH'
        weeks.append({
            'week'     : w,
            'delta_pts': delta_pts,
            'delta_pct': delta_pct,
            'mkt_dir'  : mkt_dir,
            'match'    : mkt_dir == expected_dir,
        })
    return {'base_price': base_price, 'weeks': weeks}


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print('\n══ BACKTEST COT PROFESIONAL (Streaks + COT Index) ════════════════\n')

    nq_prices = download_nq(NQ_TICKER, START_DATE)
    rows      = load_cot()
    rows      = add_cot_index(rows, INDEX_WINDOW)
    rows      = add_streaks(rows)

    # ── A) Extremos del COT Index ─────────────────────────────────────────────
    extreme_low_signals  = []   # COT Index <= EXTREME_LOW → señal BULLISH
    extreme_high_signals = []   # COT Index >= EXTREME_HIGH → señal BEARISH

    for r in rows[INDEX_WINDOW:]:   # necesita ventana completa
        monday = next_monday_after(r['date'])
        if r['cot_index'] <= EXTREME_LOW:
            fwd = measure_forward(monday, nq_prices, 'BULLISH')
            if fwd:
                extreme_low_signals.append({
                    'cot_date'  : str(r['date']),
                    'monday'    : str(monday),
                    'cot_index' : r['cot_index'],
                    'lev_net'   : r['net'],
                    'signal'    : 'BULLISH (extremo bajo)',
                    **fwd,
                })
        elif r['cot_index'] >= EXTREME_HIGH:
            fwd = measure_forward(monday, nq_prices, 'BEARISH')
            if fwd:
                extreme_high_signals.append({
                    'cot_date'  : str(r['date']),
                    'monday'    : str(monday),
                    'cot_index' : r['cot_index'],
                    'lev_net'   : r['net'],
                    'signal'    : 'BEARISH (extremo alto)',
                    **fwd,
                })

    # ── B) Rachas consecutivas ≥ STREAK_MIN ──────────────────────────────────
    streak_bull_signals = []   # 3+ semanas longs subiendo → BULLISH
    streak_bear_signals = []   # 3+ semanas longs bajando  → BEARISH

    seen_streak_start = set()   # evita contar la misma racha múltiples veces

    for i, r in enumerate(rows):
        if r['streak_len'] < STREAK_MIN:
            continue
        # Es exactamente el inicio de una racha nueva (streak_len == STREAK_MIN)
        if r['streak_len'] != STREAK_MIN:
            continue
        key = f'{r["date"]}_{r["streak_sign"]}'
        if key in seen_streak_start:
            continue
        seen_streak_start.add(key)

        monday     = next_monday_after(r['date'])
        exp_dir    = 'BULLISH' if r['streak_sign'] > 0 else 'BEARISH'
        fwd        = measure_forward(monday, nq_prices, exp_dir)
        if not fwd:
            continue

        entry = {
            'cot_date'  : str(r['date']),
            'monday'    : str(monday),
            'cot_index' : r['cot_index'],
            'lev_net'   : r['net'],
            'delta_ll'  : r['delta_ll'],
            'streak_len': r['streak_len'],
            'signal'    : exp_dir,
            **fwd,
        }
        if r['streak_sign'] > 0:
            streak_bull_signals.append(entry)
        else:
            streak_bear_signals.append(entry)

    # ── C) Cruce de cero del Net (de + a -) ──────────────────────────────────
    zero_cross_signals = []
    for i in range(1, len(rows)):
        prev, curr = rows[i-1], rows[i]
        if prev['net'] >= 0 and curr['net'] < 0:   # cruce a neto SHORT → BEARISH
            monday = next_monday_after(curr['date'])
            fwd    = measure_forward(monday, nq_prices, 'BEARISH')
            if fwd:
                zero_cross_signals.append({
                    'cot_date': str(curr['date']),
                    'monday'  : str(monday),
                    'cot_index': curr['cot_index'],
                    'net_prev': prev['net'],
                    'net_curr': curr['net'],
                    'signal'  : 'BEARISH (cruce 0 de + a -)',
                    **fwd,
                })
        elif prev['net'] <= 0 and curr['net'] > 0:  # cruce a neto LONG → BULLISH
            monday = next_monday_after(curr['date'])
            fwd    = measure_forward(monday, nq_prices, 'BULLISH')
            if fwd:
                zero_cross_signals.append({
                    'cot_date': str(curr['date']),
                    'monday'  : str(monday),
                    'cot_index': curr['cot_index'],
                    'net_prev': prev['net'],
                    'net_curr': curr['net'],
                    'signal'  : 'BULLISH (cruce 0 de - a +)',
                    **fwd,
                })

    # ── Estadísticas ─────────────────────────────────────────────────────────
    def accuracy_by_week(signals, n_weeks=WEEKS_FWD):
        stats = []
        for w in range(1, n_weeks + 1):
            valid = [s for s in signals
                     if s['weeks'] and len(s['weeks']) >= w
                     and s['weeks'][w-1] is not None]
            hits  = [s for s in valid if s['weeks'][w-1]['match']]
            avg_move = round(sum(s['weeks'][w-1]['delta_pct'] for s in valid) / len(valid), 2) if valid else None
            stats.append({
                'week': w,
                'accuracy': f'{round(len(hits)/len(valid)*100)}%' if valid else 'N/A',
                'n': len(valid),
                'avg_pct_return': avg_move,
            })
        return stats

    print('══ A) EXTREMOS COT INDEX ════════════════════════════════════════════')
    print(f'  Señales BULLISH (COT Index ≤ {EXTREME_LOW}%):  {len(extreme_low_signals)} ocasiones')
    for s in accuracy_by_week(extreme_low_signals):
        print(f'    Sem +{s["week"]}: {s["accuracy"]} correcto  |  avg retorno: {s["avg_pct_return"]}%  (n={s["n"]})')

    print(f'\n  Señales BEARISH (COT Index ≥ {EXTREME_HIGH}%):  {len(extreme_high_signals)} ocasiones')
    for s in accuracy_by_week(extreme_high_signals):
        print(f'    Sem +{s["week"]}: {s["accuracy"]} correcto  |  avg retorno: {s["avg_pct_return"]}%  (n={s["n"]})')

    print('\n══ B) RACHAS CONSECUTIVAS ≥ 3 SEMANAS ══════════════════════════════')
    print(f'  Rachas BULLISH  (longs subiendo ≥{STREAK_MIN} sem):  {len(streak_bull_signals)} ocasiones')
    for s in accuracy_by_week(streak_bull_signals):
        print(f'    Sem +{s["week"]}: {s["accuracy"]} correcto  |  avg retorno: {s["avg_pct_return"]}%  (n={s["n"]})')

    print(f'\n  Rachas BEARISH (longs bajando ≥{STREAK_MIN} sem):  {len(streak_bear_signals)} ocasiones')
    for s in accuracy_by_week(streak_bear_signals):
        print(f'    Sem +{s["week"]}: {s["accuracy"]} correcto  |  avg retorno: {s["avg_pct_return"]}%  (n={s["n"]})')

    print('\n══ C) CRUCE DE CERO DEL NET POSITION ═══════════════════════════════')
    bull_cross = [s for s in zero_cross_signals if 'BULLISH' in s['signal']]
    bear_cross = [s for s in zero_cross_signals if 'BEARISH' in s['signal']]
    print(f'  Cruces BULLISH (net de - a +): {len(bull_cross)} ocasiones')
    for s in accuracy_by_week(bull_cross):
        print(f'    Sem +{s["week"]}: {s["accuracy"]} correcto  |  avg retorno: {s["avg_pct_return"]}%  (n={s["n"]})')
    print(f'\n  Cruces BEARISH (net de + a -): {len(bear_cross)} ocasiones')
    for s in accuracy_by_week(bear_cross):
        print(f'    Sem +{s["week"]}: {s["accuracy"]} correcto  |  avg retorno: {s["avg_pct_return"]}%  (n={s["n"]})')

    # ── Guarda resultados ────────────────────────────────────────────────────
    all_results = {
        'extreme_low_bullish'  : extreme_low_signals,
        'extreme_high_bearish' : extreme_high_signals,
        'streak_bullish'       : streak_bull_signals,
        'streak_bearish'       : streak_bear_signals,
        'zero_cross'           : zero_cross_signals,
    }
    summary = {
        'generated_at': datetime.now().isoformat(),
        'config': {
            'cot_index_window': INDEX_WINDOW,
            'extreme_low': EXTREME_LOW,
            'extreme_high': EXTREME_HIGH,
            'streak_min': STREAK_MIN,
            'weeks_forward': WEEKS_FWD,
        },
        'counts': {
            'extreme_low_bullish' : len(extreme_low_signals),
            'extreme_high_bearish': len(extreme_high_signals),
            'streak_bullish'      : len(streak_bull_signals),
            'streak_bearish'      : len(streak_bear_signals),
            'zero_cross_bullish'  : len(bull_cross),
            'zero_cross_bearish'  : len(bear_cross),
        },
        'accuracy_by_week': {
            'extreme_low_bullish'  : accuracy_by_week(extreme_low_signals),
            'extreme_high_bearish' : accuracy_by_week(extreme_high_signals),
            'streak_bullish'       : accuracy_by_week(streak_bull_signals),
            'streak_bearish'       : accuracy_by_week(streak_bear_signals),
            'zero_cross_bullish'   : accuracy_by_week(bull_cross),
            'zero_cross_bearish'   : accuracy_by_week(bear_cross),
        }
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, 'backtest_cot_streaks_results.json'), 'w') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, 'backtest_cot_streaks_summary.json'), 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print('\n✅  data/backtest_cot_streaks_results.json')
    print('✅  data/backtest_cot_streaks_summary.json')
    print('════════════════════════════════════════════════════════════════════\n')


if __name__ == '__main__':
    main()
