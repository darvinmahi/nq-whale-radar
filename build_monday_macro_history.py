"""
build_monday_macro_history.py
Genera data/monday_macro_history.json

Para cada lunes en _real_backtest_data.json:
  - VXN del día (yfinance ^VXN cierre)
  - COT neto (Lev_Money Long - Short) de la semana más cercana SIN look-ahead
  - COT Index 0-100 vs rango histórico
  - Señal: si VXN + COT predecían la dirección real

Salida:
  data/monday_macro_history.json
  data/monday_correlation_summary.json
"""

import json
import csv
import os
import sys
from datetime import datetime, timedelta

# ── Constantes COT ──────────────────────────────────────────────────────────
COT_MIN = -60_000   # mínimo histórico Lev Money neto (2022-2026)
COT_MAX =  60_000   # máximo histórico
COT_BEAR_THRESH  =      0   # neto < 0  → bearish
COT_BULL_THRESH  =  10_000  # neto > 10k → bullish
VXN_HIGH  = 22.0   # VXN > 22 = volatilidad elevada → sesgo bajista
VXN_LOW   = 18.0   # VXN < 18 = baja volatilidad → sesgo alcista

# ── Ruta archivos ────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
BACKTEST_F  = os.path.join(BASE_DIR, '_real_backtest_data.json')
COT_CSV     = os.path.join(BASE_DIR, 'data', 'cot', 'nasdaq_cot_historical_study.csv')
OUT_DIR     = os.path.join(BASE_DIR, 'data')
OUT_JSON    = os.path.join(OUT_DIR, 'monday_macro_history.json')
OUT_SUMMARY = os.path.join(OUT_DIR, 'monday_correlation_summary.json')

os.makedirs(OUT_DIR, exist_ok=True)


# ── 1) Carga lunes históricos ─────────────────────────────────────────────────
def load_mondays():
    with open(BACKTEST_F, encoding='utf-8') as f:
        data = json.load(f)
    return data.get('monday', {}).get('all_mondays', [])


