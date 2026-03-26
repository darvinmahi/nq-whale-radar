@echo off
:: ═══════════════════════════════════════════════════════════════════
::  SETUP_DAILY_BACKTEST_SCHEDULER.bat
::  Registra la tarea en el Task Scheduler de Windows para ejecutar
::  el backtest diariamente a las 07:00 AM (lun-vie).
::
::  ⚠ Ejecuta como ADMINISTRADOR para que funcione.
:: ═══════════════════════════════════════════════════════════════════

:: Verificar si se ejecuta como admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  ❌ Necesitas ejecutar este script como ADMINISTRADOR.
    echo     Clic derecho → "Ejecutar como administrador"
    echo.
    pause
    exit /b 1
)

set "TASK_NAME=NQ_Intelligence_Daily_Backtest"
set "PROJECT_DIR=C:\Users\FxDarvin\Desktop\PAgina"
set "BAT_FILE=%PROJECT_DIR%\RUN_DAILY_BACKTEST.bat"
set "PYTHON=python"
set "SCRIPT=%PROJECT_DIR%\daily_backtest_runner.py"

echo.
echo  ════════════════════════════════════════════════════════════
echo    CONFIGURANDO TAREA PROGRAMADA — DAILY BACKTEST NQ
echo  ════════════════════════════════════════════════════════════
echo.

:: Eliminar tarea anterior si existe
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
echo  → Tarea anterior eliminada (si existía).

:: Crear la tarea: cada día de lunes a viernes a las 07:00 AM
:: Usa el script python directamente (sin abrir ventana extra con .bat)
schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "\"%PYTHON%\" \"%SCRIPT%\" --no-update" ^
  /sc WEEKLY ^
  /d MON,TUE,WED,THU,FRI ^
  /st 07:00 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %errorlevel% equ 0 (
    echo.
    echo  ✅ Tarea programada creada correctamente:
    echo     Nombre  : %TASK_NAME%
    echo     Horario : Lunes-Viernes a las 07:00 AM
    echo     Script  : %SCRIPT%
    echo.
    echo  Para verificar, abre Task Scheduler ^(taskschd.msc^)
    echo  o ejecuta: schtasks /query /tn "%TASK_NAME%"
) else (
    echo.
    echo  ❌ Error al crear la tarea. Código: %errorlevel%
    echo  → Intenta correr como Administrador.
)

echo.
pause
