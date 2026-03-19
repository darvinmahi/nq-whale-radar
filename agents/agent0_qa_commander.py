"""
╔══════════════════════════════════════════════════════════════╗
║          AGENT 0 · QA COMMANDER — EL JEFE DE CALIDAD        ║
║                 "No lo fácil. Lo mejor."                     ║
╚══════════════════════════════════════════════════════════════╝

Misión: Auditar cada agente del ecosistema antes y después de
su ejecución. Comprueba que los datos producidos son válidos,
frescos, ricos en señales y no son la respuesta mínima posible.

Si un agente entregó datos vacíos, desactualizados, con señales
neutras sin análisis real o simplemente copió valores por defecto,
el QA Commander lo DETECTA, lo DOCUMENTA y MARCA el pipeline
para que en el próximo ciclo ese agente sea forzado a recalcular
con más profundidad.

Filosofía: Calidad > Velocidad. Profundidad > Superficie.
"""

import json
import os
import datetime

# ─────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QA_REPORT_FILE = os.path.join(BASE_DIR, "agent0_qa_report.json")
QA_HISTORY_FILE = os.path.join(BASE_DIR, "agent0_qa_history.jsonl")

# Definición de cada agente: qué archivo produce y qué campos
# son obligatorios para considerar que el agente "hizo su trabajo bien".
AGENT_CONTRACTS = [
    {
        "agent": 1,
        "label": "Data Collector",
        "file": "agent1_data.json",
        "required_fields": ["price", "volume", "timestamp"],
        "forbidden_defaults": {},      # {campo: valor_por_defecto_sospechoso}
        "min_size_bytes": 200,
        "freshness_minutes": 30,
    },
    {
        "agent": 2,
        "label": "COT Analyst",
        "file": "agent2_data.json",
        "required_fields": ["signal", "net_position"],
        "forbidden_defaults": {"signal": "NEUTRAL"},   # NEUTRAL sin análisis = lazy
        "min_size_bytes": 300,
        "freshness_minutes": 90,
    },
    {
        "agent": 3,
        "label": "Volatility Analyst",
        "file": "agent3_data.json",
        "required_fields": ["vix_value", "vix_status"],
        "forbidden_defaults": {"vix_status": "LOW"},
        "min_size_bytes": 200,
        "freshness_minutes": 30,
    },
    {
        "agent": 4,
        "label": "Bias Engine",
        "file": "agent4_data.json",
        "required_fields": ["global_score", "global_label", "verdict"],
        "forbidden_defaults": {"global_score": 50, "global_label": "NEUTRAL"},
        "min_size_bytes": 150,
        "freshness_minutes": 30,
    },
    {
        "agent": 6,
        "label": "SMC Detective",
        "file": "agent6_data.json",
        "required_fields": ["signal"],
        "forbidden_defaults": {"signal": "NEUTRAL"},
        "min_size_bytes": 100,
        "freshness_minutes": 60,
    },
    {
        "agent": 7,
        "label": "Probability Analyst",
        "file": "agent7_data.json",
        "required_fields": ["probability"],
        "forbidden_defaults": {},
        "min_size_bytes": 80,
        "freshness_minutes": 60,
    },
    {
        "agent": 8,
        "label": "Psychologist",
        "file": "agent8_data.json",
        "required_fields": ["sentiment"],
        "forbidden_defaults": {},
        "min_size_bytes": 200,
        "freshness_minutes": 60,
    },
    {
        "agent": 9,
        "label": "Silver Bullet",
        "file": "agent9_data.json",
        "required_fields": ["status"],
        "forbidden_defaults": {"status": "INACTIVO"},
        "min_size_bytes": 100,
        "freshness_minutes": 30,
    },
    {
        "agent": 10,
        "label": "Learning Engine",
        "file": "ai_weights.json",
        "required_fields": ["layer1", "layer2", "status"],
        "forbidden_defaults": {"status": "Balanced"},  # Balanced = nunca ajustó
        "min_size_bytes": 100,
        "freshness_minutes": 90,
    },
    {
        "agent": 11,
        "label": "Strategy Crafter",
        "file": "agent11_data.json",
        "required_fields": ["active_protocols", "master_recommendation"],
        "forbidden_defaults": {},
        "min_size_bytes": 300,
        "freshness_minutes": 30,
    },
    {
        "agent": 12,
        "label": "Backtest Engine",
        "file": "agent12_backtest_results.json",
        "required_fields": ["win_rate"],
        "forbidden_defaults": {},
        "min_size_bytes": 100,
        "freshness_minutes": 120,
    },
    {
        "agent": 13,
        "label": "Research Scout",
        "file": "agent13_data.json",
        "required_fields": ["insights"],
        "forbidden_defaults": {},
        "min_size_bytes": 200,
        "freshness_minutes": 120,
    },
    {
        "agent": 14,
        "label": "Order Flow Expert",
        "file": "agent14_orderflow_data.json",
        "required_fields": ["bias_orderflow"],
        "forbidden_defaults": {"bias_orderflow": "NEUTRAL"},
        "min_size_bytes": 200,
        "freshness_minutes": 30,
    },
    {
        "agent": "sentinel",
        "label": "Sentinel Guardian",
        "file": "agent_sentinel_data.json",
        "required_fields": ["status", "verdict"],
        "forbidden_defaults": {"status": "UNHEALTHY"},
        "min_size_bytes": 300,
        "freshness_minutes": 30,
    },
]


