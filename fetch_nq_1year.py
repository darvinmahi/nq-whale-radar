"""
Descarga 1 año completo de NQ=F en 15min
Estrategia: múltiples ventanas de 59 días encadenadas
Guarda en: data/research/nq_15m_intraday.csv
"""
import yfinance as yf
import pandas as pd
import os
import time
from datetime import datetime, timedelta
import pytz

ET = pytz.timezone("America/New_York")

def fetch_1year_nq():
    symbol    = "NQ=F"
    end_dt    = datetime.now(tz=ET)
    start_dt  = end_dt - timedelta(days=365)
    chunk_days = 59   # yfinance soporta máx ~60d para 15m

    # Construir ventanas
    windows = []
    cur = start_dt
    while cur < end_dt:
        win_end = min(cur + timedelta(days=chunk_days), end_dt)
        windows.append((cur, win_end))
        cur = win_end

    print(f"📅 Descargando NQ 15min: {start_dt.strftime('%Y-%m-%d')} → {end_dt.strftime('%Y-%m-%d')}")
    print(f"🔄 Ventanas: {len(windows)} chunks de ~{chunk_days} días\n")

    frames = []
    for i, (ws, we) in enumerate(windows, 1):
        print(f"  [{i}/{len(windows)}] {ws.strftime('%Y-%m-%d')} → {we.strftime('%Y-%m-%d')} ... ", end="", flush=True)
        try:
            df = yf.download(
                symbol,
                start=ws.strftime("%Y-%m-%d"),
                end=we.strftime("%Y-%m-%d"),
                interval="15m",
                progress=False,
                auto_adjust=True,
            )
            if not df.empty:
                frames.append(df)
                print(f"✅ {len(df)} barras")
            else:
                print("⚠️ Sin datos")
        except Exception as e:
            print(f"❌ Error: {e}")
        time.sleep(1.2)   # respetar rate limit

    if not frames:
        print("\n❌ No se descargó ningún dato.")
        return

    full = pd.concat(frames)
    full = full[~full.index.duplicated(keep="last")]
    full.sort_index(inplace=True)

    out = "data/research/nq_15m_intraday.csv"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    full.to_csv(out)

    print(f"\n✅ Guardado: {out}")
    print(f"   Filas totales : {len(full)}")
    print(f"   Primer dato   : {full.index[0]}")
    print(f"   Último dato   : {full.index[-1]}\n")
    return full

if __name__ == "__main__":
    fetch_1year_nq()
