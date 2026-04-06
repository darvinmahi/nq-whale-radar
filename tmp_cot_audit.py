import csv
from datetime import datetime

rows = []
all_cols = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    all_cols = reader.fieldnames
    for r in reader:
        try:
            d = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
            rows.append((d, r))
        except: pass
rows.sort(key=lambda x: x[0])

print('=== COLUMNAS DISPONIBLES ===')
for cat in ['NonComm','Lev_Money','Asset_Mgr','Dealer']:
    cols = [c for c in all_cols if cat in c and ('Long' in c or 'Short' in c) and 'Change' not in c and 'Old' not in c and 'Other' not in c]
    if cols:
        print(f'  {cat}: {cols}')

WINDOW = 52
lev_nets, am_nets = [], []
for d, r in rows:
    ll = int(r.get('Lev_Money_Positions_Long_All',0) or 0)
    ls = int(r.get('Lev_Money_Positions_Short_All',0) or 0)
    al = int(r.get('Asset_Mgr_Positions_Long_All',0) or 0)
    as_= int(r.get('Asset_Mgr_Positions_Short_All',0) or 0)
    lev_nets.append(ll-ls)
    am_nets.append(al-as_)

print()
print('=== VALORES REALES ULTIMAS 4 SEMANAS ===')
for i, (d, r) in enumerate(rows[-4:], start=len(rows)-4):
    ll = int(r.get('Lev_Money_Positions_Long_All',0) or 0)
    ls = int(r.get('Lev_Money_Positions_Short_All',0) or 0)
    al = int(r.get('Asset_Mgr_Positions_Long_All',0) or 0)
    as_= int(r.get('Asset_Mgr_Positions_Short_All',0) or 0)
    nl = int(r.get('NonComm_Positions_Long_All',0) or 0)
    ns = int(r.get('NonComm_Positions_Short_All',0) or 0)
    lev_net = ll-ls; am_net = al-as_; nc_net = nl-ns
    w = lev_nets[max(0,i-WINDOW+1):i+1]
    lev_idx = round((lev_net-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0
    w = am_nets[max(0,i-WINDOW+1):i+1]
    am_idx  = round((am_net-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0
    print(f'Semana {d}:')
    print(f'  Asset Mgr  L={al:>8,} S={as_:>8,} Net={am_net:>+9,} Index52w={am_idx:.1f}%')
    print(f'  Lev Money  L={ll:>8,} S={ls:>8,} Net={lev_net:>+9,} Index52w={lev_idx:.1f}%')
    print(f'  NonComm    L={nl:>8,} S={ns:>8,} Net={nc_net:>+9,} (LEGACY - mezcla de ambos)')
    print()

print('=== QUE ESTA MAL ===')
print('1. DATOS: Tenemos AM y LEV SEPARADOS (Disaggregated COT) OK')
print('2. VENTANA: 52 semanas (1 ano) usando historico desde 2022')
print()
print('3. ERROR LOGICO PRINCIPAL:')
print('   AM Net SIEMPRE positivo (+35k a +85k) = fondos de pension siempre compran NQ')
print('   AM_idx < 35% = comprando MENOS que el maximo, pero SIGUEN COMPRANDO')
print('   Por eso NQ sube 64% cuando score es bajo — aun hay flujo comprador neto')
print()
print('4. COMO ARREGLARLO:')
print('   Usar CAMBIO de AM (delta semanal), no nivel absoluto')
print('   Si AM_delta < -5000 contratos (liquidando) → señal bajista real')
am_prev = None
print()
print('=== AM DELTA ULTIMAS 8 SEMANAS (CAMBIO SEMANAL) ===')
for i, (d, r) in enumerate(rows[-8:], start=len(rows)-8):
    al = int(r.get('Asset_Mgr_Positions_Long_All',0) or 0)
    as_= int(r.get('Asset_Mgr_Positions_Short_All',0) or 0)
    am_net = al-as_
    if am_prev is not None:
        delta = am_net - am_prev
        print(f'  {d}: AM Net={am_net:>+9,}  DELTA={delta:>+8,}  {"LIQUIDANDO" if delta<-3000 else ("COMPRANDO" if delta>3000 else "ESTABLE")}')
    am_prev = am_net
