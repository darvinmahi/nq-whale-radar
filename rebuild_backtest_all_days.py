#!/usr/bin/env python3
"""
rebuild_backtest_all_days.py
Reconstruye todos los JSONs de backtest por dia de semana con 1 año de datos reales.
Genera: data/research/backtest_{monday/tuesday/wednesday/thursday/friday}_1year.json
Compatible con daily_dashboard.html DAY_CONFIG.
"""
import yfinance as yf, json, os, sys
from datetime import date, timedelta, datetime, timezone
from collections import defaultdict

OUT_DIR = "data/research"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Parámetros ────────────────────────────────────────────────────────────
END_DATE   = date.today()
START_DATE = END_DATE - timedelta(days=400)   # 13+ meses para tener 1 año completo

DAY_MAP = {0:"monday",1:"tuesday",2:"wednesday",3:"thursday",4:"friday"}
DAY_LABELS = {0:"LUNES",1:"MARTES",2:"MIÉRCOLES",3:"JUEVES",4:"VIERNES"}
DAY_ES_PLURAL = {0:"all_mondays",1:"all_tuesdays",2:"all_wednesdays",3:"all_thursdays",4:"all_fridays"}

# ── Descargar datos ───────────────────────────────────────────────────────
print(f"\n📥 Descargando NQ=F daily ({START_DATE} → {END_DATE})...")
df_daily = yf.download("NQ=F", start=str(START_DATE), end=str(END_DATE),
                       interval="1d", progress=False)
if df_daily.empty: sys.exit("ERROR: sin datos daily")
if hasattr(df_daily.columns,'levels'): df_daily.columns = df_daily.columns.get_level_values(0)
df_daily = df_daily.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
print(f"   {len(df_daily)} días de datos diarios")

print(f"\n📥 Descargando NQ=F 1h para Volume Profile...")
df_1h = yf.download("NQ=F", start=str(START_DATE), end=str(END_DATE),
                    interval="1h", prepost=True, progress=False)
if hasattr(df_1h.columns,'levels'): df_1h.columns = df_1h.columns.get_level_values(0)
df_1h = df_1h.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close"})
df_1h = df_1h[["open","high","low","close"]].dropna()
if df_1h.index.tz is not None:
    df_1h.index = df_1h.index.tz_convert("UTC")
else:
    df_1h.index = df_1h.index.tz_localize("UTC")
print(f"   {len(df_1h)} barras horarias")

# ── VP simple por día ─────────────────────────────────────────────────────
def calc_vp(bars, tick=25.0):
    """bars: list de dicts {high, low}. Returns (POC, VAH, VAL)"""
    if not bars: return None, None, None
    lo = min(b["low"]  for b in bars)
    hi = max(b["high"] for b in bars)
    nb = max(1, int((hi-lo)/tick)+1)
    vp = [0.0]*nb
    for b in bars:
        for i in range(int((b["low"]-lo)/tick), min(int((b["high"]-lo)/tick)+1, nb)):
            vp[i] += 1
    pi = vp.index(max(vp))
    POC = round(lo + pi*tick + tick/2, 2)
    tv = sum(vp)*0.70; li=hi_i=pi; acc=vp[pi]
    while acc < tv:
        el=li>0; eh=hi_i<nb-1
        if el and eh:
            if vp[li-1]>=vp[hi_i+1]: li-=1; acc+=vp[li]
            else: hi_i+=1; acc+=vp[hi_i]
        elif el: li-=1; acc+=vp[li]
        elif eh: hi_i+=1; acc+=vp[hi_i]
        else: break
    VAH = round(lo+hi_i*tick+tick, 2)
    VAL = round(lo+li*tick, 2)
    return POC, VAH, VAL

def get_hourly_bars(date_str):
    """Retorna barras horarias solo del día dado (UTC)"""
    try:
        subset = df_1h[df_1h.index.strftime("%Y-%m-%d") == date_str]
        return [{"high":float(r["high"]),"low":float(r["low"])} for _,r in subset.iterrows()]
    except: return []

def identify_pattern(o, h, l, c, pre_h=None, pre_l=None):
    """Clasifica el patrón de la sesión NY"""
    move = c - o
    rng  = h - l
    if rng == 0: return "FLAT"
    # Sweep High + Return
    if pre_h and h > pre_h and c < pre_h: return "SWEEP_H_RETURN"
    # Sweep Low + Return
    if pre_l and l < pre_l and c > pre_l: return "SWEEP_L_RETURN"
    # Expansion
    if abs(move)/rng > 0.60:
        return "EXPANSION_H" if move > 0 else "EXPANSION_L"
    # Rotation/POC return
    if abs(move)/rng < 0.30: return "ROTATION_POC"
    return "NEUTRAL"

# ── Procesar sesiones por día ─────────────────────────────────────────────
sessions_by_dow = defaultdict(list)

