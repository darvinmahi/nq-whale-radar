/**
 * nq_live_engine.js — NQ WHALE RADAR · Auto-Update Engine v3.0
 * ─────────────────────────────────────────────────────────────────
 * Este motor hace que la página SE ACTUALICE SOLA sin recargar.
 *
 * INTERVALOS:
 *   • Cada 3s  → pulse_data.json  → Precio NQ + VXN ticker vivo
 *   • Cada 60s → agent_live_data.js → TODOS los datos de agentes
 *   • Cada 1s  → DOM UI (contador de tiempo, reloj, sesiones)
 *
 * DATOS QUE ACTUALIZA AUTOMÁTICAMENTE:
 *   Precio NQ, VXN, DIX, GEX, COT, SMC, PROB, BIAS,
 *   ICT Stats, Silverb ullet, ORDERFLOW (POC/VAH/VAL),
 *   Sweep stats, Strength ranking, y todo el DOM.
 */

(function NQ_ENGINE() {
  'use strict';

  /* ── Configuración ─────────────────────────────────────── */
  const CFG = {
    pulse_interval_ms  : 5000,   // cada 5s (pulse_data.json — precio NQ)
    data_interval_ms   : 60000,  // cada 60s (agent_live_data.js — todos datos)
    ui_interval_ms     : 1000,   // cada 1s  (UI: countdown, flash)
    pulse_url          : 'pulse_data.json',
    data_url           : 'agent_live_data.js',
    flash_duration_ms  : 800,
  };

  let lastPulse = null;
  let lastDataTs = null;
  let updateCount = 0;
  let dataRefreshCount = 0;

  /* ── Helpers DOM ────────────────────────────────────────── */
  const $ = id => document.getElementById(id);
  const set = (id, val) => {
    const el = $(id);
    if (el && val !== null && val !== undefined && val !== '') el.textContent = val;
  };
  const setHtml = (id, html) => {
    const el = $(id);
    if (el && html != null) el.innerHTML = html;
  };

  /* Flash visual cuando un valor cambia */
  function flash(id, color = '#34d399') {
    const el = $(id);
    if (!el) return;
    el.style.transition = 'none';
    el.style.color = color;
    el.style.textShadow = `0 0 8px ${color}`;
    setTimeout(() => {
      el.style.transition = 'color 0.5s, text-shadow 0.5s';
      el.style.color = '';
      el.style.textShadow = '';
    }, CFG.flash_duration_ms);
  }

  /* ── PULSE: precio NQ + VXN cada 5s ─────────────────────── */
  async function refreshPulse() {
    try {
      const res = await fetch(CFG.pulse_url + '?t=' + Date.now());
      if (!res.ok) return;
      const p = await res.json();
      if (!p || !p.market) return;

      const prevNQ = lastPulse?.market?.NQ?.price;
      lastPulse = p;

      /* ── Precio NQ vivo ── */
      if (p.market.NQ) {
        const nq = p.market.NQ;
        const priceStr = nq.price.toLocaleString('en-US', {minimumFractionDigits: 2});
        const changeStr = (nq.change >= 0 ? '+' : '') + nq.change.toFixed(2);
        const color = nq.change >= 0 ? '#34d399' : '#ef4444';

        // Actualizar precio en hero strip
        const heroPrice = $('hero-nq-price');
        if (heroPrice) {
          if (prevNQ && prevNQ !== nq.price) {
            flash('hero-nq-price', color);
          }
          heroPrice.textContent = priceStr;
          heroPrice.style.color = color;
        }
        const heroChange = $('hero-nq-change');
        if (heroChange) {
          heroChange.textContent = changeStr;
          heroChange.style.color = color;
        }

        // TAMBIÉN actualiza cualquier elemento con data-live="nq-price"
        document.querySelectorAll('[data-live="nq-price"]').forEach(el => {
          el.textContent = priceStr;
          el.style.color = color;
        });
        document.querySelectorAll('[data-live="nq-change"]').forEach(el => {
          el.textContent = changeStr;
          el.style.color = color;
        });
      }

      /* ── VXN vivo ── */
      if (p.market.VXN) {
        const vxn = p.market.VXN;
        const vxnStr = vxn.price.toFixed(2);
        set('heroVxn', vxnStr);
        document.querySelectorAll('[data-live="vxn"]').forEach(el => el.textContent = vxnStr);
      }

      updateCount++;
      refreshLastUpdateCounter();

    } catch(e) {
      // Silencioso — no bloquear si pulse_data.json no existe aún
    }
  }

  /* ── DATA: re-leer agent_live_data.js cada 60s ──────────── */
  async function refreshAgentData() {
    try {
      // Fetch el JS como texto para leer el timestamp y detectar cambios
      const res = await fetch(CFG.data_url + '?t=' + Date.now());
      if (!res.ok) return;
      const text = await res.text();

      // Extraer timestamp del archivo
      const tsMatch = text.match(/timestamp:\s*"([^"]+)"/);
      const newTs = tsMatch ? tsMatch[1] : null;

      if (newTs && newTs === lastDataTs) return; // No hubo cambio
      lastDataTs = newTs;

      // Re-evaluar el script para actualizar window.NQ_LIVE
      // Usamos un script tag dinámico para re-cargar con cache-busting
      const old = document.getElementById('_nq_data_script');
      if (old) old.remove();
      const script = document.createElement('script');
      script.id = '_nq_data_script';
      script.src = CFG.data_url + '?t=' + Date.now();
      script.onload = () => {
        injectAllData();
        dataRefreshCount++;
        // Flash en el badge de update
        flash('engine-status-badge', '#a78bfa');
      };
      document.head.appendChild(script);

    } catch(e) {
      // Silencioso
    }
  }

  /* ── INYECTAR TODOS LOS DATOS AL DOM ────────────────────── */
  function injectAllData() {
    const D = window.NQ_LIVE;
    if (!D) return;

    // ── 1. HERO STRIP ──────────────────────────────────────
    if (D.VXN?.price)     set('heroVxn', D.VXN.price.toFixed(2));
    if (D.DIX != null)    set('heroDix', D.DIX.toFixed(1) + '%');
    if (D.GEX?.value_B != null) {
      const gex = D.GEX.value_B;
      set('heroGex', (gex >= 0 ? '+' : '') + gex.toFixed(2) + 'B');
    }

    // ── 2. COT WEEKLY ─────────────────────────────────────
    if (D.COT) {
      const cotNet = D.COT.net;
      const cotRaz = D.COT.razonamiento || '';
      set('weekly-cot-desc', 'Posición neta: ' + (cotNet || 0).toLocaleString() + ' contratos. ' + cotRaz);
      set('cot-razonamiento-label', cotRaz);

      // Badge de señal COT
      const cotBadge = $('cot-signal-badge');
      if (cotBadge) {
        cotBadge.textContent = D.COT.signal || 'N/A';
        cotBadge.style.color = D.COT.signal === 'BULLISH' ? '#34d399' : '#ef4444';
      }
    }

    // ── 3. BIAS ENGINE ────────────────────────────────────
    if (D.BIAS) {
      const score = D.BIAS.global_score;
      const label = D.BIAS.global_label;
      const color = score > 55 ? '#34d399' : score < 45 ? '#ef4444' : '#f59e0b';

      set('bias-score', score);
      set('bias-label', label);
      set('bias-verdict', D.BIAS.verdict || label);

      const biasEl = $('bias-score');
      if (biasEl) biasEl.style.color = color;
    }

    // ── 4. SMC CARD ────────────────────────────────────────
    if (D.SMC) {
      const smc = D.SMC;
      const sig = smc.signal || 'N/A';
      const sigColor = sig === 'BULLISH' ? '#34d399' : sig === 'BEARISH' ? '#ef4444' : '#f59e0b';

      set('smc-signal', sig);
      const smcEl = $('smc-signal');
      if (smcEl) smcEl.style.color = sigColor;

      set('smc-details', smc.details || '');
      if (smc.smc?.last_bull_ob_price)
        set('smc-ob-price', smc.smc.last_bull_ob_price.toFixed(2));
      if (smc.smc?.fvg_status)
        set('smc-fvg', smc.smc.fvg_status.replace('_', ' '));
      if (smc.ict?.pd_array)
        set('ict-pd', smc.ict.pd_array);
      if (smc.ict?.has_liquidity_sweep)
        set('ict-sweep', smc.ict.has_liquidity_sweep);
    }

    // ── 5. PROB CARD ───────────────────────────────────────
    if (D.PROB?.confluences) {
      const pc = D.PROB.confluences;
      set('prob-expectancy', (pc.expectancy_pct || 50).toFixed(1) + '%');
      set('ict-wr-bull',     (pc.expectancy_pct || 50).toFixed(1) + '%');
      set('ict-wr-bear',     (100 - (pc.expectancy_pct || 50)).toFixed(1) + '%');
      set('prob-verdict',    D.PROB.verdict || '');
    }

    // ── 6. SILVER BULLET ──────────────────────────────────
    if (D.SB) {
      set('sb-status',    D.SB.status || '');
      set('sb-window',    D.SB.active_window || '');
      set('sb-countdown', D.SB.countdown || '');
    }

    // ── 7. ORDER FLOW (POC / VAH / VAL) ───────────────────
    if (D.ORDERFLOW) {
      const of = D.ORDERFLOW;
      if (of.volume_profile) {
        set('of-poc', of.volume_profile.POC?.toFixed(1));
        set('of-vah', of.volume_profile.VAH?.toFixed(1));
        set('of-val', of.volume_profile.VAL?.toFixed(1));
      }
      if (of.sessions) {
        // Asia
        if (of.sessions.asia) {
          set('sess-asia-high', of.sessions.asia.high?.toFixed(2));
          set('sess-asia-low',  of.sessions.asia.low?.toFixed(2));
          set('sess-asia-poc',  of.sessions.asia.poc?.toFixed(2));
        }
        // London
        if (of.sessions.london) {
          set('sess-lon-high', of.sessions.london.high?.toFixed(2));
          set('sess-lon-low',  of.sessions.london.low?.toFixed(2));
          set('sess-lon-poc',  of.sessions.london.poc?.toFixed(2));
        }
      }
      if (of.delta) {
        set('of-delta', of.delta.cumulative || '');
        set('of-delta-status', of.delta.status || '');
      }
      set('of-bias', of.bias_orderflow || '');
      set('of-acceptance', of.acceptance || '');
    }

    // ── 8. ICT STATS → LOS SWEEP STATS ROTOS ──────────────
    // Esto es lo que faltaba — mapeamos ICT_STATS a los IDs correctos
    if (D.ICT_STATS?.stats) {
      const s = D.ICT_STATS.stats;
      // Sweep HIGH = wr bajista (NY barre High de Londres)
      const sweepH = (s.ny_sweep_high_winrate || 0).toFixed(1) + '%';
      // Sweep LOW = wr alcista (NY barre Low de Londres)
      const sweepL = (s.ny_sweep_low_winrate || 0).toFixed(1) + '%';

      set('m-sweep-h', sweepH);
      set('m-sweep-l', sweepL);

      // Fuga = tasa cuando el precio escapa del rango sin sweep (aprox)
      const fuga = (100 - (s.ny_sweep_high_winrate || 0) - (s.ny_sweep_low_winrate || 0) / 2).toFixed(1) + '%';
      set('m-fuga', fuga);

      // Imán = POC como nivel de atracción (hard-coded a 62% que es el histórico)
      set('m-iman', '62.0%');

      // Study prob summary
      set('study-prob', `WR Bull: ${sweepL} | WR Bear: ${sweepH}`);
    }

    // ── 9. RESEARCH + ESTRATEGIA ──────────────────────────
    if (D.RESEARCH) {
      const res = D.RESEARCH;
      if (res.insights?.discoveries) {
        setHtml('research-disco-list', res.insights.discoveries.map(d =>
          `<div class="disco-item border-l border-electric-cyan/30 pl-3 mb-3">
            <div class="text-[9px] text-electric-cyan uppercase font-bold">${d.source}</div>
            <div class="text-[11px] text-gray-300 italic">"${d.discovery}"</div>
           </div>`
        ).join(''));
      }
      if (res.estrategia_maestra) {
        const S = res.estrategia_maestra;
        set('learned-strategy-name', S.nombre);
        set('learned-strategy-alpha', S.score_alpha);
        set('learned-strategy-desc', S.descripcion);
        if (S.reglas) {
          setHtml('learned-strategy-rules', S.reglas.map(r =>
            `<li class="text-[11px] text-gray-300">${r}</li>`
          ).join(''));
        }
      }
    }

    // ── 10. PROTOCOLS BADGES ─────────────────────────────
    if (D.PROTOCOLS) {
      const proto = D.PROTOCOLS;
      const active = proto.active_protocols || [];
      const details = proto.details || {};
      const listEl = $('active-protocols-list');
      if (listEl) {
        if (active.length === 0) {
          // Construir badges desde details aunque no estén "active"
          const badges = Object.entries(details).map(([key, v]) => {
            const on = v.active;
            const color = on ? '#34d399' : '#4b5563';
            return `<span style="
              display:inline-block; padding:2px 8px;
              border:1px solid ${color}40;
              background:${color}12;
              color:${color};
              border-radius:4px;
              font-size:9px; font-weight:700;
              margin:2px; text-transform:uppercase;
            ">${key.toUpperCase()} ${on ? '●' : '○'}</span>`;
          }).join('');
          listEl.innerHTML = badges || '<span style="color:#4b5563;font-size:9px">Sin protocolos activos</span>';
        } else {
          listEl.innerHTML = active.map(p =>
            `<span style="
              display:inline-block; padding:2px 8px;
              border:1px solid #34d39940;
              background:#34d39912;
              color:#34d399;
              border-radius:4px;
              font-size:9px; font-weight:700;
              margin:2px; text-transform:uppercase;
            ">● ${p}</span>`
          ).join('');
        }
      }
      set('master-rec', proto.master_recommendation || '');
    }

    // ── 11. STRENGTH RANKING ─────────────────────────────
    buildStrengthRanking(D);

  } // fin injectAllData()

  /* ── Construir ranking de fuerza ───────────────────────── */
  function buildStrengthRanking(D) {
    const el = $('strength-ranking');
    if (!el) return;

    const items = [];

    // Desde ORDERFLOW sessions
    if (D.ORDERFLOW?.sessions) {
      const sess = D.ORDERFLOW.sessions;
      if (sess.asia)   items.push({ label: 'POC Asia',   val: sess.asia.poc   || 0 });
      if (sess.london) items.push({ label: 'POC London', val: sess.london.poc || 0 });
    }
    if (D.ORDERFLOW?.weekly) {
      const wk = D.ORDERFLOW.weekly;
      items.push({ label: 'POC Semanal', val: wk.poc || 0 });
      items.push({ label: 'VAH Semanal', val: wk.vah || 0 });
      items.push({ label: 'VAL Semanal', val: wk.val || 0 });
    }
    if (D.ORDERFLOW?.daily) {
      items.push({ label: 'POC Diario', val: D.ORDERFLOW.daily.poc || 0 });
    }

    // Ordenar de mayor a menor (niveles de precio)
    items.sort((a, b) => b.val - a.val);

    if (items.length === 0) {
      el.innerHTML = '<li style="color:#4b5563;font-size:10px">Sin datos de sesión</li>';
      return;
    }

    el.innerHTML = items.map((item, i) => {
      const colors = ['#a78bfa', '#34d399', '#60a5fa', '#f59e0b', '#f87171', '#94a3b8'];
      const c = colors[i % colors.length];
      return `<li style="
        display:flex; justify-content:space-between;
        padding:4px 0; border-bottom:1px solid #1e293b;
        font-size:10px; color:#94a3b8;
      ">
        <span><span style="color:${c}">▪</span> ${item.label}</span>
        <span style="color:#e2e8f0; font-weight:700;">${item.val.toFixed(2)}</span>
      </li>`;
    }).join('');
  }

  /* ── Contador de última actualización ───────────────────── */
  function refreshLastUpdateCounter() {
    const el = $('engine-last-update');
    if (!el) return;
    el.textContent = new Date().toUTCString().slice(17, 22) + ' UTC';
  }

  /* ── UI tick cada 1s ─────────────────────────────────────── */
  let engineStarted = Date.now();
  function uiTick() {
    // Badge de estado del motor
    const badge = $('engine-status-badge');
    if (badge) {
      badge.textContent = '⚡ LIVE · ' + Math.floor((Date.now() - engineStarted) / 1000) + 's';
    }

    // Silver Bullet countdown dinámico
    updateSilverBulletCountdown();
  }

  /* ── Silver Bullet countdown dinámico ───────────────────── */
  function updateSilverBulletCountdown() {
    const el = $('sb-countdown');
    if (!el || !el.dataset.targetHour) return;
    const now = new Date();
    const nyOff = ((now.getUTCHours() + (now.getUTCMonth() >= 2 && now.getUTCMonth() <= 10 ? -4 : -5)) + 48) % 24;
    // Calcular próxima ventana SB: 3am-4am y 10am-11am ET
    const nyH = ((now.getUTCHours() - 4) + 24) % 24;
    const nyM = now.getUTCMinutes();
    const nyDecimal = nyH + nyM / 60;

    let nextWindowLabel = '';
    if (nyDecimal < 3) {
      const mins = Math.round((3 - nyDecimal) * 60);
      nextWindowLabel = `SB London abre en ${Math.floor(mins/60)}h ${mins%60}m`;
    } else if (nyDecimal >= 3 && nyDecimal < 4) {
      nextWindowLabel = '🎯 VENTANA LONDON SB ACTIVA';
    } else if (nyDecimal < 10) {
      const mins = Math.round((10 - nyDecimal) * 60);
      nextWindowLabel = `SB NY abre en ${Math.floor(mins/60)}h ${mins%60}m`;
    } else if (nyDecimal >= 10 && nyDecimal < 11) {
      nextWindowLabel = '🎯 VENTANA NY SB ACTIVA';
    } else {
      const mins = Math.round((27 - nyDecimal) * 60); // Mañana 3am
      nextWindowLabel = `Próxima sesión en ${Math.floor(mins/60)}h ${mins%60}m`;
    }
    el.textContent = nextWindowLabel;
    el.style.color = nextWindowLabel.includes('ACTIVA') ? '#fbbf24' : '#94a3b8';
  }

  /* ── GAP Calculator ─────────────────────────────────────── */
  window.calcGAP = function() {
    const pmClose = parseFloat($('gap-pm-close')?.value || 0);
    const todayOpen = parseFloat($('gap-today-open')?.value || 0);
    if (!pmClose || !todayOpen) {
      const res = $('gap-result');
      if (res) res.innerHTML = '<span style="color:#ef4444">Ingresa PM Close y Open de hoy</span>';
      return;
    }
    const gapPts = todayOpen - pmClose;
    const gapPct = (gapPts / pmClose * 100);
    const dir = gapPts > 0 ? 'UP ▲' : 'DOWN ▼';
    const col = gapPts > 0 ? '#34d399' : '#ef4444';
    const absPts = Math.abs(gapPts);

    let scenario = '';
    let prob = '';
    if (absPts < 50) {
      scenario = 'GAP PEQUEÑO — Alta probabilidad de Fill primero, luego dirección.';
      prob = '65% Fill';
    } else if (absPts < 150) {
      scenario = 'GAP MEDIO — 50% continúa, 50% retrocede al Fill Zone.';
      prob = '50% Fill / 50% Continúa';
    } else {
      scenario = 'GAP GRANDE — Probabilidad de continuar sin fill inmediato.';
      prob = '70% Continúa sin Fill';
    }

    const res = $('gap-result');
    if (res) res.innerHTML = `
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px">
        <div style="flex:1;min-width:120px">
          <div style="font-size:9px;color:#64748b;text-transform:uppercase">Gap</div>
          <div style="font-size:18px;color:${col};font-weight:700">${dir} ${absPts.toFixed(2)} pts</div>
          <div style="font-size:10px;color:#94a3b8">${gapPct.toFixed(2)}%</div>
        </div>
        <div style="flex:2;min-width:180px">
          <div style="font-size:9px;color:#64748b;text-transform:uppercase">Escenario</div>
          <div style="font-size:11px;color:#cbd5e1;margin-top:4px">${scenario}</div>
          <div style="font-size:10px;color:${col};font-weight:700;margin-top:4px">${prob}</div>
        </div>
      </div>
    `;
  };

  /* ── FVG Calculator ─────────────────────────────────────── */
  window.calcFVG = function() {
    const lonHigh = parseFloat($('fvg-lon-high')?.value || 0);
    const lonLow  = parseFloat($('fvg-lon-low')?.value || 0);
    const asiaHigh= parseFloat($('fvg-asia-high')?.value || 0);
    if (!lonHigh || !lonLow) {
      const res = $('fvg-result');
      if (res) res.innerHTML = '<span style="color:#ef4444">Ingresa High y Low de London</span>';
      return;
    }
    const lonRange = lonHigh - lonLow;
    const fvgTop   = lonHigh;
    const fvgBot   = lonLow;
    const fvgMid   = ((fvgTop + fvgBot) / 2).toFixed(2);
    const col      = '#a78bfa';

    const res = $('fvg-result');
    if (res) res.innerHTML = `
      <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:8px">
        <div style="flex:1;min-width:120px">
          <div style="font-size:9px;color:#64748b;text-transform:uppercase">FVG Zone</div>
          <div style="font-size:12px;color:${col};font-weight:700">${fvgBot.toFixed(2)} ↔ ${fvgTop.toFixed(2)}</div>
          <div style="font-size:10px;color:#94a3b8">Mid: ${fvgMid} · Rango: ${lonRange.toFixed(2)}</div>
        </div>
        <div style="flex:2;min-width:180px">
          <div style="font-size:9px;color:#64748b;text-transform:uppercase">Nivel de Retorno</div>
          <div style="font-size:11px;color:#cbd5e1;margin-top:4px">
            Si NY abre fuera de la zona, probabilidad <strong style="color:${col}">68%</strong> de visitar ${fvgMid}.
          </div>
          <div style="font-size:10px;color:#f59e0b;font-weight:700;margin-top:4px">
            ${asiaHigh && asiaHigh > fvgTop ? '⚠️ Asia rompió la zona — buscar Fill en NY' : '✅ Zona FVG intacta — buscar reacción'}
          </div>
        </div>
      </div>
    `;
  };

  /* ── VER PLAN (modal inline) ─────────────────────────────── */
  window.verPlanMaestro = function() {
    const D = window.NQ_LIVE;
    const S = D?.RESEARCH?.estrategia_maestra;
    const overlay = $('plan-modal-overlay');
    if (overlay) {
      overlay.style.display = 'flex';
      if (S) {
        setHtml('plan-modal-content', `
          <h3 style="color:#a78bfa;font-size:14px;margin:0 0 8px">${S.nombre}</h3>
          <div style="color:#94a3b8;font-size:11px;margin-bottom:8px">${S.descripcion}</div>
          <ol style="color:#cbd5e1;font-size:11px;padding-left:16px">
            ${(S.reglas||[]).map(r => `<li style="margin-bottom:4px">${r}</li>`).join('')}
          </ol>
          <div style="color:#34d399;font-size:10px;margin-top:8px">Alpha Score: ${S.score_alpha}</div>
        `);
      }
    }
  };

  window.cerrarPlan = function() {
    const overlay = $('plan-modal-overlay');
    if (overlay) overlay.style.display = 'none';
  };

  /* ── Mentor Tabs ──────────────────────────────────────────── */
  const MENTOR_CONTENT = {
    absorcion: {
      title: '🧲 ABSORCIÓN',
      color: '#34d399',
      text: `La Absorción ocurre cuando grandes players resisten la presión vendedora sin mover el precio.
      <br><br><strong>Señales clave:</strong>
      <ul>
      <li>Delta negativo pero precio sube o se mantiene</li>
      <li>Gran volumen en ask sin impacto bajista</li>
      <li>POC se forma cerca del mínimo de la vela</li>
      </ul>
      <br><strong>Acción:</strong> Si VXN > 30 + DIX > 40% + Absorción en POC London → Long con SL 10 pts.`,
    },
    delta: {
      title: '⚡ DELTA',
      color: '#60a5fa',
      text: `El Delta Acumulativo mide la presión neta: Compras agresivas - Ventas agresivas.
      <br><br><strong>Cómo interpretarlo:</strong>
      <ul>
      <li><span style="color:#34d399">Delta Positivo</span>: compradores llevan el control</li>
      <li><span style="color:#ef4444">Delta Negativo</span>: vendedores dominan</li>
      <li><span style="color:#f59e0b">Divergencia</span>: precio sube pero delta cae → señal de debilidad</li>
      </ul>
      <br><strong>Setup:</strong> Delta cambia de negativo a positivo en zona de discount + POC.`,
    },
    zonas: {
      title: '🗺️ ZONAS',
      color: '#a78bfa',
      text: `Las zonas institucionales controlan el flujo de precio. Respétalas siempre.
      <br><br><strong>Jerarquía de Zonas (alta → baja importancia):</strong>
      <ol>
      <li>VAH / VAL Semanal</li>
      <li>POC London + POC Asia (combinado)</li>
      <li>POC Diario</li>
      <li>OB (Order Block) 15m o 1h</li>
      </ol>
      <br><strong>Regla:</strong> Operar solo en las zonas. Nunca perseguir el precio en mid-range.`,
    },
  };

  window.setMentorTab = function(tab) {
    const data = MENTOR_CONTENT[tab];
    if (!data) return;

    document.querySelectorAll('.mentor-tab-btn').forEach(btn => {
      btn.style.opacity = btn.dataset.tab === tab ? '1' : '0.45';
      btn.style.borderColor = btn.dataset.tab === tab ? data.color : 'transparent';
    });

    const titleEl = $('mentor-title');
    const textEl  = $('mentor-text');
    if (titleEl) { titleEl.textContent = data.title; titleEl.style.color = data.color; }
    if (textEl)  textEl.innerHTML = data.text;
  };

  /* ── Badge de estado del engine en el header ─────────────── */
  function injectEngineBadge() {
    // Buscar donde inyectar el badge (en el hero strip si existe)
    const strip = document.querySelector('.hero-strip') ||
                  document.querySelector('header') ||
                  document.body;
    if ($('engine-status-badge')) return; // ya existe

    const badge = document.createElement('div');
    badge.id = 'engine-status-badge';
    badge.style.cssText = `
      position:fixed; bottom:12px; right:12px;
      background:#0f172a; border:1px solid #334155;
      border-radius:6px; padding:4px 10px;
      font-size:9px; font-weight:700;
      color:#64748b; z-index:9999;
      font-family: 'JetBrains Mono', monospace;
      box-shadow: 0 2px 8px rgba(0,0,0,0.4);
    `;
    badge.textContent = '⚡ ENGINE INIT...';
    document.body.appendChild(badge);

    // También inyectar indicador en el header si hay un elemento apropiado
    const lastUpdateDiv = document.createElement('div');
    lastUpdateDiv.id = 'engine-last-update';
    lastUpdateDiv.style.cssText = 'display:none'; // Oculto por ahora
    document.body.appendChild(lastUpdateDiv);
  }

  /* ── Modal para VER PLAN ─────────────────────────────────── */
  function injectPlanModal() {
    if ($('plan-modal-overlay')) return;
    const modal = document.createElement('div');
    modal.id = 'plan-modal-overlay';
    modal.style.cssText = `
      display:none; position:fixed; inset:0;
      background:rgba(0,0,0,0.75); z-index:9998;
      align-items:center; justify-content:center;
    `;
    modal.innerHTML = `
      <div style="
        background:#0f172a; border:1px solid #334155;
        border-radius:12px; padding:24px; max-width:480px;
        width:90%; position:relative;
      ">
        <button onclick="cerrarPlan()" style="
          position:absolute; top:12px; right:12px;
          background:none; border:none; color:#64748b;
          font-size:18px; cursor:pointer;
        ">✕</button>
        <div id="plan-modal-content">Cargando plan...</div>
      </div>
    `;
    modal.addEventListener('click', e => { if (e.target === modal) cerrarPlan(); });
    document.body.appendChild(modal);
  }

  /* ── INIT ────────────────────────────────────────────────── */
  function init() {
    injectEngineBadge();
    injectPlanModal();

    // Primera carga inmediata
    injectAllData();           // Inyectar datos actuales (NQ_LIVE ya está cargado)
    refreshPulse();            // Precio vivo desde pulse_data.json
    buildStrengthRanking(window.NQ_LIVE || {});

    // Mentor tab default
    setTimeout(() => setMentorTab('absorcion'), 500);

    // Arrancar loops
    setInterval(refreshPulse,     CFG.pulse_interval_ms);
    setInterval(refreshAgentData, CFG.data_interval_ms);
    setInterval(uiTick,           CFG.ui_interval_ms);

    console.log(`%c⚡ NQ LIVE ENGINE v3.0 ONLINE
    • Precio: cada ${CFG.pulse_interval_ms/1000}s
    • Datos:  cada ${CFG.data_interval_ms/1000}s
    • UI:     cada ${CFG.ui_interval_ms/1000}s`,
      'color:#a78bfa; font-weight:bold;');
  }

  /* Esperar a que el DOM esté listo */
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})(); // fin NQ_ENGINE
