"""
COT Index — NQ NASDAQ-100 Futures (CFTC Traders in Financial Futures)
═══════════════════════════════════════════════════════════════════════
Fuente: CFTC TFF (Traders in Financial Futures) — Reporte semanal oficial
Código NQ: 209742 (E-mini NASDAQ-100)

Categorías clave TFF:
  • Asset Manager      → "smart money" institucional (pensiones, fondos)
  • Leveraged Funds    → Hedge funds / grandes especuladores
  • Dealer/Intermediary→ Market makers (contra-indicador)

COT Index = (Net_actual - Net_min_3yr) / (Net_max_3yr - Net_min_3yr) * 100
  → 100 = máximo posicionamiento alcista en 3 años
  →   0 = máximo posicionamiento bajista en 3 años

Señal de trading:
  • Leveraged Funds > 70  → sesgo BULLISH (especuladores comprados)
  • Leveraged Funds < 30  → sesgo BEARISH (especuladores vendidos)
  • Asset Manager > 70    → sesgo BULLISH (institucionales acumulando)
"""
import pandas as pd
import io, zipfile, requests, warnings
warnings.filterwarnings("ignore")

NQ_CODE    = "209742"        # E-mini NASDAQ-100 CME
LOOKBACK_W = 156             # 3 años (52 semanas × 3)

# ─── 1. Descargar datos TFF de CFTC ──────────────────────────────────────────
YEARS  = [2023, 2024, 2025]
BASE   = "https://www.cftc.gov/files/dea/history/fut_fin_txt_{}.zip"
COLS   = {
    "Market_and_Exchange_Names": "market",
    "Report_Date_as_MM_DD_YYYY": "date",
    "CFTC_Market_Code":          "code",
    "Pct_of_OI_AM_Long_All":     "am_long_pct",
    "Pct_of_OI_AM_Short_All":    "am_short_pct",
    "Pct_of_OI_Lev_Long_All":    "lev_long_pct",
    "Pct_of_OI_Lev_Short_All":   "lev_short_pct",
    "Traders_AM_Long_All":       "am_long_t",
    "Traders_AM_Short_All":      "am_short_t",
    "Traders_Lev_Long_All":      "lev_long_t",
    "Traders_Lev_Short_All":     "lev_short_t",
    # Posiciones netas (usamos long - short de los reportes)
    "AM_Positions_Long_All":     "am_pos_long",
    "AM_Positions_Short_All":    "am_pos_short",
    "Lev_Money_Positions_Long_All":  "lev_pos_long",
    "Lev_Money_Positions_Short_All": "lev_pos_short",
    "Dealer_Positions_Long_All":     "dealer_pos_long",
    "Dealer_Positions_Short_All":    "dealer_pos_short",
}

frames = []
for yr in YEARS:
    url = BASE.format(yr)
    print(f"  📥 Descargando CFTC TFF {yr}...")
    try:
        r = requests.get(url, timeout=30)
        z = zipfile.ZipFile(io.BytesIO(r.content))
        fname = [n for n in z.namelist() if n.endswith(".txt")][0]
        with z.open(fname) as f:
            raw = pd.read_csv(f, low_memory=False)
        # Filtrar NQ
        nq = raw[raw["CFTC_Market_Code"].astype(str).str.strip() == NQ_CODE].copy()
        if nq.empty:
            print(f"     ⚠️  {yr}: Sin datos NQ (código {NQ_CODE})")
            continue
        # Seleccionar columnas disponibles
        available = {k: v for k, v in COLS.items() if k in nq.columns}
        nq = nq[list(available.keys())].rename(columns=available)
        frames.append(nq)
        print(f"     ✅ {yr}: {len(nq)} reportes NQ encontrados")
    except Exception as e:
        print(f"     ❌ {yr}: {e}")

if not frames:
    print("\n❌ No se pudieron descargar datos CFTC. Verificar conexión.")
    exit()

df = pd.concat(frames, ignore_index=True)
df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

print(f"\n  ✅ Total reportes COT NQ: {len(df)}")
print(f"  📅 Rango: {df['date'].min().strftime('%Y-%m-%d')} → {df['date'].max().strftime('%Y-%m-%d')}")

# ─── 2. Calcular Netos ────────────────────────────────────────────────────────
df["net_lev"]    = df["lev_pos_long"]    - df["lev_pos_short"]     # Leveraged Funds
df["net_am"]     = df["am_pos_long"]     - df["am_pos_short"]       # Asset Managers
df["net_dealer"] = df["dealer_pos_long"] - df["dealer_pos_short"]   # Dealers

