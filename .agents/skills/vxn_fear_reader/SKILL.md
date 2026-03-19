# Skill: VXN Fear Reader
- **Descripción:** Monitorea e interpreta el índice de volatilidad del Nasdaq (VXN).
- **Entrada:** `agent1_data.json` o consulta directa a Yahoo Finance.
- **Lógica de Análisis:**
    - **< 15:** Complacencia Extrema (Peligro de corrección).
    - **15 - 20:** Alcista Estable.
    - **20 - 28:** Incertidumbre (Reducir riesgo).
    - **28 - 35:** Pánico (Oportunidad de compra).
    - **> 35:** Capitulación (Compra agresiva).
- **Acción:** Cada vez que el VXN cambie de categoría, avisar al usuario y actualizar el Bias Score.
