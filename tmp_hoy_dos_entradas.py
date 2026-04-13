"""
hoy_dos_entradas.py
Gráfica de HOY (Martes 7 Abr 2026) con las 2 entradas del setup
basadas en nuestras reglas estadísticas:
  - Asia Profile (POC/VAH/VAL)
  - Combo RRR → SHORT
  - Entry 1: cierre de V3 (9:40 ET)
  - Entry 2: retesto / continuación (10:00-10:15 ET)
"""
import yfinance as yf
import pandas as pd
from datetime import date, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.ticker as mticker
from matplotlib.patches import FancyArrowPatch
import numpy as np

BG='#0a0a16'; PANEL='#0d0d1a'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; SOFT='#94a3b8'; DIM='#475569'
WHITE='#f1f5f9'; TEAL='#14b8a6'; PRP='#a78bfa'

# ── DESCARGAR DATOS ────────────────────────────────────────────────────
print("Descargando NQ 5min (hoy)...")
import yfinance as yf, pandas as pd
tk = yf.Ticker("NQ=F")
df = tk.history(period="5d", interval="5m", auto_adjust=True)
df.index = pd.to_datetime(df.index)
try:    df.index = df.index.tz_convert('America/New_York')
except: df.index = df.index.tz_localize('UTC').tz_convert('America/New_York')

today = date(2026,4,7)
mon   = date(2026,4,6)

# ── FILTRAR SESIONES ───────────────────────────────────────────────────
def ny(d):
    return df[(df.index.date==d) &
              (((df.index.hour==9)&(df.index.minute>=30))|(df.index.hour>=10)&(df.index.hour<16))]

def overnight(d_from, d_to):
    """Asia: lunes 18ET → martes 9:20 ET"""
    mask_from = (df.index.date==d_from) & (df.index.hour>=18)
    mask_to   = (df.index.date==d_to)   & ((df.index.hour<9)|((df.index.hour==9)&(df.index.minute<20)))
    return df[mask_from | mask_to]

tue_ny  = ny(today)
mon_ny  = ny(mon)
asia    = overnight(mon, today)

if tue_ny.empty:
    print("ERROR: sin datos de hoy"); exit()

