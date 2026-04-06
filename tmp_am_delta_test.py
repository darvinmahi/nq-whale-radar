import csv, yfinance as yf, pandas as pd
from datetime import datetime, timedelta

rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = datetime.strptime(r['Report_Date_as_MM_DD_YYYY'], '%Y-%m-%d').date()
            al = int(r.get('Asset_Mgr_Positions_Long_All',0) or 0)
            as_= int(r.get('Asset_Mgr_Positions_Short_All',0) or 0)
            ll = int(r.get('Lev_Money_Positions_Long_All',0) or 0)
            ls = int(r.get('Lev_Money_Positions_Short_All',0) or 0)
            rows.append({'date':d,'am_net':al-as_,'lev_net':ll-ls})
        except: pass
rows.sort(key=lambda x: x['date'])

for i,r in enumerate(rows):
    r['am_delta'] = rows[i]['am_net'] - rows[i-1]['am_net'] if i>0 else 0
    w = [x['lev_net'] for x in rows[max(0,i-52+1):i+1]]
    r['lev_idx'] = round((r['lev_net']-min(w))/(max(w)-min(w))*100,1) if max(w)!=min(w) else 50.0

print("Descargando NQ semanal...")
nq = yf.download('NQ=F', period='5y', interval='1wk', auto_adjust=True, progress=False)
def col(df,c): return df[c].iloc[:,0] if isinstance(df.columns,pd.MultiIndex) else df[c]
nq_w = pd.DataFrame({'open':col(nq,'Open'),'close':col(nq,'Close')}).dropna()
nq_w.index = pd.to_datetime(nq_w.index).tz_localize(None)
nq_w['ret'] = (nq_w['close']-nq_w['open'])/nq_w['open']*100
nq_dates = nq_w.index.tolist()

def nq_next(cot_date):
    days = (7-cot_date.weekday())%7
    if days==0: days=7
    nm = pd.Timestamp(cot_date+timedelta(days=days))
    valid = [d for d in nq_dates if d >= nm-timedelta(days=3)]
    if not valid: return None,None
    nd = min(valid, key=lambda d: abs((d-nm).days))
    if abs((nd-nm).days)>5: return None,None
    ret = float(nq_w.loc[nd,'ret'])
    return ret, 'BULL' if ret>0.3 else ('BEAR' if ret<-0.3 else 'FLAT')

buckets = {'BIG_BUY':{'n':0,'bull':0,'bear':0,'rets':[]},
           'NEUTRAL':{'n':0,'bull':0,'bear':0,'rets':[]},
           'BIG_SELL':{'n':0,'bull':0,'bear':0,'rets':[]}}
results = []
for r in rows[52:]:
    ret, dr = nq_next(r['date'])
    if ret is None: continue
    if r['am_delta'] > 5000: b='BIG_BUY'
    elif r['am_delta'] < -10000: b='BIG_SELL'
    else: b='NEUTRAL'
    buckets[b]['n']+=1
    if dr=='BULL': buckets[b]['bull']+=1
    if dr=='BEAR': buckets[b]['bear']+=1
    buckets[b]['rets'].append(ret)
    results.append({'date':r['date'],'delta':r['am_delta'],'bucket':b,'ret':ret,'dir':dr,'lev_idx':r['lev_idx']})

print()
print('=== TEST AM DELTA → SEMANA SIGUIENTE NQ ===')
print(f'  {"Bucket":12}  {"N":>4}  {"BULL%":>6}  {"BEAR%":>6}  {"RetAvg":>8}  Veredicto')
print('  '+'-'*55)
for k,d in buckets.items():
    n=d['n']
    if n==0: continue
    bp=d['bull']/n*100; rp=d['bear']/n*100
    avg=sum(d['rets'])/n if d['rets'] else 0
    if k=='BIG_BUY': ok='✅OK' if bp>55 else '❌FALLA'
    elif k=='BIG_SELL': ok='✅OK' if rp>55 else '❌FALLA'
    else: ok='--'
    print(f'  {k:12}  {n:>4}  {bp:>5.0f}%  {rp:>5.0f}%  {avg:>+7.2f}%  {ok}')

print()
big_buy = [r for r in results if r['bucket']=='BIG_BUY']
big_sell= [r for r in results if r['bucket']=='BIG_SELL']
if big_buy:
    print(f'=== BIG_BUY (Delta >+5k) — {len(big_buy)} casos ===')
    for r in big_buy[-12:]:
        print(f'  {r["date"]}  delta={r["delta"]:>+8,}  NQ={r["ret"]:>+6.2f}%  {r["dir"]:5}  LEV={r["lev_idx"]:.0f}%')
    bb_wr = sum(1 for r in big_buy if r['dir']=='BULL')/len(big_buy)*100
    print(f'  → BULL winrate: {bb_wr:.0f}%')
if big_sell:
    print()
    print(f'=== BIG_SELL (Delta < -10k) — {len(big_sell)} casos ===')
    for r in big_sell[-12:]:
        print(f'  {r["date"]}  delta={r["delta"]:>+8,}  NQ={r["ret"]:>+6.2f}%  {r["dir"]:5}  LEV={r["lev_idx"]:.0f}%')
    bs_wr = sum(1 for r in big_sell if r['dir']=='BEAR')/len(big_sell)*100
    print(f'  → BEAR winrate: {bs_wr:.0f}%')
