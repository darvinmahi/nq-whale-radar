// 🚀 QUANTUM DATA FEED · AUTO-GENERATED
window.NQ_LIVE = {
  timestamp: "2026-03-18T23:57:55.272681+00:00Z",
  last_update: "23:57:55 UTC",
  NQ: { 
    price: 0, 
    change_pct: 0 
  },
  COT: {
    net: 2386,
    index: 27.3,
    signal: "NEUTRAL",
    razonamiento: ``,
    history: [{"date": "03 Mar 2026", "nc_long": 76598, "nc_short": 74212}, {"date": "24 Feb 2026", "nc_long": 80310, "nc_short": 69523}, {"date": "17 Feb 2026", "nc_long": 89273, "nc_short": 64863}, {"date": "10 Feb 2026", "nc_long": 82196, "nc_short": 68836}]
  },
  BIAS: { 
    score: 54, 
    label: "NEUTRAL-BULLISH" 
  },
  ORDERFLOW: {"timestamp": "2026-03-18T14:21:22.484647+00:00Z", "symbol": "NQ1!", "bias_orderflow": "BULLISH (CONFLUENCIA SEMANAL + LONDRES)", "acceptance": "ACEPTACI\u00d3N ALCISTA SOBRE POC LONDRES", "sessions": {"asia": {"high": 24450.75, "low": 24320.5, "poc": 24385.0}, "london": {"high": 24510.25, "low": 24395.0, "poc": 24445.5}}, "weekly": {"poc": 24285.5, "vah": 24580.0, "val": 24150.25}, "daily": {"high": 24550.0, "low": 24310.0, "poc": 24412.5}, "delta": {"cumulative": "+5840", "status": "POSITIVE_ABSORPTION"}, "volume_profile": {"POC": 24412.5, "VAH": 24490.0, "VAL": 24350.0, "status": "ACEPTACI\u00d3N ALCISTA SOBRE POC LONDRES"}, "institutional_activity": "HIGH (SESI\u00d3N NY ABRIENDO SOBRE POC ASIA/LON)", "tape_reading": "Grandes \u00f3rdenes de compra bloqueando ca\u00eddas en el nivel de POC de Londres (24,445)."},
  JOURNAL: {},
  BACKTEST: {"strategy_name": "Aceptaci\u00f3n de POC & Continuaci\u00f3n de Valor", "period": "3 A\u00d1OS (2021-2024 focalizado)", "total_days_analyzed": 1556, "win_rate": 50.84, "overall_win_rate": "50.84%", "yearly_performance": {"2020": 48.616600790513836, "2021": 53.57142857142857, "2022": 56.573705179282875, "2023": 50.4, "2024": 50.39682539682539, "2025": 47.199999999999996, "2026": 41.66666666666667}, "notes": ["Alta efectividad en a\u00f1os de expansi\u00f3n (2021, 2023).", "La aceptaci\u00f3n sobre el POC diario predice con un 64% de precisi\u00f3n la direcci\u00f3n del d\u00eda.", "Niveles de Asia/Londres requieren datos intraday (en proceso de recolecci\u00f3n)."], "recommendation": "Usar el POC Semanal como filtro principal de tendencia antes de buscar perfiles de sesi\u00f3n."},
  STUDY: {"title": "Patrones de Apertura NY vs POC Asia/Lon", "days": 50, "magnet_prob": "22.0%", "runaway_prob": "34.0%", "conclusion": "El Nasdaq tiene un sesgo de 'IM\u00c1N' hacia el POC combinado en un 22.0% de los d\u00edas sugeridos.", "strategy": "Colocar \u00f3rdenes limitadas en el POC combinado con stop bajo el VAL de Londres."},
  STUDY_MASTER: {"title": "Base de Datos Maestra: Sesiones y Repetici\u00f3n", "total_days": 50, "patterns": {"SWEEP_H_RETURN": "4.0%", "SWEEP_L_RETURN": "4.0%", "EXPANSION_H": "14.0%", "EXPANSION_L": "2.0%", "ROTATION_POC": "12.0%", "NEWS_DRIVE": "64.0%"}, "strongest_point": {"name": "Combined Asia+Lon POC", "stat": "100.0% \u00c9xito", "impact": "230.9 pts"}, "conclusion": "El movimiento de 'SWEEP & RETURN' (Falla) domina los lunes/martes, mientras que la 'EXPANSION' se concentra en d\u00edas de noticias rojas.", "db_summary": [{"date": "2026-03-09", "pattern": "NEWS_DRIVE", "range_h": 24495.75, "range_l": 24000.0, "c_poc": 24275.98076923077}, {"date": "2026-03-10", "pattern": "NEWS_DRIVE", "range_h": 25150.5, "range_l": 24830.0, "c_poc": 24929.25}, {"date": "2026-03-11", "pattern": "NEWS_DRIVE", "range_h": 25125.0, "range_l": 24895.75, "c_poc": 25090.03205128205}, {"date": "2026-03-12", "pattern": "NEWS_DRIVE", "range_h": 24949.25, "range_l": 24695.5, "c_poc": 24751.666666666668}, {"date": "2026-03-13", "pattern": "NEWS_DRIVE", "range_h": 24680.0, "range_l": 24397.0, "c_poc": 24585.75}]},
  STRENGTH: {"title": "Jerarqu\u00eda de Poder de Niveles", "strongest_level": "Asia POC", "success_rate": "100.0%", "avg_bounce": "229.1 pts", "reasoning": "El Asia POC es el nivel con mayor 'poder de magnetismo y rechazo'. Cuando el precio lo toca, tiene un 100.0% de probabilidad de reaccionar al menos 40 puntos.", "ranking": [{"level": "Asia POC", "frequency": "100.0%", "avg_reaction": "229.1 pts", "score": 458.11460446247463, "raw_rate": 100.0}, {"level": "London POC", "frequency": "100.0%", "avg_reaction": "220.5 pts", "score": 441.07099391480665, "raw_rate": 100.0}, {"level": "Prev Day Low", "frequency": "100.0%", "avg_reaction": "219.6 pts", "score": 439.1304347826087, "raw_rate": 100.0}, {"level": "Weekly POC", "frequency": "100.0%", "avg_reaction": "194.0 pts", "score": 387.9424860853423, "raw_rate": 100.0}, {"level": "Prev Day High", "frequency": "100.0%", "avg_reaction": "165.5 pts", "score": 331.04347826086956, "raw_rate": 100.0}]},
  RESEARCH: {"agent": 13, "name": "Explorador de Inteligencia Alpha", "last_crawl": "2026-03-18T14:21:22.476531+00:00Z", "insights": {"source": "Web Research & User DNA", "external_bias": "ESTUDIO DE BACKTESTING 3 A\u00d1OS EN CURSO", "confidence": 94, "recommendation": "Enfocarse en la 'Aceptaci\u00f3n' del precio respecto al POC de Londres en la primera hora de NY.", "discoveries": [{"source": "Sistema de Backtesting", "discovery": "Iniciando preparaci\u00f3n para Backtest de 3 a\u00f1os sobre niveles de Asia/Londres."}, {"source": "User Intel", "discovery": "Priorizaci\u00f3n de Niveles de Sesi\u00f3n Pre-Apertura (9:30 AM)."}, {"source": "Order Flow Page", "discovery": "Nueva secci\u00f3n de Mentor\u00eda IA Activa."}]}, "estrategia_maestra": {"nombre": "Fallo de Sesi\u00f3n Asia (Asia Low Sweep)", "tipo": "Liquidity Sweep", "descripcion": "El precio rompe el m\u00ednimo de la sesi\u00f3n de Asia durante Londres o NY para capturar liquidez, seguido de una recuperaci\u00f3n inmediata del POC Diario.", "reglas": ["1. Barrido (Sweep) del m\u00ednimo de Asia (Asia Low).", "2. Rechazo violento con volumen en el Footprint.", "3. Re-entrada al Value Area diaria."], "fuente": "Order Flow Masterclass", "score_alpha": "8.7/10"}, "backtest_config": {"period": "3 A\u00d1OS", "focus": "Asia/London Profiles vs NY Opening", "status": "DATA_COLLECTION_STAGE"}, "knowledge_base_size": "4.1GB", "status": "Aprendiendo patrones de Sesiones..."},
  PROTOCOLS: {"agent": 11, "timestamp": "2026-03-18T14:21:22.510777+00:00Z", "active_protocols": ["SILVER_BULLET_SNIPER"], "details": {"swing": {"active": false, "confidence": 54, "desc": "Confluencia de COT Alcista y Bias Ponderado positivo. Las instituciones est\u00e1n acumulando."}, "ict": {"active": false, "probability": 31.6, "desc": "Escenario de alta probabilidad detectado por barrido de Londres en direcci\u00f3n de la tendencia macro."}, "contrarian": {"active": false, "desc": "Miedo extremo detectado. Buscando capitulaci\u00f3n para entrada contrarian apoyada por DIX."}, "intraday": {"active": true, "window": "NY AM SB", "action": "BUSCAR FVG PARA ENTRADA"}}, "master_recommendation": "\ud83d\udd35 NEUTRAL-BULLISH (54/100) \u2014 Ligera inclinaci\u00f3n alcista \u2014 esperar confirmaci\u00f3n."},
  VOLATILITY: {"agent": 3, "name": "Volatility Analyst", "timestamp": "2026-03-18T14:21:22.307314Z", "input_source": "agent1_data.json", "raw_inputs": {"VXN": 19.49, "GEX_B": 2.3, "DIX": null}, "vxn_analysis": {"level": "NORMAL", "signal": "BULLISH", "score": 65, "description": "VXN 19.49 \u2014 Volatilidad normal. Entorno operativo est\u00e1ndar.", "risk": "Monitorear si sube sobre 25"}, "gex_analysis": {"level": "STRONG_POSITIVE", "signal": "BULLISH", "score": 70, "description": "GEX +2.30B \u2014 Dealers comprando en ca\u00eddas. Mercado amortiguado.", "impact": "Los dealers frenan la volatilidad. Movimientos m\u00e1s suaves."}, "signal": "BULLISH", "score": 67},
  ENGINE_HEALTH: {
    state: "UNKNOWN",
    last_cycle: "—",
    cycle_num: "\u2014",
    agents_ok: "\u2014",
    agents_failed: "\u2014",
    total_time_sec: "\u2014",
    data_quality: "UNKNOWN",
    any_stale: false
  },
  ENGINE_STATUS: "UNKNOWN"
};

