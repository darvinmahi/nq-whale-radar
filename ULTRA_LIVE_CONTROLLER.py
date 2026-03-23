# -*- coding: utf-8 -*-
"""
ULTRA_LIVE_CONTROLLER.py - NQ Intelligence Supervisor v2.0
Lanza y supervisa todos los motores. Si un proceso muere, lo reinicia.

Motores gestionados:
  1. pulse_engine.py           -> precios NQ/VXN cada 5s
  2. run_intelligence_engine.py -> pipeline completo cada 15 min

Uso: python ULTRA_LIVE_CONTROLLER.py
     Ctrl+C para detener todo.
"""

import subprocess
import os
import sys
import time
import datetime

# Fix encoding para consolas Windows (CP1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENGINES = [
    {
        "name": "Pulse Engine (precios cada 5s)",
        "cmd": [sys.executable, os.path.join(BASE_DIR, "pulse_engine.py")],
        "restart_delay": 3,
    },
    {
        "name": "Intelligence Engine (analisis cada 15 min)",
        "cmd": [sys.executable, os.path.join(BASE_DIR, "run_intelligence_engine.py")],
        "restart_delay": 5,
    },
]

def log(msg):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] {msg}", flush=True)

def start_engine(engine):
    proc = subprocess.Popen(
        engine["cmd"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    log(f">> {engine['name']} iniciado (PID {proc.pid})")
    return proc

def main():
    log("NQ ULTRA-LIVE CONTROLLER v2.0 - Auto-restart ACTIVO")
    log("=" * 52)
    log(f"   Directorio: {BASE_DIR}")
    log("   Ctrl+C para detener todo.\n")

    running = {}
    for engine in ENGINES:
        running[engine["name"]] = {
            "engine": engine,
            "proc": start_engine(engine),
        }
        time.sleep(1)

    log("\n[OK] TODOS LOS MOTORES EN LINEA.\n")

    try:
        while True:
            time.sleep(5)
            for name, entry in running.items():
                proc = entry["proc"]
                engine = entry["engine"]
                if proc.poll() is not None:
                    exit_code = proc.returncode
                    log(f"[!] '{name}' caido (codigo {exit_code}). Reiniciando en {engine['restart_delay']}s...")
                    time.sleep(engine["restart_delay"])
                    entry["proc"] = start_engine(engine)

    except KeyboardInterrupt:
        log("\n[STOP] Apagando todos los motores...")
        for name, entry in running.items():
            try:
                entry["proc"].terminate()
                log(f"   Detenido: {name}")
            except Exception:
                pass
        log("Shutdown completo.")

if __name__ == "__main__":
    main()
