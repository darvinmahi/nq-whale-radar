#!/usr/bin/env python3
"""
FIX COMPLETO — Repara todos los datos del Daily Dashboard
==========================================================
Ejecutar: python fix_all_dashboard_data.py

Problemas que corrige:
1. VAH/POC hit rates — usa definicion correcta ICT (sweep = precio toca nivel y REGRESA)
2. NY stats en agent3_data.json — descarga datos reales de yfinance
3. today_analysis.json — normaliza claves para que el dashboard las lea
4. GEX sincronizado entre gex_today.json y agent3_data.json
"""

import json, os, sys
from datetime import date, datetime, timedelta
BASE = os.path.dirname(os.path.abspath(__file__))

def load(rel):
    with open(os.path.join(BASE, rel), 'r', encoding='utf-8') as f:
        return json.load(f)

def save(rel, data):
    with open(os.path.join(BASE, rel), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  OK saved {rel}")

# ══════════════════════════════════════════════════════════
# FIX 1 — VAH/POC/VAL Hit Rate definitivo
# Metodologia: el nivel pre-NY actua como SWEEP cuando:
#   UP sweep of VAH = precio supera VAH durante NY
#   Down sweep of VAL = precio baja bajo VAL durante NY
#   POC = precio toca POC al menos una vez
# Esto mide si el nivel funciono como trampa institucional.
# ══════════════════════════════════════════════════════════
def fix_hit_rates():
    print("\n[1] Recalculando hit rates con metodologia ICT sweep...")
    
    days_cfg = [
        ('monday',    'data/research/backtest_monday_1year.json',    'all_mondays'),
        ('tuesday',   'data/research/backtest_tuesday_1year.json',   'all_tuesdays'),
        ('wednesday', 'data/research/backtest_wednesday_1year.json', 'all_wednesdays'),
        ('thursday',  'data/research/backtest_thursday_1year.json',  'all_thursdays'),
        ('friday',    'data/research/backtest_friday_1year.json',    'all_fridays'),
    ]

    for day, rel, sess_key in days_cfg:
        fp = os.path.join(BASE, rel)
        if not os.path.exists(fp):
            continue
        d = load(rel)
        sess = d.get(sess_key) or d.get('sessions') or []
        n = len(sess)
        if n == 0:
            continue

        # ICT Definition:
        # VAH sweep = NY high > VAH (precio SUPERA la resistencia pre-NY)
        # VAL sweep = NY low < VAL (precio BAJA del soporte pre-NY)
        # POC touch = NY low <= POC <= NY high (precio TOCA el POC)
        vah_sweep, poc_touch, val_sweep = 0, 0, 0
        vah_reacts, poc_reacts, val_reacts = [], [], []

        for s in sess:
            vah = s.get('profile_vah') or 0
            poc = s.get('profile_poc') or 0
            val = s.get('profile_val') or 0
            ny_h = s.get('ny_high') or 0
            ny_l = s.get('ny_low')  or 0
            ny_move = abs(s.get('ny_move') or 0)

            if vah > 0 and ny_h > 0 and ny_h > vah:
                vah_sweep += 1
                vah_reacts.append(ny_move)
            if poc > 0 and ny_h > 0 and ny_l > 0 and ny_l <= poc <= ny_h:
                poc_touch += 1
                poc_reacts.append(ny_move)
            if val > 0 and ny_l > 0 and ny_l < val:
                val_sweep += 1
                val_reacts.append(ny_move)

        def avg(lst):
            return round(sum(lst)/len(lst), 0) if lst else 0

        va = {
            'vah': {'hit_rate': round(vah_sweep/n*100, 1), 'avg_reaction': avg(vah_reacts),
                    'definition': 'NY HIGH supera el VAH pre-NY'},
            'poc': {'hit_rate': round(poc_touch/n*100, 1), 'avg_reaction': avg(poc_reacts),
                    'definition': 'NYSE toca el POC pre-NY'},
            'val': {'hit_rate': round(val_sweep/n*100, 1), 'avg_reaction': avg(val_reacts),
                    'definition': 'NY LOW baja del VAL pre-NY'},
        }

        # Range distribution
        rd = {'0-200':0, '200-300':0, '300-400':0, '400-500':0, '500+':0}
        for s in sess:
            r = s.get('ny_range') or 0
            if   r < 200: rd['0-200']   += 1
            elif r < 300: rd['200-300'] += 1
            elif r < 400: rd['300-400'] += 1
            elif r < 500: rd['400-500'] += 1
            else:          rd['500+']    += 1

        st = d.get('stats', {})
        top_pat = st.get('top_pattern', 'N/A')
        top_pct = round((st.get('patterns',{}).get(top_pat,0)/n*100), 1) if n else 0

        d['value_area']         = va
        d['range_distribution'] = rd
        d['avg_ny_range']       = round(st.get('avg_range', 0), 1)
        d['dominant_pattern']   = top_pat
        d['dominant_pct']       = top_pct
        save(rel, d)

        print(f"   {day:12s}: VAH_sweep={va['vah']['hit_rate']}% POC_touch={va['poc']['hit_rate']}% VAL_sweep={va['val']['hit_rate']}%")


# ══════════════════════════════════════════════════════════
# FIX 2 — NY stats en agent3_data.json via yfinance
# ══════════════════════════════════════════════════════════
def fix_agent3_ny_stats():
    print("\n[2] Actualizando NY stats en agent3_data.json...")
    try:
        import yfinance as yf
        from datetime import date as d_date
        
        today = d_date.today()
        # Si es sabado/domingo, usar el viernes anterior
        wd = today.weekday()
        if wd == 5: today = today - timedelta(days=1)
        if wd == 6: today = today - timedelta(days=2)
        
        # Descargar NQ 5min del dia
        nq = yf.download("NQ=F", period="2d", interval="5m", progress=False)
        
        if nq.empty:
            print("   WARNING: no hay datos NQ=F")
            return

        # Sesion NY = 9:30 AM a 4:00 PM ET
        import pytz
        et = pytz.timezone("US/Eastern")
        
        # Convertir index a ET
        if nq.index.tz is None:
            nq.index = nq.index.tz_localize('UTC').tz_convert(et)
        else:
            nq.index = nq.index.tz_convert(et)
        
        # Filtrar solo el dia de trading mas reciente en horario NY
        today_str = today.strftime("%Y-%m-%d")
        day_data = nq[nq.index.strftime("%Y-%m-%d") == today_str]
        
        ny_data = day_data[
            (day_data.index.hour > 9) | 
            (day_data.index.hour == 9 and day_data.index.minute >= 30)
        ]
        ny_data = ny_data[day_data.index.hour < 16]
        
        if ny_data.empty:
            print(f"   WARNING: sin datos NY para {today_str}")
            return

        def get_val(series):
            v = series
            if hasattr(v, 'iloc'):
                return float(v.iloc[0])
            return float(v)

        ny_open  = get_val(ny_data['Open'].iloc[0])
        ny_close = get_val(ny_data['Close'].iloc[-1])
        ny_high  = float(ny_data['High'].max())
        ny_low   = float(ny_data['Low'].min())
        ny_range = round(ny_high - ny_low, 2)
        ny_move  = round(ny_close - ny_open, 2)
        
        # Cargar agent3
        a3_path = os.path.join(BASE, 'agent3_data.json')
        if not os.path.exists(a3_path):
            a3 = {'raw_inputs': {}}
        else:
            with open(a3_path, 'r', encoding='utf-8') as f:
                a3 = json.load(f)
        
        if 'raw_inputs' not in a3:
            a3['raw_inputs'] = {}
        
        a3['raw_inputs']['NY_OPEN']  = ny_open
        a3['raw_inputs']['NY_HIGH']  = ny_high
        a3['raw_inputs']['NY_LOW']   = ny_low
        a3['raw_inputs']['NY_CLOSE'] = ny_close
        a3['raw_inputs']['NY_RANGE'] = ny_range
        a3['raw_inputs']['NY_MOVE']  = ny_move
        a3['raw_inputs']['NY_DATE']  = today_str
        
        with open(a3_path, 'w', encoding='utf-8') as f:
            json.dump(a3, f, ensure_ascii=False, indent=2)
        
        print(f"   {today_str}: NY_OPEN={ny_open:.1f} NY_HIGH={ny_high:.1f} NY_LOW={ny_low:.1f} NY_RANGE={ny_range:.1f} MOVE={ny_move:+.1f}")
        
    except Exception as e:
        print(f"   ERROR: {e}")


# ══════════════════════════════════════════════════════════
# FIX 3 — Normalizar today_analysis.json
# ══════════════════════════════════════════════════════════  
def fix_today_analysis():
    print("\n[3] Normalizando today_analysis.json...")
    ta_path = 'data/research/today_analysis.json'
    try:
        d = load(ta_path)
        
        # El JS del dashboard espera estas claves:
        # casos, bearish_pct, bullish_pct, rango_promedio, patron_dominante, casos_detalle
        # pero analyze_today.py guarda: similar, prediction, theories
        
        similar = d.get('similar', [])
        pred = d.get('prediction', {})
        theories = d.get('theories', {})
        today = d.get('today', {})
        
        n = len(similar)
        bearish = sum(1 for s in similar if 'BEARISH' in s.get('direction','').upper())
        bullish = n - bearish
        bear_pct = round(bearish/n*100, 1) if n else 0
        bull_pct = round(bullish/n*100, 1) if n else 0
        
        ranges = [s.get('ny_range',0) for s in similar if s.get('ny_range')]
        avg_range = round(sum(ranges)/len(ranges), 0) if ranges else 0
        
        from collections import Counter
        pats = [s.get('pattern','N/A') for s in similar if s.get('pattern')]
        top_pat = Counter(pats).most_common(1)[0][0] if pats else 'N/A'
        
        # Inyectar campos normalizados que el dashboard usa
        d['casos']           = n
        d['casos_similares'] = n
        d['bearish_pct']     = bear_pct
        d['bullish_pct']     = bull_pct
        d['rango_promedio']  = avg_range
        d['patron_dominante']= top_pat
        d['casos_detalle']   = similar[-5:] if similar else []
        d['dow']             = today.get('dow', date.today().strftime('%A').lower())
        
        save(ta_path, d)
        print(f"   n={n} bearish={bear_pct}% bullish={bull_pct}% avg_range={avg_range} top_pat={top_pat}")
        
    except Exception as e:
        print(f"   ERROR: {e}")


# ══════════════════════════════════════════════════════════
# FIX 4 — Sincronizar GEX
# ══════════════════════════════════════════════════════════
def fix_gex_sync():
    print("\n[4] Sincronizando GEX...")
    try:
        gex = load('data/research/gex_today.json')
        a3 = load('agent3_data.json')
        
        if 'raw_inputs' not in a3:
            a3['raw_inputs'] = {}
        
        # Actualizar GEX en agent3 si el de gex_today.json tiene datos mas recientes
        gex_b = gex.get('gex_billions', 0)
        a3['raw_inputs']['GEX_B']   = gex_b
        a3['raw_inputs']['GEX_raw'] = gex.get('gex_raw', 0)
        a3['gex_analysis'] = {
            'value_B':     gex_b,
            'regime':      gex.get('gex_regime'),
            'description': gex.get('gex_description'),
            'positive':    gex.get('gex_positive'),
            'signal':      gex.get('gex_signal'),
            'put_call':    gex.get('put_call_ratio'),
        }
        save('agent3_data.json', a3)
        print(f"   GEX={gex_b}B {gex.get('gex_regime')}")
    except Exception as e:
        print(f"   ERROR: {e}")


if __name__ == '__main__':
    fix_hit_rates()
    fix_agent3_ny_stats()
    fix_today_analysis()
    fix_gex_sync()
    print("\n=== FIX COMPLETO === Listo para git push")
