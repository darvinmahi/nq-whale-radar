#!/usr/bin/env python3
"""
auto_deploy.py — NQ Intelligence Engine
Hace git push automático cada vez que los agentes actualizan agent_live_data.js
El sitio en Netlify se actualiza en ~15-30 segundos después del push.

USO:
    python auto_deploy.py               # push manual
    python auto_deploy.py --watch       # modo daemon: detecta cambios y pushea

INTEGRACIÓN EN AGENTES:
    Al final de cualquier script que genere datos, añadir:
        from auto_deploy import push_site
        push_site("data: live update from agent X")
"""

import subprocess
import sys
import time
import os

SITE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_TO_TRACK = [
    "agent_live_data.js",
    "agent_live_data_v2.js",
    "index.html",
    "analisis_orderflow.html",
    "analisis_promax.html.html",
]

def run(cmd, cwd=SITE_DIR):
    """Ejecuta un comando git y retorna (éxito, output)."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True
    )
    return result.returncode == 0, result.stdout.strip() or result.stderr.strip()


def push_site(message="data: live update"):
    """
    Stagea, commitea y pushea los archivos de datos.
    Llama esta función desde tus agentes después de escribir agent_live_data.js
    """
    print(f"\n🚀 [AUTO-DEPLOY] Iniciando push → Netlify")
    print(f"   Directorio: {SITE_DIR}")

    # 1. Verificar que es un repo git
    ok, _ = run(["git", "status"])
    if not ok:
        print("❌ ERROR: No es un repositorio git.")
        print("   Ejecuta primero: git init && git remote add origin <URL>")
        return False

    # 2. Stage solo los archivos de datos + html
    files_staged = []
    for f in FILES_TO_TRACK:
        path = os.path.join(SITE_DIR, f)
        if os.path.exists(path):
            run(["git", "add", f])
            files_staged.append(f)

    if not files_staged:
        print("⚠️  No hay archivos para stagear.")
        return False

    print(f"   ✅ Staged: {', '.join(files_staged)}")

    # 3. Verificar si hay cambios reales para commitear
    ok, status = run(["git", "diff", "--cached", "--stat"])
    if not ok or not status:
        print("   ℹ️  Sin cambios nuevos. Nada que pushear.")
        return True

    # 4. Commit
    timestamp = time.strftime("%H:%M:%S UTC", time.gmtime())
    commit_msg = f"{message} [{timestamp}]"
    ok, out = run(["git", "commit", "-m", commit_msg])
    if not ok:
        print(f"❌ Commit falló: {out}")
        return False
    print(f"   ✅ Commit: {commit_msg}")

    # 5. Push
    ok, out = run(["git", "push", "origin", "main"])
    if not ok:
        # Intentar con master
        ok, out = run(["git", "push", "origin", "master"])
    if not ok:
        print(f"❌ Push falló: {out}")
        print("   Verifica que tienes configurado el remote: git remote -v")
        return False

    print(f"   ✅ Push exitoso. Netlify actualizando en ~20 segundos...")
    return True


def watch_and_push(interval=30):
    """Daemon que monitorea cambios cada N segundos y pushea automáticamente."""
    print(f"\n👁️  MODO WATCH — Monitoreando cambios cada {interval}s")
    print(f"   Ctrl+C para detener\n")

    last_modified = {}
    for f in FILES_TO_TRACK:
        path = os.path.join(SITE_DIR, f)
        if os.path.exists(path):
            last_modified[f] = os.path.getmtime(path)

    while True:
        changed = []
        for f in FILES_TO_TRACK:
            path = os.path.join(SITE_DIR, f)
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if mtime != last_modified.get(f):
                    changed.append(f)
                    last_modified[f] = mtime

        if changed:
            print(f"\n🔔 Cambios detectados: {', '.join(changed)}")
            push_site(f"data: auto-update ({', '.join(changed)})")

        time.sleep(interval)


if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_and_push(interval=30)
    else:
        push_site("deploy: manual push")
