"""
BACKTEST ULTIMOS 20 LUNES: SHORT apertura NY
Proxy: QQQ (NASDAQ-100 ETF) datos diarios via yfinance
COT: archivo local (rápido)

SHORT = entramos al Open del lunes, salimos al Close del lunes
P&L positivo = precio bajó = SHORT ganó
"""
import yfinance as yf, csv, sys
from datetime import date, timedelta
from statistics import mean
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── COT ────────────────────────────────────────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            cot_rows.append({'date': d, 'lev_net': ll-ls})
        except: pass
cot_rows.sort(key=lambda x: x['date'])
for i, r in enumerate(cot_rows):
    hist = [x['lev_net'] for x in cot_rows[max(0,i-52):i+1]]
    mn,mx = min(hist),max(hist)
    r['ci'] = (r['lev_net']-mn)/(mx-mn)*100 if mx>mn else 50.0

def cot_for(monday_d):
    prev = [r for r in cot_rows if r['date'] <= monday_d - timedelta(days=3)]
    return prev[-1] if prev else None

# ── PRECIO ─────────────────────────────────────────────────────────────────
print("Descargando QQQ...")
qqq = yf.download('QQQ', period='6mo', interval='1d',
                  auto_adjust=True, progress=False)
if hasattr(qqq.columns, 'levels'):
    qqq.columns = qqq.columns.get_level_values(0)

# Solo lunes
lunes = qqq[qqq.index.weekday == 0].copy()
lunes = lunes.tail(20)  # últimos 20

results = []
for idx, row in lunes.iterrows():
    d = idx.date()
    cot = cot_for(d)
    cot_ci = cot['ci'] if cot else 50.0

    mon_open  = float(row['Open'])
    mon_close = float(row['Close'])

    # Friday anterior
    fri_d = d - timedelta(days=3)
    fri_close = None
    for delta in [0,-1,-2]:
        fd = fri_d + timedelta(days=delta)
        ft = qqq[qqq.index.date == fd]
        if not ft.empty:
            fri_close = float(ft['Close'].iloc[-1])
            break

    # Tue siguiente
    tue_d = d + timedelta(days=1)
    tue_close = None
    for delta in [0,1]:
        td2 = tue_d + timedelta(days=delta)
        tt = qqq[qqq.index.date == td2]
        if not tt.empty:
            tue_close = float(tt['Close'].iloc[-1])
            break

    # Monday range
    mon_high = float(row['High'])
    mon_low  = float(row['Low'])

    fri_ret = (mon_open - fri_close)/fri_close*100 if fri_close else None  # gap
    short_ret = (mon_open - mon_close)/mon_open*100   # SHORT lunes
    # Si Short del lunes gana → precio bajó desde open hasta close

    results.append({
        'd'       : d,
        'ci'      : round(cot_ci,1),
        'open'    : round(mon_open,2),
        'close'   : round(mon_close,2),
        'high'    : round(mon_high,2),
        'low'     : round(mon_low,2),
        'gap_pct' : round(fri_ret,2) if fri_ret else 0,
        'short'   : round(short_ret,3),  # + = gané el corto
        'long'    : round(-short_ret,3), # + = gané el largo
        'cot_bear': cot_ci > 75,
    })

n = len(results)
print(f"\n{'='*62}")
print(f"  ÚLTIMOS {n} LUNES — SHORT apert. NY (Open→Close)")
print(f"{'='*62}")
print(f"\n  {'Fecha':<12} {'COT':>6} {'Open':>8} {'Close':>8} {'SHORT%':>8} {'LONG%':>8}  {'':>4}")
print("  "+"-"*56)

total_short = 0
for r in results:
    emoji_s = "✅" if r['short'] > 0 else "❌"
    cot_flag = "🔴" if r['cot_bear'] else "  "
    print(f"  {str(r['d']):<12} {r['ci']:>5.1f}% {r['open']:>8.2f} {r['close']:>8.2f} "
          f"{r['short']:>+7.3f}% {r['long']:>+7.3f}%  {emoji_s}{cot_flag}")
    total_short += r['short']

shorts = [r['short'] for r in results]
longs  = [r['long']  for r in results]
s_pos  = sum(1 for v in shorts if v > 0)
l_pos  = sum(1 for v in longs  if v > 0)

print(f"\n{'='*62}")
print(f"  RESULTADO GLOBAL:")
print(f"  SHORT (venta lunes): {s_pos}/{n} = {s_pos/n*100:.0f}%  "
      f"avg={mean(shorts):+.3f}%  acum={sum(shorts):+.2f}%")
print(f"  LONG  (compra lunes): {l_pos}/{n} = {l_pos/n*100:.0f}%  "
      f"avg={mean(longs):+.3f}%  acum={sum(longs):+.2f}%")

# Solo con COT >75
cot_filter = [r for r in results if r['cot_bear']]
if cot_filter:
    cv = [r['short'] for r in cot_filter]
    cp = sum(1 for v in cv if v > 0)
    print(f"\n  COT>75 🔴 ({len(cot_filter)} lunes):")
    print(f"  SHORT: {cp}/{len(cv)} = {cp/len(cv)*100:.0f}%  "
          f"avg={mean(cv):+.3f}%  acum={sum(cv):+.2f}%")
print(f"{'='*62}\n")
