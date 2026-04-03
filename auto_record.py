#!/usr/bin/env python3
"""
auto_record.py — Registrador diario automático para Railway
===========================================================
Corre cada día a las 4:30PM ET vía cron en Railway.
Agrega el día de trading actual a daily_master_db.json
y regenera today_analysis.json.

Railway cron: "30 20 * * 1-5"  (20:30 UTC = 4:30PM ET)

Uso manual: python auto_record.py [YYYYMMDD]
"""

import yfinance as yf
import json, os, sys
from datetime import date, timedelta, datetime, timezone
from collections import Counter

DB_FILE   = "data/research/daily_master_db.json"
OUT_TODAY = "data/research/today_analysis.json"
A2_FILE   = "agent2_data.json"
A3_FILE   = "agent3_data.json"
A4_FILE   = "agent4_data.json"
LOG_FILE  = "data/research/auto_record.log"

os.makedirs("data/research", exist_ok=True)

# ── Fecha a registrar ──────────────────────────────────────────────────
if len(sys.argv) > 1:
    try:
        target = datetime.strptime(sys.argv[1], "%Y%m%d").date()
    except:
        print(f"Formato inválido. Usa YYYYMMDD"); sys.exit(1)
else:
    target = date.today()

date_str  = target.strftime("%Y-%m-%d")
dow       = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][target.weekday()]

if target.weekday() >= 5:
    print(f"⚠  {date_str} es fin de semana. No hay sesión. Saliendo.")
    sys.exit(0)

print(f"\n📝 Auto Record — {date_str} ({dow.upper()})")

# ── Helpers ────────────────────────────────────────────────────────────
def _load(p):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except: return {}

def _save(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(',',':'))

def semana_ciclo(d):
    day = d.day
    if day <= 7:  return "W1"
    if day <= 14: return "W2"
    if day <= 21: return "W3"
    return "W4"

def vxn_level(v):
    if not v: return "UNKNOWN"
    if v < 16:  return "COMPLACENCY"
    if v < 22:  return "NORMAL"
    if v < 30:  return "ELEVATED"
    if v < 40:  return "PANIC"
    return "EXTREME_PANIC"

def identify_pattern(o, h, l, c, prev_h=None, prev_l=None):
    move = c - o; rng = h - l if h != l else 1
    if prev_h and h > prev_h and c < prev_h: return "SWEEP_H_RETURN"
    if prev_l and l < prev_l and c > prev_l: return "SWEEP_L_RETURN"
    if abs(move)/rng > 0.60: return "EXPANSION_H" if move > 0 else "EXPANSION_L"
    if abs(move)/rng < 0.25: return "ROTATION_POC"
    return "NEUTRAL"

HIGH_IMPACT = {
    "2026-04-10": "CPI", "2026-05-07": "FOMC", "2026-05-13": "CPI",
    "2026-06-11": "CPI", "2026-06-18": "FOMC",
}
def get_noticia(ds):
    n = HIGH_IMPACT.get(ds)
    if n: return n
    try:
        d2 = datetime.strptime(ds, "%Y-%m-%d")
        if d2.weekday() == 3: return "JOBLESS_CLAIMS"
    except: pass
    return "ninguna"

# ── Descargar datos del día ────────────────────────────────────────────
date_next = (target + timedelta(days=1)).strftime("%Y-%m-%d")
date_prev = (target - timedelta(days=1)).strftime("%Y-%m-%d")

print("   Descargando NQ=F...")
df_nq = yf.download("NQ=F", start=date_prev, end=date_next, interval="1d", progress=False)
if df_nq.empty:
    print(f"   ⚠  Sin datos NQ para {date_str} (feriado?). Saliendo.")
    sys.exit(0)
if hasattr(df_nq.columns,'levels'): df_nq.columns = df_nq.columns.get_level_values(0)

# Filtrar solo el día objetivo
nq_day = df_nq[df_nq.index.strftime("%Y-%m-%d") == date_str]
if nq_day.empty:
    # Tomar el último disponible
    nq_day = df_nq.tail(1)
row = nq_day.iloc[-1]
o = float(row["Open"]); h = float(row["High"])
l = float(row["Low"]);  c = float(row["Close"])
ny_range  = round(h - l, 2)
ny_move   = round(c - o, 2)
ny_mvpct  = round(ny_move / o * 100, 3) if o else 0
direction = "BULLISH" if ny_move > 0 else "BEARISH" if ny_move < 0 else "NEUTRAL"
print(f"   NQ: O={o:.2f} H={h:.2f} L={l:.2f} C={c:.2f} | {direction}")

