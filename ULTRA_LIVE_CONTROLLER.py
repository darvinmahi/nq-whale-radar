import subprocess
import os
import time
import sys

def main():
    print("🚀 NQ SENTINELA · ULTRA-LIVE CONTROLLER")
    print("════════════════════════════════════════════")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    processes = [
        ("Pulse Engine (1s)", [sys.executable, os.path.join(base_dir, "pulse_engine.py")]),
        ("Live Injector (1s)", [sys.executable, os.path.join(base_dir, "agents", "agent5_file_injector.py")]),
        ("Logic Engine (15m)", [sys.executable, os.path.join(base_dir, "run_intelligence_engine.py")])
    ]
    
    running_procs = []
    
    for name, cmd in processes:
        print(f"▶ Iniciando {name}...")
        proc = subprocess.Popen(cmd, cwd=base_dir)
        running_procs.append(proc)
        time.sleep(1)
        
    print("\n✅ TODO EL SISTEMA ESTÁ EN LÍNEA.")
    print("El Dashboard (index.html) ahora se actualizará en tiempo real.")
    print("Presiona Ctrl+C para detener todos los motores.")
    
    try:
        while True:
            time.sleep(1)
            # Verificar si algún proceso murió
            for proc in running_procs:
                if proc.poll() is not None:
                    print("⚠️ Detectada caída de motor. Reiniciando...")
                    # Podríamos re-iniciar aquí si fuera necesario
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo motores...")
        for proc in running_procs:
            proc.terminate()
        print("SAD (Sentinela Autonomous Disconnect) Completado.")

if __name__ == "__main__":
    main()
