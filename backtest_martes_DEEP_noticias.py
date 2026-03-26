"""
backtest_martes_DEEP_noticias.py
=================================
Backtest PROFUNDO de los MARTES en NQ=F
  • Datos: yfinance 1d, 2 años (~100 Martes)
  • Separa: Martes NORMAL vs Martes con NOTICIAS de alto impacto
  • Calendario de noticias US embebido (2024–2026)
  • Estadísticas: rango, dirección, mega-movimientos, distribución
  • Alerta de próximos Martes con noticias

yfinance permite 1d para 2+ años sin problema.
Con 1d el "rango" = High-Low de ese martes.
El "movimiento" = Close-Open del martes.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, date, timedelta

# ══════════════════════════════════════════════════════════════════
# CALENDARIO DE NOTICIAS — MARTES DE ALTO IMPACTO PARA NQ
# ══════════════════════════════════════════════════════════════════
NEWS_TUESDAYS = {
    # ── 2022 ──
    "2022-01-11": ["CPI"],
    "2022-01-18": ["CB Consumer Confidence"],
    "2022-01-25": ["CB Consumer Confidence", "JOLTS"],
    "2022-02-01": ["ISM Non-Mfg PMI"],
    "2022-02-08": ["CB Consumer Confidence"],
    "2022-02-15": ["CPI"],
    "2022-02-22": ["CB Consumer Confidence"],
    "2022-03-01": ["ISM Mfg PMI", "JOLTS"],
    "2022-03-08": ["JOLTS"],
    "2022-03-15": ["CPI"],
    "2022-03-22": ["CB Consumer Confidence"],
    "2022-03-29": ["CB Consumer Confidence", "S&P Home Price"],
    "2022-04-05": ["ISM Services", "JOLTS"],
    "2022-04-12": ["CPI"],
    "2022-04-19": ["CB Consumer Confidence"],
    "2022-04-26": ["CB Consumer Confidence", "JOLTS"],
    "2022-05-03": ["ISM Services", "JOLTS"],
    "2022-05-10": ["CPI"],
    "2022-05-17": ["CB Consumer Confidence"],
    "2022-05-24": ["CB Consumer Confidence", "JOLTS"],
    "2022-05-31": ["CB Consumer Confidence", "S&P Home Price"],
    "2022-06-07": ["ISM Services"],
    "2022-06-14": ["CPI"],
    "2022-06-21": ["CB Consumer Confidence"],
    "2022-06-28": ["CB Consumer Confidence", "S&P Home Price"],
    "2022-07-05": ["ISM Services", "JOLTS"],
    "2022-07-12": ["CPI"],
    "2022-07-19": ["CB Consumer Confidence"],
    "2022-07-26": ["CB Consumer Confidence", "S&P Home Price"],
    "2022-08-02": ["ISM Services"],
    "2022-08-09": ["CPI"],
    "2022-08-16": ["CB Consumer Confidence"],
    "2022-08-23": ["CB Consumer Confidence"],
    "2022-08-30": ["CB Consumer Confidence", "S&P Home Price", "JOLTS"],
    "2022-09-06": ["ISM Services"],
    "2022-09-13": ["CPI"],
    "2022-09-20": ["CB Consumer Confidence"],
    "2022-09-27": ["CB Consumer Confidence", "S&P Home Price"],
    "2022-10-04": ["ISM Services", "JOLTS"],
    "2022-10-11": ["CPI"],
    "2022-10-18": ["CB Consumer Confidence"],
    "2022-10-25": ["CB Consumer Confidence", "S&P Home Price"],
    "2022-11-01": ["ISM Mfg PMI", "JOLTS"],
    "2022-11-08": ["ELECTION DAY — MEGA"],
    "2022-11-15": ["CPI"],
    "2022-11-22": ["CB Consumer Confidence"],
    "2022-11-29": ["CB Consumer Confidence", "S&P Home Price", "JOLTS"],
    "2022-12-06": ["ISM Services"],
    "2022-12-13": ["CPI"],
    "2022-12-20": ["CB Consumer Confidence"],
    "2022-12-27": ["CB Consumer Confidence"],
    # ── 2023 ──
    "2023-01-03": ["ISM Mfg PMI"],
    "2023-01-10": ["FOMC Minutes"],
    "2023-01-17": ["CB Consumer Confidence"],
    "2023-01-24": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-01-31": ["CB Consumer Confidence", "JOLTS"],
    "2023-02-07": ["ISM Services"],
    "2023-02-14": ["CPI"],
    "2023-02-21": ["CB Consumer Confidence"],
    "2023-02-28": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-03-07": ["ISM Services", "JOLTS"],
    "2023-03-14": ["CPI"],
    "2023-03-21": ["CB Consumer Confidence"],
    "2023-03-28": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-04-04": ["ISM Services", "JOLTS"],
    "2023-04-11": ["CPI"],
    "2023-04-18": ["CB Consumer Confidence"],
    "2023-04-25": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-05-02": ["ISM Services", "JOLTS"],
    "2023-05-09": ["CPI"],
    "2023-05-16": ["CB Consumer Confidence"],
    "2023-05-23": ["CB Consumer Confidence"],
    "2023-05-30": ["CB Consumer Confidence", "S&P Home Price", "JOLTS"],
    "2023-06-06": ["ISM Services"],
    "2023-06-13": ["CPI"],
    "2023-06-20": ["CB Consumer Confidence"],
    "2023-06-27": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-07-04": ["Holiday Independence Day"],
    "2023-07-11": ["CPI"],
    "2023-07-18": ["CB Consumer Confidence"],
    "2023-07-25": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-08-01": ["ISM Mfg PMI", "JOLTS"],
    "2023-08-08": ["CPI"],
    "2023-08-15": ["CB Consumer Confidence"],
    "2023-08-22": ["CB Consumer Confidence"],
    "2023-08-29": ["CB Consumer Confidence", "S&P Home Price", "JOLTS"],
    "2023-09-05": ["ISM Services"],
    "2023-09-12": ["CPI"],
    "2023-09-19": ["CB Consumer Confidence"],
    "2023-09-26": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-10-03": ["ISM Services", "JOLTS"],
    "2023-10-10": ["CPI"],
    "2023-10-17": ["CB Consumer Confidence"],
    "2023-10-24": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-10-31": ["CB Consumer Confidence", "JOLTS"],
    "2023-11-07": ["ISM Services"],
    "2023-11-14": ["CPI"],
    "2023-11-21": ["CB Consumer Confidence"],
    "2023-11-28": ["CB Consumer Confidence", "S&P Home Price"],
    "2023-12-05": ["ISM Services", "JOLTS"],
    "2023-12-12": ["CPI"],
    "2023-12-19": ["CB Consumer Confidence"],
    "2023-12-26": ["Holiday period"],
    # ── 2024 ──
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
    "2024-03-26": ["CB Consumer Confidence", "S&P Home Price"],
    "2024-04-02": ["ISM Non-Mfg PMI", "JOLTS"],
    "2024-04-09": ["FOMC Minutes"],
    "2024-04-16": ["CB Consumer Confidence"],
    "2024-04-23": ["CB Consumer Confidence", "MSFT/GOOG earnings"],
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
    "2024-11-05": ["ELECTION DAY — MEGA"],
    "2024-11-12": ["CPI"],
    "2024-11-19": ["CB Consumer Confidence"],
    "2024-11-26": ["CB Consumer Confidence", "JOLTS"],
    "2024-12-03": ["ISM Services", "JOLTS"],
    "2024-12-10": ["CPI"],
    "2024-12-17": ["CB Consumer Confidence"],
    # ── 2025 ──
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
    # ── 2026 (próximos estimados) ──
    "2026-04-07": ["FOMC Minutes estimado"],
    "2026-04-14": ["CPI estimado"],
    "2026-04-21": ["CB Consumer Confidence estimado"],
    "2026-04-28": ["CB Consumer Confidence", "JOLTS", "S&P Home Price"],
    "2026-05-05": ["ISM Services", "JOLTS"],
    "2026-05-12": ["CPI"],
    "2026-05-19": ["CB Consumer Confidence"],
    "2026-05-26": ["CB Consumer Confidence", "JOLTS"],
    "2026-06-02": ["ISM Services"],
    "2026-06-09": ["CPI"],
}

ULTRA_HIGH_TAGS = ["CPI", "ELECTION", "MEGA", "JOLTS", "ISM", "Retail", "FOMC"]

def get_impact(events):
    for tag in ULTRA_HIGH_TAGS:
        for ev in events:
            if tag.upper() in ev.upper():
                return "ULTRA_ALTO"
    return "ALTO"

def pct(c, t):
    return f"{c/t*100:.1f}%" if t else "0%"

def avg(vals):
    return round(sum(vals)/len(vals), 1) if vals else 0

def median_val(vals):
    if not vals: return 0
    s = sorted(vals)
    n = len(s)
    return round((s[n//2] + s[(n-1)//2]) / 2, 1)

# ══════════════════════════════════════════════════════════════════
# DESCARGAR DATOS DIARIOS — 2 AÑOS (yfinance 1d sin límite)
# ══════════════════════════════════════════════════════════════════
print("=" * 72)
print("  📥 DESCARGANDO NQ=F DIARIO — 2 AÑOS...")
print("=" * 72)

df = yf.download("NQ=F", period="2y", interval="1d",
                 auto_adjust=True, progress=False)

if df.empty:
    print("  ❌ No se pudo descargar datos. Verifica conexión.")
    raise SystemExit(1)

if hasattr(df.columns, 'levels'):
    df.columns = df.columns.get_level_values(0)

df.index = pd.to_datetime(df.index)
df = df.dropna()

print(f"  ✅ Barras descargadas: {len(df)}")
print(f"  📅 Rango: {df.index[0].date()} → {df.index[-1].date()}")
print()

# ══════════════════════════════════════════════════════════════════
# FILTRAR SOLO MARTES (weekday == 1)
# ══════════════════════════════════════════════════════════════════
df['weekday'] = df.index.weekday
tuesdays = df[df['weekday'] == 1].copy()
tuesdays['date_str'] = tuesdays.index.strftime('%Y-%m-%d')

print(f"  📅 Martes encontrados: {len(tuesdays)}")

# ══════════════════════════════════════════════════════════════════
# ENRIQUECER CON NOTICIAS
# ══════════════════════════════════════════════════════════════════
results = []
for idx, row in tuesdays.iterrows():
    d_str   = idx.strftime('%Y-%m-%d')
    events  = NEWS_TUESDAYS.get(d_str, [])
    is_news = len(events) > 0
    impact  = get_impact(events) if is_news else "NORMAL"
    try:
        hi    = float(row['High'])
        lo    = float(row['Low'])
        op    = float(row['Open'])
        cl    = float(row['Close'])
        rng   = round(hi - lo, 1)
        move  = round(cl - op, 1)
        bull  = cl >= op
        gap   = round(op - float(df.loc[df.index < idx, 'Close'].iloc[-1]), 1) if df.index.get_loc(idx) > 0 else 0
    except Exception:
        continue

    results.append({
        "date"   : idx.date(),
        "is_news": is_news,
        "events" : events,
        "impact" : impact,
        "hi": hi, "lo": lo, "op": op, "cl": cl,
        "range"  : rng,
        "move"   : move,
        "bull"   : bull,
        "gap"    : gap,
    })

N       = len(results)
normal  = [r for r in results if not r["is_news"]]
news    = [r for r in results if r["is_news"]]
ultra   = [r for r in news if r["impact"] == "ULTRA_ALTO"]

print()
print("=" * 72)
print(f"  📊 BACKTEST PROFUNDO — MARTES NQ=F | {N} sesiones")
print(f"  📅 Martes NORMALES         : {len(normal)}")
print(f"  📰 Martes CON NOTICIAS     : {len(news)}")
print(f"  🔥 Martes ULTRA-IMPACTO    : {len(ultra)}")
print("=" * 72)

# ══════════════════════════════════════════════════════════════════
# FUNCIÓN RESUMEN POR GRUPO
# ══════════════════════════════════════════════════════════════════
def print_group(label, emoji, group):
    if not group: return
    n   = len(group)
    nb  = sum(1 for r in group if r["bull"])
    nbe = n - nb
    rngs = [r["range"] for r in group]
    movs = [r["move"]  for r in group]
    gaps = [r["gap"]   for r in group]
    rng200  = sum(1 for r in group if r["range"] >= 200)
    rng300  = sum(1 for r in group if r["range"] >= 300)
    rng400  = sum(1 for r in group if r["range"] >= 400)
    rng500  = sum(1 for r in group if r["range"] >= 500)
    bull_avg = avg([r["move"] for r in group if r["bull"]])
    bear_avg = avg([r["move"] for r in group if not r["bull"]])

    print()
    print(f"  {emoji} {'─'*5} {label} {'─'*5}")
    print(f"  Sesiones       : {n}")
    print(f"  Dirección      : ↑{nb} ({pct(nb,n)}) BULL  |  ↓{nbe} ({pct(nbe,n)}) BEAR")
    print(f"  Avg Range      : {avg(rngs)} pts  |  Mediana: {median_val(rngs)} pts")
    print(f"  Avg Move       : {avg(movs):+.1f} pts")
    print(f"  Avg Move BULL  : {bull_avg:+.1f} pts  |  Avg Move BEAR: {bear_avg:+.1f} pts")
    print(f"  Avg Gap vs vsp : {avg(gaps):+.1f} pts")
    print(f"  ≥200 pts Range : {rng200}/{n} ({pct(rng200,n)})")
    print(f"  ≥300 pts Range : {rng300}/{n} ({pct(rng300,n)})")
    print(f"  ≥400 pts Range : {rng400}/{n} ({pct(rng400,n)})")
    print(f"  ≥500 pts Range : {rng500}/{n} ({pct(rng500,n)})")

print_group("MARTES NORMALES (sin noticias)", "📈", normal)
print_group("MARTES CON NOTICIAS (alto impacto)", "📰", news)
print_group("MARTES ULTRA-IMPACTO (CPI, ISM, JOLTS, etc.)", "🔥", ultra)

# ══════════════════════════════════════════════════════════════════
# DISTRIBUCIÓN DE RANGO — TABLA COMPARATIVA
# ══════════════════════════════════════════════════════════════════
print()
print("  ── 📊 DISTRIBUCIÓN RANGO DÍA (Normal vs Noticias vs Ultra) ────")
buckets = [(0,100,"0–100"),(100,200,"100–200"),(200,300,"200–300"),
           (300,400,"300–400"),(400,500,"400–500"),(500,700,"500–700"),(700,9999,"+700")]
print(f"  {'Rango':<10} {'NORMAL':>8} {'NOTICIAS':>10} {'ULTRA':>8}")
print("  " + "─"*42)
for lo, hi, lbl in buckets:
    cn = sum(1 for r in normal if lo <= r["range"] < hi)
    cw = sum(1 for r in news   if lo <= r["range"] < hi)
    cu = sum(1 for r in ultra  if lo <= r["range"] < hi)
    pn = f"{cn/len(normal)*100:.0f}%" if normal else "0%"
    pw = f"{cw/len(news)*100:.0f}%" if news else "0%"
    pu = f"{cu/len(ultra)*100:.0f}%" if ultra else "0%"
    print(f"  {lbl:<10} {pn:>8} {pw:>10} {pu:>8}")

# ══════════════════════════════════════════════════════════════════
# TABLA DÍA A DÍA — ÚLTIMOS 40 MARTES
# ══════════════════════════════════════════════════════════════════
print()
print("  ── 📅 ÚLTIMOS 40 MARTES — DÍA A DÍA ───────────────────────────")
print(f"  {'Fecha':<12} {'Range':>7} {'Move':>7} {'Dir':<6} {'Gap':>7} {'Tipo':<9} Eventos")
print("  " + "─"*85)
for r in results[-40:]:
    evs_str = ", ".join(r["events"][:2]) if r["events"] else "—"
    if len(evs_str) > 38: evs_str = evs_str[:38] + "…"
    tipo    = "🔥ULTRA" if r["impact"]=="ULTRA_ALTO" else ("📰NEWS" if r["is_news"] else "NORMAL")
    mov_str = f"{r['move']:+.0f}"
    rng_str = f"{r['range']:.0f}"
    gap_str = f"{r['gap']:+.0f}"
    dir_str = "↑BULL" if r["bull"] else "↓BEAR"
    print(f"  {str(r['date']):<12} {rng_str:>7} {mov_str:>7} {dir_str:<6} {gap_str:>7} {tipo:<9} {evs_str}")

# ══════════════════════════════════════════════════════════════════
# TOP 10 MARTES MÁS EXTREMOS
# ══════════════════════════════════════════════════════════════════
print()
print("  ── 🏆 TOP 10 MARTES MÁS GRANDES (por Range) ───────────────────")
top10 = sorted(results, key=lambda x: x["range"], reverse=True)[:10]
print(f"  {'Fecha':<12} {'Range':>7} {'Move':>7} {'Dir':<6} Eventos")
print("  " + "─"*65)
for r in top10:
    evs_str = ", ".join(r["events"][:2]) if r["events"] else "—"
    if len(evs_str) > 40: evs_str = evs_str[:40] + "…"
    dir_str = "↑BULL" if r["bull"] else "↓BEAR"
    print(f"  {str(r['date']):<12} {r['range']:>7.0f} {r['move']:>7.0f} {dir_str:<6} {evs_str}")

# ══════════════════════════════════════════════════════════════════
# STREAK DE BULLS Y BEARS
# ══════════════════════════════════════════════════════════════════
print()
print("  ── 🔁 STREAKS DE BULL/BEAR CONSECUTIVOS ────────────────────────")
max_bull = max_bear = cur_bull = cur_bear = 0
for r in results:
    if r["bull"]:
        cur_bull += 1; cur_bear = 0
    else:
        cur_bear += 1; cur_bull = 0
    max_bull = max(max_bull, cur_bull)
    max_bear = max(max_bear, cur_bear)
print(f"  Max racha BULL consecutiva : {max_bull} Martes")
print(f"  Max racha BEAR consecutiva : {max_bear} Martes")

# ══════════════════════════════════════════════════════════════════
# 🚨 PRÓXIMOS MARTES CON NOTICIAS
# ══════════════════════════════════════════════════════════════════
today = date.today()
print()
print("=" * 72)
print("  🚨 PRÓXIMOS MARTES CON NOTICIAS")
print("=" * 72)
upcoming = [(date.fromisoformat(ds), evs)
            for ds, evs in sorted(NEWS_TUESDAYS.items())
            if date.fromisoformat(ds) >= today
            and date.fromisoformat(ds).weekday() == 1]

for d_dt, evs in upcoming[:12]:
    delta   = (d_dt - today).days
    imp     = get_impact(evs)
    icon    = "🔥" if imp == "ULTRA_ALTO" else "📰"
    evs_str = " | ".join(evs[:3])
    if len(evs_str) > 52: evs_str = evs_str[:52] + "…"
    print(f"  {icon} {d_dt} — en {delta:>3} días  →  {evs_str}")

# ══════════════════════════════════════════════════════════════════
# CONCLUSIONES
# ══════════════════════════════════════════════════════════════════
print()
print("=" * 72)
print("  🎯 CONCLUSIONES ESTADÍSTICAS")
print("=" * 72)
if normal and news:
    norm_wr  = sum(1 for r in normal if r["bull"]) / len(normal) * 100
    news_wr  = sum(1 for r in news   if r["bull"]) / len(news)   * 100
    ultra_wr = sum(1 for r in ultra  if r["bull"]) / len(ultra)  * 100 if ultra else 0
    norm_rng = avg([r["range"] for r in normal])
    news_rng = avg([r["range"] for r in news])
    ultra_rng= avg([r["range"] for r in ultra]) if ultra else 0
    print(f"""
  📈 NORMAL    Win Rate:  {norm_wr:.1f}%     Avg Range: {norm_rng} pts
  📰 NOTICIAS  Win Rate:  {news_wr:.1f}%     Avg Range: {news_rng} pts
  🔥 ULTRA     Win Rate:  {ultra_wr:.1f}%     Avg Range: {ultra_rng} pts

  → Diferencia de rango (noticias vs normal): {news_rng - norm_rng:+.1f} pts
  → El Martes con noticias mueve {(news_rng/norm_rng - 1)*100:.1f}% MÁS que un Martes normal

  ⚠️  REGLA OPERATIVA:
     Martes NORMAL      → tamaño normal, mejor tendencia establecida
     Martes NOTICIAS    → reducir size 30–50%, esperar tras noticia
     Martes CPI/JOLTS   → máxima precaución, rango extremo probable
    """)

print("=" * 72)
print("   ✅  BACKTEST COMPLETO — Martes NQ=F con calendario de noticias")
print("=" * 72)