# VXN
df_vxn = yf.download("^VXN", start=date_prev, end=date_next, interval="1d", progress=False)
if hasattr(df_vxn.columns,'levels'): df_vxn.columns = df_vxn.columns.get_level_values(0)
vxn_val = None
if not df_vxn.empty:
    vxn_row = df_vxn[df_vxn.index.strftime("%Y-%m-%d") == date_str]
    if vxn_row.empty: vxn_row = df_vxn.tail(1)
    vxn_val = round(float(vxn_row.iloc[-1]["Close"]), 2)
print(f"   VXN: {vxn_val} ({vxn_level(vxn_val)})")

# Yields
df_tnx = yf.download("^TNX", start=date_prev, end=date_next, interval="1d", progress=False)
if hasattr(df_tnx.columns,'levels'): df_tnx.columns = df_tnx.columns.get_level_values(0)
y10 = None
if not df_tnx.empty:
    tnx_row = df_tnx[df_tnx.index.strftime("%Y-%m-%d") == date_str]
    if tnx_row.empty: tnx_row = df_tnx.tail(1)
    y10 = round(float(tnx_row.iloc[-1]["Close"]), 4)

df_irx = yf.download("^IRX", start=date_prev, end=date_next, interval="1d", progress=False)
if hasattr(df_irx.columns,'levels'): df_irx.columns = df_irx.columns.get_level_values(0)
y2 = None
if not df_irx.empty:
    irx_row = df_irx[df_irx.index.strftime("%Y-%m-%d") == date_str]
    if irx_row.empty: irx_row = df_irx.tail(1)
    y2 = round(float(irx_row.iloc[-1]["Close"]) / 10, 4)

yield_spread = round(y10 - y2, 4) if (y10 and y2) else None
yield_regime = "inverted" if (yield_spread and yield_spread < 0) else "normal"

# EMA200 — necesita historia previa
df_ema = yf.download("NQ=F", start=(target - timedelta(days=300)).strftime("%Y-%m-%d"),
                     end=date_next, interval="1d", progress=False)
if hasattr(df_ema.columns,'levels'): df_ema.columns = df_ema.columns.get_level_values(0)
ema200 = None
nq_vs_ema = "above"
if not df_ema.empty and "Close" in df_ema.columns:
    closes = [float(x) for x in df_ema["Close"].dropna()]
    if len(closes) >= 5:
        ema = closes[0]
        mult = 2/(200+1)
        for cl in closes[1:]:
            ema = cl * mult + ema * (1-mult)
        ema200 = round(ema, 2)
        nq_vs_ema = "above" if c > ema200 else "below"

# Leer agentes actuales para DIX/GEX/COT
a2 = _load(A2_FILE)
a3 = _load(A3_FILE)
a4 = _load(A4_FILE)

cot_data  = a2.get("cot", {})
cot_net   = int(cot_data.get("current_net", 0) or 0)
cot_idx   = float(cot_data.get("cot_index", 50) or 50)
cot_sig   = a2.get("signal", "NEUTRAL")
cot_mom   = a2.get("momentum", {})
cot_delta = int(cot_mom.get("weekly_velocity", 0) or 0)

raw3      = a3.get("raw_inputs", {})
dix_val   = float(raw3.get("DIX", 0) or 0)
gex_raw   = float(raw3.get("GEX_B", 0) or 0)
gex_pos   = gex_raw >= 0
ai_score  = int(a4.get("global_score", 50) or 50)

# VP aproximado
poc_approx = round((h + l + c) / 3, 2)
vah_approx = round(poc_approx + ny_range * 0.25, 2)
val_approx = round(poc_approx - ny_range * 0.25, 2)

# Noticia
noticia = get_noticia(date_str)

# ── Cargar DB existente ────────────────────────────────────────────────
db = _load(DB_FILE) if os.path.exists(DB_FILE) else {"meta":{}, "stats_by_dow":{}, "records":[]}
records = db.get("records", [])

# Verificar si este día ya está en la DB
existing_dates = {r["date"] for r in records}
if date_str in existing_dates:
    print(f"   ⚠  {date_str} ya existe en la DB. Actualizando...")
    records = [r for r in records if r["date"] != date_str]

