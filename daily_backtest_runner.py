#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  DAILY BACKTEST RUNNER — NQ Intelligence                                    ║
║  ─────────────────────────────────────────────────────────────────────────  ║
║  Aplica el MISMO estudio a cada día de la semana por separado:              ║
║                                                                              ║
║    TODOS → backtest_all_days.py   (Volume Profile + EMA200 + 6 patrones)    ║
║                                                                              ║
║  Cada día recibe exactamente el mismo análisis:                              ║
║    • Volume Profile (VAH / POC / VAL)  — Asia 18:00 → 09:20 NY             ║
║    • EMA 200 (15min) al momento de apertura NY                               ║
║    • 6 patrones ICT                                                          ║
║    • Dirección, rango NY, sweep time, niveles hit + reacción                ║
║                                                                              ║
║  También actualiza data/research/nq_15m_intraday.csv si tiene más          ║
║  de 24 horas sin actualizarse.                                               ║
║                                                                              ║
║  Uso:                                                                        ║
║    python daily_backtest_runner.py              → todos los días (365d)      ║
║    python daily_backtest_runner.py --day lun    → solo Lunes                 ║
║    python daily_backtest_runner.py --days 90    → últimos 90 días            ║
║    python daily_backtest_runner.py --update     → solo actualiza CSV         ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timedelta

# ─── Paths base ──────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_CSV  = os.path.join(BASE_DIR, "data", "research", "nq_15m_intraday.csv")
LOG_FILE  = os.path.join(BASE_DIR, "data", "research", "backtest_runner_log.json")

# ─── Script unificado ────────────────────────────────────────────────────────
UNIFIED_SCRIPT = "backtest_all_days.py"
UNIFIED_OUTPUT = "data/research/backtest_all_days.json"

DAY_INFO = {
    0: {"name": "LUNES",     "alias": "lun"},
    1: {"name": "MARTES",    "alias": "mar"},
    2: {"name": "MIÉRCOLES", "alias": "mie"},
    3: {"name": "JUEVES",    "alias": "jue"},
    4: {"name": "VIERNES",   "alias": "vie"},
}

# Alias para --day
DAY_ALIAS = {
    "lun": 0, "lunes": 0, "monday": 0, "mon": 0,
    "mar": 1, "martes": 1, "tuesday": 1, "tue": 1,
    "mie": 2, "miercoles": 2, "wednesday": 2, "wed": 2, "miércoles": 2,
    "jue": 3, "jueves": 3, "thursday": 3, "thu": 3,
    "vie": 4, "viernes": 4, "friday": 4, "fri": 4,
}

SEP = "═" * 72


def banner():
    now = datetime.now()
    weekday_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes",
                  "Sábado", "Domingo"]
    print(f"\n{SEP}")
    print(f"  🔬 NQ INTELLIGENCE — DAILY BACKTEST RUNNER")
    print(f"  {now.strftime('%Y-%m-%d %H:%M:%S')}   {weekday_es[now.weekday()]}")
    print(SEP)


def csv_needs_update() -> bool:
    """Devuelve True si el CSV no existe o tiene más de 24 h sin modificarse."""
    if not os.path.exists(DATA_CSV):
        return True
    mtime = datetime.fromtimestamp(os.path.getmtime(DATA_CSV))
    age   = datetime.now() - mtime
    return age > timedelta(hours=24)


def update_data():
    """Descarga / actualiza nq_15m_intraday.csv con datos frescos de yfinance."""
    print(f"\n{'─'*72}")
    print(f"  📥 ACTUALIZANDO DATA NQ 15min...")
    print(f"{'─'*72}")

    updater = os.path.join(BASE_DIR, "update_nq_csv.py")

    if os.path.exists(updater):
        # Si existe un script dedicado, úsalo
        print(f"  → Ejecutando {os.path.basename(updater)}...")
        result = subprocess.run(
            [sys.executable, updater],
            cwd=BASE_DIR,
            capture_output=False,
        )
        if result.returncode == 0:
            print("  ✅ CSV actualizado correctamente.")
        else:
            print("  ⚠️  El updater terminó con errores. Continuando con CSV existente.")
        return

    # Fallback: actualizar inline con yfinance
    try:
        import yfinance as yf
        import pandas as pd

        print("  → Descargando NQ=F 15min con yfinance...")
        df = yf.download(
            "NQ=F",
            period="60d",
            interval="15m",
            progress=False,
            prepost=True,
        )
        if df is None or len(df) == 0:
            print("  ⚠️  yfinance no devolvió datos.")
            return

        os.makedirs(os.path.dirname(DATA_CSV), exist_ok=True)

        # Si ya existe un CSV previo, combinar
        if os.path.exists(DATA_CSV):
            try:
                existing = pd.read_csv(DATA_CSV, skiprows=2)
                existing.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
                existing = existing.dropna(subset=['Datetime'])
                existing['Datetime'] = pd.to_datetime(existing['Datetime'], utc=True)
                existing.set_index('Datetime', inplace=True)
                # Unir: el nuevo sobreescribe filas con el mismo timestamp
                combined = existing.combine_first(df)
                combined.to_csv(DATA_CSV)
            except Exception as e:
                print(f"  ⚠️  No se pudo combinar con CSV existente ({e}). Sobreescribiendo.")
                df.to_csv(DATA_CSV)
        else:
            df.to_csv(DATA_CSV)

        print(f"  ✅ CSV guardado: {DATA_CSV}  ({len(df)} nuevas barras)")
    except ImportError:
        print("  ⚠️  yfinance no instalado. Instalando...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yfinance", "-q"])
        print("  Reinicia el script para actualizar data.")
    except Exception as e:
        print(f"  ❌ Error al actualizar CSV: {e}")


