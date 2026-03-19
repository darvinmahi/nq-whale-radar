import json
import os
import pandas as pd
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DATA = os.path.join(BASE_DIR, "agent1_data.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "agent6_data.json")
INTEL_BASE = os.path.join(BASE_DIR, "data", "research", "ndx_intelligence_base.csv")

def analyze_smc():
    print("\n" + "="*60)
    print("  AGENTE 6 · SMC DETECTIVE")
    print("="*60 + "\n")
    
    # Cargar datos actuales
    try:
        with open(INPUT_DATA, "r") as f:
            a1_data = json.load(f)
    except:
        print("❌ Error cargando agent1_data.json")
        return

    # Cargar base histórica para "comparar"
    try:
        intel = pd.read_csv(INTEL_BASE)
    except:
        print("❌ Base de inteligencia no encontrada. Ejecuta research_master_study.py primero.")
        return

    # Lógica de Precios actual
    current_price = a1_data['yahoo']['NDX']['price']

    # Lógica de Fair Value Gap
    fvg_bulls = intel[intel['fvg_bull'] == True]
    last_fvg_bull = fvg_bulls.iloc[-1] if not fvg_bulls.empty else None
    
    # Lógica ICT: ¿Estamos en Premium o Discount?
    last_row = intel.iloc[-1]
    pd_array = "PREMIUM" if current_price > last_row['equilibrium'] else "DISCOUNT"
    
    # Lógica de Liquidity Sweep
    recent_sweeps = intel.tail(3)
    has_bull_sweep = recent_sweeps['liquidity_sweep_bull'].any()
    has_bear_sweep = recent_sweeps['liquidity_sweep_bear'].any()

    signal = "NEUTRAL"
    confidence = 50
    details = f"Mercado en zona de {pd_array}. Sin sweeps institucionales recientes."
    
    if pd_array == "DISCOUNT" and has_bull_sweep:
        signal = "BULLISH"
        confidence = 85
        details = "ICT SETUP: Liquidity Sweep en zona de DISCOUNT detectado. Alta probabilidad alcista."
    elif pd_array == "PREMIUM" and has_bear_sweep:
        signal = "BEARISH"
        confidence = 85
        details = "ICT SETUP: Liquidity Sweep en zona de PREMIUM detectado. Riesgo de reversión bajista."
    elif last_fvg_bull is not None and current_price < last_fvg_bull['High'] and current_price > last_fvg_bull['Low']:
        signal = "BULLISH"
        confidence = 75
        details = f"Precio en zona de Fair Value Gaps (Bullish) detectado en {last_fvg_bull['High']:.0f}."
    
    output = {
        "agent": 6,
        "name": "ICT & SMC Master",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "ict": {
            "pd_array": pd_array,
            "equilibrium": float(last_row['equilibrium']),
            "has_liquidity_sweep": "BULLISH" if has_bull_sweep else "BEARISH" if has_bear_sweep else "NONE"
        },
        "smc": {
            "last_bull_ob_price": float(intel[intel['bullish_ob'] == True].iloc[-1]['Low']),
            "fvg_status": "ZONA_COMPRA" if signal == "BULLISH" else "NEUTRAL",
            "institution_bias": signal
        },
        "signal": signal,
        "confidence": confidence,
        "details": details
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=4)
    
    print(f"✅ SMC Signal: {signal} ({confidence}%)")
    print(f"📝 {details}")

def run():
    analyze_smc()

if __name__ == "__main__":
    run()