# Buscar día anterior para consecutivos
records_sorted = sorted(records, key=lambda x: x.get("date",""))
prev_record = records_sorted[-1] if records_sorted else None
prev_dir    = prev_record.get("direction") if prev_record else None
cons_bull   = (prev_record.get("consecutive_bullish",0) + 1) if prev_dir=="BULLISH" else 0
cons_bear   = (prev_record.get("consecutive_bearish",0) + 1) if prev_dir=="BEARISH" else 0
prev_h      = prev_record.get("nq_high") if prev_record else None
prev_l      = prev_record.get("nq_low") if prev_record else None

pattern = identify_pattern(o, h, l, c, prev_h, prev_l)

# ── Nuevo registro ─────────────────────────────────────────────────────
new_record = {
    "date": date_str,
    "dow": dow,
    "semana_ciclo": semana_ciclo(target),
    "cot_index": cot_idx,
    "cot_signal": cot_sig,
    "cot_net": cot_net,
    "cot_delta": cot_delta,
    "vxn": vxn_val,
    "vxn_level": vxn_level(vxn_val),
    "vxn_delta": 0,
    "dix_proxy": dix_val if dix_val else round(max(0,min(100,(45-vxn_val)/(45-13)*100)),1) if vxn_val else None,
    "dix_real": dix_val if dix_val > 0 else None,
    "gex_positive": gex_pos,
    "gex_b": round(gex_raw, 3),
    "ai_score": ai_score,
    "nq_vs_ema200": nq_vs_ema,
    "ema200": ema200,
    "nq_open": round(o,2),
    "nq_close": round(c,2),
    "nq_high": round(h,2),
    "nq_low": round(l,2),
    "yield_10y": y10,
    "yield_2y": y2,
    "yield_spread": yield_spread,
    "yield_regime": yield_regime,
    "prev_day_dir": prev_dir,
    "consecutive_bullish": cons_bull,
    "consecutive_bearish": cons_bear,
    "noticia": noticia,
    "direction": direction,
    "ny_range": ny_range,
    "ny_move_pct": ny_mvpct,
    "pattern": pattern,
    "vah_approx": vah_approx,
    "poc_approx": poc_approx,
    "val_approx": val_approx,
    "recorded_at": datetime.now(timezone.utc).isoformat(),
    "source": "auto_record.py"
}

records.append(new_record)
records.sort(key=lambda x: x.get("date",""))

# ── Estadísticas por día actualizar ───────────────────────────────────
from collections import defaultdict
by_dow = defaultdict(list)
for r in records:
    by_dow[r["dow"]].append(r)

stats = {}
for dw, recs in by_dow.items():
    n2 = len(recs)
    if n2 == 0: continue
    bull2 = sum(1 for r in recs if r["direction"]=="BULLISH")
    bear2 = sum(1 for r in recs if r["direction"]=="BEARISH")
    avg_r = round(sum(r["ny_range"] for r in recs)/n2, 1)
    stats[dw] = {"n":n2,"bull_pct":round(bull2/n2*100,1),"bear_pct":round(bear2/n2*100,1),"avg_range":avg_r}

# ── Guardar DB actualizada ─────────────────────────────────────────────
db["meta"]["generated"]     = date.today().isoformat()
db["meta"]["total_records"] = len(records)
db["meta"]["last_record"]   = date_str
db["stats_by_dow"]          = stats
db["records"]               = records

_save(DB_FILE, db)
sz = os.path.getsize(DB_FILE) // 1024
print(f"   ✅ DB actualizada: {len(records)} registros | {sz} KB")

# ── Log ────────────────────────────────────────────────────────────────
log_entry = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "date": date_str,
    "direction": direction,
    "ny_range": ny_range,
    "vxn": vxn_val,
    "cot": cot_idx,
    "pattern": pattern,
    "total_records": len(records),
}
logs = _load(LOG_FILE) if os.path.exists(LOG_FILE) else []
logs.append(log_entry)
logs = logs[-365:]  # max 1 año de log
_save(LOG_FILE, logs)

# ── Regenerar analyze_today ────────────────────────────────────────────
print("\n   Regenerando today_analysis.json...")
os.system(f'python analyze_today.py 2>&1')

print(f"\n✅ auto_record completado: {date_str}")
print(f"   {direction} | Rango: {ny_range} pts | VXN: {vxn_val} | Patrón: {pattern}")
print(f"   DB total: {len(records)} días registrados")