# ─────────────────────────────────────────────────────────
#  FUNCIONES DE AUDITORÍA
# ─────────────────────────────────────────────────────────

def check_freshness(file_path, freshness_minutes):
    """¿El archivo fue modificado en los últimos N minutos?"""
    if not os.path.exists(file_path):
        return False, "MISSING"
    mtime = os.path.getmtime(file_path)
    age = (datetime.datetime.now().timestamp() - mtime) / 60
    if age > freshness_minutes:
        return False, f"STALE ({age:.0f}min > {freshness_minutes}min)"
    return True, f"FRESH ({age:.0f}min)"


def check_size(file_path, min_size):
    """¿El archivo tiene suficiente contenido?"""
    if not os.path.exists(file_path):
        return False, "MISSING"
    size = os.path.getsize(file_path)
    if size < min_size:
        return False, f"TOO_SMALL ({size}B < {min_size}B)"
    return True, f"OK ({size}B)"


def check_required_fields(data, required_fields):
    """¿El JSON tiene todos los campos obligatorios?"""
    missing = []
    for field in required_fields:
        # Soporte para campos anidados con punto, ej: "sentiment.status"
        parts = field.split(".")
        val = data
        try:
            for p in parts:
                val = val[p]
        except (KeyError, TypeError):
            missing.append(field)
    return missing


def check_lazy_defaults(data, forbidden_defaults):
    """¿El agente devolvió exactamente los valores por defecto sin calcular nada?"""
    lazy_fields = []
    for field, default_val in forbidden_defaults.items():
        actual = data.get(field)
        if actual == default_val:
            lazy_fields.append(f"{field}={default_val!r}")
    return lazy_fields


def score_agent(checks):
    """
    Calcula un score de calidad 0-100 para el agente.
    100 = perfecto, 0 = catástrofe total.
    """
    penalties = 0
    if not checks["fresh"]:
        penalties += 35
    if not checks["size_ok"]:
        penalties += 25
    if checks["missing_fields"]:
        penalties += len(checks["missing_fields"]) * 15
    if checks["lazy_defaults"]:
        penalties += len(checks["lazy_defaults"]) * 10
    return max(0, 100 - penalties)


def audit_agent(contract):
    """Auditoría completa de un agente según su contrato."""
    file_path = os.path.join(BASE_DIR, contract["file"])

    result = {
        "agent": contract["agent"],
        "label": contract["label"],
        "file": contract["file"],
        "timestamp_audit": datetime.datetime.now().isoformat(),
        "fresh": False,
        "freshness_detail": "",
        "size_ok": False,
        "size_detail": "",
        "missing_fields": [],
        "lazy_defaults": [],
        "score": 0,
        "verdict": "❌ FAIL",
        "recommendation": ""
    }

    # 1. Frescura
    ok, detail = check_freshness(file_path, contract["freshness_minutes"])
    result["fresh"] = ok
    result["freshness_detail"] = detail

    # 2. Tamaño
    ok2, detail2 = check_size(file_path, contract["min_size_bytes"])
    result["size_ok"] = ok2
    result["size_detail"] = detail2

    # 3. Campos y valores (solo si el archivo existe)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result["missing_fields"] = check_required_fields(data, contract["required_fields"])
            result["lazy_defaults"] = check_lazy_defaults(data, contract.get("forbidden_defaults", {}))
        except Exception as e:
            result["missing_fields"] = [f"JSON_ERROR: {e}"]

    # 4. Score y veredicto final
    result["score"] = score_agent(result)
    
    if result["score"] >= 85:
        result["verdict"] = "✅ EXCELENTE"
    elif result["score"] >= 60:
        result["verdict"] = "⚠️ ACEPTABLE"
    elif result["score"] >= 35:
        result["verdict"] = "🔶 DEFICIENTE"
    else:
        result["verdict"] = "❌ CRÍTICO"

    # 5. Recomendación específica
    recs = []
    if not result["fresh"]:
        recs.append(f"Dato desactualizado ({detail}): el agente debe recalcular en el próximo ciclo.")
    if not result["size_ok"]:
        recs.append(f"Output demasiado corto ({detail2}): el agente está entregando análisis superficial.")
    if result["missing_fields"]:
        recs.append(f"Campos faltantes {result['missing_fields']}: el agente no completó todos los cálculos requeridos.")
    if result["lazy_defaults"]:
        recs.append(f"Valores por defecto detectados {result['lazy_defaults']}: el agente tomó el camino fácil sin analizar.")
    
    result["recommendation"] = " | ".join(recs) if recs else "Sin observaciones."

    return result


