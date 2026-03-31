"""
ESTUDIO LUNES: ¿Dónde abre NY vs el Value Area?
─────────────────────────────────────────────────
ESCENARIO A: NY abre DEBAJO de VAL
ESCENARIO B: NY abre DENTRO del VA (entre VAL y VAH)
ESCENARIO C: NY abre ENCIMA de VAH
"""
import csv, math
from datetime import datetime, timedelta

# ── Carga ──────────────────────────────────────────────────
bars = []
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        raw = r.get('Price', '')
        if not raw or 'Ticker' in raw or raw == 'Datetime': continue
        try:
            dt = datetime.fromisoformat(raw.replace('+00:00', '').strip())
            cl = float(r.get('Close', 0) or 0)
            if cl > 0:
                bars.append({
                    'dt': dt, 'close': cl,
                    'high': float(r.get('High', 0) or 0),
                    'low':  float(r.get('Low',  0) or 0),
                    'open': float(r.get('Open', 0) or 0),
                    'vol':  max(float(r.get('Volume', 0) or 0), 1.0)
                })
        except: pass
bars.sort(key=lambda x: x['dt'])

# ── VP ─────────────────────────────────────────────────────
def calc_vp(sb, VA_PCT=0.70, VP_BIN=5.0):
    if len(sb) < 2: return None, None, None
    lo = min(b['low'] for b in sb); hi = max(b['high'] for b in sb)
    if hi <= lo: return None, None, None
    n = max(1, int(math.ceil((hi - lo) / VP_BIN)))
    bins = [0.0] * n
    for b in sb:
        br = b['high'] - b['low'] if b['high'] > b['low'] else VP_BIN
        for i in range(n):
            bl = lo + i * VP_BIN; bh = bl + VP_BIN
            bins[i] += b['vol'] * max(0.0, min(b['high'], bh) - max(b['low'], bl)) / br
    tv = sum(bins); pi = bins.index(max(bins)); poc = lo + pi * VP_BIN + VP_BIN / 2
    ac = bins[pi]; li = pi; hi2 = pi
    while ac < tv * VA_PCT:
        vl = bins[li-1] if li > 0 else -1
        vh = bins[hi2+1] if hi2+1 < n else -1
        if vl <= 0 and vh <= 0: break
        if vh >= vl: hi2 += 1; ac += vh
        else: li -= 1; ac += vl
    return round(lo + hi2 * VP_BIN + VP_BIN, 2), round(poc, 2), round(lo + li * VP_BIN, 2)

def filt(b, df, dt): return [x for x in b if df <= x['dt'] < dt]

TM = 10.0; BM = 10.0
rows = []

for mon in [d for d in sorted(set(b['dt'].date() for b in bars)) if d.weekday() == 0]:
    prev = mon - timedelta(days=1)
    pf = filt(bars,
              datetime(prev.year, prev.month, prev.day, 23, 0),
              datetime(mon.year,  mon.month,  mon.day,  13, 20))
    if len(pf) < 4: continue
    vah, poc, val = calc_vp(pf)
    if vah is None: continue

    ny = filt(bars,
              datetime(mon.year, mon.month, mon.day, 14, 30),
              datetime(mon.year, mon.month, mon.day, 21,  0))
    if len(ny) < 2: continue

    nyo  = ny[0]['open']
    nyc  = ny[-1]['close']
    nyh  = max(b['high'] for b in ny)
    nyl  = min(b['low']  for b in ny)
    bull = nyc > nyo
    rango = nyh - nyl

    # Escenario apertura
    if   nyo < val:            esc = 'A_BAJO_VAL'
    elif nyo > vah:            esc = 'C_ARRIBA_VAH'
    else:                      esc = 'B_DENTRO_VA'

    # Lo que hizo después
    recupero_va  = (esc == 'A_BAJO_VAL')  and nyh > val           # subió a VA
    rompio_vah   = (esc == 'A_BAJO_VAL')  and nyh > vah + BM      # llegó a VAH
    rompio_abajo = (esc == 'C_ARRIBA_VAH') and nyl < vah - BM      # pullback al VA
    llego_val    = (esc == 'C_ARRIBA_VAH') and nyl < val + TM      # llegó a VAL
    expandio_arr = (esc == 'B_DENTRO_VA') and nyc > vah + BM       # salió arriba
    expandio_abj = (esc == 'B_DENTRO_VA') and nyc < val - BM       # salió abajo

    rows.append({
        'date': mon, 'bull': bull, 'val': val, 'poc': poc, 'vah': vah,
        'nyo': nyo, 'nyc': nyc, 'nyh': nyh, 'nyl': nyl, 'rango': rango,
        'esc': esc,
        'recupero_va': recupero_va, 'rompio_vah': rompio_vah,
        'rompio_abajo': rompio_abajo, 'llego_val': llego_val,
        'expandio_arr': expandio_arr, 'expandio_abj': expandio_abj,
    })

# ── Resultados ─────────────────────────────────────────────
A = [r for r in rows if r['esc'] == 'A_BAJO_VAL']
B = [r for r in rows if r['esc'] == 'B_DENTRO_VA']
C = [r for r in rows if r['esc'] == 'C_ARRIBA_VAH']

