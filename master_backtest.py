import yfinance as yf
import pandas as pd
import numpy as np
import os
import datetime
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data/research")

def backtest_strategies():
    print("🧪 INICIANDO BACKTEST MAESTRO DE ESTRATEGIAS (2 AÑOS NQ=F)")
    print("="*60)
    
    # 1. Cargar Datos
    df = yf.download("NQ=F", period="2y", interval="1h")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.index = df.index.tz_convert('America/New_York')
    df['hour'] = df.index.hour
    df['date'] = df.index.date
    
    # 2. Cargar Inteligencia Macro (COT/SMC)
    intel_path = os.path.join(DATA_DIR, "ndx_intelligence_base.csv")
    if not os.path.exists(intel_path):
        print("❌ Error: ndx_intelligence_base.csv no encontrado.")
        return
        
    intel_df = pd.read_csv(intel_path)
    intel_df['date'] = pd.to_datetime(intel_df['Date']).dt.date
    
    results = []
    dates = df['date'].unique()
    
    for d in dates:
        day_df = df[df['date'] == d]
        if day_df.empty: continue
        
        # Datos Macro del día
        macro = intel_df[intel_df['date'] == d]
        if macro.empty: continue
        
        # Sesiones
        london = day_df[(day_df['hour'] >= 4) & (day_df['hour'] < 9)]
        ny = day_df[(day_df['hour'] >= 9) & (day_df['hour'] < 16)]
        if london.empty or ny.empty: continue
        
        lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
        ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
        
        # Rendimiento
        open_p = float(day_df['Open'].iloc[0])
        close_p = float(day_df['Close'].iloc[-1])
        day_ret = (close_p / open_p) - 1
        
        # --- TEST 1: JUDAS CONTINUATION (ICT) ---
        # Si barre High en tendencia alcista (is_discount = False)
        ict_bull_signal = (ny_hi > lon_hi) and (macro['is_discount'].iloc[0] == False)
        # Si barre Low en tendencia bajista (is_discount = True)
        ict_bear_signal = (ny_lo < lon_lo) and (macro['is_discount'].iloc[0] == True)
        
        # --- TEST 2: INSTITUTIONAL ALIGNMENT (COT) ---
        # COT Alcista + Bias fuerte
        cot_signal = (macro['bullish_ob'].iloc[0] == True) and (macro['Global_Score'].iloc[0] > 60) if 'Global_Score' in macro.columns else False
        
        results.append({
            "date": d,
            "ict_bull_win": 1 if ict_bull_signal and day_ret > 0 else (0 if ict_bull_signal else None),
            "ict_bear_win": 1 if ict_bear_signal and day_ret < 0 else (0 if ict_bear_signal else None),
            "cot_win": 1 if cot_signal and day_ret > 0 else (0 if cot_signal else None),
            "day_ret": day_ret
        })

    res_df = pd.DataFrame(results)
    
    # --- RESULTADOS ---
    print("\n📊 RESULTADOS DEL BACKTEST:")
    
    ict_bull = res_df['ict_bull_win'].dropna()
    ict_bear = res_df['ict_bear_win'].dropna()
    cot_strat = res_df['cot_win'].dropna()
    
    print(f"1. ICT JUDAS (BULL): WR {ict_bull.mean()*100:.1f}% | Muestra: {len(ict_bull)} días")
    print(f"2. ICT JUDAS (BEAR): WR {ict_bear.mean()*100:.1f}% | Muestra: {len(ict_bear)} días")
    print(f"3. COT ALIGNMENT:    WR {cot_strat.mean()*100:.1f}% | Muestra: {len(cot_strat)} días")
    
    # Exportar para Agente 11
    backtest_data = {
        "ict_bull": round(ict_bull.mean()*100, 1),
        "ict_bear": round(ict_bear.mean()*100, 1),
        "cot_strat": round(cot_strat.mean()*100, 2) if not cot_strat.empty else 0,
        "sample_days": len(res_df)
    }
    
    with open(os.path.join(BASE_DIR, "strategy_backtest_results.json"), "w") as f:
        json.dump(backtest_data, f, indent=4)

if __name__ == "__main__":
    backtest_strategies()
