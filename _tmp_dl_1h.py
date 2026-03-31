import yfinance as yf, pandas as pd

df = yf.download('NQ=F', period='730d', interval='1h', auto_adjust=True)
df = df.reset_index()
df.columns = ['Datetime','Close','High','Low','Open','Volume']
df = df.sort_values('Datetime')

out = 'data/research/nq_15m_intraday.csv'
with open(out, 'w', newline='', encoding='utf-8') as f:
    f.write('Price,Close,High,Low,Open,Volume\n')
    f.write('Ticker,NQ=F,NQ=F,NQ=F,NQ=F,NQ=F\n')
    for _, row in df.iterrows():
        f.write("{},{},{},{},{},{}\n".format(
            row['Datetime'], row['Close'], row['High'],
            row['Low'], row['Open'], int(row['Volume'])))

print('Guardado en:', out)
print('Filas:', len(df))
print('Inicio:', df.iloc[0,0])
print('Fin:   ', df.iloc[-1,0])
thu = [d for d in df['Datetime'].dt.tz_localize(None).dt.normalize().unique() if d.weekday()==3]
print('Total jueves:', len(thu))
