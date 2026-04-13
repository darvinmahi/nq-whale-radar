"""
SOURCE: NOTICIAS LIVE — Financial News & Calendar
=======================================================
Provee noticias financieras en tiempo real + calendario economico
  OK: Finviz RSS (gratis, sin API key)
  OK: FRED API (datos macro)
  OK: Clasificacion de impacto automatica
"""

import os, json, requests, datetime, re
from xml.etree import ElementTree

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "news_live.json")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "NQ-Intelligence-Engine/3.0"
})

# Keywords que mueven el NQ
HIGH_IMPACT_KEYWORDS = [
    "fed", "fomc", "rate", "cpi", "ppi", "nfp", "jobs", "payroll",
    "inflation", "gdp", "recession", "crash", "rally", "nasdaq",
    "tariff", "trade war", "china", "earnings", "nvidia", "apple",
    "microsoft", "tesla", "meta", "amazon", "google", "ai ",
    "powell", "yellen", "treasury", "debt ceiling", "shutdown",
    "unemployment", "consumer", "retail sales", "housing"
]

MEDIUM_IMPACT_KEYWORDS = [
    "oil", "gold", "dollar", "dxy", "bond", "yield", "vix",
    "crypto", "bitcoin", "ipo", "merger", "acquisition",
    "upgrade", "downgrade", "outlook", "guidance", "revenue",
    "profit", "loss", "bank", "tech", "semiconductor"
]

BEARISH_KEYWORDS = [
    "crash", "recession", "downgrade", "sell", "bearish", "decline",
    "layoff", "cut", "miss", "disappoint", "risk", "fear", "panic",
    "dump", "drop", "plunge", "tumble", "slump", "warning", "weak",
    "tariff", "war", "sanction", "default", "debt"
]

BULLISH_KEYWORDS = [
    "rally", "surge", "bullish", "upgrade", "buy", "beat", "record",
    "growth", "boom", "breakout", "strong", "high", "gain", "jump",
    "soar", "optimism", "confidence", "expansion", "stimulus",
    "rate cut", "dovish", "ai boom", "innovation"
]


def classify_impact(title):
    """Clasifica el impacto de una noticia: HIGH, MEDIUM, LOW."""
    t = title.lower()
    for kw in HIGH_IMPACT_KEYWORDS:
        if kw in t:
            return "HIGH"
    for kw in MEDIUM_IMPACT_KEYWORDS:
        if kw in t:
            return "MEDIUM"
    return "LOW"


def classify_sentiment(title):
    """Clasifica el sentimiento: BULLISH, BEARISH, NEUTRAL."""
    t = title.lower()
    bull_count = sum(1 for kw in BULLISH_KEYWORDS if kw in t)
    bear_count = sum(1 for kw in BEARISH_KEYWORDS if kw in t)
    if bull_count > bear_count:
        return "BULLISH"
    elif bear_count > bull_count:
        return "BEARISH"
    return "NEUTRAL"


def fetch_finviz_news():
    """Fetch noticias de Finviz RSS (gratis, sin API key)."""
    print("[News] Fetching Finviz RSS...")
    news = []
    try:
        urls = [
            "https://finviz.com/news_feed.ashx",
        ]
        for url in urls:
            r = SESSION.get(url, timeout=15)
            if r.status_code != 200:
                continue
            root = ElementTree.fromstring(r.content)
            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pub = item.find("pubDate")
                if title is not None:
                    t = title.text or ""
                    news.append({
                        "title": t,
                        "link": link.text if link is not None else "",
                        "time": pub.text if pub is not None else "",
                        "source": "Finviz",
                        "impact": classify_impact(t),
                        "sentiment": classify_sentiment(t),
                    })
        print(f"  [OK] {len(news)} noticias de Finviz")
    except Exception as e:
        print(f"  [ERROR] Finviz: {e}")
    return news


def fetch_marketwatch_rss():
    """Fetch noticias de MarketWatch RSS."""
    print("[News] Fetching MarketWatch RSS...")
    news = []
    try:
        url = "https://feeds.marketwatch.com/marketwatch/topstories/"
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            root = ElementTree.fromstring(r.content)
            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pub = item.find("pubDate")
                if title is not None:
                    t = title.text or ""
                    news.append({
                        "title": t,
                        "link": link.text if link is not None else "",
                        "time": pub.text if pub is not None else "",
                        "source": "MarketWatch",
                        "impact": classify_impact(t),
                        "sentiment": classify_sentiment(t),
                    })
        print(f"  [OK] {len(news)} noticias de MarketWatch")
    except Exception as e:
        print(f"  [ERROR] MarketWatch: {e}")
    return news


def fetch_cnbc_rss():
    """Fetch noticias de CNBC RSS."""
    print("[News] Fetching CNBC RSS...")
    news = []
    try:
        url = "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            root = ElementTree.fromstring(r.content)
            for item in root.findall(".//item"):
                title = item.find("title")
                link = item.find("link")
                pub = item.find("pubDate")
                if title is not None:
                    t = title.text or ""
                    news.append({
                        "title": t,
                        "link": link.text if link is not None else "",
                        "time": pub.text if pub is not None else "",
                        "source": "CNBC",
                        "impact": classify_impact(t),
                        "sentiment": classify_sentiment(t),
                    })
        print(f"  [OK] {len(news)} noticias de CNBC")
    except Exception as e:
        print(f"  [ERROR] CNBC: {e}")
    return news


def get_sentiment_summary(news_list):
    """Genera resumen de sentimiento del mercado."""
    if not news_list:
        return {"score": 0, "label": "NEUTRAL", "bull": 0, "bear": 0, "neutral": 0}
    
    bull = sum(1 for n in news_list if n["sentiment"] == "BULLISH")
    bear = sum(1 for n in news_list if n["sentiment"] == "BEARISH")
    neutral = sum(1 for n in news_list if n["sentiment"] == "NEUTRAL")
    total = len(news_list)
    
    score = round(((bull - bear) / total) * 100, 1) if total else 0
    
    if score > 20:
        label = "BULLISH"
    elif score < -20:
        label = "BEARISH"
    else:
        label = "NEUTRAL"
    
    return {
        "score": score,
        "label": label,
        "bull_count": bull,
        "bear_count": bear,
        "neutral_count": neutral,
        "total": total,
        "bull_pct": round(bull/total*100, 1) if total else 0,
        "bear_pct": round(bear/total*100, 1) if total else 0,
    }


def run():
    """Ejecuta el fetching de noticias y guarda el resultado."""
    print("\n" + "="*60 + "\n  SOURCE NEWS LIVE\n" + "="*60)
    
    all_news = []
    all_news.extend(fetch_finviz_news())
    all_news.extend(fetch_marketwatch_rss())
    all_news.extend(fetch_cnbc_rss())
    
    # Deduplicar por titulo similar
    seen = set()
    unique_news = []
    for n in all_news:
        key = n["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique_news.append(n)
    
    # Separar por impacto
    high_impact = [n for n in unique_news if n["impact"] == "HIGH"]
    
    # Sentiment summary
    sentiment = get_sentiment_summary(unique_news)
    
    output = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "total_news": len(unique_news),
        "high_impact_count": len(high_impact),
        "sentiment": sentiment,
        "high_impact_news": high_impact[:10],
        "recent_news": unique_news[:25],
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n  [OK] {len(unique_news)} noticias totales")
    print(f"  [OK] {len(high_impact)} de alto impacto")
    print(f"  Sentiment: {sentiment['label']} (score: {sentiment['score']})")
    print(f"  -> {OUTPUT_FILE}")
    
    return output


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    run()
