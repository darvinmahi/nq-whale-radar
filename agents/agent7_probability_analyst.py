"""
AGENT 7 · PROBABILITY ANALYST v2.0
════════════════════════════════════
Calcula la probabilidad matemática de dirección cruzando:
  · COT (Agente 2)       — posicionamiento de Grandes Especuladores
  · SMC (Agente 6)       — estructura institucional del precio
  · Volatilidad (A3)     — régimen de volatilidad actual
  · OrderFlow (A14)      — presión compradora/vendedora en tiempo real

Output: expectancy_pct, confidence, verdict, signals_aligned
"""

import json
import os
import datetime

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent7_data.json")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_json(filename):
    path = os.path.join(BASE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def signal_to_score(signal_str):
    """Convierte strings de señal a (+1 bull, -1 bear, 0 neutral)."""
    if not signal_str:
        return 0
    s = str(signal_str).upper()
    if any(k in s for k in ("BULL", "LONG", "ALCIST", "BUY", "UP")):
        return 1
    if any(k in s for k in ("BEAR", "SHORT", "BAJIST", "SELL", "DOWN")):
        return -1
    return 0


def volatility_multiplier(a3):
    """Reduce la confianza en volatilidad extrema (mercados erráticos)."""
    if not a3:
        return 1.0
    regime = str(a3.get("volatility_regime", "")).upper()
    if "EXTREME" in regime or "VERY HIGH" in regime:
        return 0.9   # 10% de penalización en confianza
    if "HIGH" in regime:
        return 0.95
    if "LOW" in regime:
        return 1.05  # Baja vol = movimientos más predecibles
    return 1.0


# ─── Core ─────────────────────────────────────────────────────────────────────

def calculate_expectancy():
    print("\n" + "=" * 60)
    print("  AGENTE 7 · PROBABILITY ANALYST v2.0")
    print("=" * 60 + "\n")

    # ──────────── Carga de datos ────────────────────────────────
    a2  = load_json("agent2_data.json")   # COT
    a3  = load_json("agent3_data.json")   # Volatility
    a6  = load_json("agent6_data.json")   # SMC
    a14 = load_json("agent14_orderflow_data.json")  # OrderFlow

    missing = [n for n, d in [("A2 COT", a2), ("A6 SMC", a6)] if d is None]
    if missing:
        print(f"⚠️  Datos faltantes: {', '.join(missing)} — saliendo.")
        return

    # ──────────── Señales individuales ──────────────────────────
    # Pesos:  COT=35%  SMC=40%  OrderFlow=25%  (Volatility modula confianza)
    signals = {
        "COT"       : {"raw": a2.get("signal"),               "weight": 0.35},
        "SMC"       : {"raw": a6.get("signal"),               "weight": 0.40},
        "OrderFlow" : {"raw": (a14 or {}).get("bias"),        "weight": 0.25},
    }

    weighted_score = 0.0
    fired_signals  = []
    neutral_signals= []

    for name, info in signals.items():
        score  = signal_to_score(info["raw"])
        contribution = score * info["weight"]
        weighted_score += contribution
        if score != 0:
            fired_signals.append({"name": name, "direction": "BULLISH" if score > 0 else "BEARISH", "weight": info["weight"]})
        else:
            neutral_signals.append(name)

    # ──────────── Cálculo de expectancy ─────────────────────────
    # weighted_score ∈ [-1, +1]  →  expectancy ∈ [0, 100]
    raw_expectancy = round(50 + weighted_score * 50, 1)

    # Ajuste por volatilidad
    vol_mult = volatility_multiplier(a3)

    # Confianza = % de señales alineadas ponderado por pesos
    aligned_weight = sum(s["weight"] for s in fired_signals if s["direction"] == ("BULLISH" if weighted_score > 0 else "BEARISH"))
    confidence_raw = aligned_weight * vol_mult
    confidence_pct = round(min(confidence_raw * 100, 99), 0)

    # Número de señales activas (no neutrales)
    signals_aligned = len([s for s in fired_signals if s["direction"] == ("BULLISH" if weighted_score > 0 else "BEARISH")])
    signals_total   = len(signals)

    # ──────────── Veredicto ─────────────────────────────────────
    if raw_expectancy >= 75:
        verdict       = "ALTA PROBABILIDAD ALCISTA ✅"
        math_bias     = "BULLISH"
    elif raw_expectancy >= 60:
        verdict       = "PROBABILIDAD ALCISTA MODERADA 📈"
        math_bias     = "BULLISH"
    elif raw_expectancy <= 25:
        verdict       = "ALTA PROBABILIDAD BAJISTA 🔻"
        math_bias     = "BEARISH"
    elif raw_expectancy <= 40:
        verdict       = "PROBABILIDAD BAJISTA MODERADA 📉"
        math_bias     = "BEARISH"
    else:
        verdict       = "DISTRIBUCIÓN / NEUTRAL — ESPERAR CLARIDAD ⏳"
        math_bias     = "NEUTRAL"

    # ──────────── Confluencias ──────────────────────────────────
    confluence_label = (
        f"TRIPLE CONFLUENCIA ({signals_aligned}/3)"   if signals_aligned == 3 else
        f"DOBLE CONFLUENCIA ({signals_aligned}/3)"    if signals_aligned == 2 else
        f"SEÑAL AISLADA ({signals_aligned}/3)"        if signals_aligned == 1 else
        "SIN CONFLUENCIA — MERCADO INDECISO"
    )

    # ──────────── Output ────────────────────────────────────────
    output = {
        "agent"           : 7,
        "name"            : "Probability Analyst",
        "version"         : "2.0",
        "timestamp"       : datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "signals_used"    : [{"name": k, "raw_signal": v["raw"], "weight": v["weight"]} for k, v in signals.items()],
        "signals_aligned" : signals_aligned,
        "signals_neutral" : neutral_signals,
        "confluences": {
            "label"           : confluence_label,
            "cot_smc_match"   : signal_to_score(a2.get("signal")) == signal_to_score(a6.get("signal")) != 0,
            "expectancy_pct"  : raw_expectancy,
            "confidence_pct"  : confidence_pct,
            "weighted_score"  : round(weighted_score, 4),
            "vol_regime"      : (a3 or {}).get("volatility_regime", "UNKNOWN"),
            "vol_multiplier"  : vol_mult,
        },
        "verdict"         : verdict,
        "math_bias"       : math_bias,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"📊 {confluence_label}")
    print(f"📈 Expectancy: {raw_expectancy}% | Confianza: {confidence_pct}%")
    print(f"🎯 Veredicto: {verdict}")
    print(f"   Señales: COT={a2.get('signal')} | SMC={a6.get('signal')} | OrderFlow={(a14 or {}).get('bias','N/A')}")
    if a3:
        print(f"   Volatilidad: {a3.get('volatility_regime','?')} (mult={vol_mult})")
    print(f"\n✅ agent7_data.json actualizado.\n")


def run():
    calculate_expectancy()


if __name__ == "__main__":
    run()
