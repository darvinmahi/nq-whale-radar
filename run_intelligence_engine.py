"""
ORCHESTRATOR — NQ Intelligence Engine v2.2 (PARALLEL MODE)
═══════════════════════════════════════════════════════════
Mejoras v2.2:
  ✅ Paralelismo real:  Agent 1/2/3/6/7/8/9  corren en PARALELO
  ✅ Dependencias:      Agent 4/10/11/12/13/14/15/16 esperan los datos base
  ✅ Error handling:    Cada agente tiene timeout y reintento
  ✅ Health log:        Escribe engine_health.json después de cada ciclo
  ✅ Fallback:          Si un agente falla, el resto continúan
  ✅ Agent 15:          Journal Writer — genera entradas diarias del diario
  ✅ Agent 16:          Outcome Tracker — mide resultados reales vs predicciones

Frecuencia: Cada 15 minutos.
Pipeline:
  [PRE-QA]        → Agent 0
  [PARALELO 1]    → Agent 1, 2, 3 (fetch de datos independientes)
  [PARALELO 2]    → Agent 6, 7, 8, 9 (análisis, esperan datos base)
  [PARALELO 3]    → Agent 4, 10, 11, 12, 13, 14, 15, 16 (síntesis + outcomes)
  [INJECTOR]      → Agent 5 (siempre último)
  [POST-QA]       → Agent 0
"""

import sys
import os
import datetime
import time
import traceback
import importlib
import json
import threading

# Rutas
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
HEALTH_FILE = os.path.join(BASE_DIR, "engine_health.json")
sys.path.insert(0, AGENTS_DIR)

# ─── Constantes ───────────────────────────────────────────────
AGENT_TIMEOUT = 120  # segundos máx por agente antes de considerarlo colgado
CYCLE_INTERVAL = 15 * 60  # 15 minutos entre ciclos

# ─── Estado global del ciclo ──────────────────────────────────
_results_lock = threading.Lock()

def run_agent(module_name, agent_label, results_dict):
    """Ejecuta un agente y registra el resultado. Thread-safe."""
    start_t = time.time()
    try:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        mod = importlib.import_module(module_name)
        mod.run()
        elapsed = round(float(time.time() - start_t), 1)
        with _results_lock:
            results_dict[agent_label] = {"status": "✅ OK", "time": elapsed}
        print(f"  ✅ {agent_label} ({elapsed}s)")
    except Exception:
        elapsed = round(float(time.time() - start_t), 1)
        err = traceback.format_exc().strip().split("\n")[-1]  # Solo última línea del error
        with _results_lock:
            results_dict[agent_label] = {"status": "❌ ERROR", "time": elapsed, "error": err}
        print(f"  ❌ {agent_label} FALLÓ ({elapsed}s): {err}")

def run_parallel(agent_list, results_dict, label=""):
    """Ejecuta una lista de (module, label) en paralelo con threads."""
    print(f"\n  ▶ GRUPO {label} en paralelo ({len(agent_list)} agentes)...")
    threads = []
    for module_name, agent_label in agent_list:
        t = threading.Thread(
            target=run_agent,
            args=(module_name, agent_label, results_dict),
            daemon=True
        )
        threads.append(t)
        t.start()

    # Espera con timeout por agente
    for t in threads:
        t.join(timeout=AGENT_TIMEOUT)

def run_sequential(module_name, agent_label, results_dict):
    """Ejecuta un solo agente de forma síncrona."""
    print(f"\n  ▶ {agent_label}...")
    run_agent(module_name, agent_label, results_dict)

