"""
chart_sessions_thursday.py  v5  — VELAS VISIBLES 15min
Agrega 5min → 15min  => ~96 barras legibles
Recuadros sesión  |  Brackets de rango  |  Volume Profile con gradiente
"""

import os, json, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colorbar import ColorbarBase
from matplotlib.colors import Normalize

warnings.filterwarnings("ignore")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR  = os.path.join(BASE_DIR, "thursday_session_charts")
os.makedirs(OUT_DIR, exist_ok=True)

# ── PALETA ───────────────────────────────────
BG    = "#080c14";  PANEL = "#0d1421"
GOLD  = "#FFD700";  GREEN = "#00e676";  RED   = "#ff1744"
BLUE  = "#29b6f6";  CYAN  = "#00e5ff";  GRAY  = "#607d8b"
WHITE = "#ecf0f1";  ORANGE= "#ffab40"
C_ASIA = "#29b6f6"   # azul
C_LON  = "#00e676"   # verde
C_NY   = "#ff1744"   # rojo

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor":   PANEL,
    "axes.edgecolor":   "#253040", "text.color": WHITE,
    "font.family":      "DejaVu Sans",
    "xtick.labelsize":  11, "ytick.labelsize":  11,
    "grid.color": "#1a2535", "grid.linestyle": "-",
    "grid.linewidth": 0.5, "grid.alpha": 0.35,
})

# ── 5-min bars: sesiones ─────────────────────
# Cada barra = 5min. Un día: 18:00 EST → 16:00 siguiente ≈ 22h = 264 barras.
# Asia   18:00–02:00  = barras  0– 95  (8h  = 96  barras 5min)
# London 02:00–09:30  = barras 96–186  (7.5h= 90  barras 5min)  ← abre a las 02:00 EST
# NY     09:30–16:00  = barras 187–263 (6.5h= 78  barras 5min)

A5_S=0; A5_E=96        # Asia
L5_S=96; L5_E=186      # London
N5_S=186; N5_E=264     # NY  (NY open = barra 186 = 08:30 → 09:30 aprox)

# Después de agregar a 15min (dividir entre 3):
AG = 3                  # factor de agregación
A_S=0;  A_E=32          # Asia 15min
L_S=32; L_E=62          # London 15min
N_S=62; N_E=88          # NY 15min

THURSDAY_NEWS = {
    "2026-01-08": {"name": "Jobless Claims + Consumer Credit",  "slot_5": 186, "impact": "HIGH"},
    "2026-01-15": {"name": "PPI Final Demand + Retail Sales",   "slot_5": 186, "impact": "HIGH"},
    "2026-01-22": {"name": "Jobless Claims + Philly Fed",       "slot_5": 186, "impact": "HIGH"},
    "2026-01-29": {"name": "GDP Advance Q4 + Jobless Claims",   "slot_5": 186, "impact": "HIGH"},
    "2026-02-05": {"name": "Jobless Claims + Trade Balance",    "slot_5": 186, "impact": "HIGH"},
    "2026-02-12": {"name": "CPI Core YoY + Jobless Claims",     "slot_5": 198, "impact": "HIGH"},
    "2026-02-19": {"name": "PPI Core + Jobless Claims",         "slot_5": 186, "impact": "HIGH"},
    "2026-02-26": {"name": "PCE Core MoM + GDP Revision",       "slot_5": 186, "impact": "HIGH"},
    "2026-03-05": {"name": "Jobless Claims + ISM Services",     "slot_5": 198, "impact": "MEDIUM"},
    "2026-03-12": {"name": "CPI Headline & Core MoM/YoY",      "slot_5": 186, "impact": "HIGH"},
    "2026-03-19": {"name": "Jobless Claims + Philly Fed Mfg",   "slot_5": 186, "impact": "HIGH"},
}