for ts, row in df_daily.iterrows():
    try:
        d = ts.date() if hasattr(ts,'date') else ts.to_pydatetime().date()
        dow = d.weekday()
        if dow not in DAY_MAP: continue  # skip weekends
        date_str = d.strftime("%Y-%m-%d")

        o = float(row["open"]); h = float(row["high"])
        l = float(row["low"]);  c = float(row["close"])
        ny_range = round(h - l, 2)
        ny_move  = round(c - o, 2)
        direction = "BULLISH" if ny_move > 0 else "BEARISH" if ny_move < 0 else "NEUTRAL"

        # Volume Profile con datos horarios pre-NY (00:00-13:30 UTC)
        all_bars = get_hourly_bars(date_str)
        ny_open_utc = d.strftime("%Y-%m-%d") + "T13"
        pre_bars = [b for b in all_bars]   # usar todo el dia para VP si no hay separación
        POC, VAH, VAL = calc_vp(pre_bars if pre_bars else [{"high":h,"low":l}])

        # Patrón
        pattern = identify_pattern(o, h, l, c)

        session = {
            "date": date_str,
            "weekday": DAY_MAP[dow].capitalize(),
            "weekday_num": dow,
            "direction": direction,
            "ny_open": round(o, 2),
            "ny_close": round(c, 2),
            "ny_high": round(h, 2),
            "ny_low": round(l, 2),
            "ny_range": ny_range,
            "ny_move": ny_move,
            "pattern": pattern,
            "profile_poc": POC,
            "profile_vah": VAH,
            "profile_val": VAL,
            "vah_hit": 1 if VAH and h >= VAH else 0,
            "val_hit": 1 if VAL and l <= VAL else 0,
            "poc_hit": 1 if POC and l <= POC <= h else 0,
            "news_type": "NONE",
            "news_impact": "NORMAL",
            "vxn_day": None,
            "cot_net": None,
        }
        sessions_by_dow[dow].append(session)
    except Exception as e:
        pass

# ── Generar JSON por día ──────────────────────────────────────────────────
for dow, day_name in DAY_MAP.items():
    sessions = sorted(sessions_by_dow[dow], key=lambda x: x["date"])
    if not sessions:
        print(f"⚠  Sin datos para {day_name}")
        continue

    n = len(sessions)
    bull = sum(1 for s in sessions if s["direction"]=="BULLISH")
    bear = sum(1 for s in sessions if s["direction"]=="BEARISH")
    neut = sum(1 for s in sessions if s["direction"]=="NEUTRAL")

    # Distribución patrones
    pat_count = defaultdict(int)
    for s in sessions: pat_count[s["pattern"]] += 1
    patterns = {k: f"{round(v/n*100,1)}%" for k,v in sorted(pat_count.items(), key=lambda x:-x[1])}
    dominant_pattern = max(pat_count, key=pat_count.get)

    # Rango distribución
    ranges = [s["ny_range"] for s in sessions]
    avg_range = round(sum(ranges)/len(ranges), 1) if ranges else 0
    max_range = round(max(ranges), 1) if ranges else 0
    min_range = round(min(ranges), 1) if ranges else 0
    rd = {"0-100":0,"100-200":0,"200-300":0,"300+":0}
    for r in ranges:
        if r < 100: rd["0-100"] += 1
        elif r < 200: rd["100-200"] += 1
        elif r < 300: rd["200-300"] += 1
        else: rd["300+"] += 1

    # Tasas de toque de niveles
    vah_touch_rate = round(sum(s["vah_hit"] for s in sessions)/n*100, 1)
    val_touch_rate = round(sum(s["val_hit"] for s in sessions)/n*100, 1)
    poc_touch_rate = round(sum(s["poc_hit"] for s in sessions)/n*100, 1)

    sess_key = DAY_ES_PLURAL[dow]

    output = {
        "title": f"Backtest {DAY_LABELS[dow]} NQ — 1 Año",
        "period": f"{sessions[0]['date']} → {sessions[-1]['date']}",
        "generated": date.today().isoformat(),
        "total_days": n,
        f"total_{day_name}s": n,
        "dominant_pattern": dominant_pattern,
        "dominant_pct": round(pat_count[dominant_pattern]/n*100, 1),
        "avg_ny_range": avg_range,
        "max_ny_range": max_range,
        "min_ny_range": min_range,
        "directions": {"BULLISH": bull, "BEARISH": bear, "NEUTRAL": neut},
        "directions_pct": {
            "BULLISH": round(bull/n*100,1),
            "BEARISH": round(bear/n*100,1),
            "NEUTRAL": round(neut/n*100,1),
        },
        "patterns": patterns,
        "range_distribution": rd,
        "level_touch_rates": {
            "VAH": vah_touch_rate,
            "POC": poc_touch_rate,
            "VAL": val_touch_rate,
        },
        "conclusions": [
            f"{round(bull/n*100,0):.0f}% de {DAY_LABELS[dow]} son BULLISH — dirección dominante: {'BULLISH' if bull>bear else 'BEARISH'}",
            f"Rango promedio NY: {avg_range} pts (max: {max_range}, min: {min_range})",
            f"Patrón más frecuente: {dominant_pattern} ({round(pat_count[dominant_pattern]/n*100,1)}%)",
            f"Tasa toque VAH: {vah_touch_rate}% · POC: {poc_touch_rate}% · VAL: {val_touch_rate}%",
        ],
        sess_key: sessions,
    }

    # Guardar con ambas claves para compatibilidad
    out_path = f"{OUT_DIR}/backtest_{day_name}_1year.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"✅ {out_path} — {n} sesiones | {bull}B/{bear}Ba/{neut}N | avg rango: {avg_range}pts")

# También generar backtest_5dias_sesiones_6m.json para viernes
fri_sessions = sessions_by_dow[4][-130:]  # ultimos ~6 meses
if fri_sessions:
    out_fri = {
        "title": "Backtest Viernes NQ — 6 Meses",
        "period": f"{fri_sessions[0]['date']} → {fri_sessions[-1]['date']}",
        "generated": date.today().isoformat(),
        "total_days": len(fri_sessions),
        "all_fridays": fri_sessions,
    }
    with open(f"{OUT_DIR}/backtest_5dias_sesiones_6m.json", "w", encoding="utf-8") as f:
        json.dump(out_fri, f, ensure_ascii=False, indent=2)
    print(f"✅ backtest_5dias_sesiones_6m.json — {len(fri_sessions)} viernes")

print(f"\n🎯 Completado. JSONs listos en {OUT_DIR}/")
print("   Ahora sube con: git add data/research/ && git commit -m 'data: backtest 1 año todos los dias' && git push")
