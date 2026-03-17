// ═══════════════════════════════════════════════════════
// NQ Intelligence Engine — Live Data Feed
// Generated: 2026-03-17T07:48:25.039605Z
// ═══════════════════════════════════════════════════════

window.NQ_LIVE = {
  timestamp:   "2026-03-17T07:48:25.039605Z",
  last_update: "17 Mar 2026 07:48 UTC",

  NDX: { price: 24655.34, change_pct: 1.13 },
  VXN: { price: 26.32, change_pct: -11.88, color: "#eab308" },
  MACRO: {
    US10Y: { price: null, change_pct: null },
    DXY:   { price: 99.88, change_pct: null }
  },

  DIX: null,
  GEX: { value_B: null },
  PCR: 0.65,
  OI:  142165,

  COT: {
    net:            31574,
    commercial_net: 0,
    index:          46.0,
    signal:         "NEUTRAL",
    razonamiento:   "Posicionamiento en rango medio."
  },

  BIAS: {
    global_score:   52,
    global_label:   "NEUTRAL-BULLISH",
    verdict:        "NEUTRAL-BULLISH",
    icon:           "🔵",
    breakdown:      {"positioning": 50, "macro": 50.0, "liquidity": 49.0, "timing": 50.0, "algorithmic": 65.0, "order_flow": 50}
  },

  SESSIONS:  {},
  SMC:       {"agent": 6, "name": "ICT & SMC Master", "timestamp": "2026-03-17T07:48:24.951859Z", "ict": {"pd_array": "DISCOUNT", "equilibrium": 24816.595703125, "has_liquidity_sweep": "BULLISH"}, "smc": {"last_bull_ob_price": 24455.400390625, "fvg_status": "ZONA_COMPRA", "institution_bias": "BULLISH"}, "signal": "BULLISH", "confidence": 85, "details": "ICT SETUP: Liquidity Sweep en zona de DISCOUNT detectado. Alta probabilidad alcista."},
  PROB:      {"agent": 7, "name": "Probability Analyst", "timestamp": "2026-03-17T07:48:24.957742Z", "confluences": {"cot_smc_match": false, "expectancy_pct": 50}, "verdict": "DISTRIBUCI\u00d3N / NEUTRAL", "math_bias": "NEUTRAL"},
  MINDSET:   {"agent": 8, "name": "Morgan Psychologist", "timestamp": "2026-03-17T07:48:24.962553+00:00", "sentiment": {"status": "ESTABLE", "operational_risk": "BAJO", "alerts": ["Sentimiento equilibrado. Ejecuci\u00f3n t\u00e9cnica recomendada."]}, "morgan_audit": {"institutional_alignment": "LOW", "fear_index": "MEDIUM"}},
  SB:        {"agent": 9, "name": "Silver Bullet Tracker", "timestamp": "2026-03-17T07:48:24.966365+00:00Z", "ny_time": "03:48", "status": "ACTIVE", "active_window": "London SB", "macro_confluence": "NEUTRAL-BEARISH", "action": "BUSCAR FVG PARA ENTRADA", "countdown": ""},
  ICT_STATS: {"agent": 10, "name": "ICT Session Strategist", "timestamp": "2026-03-13T09:18:07.501467+00:00Z", "stats": {"ny_sweep_low_winrate": 39.1, "ny_sweep_high_winrate": 31.6, "total_days_analyzed": 499, "sample_size_sweeps": 712}, "strategies": [{"name": "NY Continuation Bull", "edge": 39.1, "desc": "NY barre Low de Londres en Bias Alcista"}, {"name": "NY Continuation Bear", "edge": 31.6, "desc": "NY barre High de Londres en Bias Bajista"}]},
  PROTOCOLS: {"agent": 11, "timestamp": "2026-03-17T07:48:25.024805+00:00Z", "active_protocols": ["SILVER_BULLET_SNIPER"], "details": {"swing": {"active": false, "confidence": 52, "desc": "Confluencia de COT Alcista y Bias Ponderado positivo. Las instituciones est\u00e1n acumulando."}, "ict": {"active": false, "probability": 31.6, "desc": "Escenario de alta probabilidad detectado por barrido de Londres en direcci\u00f3n de la tendencia macro."}, "contrarian": {"active": false, "desc": "Miedo extremo detectado. Buscando capitulaci\u00f3n para entrada contrarian apoyada por DIX."}, "intraday": {"active": true, "window": "London SB", "action": "BUSCAR FVG PARA ENTRADA"}}, "master_recommendation": "Esperar confirmaci\u00f3n."},
  RESEARCH:  {"agent": 13, "name": "Explorador de Inteligencia Alpha", "last_crawl": "2026-03-17T07:48:25.007393+00:00Z", "insights": {"source": "Web Research & User DNA", "external_bias": "ESTUDIO DE BACKTESTING 3 A\u00d1OS EN CURSO", "confidence": 94, "recommendation": "Enfocarse en la 'Aceptaci\u00f3n' del precio respecto al POC de Londres en la primera hora de NY.", "discoveries": [{"source": "Sistema de Backtesting", "discovery": "Iniciando preparaci\u00f3n para Backtest de 3 a\u00f1os sobre niveles de Asia/Londres."}, {"source": "User Intel", "discovery": "Priorizaci\u00f3n de Niveles de Sesi\u00f3n Pre-Apertura (9:30 AM)."}, {"source": "Order Flow Page", "discovery": "Nueva secci\u00f3n de Mentor\u00eda IA Activa."}]}, "estrategia_maestra": {"nombre": "Confluencia de POC Semanal y Diario", "tipo": "Volume Profile / Value Inversion", "descripcion": "Cuando el POC del d\u00eda actual se alinea con el POC de la semana anterior, se crea un 'S\u00faper Nivel' de soporte o resistencia donde las instituciones defienden sus posiciones.", "reglas": ["1. Identificar POC Semanal anterior.", "2. Esperar a que el POC Diario se desarrolle en el mismo nivel.", "3. Operar el rebote (Bounce) con confirmaci\u00f3n de Delta."], "fuente": "Institutional Profile Journals", "score_alpha": "8.9/10"}, "backtest_config": {"period": "3 A\u00d1OS", "focus": "Asia/London Profiles vs NY Opening", "status": "DATA_COLLECTION_STAGE"}, "knowledge_base_size": "4.1GB", "status": "Aprendiendo patrones de Sesiones..."},
  ORDERFLOW: {"timestamp": "2026-03-17T07:48:25.011534+00:00Z", "symbol": "NQ1!", "bias_orderflow": "BULLISH (CONFLUENCIA SEMANAL + LONDRES)", "acceptance": "ACEPTACI\u00d3N ALCISTA SOBRE POC LONDRES", "sessions": {"asia": {"high": 24450.75, "low": 24320.5, "poc": 24385.0}, "london": {"high": 24510.25, "low": 24395.0, "poc": 24445.5}}, "weekly": {"poc": 24285.5, "vah": 24580.0, "val": 24150.25}, "daily": {"high": 24550.0, "low": 24310.0, "poc": 24412.5}, "delta": {"cumulative": "+5840", "status": "POSITIVE_ABSORPTION"}, "volume_profile": {"POC": 24412.5, "VAH": 24490.0, "VAL": 24350.0, "status": "ACEPTACI\u00d3N ALCISTA SOBRE POC LONDRES"}, "institutional_activity": "HIGH (SESI\u00d3N NY ABRIENDO SOBRE POC ASIA/LON)", "tape_reading": "Grandes \u00f3rdenes de compra bloqueando ca\u00eddas en el nivel de POC de Londres (24,445)."}
};

