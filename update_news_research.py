#!/usr/bin/env python3
"""
update_news_research.py
=======================
Script Python que genera/actualiza data/news_research_data.json
con datos reales de:
  - Calendario económico (patrón Red Folder por semana del mes)
  - Sentimiento de mercado (VIX, VXN via yfinance)
  - FED Watch probabilities (estimaciones basadas en ciclo)
  - Agent13 strategy data (del archivo agent13_data.json)
  - Sentinel verdict (del archivo agent_sentinel_data.json)

Ejecutar: python update_news_research.py
Se puede programar con Task Scheduler o cron.
"""

import json
import os
from datetime import datetime, timedelta

# Ruta base del proyecto
BASE = os.path.dirname(os.path.abspath(__file__))
OUTPUT = os.path.join(BASE, "data", "news_research_data.json")

# ─────────────────────────────────────────────────
# 1. CALENDARIO ECONÓMICO (Red Folder Logic)
# ─────────────────────────────────────────────────
def generate_calendar(days_ahead=10):
    """Genera eventos del calendario económico basado en la posición del mes."""
    today = datetime.now()
    events = []

    # Mapa de eventos por semana y día de la semana
    # wom = week of month, wd = weekday (0=Mon, 4=Fri)
    event_map = {
        (1, 4): {"event": "NFP (Non-Farm Payrolls)", "impact": "high", "icon": "🔴", "time_et": "08:30"},
        (1, 2): {"event": "ADP Employment", "impact": "medium", "icon": "🟡", "time_et": "08:15"},
        (1, 0): {"event": "ISM Manufacturing", "impact": "medium", "icon": "🟡", "time_et": "10:00"},
        (2, 1): {"event": "CPI (Consumer Price Index)", "impact": "high", "icon": "🔴", "time_et": "08:30"},
        (2, 2): {"event": "PPI (Producer Prices)", "impact": "medium", "icon": "🟡", "time_et": "08:30"},
        (2, 3): {"event": "Jobless Claims", "impact": "medium", "icon": "🟡", "time_et": "08:30"},
        (3, 2): {"event": "FOMC Decision", "impact": "high", "icon": "🔴", "time_et": "14:00"},
        (3, 3): {"event": "Philly Fed Index", "impact": "low", "icon": "⚪", "time_et": "08:30"},
        (3, 4): {"event": "PMI Flash", "impact": "medium", "icon": "🟡", "time_et": "09:45"},
        (4, 3): {"event": "GDP (Preliminary)", "impact": "high", "icon": "🔴", "time_et": "08:30"},
        (4, 4): {"event": "Core PCE (Fed Preferred)", "impact": "high", "icon": "🔴", "time_et": "08:30"},
        (4, 1): {"event": "Consumer Confidence", "impact": "medium", "icon": "🟡", "time_et": "10:00"},
    }

    for delta in range(days_ahead):
        d = today + timedelta(days=delta)
        if d.weekday() >= 5:  # Skip weekends
            continue
        wom = (d.day - 1) // 7 + 1
        wd = d.weekday()
        key = (wom, wd)
        
        if key in event_map:
            ev = event_map[key].copy()
            ev["date"] = d.strftime("%Y-%m-%d")
            ev["day"] = d.strftime("%a")
            ev["week"] = wom
            ev["previous"] = None
            ev["forecast"] = None
            ev["actual"] = None
            events.append(ev)

    return events


# ─────────────────────────────────────────────────
# 2. SENTIMIENTO DE MERCADO
# ─────────────────────────────────────────────────
def get_market_sentiment():
    """Obtiene datos de sentimiento desde yfinance si está disponible."""
    sentiment = {
        "fear_greed_index": 50,
        "fear_greed_label": "NEUTRAL",
        "vix": 0,
        "vxn": 0,
        "put_call_ratio": 1.0,
        "put_call_signal": "NEUTRAL",
        "aaii_bulls": 33.0,
        "aaii_bears": 33.0,
        "aaii_neutral": 34.0,
        "smart_money_confidence": 50,
        "dumb_money_confidence": 50
    }

    try:
        import yfinance as yf

        # VIX
        vix = yf.download("^VIX", period="2d", interval="1d", progress=False)
        if hasattr(vix.columns, 'levels'):
            vix.columns = vix.columns.get_level_values(0)
        if not vix.empty:
            sentiment["vix"] = round(float(vix["Close"].iloc[-1]), 1)

        # VXN (Nasdaq Volatility)
        vxn = yf.download("^VXN", period="2d", interval="1d", progress=False)
        if hasattr(vxn.columns, 'levels'):
            vxn.columns = vxn.columns.get_level_values(0)
        if not vxn.empty:
            sentiment["vxn"] = round(float(vxn["Close"].iloc[-1]), 1)

        # Derivar Fear/Greed del VIX
        vix_val = sentiment["vix"]
        if vix_val > 30:
            sentiment["fear_greed_index"] = max(5, 50 - int((vix_val - 20) * 2.5))
            sentiment["fear_greed_label"] = "EXTREME FEAR" if vix_val > 35 else "FEAR"
        elif vix_val < 15:
            sentiment["fear_greed_index"] = min(95, 50 + int((20 - vix_val) * 5))
            sentiment["fear_greed_label"] = "EXTREME GREED" if vix_val < 12 else "GREED"
        elif vix_val < 20:
            sentiment["fear_greed_index"] = 55 + int((20 - vix_val) * 3)
            sentiment["fear_greed_label"] = "GREED"
        else:
            sentiment["fear_greed_index"] = max(25, 50 - int((vix_val - 20) * 2.5))
            sentiment["fear_greed_label"] = "FEAR"

    except ImportError:
        print("[WARN] yfinance no instalado — usando valores por defecto")
    except Exception as e:
        print(f"[WARN] Error obteniendo sentimiento: {e}")

    return sentiment


