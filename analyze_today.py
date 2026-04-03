#!/usr/bin/env python3
"""
analyze_today.py — Analizador del Día Actual con Backtest Engine
================================================================
Corre cada mañana a las 9AM ET (antes de la sesión NY).
Lee condiciones actuales + busca días similares en daily_master_db.json
Genera: data/research/today_analysis.json

Output usado por daily_dashboard.html para mostrar:
  - Condiciones del día
  - Días históricos similares
  - Estadísticas y predicción
  - Teorías activas (COT, VXN, DIX, secuencia)
"""

import json
import os
from datetime import date, datetime
from collections import Counter

DB_FILE   = "data/research/daily_master_db.json"
OUT_FILE  = "data/research/today_analysis.json"
A2_FILE   = "agent2_data.json"
A3_FILE   = "agent3_data.json"
A4_FILE   = "agent4_data.json"

DOW_ES = {
    "monday":"Lunes","tuesday":"Martes","wednesday":"Miércoles",
    "thursday":"Jueves","friday":"Viernes"
}

# ── Cargar base de datos ────────────────────────────────────────────────
if not os.path.exists(DB_FILE):
    print(f"ERROR: {DB_FILE} no existe. Ejecuta build_daily_db.py primero.")
    exit(1)

with open(DB_FILE, encoding="utf-8") as f:
    db = json.load(f)

records = db.get("records", [])
print(f"✅ DB cargada: {len(records)} registros")

# ── Condiciones de HOY ──────────────────────────────────────────────────
today     = date.today()
today_str = today.strftime("%Y-%m-%d")
dow_today = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][today.weekday()]

def semana_ciclo(d):
    day = d.day
    if day <= 7:  return "W1"
    if day <= 14: return "W2"
    if day <= 21: return "W3"
    return "W4"

def _load(path):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except: return {}

a2 = _load(A2_FILE)
a3 = _load(A3_FILE)
a4 = _load(A4_FILE)

# Leer condiciones actuales de los agentes
cot_data  = a2.get("cot", {})
raw3      = a3.get("raw_inputs", {})
vxn_raw   = raw3.get("VXN", 0) or 0
vxn_val   = float(vxn_raw)
dix_raw   = float(raw3.get("DIX", 0) or 0)
gex_raw   = float(raw3.get("GEX_B", 0) or 0)

cot_index   = float(a2.get("cot", {}).get("cot_index", 50) or 50)
cot_signal  = a2.get("signal", "NEUTRAL")
cot_net     = int(a2.get("cot", {}).get("current_net", 0) or 0)
ai_score    = int(a4.get("global_score", 50) or 50)
ai_label    = a4.get("global_label", "NEUTRAL")

def vxn_level(v):
    if v < 16:  return "COMPLACENCY"
    if v < 22:  return "NORMAL"
    if v < 30:  return "ELEVATED"
    if v < 40:  return "PANIC"
    return "EXTREME_PANIC"

vxn_lv_today = vxn_level(vxn_val)
gex_positive  = gex_raw >= 0

TODAY = {
    "date": today_str,
    "dow": dow_today,
    "dow_es": DOW_ES.get(dow_today, dow_today),
    "semana_ciclo": semana_ciclo(today),
    "cot_index": cot_index,
    "cot_signal": cot_signal,
    "cot_net": cot_net,
    "vxn": round(vxn_val, 2),
    "vxn_level": vxn_lv_today,
    "dix": round(dix_raw, 1),
    "gex_positive": gex_positive,
    "ai_score": ai_score,
    "ai_label": ai_label,
}

print(f"\n📅 HOY: {today_str} ({DOW_ES.get(dow_today,'?')})")
print(f"   COT: {cot_index}/100 ({cot_signal}) | VXN: {vxn_val} ({vxn_lv_today}) | AI: {ai_score}/100")

# ── MOTOR DE SIMILITUD ─────────────────────────────────────────────────
# Excluir el día de hoy de la comparación
historical = [r for r in records if r["date"] != today_str]

