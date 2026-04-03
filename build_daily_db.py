#!/usr/bin/env python3
"""
build_daily_db.py — Constructor de Base de Datos Histórica NQ Whale Radar
=========================================================================
Genera: data/research/daily_master_db.json

Variables por día:
  date, dow, semana_ciclo, cot_index, cot_signal, cot_delta, cot_net,
  vxn, vxn_level, vxn_delta, dix_proxy, gex_proxy,
  nq_vs_ema200, nq_open, nq_close, nq_high, nq_low,
  yield_10y, yield_2y, yield_spread, yield_regime,
  prev_day_dir, consecutive_bearish, consecutive_bullish,
  noticia, direction, ny_range, ny_move_pct, pattern,
  vah_approx, poc_approx, val_approx

Fuentes:
  yfinance: NQ=F, ^VXN, ^TNX, ^IRX
  CFTC: COT histórico CSV (Nasdaq 100 Non-Commercial)
  Cálculo: EMA200, COT Index, semana ciclo, patrón
"""

import yfinance as yf
import json
import os
import sys
import csv
import io
import urllib.request
from datetime import date, timedelta, datetime
from collections import defaultdict

OUT_DIR  = "data/research"
OUT_FILE = f"{OUT_DIR}/daily_master_db.json"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Parámetros ────────────────────────────────────────────────────────────
END_DATE   = date.today()
START_DATE = date(2024, 1, 1)
print(f"\n🏗  Construyendo Base de Datos Histórica NQ Whale Radar")
print(f"   Período: {START_DATE} → {END_DATE}")
print(f"   Archivo: {OUT_FILE}\n")

# ─────────────────────────────────────────────────────────────────────────
# 1. DESCARGAR PRECIOS NQ=F (daily)
# ─────────────────────────────────────────────────────────────────────────
print("📥 [1/5] Descargando NQ=F precios diarios...")
df_nq = yf.download("NQ=F", start=str(START_DATE), end=str(END_DATE),
                    interval="1d", progress=False)
if df_nq.empty: sys.exit("ERROR: sin datos NQ=F")
if hasattr(df_nq.columns,'levels'): df_nq.columns = df_nq.columns.get_level_values(0)
df_nq = df_nq.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close"})
print(f"   ✅ {len(df_nq)} días de NQ=F")

# ─────────────────────────────────────────────────────────────────────────
# 2. DESCARGAR VXN (volatilidad NQ)
# ─────────────────────────────────────────────────────────────────────────
print("📥 [2/5] Descargando ^VXN (Nasdaq Volatility Index)...")
df_vxn = yf.download("^VXN", start=str(START_DATE), end=str(END_DATE),
                     interval="1d", progress=False)
if hasattr(df_vxn.columns,'levels'): df_vxn.columns = df_vxn.columns.get_level_values(0)
df_vxn = df_vxn.rename(columns={"Close":"vxn_close"})
vxn_by_date = {}
for ts, row in df_vxn.iterrows():
    d = ts.date() if hasattr(ts,'date') else ts.to_pydatetime().date()
    vxn_by_date[d.strftime("%Y-%m-%d")] = round(float(row["vxn_close"]), 2)
print(f"   ✅ {len(vxn_by_date)} días de VXN")

# ─────────────────────────────────────────────────────────────────────────
# 3. DESCARGAR YIELDS (10Y y 2Y/3M)
# ─────────────────────────────────────────────────────────────────────────
print("📥 [3/5] Descargando yields ^TNX (10Y) y ^IRX (3M)...")
df_tnx = yf.download("^TNX", start=str(START_DATE), end=str(END_DATE),
                     interval="1d", progress=False)
if hasattr(df_tnx.columns,'levels'): df_tnx.columns = df_tnx.columns.get_level_values(0)
tnx_by_date = {}
for ts, row in df_tnx.iterrows():
    d = ts.date() if hasattr(ts,'date') else ts.to_pydatetime().date()
    tnx_by_date[d.strftime("%Y-%m-%d")] = round(float(row["Close"]), 4)

