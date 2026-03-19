# 🚀 ULTRA PRO — NQ Intelligence Engine · Guía de Operaciones

> **Modo activo**: ULTRA PRO — Estándar Enterprise / Estado de Guerra  
> **Engine**: v2.1 Parallel · 16 Agentes · Auto-healing  
> **Stack**: Python + Yahoo Finance + Netlify + JS Dashboard

---

## ⚡ Comandos Rápidos

| Comando | Acción |
|---|---|
| `/ultra-review` | Auditoría completa: código + seguridad + rendimiento |
| `/ultra-deploy` | Deploy seguro con backup y rollback automático |
| `/ultra-monitor` | Configurar monitoreo 24/7 y health checks |
| `/ultra-optimize` | Optimización completa: código, datos, assets |
| `/ultra-scale` | Preparar para producción escalada |
| `/ultra-verify` | Verificar que el dashboard cumple todos los estándares |
| `/daily-ultra` | Auditoría diaria con 7 agentes en paralelo |
| `/emergency-fix` | Protocolo de emergencia para fallos críticos |

---

## 🏗️ Arquitectura del Sistema

### Pipeline de Agentes (v2.1)
```
[PRE-QA]     → Agent 0  · QA Commander
[PARALELO 1] → Agent 1  · Data Collector   │ Agent 2 · COT Analyst   │ Agent 3 · Volatility
[PARALELO 2] → Agent 6  · SMC Detective    │ Agent 7 · Probability   │ Agent 8 · Psychologist  │ Agent 9 · Silver Bullet
[PARALELO 3] → Agent 4  · Bias Engine      │ Agent 10 · Learning     │ Agent 12 · Backtester
             → Agent 13 · Research Scout   │ Agent 14 · OrderFlow    │ Agent 15 · Journal Writer
[SERIE]      → Agent 11 · Strategy Crafter → Agent Sentinel
[INJECTOR]   → Agent 5  · File Injector
[POST-QA]    → Agent 0  · QA Commander
```

**Frecuencia**: cada 15 minutos  
**Tiempo por ciclo**: ~3-4 min (antes: ~14 min en serie)

### Estados del Engine
| Estado | Significado |
|---|---|
| `OPTIMAL` | Todos los agentes OK |
| `DEGRADED` | 1-2 agentes con error (sistema funciona) |
| `CRITICAL` | 3+ agentes fallando (revisar inmediatamente) |

---

## 📁 Estructura de Archivos Clave

```
PAgina/
├── run_intelligence_engine.py    ← Motor principal (Ctrl+C para detener)
├── engine_health.json            ← Estado del último ciclo
├── agent_live_data.js            ← Feed de datos para el dashboard
├── index.html                    ← Dashboard principal
├── agents/                       ← 16 agentes especializados
│   ├── agent0_qa_commander.py
│   ├── agent1_data_collector.py  ← Retry + fallback caché
│   ├── agent2_cot_analyst.py
│   ├── agent3_volatility_analyst.py
│   ├── agent4_bias_engine.py
│   ├── agent5_file_injector.py   ← Lee todos los JSONs → JS
│   ├── agent6_smc_detective.py
│   ├── agent7_probability_analyst.py
│   ├── agent8_psychologist.py
│   ├── agent9_silver_bullet.py
│   ├── agent10_learning_engine.py
│   ├── agent11_strategy_crafter.py
│   ├── agent12_backtester.py
│   ├── agent13_research_scout.py
│   ├── agent14_orderflow_expert.py
│   ├── agent15_journal_writer.py
│   └── agent_sentinel.py
├── .agent/
│   ├── rules/
│   │   ├── security-compliance.md
│   │   ├── database-integrity.md
│   │   └── deployment-safety.md
│   └── workflows/
│       ├── daily-ultra.md
│       ├── emergency-fix.md
│       ├── ultra-deploy.md
│       ├── ultra-monitor.md
│       ├── ultra-optimize.md
│       ├── ultra-review.md
│       ├── ultra-scale.md
│       └── ultra-verify.md
└── ULTRA_PRO.md                  ← Este archivo
```

---

## 🚀 Cómo Arrancar el Engine

```bash
# Modo continuo (cada 15 min):
python run_intelligence_engine.py

# Para ver el estado actual:
type engine_health.json

# Un solo ciclo de prueba (Ctrl+C después del primer ciclo):
python run_intelligence_engine.py
```

---

## 🐛 Troubleshooting Rápido

| Síntoma | Diagnóstico | Solución |
|---|---|---|
| `engine_state: CRITICAL` | 3+ agentes fallando | Ver `engine_health.json` → `"details"` para ver cuáles fallan |
| Dashboard sin actualizar | Agent 5 falló | `python agent5_file_injector.py` manualmente |
| Datos `stale: true` | Yahoo Finance caído | El agente usó caché — esperar al próximo ciclo |
| Engine no arranca | Error de importación | `python -c "import agents.agent1_data_collector"` para diagnosticar |

---

## 🔒 Reglas de Seguridad (Mandatory)

- **NO mergear** sin aprobación de Agent 0 QA Commander
- **NO deployar** sin verificar `engine_state != CRITICAL`
- **NO modificar** `agent5_file_injector.py` sin probar aisladamente
- **NO alterar** lógica de cálculo sin actualizar los backtests

---

## 📊 KPIs del Sistema

Monitorear diariamente:
- `agents_ok` ≥ 14/16 (benchmark mínimo)
- `total_time_sec` < 300s (5 min) por ciclo
- `data_quality: FRESH` en Agent 1
- `engine_state: OPTIMAL` o `DEGRADED`

---

*Última actualización del playbook: 2026-03-19 · Engine v2.1*
