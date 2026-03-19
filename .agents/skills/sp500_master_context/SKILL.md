# Skill: SP500 Master Context
- **Descripción:** Analiza la correlación entre el S&P 500 y el Nasdaq-100 para detectar divergencias y confirmar tendencias.
- **Entrada:** `agent1_data.json` (VIX, ES=F, BTC).
- **Lógica de Análisis:**
    - **Confirmación:** Si ES (SP500) y NQ (Nasdaq) suben juntos → Tendencia fuerte.
    - **Divergencia de Riesgo:** Si NQ sube pero ES baja → El Nasdaq está "tirando del carro" solo, riesgo de agotamiento rápido.
    - **VIX Alert:** El VIX manda sobre el VXN. Si el VIX rompe al alza, el Nasdaq caerá aunque sus fundamentales locales parezcan buenos.
    - **Crypto Canary:** BTC sirve como detector de "apetito de riesgo". Si BTC cae > 3% en pocas horas, el Nasdaq suele seguirlo.
- **Acción:** Ajustar el Bias Score global por un factor de "Contexto Externo" (0.9x si hay divergencia, 1.1x si hay confirmación).
