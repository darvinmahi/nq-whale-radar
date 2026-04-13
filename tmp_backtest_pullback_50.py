"""
backtest_pullback_50.py
Estrategia: Primera vela 5min NY → esperar retroceso al 50% del cuerpo → entrada
- Dirección: cierre primera vela > apertura → LONG | < apertura → SHORT
- Midpoint entry: (open + close) / 2
- SL: bajo del low de la vela (LONG) / arriba del high (SHORT) + pequeño buffer
- TP: 2R desde el midpoint
- Si el precio NO retrocede al mid en las primeras 2 horas → sin trade
- Cierre al fin de sesión si no tocó TP ni SL
"""
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings('ignore')

# ── PARÁMETROS ────────────────────────────────────────────────────────
TICKER       = "QQQ"     # NQ proxy
PERIOD       = "60d"
INTERVAL     = "5m"
TP_RATIO     = 2.0       # 1:2
SL_BUFFER    = 0.05      # buffer extra en $ debajo/encima del extremo de vela
PULL_WINDOW  = 24        # barras máx para esperar el retroceso (24 × 5min = 2h)
FILTER_VXN   = False     # poner True para filtrar por VXN > 20 (requiere datos)

print(f"Descargando {TICKER} 5min...")
df_raw = yf.download(TICKER, period=PERIOD, interval=INTERVAL, auto_adjust=True, progress=False)

def col(df, c):
    return df[c].iloc[:,0] if isinstance(df.columns, pd.MultiIndex) else df[c]

df = pd.DataFrame({
    'open':  col(df_raw,'Open'),
    'high':  col(df_raw,'High'),
    'low':   col(df_raw,'Low'),
    'close': col(df_raw,'Close'),
}).dropna()

if df.index.tz is None:
    df.index = df.index.tz_localize('UTC').tz_convert('America/New_York')
else:
    df.index = df.index.tz_convert('America/New_York')

df = df[df.index.dayofweek < 5]
print(f"  → {len(df)} barras NY, {df.index.date[0]} → {df.index.date[-1]}")

# ── BACKTEST ──────────────────────────────────────────────────────────
trades    = []
no_trades = []   # días donde el precio nunca volvió al mid

trading_days = sorted(set(df.index.date))

for day in trading_days:
    day_bars = df[df.index.date == day]

    # Primera vela 9:30
    open_bar = day_bars[
        (day_bars.index.time >= pd.Timestamp('09:30').time()) &
        (day_bars.index.time <  pd.Timestamp('09:35').time())
    ]
    if len(open_bar) == 0:
        continue

    ob         = open_bar.iloc[0]
    o          = float(ob['open'])
    c_price    = float(ob['close'])
    h          = float(ob['high'])
    l          = float(ob['low'])
    body_size  = abs(c_price - o)
    candle_range = h - l

    if body_size < 0.05:   # doji → skip
        continue

    # Dirección y niveles
    if c_price > o:
        direction = 'LONG'
        mid_entry = (o + c_price) / 2     # 50% del cuerpo → zona de pullback
        sl_price  = l - SL_BUFFER         # SL debajo del low
        risk      = mid_entry - sl_price  # distancia entry→SL
        tp_price  = mid_entry + risk * TP_RATIO
    else:
        direction = 'SHORT'
        mid_entry = (o + c_price) / 2     # 50% del cuerpo → zona de pullback
        sl_price  = h + SL_BUFFER         # SL encima del high
        risk      = sl_price - mid_entry
        tp_price  = mid_entry - risk * TP_RATIO

    if risk <= 0.01:
        continue

    # Barras restantes de sesión (después de la primera vela)
    rest = day_bars[day_bars.index >= open_bar.index[0] + pd.Timedelta(minutes=5)]
    session_bars = rest[rest.index.time <= pd.Timestamp('15:59').time()]

    if len(session_bars) == 0:
        continue

    # ── Fase 1: Esperar retroceso al midpoint (máx PULL_WINDOW barras) ──
    entry_idx     = None
    entry_bar_obj = None
    pull_bars     = session_bars.iloc[:PULL_WINDOW]

    for idx, (ts, bar) in enumerate(pull_bars.iterrows()):
        bh = float(bar['high']); bl = float(bar['low'])
        if direction == 'LONG'  and bl <= mid_entry:
            entry_idx = idx; entry_bar_obj = (ts, bar); break
        if direction == 'SHORT' and bh >= mid_entry:
            entry_idx = idx; entry_bar_obj = (ts, bar); break

    if entry_idx is None:
        no_trades.append({'date': str(day), 'direction': direction,
                          'body': round(body_size,2)})
        continue   # nunca retrocedió → no trade

    # ── Fase 2: Simular desde la barra de entrada en adelante ──
    entry_ts, _ = entry_bar_obj
    after_entry = session_bars[session_bars.index >= entry_ts]

    result     = 'TIMEOUT'
    exit_price = None

    for ts2, bar2 in after_entry.iterrows():
        bh2 = float(bar2['high']); bl2 = float(bar2['low']); bc2 = float(bar2['close'])

        if direction == 'LONG':
            if bl2 <= sl_price:
                result = 'SL';  exit_price = sl_price; break
            if bh2 >= tp_price:
                result = 'TP';  exit_price = tp_price; break
        else:
            if bh2 >= sl_price:
                result = 'SL';  exit_price = sl_price; break
            if bl2 <= tp_price:
                result = 'TP';  exit_price = tp_price; break

    if exit_price is None:
        # Timeout: cerrar al close de la última barra
        exit_price = float(after_entry.iloc[-1]['close'])

    pts = round((exit_price - mid_entry) if direction=='LONG' else (mid_entry - exit_price), 2)
    win = pts > 0

    trades.append({
        'date':       str(day),
        'direction':  direction,
        'body_size':  round(body_size, 2),
        'candle_rng': round(candle_range, 2),
        'mid_entry':  round(mid_entry, 2),
        'sl':         round(sl_price, 2),
        'tp':         round(tp_price, 2),
        'exit':       round(exit_price, 2),
        'risk':       round(risk, 2),
        'pts':        pts,
        'result':     result,
        'win':        win,
        'pull_bars':  entry_idx + 1,   # cuántas barras tardó en llegar al mid
    })

