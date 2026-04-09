"""
find_real_predictor.py  v2  (OPTIMIZADO)
═══════════════════════════════════════════════════════════════
BÚSQUEDA DEL PREDICTOR REAL — Miércoles, Jueves, Viernes

Candidatos testados:
  1. Dirección día anterior (NY session)
  2. Sesión Asia (00:00-07:00 ET)
  3. Pre-market direction (7:00-9:29)
  4. Gap apertura NY vs cierre anterior
  5. Opening drive primera vela 9:30-9:44
  6. PM range (pequeño/medio/grande)
  7. Tendencia semanal (lunes→hoy)
  8. VXN nivel (LOW/MID/HIGH)
  9. Spike 8:30

OPTIMIZADO: stats precomputadas por día (no VP por sesión)
"""

import sys, json
import pandas as pd
import numpy as np
import pytz
from datetime import datetime, date, timedelta

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

print("\n" + "█"*65)
print("  BÚSQUEDA DEL PREDICTOR REAL — Mie/Jue/Vie  [v2]")
print("  9 candidatos | Ranking por % accuracy")
print("█"*65)

# ── 1. CARGAR DATOS ───────────────────────────────────────────
print("\n  Cargando CSV...")
raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()

# ── 2. PRECOMPUTAR STATS DIARIAS ──────────────────────────────
print("  Precalculando stats diarias...")

def bt_time(d, t0, t1):
    a = datetime.strptime(t0,"%H:%M").time()
    b = datetime.strptime(t1,"%H:%M").time()
    return d[(d.index.time >= a) & (d.index.time <= b)]

all_dates = sorted({d for d in raw.index.date if pd.Timestamp(d).weekday() < 5})
day_stats = {}

for day in all_dates:
    s0 = ET.localize(datetime(day.year,day.month,day.day,0,0))
    s1 = ET.localize(datetime(day.year,day.month,day.day,16,30))
    d = raw[(raw.index>=s0)&(raw.index<=s1)].copy()
    if d.empty: continue

    asia = bt_time(d,"00:00","06:59")
    pm   = bt_time(d,"07:00","09:29")
    ny   = bt_time(d,"09:30","16:00")
    spk  = bt_time(d,"08:30","08:44")
    pre8 = bt_time(d,"08:00","08:29")
    od   = bt_time(d,"09:30","09:44")

    stats = {"day": day}

    # Asia
    if len(asia) >= 2:
        am = float(asia.iloc[-1]["Close"]) - float(asia.iloc[0]["Open"])
        stats["asia_move"]  = round(am)
        stats["asia_dir"]   = "BULL" if am>20 else ("BEAR" if am<-20 else "FLAT")
    else:
        stats["asia_dir"] = "NONE"

    # PM
    if len(pm) >= 2:
        pm_m = float(pm.iloc[-1]["Close"]) - float(pm.iloc[0]["Open"])
        pm_r = float(pm["High"].max()) - float(pm["Low"].min())
        stats["pm_move"]  = round(pm_m)
        stats["pm_range"] = round(pm_r)
        stats["pm_dir"]   = "BULL" if pm_m>15 else ("BEAR" if pm_m<-15 else "FLAT")
        stats["pm_size"]  = "SMALL" if pm_r<80 else ("MED" if pm_r<160 else "LARGE")
    else:
        stats["pm_dir"] = "NONE"; stats["pm_size"] = "NONE"

    # NY
    if len(ny) >= 4:
        ny_o = float(ny.iloc[0]["Open"])
        ny_c = float(ny.iloc[-1]["Close"])
        ny_m = ny_c - ny_o
        ny_r = float(ny["High"].max()) - float(ny["Low"].min())
        stats["ny_open"]  = round(ny_o)
        stats["ny_close"] = round(ny_c)
        stats["ny_move"]  = round(ny_m)
        stats["ny_range"] = round(ny_r)
        stats["ny_dir"]   = "BULL" if ny_m>30 else ("BEAR" if ny_m<-30 else "FLAT")
        stats["ny_hi"]    = float(ny["High"].max())
        stats["ny_lo"]    = float(ny["Low"].min())
    else:
        stats["ny_dir"] = "NONE"

    # Opening drive
    if len(od) >= 1:
        od_m = float(od.iloc[-1]["Close"]) - float(od.iloc[0]["Open"])
        stats["od_dir"] = "BULL" if od_m>10 else ("BEAR" if od_m<-10 else "FLAT")
    else:
        stats["od_dir"] = "NONE"

    # Spike 8:30
    if len(spk)>=1 and len(pre8)>=1:
        sm = float(spk.iloc[-1]["Close"]) - float(pre8.iloc[-1]["Close"])
        stats["spike_dir"] = "UP" if sm>25 else ("DOWN" if sm<-25 else "FLAT")
    else:
        stats["spike_dir"] = "NONE"

    day_stats[day] = stats

