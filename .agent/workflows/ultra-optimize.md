---
description: Ultra optimize - full optimization of code, data pipeline, and assets
---

## Workflow: /ultra-optimize

Optimización total del Whale Radar Dashboard.

### 1. Pipeline de Datos
- Revisar `agent1_data_collector.py`: ¿Hace llamadas redundantes a Yahoo Finance?
- Verificar que el intervalo de `pulse_engine.py` no sea menor a 1 segundo (evitar rate-limiting).
- Comprimir `agent2_data.json`: solo guardar los 4 campos de cada semana (date, net_position, comm_net, retail_net, oi).

### 2. JavaScript (agent_live_data.js)
- Eliminar `renderBars()` calls si los contenedores no existen en el DOM.
- Reducir DOM queries: cachear referencias a `document.getElementById()` al inicio.
- Medir tiempo de ejecución del bloque `(function sync(){...})()`.

### 3. HTML (index.html)
- Verificar que no hay CSS inlineado duplicado.
- Confirmar que Tailwind CDN tiene `defer` para no bloquear el render.
- Los 3 contenedores Trifecta deben tener `min-height` para evitar layout shift.

### 4. Python Agents
- `agent2_cot_analyst.py`: Solo descargar CFTC si el último dato tiene más de 6 días de antigüedad.
- `agent5_file_injector.py`: Usar `time.sleep(1)` exacto, no polling agresivo.

### Objetivo de Performance
- Tiempo de carga del HTML: < 1 segundo
- Latencia de actualización de datos: < 2 segundos
- Uso de CPU del engine: < 5%
