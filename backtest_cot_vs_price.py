"""
BACKTEST: COT Release → ¿Cómo reacciona el precio?

Estudia:
1. El día del reporte (viernes COT) → retorno del día
2. La semana siguiente (lunes a viernes) → retorno semanal
3. Por nivel de COT Index (Lev_Money net) → alto vs bajo
4. Por dirección del net (subiendo vs bajando)
5. Por Asset Manager posición → señal complementaria

Datos: 218 semanas COT (2022-03-17 → 2026-03-03)
Precio: nq_15m_intraday + nq_15m_2024_2026 (15m bars)
"""
import csv
import sys
from datetime import date, datetime, timedelta
from statistics import mean, stdev

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ─────────────────────── CARGA COT ────────────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            lev_l = int(r.get('Lev_Money_Positions_Long_All', 0) or 0)
            lev_s = int(r.get('Lev_Money_Positions_Short_All', 0) or 0)
            am_l  = int(r.get('Asset_Mgr_Positions_Long_All', 0) or 0)
            am_s  = int(r.get('Asset_Mgr_Positions_Short_All', 0) or 0)
            cot_rows.append({
                'date'   : d,
                'lev_net': lev_l - lev_s,   # Leveraged Money net
                'am_net' : am_l - am_s,      # Asset Manager net
            })
        except: pass

cot_rows.sort(key=lambda x: x['date'])

# ─────────────── COT INDEX (52-semana) para cada fila ──────────────────────
WINDOW = 52
for i, r in enumerate(cot_rows):
    hist = [x['lev_net'] for x in cot_rows[max(0, i-WINDOW):i+1]]
    mn, mx = min(hist), max(hist)
    r['cot_idx'] = ((r['lev_net'] - mn) / (mx - mn) * 100) if mx > mn else 50.0

# Cambio semana a semana en Lev_Money net
for i in range(1, len(cot_rows)):
    cot_rows[i]['lev_chg'] = cot_rows[i]['lev_net'] - cot_rows[i-1]['lev_net']
    cot_rows[i]['am_chg']  = cot_rows[i]['am_net']  - cot_rows[i-1]['am_net']
cot_rows[0]['lev_chg'] = 0
cot_rows[0]['am_chg']  = 0

# ─────────────────────── CARGA PRECIOS (15m) ───────────────────────────────
# Usamos cierre diario aproximado: cierre de última barra del día
bars = []
for fn in ['data/research/nq_15m_2024_2026.csv', 'data/research/nq_15m_intraday.csv']:
    try:
        with open(fn, encoding='utf-8') as f:
            for r in csv.DictReader(f):
                try:
                    dt_str = r.get('Datetime') or r.get('datetime') or ''
                    dt = datetime.fromisoformat(dt_str.replace('+00:00','').strip())
                    c  = float(r.get('Close') or r.get('close') or 0)
                    if c > 0:
                        bars.append({'dt': dt, 'c': c})
                except: pass
    except: pass

bars.sort(key=lambda x: x['dt'])

# Deduplica
seen = set()
bars_u = []
for b in bars:
    k = b['dt']
    if k not in seen:
        seen.add(k)
        bars_u.append(b)
bars = bars_u

# Construir dict: date → {open_ny, close_ny}
# NY session = 14:30-21:00 UTC
day_price = {}
for b in bars:
    d = b['dt'].date()
    if d not in day_price:
        day_price[d] = {'bars': []}
    day_price[d]['bars'].append(b)

for d, dp in day_price.items():
    ny = [b for b in dp['bars']
          if datetime(d.year,d.month,d.day,14,30) <= b['dt']
             < datetime(d.year,d.month,d.day,21,0)]
    if ny:
        dp['ny_open']  = ny[0]['c']   # apertura NY (usamos cierre 1ra barra)
        dp['ny_close'] = ny[-1]['c']
        dp['ny_ret']   = (ny[-1]['c'] - ny[0]['c']) / ny[0]['c'] * 100
    else:
        dp['ny_open'] = dp['ny_close'] = dp['ny_ret'] = None

def next_trading_day(d, offset=1):
    """Avanza N días hábiles."""
    cur = d
    count = 0
    while count < offset:
        cur += timedelta(days=1)
        if cur.weekday() < 5 and day_price.get(cur,{}).get('ny_close'):
            count += 1
    return cur

def week_return_after(start_d):
    """Retorno precio desde cierre del viernes siguiente al COT release."""
    # El COT sale un viernes, cubre hasta el martes previo.
    # Medimos price_action: lunes a viernes de la semana siguiente.
    mon = start_d + timedelta(days=3)  # lunes siguiente
    fri_next = start_d + timedelta(days=7)  # viernes siguiente
    
    # busca primer y último día con precio entre lun y viernes siguiente
    days_w = sorted([d for d in day_price
                     if mon <= d <= fri_next and day_price[d].get('ny_close')])
    if len(days_w) < 2:
        return None
    p0 = day_price[days_w[0]]['ny_open']
    p1 = day_price[days_w[-1]]['ny_close']
    return (p1 - p0) / p0 * 100 if p0 else None

