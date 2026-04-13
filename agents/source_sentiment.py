"""
SOURCE: REDDIT SENTIMENT — Market Sentiment from Reddit
=======================================================
Analiza sentimiento de r/wallstreetbets, r/stocks, r/options
  OK: Reddit JSON API (publica, sin API key)
  OK: Analisis de keywords bullish/bearish
  OK: Fear/Greed score casero
"""

import os, json, requests, datetime, re, time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_FILE = os.path.join(BASE_DIR, "data", "sentiment_reddit.json")

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "NQ-Intelligence-Engine/3.0 (research bot)"
})

SUBREDDITS = ["wallstreetbets", "stocks", "options", "investing"]

BULL_WORDS = [
    "calls", "moon", "rocket", "bull", "long", "buy", "dip",
    "breakout", "green", "pump", "tendies", "gains", "yolo",
    "squeeze", "surge", "rally", "ath", "all time high",
    "undervalued", "cheap", "strong", "beat", "crush",
]

BEAR_WORDS = [
    "puts", "crash", "bear", "short", "sell", "dump", "red",
    "bubble", "overvalued", "recession", "fear", "panic",
    "drill", "tank", "plunge", "bag", "loss", "guh",
    "dead cat", "rug pull", "margin call", "default",
]

NQ_TICKERS = ["qqq", "nq", "nasdaq", "ndx", "tqqq", "sqqq",
              "nvda", "aapl", "msft", "tsla", "meta", "amzn", "goog"]


def fetch_subreddit(sub, limit=25):
    """Fetch hot posts de un subreddit via JSON API publica."""
    try:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
        r = SESSION.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            posts = []
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                title = d.get("title", "")
                selftext = d.get("selftext", "")[:200]
                posts.append({
                    "title": title,
                    "score": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                    "sub": sub,
                    "created": d.get("created_utc", 0),
                    "text_preview": selftext,
                })
            return posts
        elif r.status_code == 429:
            print(f"  [WARN] Reddit rate limit en r/{sub}, esperando...")
            time.sleep(3)
            return []
        else:
            print(f"  [WARN] Reddit r/{sub}: HTTP {r.status_code}")
            return []
    except Exception as e:
        print(f"  [ERROR] Reddit r/{sub}: {e}")
        return []


def analyze_sentiment(posts):
    """Analiza sentimiento de los posts."""
    results = []
    for post in posts:
        text = (post["title"] + " " + post.get("text_preview", "")).lower()
        
        bull_hits = sum(1 for w in BULL_WORDS if w in text)
        bear_hits = sum(1 for w in BEAR_WORDS if w in text)
        
        if bull_hits > bear_hits:
            sentiment = "BULLISH"
        elif bear_hits > bull_hits:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
        
        # Es relevante para NQ?
        nq_relevant = any(t in text for t in NQ_TICKERS)
        
        results.append({
            **post,
            "sentiment": sentiment,
            "bull_hits": bull_hits,
            "bear_hits": bear_hits,
            "nq_relevant": nq_relevant,
        })
    
    return results


def compute_fear_greed(analyzed_posts):
    """Calcula un score Fear/Greed del -100 al +100."""
    if not analyzed_posts:
        return {"score": 0, "label": "NEUTRAL"}
    
    # Ponderar por score del post (más upvotes = más peso)
    weighted_bull = 0
    weighted_bear = 0
    total_weight = 0
    
    for post in analyzed_posts:
        weight = max(1, post["score"])  # minimo peso 1
        total_weight += weight
        if post["sentiment"] == "BULLISH":
            weighted_bull += weight
        elif post["sentiment"] == "BEARISH":
            weighted_bear += weight
    
    if total_weight == 0:
        return {"score": 0, "label": "NEUTRAL"}
    
    score = round(((weighted_bull - weighted_bear) / total_weight) * 100, 1)
    
    if score > 40:
        label = "EXTREME GREED"
    elif score > 15:
        label = "GREED"
    elif score > -15:
        label = "NEUTRAL"
    elif score > -40:
        label = "FEAR"
    else:
        label = "EXTREME FEAR"
    
    return {
        "score": score,
        "label": label,
        "interpretation": (
            "Contrarian SHORT signal" if label == "EXTREME GREED"
            else "Contrarian LONG signal" if label == "EXTREME FEAR"
            else "No clear contrarian signal"
        )
    }


def run():
    """Ejecuta el analisis de sentiment."""
    print("\n" + "="*60 + "\n  SOURCE REDDIT SENTIMENT\n" + "="*60)
    
    all_posts = []
    for sub in SUBREDDITS:
        print(f"  Fetching r/{sub}...")
        posts = fetch_subreddit(sub, limit=25)
        all_posts.extend(posts)
        time.sleep(1)  # Rate limiting
    
    # Analizar
    analyzed = analyze_sentiment(all_posts)
    
    # NQ-relevant posts
    nq_posts = [p for p in analyzed if p["nq_relevant"]]
    
    # Sentiment counts
    bull = sum(1 for p in analyzed if p["sentiment"] == "BULLISH")
    bear = sum(1 for p in analyzed if p["sentiment"] == "BEARISH")
    neutral = sum(1 for p in analyzed if p["sentiment"] == "NEUTRAL")
    
    # Fear/Greed
    fear_greed = compute_fear_greed(analyzed)
    
    # Top posts por engagement
    top_by_score = sorted(analyzed, key=lambda x: x["score"], reverse=True)[:10]
    
    # Trending tickers
    all_text = " ".join(p["title"].lower() for p in all_posts)
    ticker_counts = {}
    for t in NQ_TICKERS:
        count = all_text.count(t)
        if count > 0:
            ticker_counts[t.upper()] = count
    
    output = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "total_posts": len(analyzed),
        "nq_relevant_posts": len(nq_posts),
        "sentiment": {
            "bullish": bull,
            "bearish": bear,
            "neutral": neutral,
            "bull_pct": round(bull/len(analyzed)*100, 1) if analyzed else 0,
            "bear_pct": round(bear/len(analyzed)*100, 1) if analyzed else 0,
        },
        "fear_greed": fear_greed,
        "trending_tickers": dict(sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)),
        "top_posts": [{
            "title": p["title"],
            "score": p["score"],
            "comments": p["comments"],
            "sub": p["sub"],
            "sentiment": p["sentiment"],
        } for p in top_by_score],
        "nq_relevant": [{
            "title": p["title"],
            "score": p["score"],
            "sentiment": p["sentiment"],
            "sub": p["sub"],
        } for p in nq_posts[:10]],
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n  [OK] {len(analyzed)} posts analizados")
    print(f"  [OK] {len(nq_posts)} relevantes para NQ")
    print(f"  Sentiment: Bull {bull} | Bear {bear} | Neutral {neutral}")
    print(f"  Fear/Greed: {fear_greed['label']} ({fear_greed['score']})")
    print(f"  -> {OUTPUT_FILE}")
    
    return output


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    run()
