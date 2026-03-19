import yfinance as yf
import pandas as pd
ticker = "NQ=F"
df = yf.download(ticker, period="2y", interval="1h")
df.index = df.index.tz_convert('America/New_York')
df['hour'] = df.index.hour
df['date'] = df.index.date
groups = df.groupby('date').size()
print(groups.head(20))
print(f"Total days: {len(groups)}")
print(f"Days with >10 hours: {len(groups[groups > 10])}")
