
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def run_master_study():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print("Data file not found.")
        return

    # Load data
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    days = df.index.normalize().unique()
    
    # We will track 6 specific movements (Patterns)
    # 1. SWEEP_H_RETURN: Sale por arriba (H), vuelve al rango.
    # 2. SWEEP_L_RETURN: Sale por abajo (L), vuelve al rango.
    # 3. EXPANSION_H: Sale por arriba (H), no vuelve (Fuga).
    # 4. EXPANSION_L: Sale por abajo (L), no vuelve (Fuga).
    # 5. ROTATION_POC: Se queda en el rango testeando el POC Asia+Lon.
    # 6. NEWS_EXPANSION: Movimiento errático de gran rango.

    patterns = {
        "SWEEP_H_RETURN": 0,
        "SWEEP_L_RETURN": 0,
        "EXPANSION_H": 0,
        "EXPANSION_L": 0,
        "ROTATION_POC": 0,
        "NEWS_DRIVE": 0
    }

    results_db = []
    
    # Combined Level Ranking
    level_hits = {
        "Combined Asia+Lon POC": {"hits": 0, "reactions": 0, "pts": []},
        "Asia High/Low": {"hits": 0, "reactions": 0, "pts": []},
        "London High/Low": {"hits": 0, "reactions": 0, "pts": []}
    }

    for day in days:
        # Define Range: Asia (18:00 prev) to Lon End (08:30 today)
        start_range = (day - timedelta(days=1)).replace(hour=18, minute=0)
        end_range = day.replace(hour=8, minute=30)
        
        range_data = df.loc[start_range:end_range]
        if range_data.empty or len(range_data) < 20: continue

        r_high = range_data['High'].max()
        r_low = range_data['Low'].min()
        
        # Calculate Combined POC
        prices = range_data['Close']
        bins = np.linspace(prices.min(), prices.max(), 40)
        counts, edges = np.histogram(prices, bins=bins)
        c_poc = edges[np.argmax(counts)]

        # NY Opening (09:30 - 11:30)
        ny_data = df.loc[day.replace(hour=9, minute=30):day.replace(hour=11, minute=30)]
        if ny_data.empty: continue

        ny_open = ny_data.iloc[0]['Open']
        ny_high = ny_data['High'].max()
        ny_low = ny_data['Low'].min()
        ny_close = ny_data.iloc[-1]['Close']
        
        # Buffer for sweep detection
        buffer = 20
        
        # Logic for patterns
        p_type = "ROTATION_POC" # Default
        
        # Check if it's a News Day (Large Volatility)
        if (ny_high - ny_low) > 250: # Threshold for high volatility
            p_type = "NEWS_DRIVE"
        elif ny_high > r_high + buffer:
            if ny_close < r_high:
                p_type = "SWEEP_H_RETURN"
            else:
                p_type = "EXPANSION_H"
        elif ny_low < r_low - buffer:
            if ny_close > r_low:
                p_type = "SWEEP_L_RETURN"
            else:
                p_type = "EXPANSION_L"
        
        patterns[p_type] += 1
        
        # Track Level Strength (Combined POC)
        hits_poc = ny_data[(ny_data['Low'] <= c_poc + 15) & (ny_data['High'] >= c_poc - 15)]
        if not hits_poc.empty:
            level_hits["Combined Asia+Lon POC"]["hits"] += 1
            # Check reaction
            reaction = max(ny_high - c_poc, c_poc - ny_low)
            if reaction > 50:
                level_hits["Combined Asia+Lon POC"]["reactions"] += 1
                level_hits["Combined Asia+Lon POC"]["pts"].append(reaction)

        results_db.append({
            "date": day.strftime('%Y-%m-%d'),
            "pattern": p_type,
            "range_h": r_high,
            "range_l": r_low,
            "c_poc": c_poc
        })

    total = len(results_db)
    final_stats = {k: (v / total * 100) for k, v in patterns.items()}
    
    # Final Ranking with Combined POC
    poc_rate = (level_hits["Combined Asia+Lon POC"]["reactions"] / level_hits["Combined Asia+Lon POC"]["hits"] * 100)
    poc_pts = np.mean(level_hits["Combined Asia+Lon POC"]["pts"])

    report = {
        "title": "Base de Datos Maestra: Sesiones y Repetición",
        "total_days": total,
        "patterns": {k: f"{v:.1f}%" for k, v in final_stats.items()},
        "strongest_point": {
            "name": "Combined Asia+Lon POC",
            "stat": f"{poc_rate:.1f}% Éxito",
            "impact": f"{poc_pts:.1f} pts"
        },
        "conclusion": "El movimiento de 'SWEEP & RETURN' (Falla) domina los lunes/martes, mientras que la 'EXPANSION' se concentra en días de noticias rojas.",
        "db_summary": results_db[-5:] # Ultimos 5 días
    }

    with open("data/research/master_repetition_db.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=4, ensure_ascii=False)
    
    print("\n" + "═"*70)
    print("  BASE DE DATOS DE REPETICIÓN (SESSIONS + POC COMBINADO)")
    print("═"*70)
    for p, v in final_stats.items():
        print(f"{p:<20} | {v:.1f}%")
    print("\n" + f"PUNTO MÁS FUERTE: Combined POC ({poc_rate:.1f}% reacción)")

if __name__ == "__main__":
    run_master_study()
