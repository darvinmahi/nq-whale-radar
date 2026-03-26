"""
CHART_STYLE_DEEPCHARTS.PY  ─  v3 FINAL
Estilo ultra-pulido inspirado en deepcharts.io
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib.patheffects as pe
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.patches import FancyBboxPatch, Circle
import matplotlib.colors as mcolors
import os

# ═══════════════════════════════════════════════════════════════════
#  PALETA — DeepCharts Neon / Cyberpunk
# ═══════════════════════════════════════════════════════════════════
class DC:
    BG          = "#06030f"
    PANEL       = "#0b0622"
    BORDER      = "#1e0d45"
    GRID        = "#130830"

    BULL        = "#00ff55"
    BULL_BODY   = "#00dd44"
    BULL_WICK   = "#00ff77"
    BEAR        = "#ff1a4b"
    BEAR_BODY   = "#e0003a"
    BEAR_WICK   = "#ff4466"

    POC         = "#facc15"
    VAH         = "#a78bfa"
    VAL         = "#c084fc"
    VP_ZONE     = "#4c1d95"

    EMA1        = "#00e5ff"
    EMA2        = "#7c3aed"
    VWAP        = "#f59e0b"

    TEXT        = "#ffffff"
    LABEL       = "#8b7fc8"
    CYAN        = "#00e5ff"
    GOLD        = "#facc15"
    VIOLET      = "#7c3aed"
    ORANGE      = "#fb923c"

    GOOD        = "#00ff55"
    BAD         = "#ff1a4b"
    NEUTRAL     = "#8b7fc8"

    GLOW_VIOLET = "#5b21b6"


# ═══════════════════════════════════════════════════════════════════
#  FONDO RADIAL CON GLOW VIOLETA (firma DeepCharts)
# ═══════════════════════════════════════════════════════════════════
def _add_radial_glow(ax, color="#3b0d6e", intensity=0.40, n_rings=22):
    ax.set_facecolor(DC.PANEL)
    cx, cy = 0.5, 0.5
    radii  = np.linspace(0.0, 0.75, n_rings)
    alphas = np.linspace(intensity, 0.0, n_rings)
    for r, a in zip(reversed(radii), reversed(alphas)):
        c = Circle((cx, cy), r,
                   transform=ax.transAxes,
                   color=color, alpha=a * 0.55, zorder=0,
                   linewidth=0)
        ax.add_patch(c)


# ═══════════════════════════════════════════════════════════════════
#  APLICAR ESTILO GLOBAL
# ═══════════════════════════════════════════════════════════════════
def apply_dc_style(fig, axes_list=None, glow=True):
    fig.set_facecolor(DC.BG)
    if not axes_list:
        return
    for ax in axes_list:
        if glow:
            _add_radial_glow(ax)
        else:
            ax.set_facecolor(DC.PANEL)
        ax.tick_params(colors=DC.LABEL, labelsize=8, length=3, width=0.6)
        ax.xaxis.label.set_color(DC.LABEL)
        ax.yaxis.label.set_color(DC.LABEL)
        ax.yaxis.set_tick_params(which='both', right=False)
        ax.grid(axis='y', color=DC.GRID, lw=0.55, ls=':', alpha=0.9)
        ax.grid(axis='x', color=DC.GRID, lw=0.30, ls=':', alpha=0.5)
        for sp in ax.spines.values():
            sp.set_color(DC.BORDER)
            sp.set_linewidth(0.8)


# ═══════════════════════════════════════════════════════════════════
#  VELAS (ultra-neon)
# ═══════════════════════════════════════════════════════════════════
def candle_velas(ax, opens, closes, highs, lows, width=0.70):
    n = len(opens)
    for i in range(n):
        bull    = float(closes[i]) >= float(opens[i])
        body_lo = min(float(opens[i]), float(closes[i]))
        body_hi = max(float(opens[i]), float(closes[i]))
        body_h  = max(body_hi - body_lo, 0.20)
        fill, edge, wk = (DC.BULL_BODY, DC.BULL, DC.BULL_WICK) if bull \
                    else (DC.BEAR_BODY, DC.BEAR, DC.BEAR_WICK)

        # Mecha
        ax.plot([i, i], [float(lows[i]), float(highs[i])],
                color=wk, lw=1.0, zorder=3, solid_capstyle='round')
        # Cuerpo
        rect = plt.Rectangle((i - width/2, body_lo), width, body_h,
                              facecolor=fill, edgecolor=edge,
                              lw=0.9, zorder=4, alpha=0.94)
        ax.add_patch(rect)


# ═══════════════════════════════════════════════════════════════════
#  BARRAS DE VOLUMEN
# ═══════════════════════════════════════════════════════════════════
def volume_bars(ax, opens, closes, volumes, alpha=0.72, glow=True):
    n = len(opens)
    cols = [DC.BULL if float(closes[i]) >= float(opens[i]) else DC.BEAR for i in range(n)]
    ax.bar(np.arange(n), volumes, color=cols, alpha=alpha,
           width=0.70, linewidth=0, zorder=3)
    if glow:
        _add_radial_glow(ax, intensity=0.22)
    else:
        ax.set_facecolor(DC.PANEL)
    ax.set_yticks([])
    ax.set_ylabel("VOL", color=DC.LABEL, fontsize=7, labelpad=2)
    for sp in ax.spines.values():
        sp.set_color(DC.BORDER)
    ax.grid(axis='x', color=DC.GRID, lw=0.25, ls=':', alpha=0.5)


# ═══════════════════════════════════════════════════════════════════
#  LÍNEAS VP: VAH / POC / VAL
# ═══════════════════════════════════════════════════════════════════
def draw_vp_lines(ax, vah, poc, val, n_candles, label=True):
    extra = n_candles + 1.2
    if vah:
        ax.axhline(vah, color=DC.VAH, lw=1.3, ls='--', alpha=0.85, zorder=2)
        if label:
            ax.text(extra, vah, f"VAH {vah:.0f}",
                    color=DC.VAH, fontsize=7.5, va='bottom', fontweight='bold',
                    fontfamily='monospace')
    if poc:
        ax.axhline(poc, color=DC.POC, lw=2.5, ls='-', alpha=1.0, zorder=2)
        if label:
            ax.text(extra, poc, f"POC {poc:.0f}",
                    color=DC.POC, fontsize=8.5, va='bottom', fontweight='bold',
                    fontfamily='monospace')
    if val:
        ax.axhline(val, color=DC.VAL, lw=1.3, ls='--', alpha=0.85, zorder=2)
        if label:
            ax.text(extra, val, f"VAL {val:.0f}",
                    color=DC.VAL, fontsize=7.5, va='top', fontweight='bold',
                    fontfamily='monospace')
    if vah and val:
        ax.axhspan(val, vah, alpha=0.06, color=DC.VP_ZONE, zorder=1)


# ═══════════════════════════════════════════════════════════════════
#  LÍNEA DE EVENTO
# ═══════════════════════════════════════════════════════════════════
def event_vline(ax, x_idx, label, color=None, ylim=None, y_frac=0.95):
    color = color or DC.CYAN
    ax.axvline(x_idx, color=color, lw=1.8, ls='--', alpha=0.88, zorder=6)
    if ylim:
        yrange = ylim[1] - ylim[0]
        ypos   = ylim[0] + yrange * y_frac
        ax.text(x_idx + 0.6, ypos, f" {label}",
                color=color, fontsize=8.0, fontweight='bold',
                fontfamily='monospace', va='top',
                bbox=dict(boxstyle='round,pad=0.35',
                          facecolor=DC.BG, edgecolor=color,
                          alpha=0.90, linewidth=1.3))


# ═══════════════════════════════════════════════════════════════════
#  BADGE DE DATOS ECONÓMICOS
# ═══════════════════════════════════════════════════════════════════
def news_badge(ax, name, actual, fcst, prev, unit="K",
               x=0.01, y=0.985, fontsize=8.5):
    diff   = actual - fcst
    color  = DC.GOOD if diff < 0 else (DC.BAD if diff > 0 else DC.NEUTRAL)
    sign   = "MEJOR" if diff < 0 else ("PEOR" if diff > 0 else "EN LÍNEA")
    t      = ax.transAxes
    fs     = fontsize
    ax.text(x,       y,        name,
            color=DC.LABEL, fontsize=fs-1, va='top', transform=t, fontfamily='monospace')
    ax.text(x+0.08,  y,        f"{actual:,.0f}{unit}",
            color=color, fontsize=fs+3, va='top', transform=t,
            fontweight='bold', fontfamily='monospace')
    ax.text(x+0.20,  y-0.01,   f"FCT {fcst:,.0f}{unit}",
            color=DC.LABEL, fontsize=fs-1.5, va='top', transform=t, fontfamily='monospace')
    ax.text(x+0.30,  y-0.01,   f"PRV {prev:,.0f}{unit}",
            color=DC.LABEL, fontsize=fs-1.5, va='top', transform=t, fontfamily='monospace')
    ax.text(x+0.41,  y-0.005,  sign,
            color=color, fontsize=fs-0.5, va='top', transform=t,
            fontweight='bold', fontfamily='monospace')


# ═══════════════════════════════════════════════════════════════════
#  TÍTULO / WATERMARK DEEPCHARTS
# ═══════════════════════════════════════════════════════════════════
def dc_header(fig, title, subtitle="", watermark="NQ WHALE RADAR"):
    # Título principal con glow violeta sutil
    fig.text(0.012, 0.985, title,
             ha='left', va='top', fontsize=15, fontweight='bold',
             color=DC.TEXT, fontfamily='monospace',
             path_effects=[pe.Stroke(linewidth=4, foreground=DC.GLOW_VIOLET, alpha=0.35),
                           pe.Normal()])
    if subtitle:
        fig.text(0.012, 0.958, subtitle,
                 ha='left', va='top', fontsize=9,
                 color=DC.LABEL, fontfamily='monospace')
    # Watermark centrado abajo
    fig.text(0.5, 0.012, watermark,
             ha='center', va='bottom', fontsize=7.5, alpha=0.22,
             color=DC.VIOLET, fontfamily='monospace', fontweight='bold')


# ═══════════════════════════════════════════════════════════════════
#  DEMO COMPLETA
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    np.random.seed(12)
    n  = 60
    px = 21480 + np.cumsum(np.random.randn(n) * 14)
    o  = px + np.random.randn(n) * 5
    c  = px + np.random.randn(n) * 5
    h  = np.maximum(o, c) + np.abs(np.random.randn(n) * 8)
    l  = np.minimum(o, c) - np.abs(np.random.randn(n) * 8)
    v  = np.abs(np.random.randn(n)) * 1400 + 700

    fig = plt.figure(figsize=(17, 9), facecolor=DC.BG)
    gs  = gridspec.GridSpec(2, 1, height_ratios=[5, 1],
                            hspace=0.025, top=0.93, bottom=0.06,
                            left=0.04, right=0.87)
    ax1 = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    apply_dc_style(fig, [ax1, ax2], glow=True)

    # Velas + indicadores
    candle_velas(ax1, o, c, h, l)

    # EMA fake
    ema20 = np.convolve(px, np.ones(12)/12, mode='same')
    ax1.plot(np.arange(n), ema20, color=DC.EMA1, lw=1.1, alpha=0.80, zorder=5, label="EMA 20")

    # Niveles VP
    draw_vp_lines(ax1, vah=21530, poc=21485, val=21420, n_candles=n)

    # Evento
    evt_x = 28
    ylim  = (l.min() - 18, h.max() + 35)
    event_vline(ax1, evt_x, "JOBLESS CLAIMS", ylim=ylim)

    # Badge de datos
    news_badge(ax1, "CLAIMS", actual=215, fcst=226, prev=221)

    # Zona sombreada de trampa (pre-evento)
    ax1.axvspan(evt_x - 5, evt_x, alpha=0.05, color=DC.BAD, zorder=1)
    ax1.text(evt_x - 4.5, ylim[0] + (ylim[1]-ylim[0])*0.08,
             "TRAMPA\nBAJISTA", color=DC.BAD, fontsize=7.5,
             fontweight='bold', fontfamily='monospace', alpha=0.75, va='bottom')

    ax1.set_xlim(-1, n + 10)
    ax1.set_ylim(*ylim)
    ax1.yaxis.tick_right()
    ax1.tick_params(axis='y', right=True, labelright=True, left=False, labelleft=False)

    # Volumen
    volume_bars(ax2, o, c, v, glow=True)
    ax2.set_xlim(-1, n + 10)
    plt.setp(ax1.get_xticklabels(), visible=False)

    # Eje X como tiempo (simulado)
    ticks = np.arange(0, n, 6)
    horas = [f"{8 + i//4}:{(i%4)*15:02d}" for i in range(0, n, 6)]
    ax2.set_xticks(ticks)
    ax2.set_xticklabels(horas, color=DC.LABEL, fontsize=8, fontfamily='monospace')

    # Header
    dc_header(fig,
              title="NQ  ·  5M  ·  2025-03-20",
              subtitle="Backtest Jueves — TRAMPA BAJISTA + JOBLESS CLAIMS",
              watermark="NQ WHALE RADAR  ©2025")

    # Leyenda mínima
    leg = ax1.legend(loc='lower right', framealpha=0, labelcolor=DC.LABEL,
                     fontsize=8, borderpad=0.3)

    os.makedirs("assets", exist_ok=True)
    out = "assets/demo_deepcharts_style.png"
    plt.savefig(out, dpi=155, bbox_inches='tight', facecolor=DC.BG)
    plt.close()
    print(f"✅  Guardado: {out}")
    print("    Ver: http://localhost:8085/assets/demo_deepcharts_style.png")
