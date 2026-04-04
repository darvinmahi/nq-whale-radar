#!/usr/bin/env python3
"""
Enrich backtest JSONs con value_area, range_distribution, dominant_pattern.
Los datos del POC/VAH/VAL son del pre-NY profile (Asia hasta 9:20 AM ET),
que es la metodologia ICT que usamos: profile desde Asia hasta 10 min antes de NY.
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))

DAY_FILES = {
    'monday':    'data/research/backtest_monday_1year.json',
    'tuesday':   'data/research/backtest_tuesday_1year.json',
    'wednesday': 'data/research/backtest_wednesday_1year.json',
    'thursday':  'data/research/backtest_thursday_1year.json',
    'friday':    'data/research/backtest_friday_1year.json',
}

def avg_react(hit_sessions):
    vals = [abs(s.get('ny_move', 0)) for s in hit_sessions if s.get('ny_move')]
    return round(sum(vals) / len(vals), 0) if vals else 0

for day, rel_path in DAY_FILES.items():
    fpath = os.path.join(BASE, rel_path)
    if not os.path.exists(fpath):
        print(f"SKIP {day}: no existe {fpath}")
        continue

    with open(fpath, 'r', encoding='utf-8') as f:
        d = json.load(f)

    # Las sesiones se llaman all_fridays, all_mondays, etc.
    sessions = (d.get('all_' + day + 's')
             or d.get('sessions')
             or [])
    n = len(sessions)
    if n == 0:
        print(f"SKIP {day}: 0 sessions")
        continue

    # ── Hit rates (pre-NY profile methodology) ──────────────────────────
    vah_hits = [s for s in sessions if s.get('vah_hit')]
    poc_hits = [s for s in sessions if s.get('poc_hit')]
    val_hits = [s for s in sessions if s.get('val_hit')]

    value_area = {
        'vah': {'hit_rate': round(len(vah_hits)/n*100, 1), 'avg_reaction': avg_react(vah_hits)},
        'poc': {'hit_rate': round(len(poc_hits)/n*100, 1), 'avg_reaction': avg_react(poc_hits)},
        'val': {'hit_rate': round(len(val_hits)/n*100, 1), 'avg_reaction': avg_react(val_hits)},
    }

    # ── Range distribution ──────────────────────────────────────────────
    rd = {'0-200': 0, '200-300': 0, '300-400': 0, '400-500': 0, '500+': 0}
    for s in sessions:
        r = s.get('ny_range', 0) or 0
        if   r < 200: rd['0-200']   += 1
        elif r < 300: rd['200-300'] += 1
        elif r < 400: rd['300-400'] += 1
        elif r < 500: rd['400-500'] += 1
        else:          rd['500+']    += 1

    # ── Stats neutro + dominant ─────────────────────────────────────────
    st = d.get('stats', {})
    bull = st.get('bull', 0)
    bear = st.get('bear', 0)
    neut = n - bull - bear
    st['neut']     = max(0, neut)
    st['neut_pct'] = round(max(0, neut) / n * 100, 1) if n else 0

    top_pat = st.get('top_pattern', 'N/A')
    top_pct = round((st.get('patterns', {}).get(top_pat, 0) / n * 100), 1) if n else 0

    # ── Inject ──────────────────────────────────────────────────────────
    d['value_area']         = value_area
    d['range_distribution'] = rd
    d['avg_ny_range']       = st.get('avg_range', 0)
    d['dominant_pattern']   = top_pat
    d['dominant_pct']       = top_pct
    d['stats']              = st

    with open(fpath, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    vah = value_area['vah']['hit_rate']
    poc = value_area['poc']['hit_rate']
    val = value_area['val']['hit_rate']
    avg_r = st.get('avg_range', 0)
    print(f"OK {day:12s}: n={n} | bull={st.get('bull_pct',0):.0f}% bear={st.get('bear_pct',0):.0f}% | VAH={vah}% POC={poc}% VAL={val}% | avg_range={avg_r}")

print("\nTodos los JSONs enriquecidos.")
