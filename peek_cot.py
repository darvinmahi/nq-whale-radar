import pandas as pd
import sys

try:
    filepath = r'c:\Users\FxDarvin\Desktop\PAgina\data\cot\cot_2024.xls'
    print(f"Reading {filepath}...")
    df = pd.read_excel(filepath)
    print("Columns found:")
    print(df.columns.tolist())
    
    # Financial Traders Report column headers usually include things like 'Market_and_Exchange_Names'
    # Look for 'NASDAQ'
    print("Searching for 'NASDAQ' in data...")
    # Typically column 0 or 1 is the market name
    market_col = [col for col in df.columns if 'Market' in col or 'Name' in col]
    if market_col:
        matches = df[df[market_col[0]].str.contains('NASDAQ', na=False, case=False)]
        print(f"Found {len(matches)} rows matching 'NASDAQ'")
        print(matches[['Report_Date_as_MM_DD_YYYY', market_col[0], 'Asset_Mgr_Positions_Long_All', 'Asset_Mgr_Positions_Short_All', 'Lev_Money_Positions_Long_All', 'Lev_Money_Positions_Short_All']].head())
    else:
        print("Market column not found. Showing first 5 rows:")
        print(df.head())
        
except Exception as e:
    print(f"Error: {e}")
