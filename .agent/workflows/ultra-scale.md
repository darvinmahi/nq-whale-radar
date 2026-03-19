---
description: Ultra scale - prepares the dashboard for production deployment
---

## Workflow: /ultra-scale

Preparación del Whale Radar para producción y escalado.

### Fase A: Preparación Local (Actual)
El sistema actual corre en local (`file://`). Esto es correcto para uso personal/desarrollo.
- Engine: `ULTRA_LIVE_CONTROLLER.py` corriendo en background ✅
- Dashboard: `index.html` abriendo directamente en browser ✅
- Datos: actualizados cada segundo vía `agent_live_data.js` ✅

### Fase B: Despliegue Web (Cuando esté listo)
Para hacer el dashboard accesible desde cualquier dispositivo:

#### Opción 1: Servidor Local Simple
```powershell
# Servir el dashboard en http://localhost:8080
python -m http.server 8080 --directory c:\Users\FxDarvin\Desktop\PAgina
```

#### Opción 2: GitHub Pages (Gratis, público)
1. Crear repositorio en GitHub.
2. Subir `index.html` + `agent_live_data.js`.
3. Activar GitHub Pages en Settings → Pages.
4. **Limitación**: Los datos solo se actualizan al hacer push manual.

#### Opción 3: VPS + Python Server (Producción real)
- Contratar un VPS (DigitalOcean, Contabo).
- Subir todo el proyecto.
- Ejecutar `ULTRA_LIVE_CONTROLLER.py` como servicio systemd.
- Nginx para servir el HTML.

### Escalado de Datos
- Para manejar más usuarios: los agentes Python ya son stateless.
- El cuello de botella serán los rate limits de Yahoo Finance y CFTC.
- Solución a futuro: caché Redis entre el engine y el frontend.

### Estado Actual Recomendado
> ✅ Uso local con browser: ÓPTIMO para análisis personal diario.
> ⏳ Despliegue web: cuando quieras compartir el dashboard.
