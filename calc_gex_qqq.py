#!/usr/bin/env python3
"""
CALC GEX QQQ — Gamma Exposure Exposure del NQ (proxy via QQQ)
=============================================================
GEX mide la presión que los dealers de opciones ejercen sobre el precio.

GEX > 0 → Dealers son LONG gamma → AMORTIGUAN movimientos → día TRANQUILO
GEX < 0 → Dealers son SHORT gamma → AMPLIFICAN movimientos → día VOLÁTIL

Fuente: yfinance (QQQ options chain, proxy de NQ Nasdaq)
Output: Actualiza agent3_data.json con GEX real + guarda gex_today.json
"""

import yfinance as yf
import json
import os
from datetime import datetime, date
import pytz

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
OUT_PATH  = os.path.join(BASE_DIR, "data", "research", "gex_today.json")
A3_PATH   = os.path.join(BASE_DIR, "agent3_data.json")
ET_TZ     = pytz.timezone("US/Eastern")

os.makedirs(os.path.join(BASE_DIR, "data", "research"), exist_ok=True)

# ── GUARDIA: No ejecutar en fin de semana (mercado cerrado) ─────────────
if date.today().weekday() >= 5:
    day = "Sábado" if date.today().weekday() == 5 else "Domingo"
    print(f"⏸  {day} — calc_gex_qqq no se ejecuta en fin de semana (mercado cerrado).")
    exit(0)


def fetch_gex():
    print("=" * 55)
    print("  CALC GEX — Gamma Exposure (QQQ proxy for NQ)")
    print("=" * 55)

    try:
        qqq = yf.Ticker("QQQ")
        spot = qqq.fast_info.last_price
        if not spot:
            hist = qqq.history(period="1d")
            spot = float(hist["Close"].iloc[-1]) if not hist.empty else 480.0
        print(f"  QQQ spot: ${spot:.2f}")
    except Exception as e:
        print(f"  ⚠ Error obteniendo precio QQQ: {e}")
        spot = 480.0

    # Obtener expirations cerca (próximas 4 expiraciones)
    try:
        exps = qqq.options[:4]
        print(f"  Expirations: {exps}")
    except Exception as e:
        print(f"  ❌ No se pudo obtener opciones: {e}")
        save_fallback(spot)
        return

    total_gex = 0.0
    total_calls_oi = 0
    total_puts_oi = 0
    strikes_analyzed = 0

    for exp in exps:
        try:
            chain = qqq.option_chain(exp)
            calls = chain.calls
            puts  = chain.puts

            # Filtrar strikes cerca del dinero (±10%)
            lo = spot * 0.90
            hi = spot * 1.10

            calls_near = calls[(calls["strike"] >= lo) & (calls["strike"] <= hi)]
            puts_near  = puts[(puts["strike"] >= lo) & (puts["strike"] <= hi)]

            # === GEX = Γ × OI × 100 × spot (por strike) ===
            for _, row in calls_near.iterrows():
                gamma = row.get("gamma", 0) or 0
                oi    = row.get("openInterest", 0) or 0
                total_gex += gamma * oi * 100 * spot
                total_calls_oi += oi

            for _, row in puts_near.iterrows():
                gamma = row.get("gamma", 0) or 0
                oi    = row.get("openInterest", 0) or 0
                total_gex -= gamma * oi * 100 * spot  # Puts = negativo
                total_puts_oi += oi

            strikes_analyzed += len(calls_near) + len(puts_near)

        except Exception as e:
            print(f"  ⚠ Error en {exp}: {e}")
            continue

    # Convertir a Billions para display
    gex_b = total_gex / 1_000_000_000

    # Clasificar
    if gex_b > 0.5:
        gex_regime  = "POSITIVE_STRONG"
        gex_desc    = "Dealers LONG gamma → Día estable, movimientos amortiguados"
        gex_signal  = "📊 Baja volatilidad esperada"
    elif gex_b > 0:
        gex_regime  = "POSITIVE_WEAK"
        gex_desc    = "Dealers levemente LONG → Ligera estabilidad"
        gex_signal  = "📊 Volatilidad moderada-baja"
    elif gex_b > -0.5:
        gex_regime  = "NEGATIVE_WEAK"
        gex_desc    = "Dealers levemente SHORT gamma → Algo de amplificación"
        gex_signal  = "⚡ Volatilidad moderada-alta"
    else:
        gex_regime  = "NEGATIVE_STRONG"
        gex_desc    = "Dealers SHORT gamma → Movimientos AMPLIFICADOS"
        gex_signal  = "🔥 Alta volatilidad esperada"

    now_et = datetime.now(ET_TZ)
    result = {
        "date":              date.today().isoformat(),
        "timestamp":         now_et.isoformat(),
        "qqq_spot":          round(spot, 2),
        "gex_raw":           round(total_gex, 0),
        "gex_billions":      round(gex_b, 3),
        "gex_regime":        gex_regime,
        "gex_description":   gex_desc,
        "gex_signal":        gex_signal,
        "gex_positive":      gex_b > 0,
        "calls_oi_total":    total_calls_oi,
        "puts_oi_total":     total_puts_oi,
        "put_call_ratio":    round(total_puts_oi / max(total_calls_oi, 1), 2),
        "strikes_analyzed":  strikes_analyzed,
        "expirations_used":  list(exps),
    }

    # Guardar gex_today.json
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n  ✅ GEX calculado: {gex_b:+.3f}B → {gex_regime}")
    print(f"     {gex_desc}")
    print(f"     Strikes analizados: {strikes_analyzed}")
    print(f"     Put/Call ratio: {result['put_call_ratio']}")

    # Actualizar agent3_data.json si existe
    update_agent3(result)

    return result

def update_agent3(gex):
    """Inyecta el GEX real en agent3_data.json para que el dashboard lo muestre."""
    if not os.path.exists(A3_PATH):
        return
    try:
        with open(A3_PATH, "r", encoding="utf-8") as f:
            a3 = json.load(f)

        if "raw_inputs" not in a3:
            a3["raw_inputs"] = {}

        # Actualizar GEX (guardamos en Billions, el dashboard ya lo espera así)
        a3["raw_inputs"]["GEX_B"]     = gex["gex_billions"]
        a3["raw_inputs"]["GEX_raw"]   = gex["gex_raw"]
        a3["gex_analysis"] = {
            "value_B":     gex["gex_billions"],
            "regime":      gex["gex_regime"],
            "description": gex["gex_description"],
            "positive":    gex["gex_positive"],
            "signal":      gex["gex_signal"],
            "put_call":    gex["put_call_ratio"],
        }
        a3["last_gex_update"] = gex["timestamp"]

        with open(A3_PATH, "w", encoding="utf-8") as f:
            json.dump(a3, f, indent=2, ensure_ascii=False)
        print(f"  ✅ agent3_data.json actualizado con GEX real")
    except Exception as e:
        print(f"  ⚠ No se pudo actualizar agent3: {e}")

def save_fallback(spot):
    """Guarda un resultado neutral si las opciones no están disponibles."""
    result = {
        "date":          date.today().isoformat(),
        "gex_billions":  0.0,
        "gex_regime":    "UNKNOWN",
        "gex_description": "Datos de opciones no disponibles",
        "gex_positive":  None,
        "error":         "Sin opciones disponibles",
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    fetch_gex()
