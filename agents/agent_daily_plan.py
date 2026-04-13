"""
=======================================================
AGENTE: DAILY TRADE PLAN GENERATOR
=======================================================
Genera cada dia un plan de trading EXACTO para:
  - 20 cuentas Apex 50K
  - Target: $200/cuenta/dia
  - Instrumento: MNQ (Micro NQ)
  - Estrategia: OR 30min + filtros de calidad

El plan te dice:
  1. A que hora observar
  2. Que buscar (OR BULL/BEAR)
  3. Entry exacto
  4. Stop exacto
  5. Target exacto (para llegar a $200)
  6. Cuántos contratos
  7. Score de confianza del día

Output: data/daily_plan.json + daily_plan.html
"""

import os, sys, json, datetime, io

if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "research", "daily_master_db.json")
COT_FILE = os.path.join(BASE_DIR, "agent2_data.json")
NEWS_FILE = os.path.join(BASE_DIR, "data", "news_live.json")
SENT_FILE = os.path.join(BASE_DIR, "data", "sentiment_reddit.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "daily_plan.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "daily_plan.html")

# ═══════════════════════════════════════════════════════════════════
#  CONFIGURACION APEX
# ═══════════════════════════════════════════════════════════════════
APEX_ACCOUNTS = 20
ACCOUNT_SIZE = 50000
DAILY_TARGET = 200        # $200 por cuenta
MNQ_POINT_VALUE = 2.0     # $2 por punto por contrato MNQ
MAX_CONTRACTS_50K = 5     # Apex 50K permite hasta ~5 MNQ
TRAILING_DRAWDOWN = 2500  # Apex 50K trailing drawdown ~$2,500
MAX_DAILY_LOSS = 500      # max que queremos perder por cuenta/dia

# ═══════════════════════════════════════════════════════════════════
#  ESTRATEGIA OR 30min
# ═══════════════════════════════════════════════════════════════════
DOW_STRATEGY = {
    0: {"day": "LUNES",     "side": "LONG",  "or_expect": "BULL", "hist_wr": 71, "hist_avg": 100},
    1: {"day": "MARTES",    "side": "LONG",  "or_expect": "BULL", "hist_wr": 72, "hist_avg": 73},
    2: {"day": "MIERCOLES", "side": "SHORT", "or_expect": "BEAR", "hist_wr": 69, "hist_avg": 64},
    3: {"day": "JUEVES",    "side": "SHORT", "or_expect": "BEAR", "hist_wr": 71, "hist_avg": 119},
    4: {"day": "VIERNES",   "side": "SHORT", "or_expect": "BEAR", "hist_wr": 73, "hist_avg": 117},
}


def get_today_info():
    """Obtiene info del dia actual."""
    # Usar ET timezone (UTC-4 / UTC-5)
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    et_offset = datetime.timedelta(hours=-4)  # EDT
    et_now = utc_now + et_offset
    
    dow = et_now.weekday()  # 0=Lun
    date_str = et_now.strftime("%Y-%m-%d")
    
    # Si es fin de semana, planear para lunes
    if dow >= 5:
        days_ahead = 7 - dow  # dias hasta el lunes
        next_monday = et_now + datetime.timedelta(days=days_ahead)
        dow = 0
        date_str = next_monday.strftime("%Y-%m-%d")
    
    return dow, date_str, et_now


def load_context():
    """Carga datos de contexto de todos los agentes."""
    context = {"cot": None, "news": None, "sentiment": None, "history": None}
    
    # COT
    try:
        with open(COT_FILE, "r") as f:
            context["cot"] = json.load(f)
    except: pass
    
    # News
    try:
        with open(NEWS_FILE, "r") as f:
            context["news"] = json.load(f)
    except: pass
    
    # Reddit Sentiment
    try:
        with open(SENT_FILE, "r") as f:
            context["sentiment"] = json.load(f)
    except: pass
    
    # History (last 10 days)
    try:
        with open(DB_FILE, "r") as f:
            db = json.load(f)
        context["history"] = db.get("records", [])[-10:]
    except: pass
    
    return context


