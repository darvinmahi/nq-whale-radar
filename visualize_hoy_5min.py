"""
visualize_hoy_5min.py
Muestra visualmente cómo funciona la estrategia 50% retroceso
para el día de HOY en QQQ 5min
"""
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import warnings
warnings.filterwarnings('ignore')

# ── Descargar 5min de hoy/últimos días ───────────────────────────────
print("Descargando QQQ 5min (últimos 5 días)...")
df_raw = yf.download("QQQ", period="5d", interval="5m", auto_adjust=True, progress=False)

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

# Tomar el último día de trading
trading_dates = sorted(set(df.index.date))
today = trading_dates[-1]
print(f"  Visualizando: {today}")

day_bars = df[df.index.date == today]

# ── Calcular niveles ─────────────────────────────────────────────────
# Primera vela 9:30-9:35
open_bar = day_bars[
    (day_bars.index.time >= pd.Timestamp('09:30').time()) &
    (day_bars.index.time <  pd.Timestamp('09:35').time())
]

if len(open_bar) == 0:
    print("No hay datos de apertura para este día")
    exit()

ob = open_bar.iloc[0]
O  = float(ob['open'])
C  = float(ob['close'])
H  = float(ob['high'])
L  = float(ob['low'])
body_size = abs(C - O)
mid       = (O + C) / 2
SL_BUF    = 0.05

if C > O:
    direction = 'LONG'
    sl_price  = L - SL_BUF
    risk      = mid - sl_price
    tp_price  = mid + risk * 2.0
    entry_col = '#10b981'
else:
    direction = 'SHORT'
    sl_price  = H + SL_BUF
    risk      = sl_price - mid
    tp_price  = mid - risk * 2.0
    entry_col = '#ef4444'

print(f"  Primera vela: O={O:.2f} C={C:.2f} H={H:.2f} L={L:.2f}")
print(f"  Dirección: {direction}")
print(f"  Midpoint entry: {mid:.2f}")
print(f"  SL: {sl_price:.2f}  TP: {tp_price:.2f}  Risk: {risk:.2f}pts")

# Sesión NY hasta las 11:30 (para ver el setup completo)
session = day_bars[
    (day_bars.index.time >= pd.Timestamp('09:25').time()) &
    (day_bars.index.time <= pd.Timestamp('11:30').time())
]

# ── GRAFICA ──────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(15, 8), facecolor='#0d0d1a')
ax.set_facecolor('#131325')
ax.tick_params(colors='#64748b', labelsize=9)
for sp in ax.spines.values(): sp.set_color('#2d2d4e')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Dibujar velas manualmente
for i, (ts, bar) in enumerate(session.iterrows()):
    bO = float(bar['open']); bC = float(bar['close'])
    bH = float(bar['high']); bL = float(bar['low'])
    is_bull = bC >= bO
    clr = '#10b981' if is_bull else '#ef4444'
    # Mecha
    ax.plot([i, i], [bL, bH], color=clr, lw=1.2, zorder=2)
    # Cuerpo
    rect = patches.Rectangle(
        (i - 0.35, min(bO, bC)),
        0.70,
        abs(bC - bO) if abs(bC-bO) > 0.01 else 0.03,
        linewidth=0,
        facecolor=clr,
        alpha=0.9,
        zorder=3
    )
    ax.add_patch(rect)

# Resaltar la primera vela 9:30
first_idx = list(session.index).index(open_bar.index[0])
first_rect = patches.Rectangle(
    (first_idx - 0.38, min(O, C)),
    0.76, abs(C - O) if abs(C-O)>0.01 else 0.03,
    linewidth=2, edgecolor='#f59e0b', facecolor=entry_col, alpha=1.0, zorder=5
)
ax.add_patch(first_rect)
ax.annotate('← PRIMERA VELA\n9:30–9:35', xy=(first_idx + 0.5, (O+C)/2),
            xytext=(first_idx + 3, (O+C)/2 + 0.5),
            color='#f59e0b', fontsize=9, fontweight='bold',
            arrowprops=dict(arrowstyle='->', color='#f59e0b', lw=1.5))

# Líneas de niveles
x_range = len(session) - 1
ax.axhline(mid,      color='#818cf8', lw=2.0, ls='-',  zorder=4, alpha=0.9, label=f'ENTRY / MIDPOINT 50% = ${mid:.2f}')
ax.axhline(sl_price, color='#ef4444', lw=1.5, ls='--', zorder=4, alpha=0.8, label=f'STOP LOSS = ${sl_price:.2f}')
ax.axhline(tp_price, color='#10b981', lw=1.5, ls='--', zorder=4, alpha=0.8, label=f'TAKE PROFIT 2R = ${tp_price:.2f}')
ax.axhline(O,        color='#f59e0b', lw=0.8, ls=':',  zorder=4, alpha=0.5, label=f'OPEN vela = ${O:.2f}')
ax.axhline(C,        color='#94a3b8', lw=0.8, ls=':',  zorder=4, alpha=0.5, label=f'CLOSE vela = ${C:.2f}')