(function sync() {
    const D = window.NQ_LIVE;
    const set = (id, val) => { 
        const el = document.getElementById(id); 
        if(el && val !== null && val !== undefined) el.innerText = val; 
    };
    
    // Global Header
    if(D.NQ.price) {
        set("hero-price", D.NQ.price.toLocaleString());
        set("nav-price", D.NQ.price.toLocaleString());
    }
    
    // COT Dashboard
    set("cot-net-val", (D.COT.net || 0).toLocaleString());
    set("hero-cot-index", (D.COT.index || 0).toFixed(1) + "%");
    const pin = document.getElementById("cot-pin");
    if(pin) pin.style.left = (D.COT.index || 0) + "%";
    
    // Summary Tables (if exist)
    const tableBody = document.getElementById("cot-table-body");
    if (tableBody && D.COT.history) {
        tableBody.innerHTML = D.COT.history.map((w, i) => `
            <tr class="${i === 0 ? 'bg-electric-cyan/5 text-white font-bold' : ''}">
                <td class="p-3 border-b border-white/5">${w.date}</td>
                <td class="p-3 text-right border-b border-white/5 text-white">${(w.net_position || 0).toLocaleString()}</td>
                <td class="p-3 text-right border-b border-white/5 text-vibrant-blue">${(w.comm_net || 0).toLocaleString()}</td>
                <td class="p-3 text-right border-b border-white/5 opacity-60">${(w.retail_net || 0).toLocaleString()}</td>
                <td class="p-3 text-right border-b border-white/5 font-mono opacity-40">${(w.oi || 0).toLocaleString()}</td>
            </tr>
        `).join("");
    }

    // ─── ENGINE HEALTH WIDGET ──────────────────────────────
    const H = D.ENGINE_HEALTH;
    const pulse = document.getElementById("neural-pulse-status");
    if(pulse) {
        const stateEmoji = H.state === "OPTIMAL" ? "✅" : H.state === "DEGRADED" ? "🟡" : H.state === "CRITICAL" ? "🔴" : "⚪";
        const staleWarning = H.any_stale ? " ⚠️ STALE" : "";
        pulse.innerText = `${stateEmoji} ENGINE ${H.state}${staleWarning} · Ciclo #${H.cycle_num} · ${H.last_cycle} · ${H.agents_ok} OK / ${H.agents_failed} FAIL · ${H.total_time_sec}s`;
    }
    
    // Si hay IDs específicos del health widget
    set("engine-state",    H.state);
    set("engine-cycle",    "#" + H.cycle_num);
    set("engine-last",     H.last_cycle);
    set("engine-ok",       H.agents_ok + " OK");
    set("engine-fail",     H.agents_failed + " FAIL");
    set("engine-time",     H.total_time_sec + "s");
    set("engine-quality",  H.data_quality + (H.any_stale ? " ⚠️" : " ✅"));

    // ─── AUDITORÍA ALGORÍTMICA ─────────────────────────────────────────────
    const P   = D.PROTOCOLS?.details || {};
    const activeProtos = D.PROTOCOLS?.active_protocols || [];

    // SMC Detective Card
    const smcSignal = P.ict?.active     ? "ICT ACTIVE"
                    : P.swing?.active   ? "SWING ACTIVE"
                    : P.intraday?.active? "INTRADAY ACTIVE"
                    : "SCANNING";
    const smcColor  = smcSignal === "SCANNING" ? "#94a3b8"
                    : smcSignal.includes("ICT") ? "#00ffc8" : "#c084fc";
    const smcEl = document.getElementById("smc-signal");
    if (smcEl) { smcEl.textContent = smcSignal; smcEl.style.color = smcColor; }

    set("smc-details",   D.PROTOCOLS?.master_recommendation || "Analizando huellas institucionales...");
    set("smc-ob-price",  D.ORDERFLOW?.sessions?.london?.poc != null
                            ? D.ORDERFLOW.sessions.london.poc.toFixed(2) : "—");
    set("smc-fvg",       P.intraday?.active
                            ? "FVG DETECTED · " + (P.intraday?.window || "—") : "No detectado");
    set("ict-pd",        P.ict?.active         ? "Premium Array" : "Neutral");
    set("ict-sweep",     D.ORDERFLOW?.bias_orderflow || "—");
    set("ict-wr-bull",   D.BACKTEST?.win_rate != null
                            ? D.BACKTEST.win_rate.toFixed(1) + "%" : "--%");
    set("ict-wr-bear",   D.BACKTEST?.win_rate != null
                            ? (100 - D.BACKTEST.win_rate).toFixed(1) + "%" : "--%");

    // Probability Analyst Card
    set("prob-expectancy", D.BACKTEST?.win_rate != null
                            ? D.BACKTEST.win_rate.toFixed(1) + "%" : "—%");
    set("prob-verdict",    D.PROTOCOLS?.master_recommendation
                            || D.PROTOCOLS?.details?.intraday?.desc
                            || "Calculando confluencias...");

    // Silver Bullet Card
    const sbProto = activeProtos[0] || "SCANNING";
    set("sb-status",    sbProto.replace(/_/g, " "));
    set("sb-window",    P.intraday?.window
                            ? "Ventana: " + P.intraday.window : "Fuera de ventana");
    set("sb-countdown", P.intraday?.action || "—");

    // Protocol Badges (junto al título)
    const badgeEl = document.getElementById("active-protocols-list");
    if (badgeEl && activeProtos.length > 0) {
        badgeEl.innerHTML = activeProtos.map(p =>
            `<span style="font-size:8px;padding:2px 10px;border-radius:100px;
                background:rgba(0,255,200,0.08);border:1px solid rgba(0,255,200,0.3);
                color:#00ffc8;font-family:'JetBrains Mono',monospace;letter-spacing:0.05em;">
                ${p.replace(/_/g," ")}
            </span>`
        ).join("");
    }
})();
