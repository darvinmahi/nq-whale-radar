# 🧠 NQ Intelligence Engine — Agentes

Cada archivo aquí es un **agente independiente**. Puedes editarlos por separado
para agregar nuevas fuentes, análisis o lógica sin tocar los otros agentes.

---

## 📁 Estructura

```
PAgina/
├── agents/                          ← Estás aquí
│   ├── agent1_data_collector.py     ← Fetching de datos (Yahoo, Squeezemetrics, CFTC, CME)
│   ├── agent2_cot_analyst.py        ← Análisis COT (CFTC)
│   ├── agent3_volatility_analyst.py ← Análisis VXN + GEX
│   ├── agent4_bias_engine.py        ← Motor de sesgo ponderado
│   └── agent5_file_injector.py      ← Inyecta datos en index.html
│
├── run_intelligence_engine.py       ← Orquestador (ejecuta todos en secuencia)
├── run_engine.bat                   ← Doble clic para correr todo
│
├── agent1_data.json                 ← Salida Agent 1 (raw data)
├── agent2_data.json                 ← Salida Agent 2 (COT analysis)
├── agent3_data.json                 ← Salida Agent 3 (volatility)
├── agent4_data.json                 ← Salida Agent 4 (bias score)
├── agent_live_data.js               ← JS inyectado en index.html
└── index.html                       ← Dashboard
```

---

## ✏️ Cómo agregar tareas a un agente

Cada agente tiene una sección marcada con:
```python
# ══ AGREGAR AQUÍ ↓ ══
```

Solo escribe tu nueva función ahí y agrégala al `output` dict dentro de `run()`.

---

## ▶️ Ejecutar un agente por separado

```bash
python agents/agent1_data_collector.py
python agents/agent2_cot_analyst.py
python agents/agent3_volatility_analyst.py
python agents/agent4_bias_engine.py
python agents/agent5_file_injector.py
```

## ▶️ Ejecutar el pipeline completo

```bash
python run_intelligence_engine.py
```
O doble clic en `run_engine.bat`.
