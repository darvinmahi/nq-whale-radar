"""
generar_lunes_png_full.py
Asia→London→NY sin overlay de fondo — colores de velas exactos del HTML
UP_C = #22c55e   DN_C = #ef4444
"""
import json, os
from datetime import datetime, timedelta, timezone
import numpy as np
import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D

BG      = '#0d1117'
BG_FIG  = '#07090e'
GRID_C  = '#1e2532'
TEXT_C  = '#e2e8f0'
MUTED_C = '#64748b'
UP_C    = '#22c55e'
DN_C    = '#ef4444'
VAH_C   = '#f97316'
POC_C   = '#facc15'
VAL_C   = '#38bdf8'
EMA_C   = '#a78bfa'
VWAP_C  = '#f59e0b'
NYOP_C  = '#ffffff'

with open('data/research/lunes_levels.json', encoding='utf-8') as f:
    levels = json.load(f)
with open('data/research/lunes_5m_data.json', encoding='utf-8') as f:
    ny_sessions = {s['date']: s for s in json.load(f)}

os.makedirs('data/images/lunes', exist_ok=True)

LUNES = ['2026-01-26','2026-02-02','2026-02-09',
         '2026-02-23','2026-03-02','2026-03-09']

def fetch_full_day(date_str):
    monday = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
    ticker = yf.Ticker('NQ=F')
    df = ticker.history(
        start=(monday - timedelta(days=1)).strftime('%Y-%m-%d'),
        end=(monday + timedelta(days=1)).strftime('%Y-%m-%d'),
        interval='5m', auto_adjust=False, prepost=True,
    )
    if df.empty:
        return []
    range_start = monday.replace(hour=0) - timedelta(hours=2)
    range_end   = monday.replace(hour=21, minute=0)
    rows = []
    for ts, row in df.iterrows():
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        else:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=timezone.utc)
        if range_start <= ts <= range_end:
            rows.append({
                'time': ts,
                'o': round(float(row['Open']),  2),
                'h': round(float(row['High']),  2),
                'l': round(float(row['Low']),   2),
                'c': round(float(row['Close']), 2),
                'v': int(row['Volume']) if 'Volume' in row else 0,
            })
    rows.sort(key=lambda x: x['time'])
    return rows

def compute_vwap(rows):
    cp, cv = 0.0, 0.0
    out = []
    for r in rows:
        tp = (r['h'] + r['l'] + r['c']) / 3
        v  = r['v'] or 1
        cp += tp * v; cv += v
        out.append(cp / cv)
    return out

def utc_to_et(ts, is_dst):
    return ts - timedelta(hours=(4 if is_dst else 5))

