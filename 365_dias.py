"""
365_dias.py — TODOS los dias del año completo (Abril 2025 - Abril 2026)
Muestra cada dia trading con lo que dijo el OR y lo que pasó realmente
"""
import pandas as pd, pytz
from datetime import date, time as dtime

ET  = pytz.timezone("America/New_York")
CSV = "data/research/nq_15m_intraday.csv"

raw = pd.read_csv(CSV, skiprows=2, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True).dt.tz_convert(ET)
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_date"] = raw.index.date
grouped = {d: grp for d, grp in raw.groupby("_date")}

def bt(d,t0,t1):
    a=dtime(*map(int,t0.split(":"))); b=dtime(*map(int,t1.split(":")))
    return d[(d.index.time>=a)&(d.index.time<=b)]

ANO2_S = date(2025, 4, 10)
ANO2_E = date(2026, 4, 10)
DIAS   = ["LUNES","MARTES","MIER  ","JUEVES","VIERNES"]

print("="*80)
print("  ESTUDIO COMPLETO: TODOS LOS DIAS — AÑO 2 (Abr 2025 → Abr 2026)")
print("  OR = Opening Range 9:30-10:00 ET")
print("="*80)
print(f"  {'#':>3}  {'Fecha':>12}  {'Dia':<8}  {'OR':>5}  {'OR pts':>6}  {'NY mov':>8}  {'NY dir':>6}  OR acertó?")
print("  "+"─"*75)

all_rows = []
for day in sorted(grouped.keys()):
    if pd.Timestamp(day).weekday() >= 5: continue
    if not (ANO2_S <= day <= ANO2_E): continue
    d = grouped[day]
    or_ = bt(d,"09:30","09:59")
    ny  = bt(d,"09:30","16:00")
    if len(or_)<1 or len(ny)<4: continue
    or_m = float(or_.iloc[-1]["Close"]) - float(or_.iloc[0]["Open"])
    or_r = float(or_["High"].max())  - float(or_["Low"].min())
    ny_m = float(ny.iloc[-1]["Close"]) - float(ny.iloc[0]["Open"])
    or_d = "BEAR" if or_m < -10 else ("BULL" if or_m > 10 else "FLAT")
    ny_d = "BEAR" if ny_m < -30 else ("BULL" if ny_m > 30 else "FLAT")
    wd   = pd.Timestamp(day).weekday()
    # OR acertó si OR_dir == NY_dir (y ninguno es FLAT)
    acerto = "✅" if (or_d == ny_d and or_d != "FLAT") else ("—" if or_d == "FLAT" else "❌")
    all_rows.append({"n":0,"day":day,"wd":wd,"or_d":or_d,"or_r":round(or_r),"ny_m":round(ny_m),"ny_d":ny_d,"ok":acerto})

for i,r in enumerate(all_rows, 1):
    r["n"] = i
    star = "🔥" if r["or_r"]>=100 else "  "
    print(f"  {i:>3}  {r['day'].strftime('%d/%m/%Y'):>12}  {DIAS[r['wd']]:<8}  {r['or_d']:>5}  {r['or_r']:>4}p{star}  {r['ny_m']:>+8}p  {r['ny_d']:>6}  {r['ok']}")

# ── RESUMEN POR DIA ───────────────────────────────────────────
print()
print("="*80)
print("  RESUMEN POR DIA — De todos los dias del año 2")
print("="*80)

for wd in range(5):
    rows = [r for r in all_rows if r["wd"]==wd]
    total = len(rows)
    if total == 0: continue

    bear_rows  = [r for r in rows if r["or_d"]=="BEAR"]
    bull_rows  = [r for r in rows if r["or_d"]=="BULL"]
    flat_rows  = [r for r in rows if r["or_d"]=="FLAT"]

    bear_hit = sum(1 for r in bear_rows if r["ny_d"]=="BEAR")
    bull_hit = sum(1 for r in bull_rows if r["ny_d"]=="BULL")
    all_hit  = sum(1 for r in rows if r["ok"]=="✅")

    print(f"\n  {DIAS[wd]} — {total} dias totales")
    print(f"  {'─'*60}")
    print(f"  OR BEAR: {len(bear_rows):>2} días  → {bear_hit} terminaron BEAR  → {bear_hit/len(bear_rows)*100:.0f}%" if bear_rows else "  OR BEAR:  0 días")
    print(f"  OR BULL: {len(bull_rows):>2} días  → {bull_hit} terminaron BULL  → {bull_hit/len(bull_rows)*100:.0f}%" if bull_rows else "  OR BULL:  0 días")
    print(f"  OR FLAT: {len(flat_rows):>2} días  → sin señal (mercado indeciso)")
    print(f"  OR acertó en total: {all_hit}/{len(bear_rows)+len(bull_rows)} días con señal  →  {all_hit/(len(bear_rows)+len(bull_rows))*100:.0f}%" if (bear_rows or bull_rows) else "")

# ── GRAN RESUMEN ──────────────────────────────────────────────
print()
print("="*80)
print("  GRAN RESUMEN — OR como predictor en TODO el año 2")
print("="*80)

bear_all  = [r for r in all_rows if r["or_d"]=="BEAR"]
bull_all  = [r for r in all_rows if r["or_d"]=="BULL"]
flat_all  = [r for r in all_rows if r["or_d"]=="FLAT"]
bear_hit  = sum(1 for r in bear_all if r["ny_d"]=="BEAR")
bull_hit  = sum(1 for r in bull_all if r["ny_d"]=="BULL")
total_sig = len(bear_all)+len(bull_all)
total_hit = bear_hit+bull_hit

print(f"""
  Total dias trading en el año: {len(all_rows)}

  Los 365 días se dividieron así:
  ─────────────────────────────────────────────────
  OR BEAR (señal bajista) : {len(bear_all):>3} días  ({len(bear_all)/len(all_rows)*100:.0f}% del tiempo)
  OR BULL (señal alcista) : {len(bull_all):>3} días  ({len(bull_all)/len(all_rows)*100:.0f}% del tiempo)
  OR FLAT (sin señal)     : {len(flat_all):>3} días  ({len(flat_all)/len(all_rows)*100:.0f}% del tiempo)

  Cuando OR dio señal ({total_sig} días):
  → Acertó: {total_hit} días = {total_hit/total_sig*100:.0f}%
  → Falló:  {total_sig-total_hit} días

  OR BEAR → NY BEAR : {bear_hit}/{len(bear_all)} = {bear_hit/len(bear_all)*100:.0f}%
  OR BULL → NY BULL : {bull_hit}/{len(bull_all)} = {bull_hit/len(bull_all)*100:.0f}%

  NOTA: Los dias FLAT ({len(flat_all)}) son cuando el OR no da
  dirección clara — correctamente no operamos esos dias.
""")
