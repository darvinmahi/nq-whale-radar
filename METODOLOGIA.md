# METODOLOGÍA DE TRADING — NQ NASDAQ (Whale Radar)

> **Este archivo es la fuente de verdad de la metodología.**
> Leer al inicio de cada sesión de trabajo.

---

## 🗓️ MERCADO OBJETIVO
- **Instrumento**: NQ (Nasdaq 100 Futures)
- **Sesión principal**: New York Open (09:30–11:30 ET)
- **Datos base**: Velas de 3 minutos (backtest) / 1 minuto (live)

---

## 📐 VALUE PROFILE — REGLA CLAVE

El **Volume Profile** se construye desde el **inicio de la sesión Asia** hasta exactamente **10 minutos antes de la apertura de New York** (09:20 ET).

```
INICIO : Asia open (18:00 ET del día anterior)
FIN    : 09:20 ET (10 min antes del NY open)
```

Los niveles resultantes son:
| Nivel | Nombre | Rol |
|---|---|---|
| **VAH** | Value Area High | Resistencia superior del rango de valor |
| **POC** | Point of Control | Precio de mayor actividad / magnet |
| **VAL** | Value Area Low | Soporte inferior del rango de valor |
| **Range High** | Máximo Asia+Londres | Zona de sweep bearish |
| **Range Low** | Mínimo Asia+Londres | Zona de sweep bullish |

> **Lunes**: El rango Asia empieza el Viernes 18:00 ET (mercado cerrado el fin de semana → se usa el gap de apertura del Lunes).

---

## 🔑 LOS 6 PATRONES ICT (Tipos de Movimiento)

### 1. `SWEEP_H_RETURN` — Sweep del High + Retorno
- Precio sube **por encima del Range High** (barrida de liquidez alcista)
- **Cierra de vuelta dentro del rango**
- → **Dirección: SELL / Short**
- Trigger: NY High > Range High + 20 pts, luego precio regresa

### 2. `SWEEP_L_RETURN` — Sweep del Low + Retorno
- Precio baja **por debajo del Range Low** (barrida de liquidez bajista)
- **Cierra de vuelta dentro del rango**
- → **Dirección: BUY / Long**
- Trigger: NY Low < Range Low - 20 pts, luego precio regresa

### 3. `EXPANSION_H` — Expansión Alcista
- Precio rompe el Range High y **no regresa**
- Continuación alcista sostenida
- → **Dirección: BUY / Long (breakout)**
- Se diferencia del SWEEP porque el cierre queda sobre el Range High

### 4. `EXPANSION_L` — Expansión Bajista
- Precio rompe el Range Low y **no regresa**
- Continuación bajista sostenida
- → **Dirección: SELL / Short (breakout)**
- Se diferencia del SWEEP porque el cierre queda bajo el Range Low

### 5. `ROTATION_POC` — Rotación alrededor del POC
- Precio **no sale del rango** Asia+Londres
- Oscila entre VAH y VAL con el POC como pivote
- → **Scalp bidireccional** entre VAH↔VAL
- Típico en días sin noticias importantes

### 6. `NEWS_DRIVE` — Impulso por Noticia
- Rango NY > 250 pts en las primeras 2 horas
- Movimiento unidireccional impulsado por evento macroeconómico
- → **Seguir la dirección inicial** (no ir en contra)
- Noticias clave: CPI, NFP, FOMC, PPI, Retail Sales, ISM

---

## 📊 FRECUENCIA HISTÓRICA DE PATRONES
*(Basado en backtest Mar 2024 – Mar 2026, 564 trades)*

| Patrón | Frecuencia | Notas |
|---|---|---|
| NEWS_DRIVE | ~64% | Domina absolutamente |
| EXPANSION_H | ~14% | Días de tendencia alcista |
| ROTATION_POC | ~12% | Días laterales / sin catalizador |
| SWEEP_H_RETURN | ~4% | Alta precisión cuando aparece |
| SWEEP_L_RETURN | ~4% | Alta precisión cuando aparece |
| EXPANSION_L | ~2% | Menos frecuente |

---

## 📅 COMPORTAMIENTO POR DÍA

| Día | Patrón dominante | Notas |
|---|---|---|
| **Lunes** | SWEEP & RETURN | Post-weekend gap, digestión |
| **Martes** | SWEEP & RETURN → EXPANSION | Puede transicionar a tendencia |
| **Miércoles** | NEWS_DRIVE / EXPANSION | Frecuentemente con datos |
| **Jueves** | NEWS_DRIVE | Jobless claims + otros |
| **Viernes** | NEWS_DRIVE (NFP) / SWEEP | Pre-weekend, liquidez baja cerca del cierre |

---

## 🎯 REGLAS DE ENTRADA

### Uptrend = TRUE (contexto alcista)
- Precio sobre EMA 200 (15min) al open NY
- Priorizar **SWEEP_L_RETURN** y **EXPANSION_H**

### Uptrend = FALSE (contexto bajista)
- Precio bajo EMA 200 (15min) al open NY
- Priorizar **SWEEP_H_RETURN** y **EXPANSION_L**

### Sweep (campo `sweep`)
- `ALTO` = se barrió el máximo → esperar **SELL** (retorno)
- `BAJO` = se barrió el mínimo → esperar **BUY** (retorno)

---

## 📁 ARCHIVOS CLAVE DEL PROYECTO

| Archivo | Descripción |
|---|---|
| `data/research/daily_breakdown_trades.csv` | 564 trades históricos con resultado real |
| `data/research/backtest_research_trades.csv` | 633 trades backtested con patrón |
| `data/research/nq_15m_intraday.csv` | Datos OHLCV 15min NQ (intraday) |
| `check_today_live.py` | Script de análisis del día actual |
| `cloud_runner.py` | Engine principal / runner |
| `landing.html` | Dashboard visual principal |

---

## 🔧 PARÁMETROS TÉCNICOS

```python
BUF    = 20   # puntos buffer para clasificar sweep vs expansion
MARGIN = 20   # margen de toque para niveles VAH/POC/VAL/EMA
NY_OPEN_WINDOW  = "09:30 – 11:30 ET"  # ventana de análisis apertura
PROFILE_START   = "18:00 ET día anterior"  # inicio Value Profile
PROFILE_END     = "09:20 ET"              # fin Value Profile (10 min antes NY)
EMA_PERIOD      = 200                     # EMA en velas 15min
```

---

*Última actualización: 2026-03-25*
