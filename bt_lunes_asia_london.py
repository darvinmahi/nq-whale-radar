"""
BACKTEST: Compra apertura Asia LUNES → cierra al cierre London (14:30 UTC)
Solo lunes, ultimo 1 año. Lee el CSV rapido filtrando solo filas de lunes.
"""
import csv, sys
from datetime import date, timedelta, time as dtime
from statistics import mean
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

START = date(2025, 4, 1)

# Estructura: {date: {'asia_open': precio, 'london_close': precio}}
day_data = {}

fn = 'data/research/nq_15m_2024_2026.csv'
with open(fn, encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for r in reader:
        dt_s = r.get('Datetime', '').replace('+00:00', '').strip()
        if len(dt_s) < 16:
            continue
        d_str = dt_s[:10]
        h = int(dt_s[11:13])
        m = int(dt_s[14:16])

        try:
            d = date.fromisoformat(d_str)
        except:
            continue

        if d < START:
            continue

        # Solo lunes (weekday 0) y domingo (6) para apertura Asia
        wd = d.weekday()

        c = float(r.get('Close') or 0)
        o = float(r.get('Open') or 0)
        if c == 0:
            continue

        # Asia apertura lunes = domingo >= 22:00 o lunes < 08:00
        if wd == 6 and h >= 22:
            # domingo nocturno -> trading_date = lunes
            lunes_d = d + timedelta(days=1)
            if lunes_d < START:
                continue
            if lunes_d not in day_data:
                day_data[lunes_d] = {}
            if 'asia_open' not in day_data[lunes_d]:
                day_data[lunes_d]['asia_open'] = o if o > 0 else c

        elif wd == 0:
            # Lunes
            if d not in day_data:
                day_data[d] = {}

            # Asia (00:00-08:00)
            if h < 8:
                if 'asia_open' not in day_data[d]:
                    day_data[d]['asia_open'] = o if o > 0 else c

            # London close = ultima barra antes de 14:30
            if 8 <= h < 14 or (h == 14 and m < 30):
                day_data[d]['london_close'] = c

# Calcular resultados
results = []
for d in sorted(day_data.keys()):
    row = day_data[d]
    entry = row.get('asia_open')
    close = row.get('london_close')
    if not entry or not close:
        continue
    ret = (close - entry) / entry * 100
    results.append({'date': d, 'entry': entry, 'close': close, 'ret': ret})

n = len(results)
if n == 0:
    print("Sin datos suficientes")
    exit()

pos  = sum(1 for r in results if r['ret'] > 0)
neg  = sum(1 for r in results if r['ret'] < 0)
rets = [r['ret'] for r in results]

print(f"BACKTEST: Compra apertura Asia LUNES → cierra London (14:30 UTC)")
print(f"Período: {results[0]['date']} → {results[-1]['date']}  ({n} lunes)\n")
print(f"  ✅ Positivos: {pos}/{n} = {pos/n*100:.0f}%")
print(f"  ❌ Negativos: {neg}/{n} = {neg/n*100:.0f}%")
print(f"  📊 Avg ret:   {mean(rets):+.3f}%")
print(f"  🏆 Mejor:     {max(rets):+.2f}%")
print(f"  💀 Peor:      {min(rets):+.2f}%")
print(f"  💰 Acumulado: {sum(rets):+.2f}%")
print()
print(f"  {'Fecha':<12} {'Entry':>9} {'London cl.':>11} {'Ret':>8}  {'':>2}")
print("  " + "-"*46)
for r in results:
    emoji = "✅" if r['ret'] > 0 else "❌"
    print(f"  {str(r['date']):<12} {r['entry']:>9.1f} {r['close']:>11.1f} {r['ret']:>+7.3f}%  {emoji}")