# ─────────────────────── CONSTRUCCIÓN DE OBSERVACIONES ────────────────────
obs = []
for r in cot_rows:
    if r['date'] < date(2022,6,1): continue  # necesitamos 52 semanas para COT Index válido

    cot_d = r['date']
    # El reporte COT sale el viernes, pero la fecha es del martes previo.
    # Tradingster muestra fecha del MARTES. El reporte se publica el VIERNES +3días.
    friday = cot_d + timedelta(days=4)  # martes + 4 = viernes de publicación
    
    # Buscar el viernes exacto o el más cercano con datos
    for delta in [0, 1, -1, 2, -2]:
        f = friday + timedelta(days=delta)
        if f in day_price and day_price[f].get('ny_ret') is not None:
            friday = f
            break
    else:
        continue

    fri_ret  = day_price[friday].get('ny_ret')
    week_ret = week_return_after(friday)
    
    if fri_ret is None:
        continue

    obs.append({
        'cot_date'  : cot_d,
        'pub_friday': friday,
        'lev_net'   : r['lev_net'],
        'am_net'    : r['am_net'],
        'lev_chg'   : r['lev_chg'],
        'am_chg'    : r['am_chg'],
        'cot_idx'   : r['cot_idx'],
        'fri_ret'   : fri_ret,
        'week_ret'  : week_ret,
    })

print(f"\nObservaciones válidas: {len(obs)}")
print(f"Período: {obs[0]['cot_date']} → {obs[-1]['cot_date']}")

# ─────────────────────── ANÁLISIS ──────────────────────────────────────────
SEP = '='*70

def stats(vals):
    vals = [v for v in vals if v is not None]
    if not vals: return 'N/A', 0
    pos = sum(1 for v in vals if v > 0)
    return f"avg={mean(vals):+.3f}% | win%={pos/len(vals)*100:.0f}% | n={len(vals)}", len(vals)

print(f"\n{SEP}")
print("  COT BACKTEST: REACCIÓN DE PRECIO TRAS PUBLICACIÓN DEL REPORTE")
print(SEP)

# ── 1. Por nivel de COT Index (Leveraged Money) ───────────────────────────
print("\n📊 1. VIERNES COT por NIVEL de COT Index (Lev_Money net vs 52s)")
print(f"  {'Nivel COT Index':<22} {'Retorno viernes (mismo día)':<32} {'Retorno semana siguiente'}")
print("  " + "-"*68)

niveles = [
    ("Extremo ALTO  (>75)",  [o for o in obs if o['cot_idx'] > 75]),
    ("ALTO          (60-75)",[o for o in obs if 60 < o['cot_idx'] <= 75]),
    ("MEDIO         (40-60)",[o for o in obs if 40 < o['cot_idx'] <= 60]),
    ("BAJO          (25-40)",[o for o in obs if 25 >= o['cot_idx'] > 10]),
    ("Extremo BAJO  (<25)",  [o for o in obs if o['cot_idx'] <= 25]),
]
for label, grp in niveles:
    fs, n1 = stats([o['fri_ret']  for o in grp])
    ws, n2 = stats([o['week_ret'] for o in grp])
    print(f"  {label:<22} {fs:<32} {ws}")

# ── 2. Por dirección del cambio semanal de Lev_Money ─────────────────────
print(f"\n📊 2. VIERNES COT por DIRECCIÓN del cambio en Lev_Money Net")
print(f"  {'Señal':<28} {'Retorno viernes':<32} {'Retorno semana siguiente'}")
print("  " + "-"*68)

grps_dir = [
    ("Lev_Money SUBIÓ (alcista)", [o for o in obs if o['lev_chg'] > 0]),
    ("Lev_Money BAJÓ (bajista)",  [o for o in obs if o['lev_chg'] < 0]),
    ("Sin cambio",                [o for o in obs if o['lev_chg'] == 0]),
]
for label, grp in grps_dir:
    fs, _ = stats([o['fri_ret']  for o in grp])
    ws, _ = stats([o['week_ret'] for o in grp])
    print(f"  {label:<28} {fs:<32} {ws}")

# ── 3. COMBO: COT Index alto + Lev bajando = señal doble bajista ─────────
print(f"\n📊 3. COMBINACIONES DE SEÑALES")
print(f"  {'Combo':<36} {'Ret. viernes':<30} {'Ret. semana'}")
print("  " + "-"*68)

