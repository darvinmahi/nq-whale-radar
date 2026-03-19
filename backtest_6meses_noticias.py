import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🚀 BACKTEST 6 MESES: IMPACTO DE NOTICIAS EN NASDAQ (NQ)")
print("="*80)

def get_data():
    raw = yf.download("NQ=F", period="180d", interval="1h", progress=False)
    if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
    raw.index = raw.index.tz_convert('America/New_York')
    return raw

def get_news_type(d):
    # Lógica simplificada de calendario económico histórico
    # Semana 1 Viernes: NFP
    # Semana 2 Martes/Miércoles: CPI
    # Semana 3 Miércoles: FOMC (aprox)
    # Semana 4 Jueves: GDP
    wom = (d.day - 1) // 7 + 1
    wd = d.weekday() # 0=Mon, 4=Fri
    
    if wom == 1 and wd == 4: return "NFP"
    if wom == 2 and (wd == 1 or wd == 2): return "CPI"
    if wom == 3 and wd == 2: return "FOMC"
    if wom == 4 and wd == 3: return "GDP"
    return "NONE"

raw = get_data()
raw['date'] = raw.index.date
raw['hour'] = raw.index.hour
dates = sorted(raw['date'].unique())

results = []

for d in dates:
    day_data = raw[raw['date'] == d]
    if day_data.empty: continue
    
    # Sesiones
    london = day_data[(day_data['hour'] >= 3) & (day_data['hour'] < 9)]
    ny = day_data[(day_data['hour'] >= 9) & (day_data['hour'] < 16)]
    
    if london.empty or ny.empty: continue
    
    l_hi, l_lo = float(london['High'].max()), float(london['Low'].min())
    l_range = l_hi - l_lo
    
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_range = ny_hi - ny_lo
    ny_open = float(ny.iloc[0]['Open'])
    ny_close = float(ny.iloc[-1]['Close'])
    
    # Identificar Perfil
    broke_hi = ny_hi > l_hi + 5
    broke_lo = ny_lo < l_lo - 5
    
    if broke_hi and broke_lo: profile = "MEGÁFONO"
    elif broke_hi: profile = "EXPAN_ALC" if ny_close > l_hi else "TRAMPA_BULL"
    elif broke_lo: profile = "EXPAN_BAJ" if ny_close < l_lo else "TRAMPA_BEAR"
    else: profile = "RANGO"
    
    news = get_news_type(d)
    
    # Reacción: multiplicador de volatilidad (NY Range / London Range)
    reaction = ny_range / l_range if l_range > 0 else 1.0
    
    results.append({
        'date': d,
        'news': news,
        'profile': profile,
        'ny_range': ny_range,
        'reaction': reaction,
        'direction': "UP" if ny_close > ny_open else "DOWN"
    })

df = pd.DataFrame(results)

# ANALISIS
print("\n📊 RESUMEN 6 MESES (DÍAS CON NOTICIA VS SIN NOTICIA)")
print("-" * 50)

# 1. Perfiles más comunes por noticia
for ntype in ["NFP", "CPI", "FOMC", "GDP", "NONE"]:
    sub = df[df['news'] == ntype]
    if sub.empty: continue
    count = len(sub)
    most_common = sub['profile'].value_counts().idxmax()
    pct_m_c = (sub['profile'].value_counts().max() / count) * 100
    avg_reac = sub['reaction'].mean()
    print(f"[{ntype}] ({count} días): Perfil dominante: {most_common} ({pct_m_c:.1f}%) | Volatilidad NY/Lon: {avg_reac:.2f}x")

# 2. Reacción del precio al resultado (Dirección)
print("\n📈 SESGO DE DIRECCIÓN EN DÍAS DE NOTICIA:")
for ntype in ["NFP", "CPI", "FOMC", "GDP"]:
    sub = df[df['news'] == ntype]
    ups = len(sub[sub['direction'] == "UP"])
    downs = len(sub[sub['direction'] == "DOWN"])
    print(f"[{ntype}]: {ups} Subidas / {downs} Bajadas")

# 3. Datos para el Manual
print("\n💡 CONCLUSIÓN PARA PROMAX:")
n_days = df[df['news'] != "NONE"]
mega_news = (len(n_days[n_days['profile'] == "MEGÁFONO"]) / len(n_days)) * 100
print(f"- Los días de noticia tienen un {avg_reac:.2f}x más de rango que Londres.")
print(f"- El {mega_news:.1f}% de los días de noticia terminan en MEGÁFONO (Barrida doble).")

with open("backtest_6meses_reporte.txt", "w", encoding='utf-8') as f:
    f.write(f"REPORTE 180 DÍAS NASDAQ - NOTICIAS\n")
    f.write(df.to_string())
