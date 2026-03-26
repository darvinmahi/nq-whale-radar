"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  JUEVES NEWS DAY — SPACE MOVE + RETORNO AL POC/VA EN NY PM                 ║
║  NQ Futures | 5 min | ~60 días Yahoo Finance                               ║
║                                                                              ║
║  FLUJO:                                                                      ║
║   1. Profile: 12:00 AM → 9:29 AM ET  →  VAH / POC / VAL                   ║
║   2. Space Move: primer impulso 9:30 → 10:00 AM  (≥ SPACE_THRESHOLD pts)  ║
║   3. Retorno medido: 10:00 AM → 4:00 PM NY (tarde/afternoon)               ║
║                                                                              ║
║  OBJETIVO: ¿Cuántas veces el NQ vuelve al POC / VA range después           ║
║  del space move del Jueves de noticias?                                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ══════════════════════════════════════════════════════════
#  PARÁMETROS
# ══════════════════════════════════════════════════════════
VA_PCT          = 0.70   # Value Area = 70% del volumen
N_BINS          = 100    # precisión del perfil

SPACE_THRESHOLD = 40     # pts mínimos del impulso inicial (ajustar si 0 resultados)
SPACE_WIN_MIN   = 30     # ventana del space move en minutos desde 9:30
                         # 30 min = 9:30 → 10:00 AM

POC_MARGIN      = 10     # pts tolerancia para "tocó POC"
VA_MARGIN       = 8      # pts tolerancia para "entró al VA"

# ══════════════════════════════════════════════════════════
#  DESCARGA
# ══════════════════════════════════════════════════════════
print("═" * 72)
print("  🎯 JUEVES NEWS — Space Move Analysis + Retorno POC/VA (NY PM)")
print("═" * 72)
print("\n📡 Descargando NQ=F  5m  (60 días)...")

try:
    df_raw = yf.download("NQ=F", period="60d", interval="5m", progress=False)
    if isinstance(df_raw.columns, pd.MultiIndex):
        df_raw.columns = df_raw.columns.get_level_values(0)
    if df_raw.index.tz is None:
        df_raw.index = df_raw.index.tz_localize("UTC")
    df_raw.index = df_raw.index.tz_convert("America/New_York")
    df_raw = df_raw.sort_index()
    print(f"  ✅ {len(df_raw)} velas  ({df_raw.index[0].date()} → {df_raw.index[-1].date()})")
except Exception as e:
    print(f"  ❌ Error: {e}"); raise

df          = df_raw.copy()
df["date"]  = df.index.normalize()
df["wd"]    = df.index.dayofweek   # 3 = Jueves
df["h"]     = df.index.hour
df["m"]     = df.index.minute

thursdays = sorted(df[df["wd"] == 3]["date"].unique())
print(f"  📅 Jueves en el dataset: {len(thursdays)}")

# ══════════════════════════════════════════════════════════
#  FUNCIÓN: Volume Profile → VAL, POC, VAH
# ══════════════════════════════════════════════════════════
def build_profile(data):
    if len(data) < 2:
        m = float(data["Close"].mean()) if not data.empty else 0
        return m, m, m
    lo = float(data["Low"].min())
    hi = float(data["High"].max())
    if hi <= lo:
        m = (hi + lo) / 2; return m, m, m

    bins   = np.linspace(lo, hi, N_BINS + 1)
    vol_at = np.zeros(N_BINS)

    for _, row in data.iterrows():
        rlo  = float(row["Low"])
        rhi  = float(row["High"])
        rvol = float(row.get("Volume", 1)) or 1
        span = max(rhi - rlo, 1e-9)
        for b in range(N_BINS):
            ov = min(rhi, bins[b+1]) - max(rlo, bins[b])
            if ov > 0:
                vol_at[b] += rvol * (ov / span)

    if vol_at.sum() == 0:
        m = (hi + lo) / 2; return m, m, m

    poc_idx = int(np.argmax(vol_at))
    poc     = (bins[poc_idx] + bins[poc_idx + 1]) / 2.0

    target = vol_at.sum() * VA_PCT
    acc    = vol_at[poc_idx]
    hi_i   = poc_idx
    lo_i   = poc_idx

    while acc < target:
        can_up = hi_i + 1 < N_BINS
        can_dn = lo_i - 1 >= 0
        if not can_up and not can_dn:
            break
        v_up = vol_at[hi_i + 1] if can_up else -1.0
        v_dn = vol_at[lo_i - 1] if can_dn else -1.0
        if v_up >= v_dn:
            hi_i += 1; acc += v_up
        else:
            lo_i -= 1; acc += v_dn

    vah = (bins[hi_i] + bins[hi_i + 1]) / 2.0
    val = (bins[lo_i] + bins[lo_i + 1]) / 2.0
    return float(val), float(poc), float(vah)