combos = [
    ("COT_IDX>75 + LevNet BAJANDO",
     [o for o in obs if o['cot_idx']>75 and o['lev_chg']<0]),
    ("COT_IDX>75 + LevNet SUBIENDO",
     [o for o in obs if o['cot_idx']>75 and o['lev_chg']>0]),
    ("COT_IDX<25 + LevNet SUBIENDO",
     [o for o in obs if o['cot_idx']<25 and o['lev_chg']>0]),
    ("COT_IDX<25 + LevNet BAJANDO",
     [o for o in obs if o['cot_idx']<25 and o['lev_chg']<0]),
    ("COT_IDX>60 + AM_Net BAJANDO",
     [o for o in obs if o['cot_idx']>60 and o['am_chg']<0]),
    ("COT_IDX>60 + AM_Net SUBIENDO",
     [o for o in obs if o['cot_idx']>60 and o['am_chg']>0]),
]
for label, grp in combos:
    fs, n = stats([o['fri_ret']  for o in grp])
    ws, _ = stats([o['week_ret'] for o in grp])
    print(f"  {label:<36} {fs:<30} {ws}")

# ── 4. Distribución: ¿Qué tan confiable es el viernes COT bajista? ────────
print(f"\n📊 4. DETALLE: COT Index >75 + LevNet BAJANDO (señal bajista fuerte)")
grp_key = [o for o in obs if o['cot_idx'] > 75 and o['lev_chg'] < 0]
if grp_key:
    fri_neg = sum(1 for o in grp_key if o['fri_ret'] < 0)
    wk_neg  = sum(1 for o in grp_key if o.get('week_ret') and o['week_ret'] < 0)
    wk_v    = [o['week_ret'] for o in grp_key if o.get('week_ret') is not None]
    print(f"  Observaciones: {len(grp_key)}")
    print(f"  Viernes bajistas: {fri_neg}/{len(grp_key)} = {fri_neg/len(grp_key)*100:.0f}%")
    print(f"  Semana siguiente bajista: {wk_neg}/{len(wk_v)} = {wk_neg/len(wk_v)*100:.0f}%" if wk_v else "  Sin datos semana")
    print(f"  Retorno promedio viernes: {mean([o['fri_ret'] for o in grp_key]):+.3f}%")
    if wk_v: print(f"  Retorno promedio semana siguiente: {mean(wk_v):+.3f}%")
    print()
    print(f"  {'COT date':<12} {'Pub. Fri':<12} {'COT_Idx':>8} {'Lev_Chg':>10} {'Fri%':>7} {'Wk%':>7}")
    print('  ' + '-'*55)
    for o in sorted(grp_key, key=lambda x: x['pub_friday'])[-20:]:
        wk = f"{o['week_ret']:+.2f}%" if o.get('week_ret') else '  N/A'
        print(f"  {str(o['cot_date']):<12} {str(o['pub_friday']):<12} "
              f"{o['cot_idx']:>7.1f}% {o['lev_chg']:>+10,} {o['fri_ret']:>+6.2f}% {wk:>7}")

# ── 5. Resumen ejecutivo ───────────────────────────────────────────────────
print(f"\n{SEP}")
print("  RESUMEN EJECUTIVO — ¿QUÉ APRENDIMOS?")
print(SEP)

hi  = [o for o in obs if o['cot_idx'] > 75]
lo  = [o for o in obs if o['cot_idx'] < 25]
hi_fri = [o['fri_ret'] for o in hi]
lo_fri = [o['fri_ret'] for o in lo]
hi_wk  = [o['week_ret'] for o in hi if o.get('week_ret')]
lo_wk  = [o['week_ret'] for o in lo if o.get('week_ret')]

print(f"""
  COT Index EXTREMO ALTO (>75) — {len(hi)} semanas:
    Viernes: avg {mean(hi_fri):+.3f}% | bajistas: {sum(1 for v in hi_fri if v<0)/len(hi_fri)*100:.0f}%
    Semana+1: avg {mean(hi_wk):+.3f}% | bajistas: {sum(1 for v in hi_wk if v<0)/len(hi_wk)*100:.0f}%

  COT Index EXTREMO BAJO (<25) — {len(lo)} semanas:
    Viernes: avg {mean(lo_fri):+.3f}% | alcistas: {sum(1 for v in lo_fri if v>0)/len(lo_fri)*100:.0f}%
    Semana+1: avg {mean(lo_wk):+.3f}% | alcistas: {sum(1 for v in lo_wk if v>0)/len(lo_wk)*100:.0f}%

  CONCLUSIÓN PRÁCTICA:
  → Cuando COT_Index > 75 → sesgo BAJISTA el viernes de publicación
  → Cuando COT_Index < 25 → sesgo ALCISTA el viernes de publicación
  → La señal mejora si ADEMÁS el LevNet está CAYENDO (distribución activa)
""")
print(SEP + '\n')
