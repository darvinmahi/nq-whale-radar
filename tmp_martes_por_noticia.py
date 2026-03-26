
import yfinance as yf
import pandas as pd

NEWS_TUESDAYS = {
    "2024-01-09": ["ISM Services"],
    "2024-01-16": ["CB Consumer Confidence"],
    "2024-01-23": ["CB Consumer Confidence"],
    "2024-01-30": ["CB Consumer Confidence", "JOLTS"],
    "2024-02-06": ["ISM Non-Mfg PMI"],
    "2024-02-13": ["CPI"],
    "2024-02-20": ["CB Consumer Confidence"],
    "2024-02-27": ["CB Consumer Confidence", "JOLTS"],
    "2024-03-05": ["ISM Services", "JOLTS"],
    "2024-03-12": ["CPI"],
    "2024-03-19": ["CB Consumer Confidence"],
    "2024-03-26": ["CB Consumer Confidence", "SP Home Price"],
    "2024-04-02": ["ISM Non-Mfg PMI", "JOLTS"],
    "2024-04-09": ["FOMC Minutes"],
    "2024-04-16": ["CB Consumer Confidence"],
    "2024-04-23": ["CB Consumer Confidence", "JOLTS"],
    "2024-04-30": ["CB Consumer Confidence", "JOLTS"],
    "2024-05-07": ["ISM Services"],
    "2024-05-14": ["CPI"],
    "2024-05-21": ["CB Consumer Confidence"],
    "2024-05-28": ["CB Consumer Confidence", "JOLTS"],
    "2024-06-04": ["ISM Services"],
    "2024-06-11": ["CPI"],
    "2024-06-18": ["CB Consumer Confidence"],
    "2024-06-25": ["CB Consumer Confidence"],
    "2024-07-02": ["ISM Services", "JOLTS"],
    "2024-07-09": ["FOMC Minutes"],
    "2024-07-16": ["CB Consumer Confidence"],
    "2024-07-23": ["CB Consumer Confidence"],
    "2024-07-30": ["CB Consumer Confidence", "JOLTS"],
    "2024-08-06": ["ISM Services"],
    "2024-08-13": ["CPI"],
    "2024-08-20": ["CB Consumer Confidence"],
    "2024-08-27": ["CB Consumer Confidence"],
    "2024-09-03": ["ISM Services", "JOLTS"],
    "2024-09-10": ["CPI"],
    "2024-09-17": ["CB Consumer Confidence"],
    "2024-09-24": ["CB Consumer Confidence"],
    "2024-10-01": ["ISM Mfg PMI", "JOLTS"],
    "2024-10-08": ["FOMC Minutes"],
    "2024-10-15": ["CB Consumer Confidence"],
    "2024-10-22": ["CB Consumer Confidence"],
    "2024-10-29": ["CB Consumer Confidence", "JOLTS"],
    "2024-11-05": ["ELECTION DAY"],
    "2024-11-12": ["CPI"],
    "2024-11-19": ["CB Consumer Confidence"],
    "2024-11-26": ["CB Consumer Confidence", "JOLTS"],
    "2024-12-03": ["ISM Services", "JOLTS"],
    "2024-12-10": ["CPI"],
    "2024-12-17": ["CB Consumer Confidence"],
    "2025-01-07": ["ISM Services"],
    "2025-01-14": ["CPI"],
    "2025-01-21": ["CB Consumer Confidence"],
    "2025-01-28": ["CB Consumer Confidence", "JOLTS"],
    "2025-02-04": ["ISM Services"],
    "2025-02-11": ["CPI"],
    "2025-02-18": ["CB Consumer Confidence"],
    "2025-02-25": ["CB Consumer Confidence", "JOLTS"],
    "2025-03-04": ["ISM Services", "JOLTS"],
    "2025-03-11": ["CPI"],
    "2025-03-18": ["CB Consumer Confidence"],
    "2025-03-25": ["CB Consumer Confidence"],
}

print("Descargando NQ=F 2 anos...")
df = yf.download("NQ=F", period="2y", interval="1d", auto_adjust=True, progress=False)
if hasattr(df.columns, "levels"):
    df.columns = df.columns.get_level_values(0)