# ── 2) Carga tabla COT histórica ──────────────────────────────────────────────
def load_cot_table():
    """Devuelve lista de dicts: {date: datetime, net: int, longs: int, shorts: int}"""
    rows = []
    if not os.path.exists(COT_CSV):
        print(f'[COT] ⚠️  No encontrado: {COT_CSV}')
        return rows
    with open(COT_CSV, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                d = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d')
                lng  = int(float(r.get('Lev_Money_Positions_Long_All',  0) or 0))
                shrt = int(float(r.get('Lev_Money_Positions_Short_All', 0) or 0))
                rows.append({'date': d, 'net': lng - shrt, 'longs': lng, 'shorts': shrt})
            except Exception:
                continue
    rows.sort(key=lambda x: x['date'])
    print(f'[COT] Cargadas {len(rows)} semanas (de {rows[0]["date"].date()} a {rows[-1]["date"].date()})')
    return rows


def cot_for_monday(monday_dt: datetime, cot_table: list):
    """
    Devuelve el COT de la semana COT más reciente ANTES o igual al lunes.
    El COT se publica el viernes, con datos al martes anterior.
    Para un lunes X usamos el COT publicado el viernes anterior (fecha <= lunes).
    """
    best = None
    for row in cot_table:
        if row['date'] <= monday_dt:
            best = row   # la más reciente que no supere el lunes
    return best


def cot_index(net: int) -> int:
    """Normaliza posición neta a índice 0-100 vs rango histórico."""
    idx = (net - COT_MIN) / (COT_MAX - COT_MIN) * 100
    return max(0, min(100, round(idx)))


# ── 3) Descarga VXN histórico de Yahoo Finance ────────────────────────────────
def download_vxn(dates: list):
    """
    Descarga ^VXN para las fechas dadas.
    Devuelve dict {datetime.date: float}.
    """
    try:
        import yfinance as yf
    except ImportError:
        print('[VXN] yfinance no instalado. pip install yfinance')
        return {}

    min_date = min(dates) - timedelta(days=5)
    max_date = max(dates) + timedelta(days=2)

    try:
        ticker = yf.Ticker('^VXN')
        df = ticker.history(start=min_date.strftime('%Y-%m-%d'),
                            end=(max_date + timedelta(days=1)).strftime('%Y-%m-%d'),
                            auto_adjust=True)
        if df.empty:
            print('[VXN] ⚠️  DataFrame vacío — verifíca conexión a internet')
            return {}
        # Usa el cierre de cada día
        mapping = {}
        for idx2, row in df.iterrows():
            # idx puede ser tz-aware
            d = idx2.date() if hasattr(idx2, 'date') else idx2
            mapping[d] = round(float(row['Close']), 2)
        print(f'[VXN] Descargados {len(mapping)} días de volatilidad')
        return mapping
    except Exception as e:
        print(f'[VXN] Error descargando ^VXN: {e}')
        return {}


def vxn_for_date(target_date, vxn_map: dict):
    """Busca el VXN del lunes; si no hay (p.ej. era holiday) busca día hábil siguiente."""
    for offset in range(5):
        d = target_date.date() + timedelta(days=offset) if hasattr(target_date, 'date') else target_date + timedelta(days=offset)
        if d in vxn_map:
            return vxn_map[d]
    return None


# ── 4) Lógica de predicción ────────────────────────────────────────────────────
def predict_signal(vxn, cot_net, cot_idx):
    """
    Combina VXN + COT para dar una predicción: BEARISH / BULLISH / NEUTRAL
    """
    bear_points = 0
    bull_points = 0

    if vxn is not None:
        if vxn >= VXN_HIGH:
            bear_points += 1
        elif vxn <= VXN_LOW:
            bull_points += 1

    if cot_net is not None:
        if cot_net < COT_BEAR_THRESH:
            bear_points += 1
        elif cot_net > COT_BULL_THRESH:
            bull_points += 1

    if bear_points > bull_points:
        return 'BEARISH'
    elif bull_points > bear_points:
        return 'BULLISH'
    else:
        return 'NEUTRAL'


# ── 5) Main ────────────────────────────────────────────────────────────────────
def main():
    mondays   = load_mondays()
    cot_table = load_cot_table()

    if not mondays:
        sys.exit('[Error] No se encontraron lunes en _real_backtest_data.json')

    # Fechas como datetime para consulta VXN
    monday_dts = [datetime.strptime(m['date'], '%Y-%m-%d') for m in mondays]
    vxn_map    = download_vxn(monday_dts)

    results = []
    for m, mdt in zip(mondays, monday_dts):
        date_str  = m['date']
        direction = m.get('direction', 'NEUTRAL')
        ny_range  = m.get('ny_range', 0)

        # VXN
        vxn = vxn_for_date(mdt, vxn_map)

        # COT
        cot_row   = cot_for_monday(mdt, cot_table)
        cot_net   = cot_row['net']   if cot_row else None
        cot_longs = cot_row['longs'] if cot_row else None
        cot_shorts= cot_row['shorts']if cot_row else None
        cot_week  = cot_row['date'].strftime('%Y-%m-%d') if cot_row else None
        cot_idx   = cot_index(cot_net) if cot_net is not None else None

        # Señal macro combinada
        macro_signal = predict_signal(vxn, cot_net, cot_idx)

        # ¿Los indicadores predijeron correctamente?
        predicted_ok = (macro_signal == direction) or \
                       (macro_signal == 'NEUTRAL' and direction in ('BEARISH', 'BULLISH'))
        # Si NEUTRAL no penaliza pero tampoco es acierto total
        if macro_signal == 'NEUTRAL':
            prediction_label = '⚡ NEUTRAL'
        elif macro_signal == direction:
            prediction_label = '✅ ACERTÓ'
        else:
            prediction_label = '❌ FALLÓ'

        row = {
            'date'            : date_str,
            'direction'       : direction,
            'ny_range'        : ny_range,
            'vxn'             : vxn,
            'vxn_signal'      : ('BEAR' if vxn and vxn >= VXN_HIGH else
                                 'BULL' if vxn and vxn <= VXN_LOW else 'NEUTRAL')
                                 if vxn else 'N/D',
            'cot_net'         : cot_net,
            'cot_longs'       : cot_longs,
            'cot_shorts'      : cot_shorts,
            'cot_index'       : cot_idx,
            'cot_week'        : cot_week,
            'cot_signal'      : ('BEAR' if cot_net is not None and cot_net < COT_BEAR_THRESH else
                                 'BULL' if cot_net is not None and cot_net > COT_BULL_THRESH else 'NEUTRAL')
                                 if cot_net is not None else 'N/D',
            'macro_prediction': macro_signal,
            'prediction_label': prediction_label,
        }
        results.append(row)
        print(f'  {date_str}  dir={direction:<8}  VXN={vxn or "N/D":<6}  '
              f'COT={str(cot_net or "N/D"):<8}  → {prediction_label}')

    # ── Guardar JSON de detalle ────────────────────────────────────────────────
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f'\n✅  Guardado: {OUT_JSON}')

    # ── Resumen de correlación ─────────────────────────────────────────────────
    bears     = [r for r in results if r['direction'] == 'BEARISH']
    bulls     = [r for r in results if r['direction'] == 'BULLISH']
    neutrals  = [r for r in results if r['direction'] == 'NEUTRAL']

    def pct_vxn_high(lst):
        valid = [r for r in lst if r['vxn'] is not None]
        return round(len([r for r in valid if r['vxn'] >= VXN_HIGH]) / len(valid) * 100) if valid else 0

    def pct_cot_bear(lst):
        valid = [r for r in lst if r['cot_net'] is not None]
        return round(len([r for r in valid if r['cot_net'] < 0]) / len(valid) * 100) if valid else 0

    def pct_predicted(lst, expected):
        return round(len([r for r in lst if r['macro_prediction'] == expected]) / len(lst) * 100) if lst else 0

    summary = {
        'generated_at'        : datetime.utcnow().isoformat() + 'Z',
        'total_mondays'       : len(results),
        'bearish_mondays'     : len(bears),
        'bullish_mondays'     : len(bulls),
        'neutral_mondays'     : len(neutrals),
        'bear_with_vxn_high'  : f'{pct_vxn_high(bears)}% de lunes BEARISH tenían VXN≥{VXN_HIGH}',
        'bear_with_cot_neg'   : f'{pct_cot_bear(bears)}% de lunes BEARISH tenían COT neto negativo',
        'bull_with_vxn_low'   : f'{"N/A" if not bulls else str(round(len([r for r in bulls if r["vxn"] and r["vxn"] <= VXN_LOW]) / len(bulls) * 100))}% de lunes BULLISH tenían VXN≤{VXN_LOW}',
        'prediction_accuracy' : {
            'overall': f'{round(len([r for r in results if "ACERTÓ" in r["prediction_label"]]) / len(results) * 100)}%',
            'on_bear' : f'{pct_predicted(bears, "BEARISH")}%',
            'on_bull' : f'{pct_predicted(bulls, "BULLISH")}%',
        }
    }

    with open(OUT_SUMMARY, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'✅  Resumen: {OUT_SUMMARY}')
    print()
    print('──── HALLAZGOS ────────────────────────────────────────')
    for k, v in summary.items():
        if k not in ('generated_at', 'prediction_accuracy'):
            print(f'  {k}: {v}')
    print('  PRECISIÓN:', summary['prediction_accuracy'])

if __name__ == '__main__':
    main()
