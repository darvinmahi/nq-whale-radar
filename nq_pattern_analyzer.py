"""
NQ INTELLIGENCE v2 — ANALIZADOR DE ALTA PROBABILIDAD
=====================================================
Búsqueda profunda de patrones con WR > 60%.
Variables: COT direction/consecutivos + VXN levels + DIX proxy + price position
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COT_CSV  = os.path.join(BASE_DIR, "data", "cot", "nasdaq_cot_historical_study.csv")

print("="*65)
print("  NQ INTELLIGENCE v2 — BÚSQUEDA DE EDGE REAL (WR > 60%)")
print("="*65)

# ─── DATOS BASE ─────────────────────────────────────────────────────────────
print("\n📡 Descargando datos (2020–2026 para más muestra)...")

# NDX semanal — más historia = más muestra
ndx_raw = yf.download('^NDX', start='2020-01-01', end='2026-03-14', interval='1wk', progress=False)
vxn_raw = yf.download('^VXN', start='2020-01-01', end='2026-03-14', interval='1wk', progress=False)
spx_raw = yf.download('^GSPC', start='2020-01-01', end='2026-03-14', interval='1wk', progress=False)

for raw in [ndx_raw, vxn_raw, spx_raw]:
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    if raw.index.tz is not None:
        raw.index = raw.index.tz_convert('America/New_York').tz_localize(None)
    raw.index = pd.to_datetime(raw.index).astype('datetime64[us]')

ndx = ndx_raw[['Close', 'Open']].copy()
ndx.columns = ['NDX_Close', 'NDX_Open']
ndx['NDX_Return_Next'] = ndx['NDX_Close'].pct_change().shift(-1) * 100
ndx['NDX_MA20w'] = ndx['NDX_Close'].rolling(20).mean()
ndx['is_above_ma'] = ndx['NDX_Close'] > ndx['NDX_MA20w']
ndx['Date'] = ndx.index

vxn = vxn_raw[['Close']].rename(columns={'Close': 'VXN'})
vxn['VXN_Change'] = vxn['VXN'].pct_change() * 100
vxn['Date'] = vxn.index

spx = spx_raw[['Close']].rename(columns={'Close': 'SPX'})
spx['Date'] = spx.index

print(f"  ✅ NDX: {len(ndx)} semanas | VXN: {len(vxn)} | SPX: {len(spx)}")

# COT
print("\n📋 Cargando COT histórico...")
try:
    cot = pd.read_csv(COT_CSV)
    date_col = 'Report_Date_as_MM_DD_YYYY'
    cot[date_col] = pd.to_datetime(cot[date_col])
    cot = cot.sort_values(date_col).reset_index(drop=True)
    cot['net_position'] = (
        (cot['Asset_Mgr_Positions_Long_All'] - cot['Asset_Mgr_Positions_Short_All']) +
        (cot['Lev_Money_Positions_Long_All'] - cot['Lev_Money_Positions_Short_All'])
    )
    cot['net_change']    = cot['net_position'].diff()
    cot['net_change_2w'] = cot['net_position'].diff(2)   # cambio en 2 semanas
    cot['net_change_3w'] = cot['net_position'].diff(3)   # cambio en 3 semanas

    # COT Index (posición vs rango 52 semanas)
    cot['cot_max52'] = cot['net_position'].rolling(52).max()
    cot['cot_min52'] = cot['net_position'].rolling(52).min()
    cot['cot_index'] = ((cot['net_position'] - cot['cot_min52']) / 
                         (cot['cot_max52'] - cot['cot_min52'] + 1e-9)) * 100

    cot['Date'] = pd.to_datetime(cot[date_col].dt.normalize()).astype('datetime64[us]')
    print(f"  ✅ COT: {len(cot)} semanas. Rango: 2019-2026.")
    cot_ok = True
except Exception as e:
    print(f"  ❌ {e}")
    cot_ok = False

# ─── MERGE ──────────────────────────────────────────────────────────────────
print("\n🔀 Cruzando datasets...")

df = ndx.copy().reset_index(drop=True)
df['Date'] = df['Date'].astype('datetime64[us]')

vxn_c = vxn.reset_index(drop=True)
vxn_c['Date'] = vxn_c['Date'].astype('datetime64[us]')
df = pd.merge_asof(df.sort_values('Date'), vxn_c.sort_values('Date'), on='Date', direction='nearest')

spx_c = spx.reset_index(drop=True)
spx_c['Date'] = spx_c['Date'].astype('datetime64[us]')
df = pd.merge_asof(df.sort_values('Date'), spx_c.sort_values('Date'), on='Date', direction='nearest')

if cot_ok:
    cot_c = cot[['Date','net_position','net_change','net_change_2w','net_change_3w','cot_index']].copy()
    cot_c['Date'] = cot_c['Date'].astype('datetime64[us]')
    df = pd.merge_asof(df.sort_values('Date'), cot_c.sort_values('Date'), on='Date', direction='backward')

df = df.dropna(subset=['NDX_Return_Next', 'VXN', 'NDX_Close']).reset_index(drop=True)
print(f"  ✅ Dataset: {len(df)} semanas con todos los datos.")

# ─── FEATURES ───────────────────────────────────────────────────────────────
print("\n🧪 Calculando variables compuestas...")

# VXN
df['VXN_Level'] = pd.cut(df['VXN'], bins=[0, 18, 25, 999], labels=['BAJO', 'MEDIO', 'ALTO'])
df['VXN_Trend']  = df['VXN_Change'].apply(lambda x: 'SUBIENDO' if x > 5 else ('BAJANDO' if x < -5 else 'ESTABLE'))

# COT
if cot_ok:
    df['COT_DIR']   = df['net_change'].apply(lambda x: 'ACUMULANDO' if x > 0 else 'REDUCIENDO')
    df['COT_2w']    = df['net_change_2w'].apply(lambda x: 'ACUM_2W' if x > 0 else 'REDU_2W')
    df['COT_3w']    = df['net_change_3w'].apply(lambda x: 'ACUM_3W' if x > 0 else 'REDU_3W')
    df['COT_Idx']   = pd.cut(df['cot_index'], bins=[0, 25, 50, 75, 100], labels=['EXTREMO_BAJO','BAJO','ALTO','EXTREMO_ALTO'])
    
    # Semanas consecutivas
    dirs = df['COT_DIR'].tolist()
    consec = []
    c = 1
    for i in range(len(dirs)):
        if i == 0:
            consec.append(1)
            continue
        c = c + 1 if dirs[i] == dirs[i-1] else 1
        consec.append(c)
    df['COT_Consec'] = consec
    df['COT_Consec_Cat'] = df['COT_Consec'].apply(lambda x: '1' if x == 1 else ('2' if x == 2 else '3+'))

# Posición de mercado
df['Trend'] = df['is_above_ma'].apply(lambda x: 'UPTREND' if x else 'DOWNTREND')

# Outcome
df['NDX_Outcome'] = df['NDX_Return_Next'].apply(
    lambda r: 'SUBE' if r > 1.0 else ('BAJA' if r < -1.0 else 'LATERAL')
)

# ─── BÚSQUEDA DE PATRONES HIGH-EDGE ─────────────────────────────────────────
print("\n🔎 Buscando patrones con WR > 60% y muestra > 8 semanas...")

results = []
MIN_SAMPLE = 8
MIN_WR = 60.0

# Definir columnas a combinar (dependiendo si hay COT)
if cot_ok:
    combo_cols = [
        ['COT_DIR', 'VXN_Level', 'Trend'],
        ['COT_2w',  'VXN_Level', 'Trend'],
        ['COT_3w',  'VXN_Level'],
        ['COT_DIR', 'COT_Consec_Cat', 'VXN_Level'],
        ['COT_DIR', 'COT_Consec_Cat', 'Trend'],
        ['COT_Idx', 'VXN_Level'],
        ['COT_Idx', 'Trend'],
        ['COT_Consec_Cat', 'COT_DIR', 'VXN_Level', 'Trend'],
    ]
else:
    combo_cols = [['VXN_Level', 'Trend'], ['VXN_Level']]

for cols in combo_cols:
    for keys, group in df.groupby(cols):
        n = len(group)
        if n < MIN_SAMPLE:
            continue

        if isinstance(keys, str):
            keys = (keys,)

        vc = group['NDX_Outcome'].value_counts()
        dominant = vc.idxmax()
        wr = vc[dominant] / n * 100

        if wr < MIN_WR:
            continue

        avg_ret = group['NDX_Return_Next'].mean()
        max_ret = group['NDX_Return_Next'].max()
        min_ret = group['NDX_Return_Next'].min()
        sharpe_ap = avg_ret / (group['NDX_Return_Next'].std() + 1e-9)

        cond = dict(zip(cols, [str(k) for k in keys]))
        name = " + ".join([f"{k}={v}" for k, v in cond.items()])

        results.append({
            "name": name,
            "conditions": cond,
            "prediction": dominant,
            "count": int(n),
            "win_rate": round(float(wr), 1),
            "avg_return": round(float(avg_ret), 2),
            "max_return": round(float(max_ret), 2),
            "min_return": round(float(min_ret), 2),
            "sharpe_proxy": round(float(sharpe_ap), 2),
        })

# Ordenar por WR descendente
results.sort(key=lambda x: (-x['win_rate'], -x['count']))
for i, r in enumerate(results):
    r['rank'] = i + 1

# ─── MOSTRAR RESULTADOS ──────────────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"  ✅ {len(results)} patrones encontrados con WR ≥ {MIN_WR}%")
print(f"{'='*65}")

if results:
    for p in results[:15]:
        arrow = "📈" if p['prediction'] == 'SUBE' else ("📉" if p['prediction'] == 'BAJA' else "↔️")
        print(f"\n  #{p['rank']} — {p['name']}")
        print(f"      {arrow} {p['prediction']} | WR: {p['win_rate']}% | Muestra: {p['count']} | Ret.Medio: {p['avg_return']:+.2f}%")
        print(f"      Rango: [{p['min_return']:+.2f}% → {p['max_return']:+.2f}%] | Sharpe≈: {p['sharpe_proxy']}")
else:
    print("\n  ⚠️ No se encontraron patrones con esos criterios. Bajando umbral...")

# ─── GUARDAR JSON ────────────────────────────────────────────────────────────
output = {
    "metadata": {
        "generated": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "total_weeks_analyzed": len(df),
        "date_range": "2020-2026",
        "min_sample": MIN_SAMPLE,
        "min_win_rate": MIN_WR,
    },
    "high_edge_patterns": results[:15],
    "total_patterns_found": len(results)
}

out_path = os.path.join(BASE_DIR, "top_patterns.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=4, ensure_ascii=False)

print(f"\n\n✅ Guardado en: top_patterns.json")
print(f"📊 Total semanas analizadas: {len(df)}")
print(f"🏆 Patrones de alta probabilidad: {len(results)}")
