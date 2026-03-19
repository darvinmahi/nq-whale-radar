---
description: Ultra review - complete audit (code + security + performance)
---

## Workflow: /ultra-review

Auditoría completa del dashboard Whale Radar.

1. **Security Check**: Leer `.agent/rules/security-compliance.md`. Verificar `agent_live_data.js` y el HTML contra las reglas.
2. **Data Integrity**: Leer `.agent/rules/database-integrity.md`. Ejecutar `python peek_cot.py` para verificar los últimos 4 reportes COT.
3. **COT Trifecta check**: Verificar que `cot-specs-bars`, `cot-comm-bars`, `cot-retail-bars` tienen IDs correctos en `index.html`.
4. **Reporte**: Emitir resumen con estado OK/WARN/FAIL por categoría.
