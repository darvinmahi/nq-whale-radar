"""
fetch_nq_5m_polygon.py  v2
Descarga I:NDX 5min en UNA sola petición grande (sin loops rápidos)
"""
import sys, os, io, csv, time, datetime, requests
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def load_key():
    for path in ['.env']:
        if os.path.exists(path):
            for line in open(path):
                if line.strip().startswith('POLYGON_API_KEY='):
                    return line.strip().split('=',1)[1].strip().strip('"').strip("'")
    return os.environ.get('POLYGON_API_KEY','')

API_KEY = load_key()
print(f"API Key: {'✅ OK' if API_KEY else '❌ NO'}")
if not API_KEY:
    sys.exit(1)

TICKER    = 'I:NDX'
DATE_FROM = '2024-04-13'   # exactamente 1 año atrás
DATE_TO   = '2026-04-11'
OUT_CSV   = 'data/research/nq_5m_polygon.csv'
os.makedirs('data/research', exist_ok=True)

print(f"\nDescargando {TICKER} 5min | {DATE_FROM} → {DATE_TO}")
print("Esperando 65s para reset rate limit...")
time.sleep(65)  # wait for rate limit reset

url = f"https://api.polygon.io/v2/aggs/ticker/{TICKER}/range/5/minute/{DATE_FROM}/{DATE_TO}"
params = {'apiKey': API_KEY, 'limit': 50000, 'sort': 'asc', 'adjusted': 'true'}

all_bars = []
page = 0
while True:
    page += 1
    print(f"  Página {page}...", end='', flush=True)
    try:
        r = requests.get(url, params=params, timeout=30)
        data = r.json()
    except Exception as e:
        print(f" Error: {e}")
        break

    status = data.get('status','')
    results = data.get('results', [])
    all_bars.extend(results)
    print(f" {len(results)} barras (total: {len(all_bars):,})")

    next_url = data.get('next_url')
    if not next_url or not results:
        break
    url    = next_url
    params = {'apiKey': API_KEY}
    time.sleep(15)  # esperar entre páginas para no exceder rate limit

if not all_bars:
    print("\n❌ Sin datos. Verifica plan de Polygon.")
    sys.exit(1)

print(f"\n✅ Total: {len(all_bars):,} barras descargadas")

rows = []
for b in all_bars:
    ts    = b['t'] / 1000
    utc   = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    # ET = UTC-4 (EDT verano) / UTC-5 (EST invierno)
    # Usamos UTC-4 como aproximación (la mayoría del año)
    et    = utc - datetime.timedelta(hours=4)
    rows.append({
        'Datetime':    utc.strftime('%Y-%m-%d %H:%M:%S+00:00'),
        'Datetime_ET': et.strftime('%Y-%m-%d %H:%M:%S'),
        'Open':  b['o'], 'High': b['h'],
        'Low':   b['l'], 'Close':b['c'],
        'Volume':b.get('v',0),
    })

import csv as csv_mod
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv_mod.DictWriter(f, fieldnames=rows[0].keys())
    w.writeheader(); w.writerows(rows)

print(f"✅ Guardado: {OUT_CSV}")
print(f"   Rango ET: {rows[0]['Datetime_ET']} → {rows[-1]['Datetime_ET']}")

import pandas as pd
df = pd.DataFrame(rows)
df['date'] = pd.to_datetime(df['Datetime_ET']).dt.date
df['dow']  = pd.to_datetime(df['Datetime_ET']).dt.weekday
days = df['date'].nunique()
print(f"\n📊 {days} días de trading | {len(df):,} barras 5min")
for d, nm in {0:'Lunes',1:'Martes',2:'Miércoles',3:'Jueves',4:'Viernes'}.items():
    n = df[df['dow']==d]['date'].nunique()
    print(f"   {nm}: {n} días (~{n} muestras por patrón)")
