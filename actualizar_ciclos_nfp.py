import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def get_nfp_weeks_1year():
    """
    Identifica las semanas completas de NFP (el viernes es el primer viernes del mes)
    de los últimos 12 meses.
    """
    nfp_weeks = []
    # Empezamos desde el mes actual y vamos hacia atrás
    curr = datetime.now()
    for _ in range(12):
        # Encontrar el primer viernes del mes
        first_day = curr.replace(day=1)
        # 0=Mon, 4=Fri
        days_to_friday = (4 - first_day.weekday() + 7) % 7
        first_friday = first_day + timedelta(days=days_to_friday)
        
        # La semana NFP es de ese lunes a ese viernes
        monday = first_friday - timedelta(days=4)
        nfp_weeks.append((monday.date(), first_friday.date()))
        
        # Siguiente mes atrás
        curr = (first_day - timedelta(days=1)).replace(day=1)
    return nfp_weeks

def get_strategy(profile):
    if profile == "MEGÁFONO": return "DEFENSIVO"
    if "EXPAN" in profile: return "AGRESIVO"
    if "TRAMPA" in profile: return "REVERSA"
    return "ESPERAR"

def run_nfp_backtest():
    nfp_periods = get_nfp_weeks_1year()
    print(f"📡 Analizando {len(nfp_periods)} ciclos de NFP (1 año)...")
    
    # Descargar datos
    all_start = nfp_periods[-1][0]
    all_end = nfp_periods[0][1] + timedelta(days=1)
    
    df = yf.download("NQ=F", start=all_start, end=all_end, interval="1h", progress=False)
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df.index = df.index.tz_convert('America/New_York')
    
    vxn = yf.download("^VXN", start=all_start, end=all_end, interval="1d", progress=False)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    vxn_map = {d.date(): round(float(v), 1) for d, v in vxn['Close'].items()}

    full_results = []
    
    for start_d, end_d in nfp_periods:
        week_results = []
        # Iterar por cada día de esa semana (Lun a Vie)
        for i in range(5):
            d = start_d + timedelta(days=i)
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
            
            if brk_hi and brk_lo: perf = "MEGÁFONO"
            elif brk_hi: perf = "EXPAN_ALC" if ny_close > l_hi else "TRAMPA_BULL"
            elif brk_lo: perf = "EXPAN_BAJ" if ny_close < l_lo else "TRAMPA_BEAR"
            else: perf = "RANGO"
            
            dir_icon = "⬆️" if ny_close > ny_open else "⬇️"
            if perf == "MEGÁFONO": dir_icon = "↕️"
            
            week_results.append({
                'Date': d.strftime('%Y-%m-%d'),
                'News': "🔴 NFP" if i == 4 else "⚪ -",
                'Dir': dir_icon,
                'VIX': vxn_map.get(d, 22.0),
                'Profile': perf,
                'Strategy': get_strategy(perf)
            })
        full_results.append(week_results)
    
    # Tomar los 4 ciclos más recientes para la web
    return full_results[:4]

def inject_nfp_to_html(all_weeks):
    html_blocks = []
    titles = [
        "Ciclo NFP: Marzo 2026",
        "Ciclo NFP: Febrero 2026",
        "Ciclo NFP: Enero 2026",
        "Ciclo NFP: Diciembre 2025"
    ]
    colors = ["electric-cyan", "vibrant-blue", "electric-cyan", "vibrant-blue"]

    for idx, week in enumerate(all_weeks):
        block = f'''
                <!-- CICLO NFP {idx} -->
                <div class="glass-panel overflow-hidden border border-white/5 shadow-2xl">
                    <div class="bg-white/5 px-6 py-3 border-b border-white/10 flex justify-between items-center">
                        <span class="text-xs font-mono text-{colors[idx]} uppercase font-bold tracking-widest">{titles[idx]}</span>
                        <span class="text-[10px] text-data-gray uppercase font-mono">Auditoría Semana 1 Real</span>
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
                                    <td class="p-4">{d['Strategy']}</td>
                                    <td class="p-4 text-right {perf_color} font-bold italic">{d['Profile']}</td>
                                </tr>'''
        block += '</tbody></table></div></div>'
        html_blocks.append(block)
    return "\n".join(html_blocks)

results = run_nfp_backtest()
final_html = inject_nfp_to_html(results)

target_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analisis_promax.html")
with open(target_file, "r", encoding='utf-8') as f:
    full_content = f.read()

marker_start = '<div class="space-y-12">'
marker_end = '<!-- END AUDIT TABLES -->'

start_idx = full_content.find(marker_start) + len(marker_start)
end_idx = full_content.find(marker_end)

if start_idx != -1 and end_idx != -1:
    content = full_content[:start_idx] + "\n" + final_html + "\n" + full_content[end_idx:]
    with open(target_file, "w", encoding='utf-8') as f:
        f.write(content)
    print("✅ Biblia de Datos actualizada con Ciclos NFP Reales.")
else:
    print("❌ Marcadores no encontrados.")
