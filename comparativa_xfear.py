"""
Compara el lunes de HOY (30 Mar 2026) vs todos los lunes anteriores
con VXN >= 33 (zona XFEAR) — 5 años de historia.
"""
import yfinance as yf, pandas as pd
from datetime import date

PERIOD = "5y"
print("Descargando QQQ + VXN + VIX (5 anos)...")
qqq = yf.download("QQQ",  period=PERIOD, auto_adjust=True, progress=False)
vxn = yf.download("^VXN", period=PERIOD, auto_adjust=True, progress=False)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

qqq_o = col(qqq,"Open"); qqq_h = col(qqq,"High")
qqq_l = col(qqq,"Low");  qqq_c = col(qqq,"Close")
vxn_c = col(vxn,"Close")

df = pd.DataFrame({"O":qqq_o,"H":qqq_h,"L":qqq_l,"C":qqq_c,"VXN":vxn_c}).dropna()
df.index = pd.to_datetime(df.index).tz_localize(None)

dates = df.index.tolist()
xfear_mondays = []

for i, dt in enumerate(dates):
    if dt.weekday() != 0: continue
    prev_dates = [d for d in dates[:i]]
    if not prev_dates: continue
    prev = prev_dates[-1]
    vxn_val = float(df.loc[prev, "VXN"])
    if vxn_val < 33: continue

    nq_o  = float(df.loc[dt, "O"])
    nq_h  = float(df.loc[dt, "H"])
    nq_l  = float(df.loc[dt, "L"])
    nq_c  = float(df.loc[dt, "C"])
    nq_pc = float(df.loc[prev, "C"])

    gap_pct   = (nq_o - nq_pc) / nq_pc * 100
    move_pct  = (nq_c - nq_o)  / nq_o  * 100
    range_pct = (nq_h - nq_l)  / nq_o  * 100
    range_pts = nq_h - nq_l  # en puntos QQQ, multiplicar x10 aprox NQ

    # Donde cerro vs el range: 0=en low, 1=en high
    pos_in_range = (nq_c - nq_l) / (nq_h - nq_l) if nq_h != nq_l else 0.5

    dir_lun = "BULL" if move_pct > 0.15 else ("BEAR" if move_pct < -0.15 else "FLAT")

    xfear_mondays.append({
        "date": dt,
        "vxn": round(vxn_val, 1),
        "gap_pct": round(gap_pct, 2),
        "move_pct": round(move_pct, 2),
        "range_pct": round(range_pct, 2),
        "range_pts_qqq": round(range_pts, 2),
        "pos_in_range": round(pos_in_range, 2),
        "dir": dir_lun,
        "open": round(nq_o, 2),
        "high": round(nq_h, 2),
        "low": round(nq_l, 2),
        "close": round(nq_c, 2),
    })

xf = pd.DataFrame(xfear_mondays)
n = len(xf)
print(f"\n{'='*65}")
print(f"  LUNES XFEAR (VXN>=33) — {n} casos en 5 anos")
print(f"{'='*65}")

# --- Stats globales ---
n_bull = len(xf[xf.dir=="BULL"])
n_bear = len(xf[xf.dir=="BEAR"])
n_flat = len(xf[xf.dir=="FLAT"])
avg_rng_pct = xf.range_pct.mean()
avg_move    = xf.move_pct.mean()
avg_gap     = xf.gap_pct.mean()

print(f"\n  RESULTADOS:")
print(f"  BULL: {n_bull} ({n_bull/n*100:.0f}%)   BEAR: {n_bear} ({n_bear/n*100:.0f}%)   FLAT: {n_flat}")
print(f"\n  RANGOS:")
print(f"  Rango medio:    {avg_rng_pct:.2f}% = ~{avg_rng_pct*230:.0f} pts NQ")
print(f"  Rango mediana:  {xf.range_pct.median():.2f}% = ~{xf.range_pct.median()*230:.0f} pts NQ")
print(f"  Rango maximo:   {xf.range_pct.max():.2f}% = ~{xf.range_pct.max()*230:.0f} pts NQ")
print(f"  Rango minimo:   {xf.range_pct.min():.2f}% = ~{xf.range_pct.min()*230:.0f} pts NQ")
print(f"\n  MOVIMIENTO (Open→Close):")
print(f"  Media:          {avg_move:+.2f}%")
print(f"  Desv. std:      {xf.move_pct.std():.2f}%")
print(f"  Cierra arriba del range (>0.6): {len(xf[xf.pos_in_range>0.6])} ({len(xf[xf.pos_in_range>0.6])/n*100:.0f}%)")
print(f"  Cierra abajo del range (<0.4):  {len(xf[xf.pos_in_range<0.4])} ({len(xf[xf.pos_in_range<0.4])/n*100:.0f}%)")

