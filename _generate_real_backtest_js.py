#!/usr/bin/env python3
"""Generate real REAL_BACKTEST JS block for embedding in daily_dashboard.html"""
import json, sys

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def norm_session(s):
    return {
        "date": s.get("date",""),
        "pattern": s.get("pattern","CONSOLIDATION"),
        "direction": s.get("direction","NEUTRAL"),
        "ny_range": round(s.get("ny_range") or 0),
        "ny_open": round(s.get("ny_open") or 0, 2),
        "profile_vah": round(s.get("profile_vah") or s.get("vah") or 0, 2),
        "profile_poc": round(s.get("profile_poc") or s.get("poc") or 0, 2),
        "profile_val": round(s.get("profile_val") or s.get("val") or 0, 2),
        "vah_hit": bool(s.get("vah_hit")),
        "poc_hit": bool(s.get("poc_hit")),
        "val_hit": bool(s.get("val_hit")),
    }

def compute_avg(sessions, field='ny_range'):
    vals = [s.get(field,0) for s in sessions if s.get(field)]
    return round(sum(vals)/len(vals)) if vals else 0

# ─── MONDAY ──────────────────────────────────────────────────────────────────
m = load('data/research/backtest_monday_1year.json')
mon_sessions = [norm_session(s) for s in m.get('all_mondays', [])]
mon = {
    "title": m.get("title", "Backtest LUNES NQ"),
    "period": m.get("period",""),
    "total_sessions": m.get("total_mondays", len(mon_sessions)),
    "total_mondays":  m.get("total_mondays", len(mon_sessions)),
    "dominant_pattern": m.get("dominant_pattern",""),
    "dominant_pct": m.get("dominant_pct", 0),
    "avg_ny_range": m.get("avg_ny_range") or compute_avg(mon_sessions),
    "max_ny_range": m.get("max_ny_range", 0),
    "directions": m.get("directions", {}),
    "patterns": m.get("patterns", {}),
    "range_distribution": m.get("range_distribution", {}),
    "value_area": m.get("value_area", {}),
    "ema200": m.get("ema200", {}),
    "all_mondays": mon_sessions,
}
print(f"monday: {len(mon_sessions)} sessions, avg_range={mon['avg_ny_range']}, dom={mon['dominant_pattern']}")

# ─── TUESDAY (from mon_tue_3m MARTES section) ─────────────────────────────────
mt = load('data/research/backtest_mon_tue_3m.json')
tue_src = mt.get('MARTES', {})
tue_sessions = [norm_session(s) for s in tue_src.get('sessions', [])]
tue_dirs = tue_src.get('direction', tue_src.get('directions', {}))
tue = {
    "title": "Backtest MARTES NQ",
    "period": mt.get("period",""),
    "total_sessions": tue_src.get("total_sessions", len(tue_sessions)),
    "total_mondays":  tue_src.get("total_sessions", len(tue_sessions)),
    "dominant_pattern": tue_src.get("dominant_pattern",""),
    "dominant_pct": tue_src.get("dominant_pct", 0),
    "avg_ny_range": tue_src.get("avg_ny_range") or compute_avg(tue_sessions),
    "max_ny_range": tue_src.get("max_ny_range", 0),
    "directions": tue_dirs,
    "patterns": tue_src.get("patterns", {}),
    "range_distribution": tue_src.get("range_distribution", {}),
    "value_area": tue_src.get("value_area", {}),
    "ema200": tue_src.get("ema200", {}),
    "all_tuesdays": tue_sessions,
}
print(f"tuesday: {len(tue_sessions)} sessions, avg_range={tue['avg_ny_range']}, dom={tue['dominant_pattern']}")

# ─── WEDNESDAY ────────────────────────────────────────────────────────────────
w = load('data/research/backtest_wednesday_3m.json')
wed_sessions_raw = w.get('all_wednesdays', w.get('sessions', []))
wed_sessions = [norm_session(s) for s in wed_sessions_raw]
wed_pats = w.get('patterns', w.get('patterns_wednesday', {}))
wed_dirs = w.get('directions', w.get('direction', {}))
wed = {
    "title": w.get("title","Backtest MIÉRCOLES NQ"),
    "period": w.get("period",""),
    "total_sessions": w.get("total_wednesdays", len(wed_sessions)),
    "total_mondays":  w.get("total_wednesdays", len(wed_sessions)),
    "dominant_pattern": w.get("dominant_pattern",""),
    "dominant_pct": w.get("dominant_pct", 0),
    "avg_ny_range": w.get("avg_ny_range") or compute_avg(wed_sessions),
    "max_ny_range": w.get("max_ny_range", 0),
    "directions": wed_dirs,
    "patterns": wed_pats,
    "range_distribution": w.get("range_distribution", {}),
    "value_area": w.get("value_area", {}),
    "ema200": w.get("ema200", {}),
    "all_wednesdays": wed_sessions,
}
print(f"wednesday: {len(wed_sessions)} sessions, avg_range={wed['avg_ny_range']}, dom={wed['dominant_pattern']}")

