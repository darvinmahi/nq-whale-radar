import json
import os

BASE = r'C:\Users\FxDarvin\Desktop\PAgina'

# Intentar distintas rutas para el DB
paths = [
    os.path.join(BASE, 'data', 'research', 'daily_master_db.json'),
    os.path.join(BASE, 'daily_master_db.json'),
    os.path.join(BASE, 'agent1_data.json'),
]

for p in paths:
    if os.path.exists(p):
        print(f"Encontrado: {p}")
        with open(p, encoding='utf-8') as f:
            db = json.load(f)
        if isinstance(db, dict):
            keys = list(db.keys())[:10]
            print(f"  Keys: {keys}")
            recs = db.get('records', db.get('daily_data', []))
            if recs and isinstance(recs, list):
                print(f"  N registros: {len(recs)}")
                # Buscar desde sep 2025
                for r in recs:
                    fecha = r.get('date', r.get('Date', ''))
                    if str(fecha) >= '2025-09-01':
                        vix = r.get('vix', r.get('VIX'))
                        vxn = r.get('vxn', r.get('VXN'))
                        cot = r.get('cot_index', r.get('cot_idx'))
                        if vix or cot:
                            print(f"  {fecha}  VIX={vix}  VXN={vxn}  COT={cot}")
        break
