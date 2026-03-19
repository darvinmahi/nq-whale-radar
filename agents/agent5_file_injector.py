"""
AGENTE 5 — MEGA INJECTOR (QUANTUM EDITION)
═══════════════════════════════════════════════════════════
Responsabilidad: Inyectar TODOS los datos de los agentes en el 
frontend (index.html y analisis_orderflow.html).
"""

import os
import json
import datetime
import time
import sys

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_JS   = os.path.join(BASE_DIR, "agent_live_data.js")

def load_json(filename):
    try:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path): return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except: return {}

def safe_val(val, default="null"):
    if val is None: return default
    if isinstance(val, (int, float)): return val
    return f'"{val}"'

def generate_live_js():
    # Load all agent data
    a1 = load_json("agent1_data.json")
    a2 = load_json("agent2_data.json")
    a3 = load_json("agent3_data.json")
    a4 = load_json("agent4_data.json")
    a11 = load_json("agent11_data.json")
    a12 = load_json("agent12_backtest_results.json")
    a13 = load_json("agent13_data.json")
    a14 = load_json("agent14_orderflow_data.json")
    a15 = load_json("agent15_journal_data.json")  # ← Agent 15 Journal
    study = load_json("data/research/repetition_study.json")
    master_db = load_json("data/research/master_repetition_db.json")
    strength = load_json("data/research/level_strength.json")
    pulse = load_json("pulse_data.json")
    health = load_json("engine_health.json")  # ← health check

    now = datetime.datetime.now(datetime.UTC)
    ts = now.isoformat() + "Z"

    # Market Data Pre-processing
    market_nq = (pulse.get("market") or {}).get("NQ") or {} if pulse else {}
    nq_price = market_nq.get("price")
    if nq_price is None:
        nq_price = (a1.get("yahoo") or {}).get("NQ_futures", {}) or {}
        nq_price = nq_price.get("price") if isinstance(nq_price, dict) else None

    nq_change = ((a1.get("yahoo") or {}).get("NQ_futures") or {}).get("change_pct", 0)


    # Datos stale: si algún ticker de Yahoo falló y usó caché
    yahoo_data = a1.get("yahoo", {}) or {}
    any_stale = any(
        isinstance(v, dict) and v.get("stale")
        for v in yahoo_data.values()
    )
    data_quality = a1.get("data_quality", "UNKNOWN")

    # COT Data
    cot = a2.get("cot", {})
    history = a2.get("recent_weeks", [])

    # Health info
    engine_state  = health.get("engine_state", "UNKNOWN")
    last_update_h = health.get("last_update_human", "—")
    agents_ok     = health.get("agents_ok", "—")
    agents_failed = health.get("agents_failed", "—")
    total_time    = health.get("total_time_sec", "—")
    cycle_num     = health.get("cycle", "—")

    js = f"""// 🚀 QUANTUM DATA FEED · AUTO-GENERATED
window.NQ_LIVE = {{
  timestamp: "{ts}",
  last_update: "{now.strftime('%H:%M:%S')} UTC",
  NQ: {{ 
    price: {nq_price if nq_price else 0}, 
    change_pct: {nq_change} 
  }},
  COT: {{
    net: {safe_val(cot.get("current_net"), 0)},
    index: {safe_val(cot.get("cot_index"), 0)},
    signal: "{a2.get("signal", "NEUTRAL")}",
    razonamiento: `{a2.get("razonamiento", "")}`,
    history: {json.dumps(history)}
  }},
  BIAS: {{ 
    score: {safe_val(a4.get("global_score"), 50)}, 
    label: "{a4.get("global_label", "NEUTRAL")}" 
  }},
  ORDERFLOW: {json.dumps(a14)},
  JOURNAL: {json.dumps(a15)},
  BACKTEST: {json.dumps(a12)},
  STUDY: {json.dumps(study)},
  STUDY_MASTER: {json.dumps(master_db)},
  STRENGTH: {json.dumps(strength)},
  RESEARCH: {json.dumps(a13)},
  PROTOCOLS: {json.dumps(a11)},
  VOLATILITY: {json.dumps(a3)},
  ENGINE_HEALTH: {{
    state: "{engine_state}",
    last_cycle: "{last_update_h}",
    cycle_num: {json.dumps(cycle_num)},
    agents_ok: {json.dumps(agents_ok)},
    agents_failed: {json.dumps(agents_failed)},
    total_time_sec: {json.dumps(total_time)},
    data_quality: "{data_quality}",
    any_stale: {"true" if any_stale else "false"}
  }},
  ENGINE_STATUS: "{engine_state}"
}};

(function sync() {{
    const D = window.NQ_LIVE;
    const set = (id, val) => {{ 
        const el = document.getElementById(id); 
        if(el && val !== null && val !== undefined) el.innerText = val; 
    }};
    
    // Global Header
    if(D.NQ.price) {{
        set("hero-price", D.NQ.price.toLocaleString());
        set("nav-price", D.NQ.price.toLocaleString());
    }}
    
    // COT Dashboard
    set("cot-net-val", (D.COT.net || 0).toLocaleString());
    set("hero-cot-index", (D.COT.index || 0).toFixed(1) + "%");
    const pin = document.getElementById("cot-pin");
    if(pin) pin.style.left = (D.COT.index || 0) + "%";
    
    // Summary Tables (if exist)
    const tableBody = document.getElementById("cot-table-body");
    if (tableBody && D.COT.history) {{
        tableBody.innerHTML = D.COT.history.map((w, i) => `
            <tr class="${{i === 0 ? 'bg-electric-cyan/5 text-white font-bold' : ''}}">
                <td class="p-3 border-b border-white/5">${{w.date}}</td>
                <td class="p-3 text-right border-b border-white/5 text-white">${{(w.net_position || 0).toLocaleString()}}</td>
                <td class="p-3 text-right border-b border-white/5 text-vibrant-blue">${{(w.comm_net || 0).toLocaleString()}}</td>
                <td class="p-3 text-right border-b border-white/5 opacity-60">${{(w.retail_net || 0).toLocaleString()}}</td>
                <td class="p-3 text-right border-b border-white/5 font-mono opacity-40">${{(w.oi || 0).toLocaleString()}}</td>
            </tr>
        `).join("");
    }}

    // ─── ENGINE HEALTH WIDGET ──────────────────────────────
    const H = D.ENGINE_HEALTH;
    const pulse = document.getElementById("neural-pulse-status");
    if(pulse) {{
        const stateEmoji = H.state === "OPTIMAL" ? "✅" : H.state === "DEGRADED" ? "🟡" : H.state === "CRITICAL" ? "🔴" : "⚪";
        const staleWarning = H.any_stale ? " ⚠️ STALE" : "";
        pulse.innerText = `${{stateEmoji}} ENGINE ${{H.state}}${{staleWarning}} · Ciclo #${{H.cycle_num}} · ${{H.last_cycle}} · ${{H.agents_ok}} OK / ${{H.agents_failed}} FAIL · ${{H.total_time_sec}}s`;
    }}
    
    // Si hay IDs específicos del health widget
    set("engine-state",    H.state);
    set("engine-cycle",    "#" + H.cycle_num);
    set("engine-last",     H.last_cycle);
    set("engine-ok",       H.agents_ok + " OK");
    set("engine-fail",     H.agents_failed + " FAIL");
    set("engine-time",     H.total_time_sec + "s");
    set("engine-quality",  H.data_quality + (H.any_stale ? " ⚠️" : " ✅"));
}})();
"""
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js)

def run():
    generate_live_js()

if __name__ == "__main__":
    if "--run-once" in sys.argv:
        generate_live_js()
        sys.exit(0)
    while True:
        try:
            generate_live_js()
            time.sleep(1)
        except: time.sleep(2)