def calculate_confidence(dow, context):
    """Calcula un score de confianza 0-100 para el trade."""
    score = 50  # base
    reasons = []
    warnings = []
    
    strategy = DOW_STRATEGY[dow]
    
    # Factor 1: Historical WR del dia
    hist_wr = strategy["hist_wr"]
    if hist_wr >= 72:
        score += 15
        reasons.append(f"Hist WR {hist_wr}% (muy alto)")
    elif hist_wr >= 69:
        score += 8
        reasons.append(f"Hist WR {hist_wr}% (bueno)")
    
    # Factor 2: Prev day direction = same → boost
    hist = context.get("history", [])
    if hist:
        last_day = hist[-1]
        last_dir = last_day.get("direction", "")
        expected = strategy["or_expect"]
        if (expected == "BULL" and last_dir == "BULLISH") or \
           (expected == "BEAR" and last_dir == "BEARISH"):
            score += 12
            reasons.append(f"Prev day = {last_dir} (booster activo, +10% WR)")
        
        # VXN
        vxn = last_day.get("vxn")
        if vxn and vxn > 30:
            score -= 10
            warnings.append(f"VXN alto: {vxn:.1f} (volatilidad extrema)")
        elif vxn and vxn < 20:
            score += 5
            reasons.append(f"VXN bajo: {vxn:.1f} (calma)")
    
    # Factor 3: COT signal
    cot = context.get("cot")
    if cot:
        cot_signal = cot.get("signal", cot.get("cot_signal", ""))
        if "BULLISH" in str(cot_signal).upper() and strategy["side"] == "LONG":
            score += 8
            reasons.append(f"COT alineado: {cot_signal}")
        elif "BEARISH" in str(cot_signal).upper() and strategy["side"] == "SHORT":
            score += 8
            reasons.append(f"COT alineado: {cot_signal}")
        elif "CONTRA" in str(cot_signal).upper():
            score -= 5
            warnings.append(f"COT contradice: {cot_signal}")
    
    # Factor 4: News sentiment
    news = context.get("news")
    if news:
        ns = news.get("sentiment", {})
        if ns.get("label") == "BULLISH" and strategy["side"] == "LONG":
            score += 5
            reasons.append("Noticias alineadas (BULL)")
        elif ns.get("label") == "BEARISH" and strategy["side"] == "SHORT":
            score += 5
            reasons.append("Noticias alineadas (BEAR)")
        hi = news.get("high_impact_count", 0)
        if hi > 3:
            warnings.append(f"{hi} noticias de alto impacto (precaucion)")
    
    # Factor 5: Reddit sentiment (contrarian)
    sent = context.get("sentiment")
    if sent:
        fg = sent.get("fear_greed", {})
        fg_label = fg.get("label", "")
        if fg_label == "EXTREME FEAR" and strategy["side"] == "LONG":
            score += 10
            reasons.append("Reddit en panico - senal contrarian LONG")
        elif fg_label == "EXTREME GREED" and strategy["side"] == "SHORT":
            score += 10
            reasons.append("Reddit euforia - senal contrarian SHORT")
    
    # Miercoles BULL = evitar
    if dow == 2:
        warnings.append("Miercoles: si OR es BULL, NO entrar (solo 66%)")
    
    score = max(10, min(95, score))
    
    # Nivel
    if score >= 80:
        level = "ALTA"
        color = "#22d98a"
    elif score >= 60:
        level = "MEDIA"
        color = "#f5a623"
    else:
        level = "BAJA"
        color = "#f0485a"
    
    return {
        "score": score,
        "level": level,
        "color": color,
        "reasons": reasons,
        "warnings": warnings,
    }