S = '=' * 60
sep = '-' * 60

def pct(num, den): return f"{num/den*100:.0f}%" if den else "n/a"
def buf(pct_str):
    v = int(pct_str.replace('%','')) if '%' in pct_str else 0
    return '█' * (v // 10) + '░' * (10 - v // 10)

print(); print(S)
print('  ESTUDIO LUNES — APERTURA NY vs VALUE AREA | NQ')
print(S)
print(f'  Lunes totales: {len(rows)}')
print(f'  Periodo: {rows[0]["date"]}  →  {rows[-1]["date"]}')
print()

# ── ESCENARIO A ───────────────────────────────────────────
print(sep)
print(f'  📍 ESCENARIO A — NY ABRE DEBAJO DE VAL  (N={len(A)})')
print(sep)
if A:
    ra = sum(1 for r in A if r['recupero_va'])
    rh = sum(1 for r in A if r['rompio_vah'])
    ba = sum(1 for r in A if r['bull'])
    print(f'  Dias alcistas  : {ba}/{len(A)}  {pct(ba,len(A))}')
    print(f'  Recuperó VA    : {ra}/{len(A)}  {pct(ra,len(A))}  {buf(pct(ra,len(A)))}')
    print(f'  Llegó a romper VAH: {rh}/{len(A)}  {pct(rh,len(A))}  {buf(pct(rh,len(A)))}')
    print(f'  Rango NY medio : {sum(r["rango"] for r in A)/len(A):.0f} pts')
    print()
    for r in A:
        d = '🟢' if r['bull'] else '🔴'
        rv = '→recup.VA' if r['recupero_va'] else '→NO recup'
        rh2 = '→rompió VAH' if r['rompio_vah'] else ''
        print(f'  {r["date"]} {d} nyo={r["nyo"]:.0f} VAL={r["val"]:.0f} VAH={r["vah"]:.0f}  {rv} {rh2}')

# ── ESCENARIO B ───────────────────────────────────────────
print(); print(sep)
print(f'  📍 ESCENARIO B — NY ABRE DENTRO DEL VA  (N={len(B)})')
print(sep)
if B:
    ea = sum(1 for r in B if r['expandio_arr'])
    eb = sum(1 for r in B if r['expandio_abj'])
    ne = len(B) - ea - eb
    ba = sum(1 for r in B if r['bull'])
    print(f'  Dias alcistas  : {ba}/{len(B)}  {pct(ba,len(B))}')
    print(f'  Expandió ARRIBA (>VAH): {ea}/{len(B)}  {pct(ea,len(B))}  {buf(pct(ea,len(B)))}')
    print(f'  Expandió ABAJO (<VAL) : {eb}/{len(B)}  {pct(eb,len(B))}  {buf(pct(eb,len(B)))}')
    print(f'  Se quedó dentro VA     : {ne}/{len(B)}  {pct(ne,len(B))}')
    print(f'  Rango NY medio : {sum(r["rango"] for r in B)/len(B):.0f} pts')
    print()
    for r in B:
        d = '🟢' if r['bull'] else '🔴'
        dir_str = '↑arriba VAH' if r['expandio_arr'] else ('↓abajo VAL' if r['expandio_abj'] else '→dentro VA')
        print(f'  {r["date"]} {d} nyo={r["nyo"]:.0f} VAL={r["val"]:.0f} VAH={r["vah"]:.0f}  {dir_str}')

# ── ESCENARIO C ───────────────────────────────────────────
print(); print(sep)
print(f'  📍 ESCENARIO C — NY ABRE ARRIBA DEL VAH  (N={len(C)})')
print(sep)
if C:
    rp = sum(1 for r in C if r['rompio_abajo'])
    lv = sum(1 for r in C if r['llego_val'])
    ba = sum(1 for r in C if r['bull'])
    print(f'  Dias alcistas  : {ba}/{len(C)}  {pct(ba,len(C))}')
    print(f'  Pullback al VA  : {rp}/{len(C)}  {pct(rp,len(C))}  {buf(pct(rp,len(C)))}')
    print(f'  Llegó hasta VAL : {lv}/{len(C)}  {pct(lv,len(C))}  {buf(pct(lv,len(C)))}')
    print(f'  Rango NY medio  : {sum(r["rango"] for r in C)/len(C):.0f} pts')
    print()
    for r in C:
        d = '🟢' if r['bull'] else '🔴'
        pu = '→pullback VA' if r['rompio_abajo'] else '→se mantuvo'
        lv2 = '→llegó VAL' if r['llego_val'] else ''
        print(f'  {r["date"]} {d} nyo={r["nyo"]:.0f} VAL={r["val"]:.0f} VAH={r["vah"]:.0f}  {pu} {lv2}')

print(); print(S)
print('  RESUMEN EJECUTIVO')
print(S)
print(f'  A (Abre < VAL) : {len(A):>2} lunes  →  fuerza bajista al abrir')
print(f'  B (Abre en VA) : {len(B):>2} lunes  →  búsqueda de dirección')
print(f'  C (Abre > VAH) : {len(C):>2} lunes  →  fuerza alcista al abrir')
print()