# ── STATS ─────────────────────────────────────────────────────────────
total = len(trades)
print(f"\n  Días analizados: {len(trading_days)}")
print(f"  Trades (mid tocado): {total}  |  Sin trade (no retroceso): {len(no_trades)}")

if total == 0:
    print("Sin trades suficientes.")
    exit()

wins   = [t for t in trades if t['win']]
losses = [t for t in trades if not t['win']]
tp_h   = [t for t in trades if t['result']=='TP']
sl_h   = [t for t in trades if t['result']=='SL']
tout   = [t for t in trades if t['result']=='TIMEOUT']

wr        = len(wins)/total*100
total_pts = sum(t['pts'] for t in trades)
avg_win   = sum(t['pts'] for t in wins)/len(wins)   if wins   else 0
avg_loss  = sum(t['pts'] for t in losses)/len(losses) if losses else 0
expectancy = wr/100 * avg_win + (1-wr/100) * avg_loss

print()
print("═"*60)
print(f"  ENTRADA RETROCESO 50% — {total} trades")
print("═"*60)
print(f"  Winrate:              {wr:.1f}%")
print(f"  Expectancy/trade:     {expectancy:+.2f} pts")
print(f"  Total pts:            {total_pts:+.1f}")
print(f"  Avg WIN:              {avg_win:+.2f} pts  ({len(wins)} trades)")
print(f"  Avg LOSS:             {avg_loss:+.2f} pts  ({len(losses)} trades)")
print(f"  TP:   {len(tp_h)} ({len(tp_h)/total*100:.0f}%)  |  "
      f"SL: {len(sl_h)} ({len(sl_h)/total*100:.0f}%)  |  "
      f"Timeout: {len(tout)} ({len(tout)/total*100:.0f}%)")

# Segmentación por tamaño de vela
def seg_stats(sub, label):
    if not sub: return f"  {label}: 0 trades"
    wr_s = sum(1 for t in sub if t['win'])/len(sub)*100
    avg  = sum(t['pts'] for t in sub)/len(sub)
    return f"  {label}: {len(sub)} trades  WR={wr_s:.0f}%  avg={avg:+.2f}pts"

big_body   = [t for t in trades if t['body_size'] >= 0.5]
small_body = [t for t in trades if t['body_size'] <  0.3]
fast_pull  = [t for t in trades if t['pull_bars'] <= 4]   # retroceso rápido (<20min)
slow_pull  = [t for t in trades if t['pull_bars'] > 10]   # retroceso lento

