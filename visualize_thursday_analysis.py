"""
Visualización del Backtest — Jueves News Day + Space Move
Genera 3 imágenes PNG + tabla detallada por fecha para verificación manual
"""

import json, os
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════
# ESTILO GLOBAL
# ═══════════════════════════════════════════════════════════
plt.rcParams.update({
    "figure.facecolor"  : "#0d1117",
    "axes.facecolor"    : "#161b22",
    "axes.edgecolor"    : "#30363d",
    "axes.labelcolor"   : "#c9d1d9",
    "text.color"        : "#c9d1d9",
    "xtick.color"       : "#8b949e",
    "ytick.color"       : "#8b949e",
    "grid.color"        : "#21262d",
    "grid.linestyle"    : "--",
    "grid.alpha"        : 0.6,
    "font.family"       : "monospace",
    "font.size"         : 10,
})

GOLD   = "#FFD700"
GREEN  = "#3fb950"
RED    = "#f85149"
BLUE   = "#58a6ff"
ORANGE = "#e3b341"
PURPLE = "#bc8cff"
GRAY   = "#6e7681"

# ═══════════════════════════════════════════════════════════
# CARGAR JSON DE RESULTADOS
# ═══════════════════════════════════════════════════════════
json_path = os.path.join(BASE_DIR, "thursday_space_move_summary.json")
if not os.path.exists(json_path):
    print("❌  Primero ejecuta: python backtest_thursday_news_space_move.py")
    exit(1)

with open(json_path, encoding="utf-8") as f:
    data = json.load(f)

records = data["records"]
df      = pd.DataFrame(records)
n       = len(df)
params  = data["params"]

# Columnas auxiliares
df["ret_poc_int"] = df["returned_poc"].astype(int)
df["ret_va_int"]  = df["returned_va"].astype(int)
df["dir_up"]      = df["space_dir"].str.contains("UP")
df["color"]       = df["dir_up"].map({True: GREEN, False: RED})

print(f"\n  Cargados {n} registros del JSON.")
print(f"  Params: space≥{params['space_threshold_pts']}pts | retorno {params['return_window']}\n")

# ═══════════════════════════════════════════════════════════
# TABLA DETALLADA PARA VERIFICACIÓN
# ═══════════════════════════════════════════════════════════
print("═" * 95)
print(f"  TABLA DETALLADA — {n} JUEVES CON SPACE MOVE  (para verificar en tu plataforma)")
print("═" * 95)
print(f"  {'#':<3} {'FECHA':<12} {'DIR':<8} {'MOVE':>6} {'OPEN':>8} {'VAL':>8} {'POC':>8} {'VAH':>8}  "
      f"{'→POC?':<14} {'→VA?':<14} {'PM Close':>8}")
print(f"  {'─'*90}")

for i, r in enumerate(records, 1):
    poc_tag = f"✅ {r['ret_poc_time']}" if r["returned_poc"] else "❌ nunca"
    va_tag  = f"✅ {r['ret_va_time']}"  if r["returned_va"]  else "❌ nunca"
    dir_ico = "▲" if "UP" in r["space_dir"] else "▼"
    print(f"  {i:<3} {r['date']:<12} {dir_ico} {r['space_dir'].split()[-1]:<6} "
          f"{r['space_size_pts']:>5.0f}p "
          f"{r['open']:>8.0f} {r['val']:>8.0f} {r['poc']:>8.0f} {r['vah']:>8.0f}  "
          f"{poc_tag:<14} {va_tag:<14} {r['pm_close']:>8.0f}")

print(f"\n  Guía: DATE=día  MOVE=tamaño del impulso  OPEN=precio 9:30  "
      f"VAL/POC/VAH=perfil pre-NY\n"
      f"        →POC?=¿volvió al POC 10am-4pm?  →VA?=¿entró al Value Area?\n")

