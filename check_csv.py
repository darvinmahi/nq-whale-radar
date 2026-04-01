import csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8', errors='replace') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    rows = list(reader)

print(f'Total columnas: {len(cols)}')
print(f'Total filas: {len(rows)}')
print()

# Buscar columnas clave del reporte CLASICO COT
classic = [c for c in cols if any(k in c for k in ['NonComm','Comm_','NonRept','Open_Interest','Change'])]
print('=== Columnas COT Clasico ===')
for c in classic[:30]: print(' ', c)

print()
# Buscar columnas TFF
tff = [c for c in cols if any(k in c for k in ['Lev_Money','Asset_Mgr','Dealer','Other_Rept'])]
print('=== Columnas TFF (disaggregado) ===')
for c in tff[:20]: print(' ', c)

print()
# Mostrar ultima fila con datos clave
last = rows[-1]
print(f'=== Ultima fila: {last.get("Report_Date_as_YYYY-MM-DD", last.get("Report_Date_as_MM_DD_YYYY","?"))} ===')
for c in classic[:15]:
    print(f'  {c}: {last.get(c,"N/A")}')