# ─── THURSDAY ────────────────────────────────────────────────────────────────
t = load('data/research/backtest_thursday_noticias_1year.json')
thu_sessions_raw = t.get('all_thursdays', t.get('sessions', []))
thu_sessions = [norm_session(s) for s in thu_sessions_raw]
thu_dirs = t.get('directions', t.get('direction', {}))
thu_dom  = t.get('dominant_pattern_all_thu', t.get('dominant_pattern',''))
thu = {
    "title": t.get("title","Backtest JUEVES NQ"),
    "period": t.get("period",""),
    "total_sessions": t.get("total_thursdays", len(thu_sessions)),
    "total_mondays":  t.get("total_thursdays", len(thu_sessions)),
    "dominant_pattern": thu_dom,
    "dominant_pct": t.get("dominant_pct", 0),
    "avg_ny_range": t.get("avg_ny_range") or compute_avg(thu_sessions),
    "max_ny_range": t.get("max_ny_range", 0),
    "directions": thu_dirs,
    "patterns": t.get("patterns", {}),
    "range_distribution": t.get("range_distribution", {}),
    "value_area": t.get("value_area", {}),
    "ema200": t.get("ema200", {}),
    "all_thursdays": thu_sessions,
}
print(f"thursday: {len(thu_sessions)} sessions, avg_range={thu['avg_ny_range']}, dom={thu_dom}")

# ─── FRIDAY (from backtest_all_days VIERNES section) ─────────────────────────
ad = load('data/research/backtest_all_days.json')
fri_inner = {}
for k, v in ad.get('days', {}).items():
    if 'VIERN' in k.upper() or 'FRI' in k.upper():
        fri_inner = v
        break
fri_sessions = [norm_session(s) for s in fri_inner.get('sessions', [])]
fri_dirs_raw = fri_inner.get('direction', fri_inner.get('directions', {}))
# if float ratio, convert to counts
fri_dirs = {}
total_fri = len(fri_sessions) or 1
for k,v in fri_dirs_raw.items():
    if isinstance(v, float) and v <= 1.0:
        fri_dirs[k] = round(v * total_fri)
    else:
        fri_dirs[k] = v
fri_pats_raw = fri_inner.get('patterns', {})
fri_pats = {}
for k,v in fri_pats_raw.items():
    if isinstance(v, (int, float)):
        fri_pats[k] = str(round(v*100 if v<=1 else v, 1)) + "%"
    else:
        fri_pats[k] = str(v)
fri = {
    "title": "Backtest VIERNES NQ",
    "period": (ad.get("period_start","") + " → " + ad.get("period_end","")).strip(" →"),
    "total_sessions": len(fri_sessions),
    "total_mondays": len(fri_sessions),
    "dominant_pattern": fri_inner.get("dominant_pattern","CONSOLIDATION"),
    "dominant_pct": fri_inner.get("dominant_pct", 0),
    "avg_ny_range": round(fri_inner.get("avg_ny_range") or compute_avg(fri_sessions)),
    "max_ny_range": round(fri_inner.get("max_ny_range", 0)),
    "directions": fri_dirs,
    "patterns": fri_pats,
    "range_distribution": fri_inner.get("range_distribution", {"0-100":0,"100-200":0,"200-300":0,"300+":0}),
    "value_area": fri_inner.get("value_area", {"vah":{"hit_rate":"0%","avg_reaction":0},"poc":{"hit_rate":"0%","avg_reaction":0},"val":{"hit_rate":"0%","avg_reaction":0}}),
    "ema200": fri_inner.get("ema200", {"hit_rate":"0%","avg_reaction":0}),
    "all_fridays": fri_sessions,
}
print(f"friday: {len(fri_sessions)} sessions, avg_range={fri['avg_ny_range']}, dom={fri['dominant_pattern']}")

# ─── Write as JS ──────────────────────────────────────────────────────────────
result = {"monday": mon, "tuesday": tue, "wednesday": wed, "thursday": thu, "friday": fri}
js = "const REAL_BACKTEST = " + json.dumps(result, indent=2, ensure_ascii=False) + ";\n"
with open('_real_backtest_block.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("\n✅  _real_backtest_block.js written")