# ═══════════════════════════════════════════════════════════
# IMAGEN 1 — Dashboard Principal (3 paneles)
# ═══════════════════════════════════════════════════════════
fig = plt.figure(figsize=(18, 12), facecolor="#0d1117")
fig.suptitle(
    "🎯  JUEVES NEWS DAY — Space Move + Retorno POC/VA  (NQ Futures, 60 días)",
    fontsize=15, fontweight="bold", color=GOLD, y=0.98
)

gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.45, wspace=0.35,
                       left=0.06, right=0.97, top=0.92, bottom=0.08)

# ── Panel 1: Space Move por fecha (barras) ──────────────────
ax1 = fig.add_subplot(gs[0, :2])
x   = np.arange(n)
colors = [GREEN if "UP" in r["space_dir"] else RED for r in records]
bars = ax1.bar(x, [r["space_size_pts"] for r in records],
               color=colors, edgecolor="#0d1117", linewidth=0.8, width=0.6)

# Marcar si regresó al POC
for i, r in enumerate(records):
    y_top = r["space_size_pts"]
    if r["returned_poc"]:
        ax1.annotate("↩POC", xy=(i, y_top + 4), fontsize=7.5,
                     color=GOLD, ha="center", fontweight="bold")
    else:
        ax1.annotate("→", xy=(i, y_top + 4), fontsize=8,
                     color=GRAY, ha="center")

ax1.set_xticks(x)
ax1.set_xticklabels([r["date"][5:] for r in records],
                    rotation=35, ha="right", fontsize=8)
ax1.set_ylabel("Tamaño Space Move (pts)", color="#c9d1d9")
ax1.set_title("Space Move por Jueves  |  🟢=UP  🔴=DOWN  |  ↩POC=regresó al POC en tarde",
              fontsize=9.5, color="#8b949e", pad=6)
ax1.grid(axis="y", alpha=0.4)
ax1.axhline(params["space_threshold_pts"], color=ORANGE, linestyle=":", linewidth=1.2, alpha=0.7)
ax1.text(n - 0.5, params["space_threshold_pts"] + 2, f"min={params['space_threshold_pts']}pts",
         color=ORANGE, fontsize=7.5, ha="right")

# ── Panel 2: Gauge % retorno ────────────────────────────────
ax2 = fig.add_subplot(gs[0, 2])
cats   = ["→ POC", "→ VA", "→ POC+VA"]
n_poc  = data["returned_to_poc"]
n_va   = data["returned_to_va"]
n_both = sum(1 for r in records if r["returned_poc"] and r["returned_va"])
vals   = [n_poc / n * 100, n_va / n * 100, n_both / n * 100]
bar_c  = [BLUE, PURPLE, GOLD]

bh = ax2.barh(cats, vals, color=bar_c, edgecolor="#0d1117", height=0.45)
for bar_, v in zip(bh, vals):
    ax2.text(v + 1, bar_.get_y() + bar_.get_height() / 2,
             f"{v:.0f}%", va="center", fontsize=11, fontweight="bold",
             color="white")

ax2.set_xlim(0, 115)
ax2.set_xlabel("% de Jueves", color="#c9d1d9")
ax2.set_title("Tasa de Retorno\n(10am → 4pm NY)", fontsize=10, color="#8b949e")
ax2.axvline(50, color=GRAY, linestyle="--", linewidth=0.8, alpha=0.6)
ax2.text(50.5, 2.5, "50%", color=GRAY, fontsize=7.5)
ax2.grid(axis="x", alpha=0.3)

# Totales
ax2.text(108, 0,  f"{n_poc}/{n}",  ha="right", va="center", fontsize=8, color=BLUE)
ax2.text(108, 1,  f"{n_va}/{n}",   ha="right", va="center", fontsize=8, color=PURPLE)
ax2.text(108, 2,  f"{n_both}/{n}", ha="right", va="center", fontsize=8, color=GOLD)

