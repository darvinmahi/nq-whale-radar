"""
backtest_cot_regime_mondays.py
═══════════════════════════════════════════════════════════════════════════════
Backtest de RÉGIMEN: ¿Cuando el COT gira bearish/bullish,
cuántas semanas tarda NQ en seguirlo y qué tan sostenido es el efecto?

LÓGICA:
  1. Detecta cada "giro" del COT (de semana en semana):
       · Giro BEARISH: Lev_Long cae > DELTA_THRESH durante ≥2 semanas consecutivas
       · Giro BULLISH: Lev_Long sube > DELTA_THRESH durante ≥2 semanas consecutivas
  2. Para cada giro, mide NQ:
       · Semana 1 después (lunes +1)
       · Semana 2 después (lunes +2)
       · Semana 3 después (lunes +3)
       · Semana 4 después (lunes +4)
       · Acumulado 4 semanas
  3. También mide: ¿cuántos puntos se movió NQ?

SALIDA:
  data/backtest_cot_regime_results.json
  data/backtest_cot_regime_summary.json
"""

import json, csv, os
from datetime import datetime, timedelta, date

BASE    = os.path.dirname(os.path.abspath(__file__))
COT_CSV = os.path.join(BASE, 'data', 'cot', 'nasdaq_cot_historical_study.csv')
OUT_DIR = os.path.join(BASE, 'data')
OUT_DET = os.path.join(OUT_DIR, 'backtest_cot_regime_results.json')
OUT_SUM = os.path.join(OUT_DIR, 'backtest_cot_regime_summary.json')

START_DATE         = '2022-01-01'
NQ_TICKER          = 'NQ=F'
VXN_TICKER         = '^VXN'
DELTA_THRESH       =   2_000   # cambio semanal en posición Long para considerar giro
CONFIRM_WEEKS      =       1   # semanas consecutivas que deben confirmar el giro
WEEKS_FORWARD      =       4   # cuántas semanas hacia el futuro medimos el efecto


# ─── Descarga de precios ──────────────────────────────────────────────────────
def download_history(ticker, start):
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
        if df.empty:
            return {}
        result = {}
        for idx, row in df.iterrows():
            d = idx.date()
            result[d] = {'open': float(row['Open']), 'close': float(row['Close'])}
        print(f'[yf] {ticker}: {len(result)} días')
        return result
    except Exception as e:
        print(f'[yf] Error {ticker}: {e}')
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
                rows.append({'date': d, 'lev_long': ll, 'lev_short': ls,
                             'lev_net': ll - ls, 'asst_long': aml, 'asst_short': ams})
            except Exception:
                continue
    rows.sort(key=lambda x: x['date'])
    print(f'[COT] {len(rows)} semanas ({rows[0]["date"]} → {rows[-1]["date"]})')
    return rows


# ─── Lunes más cercano después de una fecha ───────────────────────────────────
def next_monday_on_or_after(d):
    """Dado date d, devuelve el lunes de esa semana o el siguiente."""
    dow = d.weekday()   # 0=Monday
    if dow == 0:
        return d
    return d + timedelta(days=(7 - dow))


def get_nq_close_week(monday, nq_prices, offset_weeks=0):
    """
    Devuelve el cierre del NQ en el lunes offset_weeks después del monday dado.
    Busca hasta 4 días hábiles adelante por si el lunes es feriado.
    """
    target = monday + timedelta(weeks=offset_weeks)
    for offset in range(5):
        d = target + timedelta(days=offset)
        if d in nq_prices:
            return d, nq_prices[d]['close']
    return None, None


def get_nq_open_week(monday, nq_prices, offset_weeks=0):
    target = monday + timedelta(weeks=offset_weeks)
    for offset in range(5):
        d = target + timedelta(days=offset)
        if d in nq_prices:
            return d, nq_prices[d]['open']
    return None, None