def calculate_trade_params(strategy, confidence):
    """Calcula parametros exactos del trade."""
    
    # Contracts: mas confianza = mas contratos (max 5 MNQ)
    if confidence["score"] >= 80:
        contracts = 4  # Alta confianza
    elif confidence["score"] >= 65:
        contracts = 3  # Media-alta
    elif confidence["score"] >= 50:
        contracts = 2  # Media
    else:
        contracts = 1  # Baja
    
    contracts = min(contracts, MAX_CONTRACTS_50K)
    
    # Target en puntos para llegar a $200
    value_per_pt = MNQ_POINT_VALUE * contracts
    target_pts = round(DAILY_TARGET / value_per_pt, 1)
    
    # Stop en puntos (risk:reward 1:2 => stop = target/2)
    stop_pts = round(target_pts / 2, 1)
    
    # Risk en dolares
    risk_dollars = round(stop_pts * value_per_pt, 2)
    
    # Alternativa: riesgo fijo de $100 por cuenta
    alt_stop = round(100 / value_per_pt, 1)
    alt_target = round(DAILY_TARGET / value_per_pt, 1)
    
    return {
        "contracts": contracts,
        "contract_type": "MNQ",
        "value_per_point": value_per_pt,
        "target_pts": target_pts,
        "stop_pts": stop_pts,
        "target_dollars": DAILY_TARGET,
        "risk_dollars": risk_dollars,
        "risk_reward": "1:2",
        "alt_conservative": {
            "contracts": 2,
            "stop_pts": round(100 / (MNQ_POINT_VALUE * 2), 1),
            "target_pts": round(DAILY_TARGET / (MNQ_POINT_VALUE * 2), 1),
            "note": "Opcion conservadora: 2 MNQ, risk $100, target $200"
        },
        "for_20_accounts": {
            "total_target": DAILY_TARGET * APEX_ACCOUNTS,
            "total_risk": risk_dollars * APEX_ACCOUNTS,
            "if_all_win": DAILY_TARGET * APEX_ACCOUNTS,
            "if_all_lose": risk_dollars * APEX_ACCOUNTS,
        }
    }


def generate_plan():
    """Genera el plan de trading del dia."""
    dow, date_str, et_now = get_today_info()
    strategy = DOW_STRATEGY[dow]
    context = load_context()
    confidence = calculate_confidence(dow, context)
    params = calculate_trade_params(strategy, confidence)
    
    plan = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "date": date_str,
        "day": strategy["day"],
        "dow": dow,
        
        "protocol": {
            "step1": "9:30 ET - Observar apertura, NO entrar",
            "step2": "9:30-10:00 ET - Dejar que se forme el Opening Range (30min)",
            "step3": f"10:00 ET - Verificar si OR cerro {strategy['or_expect']}",
            "step4": f"10:01 ET - Si OR = {strategy['or_expect']} -> entrar {strategy['side']}",
            "step5": f"Stop = otro lado del OR ({params['stop_pts']} pts max)",
            "step6": f"Target = +{params['target_pts']} pts ($200/cuenta)",
            "step7": "Si no toco target a las 2:00 PM -> evaluar salida parcial",
            "step8": "4:00 PM ET - Cerrar todo",
        },
        
        "action": strategy["side"],
        "or_expected": strategy["or_expect"],
        "historical_wr": strategy["hist_wr"],
        "historical_avg_pts": strategy["hist_avg"],
        
        "confidence": confidence,
        "trade_params": params,
        
        "apex_config": {
            "accounts": APEX_ACCOUNTS,
            "account_size": ACCOUNT_SIZE,
            "daily_target_per_account": DAILY_TARGET,
            "trailing_drawdown": TRAILING_DRAWDOWN,
            "max_daily_loss_per_account": MAX_DAILY_LOSS,
        },
        
        "rules": {
            "ENTRAR": f"Solo si OR 30min confirma {strategy['or_expect']}",
            "NO_ENTRAR_1": "Si OR es FLAT (<10pts movimiento)",
            "NO_ENTRAR_2": "Si OR contradice la direccion esperada",
            "NO_ENTRAR_3": "Miercoles: si OR es BULL, evitar (solo 66%)",
            "SALIR": "Al tocar target O al cierre NY 4PM",
            "STOP": "Al otro lado del Opening Range",
        },
    }
    
    # Guardar JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    
    # Generar HTML
    generate_plan_html(plan)
    
    return plan


