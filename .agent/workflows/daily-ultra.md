---
description: Daily ULTRA audit - parallel 7-agent orchestration for Whale Radar
---

## Workflow: /daily-ultra

Ejecuta estos pasos EN PARALELO para el audit diario completo:

### Agentes Simultáneos

**@security-auditor** → Verificar que `agent_live_data.js` no expone datos sin sanitizar. Revisar IDs del HTML. Emitir reporte de vulnerabilidades.

**@database-architect** → Validar que `agent2_data.json` tiene 4+ semanas. Verificar coherencia Trifecta (Specs + Commercials + Retail ≈ 0). Calcular desviación.

**@performance-guru** → Medir tiempo de carga del `index.html`. Objetivo: < 1 segundo. Reportar recursos bloqueantes.

**@cot-analyst** → Confirmar que el último reporte COT es de la semana más reciente disponible (CFTC publica los martes). Verificar `net_position`, `comm_net`, `retail_net`.

**@ux-designer** → Verificar que las 3 columnas Trifecta son visibles en mobile (responsive check). Verificar contraste de colores cyan/blue/orange.

**@test-engineer** → Ejecutar `python agents/agent5_file_injector.py --run-once` y confirmar que el output JS es válido. Verificar que los 3 `renderBars()` se ejecutan.

**@deployer** → Confirmar que `ULTRA_LIVE_CONTROLLER.py` está corriendo. Verificar uptime del engine. Reportar última actualización.

### Criterio de Éxito
- Todos los agentes reportan OK → Estado: ✅ OPTIMAL
- Algún agente reporta WARN → Estado: 🟡 DEGRADED (no crítico)
- Algún agente reporta FAIL → Estado: 🔴 CRITICAL (acción inmediata)
