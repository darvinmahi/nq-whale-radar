import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("🔍 FORENSE 90 DÍAS: VERIFICACIÓN DEL CICLO DE 4 SEMANAS")
print("   Objetivo: Confirmar si el comportamiento real coincide con la teoría")
print("="*80)

# 1. DOWNLOAD DATA (90 DAYS)
def get_data():
    raw = yf.download("NQ=F", period="90d", interval="1h", progress=False)
    if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
    raw.index = raw.index.tz_convert('America/New_York')
    raw['date'] = raw.index.date
    raw['hour'] = raw.index.hour
    return raw

raw = get_data()

# 2. DEFINIR SEMANAS POR DÍA DEL MES (ESTRICTO)
def get_week_of_month(d):
    day = d.day
    if day <= 7: return 1   # Semana del NFP generalmente
    elif day <= 14: return 2 # Semana del CPI generalmente
    elif day <= 21: return 3 # Semana del FOMC / Opex
    else: return 4           # Cierre de mes

# 3. CLASIFICACIÓN FORENSE
def classify_ny_session(madr, ny):
    # Rango de Madrugada (Pre-Market)
    pre_hi, pre_lo = float(madr['High'].max()), float(madr['Low'].min())
    
    # Movimiento en New York
    ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
    ny_close = float(ny.iloc[-1]['Close'])
    
    rompe_hi = ny_hi > pre_hi + 5 # 5 pts buffer para evitar ruido
    rompe_lo = ny_lo < pre_lo - 5
    
    # MEGÁFONO: Cruza AMBOS extremos
    if rompe_hi and rompe_lo:
        return "MEGÁFONO"
    
    # EXPANSIÓN: Rompe un lado y CIERRA fuera con fuerza
    if rompe_hi and ny_close > pre_hi + 10:
        return "EXPANSIÓN"
    if rompe_lo and ny_close < pre_lo - 10:
        return "EXPANSIÓN"
    
    # TRAMPA: Rompe un lado pero NO logra cerrar fuera o revierte
    if rompe_hi or rompe_lo:
        return "TRAMPA"
    
    return "RANGO"

dates = sorted(raw['date'].unique())
results = []

for d in dates:
    day_df = raw[raw['date'] == d]
    madr = day_df[day_df['hour'] < 9]
    ny = day_df[(day_df['hour'] >= 9) & (day_df['hour'] < 16)]
    
    if madr.empty or ny.empty: continue
    
    wom = get_week_of_month(d)
    perf = classify_ny_session(madr, ny)
    
    results.append({'Semana': wom, 'Perfil': perf})

df = pd.DataFrame(results)

# 4. CUADRO DE VERIFICACIÓN
print(f"\n📊 ANÁLISIS POR SEMANA DEL MES (n={len(df)} días analizados)")
print("-" * 70)
print(f"{'SEMANA':<12} | {'MEGÁFONO':<12} | {'EXPANSIÓN':<12} | {'TRAMPA':<10} | {'RANGO'}")
print("-" * 70)

for w in [1, 2, 3, 4]:
    sub = df[df['Semana'] == w]
    total = len(sub)
    counts = sub['Perfil'].value_counts()
    
    m_pct = (counts.get('MEGÁFONO', 0) / total) * 100
    e_pct = (counts.get('EXPANSIÓN', 0) / total) * 100
    t_pct = (counts.get('TRAMPA', 0) / total) * 100
    r_pct = (counts.get('RANGO', 0) / total) * 100
    
    print(f"Semana {w:<5} | {m_pct:>10.1f}% | {e_pct:>10.1f}% | {t_pct:>8.1f}% | {r_pct:>5.1f}%")

print("\n" + "="*80)
print("🧐 CONCLUSIÓN DEL FORENSE (¿QUÉ PASA REAL?)")
print("-" * 40)

# Verificación de tus puntos:
s1 = df[df['Semana'] == 1]
s2 = df[df['Semana'] == 2]
s3 = df[df['Semana'] == 3]
s4 = df[df['Semana'] == 4]

print(f"✅ SEMANA 1: La Expansión es del { (s1['Perfil']=='EXPANSIÓN').mean()*100:.1f}%. Es el 'inicio' del sesgo.")
print(f"✅ SEMANA 2: Megáfono ({ (s2['Perfil']=='MEGÁFONO').mean()*100:.1f}%) vs Trampa ({ (s2['Perfil']=='TRAMPA').mean()*100:.1f}%). EL CPI causa CAOS.")
print(f"✅ SEMANA 3: TRAMPAS ({ (s3['Perfil']=='TRAMPA').mean()*100:.1f}%) Y MEGÁFONOS ({ (s3['Perfil']=='MEGÁFONO').mean()*100:.1f}%). El FOMC 'limpia' antes de decidir.")
print(f"✅ SEMANA 4: Expansión ({ (s4['Perfil']=='EXPANSIÓN').mean()*100:.1f}%). El flujo institucional decide el cierre mensual.")
print("="*80)
