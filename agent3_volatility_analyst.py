"""
AGENTE 3 — VOLATILITY ANALYST
Responsabilidad: Analizar VXN, GEX y métricas de opciones para
  determinar el estado de volatilidad del mercado y riesgo.
  - VXN < 18 → Complacencia (Alcista corto plazo, riesgo de spike)
  - VXN 18–25 → Normal
  - VXN > 25 → Pánico / Precaución
  - GEX positivo → Dealers frenan movimiento (menor volatilidad realizada)
  - GEX negativo → Dealers amplifican movimiento (mayor volatilidad)

Entrada: agent1_data.json
Salida:  agent3_data.json
"""

import json
import datetime


# ─── Umbrales VXN ─────────────────────────────────────────────────────────────
VXN_COMPLACENCY    = 18.0
VXN_NORMAL_LOW     = 18.0
VXN_NORMAL_HIGH    = 25.0
VXN_PANIC          = 28.0
VXN_EXTREME_PANIC  = 35.0

# ─── Umbrales GEX (en Billions) ───────────────────────────────────────────────
GEX_POSITIVE_STRONG  =  2.0   # Muy positivo → mercado muy estable
GEX_POSITIVE         =  0.5
GEX_NEGATIVE         = -0.5
GEX_NEGATIVE_STRONG  = -2.0   # Muy negativo → volatilidad explosiva esperada


def load_agent1():
    try:
        with open("agent1_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Agent 3] ⚠️  No se pudo leer agent1_data.json: {e}")
        return None


def analyze_vxn(vxn_value):
    """Clasifica el nivel de VXN y da señal de volatilidad."""
    if vxn_value is None:
        return {"level": "UNKNOWN", "signal": "NEUTRAL", "score": 50, "description": "Dato no disponible"}

    if vxn_value < VXN_COMPLACENCY:
        level   = "COMPLACENCY"
        signal  = "BULLISH"       # Bajo miedo → favorable para longs corto plazo
        score   = 80
        desc    = f"VXN {vxn_value:.2f} — Mercado complaciente. Condición favorable para momentum alcista."
        risk    = "Riesgo de spike de volatilidad si rompe 20+"
    elif vxn_value <= VXN_NORMAL_HIGH:
        level   = "NORMAL"
        signal  = "BULLISH" if vxn_value < 22 else "NEUTRAL"
        score   = 65 if vxn_value < 22 else 50
        desc    = f"VXN {vxn_value:.2f} — Volatilidad normal. Entorno operativo estándar."
        risk    = "Monitorear si sube sobre 25"
    elif vxn_value <= VXN_PANIC:
        level   = "ELEVATED"
        signal  = "NEUTRAL"
        score   = 35
        desc    = f"VXN {vxn_value:.2f} — Volatilidad elevada. Reducir tamaño de posiciones."
        risk    = "Probable continuación de movimientos erráticos"
    elif vxn_value <= VXN_EXTREME_PANIC:
        level   = "PANIC"
        signal  = "BEARISH"
        score   = 20
        desc    = f"VXN {vxn_value:.2f} — Pánico. No operar longs sin cobertura."
        risk    = "Alta probabilidad de continuación bajista"
    else:
        level   = "EXTREME_PANIC"
        signal  = "BEARISH"
        score   = 5
        desc    = f"VXN {vxn_value:.2f} — Pánico extremo. Mercado disfuncional."
        risk    = "Evitar posiciones direccionales"

    return {"level": level, "signal": signal, "score": score, "description": desc, "risk": risk}


