"""
backtest_cot_price_journey.py
═══════════════════════════════════════════════════════════════════════════════
ESTUDIO COMPLETO: Trayectoria del precio NQ cuando COT Index toca ≤15%

Para cada señal (COT Index <= EXTREME_LOW):
  - ¿Cuánto baja el precio PRIMERO antes de subir? (max drawdown pre-rally)
  - ¿En qué semana empieza realmente a subir?
  - ¿Hasta dónde llega el rally (máximo 12 semanas)?
  - ¿Cuándo se REVIERTE la tendencia alcista?
  - Semana a semana: precio, pct cambio, estado

Esto nos dice: cuando el COT Index toca ≤15%, qué debemos ESPERAR ver en el precio
antes de que el rally empiece, y cuándo salir.

SALIDA: data/cot_price_journey.json + imprime tabla detallada
"""

import json, csv, os
from datetime import datetime, timedelta

BASE    = os.path.dirname(os.path.abspath(__file__))
COT_CSV = os.path.join(BASE, 'data', 'cot', 'nasdaq_cot_historical_study.csv')
OUT_DIR = os.path.join(BASE, 'data')

START_DATE   = '2021-01-01'   # más atrás para tener ventana de 52 sem desde 2022
NQ_TICKER    = 'NQ=F'
INDEX_WINDOW = 52
EXTREME_LOW  = 15
WEEKS_FWD    = 12   # rastreamos 12 semanas completas


def download_nq(ticker, start):
    import yfinance as yf
    df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
    prices = {}
    for idx, row in df.iterrows():
        prices[idx.date()] = {'open': float(row['Open']), 'close': float(row['Close']),
                               'high': float(row['High']), 'low': float(row['Low'])}
    print(f'[yf] {ticker}: {len(prices)} días')
    return prices


