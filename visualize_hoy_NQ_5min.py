"""
visualize_hoy_NQ_5min.py — NQ futures 5min REAL de hoy
"""
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import warnings
warnings.filterwarnings('ignore')

print("Descargando NQ=F 5min (últimos 5 días)...")
df_raw = yf.download("NQ=F", period="5d", interval="5m", auto_adjust=True, progress=False)

def col(df, c):
    return df[c].iloc[:,0] if isinstance(df.columns, pd.MultiIndex) else df[c]

if df_raw.empty:
    print("NQ=F vacío — probando MNQ=F...")
    df_raw = yf.download("MNQ=F", period="5d", interval="5m", auto_adjust=True, progress=False)
    ticker = "MNQ=F"
else:
    ticker = "NQ=F"

print(f"  Ticker: {ticker}, filas: {len(df_raw)}")

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

# Último día de trading disponible
trading_dates = sorted(set(df.index.date))
today = trading_dates[-1]
print(f"  Visualizando: {today}")

day_bars = df[df.index.date == today]

# Primera vela 9:30-9:35
open_bar = day_bars[
    (day_bars.index.time >= pd.Timestamp('09:30').time()) &
    (day_bars.index.time <  pd.Timestamp('09:35').time())
]

if len(open_bar) == 0:
    # Intentar 9:25 si no hay 9:30 exacto
    open_bar = day_bars[day_bars.index.time <= pd.Timestamp('09:40').time()].head(1)

if len(open_bar) == 0:
    print("Sin datos de apertura para este día.")
    exit()

ob = open_bar.iloc[0]
O  = float(ob['open']);  C_p = float(ob['close'])
H  = float(ob['high']);  L   = float(ob['low'])
body = abs(C_p - O)
mid  = (O + C_p) / 2
SL_BUF = 5.0  # 5 puntos NQ

if C_p > O:
    direction = 'LONG'
    sl_price  = L - SL_BUF
    risk      = mid - sl_price
    tp_price  = mid + risk * 2.0
    col_dir   = '#10b981'
else:
    direction = 'SHORT'
    sl_price  = H + SL_BUF
    risk      = sl_price - mid
    tp_price  = mid - risk * 2.0
    col_dir   = '#ef4444'

print(f"\n  === SETUP DEL DÍA ===")
print(f"  Primera vela (9:30): O={O:.0f}  H={H:.0f}  L={L:.0f}  C={C_p:.0f}")
print(f"  Cuerpo: {body:.0f}pts NQ  |  Dirección: {direction}")
print(f"  Midpoint entry:  {mid:.1f}")
print(f"  Stop Loss:       {sl_price:.1f}  (risk={risk:.1f}pts)")
print(f"  Take Profit 2R:  {tp_price:.1f}")

# Sesión NY hasta las 11:30
session = day_bars[
    (day_bars.index.time >= pd.Timestamp('09:25').time()) &
    (day_bars.index.time <= pd.Timestamp('11:30').time())
]

# ── GRAFICA ──────────────────────────────────────────────────────────
fig, (ax, ax_info) = plt.subplots(1, 2, figsize=(18, 8),
    facecolor='#0d0d1a', gridspec_kw={'width_ratios': [3, 1]})

for a in [ax, ax_info]:
    a.set_facecolor('#131325')
    a.tick_params(colors='#64748b', labelsize=9)
    for sp in a.spines.values(): sp.set_color('#2d2d4e')
    a.spines['top'].set_visible(False)
    a.spines['right'].set_visible(False)

# ── Velas ──────────────────────────────────────────────────────────
for i, (ts, bar) in enumerate(session.iterrows()):
    bO=float(bar['open']); bC=float(bar['close'])
    bH=float(bar['high']); bL=float(bar['low'])
    is_bull = bC >= bO
    clr = '#10b981' if is_bull else '#ef4444'
    ax.plot([i,i],[bL,bH], color=clr, lw=1.3, zorder=2)
    h_rect = max(abs(bC-bO), 0.5)
    ax.add_patch(patches.Rectangle(
        (i-0.35, min(bO,bC)), 0.70, h_rect,
        linewidth=0, facecolor=clr, alpha=0.9, zorder=3))

