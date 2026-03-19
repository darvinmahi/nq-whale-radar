"""
AGENTE 16 — OUTCOME TRACKER (NQ Intelligence Engine)
═══════════════════════════════════════════════════════════
El eslabón que faltaba: cierra el feedback loop.

Cada ciclo:
  1. Lee la predicción del ciclo anterior (de agent16_pending.json)
  2. Compara con el precio real actual
  3. Marca outcome: WIN / LOSS / NEUTRAL
  4. Calcula per-agent accuracy (quién acertó más)
  5. Guarda historial en agent16_outcomes.jsonl
  6. Genera agent16_scorecard.json (stats acumuladas)

Outputs:
  - agent16_pending.json      (predicción pendiente de validar)
  - agent16_outcomes.jsonl    (historial append-only)
  - agent16_scorecard.json    (stats: win rate, per-agent accuracy, streaks)
"""

import json
import os
import datetime

BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PENDING_FILE   = os.path.join(BASE_DIR, "agent16_pending.json")
OUTCOMES_FILE  = os.path.join(BASE_DIR, "agent16_outcomes.jsonl")
SCORECARD_FILE = os.path.join(BASE_DIR, "agent16_scorecard.json")

NOW = datetime.datetime.now(datetime.timezone.utc)

# Minimum price movement (points) to count as a valid directional move
MIN_MOVE_POINTS = 5.0


