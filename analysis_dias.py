import pandas as pd

df = pd.read_csv('daily_breakdown_trades.csv')
orden = ['Lunes','Martes','Mi\u00e9rcoles','Jueves','Viernes']

SEP = '=' * 68

print(SEP)
print('  ANALISIS POR DIA DE SEMANA — NQ Nasdaq')
print('  Fuente: daily_breakdown_trades.csv (%d trades)' % len(df))
print(SEP)

for dia in orden:
    sub = df[df['weekday'] == dia]
    if sub.empty:
        continue
    total = len(sub)

    # BUY stats
    b = sub[sub['direction'] == 'BUY']
    s = sub[sub['direction'] == 'SELL']
    bw = len(b[b['result'] == 'WIN'])
    sw = len(s[s['result'] == 'WIN'])
    bwr = round(bw / len(b) * 100, 1) if len(b) else 0
    swr = round(sw / len(s) * 100, 1) if len(s) else 0
    b_avg = round(b[b['result']=='WIN']['pnl_pts'].mean(), 1) if bw else 0
    s_avg = round(s[s['result']=='WIN']['pnl_pts'].mean(), 1) if sw else 0
    b_loss_avg = round(b[b['result']=='LOSS']['pnl_pts'].mean(), 1) if len(b[b['result']=='LOSS']) else 0
    s_loss_avg = round(s[s['result']=='LOSS']['pnl_pts'].mean(), 1) if len(s[s['result']=='LOSS']) else 0

    # Sweep
    alto = len(sub[sub['sweep'] == 'ALTO'])
    bajo = len(sub[sub['sweep'] == 'BAJO'])

    # Uptrend
    up_pct = round(sub['uptrend'].sum() / total * 100, 1)

    # PnL total
    pnl_tot = round(sub['pnl_pts'].sum(), 1)

    dom_dir = 'BUY' if bwr > swr else 'SELL'
    dom_icon = 'LONG' if dom_dir == 'BUY' else 'SHORT'

    print()
    print('  %s  (%d trades | PnL total: %+.0f pts | Uptrend: %.0f%%)' % (dia.upper(), total, pnl_tot, up_pct))
    print('  ' + '-'*60)
    print('  %-8s %4d trades | WR: %5.1f%%  | Avg WIN: %+.0f | Avg LOSS: %+.0f' % ('BUY', len(b), bwr, b_avg, b_loss_avg))
    print('  %-8s %4d trades | WR: %5.1f%%  | Avg WIN: %+.0f | Avg LOSS: %+.0f' % ('SELL', len(s), swr, s_avg, s_loss_avg))
    print('  Sweep ALTO (short setup): %d  |  Sweep BAJO (long setup): %d' % (alto, bajo))
    print('  >> DIRECCION MAS RENTABLE: %s (%s)  WR=%.1f%%' % (dom_dir, dom_icon, max(bwr, swr)))

print()
print(SEP)
print('  TABLA RESUMEN — WIN RATE % por dia y direccion')
print(SEP)
print('  %-12s  %8s  %8s  %10s' % ('DIA', 'BUY WR%', 'SELL WR%', 'DOMINANTE'))
print('  ' + '-'*45)
for dia in orden:
    sub = df[df['weekday'] == dia]
    if sub.empty:
        continue
    b = sub[sub['direction'] == 'BUY']
    s = sub[sub['direction'] == 'SELL']
    bwr = round(len(b[b['result']=='WIN']) / len(b) * 100, 1) if len(b) else 0
    swr = round(len(s[s['result']=='WIN']) / len(s) * 100, 1) if len(s) else 0
    dom = 'BUY' if bwr > swr else 'SELL'
    print('  %-12s  %7.1f%%  %7.1f%%  %10s' % (dia, bwr, swr, dom))

print()
print(SEP)
print('  PATRON SWEEP por dia (ALTO=short / BAJO=long)')
print(SEP)
pt = df.groupby(['weekday','sweep']).size().unstack(fill_value=0).reindex(orden)
print(pt.to_string())
print()
