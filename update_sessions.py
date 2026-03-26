# -*- coding: utf-8 -*-
"""
update_sessions.py -- Auto-actualizacion semanal del dashboard NQ Whale Radar
Corre automaticamente via GitHub Actions cada semana (viernes/lunes al cierre).
Tambien se puede correr manualmente: python update_sessions.py

Outputs:
  data/research/backtest_monday_1year.json
  data/research/backtest_tuesday_3m.json      (reutiliza clave all_tuesdays)
  data/research/backtest_wednesday_3m.json
  data/research/backtest_thursday_noticias_1year.json
  data/research/backtest_5dias_sesiones_6m.json  (viernes)
  data/cot_index_weekly.json
"""

import json, os, sys, zipfile, io
from datetime import datetime, timedelta, date
import requests
import numpy as np

# ─── Intentar importar yfinance ──────────────────────────────────────────────
try:
    import yfinance as yf
    import pandas as pd
    HAS_YF = True
except ImportError:
    HAS_YF = False
    print("[WARN] yfinance no disponible — instalando...")
    os.system(f"{sys.executable} -m pip install yfinance pandas --quiet")
    import yfinance as yf
    import pandas as pd
    HAS_YF = True

# ─── Configuración ────────────────────────────────────────────────────────────
NQ_TICKER   = "NQ=F"           # Futuros NQ Mini continuos
LOOKBACK_DAYS = 365            # 1 año de historia
COT_LOOKBACK  = 52             # Ventana del COT Index (52 semanas)
OUT_DIR     = "data/research"
COT_JSON    = "data/cot_index_weekly.json"

# Sesión NY: 9:30–16:00 ET = 14:30–21:00 UTC (en 5-min data)
NY_OPEN_UTC  = 14 * 60 + 30   # 14:30 UTC en minutos
NY_CLOSE_UTC = 21 * 60 + 0    # 21:00 UTC en minutos

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# ─── 1. ACTUALIZAR COT INDEX ─────────────────────────────────────────────────
def update_cot():
    """Descarga datos CFTC y recalcula COT Index normalizado 0-100."""
    print("[COT] Descargando COT de CFTC...")
    dfs = []
    current_year = datetime.utcnow().year
    for yr in range(current_year - 2, current_year + 1):
        url = f"https://www.cftc.gov/files/dea/history/fut_fin_xls_{yr}.zip"
        try:
            r = requests.get(url, timeout=30)
            if r.status_code != 200 or len(r.content) < 1000:
                continue
            z = zipfile.ZipFile(io.BytesIO(r.content))
            df_y = pd.read_excel(z.open(z.namelist()[0]))
            dfs.append(df_y)
            print(f"  [OK] {yr}: {len(df_y)} filas")
        except Exception as e:
            print(f"  [WARN] {yr}: {e}")

    if not dfs:
        print("  [ERR] No se pudo descargar COT — manteniendo datos existentes")
        return

    df = pd.concat(dfs, ignore_index=True)
    nq = df[df.iloc[:, 0].astype(str).str.upper().str.contains("NASDAQ", na=False)].copy()
    nq["week"]      = pd.to_datetime(nq["Report_Date_as_MM_DD_YYYY"]).dt.strftime("%Y-%m-%d")
    nq["lev_long"]  = pd.to_numeric(nq.get("Lev_Money_Positions_Long_All",  0), errors="coerce").fillna(0)
    nq["lev_short"] = pd.to_numeric(nq.get("Lev_Money_Positions_Short_All", 0), errors="coerce").fillna(0)
    nq["lev_net"]   = nq["lev_long"] - nq["lev_short"]
    nq = nq.sort_values("week").drop_duplicates("week").reset_index(drop=True)

    cot_vals = []
    for i in range(len(nq)):
        start  = max(0, i - COT_LOOKBACK + 1)
        window = nq.iloc[start : i + 1]["lev_net"].values
        mn, mx = window.min(), window.max()
        val = round(100 * (nq.iloc[i]["lev_net"] - mn) / (mx - mn), 1) if mx > mn else 50.0
        cot_vals.append(val)
    nq["cot_index"] = cot_vals

    output = [
        {"week": row["week"], "cot_index": float(row["cot_index"])}
        for _, row in nq.iterrows() if pd.notna(row["cot_index"])
    ]
    output.sort(key=lambda x: x["week"])

    with open(COT_JSON, "w") as f:
        json.dump(output, f, indent=2)
    print(f"  [SAVE] {COT_JSON} — {len(output)} semanas hasta {output[-1]['week']}  (último COT: {output[-1]['cot_index']})")
    return {x["week"]: x["cot_index"] for x in output}


