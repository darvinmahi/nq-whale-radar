
import yfinance as yf
import json, sys
from datetime import datetime, timedelta

# Fetch 5min NQ for Mar 9, Mar 16, Mar 23 2026
# yfinance allows 60 days of 5min data
ticker = yf.Ticker("NQ=F")

dates = [
    ("2026-03-09", "2026-03-10"),
    ("2026-03-16", "2026-03-17"),
    ("2026-03-23", "2026-03-24"),
]

results = {}
for start, end in dates:
    df = ticker.history(start=start, end=end, interval="5m")
    if df.empty:
        print(f"WARNING: No data for {start}", file=sys.stderr)
        results[start] = []
        continue
    candles = []
    for ts, row in df.iterrows():
        t = int(ts.timestamp())
        candles.append({
            "time": t,
            "open": round(float(row["Open"]), 2),
            "high": round(float(row["High"]), 2),
            "low": round(float(row["Low"]), 2),
            "close": round(float(row["Close"]), 2),
            "volume": int(row["Volume"])
        })
    results[start] = candles
    print(f"{start}: {len(candles)} candles", file=sys.stderr)

print(json.dumps(results))
