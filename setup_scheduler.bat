@echo off
:: ═══════════════════════════════════════════════════════════
:: NQ Intelligence — setup_scheduler.bat
:: Registra la tarea en Windows Task Scheduler para que
:: el sistema arranque AUTOMÁTICAMENTE al iniciar Windows.
::
:: EJECUTAR COMO ADMINISTRADOR
:: ═══════════════════════════════════════════════════════════

:: Verificar privilegios de administrador
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Este script necesita permisos de Administrador.
    echo  Haz clic derecho en este archivo y elige "Ejecutar como administrador".
    echo.
    pause
    exit /b 1
)

set "PROJECT_DIR=C:\Users\FxDarvin\Desktop\PAgina"
set "START_BAT=%PROJECT_DIR%\START.bat"
set "TASK_NAME=NQ Intelligence System"

echo.
echo  ═══════════════════════════════════════════════════════
echo    NQ INTELLIGENCE — Registro en Task Scheduler
echo  ═══════════════════════════════════════════════════════
echo.

if not exist "%START_BAT%" (
    echo  [ERROR] No se encontro START.bat en %PROJECT_DIR%
    pause
    exit /b 1
)

echo  Directorio del proyecto : %PROJECT_DIR%
echo  Archivo a ejecutar      : %START_BAT%
echo  Nombre de la tarea      : %TASK_NAME%
echo.

:: ─── Eliminar tarea previa si existe ────────────────────────────────────────
schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1

:: ─── Crear tarea: al iniciar sesión de Windows ──────────────────────────────
:: /sc onlogon   → ejecutar al iniciar sesión
:: /rl highest   → ejecutar con máximos privilegios
:: /f            → forzar (sobreescribir si ya existe)
:: /delay       → esperar 30s después del login para que la red esté lista
schtasks /create ^
    /sc onlogon ^
    /tn "%TASK_NAME%" ^
    /tr "\"%START_BAT%\"" ^
    /rl highest ^
    /f ^
    /delay 0000:30

if %errorlevel% equ 0 (
    echo.
    echo  ✅ TAREA REGISTRADA EXITOSAMENTE.
    echo.
    echo  El sistema NQ Intelligence se iniciara automaticamente
    echo  cada vez que inicies sesion en Windows.
    echo.
    echo  Para verificar:
    echo    schtasks /query /tn "%TASK_NAME%"
    echo.
    echo  Para lanzarlo AHORA sin reiniciar:
    echo    schtasks /run /tn "%TASK_NAME%"
    echo.
    set /p "LAUNCH_NOW=Quieres lanzarlo AHORA? (s/n): "
    if /i "%LAUNCH_NOW%"=="s" (
        echo  Lanzando...
        schtasks /run /tn "%TASK_NAME%"
    )
) else (
    echo.
    echo  ❌ ERROR al registrar la tarea.
    echo  Asegurate de ejecutar este script como Administrador.
)

echo.
pause
