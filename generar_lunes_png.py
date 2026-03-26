"""
generar_lunes_png.py
Genera imágenes PNG de velas 5min reales para cada sesión lunes.
Colores exactos del HTML: lunes_sesiones_5m.html
"""
import json, os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from datetime import datetime, timezone

# ── Colores del HTML ────────────────────────────────────────────
BG       = '#0d1117'
BG_FIG   = '#07090e'
GRID_C   = '#1e2532'
TEXT_C   = '#e2e8f0'
MUTED_C  = '#64748b'

UP_C     = '#22c55e'   # vela alcista
DN_C     = '#ef4444'   # vela bajista

VAH_C    = '#f97316'   # naranja VAH
POC_C    = '#facc15'   # amarillo POC (dashed)
VAL_C    = '#38bdf8'   # celeste VAL
EMA_C    = '#a78bfa'   # violeta EMA200
VWAP_C   = '#f59e0b'   # dorado VWAP (dashed)
NYOP_C   = '#ffffff'   # blanco NY Open (dotted)

VOL_UP   = (34/255, 197/255, 94/255,  0.25)
VOL_DN   = (239/255, 68/255, 68/255,  0.25)

# ── Cargar datos ─────────────────────────────────────────────────
with open('data/research/lunes_5m_data.json', encoding='utf-8') as f:
    sessions = json.load(f)
with open('data/research/lunes_levels.json', encoding='utf-8') as f:
    levels = json.load(f)

os.makedirs('data/images/lunes', exist_ok=True)

def to_et_label(iso, is_dst):
    """ISO → HH:MM ET string"""
    try:
        dt = datetime.fromisoformat(iso.replace('Z',''))
        off = 4 if is_dst else 5
        h = (dt.hour - off) % 24
        return f"{h:02d}:{dt.minute:02d}"
    except:
        return iso[11:16]

def compute_vwap(candles):
    cp, cv = 0.0, 0.0
    out = []
    for c in candles:
        tp = (c['h'] + c['l'] + c['c']) / 3
        v  = c.get('v', 1) or 1
        cp += tp * v
        cv += v
        out.append(cp / cv)
    return out

