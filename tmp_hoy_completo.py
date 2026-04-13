"""
hoy_analisis_completo.py
ANALISIS COMPLETO — HOY MARTES 7 ABR 2026
+ Comparación con los últimos 3 meses de martes (5min reales)
Objetivo: encontrar qué movimiento se repite SIEMPRE
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import matplotlib.patheffects as pe
import numpy as np

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'; PANEL3='#0d1520'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; SOFT='#94a3b8'; DIM='#475569'; ORG='#f97316'
WHITE='#f1f5f9'; TEAL='#14b8a6'; PINK='#f472b6'

print("Descargando datos 5min NQ (ultimos 3 meses)...")
tk = yf.Ticker("NQ=F")
df = tk.history(period="60d", interval="5m", auto_adjust=True)
df.index = pd.to_datetime(df.index)
try:    df.index = df.index.tz_convert('America/New_York')
except: df.index = df.index.tz_localize('UTC').tz_convert('America/New_York')

# Organizar por fecha
by_date = defaultdict(list)
for ts, row in df.iterrows():
    by_date[ts.date()].append({
        'et':ts, 'o':float(row['Open']), 'h':float(row['High']),
        'l':float(row['Low']),  'c':float(row['Close']),
        'v':float(row.get('Volume',0) or 0)
    })

sorted_dates = sorted(by_date.keys())
print(f"  Rango: {sorted_dates[0]} → {sorted_dates[-1]}")

def ny_bars(d):
    return sorted(
        [b for b in by_date.get(d,[])
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x:x['et']
    )

def get_vela(bars, h, m):
    return next((b for b in bars if b['et'].hour==h and b['et'].minute==m), None)

def vinfo(v):
    if v is None: return None
    body = abs(v['c']-v['o'])
    rng  = v['h']-v['l'] or 1
    return {
        'bull': v['c']>v['o'],
        'body': round(body,1),
        'rng':  round(rng,1),
        'str':  'FUERTE' if body>rng*0.6 else ('DEBIL' if body<rng*0.3 else 'MEDIA'),
        'whi':  round(v['h']-max(v['o'],v['c']),1),
        'wlo':  round(min(v['o'],v['c'])-v['l'],1),
        'v':    round(v['v']),
        'bar':  v,
    }

# ── ANÁLISIS DE CADA MARTES ───────────────────────────────────────────
martes_records = []

for d in sorted_dates:
    if d.weekday() != 1: continue

    bars = ny_bars(d)
    if len(bars) < 10: continue

    mon = d - timedelta(days=1)
    mon_bars = ny_bars(mon)
    if len(mon_bars) < 4: continue

    mon_lo = min(b['l'] for b in mon_bars)
    mon_hi = max(b['h'] for b in mon_bars)
    mon_open  = mon_bars[0]['o']
    mon_close = mon_bars[-1]['c']
    mon_chg   = round(mon_close-mon_open,1)
    pct_m = mon_chg/mon_open*100
    mon_type = ('BULL_STRONG' if pct_m>=0.8 else 'BULL' if pct_m>=0.3
                else 'FLAT' if pct_m>=-0.3 else 'BEAR' if pct_m>=-0.8 else 'BEAR_STRONG')

    # Velas apertura
    v1=get_vela(bars,9,30); v2=get_vela(bars,9,35); v3=get_vela(bars,9,40)
    v4=get_vela(bars,9,45); v5=get_vela(bars,9,50); v6=get_vela(bars,9,55)
    v7=get_vela(bars,10,0)

    vi1=vinfo(v1); vi2=vinfo(v2); vi3=vinfo(v3)

    if not vi1: continue

    # Stats del día completo
    tue_open  = bars[0]['o']
    tue_close = bars[-1]['c']
    tue_hi    = max(b['h'] for b in bars)
    tue_lo    = min(b['l'] for b in bars)
    tue_chg   = round(tue_close-tue_open,1)
    tue_bull  = tue_chg>0
    tue_rng   = round(tue_hi-tue_lo,1)

    # ── MOVIMIENTO PRINCIPAL: primer impulso largo ─────────────────────
    # Detectar primer movimiento sostenido (3+ velas en misma dirección)
    first_move_dir = None
    first_move_pts = 0
    first_move_end = None
    streak = 0
    streak_dir = None
    for i,b in enumerate(bars[:12]):  # En primera hora
        bd = b['c']>b['o']
        if streak_dir is None or bd!=streak_dir:
            streak=1; streak_dir=bd
        else:
            streak+=1
        if streak>=2 and first_move_dir is None:
            first_move_dir  = streak_dir
            first_move_end  = b['et']
            start_idx = max(0,i-streak+1)
            first_move_pts  = round(abs(bars[i]['c']-bars[start_idx]['o']),1)

    # ¿El primer movimiento sigue v1?
    first_follows_v1 = (first_move_dir==vi1['bull']) if first_move_dir is not None else None

    # ── SWEEPS ────────────────────────────────────────────────────────
    TOL=8
    swept_lo=False; swept_hi=False
    sweep_lo_time=None; sweep_hi_time=None
    for b in bars:
        if not swept_lo and b['l']<=mon_lo+TOL:
            swept_lo=True; sweep_lo_time=b['et']
        if not swept_hi and b['h']>=mon_hi-TOL:
            swept_hi=True; sweep_hi_time=b['et']

    # ── ESTRUCTURA DEL DÍA (6 tipos) ─────────────────────────────────
    if swept_lo and swept_hi:
        # ¿Cuál primero?
        if sweep_lo_time and sweep_hi_time:
            day_pattern = 'SWEEP_LO_THEN_HI' if sweep_lo_time<sweep_hi_time else 'SWEEP_HI_THEN_LO'
        else:
            day_pattern = 'SWEEP_BOTH'
    elif swept_lo and tue_bull:
        day_pattern = 'SWEEP_LO_REVERSAL'   # Barre low → reversa arriba ⭐
    elif swept_hi and not tue_bull:
        day_pattern = 'SWEEP_HI_REVERSAL'   # Barre high → reversa abajo
    elif tue_bull:
        day_pattern = 'TREND_UP'
    else:
        day_pattern = 'TREND_DOWN'

    # ── VOLUMEN apertura vs promedio ──────────────────────────────────
    v1_vol = vi1['v'] if vi1 else 0
    avg_vol_day = sum(b['v'] for b in bars)/max(1,len(bars))
    vol_ratio = round(v1_vol/max(1,avg_vol_day),2)

    # ── COMBO velas ───────────────────────────────────────────────────
    combo=''.join('V' if vinfo(vx) and vinfo(vx)['bull'] else 'R'
                  for vx in [v1,v2,v3] if vx)

    # ── TIMING del max y min del día ──────────────────────────────────
    hi_bar = max(bars, key=lambda x:x['h'])
    lo_bar = min(bars, key=lambda x:x['l'])
    hi_time = hi_bar['et'].strftime('%H:%M')
    lo_time = lo_bar['et'].strftime('%H:%M')

    # ── RETRACEMENT después del primer impulso ─────────────────────────
    # ¿El precio retrocede al 50% antes de continuar?
    retrace_50 = False
    if v1 and v3:
        impulse_range = abs(v3['c']-v1['o'])
        retrace_level = v1['o'] + (impulse_range*0.5 if vi1['bull'] else -impulse_range*0.5)
        for b in bars[3:10]:
            if vi1['bull'] and b['l']<=retrace_level: retrace_50=True; break
            if not vi1['bull'] and b['h']>=retrace_level: retrace_50=True; break

    martes_records.append({
        'd':d, 'mon_type':mon_type, 'mon_chg':mon_chg,
        'mon_lo':mon_lo, 'mon_hi':mon_hi,
        'tue_chg':tue_chg, 'tue_bull':tue_bull, 'tue_rng':tue_rng,
        'tue_hi':tue_hi, 'tue_lo':tue_lo, 'tue_open':tue_open, 'tue_close':tue_close,
        'vi1':vi1, 'vi2':vi2, 'vi3':vi3,
        'combo':combo,
        'first_move_dir':first_move_dir, 'first_move_pts':first_move_pts,
        'first_follows_v1':first_follows_v1,
        'swept_lo':swept_lo, 'swept_hi':swept_hi,
        'sweep_lo_time':sweep_lo_time, 'sweep_hi_time':sweep_hi_time,
        'day_pattern':day_pattern,
        'vol_ratio':vol_ratio,
        'hi_time':hi_time, 'lo_time':lo_time,
        'retrace_50':retrace_50,
        'bars':bars,
    })

N=len(martes_records)
print(f"\nMARTES en 3 meses (5min): {N}")

# ── ANÁLISIS HOY ──────────────────────────────────────────────────────
today = date(2026,4,7)
hoy = next((r for r in martes_records if r['d']==today), None)

print("\n" + "="*65)
print("HOY MARTES 7 ABRIL 2026 — SESIÓN NY")
print("="*65)

if hoy:
    vi1_h = hoy['vi1']
    print(f"\nLUNES 6 ABR: {hoy['mon_chg']:+.0f}pts ({hoy['mon_type']})")
    print(f"  Mon LOW={hoy['mon_lo']:.0f}  Mon HIGH={hoy['mon_hi']:.0f}")
    print()
    print(f"MARTES NY:")
    print(f"  Open={hoy['tue_open']:.0f}  Close={hoy['tue_close']:.0f}  Chg={hoy['tue_chg']:+.0f}pts")
    print(f"  High={hoy['tue_hi']:.0f} [{hoy['hi_time']}]  Low={hoy['tue_lo']:.0f} [{hoy['lo_time']}]")
    print(f"  Rango total: {hoy['tue_rng']:.0f}pts")
    print()
    v=vi1_h
    print(f"VELA 9:30 (5min):")
    print(f"  Dirección: {'VERDE (Alcista)' if v['bull'] else 'ROJA (Bajista)'}")
    print(f"  Body: {v['body']:.0f}pts  Rango: {v['rng']:.0f}pts  Fuerza: {v['str']}")
    print(f"  Volumen: {v['v']:,.0f} ({hoy['vol_ratio']:.1f}x el promedio del día)")
    print()
    vi2_h=hoy['vi2']; vi3_h=hoy['vi3']
    if vi2_h: print(f"VELA 9:35: {'VERDE' if vi2_h['bull'] else 'ROJA'} ({vi2_h['body']:.0f}pts body)")
    if vi3_h: print(f"VELA 9:40: {'VERDE' if vi3_h['bull'] else 'ROJA'} ({vi3_h['body']:.0f}pts body)")
    print(f"COMBO: {hoy['combo']}")
    print()
    print(f"PRIMER MOVIMIENTO LARGO:")
    if hoy['first_move_dir'] is not None:
        print(f"  Dirección: {'ALCISTA' if hoy['first_move_dir'] else 'BAJISTA'}")
        print(f"  Magnitud: {hoy['first_move_pts']:.0f}pts")
        print(f"  ¿Siguió dirección de v1? {'SI ✓' if hoy['first_follows_v1'] else 'NO ✗ (fakeout initial)'}")
    print()
    print(f"SWEEPS:")
    print(f"  Barrió LOW lunes ({hoy['mon_lo']:.0f}): {'SI ✓' + (hoy['sweep_lo_time'].strftime(' a las %H:%M') if hoy['sweep_lo_time'] else '') if hoy['swept_lo'] else 'NO'}")
    print(f"  Barrió HIGH lunes ({hoy['mon_hi']:.0f}): {'SI ✓' + (hoy['sweep_hi_time'].strftime(' a las %H:%M') if hoy['sweep_hi_time'] else '') if hoy['swept_hi'] else 'NO'}")
    print()
    print(f"PATRON DEL DIA: {hoy['day_pattern']}")
    print(f"Retrace 50% antes de continuar: {'SI' if hoy['retrace_50'] else 'NO'}")
else:
    print("  No hay datos de hoy todavia (mercado cerrado o no descargado)")

# ── COMPARACION 3 MESES ───────────────────────────────────────────────
print(f"\n{'='*65}")
print(f"ULTIMOS 3 MESES — TODOS LOS MARTES (n={N}):")
print(f"{'='*65}")

# Patrones
from collections import Counter
pat_counter = Counter(r['day_pattern'] for r in martes_records)
print(f"\nPATRONES DEL DIA (qué hace SIEMPRE):")
for pat,cnt in pat_counter.most_common():
    pct=cnt/N*100
    bar='█'*int(pct/3)
    print(f"  {pat:<25} {cnt:>3}/{N} = {pct:>5.0f}%  {bar}")

# Combos 3 velas
combo_counter = Counter(r['combo'] for r in martes_records if len(r['combo'])==3)
print(f"\nCOMBO 3 VELAS APERTURA:")
for combo,cnt in combo_counter.most_common():
    grp=[r for r in martes_records if r['combo']==combo]
    up=sum(1 for r in grp if r['tue_bull'])
    print(f"  {combo}  {cnt:>3}x  → día sube: {up}/{cnt} = {up/cnt*100:.0f}%")

# Primer movimiento
ff1 = [r for r in martes_records if r['first_follows_v1'] is True]
fn1 = [r for r in martes_records if r['first_follows_v1'] is False]
print(f"\nPRIMER MOVIMIENTO (primer impulso 2+ velas):")
print(f"  Siguió v1:      {len(ff1)}/{N} = {len(ff1)/N*100:.0f}%")
print(f"  Contra v1 (fakeout inicial): {len(fn1)}/{N} = {len(fn1)/N*100:.0f}%")
avg_move_pts = sum(r['first_move_pts'] for r in martes_records if r['first_move_pts']>0)/max(1,sum(1 for r in martes_records if r['first_move_pts']>0))
print(f"  Magnitud promedio primer impulso: {avg_move_pts:.0f}pts")

# Timing del HIGH y LOW del día
hi_hours = Counter(r['hi_time'][:5] for r in martes_records)
lo_hours = Counter(r['lo_time'][:5] for r in martes_records)
print(f"\nTIMING DEL MAXIMO DEL DIA (Martes):")
for t,c in hi_hours.most_common(5):
    print(f"  {t}: {c}x")
print(f"\nTIMING DEL MINIMO DEL DIA (Martes):")
for t,c in lo_hours.most_common(5):
    print(f"  {t}: {c}x")

# Sweeps
sw_lo = sum(1 for r in martes_records if r['swept_lo'])
sw_hi = sum(1 for r in martes_records if r['swept_hi'])
print(f"\nSWEEPS (último lunes):")
print(f"  Barre LOW lunes: {sw_lo}/{N} = {sw_lo/N*100:.0f}%")
print(f"  Barre HIGH lunes: {sw_hi}/{N} = {sw_hi/N*100:.0f}%")

# Lo que pasa SIEMPRE
print(f"\n{'='*65}")
print("LO QUE PASA SIEMPRE EN EL MARTES NY (3 meses):")
print(f"{'='*65}")
siempre = []
if sw_lo/N>0.6: siempre.append(f"  ▶ Barre el LOW del lunes: {sw_lo/N*100:.0f}% de los casos")
if sw_hi/N>0.6: siempre.append(f"  ▶ Barre el HIGH del lunes: {sw_hi/N*100:.0f}% de los casos")
if len(ff1)/N>0.6: siempre.append(f"  ▶ Primer impulso sigue v1(9:30): {len(ff1)/N*100:.0f}%")
top_pat=pat_counter.most_common(1)
if top_pat and top_pat[0][1]/N>0.3:
    siempre.append(f"  ▶ Patron dominante: {top_pat[0][0]} ({top_pat[0][1]/N*100:.0f}%)")
top_hi=hi_hours.most_common(1)[0] if hi_hours else None
top_lo=lo_hours.most_common(1)[0] if lo_hours else None
if top_hi: siempre.append(f"  ▶ Maximo del dia más frecuente: {top_hi[0]} ({top_hi[1]}x)")
if top_lo: siempre.append(f"  ▶ Minimo del dia más frecuente: {top_lo[0]} ({top_lo[1]}x)")
for s in siempre: print(s)

# ── FIGURA ────────────────────────────────────────────────────────────
n_charts = min(N,6)  # Mostrar los últimos 6 martes + hoy arriba
recent = martes_records[-n_charts:]

fig = plt.figure(figsize=(28, 20), facecolor=BG)
fig.suptitle(
    f"ANÁLISIS COMPLETO MARTES — HOY 7 ABR 2026 + Últimos {N} Martes (5min NY)\n"
    f"Buscando qué movimiento se repite SIEMPRE",
    color=GOLD, fontsize=13, fontweight='bold', y=0.995
)

# Layout: fila 0 = HOY grande, filas 1-2 = histórico y stats
outer = gridspec.GridSpec(2, 1, figure=fig, height_ratios=[1.8, 1],
                          hspace=0.30, left=0.04, right=0.98, top=0.96, bottom=0.05)

# ── TOP: HOY ─────────────────────────────────────────────────────────
gs_top = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[0], wspace=0.22)

# Panel precio HOY
ax_hoy = fig.add_subplot(gs_top[0, :2])
ax_hoy.set_facecolor(PANEL2)

if hoy:
    bars_h = hoy['bars']
    xs = list(range(len(bars_h)))
    times = [b['et'].strftime('%H:%M') for b in bars_h]

    # Velas
    for i, b in enumerate(bars_h):
        clr = GRN if b['c']>=b['o'] else RED
        ax_hoy.plot([i,i],[b['l'],b['h']],color=clr,lw=0.9,alpha=0.7)
        body=max(abs(b['c']-b['o']),0.5)
        bot=min(b['o'],b['c'])
        ax_hoy.add_patch(plt.Rectangle((i-0.4,bot),0.8,body,color=clr,alpha=0.85))

    # Volumen (mini barras abajo)
    vol_vals = [b['v'] for b in bars_h]
    max_vol = max(vol_vals) or 1
    price_range = hoy['tue_hi'] - hoy['tue_lo']
    vol_base = hoy['tue_lo'] - price_range * 0.18
    for i, (b, vv) in enumerate(zip(bars_h, vol_vals)):
        clr = GRN if b['c']>=b['o'] else RED
        vbar_h = (vv/max_vol) * price_range * 0.15
        ax_hoy.add_patch(plt.Rectangle((i-0.4, vol_base), 0.8, vbar_h,
                         color=clr, alpha=0.35))

    # Niveles clave
    ax_hoy.axhline(hoy['mon_lo'], color=RED,  lw=1.8, ls='--', alpha=0.9)
    ax_hoy.axhline(hoy['mon_hi'], color=GOLD, lw=1.5, ls='--', alpha=0.8)
    ax_hoy.text(len(bars_h)-1, hoy['mon_lo'], f" Mon LOW {hoy['mon_lo']:.0f}", color=RED, fontsize=8.5, va='bottom')
    ax_hoy.text(len(bars_h)-1, hoy['mon_hi'], f" Mon HIGH {hoy['mon_hi']:.0f}", color=GOLD, fontsize=8.5, va='top')

    # Marcar las 3 primeras velas
    for idx_v, (vx, clbl, cc) in enumerate([(0,'V1\n9:30',BLU),(1,'V2\n9:35',PRP),(2,'V3\n9:40',TEAL)]):
        if idx_v < len(bars_h):
            b = bars_h[idx_v]
            ax_hoy.annotate(clbl, (idx_v, b['h']+2), fontsize=8, color=cc,
                            fontweight='bold', ha='center')
            ax_hoy.add_patch(plt.Rectangle((idx_v-0.45, b['l']-1), 0.9,
                             b['h']-b['l']+2, color=cc, alpha=0.08, lw=0))

    # Sweeps
    if hoy['swept_lo'] and hoy['sweep_lo_time']:
        swi = next((i for i,b in enumerate(bars_h) if b['et']==hoy['sweep_lo_time']), None)
        if swi:
            ax_hoy.annotate('SWEEP\nLOW', (swi, hoy['mon_lo']),
                            xytext=(swi+2, hoy['mon_lo']-price_range*0.06),
                            fontsize=8.5, color=RED, fontweight='bold',
                            arrowprops=dict(arrowstyle='->', color=RED, lw=1.5))
    if hoy['swept_hi'] and hoy['sweep_hi_time']:
        swi = next((i for i, b in enumerate(bars_h) if b['et']==hoy['sweep_hi_time']), None)
        if swi:
            ax_hoy.annotate('SWEEP\nHIGH', (swi, hoy['mon_hi']),
                            xytext=(swi+2, hoy['mon_hi']+price_range*0.04),
                            fontsize=8.5, color=GOLD, fontweight='bold',
                            arrowprops=dict(arrowstyle='->', color=GOLD, lw=1.5))

    # Labels
    step=max(1,len(bars_h)//10)
    ax_hoy.set_xticks(xs[::step])
    ax_hoy.set_xticklabels(times[::step], fontsize=8, color=SOFT, rotation=30)
    ax_hoy.tick_params(colors=SOFT, labelsize=8)
    [ax_hoy.spines[s].set_visible(False) for s in ['top','right']]
    ax_hoy.set_xlim(-1, len(bars_h)+1)

    vi1_h=hoy['vi1']
    dir_str='VERDE' if vi1_h and vi1_h['bull'] else 'ROJA'
    dir_clr=GRN if vi1_h and vi1_h['bull'] else RED
    pat_clr=GRN if 'REVERSAL' in hoy['day_pattern'] or 'UP' in hoy['day_pattern'] else RED
    ax_hoy.set_title(
        f"HOY 7 ABR 2026  |  V1 {dir_str} {vi1_h['body'] if vi1_h else '?'}pts  "
        f"|  Combo: {hoy['combo']}  |  Chg: {hoy['tue_chg']:+.0f}pts  "
        f"|  Patron: {hoy['day_pattern']}",
        color=GOLD, fontsize=10.5, fontweight='bold', pad=5
    )
else:
    ax_hoy.text(0.5, 0.5, 'SIN DATOS HOY\n(mercado cerrado o aún no descargado)',
                ha='center', va='center', color=SOFT, fontsize=14, transform=ax_hoy.transAxes)
    ax_hoy.set_title('HOY 7 ABR 2026', color=GOLD, fontsize=12)
ax_hoy.spines['left'].set_color(PANEL2)
ax_hoy.spines['bottom'].set_color(PANEL2)

# Panel stats HOY
ax_stat = fig.add_subplot(gs_top[0, 2])
ax_stat.set_facecolor('#07070f'); ax_stat.axis('off')
ax_stat.set_xlim(0,10); ax_stat.set_ylim(0,20)
ax_stat.add_patch(patches.FancyBboxPatch((0.2,18.8),9.6,0.95,
    boxstyle='round,pad=0.1',facecolor='#0a1a0a',edgecolor=GRN,linewidth=2))
ax_stat.text(5,19.3,'RESUMEN HOY',ha='center',va='center',fontsize=11,fontweight='bold',color=GRN)

if hoy:
    vi1h=hoy['vi1']
    stat_lines=[
        (GOLD,'── LUNES 6 ABR ──',''),
        (GRN if hoy['mon_chg']>0 else RED,f"Cambio lunes:",f"{hoy['mon_chg']:+.0f}pts ({hoy['mon_type']})"),
        (SOFT,'Mon Low / High:',f"{hoy['mon_lo']:.0f} / {hoy['mon_hi']:.0f}"),
        (WHITE,'── VELAS APERTURA NY ──',''),
        (GRN if vi1h and vi1h['bull'] else RED,'V1 (9:30-9:35):',
         f"{'VERDE' if vi1h and vi1h['bull'] else 'ROJA'} {vi1h['body'] if vi1h else '?'}pts {'FUERTE' if vi1h and vi1h['str']=='FUERTE' else ''}"),
        (PRP if hoy['vi2'] else DIM,'V2 (9:35-9:40):',
         f"{'VERDE' if hoy['vi2'] and hoy['vi2']['bull'] else 'ROJA'} {hoy['vi2']['body'] if hoy['vi2'] else '?'}pts" if hoy['vi2'] else 'N/A'),
        (TEAL if hoy['vi3'] else DIM,'V3 (9:40-9:45):',
         f"{'VERDE' if hoy['vi3'] and hoy['vi3']['bull'] else 'ROJA'} {hoy['vi3']['body'] if hoy['vi3'] else '?'}pts" if hoy['vi3'] else 'N/A'),
        (GOLD,f"Combo: {hoy['combo']}",'' ),
        (WHITE,'── MOVIMIENTO ──',''),
        (GRN if hoy['first_follows_v1'] else RED,'1er impulso sigue v1:',
         f"{'SI' if hoy['first_follows_v1'] else 'NO (fakeout inicial)'}  {hoy['first_move_pts']:.0f}pts"),
        (GRN if hoy['tue_bull'] else RED,'Resultado día:',f"{hoy['tue_chg']:+.0f}pts  Rng:{hoy['tue_rng']:.0f}pts"),
        (RED if hoy['swept_lo'] else SOFT,'Barrió LOW lunes:','SI ✓' if hoy['swept_lo'] else 'NO'),
        (GOLD if hoy['swept_hi'] else SOFT,'Barrió HIGH lunes:','SI ✓' if hoy['swept_hi'] else 'NO'),
        (GOLD,'Patron del día:',hoy['day_pattern']),
        (BLU,'Max del día:',f"{hoy['tue_hi']:.0f} [{hoy['hi_time']}]"),
        (BLU,'Min del día:',f"{hoy['tue_lo']:.0f} [{hoy['lo_time']}]"),
    ]
    for i,(c,k,v) in enumerate(stat_lines):
        y=18.2-i*1.08
        ax_stat.text(0.4,y,k,fontsize=8.8,color=c,fontweight='bold',va='center')
        if v: ax_stat.text(5.0,y,v,fontsize=8.8,color=c,va='center')

# ── BOTTOM: HISTÓRICO ─────────────────────────────────────────────────
gs_bot = gridspec.GridSpecFromSubplotSpec(1, 3, subplot_spec=outer[1], wspace=0.28)

# Patrones frecuencia
ax_p = fig.add_subplot(gs_bot[0,0]); ax_p.set_facecolor(PANEL2)
pats=['SWEEP_LO_REVERSAL','TREND_UP','SWEEP_HI_REVERSAL','TREND_DOWN','SWEEP_LO_THEN_HI','SWEEP_HI_THEN_LO']
pat_l=['Sweep Lo\n→Reversal','Trend\nUp','Sweep Hi\n→Reversal','Trend\nDown','Lo→Hi','Hi→Lo']
pat_v=[pat_counter.get(p,0) for p in pats]
clrs_p=[GRN,GRN,RED,RED,GOLD,GOLD]
bars_p=ax_p.bar(range(len(pats)),pat_v,color=clrs_p,alpha=0.85,width=0.65)
for b,v_,lbl in zip(bars_p,pat_v,pat_l):
    if v_>0:
        ax_p.text(b.get_x()+b.get_width()/2,v_+0.1,
                  f'{v_}\n({v_/N*100:.0f}%)',color=WHITE,ha='center',fontsize=9,fontweight='bold')
ax_p.set_xticks(range(len(pats))); ax_p.set_xticklabels(pat_l,fontsize=8.5,color=SOFT)
ax_p.set_ylabel('N Martes',color=SOFT)
ax_p.set_title(f'Patrones más frecuentes\n(últimos {N} Martes NY)',color=GOLD,fontsize=11,fontweight='bold')
ax_p.tick_params(colors=SOFT); [ax_p.spines[s].set_visible(False) for s in ['top','right']]

# Timing máximo y mínimo
ax_t=fig.add_subplot(gs_bot[0,1]); ax_t.set_facecolor(PANEL2)
hi_hours_all=[r['hi_time'] for r in martes_records]
lo_hours_all=[r['lo_time'] for r in martes_records]
# Agrupar por hora ET
def hr_num(t):
    return int(t[:2])+int(t[3:])/60
hi_hr=[hr_num(t) for t in hi_hours_all]
lo_hr=[hr_num(t) for t in lo_hours_all]
bins_t=np.arange(9.5,16.5,0.5)
ax_t.hist(hi_hr,bins=bins_t,color=GOLD,alpha=0.7,label='Máximo del día',density=False)
ax_t.hist(lo_hr,bins=bins_t,color=RED,alpha=0.7,label='Mínimo del día',density=False)
ax_t.set_xticks(np.arange(10,16,1))
ax_t.set_xticklabels([f'{h}h' for h in range(10,16)],fontsize=9,color=SOFT)
ax_t.set_ylabel('N Martes',color=SOFT)
ax_t.set_title('¿A qué hora se forma\nel Max y Min del día?',color=GOLD,fontsize=11,fontweight='bold')
ax_t.legend(fontsize=9,facecolor=BG,labelcolor=SOFT)
ax_t.tick_params(colors=SOFT); [ax_t.spines[s].set_visible(False) for s in ['top','right']]

# Combo + 1er movimiento
ax_c=fig.add_subplot(gs_bot[0,2]); ax_c.set_facecolor(PANEL2)
ax_c.axis('off'); ax_c.set_xlim(0,10); ax_c.set_ylim(0,14)
ax_c.text(5,13.3,'LO QUE PASA SIEMPRE',ha='center',fontsize=11,fontweight='bold',color=GOLD)

# Calcular siempre-stats
sw_lo_pct=sw_lo/N*100; sw_hi_pct=sw_hi/N*100
ff1_pct=len(ff1)/N*100
top_pat_name=pat_counter.most_common(1)[0][0] if pat_counter else 'N/A'
top_pat_pct=pat_counter.most_common(1)[0][1]/N*100 if pat_counter else 0
top_combo=combo_counter.most_common(1)[0] if combo_counter else ('N/A',0)
top_hi_t=hi_hours.most_common(1)[0] if hi_hours else ('?',0)
top_lo_t=lo_hours.most_common(1)[0] if lo_hours else ('?',0)
avg_rng=sum(r['tue_rng'] for r in martes_records)/N

siempre_lines=[
    (GRN if sw_lo_pct>=60 else GOLD,'Barre LOW lunes:',f"{sw_lo_pct:.0f}%  ({sw_lo}/{N})"),
    (GRN if sw_hi_pct>=60 else GOLD,'Barre HIGH lunes:',f"{sw_hi_pct:.0f}%  ({sw_hi}/{N})"),
    (GRN if ff1_pct>=60 else GOLD,'1er impulso sigue V1:',f"{ff1_pct:.0f}%  ({len(ff1)}/{N})"),
    (GOLD,f'Patrón dominante:',f'{top_pat_name}'),
    (BLU,'Combo más frecuente:',f"{top_combo[0]} ({top_combo[1]}x)"),
    (GOLD,'Max del día a las:',f"{top_hi_t[0]} ET ({top_hi_t[1]}x)"),
    (RED,'Min del día a las:',f"{top_lo_t[0]} ET ({top_lo_t[1]}x)"),
    (SOFT,'Rango promedio NY:',f"{avg_rng:.0f}pts"),
    ('','',''),
    (WHITE,'REGLA OPERATIVA:',''),
    (GRN,'Si V1+V2 mismo color →','Entrar al cierre V2'),
    (RED,'Si fakeout inicial →','Esperar confirmación 10:00'),
    (BLU,'Máximo/Mínimo se forma:',f"principalmente {top_hi_t[0]}-{top_lo_t[0]}"),
]
for i,(c,k,v) in enumerate(siempre_lines):
    y=12.5-i*0.88
    if c:
        clr_k=GRN if '60%' in v or ('85%'>v>'60%') else c
        ax_c.text(0.3,y,k,fontsize=8.8,color=c,fontweight='bold',va='center')
        if v: ax_c.text(5.2,y,v,fontsize=8.8,color=c,va='center')

out='hoy_analisis_completo.png'
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
