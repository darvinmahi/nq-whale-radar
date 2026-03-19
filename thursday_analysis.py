import pandas as pd

df = pd.read_csv('daily_breakdown_trades.csv')
jue = df[df['weekday'] == 'Jueves']
buy  = jue[jue['direction'] == 'BUY']
sell = jue[jue['direction'] == 'SELL']
buy_c  = buy[buy['result'].isin(['WIN','LOSS'])]
sell_c = sell[sell['result'].isin(['WIN','LOSS'])]

print('='*55)
print('  JUEVES — 2 AÑOS (NQ Futures, sesión NY 9:30am-12pm)')
print('='*55)
print(f'\n  Total setups Jueves: {len(jue)} días')
print(f'\n  📈 COMPRAS (BUY):   {len(buy)} veces ({len(buy)/len(jue)*100:.0f}% de los Jueves)')
print(f'     ✅ Wins:   {len(buy_c[buy_c["result"]=="WIN"])}')
print(f'     ❌ Losses: {len(buy_c[buy_c["result"]=="LOSS"])}')
wr_buy = len(buy_c[buy_c["result"]=="WIN"])/len(buy_c)*100 if len(buy_c)>0 else 0
print(f'     WR: {wr_buy:.1f}%')
print(f'     PnL: {buy_c["pnl_pts"].sum():+.0f} pts (~${buy_c["pnl_pts"].sum()*20:+,.0f})')

print(f'\n  📉 VENTAS  (SELL):  {len(sell)} veces ({len(sell)/len(jue)*100:.0f}% de los Jueves)')
print(f'     ✅ Wins:   {len(sell_c[sell_c["result"]=="WIN"])}')
print(f'     ❌ Losses: {len(sell_c[sell_c["result"]=="LOSS"])}')
wr_sell = len(sell_c[sell_c["result"]=="WIN"])/len(sell_c)*100 if len(sell_c)>0 else 0
print(f'     WR: {wr_sell:.1f}%')
print(f'     PnL: {sell_c["pnl_pts"].sum():+.0f} pts (~${sell_c["pnl_pts"].sum()*20:+,.0f})')

print(f'\n  --- Por año ---')
jue2 = jue.copy()
jue2['year'] = pd.to_datetime(jue2['date']).dt.year
for yr, grp in jue2.groupby('year'):
    b = len(grp[grp['direction']=='BUY'])
    s = len(grp[grp['direction']=='SELL'])
    print(f'  {int(yr)}: BUY={b} | SELL={s} | Total={len(grp)} Jueves')

print(f'\n  VEREDICTO: {"SELL ✅" if wr_sell > wr_buy else "BUY ✅"} tiene mayor WR el Jueves')