# ── Panel 3: Space UP vs DOWN ───────────────────────────────
ax3 = fig.add_subplot(gs[1, 0])
up_recs   = [r for r in records if "UP"   in r["space_dir"]]
down_recs = [r for r in records if "DOWN" in r["space_dir"]]
n_up = len(up_recs);   n_dn = len(down_recs)
p_up_poc  = sum(1 for r in up_recs   if r["returned_poc"]) / max(n_up, 1) * 100
p_dn_poc  = sum(1 for r in down_recs if r["returned_poc"]) / max(n_dn, 1) * 100
p_up_va   = sum(1 for r in up_recs   if r["returned_va"])  / max(n_up, 1) * 100
p_dn_va   = sum(1 for r in down_recs if r["returned_va"])  / max(n_dn, 1) * 100

xb   = np.array([0, 1])
w    = 0.35
b1 = ax3.bar(xb - w/2, [p_up_poc, p_up_va],  width=w, color=GREEN,  label="Space UP",   alpha=0.85)
b2 = ax3.bar(xb + w/2, [p_dn_poc, p_dn_va],  width=w, color=RED,    label="Space DOWN", alpha=0.85)

for b, pct in zip(list(b1) + list(b2), [p_up_poc, p_up_va, p_dn_poc, p_dn_va]):
    ax3.text(b.get_x() + b.get_width()/2, b.get_height() + 1.5,
             f"{pct:.0f}%", ha="center", fontsize=9.5, fontweight="bold", color="white")

ax3.set_xticks(xb)
ax3.set_xticklabels(["→ POC", "→ VA"], fontsize=10)
ax3.set_ylabel("% Retorno", color="#c9d1d9")
ax3.set_title(f"Por Dirección del Space\n▲UP (n={n_up})  vs  ▼DOWN (n={n_dn})",
              fontsize=9, color="#8b949e")
ax3.set_ylim(0, 120)
ax3.legend(fontsize=8, facecolor="#161b22", edgecolor=GRAY)
ax3.axhline(50, color=GRAY, linestyle="--", linewidth=0.8, alpha=0.5)
ax3.grid(axis="y", alpha=0.3)

# ── Panel 4: Open position vs return rate ───────────────────
ax4 = fig.add_subplot(gs[1, 1])
positions = ["ABOVE_VA", "INSIDE_VA", "BELOW_VA"]
pos_labels = ["Open ↑ encima VA", "Open — dentro VA", "Open ↓ debajo VA"]
poc_rates  = []
for pos in positions:
    sub = [r for r in records if r["open_pos"] == pos]
    poc_rates.append(sum(1 for r in sub if r["returned_poc"]) / max(len(sub), 1) * 100)

pos_colors = [ORANGE, BLUE, PURPLE]
bh2 = ax4.bar(pos_labels, poc_rates, color=pos_colors, edgecolor="#0d1117", width=0.5)
for bar_, v in zip(bh2, poc_rates):
    ax4.text(bar_.get_x() + bar_.get_width()/2, v + 1.5,
             f"{v:.0f}%", ha="center", fontsize=10, fontweight="bold", color="white")

ax4.set_ylabel("% Regresa al POC", color="#c9d1d9")
ax4.set_title("Tasa → POC\npor posición del Open vs Profile", fontsize=9, color="#8b949e")
ax4.set_ylim(0, 120)
ax4.set_xticklabels(pos_labels, fontsize=8, rotation=12)
ax4.axhline(50, color=GRAY, linestyle="--", linewidth=0.8, alpha=0.5)
ax4.grid(axis="y", alpha=0.3)

# ── Panel 5: Hora de retorno (distribución) ─────────────────
ax5 = fig.add_subplot(gs[1, 2])
poc_bars = [r["ret_poc_bar"] for r in records if r["ret_poc_bar"] is not None]
va_bars  = [r["ret_va_bar"]  for r in records if r["ret_va_bar"]  is not None]