# Resaltar primera vela
fi = list(session.index).index(open_bar.index[0])
ax.add_patch(patches.Rectangle(
    (fi-0.40, min(O,C_p)), 0.80, max(abs(C_p-O),0.5),
    linewidth=2.5, edgecolor='#f59e0b', facecolor=col_dir, alpha=1.0, zorder=5))
ax.text(fi, H + (H-L)*0.15, f'1ª VELA\n{body:.0f}pts',
        ha='center', color='#f59e0b', fontsize=9, fontweight='bold')

# Líneas de niveles
xmax = len(session) - 1
ax.axhline(mid,      color='#818cf8', lw=2.2, ls='-',  zorder=4, label=f'ENTRY midpoint = {mid:.0f}')
ax.axhline(sl_price, color='#ef4444', lw=1.8, ls='--', zorder=4, label=f'SL = {sl_price:.0f}')
ax.axhline(tp_price, color='#10b981', lw=1.8, ls='--', zorder=4, label=f'TP = {tp_price:.0f}')
ax.axhline(O,        color='#f59e0b', lw=0.9, ls=':',  zorder=4, alpha=0.5, label=f'Open = {O:.0f}')
ax.axhline(C_p,      color='#94a3b8', lw=0.9, ls=':',  zorder=4, alpha=0.5, label=f'Close = {C_p:.0f}')

# Zonas
ax.fill_between(range(xmax+1), sl_price, mid,      alpha=0.07, color='#ef4444')
ax.fill_between(range(xmax+1), mid, tp_price,      alpha=0.07, color='#10b981')

# Labels de niveles al lado derecho
for val, lbl, clr_l in [
    (mid,      f' MID {mid:.0f} ',       '#818cf8'),
    (sl_price, f' SL  {sl_price:.0f} ',  '#ef4444'),
    (tp_price, f' TP  {tp_price:.0f} ',  '#10b981'),
]:
    ax.text(xmax*0.97, val, lbl, color=clr_l, fontsize=9, fontweight='bold',
            va='center', ha='right',
            bbox=dict(boxstyle='round,pad=0.25', facecolor='#0d0d1a',
                      edgecolor=clr_l, alpha=0.95))

# ── Detectar retroceso al mid ──────────────────────────────────────
after = list(session.iterrows())[fi+1:]
mid_hit = None; sl_hit = None; tp_hit = None

for i_rel, (ts, bar) in enumerate(after):
    bh = float(bar['high']); bl = float(bar['low'])
    if mid_hit is None:
        if (direction=='LONG' and bl<=mid) or (direction=='SHORT' and bh>=mid):
            mid_hit = fi + 1 + i_rel
    if mid_hit is not None:
        if direction=='LONG':
            if bl<=sl_price and sl_hit is None: sl_hit = fi+1+i_rel
            if bh>=tp_price and tp_hit is None: tp_hit = fi+1+i_rel
        else:
            if bh>=sl_price and sl_hit is None: sl_hit = fi+1+i_rel
            if bl<=tp_price and tp_hit is None: tp_hit = fi+1+i_rel

if mid_hit:
    ax.axvline(mid_hit, color='#818cf8', lw=2, ls=':', alpha=0.8)
    ax.text(mid_hit + 0.3, tp_price if direction=='LONG' else sl_price,
            '⬇ ENTRADA\nmidpoint', color='#818cf8', fontsize=8.5, fontweight='bold')
    if sl_hit:
        ax.axvline(sl_hit, color='#ef4444', lw=2, ls=':', alpha=0.8)
        ax.text(sl_hit+0.3, sl_price, '❌ SL', color='#ef4444', fontsize=9, fontweight='bold')
    if tp_hit:
        ax.axvline(tp_hit, color='#10b981', lw=2, ls=':', alpha=0.8)
        ax.text(tp_hit+0.3, tp_price, '✅ TP', color='#10b981', fontsize=9, fontweight='bold')
else:
    ax.text(xmax*0.5, mid + risk*0.3,
            '⚠️ Precio no retrocedió al 50% → SIN TRADE',
            color='#f59e0b', fontsize=10, fontweight='bold', ha='center')

