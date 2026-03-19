# 🟡 REGLA: DATABASE INTEGRITY (Market Data Precision)

## Activación
Se aplica a todos los agentes que procesan datos de mercado (COT, VXN, NQ, backtest).

## Mandatos
1. **Precisión de cálculo**: El `cot_index`, `net_position`, `comm_net`, y `retail_net` deben calcularse con al menos 2 decimales de precisión.
2. **Datos históricos**: El array `recent_weeks` en `agent2_data.json` debe contener SIEMPRE 4 semanas mínimo.
3. **Coherencia Trifecta**: La suma de `net_position + comm_net + retail_net` debe ser = 0 (o cercana a 0). Si diverge >5%, emitir alerta.
4. **Fechas válidas**: Ningún reporte COT con fecha anterior a 30 días debe ser marcado como "último".
5. **Campos requeridos por semana**:
   - `date` (string YYYY-MM-DD)
   - `net_position` (int, Specs)
   - `comm_net` (int, Commercials)
   - `retail_net` (int, Non-Reportable)
   - `oi` (int, Open Interest)

## Tests de Validación
Antes de escribir `agent2_data.json`, el agente debe verificar:
- [ ] ¿Hay exactamente 4+ semanas en `recent_weeks`?
- [ ] ¿Los valores son numéricos (no None/null)?
- [ ] ¿La coherencia Trifecta está dentro del ±5%?
