#!/usr/bin/env python3
"""
Extrae datos reales de los JSONs de backtest y genera el bloque REAL_BACKTEST
para embeber en daily_dashboard.html
"""
import json, os

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

# ── Lunes ─────────────────────────────────────────────────────────────────────
def get_monday():
    d = load('data/research/backtest_monday_1year.json')
    skeys = list(d.keys())
    print("monday keys:", skeys[:8])
    sessions = d.get('all_mondays', [])
    # normalize session fields
    norm = []
    for s in sessions:
        norm.append({
            "date": s.get("date"),
            "pattern": s.get("pattern"),
            "direction": s.get("direction"),
            "ny_range": s.get("ny_range", 0),
            "ny_open": s.get("ny_open", 0),
            "profile_vah": s.get("profile_vah", s.get("vah", 0)),
            "profile_poc": s.get("profile_poc", s.get("poc", 0)),
            "profile_val": s.get("profile_val", s.get("val", 0)),
            "vah_hit": s.get("vah_hit", False),
            "poc_hit": s.get("poc_hit", False),
            "val_hit": s.get("val_hit", False),
        })
    return {
        "title": d.get("title", ""),
        "period": d.get("period", ""),
        "total_sessions": d.get("total_mondays", len(sessions)),
        "total_mondays": d.get("total_mondays", len(sessions)),
        "dominant_pattern": d.get("dominant_pattern", ""),
        "dominant_pct": d.get("dominant_pct", 0),
        "avg_ny_range": d.get("avg_ny_range", 0),
        "max_ny_range": d.get("max_ny_range", 0),
        "directions": d.get("directions", {}),
        "patterns": d.get("patterns", {}),
        "range_distribution": d.get("range_distribution", {}),
        "value_area": d.get("value_area", {}),
        "ema200": d.get("ema200", {}),
        "all_mondays": norm,
    }

# ── Martes ───────────────────────────────────────────────────────────────────
def get_tuesday():
    d = load('data/research/backtest_tuesday_3m.json')
    print("tuesday keys:", list(d.keys())[:8])
    sessions = d.get('all_tuesdays', [])
    norm = []
    for s in sessions:
        norm.append({
            "date": s.get("date"),
            "pattern": s.get("pattern"),
            "direction": s.get("direction"),
            "ny_range": s.get("ny_range", 0),
            "ny_open": s.get("ny_open", 0),
            "profile_vah": s.get("profile_vah", s.get("vah", 0)),
            "profile_poc": s.get("profile_poc", s.get("poc", 0)),
            "profile_val": s.get("profile_val", s.get("val", 0)),
            "vah_hit": s.get("vah_hit", False),
            "poc_hit": s.get("poc_hit", False),
            "val_hit": s.get("val_hit", False),
        })
    return {
        "title": d.get("title", ""),
        "period": d.get("period", ""),
        "total_sessions": d.get("total_tuesdays", len(sessions)),
        "total_mondays": d.get("total_tuesdays", len(sessions)),  # renderStats compat
        "dominant_pattern": d.get("dominant_pattern", ""),
        "dominant_pct": d.get("dominant_pct", 0),
        "avg_ny_range": d.get("avg_ny_range", 0),
        "max_ny_range": d.get("max_ny_range", 0),
        "directions": d.get("directions", {}),
        "patterns": d.get("patterns", {}),
        "range_distribution": d.get("range_distribution", {}),
        "value_area": d.get("value_area", {}),
        "ema200": d.get("ema200", {}),
        "all_tuesdays": norm,
    }

# ── Miércoles ─────────────────────────────────────────────────────────────────
def get_wednesday():
    d = load('data/research/backtest_wednesday_3m.json')
    print("wednesday keys:", list(d.keys())[:8])
    sessions = d.get('all_wednesdays', d.get('sessions', []))
    norm = []
    for s in sessions:
        norm.append({
            "date": s.get("date"),
            "pattern": s.get("pattern", "CONSOLIDATION"),
            "direction": s.get("direction", "NEUTRAL"),
            "ny_range": s.get("ny_range", 0),
            "ny_open": s.get("ny_open", 0),
            "profile_vah": s.get("profile_vah", s.get("vah", 0)),
            "profile_poc": s.get("profile_poc", s.get("poc", 0)),
            "profile_val": s.get("profile_val", s.get("val", 0)),
            "vah_hit": s.get("vah_hit", False),
            "poc_hit": s.get("poc_hit", False),
            "val_hit": s.get("val_hit", False),
        })
    # try patterns_wednesday key
    patterns = d.get("patterns", d.get("patterns_wednesday", {}))
    return {
        "title": d.get("title", ""),
        "period": d.get("period", ""),
        "total_sessions": d.get("total_wednesdays", len(sessions)),
        "total_mondays": d.get("total_wednesdays", len(sessions)),
        "dominant_pattern": d.get("dominant_pattern", ""),
        "dominant_pct": d.get("dominant_pct", 0),
        "avg_ny_range": d.get("avg_ny_range", 0),
        "max_ny_range": d.get("max_ny_range", 0),
        "directions": d.get("directions", {}),
        "patterns": patterns,
        "range_distribution": d.get("range_distribution", {}),
        "value_area": d.get("value_area", {}),
        "ema200": d.get("ema200", {}),
        "all_wednesdays": norm,
    }

