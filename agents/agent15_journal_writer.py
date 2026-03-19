"""
AGENTE 15 — JOURNAL WRITER (NQ Intelligence Engine)
═══════════════════════════════════════════════════════════
Responsabilidad: Sintetizar los datos de todos los agentes
en una entrada de diario diaria y mantener un histórico
de los últimos 10 días en agent15_journal_data.json.

Formato de salida (agent15_journal_data.json):
{
  "generated_at": "...",
  "entries": [
    {
      "date": "2026-03-18",
      "display_date": "March 18, 2026",
      "weekday": "Wednesday",
      "nq_price": 19500,
      "bias_score": 54,
      "bias_label": "NEUTRAL-BULLISH",
      "cot_signal": "BULLISH",
      "cot_net": 12345,
      "vxn": 30.04,
      "key_observations": ["...", "..."],
      "session_tag": "NY AM",
      "tag_color": "#a855f7",
      "summary": "Short narrative summary of the day."
    }, ...
  ]
}
"""

import os
import json
import datetime
import sys

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent15_journal_data.json")

WEEKDAYS_ES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
MONTHS_EN   = ["January","February","March","April","May","June",
                "July","August","September","October","November","December"]

def load_json(filename):
    try:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def load_existing() -> list:
    """Load the existing journal entries list."""
    if not os.path.exists(OUTPUT_FILE):
        return []
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("entries", [])
    except Exception:
        return []

def get_session_tag(hour_utc: int) -> tuple:
    """Return (tag_label, tag_color) based on UTC hour."""
    if 13 <= hour_utc < 17:
        return ("NY AM", "#a855f7")   # purple
    elif 17 <= hour_utc < 21:
        return ("NY PM", "#7c3aed")   # deep purple
    elif 8 <= hour_utc < 13:
        return ("London", "#0066ff")  # blue
    else:
        return ("Asia / Off-Hours", "#64748b")  # gray

def build_observations(a1, a2, a3, a4, a14, pulse) -> list:
    """Build a list of key human-readable observations from agent data."""
    obs = []

    # Price / NQ
    market_nq = (pulse or {}).get("market", {}).get("NQ", {})
    nq_price = market_nq.get("price") or (a1 or {}).get("yahoo", {}).get("NQ_futures", {}).get("price")
    change_pct = (a1 or {}).get("yahoo", {}).get("NQ_futures", {}).get("change_pct")
    if nq_price:
        direction = "▲" if (change_pct or 0) >= 0 else "▼"
        pct_str = f"{abs(change_pct):.2f}%" if change_pct is not None else "—"
        obs.append(f"NQ futures cotizando en {int(nq_price):,} ({direction} {pct_str} en el día).")

    # COT
    cot = (a2 or {}).get("cot", {})
    cot_net = cot.get("current_net")
    cot_signal = (a2 or {}).get("signal", "NEUTRAL")
    if cot_net is not None:
        obs.append(f"COT: posición neta de large non-commercials = {int(cot_net):+,}. Señal: {cot_signal}.")

    # Bias
    bias_score = (a4 or {}).get("global_score")
    bias_label = (a4 or {}).get("global_label", "")
    if bias_score is not None:
        obs.append(f"Motor de Bias: {bias_label} ({bias_score}/100).")

    # Volatility (VXN)
    vxn = (pulse or {}).get("market", {}).get("VXN", {}).get("price")
    vxn_change = (pulse or {}).get("market", {}).get("VXN", {}).get("change")
    if vxn is not None:
        direction = "▲" if (vxn_change or 0) >= 0 else "▼"
        obs.append(f"Volatilidad VXN: {vxn:.2f} ({direction} {abs(vxn_change or 0):.2f}).")

    # Order Flow
    of_bias = (a14 or {}).get("session_bias", {}).get("label")
    if of_bias:
        obs.append(f"Order Flow session bias: {of_bias}.")

    # Fallback
    if not obs:
        obs.append("Sin datos de mercado disponibles en este ciclo.")

    return obs

