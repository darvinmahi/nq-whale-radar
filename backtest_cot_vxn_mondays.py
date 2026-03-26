"""
backtest_cot_vxn_mondays.py
═══════════════════════════════════════════════════════════════════════════════
Backtest: ¿Predice el COT + VXN la dirección de los lunes en NQ?

DATOS:
  • NQ histórico     → yfinance (NQ=F), 2022-hoy
  • VXN histórico    → yfinance (^VXN), 2022-hoy
  • COT histórico    → data/cot/nasdaq_cot_historical_study.csv

LÓGICA POR LUNES:
  1. NQ dirección:   close > open → BULLISH, else BEARISH
  2. COT del viernes anterior:
       · nivel neto (Lev Long - Short)
       · delta vs semana previa (cambió bearish / bullish)
  3. VXN del mismo lunes
  4. Señal combinada: COT_delta + VXN → predicción
  5. ¿Acertó en el mismo lunes? ¿En el siguiente?

SALIDA:
  data/backtest_cot_vxn_results.json   ← detalle por lunes
  data/backtest_cot_vxn_summary.json   ← estadísticas de acierto
  Imprime reporte en consola
"""

import json, csv, os
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
COT_CSV  = os.path.join(BASE, 'data', 'cot', 'nasdaq_cot_historical_study.csv')
OUT_DIR  = os.path.join(BASE, 'data')
OUT_DET  = os.path.join(OUT_DIR, 'backtest_cot_vxn_results.json')
OUT_SUM  = os.path.join(OUT_DIR, 'backtest_cot_vxn_summary.json')

# ─── Parámetros ───────────────────────────────────────────────────────────────
NQ_TICKER  = 'NQ=F'
VXN_TICKER = '^VXN'
START_DATE = '2022-01-01'
VXN_HIGH   = 22.0
VXN_LOW    = 18.0
LEV_BULL_DELTA_THRESH = 3_000   # si longs suben > 3k → señal bullish
LEV_BEAR_DELTA_THRESH = -3_000  # si longs bajan > 3k → señal bearish


# ─── 1. Descarga de datos ─────────────────────────────────────────────────────
def download_prices(ticker, start):
    try:
        import yfinance as yf
        df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
        if df.empty:
            print(f'[yf] Sin datos para {ticker}')
            return {}
        result = {}
        for idx, row in df.iterrows():
            d = idx.date()
            result[d] = {'open': float(row['Open']), 'close': float(row['Close'])}
        print(f'[yf] {ticker}: {len(result)} días descargados')
        return result
    except Exception as e:
        print(f'[yf] Error {ticker}: {e}')
        return {}


