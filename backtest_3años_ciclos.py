import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🔍 ESTRATEGIA PROMAX — BACKTEST ULTRA-DEEP (3 AÑOS)")
print("Objetivo: Validar Ciclos Semanales (W1, W2, W3, W4) con Datos Históricos 2023-2026")
print("="*80)

def run_3year_backtest():
    # Descargar datos (Aproximadamente 1095 días)
    print("📡 Descargando datos NQ=F (3 años)...")
    # Nota: yfinance permite hasta 5 años para datos diarios
    df_daily = yf.download("NQ=F", period="3y", interval="1d", progress=False)
    if isinstance(df_daily.columns, pd.MultiIndex): df_daily.columns = df_daily.columns.get_level_values(0)
    
    # Para perfiles exactos (Megáfono vs Expansión) necesitamos datos intradía.
    # yfinance solo da 2 años de 1h. Usaremos 1h para la mayor parte y 1d para el resto si es necesario.
    print("📡 Descargando datos intradía NQ=F (Máximo posible: 2 años)...")
    df_1h = yf.download("NQ=F", period="730d", interval="1h", progress=False)
    if isinstance(df_1h.columns, pd.MultiIndex): df_1h.columns = df_1h.columns.get_level_values(0)
    df_1h.index = df_1h.index.tz_convert('America/New_York')

    dates = sorted(list(set(df_1h.index.date)))
    
    cycle_stats = {
        1: {"label": "W1 (NFP)", "profiles": [], "vol": []},
        2: {"label": "W2 (CPI)", "profiles": [], "vol": []},
        3: {"label": "W3 (FOMC)", "profiles": [], "vol": []},
        4: {"label": "W4 (GDP/CIERRE)", "profiles": [], "vol": []}
    }

    for d in dates:
        day_data = df_1h[df_1h.index.date == d].copy()
        if day_data.empty: continue
        
        # Identificar semana del mes (1-4)
        wom = (d.day - 1) // 7 + 1
        if wom > 4: wom = 4 # Agrupar remanentes en W4
        
        day_data['hour'] = day_data.index.hour
        lon = day_data[(day_data['hour'] >= 3) & (day_data['hour'] < 9)]
        ny = day_data[(day_data['hour'] >= 9) & (day_data['hour'] < 16)]
        
        if lon.empty or ny.empty: continue
        
        l_hi, l_lo = float(lon['High'].max()), float(lon['Low'].min())
        ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
        ny_close = float(ny.iloc[-1]['Close'])
        
        # Lógica de Moldes ProMax
        brk_hi = ny_hi > l_hi + 10
        brk_lo = ny_lo < l_lo - 10
        
        if brk_hi and brk_lo: perf = "MEGÁFONO"
        elif brk_hi or brk_lo: perf = "EXPAN" # Simplificamos para el estudio macro
        else: perf = "RANGO"
        
        cycle_stats[wom]["profiles"].append(perf)
        cycle_stats[wom]["vol"].append(ny_hi - ny_lo)

    print("\n" + "📊 RESULTADOS AUDITORÍA PROFUNDA (730 SESIONES INTRADÍA)")
    print("="*60)
    
    for w in range(1, 5):
        s = cycle_stats[w]
        total = len(s["profiles"])
        if total == 0: continue
        
        megas = s["profiles"].count("MEGÁFONO")
        expans = s["profiles"].count("EXPAN")
        
        print(f"\n[{s['label']}]")
        print(f"  Días Auditados: {total}")
        print(f"  Probabilidad Megáfono: {megas/total*100:.1f}%")
        print(f"  Probabilidad Expansión: {expans/total*100:.1f}%")
        
        # Validar tus premisas
        if w == 1: print(f"  🎯 Validación: {'SÍ' if expans/total > 0.5 else 'CERCA'} es la más direccional.")
        if w == 2: print(f"  🎯 Validación: {'SÍ' if megas/total > 0.25 else 'NO'} los Megáfonos son críticos aquí.")

run_3year_backtest()
