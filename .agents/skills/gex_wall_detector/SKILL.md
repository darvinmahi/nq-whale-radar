# Skill: GEX Wall Detector
- **Descripción:** Mapea los niveles de Gamma Exposure de los Market Makers.
- **Entrada:** JSON de Squeezemetrics (DIX/GEX).
- **Lógica de Análisis:**
    - **GEX > 0:** Régimen de baja volatilidad (Mean reversion).
    - **GEX < 0:** Régimen de alta volatilidad (Trending/Trending).
    - **Flip Point:** Identificar el precio donde el GEX se vuelve negativo.
- **Acción:** Identificar zonas de "imán" para el precio y alertar de posibles "squeezes" cuando el GEX es muy positivo.