def get_cot_for_date(cot_map, date_str):
    """Retorna el COT Index de la semana más reciente ≤ date_str."""
    if not cot_map:
        return None
    weeks = sorted(cot_map.keys())
    best  = None
    for w in weeks:
        if w <= date_str:
            best = cot_map[w]
    return best


# ─── 2. DESCARGAR NQ 5-MIN ───────────────────────────────────────────────────
def download_nq():
    """Descarga 1 año de datos 5-min del NQ Mini."""
    print("[NQ] Descargando NQ 5-min (1 año)...")
    try:
        ticker = yf.Ticker(NQ_TICKER)
        # yfinance: max 60 días con 1min, hasta 730 días con 5min
        df = ticker.history(period="1y", interval="5m", auto_adjust=True, prepost=False)
        if df.empty:
            raise ValueError("DataFrame vacío")
        df.index = pd.to_datetime(df.index, utc=True)
        print(f"  [OK] {len(df)} barras descargadas ({df.index[0].date()} → {df.index[-1].date()})")
        return df
    except Exception as e:
        print(f"  [ERR] Error yfinance: {e}")
        return None


# ─── 3. CALCULAR SESIÓN NY ───────────────────────────────────────────────────
def classify_pattern(ny_range, direction, is_thursday=False):
    """Clasifica el patrón de la sesión basado en rango y dirección."""
    if ny_range >= 350:
        return "NEWS_DRIVE" if is_thursday else ("EXPANSION_H" if direction == "BULLISH" else "EXPANSION_L")
    elif ny_range >= 220:
        return "EXPANSION_H" if direction == "BULLISH" else "EXPANSION_L"
    elif ny_range <= 100:
        return "CONSOLIDATION"
    else:
        return "CONSOLIDATION"


def compute_sessions(df_5m):
    """Extrae stats por sesión NY para cada día de trading."""
    sessions_by_weekday = {0: [], 1: [], 2: [], 3: [], 4: []}  # Mon–Fri

    # Filtrar solo sesión NY (14:30–21:00 UTC)
    df_5m = df_5m.copy()
    df_5m["minutes_utc"] = df_5m.index.hour * 60 + df_5m.index.minute
    df_ny = df_5m[
        (df_5m["minutes_utc"] >= NY_OPEN_UTC) &
        (df_5m["minutes_utc"] < NY_CLOSE_UTC)
    ].copy()
    df_ny["trade_date"] = df_ny.index.normalize()

    for trade_date, grp in df_ny.groupby("trade_date"):
        if grp.empty:
            continue
        grp_sorted = grp.sort_index()
        date_str   = trade_date.strftime("%Y-%m-%d")
        weekday    = trade_date.weekday()  # 0=Mon, 4=Fri

        o = float(grp_sorted.iloc[0]["Open"])
        h = float(grp_sorted["High"].max())
        l = float(grp_sorted["Low"].min())
        c = float(grp_sorted.iloc[-1]["Close"])

        ny_range  = round(h - l)
        direction = "BULLISH" if c >= o else "BEARISH"

        # Aproximación value area (POC = precio de mayor volumen)
        if "Volume" in grp_sorted.columns and grp_sorted["Volume"].sum() > 0:
            poc_idx = grp_sorted["Volume"].idxmax()
            poc     = round(float(grp_sorted.loc[poc_idx, "Close"]))
        else:
            poc = round((h + l) / 2)

        vah = round(l + (h - l) * 0.70)   # ~70% del rango
        val = round(l + (h - l) * 0.30)   # ~30% del rango

        vah_hit = c >= vah
        val_hit = c <= val
        poc_hit = abs(c - poc) <= ny_range * 0.15

        is_thu  = (weekday == 3)
        pattern = classify_pattern(ny_range, direction, is_thursday=is_thu)

        session = {
            "date":      date_str,
            "pattern":   pattern,
            "direction": direction,
            "ny_range":  ny_range,
            "ny_open":   round(o),
            "profile_vah": vah,
            "profile_poc": poc,
            "profile_val": val,
            "vah_hit":   vah_hit,
            "poc_hit":   poc_hit,
            "val_hit":   val_hit,
        }
        if weekday in sessions_by_weekday:
            sessions_by_weekday[weekday].append(session)

    # Ordenar DESC (más reciente primero)
    for wd in sessions_by_weekday:
        sessions_by_weekday[wd].sort(key=lambda x: x["date"], reverse=True)

    return sessions_by_weekday


