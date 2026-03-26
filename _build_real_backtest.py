#!/usr/bin/env python3
"""Build REAL_BACKTEST JS block from all real JSON files."""
import json, re

def load(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def norm_session(s):
    return {
        "date": s.get("date",""),
        "pattern": s.get("pattern","CONSOLIDATION"),
        "direction": s.get("direction","NEUTRAL"),
        "ny_range": round(s.get("ny_range") or 0),
        "ny_open": s.get("ny_open") or 0,
        "profile_vah": s.get("profile_vah") or s.get("vah") or 0,
        "profile_poc": s.get("profile_poc") or s.get("poc") or 0,
        "profile_val": s.get("profile_val") or s.get("val") or 0,
        "vah_hit": bool(s.get("vah_hit")),
        "poc_hit": bool(s.get("poc_hit")),
        "val_hit": bool(s.get("val_hit")),
    }

def pack_day(d_src, sessions_key, total_key, extra_keys=None):
    sessions = [norm_session(s) for s in d_src.get(sessions_key, [])]
    total = d_src.get(total_key, len(sessions))
    va = d_src.get("value_area", {})
    ema = d_src.get("ema200", {})
    pats = d_src.get("patterns", {})
    dirs = d_src.get("directions", d_src.get("direction", {}))
    rd   = d_src.get("range_distribution", {})
    out = {
        "title": d_src.get("title",""),
        "period": d_src.get("period",""),
        "total_sessions": total,
        "total_mondays": total,   # compat with renderStats
        "dominant_pattern": d_src.get("dominant_pattern",""),
        "dominant_pct": d_src.get("dominant_pct", 0),
        "avg_ny_range": d_src.get("avg_ny_range", 0),
        "max_ny_range": d_src.get("max_ny_range", 0),
        "directions": dirs,
        "patterns": pats,
        "range_distribution": rd,
        "value_area": va,
        "ema200": ema,
    }
    out[sessions_key] = sessions
    if extra_keys:
        out.update(extra_keys)
    return out

# ── Monday ────────────────────────────────────────────────────────────────────
mon_raw = load('data/research/backtest_monday_1year.json')
mon = pack_day(mon_raw, 'all_mondays', 'total_mondays')

# ── Tuesday ───────────────────────────────────────────────────────────────────
mon_tue_raw = load('data/research/backtest_mon_tue_3m.json')
tue_src = mon_tue_raw.get('MARTES', {})
tue_sessions = [norm_session(s) for s in tue_src.get('sessions', [])]
tue_va  = tue_src.get('value_area', {})
tue_ema = tue_src.get('ema200', {})
tue_dir = tue_src.get('direction', {})
tue_pat = tue_src.get('patterns', {})
tue_rd  = tue_src.get('range_distribution', {})
tue = {
    "title": "Backtest MARTES NQ",
    "period": mon_tue_raw.get('period',''),
    "total_sessions": tue_src.get('total_sessions', len(tue_sessions)),
    "total_mondays": tue_src.get('total_sessions', len(tue_sessions)),
    "dominant_pattern": tue_src.get('dominant_pattern',''),
    "dominant_pct": tue_src.get('dominant_pct', 0),
    "avg_ny_range": tue_src.get('avg_ny_range', 0),
    "max_ny_range": tue_src.get('max_ny_range', 0),
    "directions": tue_dir,
    "patterns": tue_pat,
    "range_distribution": tue_rd,
    "value_area": tue_va,
    "ema200": tue_ema,
    "all_tuesdays": tue_sessions,
}

# ── Wednesday ─────────────────────────────────────────────────────────────────
wed_raw = load('data/research/backtest_wednesday_3m.json')
wed_sessions = [norm_session(s) for s in wed_raw.get('all_wednesdays', wed_raw.get('sessions', []))]
wed_pats = wed_raw.get('patterns', wed_raw.get('patterns_wednesday', {}))
wed_dirs = wed_raw.get('directions', wed_raw.get('direction', {}))
wed_rd   = wed_raw.get('range_distribution', {})
wed = {
    "title": wed_raw.get('title',''),
    "period": wed_raw.get('period',''),
    "total_sessions": wed_raw.get('total_wednesdays', len(wed_sessions)),
    "total_mondays":  wed_raw.get('total_wednesdays', len(wed_sessions)),
    "dominant_pattern": wed_raw.get('dominant_pattern',''),
    "dominant_pct": wed_raw.get('dominant_pct', 0),
    "avg_ny_range": wed_raw.get('avg_ny_range', 0),
    "max_ny_range": wed_raw.get('max_ny_range', 0),
    "directions": wed_dirs,
    "patterns": wed_pats,
    "range_distribution": wed_rd,
    "value_area": wed_raw.get('value_area', {}),
    "ema200": wed_raw.get('ema200', {}),
    "all_wednesdays": wed_sessions,
}

# ── Thursday ──────────────────────────────────────────────────────────────────
thu_raw = load('data/research/backtest_thursday_noticias_1year.json')
thu_sessions_raw = thu_raw.get('all_thursdays', thu_raw.get('sessions', []))
thu_sessions = [norm_session(s) for s in thu_sessions_raw]
thu_dirs = thu_raw.get('directions', thu_raw.get('direction', {}))
thu = {
    "title": thu_raw.get('title',''),
    "period": thu_raw.get('period',''),
    "total_sessions": thu_raw.get('total_thursdays', len(thu_sessions)),
    "total_mondays":  thu_raw.get('total_thursdays', len(thu_sessions)),
    "dominant_pattern": thu_raw.get('dominant_pattern_all_thu', thu_raw.get('dominant_pattern','')),
    "dominant_pct": thu_raw.get('dominant_pct', 0),
    "avg_ny_range": thu_raw.get('avg_ny_range', 0),
    "max_ny_range": thu_raw.get('max_ny_range', 0),
    "directions": thu_dirs,
    "patterns": thu_raw.get('patterns', {}),
    "range_distribution": thu_raw.get('range_distribution', {}),
    "value_area": thu_raw.get('value_area', {}),
    "ema200": thu_raw.get('ema200', {}),
    "all_thursdays": thu_sessions,
}

# ── Friday ────────────────────────────────────────────────────────────────────
all_raw = load('data/research/backtest_all_days.json')
fri_inner = {}
for k, v in all_raw.get('days', {}).items():
    if 'VIERN' in k.upper() or 'FRIDAY' in k.upper():
        fri_inner = v
        break
fri_sessions = [norm_session(s) for s in fri_inner.get('sessions', [])]
fri_dirs = fri_inner.get('direction', {})
if isinstance(fri_dirs, dict):
    # might be pct — convert to counts
    total_fr = len(fri_sessions) or 1
    fri_dirs_out = {}
    for k,v in fri_dirs.items():
        fri_dirs_out[k] = round(v * total_fr) if isinstance(v, float) and v <= 1 else v
else:
    fri_dirs_out = {}
fri_pats = fri_inner.get('patterns', {})
fri_pats_out = {}
for k,v in fri_pats.items():
    fri_pats_out[k] = (str(round(v*100,1)) + "%") if (isinstance(v,float) and v<=1) else str(v)

fri = {
    "title": "Backtest VIERNES NQ",
    "period": all_raw.get('period_start','') + " → " + all_raw.get('period_end',''),
    "total_sessions": len(fri_sessions),
    "total_mondays": len(fri_sessions),
    "dominant_pattern": fri_inner.get('dominant_pattern','CONSOLIDATION'),
    "dominant_pct": fri_inner.get('dominant_pct', 0),
    "avg_ny_range": round(fri_inner.get('avg_ny_range', 0)),
    "max_ny_range": round(fri_inner.get('max_ny_range', 0)),
    "directions": fri_dirs_out,
    "patterns": fri_pats_out,
    "range_distribution": fri_inner.get('range_distribution', {"0-100":0,"100-200":0,"200-300":0,"300+":0}),
    "value_area": fri_inner.get('value_area', {}),
    "ema200": fri_inner.get('ema200', {"hit_rate":"0%","avg_reaction":0}),
    "all_fridays": fri_sessions,
}

# ── Print stats ───────────────────────────────────────────────────────────────
result = {"monday": mon, "tuesday": tue, "wednesday": wed, "thursday": thu, "friday": fri}
for day, r in result.items():
    sk = f"all_{day}s"
    cnt = len(r.get(sk, []))
    print(f"  {day}: {cnt} sessions, avg={r.get('avg_ny_range',0):.0f}, dom={r.get('dominant_pattern','?')}")

# ── Write JSON ────────────────────────────────────────────────────────────────
with open('_real_backtest_data.json', 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
print("\n✅  _real_backtest_data.json written")
