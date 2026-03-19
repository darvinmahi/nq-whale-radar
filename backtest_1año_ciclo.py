import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("="*80)
print("🔍 ESTRATEGIA PROMAX — BACKTEST FORENSE 1 AÑO (365 DÍAS)")
print("Análisis de Ciclos Mensuales y Correlación con VXN")
print("="*80)

def get_data():
    print("📡 Descargando datos NQ=F y VXN (1 año)...")
    nq = yf.download("NQ=F", period="365d", interval="1h", progress=False)
    vxn = yf.download("^VXN", period="365d", interval="1d", progress=False)
    
    if isinstance(nq.columns, pd.MultiIndex): nq.columns = nq.columns.get_level_values(0)
    if isinstance(vxn.columns, pd.MultiIndex): vxn.columns = vxn.columns.get_level_values(0)
    
    nq.index = nq.index.tz_convert('America/New_York')
    vxn_map = {d.date(): float(v) for d, v in vxn['Close'].items()}
    return nq, vxn_map

def get_news_type(d):
    # Semana del mes (1-4)
    wom = (d.day - 1) // 7 + 1
    wd = d.weekday() # 0=Mon, 4=Fri
    if wom == 1 and wd == 4: return "🔴 NFP"
    if wom == 2 and (wd == 1 or wd == 2): return "🔴 CPI"
    if wom == 3 and wd == 2: return "🔴 FOMC"
    if wom == 4 and (wd == 3 or wd == 4): return "🔴 GDP/PCE"
    return "⚪ -"

def run_backtest():
    nq, vxn_map = get_data()
    dates = sorted(list(set(nq.index.date)))
    
    cycle_stats = {
        1: {"label": "Semana 1 (NFP)", "profiles": [], "vol": []},
        2: {"label": "Semana 2 (CPI)", "profiles": [], "vol": []},
        3: {"label": "Semana 3 (FOMC)", "profiles": [], "vol": []},
        4: {"label": "Semana 4 (GDP/Cierre)", "profiles": [], "vol": []}
    }
    
    results = []

    for d in dates:
        wom = (d.day - 1) // 7 + 1
        if wom > 4: continue # Agrupar semanas extras en la 4 para simplificar o ignorar
        
        day_nq = nq[nq.index.date == d].copy()
        if day_nq.empty: continue
        
        day_nq['hour'] = day_nq.index.hour
        lon = day_nq[(day_nq['hour'] >= 3) & (day_nq['hour'] < 9)]
        ny = day_nq[(day_nq['hour'] >= 9) & (day_nq['hour'] < 16)]
        
        if lon.empty or ny.empty: continue
        
        l_hi, l_lo = float(lon['High'].max()), float(lon['Low'].min())
        ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
        ny_open = float(ny.iloc[0]['Open'])
        ny_close = float(ny.iloc[-1]['Close'])
        
        l_rng = l_hi - l_lo
        ny_rng = ny_hi - ny_lo
        
        # Perfil (Precisión 1H)
        # Usamos un margen de 15 puntos para 1h
        brk_hi = ny_hi > l_hi + 15
        brk_lo = ny_lo < l_lo - 15
        
        if brk_hi and brk_lo: perf = "MEGÁFONO"
        elif brk_hi: perf = "EXPAN_ALC" if ny_close > l_hi else "TRAMPA_BULL"
        elif brk_lo: perf = "EXPAN_BAJ" if ny_close < l_lo else "TRAMPA_BEAR"
        else: perf = "RANGO"
        
        vix = vxn_map.get(d, 22.0)
        news = get_news_type(d)
        
        cycle_stats[wom]["profiles"].append(perf)
        cycle_stats[wom]["vol"].append(ny_rng / (l_rng + 1e-9))
        
        results.append({
            "Date": d,
            "Week": wom,
            "News": news,
            "VXN": vix,
            "Profile": perf,
            "Vol_Ratio": ny_rng / (l_rng + 1e-9)
        })

    print("\n" + "="*80)
    print("📊 RESULTADOS FINALES — 1 AÑO DE HISTÓRICO")
    print("="*80)
    
    for w in range(1, 5):
        s = cycle_stats[w]
        total = len(s["profiles"])
        if total == 0: continue
        
        megas = s["profiles"].count("MEGÁFONO")
        expans = s["profiles"].count("EXPAN_ALC") + s["profiles"].count("EXPAN_BAJ")
        trampas = s["profiles"].count("TRAMPA_BULL") + s["profiles"].count("TRAMPA_BEAR")
        
        print(f"\n{s['label']}")
        print(f"  Total Días: {total}")
        print(f"  MEGÁFONOS: {megas} ({megas/total*100:.1f}%)")
        print(f"  EXPANSIONES: {expans} ({expans/total*100:.1f}%)")
        print(f"  TRAMPAS ICT: {trampas} ({trampas/total*100:.1f}%)")
        print(f"  Volatilidad NY vs Londres: {np.mean(s['vol']):.2f}x")

    # Análisis VXN
    df = pd.DataFrame(results)
    print("\n" + "="*80)
    print("📉 CORRELACIÓN VXN vs PERFIL")
    print("="*80)
    
    df['vix_group'] = pd.cut(df['VXN'], bins=[0, 20, 25, 30, 40], labels=['BAJO (<20)', 'MEDIO (20-25)', 'ALTO (25-30)', 'PÁNICO (>30)'])
    for group in df['vix_group'].unique():
        sub = df[df['vix_group'] == group]
        if sub.empty: continue
        m_perf = sub['Profile'].value_counts().idxmax()
        m_pct = sub['Profile'].value_counts().iloc[0] / len(sub) * 100
        print(f"  VXN {group:14} | Perfil Dominante: {m_perf:12} ({m_pct:.1f}%)")

run_backtest()
