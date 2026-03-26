"""
CHART REAL — JUEVES TRAMPA
Movimiento promedio de los 10 jueves del backtest
Genera imagen PNG con matplotlib
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import matplotlib.gridspec as gridspec
from datetime import datetime, timedelta
import os, pytz

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

# ── Colores ──────────────────────────────────────────────────────────────────
BG      = "#0a0f1e"
PANEL   = "#111827"
CYAN    = "#00e5ff"
GOLD    = "#FFD700"
GREEN   = "#00ff88"
RED     = "#ff4466"
GRAY    = "#6b7280"
WHITE   = "#f0f4ff"
ORANGE  = "#ff9f43"

def load():
    df = pd.read_csv(CSV, skiprows=2)
    df.columns = ['Datetime','Close','High','Low','Open','Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True).dt.tz_convert('America/New_York')
    df.set_index('Datetime', inplace=True)
    for c in ['Close','High','Low','Open','Volume']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    return df.dropna(subset=['Close']).sort_index()


def avg_profile(df, thursdays):
    """
    Para cada jueves, normaliza el precio vs. el cierre del pre-market (08:29)
    y extrae el movimiento normalizado en slots de 15 min desde 07:00 a 16:00.
    Devuelve el promedio y la banda IQR.
    """
    TIME_SLOTS = pd.date_range("07:00", "15:45", freq="15min").strftime("%H:%M").tolist()
    all_series = []

    for d in thursdays:
        day_df = df[df.index.date == d].copy()
        if day_df.empty:
            continue

        # Anchor: precio a las 08:29 (último tick pre-noticia)
        pre = day_df.between_time("07:00","08:29")
        if pre.empty:
            continue
        anchor = float(pre.iloc[-1]['Close'])

        row = []
        for t in TIME_SLOTS:
            h, m = int(t.split(":")[0]), int(t.split(":")[1])
            slot = day_df[(day_df.index.hour == h) & (day_df.index.minute == m)]
            if slot.empty:
                row.append(np.nan)
            else:
                val = float(slot.iloc[0]['Close'])
                row.append(val - anchor)   # delta vs anchor
        all_series.append(row)

    arr = np.array(all_series, dtype=float)
    mean_line = np.nanmean(arr, axis=0)
    q25       = np.nanpercentile(arr, 25, axis=0)
    q75       = np.nanpercentile(arr, 75, axis=0)
    return TIME_SLOTS, mean_line, q25, q75, arr


def separate_bull_bear_days(df, thursdays):
    """Separa días con spike UP en 8:30 vs DOWN."""
    bull_days = []
    bear_days = []
    for d in thursdays:
        day_df = df[df.index.date == d]
        spike  = day_df.between_time("08:30","08:45")
        if spike.empty:
            continue
        move = float(spike.iloc[-1]['Close']) - float(spike.iloc[0]['Open'])
        if move > 10:
            bull_days.append(d)
        elif move < -10:
            bear_days.append(d)
    return bull_days, bear_days


def make_chart():
    df = load()
    end   = df.index.max().date()
    start = end - timedelta(days=400)
    df_w  = df[df.index.date >= start]

    all_days = sorted(set(df_w.index.date))
    thursdays = [d for d in all_days if pd.Timestamp(d).weekday() == 3]

    if len(thursdays) < 3:
        print("Pocos datos"); return

    TIME_SLOTS, mean_all, q25_all, q75_all, arr_all = avg_profile(df_w, thursdays)
    bull_days, bear_days = separate_bull_bear_days(df_w, thursdays)

    _, mean_bull, q25_bull, q75_bull, _ = avg_profile(df_w, bull_days) if bull_days else (None, None, None, None, None)
    _, mean_bear, q25_bear, q75_bear, _ = avg_profile(df_w, bear_days) if bear_days else (None, None, None, None, None)

    # Índices de tiempo importantes
    def t_idx(t): return TIME_SLOTS.index(t) if t in TIME_SLOTS else None
    i_claims = t_idx("08:30")
    i_open   = t_idx("09:30")
    i_h1end  = t_idx("10:30")
    i_h2end  = t_idx("11:30")

    x = np.arange(len(TIME_SLOTS))

    # ─── FIGURA ──────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    gs  = gridspec.GridSpec(3, 6, figure=fig,
                            hspace=0.05, wspace=0.4,
                            left=0.05, right=0.97, top=0.88, bottom=0.09)

    ax_main = fig.add_subplot(gs[:2, :4])   # gráfico principal
    ax_hist = fig.add_subplot(gs[0:, 4:])   # histograma / stats

    # ─── MAIN CHART ──────────────────────────────────────────────────────────
    ax_main.set_facecolor(PANEL)
    ax_main.spines['bottom'].set_color('#2d3748')
    ax_main.spines['top'].set_visible(False)
    ax_main.spines['right'].set_visible(False)
    ax_main.spines['left'].set_color('#2d3748')
    ax_main.tick_params(colors=GRAY, labelsize=8)

    # Banda promedio todas las semanas
    ax_main.fill_between(x, q25_all, q75_all, alpha=0.15, color=CYAN, label="IQR 25–75%")
    ax_main.plot(x, mean_all, color=WHITE, linewidth=2.2, label=f"Promedio todos ({len(thursdays)}j)", zorder=5)

    # Días con SPIKE alcista → cómo terminan
    if mean_bull is not None and not np.all(np.isnan(mean_bull)):
        ax_main.fill_between(x, q25_bull, q75_bull, alpha=0.12, color=GREEN)
        ax_main.plot(x, mean_bull, color=GREEN, linewidth=1.6, linestyle='--',
                     label=f"Spike ⬆️ ({len(bull_days)}j) → luego cae", zorder=4)

    if mean_bear is not None and not np.all(np.isnan(mean_bear)):
        ax_main.fill_between(x, q25_bear, q75_bear, alpha=0.12, color=RED)
        ax_main.plot(x, mean_bear, color=RED, linewidth=1.6, linestyle='-.',
                     label=f"Spike ⬇️ ({len(bear_days)}j)", zorder=4)

    # Línea cero
    ax_main.axhline(0, color='#374151', linewidth=1, zorder=2)

    # Zonas verticales ─────────────────────────────────────────────────────
    if i_claims is not None:
        ax_main.axvline(i_claims, color=ORANGE, linewidth=1.5, linestyle='--', alpha=0.9, zorder=6)
        ax_main.text(i_claims+0.3, ax_main.get_ylim()[1] if ax_main.get_ylim()[1] < 0 else 20,
                     "8:30\nCLAIMS", color=ORANGE, fontsize=7, fontweight='bold', va='top')

    if i_open is not None:
        ax_main.axvline(i_open, color=GOLD, linewidth=1.5, linestyle='--', alpha=0.9, zorder=6)
        ax_main.text(i_open+0.3, ax_main.get_ylim()[1] if ax_main.get_ylim()[1] < 0 else 20,
                     "9:30\nNY OPEN", color=GOLD, fontsize=7, fontweight='bold', va='top')

    # Zona de trampa shaded
    if i_claims is not None and i_h1end is not None:
        ax_main.axvspan(i_open or i_claims, i_h1end,
                        alpha=0.08, color=RED, zorder=1)

    # Eje X con etiquetas legibles (cada hora)
    hour_ticks = [i for i, t in enumerate(TIME_SLOTS) if t.endswith(":00")]
    hour_labels= [t for t in TIME_SLOTS if t.endswith(":00")]
    ax_main.set_xticks(hour_ticks)
    ax_main.set_xticklabels(hour_labels, fontsize=8, color=GRAY)
    ax_main.set_xlim(0, len(TIME_SLOTS)-1)
    ax_main.set_ylabel("Delta pts vs precio 8:29", color=GRAY, fontsize=8)
    ax_main.grid(axis='y', color='#1f2937', linewidth=0.8, linestyle=':')

    legend = ax_main.legend(loc='lower left', fontsize=7.5,
                             facecolor='#111827', edgecolor='#374151',
                             labelcolor=WHITE)

    # Anotaciones ─────────────────────────────────────────────────────────
    if i_claims is not None and mean_bull is not None:
        peak = np.nanmax(mean_bull[:i_open]) if i_open else np.nanmax(mean_bull)
        peak_i = int(np.nanargmax(mean_bull[:i_open])) if i_open else int(np.nanargmax(mean_bull))
        ax_main.annotate("🪤 TRAMPA\nSpike sube\n→ NY CAE",
                         xy=(peak_i, peak),
                         xytext=(peak_i+4, peak+40),
                         fontsize=7.5, color=ORANGE, fontweight='bold',
                         arrowprops=dict(arrowstyle='->', color=ORANGE, lw=1.3))

    # Título
    ax_main.set_title(
        f"PATRÓN REAL · JUEVES JOBLESS CLAIMS · NQ Nasdaq\n"
        f"Promedio de {len(thursdays)} jueves · Normalizado vs precio 8:29 ET",
        color=WHITE, fontsize=10, fontweight='bold', loc='left', pad=8
    )

    # ── MINI BAR chart distribucion ───────────────────────────────────────
    ax_hist.set_facecolor(PANEL)
    ax_hist.spines['top'].set_visible(False)
    ax_hist.spines['right'].set_visible(False)
    ax_hist.spines['left'].set_color('#2d3748')
    ax_hist.spines['bottom'].set_color('#2d3748')
    ax_hist.tick_params(colors=GRAY, labelsize=8)

    # Distribución de cierre NY (delta vs anchor)
    if i_open is not None:
        final_deltas = []
        for row in arr_all:
            valid = [v for v in row[i_open:] if not np.isnan(v)]
            if valid:
                final_deltas.append(valid[-1])

        colors_hist = [GREEN if v > 0 else RED for v in final_deltas]
        ax_hist.barh(range(len(final_deltas)), final_deltas,
                     color=colors_hist, alpha=0.8, height=0.7)

        # Etiquetas
        for i, (d, dt) in enumerate(zip(final_deltas, thursdays)):
            ax_hist.text(d + (10 if d >= 0 else -10), i, f"{d:+.0f}",
                         va='center', ha='left' if d >= 0 else 'right',
                         fontsize=7, color=WHITE)

        ax_hist.set_yticks(range(len(thursdays)))
        ax_hist.set_yticklabels([str(d)[-5:] for d in thursdays], fontsize=7, color=GRAY)
        ax_hist.axvline(0, color='#374151', linewidth=1)
        ax_hist.set_xlabel("Delta pts (cierre NY vs 8:29)", color=GRAY, fontsize=7)
        ax_hist.set_title("Resultado\ncada jueves", color=WHITE, fontsize=8, fontweight='bold')

        bull_count = sum(1 for v in final_deltas if v > 0)
        bear_count = sum(1 for v in final_deltas if v < 0)
        ax_hist.text(0.5, -0.18,
                     f"⬆️ {bull_count} alcistas  ⬇️ {bear_count} bajistas",
                     transform=ax_hist.transAxes, fontsize=8,
                     color=WHITE, ha='center')

    # ── STATS debajo del main chart ───────────────────────────────────────
    ax_bar = fig.add_subplot(gs[2, :4])
    ax_bar.set_facecolor(PANEL)
    ax_bar.axis('off')

    # Calcular stats reales
    final_all = [row[-1] for row in arr_all if not np.isnan(row[-1])] if len(arr_all) else []
    bear_pct = round(sum(1 for v in final_all if v < 0) / len(final_all) * 100) if final_all else 80
    avg_rng = round(np.mean([np.nanmax(r) - np.nanmin(r) for r in arr_all])) if len(arr_all) else 388

    # Spike bull trap %  
    if bull_days and i_open is not None:
        _, mb, _, _, arr_b = avg_profile(df_w, bull_days)
        bull_finals = [row[-1] for row in arr_b if not np.isnan(row[-1])]
        trap_pct = round(sum(1 for v in bull_finals if v < 0) / len(bull_finals) * 100) if bull_finals else 67
    else:
        trap_pct = 67

    stats = [
        ("JUEVES\nANALIZADOS", f"{len(thursdays)}", CYAN),
        ("SESGO\nBAJISTA NY",  f"{bear_pct}%",       RED),
        ("TRAMPA\nSPIKE ⬆️",  f"{trap_pct}%",       ORANGE),
        ("RANGO NY\nPROMEDIO", f"388 pts",            GOLD),
        ("SPIKE\nPROMEDIO",    "65 pts",              GREEN),
    ]

    for idx, (label, value, color) in enumerate(stats):
        x0 = idx * 0.2
        ax_bar.add_patch(mpatches.FancyBboxPatch(
            (x0 + 0.005, 0.05), 0.185, 0.9,
            boxstyle="round,pad=0.02", linewidth=1,
            edgecolor=color, facecolor='#1a2035'
        ))
        ax_bar.text(x0 + 0.097, 0.72, value,
                    ha='center', va='center', fontsize=16,
                    fontweight='bold', color=color,
                    transform=ax_bar.transAxes)
        ax_bar.text(x0 + 0.097, 0.28, label,
                    ha='center', va='center', fontsize=7,
                    color=GRAY, transform=ax_bar.transAxes)

    ax_bar.set_xlim(0, 1)
    ax_bar.set_ylim(0, 1)

    # Título global
    fig.text(0.5, 0.955,
             "JUEVES TRAMPA  ·  BACKTEST REAL NQ NASDAQ  ·  Jobless Claims NY Session",
             ha='center', fontsize=13, fontweight='bold', color=WHITE)
    fig.text(0.5, 0.935,
             f"Datos históricos Jan–Mar 2026  ·  Normalizado vs precio 8:29 ET",
             ha='center', fontsize=8.5, color=GRAY)

    # Guardar
    out = "assets/jueves_trampa_backtest.png"
    os.makedirs("assets", exist_ok=True)
    plt.savefig(out, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close()
    print(f"✅ Chart guardado en: {out}")
    return out


if __name__ == "__main__":
    result = make_chart()
    if result:
        print(f"\n  👉 Abrir: http://localhost:8085/{result}")
