#!/usr/bin/env python3
"""Auditoria completa del sistema Whale Radar."""
import json, os, sys
BASE = os.path.dirname(os.path.abspath(__file__))

def load(path):
    p = os.path.join(BASE, path)
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

def real_hit(s, key):
    level = s.get(key) or 0
    ny_h  = s.get('ny_high') or 0
    ny_l  = s.get('ny_low')  or 0
    return ny_h > 0 and ny_l > 0 and ny_l <= level <= ny_h

print("=== AUDITORIA COMPLETA DEL SISTEMA ===\n")

# ─── 1. Backtest JSONs ───────────────────────────────────────────────
days_cfg = [
    ('monday',    'data/research/backtest_monday_1year.json',    'all_mondays'),
    ('tuesday',   'data/research/backtest_tuesday_1year.json',   'all_tuesdays'),
    ('wednesday', 'data/research/backtest_wednesday_1year.json', 'all_wednesdays'),
    ('thursday',  'data/research/backtest_thursday_1year.json',  'all_thursdays'),
    ('friday',    'data/research/backtest_friday_1year.json',    'all_fridays'),
]
print("1. BACKTEST JSONs — HIT RATES (metodologia pre-NY profile):")
for day, rel, sess_key in days_cfg:
    fp = os.path.join(BASE, rel)
    if not os.path.exists(fp):
        print(f"   {day}: MISSING {fp}")
        continue
    d = load(rel)
    sess = d.get(sess_key) or d.get('sessions') or []
    n = len(sess)
    if n == 0:
        print(f"   {day}: 0 sessions")
        continue
    # Calcular hits reales (VAH dentro del rango NY)
    vah_r = sum(1 for s in sess if real_hit(s, 'profile_vah'))
    poc_r = sum(1 for s in sess if real_hit(s, 'profile_poc'))
    val_r = sum(1 for s in sess if real_hit(s, 'profile_val'))
    st = d.get('stats', {})
    bull = st.get('bull_pct', 0)
    bear = st.get('bear_pct', 0)
    avg_r = st.get('avg_range', 0)
    # Verificar si tienen los campos necesarios para el dashboard
    has_va = 'value_area' in d
    has_rd = 'range_distribution' in d
    print(f"   {day:12s}: n={n} | {bull:.0f}%B/{bear:.0f}%Br | VAH={vah_r/n*100:.0f}% POC={poc_r/n*100:.0f}% VAL={val_r/n*100:.0f}% | avg_range={avg_r:.0f} | has_value_area={has_va} has_range_dist={has_rd}")

# ─── 2. today_analysis.json ─────────────────────────────────────────
print("\n2. TODAY_ANALYSIS:")
try:
    ta = load('data/research/today_analysis.json')
    print(f"   date={ta.get('date')} dow={ta.get('dow')} casos={ta.get('casos_similares', ta.get('casos','?'))} bearish_pct={ta.get('bearish_pct','?')}")
    print(f"   keys: {list(ta.keys())}")
except Exception as e:
    print(f"   ERROR: {e}")

# ─── 3. agent3_data.json ────────────────────────────────────────────
print("\n3. AGENT3 (NY live stats):")
try:
    a3 = load('agent3_data.json')
    ri = a3.get('raw_inputs', {})
    print(f"   NY_OPEN={ri.get('NY_OPEN')} NY_HIGH={ri.get('NY_HIGH')} NY_LOW={ri.get('NY_LOW')} NY_RANGE={ri.get('NY_RANGE')}")
    print(f"   GEX_B={ri.get('GEX_B')} VXN={ri.get('VXN')} COT_INDEX={ri.get('COT_INDEX')}")
except Exception as e:
    print(f"   ERROR: {e}")

# ─── 4. GEX ─────────────────────────────────────────────────────────
print("\n4. GEX_TODAY:")
try:
    gex = load('data/research/gex_today.json')
    print(f"   {gex.get('gex_billions')}B -> {gex.get('gex_regime')} | P/C={gex.get('put_call_ratio')} strikes={gex.get('strikes_analyzed')}")
except Exception as e:
    print(f"   ERROR: {e}")

# ─── 5. Verificar errores JS conocidos ──────────────────────────────
print("\n5. ELEMENTOS DOM NECESARIOS (loadMacroIndicators):")
html_file = os.path.join(BASE, 'daily_dashboard.html')
with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

needed_ids = ['dir-bull','dir-bear','dir-neut','chartDirection','chartPatterns',
              'level-bars','range-hist','conclusions','sessions-body']
for eid in needed_ids:
    found = f'id="{eid}"' in html
    print(f"   {'OK' if found else 'MISSING'} #{eid}")

print("\n=== FIN AUDITORIA ===")
