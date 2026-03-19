import yfinance as yf
import pandas as pd
import datetime
import pytz

def analyze_yesterday():
    print("📋 AUDITORÍA DE LA SESIÓN DE AYER (12 MARZO 2026)")
    print("="*60)
    
    ticker = "NQ=F"
    df = yf.download(ticker, period="5d", interval="1h")
    
    # Aplanar MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        
    df.index = df.index.tz_convert('America/New_York')
    df['hour'] = df.index.hour
    df['date'] = df.index.date
    
    target_date = datetime.date(2026, 3, 12)
    day_df = df[df['date'] == target_date]
    
    if day_df.empty:
        print("❌ No hay datos para el 12 de marzo.")
        return

    # Sesión Londres (04:00 - 09:00 NY)
    london = day_df[(day_df['hour'] >= 4) & (day_df['hour'] < 9)]
    lon_hi = london['High'].max()
    lon_lo = london['Low'].min()
    
    # Sesión NY (09:00 - 16:00 NY)
    ny = day_df[(day_df['hour'] >= 9) & (day_df['hour'] < 16)]
    ny_hi = ny['High'].max()
    ny_lo = ny['Low'].min()
    
    # Precio de Cierre del día
    close_price = day_df['Close'].iloc[-1]
    open_price = day_df['Open'].iloc[0]
    
    print(f"📍 Rango Londres: {lon_lo:.2f} - {lon_hi:.2f}")
    print(f"📍 Rango NY:      {ny_lo:.2f} - {ny_hi:.2f}")
    print(f"📍 Apertura Día:  {open_price:.2f}")
    print(f"📍 Cierre Día:    {close_price:.2f}")
    
    # Análisis de Barridos (Sweeps)
    sweep_lo = ny_lo < lon_lo
    sweep_hi = ny_hi > lon_hi
    
    print("\n🔍 ANÁLISIS ICT:")
    if sweep_lo:
        print("⚠️ NY BARRIÓ el mínimo de Londres (Sweep Low).")
    if sweep_hi:
        print("🚀 NY BARRIÓ el máximo de Londres (Sweep High).")
        
    # Veredicto de la Estrategia (Basado en nuestro último estudio)
    # Si barre High y el mercado está fuerte -> Continuación (71%)
    # Si barre Low en Discount -> Continuación Bajista (72%)
    
    # Suponiendo que ayer el bias era fuerte (vimos a NQ subiendo en los logs)
    if sweep_hi and close_price > open_price:
        print("\n✅ ACIERTO: NY barrió el High de Londres y continuó al alza (Estrategia de Continuación Alcista).")
    elif sweep_lo and close_price < open_price:
        print("\n✅ ACIERTO: NY barrió el Low de Londres y continuó a la baja (Estrategia de Continuación Bajista).")
    else:
        print("\n❌ FALLO o Reversión no alineada con el modelo de probabilidad principal.")

if __name__ == "__main__":
    analyze_yesterday()