(function inject() {
  const D = window.NQ_LIVE;
  const set = (id, val) => { 
    const el = document.getElementById(id); 
    if (el && val !== null && val !== undefined) el.innerText = val; 
  };

  if (D.VXN.price) set("heroVxn", D.VXN.price.toFixed(2));
  if (D.DIX) set("heroDix", D.DIX.toFixed(1) + "%");
  if (D.GEX.value_B !== null) set("heroGex", (D.GEX.value_B >= 0 ? "+" : "") + D.GEX.value_B.toFixed(2) + "B");

  if (D.COT.net) set("weekly-cot-desc", "Posición neta: " + D.COT.net.toLocaleString() + " contratos. " + (D.COT.razonamiento || ""));
  set("cot-razonamiento-label", D.COT.razonamiento);

  if (D.RESEARCH && D.RESEARCH.insights && D.RESEARCH.insights.discoveries) {
    const discoEl = document.getElementById("research-disco-list");
    if (discoEl) {
      discoEl.innerHTML = D.RESEARCH.insights.discoveries.map(d => 
        '<div class="disco-item border-l border-electric-cyan/30 pl-3 mb-3">' +
          '<div class="text-[9px] text-electric-cyan uppercase font-bold">' + d.source + '</div>' +
          '<div class="text-[11px] text-gray-300 italic">"' + d.discovery + '"</div>' +
        '</div>'
      ).join("");
    }
  }

  if (D.RESEARCH && D.RESEARCH.estrategia_maestra) {
    const S = D.RESEARCH.estrategia_maestra;
    set("learned-strategy-name", S.nombre);
    set("learned-strategy-alpha", S.score_alpha);
    set("learned-strategy-desc", S.descripcion);
    
    const rulesEl = document.getElementById("learned-strategy-rules");
    if (rulesEl && S.reglas) {
        rulesEl.innerHTML = S.reglas.map((r, i) => 
            '<div class="p-4 bg-white/5 border border-white/10 rounded-xl">' +
                '<div class="text-[10px] text-electric-cyan font-mono mb-2">REGLA 0' + (i+1) + '</div>' +
                '<div class="text-xs text-white leading-relaxed">' + r + '</div>' +
            '</div>'
        ).join("");
    }
  }

  if (D.ORDERFLOW && D.ORDERFLOW.volume_profile) {
    set("of-poc", D.ORDERFLOW.volume_profile.POC);
    set("of-vah", D.ORDERFLOW.volume_profile.VAH);
    set("of-val", D.ORDERFLOW.volume_profile.VAL);
  }

  console.log("[NQ Engine] Visuals Updated successfully.");
})();
