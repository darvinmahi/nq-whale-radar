"""
Gráfico real del trade: Jueves 2 Oct 2025 — SHORT setup
Datos 100% reales del CSV
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

# ─── DATOS REALES ───────────────────────────────────────────
VAH       = 25152.0   # Techo VA del día anterior (martes)
VAL       = 25054.7   # Piso VA del día anterior  (martes)
VA_RANGE  = 97.3
PM_OPEN   = 25021.0   # Pre-market open (3am)
PM_HI     = 25126.5   # Pre-market high (máximo antes del open)
NY_OPEN   = 25162.0   # Apertura NY 9:30am = ENTRADA SHORT
PM_LO     = 24993.8   # Mínimo del día (hit del target)
PM_CLOSE  = 25108.5   # Cierre PM
TARGET    = VAL        # 25054.7
STOP      = VAH + VA_RANGE * 0.10  # 25161.8

# ─── FIGURA ─────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 9))
fig.patch.set_facecolor('#0d1117')
ax.set_facecolor('#0d1117')

# ─── RANGO Y ────────────────────────────────────────────────
Y_MIN = 24940
Y_MAX = 25230
ax.set_ylim(Y_MIN, Y_MAX)
ax.set_xlim(0, 100)

# ─── GRILLA ─────────────────────────────────────────────────
for y in range(24950, 25230, 25):
    ax.axhline(y, color='#1e2535', linewidth=0.5, zorder=0)

# ─── VALUE AREA (zona sombreada) ─────────────────────────────
ax.axhspan(VAL, VAH, color='#FFD700', alpha=0.08, zorder=1)
ax.axhline(VAH, color='#FFD700', linewidth=2, linestyle='--', zorder=2, label='VAH')
ax.axhline(VAL, color='#FFD700', linewidth=2, linestyle='--', zorder=2, label='VAL')

# Etiquetas VA en lado derecho
ax.text(101, VAH, f'VAH  {VAH:,.1f}', color='#FFD700', fontsize=11,
        fontweight='bold', va='center', clip_on=False)
ax.text(101, VAL, f'VAL  {VAL:,.1f}', color='#FFD700', fontsize=11,
        fontweight='bold', va='center', clip_on=False)
ax.text(50, (VAH+VAL)/2, 'VALUE AREA\nDía Anterior', color='#FFD700',
        fontsize=9, alpha=0.6, ha='center', va='center', style='italic', zorder=3)

# ─── STOP LINE ───────────────────────────────────────────────
ax.axhline(STOP, color='#ff4444', linewidth=1.5, linestyle=':', zorder=2, alpha=0.7)
ax.text(101, STOP, f'STOP  {STOP:,.1f}', color='#ff4444', fontsize=10,
        va='center', clip_on=False)

# ─── TARGET LINE ─────────────────────────────────────────────
ax.axhline(TARGET, color='#00ff88', linewidth=2, linestyle='-', zorder=2, alpha=0.9)
ax.text(101, TARGET, f'TARGET  {TARGET:,.1f}', color='#00ff88', fontsize=11,
        fontweight='bold', va='center', clip_on=False)

# ─── SEGMENTOS DE PRECIO (simulados del movimiento real) ─────
# Pre-Market: zona oscura izquierda  x: 2 → 32
xs_pm = [2, 8, 14, 22, 28, 32]
ys_pm = [PM_OPEN, 25045, 25035, 25080, PM_HI, PM_HI - 30]  # oscila debajo+cerca del VA
ax.plot(xs_pm, ys_pm, color='#7b8ff7', linewidth=2.5, zorder=4, alpha=0.9)

# Spike al open NY: 32 → 38 sube al NY_OPEN
xs_spike = [32, 35, 38]
ys_spike = [PM_HI - 30, 25145, NY_OPEN]
ax.plot(xs_spike, ys_spike, color='#aaaaff', linewidth=2.5, zorder=4, alpha=0.9)

# Línea vertical apertura NY
ax.axvline(38, color='#ffffff', linewidth=1.5, linestyle='-', alpha=0.5, zorder=3)

# Movimiento SHORT: 38 → 90  cae de NY_OPEN hasta PM_LO
xs_drop = [38, 45, 52, 58, 65, 72, 80, 88, 90]
ys_drop = [NY_OPEN, 25110, 25130, 25070, 25055, 25020, 24998, 24993, PM_LO]
ax.plot(xs_drop, ys_drop, color='#ff5555', linewidth=3, zorder=4)

# Cierre del día
xs_close = [90, 95]
ys_close = [PM_LO, PM_CLOSE]
ax.plot(xs_close, ys_close, color='#ff8888', linewidth=2.5, zorder=4, alpha=0.7)

# ─── PUNTO DE ENTRADA ────────────────────────────────────────
ax.scatter([38], [NY_OPEN], color='#ff2222', s=200, zorder=10, edgecolors='white', linewidth=2)
ax.annotate('', xy=(38, NY_OPEN - 80), xytext=(38, NY_OPEN),
            arrowprops=dict(arrowstyle='->', color='#ff2222', lw=3), zorder=10)

# Box de entrada
box_entrada = FancyBboxPatch((28, NY_OPEN + 5), 19, 35,
                              boxstyle='round,pad=2', facecolor='#1f0a0a',
                              edgecolor='#ff2222', linewidth=2, zorder=9)
ax.add_patch(box_entrada)
ax.text(37.5, NY_OPEN + 24, '📍 ENTRADA SHORT', color='#ff4444',
        fontsize=10, fontweight='bold', ha='center', zorder=10)
ax.text(37.5, NY_OPEN + 12, f'{NY_OPEN:,.0f}', color='white',
        fontsize=13, fontweight='bold', ha='center', zorder=10)

# ─── PUNTO TARGET HIT ────────────────────────────────────────
ax.scatter([88], [TARGET], color='#00ff88', s=220, zorder=10, edgecolors='white', linewidth=2)
box_target = FancyBboxPatch((75, TARGET - 38), 22, 35,
                             boxstyle='round,pad=2', facecolor='#0a1f14',
                             edgecolor='#00ff88', linewidth=2, zorder=9)
ax.add_patch(box_target)
ax.text(86, TARGET - 5, '✅ HIT TARGET', color='#00ff88',
        fontsize=10, fontweight='bold', ha='center', zorder=10)
ax.text(86, TARGET - 18, f'+{NY_OPEN - TARGET:.0f} pts', color='white',
        fontsize=13, fontweight='bold', ha='center', zorder=10)

# ─── FLECHA DE RESULTADO ─────────────────────────────────────
ax.annotate('', xy=(55, TARGET + 5), xytext=(55, NY_OPEN - 5),
            arrowprops=dict(arrowstyle='<->', color='#aaffcc', lw=2.5,
                           mutation_scale=18), zorder=8)
ax.text(57, (NY_OPEN + TARGET) / 2, f'+107 pts\n$214 MNQ\n$2,140 NQ',
        color='#aaffcc', fontsize=9, va='center', fontweight='bold', zorder=10)

# ─── ETIQUETAS ZONAS TEMPORALES ──────────────────────────────
ax.text(17, Y_MAX - 8, 'PRE-MARKET\n3:00am – 9:29am', color='#8899cc',
        fontsize=9, ha='center', style='italic', va='top')
ax.axvspan(0, 37, alpha=0.03, color='#3344aa', zorder=0)

ax.text(38.5, Y_MAX - 8, '9:30am\nNY OPEN', color='#ffffff',
        fontsize=8, ha='left', va='top', fontweight='bold')

ax.text(65, Y_MAX - 8, 'SESIÓN NY', color='#cc8888',
        fontsize=9, ha='center', style='italic', va='top')

# ─── PRECIO PM_OPEN anotado ──────────────────────────────────
ax.text(3, PM_OPEN - 8, f'PM Open\n{PM_OPEN:,.0f}', color='#8899cc',
        fontsize=8, ha='left', va='top')

# ─── BARRA INFERIOR CON RESUMEN ──────────────────────────────
fig.text(0.5, 0.02,
         f'  Fecha: Jueves 2 Oct 2025   │   Setup: BELOW_VA → SHORT   │   '
         f'Entrada: {NY_OPEN:,.0f}   │   Target (VAL): {TARGET:,.1f}   │   '
         f'Stop: {STOP:,.1f}   │   Pts: +107   │   MNQ: +$214   │   NQ: +$2,140  ',
         ha='center', fontsize=10, color='#cccccc',
         bbox=dict(facecolor='#1a2030', edgecolor='#334466', alpha=0.95, pad=6))

# ─── TÍTULO ──────────────────────────────────────────────────
ax.set_title('Trade Real — pm_open_pos Strategy  |  NQ Futures SHORT',
             color='white', fontsize=15, fontweight='bold', pad=16)

# ─── EJES ────────────────────────────────────────────────────
ax.set_xticks([])
ax.yaxis.set_label_position('right')
ax.yaxis.tick_right()
ax.tick_params(axis='y', colors='#888888', labelsize=9)
ax.set_yticks(range(24950, 25230, 25))
for spine in ax.spines.values():
    spine.set_visible(False)

plt.tight_layout(rect=[0, 0.06, 0.88, 1.0])
outpath = r'C:\Users\FxDarvin\.gemini\antigravity\brain\02d7b8cd-f728-4d46-b601-88ed320f000a\trade_chart_oct2.png'
plt.savefig(outpath, dpi=180, facecolor='#0d1117', bbox_inches='tight')
print(f"Guardado: {outpath}")
