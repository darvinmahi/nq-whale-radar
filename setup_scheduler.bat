@echo off
setlocal

:: Get current directory
set "SCRIPT_DIR=%~dp0"
set "EXEC_PATH=%SCRIPT_DIR%run_engine.bat"

echo ============================================================
echo   NQ INTELLIGENCE ENGINE — Windows Task Scheduler
echo ============================================================
echo.
echo Looking for engine batch: %EXEC_PATH%
echo.

if not exist "%EXEC_PATH%" (
    echo [ERROR] No se encontró run_engine.bat en %SCRIPT_DIR%
    pause
    exit /b 1
)

echo Registering task "NQ Intelligence Engine" to run every hour...

:: Create the task
:: /sc hourly : run every hour
:: /mo 1      : modifier 1 (once every hour)
:: /tn        : task name
:: /tr        : task run (command)
:: /f         : force (overwrite existing)
schtasks /create /sc hourly /mo 1 /tn "NQ Intelligence Engine" /tr "\"%EXEC_PATH%\"" /f

if %errorlevel% equ 0 (
    echo.
    echo ✅ TASK REGISTERED SUCCESSFULLY.
    echo.
    echo The engine will now run automatically every hour.
    echo You can check status with: schtasks /query /tn "NQ Intelligence Engine"
) else (
    echo.
    echo ❌ FAILED TO REGISTER TASK. 
    echo Please run this script as ADMINISTRATOR if it fails.
)

pause
