import yfinance as yf
import pandas as pd
import numpy as np
import os
import datetime
import pytz
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuración de Rutas
DATA_DIR = "data/research"
os.makedirs(DATA_DIR, exist_ok=True)

def fetch_intraday_data():
    print("📡 Descargando 2 años de datos horarios (1h) de Futuros Nasdaq (NQ=F)...")
    ticker = "NQ=F"
    df = yf.download(ticker, period="2y", interval="1h")
    
    # Aplanar MultiIndex si existe (versiones nuevas de yfinance)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # Asegurar que el índice es datetime y tiene zona horaria
    if df.index.tz is None:
        df.index = df.index.tz_localize('UTC')
    
    # Convertir a hora de Nueva York (EST/EDT) para que coincida con ICT
    df.index = df.index.tz_convert('America/New_York')
    
    return df

def analyze_sessions(df):
    print("🔍 Analizando comportamiento por sesiones ICT...")
    
    # Extraer hora y fecha
    df['hour'] = df.index.hour
    df['date'] = df.index.date
    
    results = []
    
    dates = df['date'].unique()
    print(f"📊 Procesando {len(dates)} días potenciales...")
    
    for d in dates:
        day_df = df[df['date'] == d]
        
        # Filtros de sesión (Basados en lo que suele estar disponible)
        # Asia: 20:00 - 02:00 (A veces yfinance tiene las horas 00:00-03:00)
        asia = day_df[(day_df['hour'] >= 0) & (day_df['hour'] < 4)]
        london = day_df[(day_df['hour'] >= 4) & (day_df['hour'] < 9)]
        ny = day_df[(day_df['hour'] >= 9) & (day_df['hour'] < 16)]
        
        if london.empty or ny.empty:
            continue
        
        try:
            # Sesiones
            lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
            ny_hi, ny_lo = float(ny['High'].max()), float(ny['Low'].min())
            
            # Asia (Opcional pero potente)
            asia_hi, asia_lo = (float(asia['High'].max()), float(asia['Low'].min())) if not asia.empty else (None, None)
            
            # Dirección del día
            day_open = float(day_df['Open'].iloc[0])
            day_close = float(day_df['Close'].iloc[-1])
            day_return = (day_close / day_open) - 1
            
            # Setup 1: London barriendo Asia
            lon_sweep_asia_lo = (asia_lo is not None and lon_lo < asia_lo)
            lon_sweep_asia_hi = (asia_hi is not None and lon_hi > asia_hi)
            
            # Setup 2: NY barriendo London (Judas Swing)
            ny_sweep_lon_lo = ny_lo < lon_lo
            ny_sweep_lon_hi = ny_hi > lon_hi
            
            # ¿Es una reversión o continuación?
            results.append({
                "date": d,
                "lon_sweep_asia_lo": lon_sweep_asia_lo,
                "lon_sweep_asia_hi": lon_sweep_asia_hi,
                "ny_sweep_lon_lo": ny_sweep_lon_lo,
                "ny_sweep_lon_hi": ny_sweep_lon_hi,
                "day_return": day_return
            })
        except:
            continue
            
    if not results:
        print("❌ Seguimos sin resultados. Verificando lógica de horas.")
        return

    res_df = pd.DataFrame(results)
    
    # --- CONFLUENCIA CON SMC/COT (EL "EDGE") ---
    print("\n" + "🎲 ANALIZANDO CONFLUENCIA MACRO (COT + SMC)...")
    try:
        intel_path = "data/research/ndx_intelligence_base.csv"
        intel_df = pd.read_csv(intel_path)
        intel_df['date'] = pd.to_datetime(intel_df['Date']).dt.date
        
        # Merge de estudios
        combined = pd.merge(res_df, intel_df, on='date')
        
        # Escenario A: Continuación (Barre High en mercado Alcista)
        best_bull = combined[(combined['is_discount'] == False) & (combined['ny_sweep_lon_hi'] == True)]
        wr_bull = (best_bull['day_return'] > 0).mean() * 100
        
        # Escenario B: Reversión (Barre Low en mercado Bajista/Discount)
        # Ya vimos que es 27%
        
        print(f"📈 ESCENARIO LÍDER: Continuación Alcista")
        print(f"   - Si NY barre el High de Londres y el mercado está fuerte:")
        print(f"   - Probabilidad de seguir subiendo: {wr_bull:.1f}%")
        print(f"   - Muestra: {len(best_bull)} días")
        
        # Escenario C: El "Falla de Reversión" (Vender el Sweep de Low si la tendencia es bajista)
        trend_down = combined[(combined['is_discount'] == True) & (combined['ny_sweep_lon_lo'] == True)]
        wr_short = (trend_down['day_return'] < 0).mean() * 100
        print(f"📉 ESCENARIO LÍDER: Continuación Bajista")
        print(f"   - Si NY barre el Low de Londres en zona de Discount:")
        print(f"   - Probabilidad de seguir cayendo: {wr_short:.1f}%")
        print(f"   - Muestra: {len(trend_down)} días")
        
    except Exception as e:
        print(f"⚠️ Error en backtest profundo: {e}")
        
    # --- EXPORTAR ESTADÍSTICAS PARA DASHBOARD ---
    print("\n" + "📊 GENERANDO JSON PARA DASHBOARD...")
    try:
        # Calcular tasas de éxito
        sweep_lo_days = res_df[res_df['ny_sweep_lon_lo'] == True]
        wr_lo = (sweep_lo_days['day_return'] > 0).mean() * 100
        
        sweep_hi_days = res_df[res_df['ny_sweep_lon_hi'] == True]
        wr_hi = (sweep_hi_days['day_return'] < 0).mean() * 100

        ict_stats = {
            "agent": 10,
            "name": "ICT Session Strategist",
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
            "stats": {
                "ny_sweep_low_winrate": round(wr_lo, 1),
                "ny_sweep_high_winrate": round(wr_hi, 1),
                "total_days_analyzed": len(res_df),
                "sample_size_sweeps": len(sweep_lo_days) + len(sweep_hi_days)
            },
            "strategies": [
                {"name": "NY Continuation Bull", "edge": round(wr_lo, 1), "desc": "NY barre Low de Londres en Bias Alcista"},
                {"name": "NY Continuation Bear", "edge": round(wr_hi, 1), "desc": "NY barre High de Londres en Bias Bajista"}
            ]
        }
        
        with open(os.path.join(BASE_DIR, "agent10_ict_stats.json"), "w", encoding="utf-8") as f:
            json.dump(ict_stats, f, indent=4)
            
    except Exception as e:
        print(f"⚠️ Error generando JSON: {e}")

    # Evitar error de permiso si el archivo está abierto
    try:
        path = os.path.join(DATA_DIR, "ict_master_strategy.csv")
        res_df.to_csv(path)
        print(f"\n✅ Estudio organizado en {path}")
    except:
        print(f"⚠️ No se pudo escribir el CSV (está abierto), pero el JSON se generó.")

if __name__ == "__main__":
    df = fetch_intraday_data()
    analyze_sessions(df)
