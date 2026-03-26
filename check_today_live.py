import yfinance as yf, pytz
from datetime import datetime, date

ET  = pytz.timezone("America/New_York")
now = datetime.now(ET)
print(f"Hora ET: {now.strftime('%H:%M')}")

df = yf.download("NQ=F", period="1d", interval="15m", progress=False, auto_adjust=True)
if df.empty:
    df = yf.download("MNQ=F", period="1d", interval="15m", progress=False, auto_adjust=True)
if df.empty:
    print("Sin datos live"); exit()

# Aplanar columnas MultiIndex si existen
if isinstance(df.columns, __import__('pandas').MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.index = df.index.tz_convert("America/New_York")
today    = df[df.index.date == date.today()]

def g(series): return float(series.iloc[-1]) if not series.empty else 0

pre   = today.between_time("07:00", "09:29")
ny    = today.between_time("09:30", "16:00")
spk   = today.between_time("08:30", "08:44")

anchor   = int(g(pre["Close"])) if not pre.empty else 0
sp_move  = int(g(spk["Close"]) - float(spk.iloc[0]["Open"])) if not spk.empty else 0
sp_dir   = "SUBIO" if sp_move > 0 else "BAJO" if sp_move < 0 else "FLAT"

W = 60
print("=" * W)
print("  HOY JUEVES 19-MAR-2026 | CONFIRMACION vs MODELO")
print("=" * W)
print(f"  Anchor 8:29   : {anchor:>8}")
print(f"  Spike 8:30    : {sp_move:>+8} pts  ({sp_dir})")

if not ny.empty:
    ny_open  = int(float(ny.iloc[0]["Open"]))
    ny_cur   = int(g(ny["Close"]))
    ny_high  = int(float(ny["High"].max()))
    ny_low   = int(float(ny["Low"].min()))
    ny_move  = ny_cur - ny_open
    ny_range = ny_high - ny_low
    delta_a  = ny_cur - anchor

    print(f"  NY Open 9:30  : {ny_open:>8}")
    print(f"  Precio actual : {ny_cur:>8}  ({now.strftime('%H:%M')} ET)")
    print(f"  High NY       : {ny_high:>8}")
    print(f"  Low NY        : {ny_low:>8}")
    print("-" * W)
    print(f"  Movim. NY     : {ny_move:>+8} pts  (desde apertura 9:30)")
    print(f"  Rango NY hoy  : {ny_range:>8} pts  (historico prom = 388)")
    print(f"  Delta vs 8:29 : {delta_a:>+8} pts")
    print("=" * W)
    print()
    print("  MODELO TRAMPA ESPERADO:")
    print(f"    Spike 8:30 : SUBE ~ +65 pts (premarket)")
    print(f"    NY         : CAE  ~ -200 to -400 pts")
    print(f"    Sesgo      : BAJISTA 80% de jueves")
    print()
    print("  CONFIRMACION HOY:")

    s1 = "✅ Spike UP coincide" if sp_move > 20 else ("↔️ Spike DOWN" if sp_move < -20 else "⚠️ Spike plano")
    print(f"    Spike 8:30 : {sp_move:+} pts  → {s1}")

    if ny_move < -100:
        s2 = "✅ CONFIRMA modelo BEAR / trampa"
    elif ny_move < -30:
        s2 = "⚠️ Parcialmente bajista"
    elif ny_move > 50:
        s2 = "❌ NO confirma — mercado alcista hoy"
    else:
        s2 = "⏳ Aun indeciso"
    print(f"    NY mueve   : {ny_move:+} pts  → {s2}")

    pct = int(ny_range / 388 * 100)
    print(f"    Rango acum : {ny_range} pts = {pct}% del prom")
    print("=" * W)
