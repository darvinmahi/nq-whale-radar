import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import datetime

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent4_data.json")

# ─── Configuración Neural ──────────────────────────────────────────────────
WEIGHTS_FILE = os.path.join(BASE_DIR, "ai_weights.json")

DEFAULT_WEIGHTS = {
    "layer1": 0.20, # Posicionamiento (COT)
    "layer2": 0.15, # Macro (DXY/US10Y)
    "layer3": 0.12, # Liquidez (VXN/GEX)
    "layer4": 0.08, # Timing (DIX/OI)
    "layer5": 0.15, # Algorithmic (SMC/Prob)
    "layer6": 0.30  # Order Flow & Value Profile (POC/VAH/VAL)
}

def load_neural_weights():
    if os.path.exists(WEIGHTS_FILE):
        try:
            with open(WEIGHTS_FILE, "r") as f:
                learned = json.load(f)
                valid = {k: float(learned[k]) for k in DEFAULT_WEIGHTS if k in learned}
                if len(valid) == len(DEFAULT_WEIGHTS):
                    return valid
        except: pass
    return DEFAULT_WEIGHTS

BIAS_THRESHOLDS = {
    "STRONG_BULLISH": 75,
    "BULLISH":        60,
    "NEUTRAL_HIGH":   52,
    "NEUTRAL_LOW":    48,
    "BEARISH":        40,
    "STRONG_BEARISH": 25,
}

def load_json(filename):
    try:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path): return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Agent 4] ⚠️ Error leyendo {filename}: {e}")
        return {}

def dix_to_score(dix_pct):
    if dix_pct is None: return 50
    if dix_pct >= 50:   return 85
    elif dix_pct >= 47: return 70
    elif dix_pct >= 44: return 55
    elif dix_pct >= 40: return 45
    else:               return 25

def oi_to_score(oi, nq_price_chg=None):
    if not oi: return 50
    if nq_price_chg is not None:
        if nq_price_chg < -0.5: return 30
        elif nq_price_chg > 0.5: return 70
    return 50

def score_to_bias_label(score):
    if score >= BIAS_THRESHOLDS["STRONG_BULLISH"]: return "STRONG BULLISH", "🟢"
    elif score >= BIAS_THRESHOLDS["BULLISH"]:      return "BULLISH", "🟩"
    elif score >= BIAS_THRESHOLDS["NEUTRAL_HIGH"]: return "NEUTRAL-BULLISH", "🔵"
    elif score >= BIAS_THRESHOLDS["NEUTRAL_LOW"]:  return "NEUTRAL", "⚪"
    elif score >= BIAS_THRESHOLDS["BEARISH"]:      return "NEUTRAL-BEARISH", "🟡"
    elif score >= BIAS_THRESHOLDS["STRONG_BEARISH"]: return "BEARISH", "🔴"
    else:                                           return "STRONG BEARISH", "💀"

def run():
    print("🧠 [BIAS ENGINE]: Calculando sesgo con inteligencia neural (Order Flow Focus)...")
    
    a1 = load_json("agent1_data.json")
    a2 = load_json("agent2_data.json")
    a3 = load_json("agent3_data.json")
    a6 = load_json("agent6_data.json")
    a7 = load_json("agent7_data.json")
    a14 = load_json("agent14_orderflow_data.json")

    # Scores base
    cot_strength = a2.get("strength", 50)
    cot_signal   = a2.get("signal", "NEUTRAL")
    cot_score    = cot_strength if cot_signal == "BULLISH" else (100 - cot_strength) if cot_signal == "BEARISH" else 50

    vxn_score    = a3.get("vxn_analysis", {}).get("score", 50)
    gex_score    = a3.get("gex_analysis", {}).get("score", 50)
    dix_raw      = a3.get("raw_inputs", {}).get("DIX") or a1.get("squeezemetrics", {}).get("DIX")
    dix_score    = dix_to_score(dix_raw)
    nq_chg       = (a1.get("yahoo", {}).get("NQ_futures") or {}).get("change_pct")
    oi_score     = oi_to_score(a1.get("cme", {}).get("NQ1_OI"), nq_price_chg=nq_chg)
    
    smc_score    = 75 if a6.get("signal") == "BULLISH" else 25 if a6.get("signal") == "BEARISH" else 50
    prob_score   = a7.get("confluences", {}).get("expectancy_pct", 50)

    # NEW: Order Flow Layer
    of_bias = a14.get("bias_orderflow", "NEUTRAL")
    of_score = 85 if of_bias == "BULLISH" else 15 if of_bias == "BEARISH" else 50

    # ─── MULTI-LAYER INTEGRATION ───
    layer1 = cot_score
    us10y_chg = (a1.get("yahoo", {}).get("US10Y") or {}).get("change_pct", 0)
    dxy_chg   = (a1.get("yahoo", {}).get("DXY") or {}).get("change_pct", 0)
    layer2 = min(max(50 - (us10y_chg * 5) - (dxy_chg * 5), 10), 90)
    layer3 = (vxn_score * 0.6) + (gex_score * 0.4)
    layer4 = (dix_score * 0.7) + (oi_score * 0.3)
    layer5 = (smc_score * 0.6) + (prob_score * 0.4)
    layer6 = of_score

    # Load dynamic weights
    W = load_neural_weights()

    global_score = round(
        (layer1 * W["layer1"]) +
        (layer2 * W["layer2"]) +
        (layer3 * W["layer3"]) +
        (layer4 * W["layer4"]) +
        (layer5 * W["layer5"]) +
        (layer6 * W["layer6"])
    )
    
    label, icon = score_to_bias_label(global_score)
    
    # Compose verdict string for QA Commander
    verdicts = {
        "STRONG BULLISH": "Alta convicción alcista — favorecer longs con gestión activa.",
        "BULLISH": "Sesgo alcista confirmado — buscar entradas en retrasos.",
        "NEUTRAL-BULLISH": "Ligera inclinación alcista — esperar confirmación.",
        "NEUTRAL": "Sin sesgo claro — operar el rango o esperar catalizador.",
        "NEUTRAL-BEARISH": "Ligera inclinación bajista — preferir coberturas.",
        "BEARISH": "Sesgo bajista confirmado — evitar longs agresivos.",
        "STRONG BEARISH": "Alta convicción bajista — solo lados cortos o liquidez.",
    }
    verdict_text = f"{icon} {label} ({global_score}/100) — {verdicts.get(label, 'Sin recomendación.')}"

    output = {
        "agent": 4,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        # ─── QA-required top-level field ───
        "verdict": verdict_text,
        "global_score": global_score,
        "global_label": label,
        "icon": icon,
        "layers": {
            "positioning": layer1,
            "macro": layer2,
            "liquidity": layer3,
            "timing": layer4,
            "algorithmic": layer5,
            "order_flow": layer6
        }
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Sesgo Neural (OF Focus): {global_score}/100 ({label})")
    return output

if __name__ == "__main__":
    run()