print(f"  {len(day_stats)} días con stats")

# VXN
print("  Descargando ^VXN...")
vxn_day = {}
try:
    import yfinance as yf
    vdf = yf.download("^VXN", period="24mo", interval="1d", progress=False, auto_adjust=True)
    if isinstance(vdf.columns, pd.MultiIndex):
        vdf.columns = vdf.columns.get_level_values(0)
    for idx, row in vdf.iterrows():
        vxn_day[idx.date()] = round(float(row["Close"]),2)
    print(f"  VXN: {len(vxn_day)} días")
except: print("  VXN no disponible")

# ── 3. CONSTRUIR SESIONES (lookup rápido) ─────────────────────
def build_sessions(weekday):
    target_days = [d for d in all_dates if pd.Timestamp(d).weekday()==weekday]
    sessions = []
    for day in target_days:
        if day not in day_stats: continue
        s = day_stats[day]
        if s.get("ny_dir","NONE") == "NONE": continue

        # Día anterior de trading
        prev = None
        for td in reversed(all_dates):
            if td < day:
                prev = td; break
        if prev is None or prev not in day_stats: continue
        ps = day_stats[prev]

        # Gap
        gap_d = "NONE"
        if "ny_close" in ps and "ny_open" in s:
            gap = s["ny_open"] - ps["ny_close"]
            gap_d = "GAP_UP" if gap>15 else ("GAP_DOWN" if gap<-15 else "FLAT")

        # Tendencia semanal
        week_start = day - timedelta(days=day.weekday())
        wdays = [d for d in all_dates if week_start <= d < day]
        weekly_d = "NONE"
        if wdays:
            first_open = day_stats[wdays[0]].get("ny_open",0)
            last_close = ps.get("ny_close",0)
            if first_open and last_close:
                wm = last_close - first_open
                weekly_d = "BULL" if wm>50 else ("BEAR" if wm<-50 else "FLAT")

        # VXN nivel
        vxn = vxn_day.get(day)
        vxn_lvl = "NONE"
        if vxn:
            vxn_lvl = "LOW" if vxn<20 else ("MID" if vxn<25 else "HIGH")

        sessions.append({
            "date":       day,
            "ny_dir":     s["ny_dir"],
            "ny_range":   s.get("ny_range",0),
            "prev_day":   ps.get("ny_dir","NONE"),        # 1
            "asia":       s.get("asia_dir","NONE"),        # 2
            "pm_dir":     s.get("pm_dir","NONE"),          # 3
            "gap":        gap_d,                           # 4
            "od_dir":     s.get("od_dir","NONE"),          # 5
            "pm_size":    s.get("pm_size","NONE"),         # 6
            "weekly":     weekly_d,                        # 7
            "vxn_lvl":    vxn_lvl,                        # 8
            "spike":      s.get("spike_dir","NONE"),       # 9
        })
    return pd.DataFrame(sessions)

# ── 4. EVALUAR PREDICTOR ─────────────────────────────────────
def eval_predictor(df, feature, min_n=8):
    results = []
    for val in df[feature].unique():
        if val in ("NONE","FLAT"): continue
        sub = df[df[feature]==val]
        if len(sub) < min_n: continue
        for direction in ["BULL","BEAR"]:
            n_dir = (sub["ny_dir"]==direction).sum()
            pct   = n_dir/len(sub)*100
            results.append({
                "feature":feature, "value":val,
                "predicts":direction, "n":len(sub),
                "correct":int(n_dir), "pct":round(pct,1)
            })
    return sorted(results, key=lambda x: x["pct"], reverse=True)

# ── 5. ANÁLISIS POR DÍA ───────────────────────────────────────
LABELS = {
    "prev_day":  "1. Dirección día anterior",
    "asia":      "2. Asia session direction",
    "pm_dir":    "3. Pre-market direction",
    "gap":       "4. Gap Open vs prev close",
    "od_dir":    "5. Opening drive 9:30-9:44",
    "pm_size":   "6. PM range (pequeño/grande)",
    "weekly":    "7. Tendencia semanal",
    "vxn_lvl":   "8. VXN nivel",
    "spike":     "9. Spike 8:30",
}
DIAS_ES = {2:"MIÉRCOLES",3:"JUEVES",4:"VIERNES"}

arg = sys.argv[1].lower() if len(sys.argv)>1 else "all"
days_to_run = {2,3,4}
if arg in ("wednesday","miercoles","mie","wed"): days_to_run={2}
elif arg in ("thursday","jueves","jue","thu"):   days_to_run={3}
elif arg in ("friday","viernes","vie","fri"):    days_to_run={4}

all_day_results = {}

