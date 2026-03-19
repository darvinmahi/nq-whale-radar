
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

def run_strength_study():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print("Data file not found. Run fetch_nq_intraday.py first.")
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
    
    # We will track hits and reactions for different levels
    # Levels: [Asia POC, London POC, Weekly POC, Prev Day High, Prev Day Low]
    level_stats = {
        "Asia POC": {"hits": 0, "reactions": 0, "bounce_avg": []},
        "London POC": {"hits": 0, "reactions": 0, "bounce_avg": []},
        "Weekly POC": {"hits": 0, "reactions": 0, "bounce_avg": []},
        "Prev Day High": {"hits": 0, "reactions": 0, "bounce_avg": []},
        "Prev Day Low": {"hits": 0, "reactions": 0, "bounce_avg": []},
    }

    # Buffer for "touching" a level
    buffer = 15 # NQ points
    reaction_min = 40 # Minimum movement for a "strong reaction"

    for i in range(5, len(days)): # Skip first 5 days for weekly baseline
        today = days[i]
        prev_day_data = df.loc[days[i-1].strftime('%Y-%m-%d')]
        weekly_data = df.loc[(today - timedelta(days=7)).strftime('%Y-%m-%d'):days[i-1].strftime('%Y-%m-%d')]
        
        # Calculate Levels
        pd_high = prev_day_data['High'].max()
        pd_low = prev_day_data['Low'].min()
        
        # Simple Weekly POC
        w_prices = weekly_data['Close']
        bins = np.linspace(w_prices.min(), w_prices.max(), 50)
        counts, edges = np.histogram(w_prices, bins=bins)
        w_poc = edges[np.argmax(counts)]

        # Session POCs (Asia 18:00-02:00, London 03:00-08:00)
        asia_data = df.loc[(today - timedelta(days=1)).replace(hour=18, minute=0):today.replace(hour=2, minute=0)]
        lon_data = df.loc[today.replace(hour=3, minute=0):today.replace(hour=8, minute=0)]
        
        def get_poc(data):
            if data.empty: return None
            p = data['Close']
            b = np.linspace(p.min(), p.max(), 30)
            c, e = np.histogram(p, bins=b)
            return e[np.argmax(c)]

        asia_poc = get_poc(asia_data)
        lon_poc = get_poc(lon_data)

        targets = {
            "Asia POC": asia_poc,
            "London POC": lon_poc,
            "Weekly POC": w_poc,
            "Prev Day High": pd_high,
            "Prev Day Low": pd_low
        }

        # NY Session (09:30 - 16:00)
        ny_data = df.loc[today.replace(hour=9, minute=30):today.replace(hour=16, minute=0)]
        
        for name, price in targets.items():
            if price is None: continue
            
            # Check for first touch
            # price is between low and high of a 15m bar
            touches = ny_data[(ny_data['Low'] <= price + buffer) & (ny_data['High'] >= price - buffer)]
            
            if not touches.empty:
                first_touch_idx = touches.index[0]
                level_stats[name]["hits"] += 1
                
                # Look at the next 2 hours for a reaction
                reaction_data = ny_data.loc[first_touch_idx : first_touch_idx + timedelta(hours=2)]
                if len(reaction_data) > 1:
                    # Search for max move away from level
                    # If we hit from above, look at peak bounce. If from below, peak drop.
                    # Simplified: absolute max distance reached vs price after touch
                    max_high = reaction_data['High'].max()
                    max_low = reaction_data['Low'].min()
                    
                    move_up = max_high - price
                    move_down = price - max_low
                    
                    best_move = max(move_up, move_down)
                    if best_move >= reaction_min:
                        level_stats[name]["reactions"] += 1
                        level_stats[name]["bounce_avg"].append(best_move)

    # FINAL RESULTS
    ranking = []
    for name, s in level_stats.items():
        rate = (s["reactions"] / s["hits"] * 100) if s["hits"] > 0 else 0
        avg_move = np.mean(s["bounce_avg"]) if s["bounce_avg"] else 0
        score = rate * (avg_move / 50) # Weighted score
        ranking.append({
            "level": name,
            "frequency": f"{rate:.1f}%",
            "avg_reaction": f"{avg_move:.1f} pts",
            "score": score,
            "raw_rate": rate
        })

    # Sort by score
    ranking = sorted(ranking, key=lambda x: x['score'], reverse=True)
    
    print("\n" + "═"*70)
    print("  ESTUDIO DE FORTALEZA DE NIVELES (REACCIÓN REAL 60 DÍAS)")
    print("═"*70)
    for i, r in enumerate(ranking):
        print(f"{i+1}. {r['level']:<15} | Éxito: {r['frequency']:<8} | Reacción: {r['avg_reaction']}")

    strongest = ranking[0]
    
    # Save to JSON
    report = {
        "title": "Jerarquía de Poder de Niveles",
        "strongest_level": strongest['level'],
        "success_rate": strongest['frequency'],
        "avg_bounce": strongest['avg_reaction'],
        "reasoning": f"El {strongest['level']} es el nivel con mayor 'poder de magnetismo y rechazo'. Cuando el precio lo toca, tiene un {strongest['frequency']} de probabilidad de reaccionar al menos {reaction_min} puntos.",
        "ranking": ranking
    }
    
    os.makedirs("data/research", exist_ok=True)
    with open("data/research/level_strength.json", "w", encoding="utf-8") as f:
        import json
        json.dump(report, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    run_strength_study()