df.index = pd.to_datetime(df.index)
df = df.dropna()
df["weekday"] = df.index.weekday
tuesdays = df[df["weekday"] == 1].copy()
print(f"Total Martes: {len(tuesdays)}")

results = []
for idx, row in tuesdays.iterrows():
    d_str = idx.strftime("%Y-%m-%d")
    events = NEWS_TUESDAYS.get(d_str, [])
    is_news = len(events) > 0
    try:
        hi = float(row["High"])
        lo = float(row["Low"])
        op = float(row["Open"])
        cl = float(row["Close"])
        rng = round(hi - lo, 1)
        move = round(cl - op, 1)
        bull = cl >= op
        loc = df.index.get_loc(idx)
        gap = round(op - float(df.iloc[loc - 1]["Close"]), 1) if loc > 0 else 0
    except Exception:
        continue
    results.append(
        {
            "date": idx.date(),
            "is_news": is_news,
            "events": events,
            "range": rng,
            "move": move,
            "bull": bull,
            "gap": gap,
        }
    )


def stats(group, label):
    if not group:
        return
    n = len(group)
    nb = sum(1 for r in group if r["bull"])
    rngs = [r["range"] for r in group]
    avg_r = sum(rngs) / n
    med = sorted(rngs)[n // 2]
    r200 = sum(1 for r in group if r["range"] >= 200)
    r300 = sum(1 for r in group if r["range"] >= 300)
    r400 = sum(1 for r in group if r["range"] >= 400)
    bar = "=" * 55
    print(f"\n{bar}")
    print(f"  {label}")
    print(bar)
    print(f"  Sesiones : {n}")
    print(f"  BULL     : {nb} ({nb/n*100:.1f}%)")
    print(f"  BEAR     : {n-nb} ({(n-nb)/n*100:.1f}%)")
    print(f"  Avg Range: {avg_r:.0f} pts  |  Mediana: {med:.0f} pts")
    print(f"  >=200pts : {r200} ({r200/n*100:.0f}%)")
    print(f"  >=300pts : {r300} ({r300/n*100:.0f}%)")
    print(f"  >=400pts : {r400} ({r400/n*100:.0f}%)")
    # Top 5 rangos
    top5 = sorted(group, key=lambda x: x["range"], reverse=True)[:5]
    print("  TOP 5 rangos:")
    for r in top5:
        d = "↑BULL" if r["bull"] else "↓BEAR"
        evs = ", ".join(r["events"][:2]) if r["events"] else "—"
        print(f"    {r['date']}  {r['range']:>6.0f}pts  {d}  {evs}")


# ── MARTES NORMAL ──────────────────────────────────────────────────
normal = [r for r in results if not r["is_news"]]
stats(normal, "MARTES NORMAL (sin noticias)")

# ── POR CADA TIPO DE NOTICIA ───────────────────────────────────────
news_buckets = {}
for r in results:
    for ev in r["events"]:
        ev_up = ev.upper()
        if "CPI" in ev_up:
            key = "CPI"
        elif "FOMC" in ev_up:
            key = "FOMC Minutes"
        elif "ISM" in ev_up:
            key = "ISM (Services / Mfg PMI)"
        elif "JOLTS" in ev_up:
            key = "JOLTS"
        elif "CB CONSUMER" in ev_up:
            key = "CB Consumer Confidence"
        elif "HOME PRICE" in ev_up or "SP HOME" in ev_up:
            key = "SP Home Price"
        elif "ELECTION" in ev_up:
            key = "ELECTION DAY"
        else:
            key = ev
        news_buckets.setdefault(key, [])
        if r not in news_buckets[key]:
            news_buckets[key].append(r)

ORDER = [
    "CPI",
    "FOMC Minutes",
    "ISM (Services / Mfg PMI)",
    "JOLTS",
    "CB Consumer Confidence",
    "SP Home Price",
    "ELECTION DAY",
]
for key in ORDER:
    if key in news_buckets:
        stats(news_buckets[key], f"MARTES CON {key}")