# ─── Detecta giros del COT ────────────────────────────────────────────────────
def detect_cot_turns(cot_rows):
    """
    Devuelve lista de giros:
    {date, direction: BEARISH/BULLISH, lev_long, lev_short, lev_net,
     delta_long, delta_short, asst_long, asst_short}
    """
    turns = []
    for i in range(CONFIRM_WEEKS, len(cot_rows)):
        curr = cot_rows[i]
        prev = cot_rows[i - 1]

        delta_long  = curr['lev_long']  - prev['lev_long']
        delta_short = curr['lev_short'] - prev['lev_short']

        # Giro BEARISH: longs caen fuerte O net empeora Y shorts suben
        bearish_turn = delta_long <= -DELTA_THRESH and curr['lev_net'] < prev['lev_net']
        # Giro BULLISH: longs suben fuerte O net mejora Y shorts bajan
        bullish_turn = delta_long >= DELTA_THRESH  and curr['lev_net'] > prev['lev_net']

        if bearish_turn or bullish_turn:
            direction = 'BEARISH' if bearish_turn else 'BULLISH'
            turns.append({
                'cot_date'   : curr['date'],
                'direction'  : direction,
                'lev_long'   : curr['lev_long'],
                'lev_short'  : curr['lev_short'],
                'lev_net'    : curr['lev_net'],
                'delta_long' : delta_long,
                'delta_short': delta_short,
                'prev_long'  : prev['lev_long'],
                'prev_short' : prev['lev_short'],
                'prev_net'   : prev['lev_net'],
                'asst_long'  : curr['asst_long'],
                'asst_short' : curr['asst_short'],
            })
    print(f'[GIROS] Detectados {len(turns)} giros del COT (DELTA_THRESH={DELTA_THRESH:,})')
    return turns


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print('\n══ BACKTEST RÉGIMEN COT → NQ (2022-2026) ═════════════════════════\n')

    nq_prices  = download_history(NQ_TICKER,  START_DATE)
    vxn_prices = download_history(VXN_TICKER, START_DATE)
    cot_rows   = load_cot()

    if not nq_prices:
        print('ERROR: Sin datos NQ')
        return

    turns   = detect_cot_turns(cot_rows)
    results = []

    for turn in turns:
        cot_date  = turn['cot_date']
        direction = turn['direction']

        # El COT se publica viernes → el efecto empieza el lunes siguiente
        monday_0 = next_monday_on_or_after(cot_date + timedelta(days=1))

        # Precio base: apertura del lunes 0 (el lunes después de la publicación)
        _, nq_base = get_nq_open_week(monday_0, nq_prices, offset_weeks=0)
        if nq_base is None:
            continue

        # VXN del lunes 0
        vxn_val = None
        for off in range(5):
            d2 = monday_0 + timedelta(days=off)
            if d2 in vxn_prices:
                vxn_val = round(vxn_prices[d2]['close'], 2)
                break

        # Medir NQ en cada una de las semanas siguientes
        weekly = []
        for w in range(1, WEEKS_FORWARD + 1):
            d_mon, nq_close = get_nq_close_week(monday_0, nq_prices, offset_weeks=w)
            if nq_close is None:
                weekly.append(None)
                continue
            delta_pts = round(nq_close - nq_base, 2)
            delta_pct = round((nq_close - nq_base) / nq_base * 100, 3)
            weekly_dir = 'BULLISH' if delta_pct >= 0 else 'BEARISH'
            # ¿sigue la dirección del COT?
            match = (weekly_dir == direction)
            weekly.append({
                'week'      : w,
                'date'      : str(d_mon),
                'nq_close'  : round(nq_close, 2),
                'delta_pts' : delta_pts,
                'delta_pct' : delta_pct,
                'direction' : weekly_dir,
                'cot_match' : match,
            })

        # ¿En cuántas semanas el mercado siguió al COT?
        valid_weeks  = [w for w in weekly if w is not None]
        matches      = [w for w in valid_weeks if w['cot_match']]
        match_rate   = round(len(matches) / len(valid_weeks) * 100) if valid_weeks else None

        # Max movimiento a favor / en contra en 4 semanas
        if valid_weeks:
            in_direction = [w['delta_pts'] for w in valid_weeks
                            if direction == 'BEARISH' and w['delta_pts'] < 0
                            or direction == 'BULLISH' and w['delta_pts'] > 0]
            max_move = max([abs(x) for x in in_direction]) if in_direction else 0
        else:
            max_move = None

        row = {
            'cot_date'        : str(cot_date),
            'cot_direction'   : direction,
            'monday_0'        : str(monday_0),
            'nq_base'         : round(nq_base, 2),
            'vxn'             : vxn_val,
            'lev_long'        : turn['lev_long'],
            'lev_short'       : turn['lev_short'],
            'lev_net'         : turn['lev_net'],
            'delta_long'      : turn['delta_long'],
            'delta_short'     : turn['delta_short'],
            'prev_long'       : turn['prev_long'],
            'prev_short'      : turn['prev_short'],
            'asst_long'       : turn['asst_long'],
            'asst_short'      : turn['asst_short'],
            'weeks'           : weekly,
            'weeks_matching'  : len(matches),
            'weeks_total'     : len(valid_weeks),
            'match_rate_pct'  : match_rate,
            'max_move_in_dir' : max_move,
        }
        results.append(row)

    # ─── Estadísticas ──────────────────────────────────────────────────────────
    bear_turns = [r for r in results if r['cot_direction'] == 'BEARISH']
    bull_turns = [r for r in results if r['cot_direction'] == 'BULLISH']

    def avg(lst):
        return round(sum(lst) / len(lst), 1) if lst else None

    def pct_weeks_correct(turns_list, week_n):
        """¿Qué % de giros, la semana N después el mercado siguió al COT?"""
        valid = [r for r in turns_list
                 if r['weeks'] and len(r['weeks']) >= week_n
                 and r['weeks'][week_n - 1] is not None]
        hits = [r for r in valid if r['weeks'][week_n - 1]['cot_match']]
        return (f'{round(len(hits)/len(valid)*100)}%', len(valid)) if valid else ('N/A', 0)

    print('\n══ RESULTADOS RÉGIMEN ══════════════════════════════════════════════')
    print(f'  Giros COT detectados: {len(results)}')
    print(f'    · Bearish: {len(bear_turns)}  |  Bullish: {len(bull_turns)}')
    print()

    summary_data = {
        'generated_at': datetime.now().isoformat(),
        'config': {
            'delta_thresh': DELTA_THRESH,
            'confirm_weeks': CONFIRM_WEEKS,
            'weeks_forward': WEEKS_FORWARD,
            'period': f'{cot_rows[0]["date"]} → {cot_rows[-1]["date"]}',
        },
        'total_turns': len(results),
        'bearish_turns': len(bear_turns),
        'bullish_turns': len(bull_turns),
        'effect_by_week': {},
    }

    for w in range(1, WEEKS_FORWARD + 1):
        acc_bear, n_bear = pct_weeks_correct(bear_turns, w)
        acc_bull, n_bull = pct_weeks_correct(bull_turns, w)
        pct_str   = f'Bear={acc_bear} (n={n_bear})  |  Bull={acc_bull} (n={n_bull})'
        print(f'  Semana +{w} NQ siguió al COT:  {pct_str}')
        summary_data['effect_by_week'][f'week_{w}'] = {
            'bearish': {'accuracy': acc_bear, 'n': n_bear},
            'bullish': {'accuracy': acc_bull, 'n': n_bull},
        }

    print()
    # Promedio de semanas correctas por giro
    avg_bear = avg([r['match_rate_pct'] for r in bear_turns if r['match_rate_pct'] is not None])
    avg_bull = avg([r['match_rate_pct'] for r in bull_turns if r['match_rate_pct'] is not None])
    print(f'  Avg semanas correctas por giro BEARISH: {avg_bear}%')
    print(f'  Avg semanas correctas por giro BULLISH: {avg_bull}%')

    max_bear = avg([r['max_move_in_dir'] for r in bear_turns if r['max_move_in_dir'] is not None])
    max_bull = avg([r['max_move_in_dir'] for r in bull_turns if r['max_move_in_dir'] is not None])
    print(f'  Avg max caída en 4 semanas post-giro Bearish: {max_bear} pts NQ')
    print(f'  Avg max subida en 4 semanas post-giro Bullish: {max_bull} pts NQ')

    summary_data['avg_match_rate'] = {'bearish': avg_bear, 'bullish': avg_bull}
    summary_data['avg_max_move_pts'] = {'bearish': max_bear, 'bullish': max_bull}

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_DET, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    with open(OUT_SUM, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)

    print(f'\n✅  Detalle:  {OUT_DET}')
    print(f'✅  Resumen:  {OUT_SUM}')
    print('════════════════════════════════════════════════════════════════════\n')


if __name__ == '__main__':
    main()
