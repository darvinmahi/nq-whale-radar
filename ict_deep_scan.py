"""
ICT DEEP SCAN — Búsqueda de condiciones con WR ≥ 70%
======================================================
Analiza el ICT básico (Asia sweep por Londres → NY reversa)
pero segmenta por múltiples filtros para encontrar el edge real:

- Día de la semana (Lunes es distinto a Viernes)
- Tamaño del sweep de Londres (pequeño vs grande)
- Dirección del sweep vs tendencia semanal
- Hora de apertura NY respecto al rango
- Combinaciones de los anteriores

Output: tabla completa ordenada por WR y mapa de prioridades.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DAYS = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes"}

print("="*65)
print("  ICT DEEP SCAN — Buscando condiciones WR ≥ 70%")
print("  Segmentación por día, sweep, tendencia y más")
print("="*65)

# ─── DATOS ──────────────────────────────────────────────────────────────────
print("\n📡 Descargando NQ=F horario (2 años)...")
raw = yf.download("NQ=F", period="2y", interval="1h", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')
raw['hour']    = raw.index.hour
raw['date']    = raw.index.date
raw['weekday'] = raw.index.dayofweek  # 0=Lunes
print(f"  ✅ {len(raw)} velas cargadas.")

# Tendencia semanal: MA5 días del NDX cierre diario
ndx_d = yf.download("NQ=F", period="2y", interval="1d", progress=False)
if isinstance(ndx_d.columns, pd.MultiIndex):
    ndx_d.columns = ndx_d.columns.get_level_values(0)
ndx_d.index = pd.to_datetime(ndx_d.index)
if ndx_d.index.tz is None:
    ndx_d.index = ndx_d.index.tz_localize('UTC')
ndx_d.index = ndx_d.index.tz_convert('America/New_York')
ndx_d['MA10'] = ndx_d['Close'].rolling(10).mean()
ndx_d['trend_weekly'] = (ndx_d['Close'] > ndx_d['MA10']).astype(int)
ndx_d['date'] = ndx_d.index.date

trend_map = ndx_d.set_index('date')['trend_weekly'].to_dict()

# ─── CONSTRUIR DATASET POR DÍA ──────────────────────────────────────────────
print("\n🔨 Construyendo features por sesión...")

records = []
for d in sorted(raw['date'].unique()):
    day = raw[raw['date'] == d]
    wd  = int(day['weekday'].iloc[0]) if not day.empty else -1
    if wd not in DAYS:
        continue

    asia   = day[day['hour'].between(0, 3)]
    london = day[day['hour'].between(4, 8)]
    ny     = day[day['hour'].between(9, 11)]

    if asia.empty or london.empty or ny.empty:
        continue

    asia_hi  = float(asia['High'].max())
    asia_lo  = float(asia['Low'].min())
    asia_rng = asia_hi - asia_lo
    if asia_rng < 10:
        continue

    lon_hi = float(london['High'].max())
    lon_lo = float(london['Low'].min())

    swept_lo = lon_lo < asia_lo
    swept_hi = lon_hi > asia_hi

    # Solo un sweep limpio
    if swept_lo == swept_hi:
        continue

    # Tamaño del sweep en % del rango de Asia
    if swept_lo:
        sweep_size = (asia_lo - lon_lo) / asia_rng
        direction  = "BUY"
        entry      = asia_lo
        target     = asia_hi
        stop       = lon_lo - (asia_lo - lon_lo) * 0.3
    else:
        sweep_size = (lon_hi - asia_hi) / asia_rng
        direction  = "SELL"
        entry      = asia_hi
        target     = asia_lo
        stop       = lon_hi + (lon_hi - asia_hi) * 0.3

    # Categorizar sweep
    if sweep_size < 0.15:
        sweep_cat = "PEQUEÑO(<15%)"
    elif sweep_size < 0.40:
        sweep_cat = "MEDIO(15-40%)"
    else:
        sweep_cat = "GRANDE(>40%)"

    # Tendencia semanal
    trend = trend_map.get(d, 0)
    trend_str = "UPTREND" if trend == 1 else "DOWNTREND"

    # Posición de apertura NY respecto al rango Asia
    ny_open = float(ny.iloc[0]['Open'])
    if ny_open > asia_hi:
        ny_pos = "ENCIMA"
    elif ny_open < asia_lo:
        ny_pos = "DEBAJO"
    else:
        ny_pos = "DENTRO"

    # ¿El setup va a favor de la tendencia?
    with_trend = (direction == "BUY" and trend == 1) or (direction == "SELL" and trend == 0)

    # Simular trade
    ny_bars = ny.reset_index(drop=True)
    result  = "FLAT"
    exit_p  = float(ny_bars.iloc[-1]['Close'])
    pnl     = 0.0

    for _, bar in ny_bars.iterrows():
        lo_b = float(bar['Low'])
        hi_b = float(bar['High'])

        if direction == "BUY":
            if lo_b <= stop:
                result = "LOSS"; exit_p = stop; break
            if hi_b >= entry:   # precio llega a la zona de entrada
                # desde aquí monitorear
                pass
            if hi_b >= target:
                result = "WIN"; exit_p = target; break
        else:
            if hi_b >= stop:
                result = "LOSS"; exit_p = stop; break
            if lo_b <= target:
                result = "WIN"; exit_p = target; break

    pnl = (exit_p - entry) if direction == "BUY" else (entry - exit_p)

    records.append({
        "date":       str(d),
        "weekday":    wd,
        "day_name":   DAYS[wd],
        "direction":  direction,
        "sweep_cat":  sweep_cat,
        "sweep_size": round(sweep_size, 3),
        "trend":      trend_str,
        "ny_pos":     ny_pos,
        "with_trend": with_trend,
        "asia_rng":   round(asia_rng, 1),
        "result":     result,
        "pnl_pts":    round(pnl, 2),
    })

df = pd.DataFrame(records)
print(f"  ✅ {len(df)} setups con datos completos.")

# ─── ANÁLISIS SEGMENTADO ─────────────────────────────────────────────────────

def wr_stats(sub):
    closed = sub[sub['result'].isin(['WIN', 'LOSS'])]
    if len(closed) < 5:
        return None
    wins = len(closed[closed['result'] == 'WIN'])
    n    = len(closed)
    wr   = wins / n * 100
    avg  = closed['pnl_pts'].mean()
    return {"n": n, "wr": round(wr, 1), "avg_pnl": round(avg, 1)}

results = []

# Segmentar por múltiples combinaciones
segments = [
    ["day_name"],
    ["direction"],
    ["sweep_cat"],
    ["trend"],
    ["with_trend"],
    ["ny_pos"],
    ["day_name", "direction"],
    ["day_name", "sweep_cat"],
    ["day_name", "trend"],
    ["direction", "sweep_cat"],
    ["direction", "trend"],
    ["direction", "with_trend"],
    ["sweep_cat", "trend"],
    ["sweep_cat", "with_trend"],
    ["day_name", "direction", "sweep_cat"],
    ["day_name", "direction", "trend"],
    ["direction", "sweep_cat", "trend"],
    ["day_name", "direction", "sweep_cat", "trend"],
]

for seg in segments:
    for keys, group in df.groupby(seg):
        st = wr_stats(group)
        if st is None:
            continue
        if isinstance(keys, str):
            keys = (keys,)
        label = " | ".join([f"{k}={v}" for k, v in zip(seg, keys)])
        results.append({
            "label":     label,
            "segment":   seg,
            "keys":      dict(zip(seg, [str(k) for k in keys])),
            "n":         st["n"],
            "wr":        st["wr"],
            "avg_pnl":   st["avg_pnl"],
        })

results.sort(key=lambda x: (-x['wr'], -x['n']))

# ─── MOSTRAR RESULTADOS ──────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  🎯 PATRONES CON WR ≥ 65% (mínimo 5 trades)")
print(f"{'='*65}")

high_edge = [r for r in results if r['wr'] >= 65.0]

if not high_edge:
    print("\n  ⚠️ Ningún segmento alcanza 65%+ WR.")
    high_edge = results[:15]
    print("  Mostrando los 15 mejores de todos modos:\n")

for r in high_edge[:20]:
    arrow = "📈" if "BUY" in r['label'] or "UPTREND" in r['label'] else "📉"
    print(f"\n  [{r['wr']}% WR | n={r['n']:3d}] {r['label']}")
    print(f"    {arrow} Avg PnL: {r['avg_pnl']:+.0f} pts NQ")

# ─── TABLA POR DÍA DE LA SEMANA ─────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  📅 WIN RATE POR DÍA DE LA SEMANA")
print(f"{'='*65}")
print(f"  {'Día':<12} {'Total':>6} {'BUY WR':>8} {'SELL WR':>8} {'WR Global':>10}")
print("  " + "-"*48)
for day_n in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]:
    sub  = df[df['day_name'] == day_n]
    buy  = sub[sub['direction'] == 'BUY']
    sell = sub[sub['direction'] == 'SELL']

    def day_wr(s):
        c = s[s['result'].isin(['WIN','LOSS'])]
        return f"{len(c[c['result']=='WIN'])/len(c)*100:.0f}%" if len(c) > 0 else "N/A"

    st_all = wr_stats(sub)
    wr_g   = f"{st_all['wr']:.0f}%" if st_all else "N/A"
    print(f"  {day_n:<12} {len(sub):>6} {day_wr(buy):>8} {day_wr(sell):>8} {wr_g:>10}")

# ─── TABLA POR DIRECCIÓN + TENDENCIA ────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  🧭 DIRECCIÓN VS TENDENCIA (A favor o En contra)")
print(f"{'='*65}")
for wt in [True, False]:
    label = "✅ A FAVOR de tendencia" if wt else "❌ EN CONTRA de tendencia"
    sub   = df[df['with_trend'] == wt]
    st    = wr_stats(sub)
    if st:
        print(f"\n  {label}")
        print(f"    WR: {st['wr']}% | Trades: {st['n']} | Avg PnL: {st['avg_pnl']:+.0f} pts")

# ─── GUARDAR ────────────────────────────────────────────────────────────────
output = {
    "top_patterns": high_edge[:20],
    "all_patterns": results,
    "total_setups": len(df),
}
with open(os.path.join(BASE_DIR, "ict_deep_scan.json"), "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

df.to_csv(os.path.join(BASE_DIR, "ict_pure_trades.csv"), index=False)
print(f"\n\n✅ Guardado: ict_deep_scan.json  |  ict_pure_trades.csv")
print(f"📊 Total setups analizados: {len(df)}")