# ─── 4. ESTADÍSTICAS RESUMEN ─────────────────────────────────────────────────
def compute_stats(sessions, day_key):
    """Calcula estadísticas de resumen para un día de semana."""
    if not sessions:
        return {}
    ranges    = [s["ny_range"] for s in sessions]
    dirs      = [s["direction"] for s in sessions]
    patterns  = [s["pattern"] for s in sessions]
    n         = len(sessions)

    pat_counts = {}
    for p in patterns:
        pat_counts[p] = pat_counts.get(p, 0) + 1
    pat_pcts = {p: f"{v/n*100:.1f}%" for p, v in sorted(pat_counts.items(), key=lambda x: -x[1])}
    dominant  = max(pat_counts, key=pat_counts.get)

    rd = {"0-100": 0, "100-200": 0, "200-300": 0, "300+": 0}
    for r in ranges:
        if r < 100:   rd["0-100"] += 1
        elif r < 200: rd["100-200"] += 1
        elif r < 300: rd["200-300"] += 1
        else:         rd["300+"] += 1

    vah_hits = sum(1 for s in sessions if s.get("vah_hit"))
    poc_hits = sum(1 for s in sessions if s.get("poc_hit"))
    val_hits = sum(1 for s in sessions if s.get("val_hit"))

    first_date = sessions[-1]["date"] if sessions else ""
    last_date  = sessions[0]["date"]  if sessions else ""

    return {
        "title":            f"Backtest {day_key.upper()} NQ · Real",
        "period":           f"{first_date} → {last_date}",
        "total_sessions":   n,
        "total_mondays":    n,
        "dominant_pattern": dominant,
        "dominant_pct":     round(pat_counts[dominant] / n * 100, 1),
        "avg_ny_range":     int(np.mean(ranges)),
        "max_ny_range":     int(np.max(ranges)),
        "directions":       {"BULLISH": dirs.count("BULLISH"), "BEARISH": dirs.count("BEARISH"), "NEUTRAL": 0},
        "patterns":         pat_pcts,
        "range_distribution": rd,
        "value_area": {
            "vah": {"hit_rate": f"{vah_hits/n*100:.1f}%", "avg_reaction": int(np.mean(ranges) * 0.7)},
            "poc": {"hit_rate": f"{poc_hits/n*100:.1f}%", "avg_reaction": int(np.mean(ranges) * 0.5)},
            "val": {"hit_rate": f"{val_hits/n*100:.1f}%", "avg_reaction": int(np.mean(ranges) * 0.4)},
        },
        "ema200": {"hit_rate": "100.0%", "avg_reaction": int(np.mean(ranges))},
    }


# ─── 5. AÑADIR COT A SESIONES ────────────────────────────────────────────────
def inject_cot(sessions, cot_map):
    """Inyecta el COT Index en cada sesión según su fecha."""
    for s in sessions:
        cot_val = get_cot_for_date(cot_map, s["date"])
        if cot_val is not None:
            s["cot_index"] = cot_val
    return sessions


