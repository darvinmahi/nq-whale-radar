import requests, zipfile, io, csv

url = 'https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip'
print("Descargando...")
r = requests.get(url, timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
print(f"HTTP {r.status_code}, {len(r.content)} bytes")

z = zipfile.ZipFile(io.BytesIO(r.content))
print("Archivos en ZIP:", z.namelist())

txt = z.open(z.namelist()[0])
reader = csv.DictReader(io.TextIOWrapper(txt, encoding='utf-8', errors='replace'))

NQ_KEYWORDS = ['NASDAQ 100 STOCK INDEX', 'NASDAQ-100', 'E-MINI NASDAQ', 'NQ-100']
found = []
for i, row in enumerate(reader):
    mkt = row.get('Market_and_Exchange_Names', '')
    if any(k in mkt.upper() for k in NQ_KEYWORDS):
        found.append(row)
        if len(found) == 1:
            print(f"\nColumnas disponibles: {list(row.keys())[:15]}...")
            print(f"Market: {mkt}")
            print(f"Report_Date: {row.get('Report_Date_as_MM_DD_YYYY','N/A')}")
            print(f"Lev_Long: {row.get('Lev_Money_Positions_Long_All','N/A')}")
            print(f"Asset_Mgr_Long: {row.get('Asset_Mgr_Positions_Long_All','N/A')}")

print(f"\n✅ Total filas NQ encontradas: {len(found)}")
if found:
    print(f"Última fecha: {found[-1].get('Report_Date_as_MM_DD_YYYY','?')}")
    net = int(found[-1].get('Lev_Money_Positions_Long_All',0)) - int(found[-1].get('Lev_Money_Positions_Short_All',0))
    print(f"Último LEV net: {net:+,}")
