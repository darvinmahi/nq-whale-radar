"""
repair_and_update_cot.py — repara las filas mal insertadas y agrega correctamente
las 3 semanas nuevas (2026-03-10, 17, 24) con todas las columnas del CSV.
"""
import requests, zipfile, io, csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_CSV = 'data/cot/nasdaq_cot_historical.csv'

# 1. Leer estructura del CSV (header + filas buenas)
with open(OUT_CSV, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    HEADERS = list(reader.fieldnames)
    all_rows = list(reader)

print(f"Columnas del CSV: {HEADERS}")
print(f"Total filas antes: {len(all_rows)}")

# 2. Quitar las 3 filas malas (donde Lev_Money_Long es None o vacío)
good_rows = [r for r in all_rows if (r.get('Lev_Money_Positions_Long_All') or '').strip()]
bad_count = len(all_rows) - len(good_rows)
print(f"Filas malas eliminadas: {bad_count}  |  Filas buenas: {len(good_rows)}")

existing_dates = set(r['Report_Date_as_MM_DD_YYYY'].strip() for r in good_rows)
print(f"Ultima fecha valida: {max(existing_dates)}")

# 3. Descargar CFTC 2026
print("Descargando CFTC 2026...")
resp = requests.get('https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=90)
zf   = zipfile.ZipFile(io.BytesIO(resp.content))
fobj = zf.open(zf.namelist()[0])
cftc_reader = csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace'))
CFTC_HEADERS = list(cftc_reader.fieldnames)
print(f"Columnas CFTC: {CFTC_HEADERS[:8]}...")

to_add = []
for row in cftc_reader:
    mkt = row.get('Market_and_Exchange_Names', '')
    if 'NASDAQ-100 Consolidated' not in mkt:
        continue
    d_str = row.get('Report_Date_as_YYYY-MM-DD', '').strip()
    if not d_str or d_str in existing_dates:
        continue
    # Construir fila con el mismo esquema que el CSV local
    new_row = {h: '' for h in HEADERS}
    new_row['Report_Date_as_MM_DD_YYYY']    = d_str
    new_row['Market_and_Exchange_Names']     = mkt.strip()
    # Copiar columnas que coincidan entre CFTC y nuestro CSV
    for h in HEADERS:
        if h in row and h != 'Report_Date_as_MM_DD_YYYY':
            new_row[h] = row[h]
    # Asegurarse de que Lev_Money columnas estén bien
    new_row['Lev_Money_Positions_Long_All']  = row.get('Lev_Money_Positions_Long_All','').strip()
    new_row['Lev_Money_Positions_Short_All'] = row.get('Lev_Money_Positions_Short_All','').strip()
    to_add.append(new_row)

print(f"Semanas nuevas a agregar: {len(to_add)}")
for r in sorted(to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY']):
    ll = int(r['Lev_Money_Positions_Long_All'] or 0)
    ls = int(r['Lev_Money_Positions_Short_All'] or 0)
    print(f"  {r['Report_Date_as_MM_DD_YYYY']}  L={ll:,}  S={ls:,}  Net={ll-ls:,}")

# 4. Reescribir CSV completo ordenado
final_rows = sorted(good_rows + to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY'])
with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f2:
    w = csv.DictWriter(f2, fieldnames=HEADERS)
    w.writeheader()
    w.writerows(final_rows)
print(f"\n✅ CSV reescrito: {len(final_rows)} filas totales.")

# 5. COT Index — ultimas 4 semanas
print("\n━━━ COT Index (156 semanas / 3 años) — ultimas 4 semanas ━━━")
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

print(f"  {'Semana':<14} {'Long':>9} {'Short':>9} {'Net':>9}  {'COT%':>7}  WoW")
print("  " + "─"*58)
last4 = rows[-4:]
for i, r in enumerate(last4):
    delta = r['net'] - last4[i-1]['net'] if i > 0 else 0
    arrow = '↑' if delta > 0 else ('↓' if delta < 0 else '─')
    print(f"  {r['date']:<14} {r['long']:>9,} {r['short']:>9,} {r['net']:>9,}  {r['ci']:>5.1f}%  {arrow}{abs(delta):,.0f}")

last = rows[-1]
print(f"\n  ► ULTIMO CFTC: {last['date']}")
print(f"  ► COT Index  : {last['ci']:.1f}%  |  Net = {last['net']:,}")
if   last['ci'] < 25: print("  ► 🔴🔴 MUY BEARISH")
elif last['ci'] < 45: print("  ► 🔴 BEARISH")
elif last['ci'] < 60: print("  ► 🟡 NEUTRAL")
elif last['ci'] < 80: print("  ► 🟢 BULLISH")
else:                  print("  ► 🟢🟢 MUY BULLISH")