for wd in sorted(days_to_run):
    print(f"\n\n{'█'*65}")
    print(f"  📅  {DIAS_ES[wd]}")
    print(f"{'█'*65}")

    df_s = build_sessions(wd)
    if df_s.empty or len(df_s)<10:
        print("  Datos insuficientes"); continue
    n = len(df_s)
    print(f"  {n} sesiones  |  {df_s['date'].min()} → {df_s['date'].max()}")

    bull_b=(df_s["ny_dir"]=="BULL").sum()/n*100
    bear_b=(df_s["ny_dir"]=="BEAR").sum()/n*100
    flat_b=(df_s["ny_dir"]=="FLAT").sum()/n*100
    print(f"  Base: BULL {bull_b:.0f}% | BEAR {bear_b:.0f}% | FLAT {flat_b:.0f}%")

    # Evaluar todos
    feature_bests = []
    for feat in LABELS:
        res = eval_predictor(df_s, feat)
        if res:
            feature_bests.append((feat, res[0]))

    feature_bests.sort(key=lambda x: x[1]["pct"], reverse=True)

    print(f"\n  RANKING COMPLETO DE PREDICTORES")
    print("  " + "═"*60)
    print(f"  {'Rk':<4} {'Predictor':<32} {'Signal':<13} → {'Dir':<5} {'Acc':>6}  Bar")
    print("  " + "─"*60)

    top3_rules = []
    for rk, (feat, best) in enumerate(feature_bests, 1):
        bar = "█"*int(best["pct"]/5)
        medal = "🥇" if rk==1 else ("🥈" if rk==2 else ("🥉" if rk==3 else f"  {rk} "))
        sig_flag = " ✅" if best["pct"]>=60 else (" ⚠️" if best["pct"]>=55 else "   ")
        print(f"  {medal} {LABELS[feat]:<31} [{best['value']:<11}] → {best['predicts']:<5} {best['pct']:>5.1f}% {sig_flag}  n={best['n']}  {bar}")
        if best["pct"]>=60:
            top3_rules.append(best)

    # Combos
    print(f"\n  COMBINACIONES TOP-2 (mejor precisión conjunta)")
    print("  " + "─"*58)
    combos = 0
    for i in range(min(4,len(feature_bests))):
        for j in range(i+1,min(5,len(feature_bests))):
            f1,r1 = feature_bests[i]
            f2,r2 = feature_bests[j]
            v1,p1 = r1["value"],r1["predicts"]
            v2,p2 = r2["value"],r2["predicts"]
            if p1 != p2: continue
            sub = df_s[(df_s[f1]==v1)&(df_s[f2]==v2)]
            if len(sub)<5: continue
            nc = (sub["ny_dir"]==p1).sum()
            pct = nc/len(sub)*100
            if pct < 60: continue
            bar = "█"*int(pct/5)
            print(f"  {LABELS[f1]} [{v1}]")
            print(f"  + {LABELS[f2]} [{v2}]")
            print(f"  → NY {p1}: {nc}/{len(sub)} = {pct:.1f}%  {bar}\n")
            combos += 1
    if combos == 0:
        print("  (ninguna combo supera 60%)")

    # Guardar reglas
    all_day_results[DIAS_ES[wd]] = {
        "sessions": n,
        "base_bull": round(bull_b,1),
        "base_bear": round(bear_b,1),
        "top_predictor": LABELS[feature_bests[0][0]] if feature_bests else "—",
        "top_pct": feature_bests[0][1]["pct"] if feature_bests else 0,
        "validated_rules": [
            f"{LABELS[r['feature']]} [{r['value']}] → NY {r['predicts']}: {r['pct']}%"
            for r in [feature_bests[i][1] for i in range(len(feature_bests))
                      if feature_bests[i][1]["pct"]>=60]
        ]
    }

# ── 6. RESUMEN EJECUTIVO ─────────────────────────────────────
print("\n\n" + "═"*65)
print("  📊  RESUMEN EJECUTIVO — ¿Cuál es el predictor de cada día?")
print("═"*65)
for day_name, res in all_day_results.items():
    print(f"\n  {day_name}  ({res['sessions']} sesiones)")
    print(f"  Base: BULL {res['base_bull']}% / BEAR {res['base_bear']}%")
    print(f"  Mejor predictor: {res['top_predictor']}  → {res['top_pct']}%")
    if res["validated_rules"]:
        print(f"  Reglas validadas (≥60%):")
        for r in res["validated_rules"]:
            print(f"    ✅ {r}")
    else:
        print(f"  ⚠️  Ningún predictor supera 60% de manera consistente")

# Guardar JSON
with open("data/predictor_ranking.json","w",encoding="utf-8") as f:
    json.dump(all_day_results, f, indent=2, ensure_ascii=False)
print(f"\n  💾  Guardado: data/predictor_ranking.json")
print("█"*65 + "\n")
