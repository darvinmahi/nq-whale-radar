"""
update_cot.py — Descarga el COT más reciente de CFTC y actualiza el CSV local.
URL CFTC Financial Futures (Traders in Financial Futures):
  https://www.cftc.gov/files/dea/history/fut_fin_txt_{YYYY}.zip
"""
import requests, zipfile, io, csv, os, sys
from datetime import date

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

OUT_CSV  = 'data/cot/nasdaq_cot_historical.csv'
YEAR     = date.today().year
URL      = f'https://www.cftc.gov/files/dea/history/fut_fin_txt_{YEAR}.zip'
FALLBACK = f'https://www.cftc.gov/files/dea/history/fut_fin_txt_{YEAR-1}.zip'

# Palabras clave para filtrar NASDAQ en el reporte CFTC
NQ_KEYWORDS = [
    'NASDAQ 100 STOCK INDEX',   # Legacy COT: "NASDAQ 100 STOCK INDEX X $20"
    'NASDAQ-100',               # TFF report variant
    'E-MINI NASDAQ',            # Mini variant
    'NQ-100',                   # Alternative
]

FIELDS_NEEDED = [
    'Report_Date_as_MM_DD_YYYY',
    'Market_and_Exchange_Names',
    'Lev_Money_Positions_Long_All',
    'Lev_Money_Positions_Short_All',
]

def download_cot(url):
    print(f"Descargando: {url}")
    r = requests.get(url, timeout=60)
    if r.status_code != 200:
        raise Exception(f"HTTP {r.status_code}")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    # Buscar el archivo .txt dentro del ZIP
    txt_files = [n for n in z.namelist() if n.lower().endswith('.txt')]
    if not txt_files:
        raise Exception("No se encontró .txt en el ZIP")
    print(f"  Archivo en ZIP: {txt_files[0]}")
    return z.open(txt_files[0])

def parse_nq_rows(file_obj):
    rows = []
    reader = csv.DictReader(io.TextIOWrapper(file_obj, encoding='utf-8', errors='replace'))
    for r in reader:
        mkt = r.get('Market_and_Exchange_Names','')
        if any(k in mkt.upper() for k in NQ_KEYWORDS):
            # Verificar que tiene las columnas necesarias
            try:
                d_str = r['Report_Date_as_MM_DD_YYYY'].strip()
                ll    = int(r['Lev_Money_Positions_Long_All'])
                ls    = int(r['Lev_Money_Positions_Short_All'])
                rows.append({
                    'Report_Date_as_MM_DD_YYYY': d_str,
                    'Market_and_Exchange_Names':  mkt.strip(),
                    'Lev_Money_Positions_Long_All':  ll,
                    'Lev_Money_Positions_Short_All': ls,
                })
            except (KeyError, ValueError):
                continue
    return rows

def load_existing_dates():
    if not os.path.exists(OUT_CSV):
        return set()
    dates = set()
    with open(OUT_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            dates.add(r.get('Report_Date_as_MM_DD_YYYY','').strip())
    return dates

def main():
    # 1. Cargar fechas existentes
    existing = load_existing_dates()
    print(f"Fechas ya en CSV: {len(existing)}")
    if existing:
        print(f"  Última fecha: {max(existing)}")

    # 2. Descargar datos CFTC
    try:
        file_obj = download_cot(URL)
    except Exception as e:
        print(f"  Error con {YEAR}: {e}  — intentando {YEAR-1}...")
        file_obj = download_cot(FALLBACK)

    # 3. Parsear filas NASDAQ
    new_rows = parse_nq_rows(file_obj)
    print(f"Filas NASDAQ encontradas en CFTC: {len(new_rows)}")

    # 4. Filtrar solo las nuevas
    to_add = [r for r in new_rows if r['Report_Date_as_MM_DD_YYYY'] not in existing]
    print(f"Filas NUEVAS a agregar: {len(to_add)}")

    if not to_add:
        print("El CSV ya está actualizado.")
    else:
        # 5. Agregar al CSV
        os.makedirs('data/cot', exist_ok=True)
        file_exists = os.path.exists(OUT_CSV)
        with open(OUT_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS_NEEDED)
            if not file_exists:
                writer.writeheader()
            for r in sorted(to_add, key=lambda x: x['Report_Date_as_MM_DD_YYYY']):
                writer.writerow(r)
        print(f"✅ Se agregaron {len(to_add)} semanas nuevas al CSV.")

    # 6. Mostrar resultado final
    print("\n--- COT Index actualizado (ventana 3 años = 156 semanas) ---")
    rows = []
    with open(OUT_CSV, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                d  = r['Report_Date_as_MM_DD_YYYY'].strip()
                ll = int(r['Lev_Money_Positions_Long_All'])
                ls = int(r['Lev_Money_Positions_Short_All'])
                rows.append({'date': d, 'long': ll, 'short': ls, 'net': ll - ls})
            except: pass
    rows.sort(key=lambda x: x['date'])
    for i, r in enumerate(rows):
        hist = [x['net'] for x in rows[max(0, i-156):i+1]]
        mn, mx = min(hist), max(hist)
        r['ci'] = (r['net'] - mn) / (mx - mn) * 100 if mx > mn else 50.0

    print(f"  {'Fecha':<14} {'Net':>10} {'COT Index':>10}")
    print("  " + "-"*38)
    for r in rows[-6:]:
        print(f"  {r['date']:<14} {r['net']:>10,}   {r['ci']:>5.1f}%")

    last = rows[-1]
    print(f"\n  ► ULTIMO: {last['date']}  |  COT Index = {last['ci']:.1f}%  |  Net = {last['net']:,}")
    if last['ci'] < 30:   print("  ► Señal: MUY BEARISH")
    elif last['ci'] < 50: print("  ► Señal: BEARISH")
    elif last['ci'] < 70: print("  ► Señal: BULLISH")
    else:                  print("  ► Señal: MUY BULLISH")

if __name__ == '__main__':
    main()
