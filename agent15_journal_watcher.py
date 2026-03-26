"""
AGENT 15 - JOURNAL WATCHER (Live Update)
=========================================
Actualiza agent15_journal_data.json cada segundo con datos en vivo.
El HTML lo detecta automáticamente y refresca el contenido sin recargar la página.

COMO USAR:
  windows:  python agent15_journal_watcher.py
  fondo:    start /B python agent15_journal_watcher.py
"""

import json
import os
import time
import datetime
import random
import sys

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "agent15_journal_data.json")
UPDATE_INTERVAL = 1   # segundos

# ── Intentar importar fuentes de datos del proyecto ───────────────────────────
def _load_json(fname):
    path = os.path.join(BASE_DIR, fname)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _load_indicators():
    """Lee los datos más frescos de los agentes disponibles."""
    indicators = {
        "nq_price":      None,
        "nq_change_pct": None,
        "bias_score":    49,
        "bias_label":    "NEUTRAL",
        "cot_signal":    "BEARISH",
        "cot_net":       -72688,
        "vxn":           30.04,
        "session_tag":   None,
    }

    # Agente 1 → precio NQ
    a1 = _load_json("agent1_data.json")
    if a1.get("nq_price"):   indicators["nq_price"]      = float(a1["nq_price"])
    if a1.get("nq_change"):  indicators["nq_change_pct"] = float(a1["nq_change"])
    if a1.get("session"):    indicators["session_tag"]   = a1["session"]

    # Agente 2 → bias
    a2 = _load_json("agent2_data.json")
    if a2.get("bias_score"):  indicators["bias_score"] = a2["bias_score"]
    if a2.get("bias_label"):  indicators["bias_label"] = a2["bias_label"]

    # nq_real_data
    nq = _load_json("nq_real_data.json")
    if nq.get("price"):      indicators["nq_price"]      = float(nq["price"])
    if nq.get("change_pct"): indicators["nq_change_pct"] = float(nq["change_pct"])
    if nq.get("vxn"):        indicators["vxn"]           = float(nq["vxn"])

    # pulse_data (motor central)
    pulse = _load_json("pulse_data.json")
    if pulse.get("bias_score"): indicators["bias_score"] = pulse["bias_score"]
    if pulse.get("bias_label"): indicators["bias_label"] = pulse["bias_label"]
    if pulse.get("session"):    indicators["session_tag"] = pulse["session"]

    # Agente 4 → COT
    a4 = _load_json("agent4_data.json")
    if a4.get("cot_net"):    indicators["cot_net"]    = a4["cot_net"]
    if a4.get("cot_signal"): indicators["cot_signal"] = a4["cot_signal"]

    return indicators

def _session_now():
    """Determina la sesión actual según hora UTC."""
    h = datetime.datetime.utcnow().hour
    if   0 <= h <  8: return ("Asia / Off-Hours", "#64748b")
    elif 8 <= h < 13: return ("London Session",   "#f59e0b")
    elif 13 <= h < 21: return ("New York Session", "#22c55e")
    else:              return ("After Hours",       "#6366f1")

def _build_entry(indicators, today):
    """Construye la entrada del diario para hoy."""
    price     = indicators["nq_price"]      or 24016.0
    chg       = indicators["nq_change_pct"] or 0.0
    bias_sc   = indicators["bias_score"]    or 49
    bias_lb   = indicators["bias_label"]    or "NEUTRAL"
    cot_sig   = indicators["cot_signal"]    or "BEARISH"
    cot_net   = indicators["cot_net"]       or -72688
    vxn       = indicators["vxn"]           or 30.04
    sess, col = indicators.get("session_tag") and (indicators["session_tag"], "") or _session_now()
    if not isinstance(sess, str):
        sess, col = _session_now()

    direction = "▲" if chg >= 0 else "▼"
    now_iso   = datetime.datetime.utcnow().isoformat() + "Z"

    obs = [
        f"NQ futures cotizando en {price:,.0f} ({direction} {abs(chg):.2f}% en el día).",
        f"COT: posición neta de large non-commercials = {cot_net:,}. Señal: {cot_sig}.",
        f"Motor de Bias: {bias_lb} ({bias_sc}/100).",
        f"Volatilidad VXN: {vxn:.2f}.",
        f"Sesión activa: {sess}. Última actualización: {datetime.datetime.utcnow().strftime('%H:%M:%S')} UTC.",
    ]

    return {
        "date":         today.strftime("%Y-%m-%d"),
        "display_date": today.strftime("%B %d, %Y"),
        "weekday":      today.strftime("%A"),
        "generated_at": now_iso,
        "last_live_update": now_iso,
        "nq_price":     price,
        "nq_change_pct": chg,
        "bias_score":   bias_sc,
        "bias_label":   bias_lb,
        "cot_signal":   cot_sig,
        "cot_net":      cot_net,
        "vxn":          vxn,
        "session_tag":  sess,
        "tag_color":    col if col else "#64748b",
        "key_observations": obs,
        "summary": (
            f"Actualización en vivo — NQ en {price:,.0f} ({direction}{abs(chg):.2f}%). "
            f"Bias {bias_lb} ({bias_sc}/100) | COT {cot_sig} ({cot_net:,}) | VXN {vxn:.2f} | {sess}."
        ),
    }

def _load_existing_entries():
    """Carga las entradas históricas existentes (sin hoy)."""
    today_str = datetime.date.today().isoformat()
    if not os.path.exists(OUTPUT_FILE):
        return []
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [e for e in data.get("entries", []) if e.get("date") != today_str]
    except Exception:
        return []

def update_once():
    indicators = _load_indicators()
    today      = datetime.date.today()
    today_entry = _build_entry(indicators, today)
    old_entries = _load_existing_entries()

    payload = {
        "agent":        15,
        "name":         "Journal Writer — Live",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "live":         True,
        "update_interval_s": UPDATE_INTERVAL,
        "entries":      [today_entry] + old_entries,
    }

    # Escritura atómica — nunca corrompe el archivo
    tmp = OUTPUT_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUTPUT_FILE)

    ts = datetime.datetime.utcnow().strftime("%H:%M:%S")
    nq = indicators.get("nq_price") or "?"
    print(f"[{ts}] ✓ Journal actualizado — NQ {nq} | Bias {indicators.get('bias_label','?')} | Sesión detectada", flush=True)

def main():
    print("═" * 60)
    print("  AGENT 15 — JOURNAL WATCHER v2 (Live, cada 1 segundo)")
    print(f"  Archivo: {OUTPUT_FILE}")
    print("  Ctrl+C para detener")
    print("═" * 60)
    tick = 0
    while True:
        try:
            update_once()
        except KeyboardInterrupt:
            print("\n[Agent 15] Detenido por usuario.")
            sys.exit(0)
        except Exception as ex:
            print(f"[Agent 15] Error (continúa): {ex}", flush=True)
        tick += 1
        time.sleep(UPDATE_INTERVAL)

if __name__ == "__main__":
    main()
