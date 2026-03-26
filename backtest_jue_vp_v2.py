"""
BACKTEST JUEVES v2 — VELAS CLARAS + DATOS REALES DE NOTICIAS
Volume Profile Asia→9:40 + Claims actual/forecast/prev + candlesticks nítidos
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
from datetime import datetime, date, timedelta
import os, pytz

ET      = pytz.timezone("America/New_York")
CSV     = "data/research/nq_15m_intraday.csv"
OUT_DIR = "assets/jue_backtest_v2"
VP_BINS = 60

# ── Paleta premium ───────────────────────────────────────────────────────────
BG    = "#050d1a"
PANEL = "#0c1624"
PANEL2= "#101d30"
CYAN  = "#00d4ff"
GOLD  = "#ffc845"
GREEN = "#00e676"
RED   = "#ff3d5a"
GRAY  = "#8899aa"
WHITE = "#dde8f5"
ORANGE= "#ff9500"
PURPLE= "#b388ff"
BLUE  = "#4fc3f7"
DKGRN = "#004d40"
DKRED = "#4a0018"

# ── Datos reales Jobless Claims ───────────────────────────────────────────────
# Fecha release (jueves) → (actual, forecast, previous)
CLAIMS = {
    date(2026, 1,  8): (201_000, 215_000, 201_000),   # semana ending Jan 3
    date(2026, 1, 15): (217_000, 212_000, 201_000),   # semana ending Jan 10
    date(2026, 1, 22): (223_000, 215_000, 217_000),   # semana ending Jan 17
    date(2026, 1, 29): (209_000, 206_000, 223_000),   # semana ending Jan 24
    date(2026, 2,  5): (231_000, 212_000, 209_000),   # semana ending Feb 1  ❗ sorpresa alcista
    date(2026, 2, 12): (227_000, 222_000, 232_000),   # semana ending Feb 8
    date(2026, 2, 19): (206_000, 223_000, 229_000),   # semana ending Feb 15  ❗ sorpresa bajista
    date(2026, 2, 26): (213_000, 215_000, 208_000),   # semana ending Feb 21
    date(2026, 3,  5): (213_000, 215_000, 213_000),   # semana ending Mar 1
    date(2026, 3, 12): (213_000, 214_000, 213_000),   # semana ending Mar 8
}


# ── Carga CSV ─────────────────────────────────────────────────────────────────
def load_csv():
    df = pd.read_csv(CSV, skiprows=2)
    df.columns = ["Datetime","Close","High","Low","Open","Volume"]
    df = df.dropna(subset=["Datetime"])
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True).dt.tz_convert(ET)
    df.set_index("Datetime", inplace=True)
    for c in ["Close","High","Low","Open","Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["Volume"] = df["Volume"].fillna(1)
    return df.dropna(subset=["Close"]).sort_index()


# ── Volume Profile ────────────────────────────────────────────────────────────
def calc_vp(df_slice, bins=VP_BINS):
    if df_slice.empty or len(df_slice) < 2:
        return None, None, None, np.array([]), np.array([])
    lo, hi = df_slice["Low"].min(), df_slice["High"].max()
    if hi == lo:
        return None, None, None, np.array([]), np.array([])

    edges   = np.linspace(lo, hi, bins + 1)
    centers = (edges[:-1] + edges[1:]) / 2
    vols    = np.zeros(bins)

    for _, row in df_slice.iterrows():
        vol_ = float(row["Volume"]) if row["Volume"] > 0 else 1
        mask = (centers >= float(row["Low"])) & (centers <= float(row["High"]))
        cnt  = mask.sum()
        if cnt > 0:
            vols[mask] += vol_ / cnt

    poc_idx = int(np.argmax(vols))
    poc     = centers[poc_idx]

    total   = vols.sum()
    target  = total * 0.70
    lo_i = hi_i = poc_idx
    accum = vols[poc_idx]
    while accum < target and (lo_i > 0 or hi_i < bins - 1):
        la = vols[lo_i - 1] if lo_i > 0 else 0
        ha = vols[hi_i + 1] if hi_i < bins - 1 else 0
        if la >= ha and lo_i > 0:
            lo_i -= 1; accum += la
        elif hi_i < bins - 1:
            hi_i += 1; accum += ha
        else:
            break

    return centers[hi_i], poc, centers[lo_i], centers, vols


# ── Jueves del CSV ────────────────────────────────────────────────────────────
def get_thursdays(df):
    return sorted({d for d in (df.index.date) if pd.Timestamp(d).weekday() == 3})


# ── Helper: filtro de tiempo ──────────────────────────────────────────────────
def bt(day_df, t0, t1):
    t0_ = datetime.strptime(t0, "%H:%M").time()
    t1_ = datetime.strptime(t1, "%H:%M").time()
    return day_df[(day_df.index.time >= t0_) & (day_df.index.time <= t1_)]


# ── Generar chart por jueves ──────────────────────────────────────────────────
def chart_thursday(df, thu_date):
    prev_day  = thu_date - timedelta(days=1)
    start_ts  = ET.localize(datetime(prev_day.year, prev_day.month, prev_day.day, 18, 0))
    end_ts    = ET.localize(datetime(thu_date.year, thu_date.month, thu_date.day, 16, 30))
    ny40_ts   = ET.localize(datetime(thu_date.year, thu_date.month, thu_date.day, 9, 40))

    day_df    = df[(df.index >= start_ts) & (df.index <= end_ts)].copy()
    if day_df.empty:
        return None

    asia_df   = day_df[day_df.index <= ny40_ts]
    vah, poc, val, vp_levels, vp_vols = calc_vp(asia_df)

    plot_df   = bt(day_df, "07:00", "16:00")
    if plot_df.empty:
        return None

    # Calcular métricas
    spike_df  = bt(day_df, "08:30", "08:44")
    pre_df    = bt(day_df, "08:00", "08:29")
    ny_df     = bt(day_df, "09:30", "16:00")

    sp_move   = 0
    if not spike_df.empty and not pre_df.empty:
        sp_move = round(float(spike_df.iloc[-1]["Close"]) - float(pre_df.iloc[-1]["Close"]), 0)

    ny_move, ny_open_px, ny_close_px = 0, 0, 0
    if not ny_df.empty:
        ny_open_px  = float(ny_df.iloc[0]["Open"])
        ny_close_px = float(ny_df.iloc[-1]["Close"])
        ny_move     = round(ny_close_px - ny_open_px, 0)

    ny_dir    = "BULL" if ny_move > 50 else ("BEAR" if ny_move < -50 else "FLAT")
    dir_color = GREEN if ny_dir == "BULL" else (RED if ny_dir == "BEAR" else GRAY)
    dir_arrow = "▲" if ny_dir == "BULL" else ("▼" if ny_dir == "BEAR" else "▬")

    # Claims data
    claims             = CLAIMS.get(thu_date, (None, None, None))
    actual, fcst, prev = claims
    if actual and fcst:
        surprise     = actual - fcst
        surp_color   = GREEN if surprise < 0 else RED   # menos claims = mejor para mercado
        surp_label   = f"{'MEJOR' if surprise<0 else 'PEOR'} de lo esperado ({surprise:+,}K)" if surprise != 0 else "EN LÍNEA"
    else:
        surprise, surp_color, surp_label = None, GRAY, "N/D"

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(16, 8), facecolor=BG, dpi=110)
    gs  = gridspec.GridSpec(2, 6,
                            height_ratios=[1, 5],
                            hspace=0.0,
                            wspace=0.04,
                            left=0.04, right=0.97,
                            top=0.93, bottom=0.08)

    ax_news = fig.add_subplot(gs[0, :])      # banner noticias (fila 0, todo)
    ax_vp   = fig.add_subplot(gs[1, 0])     # VP (fila 1, col 0)
    ax_px   = fig.add_subplot(gs[1, 1:])    # precio (fila 1, resto)

    # ── BANNER NOTICIAS ──────────────────────────────────────────────────────
    ax_news.set_facecolor(PANEL2)
    ax_news.set_xlim(0, 1); ax_news.set_ylim(0, 1)
    ax_news.axis('off')

    left = 0.01
    # Título fecha
    ax_news.text(left, 0.75, f"JUEVES {thu_date.strftime('%d %b %Y').upper()}",
                 color=WHITE, fontsize=13, fontweight='bold', va='top', transform=ax_news.transAxes)

    ax_news.text(left + 0.22, 0.78, "INITIAL JOBLESS CLAIMS  8:30 ET",
                 color=GOLD, fontsize=10, fontweight='bold', va='top', transform=ax_news.transAxes)

    # Bloque Claims
    bx   = 0.50
    if actual:
        ax_news.text(bx,       0.85, f"{actual:,}", color=surp_color, fontsize=16,
                     fontweight='bold', va='top', transform=ax_news.transAxes)
        ax_news.text(bx,       0.30, "ACTUAL",       color=GRAY,      fontsize=7,
                     va='top', transform=ax_news.transAxes)
        ax_news.text(bx+0.09,  0.85, f"{fcst:,}",   color=GRAY,      fontsize=13,
                     va='top', transform=ax_news.transAxes)
        ax_news.text(bx+0.09,  0.30, "FORECAST",    color=GRAY,      fontsize=7,
                     va='top', transform=ax_news.transAxes)
        ax_news.text(bx+0.18,  0.85, f"{prev:,}",   color=GRAY,      fontsize=13,
                     va='top', transform=ax_news.transAxes)
        ax_news.text(bx+0.18,  0.30, "PREV",        color=GRAY,      fontsize=7,
                     va='top', transform=ax_news.transAxes)
        ax_news.text(bx+0.29,  0.80, surp_label,    color=surp_color,fontsize=9,
                     fontweight='bold', va='top', transform=ax_news.transAxes)

    # Resultado del día
    rx = 0.82
    ax_news.text(rx,      0.85, f"NY Sesión:  {ny_move:+.0f} pts",
                 color=dir_color, fontsize=12, fontweight='bold', va='top', transform=ax_news.transAxes)
    ax_news.text(rx,      0.30, f"Spike 8:30: {sp_move:+.0f} pts",
                 color=ORANGE,   fontsize=9,  va='top', transform=ax_news.transAxes)

    # Línea separadora
    ax_news.axhline(0.08, color='#1e3a5f', linewidth=1)

    # ── VOLUME PROFILE ───────────────────────────────────────────────────────
    ax_vp.set_facecolor(PANEL)
    ax_vp.spines[:].set_visible(False)
    ax_vp.tick_params(left=False, bottom=False, labelbottom=False,
                      labelleft=True, labelsize=6.5, labelcolor=GRAY, pad=1)

    # y-axis solo izq
    ax_vp.yaxis.set_label_position("left")

    if len(vp_levels) > 0:
        bar_h   = (vp_levels[1] - vp_levels[0]) * 0.92 if len(vp_levels) > 1 else 5
        nv      = vp_vols / vp_vols.max() if vp_vols.max() > 0 else vp_vols
        bar_col = [CYAN if (val and vah and val <= p <= vah) else "#193243" for p in vp_levels]
        ax_vp.barh(vp_levels, nv, height=bar_h, color=bar_col, alpha=0.95, linewidth=0)

        # POC barra más gruesa
        poc_idx_local = int(np.argmin(np.abs(vp_levels - poc))) if poc else 0
        ax_vp.barh([vp_levels[poc_idx_local]], [nv[poc_idx_local]], height=bar_h,
                   color=GOLD, alpha=1.0, linewidth=0)

        if vah: ax_vp.axhline(vah, color=GREEN, lw=1.5, ls='--')
        if poc: ax_vp.axhline(poc, color=GOLD,  lw=2.2)
        if val: ax_vp.axhline(val, color=RED,   lw=1.5, ls='--')

        # Etiquetas
        if vah: ax_vp.text(0.98, vah, f"VAH {vah:.0f}", color=GREEN, fontsize=6.5,
                            ha='right', va='bottom', fontweight='bold')
        if poc: ax_vp.text(0.98, poc, f"POC {poc:.0f}", color=GOLD,  fontsize=7.0,
                            ha='right', va='bottom', fontweight='bold')
        if val: ax_vp.text(0.98, val, f"VAL {val:.0f}", color=RED,   fontsize=6.5,
                            ha='right', va='top',    fontweight='bold')

    ax_vp.set_xlim(0, 1.15); ax_vp.invert_xaxis()
    ax_vp.set_title("VP\nASIA\n→9:40", color=GRAY, fontsize=7, pad=3)

    # ── PRECIO (VELAS) ───────────────────────────────────────────────────────
    ax_px.set_facecolor(PANEL)
    for sp in ax_px.spines.values():
        sp.set_color('#1a2d44')
    ax_px.tick_params(colors=GRAY, labelsize=8)
    ax_px.grid(axis='y', color='#0d1f33', lw=0.8, ls=':')

    opens  = plot_df["Open"].values.astype(float)
    closes = plot_df["Close"].values.astype(float)
    highs  = plot_df["High"].values.astype(float)
    lows   = plot_df["Low"].values.astype(float)
    n      = len(opens)
    xs     = np.arange(n)

    # Velas sólidas grandes
    for i in range(n):
        bull = closes[i] >= opens[i]
        c_fill  = GREEN  if bull else RED
        c_wick  = "#00a854" if bull else "#c0002a"
        body_lo = min(opens[i], closes[i])
        body_hi = max(opens[i], closes[i])
        body_h  = max(body_hi - body_lo, 0.5)  # mínimo visible

        # Mecha
        ax_px.plot([i, i], [lows[i], highs[i]], color=c_wick, lw=0.9, zorder=3)
        # Cuerpo
        rect = plt.Rectangle((i - 0.38, body_lo), 0.76, body_h,
                               facecolor=c_fill, edgecolor=c_wick, lw=0.4, zorder=4)
        ax_px.add_patch(rect)

    # Líneas VP
    if vah: ax_px.axhline(vah, color=GREEN, lw=1.2, ls='--', alpha=0.85, zorder=2)
    if poc: ax_px.axhline(poc, color=GOLD,  lw=1.8, ls='-',  alpha=0.90, zorder=2)
    if val: ax_px.axhline(val, color=RED,   lw=1.2, ls='--', alpha=0.85, zorder=2)

    # Zona valor VP
    if vah and val:
        ax_px.axhspan(val, vah, alpha=0.05, color=CYAN, zorder=1)

    # Etiquetas derecha
    ylim_lo, ylim_hi = lows.min() - 30, highs.max() + 30
    ax_px.set_ylim(ylim_lo, ylim_hi)
    if vah: ax_px.text(n + 0.3, vah, " VAH", color=GREEN, fontsize=7, va='bottom')
    if poc: ax_px.text(n + 0.3, poc, " POC", color=GOLD,  fontsize=7.5, va='bottom', fontweight='bold')
    if val: ax_px.text(n + 0.3, val, " VAL", color=RED,   fontsize=7, va='top')

    # Líneas verticales eventos
    times = [t.strftime("%H:%M") for t in plot_df.index]
    def v_idx(t_str):
        for ii, t in enumerate(times):
            if t >= t_str: return ii
        return None

    i_claims = v_idx("08:30")
    i_open   = v_idx("09:30")
    i_10m    = v_idx("09:40")

    ymax = ylim_hi
    if i_claims is not None:
        ax_px.axvline(i_claims, color=ORANGE, lw=2.0, ls='--', alpha=0.9, zorder=6)
        ax_px.text(i_claims + 0.3, ymax - (ymax - ylim_lo)*0.02,
                   "8:30\nCLAIMS", color=ORANGE, fontsize=7.5, fontweight='bold', va='top')

    if i_open is not None:
        ax_px.axvline(i_open, color=GOLD, lw=2.0, ls='--', alpha=0.9, zorder=6)
        ax_px.text(i_open + 0.3, ymax - (ymax - ylim_lo)*0.02,
                   "9:30\nNY OPEN", color=GOLD, fontsize=7.5, fontweight='bold', va='top')

    if i_10m is not None:
        ax_px.axvline(i_10m, color=PURPLE, lw=1.2, ls=':', alpha=0.8, zorder=5)
        ax_px.text(i_10m + 0.3, ymax - (ymax - ylim_lo)*0.12,
                   "+10m", color=PURPLE, fontsize=7, va='top')

    # Eje X: etiquetas por hora
    hour_idxs = [ii for ii, t in enumerate(times) if t.endswith(":00")]
    hour_lbls = [t for t in times if t.endswith(":00")]
    ax_px.set_xticks(hour_idxs)
    ax_px.set_xticklabels(hour_lbls, fontsize=7.5, color=GRAY)
    ax_px.set_xlim(-2, n + 5)

    # Sincronizar y con VP
    ax_vp.set_ylim(ax_px.get_ylim())

    # Legend compact
    legend_h = [
        Line2D([0],[0], color=GREEN, ls='--', lw=1.5, label=f"VAH {vah:.0f}" if vah else "VAH"),
        Line2D([0],[0], color=GOLD,  ls='-',  lw=2.0, label=f"POC {poc:.0f}" if poc else "POC"),
        Line2D([0],[0], color=RED,   ls='--', lw=1.5, label=f"VAL {val:.0f}" if val else "VAL"),
        mpatches.Patch(facecolor=GREEN, label="Vela alcista"),
        mpatches.Patch(facecolor=RED,   label="Vela bajista"),
    ]
    ax_px.legend(handles=legend_h, loc='upper right', fontsize=7, ncol=5,
                 facecolor='#0a1929', edgecolor='#1e3a5f', labelcolor=WHITE,
                 framealpha=0.95)

    # Título
    fig.suptitle(
        f"NQ Futures • Jobless Claims • {thu_date.strftime('%A %d %B %Y').upper()}  "
        f"│ Volume Profile: Sesión Asia → 9:40 NY",
        color=WHITE, fontsize=11, fontweight='bold', y=0.975
    )

    out = os.path.join(OUT_DIR, f"jue_v2_{thu_date}.png")
    plt.savefig(out, dpi=130, bbox_inches='tight', facecolor=BG)
    plt.close(fig)

    print(f"  OK {thu_date}  Claims:{actual:,}  Fcst:{fcst:,}  Spike:{sp_move:+.0f}  NY:{ny_move:+.0f} {'BEAR' if ny_dir=='BEAR' else 'BULL' if ny_dir=='BULL' else 'FLAT'}")
    return dict(date=thu_date, spike=sp_move, ny_move=ny_move, ny_dir=ny_dir,
                vah=vah, poc=poc, val=val, actual=actual, fcst=fcst, path=out)


# ── Imagen RESUMEN ────────────────────────────────────────────────────────────
def chart_summary(results):
    n    = len(results)
    cols = 2
    rows = (n + 1) // 2

    fig, axes = plt.subplots(rows, cols, figsize=(28, rows * 9), facecolor=BG)
    flat = axes.flatten()

    for i, r in enumerate(results):
        ax = flat[i]
        try:
            img = plt.imread(r["path"])
            ax.imshow(img, aspect='auto')
        except Exception:
            ax.text(0.5, 0.5, str(r["date"]), ha='center', va='center',
                    color=WHITE, fontsize=12)
        ax.axis('off')

    for j in range(n, len(flat)):
        flat[j].axis('off')

    bear_n = sum(1 for r in results if r["ny_dir"]=="BEAR")
    bull_n = sum(1 for r in results if r["ny_dir"]=="BULL")
    flat_n = sum(1 for r in results if r["ny_dir"]=="FLAT")
    spk_up = sum(1 for r in results if r["spike"] > 20)
    trap   = sum(1 for r in results if r["spike"] > 20 and r["ny_dir"]=="BEAR")

    fig.suptitle(
        f"BACKTEST JUEVES JOBLESS CLAIMS  |  NQ Nasdaq Futures\n"
        f"Total {n} jueves  |  BEAR {bear_n} ({round(bear_n/n*100)}%)  |  "
        f"BULL {bull_n}  |  FLAT {flat_n}  |  "
        f"Trampa Spike-UP: {trap}/{spk_up} = {round(trap/spk_up*100) if spk_up else 0}%",
        color=WHITE, fontsize=13, fontweight='bold', y=1.002
    )

    plt.tight_layout()
    out = os.path.join(OUT_DIR, "RESUMEN_v2_TODOS_JUEVES.png")
    plt.savefig(out, dpi=110, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"\n  RESUMEN: {out}")
    return out


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("Cargando CSV...")
    df = load_csv()
    print(f"  {df.index.min().date()} → {df.index.max().date()}")

    thursdays = get_thursdays(df)
    print(f"  Jueves: {len(thursdays)}\n")

    results = []
    for thu in thursdays:
        r = chart_thursday(df, thu)
        if r:
            results.append(r)

    if results:
        chart_summary(results)
        n = len(results)
        bear = sum(1 for r in results if r["ny_dir"]=="BEAR")
        spk  = sum(1 for r in results if r["spike"] > 20)
        trap = sum(1 for r in results if r["spike"] > 20 and r["ny_dir"]=="BEAR")
        print(f"\n  BEAR: {bear}/{n} ({round(bear/n*100)}%)  |  Trampa: {trap}/{spk} = {round(trap/spk*100) if spk else 0}%")
        print(f"  Ver: http://localhost:8085/{OUT_DIR}/RESUMEN_v2_TODOS_JUEVES.png")


if __name__ == "__main__":
    main()
