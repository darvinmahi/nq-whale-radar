"""
AGENTE 5 — FILE SYSTEM INJECTOR
═══════════════════════════════════════════════════════════
Responsabilidad: Inyectar los datos del Bias Engine en el
  frontend (index.html) mediante un archivo JS live.
"""

import sys
import os
import json
import datetime

# Root directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_JS = os.path.join(BASE_DIR, "agent_live_data.js")

def load_json(filename):
    try:
        path = os.path.join(BASE_DIR, filename)
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Agent 5] Error leyendo {filename}: {e}")
        return {}

def generate_live_js(a1, a2, a3, a4, a6, a7, a8, a9, a10, a11, a13, a14):
    ts = datetime.datetime.utcnow().isoformat() + "Z"
    yahoo = a1.get("yahoo", {})
    sm = a1.get("squeezemetrics", {})
    cme = a1.get("cme", {})
    
    ndx_data = yahoo.get("NDX", {})
    vxn_data = yahoo.get("VXN", {})
    tnx_data = yahoo.get("US10Y", {})
    dxy_data = yahoo.get("DXY", {})
    
    vxn_val = vxn_data.get("price")
    vxn_color = "#34d399" if (vxn_val and vxn_val < 22) else "#ef4444" if (vxn_val and vxn_val > 28) else "#eab308"

    # Pre-encode nested JSONs
    js_sessions = json.dumps(a1.get("sessions", {}))
    js_smc = json.dumps(a6)
    js_prob = json.dumps(a7)
    js_mindset = json.dumps(a8)
    js_sb = json.dumps(a9)
    js_ict_stats = json.dumps(a10)
    js_protocols = json.dumps(a11)
    js_research = json.dumps(a13)
    js_orderflow = json.dumps(a14)
    js_breakdown = json.dumps(a4.get("layers", {}))

    js = f"""// ═══════════════════════════════════════════════════════
// NQ Intelligence Engine — Live Data Feed
// Generated: {ts}
// ═══════════════════════════════════════════════════════

window.NQ_LIVE = {{
  timestamp:   "{ts}",
  last_update: "{datetime.datetime.utcnow().strftime('%d %b %Y %H:%M')} UTC",

  NDX: {{ price: {ndx_data.get("price") or "null"}, change_pct: {ndx_data.get("change_pct") or "null"} }},
  VXN: {{ price: {vxn_val or "null"}, change_pct: {vxn_data.get("change_pct") or "null"}, color: "{vxn_color}" }},
  MACRO: {{
    US10Y: {{ price: {tnx_data.get("price") or "null"}, change_pct: {tnx_data.get("change_pct") or "null"} }},
    DXY:   {{ price: {dxy_data.get("price") or "null"}, change_pct: {dxy_data.get("change_pct") or "null"} }}
  }},

  DIX: {sm.get("DIX") or "null"},
  GEX: {{ value_B: {sm.get("GEX_B") or "null"} }},
  PCR: {a3.get("pcr") if a3.get("pcr") else "0.65"},
  OI:  {cme.get("NQ1_OI") or "null"},

  COT: {{
    net:            {a2.get("cot", {}).get("current_net") or "null"},
    commercial_net: {a2.get("cot", {}).get("commercial_net") or 0},
    index:          {a2.get("cot", {}).get("cot_index") or "null"},
    signal:         "{a2.get("signal", "NEUTRAL")}",
    razonamiento:   "{a2.get("razonamiento", "")}"
  }},

  BIAS: {{
    global_score:   {a4.get("global_score", 50)},
    global_label:   "{a4.get("global_label", "NEUTRAL")}",
    verdict:        "{a4.get("global_label", "NEUTRAL")}",
    icon:           "{a4.get("icon", "⚪")}",
    breakdown:      {js_breakdown}
  }},

  SESSIONS:  {js_sessions},
  SMC:       {js_smc},
  PROB:      {js_prob},
  MINDSET:   {js_mindset},
  SB:        {js_sb},
  ICT_STATS: {js_ict_stats},
  PROTOCOLS: {js_protocols},
  RESEARCH:  {js_research},
  ORDERFLOW: {js_orderflow}
}};

(function inject() {{
  const D = window.NQ_LIVE;
  const set = (id, val) => {{ 
    const el = document.getElementById(id); 
    if (el && val !== null && val !== undefined) el.innerText = val; 
  }};

  if (D.VXN.price) set("heroVxn", D.VXN.price.toFixed(2));
  if (D.DIX) set("heroDix", D.DIX.toFixed(1) + "%");
  if (D.GEX.value_B !== null) set("heroGex", (D.GEX.value_B >= 0 ? "+" : "") + D.GEX.value_B.toFixed(2) + "B");

  if (D.COT.net) set("weekly-cot-desc", "Posición neta: " + D.COT.net.toLocaleString() + " contratos. " + (D.COT.razonamiento || ""));
  set("cot-razonamiento-label", D.COT.razonamiento);

  if (D.RESEARCH && D.RESEARCH.insights && D.RESEARCH.insights.discoveries) {{
    const discoEl = document.getElementById("research-disco-list");
    if (discoEl) {{
      discoEl.innerHTML = D.RESEARCH.insights.discoveries.map(d => 
        '<div class="disco-item border-l border-electric-cyan/30 pl-3 mb-3">' +
          '<div class="text-[9px] text-electric-cyan uppercase font-bold">' + d.source + '</div>' +
          '<div class="text-[11px] text-gray-300 italic">"' + d.discovery + '"</div>' +
        '</div>'
      ).join("");
    }}
  }}

  if (D.RESEARCH && D.RESEARCH.estrategia_maestra) {{
    const S = D.RESEARCH.estrategia_maestra;
    set("learned-strategy-name", S.nombre);
    set("learned-strategy-alpha", S.score_alpha);
    set("learned-strategy-desc", S.descripcion);
    
    const rulesEl = document.getElementById("learned-strategy-rules");
    if (rulesEl && S.reglas) {{
        rulesEl.innerHTML = S.reglas.map((r, i) => 
            '<div class="p-4 bg-white/5 border border-white/10 rounded-xl">' +
                '<div class="text-[10px] text-electric-cyan font-mono mb-2">REGLA 0' + (i+1) + '</div>' +
                '<div class="text-xs text-white leading-relaxed">' + r + '</div>' +
            '</div>'
        ).join("");
    }}
  }}

  if (D.ORDERFLOW && D.ORDERFLOW.volume_profile) {{
    set("of-poc", D.ORDERFLOW.volume_profile.POC);
    set("of-vah", D.ORDERFLOW.volume_profile.VAH);
    set("of-val", D.ORDERFLOW.volume_profile.VAL);
  }}

  // ─── AUDITORÍA ALGORÍTMICA (permanente, regenerado por agent5) ───────────
  const _P = D.PROTOCOLS?.details || {{}};
  const _protos = D.PROTOCOLS?.active_protocols || [];

  // SMC Detective Card — datos de D.SMC (agent6)
  const _smcSig = D.SMC?.signal || "SCANNING";
  const _smcColor = _smcSig === "BULLISH" ? "#00ffc8" : _smcSig === "BEARISH" ? "#ef4444" : "#94a3b8";
  const _smcEl = document.getElementById("smc-signal");
  if (_smcEl) {{ _smcEl.textContent = _smcSig; _smcEl.style.color = _smcColor; }}
  set("smc-details",  D.SMC?.details || "Analizando huellas institucionales...");
  set("smc-ob-price", D.SMC?.smc?.last_bull_ob_price != null ? D.SMC.smc.last_bull_ob_price.toFixed(2) : "—");
  set("smc-fvg",      D.SMC?.smc?.fvg_status ? D.SMC.smc.fvg_status.replace(/_/g," ") : "No detectado");
  set("ict-pd",       D.SMC?.ict?.pd_array || "—");
  set("ict-sweep",    D.SMC?.ict?.has_liquidity_sweep || "—");
  set("ict-wr-bull",  D.PROB?.confluences?.expectancy_pct != null ? D.PROB.confluences.expectancy_pct.toFixed(1) + "%" : "--%");
  set("ict-wr-bear",  D.PROB?.confluences?.expectancy_pct != null ? (100 - D.PROB.confluences.expectancy_pct).toFixed(1) + "%" : "--%");

  // Probability Analyst Card — datos de D.PROB (agent7)
  set("prob-expectancy", D.PROB?.confluences?.expectancy_pct != null ? D.PROB.confluences.expectancy_pct.toFixed(1) + "%" : "—%");
  set("prob-verdict",    D.PROB?.verdict || D.PROTOCOLS?.master_recommendation || "Calculando confluencias...");

  // Silver Bullet Card — datos de D.SB (agent9)
  set("sb-status",    D.SB?.status || (_protos[0]?.replace(/_/g," ")) || "SCANNING");
  set("sb-window",    D.SB?.active_window ? "Ventana: " + D.SB.active_window : "Fuera de ventana");
  set("sb-countdown", D.SB?.countdown || D.SB?.action || "—");

  // Protocol Badges
  const _badgeEl = document.getElementById("active-protocols-list");
  if (_badgeEl && _protos.length > 0) {{
    _badgeEl.innerHTML = _protos.map(p =>
      `<span style="font-size:8px;padding:2px 10px;border-radius:100px;background:rgba(0,255,200,0.08);border:1px solid rgba(0,255,200,0.3);color:#00ffc8;font-family:monospace;">${{p.replace(/_/g," ")}}</span>`
    ).join("");
  }}

  console.log("[NQ Engine] Visuals Updated successfully.");
}})();
"""
    return js

def run():
    a1 = load_json("agent1_data.json")
    a2 = load_json("agent2_data.json")
    a3 = load_json("agent3_data.json")
    a4 = load_json("agent4_data.json")
    a6 = load_json("agent6_data.json")
    a7 = load_json("agent7_data.json")
    a8 = load_json("agent8_data.json")
    a9 = load_json("agent9_data.json")
    a10 = load_json("agent10_ict_stats.json")
    a11 = load_json("agent11_data.json")
    a13 = load_json("agent13_data.json")
    a14 = load_json("agent14_orderflow_data.json")
    
    js = generate_live_js(a1, a2, a3, a4, a6, a7, a8, a9, a10, a11, a13, a14)
    with open(OUTPUT_JS, "w", encoding="utf-8") as f:
        f.write(js)
    print("✅ Root Agent 5 Done.")

if __name__ == "__main__":
    run()