# ══════════════════════════════════════════════════════════
#  ANÁLISIS DÍA A DÍA
# ══════════════════════════════════════════════════════════
records  = []
skipped  = []

for day in thursdays:
    day_data = df[df["date"] == day]
    if day_data.empty:
        continue

    date_str = str(pd.Timestamp(day).date())

    # ── 1. PROFILE: 12:00 AM → 9:29 AM ─────────────────────────
    prof = day_data[
        (day_data["h"] < 9) |
        ((day_data["h"] == 9) & (day_data["m"] < 30))
    ]
    if len(prof) < 4:
        skipped.append(date_str); continue

    val, poc, vah = build_profile(prof)
    va_range = vah - val
    if va_range < 5:
        skipped.append(date_str); continue

    # ── 2. NY OPEN: barras 9:30 → 9:59 (Space Move window) ─────
    space_win = day_data[
        (day_data["h"] == 9) & (day_data["m"] >= 30)
    ]
    if space_win.empty:
        skipped.append(date_str); continue

    # Limitamos a los primeros SPACE_WIN_MIN minutos
    n_bars_space = SPACE_WIN_MIN // 5
    space_win = space_win.iloc[:n_bars_space]

    open_price  = float(space_win.iloc[0]["Open"])
    space_hi    = float(space_win["High"].max())
    space_lo    = float(space_win["Low"].min())
    space_close = float(space_win.iloc[-1]["Close"])

    move_up   = space_hi - open_price
    move_down = open_price - space_lo

    # Dirección del space move
    if move_up >= SPACE_THRESHOLD and move_up > move_down:
        space_dir  = "▲ UP"
        space_size = move_up
        extreme    = space_hi
    elif move_down >= SPACE_THRESHOLD and move_down >= move_up:
        space_dir  = "▼ DOWN"
        space_size = move_down
        extreme    = space_lo
    else:
        # No hay space move suficiente
        skipped.append(f"{date_str} [space:{max(move_up,move_down):.0f}pt < {SPACE_THRESHOLD}]")
        continue

    # Posición del open vs Profile
    if   open_price > vah + VA_MARGIN: open_pos = "ABOVE_VA"
    elif open_price < val - VA_MARGIN: open_pos = "BELOW_VA"
    else:                              open_pos  = "INSIDE_VA"

    # ── 3. RETORNO: barras 10:00 AM → 4:00 PM ───────────────────
    pm_bars = day_data[
        (day_data["h"] >= 10) & (day_data["h"] < 16)
    ]
    if pm_bars.empty:
        continue

    # Buscar primer contacto con POC y con el VA range
    ret_poc_bar  = None
    ret_poc_time = None
    ret_va_bar   = None
    ret_va_time  = None

    for idx, (ts, bar) in enumerate(pm_bars.iterrows()):
        bh = float(bar["High"])
        bl = float(bar["Low"])

        if ret_poc_bar is None:
            if bl <= poc + POC_MARGIN and bh >= poc - POC_MARGIN:
                ret_poc_bar  = idx
                ret_poc_time = ts.strftime("%H:%M")

        if ret_va_bar is None:
            if bl <= vah + VA_MARGIN and bh >= val - VA_MARGIN:
                ret_va_bar   = idx
                ret_va_time  = ts.strftime("%H:%M")

        if ret_poc_bar is not None and ret_va_bar is not None:
            break

    returned_poc = ret_poc_bar is not None
    returned_va  = ret_va_bar  is not None

    # Estadísticas PM
    pm_hi    = float(pm_bars["High"].max())
    pm_lo    = float(pm_bars["Low"].min())
    pm_close = float(pm_bars.iloc[-1]["Close"])
    pm_range = pm_hi - pm_lo

    # Distancia del extreme del space move al POC y VA
    dist_extreme_poc = abs(extreme - poc)
    dist_extreme_vah = abs(extreme - vah)
    dist_extreme_val = abs(extreme - val)

    records.append({
        "date"          : date_str,
        "val"           : round(val, 1),
        "poc"           : round(poc, 1),
        "vah"           : round(vah, 1),
        "va_range"      : round(va_range, 1),
        "open"          : round(open_price, 1),
        "open_pos"      : open_pos,
        "space_dir"     : space_dir,
        "space_size_pts": round(space_size, 1),
        "extreme"       : round(extreme, 1),
        "space_close"   : round(space_close, 1),
        "dist_to_poc"   : round(dist_extreme_poc, 1),
        "dist_to_va"    : round(min(dist_extreme_vah, dist_extreme_val), 1),
        "returned_poc"  : returned_poc,
        "returned_va"   : returned_va,
        "ret_poc_time"  : ret_poc_time or "—",
        "ret_va_time"   : ret_va_time  or "—",
        "ret_poc_bar"   : ret_poc_bar,
        "ret_va_bar"    : ret_va_bar,
        "pm_hi"         : round(pm_hi, 1),
        "pm_lo"         : round(pm_lo, 1),
        "pm_close"      : round(pm_close, 1),
        "pm_range"      : round(pm_range, 1),
    })

