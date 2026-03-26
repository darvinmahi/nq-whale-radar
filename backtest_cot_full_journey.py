"""
backtest_cot_full_journey.py
═══════════════════════════════════════════════════════════════════════════════
ESTUDIO: Camino completo del COT — Comercial (Dealer) vs Non-Comercial

Para cada período donde el NQ tuvo un giro importante, mostramos semana a semana:
  - Dealer Net    (Comercial / Smart Money)
  - Lev Money Net (Non-Comercial especulador)
  - Asset Mgr Net (Non-Comercial institucional)
  - NQ precio close
  - Semana de reversión de precio marcada con ⬆️ / ⬇️

HIPÓTESIS A INVESTIGAR:
  1. ¿Los Dealers (comerciales) empiezan a cambiar ANTES de que el precio gire?
  2. ¿Hay divergencia Dealer vs Lev Money antes de la reversión?
  3. ¿Qué patrón se repite en las semanas -4 a +4 alrededor del giro?

SALIDA: data/cot_full_journey.json + tabla visual en consola
"""

import json, csv, os
from datetime import datetime, timedelta

BASE    = os.path.dirname(os.path.abspath(__file__))
COT_CSV = os.path.join(BASE, 'data', 'cot', 'nasdaq_cot_historical_study.csv')
OUT_DIR = os.path.join(BASE, 'data')

NQ_TICKER  = 'NQ=F'
START_DATE = '2021-01-01'
WINDOW_COT = 52           # para calcular COT Index
WEEKS_BACK = 6            # semanas ANTES del giro que mostramos
WEEKS_FWD  = 8            # semanas DESPUÉS del giro que mostramos


# ─── Descarga NQ ─────────────────────────────────────────────────────────────
def download_nq(ticker, start):
    import yfinance as yf
    df = yf.Ticker(ticker).history(start=start, auto_adjust=True)
    prices = {}
    for idx, row in df.iterrows():
        prices[idx.date()] = {
            'close': float(row['Close']),
            'high' : float(row['High']),
            'low'  : float(row['Low']),
        }
    print(f'[yf] {ticker}: {len(prices)} días')
    return prices


def get_price(d, prices, kind='close'):
    for off in range(5):
        t = d + timedelta(days=off)
        if t in prices:
            return t, prices[t][kind]
    return None, None