def find_similar(
    records,
    dow,
    cot_idx,
    vxn_lv,
    gex_pos=None,
    cot_tolerance=15,
    min_matches=5,
):
    """
    Filtros en cascada — si no hay suficientes, relaja criterios
    """
    # Nivel 1: Día + COT range + VXN level (más estricto)
    matches = [
        r for r in records
        if r.get("dow") == dow
        and r.get("vxn") is not None
        and abs((r.get("cot_index") or 50) - cot_idx) <= cot_tolerance
        and r.get("vxn_level") == vxn_lv
    ]
    if len(matches) >= min_matches:
        return matches, "strict"

    # Nivel 2: Día + COT range (relaja VXN level)
    matches = [
        r for r in records
        if r.get("dow") == dow
        and abs((r.get("cot_index") or 50) - cot_idx) <= cot_tolerance + 10
    ]
    if len(matches) >= min_matches:
        return matches, "moderate"

    # Nivel 3: Solo día de semana
    matches = [r for r in records if r.get("dow") == dow]
    return matches, "relaxed"

similar, match_level = find_similar(
    historical, dow_today, cot_index, vxn_lv_today, gex_positive
)

n = len(similar)
print(f"\n🔍 Días similares encontrados: {n} (nivel: {match_level})")

# ── ESTADÍSTICAS DE LOS SIMILARES ─────────────────────────────────────
def calc_stats(recs):
    if not recs: return {}
    n = len(recs)
    bull = sum(1 for r in recs if r.get("direction")=="BULLISH")
    bear = sum(1 for r in recs if r.get("direction")=="BEARISH")
    neut = n - bull - bear
    ranges = [r.get("ny_range",0) for r in recs if r.get("ny_range")]
    moves  = [r.get("ny_move_pct",0) for r in recs if r.get("ny_move_pct") is not None]
    patterns = Counter(r.get("pattern","?") for r in recs)
    top_pattern = patterns.most_common(1)[0] if patterns else ("?", 0)
    # sortear por fecha para casos historicos
    recs_sorted = sorted(recs, key=lambda x: x.get("date",""), reverse=True)
    return {
        "n": n,
        "bull": bull,
        "bear": bear,
        "neutral": neut,
        "bull_pct": round(bull/n*100,1),
        "bear_pct": round(bear/n*100,1),
        "avg_range": round(sum(ranges)/len(ranges),1) if ranges else 0,
        "max_range": round(max(ranges),1) if ranges else 0,
        "min_range": round(min(ranges),1) if ranges else 0,
        "avg_move_pct": round(sum(moves)/len(moves),3) if moves else 0,
        "top_pattern": top_pattern[0],
        "top_pattern_pct": round(top_pattern[1]/n*100,1),
        "patterns": dict(patterns.most_common(5)),
        "cases": [
            {
                "date": r["date"],
                "dow": r.get("dow","?"),
                "direction": r.get("direction","?"),
                "ny_range": r.get("ny_range",0),
                "ny_move_pct": r.get("ny_move_pct",0),
                "cot_index": r.get("cot_index",0),
                "vxn": r.get("vxn",0),
                "pattern": r.get("pattern","?"),
                "noticia": r.get("noticia","ninguna"),
            }
            for r in recs_sorted[:20]  # últimos 20 casos
        ],
    }

stats = calc_stats(similar)
print(f"   BULLISH: {stats.get('bull_pct')}% | BEARISH: {stats.get('bear_pct')}%")
print(f"   Rango promedio: {stats.get('avg_range')} pts | Patrón top: {stats.get('top_pattern')}")

# ── ANÁLISIS POR TEORÍAS ───────────────────────────────────────────────
theories = []

# Teoría 1: COT + Día
cot_day = [r for r in historical if r.get("dow")==dow_today and r.get("vxn") is not None]
if cot_day:
    s = calc_stats(cot_day)
    theories.append({
        "id": "dow_base",
        "name": f"{DOW_ES.get(dow_today,'?')} Histórico",
        "description": f"Todos los {DOW_ES.get(dow_today,'?')} en la DB",
        "n": s["n"],
        "bull_pct": s["bull_pct"],
        "bear_pct": s["bear_pct"],
        "avg_range": s["avg_range"],
        "top_pattern": s["top_pattern"],
        "conclusion": f"{s['bull_pct']}% de {DOW_ES.get(dow_today,'?')} son BULLISH — rango prom {s['avg_range']} pts",
    })