# ─────────────────────────────────────────────────────────
#  PIPELINE PRINCIPAL
# ─────────────────────────────────────────────────────────

def run():
    print("\n" + "╔" + "═"*58 + "╗")
    print("║   🎯 AGENT 0 · QA COMMANDER — AUDITORÍA DEL ECOSISTEMA  ║")
    print("╚" + "═"*58 + "╝\n")

    audit_results = []
    
    for contract in AGENT_CONTRACTS:
        result = audit_agent(contract)
        audit_results.append(result)
        
        score_bar = "█" * (result["score"] // 10) + "░" * (10 - result["score"] // 10)
        print(f"  Agent {str(result['agent']).ljust(8)} [{score_bar}] {result['score']:>3}/100  {result['verdict']}")
        
        # Imprimir problemas si los hay
        if result["recommendation"] != "Sin observaciones.":
            for line in result["recommendation"].split(" | "):
                print(f"              └─ ⚡ {line}")

    # ── RESUMEN GLOBAL ──────────────────────────────────────
    scores = [r["score"] for r in audit_results]
    avg_score = sum(scores) / len(scores) if scores else 0
    critical_agents = [r["label"] for r in audit_results if r["score"] < 35]
    deficient_agents = [r["label"] for r in audit_results if 35 <= r["score"] < 60]
    lazy_agents = [r["label"] for r in audit_results if r["lazy_defaults"]]
    stale_agents = [r["label"] for r in audit_results if not r["fresh"]]

    # Score sistema
    if avg_score >= 85:
        system_grade = "🏆 ÉLITE"
    elif avg_score >= 70:
        system_grade = "✅ SÓLIDO"
    elif avg_score >= 50:
        system_grade = "⚠️ MEJORABLE"
    else:
        system_grade = "🚨 EN RIESGO"

    # ── GUARDAR REPORTE JSON ─────────────────────────────────
    qa_report = {
        "agent": 0,
        "label": "QA Commander",
        "timestamp": datetime.datetime.now().isoformat(),
        "system_score": round(avg_score, 1),
        "system_grade": system_grade,
        "total_agents_audited": len(audit_results),
        "critical_agents": critical_agents,
        "deficient_agents": deficient_agents,
        "lazy_agents": lazy_agents,
        "stale_agents": stale_agents,
        "agents": audit_results,
        "qa_mandate": "Todo agente debe producir el MEJOR análisis posible, no el más fácil.",
    }

    with open(QA_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(qa_report, f, indent=4, ensure_ascii=False)

    # ── HISTORIAL JSONL (para tendencias de calidad) ─────────
    history_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "system_score": round(avg_score, 1),
        "critical_count": len(critical_agents),
        "lazy_count": len(lazy_agents),
        "stale_count": len(stale_agents),
    }
    with open(QA_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(history_entry) + "\n")

    # ── PRINT FINAL ──────────────────────────────────────────
    print(f"\n{'═'*60}")
    print(f"  📊 SCORE GLOBAL DEL ECOSISTEMA: {avg_score:.1f}/100  {system_grade}")
    print(f"{'═'*60}")
    if critical_agents:
        print(f"  ❌ CRÍTICOS   ({len(critical_agents)}): {', '.join(critical_agents)}")
    if deficient_agents:
        print(f"  🔶 DEFICIENTES ({len(deficient_agents)}): {', '.join(deficient_agents)}")
    if lazy_agents:
        print(f"  😴 PEREZOSOS  ({len(lazy_agents)}): {', '.join(lazy_agents)}")
    if stale_agents:
        print(f"  🕐 DESACTUALIZADOS ({len(stale_agents)}): {', '.join(stale_agents)}")
    if not (critical_agents or deficient_agents or lazy_agents or stale_agents):
        print("  🏆 Todos los agentes operan al máximo rendimiento.")
    print(f"\n  📁 Reporte guardado en: agent0_qa_report.json")
    print(f"  📈 Historial acumulado en: agent0_qa_history.jsonl")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    run()