df_irx = yf.download("^IRX", start=str(START_DATE), end=str(END_DATE),
                     interval="1d", progress=False)
if hasattr(df_irx.columns,'levels'): df_irx.columns = df_irx.columns.get_level_values(0)
irx_by_date = {}
for ts, row in df_irx.iterrows():
    d = ts.date() if hasattr(ts,'date') else ts.to_pydatetime().date()
    irx_by_date[d.strftime("%Y-%m-%d")] = round(float(row["Close"]) / 10, 4)  # ^IRX es x10
print(f"   ✅ {len(tnx_by_date)} días de TNX | {len(irx_by_date)} días de IRX")

# ─────────────────────────────────────────────────────────────────────────
# 4. COT HISTÓRICO (CFTC.gov)
# ─────────────────────────────────────────────────────────────────────────
print("📥 [4/5] Descargando COT histórico de CFTC.gov...")
cot_by_week = {}

# CFTC publica COT Financials en archivos anuales
CFTC_URLS = {
    2024: "https://www.cftc.gov/files/dea/history/fin_fut_txt_2024.zip",
    2025: "https://www.cftc.gov/files/dea/history/fin_fut_txt_2025.zip",
    2026: "https://www.cftc.gov/files/dea/history/fin_fut_txt_2026.zip",
}

def download_cot_year(year):
    """Descarga y parsea COT de CFTC para un año dado"""
    url = CFTC_URLS.get(year)
    if not url: return {}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        import zipfile, io as _io
        with zipfile.ZipFile(_io.BytesIO(data)) as z:
            # El archivo principal tiene nombre variable
            names = z.namelist()
            txt_file = next((n for n in names if n.endswith('.txt')), names[0])
            content = z.read(txt_file).decode('latin-1')
        result = {}
        reader = csv.DictReader(_io.StringIO(content))
        for row in reader:
            # Filtrar E-Mini Nasdaq 100 (market_and_exchange_names contiene "NASDAQ")
            name = row.get('Market_and_Exchange_Names', '') + row.get('market_and_exchange_names', '')
            if 'NASDAQ' not in name.upper() and 'NQ' not in name.upper():
                continue
            try:
                date_str = row.get('Report_Date_as_YYYY-MM-DD', '') or row.get('As_of_Date_Form_MM/DD/YYYY', '')
                if '/' in date_str:
                    parts = date_str.split('/')
                    date_str = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
                nc_long  = int(row.get('NonComm_Positions_Long_All', 0))
                nc_short = int(row.get('NonComm_Positions_Short_All', 0))
                net = nc_long - nc_short
                result[date_str] = {
                    "net": net,
                    "long": nc_long,
                    "short": nc_short,
                }
            except: continue
        return result
    except Exception as e:
        print(f"     ⚠  COT {year} no disponible: {e}")
        return {}

all_cot = {}
for yr in [2024, 2025, 2026]:
    yr_data = download_cot_year(yr)
    all_cot.update(yr_data)
    print(f"     COT {yr}: {len(yr_data)} semanas")

# Si CFTC falla, usar datos del agente actual como semilla
if len(all_cot) < 10:
    print("     ⚠  CFTC no disponible — usando datos del agente2")
    try:
        with open("agent2_data.json", encoding="utf-8") as f:
            a2 = json.load(f)
        cot_data = a2.get("cot", {})
        cot_date = cot_data.get("date", str(date.today()))
        all_cot[cot_date] = {
            "net": cot_data.get("current_net", 0),
            "long": cot_data.get("current_long", 0),
            "short": cot_data.get("current_short", 0),
        }
    except: pass

print(f"   ✅ {len(all_cot)} semanas COT cargadas")

# Construir lookup: para cada fecha → COT de esa semana (martes de la semana)
def get_cot_for_date(date_str):
    """Retorna el COT vigente para una fecha — el más reciente disponible"""
    if all_cot:
        available = sorted(k for k in all_cot if k <= date_str)
        if available:
            return all_cot[available[-1]]
    return {"net": 0, "long": 0, "short": 0}