# ─── Carga COT ────────────────────────────────────────────────────────────────
def load_cot():
    rows = []
    with open(COT_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                d   = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
                dl  = int(float(r.get('Dealer_Positions_Long_All',    0) or 0))
                ds  = int(float(r.get('Dealer_Positions_Short_All',   0) or 0))
                ll  = int(float(r.get('Lev_Money_Positions_Long_All', 0) or 0))
                ls  = int(float(r.get('Lev_Money_Positions_Short_All',0) or 0))
                aml = int(float(r.get('Asset_Mgr_Positions_Long_All', 0) or 0))
                ams = int(float(r.get('Asset_Mgr_Positions_Short_All',0) or 0))
                rows.append({
                    'date'    : d,
                    'dl': dl, 'ds': ds, 'dealer_net': dl - ds,
                    'dealer_long': dl, 'dealer_short': ds,
                    'll': ll, 'ls': ls, 'lev_net': ll - ls,
                    'lev_long': ll, 'lev_short': ls,
                    'aml': aml, 'ams': ams, 'am_net': aml - ams,
                    'am_long': aml, 'am_short': ams,
                })
            except Exception:
                continue
    rows.sort(key=lambda x: x['date'])

    # Agrega deltas y COT Index
    for i, r in enumerate(rows):
        r['delta_lev_long'] = r['ll'] - rows[i-1]['ll'] if i > 0 else 0
        r['delta_lev_short']= r['ls'] - rows[i-1]['ls'] if i > 0 else 0
        r['delta_dealer_net']= r['dealer_net'] - rows[i-1]['dealer_net'] if i > 0 else 0

        # COT Index (Lev Money Net, ventana 52 sem)
        start = max(0, i - WINDOW_COT + 1)
        nets  = [rows[j]['lev_net'] for j in range(start, i+1)]
        mn, mx = min(nets), max(nets)
        r['cot_index'] = round((r['lev_net']-mn)/(mx-mn)*100, 1) if mx != mn else 50.0

    print(f'[COT] {len(rows)} semanas cargadas')
    return rows


# ─── Detecta reversiones del precio NQ (picos y valles semanales) ─────────────
def find_price_reversals(rows, prices, min_move_pct=3.0):
    """
    Para cada semana COT, obtiene el precio NQ del lunes siguiente.
    Detecta reversiones donde el precio cambia de tendencia ≥ min_move_pct%
    en el período de 6 semanas.
    """
    weekly_prices = []
    for r in rows:
        d = r['date'] + timedelta(days=(7 - r['date'].weekday()))  # siguiente lunes
        _, px = get_price(d, prices, 'close')
        weekly_prices.append({'cot_date': r['date'], 'monday': d, 'price': px})

    # Detectar valles (mínimos locales → reversión BULLISH)
    reversals = []
    for i in range(2, len(weekly_prices) - 2):
        p = weekly_prices
        if p[i]['price'] is None:
            continue
        prices_valid = [p[j]['price'] for j in range(i-2, i+3) if p[j]['price']]
        if not prices_valid:
            continue
        px = p[i]['price']

        # Valle: precio más bajo que las 2 semanas anteriores Y 2 siguientes
        is_valley = (p[i-1]['price'] and p[i-2]['price'] and
                     p[i+1]['price'] and p[i+2]['price'] and
                     px < p[i-1]['price'] and px < p[i-2]['price'] and
                     px < p[i+1]['price'] and px < p[i+2]['price'])

        # Pico: precio más alto que las 2 semanas anteriores Y 2 siguientes
        is_peak  = (p[i-1]['price'] and p[i-2]['price'] and
                    p[i+1]['price'] and p[i+2]['price'] and
                    px > p[i-1]['price'] and px > p[i-2]['price'] and
                    px > p[i+1]['price'] and px > p[i+2]['price'])

        if is_valley:
            # ¿Cuánto subió después del valle?
            future_max = max(p[j]['price'] for j in range(i+1, min(i+9, len(p))) if p[j]['price'])
            move = round((future_max - px) / px * 100, 2) if future_max else 0
            if move >= min_move_pct:
                reversals.append({'idx': i, 'type': 'VALLEY', 'direction': 'BULLISH',
                                   'monday': p[i]['monday'], 'price': round(px, 0),
                                   'post_move_pct': move})

        elif is_peak:
            future_min = min(p[j]['price'] for j in range(i+1, min(i+9, len(p))) if p[j]['price'])
            move = round((px - future_min) / px * 100, 2) if future_min else 0
            if move >= min_move_pct:
                reversals.append({'idx': i, 'type': 'PEAK', 'direction': 'BEARISH',
                                   'monday': p[i]['monday'], 'price': round(px, 0),
                                   'post_move_pct': -move})

    return weekly_prices, reversals


# ─── Construye el "camino" alrededor de cada reversión ──────────────────────
def build_journey(rev_idx, weekly_prices, rows, prices, weeks_back=6, weeks_fwd=8):
    start_i = max(0, rev_idx - weeks_back)
    end_i   = min(len(rows)-1, rev_idx + weeks_fwd)

    journey = []
    rev_price = weekly_prices[rev_idx]['price']

    for i in range(start_i, end_i + 1):
        r  = rows[i]
        wp = weekly_prices[i]
        offset = i - rev_idx
        px = wp['price']
        pct_from_rev = round((px - rev_price)/rev_price*100, 2) if px and rev_price else None

        journey.append({
            'offset'       : offset,
            'cot_date'     : str(r['date']),
            'monday'       : str(wp['monday']),
            'is_reversal'  : offset == 0,
            'nq_price'     : round(px, 0) if px else None,
            'pct_from_rev' : pct_from_rev,
            # Dealer (Comercial)
            'dealer_long'  : r['dl'],
            'dealer_short' : r['ds'],
            'dealer_net'   : r['dealer_net'],
            'delta_dealer_net': r['delta_dealer_net'],
            # Lev Money (Non-Comercial especulador)
            'lev_long'     : r['ll'],
            'lev_short'    : r['ls'],
            'lev_net'      : r['lev_net'],
            'delta_lev_long'  : r['delta_lev_long'],
            'delta_lev_short' : r['delta_lev_short'],
            # Asset Manager (Non-Comercial institucional)
            'am_long'      : r['aml'],
            'am_short'     : r['ams'],
            'am_net'       : r['am_net'],
            # COT Index
            'cot_index'    : r['cot_index'],
        })
    return journey


# ─── Print tabla visual ───────────────────────────────────────────────────────
def print_journey(rev, journey, rev_type):
    mark = '⬆️ COMPRA' if rev_type == 'VALLEY' else '⬇️ VENTA'
    print(f'\n{"═"*90}')
    print(f'{mark}  Giro {rev["direction"]} │ Lunes={rev["monday"]} │ NQ={rev["price"]:,} │ Post-mov={rev["post_move_pct"]:+.1f}%')
    print(f'{"─"*90}')
    print(f'{"Offset":<7} {"Fecha COT":<12} {"NQ":>8} {"vs Giro":>8} │ '
          f'{"Dlr L":>8} {"Dlr S":>8} {"Dlr Net":>9} {"ΔDlr":>8} │ '
          f'{"Lev L":>8} {"Lev S":>8} {"Lev Net":>9} {"ΔLevL":>8} │ '
          f'{"AM L":>7} {"AM S":>7} {"AM Net":>8} │ {"COTidx":>7}')
    print(f'{"─"*90}')
    for w in journey:
        arrow = ' ◄◄ GIRO' if w['is_reversal'] else ''
        pct_s = f'{w["pct_from_rev"]:+.1f}%' if w['pct_from_rev'] is not None else '  --'
        px_s  = f'{int(w["nq_price"]):,}' if w['nq_price'] else '--'
        print(
            f'{w["offset"]:>+6}   {w["cot_date"]:<12} {px_s:>8} {pct_s:>8} │ '
            f'{w["dealer_long"]:>8,} {w["dealer_short"]:>8,} {w["dealer_net"]:>+9,} {w["delta_dealer_net"]:>+8,} │ '
            f'{w["lev_long"]:>8,} {w["lev_short"]:>8,} {w["lev_net"]:>+9,} {w["delta_lev_long"]:>+8,} │ '
            f'{w["am_long"]:>7,} {w["am_short"]:>7,} {w["am_net"]:>+8,} │ '
            f'{w["cot_index"]:>6.1f}%{arrow}'
        )
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print('\n══ ESTUDIO CAMINO COMPLETO: COT + PRECIO + REVERSIÓN ═════════════\n')

    nq_prices    = download_nq(NQ_TICKER, START_DATE)
    rows         = load_cot()
    weekly_px, reversals = find_price_reversals(rows, nq_prices, min_move_pct=3.0)

    print(f'\nReversiones detectadas (mov ≥3%): {len(reversals)}')
    valleys = [r for r in reversals if r['type'] == 'VALLEY']
    peaks   = [r for r in reversals if r['type'] == 'PEAK']
    print(f'  Valles (compra): {len(valleys)}  |  Picos (venta): {len(peaks)}\n')

    all_journeys = []

    # ── Valles (reversiones BULLISH) ─────────────────────────────────────────
    print('\n' + '█'*90)
    print('█  VALLES — Reversiones BULLISH (precio en mínimo, luego subió ≥3%)')
    print('█'*90)
    for rev in valleys:
        journey = build_journey(rev['idx'], weekly_px, rows, nq_prices, WEEKS_BACK, WEEKS_FWD)
        print_journey(rev, journey, 'VALLEY')
        all_journeys.append({'reversal': rev, 'type': 'VALLEY', 'journey': journey})

    # ── Picos (reversiones BEARISH) ───────────────────────────────────────────
    print('\n' + '█'*90)
    print('█  PICOS — Reversiones BEARISH (precio en máximo, luego bajó ≥3%)')
    print('█'*90)
    for rev in peaks:
        journey = build_journey(rev['idx'], weekly_px, rows, nq_prices, WEEKS_BACK, WEEKS_FWD)
        print_journey(rev, journey, 'PEAK')
        all_journeys.append({'reversal': rev, 'type': 'PEAK', 'journey': journey})

    # ── Patrones promedio ─────────────────────────────────────────────────────
    print('\n' + '═'*90)
    print('PATRONES PROMEDIO EN LAS 4 SEMANAS ANTES DEL GIRO (8 semanas):')
    print('─'*90)

    for rtype, label in [('VALLEY', 'BULLISH'), ('PEAK', 'BEARISH')]:
        evts = [e for e in all_journeys if e['type'] == rtype]
        if not evts:
            continue
        print(f'\n  {label}  ({len(evts)} eventos) — Avg de Dealer Net, Lev Net, AM Net en cada offset:')
        print(f'  {"Off":>5} {"Dlr Net avg":>12} {"Lev Net avg":>12} {"AM Net avg":>11} {"COT Idx avg":>11}')
        for off in range(-4, 5):
            d_vals = [w['dealer_net'] for e in evts
                      for w in e['journey'] if w['offset'] == off]
            l_vals = [w['lev_net']    for e in evts
                      for w in e['journey'] if w['offset'] == off]
            a_vals = [w['am_net']     for e in evts
                      for w in e['journey'] if w['offset'] == off]
            c_vals = [w['cot_index']  for e in evts
                      for w in e['journey'] if w['offset'] == off]
            def avg(lst):
                return round(sum(lst)/len(lst)) if lst else None

            marker = ' ◄ GIRO' if off == 0 else ''
            print(f'  {off:>+5} {str(avg(d_vals)):>12} {str(avg(l_vals)):>12} {str(avg(a_vals)):>11} {str(avg(c_vals) or "--"):>10}%{marker}')

    # Guarda
    result = {
        'generated_at': datetime.now().isoformat(),
        'total_reversals': len(reversals),
        'valleys': len(valleys),
        'peaks'  : len(peaks),
        'journeys': [
            {
                'type'    : e['type'],
                'reversal': {**e['reversal'], 'monday': str(e['reversal']['monday'])},
                'journey' : e['journey'],
            }
            for e in all_journeys
        ]
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, 'cot_full_journey.json')
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f'\n✅  {out}')
    print('════════════════════════════════════════════════════════════════════\n')


if __name__ == '__main__':
    main()