# ─── 2. Carga COT CSV ─────────────────────────────────────────────────────────
def load_cot():
    rows = []
    with open(COT_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                d    = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
                ll   = int(float(r.get('Lev_Money_Positions_Long_All',  0) or 0))
                ls   = int(float(r.get('Lev_Money_Positions_Short_All', 0) or 0))
                aml  = int(float(r.get('Asset_Mgr_Positions_Long_All',  0) or 0))
                ams  = int(float(r.get('Asset_Mgr_Positions_Short_All', 0) or 0))
                dl   = int(float(r.get('Dealer_Positions_Long_All',     0) or 0))
                ds   = int(float(r.get('Dealer_Positions_Short_All',    0) or 0))
                rows.append({'date': d, 'lev_long': ll, 'lev_short': ls,
                             'asst_long': aml, 'asst_short': ams,
                             'deal_long': dl,  'deal_short': ds,
                             'lev_net': ll - ls})
            except Exception:
                continue
    rows.sort(key=lambda x: x['date'])
    print(f'[COT] {len(rows)} semanas cargadas ({rows[0]["date"]} → {rows[-1]["date"]})')
    return rows


def cot_before(monday, cot_rows):
    """Devuelve (cot_this_week, cot_prev_week) — ambas fechas <= lunes"""
    eligible = [r for r in cot_rows if r['date'] <= monday]
    if not eligible:
        return None, None
    this_w = eligible[-1]
    prev_w = eligible[-2] if len(eligible) >= 2 else None
    return this_w, prev_w


# ─── 3. Señal combinada ────────────────────────────────────────────────────────
def make_signal(vxn, lev_net, lev_delta):
    """
    Combina VXN + nivel COT + cambio COT → predicción BULLISH/BEARISH/NEUTRAL
    Puntaje: cada indicador suma/resta 1 punto
    """
    score = 0

    # VXN
    if vxn is not None:
        if vxn >= VXN_HIGH:
            score -= 1   # alta volatilidad = sesgo bajista
        elif vxn <= VXN_LOW:
            score += 1

    # Nivel COT (si Lev Money está neto corto = bearish)
    if lev_net is not None:
        if lev_net < 0:
            score -= 1
        elif lev_net > 10_000:
            score += 1

    # Cambio COT (delta de longs esta semana vs la anterior)
    if lev_delta is not None:
        if lev_delta <= LEV_BEAR_DELTA_THRESH:
            score -= 1   # longs bajaron → presión bajista
        elif lev_delta >= LEV_BULL_DELTA_THRESH:
            score += 1

    if score > 0:
        return 'BULLISH', score
    elif score < 0:
        return 'BEARISH', score
    return 'NEUTRAL', 0


# ─── 4. Main backtest ─────────────────────────────────────────────────────────
def main():
    print('\n══ BACKTEST COT + VXN → LUNES NQ ══════════════════════════════════\n')

    # Descargar precios NQ y VXN
    nq_prices  = download_prices(NQ_TICKER,  START_DATE)
    vxn_prices = download_prices(VXN_TICKER, START_DATE)
    cot_rows   = load_cot()

    if not nq_prices:
        print('ERROR: No se pudo descargar NQ. Verifica conexión.')
        return

    # Filtrar solo lunes con datos NQ
    from datetime import date
    import calendar
    all_mondays = sorted([d for d in nq_prices if d.weekday() == 0])
    print(f'\nTotal lunes con datos NQ: {len(all_mondays)}')
    print(f'Rango: {all_mondays[0]} → {all_mondays[-1]}\n')

    results = []

    for i, monday in enumerate(all_mondays):
        nq  = nq_prices.get(monday)
        if not nq:
            continue

        direction = 'BULLISH' if nq['close'] >= nq['open'] else 'BEARISH'
        nq_move   = round(nq['close'] - nq['open'], 2)
        nq_pct    = round((nq['close'] - nq['open']) / nq['open'] * 100, 3)

        # VXN del lunes (si no hay, busca día siguiente)
        vxn_val = None
        for offset in range(4):
            d2 = monday + timedelta(days=offset)
            if d2 in vxn_prices:
                vxn_val = round(vxn_prices[d2]['close'], 2)
                break

        # COT del viernes anterior
        cot_this, cot_prev = cot_before(monday, cot_rows)
        lev_net   = cot_this['lev_net'] if cot_this else None
        lev_long  = cot_this['lev_long'] if cot_this else None
        lev_short = cot_this['lev_short'] if cot_this else None
        asst_long = cot_this['asst_long'] if cot_this else None
        asst_short= cot_this['asst_short'] if cot_this else None
        deal_long = cot_this['deal_long'] if cot_this else None
        deal_short= cot_this['deal_short'] if cot_this else None
        cot_week  = str(cot_this['date']) if cot_this else None

        # Delta COT (cambio en longa posición de Lev Money)
        lev_delta = None
        lev_delta_short = None
        if cot_this and cot_prev:
            lev_delta       = cot_this['lev_long'] - cot_prev['lev_long']
            lev_delta_short = cot_this['lev_short'] - cot_prev['lev_short']

        # Dirección del lunes SIGUIENTE (para medir lag)
        next_monday_dir = None
        if i + 1 < len(all_mondays):
            next_mon = all_mondays[i + 1]
            nq_next  = nq_prices.get(next_mon)
            if nq_next:
                next_monday_dir = 'BULLISH' if nq_next['close'] >= nq_next['open'] else 'BEARISH'

        # Señal combinada
        signal, score = make_signal(vxn_val, lev_net, lev_delta)

        # ¿Acertó?
        hit_same = (signal == direction) if signal != 'NEUTRAL' else None
        hit_next = (signal == next_monday_dir) if (signal != 'NEUTRAL' and next_monday_dir) else None

        results.append({
            'date'               : str(monday),
            'direction'          : direction,
            'nq_move'            : nq_move,
            'nq_pct'             : nq_pct,
            'vxn'                : vxn_val,
            'cot_week'           : cot_week,
            'lev_long'           : lev_long,
            'lev_short'          : lev_short,
            'lev_net'            : lev_net,
            'lev_delta_long'     : lev_delta,
            'lev_delta_short'    : lev_delta_short,
            'asst_long'          : asst_long,
            'asst_short'         : asst_short,
            'deal_long'          : deal_long,
            'deal_short'         : deal_short,
            'signal'             : signal,
            'signal_score'       : score,
            'hit_same_monday'    : hit_same,
            'next_monday_dir'    : next_monday_dir,
            'hit_next_monday'    : hit_next,
        })

    # ─── 5. Estadísticas ──────────────────────────────────────────────────────
    non_neutral = [r for r in results if r['signal'] != 'NEUTRAL']
    has_same    = [r for r in non_neutral if r['hit_same_monday'] is not None]
    has_next    = [r for r in non_neutral if r['hit_next_monday'] is not None]

    def pct(hits, total):
        return f'{round(len(hits)/total*100)}%' if total else 'N/A'

    # Por señal
    bear_sig = [r for r in has_same if r['signal'] == 'BEARISH']
    bull_sig = [r for r in has_same if r['signal'] == 'BULLISH']

    # Acierto en mismo lunes
    acc_total       = pct([r for r in has_same if r['hit_same_monday']], len(has_same))
    acc_bear_same   = pct([r for r in bear_sig if r['hit_same_monday']], len(bear_sig))
    acc_bull_same   = pct([r for r in bull_sig if r['hit_same_monday']], len(bull_sig))

    # Acierto en lunes siguiente
    acc_next_total  = pct([r for r in has_next if r['hit_next_monday']], len(has_next))

    # Cuando COT cambió bearish (delta negativo fuerte)
    cot_turned_bear = [r for r in results if r['lev_delta_long'] is not None and
                        r['lev_delta_long'] <= LEV_BEAR_DELTA_THRESH and r['hit_same_monday'] is not None]
    cot_turned_bull = [r for r in results if r['lev_delta_long'] is not None and
                        r['lev_delta_long'] >= LEV_BULL_DELTA_THRESH and r['hit_same_monday'] is not None]

    acc_cot_bear_same = pct([r for r in cot_turned_bear if r['direction'] == 'BEARISH'], len(cot_turned_bear))
    acc_cot_bull_same = pct([r for r in cot_turned_bull if r['direction'] == 'BULLISH'], len(cot_turned_bull))

    # Cuando COT cambió Y VXN confirma
    double_bear = [r for r in cot_turned_bear if r['vxn'] and r['vxn'] >= VXN_HIGH]
    double_bull = [r for r in cot_turned_bull if r['vxn'] and r['vxn'] <= VXN_LOW]
    acc_double_bear = pct([r for r in double_bear if r['direction'] == 'BEARISH'], len(double_bear))
    acc_double_bull = pct([r for r in double_bull if r['direction'] == 'BULLISH'], len(double_bull))

    summary = {
        'generated_at'           : datetime.utcnow().isoformat() + 'Z',
        'period'                 : f'{all_mondays[0]} → {all_mondays[-1]}',
        'total_mondays'          : len(results),
        'non_neutral_signals'    : len(non_neutral),
        'accuracy_same_monday'   : {
            'overall'   : acc_total,
            'when_bear_signal': acc_bear_same,
            'when_bull_signal': acc_bull_same,
            'sample_size': len(has_same),
        },
        'accuracy_next_monday'   : {
            'overall'  : acc_next_total,
            'sample_size': len(has_next),
        },
        'cot_delta_analysis'     : {
            'when_lev_long_dropped'   : {
                'occasions'    : len(cot_turned_bear),
                'monday_was_bearish': acc_cot_bear_same,
                'thresh': f'delta Long <= {LEV_BEAR_DELTA_THRESH:,}',
            },
            'when_lev_long_rose'      : {
                'occasions'    : len(cot_turned_bull),
                'monday_was_bullish': acc_cot_bull_same,
                'thresh': f'delta Long >= {LEV_BULL_DELTA_THRESH:,}',
            },
        },
        'double_confirmation'    : {
            'cot_bear_AND_vxn_high' : {
                'occasions': len(double_bear),
                'accuracy' : acc_double_bear,
            },
            'cot_bull_AND_vxn_low'  : {
                'occasions': len(double_bull),
                'accuracy' : acc_double_bull,
            },
        },
    }

    # ─── 6. Guardar resultados ────────────────────────────────────────────────
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_DET, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    with open(OUT_SUM, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ─── 7. Reporte consola ───────────────────────────────────────────────────
    print('\n══ RESULTADOS ══════════════════════════════════════════════════════')
    print(f'  Período:              {summary["period"]}')
    print(f'  Lunes analizados:     {summary["total_mondays"]}')
    print(f'  Señales no-neutras:   {summary["non_neutral_signals"]}')
    print()
    print('── Acierto en el MISMO lunes ───────────────────────────────────────')
    print(f'  Global:               {acc_total}   (n={len(has_same)})')
    print(f'  Señal BEARISH:        {acc_bear_same}  (n={len(bear_sig)})')
    print(f'  Señal BULLISH:        {acc_bull_same}  (n={len(bull_sig)})')
    print()
    print('── Acierto en el SIGUIENTE lunes (lag 1 semana) ───────────────────')
    print(f'  Global:               {acc_next_total}  (n={len(has_next)})')
    print()
    print('── Cuando COT CAMBIÓ (delta Lev Money Longs) ──────────────────────')
    print(f'  Longs bajaron >{abs(LEV_BEAR_DELTA_THRESH):,} → lunes fue bajista: {acc_cot_bear_same}  (n={len(cot_turned_bear)})')
    print(f'  Longs subieron >{LEV_BULL_DELTA_THRESH:,} → lunes fue alcista: {acc_cot_bull_same}  (n={len(cot_turned_bull)})')
    print()
    print('── Doble confirmación (COT cambió + VXN confirma) ─────────────────')
    print(f'  COT bearish + VXN>={VXN_HIGH} → lunes bajista: {acc_double_bear}  (n={len(double_bear)})')
    print(f'  COT bullish + VXN<={VXN_LOW}  → lunes alcista: {acc_double_bull}  (n={len(double_bull)})')
    print()
    print(f'\n✅  Detalle: {OUT_DET}')
    print(f'✅  Resumen: {OUT_SUM}')
    print('════════════════════════════════════════════════════════════════════\n')


if __name__ == '__main__':
    main()
