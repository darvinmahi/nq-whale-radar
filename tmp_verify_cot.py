import csv, json, os
from datetime import datetime

rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
            ll = int(r.get('Lev_Money_Positions_Long_All',0) or 0)
            ls = int(r.get('Lev_Money_Positions_Short_All',0) or 0)
            al = int(r.get('Asset_Mgr_Positions_Long_All',0) or 0)
            as_= int(r.get('Asset_Mgr_Positions_Short_All',0) or 0)
            rows.append({'date':d,'lev_net':ll-ls,'am_net':al-as_})
        except: pass
rows.sort(key=lambda x: x['date'])

WIN = 52
for i,cr in enumerate(rows):
    w_lev = [x['lev_net'] for x in rows[max(0,i-WIN+1):i+1]]
    w_am  = [x['am_net']  for x in rows[max(0,i-WIN+1):i+1]]
    lev_idx = round((cr['lev_net']-min(w_lev))/(max(w_lev)-min(w_lev))*100,1) if max(w_lev)!=min(w_lev) else 50
    am_idx  = round((cr['am_net']-min(w_am))/(max(w_am)-min(w_am))*100,1) if max(w_am)!=min(w_am) else 50
    cr['lev_idx'] = lev_idx
    cr['am_idx']  = am_idx
    cr['triple']  = round(am_idx*0.50 + lev_idx*0.35 + 50*0.15, 1)

print("Fecha        LEV_net    AM_net   LEV%   AM%    TRIPLE(AM.50+L.35)")
print("-"*72)
for cr in rows[-8:]:
    print(str(cr['date'])+"  "+str(cr['lev_net'])+"  "+str(cr['am_net'])+"  LEV="+str(cr['lev_idx'])+"  AM="+str(cr['am_idx'])+"  score="+str(cr['triple']))

last = rows[-1]
print()
print("=== ULTIMA SEMANA "+str(last['date'])+" ===")
print("  Dashboard muestra: COT 27.3/100")
print("  Mi triple score:  "+str(last['triple']))
print("  Solo LEV:         "+str(last['lev_idx']))
print("  Solo AM:          "+str(last['am_idx']))

# Ver como calcula el COT el agente
if os.path.exists('agent2_cot_analyst.py'):
    c = open('agent2_cot_analyst.py').read()
    # buscar la formula
    idx = c.find('score')
    if idx >= 0:
        print()
        print("agent2_cot_analyst.py formula (contexto):")
        print(c[max(0,idx-200):idx+300])

# cot_data.js
if os.path.exists('cot_data.js'):
    c2 = open('cot_data.js').read()
    idx = c2.find('score')
    if idx >= 0:
        print()
        print("cot_data.js:")
        print(c2[max(0,idx-100):idx+300])
