import time
import json
import os
import datetime
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "pulse_data.json")

def get_ultra_live_data():
    """
    Obtiene datos de alta frecuencia (NQ, VXN) de forma optimizada.
    """
    tickers = {"NQ": "NQ=F", "VXN": "^VXN"}
    results = {}
    
    for name, sym in tickers.items():
        try:
            # Usamos period 1d y interval 1m para máxima frescura en el 'close'
            t = yf.Ticker(sym)
            data = t.history(period="1d", interval="1m")
            if not data.empty:
                last_price = data['Close'].iloc[-1]
                change = last_price - data['Open'].iloc[0]
                results[name] = {
                    "price": round(float(last_price), 2),
                    "change": round(float(change), 2),
                    "timestamp": datetime.datetime.now(datetime.UTC).isoformat()
                }
        except:
            results[name] = None
    return results

def main():
    print("🔥 PULSE ENGINE ONLINE - Actualización 1s (Simulada/Fast)")
    while True:
        try:
            pulse = {
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "market": get_ultra_live_data(),
                "status": "STREAMING"
            }
            
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(pulse, f, indent=2)
            
            # Nota: yfinance tiene rate limits, en producción usaríamos una API de sockets.
            # Por ahora, refrescamos cada 5s para no ser bloqueados, pero el UI refresca cada 1s.
            time.sleep(5) 
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error en Pulse: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