# ─── 3. COT Index (lookback = 3 años / todos los datos disponibles) ───────────
def cot_index(series, lookback=LOOKBACK_W):
    idx = pd.Series(index=series.index, dtype=float)
    for i in range(len(series)):
        window = series.iloc[max(0, i - lookback + 1): i + 1]
        mn, mx = window.min(), window.max()
        if mx == mn:
            idx.iloc[i] = 50.0
        else:
            idx.iloc[i] = (series.iloc[i] - mn) / (mx - mn) * 100
    return idx

df["cot_lev"]    = cot_index(df["net_lev"])
df["cot_am"]     = cot_index(df["net_am"])
df["cot_dealer"] = cot_index(df["net_dealer"])

# ─── 4. Último reporte ────────────────────────────────────────────────────────
last = df.iloc[-1]
prev = df.iloc[-2] if len(df) >= 2 else last

def bias(val):
    if val >= 70: return "🟢 BULL FUERTE"
    if val >= 55: return "🟡 BULL LEVE"
    if val <= 30: return "🔴 BEAR FUERTE"
    if val <= 45: return "🟠 BEAR LEVE"
    return "⚪ NEUTRO"

print()
print("═" * 65)
print(f"  📊 COT INDEX — NQ NASDAQ-100 (último reporte: {last['date'].strftime('%Y-%m-%d')})")
print("═" * 65)

for label, col_idx, col_net in [
    ("Leveraged Funds (Hedge Funds)", "cot_lev",    "net_lev"),
    ("Asset Managers (Institucional)", "cot_am",     "net_am"),
    ("Dealer/Intermediary (SM)",       "cot_dealer", "net_dealer"),
]:
    v_now  = last[col_idx]
    v_prev = prev[col_idx]
    net    = last[col_net]
    chg    = v_now - v_prev
    arrow  = "▲" if chg > 0 else "▼"
    bar    = "█" * int(v_now / 5) + "░" * (20 - int(v_now / 5))
    print(f"\n  {label}")
    print(f"  COT Index : {v_now:5.1f} / 100  {arrow}{abs(chg):.1f}  [{bar}]")
    print(f"  Net Pos   : {net:+,.0f} contratos")
    print(f"  SEÑAL     : {bias(v_now)}")

# ─── 5. Señal consolidada ─────────────────────────────────────────────────────
print()
print("═" * 65)
lev_bias = last["cot_lev"]
am_bias  = last["cot_am"]

if lev_bias >= 60 and am_bias >= 55:
    signal = "🟢🟢 DOBLE BULL — Alta probabilidad alcista"
elif lev_bias <= 40 and am_bias <= 45:
    signal = "🔴🔴 DOBLE BEAR — Alta probabilidad bajista"
elif lev_bias >= 60:
    signal = "🟡 BULL por Leveraged Funds (hedge funds comprados)"
elif am_bias >= 60:
    signal = "🟡 BULL por Asset Managers (institucionales acumulando)"
elif lev_bias <= 40:
    signal = "🟠 BEAR por Leveraged Funds (hedge funds vendidos)"
else:
    signal = "⚪ SEÑAL MIXTA — Sin sesgo claro"

print(f"  🎯 SEÑAL COT CONSOLIDADA: {signal}")
print()

# ─── 6. Combinado con sesgo diario ───────────────────────────────────────────
print("═" * 65)
print("  📅 SESGO DIARIO + COT INDEX → PLAN DE LA SEMANA")
print("═" * 65)
daily_bias = {
    "LUNES":      "🟢 BULL (impulso 1.31x)",
    "MARTES":     "🟡 BULL LEVE (1.11x)",
    "MIÉRCOLES":  "🟡 BULL LEVE (1.46x, mayor range)",
    "JUEVES":     "⚪ NEUTRO (0.91x, confirmar patrón)",
    "VIERNES":    "🔴 BEARISH (0.44x, 75% bear)",
}
cot_context = signal

for dia, dbias in daily_bias.items():
    if "BULL" in cot_context or "BULL" in cot_context.upper():
        if "🟢" in dbias or "🟡" in dbias:
            combo = "✅ COT + Día ALINEAN → LONG"
        elif "🔴" in dbias:
            combo = "⚠️  COT BULL pero día BEAR → reducir size o skip"
        else:
            combo = "🔶 COT BULL + día neutro → esperar confirmación"
    elif "BEAR" in cot_context:
        if "🔴" in dbias:
            combo = "✅ COT + Día ALINEAN → SHORT"
        elif "🟢" in dbias:
            combo = "⚠️  COT BEAR pero día BULL → reducir size o skip"
        else:
            combo = "🔶 COT BEAR + día neutro → esperar confirmación"
    else:
        combo = "🔶 Sin alineación clara → solo setups de alta calidad"

    print(f"  {dia:<13} {dbias:<35}  {combo}")

print()
print("  NOTA: COT data con retraso ~3 días (martes→viernes publicación)")
print("        Lookback 3 años para normalización del índice")
print("═" * 65)