def draw_session(s, lv, output_path):
    candles = s['candles']
    n       = len(candles)
    date    = s['date']
    is_dst  = date >= '2026-03-08'
    isBull  = s['direction'] == 'BULLISH'

    opens  = [c['o'] for c in candles]
    highs  = [c['h'] for c in candles]
    lows   = [c['l'] for c in candles]
    closes = [c['c'] for c in candles]
    vols   = [c.get('v', 0) or 0 for c in candles]
    xs     = np.arange(n)

    vwap = compute_vwap(candles)

    fig, (ax, axv) = plt.subplots(
        2, 1, figsize=(12, 5.5),
        facecolor=BG_FIG,
        gridspec_kw={'height_ratios': [5, 1], 'hspace': 0.04}
    )

    for ax_ in (ax, axv):
        ax_.set_facecolor(BG)
        ax_.tick_params(colors=MUTED_C, labelsize=7)
        ax_.spines[:].set_color(GRID_C)
        ax_.grid(color=GRID_C, linewidth=0.4, alpha=0.7)

    # ── Velas ─────────────────────────────────────────────────
    W = 0.6
    for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
        col = UP_C if c >= o else DN_C
        # mecha
        ax.plot([i, i], [l, h], color=col, linewidth=0.8, solid_capstyle='round')
        # body
        yb, yt = sorted([o, c])
        ht = max(yt - yb, 0.5)
        ax.add_patch(mpatches.FancyBboxPatch(
            (i - W/2, yb), W, ht,
            boxstyle='square,pad=0',
            facecolor=col, edgecolor=col, linewidth=0
        ))

    # ── Volumen ───────────────────────────────────────────────
    for i, (o, c, v) in enumerate(zip(opens, closes, vols)):
        col = VOL_UP if c >= o else VOL_DN
        axv.bar(i, v, width=0.8, color=col, linewidth=0)

    # ── Niveles horizontales ──────────────────────────────────
    prng = [min(lows), max(highs)]
    def hline(val, color, lw, ls, label, alpha=1.0):
        if val is None: return
        ax.axhline(val, color=color, linewidth=lw, linestyle=ls, alpha=alpha,
                   label=label, zorder=3)
        ax.text(n - 0.3, val, f' {val:.2f}', color=color,
                fontsize=6.5, va='center', ha='left',
                fontfamily='monospace', zorder=4)

    # NY Open
    ny = lv.get('ny_open') or s.get('ny_open')
    hline(ny,       NYOP_C,  0.8, ':', 'NY Open', alpha=0.4)
    # VAH
    hline(lv.get('vah'), VAH_C,  1.0, '-',   'VAH')
    # POC (dashed)
    hline(lv.get('poc'), POC_C,  1.2, '--',  'POC')
    # VAL
    hline(lv.get('val'), VAL_C,  1.0, '-',   'VAL')
    # EMA 200
    hline(lv.get('ema200'), EMA_C, 1.0, '-', 'EMA200')
    # VWAP
    ax.plot(xs, vwap, color=VWAP_C, linewidth=1.0, linestyle='--', alpha=0.75,
            label='VWAP', zorder=3)

    # ── X axis labels ─────────────────────────────────────────
    step = max(1, n // 8)
    ticks = xs[::step]
    lbls  = [to_et_label(candles[i]['time'], is_dst) for i in ticks]
    ax.set_xticks([])
    axv.set_xticks(ticks)
    axv.set_xticklabels(lbls, color=MUTED_C, fontsize=7, fontfamily='monospace')
    axv.set_xlim(-1, n)
    ax.set_xlim(-1, n)

    # ── Y range con padding ───────────────────────────────────
    pad = (prng[1] - prng[0]) * 0.04
    ax.set_ylim(prng[0] - pad, prng[1] + pad)
    ax.yaxis.set_tick_params(labelsize=7)

    # ── Títulos / header ──────────────────────────────────────
    dir_sym = '▲ BULL' if isBull else '▼ BEAR'
    dir_col = UP_C if isBull else DN_C
    ny_range = s.get('ny_range', max(highs) - min(lows))
    cot = s.get('cot', '—')

    fig.text(0.012, 0.97, f'{date}', color=TEXT_C,
             fontsize=14, fontweight='bold', fontfamily='monospace', va='top')
    fig.text(0.18,  0.97, dir_sym, color=dir_col,
             fontsize=11, fontweight='bold', va='top')
    fig.text(0.28,  0.97, f'Rango NY: {ny_range:.1f} pts',
             color=TEXT_C, fontsize=9, va='top')
    fig.text(0.50,  0.97, f'COT: {cot}',
             color='#f59e0b', fontsize=9, fontfamily='monospace', va='top')
    fig.text(0.62,  0.97, f'5 min · NY Session · {n} velas',
             color=MUTED_C, fontsize=8, va='top')

    # ── Leyenda ───────────────────────────────────────────────
    legend_els = [
        Line2D([0],[0], color=VAH_C,  lw=1.5, label='VAH'),
        Line2D([0],[0], color=POC_C,  lw=1.5, linestyle='--', label='POC'),
        Line2D([0],[0], color=VAL_C,  lw=1.5, label='VAL'),
        Line2D([0],[0], color=EMA_C,  lw=1.5, label='EMA200'),
        Line2D([0],[0], color=VWAP_C, lw=1.5, linestyle='--', label='VWAP'),
        Line2D([0],[0], color=NYOP_C, lw=1.0, linestyle=':', alpha=0.5, label='NY Open'),
    ]
    ax.legend(handles=legend_els, loc='upper left',
              facecolor='#111827', edgecolor=GRID_C,
              fontsize=7, framealpha=0.85,
              labelcolor=TEXT_C, ncol=6)

    ax.tick_params(labelbottom=False)
    axv.set_ylabel('Vol', color=MUTED_C, fontsize=7)
    axv.yaxis.set_tick_params(labelsize=0)

    plt.savefig(output_path, dpi=130, bbox_inches='tight',
                facecolor=BG_FIG, edgecolor='none')
    plt.close(fig)
    print(f'  ✓ {output_path}')

# ── Generar UNA imagen (demo) ─────────────────────────────────────
s0   = sessions[0]   # 2026-01-26
d0   = s0['date']
lv0  = levels.get(d0, {})
out0 = f"data/images/lunes/lunes_{d0.replace('-','')}.png"
draw_session(s0, lv0, out0)
print("DONE:", out0)
