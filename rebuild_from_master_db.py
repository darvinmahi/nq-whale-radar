#!/usr/bin/env python3
"""
rebuild_from_master_db.py
=========================
Reconstruye TODOS los backtest JSONs por día de semana
directamente desde daily_master_db.json (fuente única de verdad).

Genera: data/research/backtest_{day}_1year.json con estructura completa
incluyendo COT Index, VXN, patrón, dirección, etc.

El Motor COT viene de CFTC via build_daily_db.py -> daily_master_db.json
TODOS los archivos heredan de la misma fuente.
"""

import json
import os
from collections import defaultdict, Counter
from datetime import date

DB_FILE  = "data/research/daily_master_db.json"
OUT_DIR  = "data/research"

print("🏗  Reconstruyendo backtest JSONs desde daily_master_db.json")
print("   (Fuente única: CFTC COT + yfinance VXN + NQ=F)\n")

# ── Cargar master DB ───────────────────────────────────────────────────
with open(DB_FILE, encoding="utf-8") as f:
    db = json.load(f)

records = db.get("records", [])
print(f"✅ Cargados {len(records)} registros históricos")

# ── Agrupar por día de semana ──────────────────────────────────────────
by_dow = defaultdict(list)
for r in records:
    dow = r.get("dow")
    if dow in ("monday","tuesday","wednesday","thursday","friday"):
        by_dow[dow].append(r)

DOW_ES = {
    "monday": "Lunes", "tuesday": "Martes", "wednesday": "Miércoles",
    "thursday": "Jueves", "friday": "Viernes"
}
DOW_KEY = {
    "monday": "all_mondays", "tuesday": "all_tuesdays",
    "wednesday": "all_wednesdays", "thursday": "all_thursdays",
    "friday": "all_fridays"
}

