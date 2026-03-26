"""
AGENTE 17 — JOURNAL PAGE GENERATOR v2  (NQ Intelligence Engine)
════════════════════════════════════════════════════════════════
Genera journal_YYYYMMDD.html con:

  ① Gráfico de velas (lightweight-charts)
  ② Panel de señales de los 7 agentes
  ③ Tabla de entradas del día
  ④ Consejero Inteligente por trade:
       • Score 0-100 + Grade A+/A/B/C/D
       ★ DANGER BADGE  — independiente del resultado (WIN puede ser EXTREME)
       ★ Mejor alternativa siempre visible
  ⑤ Shadow Projection — overlay semi-transparente del movimiento predicho
       • Datos desde deepchart_projection_YYYYMMDD.json
       • Banda de incertidumbre (high/low) + línea central (mid)
       • Key levels de DeepChart como líneas horizontales
"""

import os
import json
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── Loaders ──────────────────────────────────────────────────────────────────

def load(filename: str) -> dict:
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

def load_trades(date_str: str) -> list:
    date_safe  = date_str.replace("-", "")
    trade_file = os.path.join(BASE_DIR, f"agent17_trades_{date_safe}.json")

    if os.path.exists(trade_file):
        try:
            with open(trade_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return data.get("trades", [])
        except Exception:
            return []

    # Crear template
    template = {
        "_instructions": (
            "direction: LONG|SHORT  |  outcome: WIN|LOSS|BE  |  "
            "entry_type: Silver Bullet|FVG|BOS|OB|CISD etc."
        ),
        "trades": [{
            "time": "09:45", "session": "NY AM",
            "direction": "LONG", "entry_type": "Silver Bullet",
            "entry_price": 0, "sl": 0, "tp": 0,
            "rr_planned": 2.0, "rr_achieved": 0,
            "outcome": "WIN", "notes": ""
        }]
    }
    with open(trade_file, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"  📄 Template creado: {trade_file}")
    return []

def load_deepchart(date_str: str) -> dict:
    date_safe = date_str.replace("-", "")
    path = os.path.join(BASE_DIR, f"deepchart_projection_{date_safe}.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

# ── Risk / Danger assessment ──────────────────────────────────────────────────

DANGER_LEVELS = {
    "LOW":     {"label": "LOW RISK",     "emoji": "🟢", "color": "#22c55e",
                "bg": "rgba(34,197,94,.14)", "bdr": "rgba(34,197,94,.35)"},
    "MEDIUM":  {"label": "MEDIUM RISK",  "emoji": "🟡", "color": "#f59e0b",
                "bg": "rgba(245,158,11,.14)", "bdr": "rgba(245,158,11,.35)"},
    "HIGH":    {"label": "HIGH RISK",    "emoji": "🟠", "color": "#f97316",
                "bg": "rgba(249,115,22,.14)", "bdr": "rgba(249,115,22,.35)"},
    "EXTREME": {"label": "EXTREME RISK", "emoji": "🔴", "color": "#ff0055",
                "bg": "rgba(255,0,85,.14)",   "bdr": "rgba(255,0,85,.4)"},
}

def assess_danger(trade: dict, journal_entry: dict, signals: dict) -> tuple:
    """
    Evalúa qué tan PELIGROSA fue la entrada, independientemente del resultado.
    Devuelve (level_key, reasons_list).
    """
    danger_pts = 0
    reasons = []

    bias_lbl  = journal_entry.get("bias_label", "NEUTRAL").upper()
    vxn       = float(journal_entry.get("vxn") or 0)
    direction = trade.get("direction", "").upper()
    entry_t   = trade.get("entry_type", "")
    rr_pl     = float(trade.get("rr_planned") or 2)
    session   = trade.get("session", "").upper()

    # 1 — Contra el bias
    bias_dir  = 1 if "BULL" in bias_lbl else (-1 if "BEAR" in bias_lbl else 0)
    trade_dir = 1 if direction == "LONG" else (-1 if direction == "SHORT" else 0)
    if bias_dir != 0 and bias_dir != trade_dir:
        danger_pts += 30
        reasons.append("⚠️ Entrada contra el bias dominante del motor.")

    # 2 — VXN elevado
    if vxn > 30:
        danger_pts += 20
        reasons.append(f"⚠️ VXN extremo ({vxn:.1f}) — mercado muy volátil.")
    elif vxn > 25:
        danger_pts += 10
        reasons.append(f"⚠️ VXN elevado ({vxn:.1f}) — volatilidad aumentada.")

    # 3 — Sin confluencia de SMC
    smc_dir = signals.get("SMC", {}).get("dir", 0)
    if smc_dir != 0 and smc_dir != trade_dir:
        danger_pts += 15
        reasons.append("⚠️ Estructura SMC contraria a tu dirección.")

    # 4 — R:R muy bajo
    if rr_pl < 1.5:
        danger_pts += 15
        reasons.append(f"⚠️ R:R planificado muy bajo ({rr_pl:.1f}R < 1.5R).")

    # 5 — Sesión de baja probabilidad sin Silver Bullet
    if "PM" in session and "SILVER" not in entry_t.upper():
        danger_pts += 10
        reasons.append("⚠️ Sesión PM sin patrón Silver Bullet confirmado.")

    # 6 — Order flow contrario
    of_sig = signals.get("ORDERFLOW", {}).get("raw", "")
    if of_sig and direction not in of_sig.upper() and "NEUTRAL" not in of_sig.upper():
        danger_pts += 15
        reasons.append(f"⚠️ Order Flow ({of_sig}) no confirma la entrada.")

    # 7 — COT contrario
    cot_sig = journal_entry.get("cot_signal", "NEUTRAL").upper()
    cot_dir = 1 if "BULL" in cot_sig else (-1 if "BEAR" in cot_sig else 0)
    if cot_dir != 0 and cot_dir != trade_dir:
        danger_pts += 10
        reasons.append(f"⚠️ COT institucional ({cot_sig}) apunta diferente.")

    if not reasons:
        reasons.append("✅ Ningún factor de riesgo mayor detectado.")

    if danger_pts >= 45:   level = "EXTREME"
    elif danger_pts >= 28: level = "HIGH"
    elif danger_pts >= 12: level = "MEDIUM"
    else:                  level = "LOW"

    return level, reasons

def score_trade(trade: dict, pending: dict, journal_entry: dict) -> dict:
    signals   = pending.get("agent_signals", {})
    bias_lbl  = journal_entry.get("bias_label", "NEUTRAL").upper()
    cot_sig   = journal_entry.get("cot_signal", "NEUTRAL").upper()
    vxn       = float(journal_entry.get("vxn") or 0)
    direction = trade.get("direction", "").upper()
    outcome   = trade.get("outcome", "").upper()
    entry_type= trade.get("entry_type", "")
    rr        = float(trade.get("rr_achieved") or 0)
    planned_rr= float(trade.get("rr_planned") or 2)

    score   = 50
    reasons = []
    alt_entry = None

    bias_dir  = 1 if "BULL" in bias_lbl else (-1 if "BEAR" in bias_lbl else 0)
    trade_dir = 1 if direction == "LONG" else (-1 if direction == "SHORT" else 0)

    if bias_dir == trade_dir:
        score += 15
        reasons.append("✅ Dirección alineada con el bias del motor.")
    elif bias_dir == 0:
        score -= 5
        reasons.append("⚠️ Bias neutral — mayor incertidumbre en la entrada.")
    else:
        score -= 20
        reasons.append("❌ Fuiste en contra del bias del motor de agentes.")
        alt_dir = "LONG" if bias_dir == 1 else "SHORT"
        alt_entry = f"Una entrada {alt_dir} (a favor del bias {bias_lbl}) tenía mejor probabilidad estructural."

    cot_dir = 1 if "BULL" in cot_sig else (-1 if "BEAR" in cot_sig else 0)
    if cot_dir == trade_dir:
        score += 10
        reasons.append("✅ Dirección alineada con señal COT.")
    elif cot_dir != 0 and cot_dir != trade_dir:
        score -= 10
        reasons.append(f"⚠️ COT indica {cot_sig} — contrario a tu dirección.")

    of_sig = signals.get("ORDERFLOW", {}).get("raw", "")
    if of_sig and direction in of_sig.upper():
        score += 8
        reasons.append(f"✅ Order Flow confirma tu dirección ({of_sig}).")
    elif of_sig and direction not in of_sig.upper() and "NEUTRAL" not in of_sig.upper():
        score -= 8
        reasons.append(f"⚠️ Order Flow no confirma ({of_sig}).")

    sb_sig = signals.get("SILVER_BULLET", {}).get("raw", "")
    if "ACTIVE" in sb_sig.upper() and "SILVER" in entry_type.upper():
        score += 12
        reasons.append("✅ Silver Bullet tomado dentro de su ventana activa.")
    elif "ACTIVE" in sb_sig.upper() and "SILVER" not in entry_type.upper():
        alt_entry = alt_entry or "Silver Bullet activo — esa ventana ofrecía mejor confluencia ICT."
        reasons.append("💡 Silver Bullet estaba activo pero no lo usaste como tipo de entrada.")
    elif "UPCOMING" in sb_sig.upper():
        reasons.append("💡 Silver Bullet próximo — considera esperar esa ventana.")

    if vxn > 28:
        score -= 5
        reasons.append(f"⚠️ VXN elevado ({vxn:.1f}) — stops más amplios necesarios.")
    elif vxn < 18:
        score += 5
        reasons.append(f"✅ VXN bajo ({vxn:.1f}) — movimientos más predecibles.")

    if outcome == "WIN" and rr >= planned_rr:
        score += 10
        reasons.append(f"✅ R:R logrado ({rr:.1f}R) ≥ planificado ({planned_rr:.1f}R).")
    elif outcome == "WIN" and rr < planned_rr:
        score += 4
        reasons.append(f"⚠️ Ganaste pero saliste antes del target ({rr:.1f}R < {planned_rr:.1f}R).")
        alt_entry = alt_entry or "Mantener hasta el target planificado habría dado mejor resultado."
    elif outcome == "LOSS":
        score -= 15
        reasons.append("❌ Trade resultó en pérdida.")
    elif outcome == "BE":
        score -= 3
        reasons.append("📊 Trade cerrado en break-even.")

    smc_dir = signals.get("SMC", {}).get("dir", 0)
    if smc_dir == trade_dir:
        score += 8
        reasons.append("✅ SMC confirma estructura en tu dirección.")
    elif smc_dir != 0 and smc_dir != trade_dir:
        score -= 8
        reasons.append("⚠️ Estructura SMC contraria a tu entrada.")

    score = max(0, min(100, score))
    if score >= 85:   grade = "A+"
    elif score >= 72: grade = "A"
    elif score >= 58: grade = "B"
    elif score >= 42: grade = "C"
    else:             grade = "D"

    verdicts = {
        "A+": "Ejecución óptima — sigue así.",
        "A":  "Buena entrada con confluencias sólidas.",
        "B":  "Entrada aceptable — hay mejoras posibles.",
        "C":  "Entrada débil — pocas confluencias.",
        "D":  "Entrada contra las señales del motor.",
    }

    if not alt_entry:
        bias_w = "LONG" if bias_dir == 1 else ("SHORT" if bias_dir == -1 else None)
        sb_w   = "Silver Bullet" if ("UPCOMING" in sb_sig.upper() or "ACTIVE" in sb_sig.upper()) else None
        if grade in ("A+", "A"):
            alt_entry = "No había alternativa claramente superior — entrada bien calibrada."
        elif sb_w and bias_w:
            alt_entry = f"Esperar ventana {sb_w} en dirección {bias_w} alineada con bias {bias_lbl}."
        elif bias_w:
            alt_entry = f"Una entrada {bias_w} con BOS/FVG confirmado en dirección del bias {bias_lbl}."
        else:
            alt_entry = "Esperar mayor confluencia — sesión sin señales definidas del motor."

    # Danger assessment (independiente del resultado)
    danger_level, danger_reasons = assess_danger(trade, journal_entry, signals)

    return {
        "score":         score,
        "grade":         grade,
        "verdict":       verdicts[grade],
        "reasons":       reasons,
        "best_alt":      alt_entry,
        "danger_level":  danger_level,
        "danger_reasons": danger_reasons,
    }

# ── Shadow projection JS builder ──────────────────────────────────────────────

def _hhmm_to_unix(date_str: str, hhmm: str) -> int:
    """
    Convierte 'HH:MM' + fecha ISO ('YYYY-MM-DD') a timestamp UNIX en segundos.
    Si ya es un número lo devuelve tal cual.
    """
    if isinstance(hhmm, (int, float)):
        return int(hhmm)
    try:
        dt = datetime.datetime.strptime(f"{date_str}T{hhmm}:00", "%Y-%m-%dT%H:%M:%S")
        # Asumimos hora local (Eastern ya asumido en el JSON); sin tzinfo → epoch local
        import calendar
        return calendar.timegm(dt.timetuple())  # UTC epoch; ajusta si necesitas local
    except Exception:
        return 0


def build_shadow_js(dc: dict, date_str: str = "") -> str:
    """Genera el bloque JS para inicializar el gráfico con el shadow overlay."""
    if not dc or "projection" not in dc:
        return ""

    proj   = dc["projection"]
    path   = proj.get("path", [])
    label  = proj.get("label", "Proyección DeepChart")
    conf   = proj.get("confidence_pct", 70)
    levels = dc.get("key_levels", [])

    def to_ts(p_time):
        return _hhmm_to_unix(date_str, p_time) if date_str else p_time

    mid_data  = json.dumps([{"time": to_ts(p["time"]), "value": p["mid"]}  for p in path])
    high_data = json.dumps([{"time": to_ts(p["time"]), "value": p["high"]} for p in path])
    low_data  = json.dumps([{"time": to_ts(p["time"]), "value": p["low"]}  for p in path])

    levels_js = ""
    for lv in levels:
        color = lv.get("color", "#f59e0b")
        price = lv.get("price", 0)
        lbl   = lv.get("label", "")
        levels_js += f"""
    chart.addLineSeries({{
        color: '{color}',
        lineWidth: 1,
        lineStyle: 2,  // dashed
        priceLineVisible: false,
        lastValueVisible: true,
        title: '{lbl}',
    }}).setData([
        {{time: shadowData[0].time, value: {price}}},
        {{time: shadowData[shadowData.length-1].time, value: {price}}},
    ]);"""

    return f"""
    /* ── DeepChart Shadow Projection ─────────────────────────── */
    const shadowData      = {mid_data};
    const shadowHigh      = {high_data};
    const shadowLow       = {low_data};

    // Banda de incertidumbre — high
    const shadowHighSeries = chart.addLineSeries({{
        color: 'rgba(124,58,237,0.18)',
        lineWidth: 1,
        lineStyle: 0,
        priceLineVisible: false,
        lastValueVisible: false,
        title: '',
    }});
    shadowHighSeries.setData(shadowHigh);

    // Banda de incertidumbre — low (con fill visual via áreas)
    const shadowLowSeries = chart.addLineSeries({{
        color: 'rgba(124,58,237,0.18)',
        lineWidth: 1,
        lineStyle: 0,
        priceLineVisible: false,
        lastValueVisible: false,
        title: '',
    }});
    shadowLowSeries.setData(shadowLow);

    // Línea central mid — gradiente morado
    const shadowMidSeries = chart.addLineSeries({{
        color: 'rgba(167,139,250,0.85)',
        lineWidth: 2,
        lineStyle: 1,   // dotted
        priceLineVisible: false,
        lastValueVisible: true,
        title: '📡 {label} ({conf}%)',
    }});
    shadowMidSeries.setData(shadowData);

    // Key levels de DeepChart
    {levels_js}

    // Badge de confianza en el chart
    const shadowBadge = document.createElement('div');
    shadowBadge.style.cssText = `
        position:absolute;top:12px;right:14px;z-index:10;
        background:rgba(124,58,237,.22);border:1px solid rgba(167,139,250,.45);
        color:#c4b5fd;font-size:11px;font-weight:700;padding:5px 12px;
        border-radius:8px;letter-spacing:.5px;font-family:'JetBrains Mono',monospace;
        backdrop-filter:blur(4px);
    `;
    shadowBadge.textContent = '📡 DeepChart Shadow · {conf}% conf';
    document.getElementById('chart-wrap').style.position = 'relative';
    document.getElementById('chart-wrap').appendChild(shadowBadge);
"""

# ── HTML builder ──────────────────────────────────────────────────────────────

def build_html(journal_entry: dict, pending: dict, trades: list, dc: dict) -> str:
    date_str   = journal_entry.get("date", "")
    display    = journal_entry.get("display_date", date_str)
    weekday    = journal_entry.get("weekday", "")
    nq_price   = journal_entry.get("nq_price") or 0
    nq_chg     = journal_entry.get("nq_change_pct") or 0
    bias_lbl   = journal_entry.get("bias_label", "NEUTRAL")
    bias_score = journal_entry.get("bias_score", 50)
    cot_sig    = journal_entry.get("cot_signal", "NEUTRAL")
    cot_net    = journal_entry.get("cot_net", 0)
    vxn        = journal_entry.get("vxn") or 0
    session_tag= journal_entry.get("session_tag", "NY AM")
    obs        = journal_entry.get("key_observations", [])
    summary    = journal_entry.get("summary", "")
    signals    = pending.get("agent_signals", {})
    date_safe  = date_str.replace("-", "")

    bias_col = "#00ff80" if "BULL" in bias_lbl.upper() else ("#ff0055" if "BEAR" in bias_lbl.upper() else "#f59e0b")
    chg_col  = "#00ff80" if nq_chg >= 0 else "#ff0055"
    chg_arr  = "▲" if nq_chg >= 0 else "▼"

    # ── Helper: score badge ──────────────────────────────
    def score_bg(s: int) -> tuple:
        if s >= 72: return ("rgba(0,255,128,.15)","rgba(0,255,128,.4)","#6ee7b7")
        if s >= 50: return ("rgba(245,158,11,.1)","rgba(245,158,11,.3)","#fcd34d")
        return ("rgba(255,0,85,.14)","rgba(255,0,85,.4)","#fca5a5")

    # ── Signals panel ────────────────────────────────────
    SIG_ICONS = {"COT":"📊","VOLATILITY":"🌊","SMC":"🏗️","PROBABILITY":"🎲",
                 "SENTIMENT":"🧠","SILVER_BULLET":"🎯","ORDERFLOW":"💧"}
    SIG_NAMES = {"COT":"COT","VOLATILITY":"Volatilidad","SMC":"SMC",
                 "PROBABILITY":"Probabilidad","SENTIMENT":"Sentimiento",
                 "SILVER_BULLET":"Silver Bullet","ORDERFLOW":"Order Flow"}

    def sig_col(d: int) -> tuple:
        if d == 1:  return ("rgba(0,255,128,.15)","rgba(0,255,128,.4)","#6ee7b7")
        if d == -1: return ("rgba(255,0,85,.14)","rgba(255,0,85,.4)","#fca5a5")
        return ("rgba(245,158,11,.1)","rgba(245,158,11,.3)","#fcd34d")

    sigs_html = ""
    for key, meta in SIG_NAMES.items():
        sig = signals.get(key, {})
        d   = sig.get("dir", 0)
        raw = sig.get("raw", "—")
        bg, bdr, tc = sig_col(d)
        sigs_html += f"""
        <div style="background:{bg};border:1px solid {bdr};border-radius:10px;padding:10px 14px;display:flex;flex-direction:column;gap:4px;">
          <div style="font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">{SIG_ICONS.get(key,'•')} {meta}</div>
          <div style="font-size:12px;font-weight:700;color:{tc};font-family:'JetBrains Mono',monospace;line-height:1.3;">{raw}</div>
        </div>"""

    # ── Observations ─────────────────────────────────────
    obs_html = "".join(
        f'<li style="padding:6px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:12px;line-height:1.6;color:#a0aec0;">{o}</li>'
        for o in obs
    )

    # ── Shadow JS ─────────────────────────────────────────
    has_shadow  = bool(dc and dc.get("projection", {}).get("path"))
    shadow_js   = build_shadow_js(dc, date_str) if has_shadow else ""
    shadow_note = ""
    if has_shadow:
        conf  = dc["projection"].get("confidence_pct", 0)
        lbl   = dc["projection"].get("label", "DeepChart")
        shadow_note = f"""
        <div style="background:rgba(124,58,237,.1);border:1px solid rgba(167,139,250,.25);border-radius:10px;padding:10px 16px;margin-top:10px;display:flex;align-items:center;gap:10px;">
          <span style="font-size:18px;">📡</span>
          <div>
            <div style="font-size:11px;font-weight:700;color:#a78bfa;letter-spacing:.5px;">SHADOW DEEPCHART · {conf}% confianza</div>
            <div style="font-size:12px;color:#c4b5fd;">{lbl}</div>
          </div>
        </div>"""
    else:
        shadow_note = """
        <div style="background:rgba(255,255,255,.03);border:1px dashed rgba(255,255,255,.08);border-radius:10px;padding:10px 16px;margin-top:10px;font-size:12px;color:#64748b;">
          📡 Shadow DeepChart no disponible para esta sesión —
          crea <code style="color:#a78bfa;">deepchart_projection_""" + date_safe + """.json</code>
        </div>"""

    # ── Trades section ────────────────────────────────────
    trades_html  = ""
    advisor_html = ""
    sessions_verdict = ""

    if trades:
        trades_html = """
        <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:12px;">
          <thead>
            <tr style="border-bottom:1px solid rgba(255,255,255,.08);">
              <th style="padding:8px 10px;text-align:left;color:#64748b;font-size:10px;">#</th>
              <th style="padding:8px 10px;text-align:left;color:#64748b;font-size:10px;">HORA</th>
              <th style="padding:8px 10px;text-align:left;color:#64748b;font-size:10px;">DIR</th>
              <th style="padding:8px 10px;text-align:left;color:#64748b;font-size:10px;">TIPO</th>
              <th style="padding:8px 10px;text-align:right;color:#64748b;font-size:10px;">ENTRY</th>
              <th style="padding:8px 10px;text-align:right;color:#64748b;font-size:10px;">SL</th>
              <th style="padding:8px 10px;text-align:right;color:#64748b;font-size:10px;">TP</th>
              <th style="padding:8px 10px;text-align:right;color:#64748b;font-size:10px;">R:R</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-size:10px;">RESULT</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-size:10px;">SCORE</th>
              <th style="padding:8px 10px;text-align:center;color:#64748b;font-size:10px;">RIESGO</th>
            </tr>
          </thead><tbody>"""

        advisor_html = """<div style="margin-top:24px;">
          <div style="font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">
            🤖 Consejero Inteligente — Análisis de tus Entradas
          </div>"""

        total_score = 0
        for i, trade in enumerate(trades):
            analysis  = score_trade(trade, pending, journal_entry)
            total_score += analysis["score"]

            direction = trade.get("direction", "—")
            outcome   = trade.get("outcome", "—").upper()
            entry_type= trade.get("entry_type", "—")
            entry_p   = trade.get("entry_price", "—")
            sl_p      = trade.get("sl", "—")
            tp_p      = trade.get("tp", "—")
            rr_ach    = trade.get("rr_achieved", "—")
            notes     = trade.get("notes", "")
            time_str  = trade.get("time", "—")
            session   = trade.get("session", "—")

            dir_col = "#6ee7b7" if direction == "LONG" else "#fca5a5"
            dir_bg  = "rgba(0,255,128,.12)" if direction == "LONG" else "rgba(255,0,85,.12)"
            dir_bdr = "rgba(0,255,128,.35)" if direction == "LONG" else "rgba(255,0,85,.35)"

            out_map = {
                "WIN":  ("#6ee7b7","rgba(0,255,128,.15)","rgba(0,255,128,.4)"),
                "LOSS": ("#fca5a5","rgba(255,0,85,.15)","rgba(255,0,85,.4)"),
                "BE":   ("#fcd34d","rgba(245,158,11,.1)","rgba(245,158,11,.3)"),
            }
            out_tc, out_bg, out_bd = out_map.get(outcome, ("#a0aec0","rgba(255,255,255,.05)","rgba(255,255,255,.1)"))

            sc = analysis["score"]
            sc_bg, sc_bdr, sc_tc = score_bg(sc)
            gd = analysis["grade"]
            gd_col = {"A+":"#00ff80","A":"#6ee7b7","B":"#fcd34d","C":"#f59e0b","D":"#ff0055"}.get(gd,"#a0aec0")

            # ── Danger badge ─────────────────────────────
            dl  = analysis["danger_level"]
            dmt = DANGER_LEVELS[dl]

            trades_html += f"""
              <tr style="border-bottom:1px solid rgba(255,255,255,.04);"
                  onmouseover="this.style.background='rgba(255,255,255,.03)'"
                  onmouseout="this.style.background='transparent'">
                <td style="padding:10px 10px;color:#64748b;font-family:'JetBrains Mono',monospace;">{i+1}</td>
                <td style="padding:10px 10px;font-family:'JetBrains Mono',monospace;color:#67e8f9;">{time_str}</td>
                <td style="padding:10px 10px;">
                  <span style="background:{dir_bg};border:1px solid {dir_bdr};color:{dir_col};font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;">{direction}</span>
                </td>
                <td style="padding:10px 10px;color:#c8d0e0;font-size:11px;">{entry_type}</td>
                <td style="padding:10px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;">{entry_p}</td>
                <td style="padding:10px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:#fca5a5;">{sl_p}</td>
                <td style="padding:10px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:#6ee7b7;">{tp_p}</td>
                <td style="padding:10px 10px;text-align:right;font-family:'JetBrains Mono',monospace;font-size:12px;color:#67e8f9;">{rr_ach}R</td>
                <td style="padding:10px 10px;text-align:center;">
                  <span style="background:{out_bg};border:1px solid {out_bd};color:{out_tc};font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;">{outcome}</span>
                </td>
                <td style="padding:10px 10px;text-align:center;">
                  <span style="background:{sc_bg};border:1px solid {sc_bdr};color:{sc_tc};font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;padding:2px 10px;border-radius:8px;">{sc}/100</span>
                </td>
                <td style="padding:10px 10px;text-align:center;">
                  <span style="background:{dmt['bg']};border:1px solid {dmt['bdr']};color:{dmt['color']};font-size:10px;font-weight:700;padding:2px 8px;border-radius:8px;white-space:nowrap;">{dmt['emoji']} {dl}</span>
                </td>
              </tr>"""

            # ── Advisor card ─────────────────────────────
            reasons_li  = "".join(f'<li style="font-size:12px;line-height:1.7;color:#a0aec0;">{r}</li>' for r in analysis["reasons"])
            danger_li   = "".join(f'<li style="font-size:12px;line-height:1.7;color:{dmt["color"]};">{r}</li>' for r in analysis["danger_reasons"])

            # Special warning box if dangerous but won
            danger_won_box = ""
            if outcome == "WIN" and dl in ("HIGH","EXTREME"):
                danger_won_box = f"""
                <div style="background:rgba(249,115,22,.1);border:1px solid rgba(249,115,22,.3);border-radius:10px;padding:12px 16px;margin-bottom:10px;">
                  <div style="font-size:11px;font-weight:700;color:#fb923c;letter-spacing:.5px;margin-bottom:5px;">
                    {dmt['emoji']} GANASTE — PERO FUE UNA ENTRADA PELIGROSA
                  </div>
                  <div style="font-size:12px;color:#fed7aa;line-height:1.6;">
                    El resultado positivo no valida la entrada. Este tipo de trades erosiona el edge a largo plazo.
                    Una buena ejecución requiere confluencia, no solo suerte.
                  </div>
                </div>"""

            advisor_html += f"""
          <div style="background:#06060a;border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:18px 20px;margin-bottom:12px;position:relative;overflow:hidden;">
            <div style="position:absolute;left:0;top:0;bottom:0;width:3px;background:{gd_col};"></div>

            <!-- Header -->
            <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:14px;">
              <div>
                <span style="font-size:11px;color:#64748b;font-family:'JetBrains Mono',monospace;">TRADE #{i+1} · {time_str} · {session}</span>
                <div style="font-size:15px;font-weight:800;color:#fff;margin-top:3px;">{direction} {entry_type}</div>
              </div>
              <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <!-- Score -->
                <div style="text-align:center;">
                  <div style="font-size:26px;font-weight:900;color:{gd_col};font-family:'JetBrains Mono',monospace;line-height:1;">{gd}</div>
                  <div style="font-size:9px;color:#64748b;letter-spacing:1px;">GRADE</div>
                </div>
                <div style="text-align:center;">
                  <div style="font-size:20px;font-weight:900;color:#fff;font-family:'JetBrains Mono',monospace;line-height:1;">{sc}<span style="font-size:12px;color:#64748b;">/100</span></div>
                  <div style="font-size:9px;color:#64748b;letter-spacing:1px;">SCORE</div>
                </div>
                <!-- Danger badge grande -->
                <div style="background:{dmt['bg']};border:1px solid {dmt['bdr']};border-radius:10px;padding:8px 14px;text-align:center;">
                  <div style="font-size:18px;line-height:1;">{dmt['emoji']}</div>
                  <div style="font-size:10px;font-weight:800;color:{dmt['color']};letter-spacing:.5px;margin-top:2px;">{dl}</div>
                  <div style="font-size:9px;color:#64748b;">RIESGO</div>
                </div>
              </div>
            </div>

            <!-- Verdict -->
            <div style="font-size:13px;font-weight:600;color:{gd_col};margin-bottom:10px;">👉 {analysis['verdict']}</div>

            <!-- Dangerous but won alert -->
            {danger_won_box}

            <!-- Quality reasons -->
            <div style="margin-bottom:12px;">
              <div style="font-size:10px;color:#64748b;font-weight:700;letter-spacing:.5px;margin-bottom:4px;">📊 ANÁLISIS DE CALIDAD</div>
              <ul style="list-style:none;padding:0;margin:0;">{reasons_li}</ul>
            </div>

            <!-- Danger reasons -->
            <div style="background:rgba(0,0,0,.25);border:1px solid rgba(255,255,255,.05);border-radius:8px;padding:10px 14px;margin-bottom:12px;">
              <div style="font-size:10px;color:{dmt['color']};font-weight:700;letter-spacing:.5px;margin-bottom:6px;">{dmt['emoji']} FACTORES DE RIESGO DE LA ENTRADA</div>
              <ul style="list-style:none;padding:0;margin:0;">{danger_li}</ul>
            </div>

            <!-- Best alt -->
            <div style="background:rgba(124,58,237,.1);border:1px solid rgba(124,58,237,.25);border-radius:10px;padding:12px 16px;">
              <div style="font-size:10px;font-weight:700;color:#a78bfa;letter-spacing:.5px;margin-bottom:5px;">🎯 MEJOR ALTERNATIVA</div>
              <div style="font-size:13px;color:#c4b5fd;line-height:1.6;">{analysis['best_alt']}</div>
            </div>

            {f'<div style="margin-top:10px;font-size:11px;color:#64748b;font-style:italic;">📝 {notes}</div>' if notes else ""}
          </div>"""

        trades_html += "</tbody></table></div>"
        advisor_html += "</div>"

        # Session overall verdict
        avg_sc = total_score / len(trades)
        sc_bg, sc_bdr, sc_tc = score_bg(int(avg_sc))
        sessions_verdict = f"""
        <div style="background:{sc_bg};border:1px solid {sc_bdr};border-radius:14px;padding:16px 20px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:16px;">
          <div>
            <div style="font-size:11px;color:{sc_tc};font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px;">⭐ Evaluación Global de la Sesión</div>
            <div style="font-size:20px;font-weight:900;color:#fff;">{len(trades)} trade{"s" if len(trades)!=1 else ""} · Score Promedio: <span style="color:{sc_tc};font-family:'JetBrains Mono',monospace;">{avg_sc:.0f}/100</span></div>
          </div>
          <div style="font-size:12px;color:#a0aec0;max-width:360px;line-height:1.6;">
            El consejero analizó calidad Y peligrosidad de cada entrada, independientemente del resultado.
          </div>
        </div>"""
    else:
        trades_html = f"""
        <div style="background:rgba(255,255,255,.03);border:1px dashed rgba(255,255,255,.08);border-radius:12px;padding:30px;text-align:center;color:#64748b;font-size:13px;">
          📭 Sin entradas registradas.<br>
          <span style="font-size:11px;margin-top:6px;display:block;">Agrega tus trades en <code style="color:#a78bfa;">agent17_trades_{date_safe}.json</code></span>
        </div>"""

    # Chart note — usa timestamps UNIX (segundos) requeridos por lightweight-charts v4
    chart_data_note = f"""
    // Placeholder candles — reemplaza con datos reales de NQ
    const dummyCandles = [];
    const base = {nq_price or 21480};
    const t0 = new Date('{date_str}T09:30:00Z');  // UTC noon-ish; ajusta TZ si necesario
    for(let i=0;i<78;i++){{
        const t = new Date(t0.getTime() + i*5*60000);
        const unixSec = Math.floor(t.getTime() / 1000);  // UNIX epoch en segundos
        const o = base + (Math.random()-0.495)*8*(i+1)*0.12;
        const c = o + (Math.random()-0.47)*12;
        const h = Math.max(o,c) + Math.random()*6;
        const l = Math.min(o,c) - Math.random()*6;
        dummyCandles.push({{time:unixSec,open:+o.toFixed(2),high:+h.toFixed(2),low:+l.toFixed(2),close:+c.toFixed(2)}});
    }}
    candleSeries.setData(dummyCandles);
    chart.timeScale().fitContent();
    """

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NQ Journal — {weekday} {display}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
  <script src="https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#000;color:#c8d0e0;font-family:'Inter',sans-serif;min-height:100vh}}
    .top-bar{{background:#000;border-bottom:1px solid rgba(0,255,128,.08);padding:14px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}}
    .logo{{background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;letter-spacing:1px;}}
    .real-badge{{background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.5);color:#6ee7b7;font-size:11px;font-weight:700;padding:4px 12px;border-radius:6px;letter-spacing:1px;}}
    .back-btn{{background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.35);color:#a78bfa;font-size:13px;font-weight:600;padding:7px 16px;border-radius:8px;cursor:pointer;text-decoration:none;transition:all .2s;}}
    .back-btn:hover{{background:rgba(124,58,237,.28)}}
    .page{{max-width:1400px;margin:0 auto;padding:20px 18px}}
    .panel{{background:#060608;border:1px solid #111118;border-radius:14px;padding:20px;margin-bottom:16px;}}
    .panel-title{{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:14px;}}
    .stats-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:10px;margin-bottom:16px;}}
    .stat-card{{background:#060608;border:1px solid #111118;border-radius:12px;padding:12px 14px;text-align:center;}}
    .stat-label{{font-size:9px;color:#64748b;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;}}
    .stat-value{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700;}}
    #chart-wrap{{background:#060608;border:1px solid rgba(0,255,128,.15);border-radius:16px;overflow:hidden;margin-bottom:20px;position:relative;}}
    .chart-top{{padding:12px 20px;border-bottom:1px solid rgba(0,255,128,.08);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}}
    #chart{{width:100%;height:520px;}}
    .date-header{{background:linear-gradient(135deg,#0c0a1e,#130f2a);border:1px solid #111118;border-radius:16px;padding:18px 24px;margin-bottom:16px;position:relative;overflow:hidden;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;}}
    .date-header::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,#f59e0b,#00ff80,#06b6d4,#7c3aed);}}
    .foot{{text-align:center;padding:20px;color:#64748b;font-size:11px;}}
  </style>
</head>
<body>

<div class="top-bar">
  <div style="display:flex;align-items:center;gap:12px;">
    <div class="logo">NQ RADAR</div>
    <span style="color:#64748b;font-size:13px;font-family:'JetBrains Mono',monospace;">{date_str} · JOURNAL</span>
    <div class="real-badge">📓 DATOS REALES</div>
    {"<div style='background:rgba(124,58,237,.2);border:1px solid rgba(167,139,250,.45);color:#c4b5fd;font-size:11px;font-weight:700;padding:4px 12px;border-radius:6px;letter-spacing:1px;'>📡 DeepChart</div>" if has_shadow else ""}
  </div>
  <a href="index.html" class="back-btn">← Panel Principal</a>
</div>

<div class="page">

  <!-- DATE HEADER -->
  <div class="date-header">
    <div>
      <div style="font-size:20px;font-weight:900;margin-bottom:4px;">📅 {weekday} {display} — Journal NQ</div>
      <div style="color:#64748b;font-size:12px;">Análisis post-sesión · Motor de {len(signals)} agentes · Consejero con detector de peligro</div>
    </div>
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
      <span style="background:rgba(245,158,11,.15);border:1px solid rgba(245,158,11,.35);color:#fcd34d;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">{session_tag}</span>
      <span style="background:{'rgba(0,255,128,.15)' if 'BULL' in bias_lbl.upper() else 'rgba(255,0,85,.15)'};border:1px solid {'rgba(0,255,128,.4)' if 'BULL' in bias_lbl.upper() else 'rgba(255,0,85,.4)'};color:{bias_col};padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">{'↑' if 'BULL' in bias_lbl.upper() else ('↓' if 'BEAR' in bias_lbl.upper() else '↔')} {bias_lbl}</span>
    </div>
  </div>

  <!-- STATS -->
  <div class="stats-row">
    <div class="stat-card"><div class="stat-label">NQ Price</div><div class="stat-value" style="color:{chg_col};">{nq_price:,.1f}</div></div>
    <div class="stat-card"><div class="stat-label">Change</div><div class="stat-value" style="color:{chg_col};">{chg_arr} {abs(nq_chg):.2f}%</div></div>
    <div class="stat-card"><div class="stat-label">Bias Score</div><div class="stat-value" style="color:{bias_col};">{bias_score}/100</div></div>
    <div class="stat-card"><div class="stat-label">COT</div><div class="stat-value" style="color:{'#fca5a5' if 'BEAR' in cot_sig else '#6ee7b7'}">{cot_sig}</div></div>
    <div class="stat-card"><div class="stat-label">COT Net</div><div class="stat-value" style="font-size:12px;font-family:'JetBrains Mono',monospace;color:{'#fca5a5' if cot_net<0 else '#6ee7b7'}">{int(cot_net):+,}</div></div>
    <div class="stat-card"><div class="stat-label">VXN</div><div class="stat-value" style="color:{'#fca5a5' if vxn>28 else '#fcd34d' if vxn>20 else '#6ee7b7'}">{vxn:.2f}</div></div>
  </div>

  <!-- CHART + SHADOW -->
  <div id="chart-wrap">
    <div class="chart-top">
      <div>
        <span style="font-size:13px;font-weight:700;color:#fff;">NQ1! — 5m · {display}</span>
        <span style="font-size:11px;color:#64748b;margin-left:10px;">{session_tag}</span>
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        {f'<span style="font-size:11px;color:#c4b5fd;background:rgba(124,58,237,.12);border:1px solid rgba(167,139,250,.25);padding:3px 10px;border-radius:6px;">📡 Shadow DeepChart activo</span>' if has_shadow else ''}
        <span style="font-size:11px;color:#64748b;">Banda de incertidumbre · Proyección mid</span>
      </div>
    </div>
    <div id="chart"></div>
  </div>
  {shadow_note}

  <!-- AGENT SIGNALS -->
  <div class="panel">
    <div class="panel-title">📡 Señales del Motor — {date_str}</div>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;">
      {sigs_html}
    </div>
  </div>

  <!-- OBSERVATIONS -->
  <div class="panel">
    <div class="panel-title">🔍 Observaciones Clave</div>
    <ul style="list-style:none;padding:0;">{obs_html}</ul>
    <div style="margin-top:12px;padding:12px 16px;background:rgba(124,58,237,.08);border:1px solid rgba(124,58,237,.2);border-radius:10px;font-size:13px;line-height:1.7;color:#c4b5fd;">{summary}</div>
  </div>

  <!-- SESSION VERDICT -->
  {sessions_verdict}

  <!-- TRADES + ADVISOR -->
  <div class="panel">
    <div class="panel-title">📓 Journal de Trading</div>
    <div style="font-size:11px;color:#64748b;margin-bottom:12px;">
      🟢 LOW RISK &nbsp; 🟡 MEDIUM RISK &nbsp; 🟠 HIGH RISK &nbsp; 🔴 EXTREME RISK —
      El nivel de riesgo es <strong style="color:#fff;">independiente del resultado</strong> (una entrada EXTREME puede ser WIN y seguir siendo peligrosa)
    </div>
    {trades_html}
    {advisor_html}
  </div>

  <div class="foot">
    Agent 17 v2 · NQ Intelligence Engine · {date_str} ·
    Trades: <code>agent17_trades_{date_safe}.json</code> ·
    DeepChart projection: <code>deepchart_projection_{date_safe}.json</code>
  </div>

</div>

<script>
(function() {{
  const chart = LightweightCharts.createChart(document.getElementById('chart'), {{
    width: document.getElementById('chart').offsetWidth,
    height: 520,
    layout: {{
      background: {{ type: 'solid', color: '#06060a' }},
      textColor: '#64748b',
    }},
    grid: {{
      vertLines: {{ color: 'rgba(255,255,255,.04)' }},
      horzLines: {{ color: 'rgba(255,255,255,.04)' }},
    }},
    crosshair: {{
      mode: LightweightCharts.CrosshairMode.Normal,
      vertLine: {{ color: 'rgba(0,255,128,.4)', width: 1, style: 1 }},
      horzLine: {{ color: 'rgba(0,255,128,.4)', width: 1, style: 1 }},
    }},
    rightPriceScale: {{
      borderColor: 'rgba(255,255,255,.08)',
      scaleMargins: {{ top: 0.08, bottom: 0.08 }},
    }},
    timeScale: {{
      borderColor: 'rgba(255,255,255,.08)',
      timeVisible: true,
      secondsVisible: false,
    }},
  }});

  const candleSeries = chart.addCandlestickSeries({{
    upColor:          '#00ff80',
    downColor:        '#ff0055',
    borderUpColor:    '#00ff80',
    borderDownColor:  '#ff0055',
    wickUpColor:      '#00ff80',
    wickDownColor:    '#ff0055',
  }});

  {chart_data_note}

  {shadow_js}

  window.addEventListener('resize', () => {{
    chart.resize(document.getElementById('chart').offsetWidth, 520);
  }});
}})();
</script>
</body>
</html>"""

# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print("📓 Agent 17 v2 · Journal + Danger + Shadow — iniciando...")

    journal_data = load("agent15_journal_data.json")
    pending_data = load("agent16_pending.json")

    entries = journal_data.get("entries", [])
    if not entries:
        print("  ⚠️  Sin entradas en agent15_journal_data.json — ejecuta agent15 primero.")
        return

    today_entry = entries[0]
    date_str    = today_entry.get("date", datetime.datetime.now().strftime("%Y-%m-%d"))
    date_safe   = date_str.replace("-", "")

    trades = load_trades(date_str)
    dc     = load_deepchart(date_str)

    if dc:
        print(f"  📡 Shadow DeepChart cargado ({len(dc.get('projection',{}).get('path',[]))} puntos)")
    else:
        print(f"  ── Sin shadow DeepChart para {date_str}")

    html = build_html(today_entry, pending_data, trades, dc)

    out_file = os.path.join(BASE_DIR, f"journal_{date_safe}.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✅ Generado: journal_{date_safe}.html")
    if trades:
        print(f"  📊 {len(trades)} trade(s) — Consejero + Danger activados.")
    else:
        print(f"  ℹ️  Rellena agent17_trades_{date_safe}.json y regenera.")

if __name__ == "__main__":
    run()
