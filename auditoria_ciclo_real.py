import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def get_last_4_full_weeks():
    # Obtener el último viernes o hoy
    end_date = datetime.now()
    # Retroceder hasta un lunes para tener semanas completas
    while end_date.weekday() != 0: # 0 = Lunes
        end_date -= timedelta(days=1)
    
    # Queremos 4 semanas completas (28 días) antes de ese lunes
    start_date = end_date - timedelta(weeks=4)
    return start_date, end_date + timedelta(days=5) # Hasta el viernes de la última semana

def get_news(d):
    # Lógica de calendario real por semana del mes
    day = d.day
    wom = (day - 1) // 7 + 1
    wd = d.weekday()
    if wom == 1 and wd == 4: return "🔴 NFP"
    if wom == 2 and (wd == 1 or wd == 2): return "🔴 CPI"
    if wom == 3 and wd == 2: return "🔴 FOMC"
    if wom == 4 and (wd == 3 or wd == 4): return "🔴 GDP/PCE"
    return "⚪ -"

def run_audit():
    start, end = get_last_4_full_weeks()
    print(f"📊 Auditando Ciclo Real de 4 Semanas: {start.date()} al {end.date()}")
    
    # Descargar datos 5m para máxima precisión
    df = yf.download("NQ=F", start=start, end=end, interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_convert('America/New_York')
    
    dates = sorted(list(set(df.index.date)))
    results = []
    
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
        
        # Perfiles
        brk_hi = ny_hi > l_hi + 5
        brk_lo = ny_lo < l_lo - 5
        
        if brk_hi and brk_lo: perf = "MEGÁFONO"
        elif brk_hi: perf = "EXPAN_ALC" if ny_close > l_hi else "TRAMPA_BULL"
        elif brk_lo: perf = "EXPAN_BAJ" if ny_close < l_lo else "TRAMPA_BEAR"
        else: perf = "RANGO"
        
        dir_icon = "⬆️" if ny_close > ny_open else "⬇️"
        if perf == "MEGÁFONO": dir_icon = "↕️"
        
        results.append({
            'Date': d.strftime('%Y-%m-%d'),
            'News': get_news(d),
            'Dir': dir_icon,
            'Profile': perf
        })
    
    return results

def format_html_table(audit_data):
    html = ""
    # Dividir en 4 bloques de 5 días (semanas)
    for i in range(0, len(audit_data), 5):
        week_num = (i // 5) + 1
        html += f'\n<!-- SEMANA {week_num} -->\n'
        week_days = audit_data[i:i+5]
        for day in week_days:
            color_class = "text-emerald-400" if day['Dir'] == "⬆️" else "text-risk-red" if day['Dir'] == "⬇️" else "text-vibrant-blue"
            html += f'''<tr>
                <td class="py-4 font-mono text-[10px] text-data-gray">{day['Date']}</td>
                <td class="py-4 text-center">{day['Dir']}</td>
                <td class="py-4 font-bold {color_class} text-[10px]">{day['News']}</td>
                <td class="py-4 text-right text-white font-bold italic text-[10px]">{day['Profile']}</td>
            </tr>\n'''
    return html

data = run_audit()
table_html = format_html_table(data)
print("\n✅ Auditoría completa. Generando HTML...")

# Guardar temporalmente para inspección
with open("temp_audit_table.txt", "w", encoding='utf-8') as f:
    f.write(table_html)
