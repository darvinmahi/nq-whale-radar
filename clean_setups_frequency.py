"""
clean_setups_frequency.py
Busca los setups mas limpios en TODOS los dias (Lun-Vie):
  - Value Profile pre-NY (sesion nocturna → 09:20 ET)
  - NY abre ABOVE VA + FEAR/XFEAR = SELL setup
  - NY abre BELOW VA + FEAR/XFEAR = BUY setup
Cuenta frecuencia: por semana, por mes, por año
"""
import csv, math, yfinance as yf, pandas as pd
from datetime import datetime, date, timedelta
from collections import defaultdict

VP_BIN = 5.0
VA_PCT = 0.70
MIN_SETUP_QUALITY = 0.67  # minimo % acierto para considerar "setup limpio"

# ─── 1. NQ 15min ──────────────────────────────────────────────
print("Cargando NQ 15min...")
nq_bars = []
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            dt_et = datetime.fromisoformat(r["Datetime"].replace("+00:00","")) - timedelta(hours=5)
            cl=float(r["Close"]); hi=float(r["High"])
            lo=float(r["Low"]);   op=float(r["Open"])
            vol=float(r.get("Volume",0) or 0)
            if cl > 0:
                nq_bars.append({"et":dt_et,"c":cl,"h":hi,"l":lo,"o":op,
                                "vol":vol if vol>0 else (hi-lo)*10})
        except: pass
nq_bars.sort(key=lambda x: x["et"])
by_date = defaultdict(list)
for b in nq_bars: by_date[b["et"].date()].append(b)
print(f"  {len(nq_bars):,} barras | {min(by_date)} → {max(by_date)}")

# ─── 2. VXN + VIX diario ──────────────────────────────────────
print("Descargando VXN + VIX...")
vxn = yf.download("^VXN", period="5y", auto_adjust=True, progress=False)
vix = yf.download("^VIX", period="5y", auto_adjust=True, progress=False)

def col(df, c):
    if isinstance(df.columns, pd.MultiIndex): return df[c].iloc[:,0]
    return df[c]

dfv = pd.DataFrame({"VXN":col(vxn,"Close"),"VIX":col(vix,"Close")}).dropna()
dfv.index = pd.to_datetime(dfv.index).tz_localize(None)
vdates = dfv.index.tolist()

def get_vxn_vix(day):
    prev = [d for d in vdates if d < pd.Timestamp(day)]
    if not prev: return None, None
    pd_ = prev[-1]
    return float(dfv.loc[pd_,"VXN"]), float(dfv.loc[pd_,"VIX"])

def vxn_zona(v):
    if v is None: return "?"
    if v >= 33: return "XFEAR"
    if v >= 25: return "FEAR"
    if v >= 18: return "NEUT"
    return "GREED"

# ─── 3. VP ────────────────────────────────────────────────────
def calc_vp(bars):
    if len(bars) < 3: return None, None, None
    lo_all = min(b["l"] for b in bars)
    hi_all = max(b["h"] for b in bars)
    if hi_all <= lo_all: return None, None, None
    n = max(1, int(math.ceil((hi_all - lo_all) / VP_BIN)))
    bins = [0.0] * n
    for b in bars:
        vol = b["vol"] if b["vol"] > 0 else 1.0
        rng = b["h"] - b["l"] if b["h"] > b["l"] else VP_BIN
        for i in range(n):
            bl = lo_all + i * VP_BIN; bh = bl + VP_BIN
            ov = max(0, min(b["h"], bh) - max(b["l"], bl))
            bins[i] += vol * (ov / rng)
    total = sum(bins)
    if total == 0: return None, None, None
    pi = bins.index(max(bins))
    poc = lo_all + pi * VP_BIN + VP_BIN / 2
    va = total * VA_PCT; acc = bins[pi]; li = hi = pi
    while acc < va:
        el = li-1 if li>0 else None; eh = hi+1 if hi<n-1 else None
        vl = bins[el] if el is not None else -1
        vh = bins[eh] if eh is not None else -1
        if vl<=0 and vh<=0: break
        if vh>=vl: hi=eh; acc+=vh
        else: li=el; acc+=vl
    return round(lo_all+hi*VP_BIN+VP_BIN,1), round(poc,1), round(lo_all+li*VP_BIN,1)

def dir_label(pct, thr=0.10):
    if pct >  thr: return "BULL"
    if pct < -thr: return "BEAR"
    return "FLAT"

