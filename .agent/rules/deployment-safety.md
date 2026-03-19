# 🟢 REGLA: DEPLOYMENT SAFETY

## Activación
Se aplica antes de cualquier modificación a `index.html` o `agent_live_data.js`.

## Checklist de Despliegue (NO OMITIR)
1. **Backup automático**: Crear copia de `index.html` → `index.html.bak` antes de editar.
2. **Verificar IDs de elementos**: Confirmar que los `id=""` en HTML coincidan con los `getElementById()` en el inyector JS.
3. **Test de renderizado**: Abrir el HTML en el browser y verificar que la sección Trifecta muestra las 3 columnas.
4. **Engine running**: Confirmar que `ULTRA_LIVE_CONTROLLER.py` está activo antes de verificar datos live.
5. **Rollback plan**: Si algo falla, usar `index.html.bak` para restaurar en < 30 segundos.

## Reglas de Modificación
- **NUNCA** eliminar un `id=""` del HTML sin actualizar el inyector correspondiente.
- **SIEMPRE** mantener los 3 bloques: `cot-specs-bars`, `cot-comm-bars`, `cot-retail-bars`.
- **SIEMPRE** mantener `cot-table-body` para la matrix de datos crudos.

## Verificación Post-Deploy
- [ ] ¿El "Latido Neuronal" actualiza cada segundo?
- [ ] ¿Los 3 bloques (Whales/Banks/Retail) tienen 4 barras cada uno?
- [ ] ¿La tabla matrix muestra 4 filas de datos COT?