print()
print(f"  Segmentación por tamaño de cuerpo:")
print(seg_stats(big_body,   "  Cuerpo grande (≥0.5$) "))
print(seg_stats(small_body, "  Cuerpo pequeño (<0.3$)"))
print(f"  Segmentación por velocidad del retroceso:")
print(seg_stats(fast_pull,  "  Retroceso rápido ≤4bars "))
print(seg_stats(slow_pull,  "  Retroceso lento >10bars"))

# Tabla últimos 20
print()
print(f"  {'Fecha':12} {'Dir':6} {'Body':5}  {'Mid':7}  {'Pts':>7}  {'Bars':>5}  Res")
print("  "+"-"*62)
acum = 0
for t in trades[-20:]:
    acum += t['pts']
    icon = "✅" if t['win'] else "❌"
    print(f"  {t['date']:12} {t['direction']:6} {t['body_size']:4.2f}$  "
          f"${t['mid_entry']:6.2f}  {t['pts']:>+6.2f}  {t['pull_bars']:>4}b  "
          f"{icon}{t['result']:7}  acum={acum:+.1f}")

# ── GRÁFICAS ──────────────────────────────────────────────────────────
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLUE='#818cf8'

fig = plt.figure(figsize=(16,11), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.38)

def sax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=9)
    for sp in ax.spines.values(): sp.set_color('#2d2d4e')
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)

# 1. Equity curve
ax1 = fig.add_subplot(gs[0,:2])
sax(ax1)
equity=[0]
for t in trades: equity.append(equity[-1]+t['pts'])
col_eq = GRN if equity[-1]>0 else RED
ax1.plot(equity, color=col_eq, lw=2.2)
ax1.fill_between(range(len(equity)), equity, 0, alpha=0.13, color=col_eq)
ax1.axhline(0, color='#475569', lw=0.8, ls='--')
ax1.set_title(f'Equity Curve — {total} trades · {equity[-1]:+.1f}pts  (expectancy {expectancy:+.2f}/trade)',
              color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)
ax1.set_ylabel('Puntos QQQ', color='#64748b', fontsize=9)

# 2. Pie
ax2 = fig.add_subplot(gs[0,2])
sax(ax2)
ax2.pie([len(wins),len(losses)],
        labels=[f'WIN\n{len(wins)}',f'LOSS\n{len(losses)}'],
        colors=[GRN,RED], autopct='%1.0f%%', startangle=90,
        textprops={'color':'#e2e8f0','fontsize':11,'fontweight':'bold'},
        wedgeprops={'edgecolor':'#131325','linewidth':2})
ax2.set_title(f'Winrate {wr:.1f}%', color='#e2e8f0', fontsize=12, fontweight='bold', pad=10)

# 3. Scatter body_size vs pts
ax3 = fig.add_subplot(gs[1,:2])
sax(ax3)
colors3 = [GRN if t['win'] else RED for t in trades]
ax3.scatter([t['body_size'] for t in trades],
            [t['pts']      for t in trades],
            c=colors3, s=60, alpha=0.75, edgecolor='none')
ax3.axhline(0, color='#475569', lw=0.8, ls='--')
ax3.set_xlabel('Tamaño cuerpo vela apertura ($)', color='#64748b', fontsize=9)
ax3.set_ylabel('Resultado trade (pts $)', color='#64748b', fontsize=9)
ax3.set_title('Cuerpo vela vs Resultado — más grande mejor?', color='#e2e8f0',
              fontsize=11, fontweight='bold', pad=10)

# 4. Bars por resultado
ax4 = fig.add_subplot(gs[1,2])
sax(ax4)
cats = ['TP','SL','Timeout']
vals = [len(tp_h), len(sl_h), len(tout)]
cols4= [GRN, RED, GOLD]
bars4 = ax4.bar(cats, vals, color=cols4, alpha=0.85, edgecolor='none', width=0.5)
for b,v in zip(bars4,vals):
    ax4.text(b.get_x()+b.get_width()/2, b.get_height()+0.2, str(v),
             ha='center',va='bottom',color='#e2e8f0',fontsize=11,fontweight='bold')
ax4.set_title('Distribución Resultados', color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)
ax4.set_ylabel('N° trades', color='#64748b', fontsize=9)

fig.suptitle('Backtest: Entrada Retroceso 50% Vela Apertura NY (5min) — QQQ · 60 días',
             color='#e2e8f0', fontsize=14, fontweight='bold', y=0.99)

out = 'backtest_pullback_50_result.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Gráfica guardada: {out}")
plt.close()