def draw_full(date_str, rows, lv, s_ny, output_path):
    n = len(rows)
    if n == 0:
        print(f'  ⚠ Sin velas {date_str}'); return

    is_dst = date_str >= '2026-03-08'
    isBull = s_ny.get('direction','') == 'BULLISH' if s_ny else True

    opens  = [r['o'] for r in rows]
    highs  = [r['h'] for r in rows]
    lows   = [r['l'] for r in rows]
    closes = [r['c'] for r in rows]
    vols   = [r['v'] for r in rows]
    times  = [r['time'] for r in rows]
    vwap   = compute_vwap(rows)

    fig = plt.figure(figsize=(16, 6), facecolor=BG_FIG)
    ax  = fig.add_axes([0.04, 0.14, 0.91, 0.73])
    axv = fig.add_axes([0.04, 0.03, 0.91, 0.10])

    for a in (ax, axv):
        a.set_facecolor(BG)
        a.tick_params(colors=MUTED_C, labelsize=7)
        for sp in a.spines.values(): sp.set_color(GRID_C)
        a.grid(color=GRID_C, linewidth=0.3, alpha=0.55)

    # ── Velas: fondo limpio, sin overlay ──────────────────────────
    W = 0.55
    for i, (o, h, l, c) in enumerate(zip(opens, highs, lows, closes)):
        col = UP_C if c >= o else DN_C
        ax.plot([i, i], [l, h], color=col, lw=0.8, solid_capstyle='round', zorder=2)
        yb, yt = sorted([o, c])
        ax.add_patch(mpatches.Rectangle(
            (i - W/2, yb), W, max(yt - yb, 0.2),
            facecolor=col, edgecolor='none', lw=0, zorder=2))

    # ── Volumen ───────────────────────────────────────────────────
    for i, (o, c, v) in enumerate(zip(opens, closes, vols)):
        axv.bar(i, v, width=0.65,
                color=(UP_C if c >= o else DN_C), alpha=0.30, lw=0)

    # ── Divisores sesión: sólo líneas verticales delgadas ─────────
    london_i = next((i for i, ts in enumerate(times)
                     if ts.hour == 7 and ts.minute == 0), None)
    ny_i     = next((i for i, ts in enumerate(times)
                     if ts.hour == 14 and ts.minute == 30), None)

    ymax = max(highs); ymin = min(lows)
    pad  = (ymax - ymin) * 0.035

    for idx, lbl, col in [(0,'ASIA','#3b82f6'),
                           (london_i,'LONDON','#8b5cf6'),
                           (ny_i,'NY','#22c55e')]:
        if idx is None: continue
        for a in (ax, axv):
            a.axvline(idx - 0.5, color=col, lw=0.9,
                      ls='--', alpha=0.45, zorder=1)
        ax.text(idx + 0.8, ymax + pad * 0.05, lbl, color=col,
                fontsize=7.5, fontweight='bold', fontfamily='monospace',
                va='bottom', ha='left', alpha=0.85)

    # ── VWAP ─────────────────────────────────────────────────────
    ax.plot(vwap, color=VWAP_C, lw=1.1, ls='--', alpha=0.85, zorder=3)

    # ── Niveles ───────────────────────────────────────────────────
    def hline(val, col, lw, ls, alpha=0.9):
        if val is None: return
        ax.axhline(val, color=col, lw=lw, ls=ls, alpha=alpha, zorder=3)
        ax.text(n-0.2, val, f'{val:.2f}', color=col, fontsize=6.5,
                va='center', ha='left', fontfamily='monospace', zorder=4,
                bbox=dict(fc=BG, ec='none', pad=1))

    ny_open_val = lv.get('ny_open') or (s_ny.get('ny_open') if s_ny else None)
    if ny_i: ax.axvline(ny_i - 0.5, color=NYOP_C, lw=0.6, ls=':', alpha=0.3)
    if ny_open_val: hline(ny_open_val, NYOP_C, 0.6, ':', 0.3)
    hline(lv.get('vah'),    VAH_C, 1.2, '-')
    hline(lv.get('poc'),    POC_C, 1.4, '--')
    hline(lv.get('val'),    VAL_C, 1.2, '-')
    hline(lv.get('ema200'), EMA_C, 1.0, '-')

    # ── X ticks ───────────────────────────────────────────────────
    tick_idx, tick_lbl, prev_h = [], [], None
    for i, ts in enumerate(times):
        et = utc_to_et(ts, is_dst)
        if et.hour != prev_h and et.minute == 0:
            prev_h = et.hour
            tick_idx.append(i)
            h12 = et.hour % 12 or 12
            tick_lbl.append(f"{h12}{'AM' if et.hour<12 else 'PM'}")

    for a in (ax, axv): a.set_xlim(-1, n)
    ax.set_xticks([])
    axv.set_xticks(tick_idx)
    axv.set_xticklabels(tick_lbl, color=MUTED_C, fontsize=7, fontfamily='monospace')
    ax.set_ylim(ymin - pad, ymax + pad * 1.2)
    ax.yaxis.set_tick_params(labelsize=7)
    axv.yaxis.set_tick_params(labelsize=0)

    # ── Header ───────────────────────────────────────────────────
    dir_sym = '▲ BULL' if isBull else '▼ BEAR'
    dir_col = UP_C if isBull else DN_C
    ny_range = s_ny.get('ny_range', 0) if s_ny else 0
    cot      = s_ny.get('cot', '—') if s_ny else '—'

    fig.text(0.04, 0.99, date_str,  color=TEXT_C,  fontsize=13, fontweight='bold', fontfamily='monospace', va='top')
    fig.text(0.20, 0.99, dir_sym,   color=dir_col, fontsize=10, fontweight='bold', va='top')
    fig.text(0.29, 0.99, f'Rango NY: {ny_range:.0f} pts', color=TEXT_C, fontsize=8.5, va='top')
    fig.text(0.49, 0.99, f'COT: {cot}', color=VWAP_C, fontsize=8.5, fontfamily='monospace', va='top')
    fig.text(0.63, 0.99, f'5 min · Asia→London→NY · {n} velas', color=MUTED_C, fontsize=8, va='top')

    # ── Leyenda ───────────────────────────────────────────────────
    ax.legend(handles=[
        Line2D([],[],color=UP_C,  lw=0,marker='s',ms=8,label='BULL'),
        Line2D([],[],color=DN_C,  lw=0,marker='s',ms=8,label='BEAR'),
        Line2D([],[],color=VAH_C, lw=1.4,                 label='VAH'),
        Line2D([],[],color=POC_C, lw=1.4,ls='--',         label='POC'),
        Line2D([],[],color=VAL_C, lw=1.4,                 label='VAL'),
        Line2D([],[],color=EMA_C, lw=1.2,                 label='EMA200'),
        Line2D([],[],color=VWAP_C,lw=1.2,ls='--',         label='VWAP'),
    ], loc='upper left', facecolor='#111827', edgecolor=GRID_C,
       fontsize=7, framealpha=0.85, labelcolor=TEXT_C, ncol=7)

    plt.savefig(output_path, dpi=130, bbox_inches='tight',
                facecolor=BG_FIG, edgecolor='none')
    plt.close(fig)
    print(f'  ✓ {output_path}  ({n} velas)')

# ── TEST primera sesión ──────────────────────────────────────────
date = LUNES[0]
print(f'Descargando {date}...')
rows = fetch_full_day(date)
print(f'  {len(rows)} velas')
lv   = levels.get(date, {})
s_ny = ny_sessions.get(date, {})
out  = f"data/images/lunes/lunes_{date.replace('-','')}_full.png"
draw_full(date, rows, lv, s_ny, out)
print('DONE:', out)