def va_pos(price, vah, val):
    if vah is None: return "?"
    if price > vah: return "ABOVE"
    if price < val: return "BELOW"
    return "INSIDE"

# ─── 4. Analizar TODOS los dias (Lun-Vie) ─────────────────────
print("Analizando todos los dias...")
all_days = sorted(by_date.keys())
results  = []
DAYS = ["Lun","Mar","Mié","Jue","Vie"]

for i, day in enumerate(all_days):
    dow = day.weekday()
    if dow > 4: continue  # solo Lun-Vie

    bars = by_date[day]
    if len(bars) < 6: continue

    # NY session del dia actual
    ny_bars = [b for b in bars if
               (b["et"].hour > 9 or (b["et"].hour==9 and b["et"].minute>=30)) and
               b["et"].hour < 16]
    if len(ny_bars) < 4: continue

    ny_o = ny_bars[0]["o"];  ny_c = ny_bars[-1]["c"]
    ny_h = max(b["h"] for b in ny_bars); ny_l = min(b["l"] for b in ny_bars)
    ny_move = (ny_c - ny_o) / ny_o * 100
    ny_rng  = (ny_h - ny_l) / ny_o * 100
    ny_dir  = dir_label(ny_move)

    # Pre-NY: dia previo 17:00 ET → hoy 09:19 ET
    prev_day = all_days[i-1] if i > 0 else None
    pre_bars = []
    if prev_day:
        pre_bars += [b for b in by_date[prev_day] if b["et"].hour >= 17]
    pre_bars += [b for b in bars if
                 b["et"].hour < 9 or (b["et"].hour==9 and b["et"].minute < 20)]
    pre_bars.sort(key=lambda x: x["et"])

    if len(pre_bars) < 4: continue

    # VP de la sesion pre-NY
    vah, poc, val = calc_vp(pre_bars)
    if vah is None: continue

    va_position = va_pos(ny_o, vah, val)
    poc_dist = round(ny_o - poc, 0)

    # VXN + VIX
    vxn_val, vix_val = get_vxn_vix(day)
    if vxn_val is None: continue
    zona = vxn_zona(vxn_val)

    # Setup tipo
    # SELL: ABOVE + FEAR/XFEAR
    # BUY:  BELOW + FEAR/XFEAR
    setup_type = None
    if va_position == "ABOVE" and zona in ("FEAR","XFEAR"):
        setup_type = "SELL"
    elif va_position == "BELOW" and zona in ("FEAR","XFEAR"):
        setup_type = "BUY"
    elif va_position == "ABOVE" and zona == "NEUT":
        setup_type = "SELL_NEUT"
    elif va_position == "BELOW" and zona == "NEUT":
        setup_type = "BUY_NEUT"

    # Resultado del setup
    setup_result = None
    if setup_type == "SELL":
        setup_result = "✅WIN" if ny_dir=="BEAR" else ("❌LOSS" if ny_dir=="BULL" else "—FLAT")
    elif setup_type == "BUY":
        setup_result = "✅WIN" if ny_dir=="BULL" else ("❌LOSS" if ny_dir=="BEAR" else "—FLAT")

    # Rango pre-NY
    pre_h = max(b["h"] for b in pre_bars); pre_l = min(b["l"] for b in pre_bars)
    pre_rng = round((pre_h - pre_l) / pre_bars[0]["o"] * 100, 2)

    results.append({
        "date": day,
        "dow": dow,
        "dow_name": DAYS[dow],
        "week": day.isocalendar()[1],
        "month": day.month,
        "year": day.year,
        "vxn": round(vxn_val, 1),
        "vix": round(vix_val, 1) if vix_val else 0,
        "zona": zona,
        "vah": vah, "poc": poc, "val": val,
        "va_pos": va_position,
        "poc_dist": poc_dist,
        "pre_rng": pre_rng,
        "ny_o": round(ny_o, 0),
        "ny_move": round(ny_move, 2),
        "ny_rng": round(ny_rng, 2),
        "ny_dir": ny_dir,
        "setup_type": setup_type,
        "setup_result": setup_result,
    })

n_total = len(results)
print(f"  Dias analizados: {n_total}")

# ─── 5. FILTRAR SETUPS LIMPIOS ────────────────────────────────
clean  = [r for r in results if r["setup_type"] == "SELL"]        # SELL FEAR/XFEAR + ABOVE
clean += [r for r in results if r["setup_type"] == "BUY"]         # BUY  FEAR/XFEAR + BELOW
clean_sell = [r for r in results if r["setup_type"] == "SELL"]
clean_buy  = [r for r in results if r["setup_type"] == "BUY"]

