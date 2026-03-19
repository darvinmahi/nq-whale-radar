import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def get_strategy(profile):
    if profile == "MEGÁFONO": return "DEFENSIVO/BULL"
    if profile == "EXPAN_ALC": return "AGRESI/COMPRA"
    if profile == "EXPAN_BAJ": return "AGRESI/VENTA"
    if profile == "TRAMPA_BEAR": return "REV/COMPRA"
    if profile == "TRAMPA_BULL": return "REV/VENTA"
    return "WAIT/RANGO"

def get_news_feb(d):
    # Calendario real Febrero 2026
    # Sem 1 (Feb 2-6): NFP el Viernes 6
    # Sem 2 (Feb 9-13): CPI el Martes 10/Miércoles 11
    # Sem 3 (Feb 16-20): FOMC el Miércoles 18
    # Sem 4 (Feb 23-27): GDP el Jueves 26
    day = d.day
    wd = d.weekday()
    if day == 6: return "🔴 NFP"
    if day in [10, 11]: return "🔴 CPI"
    if day == 18: return "🔴 FOMC"
    if day == 26: return "🔴 GDP/PCE"
    return "⚪ -"

def run_full_month_audit():
    # Auditoría de FEBRERO 2026 (Mes Completo)
    start = "2026-02-01"
    end = "2026-03-01"
    
    print(f"📡 Auditeando Febrero 2026 Completo (Velas 5m)...")
    df = yf.download("NQ=F", start=start, end=end, interval="5m", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_convert('America/New_York')
    
    vxn = yf.download("^VXN", start=start, end=end, interval="1d", progress=False)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    vxn_map = {d.date(): round(float(v), 1) for d, v in vxn['Close'].items()}

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
            'News': get_news_feb(d),
            'Dir': dir_icon,
            'VIX': vxn_map.get(d, 22.0),
            'Profile': perf,
            'Strategy': get_strategy(perf),
            'Day': d.day
        })
    return results

def inject_to_html(audit_data):
    # Dividir en 4 semanas naturales de Febrero
    weeks = [
        [d for d in audit_data if 1 <= d['Day'] <= 8],   # Sem 1
        [d for d in audit_data if 9 <= d['Day'] <= 15],  # Sem 2
        [d for d in audit_data if 16 <= d['Day'] <= 22], # Sem 3
        [d for d in audit_data if 23 <= d['Day'] <= 31], # Sem 4
    ]
    
    titles = [
        "Semana 1: NFP Cycle (Feb 2-6)",
        "Semana 2: CPI Cycle (Feb 9-13)",
        "Semana 3: FOMC Cycle (Feb 16-20)",
        "Semana 4: GDP & Cierre (Feb 23-27)"
    ]
    subtitles = ["Tendencia Inicial", "Zona Megáfonos", "Limpieza Fed", "Flujo Final"]
    colors = ["electric-cyan", "risk-red", "vibrant-blue", "data-gray"]

    html_blocks = []
    for idx, week in enumerate(weeks):
        if not week: continue
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
            
            block += f'''
                                <tr class="border-b border-white/5 hover:bg-white/5">
                                    <td class="p-4">{d['Date']}</td>
                                    <td class="p-4 text-center {dir_color} font-bold">{d['Dir']}</td>
                                    <td class="p-4 text-center text-[10px] font-bold">{d['News']}</td>
                                    <td class="p-4 text-center">{d['VIX']}</td>
                                    <td class="p-4 font-bold text-white/50">{d['Strategy']}</td>
                                    <td class="p-4 text-right {perf_color} font-bold italic">{d['Profile']}</td>
                                </tr>'''
        block += '</tbody></table></div></div>'
        html_blocks.append(block)
    return "\n".join(html_blocks)

audit_data = run_full_month_audit()
final_html = inject_to_html(audit_data)

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
    print("✅ Auditoría de Mes Completo (Febrero 2026) inyectada correctamente.")
else:
    print("❌ Error: No se encontraron los marcadores en el HTML.")