def calc_cot_index(net_values_sorted):
    """COT Index = percentil del net actual en el rango de 1 año"""
    if len(net_values_sorted) < 2: return 50
    mn, mx = min(net_values_sorted), max(net_values_sorted)
    if mx == mn: return 50
    current = net_values_sorted[-1]
    return round((current - mn) / (mx - mn) * 100, 1)

# ─────────────────────────────────────────────────────────────────────────
# 5. FOMC / CPI CALENDAR (fechas conocidas de alto impacto)
# ─────────────────────────────────────────────────────────────────────────
print("📅 [5/5] Cargando calendario macroeconómico conocido...")

# Fechas FOMC y CPI 2024-2026 (anunciadas por la Fed/BLS)
HIGH_IMPACT_DATES = {
    # FOMC
    "2024-01-31": "FOMC", "2024-03-20": "FOMC", "2024-05-01": "FOMC",
    "2024-06-12": "FOMC", "2024-07-31": "FOMC", "2024-09-18": "FOMC",
    "2024-11-07": "FOMC", "2024-12-18": "FOMC",
    "2025-01-29": "FOMC", "2025-03-19": "FOMC", "2025-05-07": "FOMC",
    "2025-06-18": "FOMC", "2025-07-30": "FOMC", "2025-09-17": "FOMC",
    "2025-11-05": "FOMC", "2025-12-17": "FOMC",
    "2026-01-28": "FOMC", "2026-03-18": "FOMC",
    # CPI
    "2024-01-11": "CPI", "2024-02-13": "CPI", "2024-03-12": "CPI",
    "2024-04-10": "CPI", "2024-05-15": "CPI", "2024-06-12": "CPI",
    "2024-07-11": "CPI", "2024-08-14": "CPI", "2024-09-11": "CPI",
    "2024-10-10": "CPI", "2024-11-13": "CPI", "2024-12-11": "CPI",
    "2025-01-15": "CPI", "2025-02-12": "CPI", "2025-03-12": "CPI",
    "2025-04-10": "CPI", "2025-05-13": "CPI", "2025-06-11": "CPI",
    "2025-07-15": "CPI", "2025-08-13": "CPI", "2025-09-10": "CPI",
    "2025-10-15": "CPI", "2025-11-12": "CPI", "2025-12-10": "CPI",
    "2026-01-14": "CPI", "2026-02-12": "CPI", "2026-03-11": "CPI",
    "2026-04-10": "CPI",
    # NFP (primer viernes del mes)
    "2024-01-05": "NFP", "2024-02-02": "NFP", "2024-03-08": "NFP",
    "2024-04-05": "NFP", "2024-05-03": "NFP", "2024-06-07": "NFP",
    "2024-07-05": "NFP", "2024-08-02": "NFP", "2024-09-06": "NFP",
    "2024-10-04": "NFP", "2024-11-01": "NFP", "2024-12-06": "NFP",
    "2025-01-10": "NFP", "2025-02-07": "NFP", "2025-03-07": "NFP",
    "2025-04-04": "NFP", "2025-05-02": "NFP", "2025-06-06": "NFP",
    "2025-07-03": "NFP",
}

def get_noticia(date_str):
    n = HIGH_IMPACT_DATES.get(date_str)
    if n: return n
    # Jobless claims → siempre jueves
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        if d.weekday() == 3: return "JOBLESS_CLAIMS"
    except: pass
    return "ninguna"

# ─────────────────────────────────────────────────────────────────────────
# 6. CONSTRUIR BASE DE DATOS
# ─────────────────────────────────────────────────────────────────────────
print("\n🏗  Construyendo registros históricos...")

DOW_MAP = {0:"monday",1:"tuesday",2:"wednesday",3:"thursday",4:"friday"}

def vxn_level(v):
    if v is None: return "UNKNOWN"
    if v < 16:  return "COMPLACENCY"
    if v < 22:  return "NORMAL"
    if v < 30:  return "ELEVATED"
    if v < 40:  return "PANIC"
    return "EXTREME_PANIC"

