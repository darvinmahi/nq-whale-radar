import csv, os
csv_path = 'data/cot/nasdaq_cot_historical.csv'
if not os.path.exists(csv_path):
    print('ERROR: CSV no existe en', csv_path)
else:
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8')))
    dates = sorted([r['Report_Date_as_MM_DD_YYYY'] for r in rows])
    print('Filas totales:', len(rows))
    print('Ultima fecha CSV:', dates[-1] if dates else 'vacio')
    print('Primera fecha:', dates[0] if dates else 'vacio')
    for d in dates[-5:]:
        r = next(x for x in rows if x['Report_Date_as_MM_DD_YYYY']==d)
        net = int(r.get('Lev_Money_Positions_Long_All',0)) - int(r.get('Lev_Money_Positions_Short_All',0))
        print(' ', d, 'net='+str(net))
