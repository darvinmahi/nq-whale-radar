@echo off
:: ═══════════════════════════════════════════════════════
:: NQ INTELLIGENCE — START.bat  (Launcher Definitivo)
:: Doble clic para arrancar TODO el sistema.
:: ═══════════════════════════════════════════════════════

title NQ Intelligence System — Iniciando...

:: Ir al directorio del proyecto
cd /d "C:\Users\FxDarvin\Desktop\PAgina"

echo.
echo  ██╗   ██╗ ██████╗         ███████╗██╗   ██╗███████╗
echo  ███╗  ██║██╔═══██╗        ██╔════╝╚██╗ ██╔╝██╔════╝
echo  ████╗ ██║██║   ██║        ███████╗ ╚████╔╝ ███████╗
echo  ██╔██╗██║██║▄▄ ██║        ╚════██║  ╚██╔╝  ╚════██║
echo  ██║╚████║╚██████╔╝███████╗███████║   ██║   ███████║
echo  ╚═╝ ╚═══╝ ╚══▀▀═╝ ╚══════╝╚══════╝   ╚═╝   ╚══════╝
echo.
echo  NQ Intelligence Engine — Sistema 24/7
echo  ════════════════════════════════════════════════════
echo.

:: ─── 1. Matar instancias previas del controlador (si las hay) ───────────────
echo [1/4] Limpiando instancias previas...
taskkill /F /FI "WINDOWTITLE eq NQ Intelligence*" >nul 2>&1
:: No matamos TODOS los python.exe por si acaso hay otros en uso
echo       OK.
echo.

:: ─── 2. Verificar que Python existe ─────────────────────────────────────────
echo [2/4] Verificando Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python no encontrado. Instala Python 3.10+ y agrega al PATH.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo       %%v
echo.

:: ─── 3. Verificar dependencias clave ────────────────────────────────────────
echo [3/4] Verificando dependencias...
python -c "import yfinance, requests" >nul 2>&1
if %errorlevel% neq 0 (
    echo  Instalando dependencias faltantes...
    pip install yfinance requests --quiet
)
echo       Dependencias OK.
echo.

:: ─── 4. Lanzar el controlador principal ────────────────────────────────────
echo [4/4] Lanzando ULTRA_LIVE_CONTROLLER...
echo.
echo  El sistema se actualizara automaticamente:
echo    - Precios NQ/VXN    : cada 5 segundos
echo    - Pipeline completo : cada 15 minutos
echo.
echo  Minimiza esta ventana. NO la cierres.
echo  ════════════════════════════════════════════════════
echo.

title NQ Intelligence System — EN LINEA ✅

python ULTRA_LIVE_CONTROLLER.py

echo.
echo  Sistema detenido. Presiona cualquier tecla para cerrar.
pause >nul
