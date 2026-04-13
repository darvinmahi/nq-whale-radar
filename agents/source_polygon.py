"""
SOURCE: POLYGON.IO — NQ Intraday Data Provider
═══════════════════════════════════════════════════════════
Provee datos intraday del NASDAQ desde Polygon.io
  ✅ Barras 1min, 5min, 15min, 1h
  ✅ Volume Profile (POC, VAH, VAL)
  ✅ Datos por sesión (Asia, London, NY)
  ✅ VWAP intraday
"""

import os, json, time, requests, datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_api_key():
    env_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("POLYGON_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return os.environ.get("POLYGON_API_KEY", "")

API_KEY = _load_api_key()
BASE_URL = "https://api.polygon.io"
SESSION = requests.Session()

def get_bars(ticker="I:NDX", multiplier=5, timespan="minute",
             date_from=None, date_to=None, limit=5000):
    if not API_KEY:
        print("  ❌ POLYGON_API_KEY no configurada")
        return []
    if not date_from:
        date_from = (datetime.date.today() - datetime.timedelta(days=5)).isoformat()
    if not date_to:
        date_to = datetime.date.today().isoformat()

    url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{date_from}/{date_to}"
    params = {"apiKey": API_KEY, "limit": limit, "sort": "asc"}

    for attempt in range(2):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            data = r.json()
            if data.get("status") == "OK" and data.get("results"):
                bars = []
                for bar in data["results"]:
                    bars.append({
                        "timestamp": bar["t"],
                        "time_utc": datetime.datetime.fromtimestamp(
                            bar["t"]/1000, tz=datetime.timezone.utc
                        ).strftime("%Y-%m-%d %H:%M:%S"),
                        "open": bar["o"], "high": bar["h"],
                        "low": bar["l"], "close": bar["c"],
                        "volume": bar.get("v", 0),
                        "vwap": bar.get("vw", 0),
                        "trades": bar.get("n", 0)
                    })
                print(f"  ✅ Polygon: {len(bars)} barras {multiplier}{timespan}")
                return bars
            else:
                print(f"  ⚠️ Polygon intento {attempt+1}: {data.get('error', 'Sin datos')}")
                time.sleep(2)
        except Exception as e:
            print(f"  ⚠️ Polygon intento {attempt+1}: {e}")
            time.sleep(2)
    return []

def get_today_bars(ticker="I:NDX", multiplier=5, timespan="minute"):
    today = datetime.date.today().isoformat()
    return get_bars(ticker, multiplier, timespan, date_from=today, date_to=today)

def get_session_data(bars):
    """Divide barras en sesiones: Asia, London, NY."""
    sessions = {
        "asia":   {"bars": [], "label": "🌏 Asia (22:00-07:00 UTC)"},
        "london": {"bars": [], "label": "🇬🇧 London (07:00-12:30 UTC)"},
        "ny":     {"bars": [], "label": "🇺🇸 New York (12:30-21:00 UTC)"},
    }
    for bar in bars:
        parts = bar["time_utc"].split(" ")[1].split(":")
        h = int(parts[0]) + int(parts[1]) / 60
        if h >= 22 or h < 7:
            sessions["asia"]["bars"].append(bar)
        elif 7 <= h < 12.5:
            sessions["london"]["bars"].append(bar)
        elif 12.5 <= h < 21:
            sessions["ny"]["bars"].append(bar)

    for key, sess in sessions.items():
        sb = sess["bars"]
        if sb:
            highs = [b["high"] for b in sb]
            lows = [b["low"] for b in sb]
            sess["stats"] = {
                "open": sb[0]["open"], "close": sb[-1]["close"],
                "high": max(highs), "low": min(lows),
                "range_pts": round(max(highs) - min(lows), 2),
                "direction": "↗ Alcista" if sb[-1]["close"] > sb[0]["open"] else "↘ Bajista",
                "change_pts": round(sb[-1]["close"] - sb[0]["open"], 2),
                "total_volume": sum(b["volume"] for b in sb),
                "num_bars": len(sb),
                "time_start": sb[0]["time_utc"], "time_end": sb[-1]["time_utc"],
            }
        else:
            sess["stats"] = None
    return sessions

def compute_volume_profile(bars, num_levels=30):
    """Calcula Volume Profile: POC, VAH, VAL."""
    if not bars:
        return {}
    price_max = max(b["high"] for b in bars)
    price_min = min(b["low"] for b in bars)
    if price_max == price_min:
        return {"poc": price_max, "vah": price_max, "val": price_min}

    level_size = (price_max - price_min) / num_levels
    levels = defaultdict(float)
    for bar in bars:
        for i in range(num_levels):
            lp = price_min + (i * level_size)
            lt = lp + level_size
            if bar["low"] <= lt and bar["high"] >= lp:
                overlap = min(bar["high"], lt) - max(bar["low"], lp)
                br = bar["high"] - bar["low"] if bar["high"] != bar["low"] else 1
                levels[round(lp + level_size/2, 2)] += bar["volume"] * (overlap / br)

    poc = max(levels, key=levels.get)
    total_vol = sum(levels.values())
    sorted_lvls = sorted(levels.items(), key=lambda x: x[1], reverse=True)
    va_vol, va_prices = 0, []
    for price, vol in sorted_lvls:
        va_prices.append(price)
        va_vol += vol
        if va_vol >= total_vol * 0.7:
            break
    return {
        "poc": poc, "vah": round(max(va_prices), 2), "val": round(min(va_prices), 2),
        "total_volume": round(total_vol, 0)
    }

def get_multi_day_sessions(ticker="I:NDX", days=5):
    """Datos de sesiones de los últimos N días para comparar."""
    date_from = (datetime.date.today() - datetime.timedelta(days=days+2)).isoformat()
    bars = get_bars(ticker, 5, "minute", date_from=date_from)
    days_data = defaultdict(list)
    for bar in bars:
        days_data[bar["time_utc"].split(" ")[0]].append(bar)

    results = {}
    for date_str, day_bars in sorted(days_data.items()):
        sessions = get_session_data(day_bars)
        vp = compute_volume_profile(day_bars)
        results[date_str] = {
            "sessions": {k: v["stats"] for k, v in sessions.items()},
            "volume_profile": {"poc": vp.get("poc"), "vah": vp.get("vah"), "val": vp.get("val")},
            "day_stats": {
                "open": day_bars[0]["open"], "close": day_bars[-1]["close"],
                "high": max(b["high"] for b in day_bars),
                "low": min(b["low"] for b in day_bars),
                "range": round(max(b["high"] for b in day_bars) - min(b["low"] for b in day_bars), 2),
            }
        }
    return results

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    print("\n" + "="*60 + "\n  SOURCE POLYGON.IO -- Test\n" + "="*60)
    print(f"  API Key: {'[OK]' if API_KEY else '[FALTA]'}")
    if API_KEY:
        bars = get_today_bars()
        if bars:
            print(f"  {len(bars)} barras | {bars[0]['time_utc']} -> {bars[-1]['time_utc']}")
            vp = compute_volume_profile(bars)
            if vp:
                print(f"  VP: POC={vp['poc']} VAH={vp['vah']} VAL={vp['val']}")
        else:
            print("  Sin barras (mercado cerrado o fin de semana)")