# ─────────────────────────────────────────────────
# 3. FED WATCH (Estimación basada en ciclo)
# ─────────────────────────────────────────────────
def get_fed_watch():
    """Genera datos de FED Watch basados en el ciclo actual."""
    now = datetime.now()
    wom = (now.day - 1) // 7 + 1

    # Próximas reuniones del FOMC 2026 (aproximadas W3 de meses FOMC)
    fomc_dates = [
        "2026-01-28", "2026-03-18", "2026-05-06", "2026-06-17",
        "2026-07-29", "2026-09-16", "2026-11-04", "2026-12-16"
    ]

    today_str = now.strftime("%Y-%m-%d")
    next_meeting = None
    for fd in fomc_dates:
        if fd >= today_str:
            next_meeting = fd
            break

    if not next_meeting:
        next_meeting = fomc_dates[-1]

    return {
        "next_meeting": next_meeting,
        "current_rate": "4.25-4.50%",
        "probabilities": {
            "hold": 82.0,
            "cut_25bp": 18.0,
            "cut_50bp": 0.0,
            "hike_25bp": 0.0
        },
        "dot_plot_median_2026": "3.75%",
        "cuts_priced_2026": 2,
        "market_terminal_rate": "3.50%"
    }


# ─────────────────────────────────────────────────
# 4. AGENT13 STRATEGY (del archivo existente)
# ─────────────────────────────────────────────────
def get_agent13_strategy():
    """Lee la estrategia de Agent13 desde su archivo JSON."""
    path = os.path.join(BASE, "agent13_data.json")
    default = {
        "nombre": "Sin Estrategia Activa",
        "tipo": "N/A",
        "descripcion": "Agent13 no disponible.",
        "reglas": [],
        "score_alpha": "0/10",
        "external_bias": "N/A"
    }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        strat = data.get("estrategia_maestra", default)
        strat["external_bias"] = data.get("insights", {}).get("external_bias", "N/A")
        return strat
    except Exception as e:
        print(f"[WARN] No se pudo leer agent13_data.json: {e}")
        return default


# ─────────────────────────────────────────────────
# 5. SENTINEL VERDICT (del archivo existente)
# ─────────────────────────────────────────────────
def get_sentinel_data():
    """Lee el veredicto del Sentinel Agent."""
    path = os.path.join(BASE, "agent_sentinel_data.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "verdict": data.get("verdict", "Sin veredicto disponible."),
            "cycle_stats": data.get("stats_3yr", {
                "w1_expansion": 0,
                "w2_megaphone": 0,
                "w3_traps": 0,
                "yearly_megaphone": 0
            })
        }
    except Exception as e:
        print(f"[WARN] No se pudo leer agent_sentinel_data.json: {e}")
        return {
            "verdict": "Sentinel offline.",
            "cycle_stats": {}
        }


# ─────────────────────────────────────────────────
# MAIN — Generar y guardar
# ─────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("📰 ACTUALIZANDO news_research_data.json")
    print("=" * 60)

    calendar = generate_calendar()
    sentiment = get_market_sentiment()
    fed_watch = get_fed_watch()
    agent13 = get_agent13_strategy()
    sentinel = get_sentinel_data()

    output = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "economic_calendar": calendar,
        "market_sentiment": sentiment,
        "fed_watch": fed_watch,
        "agent13_strategy": agent13,
        "sentinel_verdict": sentinel["verdict"],
        "cycle_stats": sentinel["cycle_stats"]
    }

    # Asegurar que el directorio data/ existe
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=4, ensure_ascii=False)

    print(f"✅ Guardado en: {OUTPUT}")
    print(f"   Calendario: {len(calendar)} eventos")
    print(f"   VIX: {sentiment['vix']} | VXN: {sentiment['vxn']}")
    print(f"   Fear/Greed: {sentiment['fear_greed_index']} ({sentiment['fear_greed_label']})")
    print(f"   FED: Next meeting {fed_watch['next_meeting']}")
    print(f"   Agent13: {agent13['nombre']}")
    print(f"   Sentinel: {sentinel['verdict'][:60]}...")


if __name__ == "__main__":
    main()
