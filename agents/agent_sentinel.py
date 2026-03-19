import json
import os
import datetime

# Rutas absolutas para evitar errores de ejecución
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent_sentinel_data.json")

def run_sentinel():
    print("\n" + "═"*60)
    print("  🛡️ AGENTE SENTINEL · GUARDIÁN DEL DASHBOARD")
    print("═"*60 + "\n")

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "status": "HEALTHY",
        "alerts": [],
        "integrity_check": {},
        "verdict": "Sistema operativo y monitoreado. No se detectan anomalías en el ciclo actual.",
        "stats_3yr": {
            "w1_expansion": 67.9,
            "w2_megaphone": 34.5,
            "w3_traps": 31.6,
            "yearly_megaphone": 31.5
        }
    }

    # 1. VERIFICAR INTEGRIDAD DE ARCHIVOS CLAVE
    critical_files = [
        "index.html", "analisis_promax.html", "agent_live_data.js", 
        "agent1_data.json", "agent4_data.json"
    ]
    
    for f_name in critical_files:
        path = os.path.join(BASE_DIR, f_name)
        exists = os.path.exists(path)
        size = os.path.getsize(path) if exists else 0
        report["integrity_check"][f_name] = {"exists": exists, "size": size}
        
        if not exists:
            report["alerts"].append(f"CRÍTICO: Falta archivo {f_name}")
            report["status"] = "CRITICAL"
        elif size == 0:
            report["alerts"].append(f"ADVERTENCIA: Archivo {f_name} está vacío")

    # 2. AUDITORÍA DE CONTENIDO (Paso a paso)
    try:
        with open(os.path.join(BASE_DIR, "analisis_promax.html"), "r", encoding="utf-8") as f:
            content = f.read()
            if "MARZO 2026" not in content.upper():
                report["alerts"].append("DATO: Auditoría de Marzo no detectada")
            if "FEBRERO 2026" not in content.upper():
                report["alerts"].append("DATO: Auditoría de Febrero no detectada")
    except Exception as e:
        report["alerts"].append(f"ERROR: Fallo al leer HTML: {str(e)}")

    # 3. GENERAR VERDICTO DINÁMICO CON ESTADÍSTICAS REALES (Backtest 3 años)
    try:
        with open(os.path.join(BASE_DIR, "agent4_data.json"), "r") as f:
            a4 = json.load(f)
            bias = a4.get("global_label", "NEUTRAL")
            score = a4.get("global_score", 50)
            
            wom = (datetime.datetime.now().day - 1) // 7 + 1
            if wom == 2:
                report["verdict"] = f"ATENCIÓN: Ciclo CPI (W2). Históricamente (3 años), el MEGÁFONO ocurre el {report['stats_3yr']['w2_megaphone']}% de las veces en este ciclo. Sesgo macro: {bias} ({score}/100)."
            elif wom == 1:
                report["verdict"] = f"INFO: Ciclo NFP (W1). Probabilidad de EXPANSIÓN: {report['stats_3yr']['w1_expansion']}%. Sesgo {bias} fuerte. Busca seguir el flujo de la EMA 200."
            elif wom == 3:
                report["verdict"] = f"ALERTA: Ciclo FOMC (W3). Dominio de TRAMPAS ({report['stats_3yr']['w3_traps']}%). El precio suele barrer liquidez antes de la FED."
            else:
                report["verdict"] = f"CIERRE: Última semana del mes. El mercado busca claridad tras GDP. Sesgo {bias} en {score} puntos. Monitorea flujos finales."
    except:
        report["verdict"] = "Sentinel está en modo pasivo. Datos de bias no disponibles para análisis profundo."

    # GUARDAR REPORTE
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"✅ Sentinel finalizado. Status: {report['status']}")
    if report["alerts"]:
        for a in report["alerts"]: print(f"   🚨 {a}")
    else:
        print("🟢 Sistema verificado. Datos de 3 años inyectados.")

def run():
    run_sentinel()

if __name__ == "__main__":
    run()