# ── Jueves ────────────────────────────────────────────────────────────────────
def get_thursday():
    d = load('data/research/backtest_thursday_noticias_1year.json')
    print("thursday keys:", list(d.keys())[:8])
    sessions = d.get('all_thursdays', [])
    norm = []
    for s in sessions:
        norm.append({
            "date": s.get("date"),
            "pattern": s.get("pattern", "NEWS_DRIVE"),
            "direction": s.get("direction", "NEUTRAL"),
            "ny_range": s.get("ny_range", 0),
            "ny_open": s.get("ny_open", 0),
            "profile_vah": s.get("profile_vah", s.get("vah", 0)),
            "profile_poc": s.get("profile_poc", s.get("poc", 0)),
            "profile_val": s.get("profile_val", s.get("val", 0)),
            "vah_hit": s.get("vah_hit", False),
            "poc_hit": s.get("poc_hit", False),
            "val_hit": s.get("val_hit", False),
        })
    return {
        "title": d.get("title", ""),
        "period": d.get("period", ""),
        "total_sessions": d.get("total_thursdays", len(sessions)),
        "total_mondays": d.get("total_thursdays", len(sessions)),
        "dominant_pattern": d.get("dominant_pattern", ""),
        "dominant_pct": d.get("dominant_pct", 0),
        "avg_ny_range": d.get("avg_ny_range", 0),
        "max_ny_range": d.get("max_ny_range", 0),
        "directions": d.get("directions", {}),
        "patterns": d.get("patterns", {}),
        "range_distribution": d.get("range_distribution", {}),
        "value_area": d.get("value_area", {}),
        "ema200": d.get("ema200", {}),
        "all_thursdays": norm,
    }

# ── Viernes — desde backtest_all_days.json ya que 5dias_sesiones usa otra estructura
def get_friday():
    d = load('data/research/backtest_all_days.json')
    days_raw = d.get('days', {})
    # find VIERNES key (handles accent)
    fri_dd = {}
    for k in days_raw:
        if 'VIERN' in k.upper():
            fri_dd = days_raw[k]
            break
    print("friday inner keys:", list(fri_dd.keys())[:10])
    sessions = fri_dd.get('sessions', [])
    norm = []
    for s in sessions:
        norm.append({
            "date": s.get("date"),
            "pattern": s.get("pattern", "CONSOLIDATION"),
            "direction": s.get("direction", "NEUTRAL"),
            "ny_range": round(s.get("ny_range", 0)),
            "ny_open": s.get("ny_open", 0),
            "profile_vah": s.get("vah", s.get("profile_vah", 0)),
            "profile_poc": s.get("poc", s.get("profile_poc", 0)),
            "profile_val": s.get("val", s.get("profile_val", 0)),
            "vah_hit": s.get("vah_hit", False),
            "poc_hit": s.get("poc_hit", False),
            "val_hit": s.get("val_hit", False),
        })
    # Build value_area from fri_dd stats
    va = {
        "vah": {"hit_rate": str(round(fri_dd.get("vah_react_rate", 0)*100, 1)) + "%", "avg_reaction": round(fri_dd.get("avg_vah_react", fri_dd.get("avg_ny_range", 0)))},
        "poc": {"hit_rate": str(round(fri_dd.get("poc_react_rate", 0)*100, 1)) + "%", "avg_reaction": round(fri_dd.get("avg_poc_react", 0))},
        "val": {"hit_rate": str(round(fri_dd.get("val_react_rate", 0)*100, 1)) + "%", "avg_reaction": round(fri_dd.get("avg_val_react", 0))},
    }
    dirs_raw = fri_dd.get("direction", {})
    total_n = len(sessions) or 1
    dirs = {}
    if isinstance(dirs_raw, dict):
        for k,v in dirs_raw.items():
            dirs[k] = v if isinstance(v, int) else round(v * total_n)
    patterns_raw = fri_dd.get("patterns", {})
    # make sure patterns are percentages strings
    pats = {}
    for k,v in patterns_raw.items():
        if isinstance(v, str):
            pats[k] = v
        else:
            pats[k] = str(round(v*100, 1)) + "%"

    rd = fri_dd.get("range_distribution", {})
    if not rd:
        rd = {"0-100": 0, "100-200": 0, "200-300": 0, "300+": 0}

    return {
        "title": "Backtest VIERNES NQ",
        "period": d.get("period_start","") + " → " + d.get("period_end",""),
        "total_sessions": len(sessions),
        "total_mondays": len(sessions),
        "dominant_pattern": fri_dd.get("dominant_pattern", "CONSOLIDATION"),
        "dominant_pct": fri_dd.get("dominant_pct", 0),
        "avg_ny_range": round(fri_dd.get("avg_ny_range", 0)),
        "max_ny_range": round(fri_dd.get("max_ny_range", 0)),
        "directions": dirs,
        "patterns": pats,
        "range_distribution": rd,
        "value_area": va,
        "ema200": {"hit_rate": "0%", "avg_reaction": 0},
        "all_fridays": norm,
    }

# ── Build output ──────────────────────────────────────────────────────────────
mon = get_monday()
tue = get_tuesday()
wed = get_wednesday()
thu = get_thursday()
fri = get_friday()

result = {
    "monday": mon,
    "tuesday": tue,
    "wednesday": wed,
    "thursday": thu,
    "friday": fri,
}

js_blob = json.dumps(result, indent=2, ensure_ascii=False)
print("\n=== STATS ===")
for day in result:
    r = result[day]
    key = "all_" + day + "s" if day != "friday" else "all_fridays"
    count = len(r.get(key, []))
    print(f"  {day}: {count} sessions, avg_range={r.get('avg_ny_range',0)}")

with open('_real_backtest_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("\nWritten to _real_backtest_data.json")
