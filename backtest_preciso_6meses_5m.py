import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🚀 BACKTEST 6 MESES (PRECISIÓN 5M + 1H): IMPACTO NOTICIAS")
print("="*80)

def get_data_hybrid():
    print("📡 Descargando 5m (60 días)...")
    d5 = yf.download("NQ=F", period="60d", interval="5m", progress=False)
    if isinstance(d5.columns, pd.MultiIndex): d5.columns = d5.columns.get_level_values(0)
    d5.index = d5.index.tz_convert('America/New_York')
    
    print("📡 Descargando 1h (210 días)...")
    d1h = yf.download("NQ=F", period="210d", interval="1h", progress=False)
    if isinstance(d1h.columns, pd.MultiIndex): d1h.columns = d1h.columns.get_level_values(0)
    d1h.index = d1h.index.tz_convert('America/New_York')
    
    return d5, d1h

def get_news_type(d):
    wom = (d.day - 1) // 7 + 1
    wd = d.weekday()
    if wom == 1 and wd == 4: return "🔴 NFP"
    if (wom == 2 and (wd == 1 or wd == 2)): return "🔴 CPI"
    if (wom == 3 and wd == 2): return "🔴 FOMC"
    if (wom == 4 and (wd == 3 or wd == 4)): return "🔴 GDP/PCE"
    return "⚪ -"

d5, d1h = get_data_hybrid()
all_dates = sorted(list(set(d1h.index.date)))
cutoff_5m = d5.index.date.min()

results = []

for d in all_dates:
    is_5m = d >= cutoff_5m
    day_source = d5[d5.index.date == d].copy() if is_5m else d1h[d1h.index.date == d].copy()
    
    if day_source.empty: continue
    day_source['hour'] = day_source.index.hour
    
    london = day_source[(day_source['hour'] >= 3) & (day_source['hour'] < 9)]
    ny = day_source[(day_source['hour'] >= 9) & (day_source['hour'] < 16)]
    
    if london.empty or ny.empty: continue
    
    l_hi, l_lo = float(london['High'].max()), float(london['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_open = float(ny.iloc[0]['Open'])
    ny_close = float(ny.iloc[-1]['Close'])
    
    brk_hi = ny_hi > l_hi + 5
    brk_lo = ny_lo < l_lo - 5
    
    if brk_hi and brk_lo: perf = "MEGÁFONO"
    elif brk_hi: perf = "EXPAN_ALC" if ny_close > l_hi else "TRAMPA_BULL"
    elif brk_lo: perf = "EXPAN_BAJ" if ny_close < l_lo else "TRAMPA_BEAR"
    else: perf = "RANGO"
    
    news = get_news_type(d)
    results.append({
        'Date': d.strftime('%Y-%m-%d'),
        'News': news,
        'Vol': round( (ny_hi-ny_lo)/(l_hi-l_lo+1e-9), 2),
        'Profile': perf,
        'Acc': "5M" if is_5m else "1H"
    })

df = pd.DataFrame(results)

print("\n📊 RESULTADOS POR NOTICIA (6 MESES):")
print("-" * 60)
for ntype in ["🔴 NFP", "🔴 CPI", "🔴 FOMC", "🔴 GDP/PCE"]:
    sub = df[df['News'] == ntype]
    if sub.empty: continue
    print(f"{ntype:12} | Vol Avg: {sub['Vol'].mean():.2f}x | Most Common: {sub['Profile'].value_counts().idxmax()}")

# GUARDAR SIN TABULATE
with open("estudio_6meses_5m_final.csv", "w", encoding='utf-8') as f:
    df.to_csv(f, index=False)
print("\n✅ Guardado: estudio_6meses_5m_final.csv")
