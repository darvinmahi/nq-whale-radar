"""
backtest_primera_vela_3m.py
Backtest estrategia: primera vela 3min NY session
Entrada al cierre de 9:30-9:33, SL en extremo opuesto, TP 2:1
Últimos 3 meses en NQ=F (o QQQ como proxy)
"""
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from datetime import datetime, timedelta, timezone
import warnings
warnings.filterwarnings('ignore')

# ── PARÁMETROS ────────────────────────────────────────────────────────
TICKER   = "QQQ"   # NQ proxy — yfinance no tiene 3min para futuros
PERIOD   = "60d"   # yfinance 5min max ~60 días
INTERVAL = "5m"    # 5min es lo más cercano a 3min disponible en yfinance
SESSION_OPEN  = (9, 30)  # ET
SESSION_CLOSE = (16, 0)  # ET
TP_RATIO = 2.0           # 1:2 risk/reward
MIN_CANDLE_BIG   = 20    # pts — vela "grande"
MAX_CANDLE_SMALL = 10    # pts — vela "pequeña"

print(f"Descargando {TICKER} 3min (3 meses)...")
df_raw = yf.download(TICKER, period=PERIOD, interval=INTERVAL, auto_adjust=True, progress=False)

def col(df, c):
    return df[c].iloc[:,0] if isinstance(df.columns, pd.MultiIndex) else df[c]

df = pd.DataFrame({
    'open':  col(df_raw,'Open'),
    'high':  col(df_raw,'High'),
    'low':   col(df_raw,'Low'),
    'close': col(df_raw,'Close'),
}).dropna()

# Convertir a ET (UTC-5, ignoramos DST por simplicidad)
if df.index.tz is not None:
    df.index = df.index.tz_convert('America/New_York')
else:
    df.index = df.index.tz_localize('UTC').tz_convert('America/New_York')

df = df[df.index.dayofweek < 5]  # solo lunes-viernes
print(f"  → {len(df)} barras, {df.index.date[0]} → {df.index.date[-1]}")

# ── BACKTEST ──────────────────────────────────────────────────────────
trades = []
trading_days = sorted(set(df.index.date))

for day in trading_days:
    day_bars = df[df.index.date == day]
    # Primera vela 9:30
    open_bars = day_bars[(day_bars.index.time >= pd.Timestamp('09:30').time()) &
                         (day_bars.index.time <= pd.Timestamp('09:33').time())]
    if len(open_bars) == 0:
        continue
    entry_bar = open_bars.iloc[0]
    entry_time = open_bars.index[0]

    candle_open  = float(entry_bar['open'])
    candle_close = float(entry_bar['close'])
    candle_high  = float(entry_bar['high'])
    candle_low   = float(entry_bar['low'])
    candle_size  = round(abs(candle_close - candle_open), 2)

    # Dirección
    if candle_close > candle_open:
        direction = 'LONG'
        entry_price = candle_close
        sl_price    = candle_low
        risk_pts    = entry_price - sl_price
        tp_price    = entry_price + risk_pts * TP_RATIO
    elif candle_close < candle_open:
        direction = 'SHORT'
        entry_price = candle_close
        sl_price    = candle_high
        risk_pts    = sl_price - entry_price
        tp_price    = entry_price - risk_pts * TP_RATIO
    else:
        continue  # doji, skip

    if risk_pts <= 0.5:
        continue  # vela sin cuerpo relevante

    # Simular el resto de la sesión
    session_bars = day_bars[day_bars.index > entry_time]
    session_bars = session_bars[session_bars.index.time <= pd.Timestamp('16:00').time()]

    result = 'TIMEOUT'
    exit_price = None
    exit_time = None

    for _, bar in session_bars.iterrows():
        h = float(bar['high']); l = float(bar['low']); c = float(bar['close'])
        bar_t = bar.name

        if direction == 'LONG':
            if l <= sl_price:
                result = 'SL'; exit_price = sl_price; exit_time = bar_t; break
            if h >= tp_price:
                result = 'TP'; exit_price = tp_price; exit_time = bar_t; break
        else:  # SHORT
            if h >= sl_price:
                result = 'SL'; exit_price = sl_price; exit_time = bar_t; break
            if l <= tp_price:
                result = 'TP'; exit_price = tp_price; exit_time = bar_t; break

    if exit_price is None:
        # timeout al cierre
        close_bar = session_bars[session_bars.index.time <= pd.Timestamp('15:59').time()]
        if len(close_bar) == 0:
            continue
        exit_price = float(close_bar.iloc[-1]['close'])
        exit_time  = close_bar.index[-1]

    pts = round((exit_price - entry_price) if direction=='LONG' else (entry_price - exit_price), 2)
    win = pts > 0

    trades.append({
        'date':        str(day),
        'direction':   direction,
        'candle_size': candle_size,
        'entry':       round(entry_price,2),
        'sl':          round(sl_price,2),
        'tp':          round(tp_price,2),
        'exit':        round(exit_price,2),
        'result':      result,
        'pts':         pts,
        'win':         win,
        'risk_pts':    round(risk_pts,2),
    })

