import yfinance as yf, pandas as pd
from datetime import date

print("=== HOY LUNES 30 MARZO 2026 | Analisis Intraday ===")
print("Hora actual ET: ~10:40\n")

# NQ Futures
nq = yf.Ticker("NQ=F")
nq_hist = nq.history(period="2d", interval="15m")

if not nq_hist.empty:
    nq_hist.index = nq_hist.index.tz_convert("America/New_York")
    today_nq = nq_hist[nq_hist.index.date == date(2026, 3, 30)]
    print(f"Barras NQ hoy: {len(today_nq)}")
    print(f"{'Hora':8} {'High':>8} {'Low':>8} {'Close':>8} {'Rng':>6}  Nota")
    print("-"*60)
    prev_c = None
    for idx, row in today_nq.iterrows():
        t = idx.strftime("%H:%M")
        rng = row["High"] - row["Low"]
        nota = ""
        if t == "09:15":
            nota = "<-- zona 9:20 ET"
        elif t == "09:30":
            nota = "<-- NY OPEN"
        elif t == "08:30":
            nota = "<-- News/Macro"
        mv = ""
        if prev_c:
            delta = row["Close"] - prev_c
            mv = f"  ({delta:+.0f})"
        print(f"  {t}   {row['High']:>8.0f}  {row['Low']:>8.0f}  {row['Close']:>8.0f}  {rng:>5.0f}  {nota}{mv}")
        prev_c = row["Close"]

    # Resumen
    if not today_nq.empty:
        hi_all = today_nq["High"].max()
        lo_all = today_nq["Low"].min()
        pre = today_nq[today_nq.index.time < pd.Timestamp("09:30").time()]
        ny  = today_nq[today_nq.index.time >= pd.Timestamp("09:30").time()]

        print("\n--- RESUMEN ---")
        print(f"  Rango total sesion: {hi_all:.0f} / {lo_all:.0f} = {hi_all-lo_all:.0f} pts")

        if not pre.empty:
            pre_hi = pre["High"].max()
            pre_lo = pre["Low"].min()
            print(f"  Pre-NY range:       {pre_hi:.0f} / {pre_lo:.0f} = {pre_hi-pre_lo:.0f} pts")
            # Encontrar la expansion principal pre-NY
            pre["rng"] = pre["High"] - pre["Low"]
            max_bar = pre.loc[pre["rng"].idxmax()]
            print(f"  Barra max expansion pre-NY: {max_bar.name.strftime('%H:%M')} ET  rng={max_bar['rng']:.0f} pts")

        if not ny.empty:
            ny_hi = ny["High"].max()
            ny_lo = ny["Low"].min()
            ny_o  = ny["Open"].iloc[0]
            ny_c  = ny["Close"].iloc[-1]
            print(f"  NY session range:   {ny_hi:.0f} / {ny_lo:.0f} = {ny_hi-ny_lo:.0f} pts")
            print(f"  NY Open: {ny_o:.0f}  ->  Precio actual: {ny_c:.0f}  ({ny_c-ny_o:+.0f} pts)")
else:
    print("NQ Futures no disponible, probando QQQ...")
    qqq = yf.Ticker("QQQ")
    q = qqq.history(period="2d", interval="15m")
    if not q.empty:
        q.index = q.index.tz_convert("America/New_York")
        today_q = q[q.index.date == date(2026, 3, 30)]
        print(f"QQQ barras hoy: {len(today_q)}")
        for idx, row in today_q.iterrows():
            t = idx.strftime("%H:%M")
            print(f"  {t}  H:{row['High']:.2f}  L:{row['Low']:.2f}  C:{row['Close']:.2f}")
    else:
        print("Sin datos intraday disponibles")
