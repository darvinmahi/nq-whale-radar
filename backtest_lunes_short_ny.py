"""
BACKTEST: SHORT apertura NY del lunes
Condiciones: COT Index >75 + Asia BULL + London BULL

Usa pandas para rapidez. Lee CSV 15m, filtra, calcula sesiones,
cruza con COT y mide P&L del corto.
"""
import pandas as pd
import csv
import sys
from datetime import date, timedelta
from statistics import mean, stdev

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

START = '2025-04-01'

# ── 1. LEER COT (218 rows, instantáneo) ──────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            cot_rows.append({'date': d, 'lev_net': ll - ls})
        except:
            pass
cot_rows.sort(key=lambda x: x['date'])

# COT Index 52 semanas
for i, r in enumerate(cot_rows):
    hist = [x['lev_net'] for x in cot_rows[max(0, i-52):i+1]]
    mn, mx = min(hist), max(hist)
    r['cot_idx'] = (r['lev_net'] - mn) / (mx - mn) * 100 if mx > mn else 50.0

def get_cot_for_monday(monday_date):
    """Retorna el COT publicado el viernes anterior al lunes dado."""
    # COT se publica el viernes, dato es del martes previo
    # Para un lunes dado, el último COT disponible fue el viernes anterior
    prev_fri = monday_date - timedelta(days=3)  # viernes = lunes - 3
    available = [r for r in cot_rows if r['date'] <= prev_fri]
    return available[-1] if available else None

print("📥 Leyendo CSV 15m con pandas...")
df = pd.read_csv('data/research/nq_15m_2024_2026.csv')
df.columns = [c.strip() for c in df.columns]

# Parsear datetime
dt_col = 'Datetime' if 'Datetime' in df.columns else 'datetime'
df['dt'] = pd.to_datetime(df[dt_col].str.replace('+00:00', '', regex=False))
df['date_'] = df['dt'].dt.date
df['hour']  = df['dt'].dt.hour
df['minute'] = df['dt'].dt.minute
df['weekday'] = df['dt'].dt.weekday
df['close'] = pd.to_numeric(df.get('Close', df.get('close', 0)), errors='coerce')
df['open_p'] = pd.to_numeric(df.get('Open', df.get('open', 0)), errors='coerce')
df = df[df['close'] > 0]
df = df[df['dt'] >= pd.Timestamp(START)]
print(f"   {len(df):,} barras desde {START}")

# ── 2. CALCULAR SESIONES POR DÍA ─────────────────────────────────────────
results = []

lunes_dates = df[df['weekday'] == 0]['date_'].unique()

for lunes_d in sorted(lunes_dates):
    lunes_d_dt = pd.Timestamp(lunes_d)
    dom_d = (lunes_d_dt - pd.Timedelta(days=1)).date()

    # COT disponible para este lunes
    cot = get_cot_for_monday(lunes_d)
    if not cot:
        continue
    cot_idx = cot['cot_idx']

    # Sesión ASIA del lunes: domingo >= 22h + lunes < 8h
    dom_df = df[(df['date_'] == dom_d) & (df['hour'] >= 22)]
    mon_asia = df[(df['date_'] == lunes_d) & (df['hour'] < 8)]
    asia_bars = pd.concat([dom_df, mon_asia]).sort_values('dt')

    # Sesión LONDON del lunes: 8h-14h30
    london_bars = df[(df['date_'] == lunes_d) & 
                     ((df['hour'] > 8) | ((df['hour'] == 8) & (df['minute'] >= 0))) &
                     ((df['hour'] < 14) | ((df['hour'] == 14) & (df['minute'] < 30)))]

    # Sesión NY del lunes: 14h30-21h
    ny_bars = df[(df['date_'] == lunes_d) &
                 ((df['hour'] > 14) | ((df['hour'] == 14) & (df['minute'] >= 30))) &
                 (df['hour'] < 21)]

    if len(asia_bars) < 2 or len(london_bars) < 2 or len(ny_bars) < 4:
        continue

    # Retornos de sesión
    asia_ret   = (asia_bars['close'].iloc[-1] - asia_bars['close'].iloc[0]) / asia_bars['close'].iloc[0] * 100
    london_ret = (london_bars['close'].iloc[-1] - london_bars['close'].iloc[0]) / london_bars['close'].iloc[0] * 100
    ny_open_price  = ny_bars['close'].iloc[0]   # primera barra NY ~ apertura
    ny_close_price = ny_bars['close'].iloc[-1]  # última barra NY

    asia_bull   = asia_ret > 0.05
    london_bull = london_ret > 0.05

    # P&L del CORTO: entry = apertura NY, exit = cierre NY
    # Si entramos SHORT: ganamos si precio baja
    short_ret = (ny_open_price - ny_close_price) / ny_open_price * 100  # positivo = ganamos

    results.append({
        'date'       : lunes_d,
        'cot_idx'    : round(cot_idx, 1),
        'asia_ret'   : round(asia_ret, 3),
        'london_ret' : round(london_ret, 3),
        'asia_bull'  : asia_bull,
        'london_bull': london_bull,
        'ny_open'    : round(ny_open_price, 1),
        'ny_close'   : round(ny_close_price, 1),
        'short_ret'  : round(short_ret, 3),  # positivo = corto ganó
    })

