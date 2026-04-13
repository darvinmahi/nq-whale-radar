"""
cuadro_3m_pro.py — Cuadro profesional completo de los ultimos 3 meses
Incluye: OR, OR45, PM, VXN, precio NQ, movimiento NY, señal acertada
Organizado por dia de semana con resumen estadistico detallado
"""
import pandas as pd, pytz, sys
from datetime import date, time as dtime

sys.stdout.reconfigure(encoding="utf-8")
ET = pytz.timezone("America/New_York")

# CSV recortado (carga rapida)
raw = pd.read_csv("data/research/nq_3m.csv", skiprows=1, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True, errors="coerce").dt.tz_convert(ET)
raw = raw.dropna(subset=["Datetime"])
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_d"] = raw.index.date
grouped = {d: g for d, g in raw.groupby("_d")}

# VXN
try:
    import yfinance as yf
    vdf = yf.download("^VXN", start="2025-12-01", end="2026-04-11",
                      interval="1d", progress=False, auto_adjust=True)
    if hasattr(vdf.columns, "get_level_values"):
        vdf.columns = vdf.columns.get_level_values(0)
    vxn_day = {idx.date(): round(float(row["Close"]), 2) for idx, row in vdf.iterrows()}
    all_vxn_dates = sorted(vxn_day.keys())
except:
    vxn_day = {}; all_vxn_dates = []

def bt(d, t0, t1):
    a = dtime(*map(int, t0.split(":"))); b = dtime(*map(int, t1.split(":")))
    return d[(d.index.time >= a) & (d.index.time <= b)]

def dir_label(m, threshold=10):
    return "BULL" if m > threshold else ("BEAR" if m < -threshold else "FLAT")

START = date(2026, 1, 5)
END   = date(2026, 4, 9)
DIAS  = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES"]
all_dates = sorted(grouped.keys())

rows = []
prev_ny_d = None

for day in sorted(grouped.keys()):
    wd = pd.Timestamp(day).weekday()
    if wd >= 5 or not (START <= day <= END):
        # track prev
        d = grouped[day]
        ny = bt(d, "09:30", "16:00")
        if len(ny) >= 4:
            nm = float(ny.iloc[-1]["Close"]) - float(ny.iloc[0]["Open"])
            prev_ny_d = dir_label(nm, 30)
        continue

    d = grouped[day]
    or_  = bt(d, "09:30", "09:59")
    or45 = bt(d, "09:30", "10:14")
    ny   = bt(d, "09:30", "16:00")
    pm   = bt(d, "07:00", "09:29")

    if len(or_) < 1 or len(ny) < 4:
        prev_ny_d = None; continue

    ny_open  = float(ny.iloc[0]["Open"])
    ny_close = float(ny.iloc[-1]["Close"])
    ny_high  = float(ny["High"].max())
    ny_low   = float(ny["Low"].min())
    or_open  = float(or_.iloc[0]["Open"])
    or_close = float(or_.iloc[-1]["Close"])
    or_r     = float(or_["High"].max()) - float(or_["Low"].min())

    or_m   = or_close  - or_open
    or45_m = float(or45.iloc[-1]["Close"]) - float(or45.iloc[0]["Open"]) if len(or45) >= 1 else 0
    ny_m   = ny_close  - ny_open
    pm_m   = float(pm.iloc[-1]["Close"])  - float(pm.iloc[0]["Open"])  if len(pm) >= 2 else 0

    od   = dir_label(or_m, 10)
    o4d  = dir_label(or45_m, 10)
    nd   = dir_label(ny_m, 30)
    pmd  = dir_label(pm_m, 15)

    # VXN
    vxn = vxn_day.get(day)
    vxn_str = f"{vxn:.1f}" if vxn else "  —  "
    vxn_trend = "—"
    if vxn and all_vxn_dates:
        prev_vxn_dates = [v for v in all_vxn_dates if v < day]
        if prev_vxn_dates:
            prev_v = vxn_day.get(prev_vxn_dates[-1])
            if prev_v:
                delta = vxn - prev_v
                vxn_trend = "↑" if delta > 0.5 else ("↓" if delta < -0.5 else "→")

    # Resultado
    if od == "FLAT":
        resultado = "SIN SEÑAL"
        acerto    = "--"
    elif od == nd:
        resultado = f"✅ ACIERTO ({od})"
        acerto    = "OK"
    else:
        resultado = f"❌ FALLO   (OR:{od} → NY:{nd})"
        acerto    = "XX"

    # Señal doble (OR + OR45 coinciden)
    double = "✓" if od == o4d and od != "FLAT" else " "

    rows.append({
        "day": day, "wd": wd,
        "od": od, "o4d": o4d, "pmd": pmd,
        "or_r": round(or_r), "or_large": or_r >= 100,
        "ny_open": round(ny_open), "ny_close": round(ny_close),
        "ny_high": round(ny_high), "ny_low": round(ny_low),
        "ny_m": round(ny_m), "nd": nd,
        "vxn": vxn_str, "vxn_t": vxn_trend,
        "prev": prev_ny_d or "—",
        "double": double, "acerto": acerto, "resultado": resultado,
    })
    prev_ny_d = nd

print(f"Total dias: {len(rows)}\n")

SEP = "═" * 110