def generate_plan_html(plan):
    """Genera un HTML visual del plan de trading."""
    p = plan
    s = p["trade_params"]
    c = p["confidence"]
    prot = p["protocol"]
    
    # Reasons / Warnings
    reasons_html = "".join(f'<div style="padding:3px 0;color:var(--green);">&#9989; {r}</div>' for r in c["reasons"])
    warnings_html = "".join(f'<div style="padding:3px 0;color:var(--orange);">&#9888;&#65039; {w}</div>' for w in c["warnings"])
    
    action_color = "#22d98a" if p["action"] == "LONG" else "#f0485a"
    action_icon = "&#9650;" if p["action"] == "LONG" else "&#9660;"
    conf_color = c["color"]
    
    # Protocol steps
    steps_html = ""
    for key in sorted(p["protocol"].keys()):
        step = p["protocol"][key]
        emoji = "&#128064;" if "Observar" in step else "&#9203;" if "Dejar" in step else "&#9989;" if "Verificar" in step else "&#128640;" if "entrar" in step else "&#128721;" if "Stop" in step else "&#127919;" if "Target" in step else "&#128200;" if "evaluar" in step else "&#128308;"
        steps_html += f'<div style="padding:8px 12px;margin:4px 0;background:rgba(99,130,255,0.05);border-radius:8px;font-size:0.82rem;">{emoji} {step}</div>'
    
    alt = s["alt_conservative"]
    a20 = s["for_20_accounts"]
    
    html = f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Plan de Trading - {p['date']} {p['day']}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root{{--bg:#0b0e1a;--bg2:#111420;--bg3:#181d2e;--border:rgba(99,130,255,0.18);--accent:#6382ff;--accent2:#38c9e8;--green:#22d98a;--red:#f0485a;--orange:#f5a623;--text:#e4e8ff;--text2:#8898bb;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;padding:20px;min-height:100vh;}}
.c{{max-width:900px;margin:0 auto;}}
.card{{background:var(--bg2);border:1px solid var(--border);border-radius:16px;padding:20px;margin-bottom:16px;}}
.hero{{text-align:center;padding:30px 20px;border:2px solid {action_color}44;position:relative;overflow:hidden;}}
.hero::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,{action_color},{action_color}88,{action_color});}}
h1{{font-size:1.3rem;font-weight:800;}}
.action-big{{font-size:3rem;font-weight:800;color:{action_color};margin:10px 0;letter-spacing:2px;}}
.badge{{display:inline-flex;padding:5px 14px;border-radius:20px;font-size:0.75rem;font-weight:700;}}
.sg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:12px 0;}}
.sb{{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center;}}
.sv{{font-size:1.3rem;font-weight:800;}}.sl{{font-size:0.58rem;color:var(--text2);text-transform:uppercase;margin-top:3px;}}
.ct{{font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--accent);margin-bottom:14px;}}
a.bk{{color:var(--accent2);text-decoration:none;font-size:.8rem;display:inline-flex;align-items:center;gap:5px;margin-bottom:16px;}}
.mono{{font-family:'JetBrains Mono',monospace;}}
@media(max-width:600px){{.sg{{grid-template-columns:1fr 1fr;}}.action-big{{font-size:2rem;}}}}
</style></head><body>
<div class="c">
<a href="daily_dashboard.html" class="bk">&#9664; Daily Dashboard</a>

<!-- HERO -->
<div class="card hero">
  <div style="font-size:0.7rem;color:var(--text2);text-transform:uppercase;letter-spacing:2px;">Plan de Trading</div>
  <h1>{p['day']} {p['date']}</h1>
  <div class="action-big">{action_icon} {p['action']}</div>
  <div style="margin:8px 0;">
    <span class="badge" style="background:{conf_color}22;color:{conf_color};border:1px solid {conf_color}44;">
      Confianza: {c['score']}% — {c['level']}
    </span>
  </div>
  <div style="font-size:0.8rem;color:var(--text2);margin-top:6px;">
    Esperar OR 30min = {p['or_expected']} &rarr; {p['action']} | Historical WR: {p['historical_wr']}%
  </div>
</div>

<!-- PARAMETROS DEL TRADE -->
<div class="card">
  <div class="ct">&#127919; Parametros del Trade</div>
  <div class="sg">
    <div class="sb"><div class="sv mono" style="color:var(--accent2);">{s['contracts']}</div><div class="sl">{s['contract_type']} Contratos</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--green);">+{s['target_pts']}</div><div class="sl">Target (pts)</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--red);">-{s['stop_pts']}</div><div class="sl">Stop (pts)</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--green);">${s['target_dollars']}</div><div class="sl">Ganancia/Cuenta</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--red);">-${s['risk_dollars']}</div><div class="sl">Riesgo/Cuenta</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--text);">{s['risk_reward']}</div><div class="sl">Risk : Reward</div></div>
  </div>
  <div style="background:rgba(99,130,255,0.05);border:1px solid var(--border);border-radius:10px;padding:12px;margin-top:8px;">
    <div style="font-size:0.7rem;font-weight:600;color:var(--accent2);margin-bottom:6px;">&#128176; Si las 20 cuentas ganan:</div>
    <div style="font-size:1.2rem;font-weight:800;color:var(--green);">+${a20['total_target']:,}</div>
    <div style="font-size:0.65rem;color:var(--text2);margin-top:4px;">Riesgo total si todas pierden: -${a20['total_risk']:,.0f}</div>
  </div>