n_total = len(results)
print(f"   {n_total} lunes analizados\n")

SEP = '='*60

print(SEP)
print("  BACKTEST: SHORT APERTURA NY LUNES")
print("  Condiciones: COT>75 + Asia BULL + London BULL")
print(SEP)

# ── TODOS LOS LUNES (sin filtro) ─────────────────────────────────────────
all_rets = [r['short_ret'] for r in results]
all_pos  = sum(1 for v in all_rets if v > 0)
print(f"\n📊 SIN FILTRO — SHORT apertura NY cada lunes:")
print(f"   n={n_total}  Win%={all_pos/n_total*100:.0f}%  avg={mean(all_rets):+.3f}%  acum={sum(all_rets):+.2f}%")

# ── FILTRO: COT >75 ────────────────────────────────────────────────────────
cot75 = [r for r in results if r['cot_idx'] > 75]
if cot75:
    v = [r['short_ret'] for r in cot75]
    pos = sum(1 for x in v if x > 0)
    print(f"\n📊 FILTRO COT>75:")
    print(f"   n={len(cot75)}  Win%={pos/len(cot75)*100:.0f}%  avg={mean(v):+.3f}%  acum={sum(v):+.2f}%")

# ── FILTRO: Asia BULL + London BULL ────────────────────────────────────────
ab_lb = [r for r in results if r['asia_bull'] and r['london_bull']]
if ab_lb:
    v = [r['short_ret'] for r in ab_lb]
    pos = sum(1 for x in v if x > 0)
    print(f"\n📊 FILTRO Asia🟢 + London🟢:")
    print(f"   n={len(ab_lb)}  Win%={pos/len(ab_lb)*100:.0f}%  avg={mean(v):+.3f}%  acum={sum(v):+.2f}%")

# ── FILTRO COMPLETO: COT>75 + Asia🟢 + London🟢 ───────────────────────────
setup = [r for r in results if r['cot_idx'] > 75 and r['asia_bull'] and r['london_bull']]
print(f"\n{SEP}")
print(f"  🎯 SETUP COMPLETO: COT>75 + Asia🟢 + London🟢 → SHORT NY")
print(SEP)
if setup:
    v = [r['short_ret'] for r in setup]
    pos = sum(1 for x in v if x > 0)
    neg = sum(1 for x in v if x < 0)
    print(f"\n   n={len(setup)}  ✅ Ganados={pos} ({pos/len(setup)*100:.0f}%)  ❌ Perdidos={neg}")
    print(f"   avg ret: {mean(v):+.3f}%  |  acumulado: {sum(v):+.2f}%")
    print(f"   mejor:   {max(v):+.2f}%  |  peor:      {min(v):+.2f}%")
    print(f"   Profit Factor: {sum(x for x in v if x>0)/abs(sum(x for x in v if x<0) or 1):.2f}")
    print()
    print(f"   {'Fecha':<12} {'COT_Idx':>8} {'Asia':>7} {'London':>8} {'NYopen':>9} {'SHORT%':>8}  {'':>2}")
    print("   " + "-"*58)
    for r in setup:
        emoji = "✅" if r['short_ret'] > 0 else "❌"
        print(f"   {str(r['date']):<12} {r['cot_idx']:>7.1f}% {r['asia_ret']:>+6.2f}% {r['london_ret']:>+7.2f}% "
              f"{r['ny_open']:>9.1f} {r['short_ret']:>+7.3f}%  {emoji}")
else:
    print("   Sin señales con esos filtros en el período")

# ── VARIANTE: COT>60 (más señales) ─────────────────────────────────────────
setup60 = [r for r in results if r['cot_idx'] > 60 and r['asia_bull'] and r['london_bull']]
if setup60:
    v60 = [r['short_ret'] for r in setup60]
    pos60 = sum(1 for x in v60 if x > 0)
    print(f"\n📊 VARIANTE COT>60 + Asia🟢 + London🟢 → SHORT NY:")
    print(f"   n={len(setup60)}  Win%={pos60/len(setup60)*100:.0f}%  avg={mean(v60):+.3f}%  acum={sum(v60):+.2f}%")

print(f"\n{SEP}")