# Eje X tiempo
tick_idxs = list(range(0, len(session), max(1, len(session)//10)))
ax.set_xticks(tick_idxs)
ax.set_xticklabels([session.index[i].strftime('%H:%M') for i in tick_idxs],
                   color='#64748b', fontsize=8)
ax.set_xlim(-1, len(session)+1)
ax.set_ylabel('Precio NQ (pts)', color='#64748b', fontsize=10)

dir_emoji = '📈 LONG' if direction=='LONG' else '📉 SHORT'
ax.set_title(
    f'{ticker} 5min — {today}  |  {dir_emoji}\n'
    f'O={O:.0f}  H={H:.0f}  L={L:.0f}  C={C_p:.0f}  Cuerpo={body:.0f}pts',
    color='#e2e8f0', fontsize=11, fontweight='bold', pad=10)
ax.legend(loc='upper left', fontsize=8.5, facecolor='#1a1a2e',
          labelcolor='#94a3b8', framealpha=0.8, edgecolor='#2d2d4e')

# ── Panel derecho: info y resultado ──────────────────────────────────
ax_info.set_xlim(0,1); ax_info.set_ylim(0,1)
ax_info.axis('off')

if mid_hit:
    if sl_hit and (not tp_hit or sl_hit < tp_hit):
        result_str = f'❌ LOSS\nSL tocado barra {sl_hit-fi}'
        pts = -risk
        res_clr = '#ef4444'
    elif tp_hit:
        result_str = f'✅ WIN\nTP tocado barra {tp_hit-fi}'
        pts = risk * 2.0
        res_clr = '#10b981'
    else:
        result_str = '⏱ EN CURSO'
        pts = 0; res_clr = '#f59e0b'
else:
    result_str = '— SIN TRADE\n(no retroceso)'
    pts = 0; res_clr = '#64748b'

lines = [
    ('ESTRATEGIA',    'Retroceso 50% Vela Apertura', '#94a3b8'),
    ('',              '', ''),
    ('Instrumento',   f'{ticker}', '#e2e8f0'),
    ('Fecha',         str(today), '#e2e8f0'),
    ('Dirección',     direction, col_dir),
    ('',              '', ''),
    ('Open vela',     f'{O:.0f}', '#f59e0b'),
    ('Close vela',    f'{C_p:.0f}', '#f59e0b'),
    ('High',          f'{H:.0f}', '#64748b'),
    ('Low',           f'{L:.0f}', '#64748b'),
    ('Cuerpo',        f'{body:.0f} pts NQ', '#e2e8f0'),
    ('',              '', ''),
    ('ENTRY (50%)',    f'{mid:.0f}', '#818cf8'),
    ('Stop Loss',     f'{sl_price:.0f}  (−{risk:.0f}pt)', '#ef4444'),
    ('Take Profit',   f'{tp_price:.0f}  (+{risk*2:.0f}pt)', '#10b981'),
    ('Risk:Reward',   '1 : 2', '#e2e8f0'),
    ('',              '', ''),
    ('Retroceso',     f'{"Sí, barra "+str(mid_hit-fi) if mid_hit else "No"}', '#818cf8' if mid_hit else '#f59e0b'),
    ('RESULTADO',     result_str, res_clr),
]

y = 0.97
for label, val, clr in lines:
    if not label and not val:
        y -= 0.025; continue
    if label == 'RESULTADO':
        ax_info.text(0.05, y, val, color=clr, fontsize=12,
                     fontweight='bold', va='top',
                     bbox=dict(boxstyle='round,pad=0.5', facecolor=clr+'22',
                               edgecolor=clr, alpha=0.9))
    elif label == 'ESTRATEGIA':
        ax_info.text(0.05, y, val, color='#e2e8f0', fontsize=10,
                     fontweight='bold', va='top')
    elif label:
        ax_info.text(0.05, y, label+':', color='#64748b', fontsize=9, va='top')
        ax_info.text(0.52, y, val,   color=clr,     fontsize=9, va='top', fontweight='bold')
    y -= 0.052

plt.tight_layout(pad=1.5)
out = 'visualize_hoy_NQ_5min.png'
plt.savefig(out, dpi=140, bbox_inches='tight', facecolor='#0d0d1a')
print(f"\n  Gráfica guardada: {out}")
plt.close()
