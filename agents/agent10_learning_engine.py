"""
AGENTE 10 — LEARNING ENGINE v3.0 (MONSTER EDITION)
═══════════════════════════════════════════════════════
Cerebro central que aprende de TODOS los agentes.

Fases:
  1. Multi-Source: lee los 12 agentes + backtest
  2. Memoria Histórica: guarda snapshot en agent10_memory.jsonl
  3. Knowledge Base: genera insights, correlaciones, FAQ

Inputs:  agent*_data.json, agent12_backtest_results.json, agent10_ict_stats.json,
         agent16_scorecard.json (NUEVO — outcomes reales del Outcome Tracker)
Outputs: ai_weights.json, agent10_memory.jsonl, agent10_knowledge.json
"""

import json
import os
import datetime

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS_FILE  = os.path.join(BASE_DIR, "ai_weights.json")
MEMORY_FILE    = os.path.join(BASE_DIR, "agent10_memory.jsonl")
KNOWLEDGE_FILE = os.path.join(BASE_DIR, "agent10_knowledge.json")
BACKTEST_FILE  = os.path.join(BASE_DIR, "agent12_backtest_results.json")
SCORECARD_FILE = os.path.join(BASE_DIR, "agent16_scorecard.json")

NOW = datetime.datetime.now(datetime.timezone.utc)

# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def load(name):
    p = os.path.join(BASE_DIR, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def append_jsonl(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_memory(max_lines=200):
    """Read recent memory snapshots."""
    if not os.path.exists(MEMORY_FILE):
        return []
    lines = []
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    try:
                        lines.append(json.loads(raw))
                    except Exception:
                        pass
    except Exception:
        pass
    return lines[-max_lines:]

def signal_direction(sig):
    """Normalize any signal string to +1 / -1 / 0."""
    if sig is None:
        return 0
    s = str(sig).upper()
    if any(k in s for k in ["BULL", "ALCIST", "LONG", "BUY", "COMPRA"]):
        return 1
    if any(k in s for k in ["BEAR", "BAJIST", "SHORT", "SELL", "VENTA"]):
        return -1
    return 0


# ═════════════════════════════════════════════════════════════
#  FASE 1 · Multi-Source Signal Extraction
# ═════════════════════════════════════════════════════════════
def extract_all_signals():
    """Read every agent JSON and extract actionable signals."""
    a1  = load("agent1_data.json")  or {}
    a2  = load("agent2_data.json")  or {}
    a3  = load("agent3_data.json")  or {}
    a4  = load("agent4_data.json")  or {}
    a6  = load("agent6_data.json")  or {}
    a7  = load("agent7_data.json")  or {}
    a8  = load("agent8_data.json")  or {}
    a9  = load("agent9_data.json")  or {}
    a14 = load("agent14_orderflow_data.json") or {}
    a11 = load("agent11_data.json") or {}
    bt  = load("agent12_backtest_results.json") or {}
    ict = load("agent10_ict_stats.json") or {}

    # ── Market state from A1/pulse ──
    yahoo = a1.get("yahoo") or {}
    nq_data = yahoo.get("NQ_futures") or yahoo.get("NDX") or {}
    nq_price = nq_data.get("price") if isinstance(nq_data, dict) else nq_data

    sq = a1.get("squeezemetrics") or {}
    dix_val = sq.get("DIX")
    gex_val = sq.get("GEX_raw") or sq.get("GEX_B")

    # ── Individual agent signals ──
    signals = {}

    # A2 COT
    cot_sig = a2.get("signal")
    cot_net = (a2.get("cot") or {}).get("current_net")
    cot_idx = (a2.get("cot") or {}).get("cot_index")
    signals["COT"] = {
        "direction": signal_direction(cot_sig),
        "raw": cot_sig,
        "details": {"net": cot_net, "index": cot_idx},
        "source": "agent2"
    }

    # A3 Volatility
    vol_regime = (a3.get("regime") or a3.get("volatility_regime")
                  or (a3.get("vxn_analysis") or {}).get("level"))
    vol_signal = (a3.get("vxn_analysis") or {}).get("signal")
    vxn_val = (a3.get("raw_inputs") or {}).get("VXN")
    signals["VOLATILITY"] = {
        "direction": signal_direction(vol_signal),
        "raw": vol_signal,
        "details": {"regime": vol_regime, "vxn": vxn_val},
        "source": "agent3"
    }

    # A6 SMC/ICT
    smc_sig = a6.get("signal")
    smc_conf = a6.get("confidence")
    signals["SMC"] = {
        "direction": signal_direction(smc_sig),
        "raw": smc_sig,
        "details": {"confidence": smc_conf,
                    "pd_array": (a6.get("ict") or {}).get("pd_array"),
                    "bias": (a6.get("smc") or {}).get("institution_bias")},
        "source": "agent6"
    }

    # A7 Probability
    a7_exp = a7.get("expectancy_pct")
    a7_conf = a7.get("confidence_pct")
    a7_verdict = a7.get("verdict")
    a7_dir = 1 if (a7_exp or 50) > 55 else (-1 if (a7_exp or 50) < 45 else 0)
    signals["PROBABILITY"] = {
        "direction": a7_dir,
        "raw": a7_verdict,
        "details": {"expectancy": a7_exp, "confidence": a7_conf,
                    "signals_aligned": a7.get("signals_aligned")},
        "source": "agent7"
    }

    # A8 Sentiment
    sent_status = (a8.get("sentiment") or {}).get("status")
    fear_idx = (a8.get("morgan_audit") or {}).get("fear_index")
    inst_align = (a8.get("morgan_audit") or {}).get("institutional_alignment")
    signals["SENTIMENT"] = {
        "direction": 1 if inst_align == "HIGH" and fear_idx == "LOW" else (
                    -1 if fear_idx == "HIGH" else 0),
        "raw": sent_status,
        "details": {"fear_index": fear_idx, "institutional_alignment": inst_align},
        "source": "agent8"
    }

    # A9 Silver Bullet
    sb_status = a9.get("status")
    sb_confluence = a9.get("macro_confluence")
    signals["SILVER_BULLET"] = {
        "direction": signal_direction(sb_confluence),
        "raw": sb_status,
        "details": {"window": a9.get("active_window"),
                    "confluence": sb_confluence},
        "source": "agent9"
    }

    # A14 OrderFlow
    of_bias = a14.get("bias_orderflow")
    of_accept = a14.get("acceptance")
    signals["ORDERFLOW"] = {
        "direction": signal_direction(of_bias),
        "raw": of_bias,
        "details": {"acceptance": of_accept,
                    "sessions": a14.get("sessions")},
        "source": "agent14"
    }

    # A4 Consensus score
    consensus_score = a4.get("global_score", 50)
    consensus_label = a4.get("global_label", "NEUTRAL")

    # ── Backtest info ──
    raw_wr = bt.get("win_rate", bt.get("overall_win_rate", 50))
    if isinstance(raw_wr, str):
        raw_wr = float(raw_wr.replace("%", "").strip())
    win_rate = float(raw_wr) if raw_wr else 50.0

    market_state = {
        "nq_price": nq_price,
        "vxn": vxn_val,
        "dix": dix_val,
        "gex": gex_val,
        "vol_regime": vol_regime,
    }

    return signals, market_state, consensus_score, consensus_label, win_rate, bt


# ═════════════════════════════════════════════════════════════
#  FASE 1b · Adaptive Weight Adjustment
# ═════════════════════════════════════════════════════════════
LAYER_MAP = {
    "layer1": {"name": "Posicionamiento (COT)",     "signals": ["COT"]},
    "layer2": {"name": "Macro & Sentiment",          "signals": ["SENTIMENT"]},
    "layer3": {"name": "Liquidez",                   "signals": []},
    "layer4": {"name": "Timing & Session",           "signals": ["SILVER_BULLET", "VOLATILITY"]},
    "layer5": {"name": "Algorítmico (SMC/Prob)",     "signals": ["SMC", "PROBABILITY"]},
    "layer6": {"name": "Order Flow & Value Profile", "signals": ["ORDERFLOW"]},
}

DEFAULT_WEIGHTS = {
    "layer1": 0.15, "layer2": 0.15, "layer3": 0.12,
    "layer4": 0.13, "layer5": 0.15, "layer6": 0.30
}

def load_weights():
    w = load("ai_weights.json")
    if not w:
        return dict(DEFAULT_WEIGHTS)
    return {k: w.get(k, DEFAULT_WEIGHTS.get(k, 0.2)) for k in DEFAULT_WEIGHTS}

def load_scorecard():
    """Load real outcome data from Agent 16."""
    if not os.path.exists(SCORECARD_FILE):
        return None
    try:
        with open(SCORECARD_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def adjust_weights(current_weights, win_rate, signals, memory, scorecard=None):
    """
    Gradient-based weight adjustment using REAL outcome data when available.
    Falls back to backtest win_rate if no scorecard yet.
    """
    new_w = dict(current_weights)

    # ── Use REAL win rate from outcomes if available ──
    real_wr = None
    if scorecard and scorecard.get("win_rate_real") is not None:
        real_wr = scorecard["win_rate_real"]
        effective_wr = real_wr
        wr_source = "REAL (outcomes)"
    else:
        effective_wr = win_rate
        wr_source = "BACKTEST (estimado)"

    # How far from 55% (our target edge)?
    target = 55.0
    delta = effective_wr - target

    # Scale factor: small adjustments, max ±0.03 per cycle
    scale = max(min(delta / 100.0, 0.03), -0.03)

    # ── Per-agent accuracy adjustments (the real learning) ──
    agent_boosts = {}  # signal_name -> boost factor
    if scorecard and scorecard.get("agent_accuracy"):
        for sig_name, acc_data in scorecard["agent_accuracy"].items():
            acc = acc_data.get("accuracy_pct")
            if acc is not None and acc_data.get("total_calls", 0) >= 3:
                # Agents above 55% get boosted, below 45% get reduced
                agent_boosts[sig_name] = (acc - 50) / 100.0  # e.g. 60% → +0.10

    # Count how many signals in each layer are "active" (non-zero direction)
    layer_activity = {}
    for lk, linfo in LAYER_MAP.items():
        sigs = linfo["signals"]
        if not sigs:
            layer_activity[lk] = 0.5  # neutral for layers with no direct signal mapping
            continue
        active = sum(1 for sn in sigs
                     if signals.get(sn, {}).get("direction", 0) != 0)
        total = len(sigs)
        layer_activity[lk] = active / total if total > 0 else 0

    # ── Apply adjustments ──
    if delta < -3:
        # Below target: use agent accuracy to decide WHO gets more weight
        for lk, linfo in LAYER_MAP.items():
            activity = layer_activity.get(lk, 0)
            # Base adjustment from activity
            base_adj = scale * (activity - 0.5)
            # Accuracy boost: layers with accurate agents get more weight
            acc_boost = 0
            for sig_name in linfo["signals"]:
                if sig_name in agent_boosts:
                    acc_boost += agent_boosts[sig_name] * 0.01  # small per-cycle
            new_w[lk] += base_adj + acc_boost
        status = f"Adaptando — WR {effective_wr:.1f}% [{wr_source}] (bajo target {target}%)"
    elif delta > 5:
        status = f"Reforzado — WR {effective_wr:.1f}% [{wr_source}] (sobre target)"
    else:
        status = f"Equilibrado — WR {effective_wr:.1f}% [{wr_source}] (zona neutral)"

    # Clamp: no layer below 0.05
    for lk in new_w:
        new_w[lk] = max(new_w[lk], 0.05)

    # Normalize to sum = 1.0
    total = sum(new_w.values())
    for lk in new_w:
        new_w[lk] = round(new_w[lk] / total, 4)

    return new_w, status, wr_source


# ═════════════════════════════════════════════════════════════
#  FASE 2 · Memory Snapshot
# ═════════════════════════════════════════════════════════════
def save_memory_snapshot(signals, market_state, consensus_score,
                         weights, old_weights, status, win_rate):
    """Append one snapshot to agent10_memory.jsonl."""
    memory_lines = read_memory()
    cycle = len(memory_lines) + 1

    # Detect patterns
    patterns = []
    dirs = [s.get("direction", 0) for s in signals.values()]
    aligned_bull = sum(1 for d in dirs if d > 0)
    aligned_bear = sum(1 for d in dirs if d < 0)
    total_active = aligned_bull + aligned_bear

    if aligned_bull >= 3 and aligned_bear == 0:
        patterns.append("triple_confluence_bull")
    if aligned_bear >= 3 and aligned_bull == 0:
        patterns.append("triple_confluence_bear")
    if total_active <= 1:
        patterns.append("low_signal_environment")
    if market_state.get("vol_regime") and "EXTREME" in str(market_state["vol_regime"]).upper():
        patterns.append("extreme_volatility")
    elif market_state.get("vol_regime") and "LOW" in str(market_state["vol_regime"]).upper():
        patterns.append("low_vol_regime")

    # Weight changes
    weight_changes = {}
    for lk in weights:
        diff = round(weights[lk] - old_weights.get(lk, weights[lk]), 4)
        if diff != 0:
            weight_changes[lk] = diff

    snapshot = {
        "timestamp": NOW.isoformat(),
        "cycle": cycle,
        "market_state": market_state,
        "agent_signals": {k: {"dir": v["direction"], "raw": v["raw"]}
                          for k, v in signals.items()},
        "consensus": {"score": consensus_score, "win_rate": win_rate},
        "weights_snapshot": weights,
        "weight_changes": weight_changes,
        "patterns_detected": patterns,
        "status": status,
    }

    append_jsonl(MEMORY_FILE, snapshot)
    return snapshot, cycle, patterns


# ═════════════════════════════════════════════════════════════
#  FASE 3 · Knowledge Base Generation
# ═════════════════════════════════════════════════════════════
def generate_knowledge(signals, market_state, weights, win_rate,
                       cycle, patterns, status):
    """Build agent10_knowledge.json with insights, stats, FAQ."""
    memory = read_memory()

    # ─── Pattern frequency ───
    pattern_counts = {}
    for snap in memory:
        for p in snap.get("patterns_detected", []):
            pattern_counts[p] = pattern_counts.get(p, 0) + 1

    # ─── Signal agreement tracking ───
    signal_agreement = {}  # how often each signal aligns with consensus direction
    for snap in memory:
        consensus_dir = 1 if snap.get("consensus", {}).get("score", 50) > 55 else (
                       -1 if snap.get("consensus", {}).get("score", 50) < 45 else 0)
        for sig_name, sig_info in snap.get("agent_signals", {}).items():
            if sig_name not in signal_agreement:
                signal_agreement[sig_name] = {"aligned": 0, "total": 0}
            sig_dir = sig_info.get("dir", 0)
            if sig_dir != 0:
                signal_agreement[sig_name]["total"] += 1
                if sig_dir == consensus_dir:
                    signal_agreement[sig_name]["aligned"] += 1

    # Calculate alignment rates
    agent_perf = {}
    for sig_name, counts in signal_agreement.items():
        rate = round(counts["aligned"] / counts["total"] * 100, 1) if counts["total"] > 5 else None
        agent_perf[sig_name] = {
            "alignment_pct": rate,
            "samples": counts["total"],
            "source": LAYER_MAP.get(sig_name, {}).get("name", sig_name)
        }

    # Best/worst predictors
    ranked = sorted(
        [(k, v) for k, v in agent_perf.items() if v["alignment_pct"] is not None],
        key=lambda x: x[1]["alignment_pct"], reverse=True
    )
    best_predictor = f"{ranked[0][0]} ({ranked[0][1]['alignment_pct']}% alineación)" if ranked else "Insuficientes datos"
    worst_predictor = f"{ranked[-1][0]} ({ranked[-1][1]['alignment_pct']}% alineación)" if ranked else "Insuficientes datos"

    # ─── Weight evolution ───
    weight_deltas = {}
    if len(memory) >= 2:
        first = memory[0].get("weights_snapshot", {})
        last = memory[-1].get("weights_snapshot", {})
        for lk in first:
            d = round(last.get(lk, 0) - first.get(lk, 0), 4)
            if d != 0:
                weight_deltas[lk] = d

    # ─── Build insights ───
    insights = []

    # Pattern insights
    for pname, count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        if count >= 2:
            insights.append({
                "type": "pattern",
                "text": f"'{pname}' detectado {count} veces en {len(memory)} ciclos",
                "confidence": min(50 + count * 5, 95),
                "count": count
            })

    # Weight evolution insights
    for lk, d in weight_deltas.items():
        layer_name = LAYER_MAP.get(lk, {}).get("name", lk)
        direction = "subió" if d > 0 else "bajó"
        insights.append({
            "type": "weight_evolution",
            "text": f"{layer_name} ({lk}) {direction} {abs(d)*100:.1f}% desde el primer ciclo",
            "confidence": 100
        })

    # Data quality insights
    null_fields = [k for k, v in market_state.items() if v is None]
    if null_fields:
        insights.append({
            "type": "warning",
            "text": f"Datos faltantes: {', '.join(null_fields)}",
            "confidence": 100
        })

    # Current alignment
    dirs = [s.get("direction", 0) for s in signals.values()]
    bulls = sum(1 for d in dirs if d > 0)
    bears = sum(1 for d in dirs if d < 0)
    neutrals = sum(1 for d in dirs if d == 0)
    insights.append({
        "type": "current_state",
        "text": f"Ahora: {bulls} señales alcistas, {bears} bajistas, {neutrals} neutrales de {len(signals)} totales",
        "confidence": 100
    })

    # ─── FAQ generation ───
    current_bias = "ALCISTA" if bulls > bears else ("BAJISTA" if bears > bulls else "NEUTRAL")
    active_agents = [k for k, v in signals.items() if v.get("direction", 0) != 0]

    faq = [
        {
            "q": "¿Cuál es el sesgo actual?",
            "a": f"{current_bias} — {bulls} de {len(signals)} señales alineadas. "
                 f"Agentes activos: {', '.join(active_agents) if active_agents else 'ninguno'}"
        },
        {
            "q": "¿Qué agente acierta más?",
            "a": best_predictor if len(memory) > 10 else f"Necesito más datos ({len(memory)} ciclos, mínimo 10)"
        },
        {
            "q": "¿Qué agente acierta menos?",
            "a": worst_predictor if len(memory) > 10 else f"Necesito más datos ({len(memory)} ciclos, mínimo 10)"
        },
        {
            "q": "¿Cuántos ciclos ha analizado?",
            "a": f"{len(memory)} ciclos en memoria. Win rate del backtest: {win_rate:.1f}%"
        },
        {
            "q": "¿Hay algún patrón recurrente?",
            "a": (", ".join(f"{p} ({c}x)" for p, c in sorted(pattern_counts.items(), key=lambda x: -x[1])[:3])
                  if pattern_counts else "Aún no hay suficientes datos para detectar patrones")
        },
        {
            "q": "¿Los pesos han cambiado?",
            "a": ("Sí: " + ", ".join(f"{lk} {'↑' if d>0 else '↓'}{abs(d)*100:.1f}%"
                                      for lk, d in weight_deltas.items())
                  if weight_deltas else "No — los pesos se han mantenido estables")
        }
    ]

    # Build final knowledge
    knowledge = {
        "last_updated": NOW.isoformat(),
        "total_cycles_analyzed": len(memory),
        "current_win_rate": win_rate,
        "current_bias": current_bias,
        "status": status,
        "insights": insights,
        "agent_performance": agent_perf,
        "summary": {
            "best_predictor": best_predictor,
            "worst_predictor": worst_predictor,
        },
        "pattern_history": pattern_counts,
        "weight_evolution": weight_deltas,
        "system_health": {
            "data_quality": f"{round((1 - len(null_fields)/5)*100)}% — {len(null_fields)} campos sin datos" if null_fields else "100% — Todos los datos disponibles",
            "weight_stability": "ESTABLE" if not weight_deltas else "EN AJUSTE",
            "memory_size": len(memory),
        },
        "faq": faq,
        "weights": weights,
    }

    save(KNOWLEDGE_FILE, knowledge)
    return knowledge


# ═════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════
def run():
    print("=" * 60)
    print("  AGENTE 10 · LEARNING ENGINE v4.0 (STUDY MODE)")
    print("=" * 60)
    print()

    # FASE 0: Load real outcome data from Agent 16
    print("📊 FASE 0 — Cargando outcomes reales del Agent 16...")
    scorecard = load_scorecard()
    if scorecard and scorecard.get("win_rate_real") is not None:
        print(f"   ✅ Scorecard cargado: WR Real={scorecard['win_rate_real']}% | {scorecard['validated']} predicciones validadas")
        print(f"   Mejor agente: {scorecard.get('best_agent', '—')}")
        print(f"   Peor agente:  {scorecard.get('worst_agent', '—')}")
    else:
        print(f"   ⏸ Sin datos de outcomes — usando WR del backtester como fallback")
    print()

    # FASE 1: Extract signals from all agents
    print("🔬 FASE 1 — Extrayendo señales de 12 agentes...")
    signals, market, consensus_score, consensus_label, win_rate, bt = extract_all_signals()

    active = [k for k, v in signals.items() if v["direction"] != 0]
    print(f"   Señales activas: {len(active)}/{len(signals)} → {', '.join(active) if active else 'ninguna'}")
    print(f"   Market: NQ={market.get('nq_price')} | VXN={market.get('vxn')} | DIX={market.get('dix')}")
    print(f"   WR Backtest: {win_rate:.1f}%")

    # Adjust weights — NOW WITH REAL OUTCOME DATA
    old_weights = load_weights()
    new_weights, status, wr_source = adjust_weights(
        old_weights, win_rate, signals, read_memory(), scorecard
    )

    # Use real WR if available for knowledge base
    effective_wr = scorecard["win_rate_real"] if (scorecard and scorecard.get("win_rate_real") is not None) else win_rate

    # Save weights
    weight_data = dict(new_weights)
    weight_data["status"] = status
    weight_data["last_learning"] = NOW.isoformat()
    weight_data["version"] = "4.0"
    weight_data["wr_source"] = wr_source
    save(WEIGHTS_FILE, weight_data)
    print(f"   ⚖️  Pesos: {' | '.join(f'{k}={v}' for k,v in new_weights.items())}")
    print(f"   📊 {status}")
    print()

    # FASE 2: Save memory snapshot
    print("💾 FASE 2 — Guardando snapshot en memoria...")
    snapshot, cycle, patterns = save_memory_snapshot(
        signals, market, consensus_score, new_weights, old_weights, status, effective_wr
    )
    print(f"   Ciclo #{cycle} guardado. Patrones: {patterns if patterns else 'ninguno'}")
    print()

    # FASE 3: Generate knowledge base
    print("🧠 FASE 3 — Generando Knowledge Base...")
    knowledge = generate_knowledge(
        signals, market, new_weights, effective_wr, cycle, patterns, status
    )
    n_insights = len(knowledge["insights"])
    n_faq = len(knowledge["faq"])
    print(f"   {n_insights} insights | {n_faq} FAQ | {knowledge['system_health']['memory_size']} ciclos en memoria")
    print(f"   Sesgo actual: {knowledge['current_bias']}")
    print(f"   Best predictor: {knowledge['summary']['best_predictor']}")
    if scorecard:
        print(f"   🎯 WR Real: {scorecard.get('win_rate_real', '—')}% [{wr_source}]")
    print()

    print("✅ Agent 10 v4.0 (Study Mode) completado.")
    return f"Aprendizaje completado — {status}"


if __name__ == "__main__":
    run()