def cot_signal(idx):
    if idx is None: return "UNKNOWN"
    if idx >= 65: return "BULLISH"
    if idx >= 50: return "NEUTRAL-BULLISH"
    if idx >= 35: return "NEUTRAL-BEARISH"
    return "BEARISH"

def semana_ciclo(d):
    """W1-W4 = semana del mes"""
    day = d.day
    if day <= 7:  return "W1"
    if day <= 14: return "W2"
    if day <= 21: return "W3"
    return "W4"

def identify_pattern(o, h, l, c, prev_h=None, prev_l=None):
    move = c - o
    rng  = h - l if h != l else 1
    if prev_h and h > prev_h and c < prev_h: return "SWEEP_H_RETURN"
    if prev_l and l < prev_l and c > prev_l: return "SWEEP_L_RETURN"
    if abs(move)/rng > 0.60:
        return "EXPANSION_H" if move > 0 else "EXPANSION_L"
    if abs(move)/rng < 0.25: return "ROTATION_POC"
    return "NEUTRAL"

# EMA200 rolling
ema200_val = None
ema_period = 200
ema_mult   = 2 / (ema_period + 1)

# Build sorted NQ list
nq_dates = []
for ts, row in df_nq.iterrows():
    try:
        d = ts.date() if hasattr(ts,'date') else ts.to_pydatetime().date()
        nq_dates.append((d, float(row["open"]), float(row["high"]),
                         float(row["low"]), float(row["close"])))
    except: pass
nq_dates.sort(key=lambda x: x[0])

# Para COT Index rolling: necesitar los últimos 52 valores de COT net
cot_window = []
records = []
prev_close = None
prev_dir   = None
consec_bull = 0
consec_bear = 0

for i, (d, o, h, l, c) in enumerate(nq_dates):
    if d.weekday() >= 5: continue  # skip weekends
    date_str = d.strftime("%Y-%m-%d")

    # EMA200
    if ema200_val is None:
        ema200_val = (o + c) / 2
    else:
        ema200_val = c * ema_mult + ema200_val * (1 - ema_mult)
    nq_vs_ema200 = "above" if c > ema200_val else "below"

    # VXN
    vxn = vxn_by_date.get(date_str)
    vxn_level_str = vxn_level(vxn)

    # VXN delta (vs día anterior)
    prev_vxn = None
    if i > 0:
        prev_date = nq_dates[i-1][0].strftime("%Y-%m-%d")
        prev_vxn = vxn_by_date.get(prev_date)
    vxn_delta = round(vxn - prev_vxn, 2) if (vxn and prev_vxn) else 0

    # DIX proxy: usamos VXN inverso normalizado (cuando VXN baja → institucionales compran)
    # Rango histórico VXN: ~13 (mín) a ~45 (máx) → invertido → 0-100
    dix_proxy = None
    if vxn:
        dix_proxy = round(max(0, min(100, (45 - vxn) / (45 - 13) * 100)), 1)

    # GEX proxy: usamos pendiente de VXN (negativa = GEX positivo)
    gex_positive = None
    if vxn_delta is not None:
        gex_positive = vxn_delta <= 0  # VXN baja → GEX positivo

    # Yields
    y10 = tnx_by_date.get(date_str)
    y2  = irx_by_date.get(date_str)
    yield_spread = round(y10 - y2, 4) if (y10 and y2) else None
    yield_regime = "inverted" if (yield_spread and yield_spread < 0) else "normal"

    # COT
    cot_data = get_cot_for_date(date_str)
    cot_net  = cot_data["net"]
    cot_window.append(cot_net)
    if len(cot_window) > 52: cot_window.pop(0)
    cot_idx_val = calc_cot_index(cot_window)
    cot_sig_str = cot_signal(cot_idx_val)

    # COT delta vs semana anterior
    cot_delta = 0
    if len(cot_window) >= 2:
        # Buscar COT de semana anterior
        prev_week_cot = get_cot_for_date((d - timedelta(days=7)).strftime("%Y-%m-%d"))
        cot_delta = cot_net - prev_week_cot["net"]

    # Dirección del día
    ny_range = round(h - l, 2)
    ny_move  = round(c - o, 2)
    direction = "BULLISH" if ny_move > 0 else ("BEARISH" if ny_move < 0 else "NEUTRAL")
    ny_move_pct = round(ny_move / o * 100, 3) if o else 0

    # Patrones
    prev_high = nq_dates[i-1][2] if i > 0 else None
    prev_low  = nq_dates[i-1][3] if i > 0 else None
    pattern   = identify_pattern(o, h, l, c, prev_high, prev_low)

    # VP aproximado (simple: POC ≈ VWAP simplificado)
    poc_approx = round((h + l + c) / 3, 2)
    vah_approx = round(poc_approx + ny_range * 0.25, 2)
    val_approx = round(poc_approx - ny_range * 0.25, 2)

    # Contadores consecutivos
    if prev_dir == "BULLISH": consec_bull += 1
    else: consec_bull = 0
    if prev_dir == "BEARISH": consec_bear += 1
    else: consec_bear = 0

    # Noticia
    noticia = get_noticia(date_str)

    record = {
        "date": date_str,
        "dow": DOW_MAP.get(d.weekday(), "unknown"),
        "semana_ciclo": semana_ciclo(d),
        "cot_index": cot_idx_val,
        "cot_signal": cot_sig_str,
        "cot_net": cot_net,
        "cot_delta": cot_delta,
        "vxn": vxn,
        "vxn_level": vxn_level_str,
        "vxn_delta": vxn_delta,
        "dix_proxy": dix_proxy,
        "gex_positive": gex_positive,
        "nq_vs_ema200": nq_vs_ema200,
        "nq_open": round(o, 2),
        "nq_close": round(c, 2),
        "nq_high": round(h, 2),
        "nq_low": round(l, 2),
        "yield_10y": y10,
        "yield_2y": y2,
        "yield_spread": yield_spread,
        "yield_regime": yield_regime,
        "prev_day_dir": prev_dir,
        "consecutive_bullish": consec_bull,
        "consecutive_bearish": consec_bear,
        "noticia": noticia,
        "direction": direction,
        "ny_range": ny_range,
        "ny_move_pct": ny_move_pct,
        "pattern": pattern,
        "vah_approx": vah_approx,
        "poc_approx": poc_approx,
        "val_approx": val_approx,
    }
    records.append(record)

    prev_close = c
    prev_dir   = direction