# ── ASIA PROFILE ────────────────────────────────────────────────────────
def calc_poc(bars_df, tick=5.0):
    if bars_df.empty: return None,None,None
    lo_all=bars_df['Low'].min(); hi_all=bars_df['High'].max()
    lo_f=(lo_all//tick)*tick; hi_c=(hi_all//tick+1)*tick
    n=int((hi_c-lo_f)/tick)
    if n<1: return None,None,None
    vol=np.zeros(n)
    for _,r in bars_df.iterrows():
        rng=r['High']-r['Low']
        if rng<=0: continue
        li=max(0,int((r['Low']-lo_f)/tick))
        hi=min(n-1,int((r['High']-lo_f)/tick))
        nt=hi-li+1
        v=(r['Volume'] if r['Volume']>0 else nt)
        vol[li:hi+1]+= v/nt
    total=vol.sum()
    poc_i=np.argmax(vol); poc=lo_f+poc_i*tick
    va=vol[poc_i]; lv=poc_i; hv=poc_i
    while va<total*0.70:
        el=lv>0; eh=hv<n-1
        if not el and not eh: break
        al=vol[lv-1] if el else -1; ah=vol[hv+1] if eh else -1
        if al>=ah and el: lv-=1; va+=vol[lv]
        elif eh: hv+=1; va+=vol[hv]
        else: lv-=1; va+=vol[lv]
    return poc, lo_f+lv*tick, lo_f+hv*tick

poc, val, vah = calc_poc(asia)
print(f"Asia Profile: POC={poc:.0f}  VAL={val:.0f}  VAH={vah:.0f}")

# ── NIVELES CLAVE ──────────────────────────────────────────────────────
mon_lo = mon_ny['Low'].min()
mon_hi = mon_ny['High'].max()
print(f"Mon LOW={mon_lo:.0f}  Mon HIGH={mon_hi:.0f}")

# Velas de apertura
v1 = tue_ny[tue_ny.index.time == pd.Timestamp('09:30').time()]
v2 = tue_ny[tue_ny.index.time == pd.Timestamp('09:35').time()]
v3 = tue_ny[tue_ny.index.time == pd.Timestamp('09:40').time()]
v4 = tue_ny[tue_ny.index.time == pd.Timestamp('09:45').time()]

if v1.empty or v2.empty or v3.empty:
    print("No hay velas 9:30-9:40, usando primeras barras")

# ── CONSTRUIR OHLCV MANUAL ─────────────────────────────────────────────
# Para dibujar candlesticks manualmente
def draw_candles(ax, df_slice, body_w=0.6, alpha=1.0):
    for i,(ts,row) in enumerate(df_slice.iterrows()):
        o,h,l,c=row['Open'],row['High'],row['Low'],row['Close']
        color=GRN if c>=o else RED
        # Wick
        ax.plot([i,i],[l,h],color=color,lw=0.9,alpha=alpha*0.85,zorder=2)
        # Body
        ax.add_patch(patches.Rectangle(
            (i-body_w/2, min(o,c)), body_w, abs(c-o),
            facecolor=color, edgecolor=color, lw=0, alpha=alpha, zorder=3
        ))

# ── FIGURA ─────────────────────────────────────────────────────────────
fig, (ax, ax2) = plt.subplots(2,1,figsize=(22,14),facecolor=BG,
                               gridspec_kw={'height_ratios':[5,1.2],'hspace':0.06})
for a in [ax,ax2]:
    a.set_facecolor(PANEL)
    a.tick_params(colors=SOFT,labelsize=8.5)
    [a.spines[s].set_visible(False) for s in ['top','right','left','bottom']]
    a.grid(axis='y',color=DIM,alpha=0.2,lw=0.5)

indices = list(range(len(tue_ny)))
times   = [ts.strftime('%H:%M') for ts in tue_ny.index]
highs   = tue_ny['High'].values
lows    = tue_ny['Low'].values
opens   = tue_ny['Open'].values
closes  = tue_ny['Close'].values
vols    = tue_ny['Volume'].values

draw_candles(ax, tue_ny)

# ── NIVELES HORIZONTALES ───────────────────────────────────────────────
n=len(indices)

# POC Asia
if poc:
    ax.axhline(poc, color=GOLD, lw=1.5, ls='--', alpha=0.85, zorder=1)
    ax.text(n+0.3, poc, f'POC Asia\n{poc:.0f}', color=GOLD, fontsize=8.5, va='center', fontweight='bold')
if val:
    ax.axhline(val, color=TEAL, lw=1.0, ls=':', alpha=0.7, zorder=1)
    ax.text(n+0.3, val, f'VAL {val:.0f}', color=TEAL, fontsize=7.5, va='center')
if vah:
    ax.axhline(vah, color=RED, lw=1.0, ls=':', alpha=0.7, zorder=1)
    ax.text(n+0.3, vah, f'VAH {vah:.0f}', color=RED, fontsize=7.5, va='center')

# Monday H/L
ax.axhline(mon_lo, color=RED, lw=1.2, ls=(0,(5,3)), alpha=0.6, zorder=1)
ax.text(n+0.3, mon_lo, f'Mon LOW\n{mon_lo:.0f}', color=RED, fontsize=8, va='center')
ax.axhline(mon_hi, color=GRN, lw=1.2, ls=(0,(5,3)), alpha=0.6, zorder=1)
ax.text(n+0.3, mon_hi, f'Mon HIGH\n{mon_hi:.0f}', color=GRN, fontsize=8, va='center')

# ── RESALTAR V1/V2/V3 ─────────────────────────────────────────────────
for vi_time, vi_lbl, vi_clr in [
    ('09:30','V1\n9:30',RED), ('09:35','V2\n9:35',RED), ('09:40','V3\n9:40',RED)
]:
    idx_list=[i for i,t in enumerate(times) if t==vi_time]
    if not idx_list: continue
    i=idx_list[0]
    ax.add_patch(patches.Rectangle((i-0.45,-1e9),0.9,2e9,
        facecolor=RED,alpha=0.08,zorder=0))
    ax.text(i, highs[i]+15, vi_lbl, ha='center', fontsize=9, color=RED,
            fontweight='bold', va='bottom')

# ── COMBO LABEL ───────────────────────────────────────────────────────
combo_box = patches.FancyBboxPatch((0.5, highs[:3].max()+35), 4.0, 65,
    boxstyle='round,pad=2',facecolor='#2a0000',edgecolor=RED,linewidth=2)
ax.add_patch(combo_box)
ax.text(2.5, highs[:3].max()+68, 'COMBO: R+R+R', ha='center', fontsize=13,
        color=RED, fontweight='bold', va='center')
ax.text(2.5, highs[:3].max()+45, '→ 69% baja (195 casos)', ha='center',
        fontsize=9, color=SOFT, va='center')

# ── ENTRADA 1: SHORT al cierre de V3 (9:40) ───────────────────────────
# Al cierre de la 3ª vela roja, SHORT con SL sobre HIGH de V1
v3_idx = next((i for i,t in enumerate(times) if t=='09:40'), 2)
v3_close = closes[v3_idx]
v1_high  = highs[0]   # HIGH de la primera vela 9:30
sl1      = v1_high + 10   # SL sobre high de V1
tp1_1    = v3_close - (sl1-v3_close)*1.5  # TP1 1.5R
tp1_2    = v3_close - (sl1-v3_close)*3.0  # TP2 3R (POC retest desde abajo)
riesgo1  = sl1 - v3_close
reward1  = v3_close - tp1_1

# Flecha entrada 1
ax.annotate('',
    xy=(v3_idx, v3_close-5), xytext=(v3_idx+2, v3_close+80),
    arrowprops=dict(arrowstyle='->', color=RED, lw=2.5))

# Box entrada 1
box1_y = v3_close + 90
box1 = patches.FancyBboxPatch((v3_idx-2, box1_y), 12, 130,
    boxstyle='round,pad=2', facecolor='#1a0808', edgecolor=RED, linewidth=2)
ax.add_patch(box1)
ax.text(v3_idx+4, box1_y+110, '⬇ ENTRADA 1 — SHORT', ha='center', fontsize=10.5,
        color=RED, fontweight='bold')
ax.text(v3_idx+4, box1_y+88, f'9:40 ET | Cierre V3 = {v3_close:.0f}', ha='center', fontsize=9, color=WHITE)
ax.text(v3_idx+4, box1_y+68, f'SL: {sl1:.0f}  (sobre HIGH V1, +{sl1-v3_close:.0f}pts)', ha='center', fontsize=9, color=RED)
ax.text(v3_idx+4, box1_y+48, f'TP1: {tp1_1:.0f}  (1.5R = {reward1:.0f}pts)', ha='center', fontsize=9, color=GRN)
ax.text(v3_idx+4, box1_y+28, f'TP2: {tp1_2:.0f}  (3R = {v3_close-tp1_2:.0f}pts)', ha='center', fontsize=9.5, color=GOLD, fontweight='bold')
ax.text(v3_idx+4, box1_y+8,  f'Regla: RRR + Sobre POC + VXN normal', ha='center', fontsize=8, color=SOFT)

# Líneas SL/TP1/TP2 limitadas al rango 9:40-11:00
tp_end_idx = next((i for i,t in enumerate(times) if t=='11:00'), len(times)-1)
ax.hlines(sl1,  v3_idx, tp_end_idx, colors=RED,  lw=1.2, ls='--', alpha=0.6, zorder=5)
ax.hlines(tp1_1,v3_idx, tp_end_idx, colors=GRN,  lw=1.2, ls='--', alpha=0.6, zorder=5)
ax.hlines(tp1_2,v3_idx, tp_end_idx, colors=GOLD,  lw=1.5, ls='--', alpha=0.7, zorder=5)

# Zona riesgo/reward entrada 1
ax.fill_between(range(v3_idx, min(v3_idx+25,len(times))), v3_close, sl1, alpha=0.10, color=RED)
ax.fill_between(range(v3_idx, min(v3_idx+25,len(times))), tp1_2, v3_close, alpha=0.08, color=GRN)

# ── ENTRADA 2: SHORT en retest del POC (10:00-10:15) ──────────────────
# Si el precio sube a retestear el POC después del primer impulso → 2nd SHORT
# Buscamos la barra más cerca del POC entre 10:00-10:30
e2_window = [(i,t) for i,t in enumerate(times) if '10:00'<=t<='10:30']
if poc and e2_window:
    # Buscar la barra del retorno al POC (high más cercano al POC)
    e2_candidates = [(i, abs(highs[i]-poc)) for i,t in e2_window]
    e2_best = min(e2_candidates, key=lambda x:x[1])
    e2_idx = e2_best[0]
    e2_close = closes[e2_idx]
    e2_high  = highs[e2_idx]
    sl2  = e2_high + 8
    tp2_1 = e2_close - (sl2-e2_close)*1.5
    tp2_2 = e2_close - (sl2-e2_close)*2.5
    riesgo2 = sl2 - e2_close

    ax.annotate('',
        xy=(e2_idx, e2_close-5), xytext=(e2_idx+2, e2_close+70),
        arrowprops=dict(arrowstyle='->', color=PRP, lw=2.5))

    box2_y = lows.min() - 200
    box2 = patches.FancyBboxPatch((e2_idx-4, box2_y), 14, 130,
        boxstyle='round,pad=2', facecolor='#100a1a', edgecolor=PRP, linewidth=2)
    ax.add_patch(box2)
    ax.text(e2_idx+3, box2_y+110, '⬇ ENTRADA 2 — SHORT (Retest)', ha='center',
            fontsize=10.5, color=PRP, fontweight='bold')
    ax.text(e2_idx+3, box2_y+88, f'{times[e2_idx]} ET | Retest POC = {e2_close:.0f}', ha='center', fontsize=9, color=WHITE)
    ax.text(e2_idx+3, box2_y+68, f'SL: {sl2:.0f}  (sobre HIGH barra, +{sl2-e2_close:.0f}pts)', ha='center', fontsize=9, color=RED)
    ax.text(e2_idx+3, box2_y+48, f'TP1: {tp2_1:.0f}  (1.5R = {e2_close-tp2_1:.0f}pts)', ha='center', fontsize=9, color=GRN)
    ax.text(e2_idx+3, box2_y+28, f'TP2: {tp2_2:.0f}  (2.5R = {e2_close-tp2_2:.0f}pts)', ha='center', fontsize=9.5, color=GOLD, fontweight='bold')
    ax.text(e2_idx+3, box2_y+8,  f'Regla: Retorno POC → Rechaza → SHORT', ha='center', fontsize=8, color=SOFT)

    # Flechita al retest
    ax.annotate('Retest\nPOC', xy=(e2_idx, poc), xytext=(e2_idx+3, poc+80),
        fontsize=8.5, color=GOLD, ha='center',
        arrowprops=dict(arrowstyle='->', color=GOLD, lw=1.5))

    # Líneas SL/TP entrada 2
    e2_end = min(e2_idx+30, len(times)-1)
    ax.hlines(sl2,  e2_idx, e2_end, colors=RED,  lw=1.2, ls='--', alpha=0.6, zorder=5)
    ax.hlines(tp2_1,e2_idx, e2_end, colors=GRN,  lw=1.2, ls='--', alpha=0.6, zorder=5)
    ax.hlines(tp2_2,e2_idx, e2_end, colors=GOLD,  lw=1.5, ls='--', alpha=0.7, zorder=5)

# ── EJE X ─────────────────────────────────────────────────────────────
step = max(1, len(times)//20)
ax.set_xticks(range(0, len(times), step))
ax.set_xticklabels([times[i] for i in range(0, len(times), step)], fontsize=8, color=SOFT, rotation=30)
ax.set_xlim(-1, len(times)+8)
ax_ylo=lows.min()-300; ax_yhi=highs.max()+300
ax.set_ylim(ax_ylo, ax_yhi)
ax.yaxis.set_major_formatter(mticker.FormatStrFormatter('%.0f'))
ax.set_ylabel('NQ Precio', color=SOFT, fontsize=9)

# ── VOLUMEN ────────────────────────────────────────────────────────────
colors_vol = [GRN if c>=o else RED for o,c in zip(opens,closes)]
ax2.bar(indices, vols, color=colors_vol, alpha=0.65, width=0.8)
ax2.set_xlim(-1, len(times)+8)
ax2.set_xticks(range(0, len(times), step))
ax2.set_xticklabels([times[i] for i in range(0, len(times), step)], fontsize=8, color=SOFT, rotation=30)
ax2.set_ylabel('Vol', color=SOFT, fontsize=8)
ax2.yaxis.set_visible(False)

# Highlight primeras 3 barras en volumen también
for vi_time in ['09:30','09:35','09:40']:
    for i,t in enumerate(times):
        if t==vi_time:
            ax2.add_patch(patches.Rectangle((i-0.45,0),0.9,max(vols)*1.1,
                facecolor=RED,alpha=0.12,zorder=0))

# ── TÍTULO ─────────────────────────────────────────────────────────────
fig.suptitle(
    f'martes 7 ABR 2026 — NQ 5min NY | COMBO RRR → 2 ENTRADAS SHORT\n'
    f'Asia POC: {poc:.0f}   Mon LOW: {mon_lo:.0f} / HIGH: {mon_hi:.0f}   '
    f'VXN: 20.0 (NORMAL)   COT: NEUTRAL',
    color=GOLD, fontsize=13, fontweight='bold', y=0.99
)

# ── INFO BOX LATERAL ──────────────────────────────────────────────────
fig.text(0.01, 0.96, 'REGLAS APLICADAS HOY:', fontsize=10, color=GOLD,
         fontweight='bold', va='top', transform=fig.transFigure)
reglas = [
    ('Combo',   'R+R+R (9:30, 9:35, 9:40)',   RED),
    ('Asia',    'NY abre SOBRE POC (+29pts)',   GOLD),
    ('COT',     'NEUTRAL (sin sesgo fuerte)',   SOFT),
    ('VXN',     '20.0 — NORMAL',               GRN),
    ('Stat 195','RRR → baja 69% de veces',     RED),
    ('Stat 3m', 'RRR → baja 2/3 últimos meses',RED),
    ('Min día', '59% antes 11ET → urgencia',   ORG:=ORG if 'ORG' in dir() else '#f97316'),
]
y_txt=0.93
for lbl,val_t,clr in reglas:
    fig.text(0.01, y_txt, f'  {lbl}:', fontsize=8.5, color=SOFT, va='top', transform=fig.transFigure)
    fig.text(0.06, y_txt, val_t, fontsize=8.5, color=clr, fontweight='bold', va='top', transform=fig.transFigure)
    y_txt-=0.028

out='hoy_dos_entradas.png'
plt.savefig(out, dpi=130, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'Grafica: {out}')
print(f'\nE1 SHORT @ {v3_close:.0f} | SL {sl1:.0f} (+{sl1-v3_close:.0f}) | TP2 {tp1_2:.0f} ({v3_close-tp1_2:.0f}pts)')