# --- HOY: 30 Mar 2026 ---
# Datos reales de hoy del script hoy_analisis.py
HOY_RANGE_PTS = 312     # total con pre-market (23574-23262)
HOY_NY_RANGE  = 276     # NY solo (23538-23262)
HOY_OPEN      = 23509
HOY_CLOSE_APROX = 23288 # aprox 12:30 ET
HOY_HIGH      = 23574
HOY_LOW       = 23262
HOY_MOVE_PCT  = (HOY_CLOSE_APROX - HOY_OPEN) / HOY_OPEN * 100
HOY_RNG_PCT   = (HOY_HIGH - HOY_LOW) / HOY_OPEN * 100
HOY_POS       = (HOY_CLOSE_APROX - HOY_LOW) / (HOY_HIGH - HOY_LOW)
HOY_VXN       = 33.5

print(f"\n{'='*65}")
print(f"  HOY 30 MAR 2026 (VXN={HOY_VXN})")
print(f"{'='*65}")
print(f"  Rango total:    {HOY_RANGE_PTS} pts  ({HOY_RNG_PCT:.2f}%)")
print(f"  NY range solo:  {HOY_NY_RANGE} pts")
print(f"  Movimiento:     {HOY_MOVE_PCT:+.2f}%  (BEAR)")
print(f"  Pos en range:   {HOY_POS:.2f}  (0=low, 1=high)")
print(f"  High/Low:       {HOY_HIGH} / {HOY_LOW}")

# --- Percentiles de hoy vs historico ---
pct_rng  = (xf.range_pct < HOY_RNG_PCT).mean() * 100
pct_move = (xf.move_pct  < HOY_MOVE_PCT).mean() * 100

print(f"\n  VS HISTORICO XFEAR:")
print(f"  Rango hoy percentil:    {pct_rng:.0f}%  ({pct_rng:.0f} de cada 100 dias XFEAR tienen menos rango)")
print(f"  Movimiento hoy percentil: {pct_move:.0f}%  (fue mas bajista que el {100-pct_move:.0f}% de dias XFEAR)")

# --- Tabla de todos los lunes XFEAR ---
print(f"\n{'='*65}")
print(f"  TODOS LOS LUNES XFEAR (mas recientes primero):")
print(f"{'='*65}")
print(f"  {'Fecha':12} {'VXN':5} {'Gap%':7} {'Move%':7} {'Rng%':7} {'Dir':5} {'Pos':5}")
print(f"  {'-'*55}")
for _, r in xf.sort_values("date", ascending=False).head(20).iterrows():
    marker = " <<< HOY" if r["date"].date() == date(2026,3,30) else ""
    print(f"  {r['date'].strftime('%d %b %Y'):12} {r['vxn']:5.1f} {r['gap_pct']:+6.2f}% {r['move_pct']:+6.2f}% {r['range_pct']:6.2f}% {r['dir']:5} {r['pos_in_range']:.2f}{marker}")

# --- Sub-analisis: lunes XFEAR con VIE bearish (como hoy el vie fue bajista) ---
print(f"\n{'='*65}")
print(f"  DISTRIBUCION DE RESULTADOS XFEAR:")
print(f"{'='*65}")
bull_rng = xf[xf.dir=="BULL"].range_pct.mean()
bear_rng = xf[xf.dir=="BEAR"].range_pct.mean()
print(f"  Rango medio en dias BULL: {bull_rng:.2f}% = ~{bull_rng*230:.0f} pts NQ")
print(f"  Rango medio en dias BEAR: {bear_rng:.2f}% = ~{bear_rng*230:.0f} pts NQ")
print(f"\n  VXN breakdown dentro de XFEAR:")
for lo, hi in [(33,36),(36,40),(40,50),(50,99)]:
    sub = xf[(xf.vxn>=lo)&(xf.vxn<hi)]
    if sub.empty: continue
    sb = len(sub[sub.dir=="BULL"])
    se = len(sub[sub.dir=="BEAR"])
    print(f"  VXN {lo}-{hi}: n={len(sub):2d}  BULL={sb} ({sb/len(sub)*100:.0f}%)  BEAR={se} ({se/len(sub)*100:.0f}%)  Rng={sub.range_pct.mean():.2f}%")
