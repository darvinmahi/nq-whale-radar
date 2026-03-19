---
description: Ultra monitor - 24/7 monitoring configuration and health checks
---

## Workflow: /ultra-monitor

Monitoreo continuo del sistema Whale Radar.

### Checks de Salud (Ejecutar cada vez que abras el proyecto)

#### 1. Engine Status
```powershell
# Verificar que el controller está corriendo
Get-Process python | Where-Object {$_.CommandLine -like "*ULTRA_LIVE_CONTROLLER*"}
```

#### 2. Frescura de Datos
```python
# peek_cot.py ya hace esto - ejecutar y verificar:
# - Fecha del último reporte COT (debe ser <= 7 días)
# - net_position, comm_net, retail_net son numéricos
python peek_cot.py
```

#### 3. Validación del JS generado
```powershell
# Verificar que agent_live_data.js fue modificado hace < 5 segundos
(Get-Item agent_live_data.js).LastWriteTime
```

#### 4. Integridad del HTML
- Abrir `index.html` en el browser.
- Confirmar que los 3 bloques Trifecta tienen barras.
- Confirmar que la tabla matrix tiene 4 filas.

### Alertas Manuales (señales de problema)
| Señal | Diagnóstico | Acción |
|---|---|---|
| Barras vacías | `cot-specs-bars` sin contenido | Ejecutar `/emergency-fix` |
| Fecha COT vieja | > 7 días sin actualizar | Re-ejecutar `agent2_cot_analyst.py` |
| Latido Neuronal detenido | Controller muerto | Reiniciar `ULTRA_LIVE_CONTROLLER.py` |
| JS con `null` en todo | `agent1_data.json` vacío | Re-ejecutar `agent1_data_collector.py` |
