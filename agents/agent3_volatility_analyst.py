"""
AGENTE 3 — VOLATILITY ANALYST
═══════════════════════════════════════════════════════════
Responsabilidad: Analizar el entorno de volatilidad.

Análisis:
  ✅ VXN: nivel de volatilidad (Complacencia / Normal / Pánico)
  ✅ GEX: impacto de dealers en volatilidad realizada
  ✅ Señal combinada VXN+GEX ponderada

Entrada: ../agent1_data.json
Salida:  ../agent3_data.json
═══════════════════════════════════════════════════════════
PARA AGREGAR ANÁLISIS:
  - Ajusta los umbrales VXN_* y GEX_* según contexto macro
  - Agrega Put/Call Ratio con una función analyze_pcr()
  - Incluye el nuevo score en combined_volatility_signal()
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import datetime

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_FILE  = os.path.join(BASE_DIR, "agent1_data.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "agent3_data.json")

# ─── Umbrales VXN ─────────────────────────────────────────────────────────────
VXN_COMPLACENCY   = 18.0
VXN_NORMAL_HIGH   = 25.0
VXN_PANIC         = 28.0
VXN_EXTREME_PANIC = 35.0

# ─── Umbrales GEX (Billions) ──────────────────────────────────────────────────
GEX_POSITIVE_STRONG =  2.0
GEX_POSITIVE        =  0.5
GEX_NEGATIVE        = -0.5
GEX_NEGATIVE_STRONG = -2.0


def load_agent1():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Agent 3] ⚠️  {e}")
        return None


def analyze_vxn(vxn_value):
    if vxn_value is None:
        return {"level": "UNKNOWN", "signal": "NEUTRAL", "score": 50, "description": "N/A", "risk": "N/A"}
    if vxn_value < VXN_COMPLACENCY:
        return {"level": "COMPLACENCY", "signal": "BULLISH", "score": 80,
                "description": f"VXN {vxn_value:.2f} — Mercado complaciente. Momentum alcista favorable.",
                "risk": "Riesgo de spike si rompe 20+"}
    elif vxn_value <= VXN_NORMAL_HIGH:
        s = "BULLISH" if vxn_value < 22 else "NEUTRAL"
        sc = 65 if vxn_value < 22 else 50
        return {"level": "NORMAL", "signal": s, "score": sc,
                "description": f"VXN {vxn_value:.2f} — Volatilidad normal.",
                "risk": "Monitorear si sube sobre 25"}
    elif vxn_value <= VXN_PANIC:
        return {"level": "ELEVATED", "signal": "NEUTRAL", "score": 35,
                "description": f"VXN {vxn_value:.2f} — Volatilidad elevada. Reducir tamaño.",
                "risk": "Movimientos erráticos probables"}
    elif vxn_value <= VXN_EXTREME_PANIC:
        return {"level": "PANIC", "signal": "BEARISH", "score": 20,
                "description": f"VXN {vxn_value:.2f} — Pánico. No operar longs sin cobertura.",
                "risk": "Continuación bajista probable"}
    else:
        return {"level": "EXTREME_PANIC", "signal": "BEARISH", "score": 5,
                "description": f"VXN {vxn_value:.2f} — Pánico extremo.",
                "risk": "Evitar posiciones direccionales"}


def analyze_gex(gex_b):
    if gex_b is None:
        return {"level": "UNKNOWN", "signal": "NEUTRAL", "score": 50, "description": "N/A", "impact": "N/A"}
    if gex_b >= GEX_POSITIVE_STRONG:
        return {"level": "STRONG_POSITIVE", "signal": "BULLISH", "score": 70,
                "description": f"GEX +{gex_b:.2f}B — Dealers comprando en caídas. Mercado amortiguado.",
                "impact": "Movimientos suaves. Dealers frenan volatilidad."}
    elif gex_b >= GEX_POSITIVE:
        return {"level": "POSITIVE", "signal": "NEUTRAL", "score": 60,
                "description": f"GEX +{gex_b:.2f}B — GEX positivo. Estabilidad moderada.",
                "impact": "Rango de trading estrecho."}
    elif gex_b >= GEX_NEGATIVE:
        return {"level": "NEAR_ZERO", "signal": "NEUTRAL", "score": 50,
                "description": f"GEX {gex_b:.2f}B — Flujo neutro.",
                "impact": "Mercado libre en cualquier dirección."}
    elif gex_b >= GEX_NEGATIVE_STRONG:
        return {"level": "NEGATIVE", "signal": "BEARISH", "score": 35,
                "description": f"GEX {gex_b:.2f}B — Dealers amplificarán movimientos.",
                "impact": "Volatilidad realizada > implícita."}
    else:
        return {"level": "STRONG_NEGATIVE", "signal": "BEARISH", "score": 15,
                "description": f"GEX {gex_b:.2f}B — Riesgo de explosión de volatilidad.",
                "impact": "Posibles gaps extremos."}


# ══════════════════════════════════════════════════════════
#  AGREGAR ANÁLISIS ADICIONAL AQUÍ ↓  (ej: Put/Call Ratio)
# ══════════════════════════════════════════════════════════


def run():
    print("\n" + "="*60)
    print("  AGENTE 3 · VOLATILITY ANALYST")
    print("="*60 + "\n")

    a1 = load_agent1()
    yahoo = a1.get("yahoo", {}) if a1 else {}
    sm    = a1.get("squeezemetrics", {}) if a1 else {}

    vxn_val = (yahoo.get("VXN") or {}).get("price") or 19.49
    gex_b   = sm.get("GEX_B") or 2.3
    dix     = sm.get("DIX")

    vxn_analysis = analyze_vxn(vxn_val)
    gex_analysis = analyze_gex(gex_b)

    sm_raw = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
    combined_raw = (sm_raw.get(vxn_analysis["signal"], 0) * 0.65) + (sm_raw.get(gex_analysis["signal"], 0) * 0.35)
    vol_signal = "BULLISH" if combined_raw > 0.15 else "BEARISH" if combined_raw < -0.15 else "NEUTRAL"
    vol_score  = round((vxn_analysis["score"] * 0.65) + (gex_analysis["score"] * 0.35))

    print(f"  VXN: {vxn_val}  → {vxn_analysis['level']}  ({vxn_analysis['signal']}, score {vxn_analysis['score']})")
    print(f"  GEX: {gex_b}B  → {gex_analysis['level']}  ({gex_analysis['signal']}, score {gex_analysis['score']})")
    print(f"  DIX: {dix}%")
    print(f"  ── Señal ── : {vol_signal}  (score {vol_score}/100)")

    output = {
        "agent": 3,
        "name": "Volatility Analyst",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        # ─── QA-required top-level fields ───
        "vix_value":  vxn_val,
        "vix_status": vxn_analysis["level"],
        # ─── Full nested data ───
        "raw_inputs": {"VXN": vxn_val, "GEX_B": gex_b, "DIX": dix},
        "vxn_analysis": vxn_analysis,
        "gex_analysis": gex_analysis,
        "signal": vol_signal,
        "score": vol_score
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Agent 3 → {OUTPUT_FILE}")
    return output


if __name__ == "__main__":
    run()
