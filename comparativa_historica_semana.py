import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_week_of_month(d):
    return (d.day - 1) // 7 + 1

def run_deep_comparison():
    now = datetime.now()
    # Identificar la semana actual (Mar 9-13, 2026 es Semana 2 del mes)
    current_wom = 2
    
    # Descargar datos históricos para los indicadores
    print("📡 Descargando datos históricos (6 meses)...")
    nq = yf.download("NQ=F", period="210d", interval="1h", progress=False)
    vxn = yf.download("^VXN", period="210d", interval="1d", progress=False)
    
    if isinstance(nq.columns, pd.MultiIndex): nq.columns = nq.columns.get_level_values(0)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    
    nq.index = nq.index.tz_convert('America/New_York')
    vxn_map = {d.date(): float(v) for d, v in vxn['Close'].items()}
    
    # Meses a comparar (Semana 2 de cada mes)
    months = []
    curr = datetime(2026, 3, 1)
    for _ in range(6):
        months.append((curr.year, curr.month))
        # Retroceder un mes
        curr = (curr.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    comparison = []
    
    for year, month in months:
        # Encontrar la semana 2 de ese mes
        first_day = datetime(year, month, 1)
        # Buscar el segundo lunes del mes
        lunes_count = 0
        target_week_days = []
        for d_off in range(31):
            target_d = first_day + timedelta(days=d_off)
            if target_d.month != month: break
            if target_d.weekday() == 0: # Lunes
                lunes_count += 1
            if lunes_count == 2: # Esta es la semana 2
                for i in range(5): # De lunes a viernes
                    target_week_days.append(target_d + timedelta(days=i))
                break
        
        month_name = datetime(year, month, 1).strftime('%B %Y')
        week_data = []
        
        for d in target_week_days:
            d_date = d.date()
            day_nq = nq[nq.index.date == d_date]
            if day_nq.empty: continue
            
            day_nq = day_nq.copy()
            day_nq['hour'] = day_nq.index.hour
            lon = day_nq[(day_nq['hour'] >= 3) & (day_nq['hour'] < 9)]
            ny = day_nq[(day_nq['hour'] >= 9) & (day_nq['hour'] < 16)]
            
            if lon.empty or ny.empty: continue
            
            l_hi, l_lo = float(lon['High'].max()), float(lon['Low'].min())
            ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
            ny_open = float(ny.iloc[0]['Open'])
            ny_close = float(ny.iloc[-1]['Close'])
            
            brk_hi = ny_hi > l_hi + 10
            brk_lo = ny_lo < l_lo - 10
            
            if brk_hi and brk_lo: perf = "MEGÁFONO"
            elif brk_hi: perf = "EXPAN_ALC" if ny_close > l_hi else "TRAMPA_BULL"
            elif brk_lo: perf = "EXPAN_BAJ" if ny_close < l_lo else "TRAMPA_BEAR"
            else: perf = "RANGO"
            
            week_data.append({
                "day": d.strftime('%a'),
                "vxn": vxn_map.get(d_date, 25.0),
                "perf": perf,
                "dir": "UP" if ny_close > ny_open else "DOWN"
            })
        
        comparison.append({"month": month_name, "days": week_data})
    
    return comparison

data = run_deep_comparison()

# REPORTE PARA EL USUARIO
print("\n" + "="*60)
print("🔍 COMPARATIVA HISTÓRICA: SEMANA 2 (CPI WEEK)")
print("="*60)

for month in data:
    print(f"\n📅 {month['month'].upper()}")
    print("-" * 60)
    for d in month['days']:
        print(f"{d['day']}: VXN: {d['vxn']:.1f} | Perfil: {d['perf']:12} | Dir: {d['dir']}")
    
    # Análisis de consistencia
    perfs = [d['perf'] for d in month['days']]
    megas = perfs.count("MEGÁFONO")
    print(f"👉 Resumen: {megas} Megáfonos detectados esta semana.")