# Horarios en 15min bars para el eje X
# barra 0 = 18:00,  cada barra = 15min
TIME_TICKS = [
    (0,  "18:00"), (4,  "19:00"), (8,  "20:00"), (12, "21:00"),
    (16, "22:00"), (20, "23:00"), (24, "00:00"), (28, "01:00"),
    (32, "02:00"), (36, "03:00"), (40, "04:00"), (44, "05:00"),
    (48, "06:00"), (52, "07:00"), (56, "08:00"), (60, "09:00"),
    (62, "09:30"), (64, "10:00"), (68, "11:00"), (72, "12:00"),
    (76, "13:00"), (80, "14:00"), (84, "15:00"), (88, "16:00"),
]

# ════════════════════════════════════════════
#  GENERAR PRECIO 5-min (264 barras)
# ════════════════════════════════════════════
def gen_price_5min(rec, n=264):
    val = rec["val"]; poc = rec["poc"]; vah = rec["vah"]
    rng = vah - val
    up  = "UP" in rec["space_dir"]
    p   = np.zeros(n)
    p[0] = rec["pm_close"]
    # Asia: deriva lenta hacia poc
    for i in range(1, A5_E):
        p[i] = p[i-1] + (poc - p[i-1]) * 0.025 + np.random.normal(0, rng * 0.006)
    # London: toca VAH o VAL según dirección
    lt = vah if up else val
    for i in range(L5_S, L5_E):
        p[i] = p[i-1] + (lt - p[i-1]) * 0.018 + np.random.normal(0, rng * 0.009)
    # NY open
    p[N5_S] = rec["open"]
    target = rec["extreme"]
    sp_end = N5_S + 24  # primer impulso: 2h
    for i in range(N5_S + 1, sp_end):
        t = ((i - N5_S) / (sp_end - N5_S)) ** 0.55
        p[i] = rec["open"] + (target - rec["open"]) * t + np.random.normal(0, rng * 0.007)
    # Post-extremo
    if rec["returned_poc"]:
        for i in range(sp_end, n):
            t = min((i - sp_end) / max(n - sp_end, 1) * 1.4, 1.0)
            p[i] = target + (poc - target) * t + np.random.normal(0, rng * 0.004)
    else:
        for i in range(sp_end, n):
            p[i] = p[i-1] + np.random.normal(0, rng * 0.005) + (target - p[i-1]) * 0.012
    return p


def agg_15min(p5):
    """Agrega precio 5min → OHLCV 15min."""
    n5 = len(p5)
    n15 = n5 // AG
    O = np.zeros(n15); H = np.zeros(n15); L = np.zeros(n15)
    C = np.zeros(n15); V = np.zeros(n15)
    for i in range(n15):
        seg = p5[i*AG:(i+1)*AG]
        noise = abs(seg[-1] - seg[0]) * 0.5 + np.random.uniform(0.5, 3.5)
        O[i] = seg[0]
        C[i] = seg[-1]
        H[i] = max(seg) + noise * np.random.uniform(0.3, 1.0)
        L[i] = min(seg) - noise * np.random.uniform(0.3, 1.0)
        # Volumen base; explosivo en NY open y news
        base = 800
        bar_time = i  # barra 15min
        if N_S <= bar_time <= N_S + 3:  base = 7000
        if abs(bar_time - N_S - 8) < 3: base = 5000
        V[i] = base * np.random.uniform(0.5, 1.5)
    return O, H, L, C, V


# ════════════════════════════════════════════
#  DIBUJAR VELAS (OHLCV)
# ════════════════════════════════════════════
def draw_candles(ax, O, H, L, C, bar_w=0.7):
    for i in range(len(O)):
        bull   = C[i] >= O[i]
        color  = GREEN if bull else RED
        body_lo = min(O[i], C[i])
        body_hi = max(O[i], C[i])
        body_h  = max(body_hi - body_lo, 0.5)   # mínimo visible

        # Mecha (wick)
        ax.plot([i, i], [L[i], H[i]], color=color, lw=1.2, zorder=2)

        # Cuerpo sólido
        ax.add_patch(plt.Rectangle(
            (i - bar_w/2, body_lo), bar_w, body_h,
            facecolor=color, zorder=3,
            edgecolor="#111820", linewidth=0.4
        ))