def analyze_gex(gex_b):
    """Clasifica el GEX y su impacto en volatilidad realizada."""
    if gex_b is None:
        return {"level": "UNKNOWN", "signal": "NEUTRAL", "score": 50, "description": "Dato no disponible"}

    if gex_b >= GEX_POSITIVE_STRONG:
        level   = "STRONG_POSITIVE"
        signal  = "BULLISH"
        score   = 70
        desc    = f"GEX +{gex_b:.2f}B — Dealers comprando en caídas. Mercado amortiguado."
        impact  = "Los dealers frenan la volatilidad. Movimientos más suaves."
    elif gex_b >= GEX_POSITIVE:
        level   = "POSITIVE"
        signal  = "NEUTRAL"
        score   = 60
        desc    = f"GEX +{gex_b:.2f}B — GEX levemente positivo. Estabilidad moderada."
        impact  = "Rango de trading estrecho esperado."
    elif gex_b >= GEX_NEGATIVE:
        level   = "NEAR_ZERO"
        signal  = "NEUTRAL"
        score   = 50
        desc    = f"GEX {gex_b:.2f}B — GEX cerca de cero. Flujo de dealers neutro."
        impact  = "Mercado puede moverse libremente en cualquier dirección."
    elif gex_b >= GEX_NEGATIVE_STRONG:
        level   = "NEGATIVE"
        signal  = "BEARISH"
        score   = 35
        desc    = f"GEX {gex_b:.2f}B — GEX negativo. Dealers amplificarán movimientos."
        impact  = "Volatilidad realizada puede exceder la implícita."
    else:
        level   = "STRONG_NEGATIVE"
        signal  = "BEARISH"
        score   = 15
        desc    = f"GEX {gex_b:.2f}B — GEX muy negativo. Riesgo de explosión de volatilidad."
        impact  = "Condición de alta peligrosidad. Posibles gap extremos."

    return {"level": level, "signal": signal, "score": score, "description": desc, "impact": impact}


def combined_volatility_signal(vxn_signal, gex_signal, vxn_score, gex_score):
    """
    Combina VXN (peso 65%) + GEX (peso 35%) en una señal de volatilidad consolidada.
    Score 0–100: más alto = entorno más favorable para operar largo.
    """
    composite = (vxn_score * 0.65) + (gex_score * 0.35)
    composite = round(composite)

    signal_map = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
    combined_raw = (signal_map.get(vxn_signal, 0) * 0.65) + (signal_map.get(gex_signal, 0) * 0.35)

    if combined_raw > 0.15:
        combined_signal = "BULLISH"
    elif combined_raw < -0.15:
        combined_signal = "BEARISH"
    else:
        combined_signal = "NEUTRAL"

    return combined_signal, composite


def run():
    print("\n" + "="*60)
    print("  AGENTE 3 · VOLATILITY ANALYST · INICIO")
    print("="*60 + "\n")

    a1 = load_agent1()

    # Extraer datos del Agente 1
    yahoo = a1.get("yahoo", {}) if a1 else {}
    sm    = a1.get("squeezemetrics", {}) if a1 else {}

    vxn_data = yahoo.get("VXN", {}) or {}
    vxn_val  = vxn_data.get("price")
    gex_b    = sm.get("GEX_B")
    dix      = sm.get("DIX")

    # Usar fallbacks si los datos no están disponibles
    if vxn_val is None:
        print("  ⚠️  VXN no disponible, usando valor de referencia 19.49")
        vxn_val = 19.49
    if gex_b is None:
        print("  ⚠️  GEX no disponible, usando valor de referencia +2.3B")
        gex_b = 2.3

    vxn_analysis = analyze_vxn(vxn_val)
    gex_analysis = analyze_gex(gex_b)
    vol_signal, vol_score = combined_volatility_signal(
        vxn_analysis["signal"], gex_analysis["signal"],
        vxn_analysis["score"], gex_analysis["score"]
    )

    print(f"  VXN: {vxn_val}  → {vxn_analysis['level']}  ({vxn_analysis['signal']}, score {vxn_analysis['score']})")
    print(f"  GEX: {gex_b}B  → {gex_analysis['level']}  ({gex_analysis['signal']}, score {gex_analysis['score']})")
    print(f"  DIX: {dix}%")
    print(f"  ── Señal Volatilidad ──: {vol_signal}  (score {vol_score}/100)")

    output = {
        "agent": 3,
        "name": "Volatility Analyst",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "input_source": "agent1_data.json",
        "raw_inputs": {
            "VXN": vxn_val,
            "GEX_B": gex_b,
            "DIX": dix
        },
        "vxn_analysis": vxn_analysis,
        "gex_analysis": gex_analysis,
        "signal": vol_signal,
        "score": vol_score
    }

    with open("agent3_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n✅ Agent 3 completado → agent3_data.json")
    return output


if __name__ == "__main__":
    run()
