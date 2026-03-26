"""
Chart: Open vs Value Area — Real Thursday NQ Data
Generates a grid of 10 real Thursdays showing open position vs VAL/POC/VAH
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np

# ── DATOS REALES DEL BACKTEST ────────────────────────────────────────────────
thursdays = [
    {"date": "2026-01-08", "pattern": "EXPANSION_L",  "direction": "BEARISH",  "ny_open": 25786.0,  "ny_close": 25648.25, "r_high": 25849.75, "r_low": 25670.0,  "val": 25755.38, "poc": 25773.36, "vah": 25805.71, "poc_hit": True,  "val_hit": True},
    {"date": "2026-01-15", "pattern": "EXPANSION_H",  "direction": "BEARISH",  "ny_open": 25924.75, "ny_close": 25915.0,  "r_high": 25894.0,  "r_low": 25562.5,  "val": 25576.1,  "poc": 25607.18, "vah": 25646.03, "poc_hit": False, "val_hit": False},
    {"date": "2026-01-22", "pattern": "ROTATION_POC", "direction": "BEARISH",  "ny_open": 25729.0,  "ny_close": 25681.25, "r_high": 25715.75, "r_low": 25483.75, "val": 25556.71, "poc": 25566.95, "vah": 25569.51, "poc_hit": True,  "val_hit": True},
    {"date": "2026-01-29", "pattern": "NEWS_DRIVE",   "direction": "BEARISH",  "ny_open": 26133.25, "ny_close": 25709.5,  "r_high": 26296.0,  "r_low": 26085.5,  "val": 26168.65, "poc": 26170.75, "vah": 26187.59, "poc_hit": True,  "val_hit": True},
    {"date": "2026-02-05", "pattern": "NEWS_DRIVE",   "direction": "BEARISH",  "ny_open": 24770.25, "ny_close": 24783.5,  "r_high": 25169.0,  "r_low": 24707.5,  "val": 24977.48, "poc": 25028.24, "vah": 25120.54, "poc_hit": False, "val_hit": True},
    {"date": "2026-02-12", "pattern": "NEWS_DRIVE",   "direction": "BEARISH",  "ny_open": 25346.25, "ny_close": 24875.25, "r_high": 25419.75, "r_low": 25206.0,  "val": 25309.67, "poc": 25341.73, "vah": 25369.52, "poc_hit": True,  "val_hit": True},
    {"date": "2026-02-19", "pattern": "SWEEP_L_RETURN","direction": "NEUTRAL", "ny_open": 24833.75, "ny_close": 24842.75, "r_high": 25054.0,  "r_low": 24798.0,  "val": 24929.84, "poc": 24973.36, "vah": 24998.96, "poc_hit": True,  "val_hit": True},
    {"date": "2026-02-26", "pattern": "NEWS_DRIVE",   "direction": "BEARISH",  "ny_open": 25341.25, "ny_close": 25001.5,  "r_high": 25418.25, "r_low": 25264.75, "val": 25291.61, "poc": 25300.82, "vah": 25319.24, "poc_hit": True,  "val_hit": True},
    {"date": "2026-03-05", "pattern": "NEWS_DRIVE",   "direction": "BULLISH",  "ny_open": 24987.75, "ny_close": 25005.75, "r_high": 25250.0,  "r_low": 24973.25, "val": 25030.25, "poc": 25087.7,  "vah": 25116.43, "poc_hit": True,  "val_hit": True},
    {"date": "2026-03-12", "pattern": "NEWS_DRIVE",   "direction": "BEARISH",  "ny_open": 24775.75, "ny_close": 24688.0,  "r_high": 24949.25, "r_low": 24695.5,  "val": 24717.07, "poc": 24729.76, "vah": 24732.29, "poc_hit": True,  "val_hit": True},
]

def classify_open(ny_open, val, vah):
    if ny_open < val:
        return "BELOW_VA", "#ef4444"
    elif ny_open > vah:
        return "ABOVE_VA", "#22c55e"
    else:
        return "INSIDE_VA", "#eab308"

PATTERN_EMOJIS = {
    "NEWS_DRIVE": "ND", "SWEEP_L_RETURN": "SLR", "EXPANSION_L": "EL",
    "EXPANSION_H": "EH", "ROTATION_POC": "RP"
}
PATTERN_COLORS = {
    "NEWS_DRIVE": "#f97316", "SWEEP_L_RETURN": "#3b82f6", "EXPANSION_L": "#ef4444",
    "EXPANSION_H": "#22c55e", "ROTATION_POC": "#a855f7"
}

# ── FIGURE ───────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(22, 18), facecolor='#0d1117')
fig.suptitle('OPEN vs VALUE AREA — Jueves NQ Reales (10 Jueves)', 
             color='#e2e8f0', fontsize=18, fontweight='bold', y=0.98,
             fontfamily='monospace')

subtitle = 'Todos son Jueves de Noticias | Datos reales del backtest | VAL / POC / VAH del día anterior | Open NY 9:30 AM'
fig.text(0.5, 0.955, subtitle, ha='center', color='#64748b', fontsize=10, fontfamily='monospace')

# Legend
leg_items = [
    mpatches.Patch(color='#ef4444', label='BELOW_VA (Open < VAL)'),
    mpatches.Patch(color='#eab308', label='INSIDE_VA (Open entre VAL-VAH)'),
    mpatches.Patch(color='#22c55e', label='ABOVE_VA (Open > VAH)'),
    mpatches.Patch(color='#06b6d4', alpha=0.3, label='Value Area (70% volumen)'),
    mpatches.Patch(color='#fbbf24', label='POC (max volumen)'),
]
fig.legend(handles=leg_items, loc='lower center', ncol=5, 
           facecolor='#1e293b', edgecolor='#334155',
           labelcolor='#cbd5e1', fontsize=9, framealpha=0.9,
           bbox_to_anchor=(0.5, 0.01))

cols, rows = 5, 2
for i, d in enumerate(thursdays):
    ax = fig.add_subplot(rows, cols, i + 1)
    ax.set_facecolor('#0f172a')
    for spine in ax.spines.values():
        spine.set_color('#1e293b')

    # Price range for this chart: build a window around all levels
    all_prices = [d['r_high'], d['r_low'], d['val'], d['poc'], d['vah'], d['ny_open'], d['ny_close']]
    p_min, p_max = min(all_prices), max(all_prices)
    pad = (p_max - p_min) * 0.15
    y_min, y_max = p_min - pad, p_max + pad

    # Value Area shaded rectangle
    ax.axhspan(d['val'], d['vah'], alpha=0.18, color='#06b6d4', zorder=1)

    # VAH line
    ax.axhline(d['vah'], color='#f97316', linewidth=1.2, linestyle='--', alpha=0.9, zorder=2)
    ax.text(0.02, d['vah'], f"VAH {d['vah']:,.0f}", color='#f97316', fontsize=6.5,
            va='bottom', ha='left', fontfamily='monospace', transform=ax.get_yaxis_transform())

    # VAL line
    ax.axhline(d['val'], color='#f97316', linewidth=1.2, linestyle='--', alpha=0.9, zorder=2)
    ax.text(0.02, d['val'], f"VAL {d['val']:,.0f}", color='#f97316', fontsize=6.5,
            va='top', ha='left', fontfamily='monospace', transform=ax.get_yaxis_transform())

    # POC line (thicker, yellow)
    ax.axhline(d['poc'], color='#fbbf24', linewidth=2.0, linestyle='-', alpha=1.0, zorder=3)
    ax.text(0.98, d['poc'], f"POC {d['poc']:,.0f}", color='#fbbf24', fontsize=6.5,
            va='bottom', ha='right', fontfamily='monospace', transform=ax.get_yaxis_transform())

    # Draw a simple price bar: vertical line from r_low to r_high, with open/close ticks
    x_bar = 0.5  # center x (using axes units 0-1)
    ax.set_xlim(0, 1)
    ax.set_ylim(y_min, y_max)

    # High-Low bar
    bar_color = '#22c55e' if d['ny_close'] >= d['ny_open'] else '#ef4444'
    ax.plot([0.42, 0.42], [d['r_low'], d['r_high']], color='#475569', linewidth=1.5, zorder=4)

    # Candle body (open→close)
    body_bot = min(d['ny_open'], d['ny_close'])
    body_top = max(d['ny_open'], d['ny_close'])
    body_height = body_top - body_bot
    rect = mpatches.FancyBboxPatch((0.30, body_bot), 0.24, max(body_height, (y_max-y_min)*0.005),
                                    boxstyle="round,pad=0", linewidth=0,
                                    facecolor=bar_color, alpha=0.9, zorder=5,
                                    transform=ax.get_yaxis_transform() if False else ax.transData)
    # Use regular rectangle instead
    ax.fill_betweenx([body_bot, body_top], 0.30, 0.54, color=bar_color, alpha=0.9, zorder=5)

    # Open tick (horizontal left)
    ax.plot([0.22, 0.30], [d['ny_open'], d['ny_open']], color='#94a3b8', linewidth=1.5, zorder=6)
    # Close tick (horizontal right)
    ax.plot([0.54, 0.62], [d['ny_close'], d['ny_close']], color='#94a3b8', linewidth=1.5, zorder=6)

    # Open marker — big dot color-coded by BELOW/INSIDE/ABOVE
    va_status, va_color = classify_open(d['ny_open'], d['val'], d['vah'])
    ax.scatter([0.22], [d['ny_open']], color=va_color, s=80, zorder=10, 
               edgecolors='white', linewidth=0.8)

    # Arrow from open toward POC if poc_hit
    if d['poc_hit']:
        arrow_color = '#22c55e'
        dy = d['poc'] - d['ny_open']
        if abs(dy) > (y_max - y_min) * 0.005:
            ax.annotate('', xy=(0.42, d['poc']), xytext=(0.22, d['ny_open']),
                        arrowprops=dict(arrowstyle='->', color=arrow_color, lw=1.3),
                        zorder=8)

    # POC hit badge
    poc_txt = "[POC OK]" if d['poc_hit'] else "[POC X]"
    poc_c = '#22c55e' if d['poc_hit'] else '#ef4444'
    ax.text(0.98, 0.04, poc_txt, transform=ax.transAxes, color=poc_c,
            fontsize=7.5, fontweight='bold', ha='right', va='bottom', fontfamily='monospace')

    # Open vs VA badge
    ax.text(0.02, 0.97, va_status, transform=ax.transAxes, color=va_color,
            fontsize=7, fontweight='bold', ha='left', va='top', fontfamily='monospace')

    # Title
    pattern_color = PATTERN_COLORS.get(d['pattern'], '#94a3b8')
    emoji = PATTERN_EMOJIS.get(d['pattern'], '-')
    ax.set_title(f"{d['date']}\n{emoji} {d['pattern'].replace('_',' ')}", 
                 color=pattern_color, fontsize=8, fontweight='bold',
                 fontfamily='monospace', pad=4)

    # Jobless Claims label
    ax.text(0.02, 0.88, 'Jobless Claims', transform=ax.transAxes,
            color='#64748b', fontsize=6, ha='left', va='top', fontfamily='monospace')

    # Direction label
    dir_colors = {'BEARISH': '#ef4444', 'BULLISH': '#22c55e', 'NEUTRAL': '#eab308'}
    ax.text(0.5, 0.04, d['direction'], transform=ax.transAxes,
            color=dir_colors.get(d['direction'], '#94a3b8'),
            fontsize=7, fontweight='bold', ha='center', va='bottom', fontfamily='monospace')

    # Clean axes
    ax.set_xticks([])
    ax.tick_params(axis='y', labelsize=6, colors='#475569', labelright=False, labelleft=False)
    ax.yaxis.set_visible(False)

    # Range label top right
    ny_range = d['r_high'] - d['r_low']
    ax.text(0.98, 0.97, f"Rango: {ny_range:.0f}pts", transform=ax.transAxes,
            color='#64748b', fontsize=6.5, ha='right', va='top', fontfamily='monospace')

plt.tight_layout(rect=[0, 0.06, 1, 0.95])
out_path = r"C:\Users\FxDarvin\Desktop\PAgina\data\research\chart_open_vs_va_real.png"
plt.savefig(out_path, dpi=300, bbox_inches='tight', facecolor='#0d1117')
plt.close()
print("Chart saved OK -> " + out_path)