# Zona de riesgo (SL a mid)
ax.fill_between(range(x_range+1), sl_price, mid, alpha=0.08, color='#ef4444')
# Zona de profit (mid a TP)
ax.fill_between(range(x_range+1), mid, tp_price, alpha=0.08, color='#10b981')

# Annotations de niveles
def annot_level(y, label, col, x_frac=0.92):
    ax.text(x_range * x_frac, y, label, color=col, fontsize=8.5,
            fontweight='bold', va='center',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='#0d0d1a', edgecolor=col, alpha=0.9))

annot_level(mid,      f' ENTRY ${mid:.2f} ', '#818cf8')
annot_level(sl_price, f' SL ${sl_price:.2f} ', '#ef4444')
annot_level(tp_price, f' TP ${tp_price:.2f} ', '#10b981')

# ── Detectar si el mid fue tocado ────────────────────────────────────
after_first = session.iloc[first_idx + 1:]
mid_touched = False
mid_touch_idx = None
for i_rel, (ts, bar) in enumerate(after_first.iterrows()):
    bh = float(bar['high']); bl = float(bar['low'])
    if (direction == 'LONG'  and bl <= mid) or \
       (direction == 'SHORT' and bh >= mid):
        mid_touched   = True
        mid_touch_idx = first_idx + 1 + i_rel
        break

if mid_touched:
    ax.axvline(mid_touch_idx, color='#818cf8', lw=2, ls=':', alpha=0.7)
    ax.text(mid_touch_idx + 0.3,
            tp_price if direction=='LONG' else sl_price,
            '⬇ ENTRADA\nretroceso', color='#818cf8', fontsize=8.5, fontweight='bold')
else:
    ax.text(x_range * 0.5, mid + 0.1,
            '⚠️ Precio nunca retrocedió al 50% → SIN TRADE',
            color='#f59e0b', fontsize=10, fontweight='bold',
            ha='center', va='bottom')

# Etiquetas del eje X (tiempo)
tick_idxs = list(range(0, len(session), 6))
ax.set_xticks(tick_idxs)
ax.set_xticklabels(
    [session.index[i].strftime('%H:%M') for i in tick_idxs],
    color='#64748b', fontsize=8
)
ax.set_xlim(-1, len(session))
ax.set_ylabel('Precio QQQ ($)', color='#64748b', fontsize=10)

direction_emoji = '📈 LONG' if direction == 'LONG' else '📉 SHORT'
title = (f'QQQ 5min — {today}  |  {direction_emoji}  |  '
         f'Mid Entry ${mid:.2f}  |  SL ${sl_price:.2f}  |  TP ${tp_price:.2f}\n'
         f'Vela apertura: O={O:.2f} H={H:.2f} L={L:.2f} C={C:.2f}  '
         f'Cuerpo={body_size:.2f}$')
ax.set_title(title, color='#e2e8f0', fontsize=11, fontweight='bold', pad=12)

leg = ax.legend(loc='upper left', fontsize=8.5, facecolor='#1a1a2e',
                labelcolor='#94a3b8', framealpha=0.8, edgecolor='#2d2d4e')

# Info box
info = (f"ESTRATEGIA: Retroceso 50% vela apertura\n"
        f"  Dirección vela: {direction}\n"
        f"  50% cuerpo: ${mid:.2f}  (entre {min(O,C):.2f}–{max(O,C):.2f})\n"
        f"  Stop: ${sl_price:.2f} ({'bajo low' if direction=='LONG' else 'encima high'} + buffer)\n"
        f"  Risk: ${risk:.2f}  |  TP ratio 1:2  →  ${tp_price:.2f}\n"
        f"  Retroceso al mid: {'✅ SÍ (barra '+str(mid_touch_idx-first_idx)+')' if mid_touched else '❌ NO → sin trade'}")
ax.text(0.01, 0.03, info, transform=ax.transAxes,
        color='#94a3b8', fontsize=8.5, va='bottom', linespacing=1.6,
        bbox=dict(boxstyle='round,pad=0.6', facecolor='#0a0a18', edgecolor='#2d2d4e', alpha=0.95))

plt.tight_layout(pad=1.5)
out = 'visualize_hoy_5min.png'
plt.savefig(out, dpi=140, bbox_inches='tight', facecolor='#0d0d1a')
print(f"  Gráfica guardada: {out}")
plt.close()