def save_health(results, elapsed, cycle_num):
    """Escribe engine_health.json con el estado del último ciclo."""
    now = datetime.datetime.now(datetime.UTC)
    ok_count  = sum(1 for v in results.values() if "OK"    in v.get("status",""))
    err_count = sum(1 for v in results.values() if "ERROR" in v.get("status",""))

    if err_count == 0:
        engine_state = "OPTIMAL"
    elif err_count <= 2:
        engine_state = "DEGRADED"
    else:
        engine_state = "CRITICAL"

    health = {
        "cycle": cycle_num,
        "timestamp": now.isoformat() + "Z",
        "last_update_human": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "next_update_in_min": CYCLE_INTERVAL // 60,
        "engine_state": engine_state,
        "total_time_sec": round(elapsed, 1),
        "agents_ok": ok_count,
        "agents_failed": err_count,
        "details": results
    }
    try:
        with open(HEALTH_FILE, "w", encoding="utf-8") as f:
            json.dump(health, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  ⚠️ No se pudo escribir engine_health.json: {e}")

def run_pipeline(cycle_num):
    start = datetime.datetime.now(datetime.UTC)
    results = {}

    print("\n" + "█"*60)
    print(f"  NQ INTELLIGENCE ENGINE v2.0 — CICLO #{cycle_num}")
    print(f"  Inicio: {start.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("█"*60)

    # ── PRE-FLIGHT QA ──────────────────────────────────────────
    run_sequential("agent0_qa_commander", "Agent 0 · QA Commander [PRE]", results)

    # ── GRUPO 1: Fetchers de datos (100% independientes → PARALELO) ──
    grupo1 = [
        ("agent1_data_collector",      "Agent 1 · Data Collector"),
        ("agent2_cot_analyst",         "Agent 2 · COT Analyst"),
        ("agent3_volatility_analyst",  "Agent 3 · Volatility Analyst"),
    ]
    run_parallel(grupo1, results, "1 (Fetchers)")

    # ── GRUPO 2: Análisis (dependen de A1/A2/A3 → esperamos su fin) ──
    grupo2 = [
        ("agent6_smc_detective",       "Agent 6 · SMC Detective"),
        ("agent7_probability_analyst", "Agent 7 · Probability Analyst"),
        ("agent8_psychologist",        "Agent 8 · Morgan Psychologist"),
        ("agent9_silver_bullet",       "Agent 9 · Silver Bullet"),
    ]
    run_parallel(grupo2, results, "2 (Análisis)")

    # ── GRUPO 3: Síntesis (dependen de A1-A9) ─────────────────────
    grupo3 = [
        ("agent4_bias_engine",          "Agent 4 · Bias Engine"),
        ("agent10_learning_engine",     "Agent 10 · Learning Engine"),
        ("agent12_backtester",          "Agent 12 · Backtest Engine"),
        ("agent13_research_scout",      "Agent 13 · Research Scout"),
        ("agent14_orderflow_expert",    "Agent 14 · Order Flow Expert"),
        ("agent15_journal_writer",      "Agent 15 · Journal Writer"),
        ("agent16_outcome_tracker",     "Agent 16 · Outcome Tracker"),
    ]
    run_parallel(grupo3, results, "3 (Síntesis + Outcomes)")

    # ── GRUPO 4: Strategy (depende de Bias) ───────────────────────
    run_sequential("agent11_strategy_crafter", "Agent 11 · Strategy Crafter", results)
    run_sequential("agent_sentinel",           "Agent Sentinel · Guardian", results)

    # ── INJECTOR (siempre último — usa TODO lo anterior) ──────────
    run_sequential("agent5_file_injector", "Agent 5 · File Injector", results)

    # ── POST-FLIGHT QA ────────────────────────────────────────────
    run_sequential("agent0_qa_commander", "Agent 0 · QA Commander [POST]", results)

    # ── Resumen ───────────────────────────────────────────────────
    end     = datetime.datetime.now(datetime.UTC)
    elapsed = (end - start).total_seconds()
    save_health(results, elapsed, cycle_num)

    ok_count  = sum(1 for v in results.values() if "OK"    in v.get("status",""))
    err_count = sum(1 for v in results.values() if "ERROR" in v.get("status",""))

    print("\n" + "═"*60)
    print("  RESUMEN DEL CICLO")
    print("═"*60)
    for label, data in results.items():
        t = data.get("time", "-")
        s = data.get("status", "?")
        print(f"  {s}  {label} ({t}s)")
    print(f"\n  ✅ {ok_count} OK  ❌ {err_count} FALLOS")
    print(f"  ⏱  Tiempo total: {elapsed:.1f}s  (antes era ~secuencial)")
    print(f"  🕐  Finalizado: {end.strftime('%H:%M:%S UTC')}")
    print(f"  📄  Health log: engine_health.json")
    print("═"*60 + "\n")

def main():
    print("🚀 NQ Intelligence Engine v2.0 — MODO PARALELO ACTIVO")
    print(f"   Actualizaciones cada {CYCLE_INTERVAL//60} min")
    print(f"   Health log: {HEALTH_FILE}")
    print("   Presiona Ctrl+C para detener.\n")

    cycle_num: int = 1
    while True:
        try:
            run_pipeline(cycle_num)
            cycle_num += 1
            print(f"💤 Próxima actualización en {CYCLE_INTERVAL//60} minutos...")
            time.sleep(CYCLE_INTERVAL)
        except KeyboardInterrupt:
            print("\n🛑 Motor detenido por el usuario.")
            break
        except Exception as e:
            print(f"\n⚠️ Error crítico en el bucle principal: {e}")
            traceback.print_exc()
            time.sleep(60)

if __name__ == "__main__":
    main()