# ══════════════════════════════════════════════════════════
#  REPORTE — TABLA POR JUEVES
# ══════════════════════════════════════════════════════════
n = len(records)

print(f"\n{'═'*76}")
print(f"  {'FECHA':<12} {'SPACE':>8} {'DIR':<7} {'OPEN':>7} {'POC':>7} {'VA':>13}  "
      f"{'→POC?':<10} {'→VA?':<10}")
print(f"{'─'*76}")

for r in records:
    poc_tag = f"✅ {r['ret_poc_time']}" if r["returned_poc"] else "❌ nunca"
    va_tag  = f"✅ {r['ret_va_time']}"  if r["returned_va"]  else "❌ nunca"
    print(f"  {r['date']:<12} {r['space_size_pts']:>7.0f}p {r['space_dir']:<7} "
          f"{r['open']:>7.0f} {r['poc']:>7.0f} [{r['val']:>6.0f}-{r['vah']:>6.0f}]  "
          f"{poc_tag:<10} {va_tag:<10}")

# ══════════════════════════════════════════════════════════
#  ESTADÍSTICAS GLOBALES
# ══════════════════════════════════════════════════════════
print(f"\n{'═'*72}")
print(f"  📊 RESUMEN ESTADÍSTICO")
print(f"{'═'*72}")

if n == 0:
    print(f"\n  ⚠️  Sin jueves con space move ≥ {SPACE_THRESHOLD} pts")
    print(f"  Jueves saltados: {len(skipped)}")
    for s in skipped:
        print(f"    · {s}")
