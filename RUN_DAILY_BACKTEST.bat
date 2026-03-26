@echo off
:: ═══════════════════════════════════════════════════════════════════
::  NQ INTELLIGENCE — RUN_DAILY_BACKTEST.bat
::  Ejecuta el backtest del día automáticamente.
::
::  Doble clic para ejecutar manualmente, o agrega al Task Scheduler
::  con SETUP_DAILY_BACKTEST_SCHEDULER.bat
:: ═══════════════════════════════════════════════════════════════════

set "PROJECT_DIR=C:\Users\FxDarvin\Desktop\PAgina"
set "PYTHON=python"
set "SCRIPT=%PROJECT_DIR%\daily_backtest_runner.py"
set "LOG_DIR=%PROJECT_DIR%\data\research"
set "LOG=%LOG_DIR%\backtest_runner_stdout.txt"

:: Crear directorio de log si no existe
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo.
echo  ════════════════════════════════════════════════════════════
echo    NQ INTELLIGENCE — DAILY BACKTEST
echo    %date% %time%
echo  ════════════════════════════════════════════════════════════
echo.

cd /d "%PROJECT_DIR%"

:: Ejecutar y guardar log con fecha
echo [%date% %time%] Iniciando daily_backtest_runner.py >> "%LOG%"
%PYTHON% "%SCRIPT%" >> "%LOG%" 2>&1
%PYTHON% "%SCRIPT%"

if %errorlevel% equ 0 (
    echo.
    echo  ✅ Backtest completado correctamente.
) else (
    echo.
    echo  ⚠️  El backtest terminó con advertencias. Revisa el log:
    echo     %LOG%
)

echo.
echo  Presiona cualquier tecla para cerrar...
pause >nul
