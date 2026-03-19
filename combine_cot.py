import pandas as pd
import glob
import os

def process_cot_files():
    data_dir = r"c:\Users\FxDarvin\Desktop\PAgina\data\cot"
    files = glob.glob(os.path.join(data_dir, "cot_*.xls"))
    
    all_data = []
    
    for f in files:
        print(f"Processing {f}...")
        try:
            df = pd.read_excel(f)
            # Find NASDAQ rows
            nasdaq_df = df[df['Market_and_Exchange_Names'].str.contains('NASDAQ-100 Consolidated', na=False, case=False)]
            # Also look for mini if separate but consolidated usually has it
            
            # Select relevant columns
            # Report_Date_as_MM_DD_YYYY is the official date column in Financial reports
            cols = [
                'Report_Date_as_MM_DD_YYYY', 
                'Market_and_Exchange_Names',
                'Asset_Mgr_Positions_Long_All', 
                'Asset_Mgr_Positions_Short_All',
                'Lev_Money_Positions_Long_All', 
                'Lev_Money_Positions_Short_All',
                'Dealer_Positions_Long_All', 
                'Dealer_Positions_Short_All'
            ]
            
            # Check which columns exist (sometimes names vary slightly)
            available_cols = [c for c in cols if c in df.columns]
            
            if not nasdaq_df.empty:
                nasdaq_df = nasdaq_df[available_cols]
                all_data.append(nasdaq_df)
                print(f"  Added {len(nasdaq_df)} rows from {f}")
            else:
                print(f"  No 'NASDAQ-100 Consolidated' found in {f}")
                
        except Exception as e:
            print(f"  Error processing {f}: {e}")
            
    if all_data:
        combined = pd.concat(all_data)
        # Convert date and sort
        combined['Report_Date_as_MM_DD_YYYY'] = pd.to_datetime(combined['Report_Date_as_MM_DD_YYYY'])
        combined = combined.sort_values(by='Report_Date_as_MM_DD_YYYY', ascending=True)
        
        # Save to a clean CSV
        output_path = r"c:\Users\FxDarvin\Desktop\PAgina\data\cot\nasdaq_cot_historical_study.csv"
        combined.to_csv(output_path, index=False)
        print(f"Saved combined data to {output_path}")
        return combined
    else:
        print("No data found to combine.")
        return None

if __name__ == "__main__":
    combined_df = process_cot_files()
    if combined_df is not None:
        print(combined_df.tail())
