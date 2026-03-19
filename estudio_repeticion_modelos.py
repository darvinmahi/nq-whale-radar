import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def run_model_frequency_backtest():
    print("="*80)
    print("📊 ESTUDIO DE REPETICIÓN DE MODELOS - ÚLTIMO AÑO")
    print("="*80)
    
    # Descargar 1 año de datos 1h (Mínimo para identificar perfiles con precisión)
    print("📡 Descargando datos NQ=F (365 días)...")
    df = yf.download("NQ=F", period="1y", interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_convert('America/New_York')

    dates = sorted(list(set(df.index.date)))
    total_days = 0
    model_counts = {
        "MEGÁFONO": 0,
        "EXPAN_ALCISTA": 0,
        "EXPAN_BAJISTA": 0,
        "TRAMPA_BULL": 0,
        "TRAMPA_BEAR": 0,
        "RANGO/OTRO": 0
    }

    for d in dates:
        day_data = df[df.index.date == d].copy()
        if day_data.empty: continue
        
        day_data['hour'] = day_data.index.hour
        lon = day_data[(day_data['hour'] >= 3) & (day_data['hour'] < 9)]
        ny = day_data[(day_data['hour'] >= 9) & (day_data['hour'] < 16)]
        
        if lon.empty or ny.empty: continue
        
        l_hi, l_lo = float(lon['High'].max()), float(lon['Low'].min())
        ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
        ny_open = float(ny.iloc[0]['Open'])
        ny_close = float(ny.iloc[-1]['Close'])
        
        brk_hi = ny_hi > l_hi + 15
        brk_lo = ny_lo < l_lo - 15
        
        total_days += 1
        
        if brk_hi and brk_lo:
            model_counts["MEGÁFONO"] += 1
        elif brk_hi:
            if ny_close > l_hi:
                model_counts["EXPAN_ALCISTA"] += 1
            else:
                model_counts["TRAMPA_BULL"] += 1
        elif brk_lo:
            if ny_close < l_lo:
                model_counts["EXPAN_BAJISTA"] += 1
            else:
                model_counts["TRAMPA_BEAR"] += 1
        else:
            model_counts["RANGO/OTRO"] += 1

    print(f"\nTotal Sesiones Auditadas: {total_days}")
    print("-" * 40)
    for model, count in model_counts.items():
        pct = (count / total_days) * 100
        print(f"{model:15}: {count:3} veces ({pct:5.1f}%)")
    print("-" * 40)

if __name__ == "__main__":
    run_model_frequency_backtest()
