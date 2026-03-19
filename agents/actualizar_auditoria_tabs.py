import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def get_strategy(profile):
    if profile == "MEGÁFONO": return "DEFENSIVO"
    if profile == "EXPAN_ALC": return "AGRESI/COMPRA"
    if profile == "EXPAN_BAJ": return "AGRESI/VENTA"
    if profile == "TRAMPA_BEAR": return "REV/COMPRA"
    if profile == "TRAMPA_BULL": return "REV/VENTA"
    return "WAIT/RANGO"

def get_news(d):
    day, month = d.day, d.month
    wd = d.weekday()
    # Noticias Marzo 2026
    if month == 3:
        if day == 6: return "🔴 NFP"
        if day in [10, 11]: return "🔴 CPI"
        if day == 18: return "🔴 FOMC"
        if day == 26: return "🔴 GDP/PCE"
    # Noticias Febrero 2026
    if month == 2:
        if day == 6: return "🔴 NFP"
        if day in [10, 11]: return "🔴 CPI"
        if day == 18: return "🔴 FOMC"
        if day == 26: return "🔴 GDP/PCE"
    return "⚪ -"

def audit_month(start, end):
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
            'VIX': vix_map.get(d, 22.0),
            'Profile': perf,
            'Strategy': get_strategy(perf),
            'Wom': (d.day - 1) // 7 + 1
        })
    return results

def generate_table_html(month_data, month_name):
    # Agrupar por semanas del mes
    weeks = {}
    for d in month_data:
        w = d['Wom']
        if w not in weeks: weeks[w] = []
        weeks[w].append(d)
    
    html = f'<div class="space-y-8">'
    titles = {1: "Semana 1: NFP", 2: "Semana 2: CPI", 3: "Semana 3: FOMC", 4: "Semana 4: GDP", 5: "Semana 5: Cierre"}
    
    for w_num in sorted(weeks.keys()):
        week = weeks[w_num]
        title = titles.get(w_num, f"Semana {w_num}")
        html += f'''
        <div class="glass-panel overflow-hidden border border-white/5">
            <div class="bg-white/5 px-4 py-2 border-b border-white/10 flex justify-between items-center">
                <span class="text-[10px] font-mono text-electric-cyan uppercase font-bold">{title}</span>
            </div>
            <table class="w-full text-left text-[10px] font-mono">
                <thead class="bg-black/20 text-data-gray uppercase">
                    <tr>
                        <th class="p-3">Fecha</th>
                        <th class="p-3 text-center">Dir</th>
                        <th class="p-3">Noticia</th>
                        <th class="p-3 text-center">VIX</th>
                        <th class="p-3">Estrategia</th>
                        <th class="p-3 text-right">Perfil</th>
                    </tr>
                </thead>
                <tbody>'''
        for d in week:
            dir_col = "text-emerald-400" if d['Dir']=="⬆️" else "text-risk-red" if d['Dir']=="⬇️" else "text-vibrant-blue"
            perf_col = "text-electric-cyan" if "EXPAN" in d['Profile'] else "text-risk-red" if "MEGÁ" in d['Profile'] else "text-vibrant-blue"
            html += f'''
                    <tr class="border-b border-white/5 hover:bg-white/5">
                        <td class="p-3 text-data-gray">{d['Date']}</td>
                        <td class="p-3 text-center {dir_col} font-bold">{d['Dir']}</td>
                        <td class="p-3 font-bold">{d['News']}</td>
                        <td class="p-3 text-center">{d['VIX']}</td>
                        <td class="p-3 text-white/60">{d['Strategy']}</td>
                        <td class="p-3 text-right {perf_col} font-bold italic">{d['Profile']}</td>
                    </tr>'''
        html += '</tbody></table></div>'
    html += '</div>'
    return html

print("📡 Auditando Marzo 2026...")
march_data = audit_month("2026-03-01", "2026-03-15")
print("📡 Auditando Febrero 2026 (Completo)...")
feb_data = audit_month("2026-02-01", "2026-03-01")

march_html = generate_table_html(march_data, "Marzo")
feb_html = generate_table_html(feb_data, "Febrero")

# Estructura de Pestañas
tabs_html = f'''
<div class="mb-12">
    <div class="flex gap-4 mb-8">
        <button onclick="showMonth('march')" id="btnMarch" class="px-6 py-2 rounded-full border border-electric-cyan bg-electric-cyan/20 text-electric-cyan text-xs font-bold uppercase tracking-widest transition-all">
            MARZO 2026 (Actual)
        </button>
        <button onclick="showMonth('february')" id="btnFeb" class="px-6 py-2 rounded-full border border-white/10 bg-white/5 text-data-gray text-xs font-bold uppercase tracking-widest hover:border-white/20 transition-all">
            FEBRERO 2026 (Atrás)
        </button>
    </div>

    <div id="month-march" class="tab-content">
        {march_html}
    </div>

    <div id="month-february" class="tab-content hidden">
        {feb_html}
    </div>
</div>

<script>
function showMonth(m) {{
    document.getElementById('month-march').classList.toggle('hidden', m !== 'march');
    document.getElementById('month-february').classList.toggle('hidden', m !== 'february');
    
    const btnM = document.getElementById('btnMarch');
    const btnF = document.getElementById('btnFeb');
    
    if(m === 'march') {{
        btnM.className = 'px-6 py-2 rounded-full border border-electric-cyan bg-electric-cyan/20 text-electric-cyan text-xs font-bold uppercase tracking-widest transition-all';
        btnF.className = 'px-6 py-2 rounded-full border border-white/10 bg-white/5 text-data-gray text-xs font-bold uppercase tracking-widest hover:border-white/20 transition-all';
    }} else {{
        btnF.className = 'px-6 py-2 rounded-full border border-vibrant-blue bg-vibrant-blue/20 text-vibrant-blue text-xs font-bold uppercase tracking-widest transition-all';
        btnM.className = 'px-6 py-2 rounded-full border border-white/10 bg-white/5 text-data-gray text-xs font-bold uppercase tracking-widest hover:border-white/20 transition-all';
    }}
}}
</script>
'''

target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analisis_promax.html")
with open(target_file, "r", encoding='utf-8') as f:
    full_content = f.read()

start_marker = '<div class="space-y-12">'
end_marker = '<!-- END AUDIT TABLES -->'
start_idx = full_content.find(start_marker)
end_idx = full_content.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_content = full_content[:start_idx] + tabs_html + "\n" + full_content[end_idx:]
    with open(target_file, "w", encoding='utf-8') as f:
        f.write(new_content)
    print("✅ Biblia de Datos actualizada con pestañas Marzo/Febrero.")
else:
    print("❌ Error: No se encontraron los marcadores.")
