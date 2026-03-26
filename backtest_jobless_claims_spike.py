"""
╔══════════════════════════════════════════════════════════════════════════╗
║  ANÁLISIS DETALLADO: JOBLESS CLAIMS → FIGURA DE PRECIO EN APERTURA NY  ║
║  ─────────────────────────────────────────────────────────────────────  ║
║  Pregunta clave:                                                         ║
║    ¿Jobless Claims da DIRECCIÓN REAL al NQ o solo hace spike y vuelve? ║
║                                                                          ║
║  Metodología:                                                            ║
║    1. Capturar cada barra de 8:30 (pre-noticia) vs 8:45 (spike)         ║
║    2. Medir amplitud del spike (pts)                                     ║
║    3. Clasificar: ¿el spike se mantiene? ¿regresa? ¿continúa?          ║
║    4. Detectar figura: FAKE-OUT / CONTINUATION / CHOP                   ║
║    5. Comparar dirección spike vs cierre NY (16:00)                     ║
║                                                                          ║
║  Dato extra: Jobless Claims sale a las 8:30 ET (pre-market)             ║
║  → La reacción visible es en la apertura NY 9:30 y en el pre-market    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from collections import defaultdict


# ─────────────────────────────────────────────────────────────────────────────
#  NOTA IMPORTANTE SOBRE JOBLESS CLAIMS
# ─────────────────────────────────────────────────────────────────────────────
# • Sale TODOS los jueves a las 8:30 ET (pre-mercado)
# • Número MENOR al esperado = señal POSITIVA (menos desempleo) → puede subir NQ
# • Número MAYOR al esperado = señal NEGATIVA (más desempleo)  → puede bajar NQ
# • El mercado YA descuenta expectativas → el movimiento depende del DELTA
#   vs. estimado (consensus), no del número absoluto
#
# Tipos de reacción observados en el mercado:
# ┌─────────────────┬────────────────────────────────────────────────────┐
# │ FAKE-OUT BAJISTA│ Cae fuerte en pre-market → recupera y cierra sup   │
# │ FAKE-OUT ALCISTA│ Sube fuerte en pre-market → cae y cierra inferior  │
# │ CONTINUATION    │ Spike en una dirección + sigue toda la sesión NY   │
# │ CHOP / NO-MOVE  │ Se mueve < 50 pts en todo el rango → confusión     │
# └─────────────────┴────────────────────────────────────────────────────┘


def calc_spike_analysis(df, day):
    """
    Analiza el comportamiento de precio en el jueves de Jobless Claims.
    Ventanas:
      • Pre-noticia (pre-market):  7:00–8:29 ET
      • Spike inicial:             8:30–8:45 ET
      • Pre-apertura:              8:45–9:29 ET
      • Apertura NY (1ra hora):   9:30–10:30 ET
      • Hora 2:                   10:30–11:30 ET
      • Tarde:                    11:30–14:00 ET
      • Cierre:                   14:00–16:00 ET
    """
    results = {}

    def get_slice(h_start, m_start, h_end, m_end):
        t0 = day.replace(hour=h_start, minute=m_start, second=0, microsecond=0)
        t1 = day.replace(hour=h_end,   minute=m_end,   second=0, microsecond=0)
        return df.loc[t0:t1]

    # Pre-noticia
    pre = get_slice(7, 0, 8, 29)
    if pre.empty:
        return None
    pre_close  = float(pre.iloc[-1]['Close'])
    results['pre_close'] = pre_close

    # Spike (8:30 exacto)
    spike_window = get_slice(8, 30, 8, 45)
    if spike_window.empty:
        return None
    spike_high = float(spike_window['High'].max())
    spike_low  = float(spike_window['Low'].min())
    spike_open = float(spike_window.iloc[0]['Open'])
    spike_close= float(spike_window.iloc[-1]['Close'])
    spike_range = spike_high - spike_low
    spike_dir  = "UP"   if spike_close > spike_open + 10 else \
                 "DOWN" if spike_close < spike_open - 10 else "FLAT"
    spike_magnitude = spike_close - spike_open  # positivo = subió
    results['spike_range']     = round(spike_range, 1)
    results['spike_dir']       = spike_dir
    results['spike_magnitude'] = round(spike_magnitude, 1)
    results['spike_from_pre']  = round(spike_close - pre_close, 1)

    # Pre-apertura 8:45–9:29
    pre_open = get_slice(8, 45, 9, 29)
    if not pre_open.empty:
        results['pre_open_close'] = round(float(pre_open.iloc[-1]['Close']), 2)
    else:
        results['pre_open_close'] = spike_close

    # Apertura NY 9:30
    ny_open_bar = get_slice(9, 30, 9, 30)
    ny_open_price = float(ny_open_bar.iloc[0]['Open']) if not ny_open_bar.empty else None

    # Hora 1: 9:30–10:30
    h1 = get_slice(9, 30, 10, 30)
    if h1.empty:
        return None
    h1_high  = float(h1['High'].max())
    h1_low   = float(h1['Low'].min())
    h1_open  = float(h1.iloc[0]['Open'])
    h1_close = float(h1.iloc[-1]['Close'])
    h1_range = h1_high - h1_low
    results['h1_open']  = round(h1_open, 2)
    results['h1_close'] = round(h1_close, 2)
    results['h1_range'] = round(h1_range, 1)
    results['h1_dir']   = "UP" if h1_close > h1_open + 15 else \
                          "DOWN" if h1_close < h1_open - 15 else "FLAT"

    # Hora 2: 10:30–11:30
    h2 = get_slice(10, 30, 11, 30)
    if not h2.empty:
        results['h2_close'] = round(float(h2.iloc[-1]['Close']), 2)
        results['h2_range'] = round(float(h2['High'].max() - h2['Low'].min()), 1)

    # Full day
    full = get_slice(9, 30, 16, 0)
    if not full.empty:
        results['ny_close']   = round(float(full.iloc[-1]['Close']), 2)
        results['ny_high']    = round(float(full['High'].max()), 2)
        results['ny_low']     = round(float(full['Low'].min()), 2)
        results['full_range'] = round(full['High'].max() - full['Low'].min(), 1)

        # Dirección NY completa (vs apertura)
        if ny_open_price:
            ny_move = float(full.iloc[-1]['Close']) - ny_open_price
            results['ny_dir'] = "UP" if ny_move > 30 else "DOWN" if ny_move < -30 else "FLAT"
            results['ny_move_pts'] = round(ny_move, 1)
        else:
            results['ny_dir']      = "N/A"
            results['ny_move_pts'] = 0

    # ── CLASIFICACIÓN FIGURA ─────────────────────────────────────────────
    # ¿El spike de 8:30 da la dirección de la sesión NY completa?
    spike_matches_ny = (
        results.get('spike_dir') == results.get('ny_dir') and
        results.get('spike_dir') != "FLAT"
    )
    results['spike_confirms_ny'] = spike_matches_ny

    # Tipo de figura
    spike_d  = results.get('spike_dir', 'FLAT')
    ny_d     = results.get('ny_dir', 'FLAT')
    ny_move  = abs(results.get('ny_move_pts', 0))
    h1_r     = results.get('h1_range', 0)
    s_mag    = abs(results.get('spike_magnitude', 0))

    if s_mag < 30 and ny_move < 50:
        figura = "CHOP_LATERAL"
    elif spike_d == "FLAT":
        figura = "SIN_REACCION_SPIKE"
    elif spike_d == ny_d:
        figura = "CONTINUATION"     # Spike da dirección real y se mantiene
    elif spike_d != ny_d and s_mag > 50:
        figura = "FAKE_OUT"          # Spike fuerte pero NY va al revés
    elif spike_d != ny_d and s_mag <= 50:
        figura = "REVERSAL_MENOR"    # Spike chico y revierte
    else:
        figura = "MIXTA"

    results['figura'] = figura

    return results


def run_jobless_analysis():
    csv_path = "data/research/nq_15m_intraday.csv"
    if not os.path.exists(csv_path):
        print(f"❌ No se encontró: {csv_path}")
        return

    print("⏳ Cargando datos...")
    df = pd.read_csv(csv_path, skiprows=2)
    df.columns = ['Datetime', 'Close', 'High', 'Low', 'Open', 'Volume']
    df = df.dropna(subset=['Datetime'])
    df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)
    df.set_index('Datetime', inplace=True)
    df.index = df.index.tz_convert('America/New_York')
    df = df.sort_index()

    # Últimos 365 días
    end_date   = df.index.max()
    start_date = end_date - timedelta(days=365)
    df_window  = df.loc[start_date:]

    days = df_window.index.normalize().unique()

    # Colectores
    all_results   = []
    figuras_count = defaultdict(int)
    spike_vs_ny   = {"ALINEA": 0, "REVIERTE": 0, "FLAT": 0}

    # Métricas de comportamiento
    spike_ranges  = []
    h1_ranges     = []
    full_ranges   = []
    spike_mags    = []

    # ── Analizar cada jueves ───────────────────────────────────────────────
    for day in days:
        if day.weekday() != 3:  # Solo jueves
            continue

        date_str = day.strftime('%Y-%m-%d')
        res = calc_spike_analysis(df_window, day)
        if res is None:
            continue

        res['date'] = date_str
        all_results.append(res)

        figuras_count[res['figura']] += 1
        spike_ranges.append(res.get('spike_range', 0))
        h1_ranges.append(res.get('h1_range', 0))
        full_ranges.append(res.get('full_range', 0))
        spike_mags.append(abs(res.get('spike_magnitude', 0)))

        if res.get('spike_dir') == 'FLAT' or res.get('ny_dir') == 'FLAT':
            spike_vs_ny["FLAT"] += 1
        elif res.get('spike_confirms_ny'):
            spike_vs_ny["ALINEA"] += 1
        else:
            spike_vs_ny["REVIERTE"] += 1

    total = len(all_results)
    if total == 0:
        print("❌ Sin datos suficientes")
        return

    W = 76

    print("\n" + "═" * W)
    print("  🔔 JOBLESS CLAIMS → ¿DIRECCIÓN REAL O SOLO SPIKE?")
    print("  📊 NQ Nasdaq · Análisis comportamiento NY")
    print("═" * W)
    print(f"  Jueves analizados: {total}")
    print(f"  Período: {all_results[0]['date']} → {all_results[-1]['date']}")

    # ── RESPUESTA A LA PREGUNTA ────────────────────────────────────────────
    pct_alinea  = round(spike_vs_ny["ALINEA"]  / total * 100, 1)
    pct_reviert = round(spike_vs_ny["REVIERTE"]/ total * 100, 1)
    pct_flat    = round(spike_vs_ny["FLAT"]    / total * 100, 1)

    print(f"\n{'─'*W}")
    print("  ❓ RESPUESTA: ¿El Jobless Claims da dirección real?")
    print(f"{'─'*W}")
    print(f"")
    print(f"  {'█' * int(pct_alinea/3):<25} SPIKE ALINEA con NY   : {spike_vs_ny['ALINEA']:>3} veces ({pct_alinea:.1f}%)")
    print(f"  {'█' * int(pct_reviert/3):<25} SPIKE REVIERTE vs NY  : {spike_vs_ny['REVIERTE']:>3} veces ({pct_reviert:.1f}%)")
    print(f"  {'█' * int(pct_flat/3):<25} SPIKE PLANO / SIN MOVE : {spike_vs_ny['FLAT']:>3} veces ({pct_flat:.1f}%)")
    print(f"")

    if pct_alinea > pct_reviert:
        print(f"  ✅ CONCLUSIÓN: El spike del Claims SÍ tiende a dar DIRECCIÓN")
        print(f"     Alineación {pct_alinea:.0f}% vs reversal {pct_reviert:.0f}%")
    elif pct_reviert > pct_alinea:
        print(f"  ⚠️  CONCLUSIÓN: El spike del Claims es FRECUENTEMENTE FAKE-OUT")
        print(f"     Revierte {pct_reviert:.0f}% de las veces → NO fiar del primer movimiento")
    else:
        print(f"  🔄 CONCLUSIÓN: Resultado MIXTO — Claims no tiene edge claro")

    # ── FIGURAS QUE FORMA ─────────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📐 FIGURAS DE PRECIO FORMADAS (8:30 → Cierre NY)")
    print(f"{'─'*W}")
    print()

    figura_desc = {
        "CONTINUATION":      "Spike → continúa en la misma dirección todo el día",
        "FAKE_OUT":          "Spike fuerte (>50pts) → REVIERTE completamente (NYC opuesto)",
        "REVERSAL_MENOR":    "Spike chico → se da vuelta suave",
        "CHOP_LATERAL":      "Sin reacción real, mercado lateral todo el día",
        "SIN_REACCION_SPIKE":"No hay spike en premarket, NY mueve solo",
        "MIXTA":             "Comportamiento mixto / inclasificable",
    }

    sorted_figs = sorted(figuras_count.items(), key=lambda x: x[1], reverse=True)
    for fig, cnt in sorted_figs:
        pct = round(cnt / total * 100, 1)
        bar = "█" * int(pct / 4)
        desc = figura_desc.get(fig, "")
        print(f"  {fig:<22} {cnt:>2} casos ({pct:>5.1f}%)  {bar}")
        print(f"  {'':22} → {desc}")
        print()

    # ── AMPLITUDES ────────────────────────────────────────────────────────
    print(f"{'─'*W}")
    print("  📏 AMPLITUD DE MOVIMIENTOS")
    print(f"{'─'*W}")
    print(f"  Spike 8:30 (amplitud 15m) : prom {round(np.mean(spike_ranges), 0):.0f} pts  |  máx {max(spike_ranges):.0f}  |  mín {min(spike_ranges):.0f}")
    print(f"  Spike magnitud (dir) prom : {round(np.mean(spike_mags), 0):.0f} pts en la dirección del movimiento")
    print(f"  Hora 1 NY (9:30–10:30)   : prom {round(np.mean(h1_ranges), 0):.0f} pts  |  máx {max(h1_ranges):.0f}  |  mín {min(h1_ranges):.0f}")
    print(f"  Full Day (9:30–16:00)    : prom {round(np.mean(full_ranges), 0):.0f} pts  |  máx {max(full_ranges):.0f}  |  mín {min(full_ranges):.0f}")

    ratio = round(np.mean(spike_ranges) / np.mean(full_ranges) * 100, 1) if np.mean(full_ranges) else 0
    print(f"\n  El spike inicial representa el {ratio:.0f}% del rango total del día")
    if ratio < 20:
        print(f"  → El movimiento del Claims es SOLO UNA PARTE PEQUEÑA del total del día")
    elif ratio > 50:
        print(f"  → El spike inicial ya define GRAN PARTE del movimiento del día")

    # ── TABLA DETALLE POR DÍA ────────────────────────────────────────────
    print(f"\n{'─'*W}")
    print("  📋 DETALLE POR JUEVES (Jobless Claims)")
    print(f"{'─'*W}")
    print(f"  {'FECHA':<12} {'SPIKE(pts)':<12} {'SPIKE_DIR':<10} {'H1_DIR':<8} {'NY_DIR':<8} {'FIGURA':<20} {'NY_TOTAL'}")
    print(f"  {'─'*72}")

    for r in all_results:
        spike_icon = "⬆️ " if r.get('spike_dir') == 'UP' else ("⬇️ " if r.get('spike_dir') == 'DOWN' else "➡️ ")
        ny_icon    = "⬆️ " if r.get('ny_dir')    == 'UP' else ("⬇️ " if r.get('ny_dir')    == 'DOWN' else "➡️ ")
        h1_icon    = "⬆️ " if r.get('h1_dir')    == 'UP' else ("⬇️ " if r.get('h1_dir')    == 'DOWN' else "➡️ ")
        match_icon = "✅" if r.get('spike_confirms_ny') else "❌"

        print(f"  {r['date']:<12} {r.get('spike_magnitude',0):>+7.0f} pts  "
              f"{spike_icon:<5} "
              f"{h1_icon:<5} "
              f"{ny_icon}{match_icon}    "
              f"{r.get('figura','?'):<20} "
              f"{r.get('ny_move_pts',0):>+6.0f} pts")

    # ── GUÍA OPERATIVA ────────────────────────────────────────────────────
    print(f"\n{'═'*W}")
    print("  💡 GUÍA OPERATIVA PARA JUEVES DE JOBLESS CLAIMS")
    print(f"{'═'*W}")
    print("""
  ┌─────────────────────────────────────────────────────────────────────┐
  │  DATO CLAVE: Jobless Claims sale 8:30 ET (1 hora antes apertura NY) │
  └─────────────────────────────────────────────────────────────────────┘

  PROTOCOLO RECOMENDADO SEGÚN FIGURA:

  🔴 ANTES DE 8:30:
     • No entres posiciones nuevas – el mercado está esperando el dato
     • Identifica el rango de Asia/Londres (VAH/POC/VAL)
     • Marca el nivel del EMA200 en 15min

  📊 A LAS 8:30 ET (SPIKE):
     • Observa la magnitud: <50pts = ruido / >100pts = dato sorpresa
     • NO entres en el primer spike inmediato (trampa frecuente)
     • Espera CONFIRMACIÓN: ¿el precio aguanta el movimiento 10-15 min?

  🎯 9:00–9:30 ET (PRE-APERTURA):
     • Si el spike se mantuvo → espera CONTINUATION en apertura
     • Si el spike ya revirtió → busca FADE en apertura NY
     • El nivel del VAL o VAH del profile Asia es tu filtro principal

  🏁 9:30 ET (APERTURA NY):
     • SETUP 1 – CONTINUATION: Si spike subió Y sigue sobre VAH → LONG
     • SETUP 2 – FADE/REVERSAL: Si spike subió Y ya volvió bajo POC → SHORT
     • SETUP 3 – CHOP: Si rango 8:30–9:30 < 50pts → esperar hasta 10am

  ⚠️  REGLAS DE GESTIÓN:
     • STOP siempre del otro lado del extremo del spike
     • Normal los jueves: rango H1 de 200-400 pts
     • Si el dato es muy sorpresa (>50k diferencia vs estimado): volatilidad
       extrema – reducir tamaño 50% o esperar 9:45 para entrar