# ── STATS ─────────────────────────────────────────────────────────────
print(f"\n  → {len(trades)} trades ejecutados")
if not trades:
    print("Sin trades. Revisa el ticker o periodo.")
    exit()

total_pts = sum(t['pts'] for t in trades)
wins      = [t for t in trades if t['win']]
losses    = [t for t in trades if not t['win']]
tp_hits   = [t for t in trades if t['result']=='TP']
sl_hits   = [t for t in trades if t['result']=='SL']
timeouts  = [t for t in trades if t['result']=='TIMEOUT']

wr = len(wins)/len(trades)*100
avg_win  = sum(t['pts'] for t in wins)/len(wins) if wins else 0
avg_loss = sum(t['pts'] for t in losses)/len(losses) if losses else 0

big_candle   = [t for t in trades if t['candle_size'] >= MIN_CANDLE_BIG]
small_candle = [t for t in trades if t['candle_size'] <= MAX_CANDLE_SMALL]

def wr_sub(sub):
    if not sub: return 0
    return sum(1 for t in sub if t['win'])/len(sub)*100

print()
print("═"*60)
print(f"  BACKTEST: Primera vela 3min NY — {len(trades)} trading days")
print("═"*60)
print(f"  Winrate total:         {wr:.1f}%")
print(f"  Total pts:             {total_pts:+.1f}")
print(f"  Avg WIN:               {avg_win:+.1f} pts   ({len(wins)} trades)")
print(f"  Avg LOSS:              {avg_loss:+.1f} pts   ({len(losses)} trades)")
print(f"  TP hits:               {len(tp_hits)} ({len(tp_hits)/len(trades)*100:.0f}%)")
print(f"  SL hits:               {len(sl_hits)} ({len(sl_hits)/len(trades)*100:.0f}%)")
print(f"  Timeout (close):       {len(timeouts)} ({len(timeouts)/len(trades)*100:.0f}%)")
print()
print(f"  Vela GRANDE (>{MIN_CANDLE_BIG}pts): {len(big_candle)} trades  WR={wr_sub(big_candle):.1f}%  avg_pts={sum(t['pts'] for t in big_candle)/len(big_candle) if big_candle else 0:+.1f}")
print(f"  Vela PEQUEÑA (<{MAX_CANDLE_SMALL}pts): {len(small_candle)} trades  WR={wr_sub(small_candle):.1f}%  avg_pts={sum(t['pts'] for t in small_candle)/len(small_candle) if small_candle else 0:+.1f}")
print()

# ── TABLA DÍA A DÍA ──────────────────────────────────────────────────
print(f"  {'Fecha':12} {'Dir':6} {'Vela':6} {'Pts':>7} {'Res':8} {'Acum':>8}")
print("  "+"-"*58)
acum = 0
for t in trades[-20:]:  # últimos 20
    acum += t['pts']
    icon = "✅" if t['win'] else "❌"
    print(f"  {t['date']:12} {t['direction']:6} {t['candle_size']:5.1f}pt  {t['pts']:>+6.1f}  {icon}{t['result']:7}  {acum:>+7.1f}")

# ── GRÁFICAS ──────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16,10), facecolor='#0d0d1a')
gs  = gridspec.GridSpec(2, 3, figure=fig, hspace=0.4, wspace=0.35)

GOLD = '#f59e0b'; GRN = '#10b981'; RED = '#ef4444'; BLUE = '#818cf8'
ax_style = dict(facecolor='#1a1a2e', labelcolor='#94a3b8',
                xcolor='#475569', ycolor='#475569')

