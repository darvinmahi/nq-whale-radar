import yfinance as yf
import pandas as pd
ticker = "NQ=F"
df = yf.download(ticker, period="5d", interval="1h")
df.index = df.index.tz_convert('America/New_York')
df['hour'] = df.index.hour
df['date'] = df.index.date
today = df['date'].unique()[0]
day_df = df[df['date'] == today]
print(f"DAY: {today}")
print(day_df[['hour', 'Open', 'High', 'Low', 'Close']])
