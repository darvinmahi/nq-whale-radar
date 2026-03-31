"""
Monday News Tracker — NQ Whale Radar
Registra la noticia del fin de semana y correlaciona con dirección del lunes
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

# ─────────────────────────────────────────
# DATOS HISTÓRICOS  (los 8 lunes del backtest + causa)
# ─────────────────────────────────────────
HISTORICAL = [
    {
        "date": "2026-01-05",
        "direction": "BEARISH",
        "ny_range": 158,
        "pattern": "EXPANSION_H",
        "news_category": "ROTATION",
        "news_summary": "Profit-taking inicio año. Sin catalizador claro. Flujos de rebalanceo Q4→Q1.",
        "news_source": "Reuters / Axios Markets",
        "ema_hit": True,
        "oil_price": 78.0,
        "sentiment": "RISK_OFF",
    },
    {
        "date": "2026-01-12",
        "direction": "BULLISH",
        "ny_range": 216,
        "pattern": "EXPANSION_H",
        "news_category": "MACRO_POSITIVE",
        "news_summary": "Expectativas recorte Fed en marzo. CPI previo mejor de lo esperado. Flujos ETF tech.",
        "news_source": "WSJ / Bloomberg",
        "ema_hit": True,
        "oil_price": 77.5,
        "sentiment": "RISK_ON",
    },
    {
        "date": "2026-01-26",
        "direction": "BULLISH",
        "ny_range": 224,
        "pattern": "EXPANSION_H",
        "news_category": "EARNINGS_SEASON",
        "news_summary": "Inicio earnings Q4. Expectativas positivas MSFT/GOOG. Rotación hacia tech.",
        "news_source": "Barron's / CNBC",
        "ema_hit": False,
        "oil_price": 76.0,
        "sentiment": "RISK_ON",
    },
    {
        "date": "2026-02-02",
        "direction": "BULLISH",
        "ny_range": 373,
        "pattern": "NEWS_DRIVE",
        "news_category": "MACRO_POSITIVE",
        "news_summary": "NFP viernes anterior sorpresa positiva +280K. Mercado descuenta soft landing. Gaps up en futuros Asia.",
        "news_source": "BLS / Reuters",
        "ema_hit": True,
        "oil_price": 78.5,
        "sentiment": "RISK_ON",
    },
    {
        "date": "2026-02-09",
        "direction": "BULLISH",
        "ny_range": 411,
        "pattern": "NEWS_DRIVE",
        "news_category": "MACRO_POSITIVE",
        "news_summary": "Fed Chair Powell: economía 'resiliente'. Sin señales de recesión inminente. Compras institucionales.",
        "news_source": "Fed / Bloomberg",
        "ema_hit": True,
        "oil_price": 79.0,
        "sentiment": "RISK_ON",
    },
    {
        "date": "2026-02-23",
        "direction": "BEARISH",
        "ny_range": 372,
        "pattern": "NEWS_DRIVE",
        "news_category": "GEOPOLITICAL",
        "news_summary": "SPIKE PETRÓLEO: Brent sube >$95/bbl. Drones iraníes atacan plataformas golfo. Risk-off total. Yields suben.",
        "news_source": "Reuters / AP News",
        "ema_hit": True,
        "oil_price": 95.0,
        "sentiment": "RISK_OFF",
    },
    {
        "date": "2026-03-02",
        "direction": "BULLISH",
        "ny_range": 414,
        "pattern": "NEWS_DRIVE",
        "news_category": "MACRO_POSITIVE",
        "news_summary": "CPI viernes +2.8% (estimado 3.1%). Sorpresa bajista → mercado descuenta pausa más larga. Gap up futuros.",
        "news_source": "BLS / CNBC",
        "ema_hit": True,
        "oil_price": 81.0,
        "sentiment": "RISK_ON",
    },
    {
        "date": "2026-03-09",
        "direction": "BULLISH",
        "ny_range": 337,
        "pattern": "NEWS_DRIVE",
        "news_category": "EARNINGS_POSITIVE",
        "news_summary": "NVDA guidance superior en conferencia. Mega-cap tech compras masivas. Futuros Asia +1.5%.",
        "news_source": "NVDA IR / Bloomberg",
        "ema_hit": True,
        "oil_price": 83.0,
        "sentiment": "RISK_ON",
    },
]

# ─────────────────────────────────────────
# CATEGORÍAS DE NOTICIAS
# ─────────────────────────────────────────
NEWS_CATEGORIES = {
    "GEOPOLITICAL":      {"emoji": "🌍", "default_dir": "BEARISH", "volatility": "HIGH"},
    "MACRO_POSITIVE":    {"emoji": "📈", "default_dir": "BULLISH", "volatility": "HIGH"},
    "MACRO_NEGATIVE":    {"emoji": "📉", "default_dir": "BEARISH", "volatility": "HIGH"},
    "EARNINGS_POSITIVE": {"emoji": "💰", "default_dir": "BULLISH", "volatility": "MEDIUM"},
    "EARNINGS_NEGATIVE": {"emoji": "💸", "default_dir": "BEARISH", "volatility": "MEDIUM"},
    "ROTATION":          {"emoji": "🔄", "default_dir": "NEUTRAL", "volatility": "LOW"},
    "FED_HAWKISH":       {"emoji": "🦅", "default_dir": "BEARISH", "volatility": "HIGH"},
    "FED_DOVISH":        {"emoji": "🕊️", "default_dir": "BULLISH",  "volatility": "HIGH"},
    "OIL_SPIKE":         {"emoji": "🛢️", "default_dir": "BEARISH", "volatility": "HIGH"},
    "NO_NEWS":           {"emoji": "😴", "default_dir": "NEUTRAL",  "volatility": "LOW"},
}

# ─────────────────────────────────────────
# ANÁLISIS DE CORRELACIÓN
# ─────────────────────────────────────────
def analyze_news_vs_direction():
    """Muestra correlación entre categoría de noticia y dirección del mercado"""
    
    print("\n" + "="*60)
    print("📰 CORRELACIÓN: NOTICIA FIN DE SEMANA vs DIRECCIÓN LUNES")
    print("="*60)
    
    cat_stats = {}
    for s in HISTORICAL:
        cat = s["news_category"]
        if cat not in cat_stats:
            cat_stats[cat] = {"BULLISH": 0, "BEARISH": 0, "NEUTRAL": 0, "ranges": []}
        cat_stats[cat][s["direction"]] += 1
        cat_stats[cat]["ranges"].append(s["ny_range"])
    
    for cat, stats in cat_stats.items():
        total = stats["BULLISH"] + stats["BEARISH"] + stats["NEUTRAL"]
        bull_pct = stats["BULLISH"] / total * 100
        avg_range = sum(stats["ranges"]) / len(stats["ranges"])
        emoji = NEWS_CATEGORIES.get(cat, {}).get("emoji", "❓")
        print(f"\n{emoji} {cat}")
        print(f"   ▲ Bullish: {stats['BULLISH']}/{total} ({bull_pct:.0f}%)  |  Rango prom: {avg_range:.0f} pts")

def show_bearish_mondays():
    """Detalle de los lunes bajistas y su causa"""
    
    print("\n" + "="*60)
    print("🔴 LUNES BEARISH — Análisis de causa")
    print("="*60)
    
    bearish = [s for s in HISTORICAL if s["direction"] == "BEARISH"]
    for s in bearish:
        cat_info = NEWS_CATEGORIES.get(s["news_category"], {})
        print(f"\n📅 {s['date']}")
        print(f"   Categoría: {cat_info.get('emoji','')} {s['news_category']}")
        print(f"   Rango NY:  {s['ny_range']} pts")
        print(f"   Oil:       ${s['oil_price']}/bbl")
        print(f"   Causa:     {s['news_summary']}")
        print(f"   Fuente:    {s['news_source']}")

def sources_to_check_sunday():
    """Lista de fuentes a revisar cada domingo noche"""
    
    print("\n" + "="*60)
    print("📋 CHECKLIST DOMINGO NOCHE — Antes del lunes")
    print("="*60)
    sources = [
        ("18:00 ET", "Axios Markets Newsletter", "axios.com/newsletters/markets", "Resumen semanal + qué mover el lunes"),
        ("19:00 ET", "Reuters World/Business", "reuters.com", "Geopolitical + macro headlines"),
        ("20:00 ET", "CNBC Futures Now", "cnbc.com/futures-now", "Ver dónde abren futuros NQ/ES"),
        ("20:30 ET", "Twitter/X: @kgreifeld @markets", "x.com", "Análisis hedge funds y sell-side"),
        ("21:00 ET", "Barron's Weekend", "barrons.com", "Cover story = sesgo institucional"),
        ("22:00 ET", "GS Weekly Kickstart (si tienes)", "gs.com (institutcional)", "Forecast semanal equities"),
    ]
    
    for time, name, url, desc in sources:
        print(f"\n  ⏰ {time}")
        print(f"     📰 {name}")
        print(f"     🔗 {url}")
        print(f"     ℹ️  {desc}")

def add_next_monday(date_str: str, category: str, summary: str, source: str, oil_price: float = 0.0):
    """
    Registra la noticia del próximo lunes ANTES de que abra el mercado
    
    Uso:
        add_next_monday(
            date_str="2026-03-30",
            category="MACRO_POSITIVE",
            summary="PCE viernes +2.6% vs 2.8% esperado. Core inflation bajando.",
            source="BEA / Reuters",
            oil_price=110.0
        )
    """
    entry = {
        "date": date_str,
        "direction": "PENDING",
        "ny_range": None,
        "pattern": "UNKNOWN",
        "news_category": category,
        "news_summary": summary,
        "news_source": source,
        "ema_hit": None,
        "oil_price": oil_price,
        "sentiment": "UNKNOWN",
        "timestamp_added": datetime.now().isoformat(),
    }
    
    # Predicción basada en categoría
    cat_info = NEWS_CATEGORIES.get(category, {})
    predicted_dir = cat_info.get("default_dir", "NEUTRAL")
    volatility    = cat_info.get("volatility", "MEDIUM")
    
    print(f"\n✅ Entrada registrada para {date_str}")
    print(f"   Categoría: {cat_info.get('emoji','')} {category}")
    print(f"   Predicción: {predicted_dir} (volatilidad {volatility})")
    print(f"   Noticia: {summary[:80]}...")
    
    # Guardar JSON
    out_path = Path("data/research/monday_news_log.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    existing = []
    if out_path.exists():
        with open(out_path) as f:
            existing = json.load(f)
    
    existing.append(entry)
    with open(out_path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    
    print(f"   💾 Guardado en {out_path}")
    return entry

def quick_predict(category: str) -> dict:
    """Predicción rápida dado una categoría de noticia"""
    cat_info = NEWS_CATEGORIES.get(category)
    if not cat_info:
        print(f"❌ Categoría desconocida. Opciones: {', '.join(NEWS_CATEGORIES.keys())}")
        return {}
    
    # Stats históricas de esa categoría
    matching = [s for s in HISTORICAL if s["news_category"] == category]
    if matching:
        bullish_count = sum(1 for s in matching if s["direction"] == "BULLISH")
        bull_pct = bullish_count / len(matching) * 100
        avg_range = sum(s["ny_range"] for s in matching) / len(matching)
    else:
        bull_pct = 50.0
        avg_range = 313.0  # promedio general
    
    print(f"\n🎯 PREDICCIÓN RÁPIDA: {cat_info['emoji']} {category}")
    print(f"   Dirección esperada: {cat_info['default_dir']}")
    print(f"   Bullish histórico:  {bull_pct:.0f}%")
    print(f"   Rango esperado NY:  {avg_range:.0f} pts")
    print(f"   Volatilidad:        {cat_info['volatility']}")
    
    return {
        "category": category,
        "predicted_direction": cat_info["default_dir"],
        "bullish_pct": bull_pct,
        "expected_range": avg_range,
        "volatility": cat_info["volatility"],
    }

# ─────────────────────────────────────────
# MAIN — Ejecutar análisis completo
# ─────────────────────────────────────────
if __name__ == "__main__":
    
    print("\n🐋 WHALE RADAR — Monday News Tracker")
    print(f"📅 Hoy: {datetime.now().strftime('%A %d %b %Y %H:%M')}")
    
    # 1. Análisis histórico
    analyze_news_vs_direction()
    
    # 2. Detalle lunes bajistas
    show_bearish_mondays()
    
    # 3. Qué revisar este domingo
    sources_to_check_sunday()
    
    print("\n" + "="*60)
    print("📅 PRÓXIMO LUNES: 30 Marzo 2026")
    print("="*60)
    print("""
NOTICIA DOMINANTE ESTE FIN DE SEMANA:
  🛢️ Petróleo Brent $110/bbl — Tensión Irán/Estrecho Ormuz
  📊 PCE de viernes (dato inflación favorito del Fed)
  🌍 Sentimiento GS: -0.9 (mínimo desde Agosto 2025)

CATEGORÍA PROBABLE: OIL_SPIKE + MACRO_NEGATIVE
""")
    quick_predict("OIL_SPIKE")
    
    print("""
─────────────────────────────────────────
USO: Para registrar noticia del próximo lunes:

    add_next_monday(
        date_str="2026-03-30",
        category="GEOPOLITICAL",   # ← cambia según lo que veas
        summary="Petróleo $110 por tensión Irán. Risk-off en Asia.",
        source="Reuters Sunday",
        oil_price=110.0
    )
─────────────────────────────────────────
""")