else:
    n_poc  = sum(1 for r in records if r["returned_poc"])
    n_va   = sum(1 for r in records if r["returned_va"])
    n_both = sum(1 for r in records if r["returned_poc"] and r["returned_va"])

    pct_poc  = n_poc  / n * 100
    pct_va   = n_va   / n * 100
    pct_both = n_both / n * 100

    avg_space = np.mean([r["space_size_pts"] for r in records])
    avg_dist  = np.mean([r["dist_to_poc"]    for r in records])

    print(f"\n  📅 Jueves totales en dataset         : {len(thursdays)}")
    print(f"  🚫 Sin space move ≥{SPACE_THRESHOLD}pts (saltados)   : {len(skipped)}")
    print(f"  🎯 Jueves con Space Move analizado  : {n}")
    print(f"  📏 Tamaño promedio del space move   : {avg_space:.0f} pts")
    print(f"  📐 Distancia promedio extreme→POC  : {avg_dist:.0f} pts")

    print(f"\n  ┌────────────────────────────────────────────────────────────┐")
    print(f"  │           RETORNO EN NY AFTERNOON (10am → 4pm)            │")
    print(f"  ├────────────────────────────────────────────────────────────┤")
    print(f"  │  Regresó al POC  (±{POC_MARGIN} pts)  {n_poc:>3}/{n} = {pct_poc:5.1f}%  {('🔥' if pct_poc>=65 else '✅' if pct_poc>=50 else '⚠️'):<3}         │")
    print(f"  │  Entró al VA   (VAL-VAH±{VA_MARGIN}p)  {n_va:>3}/{n} = {pct_va:5.1f}%  {('🔥' if pct_va>=65 else '✅' if pct_va>=50 else '⚠️'):<3}         │")
    print(f"  │  Tocó POC Y VA               {n_both:>3}/{n} = {pct_both:5.1f}%  {('🔥' if pct_both>=65 else '✅' if pct_both>=50 else '⚠️'):<3}         │")
    print(f"  └────────────────────────────────────────────────────────────┘")

    # ── Por dirección del space move ────────────────────────────
    print(f"\n  🧭 Desglose por dirección del Space Move:")
    for direc in ["▲ UP", "▼ DOWN"]:
        sub = [r for r in records if r["space_dir"] == direc]
        if not sub: continue
        sn   = len(sub)
        sp   = sum(1 for r in sub if r["returned_poc"])
        sv   = sum(1 for r in sub if r["returned_va"])
        avg_s = np.mean([r["space_size_pts"] for r in sub])
        emoji = "🔺" if "UP" in direc else "🔻"
        print(f"\n  {emoji} Space {direc}  →  n={sn}  |  Avg size={avg_s:.0f}pts")
        print(f"     Regresó al POC   : {sp:>2}/{sn} = {sp/sn*100:5.1f}%  {'🔥' if sp/sn>=0.65 else '✅' if sp/sn>=0.50 else '⚠️'}")
        print(f"     Entró al VA      : {sv:>2}/{sn} = {sv/sn*100:5.1f}%  {'🔥' if sv/sn>=0.65 else '✅' if sv/sn>=0.50 else '⚠️'}")

    # ── Por posición de open vs profile ─────────────────────────
    print(f"\n  📍 Por posición del NY Open vs Profile:")
    for pos in ["ABOVE_VA", "INSIDE_VA", "BELOW_VA"]:
        sub = [r for r in records if r["open_pos"] == pos]
        if not sub: continue
        sn = len(sub)
        sp = sum(1 for r in sub if r["returned_poc"])
        sv = sum(1 for r in sub if r["returned_va"])
        lbl = {"ABOVE_VA":"Open encima VA ▲", "INSIDE_VA":"Open dentro VA  —", "BELOW_VA":"Open debajo VA ▼"}[pos]
        print(f"     {lbl}   n={sn:>2}   POC:{sp/sn*100:5.1f}%   VA:{sv/sn*100:5.1f}%")

    # ── Hora promedio de retorno ─────────────────────────────────
    bars_poc = [r["ret_poc_bar"] for r in records if r["ret_poc_bar"] is not None]
    bars_va  = [r["ret_va_bar"]  for r in records if r["ret_va_bar"]  is not None]

    if bars_poc:
        avg_poc_bar   = np.mean(bars_poc)
        # Barra 0 = 10:00 AM, cada barra = 5 min
        avg_poc_mins  = avg_poc_bar * 5
        poc_hour      = 10 + int(avg_poc_mins) // 60
        poc_min       = int(avg_poc_mins) % 60
        print(f"\n  ⏱️  TIEMPO PROMEDIO DE RETORNO AL POC   : barra {avg_poc_bar:.1f}  → ~{poc_hour}:{poc_min:02d} AM/PM")

    if bars_va:
        avg_va_bar    = np.mean(bars_va)
        avg_va_mins   = avg_va_bar * 5
        va_hour       = 10 + int(avg_va_mins) // 60
        va_min        = int(avg_va_mins) % 60
        print(f"  ⏱️  TIEMPO PROMEDIO DE RETORNO AL VA    : barra {avg_va_bar:.1f}   → ~{va_hour}:{va_min:02d} AM/PM")

    # ── Interpretación estratégica ───────────────────────────────
    print(f"\n  {'─'*68}")
    print(f"  💡 LECTURA ESTRATÉGICA:")
    print(f"     Space Move umbral  : {SPACE_THRESHOLD} pts en {SPACE_WIN_MIN} min (9:30→10:00 AM)")
    print(f"     Ventana de retorno : 10:00 AM → 4:00 PM NY")
    print(f"")

    if pct_poc >= 65:
        print(f"  🔥 PATRÓN FUERTE: El NQ retorna al POC en {pct_poc:.0f}% de los Jueves.")
        print(f"     → Bias de MEAN-REVERSION después del space move del Jueves")
        print(f"     → Al confirmar el space move (9:30-10:00), buscar FADE hacia el POC")
    elif pct_poc >= 50:
        print(f"  ✅ PATRÓN MODERADO: Retorno al POC en {pct_poc:.0f}% de los casos.")
        print(f"     → Válido como lado de mercado, usar con filtros adicionales")
    else:
        print(f"  ⚠️  El space move tiende a CONTINUAR (sólo {pct_poc:.0f}% regresa al POC)")
        print(f"     → Jueves puede ser un día de TREND CONTINUATION")

    if pct_both >= 50:
        print(f"\n  📌 En el {pct_both:.0f}% de los casos toca AMBOS: POC y Value Area")
        print(f"     → El Value Area actúa como IMÁN magnético tras el news move")