if poc_bars:
    poc_times = [10 + b * 5 / 60 for b in poc_bars]   # hora decimal
    va_times  = [10 + b * 5 / 60 for b in va_bars]
    ax5.scatter(poc_times, [1.1] * len(poc_times), color=GOLD,   s=120, zorder=5, label="Hit POC")
    ax5.scatter(va_times,  [0.9] * len(va_times),  color=PURPLE, s=120, zorder=5, label="Hit VA")

    # Promedio
    if poc_times:
        ax5.axvline(np.mean(poc_times), color=GOLD,   linestyle="--", linewidth=1.2,
                    label=f"Avg POC: {np.mean(poc_times):.2f}h")
    if va_times:
        ax5.axvline(np.mean(va_times),  color=PURPLE, linestyle="--", linewidth=1.2,
                    label=f"Avg VA:  {np.mean(va_times):.2f}h")

ax5.set_xlim(9.8, 16.2)
ax5.set_ylim(0.5, 1.5)
ax5.set_xticks([10, 11, 12, 13, 14, 15, 16])
ax5.set_xticklabels(["10am","11am","12pm","1pm","2pm","3pm","4pm"], fontsize=8)
ax5.set_title("¿A QUÉ HORA regresa al POC/VA?\n(cada punto = 1 Jueves)", fontsize=9, color="#8b949e")
ax5.set_yticks([])
ax5.legend(fontsize=7.5, facecolor="#161b22", edgecolor=GRAY, loc="upper right")
ax5.axvspan(10, 12, alpha=0.08, color=GREEN, label="AM session")
ax5.grid(axis="x", alpha=0.4)

# Guardar
img1 = os.path.join(BASE_DIR, "thursday_analysis_dashboard.png")
fig.savefig(img1, dpi=140, bbox_inches="tight", facecolor="#0d1117")
plt.close(fig)
print(f"  ✅ Imagen 1 guardada: thursday_analysis_dashboard.png")

# ═══════════════════════════════════════════════════════════
# IMAGEN 2 — Gráfico de precio por cada Jueves (5 paneles 3x4)
# ═══════════════════════════════════════════════════════════
print("  📡 Descargando datos 5m para mini-charts...")
df_raw = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(df_raw.columns, pd.MultiIndex):
    df_raw.columns = df_raw.columns.get_level_values(0)
if df_raw.index.tz is None:
    df_raw.index = df_raw.index.tz_localize("UTC")
df_raw.index = df_raw.index.tz_convert("America/New_York")
df_raw = df_raw.sort_index()
df_raw["date"] = df_raw.index.normalize()
df_raw["h"]    = df_raw.index.hour
df_raw["m"]    = df_raw.index.minute

rows = 3; cols = 4
fig2, axes = plt.subplots(rows, cols, figsize=(20, 14), facecolor="#0d1117")
fig2.suptitle(
    "📅  CADA JUEVES — Space Move + Precio PM  (Profile pre-NY : VAL / POC / VAH)",
    fontsize=13, fontweight="bold", color=GOLD, y=0.99
)
axes_flat = axes.flatten()

