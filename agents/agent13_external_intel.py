import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent13_data.json")
SOURCES_FILE = os.path.join(BASE_DIR, "external_sources.json")

def study_external_sources():
    print("\n" + "="*60)
    print("  AGENTE 13 · EXTERNAL INTELLIGENCE (STUDY MODE)")
    print("="*60 + "\n")

    # Inicializar fuentes si no existen
    if not os.path.exists(SOURCES_FILE):
        default_sources = {
            "youtube": [
                {"name": "World Class Edge", "url": "https://www.youtube.com/@worldclassedge", "priority": "High"},
                {"name": "ICT", "url": "https://www.youtube.com/@InnerCircleTrader", "priority": "Essential"}
            ],
            "blogs": ["ZeroHedge", "Goldman Sachs Macro"],
            "last_crawl": None
        }
        with open(SOURCES_FILE, "w") as f:
            json.dump(default_sources, f, indent=4)

    with open(SOURCES_FILE, "r") as f:
        sources = json.load(f)

    print(f"🧐 [ESTUDIANDO]: Analizando {len(sources['youtube'])} canales de YouTube y {len(sources['blogs'])} fuentes macro...")

    # Simulación de extracción de datos (en producción esto usaría web_search o APIs)
    # Aquí la IA "aprende" conceptos como 'Judas Swing', 'London Open Killzone', etc.
    
    study_insights = {
        "source": "World Class Edge / ICT",
        "concepts_learned": ["FVG Equilibrium", "Liquidity Sweeps L3", "DXY Inverse Correlation"],
        "external_bias": "NEUTRAL-BULLISH",
        "confidence": 75,
        "recommendation": "Esperar barrido de mínimos de Londres antes de buscar expansión alcista.",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

    output = {
        "agent": 13,
        "name": "External Intelligence",
        "last_crawl": datetime.datetime.utcnow().isoformat(),
        "insights": study_insights,
        "knowledge_base_size": "2.4GB (Simulated)",
        "status": "Learning"
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)
    
    print(f"✅ Inteligencia Externa actualizada. Nuevo aprendizaje de: {study_insights['source']}")

def run():
    study_external_sources()

if __name__ == "__main__":
    run()