</div>

<!-- PROTOCOLO PASO A PASO -->
<div class="card">
  <div class="ct">&#128203; Protocolo Paso a Paso</div>
  {steps_html}
</div>

<!-- CONFIANZA -->
<div class="card">
  <div class="ct">&#128200; Analisis de Confianza — {c['score']}%</div>
  <div style="background:linear-gradient(90deg,{action_color}22,{conf_color}22);border-radius:8px;height:12px;margin-bottom:12px;position:relative;">
    <div style="width:{c['score']}%;height:100%;background:{conf_color};border-radius:8px;transition:width 0.8s;"></div>
  </div>
  <div style="font-size:0.78rem;line-height:1.8;">
    {reasons_html}
    {warnings_html}
  </div>
</div>

<!-- OPCION CONSERVADORA -->
<div class="card" style="border:1px solid rgba(56,201,232,0.2);">
  <div class="ct" style="color:var(--accent2);">&#128737; Opcion Conservadora</div>
  <div class="sg">
    <div class="sb"><div class="sv mono" style="color:var(--accent2);">{alt['contracts']}</div><div class="sl">MNQ Contratos</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--green);">+{alt['target_pts']}</div><div class="sl">Target (pts)</div></div>
    <div class="sb"><div class="sv mono" style="color:var(--red);">-{alt['stop_pts']}</div><div class="sl">Stop (pts)</div></div>
  </div>
  <div style="font-size:0.75rem;color:var(--text2);">{alt['note']}</div>
</div>

<!-- REGLAS -->
<div class="card">
  <div class="ct">&#128308; Reglas Inquebrantables</div>
  <div style="font-size:0.78rem;line-height:2.0;">
    <div>&#9989; <b>ENTRAR:</b> {p['rules']['ENTRAR']}</div>
    <div>&#10060; <b>NO ENTRAR:</b> {p['rules']['NO_ENTRAR_1']}</div>
    <div>&#10060; <b>NO ENTRAR:</b> {p['rules']['NO_ENTRAR_2']}</div>
    <div>&#10060; <b>NO ENTRAR:</b> {p['rules']['NO_ENTRAR_3']}</div>
    <div>&#128308; <b>SALIR:</b> {p['rules']['SALIR']}</div>
    <div>&#128721; <b>STOP:</b> {p['rules']['STOP']}</div>
  </div>
</div>

<div style="text-align:center;color:var(--text2);font-size:0.65rem;padding:20px;">
  Generado por Whale Radar Intelligence Engine · {p['timestamp'][:19]}
</div>
</div></body></html>"""
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


def run():
    """Run the daily plan generator."""
    print("\n" + "="*60)
    print("  DAILY TRADE PLAN GENERATOR")
    print("  Apex 50K x 20 cuentas · Target $200/dia")
    print("="*60)
    
    plan = generate_plan()
    
    p = plan
    s = p["trade_params"]
    c = p["confidence"]
    
    print(f"\n  Fecha: {p['date']} ({p['day']})")
    print(f"  Accion: {p['action']}")
    print(f"  OR esperado: {p['or_expected']}")
    print(f"  Confianza: {c['score']}% ({c['level']})")
    print(f"\n  Contratos: {s['contracts']} {s['contract_type']}")
    print(f"  Target: +{s['target_pts']} pts (${s['target_dollars']}/cuenta)")
    print(f"  Stop: -{s['stop_pts']} pts (-${s['risk_dollars']}/cuenta)")
    print(f"  R:R = {s['risk_reward']}")
    print(f"\n  20 cuentas total: ${s['for_20_accounts']['total_target']:,}/dia")
    
    if c["reasons"]:
        print(f"\n  Razones:")
        for r in c["reasons"]:
            print(f"    + {r}")
    if c["warnings"]:
        print(f"\n  Advertencias:")
        for w in c["warnings"]:
            print(f"    ! {w}")
    
    print(f"\n  -> {OUTPUT_JSON}")
    print(f"  -> {OUTPUT_HTML}")
    
    return plan


if __name__ == "__main__":
    run()
