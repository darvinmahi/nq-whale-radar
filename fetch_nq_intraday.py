
import yfinance as yf
import pandas as pd
import os

def fetch_data():
    print("Fetching NQ 15m data for session profile analysis...")
    # NQ=F is Nasdaq Futures
    sym = "NQ=F"
    # period="60d" is the max for 15m
    df = yf.download(sym, period="60d", interval="15m")
    
    if df.empty:
        print("Error: No data found.")
        return
    
    output_path = "data/research/nq_15m_intraday.csv"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path)
    print(f"Success! Data saved to {output_path}")
    print(f"Total rows: {len(df)}")

if __name__ == "__main__":
    fetch_data()
