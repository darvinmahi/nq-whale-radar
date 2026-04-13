"""
martes_reaccion_niveles.py
ESTUDIO: Cuando el precio del MARTES toca un nivel clave y ya CONFIRMÓ
30pts de reacción → ¿cuánto más se mueve? (segunda ola)

Niveles estudiados:
  - Monday LOW / Monday HIGH
  - Overnight LOW / Overnight HIGH (6PM→9:20AM = VAL/VAH proxy)
  - Overnight MID (POC proxy)
  - VWAP NY

No importa dirección inicial.
Solo importa: toca nivel → reacciona → ¿cuánto más?
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

BG='#0a0a16'; PANEL='#0d0d1a'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; SOFT='#94a3b8'; DIM='#475569'
ORG='#f97316'; WHITE='#f1f5f9'; TEAL='#14b8a6'; PRP='#a78bfa'

# ═══════════════════════════════════════════════════════════════════
# 1. CARGAR TODOS LOS DATOS DE 15MIN (incluye overnight)
# ═══════════════════════════════════════════════════════════════════
def et_offset(d_raw):
    for start,end in [
        (date(2019,3,10),date(2019,11,3)),(date(2020,3,8),date(2020,11,1)),
        (date(2021,3,14),date(2021,11,7)),(date(2022,3,13),date(2022,11,6)),
        (date(2023,3,12),date(2023,11,5)),(date(2024,3,10),date(2024,11,3)),
        (date(2025,3,9),date(2025,11,2)),(date(2026,3,8),date(2099,1,1)),
    ]:
        if start <= d_raw < end: return 4
    return 5

all_bars = []
with open('data/research/nq_15m_intraday.csv') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            off = et_offset(raw.date())
            et  = raw - timedelta(hours=off)
            all_bars.append({
                'et':et,'date':et.date(),
                'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close']),
                'v':float(r.get('Volume',0) or 0),
            })
        except: pass
all_bars.sort(key=lambda x:x['et'])
print(f"Total bars: {len(all_bars)}")

# Índice por fecha
bars_by_date = defaultdict(list)
for b in all_bars:
    bars_by_date[b['date']].append(b)

def get_bars(d, h_start, m_start, h_end, m_end):
    """Barras de un día en rango horario ET"""
    result = []
    for b in bars_by_date.get(d, []):
        t = b['et'].hour * 60 + b['et'].minute
        if (h_start*60+m_start) <= t < (h_end*60+m_end):
            result.append(b)
    return sorted(result, key=lambda x:x['et'])

def get_overnight(tue):
    """6PM ET del lunes → 9:20AM ET del martes"""
    mon = tue - timedelta(days=1)
    bars = []
    # Lunes 18:00 → 23:59
    for b in bars_by_date.get(mon, []):
        if b['et'].hour >= 18:
            bars.append(b)
    # Martes 00:00 → 9:20
    for b in bars_by_date.get(tue, []):
        t = b['et'].hour*60+b['et'].minute
        if t < 9*60+20:
            bars.append(b)
    return sorted(bars, key=lambda x:x['et'])

# ═══════════════════════════════════════════════════════════════════
# 2. FUNCIÓN PRINCIPAL: detectar toque + medir reacción
# ═══════════════════════════════════════════════════════════════════
CONFIRM_PTS = 30   # puntos mínimos de reacción para "confirmar"
TOUCH_ZONE  = 10   # margen para "tocó el nivel" (±10pts)

def measure_reaction(ny_bars, level, direction):
    """
    Cuando precio toca 'level' (±TOUCH_ZONE),
    direction='long'  → rebote hacia arriba
    direction='short' → rebote hacia abajo
    
    Devuelve: lista de magnitudes de segunda ola tras confirmación
    """
    reactions = []
    n = len(ny_bars)
    i = 0
    while i < n:
        b = ny_bars[i]
        touched = False
        if direction == 'long' and b['l'] <= level + TOUCH_ZONE:
            touched = True
        elif direction == 'short' and b['h'] >= level - TOUCH_ZONE:
            touched = True

        if touched:
            touch_price = level
            # Buscar confirmación: 30pts en la dirección correcta en las próximas 4 barras
            confirmed = False
            confirm_bar = i
            for j in range(i+1, min(i+6, n)):
                if direction == 'long' and ny_bars[j]['c'] >= touch_price + CONFIRM_PTS:
                    confirmed = True; confirm_bar = j; break
                elif direction == 'short' and ny_bars[j]['c'] <= touch_price - CONFIRM_PTS:
                    confirmed = True; confirm_bar = j; break

            if confirmed:
                # Medir cuánto más se mueve después de la confirmación
                entry_price = touch_price + (CONFIRM_PTS if direction=='long' else -CONFIRM_PTS)
                max_move = 0
                for k in range(confirm_bar+1, min(confirm_bar+20, n)):
                    if direction == 'long':
                        move = ny_bars[k]['h'] - entry_price
                    else:
                        move = entry_price - ny_bars[k]['l']
                    if move > max_move: max_move = move
                reactions.append(round(max_move, 1))
            i = confirm_bar + 1 if touched else i + 1
        else:
            i += 1
    return reactions

# ═══════════════════════════════════════════════════════════════════
# 3. ESTUDIAR TODOS LOS MARTES
# ═══════════════════════════════════════════════════════════════════
results = {
    'mon_low_long':   [],
    'mon_high_short': [],
    'ov_low_long':    [],
    'ov_high_short':  [],
    'ov_mid_long':    [],
    'ov_mid_short':   [],
}

tue_count = 0
for d in sorted(bars_by_date.keys()):
    if d.weekday() != 1: continue
    mon = d - timedelta(days=1)

    # NY bars del martes (9:30 → 16:00)
    ny_bars = get_bars(d, 9, 30, 16, 0)
    # Lunes NY
    mon_ny  = get_bars(mon, 9, 30, 16, 0)
    # Overnight
    ov_bars = get_overnight(d)

    if len(ny_bars) < 8 or len(mon_ny) < 4: continue

    # Niveles
    mon_low  = min(b['l'] for b in mon_ny)
    mon_high = max(b['h'] for b in mon_ny)
    ov_low   = min(b['l'] for b in ov_bars) if ov_bars else None
    ov_high  = max(b['h'] for b in ov_bars) if ov_bars else None
    ov_mid   = (ov_low + ov_high) / 2 if ov_low and ov_high else None

    # Medir reacciones
    results['mon_low_long']   += measure_reaction(ny_bars, mon_low,   'long')
    results['mon_high_short'] += measure_reaction(ny_bars, mon_high,  'short')
    if ov_low:
        results['ov_low_long']  += measure_reaction(ny_bars, ov_low,  'long')
    if ov_high:
        results['ov_high_short']+= measure_reaction(ny_bars, ov_high, 'short')
    if ov_mid:
        results['ov_mid_long']  += measure_reaction(ny_bars, ov_mid,  'long')
        results['ov_mid_short'] += measure_reaction(ny_bars, ov_mid,  'short')

    tue_count += 1

print(f"\nMartes analizados: {tue_count}")
print(f"\n{'Nivel':<22} {'n':>5} {'avg':>7} {'med':>7} {'≥50%':>7} {'≥100%':>7} {'≥150%':>7} {'max':>7}")
print("-"*68)

labels = {
    'mon_low_long':   'Mon LOW → LONG',
    'mon_high_short': 'Mon HIGH → SHORT',
    'ov_low_long':    'OvN LOW → LONG',
    'ov_high_short':  'OvN HIGH → SHORT',
    'ov_mid_long':    'OvN MID → LONG',
    'ov_mid_short':   'OvN MID → SHORT',
}

stats = {}
for key, vals in results.items():
    if not vals:
        stats[key] = None; continue
    n_    = len(vals)
    avg_  = round(np.mean(vals), 1)
    med_  = round(np.median(vals), 1)
    p50   = round(sum(1 for v in vals if v >= 50)  / n_ * 100, 1)
    p100  = round(sum(1 for v in vals if v >= 100) / n_ * 100, 1)
    p150  = round(sum(1 for v in vals if v >= 150) / n_ * 100, 1)
    mx    = round(max(vals), 1)
    stats[key] = {'n':n_,'avg':avg_,'med':med_,'p50':p50,'p100':p100,'p150':p150,'max':mx,'vals':vals}
    print(f"  {labels[key]:<20} {n_:>5} {avg_:>7.1f} {med_:>7.1f} {p50:>6.0f}% {p100:>6.0f}% {p150:>6.0f}% {mx:>7.1f}")

# ═══════════════════════════════════════════════════════════════════
# 4. FIGURA
# ═══════════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(28, 20), facecolor=BG)
fig.suptitle(
    f'MARTES NQ — REACCIÓN EN NIVELES CLAVE (tras confirmar {CONFIRM_PTS}pts)\n'
    f'"No adivines el primer movimiento — espera que toque el nivel y únete a la segunda ola"',
    color=GOLD, fontsize=14, fontweight='bold', y=0.999
)
gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.44, wspace=0.30,
                       left=0.05, right=0.97, top=0.96, bottom=0.04)

LEVEL_ORDER = [
    ('mon_low_long',   'Mon LOW → LONG\n(rebote desde bajo de lunes)', GRN),
    ('mon_high_short', 'Mon HIGH → SHORT\n(techo del lunes → baja)', RED),
    ('ov_low_long',    'Overnight LOW → LONG\n(VAL proxy — rebote)', TEAL),
    ('ov_high_short',  'Overnight HIGH → SHORT\n(VAH proxy — techo)', ORG),
    ('ov_mid_long',    'Overnight MID → LONG\n(POC proxy — soporte)', BLU),
    ('ov_mid_short',   'Overnight MID → SHORT\n(POC proxy — resistencia)', PRP),
]

for idx, (key, title, color) in enumerate(LEVEL_ORDER):
    row, col = divmod(idx, 3)
    ax = fig.add_subplot(gs[row, col]); ax.set_facecolor(PANEL2)
    st = stats.get(key)
    if not st:
        ax.text(0.5, 0.5, 'sin datos', ha='center', va='center', color=SOFT, transform=ax.transAxes)
        ax.set_title(title, color=GOLD, fontsize=10, fontweight='bold')
        continue

    vals = st['vals']
    cap  = 400  # limitar outliers en el histograma
    vals_cap = [min(v, cap) for v in vals]
    bins = np.arange(0, cap+50, 25)
    ax.hist(vals_cap, bins=bins, color=color, alpha=0.80, edgecolor=BG, linewidth=0.5)

    # Líneas de referencia
    for lvl, lbl, lc in [(50,'50pts','white'),(100,'100pts',GOLD),(150,'150pts',ORG)]:
        ax.axvline(lvl, color=lc, lw=1.5, ls='--', alpha=0.7, label=f'{lbl}: {st["p"+str(lvl)]:.0f}%')
    ax.axvline(st['med'], color=color, lw=2.5, ls='-', alpha=0.9, label=f'Med={st["med"]:.0f}pts')

    # Cuadro stats
    txt = (f"n={st['n']}  avg={st['avg']:.0f}pts\n"
           f"Mediana={st['med']:.0f}pts\n"
           f"≥50pts:  {st['p50']:.0f}%\n"
           f"≥100pts: {st['p100']:.0f}%\n"
           f"≥150pts: {st['p150']:.0f}%")
    ax.text(0.97, 0.97, txt, transform=ax.transAxes, fontsize=9.5,
            color=WHITE, va='top', ha='right',
            bbox=dict(boxstyle='round', facecolor='#0a0a20', edgecolor=color, alpha=0.9))

    ax.set_title(title, color=GOLD, fontsize=10.5, fontweight='bold')
    ax.set_xlabel(f'Puntos de segunda ola (tras +{CONFIRM_PTS}pts de confirmación)', color=SOFT, fontsize=8.5)
    ax.set_ylabel('N casos', color=SOFT, fontsize=8.5)
    ax.legend(fontsize=8, facecolor=BG, labelcolor=WHITE, loc='upper right')
    ax.tick_params(colors=SOFT)
    [ax.spines[s].set_visible(False) for s in ['top', 'right']]

# ── Panel de resumen ──────────────────────────────────────────────
ax_sum = fig.add_subplot(gs[2, :]); ax_sum.set_facecolor('#07070f'); ax_sum.axis('off')
ax_sum.set_xlim(0, 28); ax_sum.set_ylim(0, 10)

ax_sum.text(14, 9.6,
    'RANKING: ¿QUÉ NIVEL DA MÁS PUNTOS DE SEGUNDA OLA? (confirma 30pts → cuánto más sigue)',
    ha='center', fontsize=12, fontweight='bold', color=GOLD, va='center')

# Ordenar por mediana descendente
ranked = [(key, stats[key], labels[key]) for key in results if stats.get(key)]
ranked.sort(key=lambda x: -x[1]['med'])

col_headers = ['Ranking', 'Nivel', 'Casos', 'Mediana', 'Promedio', '≥100pts', '≥150pts', 'Veredicto']
col_xs = [0.3, 2.5, 9.5, 12.0, 15.0, 18.2, 21.0, 23.5]
for h, x in zip(col_headers, col_xs):
    ax_sum.text(x, 8.9, h, fontsize=10, color=GOLD, fontweight='bold', va='center')
ax_sum.plot([0.2, 27.8], [8.6, 8.6], color=DIM, lw=0.8)

medals = ['🥇', '🥈', '🥉', '4°', '5°', '6°']
y_r = 8.1
for rank, (key, st, lbl) in enumerate(ranked[:6]):
    med_ = st['med']; p100_ = st['p100']; p150_ = st['p150']
    verdict = ('EXCELENTE' if med_ >= 120 and p100_ >= 60
               else 'MUY BUENO' if med_ >= 80 and p100_ >= 45
               else 'BUENO'    if med_ >= 50
               else 'REGULAR')
    c_ = GRN if 'EXCELENTE' in verdict else (TEAL if 'MUY' in verdict else (BLU if 'BUENO' == verdict else SOFT))
    for txt, x in zip(
        [medals[rank], lbl, str(st['n']), f"{med_:.0f}pts", f"{st['avg']:.0f}pts",
         f"{p100_:.0f}%", f"{p150_:.0f}%", verdict],
        col_xs
    ):
        fw = 'bold' if txt in [f"{med_:.0f}pts", verdict] else 'normal'
        ax_sum.text(x, y_r, txt, fontsize=9.5,
                    color=c_ if txt in [f"{med_:.0f}pts", verdict, lbl] else SOFT,
                    fontweight=fw, va='center')
    y_r -= 0.82

# Nota al pie
ax_sum.text(14, 0.3,
    f'Metodología: Toca nivel ±{TOUCH_ZONE}pts → confirma {CONFIRM_PTS}pts en dirección → mide cuánto más sigue | {tue_count} martes (2019-2026)',
    ha='center', fontsize=8.5, color=DIM, style='italic', va='center')

out = 'martes_reaccion_niveles.png'
plt.savefig(out, dpi=120, bbox_inches='tight', facecolor=BG)
plt.close()
print(f'\nGrafica: {out}')
