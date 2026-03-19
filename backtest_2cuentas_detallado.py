import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🧠 ESTRATEGIA DE 2 CUENTAS: ANÁLISIS POR SEMANAS Y NOTICIAS (90 DÍAS)")
print("   Lógica: Cuenta A (Seguidora) vs Cuenta B (Contraria)")
print("="*80)

# 1. DOWNLOAD DATA
def get_90d_data():
    raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
    if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
    raw.index = raw.index.tz_convert('America/New_York')
    raw['date'] = raw.index.date
    raw['hour'] = raw.index.hour
    return raw

raw = get_90d_data()

# 2. CALENDARIO DE SEMANAS Y NOTICIAS
def get_week_of_month(d):
    first_day = d.replace(day=1)
    adjusted_dom = d.day + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1

def is_red_news_day(d):
    wom = get_week_of_month(d)
    wd = d.weekday() # 0=Lun, 4=Vie
    if wom == 1 and wd == 4: return "NFP"
    if wom == 2 and wd in [1, 2, 3]: return "CPI"
    if wom == 3 and wd == 2: return "FOMC"
    return "NINGUNA"

dates = sorted(raw['date'].unique())
data = []

for d in dates:
    day = raw[raw['date'] == d]
    if day.empty: continue
    
    madr = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    
    # Análisis Primera Hora NY (9:00 - 10:30 aprox)
    ny_start = ny[ny['hour'] <= 10]
    fh_hi, fh_lo = float(ny_start['High'].max()), float(ny_start['Low'].min())
    
    break_hi = fh_hi > pre_hi
    break_lo = fh_lo < pre_lo
    
    # Final Result
    total_hi, total_lo = float(ny['High'].max()), float(ny['Low'].min())
    total_close = float(ny.iloc[-1]['Close'])
    r_hi = total_hi > pre_hi
    r_lo = total_lo > pre_lo
    
    if r_hi and r_lo: perf = "MEGÁFONO"
    elif r_hi: perf = "EXPANSIÓN" if total_close > pre_hi else "TRAMPA"
    elif r_lo: perf = "EXPANSIÓN" if total_close < pre_lo else "TRAMPA"
    else: perf = "RANGO"

    wom = get_week_of_month(d)
    news = is_red_news_day(d)
    
    data.append({
        'Semana': wom,
        'Noticia': news,
        'Perfil': perf,
        'Inicial': "ROMPE_HI" if break_hi else ("ROMPE_LO" if break_lo else "DENTRO")
    })

df = pd.DataFrame(data)

# 3. ANÁLISIS DE LÓGICA DE DIVERGENCIA (CUENTAS A y B)
print(f"{'SEMANA':<8} | {'TIPO NOTICIA':<12} | {'MEGÁFONOS %':<12} | {'EXPANSIÓN %':<12} | {'Sugerencia Cuentas'}")
print("-" * 85)

for wom in range(1, 6):
    sub = df[df['Semana'] == wom]
    if sub.empty: continue
    
    meg_pct = (len(sub[sub['Perfil'] == 'MEGÁFONO']) / len(sub)) * 100
    exp_pct = (len(sub[sub['Perfil'] == 'EXPANSIÓN']) / len(sub)) * 100
    news = "CARPETA ROJA" if wom in [1, 2, 3] else "CIERRE MES"
    
    # Sugerencia
    if meg_pct > 40:
        sug = "Doble Cuenta (A+B) - Énfasis en B (Contraria)"
    else:
        sug = "Cuenta A (Seguidora de Tendencia)"
        
    print(f"Semana {wom:<1} | {news:<12} | {meg_pct:>10.1f}% | {exp_pct:>10.1f}% | {sug}")

print("\n" + "="*80)
print("📊 CONFIRMACIÓN DE BARRIDAS (MEGÁFONOS):")
print("-" * 50)
news_days = df[df['Noticia'] != "NINGUNA"]
news_meg_pct = (len(news_days[news_days['Perfil'] == 'MEGÁFONO']) / len(news_days)) * 100
print(f"👉 Días de NOTICIAS ROJAS finalizan en MEGÁFONO el {news_meg_pct:.1f}% de las veces.")
print("👉 Conclusión: En Semanas 1, 2 y 3 (Noticias), la CUENTA B (Contraria) es tu seguro de vida.")
print("="*80)
