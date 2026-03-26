"""
fetch_lunes_5m_v2.py
Descarga datos 5m NQ para los 6 lunes dentro del límite de 60 días de yfinance.
"""
import json, os
from datetime import datetime

try:
    import yfinance as yf
except ImportError:
    print("pip install yfinance"); exit()

# 6 lunes disponibles (26 Ene en adelante)
LUNES = [
    {'date':'2026-01-26','pattern':'EXPANSION_H','direction':'BULLISH','ny_range':224.2,'cot':76.4,'cot_label':'Bull Fuerte','match':True},
    {'date':'2026-02-02','pattern':'NEWS_DRIVE', 'direction':'BULLISH','ny_range':372.5,'cot':75.8,'cot_label':'Bull Fuerte','match':True},
    {'date':'2026-02-09','pattern':'NEWS_DRIVE', 'direction':'BULLISH','ny_range':410.8,'cot':58.9,'cot_label':'Bull Moderado','match':True},
    {'date':'2026-02-23','pattern':'NEWS_DRIVE', 'direction':'BEARISH','ny_range':372.0,'cot':79.7,'cot_label':'Bull Fuerte','match':False},
    {'date':'2026-03-02','pattern':'NEWS_DRIVE', 'direction':'BULLISH','ny_range':414.2,'cot':75.5,'cot_label':'Bull Fuerte','match':True},
    {'date':'2026-03-09','pattern':'NEWS_DRIVE', 'direction':'BULLISH','ny_range':337.0,'cot':23.0,'cot_label':'Bear Moderado','match':False},
]

print("Descargando NQ=F 5m (máx 60 días)...")
df = yf.download('NQ=F', period='60d', interval='5m', auto_adjust=True)

if df.empty:
    print("ERROR: sin datos"); exit()

if hasattr(df.columns, 'levels'):
    df.columns = df.columns.get_level_values(0)

df = df.reset_index()
time_col = df.columns[0]
print(f"Total barras: {len(df)} | col tiempo: {time_col}")

result = []

for lunes in LUNES:
    target = lunes['date']
    dt = datetime.strptime(target, '%Y-%m-%d')

    # DST: desde 8 Mar 2026 EDT (UTC-4), anterior EST (UTC-5)
    if target >= '2026-03-08':
        ny_open_utc  = (13, 30)  # 9:30 ET = 13:30 UTC
        ny_close_utc = 20        # 16:00 ET = 20:00 UTC
    else:
        ny_open_utc  = (14, 30)  # 9:30 ET = 14:30 UTC
        ny_close_utc = 21        # 16:00 ET = 21:00 UTC

    candles = []
    for _, row in df.iterrows():
        ts = row[time_col]
        ts_date = str(ts)[:10]
        if ts_date != target:
            continue

        h, m = ts.hour, ts.minute
        after_open   = (h > ny_open_utc[0]) or (h == ny_open_utc[0] and m >= ny_open_utc[1])
        before_close = h < ny_close_utc

        if not (after_open and before_close):
            continue

        try:
            candles.append({
                'time': ts.isoformat(),
                'o': round(float(row['Open']),  2),
                'h': round(float(row['High']),  2),
                'l': round(float(row['Low']),   2),
                'c': round(float(row['Close']), 2),
                'v': int(float(row.get('Volume', 0))),
            })
        except Exception:
            continue

    print(f"  {target}: {len(candles)} velas 5m")
    entry = dict(lunes)
    entry['candles'] = candles
    result.append(entry)

os.makedirs('data/research', exist_ok=True)
OUT = 'data/research/lunes_5m_data.json'
with open(OUT, 'w') as f:
    json.dump(result, f, indent=2)

print(f"\n✅ Guardado: {OUT} | {sum(len(d['candles']) for d in result)} velas totales")