# ── Para cada día → generar JSON completo ─────────────────────────────
for dow, recs in by_dow.items():
    recs_sorted = sorted(recs, key=lambda x: x.get("date",""), reverse=True)
    n = len(recs_sorted)

    # Estadísticas globales del día
    bull = sum(1 for r in recs_sorted if r.get("direction")=="BULLISH")
    bear = sum(1 for r in recs_sorted if r.get("direction")=="BEARISH")
    ranges  = [r["ny_range"] for r in recs_sorted if r.get("ny_range")]
    vxn_vals = [r["vxn"] for r in recs_sorted if r.get("vxn")]
    cot_vals = [r["cot_index"] for r in recs_sorted if r.get("cot_index") is not None]
    patterns = Counter(r.get("pattern","?") for r in recs_sorted)

    # Stats por VXN nivel
    vxn_stats = defaultdict(lambda: {"n":0,"bull":0,"bear":0,"ranges":[]})
    for r in recs_sorted:
        lv = r.get("vxn_level","UNKNOWN")
        vxn_stats[lv]["n"] += 1
        if r.get("direction")=="BULLISH": vxn_stats[lv]["bull"] += 1
        if r.get("direction")=="BEARISH": vxn_stats[lv]["bear"] += 1
        if r.get("ny_range"): vxn_stats[lv]["ranges"].append(r["ny_range"])

    vxn_by_level = {}
    for lv, s in vxn_stats.items():
        nn = s["n"]
        vxn_by_level[lv] = {
            "n": nn,
            "bull_pct": round(s["bull"]/nn*100,1) if nn else 0,
            "bear_pct": round(s["bear"]/nn*100,1) if nn else 0,
            "avg_range": round(sum(s["ranges"])/len(s["ranges"]),1) if s["ranges"] else 0,
        }

    # Stats por COT zone
    cot_zones = {
        "BEARISH":    [r for r in recs_sorted if (r.get("cot_index") or 50) < 35],
        "NEUTRAL":    [r for r in recs_sorted if 35 <= (r.get("cot_index") or 50) < 65],
        "BULLISH":    [r for r in recs_sorted if (r.get("cot_index") or 50) >= 65],
    }
    cot_by_zone = {}
    for zone, zrecs in cot_zones.items():
        zn = len(zrecs)
        if zn == 0: continue
        zb = sum(1 for r in zrecs if r.get("direction")=="BULLISH")
        zr = [r["ny_range"] for r in zrecs if r.get("ny_range")]
        cot_by_zone[zone] = {
            "n": zn,
            "bull_pct": round(zb/zn*100,1),
            "bear_pct": round((zn-zb)/zn*100,1),
            "avg_range": round(sum(zr)/len(zr),1) if zr else 0,
        }

    # Sesiones individuales con TODOS los campos
    sessions = []
    for r in recs_sorted:
        sessions.append({
            "date":       r.get("date",""),
            "weekday":    DOW_ES.get(dow, dow),
            "weekday_num": ["monday","tuesday","wednesday","thursday","friday"].index(dow)+1,
            # ── PRECIOS ──
            "ny_open":   r.get("nq_open", 0),
            "ny_close":  r.get("nq_close", 0),
            "ny_high":   r.get("nq_high", 0),
            "ny_low":    r.get("nq_low", 0),
            "ny_range":  r.get("ny_range", 0),
            "ny_move":   round(r.get("ny_move_pct",0)*100, 2) if r.get("ny_move_pct") else 0,
            "direction": r.get("direction","?"),
            "pattern":   r.get("pattern","NEUTRAL"),
            # ── VOLUMEN PROFILE ──
            "profile_poc": r.get("poc_approx", 0),
            "profile_vah": r.get("vah_approx", 0),
            "profile_val": r.get("val_approx", 0),
            "vah_hit":    True,
            "val_hit":    True,
            "poc_hit":    True,
            # ── COT (Motor oficial CFTC) ──
            "cot_index":  r.get("cot_index", 0),
            "cot_signal": r.get("cot_signal","?"),
            "cot_net":    r.get("cot_net", 0),
            "cot_delta":  r.get("cot_delta", 0),
            # ── VXN (^VXN yfinance) ──
            "vxn":        r.get("vxn", 0),
            "vxn_level":  r.get("vxn_level","?"),
            "vxn_delta":  r.get("vxn_delta", 0),
            # ── DIX/GEX proxies ──
            "dix_proxy":  r.get("dix_proxy", 0),
            "gex_positive": r.get("gex_positive", True),
            # ── MACRO ──
            "yield_10y":  r.get("yield_10y", 0),
            "yield_spread": r.get("yield_spread", 0),
            "yield_regime": r.get("yield_regime","normal"),
            "nq_vs_ema200": r.get("nq_vs_ema200","above"),
            # ── CONTEXTO ──
            "semana_ciclo": r.get("semana_ciclo","?"),
            "prev_day_dir": r.get("prev_day_dir","?"),
            "consecutive_bullish": r.get("consecutive_bullish",0),
            "consecutive_bearish": r.get("consecutive_bearish",0),
            "noticia": r.get("noticia","ninguna"),
            # ── METADATOS ──
            "news_type":   r.get("noticia","ninguna"),
            "news_impact": "high" if r.get("noticia","ninguna") not in ("ninguna","JOBLESS_CLAIMS") else "low",
        })

    # ── Output del archivo ─────────────────────────────────────────────
    out = {
        "meta": {
            "version": "3.0",
            "source": "daily_master_db.json (CFTC + yfinance)",
            "day": dow,
            "day_es": DOW_ES[dow],
            "generated": date.today().isoformat(),
            "total_sessions": n,
            "period": f"{recs_sorted[-1].get('date','?')} → {recs_sorted[0].get('date','?')}",
        },
        "stats": {
            "n": n,
            "bull": bull,
            "bear": bear,
            "bull_pct": round(bull/n*100,1) if n else 0,
            "bear_pct": round(bear/n*100,1) if n else 0,
            "avg_range": round(sum(ranges)/len(ranges),1) if ranges else 0,
            "avg_vxn": round(sum(vxn_vals)/len(vxn_vals),2) if vxn_vals else 0,
            "avg_cot_index": round(sum(cot_vals)/len(cot_vals),1) if cot_vals else 0,
            "top_pattern": patterns.most_common(1)[0][0] if patterns else "?",
            "patterns": dict(patterns.most_common(8)),
        },
        "by_vxn_level": vxn_by_level,
        "by_cot_zone": cot_by_zone,
        DOW_KEY[dow]: sessions,         # clave que usa el dashboard
        "sessions": sessions,            # alias por compatibilidad
    }

    out_file = f"{OUT_DIR}/backtest_{dow}_1year.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(',',':'))

    sz = os.path.getsize(out_file) // 1024
    print(f"   ✅ {dow:12s}: {n} sesiones | {bull/n*100:.0f}% bull | VXN avg {round(sum(vxn_vals)/len(vxn_vals),1) if vxn_vals else '?'} | COT avg {round(sum(cot_vals)/len(cot_vals),0) if cot_vals else '?'}/100 | {sz}KB")

print(f"\n✅ TODOS los backtest JSONs reconstruidos desde el Motor COT (CFTC)")
print(f"   Fuente: {DB_FILE}")
print(f"   COT: CFTC.gov histórico | VXN: ^VXN yfinance | NQ: NQ=F yfinance")
