"""
update_cot_now.py — descarga CFTC 2026, actualiza el CSV, muestra COT Index 4 semanas
"""
import requests, zipfile, io, csv, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_CSV = 'data/cot/nasdaq_cot_historical.csv'
FIELDS  = ['Report_Date_as_MM_DD_YYYY','Market_and_Exchange_Names',
           'Lev_Money_Positions_Long_All','Lev_Money_Positions_Short_All']

# 1. Cargar fechas existentes
existing = set()
with open(OUT_CSV, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        existing.add(row.get('Report_Date_as_MM_DD_YYYY','').strip())
print(f"Fechas en CSV: {len(existing)} | Ultima: {max(existing)}")

# 2. Descargar CFTC 2026
print("Descargando CFTC 2026 (Traders in Financial Futures)...")
resp = requests.get('https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=90)
zf   = zipfile.ZipFile(io.BytesIO(resp.content))
fobj = zf.open(zf.namelist()[0])
reader = csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace'))

to_add = []
for row in reader:
    mkt = row.get('Market_and_Exchange_Names', '')
    if 'NASDAQ-100 Consolidated' not in mkt:
        continue
    d_str = row.get('Report_Date_as_MM_DD_YYYY', '').strip()
    if d_str in existing:
        continue
    try:
        ll = int(row['Lev_Money_Positions_Long_All'])
        ls = int(row['Lev_Money_Positions_Short_All'])
        to_add.append({
            'Report_Date_as_MM_DD_YYYY':    d_str,
            'Market_and_Exchange_Names':     mkt.strip(),
            'Lev_Money_Positions_Long_All':  ll,
            'Lev_Money_Positions_Short_All': ls,
        })
    except Exception as e:
        print(f"  skip {d_str}: {e}")

print(f"Nuevas filas a agregar: {len(to_add)}")
for r in sorted(to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY']):
    net = r['Lev_Money_Positions_Long_All'] - r['Lev_Money_Positions_Short_All']
    print(f"  {r['Report_Date_as_MM_DD_YYYY']}  L={r['Lev_Money_Positions_Long_All']:,}  S={r['Lev_Money_Positions_Short_All']:,}  Net={net:,}")

if to_add:
    with open(OUT_CSV, 'a', newline='', encoding='utf-8') as f2:
        w = csv.DictWriter(f2, fieldnames=FIELDS)
        for r in sorted(to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY']):
            w.writerow(r)
    print(f"\n✅ CSV actualizado con {len(to_add)} semanas nuevas.")
else:
    print("El CSV ya esta al dia o no habia data nueva.")

# 3. Recalcular COT Index 3 años y mostrar ultimas 4 semanas
print("\n--- COT Index (156 semanas) — ultimas 4 semanas ---")
rows = []
with open(OUT_CSV, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        try:
            d  = row['Report_Date_as_MM_DD_YYYY'].strip()
            ll = int(row['Lev_Money_Positions_Long_All'])
            ls = int(row['Lev_Money_Positions_Short_All'])
            rows.append({'date': d, 'long': ll, 'short': ls, 'net': ll - ls})
        except:
            pass

rows.sort(key=lambda x: x['date'])
for i, r in enumerate(rows):
    hist = [x['net'] for x in rows[max(0, i-156):i+1]]
    mn, mx = min(hist), max(hist)
    r['ci'] = (r['net'] - mn) / (mx - mn) * 100 if mx > mn else 50.0

print(f"  {'Fecha':<14} {'Long':>10} {'Short':>10} {'Net':>10} {'COT%':>7}")
print("  " + "-"*55)
for r in rows[-4:]:
    arrow = '↑' if r['net'] > rows[rows.index(r)-1]['net'] else '↓'
    print(f"  {r['date']:<14} {r['long']:>10,} {r['short']:>10,} {r['net']:>10,}  {r['ci']:>5.1f}% {arrow}")

last = rows[-1]
print(f"\n  ULTIMO: {last['date']}  |  COT Index = {last['ci']:.1f}%  |  Net = {last['net']:,}")
print(f"  {'MUY BEARISH (<30%)' if last['ci']<30 else 'BEARISH' if last['ci']<50 else 'BULLISH' if last['ci']<70 else 'MUY BULLISH'}")
