# 🔴 REGLA: SECURITY COMPLIANCE (Fintech Grade)

## Activación
Esta regla se aplica a CADA cambio de código en el proyecto.

## Mandatos
1. **No vulnerabilidades críticas**: Ningún código con inyección de datos externos sin sanitizar.
2. **Auditría pre-commit**: Verificar que no existan credenciales hardcodeadas (API keys, passwords).
3. **Validación de inputs**: Todo dato externo (CFTC, Yahoo Finance, COT) debe validarse antes de renderizarse en el HTML.
4. **Content Security Policy**: El `index.html` no debe cargar scripts externos sin `integrity` hash.
5. **Datos JSON**: Los archivos `agent*_data.json` jamás deben exponer datos sensibles al frontend sin filtrado.

## Verificación Automática
Antes de cualquier cambio en `index.html` o `agent_live_data.js`, confirmar:
- [ ] ¿El dato viene de una fuente confiable (CFTC oficial, Yahoo Finance)?
- [ ] ¿Está sanitizado antes de inyectarse en el DOM?
- [ ] ¿No hay eval() ni innerHTML con datos brutos no validados?