print(f"   ✅ {len(records)} registros construidos")

# ─────────────────────────────────────────────────────────────────────────
# 7. ESTADÍSTICAS GLOBALES + GUARDAR
# ─────────────────────────────────────────────────────────────────────────
by_dow = defaultdict(list)
for r in records:
    by_dow[r["dow"]].append(r)

stats = {}
for dow, recs in by_dow.items():
    n = len(recs)
    if n == 0: continue
    bull = sum(1 for r in recs if r["direction"]=="BULLISH")
    bear = sum(1 for r in recs if r["direction"]=="BEARISH")
    avg_range = round(sum(r["ny_range"] for r in recs)/n, 1)
    stats[dow] = {
        "n": n,
        "bull_pct": round(bull/n*100,1),
        "bear_pct": round(bear/n*100,1),
        "avg_range": avg_range,
    }

output = {
    "meta": {
        "version": "2.0",
        "generated": date.today().isoformat(),
        "period": f"{START_DATE} → {END_DATE}",
        "total_records": len(records),
        "variables": list(records[0].keys()) if records else [],
        "note": "DIX: proxy via VXN inverted | GEX: proxy via VXN delta | COT: CFTC.gov"
    },
    "stats_by_dow": stats,
    "records": records,
}

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, separators=(',',':'))

size_kb = os.path.getsize(OUT_FILE) // 1024
print(f"\n✅ Base de datos guardada: {OUT_FILE}")
print(f"   {len(records)} registros | {size_kb} KB")
print(f"\n📊 Estadísticas por día:")
for dow, s in sorted(stats.items()):
    print(f"   {dow:12s}: {s['n']} dias | {s['bull_pct']}% Bull | avg rango {s['avg_range']} pts")
print(f"\n🎯 Siguiente paso: python analyze_today.py")
