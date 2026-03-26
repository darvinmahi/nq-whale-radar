"""
BACKTEST JUEVES — VOLUME PROFILE ASIA → NY+10min
Para cada jueves de Jobless Claims:
  - Calcula Volume Profile desde sesión Asia (18:00 ET miérc) hasta 9:40 ET
  - Marca VAH, POC, VAL
  - Grafica el movimiento completo del día con los niveles de VP
  - Genera imagen individual por jueves + imagen resumen de todos
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from datetime import datetime, date, timedelta
import os, pytz

# ─── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
CSV     = "data/research/nq_15m_intraday.csv"
OUT_DIR = "assets/jue_backtest"
ET      = pytz.timezone("America/New_York")

# Colores
BG    = "#0a0f1e"
PANEL = "#0f1729"
CYAN  = "#00e5ff"
GOLD  = "#FFD700"
GREEN = "#00ff88"
RED   = "#ff4057"
GRAY  = "#6b7280"
WHITE = "#e8edf8"
ORANGE= "#ff9f43"
PURPLE= "#a78bfa"

VP_BINS = 50   # bins del volume profile

# ─── CARGA DE DATOS ────────────────────────────────────────────────────────────
def load_csv():
    df = pd.read_csv(CSV, skiprows=2)
    df.columns = ["Datetime","Close","High","Low","Open","Volume"]
    df = df.dropna(subset=["Datetime"])
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True).dt.tz_convert(ET)
    df.set_index("Datetime", inplace=True)
    for c in ["Close","High","Low","Open","Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Volume"] = df["Volume"].fillna(1)  # si no hay vol, usar 1
    return df.dropna(subset=["Close"]).sort_index()


# ─── VOLUME PROFILE ────────────────────────────────────────────────────────────
def calc_vp(df_slice, bins=VP_BINS):
    """Retorna (vah, poc, val, price_levels, vols)"""
    if df_slice.empty or len(df_slice) < 2:
        return None, None, None, [], []

    lo = df_slice["Low"].min()
    hi = df_slice["High"].max()
    if hi == lo:
        return None, None, None, [], []

    edges = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols = np.zeros(bins)

    for _, row in df_slice.iterrows():
        # distribución uniforme del volumen en el rango High-Low de cada barra
        bar_lo, bar_hi = row["Low"], row["High"]
        bar_vol = row["Volume"] if row["Volume"] > 0 else 1
        mask = (centers >= bar_lo) & (centers <= bar_hi)
        count = mask.sum()
        if count > 0:
            vols[mask] += bar_vol / count

    poc_idx = int(np.argmax(vols))
    poc     = centers[poc_idx]

    # VAH y VAL: 70% del volumen alrededor del POC
    total_vol = vols.sum()
    target    = total_vol * 0.70
    lo_i, hi_i = poc_idx, poc_idx
    accum = vols[poc_idx]
    while accum < target and (lo_i > 0 or hi_i < bins - 1):
        lo_add = vols[lo_i - 1] if lo_i > 0 else 0
        hi_add = vols[hi_i + 1] if hi_i < bins - 1 else 0
        if lo_add >= hi_add and lo_i > 0:
            lo_i  -= 1; accum += lo_add
        elif hi_i < bins - 1:
            hi_i  += 1; accum += hi_add
        else:
            break

    vah = centers[hi_i]
    val = centers[lo_i]
    return vah, poc, val, centers, vols


# ─── IDENTIFICAR JUEVES ────────────────────────────────────────────────────────
def get_thursdays(df):
    days = sorted(set(df.index.date))
    return [d for d in days if pd.Timestamp(d).weekday() == 3]


# ─── CHART INDIVIDUAL ─────────────────────────────────────────────────────────
def chart_thursday(df, thu_date, idx, total):
    """Genera el chart para un jueves concreto."""

    # Datos del día: 18:00 ET del miércoles hasta 16:00 ET del jueves
    prev_day = thu_date - timedelta(days=1)
    start_ts = ET.localize(datetime(prev_day.year, prev_day.month, prev_day.day, 18, 0))
    end_ts   = ET.localize(datetime(thu_date.year, thu_date.month, thu_date.day, 16, 0))

    day_df   = df[(df.index >= start_ts) & (df.index <= end_ts)].copy()
    if day_df.empty:
        return None

    # Slice Asia → 9:40 ET (para el VP)
    ny9_40   = ET.localize(datetime(thu_date.year, thu_date.month, thu_date.day, 9, 40))
    asia_df  = day_df[day_df.index <= ny9_40]

    vah, poc, val, vp_prices, vp_vols = calc_vp(asia_df)

    # Slice para graficar: 7:00 → 16:00 ET del jueves
    plot_start = ET.localize(datetime(thu_date.year, thu_date.month, thu_date.day, 7, 0))
    plot_df    = day_df[day_df.index >= plot_start]

    if plot_df.empty:
        return None

    # Spike y anchors
    spike_df = day_df.between_time("08:30", "08:44") if hasattr(day_df.index, 'time') else pd.DataFrame()
    pre_anchor_df = day_df.between_time("08:15", "08:29") if hasattr(day_df.index, 'time') else pd.DataFrame()

    # Usar between_time correctamente
    day_df_bt = day_df.copy()
    day_df_bt.index = day_df_bt.index  # ya esta en ET

    def bt(start_t, end_t):
        return day_df_bt[(day_df_bt.index.time >= datetime.strptime(start_t, "%H:%M").time()) &
                         (day_df_bt.index.time <= datetime.strptime(end_t, "%H:%M").time())]

    plot_df2  = day_df_bt[(day_df_bt.index.time >= datetime.strptime("07:00", "%H:%M").time())]
    spike_df  = bt("08:30","08:44")
    pre_df    = bt("08:15","08:29")
    ny_df     = bt("09:30","16:00")

    sp_move   = 0
    if not spike_df.empty and not pre_df.empty:
        sp_move = round(float(spike_df.iloc[-1]["Close"]) - float(pre_df.iloc[-1]["Close"]), 0)

    ny_move = 0
    ny_dir  = "FLAT"
    if not ny_df.empty:
        ny_open   = float(ny_df.iloc[0]["Open"])
        ny_close  = float(ny_df.iloc[-1]["Close"])
        ny_move   = round(ny_close - ny_open, 0)
        ny_dir    = "BULL" if ny_move > 50 else ("BEAR" if ny_move < -50 else "FLAT")

    # ─── FIGURA ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 6), facecolor=BG)
    gs  = gridspec.GridSpec(1, 5, figure=fig, wspace=0.02,
                            left=0.04, right=0.97, top=0.88, bottom=0.12)

    ax_vp  = fig.add_subplot(gs[0, 0])    # volume profile (izq)
    ax_px  = fig.add_subplot(gs[0, 1:])   # price chart

    # ── VOLUME PROFILE ─────────────────────────────────────────────────────────
    ax_vp.set_facecolor(PANEL)
    ax_vp.spines[:].set_visible(False)
    ax_vp.tick_params(left=False, bottom=False, labelbottom=False,
                      labelleft=True, labelsize=7, labelcolor=GRAY)

    if len(vp_prices) > 0 and len(vp_vols) > 0:
        norm_vols = vp_vols / vp_vols.max() if vp_vols.max() > 0 else vp_vols
        # colores: zona valor vs fuera
        bar_colors = []
        for p in vp_prices:
            if val is None or vah is None:
                bar_colors.append(GRAY)
            elif val <= p <= vah:
                bar_colors.append(CYAN)
            else:
                bar_colors.append("#1e3a4a")

        ax_vp.barh(vp_prices, norm_vols, height=(vp_prices[1]-vp_prices[0]) if len(vp_prices)>1 else 1,
                   color=bar_colors, alpha=0.9)

        if vah: ax_vp.axhline(vah, color=GREEN,  linewidth=1.2, linestyle='--')
        if poc: ax_vp.axhline(poc, color=GOLD,   linewidth=2.0)
        if val: ax_vp.axhline(val, color=RED,    linewidth=1.2, linestyle='--')

        # Labels VP
        px_range = vp_prices[-1] - vp_prices[0]
        if vah: ax_vp.text(0.95, vah, f"VAH\n{vah:.0f}", color=GREEN,  fontsize=6, va='bottom', ha='right', fontweight='bold')
        if poc: ax_vp.text(0.95, poc, f"POC\n{poc:.0f}", color=GOLD,   fontsize=6, va='bottom', ha='right', fontweight='bold')
        if val: ax_vp.text(0.95, val, f"VAL\n{val:.0f}", color=RED,    fontsize=6, va='top',    ha='right', fontweight='bold')

    ax_vp.set_xlim(0, 1.3)
    ax_vp.set_title("VP\nASIA\n→9:40", color=GRAY, fontsize=7, pad=3)
    ax_vp.invert_xaxis()

    # ── PRICE CHART ────────────────────────────────────────────────────────────
    ax_px.set_facecolor(PANEL)
    ax_px.spines['top'].set_visible(False)
    ax_px.spines['right'].set_visible(False)
    ax_px.spines['left'].set_color('#2d3748')
    ax_px.spines['bottom'].set_color('#2d3748')
    ax_px.tick_params(colors=GRAY, labelsize=7)

    times = [t.strftime("%H:%M") for t in plot_df2.index]
    closes= plot_df2["Close"].values.astype(float)
    highs = plot_df2["High"].values.astype(float)
    lows  = plot_df2["Low"].values.astype(float)
    opens = plot_df2["Open"].values.astype(float)

    # Dibujar velas
    for i in range(len(times)):
        c = GREEN if closes[i] >= opens[i] else RED
        ax_px.plot([i, i], [lows[i], highs[i]], color=c, linewidth=0.7, zorder=3)
        ax_px.add_patch(plt.Rectangle((i-0.3, min(opens[i], closes[i])),
                                       0.6, abs(closes[i]-opens[i]),
                                       color=c, zorder=4))

    x_range = range(len(times))
    n = len(times)

    # Líneas VP sobre el chart
    if vah: ax_px.axhline(vah, color=GREEN,  linewidth=0.9, linestyle='--', alpha=0.8, zorder=2)
    if poc: ax_px.axhline(poc, color=GOLD,   linewidth=1.4, linestyle='-',  alpha=0.9, zorder=2)
    if val: ax_px.axhline(val, color=RED,    linewidth=0.9, linestyle='--', alpha=0.8, zorder=2)

    # Etiquetas derecha del chart para VP
    if vah: ax_px.text(n-0.5, vah, f" VAH", color=GREEN, fontsize=6, va='bottom')
    if poc: ax_px.text(n-0.5, poc, f" POC", color=GOLD,  fontsize=6, va='bottom')
    if val: ax_px.text(n-0.5, val, f" VAL", color=RED,   fontsize=6, va='top')

    # Líneas verticales de eventos
    def v_idx(t_str):
        for i2, t in enumerate(times):
            if t >= t_str:
                return i2
        return None

    i_claims = v_idx("08:30")
    i_open   = v_idx("09:30")
    i_10min  = v_idx("09:40")  # 10 min después del open

    if i_claims is not None:
        ax_px.axvline(i_claims, color=ORANGE, linewidth=1.5, linestyle='--', alpha=0.9, zorder=5)
        ax_px.text(i_claims+0.2, ax_px.get_ylim()[1], "8:30\nCLAIMS",
                   color=ORANGE, fontsize=6.5, fontweight='bold', va='top')

    if i_open is not None:
        ax_px.axvline(i_open, color=GOLD, linewidth=1.5, linestyle='--', alpha=0.9, zorder=5)
        ax_px.text(i_open+0.2, ax_px.get_ylim()[1], "9:30\nNY",
                   color=GOLD, fontsize=6.5, fontweight='bold', va='top')

    if i_10min is not None and i_10min != i_open:
        ax_px.axvline(i_10min, color=PURPLE, linewidth=1.0, linestyle=':', alpha=0.8, zorder=5)
        ax_px.text(i_10min+0.2, ax_px.get_ylim()[1], "+10m",
                   color=PURPLE, fontsize=6, va='top')

    # Zona VP shaded en chart
    if vah is not None and val is not None:
        ax_px.axhspan(val, vah, alpha=0.06, color=CYAN, zorder=1)

    # Ejes X: solo horas en punto
    hour_idxs  = [i3 for i3, t in enumerate(times) if t.endswith(":00")]
    hour_labels= [t for t in times if t.endswith(":00")]
    ax_px.set_xticks(hour_idxs)
    ax_px.set_xticklabels(hour_labels, fontsize=7, color=GRAY)
    ax_px.set_xlim(-1, n + 2)
    ax_px.grid(axis='y', color='#1a2535', linewidth=0.6, linestyle=':')

    # Sincronizar eje Y con VP
    y_min_plot = lows.min()  if len(lows)  > 0 else 0
    y_max_plot = highs.max() if len(highs) > 0 else 1
    margin = (y_max_plot - y_min_plot) * 0.06
    ax_px.set_ylim(y_min_plot - margin, y_max_plot + margin)
    ax_vp.set_ylim(ax_px.get_ylim())

    # Color del título según dirección
    dir_color = GREEN if ny_dir == "BULL" else (RED if ny_dir == "BEAR" else GRAY)
    dir_emoji = "⬆️" if ny_dir == "BULL" else ("⬇️" if ny_dir == "BEAR" else "➡️")

    fig.suptitle(
        f"JUEVES {thu_date}  |  Jobless Claims 8:30 ET  |  "
        f"Spike 8:30: {sp_move:+.0f} pts  |  NY: {ny_move:+.0f} pts {dir_emoji}",
        color=WHITE, fontsize=10, fontweight='bold', y=0.97
    )

    # Legend
    legend_items = [
        Line2D([0],[0], color=GREEN,  linestyle='--', label=f"VAH {vah:.0f}" if vah else "VAH"),
        Line2D([0],[0], color=GOLD,   linestyle='-',  label=f"POC {poc:.0f}" if poc else "POC"),
        Line2D([0],[0], color=RED,    linestyle='--', label=f"VAL {val:.0f}" if val else "VAL"),
        Line2D([0],[0], color=ORANGE, linestyle='--', label="8:30 Claims"),
        Line2D([0],[0], color=GOLD,   linewidth=1.5,  label="9:30 NY Open"),
    ]
    ax_px.legend(handles=legend_items, loc='upper right', fontsize=6.5,
                 facecolor='#111827', edgecolor='#374151', labelcolor=WHITE,
                 ncol=3, framealpha=0.9)

    out_path = os.path.join(OUT_DIR, f"jue_{thu_date}.png")
    plt.savefig(out_path, dpi=130, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  ✅ {thu_date}  Spike:{sp_move:+.0f}  NY:{ny_move:+.0f}  {dir_emoji} → {out_path}")

    return {
        "date":     thu_date,
        "spike":    sp_move,
        "ny_move":  ny_move,
        "ny_dir":   ny_dir,
        "vah":      vah,
        "poc":      poc,
        "val":      val,
        "path":     out_path,
    }


# ─── RESUMEN GRID ─────────────────────────────────────────────────────────────
def chart_summary(results):
    """Un grid con todos los jueves en una sola imagen."""
    n     = len(results)
    if n == 0:
        return
    cols  = 3
    rows  = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(18, rows * 5), facecolor=BG)
    axes_flat = axes.flatten() if rows > 1 else [axes] if cols == 1 else list(axes.flatten())

    for i, res in enumerate(results):
        ax = axes_flat[i]
        try:
            img = plt.imread(res["path"])
            ax.imshow(img)
        except Exception:
            ax.text(0.5, 0.5, str(res["date"]), ha='center', va='center',
                    color=WHITE, fontsize=10)
        ax.axis('off')

        dir_color = GREEN if res["ny_dir"]=="BULL" else (RED if res["ny_dir"]=="BEAR" else GRAY)
        emoji     = "⬆️" if res["ny_dir"]=="BULL" else ("⬇️" if res["ny_dir"]=="BEAR" else "➡️")
        ax.set_title(f"{res['date']}  {emoji}  NY {res['ny_move']:+.0f}pts  |  Spike {res['spike']:+.0f}pts",
                     color=dir_color, fontsize=8, fontweight='bold', pad=4)

    # Apagar ejes vacíos
    for j in range(n, len(axes_flat)):
        axes_flat[j].axis('off')

    # Estadísticas generales en el supertítulo
    bear_n    = sum(1 for r in results if r["ny_dir"] == "BEAR")
    bull_n    = sum(1 for r in results if r["ny_dir"] == "BULL")
    flat_n    = sum(1 for r in results if r["ny_dir"] == "FLAT")
    spk_up_n  = sum(1 for r in results if r["spike"] > 20)
    trap_n    = sum(1 for r in results if r["spike"] > 20 and r["ny_dir"] == "BEAR")
    trap_pct  = round(trap_n / spk_up_n * 100) if spk_up_n else 0

    fig.suptitle(
        f"BACKTEST JUEVES JOBLESS CLAIMS — NQ Nasdaq — Volume Profile Asia→9:40 NY\n"
        f"Total: {n} jueves  |  ⬇️ BEAR: {bear_n} ({round(bear_n/n*100)}%)  |  "
        f"⬆️ BULL: {bull_n}  |  ➡️ FLAT: {flat_n}  |  "
        f"🪤 TRAMPA ↑: {trap_pct}% (spike ↑ → NY cae)",
        color=WHITE, fontsize=11, fontweight='bold', y=0.998
    )

    out = os.path.join(OUT_DIR, "RESUMEN_TODOS_JUEVES.png")
    plt.tight_layout(rect=[0, 0, 1, 0.99])
    plt.savefig(out, dpi=120, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"\n  📊 RESUMEN guardado: {out}")
    return out


# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("📂 Cargando CSV...")
    df = load_csv()
    print(f"   Datos: {df.index.min().date()} → {df.index.max().date()}")

    thursdays = get_thursdays(df)
    print(f"\n   Jueves encontrados: {len(thursdays)}")

    results = []
    for i, thu in enumerate(thursdays):
        print(f"\n  [{i+1}/{len(thursdays)}] Procesando {thu}...")
        res = chart_thursday(df, thu, i, len(thursdays))
        if res:
            results.append(res)

    if results:
        print(f"\n📊 Generando RESUMEN de {len(results)} jueves...")
        resumen = chart_summary(results)

        print(f"\n{'='*65}")
        print(f"  RESULTADOS FINALES BACKTEST JUEVES")
        print(f"{'='*65}")
        for r in results:
            e = "⬆️" if r["ny_dir"]=="BULL" else ("⬇️" if r["ny_dir"]=="BEAR" else "➡️")
            print(f"  {r['date']}  Spike:{r['spike']:>+5.0f}  NY:{r['ny_move']:>+6.0f}  {e}  "
                  f"VP: {r['val']:.0f}/{r['poc']:.0f}/{r['vah']:.0f}" if r['vah'] else "  sin VP")

        bear = sum(1 for r in results if r["ny_dir"]=="BEAR")
        bull = sum(1 for r in results if r["ny_dir"]=="BULL")
        flat = sum(1 for r in results if r["ny_dir"]=="FLAT")
        spk_up = sum(1 for r in results if r["spike"] > 20)
        trap   = sum(1 for r in results if r["spike"] > 20 and r["ny_dir"] == "BEAR")
        n = len(results)
        print(f"\n  Total: {n}j | ⬇️ BEAR {bear} ({round(bear/n*100)}%) | ⬆️ BULL {bull} | ➡️ FLAT {flat}")
        print(f"  🪤 Spike↑ con NY bajando: {trap}/{spk_up} = {round(trap/spk_up*100) if spk_up else 0}%")
        print(f"\n  📁 Imágenes en: {OUT_DIR}/")
        if resumen:
            print(f"  🖼  http://localhost:8085/{resumen.replace(chr(92),'/')}")
    else:
        print("⚠️  No se procesaron jueves")


if __name__ == "__main__":
    main()
