"""
fix_and_update_cot.py — limpia filas sin fecha y descarga correctamente con
la columna real: Report_Date_as_YYYY-MM-DD
"""
import requests, zipfile, io, csv, sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_CSV = 'data/cot/nasdaq_cot_historical.csv'
FIELDS  = ['Report_Date_as_MM_DD_YYYY','Market_and_Exchange_Names',
           'Lev_Money_Positions_Long_All','Lev_Money_Positions_Short_All']

# 1. Leer CSV actual y eliminar filas con fecha vacía o inválida
print("Limpiando CSV...")
clean_rows = []
with open(OUT_CSV, encoding='utf-8') as f:
    for row in csv.DictReader(f):
        d = row.get('Report_Date_as_MM_DD_YYYY','').strip()
        if d and len(d) >= 8:   # fecha valida (YYYY-MM-DD tiene 10 chars)
            clean_rows.append(row)

print(f"  Filas validas: {len(clean_rows)}")
# Reescribir el CSV limpio
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=clean_rows[0].keys())
    w.writeheader()
    w.writerows(clean_rows)

existing = set(r['Report_Date_as_MM_DD_YYYY'].strip() for r in clean_rows)
print(f"  Ultima fecha en CSV: {max(existing)}")

# 2. Descargar CFTC 2026 con el nombre de columna correcto
print("Descargando CFTC 2026...")
resp = requests.get('https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=90)
zf   = zipfile.ZipFile(io.BytesIO(resp.content))
fobj = zf.open(zf.namelist()[0])
reader = csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace'))

to_add = []
for row in reader:
    mkt = row.get('Market_and_Exchange_Names', '')
    if 'NASDAQ-100 Consolidated' not in mkt:
        continue
    # ← columna correcta en el archivo CFTC 2026
    d_str = row.get('Report_Date_as_YYYY-MM-DD', '').strip()
    if not d_str or d_str in existing:
        continue
    try:
        ll = int(row['Lev_Money_Positions_Long_All'].strip())
        ls = int(row['Lev_Money_Positions_Short_All'].strip())
        to_add.append({
            'Report_Date_as_MM_DD_YYYY':    d_str,
            'Market_and_Exchange_Names':     mkt.strip(),
            'Lev_Money_Positions_Long_All':  ll,
            'Lev_Money_Positions_Short_All': ls,
        })
    except Exception as e:
        print(f"  skip {d_str}: {e}")

print(f"Nuevas semanas CFTC: {len(to_add)}")
for r in sorted(to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY']):
    net = r['Lev_Money_Positions_Long_All'] - r['Lev_Money_Positions_Short_All']
    print(f"  {r['Report_Date_as_MM_DD_YYYY']}  Long={r['Lev_Money_Positions_Long_All']:,}  Short={r['Lev_Money_Positions_Short_All']:,}  Net={net:,}")

if to_add:
    with open(OUT_CSV, 'a', newline='', encoding='utf-8') as f2:
        w2 = csv.DictWriter(f2, fieldnames=FIELDS)
        for r in sorted(to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY']):
            w2.writerow(r)
    print(f"\n✅ {len(to_add)} semanas nuevas agregadas.")

# 3. COT Index — ultimas 4 semanas
print("\n━━━ COT Index (ventana 3 años) — ultimas 4 semanas ━━━")
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

print(f"  {'Semana':<14} {'Long':>9} {'Short':>9} {'Net':>9}  {'COT%':>7}  Cambio")
print("  " + "─"*58)
for idx, r in enumerate(rows[-4:]):
    prev = rows[-(4-idx)-1] if idx > 0 else r
    delta_net = r['net'] - prev['net'] if idx > 0 else 0
    arrow = '↑' if delta_net > 0 else ('↓' if delta_net < 0 else '─')
    bar = '█' * int(r['ci']/10)
    print(f"  {r['date']:<14} {r['long']:>9,} {r['short']:>9,} {r['net']:>9,}  {r['ci']:>5.1f}%  {arrow} {delta_net:+,}")

last = rows[-1]
print(f"\n  ► ACTUAL: {last['date']}  COT Index = {last['ci']:.1f}%  Net = {last['net']:,}")
if   last['ci'] < 25: print("  ► 🔴🔴 MUY BEARISH — institucionales vendiendo fuerte")
elif last['ci'] < 45: print("  ► 🔴 BEARISH — posiciones en zona baja")
elif last['ci'] < 60: print("  ► 🟡 NEUTRAL")
elif last['ci'] < 80: print("  ► 🟢 BULLISH")
else:                  print("  ► 🟢🟢 MUY BULLISH")
