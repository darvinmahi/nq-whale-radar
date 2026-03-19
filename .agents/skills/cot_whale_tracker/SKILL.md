# Skill: COT Whale Tracker
- **Descripción:** Analiza el posicionamiento de los Non-Commercials y Commercials en el futuro del Nasdaq.
- **Entrada:** Archivos COT de la CFTC (`data/cot/`).
- **Lógica de Análisis:**
    - **COT Index > 80%:** Acumulación institucional (Bullish).
    - **COT Index < 20%:** Distribución institucional (Bearish).
    - **Cambio de 3 semanas:** Detectar si los institucionales están aumentando posiciones a pesar de que el precio caiga.
- **Acción:** Generar una señal macro semanal cada viernes/lunes.