# ─── 6. OUTPUT LISTA COMPLETA DE SETUPS ───────────────────────
SEP = "═"*110

print(f"\n{SEP}")
print(f"  SETUPS LIMPIOS: FEAR/XFEAR + VA Position (todos los dias)")
print(f"  Total SELL: {len(clean_sell)}  |  Total BUY: {len(clean_buy)}  |  Total: {len(clean)}")
print(f"{SEP}")
print(f"  {'Fecha':12} {'Dia':4} {'VXN':5} {'VIX':5} {'Zona':6}"
      f" {'VAH':>6} {'POC':>6} {'VAL':>6} {'NYO':>6} {'Dist':>6}"
      f" {'Setup':6} {'NY M%':>6} {'NYDir':>5} {'Result':>7}")
print("─"*110)

for r in sorted(clean, key=lambda x: x["date"], reverse=True):
    today = " ◄" if r["date"]==date(2026,3,30) else ""
    res = r["setup_result"] or "—"
    print(
        f"  {r['date'].strftime('%d %b %Y'):12} {r['dow_name']:4}"
        f" {r['vxn']:5.1f} {r['vix']:5.1f} {r['zona']:6}"
        f" {r['vah']:>6.0f} {r['poc']:>6.0f} {r['val']:>6.0f} {r['ny_o']:>6.0f}"
        f" {r['poc_dist']:>+6.0f}"
        f" {r['setup_type']:6} {r['ny_move']:>+5.2f}% {r['ny_dir']:>5} {res:>7}{today}"
    )

# ─── 7. ESTADÍSTICAS ──────────────────────────────────────────
print(f"\n{SEP}")
print(f"  ESTADÍSTICAS DE FRECUENCIA — {n_total} dias analizados")
print(f"{'='*80}")

# ── Winrate setups limpios ──
def winrate(lst, win_dir):
    wins = sum(1 for r in lst if r["ny_dir"]==win_dir)
    loss = sum(1 for r in lst if r["ny_dir"] in ("BULL","BEAR") and r["ny_dir"]!=win_dir)
    tot  = wins+loss
    return wins, loss, tot

w,l,t = winrate(clean_sell,"BEAR")
print(f"\n  🔴 SELL SETUP (FEAR/XFEAR + ABOVE VA): {t} casos")
print(f"     WIN (NY BEAR): {w} = {w/t*100:.0f}%   LOSS: {l} = {l/t*100:.0f}%" if t else "")
if clean_sell:
    avg_m = sum(r["ny_move"] for r in clean_sell)/len(clean_sell)
    avg_r = sum(r["ny_rng"]  for r in clean_sell)/len(clean_sell)
    print(f"     Move medio NY: {avg_m:+.2f}%  Rango: {avg_r:.2f}% ≈ {avg_r*230:.0f} pts NQ")

w,l,t = winrate(clean_buy,"BULL")
print(f"\n  🟢 BUY SETUP (FEAR/XFEAR + BELOW VA): {t} casos")
print(f"     WIN (NY BULL): {w} = {w/t*100:.0f}%   LOSS: {l} = {l/t*100:.0f}%" if t else "")
if clean_buy:
    avg_m = sum(r["ny_move"] for r in clean_buy)/len(clean_buy)
    avg_r = sum(r["ny_rng"]  for r in clean_buy)/len(clean_buy)
    print(f"     Move medio NY: {avg_m:+.2f}%  Rango: {avg_r:.2f}% ≈ {avg_r*230:.0f} pts NQ")

# ── Frecuencia ──
# Años y meses disponibles
years  = sorted(set(r["year"]  for r in results))
months_all = sorted(set((r["year"],r["month"]) for r in results))

print(f"\n  {'─'*70}")
print(f"  FRECUENCIA MENSUAL (Setups SELL + BUY FEAR/XFEAR):")
print(f"  {'Mes':12} {'Dias':>5} {'SELL':>6} {'BUY':>5} {'Total':>6} {'%Dias':>6}")
print(f"  {'─'*50}")

