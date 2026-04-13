import csv
from datetime import datetime, timedelta, date

rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
            al = int(r.get('Asset_Mgr_Positions_Long_All',0) or 0)
            as_ = int(r.get('Asset_Mgr_Positions_Short_All',0) or 0)
            ll = int(r.get('Lev_Money_Positions_Long_All',0) or 0)
            ls = int(r.get('Lev_Money_Positions_Short_All',0) or 0)
            rows.append({'date':d,'am':al-as_,'lev':ll-ls})
        except: pass

rows.sort(key=lambda x: x['date'])
for i,w in enumerate(rows):
    w['am_d'] = w['am'] - rows[i-1]['am'] if i>0 else 0
    win = [x['lev'] for x in rows[max(0,i-51):i+1]]
    mn,mx = min(win),max(win)
    w['lev_p'] = round((w['lev']-mn)/(mx-mn)*100,1) if mx!=mn else 50

print('Ultimas 8 semanas COT:')
print(f'{"Fecha":<14} {"AM Net":>10} {"AM Delta":>10} {"LEV Net":>10} {"LEV%":>7}  Signal')
for w in rows[-8:]:
    ad=w['am_d']; lp=w['lev_p']
    if   ad<-10000 and lp>60: sig='BEAR_STRONG'
    elif ad<-5000  and lp>60: sig='BEAR'
    elif ad>10000  and lp<40: sig='BULL_STRONG'
    elif ad>5000   and lp<40: sig='BULL'
    else:                      sig='NEUTRAL'
    print(f'{str(w["date"]):<14} {w["am"]:>10,} {w["am_d"]:>+10,} {w["lev"]:>10,} {lp:>7.1f}%  {sig}')

last = rows[-1]
ad=last['am_d']; lp=last['lev_p']
if   ad<-10000 and lp>60: sig='BEAR_STRONG'
elif ad<-5000  and lp>60: sig='BEAR'
elif ad>10000  and lp<40: sig='BULL_STRONG'
elif ad>5000   and lp<40: sig='BULL'
else:                      sig='NEUTRAL'

print(f'\nCOT mas reciente: {last["date"]}')
print(f'AM Net={last["am"]:,} | AM Delta={last["am_d"]:+,} | LEV%={lp:.1f}%')
print(f'Señal: {sig}')
print(f'Pub viernes: {last["date"]+timedelta(days=4)}')
print(f'Semana aplica: {last["date"]+timedelta(days=7)} al {last["date"]+timedelta(days=11)}')
