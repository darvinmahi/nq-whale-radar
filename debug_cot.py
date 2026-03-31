"""Diagnose CFTC date format and column names"""
import requests, zipfile, io, csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

resp = requests.get('https://www.cftc.gov/files/dea/history/fut_fin_txt_2026.zip', timeout=90)
zf   = zipfile.ZipFile(io.BytesIO(resp.content))
fobj = zf.open(zf.namelist()[0])
reader = csv.DictReader(io.TextIOWrapper(fobj, encoding='utf-8', errors='replace'))
print("Columnas:", list(reader.fieldnames)[:10])
print()
for i, row in enumerate(reader):
    if 'NASDAQ-100 Consolidated' in row.get('Market_and_Exchange_Names',''):
        print("MUESTRA FILA NASDAQ:")
        for k in ['Report_Date_as_MM_DD_YYYY','As_of_Date_In_Form_YYMMDD',
                  'Lev_Money_Positions_Long_All','Lev_Money_Positions_Short_All']:
            print(f"  {k}: {row.get(k,'NO EXISTE')}")
        break