# Teoría 2: VXN Level + Día
vxn_day = [r for r in cot_day if r.get("vxn_level")==vxn_lv_today]
if len(vxn_day) >= 3:
    sv = calc_stats(vxn_day)
    theories.append({
        "id": "vxn_dow",
        "name": f"VXN {vxn_lv_today} en {DOW_ES.get(dow_today,'?')}",
        "description": f"{DOW_ES.get(dow_today,'?')} con volatilidad {vxn_lv_today}",
        "n": sv["n"],
        "bull_pct": sv["bull_pct"],
        "bear_pct": sv["bear_pct"],
        "avg_range": sv["avg_range"],
        "top_pattern": sv["top_pattern"],
        "conclusion": f"Con VXN {vxn_lv_today} en {DOW_ES.get(dow_today,'?')}: {sv['bull_pct']}% bull, rango {sv['avg_range']} pts",
    })

# Teoría 3: COT Zone
cot_zone = "BULLISH" if cot_index >= 60 else ("NEUTRAL" if cot_index >= 40 else "BEARISH")
cot_similar = [r for r in cot_day if abs((r.get("cot_index") or 50) - cot_index) <= 20]
if len(cot_similar) >= 3:
    sc = calc_stats(cot_similar)
    theories.append({
        "id": "cot_zone",
        "name": f"COT {cot_zone} ({round(cot_index-20)}-{round(cot_index+20)}/100)",
        "description": f"{DOW_ES.get(dow_today,'?')} con COT similar al actual",
        "n": sc["n"],
        "bull_pct": sc["bull_pct"],
        "bear_pct": sc["bear_pct"],
        "avg_range": sc["avg_range"],
        "top_pattern": sc["top_pattern"],
        "conclusion": f"COT ≈ {round(cot_index)}/100 en {DOW_ES.get(dow_today,'?')}: {sc['bull_pct']}% bull",
    })

# Teoría 4: Triple alineación (COT + VXN + GEX todos confirman)
if ai_score >= 65:
    aligned = [r for r in similar if r.get("cot_index",50) >= 60]
elif ai_score <= 35:
    aligned = [r for r in similar if r.get("cot_index",50) <= 40]
else:
    aligned = similar
if len(aligned) >= 3:
    sa = calc_stats(aligned)
    theories.append({
        "id": "triple_align",
        "name": f"Setup Confluencia (AI={ai_score}/100)",
        "description": "Días donde COT + VXN + AI apuntan en la misma dirección",
        "n": sa["n"],
        "bull_pct": sa["bull_pct"],
        "bear_pct": sa["bear_pct"],
        "avg_range": sa["avg_range"],
        "top_pattern": sa["top_pattern"],
        "conclusion": f"Cuando todos los indicadores apuntan igual: {sa['bull_pct']}% bull | Confianza alta",
    })

# ── PREDICCIÓN FINAL ────────────────────────────────────────────────────
bull_signals = 0
bear_signals = 0
confidence   = 0

for t in theories:
    weight = {"dow_base":1, "vxn_dow":2, "cot_zone":2, "triple_align":3}.get(t["id"],1)
    if t["bull_pct"] > 55:
        bull_signals += weight
    elif t["bear_pct"] > 55:
        bear_signals += weight
    confidence += weight

pred_dir   = "BULLISH" if bull_signals > bear_signals else ("BEARISH" if bear_signals > bull_signals else "NEUTRAL")
pred_score = round(max(bull_signals, bear_signals) / max(confidence, 1) * 100, 1) if confidence else 50

print(f"\n🎯 Predicción: {pred_dir} ({pred_score}% confianza)")

