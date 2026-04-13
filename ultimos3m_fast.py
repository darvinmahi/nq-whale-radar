import pandas as pd, pytz, sys
from datetime import date, time as dtime

sys.stdout.reconfigure(encoding="utf-8")
ET = pytz.timezone("America/New_York")
CSV = "data/research/nq_3m.csv"  # archivo recortado = carga rapida

raw = pd.read_csv(CSV, skiprows=1, header=None,
                  names=["Datetime","Close","High","Low","Open"])
raw = raw.dropna(subset=["Datetime"])
raw["Datetime"] = pd.to_datetime(raw["Datetime"], utc=True, errors="coerce").dt.tz_convert(ET)
raw = raw.dropna(subset=["Datetime"])
raw.set_index("Datetime", inplace=True)
for c in ["Close","High","Low","Open"]:
    raw[c] = pd.to_numeric(raw[c], errors="coerce")
raw = raw.dropna(subset=["Close"]).sort_index()
raw["_d"] = raw.index.date
grouped = {d: g for d,g in raw.groupby("_d")}

def bt(d, t0, t1):
    a = dtime(*map(int, t0.split(":"))); b = dtime(*map(int, t1.split(":")))
    return d[(d.index.time >= a) & (d.index.time <= b)]

S = date(2026, 1, 5); E = date(2026, 4, 10)
DIAS = ["LUNES ", "MARTES", "MIER  ", "JUEVES", "VIERNE"]

rows = []
for day in sorted(grouped.keys()):
    wd = pd.Timestamp(day).weekday()
    if wd >= 5 or not (S <= day <= E): continue
    d = grouped[day]
    o  = bt(d, "09:30", "09:59")
    o4 = bt(d, "09:30", "10:14")
    n  = bt(d, "09:30", "16:00")
    p  = bt(d, "07:00", "09:29")
    if len(o) < 1 or len(n) < 4: continue
    om  = float(o.iloc[-1]["Close"])  - float(o.iloc[0]["Open"])
    o4m = float(o4.iloc[-1]["Close"]) - float(o4.iloc[0]["Open"]) if len(o4) >= 1 else 0
    nm  = float(n.iloc[-1]["Close"])  - float(n.iloc[0]["Open"])
    pm  = float(p.iloc[-1]["Close"])  - float(p.iloc[0]["Open"]) if len(p) >= 2 else 0
    rng = float(o["High"].max()) - float(o["Low"].min())
    od  = "BULL" if om  >  10 else ("BEAR" if om  < -10 else "FLAT")
    o4d = "BULL" if o4m >  10 else ("BEAR" if o4m < -10 else "FLAT")
    nd  = "BULL" if nm  >  30 else ("BEAR" if nm  < -30 else "FLAT")
    pmd = "BULL" if pm  >  15 else ("BEAR" if pm  < -15 else "FLAT")
    ok  = "OK" if (od == nd and od != "FLAT") else ("XX" if od != "FLAT" else "--")
    rows.append({"day":day,"wd":wd,"od":od,"o4d":o4d,"pmd":pmd,
                 "rng":round(rng),"nm":round(nm),"nd":nd,"ok":ok})

print(f"Dias procesados: {len(rows)}")

for wd in range(5):
    wr = [r for r in rows if r["wd"] == wd]
    if not wr: continue
    print()
    print(f"=== {DIAS[wd]} ({len(wr)} dias Ene-Abr 2026) ===")
    print(f"  {'#':>2}  {'Fecha':>10}  {'OR':>5}  {'OR45':>5}  {'PM':>5}  {'Rango':>6}  {'NY mov':>8}  Res")
    print("  " + "-" * 62)
    hits = 0; sigs = 0
    for i, r in enumerate(wr, 1):
        flag = "!" if r["rng"] >= 100 else " "
        print(f"  {i:>2}  {r['day'].strftime('%d/%m/%Y'):>10}  "
              f"{r['od']:>5}  {r['o4d']:>5}  {r['pmd']:>5}  "
              f"{r['rng']:>4}p{flag}  {r['nm']:>+7}p  {r['ok']}")
        if r["ok"] == "OK": hits += 1
        if r["ok"] != "--": sigs += 1
    bull  = sum(1 for r in wr if r["od"] == "BULL")
    bear  = sum(1 for r in wr if r["od"] == "BEAR")
    flat  = sum(1 for r in wr if r["od"] == "FLAT")
    ny_b  = sum(1 for r in wr if r["nd"] == "BULL")
    ny_br = sum(1 for r in wr if r["nd"] == "BEAR")
    acc   = round(hits / sigs * 100) if sigs else 0
    print(f"\n  OR: BULL={bull} BEAR={bear} FLAT={flat}  |  "
          f"NY cierre: BULL={ny_b} BEAR={ny_br}  |  OR acerto: {hits}/{sigs}={acc}%")
