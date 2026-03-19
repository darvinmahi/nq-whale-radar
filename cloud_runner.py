"""
CLOUD RUNNER — NQ Intelligence Engine (Single-Cycle Mode)
═══════════════════════════════════════════════════════════
Para GitHub Actions: ejecuta UN solo ciclo del engine y sale.
El cron de GitHub lo re-ejecuta cada 30 minutos.
"""

import sys
import os

# Asegurar que los módulos de agents/ se encuentren
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(BASE_DIR, "agents")
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, AGENTS_DIR)

# Re-usar el pipeline existente pero solo 1 ciclo
from run_intelligence_engine import run_pipeline

if __name__ == "__main__":
    print("☁️  NQ Cloud Runner — Single Cycle Mode")
    run_pipeline(cycle_num=1)
    print("✅ Ciclo completado. GitHub Actions hará commit + push.")
