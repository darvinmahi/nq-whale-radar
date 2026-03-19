---
description: Ultra verify - ensures dashboard meets all quality standards
---

## Workflow: /ultra-verify

Verificación rápida de estándares. Ejecutar en paralelo:

1. **Latido Neuronal activo**: Verificar que `ULTRA_LIVE_CONTROLLER.py` reporta updates cada < 2 segundos.
2. **Trifecta visible**: Confirmar que los 3 bloques del dashboard tienen 4 barras cada uno (4 semanas).
3. **Datos COT frescos**: Verificar que la fecha más reciente en `recent_weeks[0].date` es del reporte CFTC más nuevo.
4. **Cálculo correcto**: `net_position` del reporte más reciente debe coincidir con lo que muestra `peek_cot.py`.
5. **Zero errores JS**: El `agent_live_data.js` debe ser parseable sin errores de sintaxis.

### Comando Rápido de Verficación
```powershell
python peek_cot.py
python agents/agent5_file_injector.py --run-once
```
Revisar output y confirmar que no hay errores.
