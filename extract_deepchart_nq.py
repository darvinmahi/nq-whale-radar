"""
extract_deepchart_nq.py
Lee los archivos binarios de Deepchart (NQ-CME) y exporta CSV de 15 minutos.

Formato binario: 36 bytes por registro
  - int64  : timestamp en .NET ticks (100ns desde 01/01/0001 UTC)
  - double : Open
  - double : High
  - double : Low
  - double : Close
"""

import struct
import os
import pandas as pd
from datetime import datetime, timezone, timedelta
from pathlib import Path

DB_ROOT   = Path(os.environ["LOCALAPPDATA"]) / "Deepchart" / "Database" / "NQ-CME"
OUT_CSV   = Path("data/research/nq_15m_intraday.csv")
REC_SIZE  = 36
REC_FMT   = "<qdddd"
DOTNET_EPOCH = datetime(1, 1, 1, tzinfo=timezone.utc)

def dotnet_ticks_to_dt(ticks):
    return DOTNET_EPOCH + timedelta(microseconds=ticks // 10)

def read_minute_file(path):
    records = []
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // REC_SIZE
    for i in range(n):
        ts_raw, o, h, l, c = struct.unpack_from(REC_FMT, data, i * REC_SIZE)
        if ts_raw <= 0:
            continue
        try:
            dt = dotnet_ticks_to_dt(ts_raw)
            if 2020 <= dt.year <= 2030 and 5000 < o < 100000:
                records.append({"Datetime": dt, "Open": o, "High": h, "Low": l, "Close": c})
        except Exception:
            pass
    return records

def main():
    all_records = []
    contracts = sorted(DB_ROOT.iterdir())
    for contract_dir in contracts:
        minute_dir = contract_dir / "Minute"
        if not minute_dir.exists():
            continue
        files = sorted(minute_dir.glob("*.data"))
        print(f"  {contract_dir.name}: {len(files)} archivos")
        for f in files:
            recs = read_minute_file(f)
            all_records.extend(recs)

    if not all_records:
        print("❌ No se encontraron registros.")
        return

    df = pd.DataFrame(all_records)
    df["Datetime"] = pd.to_datetime(df["Datetime"], utc=True)
    df = df.sort_values("Datetime").drop_duplicates("Datetime")
    df.set_index("Datetime", inplace=True)

    print(f"\n✅ Datos 1min cargados: {len(df)} registros")
    print(f"   Periodo: {df.index[0]} → {df.index[-1]}")

    # Resamplear a 15 minutos
    df_15m = df.resample("15min").agg(
        Open=("Open", "first"),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
    ).dropna()

    print(f"   15min barras: {len(df_15m)}")
    print(f"   Periodo 15m : {df_15m.index[0]} → {df_15m.index[-1]}")

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_15m.to_csv(OUT_CSV)
    print(f"\n💾 Guardado: {OUT_CSV}")

    # Contar jueves
    days = df_15m.index.normalize().unique()
    thursdays = [d for d in days if d.weekday() == 3]
    print(f"   Jueves disponibles: {len(thursdays)}")

if __name__ == "__main__":
    main()
