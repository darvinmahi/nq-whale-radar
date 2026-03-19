import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent11_data.json")

def craft_strategies():
    print("\n" + "="*60)
    print("  AGENTE 11 · STRATEGY CRAFTER (PROTOCOLS)")
    print("="*60 + "\n")

    def load_agent_data(filename):
        path = os.path.join(BASE_DIR, filename)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # Cargar datos de todos los expertos
    a2 = load_agent_data("agent2_data.json") # COT
    a3 = load_agent_data("agent3_data.json") # Volatility
    a4 = load_agent_data("agent4_data.json") # Bias
    a6 = load_agent_data("agent6_data.json") # SMC/ICT
    a8 = load_agent_data("agent8_data.json") # Psychology
    a9 = load_agent_data("agent9_data.json") # Silver Bullet
    a10 = load_agent_data("agent10_ict_stats.json") # ICT Stats

    # 1. PROTOCOLO: "ALINEACIÓN INSTITUCIONAL" (SWING)
    cot_signal = a2.get("signal", "NEUTRAL")
    try:
        global_score = int(a4.get("global_score", 50))
    except:
        global_score = 50

    protocol_swing = {
        "active": cot_signal == "BULLISH" and global_score > 65,
        "confidence": global_score,
        "desc": "Confluencia de COT Alcista y Bias Ponderado positivo. Las instituciones están acumulando."
    }

    # 2. PROTOCOLO: "JUDAS CONTINUATION" (ICT)
    ict_signal = a6.get("signal", "NEUTRAL")
    ict_stats_obj = a10.get("stats", {}) if isinstance(a10, dict) else {}
    
    protocol_ict_cont = {
        "active": ict_signal == "BULLISH" and global_score > 70,
        "probability": ict_stats_obj.get("ny_sweep_high_winrate", 71.3),
        "desc": "Escenario de alta probabilidad detectado por barrido de Londres en dirección de la tendencia macro."
    }

    # 3. PROTOCOLO: "PANIC TRAP" (CONTRARIAN)
    sentiment_status = a8.get("sentiment", {}).get("status", "STABLE") if isinstance(a8, dict) else "STABLE"
    vix_spiking = a3.get("vix_status", "LOW") == "HIGH"
    
    protocol_panic = {
        "active": sentiment_status == "PANIC" or vix_spiking,
        "desc": "Miedo extremo detectado. Buscando capitulación para entrada contrarian apoyada por DIX."
    }

    # 4. PROTOCOLO: "SILVER BULLET SNIPER" (INTRADAY)
    sb_status = a9.get("status", "INACTIVO")
    protocol_scalp = {
        "active": sb_status == "ACTIVE",
        "window": a9.get("active_window", "N/A"),
        "action": a9.get("action", "ESPERAR")
    }

    # 5. PROTOCOLO: "ORDER FLOW DOMINANCE" (AGENT 14)
    a14 = load_agent_data("agent14_orderflow_data.json")
    of_bias = a14.get("bias_orderflow", "NEUTRAL")
    pos_in_value = a14.get("value_area", {}).get("current_position", "INSIDE")
    
    protocol_orderflow = {
        "active": of_bias == "BULLISH" and pos_in_value == "ABOVE_VAH",
        "desc": "Fuerza compradora agresiva detectada por encima del VAH. Alta convicción institucional.",
        "delta_status": a14.get("delta", {}).get("status")
    }

    # 6. PROTOCOLO: "RESEARCH ALPHA SCOUT" (AGENT 13)
    a13 = load_agent_data("agent13_data.json")
    research_bias = a13.get("insights", {}).get("external_bias", "NEUTRAL")
    
    protocol_research = {
        "active": research_bias == "BULLISH" and global_score > 60,
        "desc": "Confluencia con análisis de fuentes externas (YouTube/Blogs). El sentimiento experto apoya la dirección."
    }

    active_protocols = []
    if protocol_swing["active"]: active_protocols.append("INSTITUTIONAL_ALIGNMENT")
    if protocol_ict_cont["active"]: active_protocols.append("JUDAS_CONTINUATION")
    if protocol_panic["active"]: active_protocols.append("PANIC_TRAP")
    if protocol_scalp["active"]: active_protocols.append("SILVER_BULLET_SNIPER")
    if protocol_orderflow["active"]: active_protocols.append("ORDERFLOW_DOMINANCE")
    if protocol_research["active"]: active_protocols.append("RESEARCH_ALPHA")

    output = {
        "agent": 11,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "active_protocols": active_protocols,
        "details": {
            "swing": protocol_swing,
            "ict": protocol_ict_cont,
            "contrarian": protocol_panic,
            "intraday": protocol_scalp
        },
        "master_recommendation": a4.get("verdict", "Esperar confirmación.")
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Protocolos Identificados: {', '.join(active_protocols) if active_protocols else 'Ninguno'}")

def run():
    craft_strategies()

if __name__ == "__main__":
    run()
