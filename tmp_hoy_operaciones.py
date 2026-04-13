"""
hoy_martes_operaciones.py
Analiza qu operaciones pudimos hacer HOY MARTES 7 ABR 2026
Usa el caso mas similar de nuestra DB + simula setups
"""
import csv
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; SOFT='#94a3b8'; DIM='#475569'; ORG='#f97316'
WHITE='#f1f5f9'

def utc_off(d):
    if date(2025,3,9)<=d<date(2025,11,2) or date(2026,3,8)<=d: return 4
    return 5

by_date = defaultdict(list)
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            by_date[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close'])
            })
        except: pass

sorted_dates = sorted(by_date.keys())
last_date = sorted_dates[-1]
print(f"Datos disponibles hasta: {last_date}")

# ── Mostrar fechas en DB que son martes post-crash ────────────────────
print("\nUltimas fechas en la DB:")
for d in sorted_dates[-8:]:
    bars = sorted(
        [b for b in by_date[d]
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )
    if bars:
        chg = bars[-1]['c'] - bars[0]['o']
        day_name = d.strftime('%A')
        print(f"  {d} ({day_name}) open={bars[0]['o']:.0f} close={bars[-1]['c']:.0f} chg={chg:+.0f}pts n={len(bars)}")

# ── CASOS MAS SIMILARES A HOY (martes post-crash >-100) ───────────────
casos_analogos = [
    date(2026, 3, 3),   # Martes post -457 lunes  → +106pts
    date(2026, 2, 10),  # Martes post -108 lunes  → +10pts
    date(2026, 1, 13),  # Martes post -118 lunes  → +22pts
    date(2025, 5, 6),   # Martes post -129 lunes  → +166pts
    date(2025, 2, 25),  # Martes post -146 lunes  → +71pts
]

print("\n\nANALISIS DE OPERACIONES - CASOS ANALOGOS AL HOY:")
print("="*70)

resultados_trades = []

for target_tue in casos_analogos:
    if target_tue not in by_date:
        print(f"  {target_tue}: sin datos")
        continue

    target_mon = target_tue - timedelta(days=1)
    if target_mon not in by_date:
        continue

    # Datos del lunes (NY)
    mon_bars = sorted(
        [b for b in by_date[target_mon]
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )
    if not mon_bars: continue
    mon_lo = min(b['l'] for b in mon_bars)
    mon_hi = max(b['h'] for b in mon_bars)
    mon_open = mon_bars[0]['o']
    mon_close = mon_bars[-1]['c']
    mon_chg = round(mon_close - mon_open, 1)

    # Datos del martes intraday completo (NY)
    tue_bars = sorted(
        [b for b in by_date[target_tue]
         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
        key=lambda x: x['et']
    )
    if len(tue_bars) < 6: continue

    tue_open  = tue_bars[0]['o']
    tue_close = tue_bars[-1]['c']
    tue_chg   = round(tue_close - tue_open, 1)
    tue_hi    = max(b['h'] for b in tue_bars)
    tue_lo    = min(b['l'] for b in tue_bars)
    tue_rng   = round(tue_hi - tue_lo, 1)

    # ── SETUP 1: SWEEP LOW LUNES → LONG ─────────────────────────────
    # El martes barre el low del lunes en la apertura → entramos long
    sweep_bar = None
    for b in tue_bars[:8]:  # Primera hora (9:30-11:00)
        if b['l'] <= mon_lo + 5:  # Toca o barre el low del lunes
            sweep_bar = b
            break

    s1_result = None
    if sweep_bar:
        entry = round(sweep_bar['h'] + 0.25, 2)  # Entry en el high de la barra de sweep
        sl    = round(sweep_bar['l'] - 5, 2)       # SL bajo el mínimo del sweep
        sl_pts= round(entry - sl, 1)
        tp1   = round(entry + 50, 1)
        tp2   = round(entry + 80, 1)

        # Ver si TP1 se tocó después de la entrada
        entry_bar_idx = tue_bars.index(sweep_bar)
        tp1_hit = False; tp2_hit = False; sl_hit = False
        tp1_bar = None; tp2_bar = None; sl_bar = None

        for b in tue_bars[entry_bar_idx+1:]:
            if not sl_hit and not tp1_hit:
                if b['l'] <= sl:
                    sl_hit = True; sl_bar = b; break
            if b['h'] >= tp1 and not tp1_hit:
                tp1_hit = True; tp1_bar = b
            if tp1_hit and b['h'] >= tp2 and not tp2_hit:
                tp2_hit = True; tp2_bar = b

        pnl_3mnq = 0
        if sl_hit:
            pnl_3mnq = -(sl_pts * 3 * 2)  # 3 contratos × $2/pt
            result_str = "STOP"
        elif tp2_hit:
            pnl_3mnq = (80 * 3 * 2)
            result_str = "TP2 +80pts"
        elif tp1_hit:
            pnl_3mnq = (50 * 3 * 2)
            result_str = "TP1 +50pts"
        else:
            pnl_3mnq = 0
            result_str = "SIN TOCAR"

        s1_result = {
            'entry': entry, 'sl': sl, 'sl_pts': sl_pts,
            'tp1': tp1, 'tp2': tp2,
            'tp1_hit': tp1_hit, 'tp2_hit': tp2_hit, 'sl_hit': sl_hit,
            'pnl': pnl_3mnq, 'result': result_str,
            'sweep_time': sweep_bar['et'].strftime('%H:%M'),
            'tp1_time': tp1_bar['et'].strftime('%H:%M') if tp1_bar else '-',
            'tp2_time': tp2_bar['et'].strftime('%H:%M') if tp2_bar else '-',
        }

    # ── SETUP 2: PRIMERA VELA 9:30 GREEN → LONG ─────────────────────
    fc = next((b for b in tue_bars if b['et'].hour==9 and b['et'].minute==30), None)
    s2_result = None
    if fc and fc['c'] > fc['o'] and abs(fc['c']-fc['o']) > 10:
        entry2 = round(fc['h'] + 0.25, 2)
        sl2    = round(fc['l'] - 5, 2)
        sl2_pts= round(entry2 - sl2, 1)
        tp1_2  = round(entry2 + 50, 1)
        tp2_2  = round(entry2 + 80, 1)

        fc_idx = tue_bars.index(fc)
        tp1_hit2=False; tp2_hit2=False; sl_hit2=False
        tp1_bar2=None; sl_bar2=None; tp2_bar2=None
        for b in tue_bars[fc_idx+1:]:
            if not sl_hit2 and not tp1_hit2:
                if b['l'] <= sl2:
                    sl_hit2=True; sl_bar2=b; break
            if b['h']>=tp1_2 and not tp1_hit2:
                tp1_hit2=True; tp1_bar2=b
            if tp1_hit2 and b['h']>=tp2_2 and not tp2_hit2:
                tp2_hit2=True; tp2_bar2=b

        if sl_hit2:
            pnl2 = -(sl2_pts * 3 * 2); res2 = "STOP"
        elif tp2_hit2:
            pnl2 = (80*3*2); res2 = "TP2 +80pts"
        elif tp1_hit2:
            pnl2 = (50*3*2); res2 = "TP1 +50pts"
        else:
            pnl2 = 0; res2 = "SIN TOCAR"

        s2_result = {
            'entry': entry2, 'sl': sl2, 'sl_pts': sl2_pts,
            'tp1': tp1_2, 'tp2': tp2_2,
            'pnl': pnl2, 'result': res2,
            'fc_bull': True, 'fc_body': round(abs(fc['c']-fc['o']),1),
            'tp1_time': tp1_bar2['et'].strftime('%H:%M') if tp1_bar2 else '-',
        }

    print(f"\n{'─'*70}")
    print(f"MARTES {target_tue}  (Lunes: {mon_chg:+.0f}pts  |  Martes: {tue_chg:+.0f}pts  |  Rng: {tue_rng:.0f}pts)")
    print(f"  Mon LOW={mon_lo:.0f}  Mon HIGH={mon_hi:.0f}  Tue OPEN={tue_open:.0f}")
    print()
    if s1_result:
        p = s1_result['pnl']
        pc = '+' if p>0 else ''
        print(f"  SETUP 1 — Sweep LOW Lunes [{s1_result['sweep_time']}]:")
        print(f"    Entry={s1_result['entry']:.0f}  SL={s1_result['sl']:.0f} ({s1_result['sl_pts']:.0f}pts)")
        print(f"    TP1={s1_result['tp1']:.0f} [{s1_result['tp1_time']}]  TP2={s1_result['tp2']:.0f} [{s1_result['tp2_time']}]")
        print(f"    ➤ RESULTADO: {s1_result['result']}  |  P&L 3MNQ: {pc}${p:.0f}")
    else:
        print(f"  SETUP 1 — Sweep LOW Lunes: NO SE DIO (martes no barrió el low)")

    if s2_result:
        p2 = s2_result['pnl']
        pc2 = '+' if p2>0 else ''
        print(f"  SETUP 2 — 1a Vela 9:30 GREEN ({s2_result['fc_body']:.0f}pts body):")
        print(f"    Entry={s2_result['entry']:.0f}  SL={s2_result['sl']:.0f} ({s2_result['sl_pts']:.0f}pts)  TP1={s2_result['tp1']:.0f} [{s2_result['tp1_time']}]")
        print(f"    ➤ RESULTADO: {s2_result['result']}  |  P&L 3MNQ: {pc2}${p2:.0f}")
    else:
        print(f"  SETUP 2 — 1a Vela 9:30: NO verde o cuerpo < 10pts")

    total_pnl = (s1_result['pnl'] if s1_result else 0) + (s2_result['pnl'] if s2_result else 0)
    print(f"\n  TOTAL P&L DIA: {'+' if total_pnl>=0 else ''}${total_pnl:.0f} (3 MNQ)")

    resultados_trades.append({
        'date': target_tue, 'mon_chg': mon_chg, 'tue_chg': tue_chg,
        's1': s1_result, 's2': s2_result, 'total': total_pnl,
        'bars': tue_bars, 'mon_lo': mon_lo, 'mon_hi': mon_hi
    })

# ── Resumen ─────────────────────────────────────────────────────────
print(f"\n{'='*70}")
print("RESUMEN SETUPS - CASOS ANALOGOS AL HOY:")
total_dias = len(resultados_trades)
total_pnl_all = sum(r['total'] for r in resultados_trades)
s1_hits = sum(1 for r in resultados_trades if r['s1'] and r['s1']['pnl']>0)
s2_hits = sum(1 for r in resultados_trades if r['s2'] and r['s2']['pnl']>0)
print(f"  Dias analizados: {total_dias}")
print(f"  Setup1 (Sweep Low Lunes) ganador: {s1_hits}/{total_dias}")
print(f"  Setup2 (1a Vela Green)   ganador: {s2_hits}/{total_dias}")
print(f"  P&L Total acumulado: {'+' if total_pnl_all>=0 else ''}${total_pnl_all:.0f}")

# ── FIGURA ────────────────────────────────────────────────────────────
if not resultados_trades:
    print("Sin datos para graficar")
    exit()

n_cases = len(resultados_trades)
fig = plt.figure(figsize=(26, 14), facecolor=BG)
fig.suptitle(
    "OPERACIONES QUE PUDIMOS HACER — Martes Post-Crash Lunes | Casos Análogos al 7 Abr 2026",
    color=GOLD, fontsize=13, fontweight='bold', y=0.99
)
gs = gridspec.GridSpec(2, n_cases, figure=fig, hspace=0.35, wspace=0.25,
                       left=0.04, right=0.98, top=0.94, bottom=0.08)

for col, r in enumerate(resultados_trades):
    bars = r['bars']
    mon_lo = r['mon_lo']
    mon_hi = r['mon_hi']
    s1 = r['s1']
    s2 = r['s2']

    # Panel precio
    ax = fig.add_subplot(gs[0, col])
    ax.set_facecolor(PANEL2)

    times = [b['et'].strftime('%H:%M') for b in bars]
    opens  = [b['o'] for b in bars]
    closes = [b['c'] for b in bars]
    highs  = [b['h'] for b in bars]
    lows   = [b['l'] for b in bars]
    xs = list(range(len(bars)))

    # Velas
    for i, b in enumerate(bars):
        clr = GRN if b['c'] >= b['o'] else RED
        ax.plot([i, i], [b['l'], b['h']], color=clr, lw=0.8, alpha=0.7)
        body = max(abs(b['c']-b['o']), 0.5)
        bot  = min(b['o'], b['c'])
        ax.add_patch(plt.Rectangle((i-0.4, bot), 0.8, body, color=clr, alpha=0.8))

    # Niveles clave
    ax.axhline(mon_lo, color=RED,  lw=1.5, ls='--', alpha=0.9, label=f'Low Lunes {mon_lo:.0f}')
    ax.axhline(mon_hi, color=GOLD, lw=1.0, ls='--', alpha=0.6, label=f'High Lunes {mon_hi:.0f}')

    # Setup 1
    if s1:
        entry_idx = next((i for i,b in enumerate(bars)
                          if b['et'].strftime('%H:%M')==s1['sweep_time']), None)
        if entry_idx is not None:
            ax.axhline(s1['entry'], color=BLU, lw=1.5, ls='-', alpha=0.9)
            ax.axhline(s1['sl'],    color=RED,  lw=1.0, ls=':',  alpha=0.8)
            ax.axhline(s1['tp1'],   color=GRN,  lw=1.0, ls=':',  alpha=0.8)
            ax.axhline(s1['tp2'],   color=GRN,  lw=1.5, ls='-',  alpha=0.7)
            ax.annotate('ENTRY', (entry_idx, s1['entry']),
                        fontsize=7, color=BLU, fontweight='bold',
                        xytext=(entry_idx+0.5, s1['entry']+3))
            pnl_c = GRN if s1['pnl']>0 else RED
            ax.text(len(bars)*0.7, s1['entry']+8,
                    f"S1: {'+' if s1['pnl']>=0 else ''}${s1['pnl']:.0f}",
                    fontsize=8, color=pnl_c, fontweight='bold')

    # Setup 2
    if s2:
        fc_idx = next((i for i,b in enumerate(bars)
                       if b['et'].hour==9 and b['et'].minute==30), 0)
        ax.axhline(s2['entry'], color=PRP, lw=1.2, ls='-', alpha=0.8)
        ax.annotate('S2', (fc_idx, s2['entry']),
                    fontsize=7, color=PRP, fontweight='bold',
                    xytext=(fc_idx+0.8, s2['entry']+5))
        ax.text(len(bars)*0.7, s2['entry']+3,
                f"S2: {'+' if s2['pnl']>=0 else ''}${s2['pnl']:.0f}",
                fontsize=8, color=GRN if s2['pnl']>0 else RED, fontweight='bold')

    # Eje x
    step = max(1, len(bars)//6)
    ax.set_xticks(xs[::step])
    ax.set_xticklabels(times[::step], fontsize=7, color=SOFT, rotation=30)
    ax.tick_params(colors=SOFT, labelsize=7)
    [ax.spines[s_].set_visible(False) for s_ in ['top','right']]
    ax.spines['left'].set_color(PANEL); ax.spines['bottom'].set_color(PANEL)

    tc = r['tue_chg']
    tc_c = GRN if tc > 0 else RED
    title = f"{r['date']}\nLun:{r['mon_chg']:+.0f} | Mar:{tc:+.0f}"
    ax.set_title(title, fontsize=9, color=tc_c, fontweight='bold', pad=3)

    # Panel de P&L
    ax_pnl = fig.add_subplot(gs[1, col])
    ax_pnl.set_facecolor(PANEL2)
    ax_pnl.set_xlim(0,4); ax_pnl.set_ylim(-2,4); ax_pnl.axis('off')

    pnl1 = s1['pnl'] if s1 else 0
    pnl2 = s2['pnl'] if s2 else 0
    total = r['total']

    def card(ax_, x, y, label, val, res):
        c = GRN if val > 0 else (RED if val < 0 else SOFT)
        ax_.add_patch(patches.FancyBboxPatch(
            (x-0.5, y-0.4), 2.0, 0.78,
            boxstyle='round,pad=0.05', facecolor=PANEL, edgecolor=c, linewidth=1.3
        ))
        ax_.text(x+0.5, y+0.22, label, ha='center', fontsize=8.5, color=SOFT, fontweight='bold')
        ax_.text(x+0.5, y-0.1,  f'{"+$" if val>0 else ""}{val:.0f}' if val != 0 else 'N/A',
                 ha='center', fontsize=11, color=c, fontweight='bold')
        ax_.text(x+0.5, y-0.32, res, ha='center', fontsize=7.5, color=c)

    card(ax_pnl, 0.5, 3.3, 'SETUP 1\nSweep Low', pnl1, s1['result'] if s1 else 'No se dio')
    card(ax_pnl, 2.5, 3.3, 'SETUP 2\n1a Vela', pnl2, s2['result'] if s2 else 'No verde')

    tc_ = GRN if total >= 0 else RED
    ax_pnl.add_patch(patches.FancyBboxPatch(
        (0.2, 1.4), 3.6, 0.9,
        boxstyle='round,pad=0.08', facecolor='#0d1a0d' if total >= 0 else '#1a0d0d',
        edgecolor=tc_, linewidth=2
    ))
    ax_pnl.text(2.0, 2.1, 'TOTAL DIA', ha='center', fontsize=9, color=SOFT, fontweight='bold')
    ax_pnl.text(2.0, 1.7, f'{"+$" if total>=0 else "-$"}{abs(total):.0f}',
                ha='center', fontsize=15, color=tc_, fontweight='bold')
    ax_pnl.text(2.0, 0.8, f'3 MNQ  |  SL 25pts  |  TP1 +50pts  |  TP2 +80pts',
                ha='center', fontsize=7.5, color=DIM)

out = 'hoy_martes_operaciones.png'
plt.savefig(out, dpi=120, bbox_inches='tight', facecolor=BG)
plt.close()
print(f"\nGrafica guardada: {out}")