# ════════════════════════════════════════════
#  VOLUME PROFILE
# ════════════════════════════════════════════
def build_profile(O, H, L, C, V, n_bins=60):
    pmin = L.min(); pmax = H.max()
    bins = np.linspace(pmin, pmax, n_bins + 1)
    vacc = np.zeros(n_bins)
    for i in range(len(O)):
        for b in range(n_bins):
            if bins[b] <= H[i] and bins[b+1] >= L[i]:
                span = max(sum(1 for b2 in range(n_bins)
                               if bins[b2] <= H[i] and bins[b2+1] >= L[i]), 1)
                vacc[b] += V[i] / span
    mid = (bins[:-1] + bins[1:]) / 2
    return mid, vacc


def session_box(ax, x0, x1, ylo, yhi, col, bg_a=0.08):
    """Recuadro de sesión con fondo + borde."""
    ax.axvspan(x0, x1, facecolor=col, alpha=bg_a, zorder=0)
    for y in [ylo, yhi]:
        ax.plot([x0, x1], [y, y], color=col, lw=2.0, alpha=0.55, ls="--", zorder=1)
    ax.plot([x0, x0], [ylo, yhi], color=col, lw=3.0, alpha=0.80, zorder=1)
    ax.plot([x1, x1], [ylo, yhi], color=col, lw=2.0, alpha=0.60, zorder=1)


def range_bracket(ax, x0, x1, ylo, yhi, col, label):
    """Bracket izquierdo que indica el rango de sesión."""
    pts = yhi - ylo
    mid = (yhi + ylo) / 2
    bx  = x0 - 1.2
    tck = (yhi - ylo) * 0.05
    ax.plot([bx, bx], [ylo, yhi], color=col, lw=2.2, alpha=0.9, zorder=7)
    ax.plot([bx, bx + tck * 2.5], [yhi, yhi], color=col, lw=2.2, alpha=0.9, zorder=7)
    ax.plot([bx, bx + tck * 2.5], [ylo, ylo], color=col, lw=2.2, alpha=0.9, zorder=7)
    ax.text(bx - 0.4, mid, f"{label}\n{pts:.0f}p",
            fontsize=10, color=col, fontweight="bold",
            ha="right", va="center", zorder=8,
            bbox=dict(facecolor=BG, alpha=0.85, edgecolor=col,
                      boxstyle="round,pad=0.35", lw=1.5))


# ════════════════════════════════════════════
#  MAIN LOOP
# ════════════════════════════════════════════
json_path = os.path.join(BASE_DIR, "thursday_space_move_summary.json")
with open(json_path, encoding="utf-8") as f:
    bt = json.load(f)

print(f"\n  📊 Generando {len(bt['records'])} charts v5  (velas 15min)...\n")