def styled_ax(ax):
    ax.set_facecolor('#131325')
    ax.tick_params(colors='#64748b', labelsize=9)
    ax.spines['bottom'].set_color('#2d2d4e')
    ax.spines['left'].set_color('#2d2d4e')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

# 1. Equity curve
ax1 = fig.add_subplot(gs[0, :2])
styled_ax(ax1)
equity = [0]
for t in trades: equity.append(equity[-1] + t['pts'])
color_eq = GRN if equity[-1] > 0 else RED
ax1.plot(range(len(equity)), equity, color=color_eq, lw=2)
ax1.fill_between(range(len(equity)), equity, 0, alpha=0.15, color=color_eq)
ax1.axhline(0, color='#475569', lw=0.8, ls='--')
ax1.set_title(f'Equity Curve — {len(trades)} trades  ({equity[-1]:+.0f}pts)', 
              color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)
ax1.set_ylabel('Puntos NQ', color='#64748b', fontsize=9)
ax1.yaxis.label.set_color('#64748b')

# 2. Win/Loss pie
ax2 = fig.add_subplot(gs[0, 2])
styled_ax(ax2)
ax2.pie([len(wins), len(losses)], labels=[f'WIN\n{len(wins)}', f'LOSS\n{len(losses)}'],
        colors=[GRN, RED], autopct='%1.0f%%', startangle=90,
        textprops={'color':'#e2e8f0','fontsize':10,'fontweight':'bold'},
        wedgeprops={'edgecolor':'#131325','linewidth':2})
ax2.set_title(f'Winrate: {wr:.1f}%', color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)

# 3. Resultado por vela (scatter)
ax3 = fig.add_subplot(gs[1, :2])
styled_ax(ax3)
sizes  = [t['candle_size'] for t in trades]
pts    = [t['pts'] for t in trades]
colors = [GRN if t['win'] else RED for t in trades]
ax3.scatter(sizes, pts, c=colors, alpha=0.7, s=50, edgecolor='none')
ax3.axhline(0, color='#475569', lw=0.8, ls='--')
ax3.axvline(MIN_CANDLE_BIG, color=GOLD, lw=1, ls='--', alpha=0.5, label=f'Vela grande >{MIN_CANDLE_BIG}pt')
ax3.axvline(MAX_CANDLE_SMALL, color=BLUE, lw=1, ls='--', alpha=0.5, label=f'Vela pequeña <{MAX_CANDLE_SMALL}pt')
ax3.set_xlabel('Tamaño vela apertura (pts)', color='#64748b', fontsize=9)
ax3.set_ylabel('Resultado trade (pts)', color='#64748b', fontsize=9)
ax3.set_title('Tamaño vela vs Resultado', color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)
ax3.legend(fontsize=8, facecolor='#1a1a2e', labelcolor='#94a3b8', framealpha=0.5)

# 4. Barras LONG vs SHORT
ax4 = fig.add_subplot(gs[1, 2])
styled_ax(ax4)
longs  = [t for t in trades if t['direction']=='LONG']
shorts = [t for t in trades if t['direction']=='SHORT']
cats   = ['LONG WIN','LONG LOSS','SHORT WIN','SHORT LOSS']
vals   = [
    sum(1 for t in longs  if t['win']),
    sum(1 for t in longs  if not t['win']),
    sum(1 for t in shorts if t['win']),
    sum(1 for t in shorts if not t['win']),
]
bar_colors = [GRN, RED, GRN, RED]
bars = ax4.bar(cats, vals, color=bar_colors, alpha=0.8, edgecolor='none')
for bar, v in zip(bars, vals):
    ax4.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.3, str(v),
             ha='center', va='bottom', color='#e2e8f0', fontsize=9, fontweight='bold')
ax4.set_title('LONG vs SHORT', color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)
ax4.tick_params(axis='x', labelsize=7, rotation=15)
ax4.set_ylabel('Número trades', color='#64748b', fontsize=9)

fig.suptitle(f'Backtest: Primera Vela 3min NY — {TICKER} · Últimos 3 meses',
             color='#e2e8f0', fontsize=14, fontweight='bold', y=0.98)

out = 'backtest_primera_vela_3m_result.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Gráfica guardada: {out}")
plt.close()