def run_unified(day_alias: str | None, days_window: int) -> dict:
    """Ejecuta backtest_all_days.py, opcionalmente filtrado por un día."""
    script_path = os.path.join(BASE_DIR, UNIFIED_SCRIPT)

    if not os.path.exists(script_path):
        return {"status": "error", "msg": f"Script no encontrado: {script_path}"}

    label = day_alias.upper() if day_alias else "TODOS LOS DÍAS"
    print(f"\n{SEP}")
    print(f"  🚀 EJECUTANDO BACKTEST — {label}")
    print(f"  Script : {UNIFIED_SCRIPT}")
    print(f"  Periodo: últimos {days_window} días  |  mismo estudio en todos los días")
    print(SEP)

    cmd = [sys.executable, script_path, "--days", str(days_window)]
    if day_alias:
        cmd += ["--day", day_alias]

    start_ts = datetime.now()
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=False)
    elapsed = (datetime.now() - start_ts).total_seconds()

    success  = result.returncode == 0
    out_path = os.path.join(BASE_DIR, UNIFIED_OUTPUT)

    status = {
        "script":      UNIFIED_SCRIPT,
        "day":         label,
        "days_window": days_window,
        "status":      "ok" if success else "error",
        "returncode":  result.returncode,
        "elapsed_s":   round(elapsed, 2),
        "output_json": out_path if os.path.exists(out_path) else None,
        "timestamp":   start_ts.isoformat(),
    }

    if success:
        print(f"\n  ✅ {label}: completado en {elapsed:.1f}s")
    else:
        print(f"\n  ❌ {label}: falló (código {result.returncode})")

    return status


def save_log(results: list):
    """Persiste el historial de ejecuciones en JSON."""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    log = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            log = []

    log.extend(results)
    # Conservar solo las últimas 500 entradas
    log = log[-500:]

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

    print(f"\n  📝 Log guardado → {LOG_FILE}")


def print_summary(results: list):
    print(f"\n{SEP}")
    print(f"  📋 RESUMEN DE EJECUCIÓN")
    print(f"{'─'*72}")
    for r in results:
        icon = "✅" if r["status"] == "ok" else "❌"
        out  = os.path.basename(r["output_json"]) if r["output_json"] else "–"
        print(f"  {icon} {r['day']:<12} {r['elapsed_s']:>6.1f}s   → {out}")
    print(SEP)


def main():
    banner()

    parser = argparse.ArgumentParser(
        description="NQ Intelligence — Daily Backtest Runner (mismo estudio todos los días)"
    )
    parser.add_argument(
        "--day", type=str, default=None,
        help="Analiza solo un día: lun|mar|mie|jue|vie (por defecto: TODOS)",
    )
    parser.add_argument(
        "--days", type=int, default=365,
        help="Ventana de datos en días (default: 365)",
    )
    parser.add_argument(
        "--update", action="store_true",
        help="Solo actualiza el CSV de datos, sin ejecutar backtests",
    )
    parser.add_argument(
        "--no-update", action="store_true",
        help="Salta la actualización del CSV aunque tenga más de 24h",
    )
    args = parser.parse_args()

    # ── 1. Actualizar datos ────────────────────────────────────────────
    if not args.no_update:
        if args.update:
            update_data()
            print(f"\n  Actualización completada. Saliendo (--update).\n")
            return
        if csv_needs_update():
            print(f"\n  ℹ️  CSV tiene más de 24h. Actualizando datos...")
            update_data()
        else:
            mtime = datetime.fromtimestamp(os.path.getmtime(DATA_CSV))
            age_h = (datetime.now() - mtime).total_seconds() / 3600
            print(f"\n  ✓ CSV actualizado hace {age_h:.1f}h — sin actualización necesaria.")
    else:
        print(f"\n  ℹ️  --no-update: saltando actualización de CSV.")

    # ── 2. Validar --day si se pasó ────────────────────────────────────
    day_alias = None
    if args.day:
        key = args.day.lower().strip()
        if key not in DAY_ALIAS:
            print(f"\n  ❌ Día no reconocido: '{args.day}'")
            print(f"     Opciones: lun|mar|mie|jue|vie")
            sys.exit(1)
        day_num   = DAY_ALIAS[key]
        day_alias = DAY_INFO[day_num]["alias"]
        print(f"\n  → Modo específico: solo {DAY_INFO[day_num]['name']}")
    else:
        today_str = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"][datetime.now().weekday()]
        print(f"\n  → Ejecutando todos los días ({today_str}) | ventana: {args.days} días")

    # ── 3. Ejecutar backtest unificado ────────────────────────────────
    res = run_unified(day_alias, args.days)
    results = [res]

    # ── 4. Resumen + log ──────────────────────────────────────────────
    print_summary(results)
    save_log(results)

    ok_count  = sum(1 for r in results if r["status"] == "ok")
    err_count = len(results) - ok_count
    print(f"\n  Completado: {ok_count} OK · {err_count} errores\n")

    return 0 if err_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
