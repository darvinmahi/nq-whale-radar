@echo off
:: ═══════════════════════════════════════════════════════════
:: NQ Intelligence Engine — Launcher
:: Haz doble clic para ejecutar el pipeline completo
:: ═══════════════════════════════════════════════════════════

cd /d "C:\Users\FxDarvin\Desktop\PAgina"

echo.
echo ═══════════════════════════════════════
echo   NQ INTELLIGENCE ENGINE — INICIANDO
echo ═══════════════════════════════════════
echo.

set PYTHON=python

:: Intenta ejecutar el pipeline completo
"%PYTHON%" run_intelligence_engine.py

echo.
echo Pipeline finalizado. Presiona cualquier tecla para cerrar.
pause >nul
