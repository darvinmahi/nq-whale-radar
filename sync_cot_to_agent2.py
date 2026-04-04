#!/usr/bin/env python3
"""
sync_cot_to_agent2.py
=====================
Lee el CSV maestro del COT (data/cot/nasdaq_cot_historical.csv)
y actualiza agent2_data.json con los datos más recientes.
Se ejecuta automáticamente después de update_cot.py
"""
import csv, json, os
from datetime import datetime, timezone

CSV    = 'data/cot/nasdaq_cot_historical.csv'
A2     = 'agent2_data.json'
DB     = 'data/research/daily_master_db.json'

def run():
    # ── 1. Leer CSV y calcular COT Index ──────────────────────────────
    rows = []
    with open(CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                d  = r['Report_Date_as_MM_DD_YYYY'].strip()
                ll = int(r['Lev_Money_Positions_Long_All'])
                ls = int(r['Lev_Money_Positions_Short_All'])
                rows.append({'date': d, 'long': ll, 'short': ls, 'net': ll - ls})
            except: pass

    rows.sort(key=lambda x: x['date'])
    for i, r in enumerate(rows):
        hist  = [x['net'] for x in rows[max(0, i - 156):i + 1]]
        mn, mx = min(hist), max(hist)
        r['ci']  = round((r['net'] - mn) / (mx - mn) * 100, 1) if mx > mn else 50.0

    if not rows:
        print('ERROR: CSV vacío')
        return

    last  = rows[-1]
    prev  = rows[-2] if len(rows) > 1 else last
    delta = last['net'] - prev['net']
    recent_12 = rows[-12:]

    # Señal
    ci = last['ci']
    if ci >= 70:   signal, strength = 'BULLISH',      80
    elif ci >= 55: signal, strength = 'BULLISH',      60
    elif ci >= 45: signal, strength = 'NEUTRAL',      50
    elif ci >= 30: signal, strength = 'BEARISH',      60
    else:          signal, strength = 'VERY_BEARISH', 80

    momentum_dir = 'SUBIENDO' if delta > 0 else 'BAJANDO'

    print('[OK] COT actualizado:')
    print(f'   Fecha:     {last["date"]}')
    print(f'   Net:       {last["net"]:,}')
    print(f'   COT Index: {ci}/100')
    print(f'   Señal:     {signal}')
    print(f'   Delta sem: {delta:+,}')

    # ── 2. Actualizar agent2_data.json ────────────────────────────────
    a2 = {}
    if os.path.exists(A2):
        with open(A2, encoding='utf-8') as f:
            a2 = json.load(f)

    a2['updated_at'] = datetime.now(timezone.utc).isoformat()
    a2['signal']     = signal
    a2['strength']   = strength
    a2['cot'] = {
        'report_date':   last['date'],
        'date':          last['date'],
        'current_net':   last['net'],
        'current_long':  last['long'],
        'current_short': last['short'],
        'cot_index':     ci,
        'delta':         delta,
        'history_min':   min(r['net'] for r in rows),
        'history_max':   max(r['net'] for r in rows),
    }
    a2['momentum'] = {
        'direction':          momentum_dir,
        'consecutive_weeks':  1,
        'weekly_velocity':    delta,
    }
    a2['recent_weeks'] = [
        {'date': r['date'], 'net': r['net'], 'long': r['long'],
         'short': r['short'], 'ci': r['ci']}
        for r in recent_12
    ]

    with open(A2, 'w', encoding='utf-8') as f:
        json.dump(a2, f, indent=2, ensure_ascii=False)
    print('   [OK] agent2_data.json actualizado')

    # ── 3. Actualizar daily_master_db con COT correcto ────────────────
    # Para cada registro de la DB, cruzar con la semana COT más cercana
    if not os.path.exists(DB):
        print('   ⚠  daily_master_db.json no encontrado, skip')
        return

    # Índice de fechas COT: para cada semana saber el CI
    cot_by_date = {r['date']: r['ci'] for r in rows}

    def find_cot_for_date(trade_date_str):
        """Encuentra el COT index más reciente disponible para esa fecha."""
        # trade_date en formato YYYY-MM-DD
        # cot dates en formato MM/DD/YYYY
        try:
            from datetime import date as d_
            td = d_.fromisoformat(trade_date_str)
            best_ci  = None
            best_diff = 9999
            for cot_str, ci in cot_by_date.items():
                parts = cot_str.split('/')
                if len(parts) == 3:
                    cd = d_(int(parts[2]), int(parts[0]), int(parts[1]))
                elif '-' in cot_str:
                    cd = d_.fromisoformat(cot_str)
                else:
                    continue
                diff = (td - cd).days
                if 0 <= diff < best_diff:
                    best_diff = diff
                    best_ci   = ci
            return best_ci
        except: return None

    with open(DB, encoding='utf-8') as f:
        db = json.load(f)
    records = db.get('records', [])
    updated = 0
    for r in records:
        ci_hist = find_cot_for_date(r.get('date', ''))
        if ci_hist is not None:
            r['cot_index'] = ci_hist
            updated += 1
    db['records'] = records
    db['meta']['cot_synced'] = datetime.now(timezone.utc).isoformat()
    with open(DB, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, separators=(',', ':'))
    print(f'   [OK] daily_master_db: {updated} registros con COT index corregido')

    # ── 4. Generar agent2_cot_analyst.js para la web ─────────────────
    recent_6 = rows[-6:]
    js_recent = ',\n    '.join([
        f'{{"date":"{r["date"]}","net":{r["net"]},"ci":{r["ci"]}}}'
        for r in reversed(recent_6)
    ])
    js_content = f'''// agent2_cot_analyst.js
// Generado automaticamente por sync_cot_to_agent2.py
// NO editar manualmente — se regenera cada viernes
window.NQ_COT = {{
  "generated": "{datetime.now(timezone.utc).isoformat()}",
  "report_date": "{last["date"]}",
  "cot_index": {ci},
  "current_net": {last["net"]},
  "current_long": {last["long"]},
  "current_short": {last["short"]},
  "delta_week": {delta},
  "signal": "{signal}",
  "strength": {strength},
  "momentum": "{momentum_dir}",
  "weeks_in_db": {len(rows)},
  "recent_weeks": [
    {js_recent}
  ]
}};
if (typeof window._cotLoaded === "function") window._cotLoaded(window.NQ_COT);
'''
    with open('agent2_cot_analyst.js', 'w', encoding='utf-8') as f:
        f.write(js_content)
    print(f'   [OK] agent2_cot_analyst.js generado con COT {ci}/100 {signal}')

if __name__ == '__main__':
    run()
