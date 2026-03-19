import json, os

BASE = r'C:\Users\FxDarvin\Desktop\PAgina'
files = [
    'agent1_data.json','agent2_data.json','agent3_data.json',
    'agent4_data.json','agent6_data.json','agent7_data.json',
    'agent8_data.json','agent9_data.json','agent10_ict_stats.json',
    'agent11_data.json','agent12_backtest_results.json','agent13_data.json',
    'agent14_orderflow_data.json','agent_sentinel_data.json',
    'pulse_data.json','agent_live_data.js','index.html','analisis_promax.html'
]

for f in files:
    p = os.path.join(BASE, f)
    exists = os.path.exists(p)
    size = os.path.getsize(p) if exists else 0
    status = "OK" if (exists and size > 10) else "MISSING/EMPTY"
    print(f"  {status}: {f} ({size}b)")