def build_summary(bias_label: str, cot_signal: str, nq_price, obs: list) -> str:
    """Generate a short narrative summary for the journal entry."""
    price_str = f"{int(nq_price):,}" if nq_price else "sin precio"
    bias_map = {
        "BULLISH": "alcista",
        "BEARISH": "bajista",
        "NEUTRAL": "neutral",
        "NEUTRAL-BULLISH": "levemente alcista",
        "NEUTRAL-BEARISH": "levemente bajista",
    }
    bias_es = bias_map.get(bias_label.upper().replace(" ", "-"), bias_label.lower())
    cot_es  = bias_map.get(cot_signal.upper(), cot_signal.lower())

    lines = [
        f"El día cerró con NQ en {price_str}.",
        f"El bias del motor es {bias_es}, alineado con una señal COT {cot_es}.",
    ]
    if obs:
        lines.append(obs[0])
    return " ".join(lines)

def build_entry() -> dict:
    """Build today's journal entry from live agent data."""
    a1     = load_json("agent1_data.json")
    a2     = load_json("agent2_data.json")
    a3     = load_json("agent3_data.json")
    a4     = load_json("agent4_data.json")
    a14    = load_json("agent14_orderflow_data.json")
    pulse  = load_json("pulse_data.json")

    now      = datetime.datetime.now(datetime.UTC)
    date_str = now.strftime("%Y-%m-%d")
    display  = f"{MONTHS_EN[now.month-1]} {now.day}, {now.year}"
    weekday  = WEEKDAYS_ES[now.weekday()]
    session_tag, tag_color = get_session_tag(now.hour)

    # Extract key values
    market_nq   = (pulse or {}).get("market", {}).get("NQ", {})
    nq_price    = market_nq.get("price") or (a1 or {}).get("yahoo", {}).get("NQ_futures", {}).get("price")
    change_pct  = (a1 or {}).get("yahoo", {}).get("NQ_futures", {}).get("change_pct")
    bias_score  = (a4 or {}).get("global_score", 50)
    bias_label  = (a4 or {}).get("global_label", "NEUTRAL")
    cot_signal  = (a2 or {}).get("signal", "NEUTRAL")
    cot         = (a2 or {}).get("cot", {})
    cot_net     = cot.get("current_net", 0)
    vxn         = (pulse or {}).get("market", {}).get("VXN", {}).get("price")

    observations = build_observations(a1, a2, a3, a4, a14, pulse)
    summary      = build_summary(bias_label, cot_signal, nq_price, observations)

    return {
        "date":              date_str,
        "display_date":      display,
        "weekday":           weekday,
        "generated_at":      now.isoformat() + "Z",
        "nq_price":          nq_price,
        "nq_change_pct":     change_pct,
        "bias_score":        bias_score,
        "bias_label":        bias_label,
        "cot_signal":        cot_signal,
        "cot_net":           cot_net,
        "vxn":               vxn,
        "session_tag":       session_tag,
        "tag_color":         tag_color,
        "key_observations":  observations,
        "summary":           summary,
    }

def run():
    """Main entry point — called by the orchestrator."""
    print("📓 Agent 15 · Journal Writer — generando entrada...")

    today_entry = build_entry()
    today_date  = today_entry["date"]

    existing = load_existing()

    # Remove existing entry for today (will replace with fresh data)
    existing = [e for e in existing if e.get("date") != today_date]

    # Prepend today, keep last 10 days
    existing.insert(0, today_entry)
    entries = existing[:10]

    output = {
        "agent":        15,
        "name":         "Journal Writer",
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "entries":      entries,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Entrada '{today_date}' guardada. Total entradas: {len(entries)}.")

if __name__ == "__main__":
    if "--run-once" in sys.argv:
        run()
        sys.exit(0)
    run()