for idx, r in enumerate(records):
    ax = axes_flat[idx]
    day = pd.Timestamp(r["date"]).normalize()

    # Datos del día 9:00 → 16:00
    day_data = df_raw[df_raw["date"] == day]
    plot_data = day_data[(day_data["h"] >= 9) & (day_data["h"] < 16)].copy()

    if plot_data.empty:
        ax.set_visible(False); continue

    x_idx = np.arange(len(plot_data))
    closes = plot_data["Close"].values.flatten()
    highs  = plot_data["High"].values.flatten()
    lows   = plot_data["Low"].values.flatten()

    # Línea de precio
    ax.plot(x_idx, closes, color="#58a6ff", linewidth=1.2, zorder=3)
    ax.fill_between(x_idx, lows, highs, alpha=0.15, color="#58a6ff")

    poc = r["poc"]; val = r["val"]; vah = r["vah"]

    # Niveles del profile
    ax.axhline(poc, color=GOLD,   linewidth=1.5, linestyle="-",  alpha=0.9, zorder=4, label="POC")
    ax.axhline(vah, color=GREEN,  linewidth=1.0, linestyle="--", alpha=0.7, zorder=4, label="VAH")
    ax.axhline(val, color=RED,    linewidth=1.0, linestyle="--", alpha=0.7, zorder=4, label="VAL")

    # Sombrear el Value Area
    ax.fill_between(x_idx, val, vah, alpha=0.06, color=GOLD)

    # Marcar el open 9:30
    open_bars = plot_data[(plot_data["h"] == 9) & (plot_data["m"] >= 30)]
    if not open_bars.empty:
        open_idx = x_idx[plot_data.index.get_loc(open_bars.index[0])] if open_bars.index[0] in plot_data.index else 0
        ax.axvline(open_idx, color=ORANGE, linewidth=1.2, linestyle=":", alpha=0.8)

    # Marcar 10:00 AM
    pm_bars = plot_data[(plot_data["h"] == 10) & (plot_data["m"] == 0)]
    if not pm_bars.empty:
        pm_idx = list(plot_data.index).index(pm_bars.index[0])
        ax.axvline(pm_idx, color=PURPLE, linewidth=1.5, linestyle="-", alpha=0.6)
        ax.text(pm_idx + 0.5, ax.get_ylim()[0] if ax.get_ylim()[0] != 0 else closes.min(),
                "10am", fontsize=6, color=PURPLE, va="bottom")

    # Título del panel
    dir_ico = "▲" if "UP" in r["space_dir"] else "▼"
    poc_icon = "✅" if r["returned_poc"] else "❌"
    va_icon  = "✅" if r["returned_va"]  else "❌"
    ax.set_title(
        f"{r['date']}  {dir_ico}{r['space_size_pts']:.0f}p\n"
        f"POC:{poc:.0f}  {poc_icon}ret  VA:{va_icon}",
        fontsize=7.5, color="#c9d1d9", pad=3
    )

    # Eje X: horas
    tick_positions = []
    tick_labels    = []
    for h in [9, 10, 11, 12, 13, 14, 15]:
        for m in [0, 30]:
            mask = (plot_data["h"] == h) & (plot_data["m"] == m)
            if mask.any():
                tick_positions.append(list(x_idx[mask])[0])
                tick_labels.append(f"{h}:{m:02d}" if m == 0 else "")

    ax.set_xticks(tick_positions)
    ax.set_xticklabels(tick_labels, fontsize=5.5, rotation=0)
    ax.tick_params(axis="y", labelsize=6.5)
    ax.grid(alpha=0.25)

# Ocultar paneles vacíos
for idx in range(len(records), rows * cols):
    axes_flat[idx].set_visible(False)

# Leyenda
legend_elements = [
    mpatches.Patch(color=GOLD,   label="POC"),
    mpatches.Patch(color=GREEN,  label="VAH"),
    mpatches.Patch(color=RED,    label="VAL"),
    mpatches.Patch(color=ORANGE, label="9:30 Open"),
    mpatches.Patch(color=PURPLE, label="10:00 AM"),
]
fig2.legend(handles=legend_elements, loc="lower center", ncol=5,
            fontsize=9, facecolor="#161b22", edgecolor=GRAY,
            bbox_to_anchor=(0.5, 0.01))

fig2.tight_layout(rect=[0, 0.03, 1, 0.98])
img2 = os.path.join(BASE_DIR, "thursday_charts_per_day.png")
fig2.savefig(img2, dpi=130, bbox_inches="tight", facecolor="#0d1117")
plt.close(fig2)
print(f"  ✅ Imagen 2 guardada: thursday_charts_per_day.png")

# ═══════════════════════════════════════════════════════════
# IMAGEN 3 — Tabla visual resumen
# ═══════════════════════════════════════════════════════════
fig3, ax = plt.subplots(figsize=(18, 8), facecolor="#0d1117")
ax.set_facecolor("#0d1117")
ax.axis("off")
ax.set_title("📋  TABLA DE VERIFICACIÓN — Jueves News Day  (NQ, últimos 60 días)",
             fontsize=13, fontweight="bold", color=GOLD, pad=15)

