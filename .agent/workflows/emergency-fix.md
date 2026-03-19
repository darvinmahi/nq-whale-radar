---
description: Emergency fix protocol for critical Whale Radar failures
---

## Workflow: /emergency-fix

Protocolo de respuesta rápida para fallos críticos. Ejecutar en SECUENCIA:

### Paso 1: Triage (< 2 min)
**@debugger** → Identificar síntoma exacto:
- ¿Dashboard sin datos? → Verificar `agent_live_data.js` y el controller.
- ¿Barras Trifecta vacías? → Verificar IDs `cot-specs-bars`, `cot-comm-bars`, `cot-retail-bars`.
- ¿Datos desactualizados? → Verificar que `ULTRA_LIVE_CONTROLLER.py` está corriendo.

### Paso 2: Análisis de Impacto (< 3 min)
**@security-auditor** → Confirmar que el fallo NO es una brecha de seguridad (datos externos maliciosos).
**@database-architect** → Verificar integridad del `agent2_data.json`. ¿Los 4 campos por semana están presentes?

### Paso 3: Fix & Test (< 5 min)
**@tester** → Ejecutar `python agents/agent5_file_injector.py --run-once`. Verificar output. Crear test que prevenga la recurrencia.

### Paso 4: Deploy & Rollback Ready
**@deployer** →
- Si el fix funciona: Reiniciar `ULTRA_LIVE_CONTROLLER.py`.
- Si el fix falla: Restaurar `index.html` desde `index.html.bak`.

### Rollback de Emergencia (< 30 segundos)
```
copy index.html.bak index.html
python agents/agent5_file_injector.py --run-once
```