for wd in range(5):
    wr = [r for r in rows if r["wd"] == wd]
    if not wr: continue

    hits_bull  = sum(1 for r in wr if r["acerto"]=="OK" and r["od"]=="BULL")
    hits_bear  = sum(1 for r in wr if r["acerto"]=="OK" and r["od"]=="BEAR")
    fails_bull = sum(1 for r in wr if r["acerto"]=="XX" and r["od"]=="BULL")
    fails_bear = sum(1 for r in wr if r["acerto"]=="XX" and r["od"]=="BEAR")
    no_signal  = sum(1 for r in wr if r["acerto"]=="--")
    n_bull_sig = hits_bull + fails_bull
    n_bear_sig = hits_bear + fails_bear
    n_sig      = n_bull_sig + n_bear_sig
    n_ok       = hits_bull + hits_bear
    acc        = round(n_ok / n_sig * 100) if n_sig else 0

    ny_bull  = sum(1 for r in wr if r["nd"]=="BULL")
    ny_bear  = sum(1 for r in wr if r["nd"]=="BEAR")
    ny_flat  = sum(1 for r in wr if r["nd"]=="FLAT")

    print(SEP)
    print(f"  ▶ {DIAS[wd]}  —  {len(wr)} días hábiles  (Enero – Abril 2026)")
    print(f"  NY cierre real: 🟢 BULL={ny_bull}d  🔴 BEAR={ny_bear}d  ⚪FLAT={ny_flat}d")
    print(f"  OR BULL señales: {n_bull_sig}d → acertó {hits_bull}/{n_bull_sig} = {round(hits_bull/n_bull_sig*100) if n_bull_sig else 0}%  |  "
          f"OR BEAR señales: {n_bear_sig}d → acertó {hits_bear}/{n_bear_sig} = {round(hits_bear/n_bear_sig*100) if n_bear_sig else 0}%  |  "
          f"Sin señal (FLAT): {no_signal}d")
    print(f"  OR total acertó: {n_ok}/{n_sig} = {acc}%  |  Señal doble (OR=OR45): {sum(1 for r in wr if r['double']=='✓')}d")
    print("─" * 110)
    print(f"  {'#':>2}  {'FECHA':>10}  {'D':>1}  {'OR':>5}  {'OR45':>5}  "
          f"{'PM':>5}  {'VXN':>6} {'Vt':>2}  {'PrevDay':>7}  "
          f"{'Rango':>5}  {'NQ open':>7}  {'NQ close':>8}  {'NY mov':>8}  {'RESULTADO'}")
    print("─" * 110)

    for i, r in enumerate(wr, 1):
        flag     = "🔥" if r["or_large"] else "  "
        d_double = r["double"]
        print(f"  {i:>2}  {r['day'].strftime('%d/%m/%Y'):>10}  {d_double:>1}  "
              f"{r['od']:>5}  {r['o4d']:>5}  {r['pmd']:>5}  "
              f"{r['vxn']:>6} {r['vxn_t']:>2}  {r['prev']:>7}  "
              f"{r['or_r']:>4}p{flag}  {r['ny_open']:>7}  {r['ny_close']:>8}  "
              f"{r['ny_m']:>+8}p  {r['resultado']}")

    print()
    # Patrones clave del dia
    bear_ok = [(r['day'].strftime('%d/%m'),r['or_r']) for r in wr if r['acerto']=="OK" and r['od']=="BEAR"]
    bull_ok = [(r['day'].strftime('%d/%m'),r['or_r']) for r in wr if r['acerto']=="OK" and r['od']=="BULL"]
    bear_xx = [(r['day'].strftime('%d/%m'),r['nd'])  for r in wr if r['acerto']=="XX" and r['od']=="BEAR"]
    bull_xx = [(r['day'].strftime('%d/%m'),r['nd'])  for r in wr if r['acerto']=="XX" and r['od']=="BULL"]

    if bear_ok:  print(f"  ✅ OR BEAR acertó: {', '.join(f'{x[0]}({x[1]}p)' for x in bear_ok)}")
    if bull_ok:  print(f"  ✅ OR BULL acertó: {', '.join(f'{x[0]}({x[1]}p)' for x in bull_ok)}")
    if bear_xx:  print(f"  ❌ OR BEAR falló : {', '.join(f'{x[0]}(NY={x[1]})' for x in bear_xx)}")
    if bull_xx:  print(f"  ❌ OR BULL falló : {', '.join(f'{x[0]}(NY={x[1]})' for x in bull_xx)}")

print(SEP)
# RANKING FINAL
print()
print("  RANKING FINAL — ULTIMOS 3 MESES")
print("─" * 60)
for wd in range(5):
    wr = [r for r in rows if r["wd"] == wd]
    sig=[r for r in wr if r["acerto"]!="--"]
    ok=sum(1 for r in sig if r["acerto"]=="OK")
    acc=round(ok/len(sig)*100) if sig else 0
    bar="█"*round(acc/10) if acc else ""
    ny_b=sum(1 for r in wr if r["nd"]=="BULL")
    ny_br=sum(1 for r in wr if r["nd"]=="BEAR")
    icon="🔥" if acc>=80 else("✅" if acc>=65 else("~" if acc>=50 else"❌"))
    print(f"  {DIAS[wd]:<10} OR acerto: {ok}/{len(sig)}={acc}%{icon}  {bar}   |  "
          f"NY: BULL={ny_b} BEAR={ny_br}")
