import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent8_data.json")

def load_json(name):
    path = os.path.join(BASE_DIR, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def run():
    print("\n" + "="*60)
    print("  AGENTE 8 · MORGAN PSYCHOLOGIST")
    print("="*60 + "\n")

    a1 = load_json("agent1_data.json")
    a3 = load_json("agent3_data.json")
    a4 = load_json("agent4_data.json")
    
    # Inputs de sentimiento
    raw_inputs = a3.get("raw_inputs", {})
    vxn_val = raw_inputs.get("VXN", 20)
    dix_val = raw_inputs.get("DIX", 45)
    
    # Prevenir errores de tipo si los valores son None
    vxn_val = vxn_val if vxn_val is not None else 20
    dix_val = dix_val if dix_val is not None else 45

    ndx_data = a1.get("yahoo", {}).get("NDX", {})
    change_pct = ndx_data.get("change_pct", 0)
    change_pct = change_pct if change_pct is not None else 0
    
    mindset_status = "ESTABLE"
    warnings = []
    operational_risk = "BAJO"
    
    # Lógica de detección de sesgos (Inspirado en Morgan Stanley Sentiment)
    
    # 1. Detección de FOMO (Retail Buying Top)
    if change_pct > 1.0 and vxn_val < 18 and dix_val < 42:
        mindset_status = "ALERTA: FOMO DETECTADO"
        warnings.append("Cuidado: Estás comprando euforia retail. Los flujos institucionales (DIX) no están apoyando este movimiento.")
        operational_risk = "ALTO (Trampa de Liquidez)"
        
    # 2. Detección de Pánico / Capitulación
    elif change_pct < -1.5 and vxn_val > 30:
        mindset_status = "ALERTA: PÁNICO EXTREMO"
        warnings.append("Capitulación en curso. El mercado está barriendo manos débiles. Busca niveles SMC para soporte.")
        operational_risk = "ALTO (Volatilidad Desatada)"
        
    # 3. Sesgo de Confirmación
    global_score = a4.get("global_score", 50)
    if global_score and global_score > 85:
        warnings.append("Sesgo de confirmación: Antigravity detecta un consenso demasiado optimista. ¿Qué pasa si el mercado gira mañana?")

    output = {
        "agent": 8,
        "name": "Morgan Psychologist",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
        "sentiment": {
            "status": mindset_status,
            "operational_risk": operational_risk,
            "alerts": warnings if warnings else ["Sentimiento equilibrado. Ejecución técnica recomendada."]
        },
        "morgan_audit": {
            "institutional_alignment": "HIGH" if dix_val > 45 else "LOW",
            "fear_index": "LOW" if vxn_val < 20 else "MEDIUM" if vxn_val < 30 else "HIGH"
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
        
    print(f"🧠 Mindset: {mindset_status}")
    print(f"⚠️ Riesgo: {operational_risk}")

if __name__ == "__main__":
    run()