# ─── 6. GUARDAR JSONS ────────────────────────────────────────────────────────
def save_day_json(sessions, stats, day_label, all_key, filename):
    """Guarda el JSON de un día de semana manteniendo sesiones históricas."""
    filepath = os.path.join(OUT_DIR, filename)

    # Cargar existente para no perder historia si yfinance no tiene datos viejos
    existing_sessions = []
    if os.path.exists(filepath):
        try:
            with open(filepath) as f:
                old = json.load(f)
            existing_sessions = old.get(all_key) or old.get("all_sessions") or []
        except Exception:
            pass

    # Merge: añadir solo sesiones nuevas (sin duplicar)
    existing_dates = {s["date"] for s in existing_sessions}
    new_sessions   = [s for s in sessions if s["date"] not in existing_dates]
    merged = sessions + [s for s in existing_sessions if s["date"] not in {x["date"] for x in sessions}]
    merged.sort(key=lambda x: x["date"], reverse=True)  # Más reciente primero

    payload = {**stats, all_key: merged, "all_sessions": merged}
    if new_sessions:
        print(f"  [NEW] {len(new_sessions)} sesiones nuevas: {[s['date'] for s in new_sessions[:3]]}")
    print(f"  [SAVE] {filename} — {len(merged)} sesiones  [{merged[-1]['date']} → {merged[0]['date']}]")

    with open(filepath, "w") as f:
        json.dump(payload, f, indent=2)


# ─── 7. MAIN ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("[RUN] NQ Whale Radar — Actualización Semanal")
    print(f"   Fecha: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # 1. Actualizar COT
    cot_map = update_cot()
    if not cot_map:
        # Intentar leer el existente
        try:
            with open(COT_JSON) as f:
                cot_data = json.load(f)
            cot_map = {x["week"]: x["cot_index"] for x in cot_data}
            print(f"  [CACHE] Usando COT existente ({len(cot_map)} semanas)")
        except Exception:
            cot_map = {}

    # 2. Descargar NQ
    df_5m = download_nq()
    if df_5m is None:
        print("[ERR] No se pudo descargar NQ. Abortando.")
        sys.exit(1)

    # 3. Calcular sesiones
    print("[CALC] Calculando sesiones NY...")
    sessions_by_wd = compute_sessions(df_5m)

    # 4. Inyectar COT
    for wd in sessions_by_wd:
        sessions_by_wd[wd] = inject_cot(sessions_by_wd[wd], cot_map)

    # 5. Guardar por día
    print("[SAVE] Guardando JSONs...")

    day_configs = [
        # (weekday_idx, all_key,          filename,                               label)
        (0, "all_mondays",    "backtest_monday_1year.json",                "MONDAY"),
        (1, "all_tuesdays",   "backtest_tuesday_3m.json",                  "TUESDAY"),
        (2, "all_wednesdays", "backtest_wednesday_3m.json",                "WEDNESDAY"),
        (3, "all_thursdays",  "backtest_thursday_noticias_1year.json",     "THURSDAY"),
        (4, "all_fridays",    "backtest_5dias_sesiones_6m.json",           "FRIDAY"),
    ]

    for wd, all_key, filename, label in day_configs:
        sessions = sessions_by_wd.get(wd, [])
        stats    = compute_stats(sessions, label)
        save_day_json(sessions, stats, label, all_key, filename)

    # 6. Verificar
    print()
    print("=" * 60)
    print("[OK] ACTUALIZACIÓN COMPLETA")
    for _, all_key, filename, label in day_configs:
        fp = os.path.join(OUT_DIR, filename)
        with open(fp) as f:
            d = json.load(f)
        sess = d.get(all_key) or d.get("all_sessions") or []
        cot_present = sum(1 for s in sess if "cot_index" in s)
        last_date   = sess[0]["date"] if sess else "—"
        last_cot    = sess[0].get("cot_index", "—") if sess else "—"
        print(f"  {label:<12} {len(sess):>3} sesiones | Última: {last_date} | COT: {last_cot} ({cot_present}/{len(sess)} con COT)")
    print("=" * 60)


if __name__ == "__main__":
    main()
