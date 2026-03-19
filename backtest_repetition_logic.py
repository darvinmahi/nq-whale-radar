
import pandas as pd
import numpy as np
import os
from datetime import time

def run_study():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print("Data file not found.")
        return

    # Skip first 2 lines and use 3rd as header
    df = pd.read_csv(csv_path, skiprows=2)
    # The first column is 'Datetime'
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    days = df.index.normalize().unique()
    results = []

    for day in days:
        # Asia + London: 18:00 (prev day) to 09:25 (today)
        start_time = (day - pd.Timedelta(days=1)).replace(hour=18, minute=0)
        end_time = day.replace(hour=9, minute=25)
        
        pre_ny_data = df.loc[start_time:end_time]
        if len(pre_ny_data) < 10: continue

        # Simple POC estimation (most frequent price bucket)
        prices = pre_ny_data['Close']
        bins = np.linspace(prices.min(), prices.max(), 50)
        counts, edges = np.histogram(prices, bins=bins)
        poc = edges[np.argmax(counts)]
        
        # NY Open (9:30 - 11:30)
        ny_start = day.replace(hour=9, minute=30)
        ny_end = day.replace(hour=11, minute=30)
        ny_data = df.loc[ny_start:ny_end]
        if ny_data.empty: continue

        ny_open = ny_data.iloc[0]['Open']
        ny_low = ny_data['Low'].min()
        ny_high = ny_data['High'].max()
        ny_close = ny_data.iloc[-1]['Close']

        # Analysis
        is_bullish = ny_open > poc
        test_buffer = 25 # Increased buffer for NQ
        
        did_test_poc = ny_low <= (poc + test_buffer) if is_bullish else ny_high >= (poc - test_buffer)
        
        if did_test_poc:
            # Re-test scenario
            if is_bullish:
                p_type = "MAGNET_BUY" if ny_close > ny_open else "REVERSAL_FALL"
            else:
                p_type = "MAGNET_SELL" if ny_close < ny_open else "REVERSAL_RISE"
        else:
            # Runaway scenario
            p_type = "RUNAWAY_UP" if is_bullish else "RUNAWAY_DOWN"

        results.append({
            "date": day.date(),
            "p_type": p_type
        })

    # Stats
    pdf = pd.DataFrame(results)
    counts = pdf['p_type'].value_counts()
    total = len(pdf)
    stats = (counts / total) * 100
    
    print("\n" + "═"*60)
    print("  ESTUDIO DE REPETICIÓN: ASIA+LON -> NY OPEN (60 DÍAS)")
    print("═"*60)
    print(f"1. EFECTO IMÁN (Re-test POC + Continúa): {stats.get('MAGNET_BUY', 0) + stats.get('MAGNET_SELL', 0):.1f}%")
    print(f"2. EFECTO FUGA (No toca el POC y se va): {stats.get('RUNAWAY_UP', 0) + stats.get('RUNAWAY_DOWN', 0):.1f}%")
    print(f"3. FALLO DE NIVEL (Testea y Revierte):  {stats.get('REVERSAL_FALL', 0) + stats.get('REVERSAL_RISE', 0):.1f}%")
    
    # Save the study for the UI
    report = {
        "title": "Patrones de Apertura NY vs POC Asia/Lon",
        "days": total,
        "magnet_prob": f"{stats.get('MAGNET_BUY', 0) + stats.get('MAGNET_SELL', 0):.1f}%",
        "runaway_prob": f"{stats.get('RUNAWAY_UP', 0) + stats.get('RUNAWAY_DOWN', 0):.1f}%",
        "conclusion": "El Nasdaq tiene un sesgo de 'IMÁN' hacia el POC combinado en un " + f"{stats.get('MAGNET_BUY', 0) + stats.get('MAGNET_SELL', 0):.1f}%" + " de los días sugeridos.",
        "strategy": "Colocar órdenes limitadas en el POC combinado con stop bajo el VAL de Londres."
    }
    
    with open("data/research/repetition_study.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    run_study()
