import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def get_last_4_full_weeks():
    end_date = datetime.now()
    while end_date.weekday() != 0: 
        end_date -= timedelta(days=1)
    start_date = end_date - timedelta(weeks=4)
    return start_date, datetime.now()

def get_news(d):
    day = d.day
    wom = (day - 1) // 7 + 1
    wd = d.weekday()
    if wom == 1 and wd == 4: return "🔴 NFP"
    if wom == 2 and (wd == 1 or wd == 2): return "🔴 CPI"
    if wom == 3 and wd == 2: return "🔴 FOMC"
    if wom == 4 and (wd == 3 or wd == 4): return "🔴 GDP/PCE"
    return "⚪ -"

def get_strategy(profile):
    if profile == "MEGÁFONO": return "DEFENSIVO/BULL"
    if profile == "EXPAN_ALC": return "AGRESI/COMPRA"
    if profile == "EXPAN_BAJ": return "AGRESI/VENTA"
    if profile == "TRAMPA_BEAR": return "REV/COMPRA"
    if profile == "TRAMPA_BULL": return "REV/VENTA"
    return "WAIT/RANGO"

def run_audit():
    start, end = get_last_4_full_weeks()
    df = yf.download("NQ=F", start=start, end=end, interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_convert('America/New_York')
    
    vix = yf.download("^VIX", start=start, end=end, interval="1d", progress=False)
    if isinstance(vix.columns, pd.MultiIndex): vix.columns = vix.columns.get_level_values(0)
    vix_map = {d.date(): round(float(v), 1) for d, v in vix['Close'].items()}

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
            'VIX': vix_map.get(d, 25.0),
            'Profile': perf,
            'Strategy': get_strategy(perf)
        })
    return results

def inject_to_html(audit_data):
    weeks = []
    for i in range(0, len(audit_data), 5):
        weeks.append(audit_data[i:i+5])

    weeks = weeks[-4:]
    html_blocks = []
    titles = ["Semana 1: Expansión", "Semana 2: Megáfonos", "Semana 3: Manipulación", "Semana 4: Cierre"]
    subtitles = ["Tendencia", "Peligro Barrida", "Institucional", "Mensual"]
    colors = ["electric-cyan", "risk-red", "vibrant-blue", "data-gray"]

    for idx, week in enumerate(weeks):
        block = f'''
                <div class="glass-panel overflow-hidden border border-white/5 shadow-2xl">
                    <div class="bg-white/5 px-6 py-3 border-b border-white/10 flex justify-between items-center">
                        <span class="text-xs font-mono text-{colors[idx]} uppercase font-bold tracking-widest">{titles[idx]}</span>
                        <span class="text-[10px] text-data-gray uppercase font-mono">{subtitles[idx]}</span>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs font-mono">
                            <thead class="text-data-gray border-b border-white/5 uppercase bg-black/20">
                                <tr>
                                    <th class="p-4">Fecha</th>
                                    <th class="p-4 text-center">Dir</th>
                                    <th class="p-4 text-center">Noticia</th>
                                    <th class="p-4 text-center">VIX</th>
                                    <th class="p-4">Estrategia</th>
                                    <th class="p-4 text-right">Perfil</th>
                                </tr>
                            </thead>
                            <tbody class="text-white/80">'''
        
        for d in week:
            dir_color = "text-emerald-400" if d['Dir'] == "⬆️" else "text-risk-red" if d['Dir'] == "⬇️" else "text-vibrant-blue"
            perf_color = "text-electric-cyan" if "EXPAN" in d['Profile'] else "text-risk-red" if "MEGÁ" in d['Profile'] else "text-vibrant-blue"
            strat_color = "text-white/40" if "WAIT" in d['Strategy'] else "text-white font-bold"
            
            block += f'''
                                <tr class="border-b border-white/5 hover:bg-white/5">
                                    <td class="p-4">{d['Date']}</td>
                                    <td class="p-4 text-center {dir_color} font-bold">{d['Dir']}</td>
                                    <td class="p-4 text-center text-[10px] font-bold">{d['News']}</td>
                                    <td class="p-4 text-center">{d['VIX']}</td>
                                    <td class="p-4 {strat_color}">{d['Strategy']}</td>
                                    <td class="p-4 text-right {perf_color} font-bold italic">{d['Profile']}</td>
                                </tr>'''
        block += '</tbody></table></div></div>'
        html_blocks.append(block)
    return "\n".join(html_blocks)

audit_results = run_audit()
final_html = inject_to_html(audit_results)

target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analisis_promax.html")
with open(target_file, "r", encoding='utf-8') as f:
    full_content = f.read()

start_marker = '<div class="space-y-12">'
end_marker = '<!-- END AUDIT TABLES -->'
start_idx = full_content.find(start_marker) + len(start_marker)
end_idx = full_content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_content = full_content[:start_idx] + "\n" + final_html + "\n" + full_content[end_idx:]
    with open(target_file, "w", encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Biblia de Datos actualizada con Estrategia Aplicada.")
else:
    print("❌ No se encontraron los marcadores en el HTML.")
