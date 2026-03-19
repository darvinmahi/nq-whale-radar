@echo off
:: NQ Intelligence Engine — Auto-Launcher
:: Se ejecuta automáticamente al iniciar sesión en Windows
cd /d "C:\Users\FxDarvin\Desktop\PAgina"
start "" "C:\Users\FxDarvin\AppData\Local\Programs\Python\Python312\python.exe" -u run_intelligence_engine.py > logs\engine_autostart.log 2>&1