# Columnas de la tabla
col_labels = [
    "#", "FECHA", "DIRECCIÓN", "SPACE\n(pts)", "OPEN\n9:30",
    "VAL", "POC", "VAH",
    "OPEN\nvs Profile", "→ POC\nPM?", "HORA\nPOC", "→ VA\nPM?", "HORA\nVA",
    "PM\nRANGE (pts)"
]

table_data = []
for i, r in enumerate(records, 1):
    dir_str  = f"▲ UP   +{r['space_size_pts']:.0f}" if "UP" in r["space_dir"] else f"▼ DOWN -{r['space_size_pts']:.0f}"
    poc_bool = "✅ SÍ" if r["returned_poc"] else "❌ NO"
    va_bool  = "✅ SÍ" if r["returned_va"]  else "❌ NO"
    poc_t    = r["ret_poc_time"] if r["returned_poc"] else "—"
    va_t     = r["ret_va_time"]  if r["returned_va"]  else "—"
    op_pos   = {"ABOVE_VA": "↑ encima VA", "INSIDE_VA": "— dentro VA", "BELOW_VA": "↓ debajo VA"}.get(r["open_pos"], r["open_pos"])

    table_data.append([
        str(i), r["date"], dir_str,
        f"{r['space_size_pts']:.0f}", f"{r['open']:.0f}",
        f"{r['val']:.0f}", f"{r['poc']:.0f}", f"{r['vah']:.0f}",
        op_pos, poc_bool, poc_t, va_bool, va_t,
        f"{r['pm_range']:.0f}",
    ])

# Colores de filas
row_colors = []
for r in records:
    if "UP" in r["space_dir"]:
        base = "#0d2b0d" if r["returned_poc"] else "#1a1a0d"
    else:
        base = "#2b0d0d" if r["returned_poc"] else "#1a1a1a"
    row_colors.append([base] * len(col_labels))

tbl = ax.table(
    cellText    = table_data,
    colLabels   = col_labels,
    cellLoc     = "center",
    loc         = "center",
    cellColours = row_colors,
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8)
tbl.scale(1, 2.1)

# Estilo encabezados
for j in range(len(col_labels)):
    cell = tbl[0, j]
    cell.set_facecolor("#1f6feb")
    cell.set_text_props(color="white", fontweight="bold", fontsize=7.5)
    cell.set_edgecolor("#30363d")

# Estilo celdas
for i in range(1, len(table_data) + 1):
    for j in range(len(col_labels)):
        cell = tbl[i, j]
        cell.set_edgecolor("#21262d")
        txt = cell.get_text().get_text()
        if "✅" in txt:
            cell.get_text().set_color(GREEN)
            cell.get_text().set_fontweight("bold")
        elif "❌" in txt:
            cell.get_text().set_color(RED)
        elif "▲" in txt:
            cell.get_text().set_color(GREEN)
        elif "▼" in txt:
            cell.get_text().set_color(RED)

# Footer
total_poc = data["returned_to_poc"]
total_va  = data["returned_to_va"]
fig3.text(0.5, 0.02,
          f"TOTAL:  {n} Jueves con Space Move ≥{params['space_threshold_pts']}pts  |  "
          f"→POC: {total_poc}/{n} = {total_poc/n*100:.0f}%  |  "
          f"→VA: {total_va}/{n} = {total_va/n*100:.0f}%  |  "
          f"Ventana retorno: 10:00 AM → 4:00 PM NY",
          ha="center", fontsize=9, color=GOLD, fontweight="bold")

img3 = os.path.join(BASE_DIR, "thursday_verification_table.png")
fig3.savefig(img3, dpi=130, bbox_inches="tight", facecolor="#0d1117")
plt.close(fig3)
print(f"  ✅ Imagen 3 guardada: thursday_verification_table.png")

print(f"\n{'═'*60}")
print(f"  📸 3 IMÁGENES GENERADAS:")
print(f"     1. thursday_analysis_dashboard.png  — Dashboard estadístico")
print(f"     2. thursday_charts_per_day.png      — Mini-chart de cada jueves")
print(f"     3. thursday_verification_table.png  — Tabla para verificar")
print(f"{'═'*60}\n")