# ══════════════════════════════════════════════════════════
#  DETALLE DE CADA JUEVES — MAPA DE BARRAS PM
# ══════════════════════════════════════════════════════════
print(f"\n{'═'*72}")
print(f"  🔍 DETALLE — TRAYECTORIA PM de cada Jueves con Space Move")
print(f"{'═'*72}")

for r in records:
    day      = r["date"]
    day_data = df[df["date"] == pd.Timestamp(day).normalize()]
    pm_bars  = day_data[(day_data["h"] >= 10) & (day_data["h"] < 16)].iloc[:24]

    poc = r["poc"]; val = r["val"]; vah = r["vah"]

    print(f"\n  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  📅 {day}  │  Space: {r['space_dir']} {r['space_size_pts']:.0f}pts  │  "
          f"Profile: VAL={val:.0f}  POC={poc:.0f}  VAH={vah:.0f}")
    print(f"  Open={r['open']:.0f}  Extreme={r['extreme']:.0f}  ({r['open_pos']})")
    print(f"  {'Hora':<7} {'Open':>7} {'High':>7} {'Low':>7} {'Cls':>7}  Estado")
    print(f"  {'─'*55}")

    for ts, bar in pm_bars.iterrows():
        ho   = float(bar["Open"])
        hh   = float(bar["High"])
        hl   = float(bar["Low"])
        hc   = float(bar["Close"])
        hora = ts.strftime("%H:%M")

        tags = []
        # POC touch
        if hl <= poc + POC_MARGIN and hh >= poc - POC_MARGIN:
            tags.append("🎯POC")
        # VA touch
        if hl <= vah + VA_MARGIN and hh >= val - VA_MARGIN:
            if not any("POC" in t for t in tags):
                tags.append("📦VA")
        # Above/below VA
        if hh < val:
            tags.append("↓belowVA")
        elif hl > vah:
            tags.append("↑aboveVA")

        tag_str = " ".join(tags) if tags else "  —"
        print(f"  {hora:<7} {ho:>7.0f} {hh:>7.0f} {hl:>7.0f} {hc:>7.0f}  {tag_str}")

# ══════════════════════════════════════════════════════════
#  EXPORTAR
# ══════════════════════════════════════════════════════════
if records:
    csv_path = os.path.join(BASE_DIR, "thursday_space_move_analysis.csv")
    pd.DataFrame(records).to_csv(csv_path, index=False)
    print(f"\n  💾 Exportado: thursday_space_move_analysis.csv  ({n} filas)")

    json_path = os.path.join(BASE_DIR, "thursday_space_move_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "params": {
                "space_threshold_pts": SPACE_THRESHOLD,
                "space_window_min"   : SPACE_WIN_MIN,
                "poc_margin"         : POC_MARGIN,
                "va_margin"          : VA_MARGIN,
                "return_window"      : "10:00 AM → 4:00 PM NY",
            },
            "total_thursdays"  : len(thursdays),
            "with_space_move"  : n,
            "returned_to_poc"  : n_poc  if n > 0 else 0,
            "returned_to_va"   : n_va   if n > 0 else 0,
            "pct_poc"          : round(pct_poc, 1)  if n > 0 else 0,
            "pct_va"           : round(pct_va,  1)  if n > 0 else 0,
            "records"          : records,
        }, f, indent=2, default=str, ensure_ascii=False)
    print(f"  💾 Exportado: thursday_space_move_summary.json")

print(f"\n{'═'*72}")
print(f"  ✅ ANÁLISIS COMPLETO — {n} Jueves con Space Move ≥{SPACE_THRESHOLD}pts")
print(f"{'═'*72}\n")
