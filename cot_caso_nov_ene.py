"""
cot_caso_nov_ene.py - Caso especifico: Nov 12 2025 -> Ene 25 2026
Muestra semana a semana: longs/shorts de Dealer + Lev Money + Asset Mgr + precio NQ
para ver como cambiaron las posiciones en los dos giros de precio.
"""
import csv, json
from datetime import datetime, date, timedelta

COT_CSV = 'data/cot/nasdaq_cot_historical_study.csv'

# Carga COT
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
            rows.append({'date':d, 'dl':dl,'ds':ds,'dealer_net':dl-ds,
                         'll':ll,'ls':ls,'lev_net':ll-ls,
                         'aml':aml,'ams':ams,'am_net':aml-ams})
        except:
            continue
rows.sort(key=lambda x: x['date'])

# Agrega deltas
for i, r in enumerate(rows):
    for k in ['dealer_net','lev_net','am_net','ll','ls','dl','ds','aml','ams']:
        r['d_'+k] = r[k] - rows[i-1][k] if i > 0 else 0

# COT Index (52 sem ventana, Lev Money Net)
for i, r in enumerate(rows):
    start = max(0, i - 51)
    nets = [rows[j]['lev_net'] for j in range(start, i+1)]
    mn, mx = min(nets), max(nets)
    r['cot_idx'] = round((r['lev_net']-mn)/(mx-mn)*100, 1) if mx != mn else 50.0

# Filtra periodo
start_d = date(2025, 11, 4)
end_d   = date(2026, 2, 10)
period  = [r for r in rows if start_d <= r['date'] <= end_d]

# Precios NQ aproximados del periodo (weekly close)
# Descarga yfinance
import requests, time
def download_nq_via_requests(ticker='NQ=F', start='2025-11-03', end='2026-02-14'):
    from datetime import datetime
    t1 = int(datetime.strptime(start, '%Y-%m-%d').timestamp())
    t2 = int(datetime.strptime(end,   '%Y-%m-%d').timestamp())
    url = (f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}'
           f'?period1={t1}&period2={t2}&interval=1wk&events=history')
    hdrs = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=hdrs, timeout=30)
    data = r.json()['chart']['result'][0]
    ts   = data['timestamp']
    cls  = data['indicators']['quote'][0]['close']
    out  = {}
    for t, c in zip(ts, cls):
        if c is None: continue
        d = datetime.utcfromtimestamp(t).date()
        out[d] = round(c, 0)
    return out

prices = download_nq_via_requests()

def get_nq_close(cot_date):
    # Busca el viernes de la semana del COT (report es martes, cierre de semana es viernes)
    # O lunes siguiente
    for off in range(0, 8):
        d = cot_date + timedelta(days=off)
        if d in prices:
            return d, prices[d]
    return None, None

# Marcadores visuales
markers = {
    date(2025,11,12): 'INI',
    date(2025,11,18): 'GIRO-UP',
    date(2025,11,25): 'POST-TOP',
    date(2026,1,6):   'JAN-GIRO',
    date(2026,1,27):  'GIRO-DWN',
}

print()
print('=' * 120)
print('CASO ESTUDIO: Nov 12 2025 -> Feb 2026 — Recorrido completo COT + Precio NQ')
print('=' * 120)
print()

# Cabecera
print(f"{'Fecha':12} {'Evento':10} {'NQ':>8} {'DeltaNQ':>8}  |  "
      f"{'DLR-L':>8} {'DLR-S':>9} {'DlrNet':>8} {'dNet':>7}  |  "
      f"{'LEV-L':>8} {'LEV-S':>8} {'LevNet':>8} {'dL':>7} {'dS':>7}  |  "
      f"{'AM-L':>8} {'AM-S':>8} {'AmNet':>8} {'dAM':>7}  | COTIdx")
print('-' * 140)

prev_nq = None
for r in period:
    _, nq = get_nq_close(r['date'])
    nq_str  = f"{int(nq):,}"   if nq   else '--'
    dnq_str = f"{int(nq-prev_nq):+,}" if (nq and prev_nq) else '--'
    prev_nq = nq if nq else prev_nq
    mark = markers.get(r['date'], '')

    print(f"{str(r['date']):12} {mark:10} {nq_str:>8} {dnq_str:>8}  |  "
          f"{r['dl']:>8,} {r['ds']:>9,} {r['dealer_net']:>+8,} {r['d_dealer_net']:>+7,}  |  "
          f"{r['ll']:>8,} {r['ls']:>8,} {r['lev_net']:>+8,} {r['d_ll']:>+7,} {r['d_ls']:>+7,}  |  "
          f"{r['aml']:>8,} {r['ams']:>8,} {r['am_net']:>+8,} {r['d_am_net']:>+7,}  | {r['cot_idx']:>5.1f}%")

print()
print('LEYENDA:')
print('  DLR = Dealer (Comerciales / Smart Money contrarian)')
print('  LEV = Lev Money (Hedge Funds / especuladores)')
print('  AM  = Asset Manager (fondos institucionales long-biased)')
print('  dL/dS = delta longs/shorts vs semana anterior')
print('  COTIdx = COT Index (0%=max short, 100%=max long en 52 semanas)')
print()
print('EVENTOS:')
print('  GIRO-UP  = Semana donde el precio hizo minimo y empezo a subir')
print('  GIRO-DWN = Semana donde el precio hizo maximo y empezo a bajar')
