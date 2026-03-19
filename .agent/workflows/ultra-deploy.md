---
description: Ultra deploy - deploys changes safely with backup and rollback
---

## Workflow: /ultra-deploy

Protocolo de despliegue seguro. NUNCA omitir este proceso.

### Pre-Deploy (obligatorio)
```powershell
# 1. Backup
copy c:\Users\FxDarvin\Desktop\PAgina\index.html c:\Users\FxDarvin\Desktop\PAgina\index.html.bak
```

### Deploy
1. Aplicar cambios al `index.html` o agentes.
2. Ejecutar `python agents/agent5_file_injector.py --run-once`.
3. Verificar que el JS generado no tiene errores de sintaxis.

### Post-Deploy Verification
- [ ] ¿Las 3 columnas Trifecta están visibles?
- [ ] ¿El `cot-table-body` muestra 4 filas?
- [ ] ¿El "Latido Neuronal" actualiza cada segundo?

### Rollback (si algo falla)
```powershell
copy c:\Users\FxDarvin\Desktop\PAgina\index.html.bak c:\Users\FxDarvin\Desktop\PAgina\index.html
```