monthly_counts = []
for yr, mo in months_all:
    dias_mes   = [r for r in results  if r["year"]==yr and r["month"]==mo]
    sell_mes   = [r for r in clean_sell if r["year"]==yr and r["month"]==mo]
    buy_mes    = [r for r in clean_buy  if r["year"]==yr and r["month"]==mo]
    tot_setup  = len(sell_mes)+len(buy_mes)
    monthly_counts.append(tot_setup)
    pct = tot_setup/len(dias_mes)*100 if dias_mes else 0
    mo_str = date(yr,mo,1).strftime("%b %Y")
    if tot_setup > 0:
        print(f"  {mo_str:12} {len(dias_mes):>5} {len(sell_mes):>6} {len(buy_mes):>5} {tot_setup:>6} {pct:>5.0f}%")

print(f"\n  Promedio setups por mes:   {sum(monthly_counts)/len(monthly_counts):.1f}")
print(f"  Promedio dias con setup:   {sum(1 for m in monthly_counts if m>0)/len(monthly_counts)*100:.0f}% de los meses")
print(f"  Max setups en un mes:      {max(monthly_counts)}")
print(f"  Meses sin ningun setup:    {sum(1 for m in monthly_counts if m==0)}/{len(monthly_counts)}")

# ── Frecuencia por dia de la semana ──
print(f"\n  FRECUENCIA POR DIA DE LA SEMANA:")
print(f"  {'Dia':5} {'TotalDias':>10} {'Setups':>8} {'%dias':>7} {'Winrate(SELL)':>14} {'Winrate(BUY)':>13}")
print(f"  {'─'*65}")
for dow_i, dname in enumerate(DAYS):
    dias_d = [r for r in results    if r["dow"]==dow_i]
    sell_d = [r for r in clean_sell if r["dow"]==dow_i]
    buy_d  = [r for r in clean_buy  if r["dow"]==dow_i]
    tot    = len(sell_d)+len(buy_d)
    pct    = tot/len(dias_d)*100 if dias_d else 0
    ws, _, ts = winrate(sell_d,"BEAR")
    wb, _, tb = winrate(buy_d,"BULL")
    sell_wr = f"{ws}/{ts}={ws/ts*100:.0f}%" if ts else "—"
    buy_wr  = f"{wb}/{tb}={wb/tb*100:.0f}%" if tb else "—"
    print(f"  {dname:5} {len(dias_d):>10} {tot:>8} {pct:>6.0f}% {sell_wr:>14} {buy_wr:>13}")

# ── Por zona ──
print(f"\n  SELL SETUPS por zona (ABOVE VA):")
for zona in ["XFEAR","FEAR","NEUT"]:
    sub = [r for r in clean_sell if r["zona"]==zona] if zona!="NEUT" else \
          [r for r in results if r["setup_type"]=="SELL_NEUT"]
    if not sub: continue
    ws,wl,wt = winrate(sub,"BEAR")
    avg_rng = sum(r["ny_rng"] for r in sub)/len(sub)
    avg_poc = sum(abs(r["poc_dist"]) for r in sub)/len(sub)
    print(f"    {zona:6}: n={len(sub):3d}  WIN={ws/wt*100:.0f}%  Rng={avg_rng:.2f}%≈{avg_rng*230:.0f}pts  DistPOC={avg_poc:.0f}pts")

# ── Resumen ejecutivo ──
total_semanas = len(set((r["year"],r["week"]) for r in results))
total_clean   = len(clean)
print(f"\n{'='*60}")
print(f"  RESUMEN EJECUTIVO")
print(f"{'='*60}")
print(f"  Semanas analizadas:         {total_semanas}")
print(f"  Dias totales:               {n_total}")
print(f"  Setups limpios totales:     {total_clean}")
print(f"  Setup cada N semanas:       {total_semanas/total_clean:.1f} semanas" if total_clean else "")
print(f"  Setups por semana (media):  {total_clean/total_semanas:.2f}")
print(f"  Setups por mes (media):     {total_clean/(len(months_all)):.1f}")
print(f"  Winrate global SELL:        {winrate(clean_sell,'BEAR')[0]}/{winrate(clean_sell,'BEAR')[2]} = {winrate(clean_sell,'BEAR')[0]/winrate(clean_sell,'BEAR')[2]*100:.0f}%" if clean_sell else "")
print(f"  Winrate global BUY:         {winrate(clean_buy,'BULL')[0]}/{winrate(clean_buy,'BULL')[2]} = {winrate(clean_buy,'BULL')[0]/winrate(clean_buy,'BULL')[2]*100:.0f}%" if clean_buy else "")