def load_cot():
    rows = []
    with open(COT_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                d  = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
                ll = int(float(r.get('Lev_Money_Positions_Long_All',  0) or 0))
                ls = int(float(r.get('Lev_Money_Positions_Short_All', 0) or 0))
                aml= int(float(r.get('Asset_Mgr_Positions_Long_All',  0) or 0))
                ams= int(float(r.get('Asset_Mgr_Positions_Short_All', 0) or 0))
                rows.append({'date': d, 'net': ll - ls, 'll': ll, 'ls': ls,
                             'aml': aml, 'ams': ams, 'am_net': aml - ams})
            except: continue
    rows.sort(key=lambda x: x['date'])
    return rows


def add_cot_index(rows, window=52):
    for i, r in enumerate(rows):
        start = max(0, i - window + 1)
        nets = [rows[j]['net'] for j in range(start, i+1)]
        mn, mx = min(nets), max(nets)
        r['cot_index'] = round((r['net'] - mn) / (mx - mn) * 100, 1) if mx != mn else 50.0
        r['delta_ll']  = r['ll'] - rows[i-1]['ll'] if i > 0 else 0
        r['delta_ls']  = r['ls'] - rows[i-1]['ls'] if i > 0 else 0
        r['delta_net'] = r['net'] - rows[i-1]['net'] if i > 0 else 0
    return rows


def get_nq_price(monday, prices, offset_weeks=0, kind='close'):
    from datetime import timedelta
    target = monday + timedelta(weeks=offset_weeks)
    for off in range(5):
        d = target + timedelta(days=off)
        if d in prices:
            return d, prices[d][kind]
    return None, None


def next_monday_after(d):
    days_ahead = 7 - d.weekday()
    if d.weekday() == 0:
        days_ahead = 7
    return d + timedelta(days=days_ahead)


def main():
    print('\n══ ESTUDIO TRAYECTORIA COT INDEX ≤15% → NQ JOURNEY ══════════════\n')

    nq_prices = download_nq(NQ_TICKER, START_DATE)
    rows      = load_cot()
    rows      = add_cot_index(rows, INDEX_WINDOW)

    # Detecta señales (primera semana de cada cluster en ≤15%)
    signals = []
    in_zone = False
    for i, r in enumerate(rows[INDEX_WINDOW:], start=INDEX_WINDOW):
        if r['cot_index'] <= EXTREME_LOW:
            if not in_zone:
                in_zone = True
                signals.append(r)
        else:
            in_zone = False

    print(f'Señales COT Index ≤{EXTREME_LOW}%: {len(signals)} ocasiones\n')

    journeys = []

    for sig in signals:
        monday = next_monday_after(sig['date'])
        _, base = get_nq_price(monday, nq_prices, 0, 'close')
        if base is None:
            continue

        # Rastrear semana a semana hasta 12 semanas
        weekly = []
        for w in range(1, WEEKS_FWD + 1):
            d, close = get_nq_price(monday, nq_prices, w, 'close')
            if close is None:
                weekly.append(None)
                continue
            pct  = round((close - base) / base * 100, 3)
            pts  = round(close - base, 0)
            weekly.append({'w': w, 'date': str(d), 'close': round(close,0),
                           'pct': pct, 'pts': pts})

        # Findear el suelo (semana con mayor caída antes del rally)
        valid    = [w for w in weekly if w]
        # Max drawdown: peor semana consecutiva antes del pico
        losing   = [w for w in valid if w['pct'] < 0]
        max_dd   = min([w['pct'] for w in losing], default=0)
        max_dd_w = next((w['w'] for w in valid if w['pct'] == max_dd), None)

        # Max ganancia en todo el período
        max_gain   = max([w['pct'] for w in valid], default=0)
        max_gain_w = next((w['w'] for w in valid if w['pct'] == max_gain), None)

        # ¿Primera semana positiva? (inicio del rally)
        first_pos  = next((w['w'] for w in valid if w['pct'] > 0), None)

        # ¿Semana de reversión? (última semana positiva antes de volver negativo)
        # Busca el pico y cuánto tardó en regresar al punto de entrada
        reversal_w = None
        if max_gain_w:
            after_peak = [w for w in valid if w['w'] > max_gain_w]
            reversal   = next((w for w in after_peak if w['pct'] < 0), None)
            reversal_w = reversal['w'] if reversal else None

        entry = {
            'cot_date'   : str(sig['date']),
            'monday'     : str(monday),
            'cot_index'  : sig['cot_index'],
            'lev_net'    : sig['net'],
            'lev_long'   : sig['ll'],
            'lev_short'  : sig['ls'],
            'delta_long' : sig['delta_ll'],
            'delta_short': sig['delta_ls'],
            'am_net'     : sig['am_net'],
            'nq_base'    : round(base, 0),
            'max_drawdown_pct' : max_dd,
            'max_drawdown_week': max_dd_w,
            'max_gain_pct'     : max_gain,
            'max_gain_week'    : max_gain_w,
            'first_positive_week': first_pos,
            'reversal_back_week' : reversal_w,
            'weeks_data'  : weekly,
        }
        journeys.append(entry)

        # Imprime tabla de esa señal
        print(f'━━ Señal {sig["date"]}  COT Index={sig["cot_index"]}%  NQ Base={round(base,0):,}')
        print(f'   Lev: Long={sig["ll"]:,}  Short={sig["ls"]:,}  Net={sig["net"]:+,}  ΔLong={sig["delta_ll"]:+,}')
        print(f'   Max DD antes de rally: {max_dd}% (sem {max_dd_w})  |  Max ganancia: +{max_gain}% (sem {max_gain_w})')
        if first_pos:
            print(f'   Rally empieza: semana +{first_pos}')
        if reversal_w:
            print(f'   Price revierte a base: semana +{reversal_w}')
        print(f'   Sem:  ', end='')
        for w in valid[:8]:
            sign = '+' if w['pct'] >= 0 else ''
            print(f'W{w["w"]}:{sign}{w["pct"]}%  ', end='')
        print()
        print()

    # ── Promedios globales ────────────────────────────────────────────────────
    valid_j = [j for j in journeys if j['max_gain_pct'] > 0]
    if valid_j:
        avg_max_dd   = round(sum(j['max_drawdown_pct']   for j in journeys) / len(journeys), 2)
        avg_max_gain = round(sum(j['max_gain_pct']       for j in valid_j)  / len(valid_j),  2)
        avg_dd_week  = round(sum(j['max_drawdown_week']  for j in journeys if j['max_drawdown_week']) / 
                             sum(1 for j in journeys if j['max_drawdown_week']), 1)
        avg_gain_week= round(sum(j['max_gain_week']      for j in valid_j  if j['max_gain_week']) /
                             sum(1 for j in valid_j if j['max_gain_week']), 1)
        first_pos_avg= round(sum(j['first_positive_week'] for j in journeys if j['first_positive_week']) /
                             sum(1 for j in journeys if j['first_positive_week']), 1)

        print('═══════════════════════════════════════════════════════════════════')
        print(f'PROMEDIOS GLOBALES ({len(journeys)} señales):')
        print(f'  Avg caída antes del rally: {avg_max_dd}% en semana {avg_dd_week}')
        print(f'  Avg primera semana positiva: sem +{first_pos_avg}')
        print(f'  Avg max ganancia alcanzada: +{avg_max_gain}% en semana {avg_gain_week}')
        print('═══════════════════════════════════════════════════════════════════')

    # Guardar
    result = {
        'generated_at': datetime.now().isoformat(),
        'config': {'extreme_low': EXTREME_LOW, 'index_window': INDEX_WINDOW, 'weeks_forward': WEEKS_FWD},
        'total_signals': len(journeys),
        'journeys': journeys,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, 'cot_price_journey.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f'\n✅  {out_path}')


if __name__ == '__main__':
    main()
