import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("🔍 Generando Cuadro Comparativo de Noticias (6 Meses)...")

def get_data():
    d = yf.download("NQ=F", period="210d", interval="1h", progress=False)
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    d.index = d.index.tz_convert('America/New_York')
    return d

def get_news_type(d):
    wom = (d.day - 1) // 7 + 1
    wd = d.weekday()
    if wom == 1 and wd == 4: return "NFP"
    if wom == 2 and (wd == 1 or wd == 2): return "CPI"
    if wom == 3 and wd == 2: return "FOMC"
    if wom == 4 and (wd == 3 or wd == 4): return "GDP/PCE"
    return None

data = get_data()
all_dates = sorted(list(set(data.index.date)))

stats = {
    "NFP": {"count": 0, "expansions": 0, "reversals": 0, "vol": []},
    "CPI": {"count": 0, "expansions": 0, "reversals": 0, "vol": []},
    "FOMC": {"count": 0, "expansions": 0, "reversals": 0, "vol": []},
    "GDP/PCE": {"count": 0, "expansions": 0, "reversals": 0, "vol": []}
}

for d in all_dates:
    news = get_news_type(d)
    if not news: continue
    
    day_data = data[data.index.date == d]
    if day_data.empty: continue
    
    day_data['hour'] = day_data.index.hour
    lon = day_data[(day_data['hour'] >= 3) & (day_data['hour'] < 9)]
    ny = day_data[(day_data['hour'] >= 9) & (day_data['hour'] < 16)]
    
    if lon.empty or ny.empty: continue
    
    l_rng = lon['High'].max() - lon['Low'].min()
    ny_rng = ny['High'].max() - ny['Low'].min()
    
    ny_open = ny.iloc[0]['Open']
    ny_close = ny.iloc[-1]['Close']
    ny_hi = ny['High'].max()
    ny_lo = ny['Low'].min()
    
    stats[news]["count"] += 1
    stats[news]["vol"].append(ny_rng / (l_rng + 1e-9))
    
    # Efecto Post-Noticia (Simplificado)
    # Expansión: Si cierra cerca de un extremo de NY
    # Reversión/Megáfono: Si el precio toca ambos extremos o cierra en el centro tras gran movimiento
    if (ny_close > ny_hi - 0.2*ny_rng) or (ny_close < ny_lo + 0.2*ny_rng):
        stats[news]["expansions"] += 1
    else:
        stats[news]["reversals"] += 1

print("\n--- CUADRO COMPARATIVO HISTÓRICO (6 MESES) ---")
print("| Evento | Repeticiones | Volatilidad Promedio | Comportamiento Típico | Efecto Resultante |")
print("| :--- | :---: | :---: | :--- | :--- |")

for k, v in stats.items():
    avg_v = np.mean(v["vol"]) if v["vol"] else 0
    pattern = "EXPANSIÓN (Tendencia)" if v["expansions"] > v["reversals"] else "MEGÁFONO / RANGO"
    effect = "Continuación Diaria" if k == "NFP" else "Barrida de Stops"
    if k == "FOMC": effect = "Ruptura Explosiva"
    if k == "CPI": effect = "Caos Institucional"
    
    print(f"| {k:8} | {v['count']:12} | {avg_v:18.2f}x | {pattern:20} | {effect} |")

