import yfinance as yf
import pandas as pd
import numpy as np
import os

BASE_DIR = r"c:\Users\FxDarvin\Desktop\PAgina"
DATA_DIR = os.path.join(BASE_DIR, "data", "research")
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_historical_data():
    print("📡 Descargando 5 años de datos del Nasdaq (NDX)...")
    ndx = yf.download("^NDX", start="2020-01-01", interval="1d")
    if isinstance(ndx.columns, pd.MultiIndex):
        ndx.columns = ndx.columns.get_level_values(0)
    return ndx

def detect_smc_patterns(df):
    print("🔍 Detectando patrones SMC (Order Blocks & Gaps)...")
    # 1. Fair Value Gaps (FVG)
    df['fvg_bull'] = (df['Low'].shift(-1) > df['High'].shift(1))
    df['fvg_bear'] = (df['High'].shift(-1) < df['Low'].shift(1))
    
    # 3. ICT: Dealer Ranges (Premium vs Discount)
    # Calculamos el 50% de los últimos 20 días
    df['range_hi'] = df['High'].rolling(20).max()
    df['range_lo'] = df['Low'].rolling(20).min()
    df['equilibrium'] = (df['range_hi'] + df['range_lo']) / 2
    df['is_discount'] = df['Close'] < df['equilibrium']
    df['is_premium'] = df['Close'] > df['equilibrium']
    
    # 4. ICT: Liquidity Sweeps (Barridos de liquidez)
    # Si el Low actual es menor que el Low de ayer pero el Close es mayor (Rechazo)
    df['prev_low'] = df['Low'].shift(1)
    df['prev_high'] = df['High'].shift(1)
    df['liquidity_sweep_bull'] = (df['Low'] < df['prev_low']) & (df['Close'] > df['prev_low'])
    df['liquidity_sweep_bear'] = (df['High'] > df['prev_high']) & (df['Close'] < df['prev_high'])
    
    # 2. Order Blocks
    # Un Bullish OB es una vela bajista con volumen > media que precede un impulso alcista del 1.5%
    df['vol_ma'] = df['Volume'].rolling(20).mean()
    df['high_vol'] = df['Volume'] > df['vol_ma']
    df['is_down'] = df['Close'] < df['Open']
    
    # Marcamos el OB
    df['bullish_ob'] = df['is_down'] & df['high_vol'] & (df['Close'].shift(-2) > df['High'] * 1.015)
    
    return df

def cross_probability_study(df):
    print("🎲 Calculando probabilidades cruzadas...")
    # Necesitamos retornos a 5 días (1 semana trading)
    df['ret_5d'] = df['Close'].shift(-5) / df['Close'] - 1
    
    # Ejemplo: Probabilidad de éxito si hay Bullish OB
    ob_wins = df[df['bullish_ob'] == True]['ret_5d']
    if len(ob_wins) > 0:
        win_rate = (ob_wins > 0).mean() * 100
        avg_ret = ob_wins.mean() * 100
        print(f"  📈 Bullish OB Win Rate: {win_rate:.1f}% (Avg Ret: {avg_ret:.2f}%)")
    
    return df

def run_study():
    df = fetch_historical_data()
    df = detect_smc_patterns(df)
    df = cross_probability_study(df)
    
    # Guardar
    path = os.path.join(DATA_DIR, "ndx_intelligence_base.csv")
    df.to_csv(path)
    print(f"✅ Base de Inteligencia guardada en {path}")

if __name__ == "__main__":
    run_study()