# ─────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────
def load_json(filename):
    p = os.path.join(BASE_DIR, filename)
    if not os.path.exists(p):
        return None
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def append_jsonl(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def read_outcomes(max_lines=500):
    """Read outcome history."""
    if not os.path.exists(OUTCOMES_FILE):
        return []
    results = []
    try:
        with open(OUTCOMES_FILE, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if raw:
                    try:
                        results.append(json.loads(raw))
                    except Exception:
                        pass
    except Exception:
        pass
    return results[-max_lines:]

def signal_direction(sig):
    """Normalize signal to +1 / -1 / 0."""
    if sig is None:
        return 0
    s = str(sig).upper()
    if any(k in s for k in ["BULL", "ALCIST", "LONG", "BUY", "COMPRA"]):
        return 1
    if any(k in s for k in ["BEAR", "BAJIST", "SHORT", "SELL", "VENTA"]):
        return -1
    return 0


# ═════════════════════════════════════════════════════════════
#  FASE 1 · Validate Previous Prediction
# ═════════════════════════════════════════════════════════════
def get_current_price():
    """Get NQ price from available sources."""
    # Try pulse_data first (freshest)
    pulse = load_json("pulse_data.json")
    if pulse:
        nq = (pulse.get("market") or {}).get("NQ", {})
        if nq.get("price"):
            return float(nq["price"])

    # Try agent1_data
    a1 = load_json("agent1_data.json")
    if a1:
        yahoo = a1.get("yahoo") or {}
        nq_data = yahoo.get("NQ_futures") or yahoo.get("NDX") or {}
        if isinstance(nq_data, dict) and nq_data.get("price"):
            return float(nq_data["price"])

    return None

def validate_pending():
    """
    Compare pending prediction with current price.
    Returns (outcome_record, was_validated) or (None, False).
    """
    if not os.path.exists(PENDING_FILE):
        return None, False

    try:
        with open(PENDING_FILE, "r", encoding="utf-8") as f:
            pending = json.load(f)
    except Exception:
        return None, False

    if not pending or not pending.get("prediction_price"):
        return None, False

    current_price = get_current_price()
    if current_price is None:
        print("  ⚠️ No hay precio actual — no puedo validar la predicción anterior")
        return None, False

    pred_price = pending["prediction_price"]
    pred_bias  = pending.get("prediction_bias", "NEUTRAL")
    pred_score = pending.get("prediction_score", 50)
    agent_signals = pending.get("agent_signals", {})

    # Calculate actual price movement
    price_delta = current_price - pred_price
    actual_direction = 0
    if abs(price_delta) >= MIN_MOVE_POINTS:
        actual_direction = 1 if price_delta > 0 else -1

    # Determine predicted direction from bias
    pred_direction = 0
    if pred_score > 55:
        pred_direction = 1
    elif pred_score < 45:
        pred_direction = -1

    # Outcome
    if actual_direction == 0:
        outcome = "NEUTRAL"  # price didn't move enough
    elif pred_direction == 0:
        outcome = "NEUTRAL"  # prediction was neutral (no call)
    elif pred_direction == actual_direction:
        outcome = "WIN"
    else:
        outcome = "LOSS"

    # Per-agent accuracy
    agent_results = {}
    for name, sig_info in agent_signals.items():
        sig_dir = sig_info.get("dir", 0)
        if sig_dir == 0:
            agent_results[name] = "NEUTRAL"
        elif actual_direction == 0:
            agent_results[name] = "NEUTRAL"
        elif sig_dir == actual_direction:
            agent_results[name] = "WIN"
        else:
            agent_results[name] = "LOSS"

    outcome_record = {
        "timestamp": NOW.isoformat(),
        "prediction_time": pending.get("timestamp"),
        "prediction_price": pred_price,
        "validation_price": current_price,
        "price_delta": round(price_delta, 2),
        "prediction_bias": pred_bias,
        "prediction_score": pred_score,
        "predicted_direction": pred_direction,
        "actual_direction": actual_direction,
        "outcome": outcome,
        "agent_results": agent_results,
    }

    return outcome_record, True


# ═════════════════════════════════════════════════════════════
#  FASE 2 · Save New Prediction (for next cycle)
# ═════════════════════════════════════════════════════════════
def save_new_prediction():
    """Save current state as the next prediction to validate."""
    a4 = load_json("agent4_data.json") or {}
    current_price = get_current_price()

    # Get agent signals from memory if available
    memory_lines = []
    mem_path = os.path.join(BASE_DIR, "agent10_memory.jsonl")
    if os.path.exists(mem_path):
        try:
            with open(mem_path, "r", encoding="utf-8") as f:
                for raw in f:
                    raw = raw.strip()
                    if raw:
                        try:
                            memory_lines.append(json.loads(raw))
                        except Exception:
                            pass
        except Exception:
            pass

    # Get latest agent signals
    agent_signals = {}
    if memory_lines:
        latest = memory_lines[-1]
        agent_signals = latest.get("agent_signals", {})

    pending = {
        "timestamp": NOW.isoformat(),
        "prediction_price": current_price,
        "prediction_bias": a4.get("global_label", "NEUTRAL"),
        "prediction_score": a4.get("global_score", 50),
        "agent_signals": agent_signals,
    }

    save_json(PENDING_FILE, pending)
    return pending


# ═════════════════════════════════════════════════════════════
#  FASE 3 · Generate Scorecard
# ═════════════════════════════════════════════════════════════
def generate_scorecard(outcomes):
    """Build cumulative stats from all outcomes."""
    if not outcomes:
        return {
            "total_predictions": 0,
            "validated": 0,
            "win_rate_real": None,
            "wins": 0, "losses": 0, "neutrals": 0,
            "current_streak": {"type": "NONE", "count": 0},
            "agent_accuracy": {},
            "last_10_outcomes": [],
            "status": "ESPERANDO DATOS — Ejecutar al menos 2 ciclos",
        }

    wins     = sum(1 for o in outcomes if o["outcome"] == "WIN")
    losses   = sum(1 for o in outcomes if o["outcome"] == "LOSS")
    neutrals = sum(1 for o in outcomes if o["outcome"] == "NEUTRAL")
    decided  = wins + losses  # exclude neutrals from win rate

    win_rate_real = round(wins / decided * 100, 1) if decided > 0 else None

    # Current streak
    streak_type = "NONE"
    streak_count = 0
    for o in reversed(outcomes):
        if o["outcome"] == "NEUTRAL":
            continue
        if streak_type == "NONE":
            streak_type = o["outcome"]
            streak_count = 1
        elif o["outcome"] == streak_type:
            streak_count += 1
        else:
            break

    # Per-agent accuracy
    agent_stats = {}
    for o in outcomes:
        for agent_name, result in o.get("agent_results", {}).items():
            if agent_name not in agent_stats:
                agent_stats[agent_name] = {"wins": 0, "losses": 0, "neutrals": 0}
            if result == "WIN":
                agent_stats[agent_name]["wins"] += 1
            elif result == "LOSS":
                agent_stats[agent_name]["losses"] += 1
            else:
                agent_stats[agent_name]["neutrals"] += 1

    agent_accuracy = {}
    for name, stats in agent_stats.items():
        decided_a = stats["wins"] + stats["losses"]
        accuracy = round(stats["wins"] / decided_a * 100, 1) if decided_a > 0 else None
        agent_accuracy[name] = {
            "accuracy_pct": accuracy,
            "wins": stats["wins"],
            "losses": stats["losses"],
            "neutrals": stats["neutrals"],
            "total_calls": decided_a,
        }

    # Last 10 outcomes (for dashboard display)
    last_10 = [
        {
            "time": o.get("prediction_time", ""),
            "outcome": o["outcome"],
            "delta": o.get("price_delta", 0),
            "bias": o.get("prediction_bias", ""),
        }
        for o in outcomes[-10:]
    ]

    # Best/worst agents
    ranked = sorted(
        [(k, v) for k, v in agent_accuracy.items() if v["accuracy_pct"] is not None],
        key=lambda x: x[1]["accuracy_pct"], reverse=True
    )
    best_agent  = f"{ranked[0][0]} ({ranked[0][1]['accuracy_pct']}%)" if ranked else "—"
    worst_agent = f"{ranked[-1][0]} ({ranked[-1][1]['accuracy_pct']}%)" if ranked else "—"

    # Status
    if decided < 5:
        status = f"APRENDIENDO — {decided} predicciones validadas (mínimo 5)"
    elif win_rate_real and win_rate_real >= 55:
        status = f"RENTABLE — WR {win_rate_real}% ✅"
    elif win_rate_real and win_rate_real >= 50:
        status = f"NEUTRAL — WR {win_rate_real}% (target: 55%)"
    else:
        status = f"EN AJUSTE — WR {win_rate_real}% (bajo target)"

    scorecard = {
        "generated_at": NOW.isoformat(),
        "total_predictions": len(outcomes),
        "validated": decided,
        "win_rate_real": win_rate_real,
        "wins": wins,
        "losses": losses,
        "neutrals": neutrals,
        "current_streak": {"type": streak_type, "count": streak_count},
        "agent_accuracy": agent_accuracy,
        "best_agent": best_agent,
        "worst_agent": worst_agent,
        "last_10_outcomes": last_10,
        "status": status,
    }

    save_json(SCORECARD_FILE, scorecard)
    return scorecard


# ═════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════
def run():
    print("=" * 60)
    print("  AGENTE 16 · OUTCOME TRACKER v1.0")
    print("=" * 60)
    print()

    # FASE 1: Validate previous prediction
    print("🔍 FASE 1 — Validando predicción anterior...")
    outcome_record, was_validated = validate_pending()

    if was_validated and outcome_record:
        append_jsonl(OUTCOMES_FILE, outcome_record)
        emoji = {"WIN": "✅", "LOSS": "❌", "NEUTRAL": "⚪"}.get(outcome_record["outcome"], "?")
        print(f"   {emoji} Resultado: {outcome_record['outcome']}")
        print(f"      Predicción: {outcome_record['prediction_price']} → Real: {outcome_record['validation_price']}")
        print(f"      Delta: {outcome_record['price_delta']:+.2f} pts")
        print(f"      Bias predecido: {outcome_record['prediction_bias']} (score {outcome_record['prediction_score']})")
    elif not os.path.exists(PENDING_FILE):
        print("   ℹ️ Primera ejecución — no hay predicción anterior para validar")
    else:
        print("   ⏸ No se pudo validar (datos insuficientes)")
    print()

    # FASE 2: Save current prediction for next cycle
    print("💾 FASE 2 — Guardando predicción actual para validar en el próximo ciclo...")
    new_pred = save_new_prediction()
    if new_pred.get("prediction_price"):
        print(f"   📌 Predicción guardada: NQ {new_pred['prediction_price']} | Bias: {new_pred['prediction_bias']} ({new_pred['prediction_score']}/100)")
    else:
        print("   ⚠️ No hay precio disponible para guardar predicción")
    print()

    # FASE 3: Generate scorecard
    print("📊 FASE 3 — Generando Scorecard...")
    all_outcomes = read_outcomes()
    scorecard = generate_scorecard(all_outcomes)
    print(f"   Total validadas: {scorecard['validated']}")
    if scorecard["win_rate_real"] is not None:
        print(f"   Win Rate Real: {scorecard['win_rate_real']}%")
    else:
        print(f"   Win Rate Real: — (esperando más datos)")
    print(f"   Racha actual: {scorecard['current_streak']['count']}x {scorecard['current_streak']['type']}")
    if scorecard.get("best_agent") and scorecard["best_agent"] != "—":
        print(f"   Mejor agente: {scorecard['best_agent']}")
        print(f"   Peor agente:  {scorecard['worst_agent']}")
    print(f"   Estado: {scorecard['status']}")
    print()

    print("✅ Agent 16 completado.")
    return scorecard.get("status", "OK")


if __name__ == "__main__":
    run()
