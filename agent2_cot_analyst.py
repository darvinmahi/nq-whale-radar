"""
AGENTE 2 — COT ANALYST
Responsabilidad: Analizar datos COT del Agente 1.
  - Calcular COT Index (posición actual vs rango histórico)
  - Detectar cambios consecutivos (bullish/bearish momentum)
  - Identificar extremos históricos
  - Emitir señal: BULLISH / BEARISH / NEUTRAL + fuerza (0–100)

Entrada: agent1_data.json
Salida:  agent2_data.json
"""

import json
import datetime

# ─── Rango histórico de referencia (3 años, Nasdaq 100 E-mini Non-Commercial Net) ─
COT_HISTORY_MIN = -50_000   # mínimo histórico (extremo bajista)
COT_HISTORY_MAX = 142_000   # máximo histórico (extremo alcista)
COT_MEAN        = 95_000    # media histórica aproximada

# Últimas 4 semanas de COT para detección de momentum (actualizar semanalmente)
# Formato: más reciente primero
COT_RECENT_WEEKS = [
    {"date": "03 Mar 2026", "nc_long": 76_598, "nc_short": 74_212},
    {"date": "24 Feb 2026", "nc_long": 80_310, "nc_short": 69_523},
    {"date": "17 Feb 2026", "nc_long": 89_273, "nc_short": 64_863},
    {"date": "10 Feb 2026", "nc_long": 82_196, "nc_short": 68_836},
]


def load_agent1():
    try:
        with open("agent1_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Agent 2] ⚠️  No se pudo leer agent1_data.json: {e}")
        return None


def calc_cot_index(net_position):
    """
    COT Index: normaliza la posición neta actual en escala 0–100
    respecto al rango histórico (min/max).
    """
    rng = COT_HISTORY_MAX - COT_HISTORY_MIN
    idx = ((net_position - COT_HISTORY_MIN) / rng) * 100
    return round(max(0, min(100, idx)), 1)


def detect_consecutive_changes(weeks):
    """
    Analiza si los net positions de las semanas recientes
    muestran una tendencia consistente (subiendo o bajando).
    Devuelve: (direction, count)
    """
    nets = [w["nc_long"] - w["nc_short"] for w in weeks]
    direction = None
    count = 0
    for i in range(len(nets) - 1):
        diff = nets[i] - nets[i + 1]   # semana más reciente vs anterior
        if diff < 0:
            d = "BAJANDO"
        elif diff > 0:
            d = "SUBIENDO"
        else:
            d = "PLANO"

        if i == 0:
            direction = d
            count = 1
        elif d == direction:
            count += 1
        else:
            break

    return direction, count


def classify_cot_signal(cot_index, direction, weeks_consec):
    """
    Combina COT Index + momentum para dar señal y fuerza.
    """
    # Fuerza base según índice
    if cot_index >= 75:
        base_signal = "BULLISH"
        base_strength = cot_index
    elif cot_index <= 25:
        base_signal = "BEARISH"
        base_strength = 100 - cot_index
    else:
        base_signal = "NEUTRAL"
        base_strength = 50

    # Ajuste por momentum
    if direction == "BAJANDO" and weeks_consec >= 3:
        # HF vendiendo consecutivamente → presión bajista añadida
        base_strength = max(0, base_strength - (weeks_consec * 8))
        if base_signal == "BULLISH" and weeks_consec >= 3:
            base_signal = "NEUTRAL"   # Contradice el índice
    elif direction == "SUBIENDO" and weeks_consec >= 3:
        base_strength = min(100, base_strength + (weeks_consec * 8))
        if base_signal == "BEARISH":
            base_signal = "NEUTRAL"

    return base_signal, round(base_strength)


def generate_cot_insight(net, cot_index, direction, weeks_consec, signal, strength):
    velocity = 0
    if len(COT_RECENT_WEEKS) >= 2:
        nets = [w["nc_long"] - w["nc_short"] for w in COT_RECENT_WEEKS]
        velocity = round((nets[0] - nets[-1]) / (len(nets) - 1))

    if cot_index >= 75:
        level_str = "🟢 ZONA ALCISTA — HF fuertemente largos"
        alert = None
    elif cot_index <= 20:
        level_str = "🔴 ZONA BAJISTA — Capitalización o capitulación"
        alert = f"COT en extremo bajo ({cot_index}/100). Históricamente precede recuperación."
    elif direction == "BAJANDO" and weeks_consec >= 3:
        level_str = "🟡 ZONA DE VIGILANCIA — HF reduciendo longs"
        alert = f"⚡ {weeks_consec} semanas consecutivas bajando. Velocidad: {velocity:+,}/sem."
    else:
        level_str = "🔵 ZONA NEUTRAL"
        alert = None

    return {"level_description": level_str, "weekly_velocity": velocity, "alert": alert}


def run():
    print("\n" + "="*60)
    print("  AGENTE 2 · COT ANALYST · INICIO")
    print("="*60 + "\n")

    a1 = load_agent1()
    cot_raw = a1.get("cftc_cot", {}) if a1 else {}

    # Use live data if available, else fall back to latest historical row
    live_net = cot_raw.get("cot_net")
    live_oi  = cot_raw.get("cot_oi")
    live_date = cot_raw.get("cot_date")

    # Primary net from live COT; fallback to last historical week
    hist_nets = [w["nc_long"] - w["nc_short"] for w in COT_RECENT_WEEKS]
    current_net = live_net if live_net is not None else hist_nets[0]
    current_oi  = live_oi  if live_oi  is not None else 273_307
    current_date = live_date if live_date else COT_RECENT_WEEKS[0]["date"]

    # Inject live net into history for momentum analysis
    weeks_for_analysis = COT_RECENT_WEEKS[:]
    if live_net is not None:
        weeks_for_analysis.insert(0, {
            "date": current_date,
            "nc_long": cot_raw.get("cot_nc_long", 0),
            "nc_short": cot_raw.get("cot_nc_short", 0)
        })

    cot_index = calc_cot_index(current_net)
    direction, weeks_consec = detect_consecutive_changes(weeks_for_analysis)
    signal, strength = classify_cot_signal(cot_index, direction, weeks_consec)
    insight = generate_cot_insight(current_net, cot_index, direction, weeks_consec, signal, strength)

    print(f"  COT Net Position : {current_net:+,}")
    print(f"  COT Index        : {cot_index}/100")
    print(f"  Momentum         : {direction} · {weeks_consec} semanas")
    print(f"  ── Señal ──      : {signal}  (fuerza {strength}/100)")
    if insight["alert"]:
        print(f"  ⚠️ ALERTA: {insight['alert']}")

    output = {
        "agent": 2,
        "name": "COT Analyst",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "input_source": "agent1_data.json",
        "cot": {
            "current_net": current_net,
            "current_oi": current_oi,
            "date": current_date,
            "cot_index": cot_index,
            "history_min": COT_HISTORY_MIN,
            "history_max": COT_HISTORY_MAX,
            "history_mean": COT_MEAN,
        },
        "momentum": {
            "direction": direction,
            "consecutive_weeks": weeks_consec,
            "weekly_velocity": insight["weekly_velocity"]
        },
        "signal": signal,
        "strength": strength,
        "insight": insight,
        "recent_weeks": weeks_for_analysis[:5]
    }

    with open("agent2_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("\n✅ Agent 2 completado → agent2_data.json")
    return output


if __name__ == "__main__":
    run()
