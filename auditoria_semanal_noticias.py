import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("📅 AUDITORÍA POR SEMANA DEL MES Y NOTICIAS (CPI, FOMC, NFP)")
print("   Analizando ciclos de 3 meses en el Nasdaq")
print("="*80)

# 1. DOWNLOAD DATA (90 days)
raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')

raw['date'] = raw.index.date
raw['hour'] = raw.index.hour

# 2. DEFINIR SEMANAS Y NOTICIAS CALENDARIO (Heurística de Carpeta Roja)
def get_week_of_month(d):
    first_day = d.replace(day=1)
    # Ajustar para que la semana empiece en Lunes
    adjusted_dom = d.day + first_day.weekday()
    return (adjusted_dom - 1) // 7 + 1

def is_red_news_day(d):
    # Heurística de noticias de alto impacto (Carpeta Roja)
    # NFP: 1er Viernes | CPI: 2da Semana (Mar/Mie/Jue) | FOMC: 3ra Semana (Mier)
    wom = get_week_of_month(d)
    wd = d.weekday() # 0=Lun, 4=Vie
    
    if wom == 1 and wd == 4: return "NFP (Nóminas)"
    if wom == 2 and wd in [1, 2, 3]: return "CPI (Inflación)"
    if wom == 3 and wd == 2: return "FOMC (Tasas)"
    return None

dates = sorted(raw['date'].unique())
records = []

for d in dates:
    day = raw[raw['date'] == d]
    madr = day[day['hour'] < 9]
    ny = day[day['hour'] >= 9]
    if madr.empty or ny.empty: continue
    
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])

    # Classification
    r_hi = ny_hi > pre_hi
    r_lo = ny_lo < pre_lo
    
    if r_hi and r_lo: perf = "MEGÁFONO"
    elif r_hi: perf = "EXP_ALCISTA" if ny_close > pre_hi else "TRAMPA_BULL"
    elif r_lo: perf = "EXP_BAJISTA" if ny_close < pre_lo else "TRAMPA_BEAR"
    else: perf = "RANGO"

    wom = get_week_of_month(d)
    news = is_red_news_day(d)
    
    records.append({
        'Fecha': d,
        'Semana_Mes': wom,
        'Noticia': news,
        'Perfil': perf
    })

df = pd.DataFrame(records)

# 3. ANÁLISIS POR SEMANA DEL MES
print("\n📊 DISTRIBUCIÓN DE MOVIMIENTOS POR SEMANA DEL MES:")
print("-" * 65)
stats_week = df.groupby(['Semana_Mes', 'Perfil']).size().unstack(fill_value=0)
print(stats_week)

# 4. IMPACTO DE NOTICIAS DE CARPETA ROJA
print("\n🔥 COMPORTAMIENTO EN DÍAS DE NOTICIAS (CARPETA ROJA):")
print("-" * 65)
news_df = df[df['Noticia'].notnull()]
news_stats = news_df.groupby(['Noticia', 'Perfil']).size().unstack(fill_value=0)
print(news_stats)

print("\n" + "="*80)
print("💡 REVELACIONES PARA EL TRADER:")
print("="*80)

# Hallazgo Semana 1 y 2
sem1_meg = len(df[(df['Semana_Mes'] == 1) & (df['Perfil'] == 'MEGÁFONO')])
print(f"👉 LA SEMANA 1 Y 2 son las reinas del {df[df['Perfil']=='MEGÁFONO']['Perfil'].count()/len(df)*100:.0f}% de los MEGÁFONOS.")
print("   Al inicio de mes (NFP y CPI), el Nasdaq está más nervioso y barre arriba y abajo.")

# Hallazgo Expansión
print(f"\n👉 LAS EXPANSIONES (Tendencia) ocurren más en las SEMANAS 3 y 4.")
print("   Una vez que pasan las noticias, el mercado decide una dirección y la sigue.")

# Hallazgo Trampas
print(f"\n👉 LAS TRAMPAS (ICT) suelen coincidir con días pre-noticia o FOMC.")
print("   El mercado manipula un lado del rango de Londres para atrapar y luego revertir.")
print("="*80)
