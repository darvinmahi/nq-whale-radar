#!/usr/bin/env python3
"""
MASTER SCHEDULER — NQ Whale Radar
===================================
Corre en Railway 24/7 junto a run_intelligence_engine.py
Maneja los scripts con horario específico ET:

  09:00 ET  → analyze_today.py     (brief IA del día)
  16:30 ET  → auto_record.py       (registra el día completo)
  06:00 ET  → rebuild_from_master  (recalcula todo día nuevo)

Este script NO reemplaza el engine — corre EN PARALELO.
"""

import os
import sys
import time
import datetime
import subprocess
import json
import pytz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ET_TZ    = pytz.timezone("US/Eastern")
LOG_FILE = os.path.join(BASE_DIR, "data", "research", "scheduler_log.json")

os.makedirs(os.path.join(BASE_DIR, "data", "research"), exist_ok=True)

def now_et():
    return datetime.datetime.now(ET_TZ)

def log(msg):
    ts = now_et().strftime("%Y-%m-%d %H:%M ET")
    print(f"[SCHEDULER {ts}] {msg}", flush=True)

def run_script(name):
    script = os.path.join(BASE_DIR, name)
    log(f"▶ Ejecutando {name}...")
    try:
        result = subprocess.run(
            [sys.executable, script],
            cwd=BASE_DIR,
            timeout=300,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        if result.returncode == 0:
            log(f"✅ {name} completado")
            return True
        else:
            log(f"❌ {name} error: {result.stderr[-200:]}")
            return False
    except subprocess.TimeoutExpired:
        log(f"⏱ {name} timeout (5min)")
        return False
    except Exception as e:
        log(f"❌ {name} excepción: {e}")
        return False

def push_to_github():
    """Push automático de los JSONs generados a GitHub Pages."""
    log("📤 Push automático a GitHub Pages...")
    try:
        subprocess.run(
            ["git", "add",
             "data/research/daily_master_db.json",
             "data/research/today_analysis.json",
             "data/research/backtest_monday_1year.json",
             "data/research/backtest_tuesday_1year.json",
             "data/research/backtest_wednesday_1year.json",
             "data/research/backtest_thursday_1year.json",
             "data/research/backtest_friday_1year.json",
             "data/research/auto_record.log"],
            cwd=BASE_DIR, timeout=30, check=False
        )
        dt = now_et().strftime("%Y-%m-%d %H:%M ET")
        subprocess.run(
            ["git", "commit", "-m", f"auto: datos diarios actualizados {dt}"],
            cwd=BASE_DIR, timeout=30, check=False
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=BASE_DIR, timeout=60, check=False
        )
        log("✅ GitHub Pages actualizado")
    except Exception as e:
        log(f"⚠ Push falló: {e} (los datos siguen válidos localmente)")

def save_scheduler_health(last_run, next_run, status):
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "last_run": last_run,
                "next_run": next_run,
                "status": status,
                "scheduler_alive": True
            }, f)
    except: pass

# ── Tareas y sus horarios ET ──────────────────────────────────────
# Formato: (hora, minuto, script, descripcion)
TASKS = [
    (6,  0,  "rebuild_from_master_db.py",  "Rebuild backtest JSONs (pre-market)"),
    (9,  0,  "analyze_today.py",            "Análisis IA del día (9AM ET)"),
    (16, 30, "auto_record.py",              "Registrar día completo (4:30PM ET)"),
]

def main():
    log("🚀 MASTER SCHEDULER iniciado")
    log(f"   Tareas programadas: {len(TASKS)}")
    for h, m, s, d in TASKS:
        log(f"   {h:02d}:{m:02d} ET → {s} ({d})")

    executed_today = set()  # (hora, minuto) ejecutados hoy

    while True:
        try:
            now  = now_et()
            hhmm = (now.hour, now.minute)
            today_key = now.strftime("%Y-%m-%d")

            for hour, minute, script, desc in TASKS:
                task_key = (today_key, hour, minute)
                if hhmm == (hour, minute) and task_key not in executed_today:
                    log(f"🕐 TAREA PROGRAMADA: {desc}")
                    success = run_script(script)
                    executed_today.add(task_key)

                    # Después de auto_record → push todo a GitHub
                    if script == "auto_record.py" and success:
                        push_to_github()

                    # Después de analyze_today → también push
                    if script == "analyze_today.py" and success:
                        push_to_github()

            # Limpiar ejecutados de días anteriores
            executed_today = {k for k in executed_today if k[0] == today_key}

            # Health save cada 10 min
            if now.minute % 10 == 0:
                next_tasks = [(h, m, s) for h, m, s, _ in TASKS]
                save_scheduler_health(
                    now.isoformat(),
                    str(next_tasks),
                    "RUNNING"
                )

        except Exception as e:
            log(f"⚠️ Error en loop principal: {e}")

        time.sleep(60)  # Checar cada minuto

if __name__ == "__main__":
    main()