# ── GUARDAR OUTPUT ─────────────────────────────────────────────────────
output = {
    "generated": datetime.now().isoformat(),
    "date": today_str,
    "today": TODAY,
    "match_level": match_level,
    "similar": stats,
    "theories": theories,
    "prediction": {
        "direction": pred_dir,
        "confidence": pred_score,
        "bull_signals": bull_signals,
        "bear_signals": bear_signals,
        "basis": f"{n} días similares {'(criterio estricto)' if match_level=='strict' else '(criterio amplio)'}",
    },
    "db_stats": db.get("stats_by_dow", {}),
}

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ {OUT_FILE} guardado")
print(f"   Predicción: {pred_dir} | Confianza: {pred_score}%")
print(f"   Teorías activas: {len(theories)}")

# ── GEMINI AI BRIEF ────────────────────────────────────────────────────
print("\n🤖 Generando brief con Gemini AI...")
ai_brief     = None
ai_brief_ts  = None

try:
    # Cargar API key desde .env o variable de entorno
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        try:
            with open(".env", encoding="utf-8") as ef:
                for line in ef:
                    if line.startswith("GEMINI_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip()
                        break
        except: pass

    if not api_key:
        print("   ⚠  GEMINI_API_KEY no encontrada en .env. Saltando brief IA.")
    else:
        try:
            from google import genai as google_genai
            client = google_genai.Client(api_key=api_key)

            # Construir contexto rico para el prompt
            top_cases_text = ""
            for i, c in enumerate(stats.get("cases", [])[:5], 1):
                sign = "▲" if c["direction"]=="BULLISH" else "▼"
                top_cases_text += f"  {i}. {c['date']} → {sign} {c['direction']} | Rango {c.get('ny_range',0):.0f} pts | {c.get('pattern','?')}\n"

            prompt = f"""Eres un analista institucional experto en NQ Futures (E-Mini Nasdaq 100 en CME).
Analiza las condiciones del mercado para el dia de trading: {today_str} ({DOW_ES.get(dow_today,'?')}).

CONDICIONES ACTUALES:
- Dia: {DOW_ES.get(dow_today,'?')} (semana {semana_ciclo(today)})
- COT Index: {cot_index}/100 Senal: {cot_signal}
- VXN: {round(vxn_val,2)} Nivel: {vxn_lv_today}
- DIX dark pool: {round(dix_raw,1)}%
- Score IA sistema: {ai_score}/100 ({ai_label})

ESTADISTICA HISTORICA:
- Dias similares: {n} casos ({match_level})
- Resultado: {stats.get('bull_pct',0)}% BULLISH | {stats.get('bear_pct',0)}% BEARISH
- Rango promedio: {stats.get('avg_range',0)} puntos NQ
- Patron frecuente: {stats.get('top_pattern','?')}
- Ultimos casos:
{top_cases_text}

PREDICCION: {pred_dir} con {pred_score}% confianza

Escribe en ESPANOL un analisis profesional con 3 secciones:

**CONFIGURACION INSTITUCIONAL**
(2-3 oraciones sobre COT + VXN + DIX hoy)

**LO QUE DICE LA HISTORIA**
(2 oraciones sobre los {n} dias similares)

**PUNTOS CLAVE A VIGILAR**
(3 bullets concretos para la sesion NY)

Maximo 180 palabras. Directo y accionable."""

            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            ai_brief    = response.text.strip()
            ai_brief_ts = datetime.now().isoformat()
            print(f"   ✅ Brief Gemini generado ({len(ai_brief)} chars)")
            print(f"\n── BRIEF ──────────────────────────")
            print(ai_brief[:400] + ("..." if len(ai_brief) > 400 else ""))
            print(f"───────────────────────────────────")
        except ImportError:
            print("   ⚠  google-genai no instalado. Ejecuta: pip install google-genai")
        except Exception as e:
            print(f"   ⚠  Error Gemini: {e}")
        except Exception as e:
            print(f"   ⚠  Error Gemini: {e}")

except Exception as e:
    print(f"   ⚠  Error general Gemini: {e}")



# ── RE-GUARDAR con AI brief ────────────────────────────────────────────
output["ai_brief"]    = ai_brief
output["ai_brief_ts"] = ai_brief_ts

with open(OUT_FILE, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n🎯 Dashboard listo — {OUT_FILE} actualizado con IA")