""")
    print("═" * W)
    print(f"\n  ✅ Análisis completado — {total} jueves de Jobless Claims\n")

    # ── EXPORTAR JSON PARA DASHBOARD ─────────────────────────────────────
    if pct_alinea > pct_reviert:
        conclusion = "GIVES_DIRECTION"
    elif pct_reviert > pct_alinea:
        conclusion = "FREQUENT_FAKEOUT"
    else:
        conclusion = "MIXED"

    output = {
        "title":           "Jobless Claims Spike Analysis · NQ",
        "period":          f"{all_results[0]['date']} → {all_results[-1]['date']}",
        "total_thursdays": total,
        "spike_vs_ny": {
            "ALINEA":   spike_vs_ny["ALINEA"],
            "REVIERTE": spike_vs_ny["REVIERTE"],
            "FLAT":     spike_vs_ny["FLAT"],
        },
        "pct_alinea":  pct_alinea,
        "pct_revierte": pct_reviert,
        "pct_flat":    pct_flat,
        "conclusion":  conclusion,
        "figuras": dict(figuras_count),
        "amplitudes": {
            "avg_spike_range":      round(float(np.mean(spike_ranges)), 1),
            "max_spike_range":      round(float(max(spike_ranges)), 1),
            "min_spike_range":      round(float(min(spike_ranges)), 1),
            "avg_spike_magnitude":  round(float(np.mean(spike_mags)), 1),
            "avg_h1_range":         round(float(np.mean(h1_ranges)), 1),
            "max_h1_range":         round(float(max(h1_ranges)), 1),
            "avg_full_range":       round(float(np.mean(full_ranges)), 1),
            "max_full_range":       round(float(max(full_ranges)), 1),
            "spike_pct_of_day":     ratio,
        },
        "all_thursdays": [
            {
                "date":             r["date"],
                "spike_magnitude":  r.get("spike_magnitude", 0),
                "spike_range":      r.get("spike_range", 0),
                "spike_dir":        r.get("spike_dir", "FLAT"),
                "h1_dir":           r.get("h1_dir", "FLAT"),
                "ny_dir":           r.get("ny_dir", "FLAT"),
                "figura":           r.get("figura", "MIXTA"),
                "spike_confirms_ny":r.get("spike_confirms_ny", False),
                "full_range":       r.get("full_range", 0),
                "ny_move_pts":      r.get("ny_move_pts", 0),
                "h1_range":         r.get("h1_range", 0),
            }
            for r in all_results
        ],
    }

    out_path = os.path.join("data", "research", "backtest_jobless_claims_spike.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"  📁 JSON exportado → {out_path}\n")


if __name__ == "__main__":
    # ── EXPLICACIÓN ADICIONAL (imprime siempre) ────────────────────────────
    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║  📚 ¿Qué es Jobless Claims y cómo afecta al NQ?                        ║
╠══════════════════════════════════════════════════════════════════════════╣
║  • Sale TODOS los JUEVES a las 8:30 ET                                 ║
║  • Mide cuántas personas pidieron desempleo esa semana                  ║
║                                                                          ║
║  IMPACTO en NQ (Nasdaq):                                                ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │ Claims MENOR al estimado → mercado laboral FUERTE                │   ║
║  │   → Puede subir NQ (economía bien)  O bajar (Fed no baja tasas) │   ║
║  │                                                                  │   ║
║  │ Claims MAYOR al estimado → mercado laboral DÉBIL                 │   ║
║  │   → Puede bajar NQ (economía mal) O subir (Fed bajará tasas)    │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                          ║
║  👆 POR ESO el spike es frecuentemente INCIERTO en dirección            ║
║  El mercado necesita PROCESAR si el dato es bueno o malo en contexto   ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)

    run_jobless_analysis()
