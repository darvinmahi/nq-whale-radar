"""
Análisis de Patrones Reales — Jueves NQ
Combina ambos backtests para extraer movimientos reales por patrón
"""
import json, statistics

# ── CARGAR DATOS ─────────────────────────────────────────────────────────────
with open("thursday_space_move_summary.json", "r") as f:
    space = json.load(f)

with open("data/research/backtest_thursday_noticias_1year.json", "r") as f:
    news = json.load(f)

records_space = space["records"]   # 11 jueves (SP ≥40 pts)
records_news  = news["all_thursdays"]  # 10 jueves (Jobless)

# ── CRUZAR POR FECHA ─────────────────────────────────────────────────────────
merged = {}
for r in records_space:
    merged[r["date"]] = {"space": r}
for r in records_news:
    if r["date"] in merged:
        merged[r["date"]]["news"] = r
    else:
        merged[r["date"]] = {"news": r}

print("=" * 70)
print("  PATRONES REALES — JUEVES NQ  (Jobless Claims + Space Move)")
print("=" * 70)

# ── TABLA POR PATRÓN ─────────────────────────────────────────────────────────
by_pattern = {}
for date, d in sorted(merged.items()):
    n = d.get("news", {})
    s = d.get("space", {})
    pat = n.get("pattern", "N/A")
    direction = n.get("direction", "N/A")
    ny_range = n.get("ny_range", 0)
    space_dir = s.get("space_dir", "—")
    space_pts = s.get("space_size_pts", 0)
    returned_poc = s.get("returned_poc", None)
    dist_poc = s.get("dist_to_poc", 0)
    ret_poc_time = s.get("ret_poc_time", "—")
    open_pos = s.get("open_pos", "—")
    ny_open = n.get("ny_open", 0)
    ny_close = n.get("ny_close", 0)
    move_pts = round(ny_close - ny_open, 1) if ny_open and ny_close else 0

    if pat not in by_pattern:
        by_pattern[pat] = []
    by_pattern[pat].append({
        "date": date,
        "direction": direction,
        "ny_range": ny_range,
        "move_pts": move_pts,
        "space_dir": space_dir,
        "space_pts": space_pts,
        "returned_poc": returned_poc,
        "dist_poc": dist_poc,
        "ret_poc_time": ret_poc_time,
        "open_pos": open_pos,
    })

# ── IMPRIMIR POR PATRÓN ───────────────────────────────────────────────────────
for pat, entries in sorted(by_pattern.items(), key=lambda x: -len(x[1])):
    count = len(entries)
    pct = round(count / len(records_news) * 100, 0)
    ranges = [e["ny_range"] for e in entries if e["ny_range"]]
    moves  = [e["move_pts"] for e in entries if e["move_pts"] != 0]
    spaces = [e["space_pts"] for e in entries if e["space_pts"]]
    returns = [e for e in entries if e["returned_poc"] is True]

    avg_range = round(statistics.mean(ranges), 1) if ranges else 0
    avg_move  = round(statistics.mean(moves), 1) if moves else 0
    avg_space = round(statistics.mean(spaces), 1) if spaces else 0
    ret_rate  = round(len(returns) / count * 100, 0) if count else 0

    icon = {"NEWS_DRIVE": "🚀", "EXPANSION_L": "📉", "EXPANSION_H": "📈",
            "ROTATION_POC": "🔄", "SWEEP_L_RETURN": "↩️"}.get(pat, "📊")

    print(f"\n{icon}  PATRÓN: {pat}  ({count}x = {pct}%)")
    print(f"   Rango NY promedio : {avg_range} pts")
    print(f"   Movimiento NY open→close : {avg_move} pts  {'▼' if avg_move < 0 else '▲'}")
    print(f"   Space move promedio : {avg_space} pts")
    print(f"   Retorno al POC : {ret_rate}%")
    print(f"   {'─'*54}")

    for e in entries:
        ret_sym = "✅" if e["returned_poc"] else ("❌" if e["returned_poc"] is False else "—")
        move_sym = "▼" if e["move_pts"] < 0 else "▲"
        print(f"   {e['date']}  {e['space_dir']:10}  "
              f"SP:{e['space_pts']:6.1f}pts  "
              f"NY:{e['move_pts']:+7.1f}pts {move_sym}  "
              f"POC: {ret_sym} {e['ret_poc_time']}  "
              f"Pos: {e['open_pos']}")

# ── RESUMEN FINAL ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  RESUMEN EJECUTIVO")
print("=" * 70)
nd = [e for p, entries in by_pattern.items() if p == "NEWS_DRIVE" for e in entries]
if nd:
    nd_bear = [e for e in nd if e["direction"] == "BEARISH"]
    nd_moves = [e["move_pts"] for e in nd if e["move_pts"] != 0]
    print(f"  NEWS_DRIVE: {len(nd_bear)}/{len(nd)} BEARISH | avg move: {round(statistics.mean(nd_moves),1) if nd_moves else 0} pts")
    print(f"  → Cuando es NEWS_DRIVE el precio NO regresa al POC (retorno {round(len([e for e in nd if e['returned_poc']])/len(nd)*100,0)}%)")

print(f"\n  VAL hit rate (1 año): {news['by_news_type']['JOBLESS']['val_hit_rate']}")
print(f"  POC hit rate (1 año): {news['by_news_type']['JOBLESS']['poc_hit_rate']}")
print(f"  VAH hit rate (1 año): {news['by_news_type']['JOBLESS']['vah_hit_rate']}")
print(f"\n  Rango promedio jueves NY: {news['avg_range_all_thursdays']} pts")