for rec in bt["records"]:
    date_str = rec["date"]
    news     = THURSDAY_NEWS.get(date_str, {"name": "Economic Data", "slot_5": 186, "impact": "HIGH"})
    up       = "UP" in rec["space_dir"]
    sp_pts   = rec["space_size_pts"]
    ret_poc  = rec["returned_poc"]
    dir_sym  = "▲" if up else "▼"
    ar_col   = GREEN if up else RED

    np.random.seed(int(date_str.replace("-", "")) % 9999)

    # Precio 5min → agregar a 15min
    p5            = gen_price_5min(rec)
    O, H, L, C, V = agg_15min(p5)
    n_bars         = len(O)   # ≈ 88

    val   = rec["val"]; poc = rec["poc"]; vah = rec["vah"]
    pm_hi = rec["pm_hi"]; pm_lo = rec["pm_lo"]

    # Rangos por sesión (barras 15min)
    ah = H[A_S:A_E].max();   al = L[A_S:A_E].min()
    lh = H[L_S:L_E].max();   ll = L[L_S:L_E].min()
    nh = H[N_S:].max();       nl = L[N_S:].min()

    pmin = L.min() - (vah - val) * 0.07
    pmax = H.max() + (vah - val) * 0.20
    prng = pmax - pmin

    # News position in 15min bars
    news_bar = news["slot_5"] // AG

    # ── FIGURA ────────────────────────────────
    fig = plt.figure(figsize=(32, 18), facecolor=BG, dpi=150)
    gs  = plt.GridSpec(
        2, 2, figure=fig,
        height_ratios=[8, 2],
        width_ratios=[1.05, 10.5],
        hspace=0.04, wspace=0.025,
        left=0.04, right=0.975,
        top=0.90, bottom=0.065,
    )
    ax_p = fig.add_subplot(gs[:, 0])                    # Volume Profile
    ax_m = fig.add_subplot(gs[0, 1])                    # Chart principal
    ax_v = fig.add_subplot(gs[1, 1], sharex=ax_m)       # Volumen

    x_arr = np.arange(n_bars)

    # ── RECUADROS SESIÓN ──────────────────────
    session_box(ax_m, A_S, A_E, al, ah, C_ASIA, bg_a=0.10)
    session_box(ax_m, L_S, L_E, ll, lh, C_LON,  bg_a=0.09)
    session_box(ax_m, N_S, n_bars, nl, nh, C_NY, bg_a=0.08)
    ax_v.axvspan(A_S, A_E, facecolor=C_ASIA, alpha=0.12, zorder=0)
    ax_v.axvspan(L_S, L_E, facecolor=C_LON,  alpha=0.12, zorder=0)
    ax_v.axvspan(N_S, n_bars, facecolor=C_NY, alpha=0.10, zorder=0)

    # Separadores
    for xv, col in [(A_E, C_ASIA), (L_E, C_LON), (N_S, C_NY)]:
        ax_m.axvline(xv, color=col, lw=2.5, alpha=0.75, zorder=5)
        ax_v.axvline(xv, color=col, lw=1.8, alpha=0.55, zorder=5)

    # ── VELAS ─────────────────────────────────
    draw_candles(ax_m, O, H, L, C, bar_w=0.72)

    # ── BRACKETS DE RANGO ─────────────────────
    range_bracket(ax_m, A_S, A_E,  al, ah, C_ASIA, "ASIA")
    range_bracket(ax_m, L_S, L_E,  ll, lh, C_LON,  "LON")
    range_bracket(ax_m, N_S, n_bars, nl, nh, C_NY,  "NY")

    # ── NIVELES CLAVE ─────────────────────────
    ax_m.fill_between(x_arr, val, vah, alpha=0.07, color=GOLD, zorder=1)
    ax_m.axhline(poc, color=GOLD,  lw=3.0, ls="-",  alpha=0.95, zorder=6)
    ax_m.axhline(vah, color=GREEN, lw=2.0, ls="--", alpha=0.80, zorder=6)
    ax_m.axhline(val, color=RED,   lw=2.0, ls="--", alpha=0.80, zorder=6)
    ax_m.axhline(pm_hi, color=GRAY, lw=1.2, ls=":", alpha=0.55)
    ax_m.axhline(pm_lo, color=GRAY, lw=1.2, ls=":", alpha=0.55)

    # Labels niveles (lado derecho, fuera del gráfico)
    rx = n_bars + 0.8
    for price, lbl, col, bld in [
        (poc,   f"POC  {poc:.0f}",  GOLD,  True),
        (vah,   f"VAH  {vah:.0f}",  GREEN, True),
        (val,   f"VAL  {val:.0f}",  RED,   True),
        (pm_hi, f"PDH {pm_hi:.0f}", GRAY,  False),
        (pm_lo, f"PDL {pm_lo:.0f}", GRAY,  False),
    ]:
        ax_m.text(rx, price, f" {lbl}",
                  fontsize=11 if bld else 9.5,
                  color=col,
                  fontweight="bold" if bld else "normal",
                  va="center", clip_on=False)

    # ── SPACE MOVE ARROW ──────────────────────
    arx = N_S + 5
    ax_m.annotate(
        "",
        xy=(arx, rec["extreme"]), xytext=(arx, rec["open"]),
        arrowprops=dict(arrowstyle="-|>", color=ar_col, lw=5.0, mutation_scale=35),
        zorder=10,
    )
    mid_ar = (rec["open"] + rec["extreme"]) / 2
    ax_m.text(arx + 2.5, mid_ar,
              f" {dir_sym} SPACE MOVE\n {sp_pts:.0f} pts",
              fontsize=14, color=ar_col, fontweight="bold", va="center", zorder=11,
              bbox=dict(facecolor="#05080f", alpha=0.95, edgecolor=ar_col,
                        boxstyle="round,pad=0.6", lw=2.5))

    # ── NOTICIA ───────────────────────────────
    ic = RED if news["impact"] == "HIGH" else ORANGE
    ax_m.axvline(news_bar, color=ic, lw=2.5, ls="--", alpha=0.90, zorder=8)
    ax_v.axvline(news_bar, color=ic, lw=1.8, ls="--", alpha=0.70, zorder=8)
    ax_m.text(news_bar + 0.6, pmin + prng * 0.06,
              f"📰  {news['name']}\n{news['impact']} IMPACT",
              fontsize=10.5, color=ic, va="bottom", zorder=9,
              bbox=dict(facecolor="#0d0400", alpha=0.94, edgecolor=ic,
                        boxstyle="round,pad=0.55", lw=1.8))

    # ── RETORNO AL POC ────────────────────────
    if ret_poc:
        ret_time = rec.get("ret_poc_time", "")
        if ret_time and ":" in str(ret_time):
            rh, rm = map(int, str(ret_time).split(":"))
            offset = (rh - 9) * 4 + rm // 15    # aprox en barras 15min desde NY open
            xr = N_S + max(offset, 4)
            if xr < n_bars:
                ax_m.axvline(xr, color=GOLD, lw=2.2, ls=":", alpha=0.90, zorder=8)
                ax_m.text(xr + 0.5, poc + (vah - val) * 0.09,
                          f" ↩ POC  {ret_time} ",
                          fontsize=12, color=GOLD, fontweight="bold", zorder=9,
                          bbox=dict(facecolor="#0e0b00", alpha=0.95, edgecolor=GOLD,
                                    boxstyle="round,pad=0.45", lw=2.0))

    # ── ETIQUETAS SESIÓN ──────────────────────
    y_top = pmax - prng * 0.015
    for (xc, lbl, col, icon) in [
        ((A_S + A_E)/2,    "ASIA",     C_ASIA, "🌏"),
        ((L_S + L_E)/2,    "LONDON",   C_LON,  "🏦"),
        ((N_S + n_bars)/2, "NEW YORK", C_NY,   "🗽"),
    ]:
        ax_m.text(xc, y_top, f"{icon}  {lbl}",
                  ha="center", fontsize=15, fontweight="bold", color=col, zorder=12,
                  bbox=dict(facecolor=BG, alpha=0.80, edgecolor=col,
                            boxstyle="round,pad=0.4", lw=1.8))

    # ── EJES CHART ────────────────────────────
    tk_x = [t for t, _ in TIME_TICKS if t <= n_bars]
    tk_l = [lbl for t, lbl in TIME_TICKS if t <= n_bars]
    ax_m.set_xticks(tk_x)
    ax_m.set_xticklabels([""] * len(tk_x))   # sin ticks arriba
    ax_m.set_xlim(-3, n_bars + 14)
    ax_m.set_ylim(pmin, pmax)
    ax_m.yaxis.set_label_position("right")
    ax_m.yaxis.tick_right()
    ax_m.tick_params(axis="y", colors=GRAY, labelsize=11)
    ax_m.grid(True, alpha=0.25)

    # ── PANEL VOLUMEN ─────────────────────────
    vc = [GREEN if C[i] >= O[i] else RED for i in range(n_bars)]
    ax_v.bar(x_arr, V, color=vc, alpha=0.75, width=0.80, zorder=2)
    ax_v.set_xticks(tk_x)
    ax_v.set_xticklabels(tk_l, fontsize=9.5, color=GRAY, rotation=30, ha="right")
    ax_v.yaxis.set_label_position("right")
    ax_v.yaxis.tick_right()
    ax_v.tick_params(axis="y", colors=GRAY, labelsize=9)
    ax_v.set_ylabel("Vol", color=GRAY, fontsize=10)
    ax_v.set_xlim(-3, n_bars + 14)
    ax_v.grid(True, alpha=0.20)
    # Barra de volumen especial en news
    ax_v.bar(news_bar, V[min(news_bar, n_bars-1)] * 2.2, color=ic,
             alpha=0.55, width=0.90, zorder=3)

    # ── VOLUME PROFILE ────────────────────────
    mid_p, vacc = build_profile(O, H, L, C, V, n_bins=60)
    bin_h   = (mid_p[1] - mid_p[0]) * 0.90
    poc_idx = int(np.argmax(vacc))
    max_v   = vacc.max() or 1
    norm_v  = vacc / max_v

    heat = LinearSegmentedColormap.from_list(
        "vp",
        ["#1a3a5c","#1976D2","#00acc1","#00e676","#ffeb3b","#ff6f00","#b71c1c"],
        N=256
    )
    for i, (pp, vn) in enumerate(zip(mid_p, norm_v)):
        col = heat(vn * 0.95)
        ax_p.add_patch(plt.Rectangle(
            (0, pp - bin_h/2), vn, bin_h,
            color=col, alpha=0.55 + vn*0.44, zorder=3, lw=0
        ))
    # POC barra especial
    pp = mid_p[poc_idx]
    ax_p.add_patch(plt.Rectangle(
        (0, pp - bin_h/2), norm_v[poc_idx], bin_h,
        facecolor=GOLD, alpha=0.97, zorder=5, lw=0
    ))
    ax_p.add_patch(mpatches.FancyBboxPatch(
        (-0.01, pp - bin_h/2 - 0.8), 1.02, bin_h + 1.6,
        boxstyle="round,pad=0.01", fill=False,
        edgecolor=GOLD, lw=2.5, zorder=6
    ))

    # Líneas en perfil
    ax_p.axhline(poc, color=GOLD,  lw=2.8, alpha=0.95)
    ax_p.axhline(vah, color=GREEN, lw=1.8, ls="--", alpha=0.85)
    ax_p.axhline(val, color=RED,   lw=1.8, ls="--", alpha=0.85)
    ax_p.fill_betweenx([val, vah], 0, 1.06, alpha=0.07, color=GOLD)

    # Labels perfil
    ax_p.text(1.10, poc, f"POC\n{poc:.0f}", fontsize=9.5, color=GOLD,
              fontweight="bold", va="center", ha="left", clip_on=False)
    ax_p.text(1.10, vah, f"VAH\n{vah:.0f}", fontsize=9, color=GREEN,
              fontweight="bold", va="center", ha="left", clip_on=False)
    ax_p.text(1.10, val, f"VAL\n{val:.0f}", fontsize=9, color=RED,
              fontweight="bold", va="center", ha="left", clip_on=False)

    ax_p.set_xlim(-0.02, 1.05)
    ax_p.set_ylim(pmin, pmax)
    ax_p.yaxis.tick_left()
    ax_p.tick_params(axis="x", bottom=False, labelbottom=False)
    ax_p.tick_params(axis="y", colors=GRAY, labelsize=10)
    ax_p.set_facecolor(PANEL)
    ax_p.grid(axis="y", alpha=0.18)
    ax_p.set_title("VOLUME\nPROFILE", fontsize=10.5, color=CYAN, fontweight="bold", pad=6)

    # Mini colorbar
    ax_cb = fig.add_axes([0.027, 0.09, 0.008, 0.22])
    cb = ColorbarBase(ax_cb, cmap=heat, norm=Normalize(0, 1), orientation="vertical")
    cb.set_ticks([0, 0.5, 1.0])
    cb.set_ticklabels(["Low", "Mid", "High"])
    cb.ax.tick_params(labelsize=8, colors=GRAY, length=0)
    cb.outline.set_visible(False)

    # ── TÍTULO + BADGES ───────────────────────
    fig.text(0.5, 0.965,
             f"NQ Futures  15m  —  THURSDAY  {date_str}",
             ha="center", fontsize=20, fontweight="bold", color=WHITE)

    bkw = dict(ha="center", fontsize=13, fontweight="bold",
               bbox=dict(facecolor=BG, boxstyle="round,pad=0.5", lw=2.0, alpha=0.95))
    fig.text(0.30, 0.941,
             f"  {dir_sym} SPACE {'UP' if up else 'DOWN'}  {sp_pts:.0f} pts  ",
             color=ar_col, **{**bkw, "bbox": {**bkw["bbox"], "edgecolor": ar_col}})
    fig.text(0.54, 0.941,
             f"  {'✅ RETORNÓ AL POC' if ret_poc else '❌ SIN RETORNO'}  ",
             color=GREEN if ret_poc else RED,
             **{**bkw, "bbox": {**bkw["bbox"], "edgecolor": GREEN if ret_poc else RED}})
    fig.text(0.77, 0.941, f"  📰 {news['name']}  ",
             ha="center", fontsize=11, color=ORANGE,
             bbox=dict(facecolor=BG, edgecolor=ORANGE, boxstyle="round,pad=0.4",
                       lw=1.8, alpha=0.95))

    # Pie
    op_pos = rec["open_pos"].replace("_", " ")
    fig.text(0.5, 0.024,
             f"Open 9:30 → {rec['open']:.0f}   |   {op_pos}   |   "
             f"VAL {val:.0f}  ·  POC {poc:.0f}  ·  VAH {vah:.0f}   |   "
             f"PM Range {rec['pm_range']:.0f}pts  (H:{pm_hi:.0f} / L:{pm_lo:.0f})",
             ha="center", fontsize=10.5, color=GRAY,
             bbox=dict(facecolor="#07090f", edgecolor="#1e2d40",
                       boxstyle="round,pad=0.3", lw=1.0, alpha=0.88))

    # Leyenda
    leg_h = [
        mpatches.Patch(color=GOLD,   label=f"POC {poc:.0f}"),
        mpatches.Patch(color=GREEN,  label=f"VAH {vah:.0f}"),
        mpatches.Patch(color=RED,    label=f"VAL {val:.0f}"),
        mpatches.Patch(color=C_ASIA, alpha=0.7, label="ASIA"),
        mpatches.Patch(color=C_LON,  alpha=0.7, label="LONDON"),
        mpatches.Patch(color=C_NY,   alpha=0.6, label="NY"),
        mpatches.Patch(color=ORANGE, label="📰 News"),
        mpatches.Patch(color=GRAY,   label="PDH/PDL"),
    ]
    ax_m.legend(handles=leg_h, loc="upper right", fontsize=10.5,
                facecolor="#07090f", edgecolor=GRAY, ncol=4,
                framealpha=0.92, borderpad=0.9, handlelength=1.5)

    # ── GUARDAR ───────────────────────────────
    out = os.path.join(OUT_DIR, f"thursday_{date_str.replace('-','')}_sessions.png")
    fig.savefig(out, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    rt_tag = "✅ POC" if ret_poc else "❌ no ret"
    print(f"  ✅  {date_str}  {dir_sym} {'UP' if up else 'DOWN'} {sp_pts:.0f}pts  {rt_tag:<10}  {os.path.basename(out)}")

print(f"\n  📁 {len(bt['records'])} charts en: {OUT_DIR}\n")
