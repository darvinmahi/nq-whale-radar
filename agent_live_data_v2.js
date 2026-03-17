/**
 * agent_live_data.js — NQ Intelligence v2.0
 * ─────────────────────────────────────────
 * Motor de bias institucional para Nasdaq
 * 7 señales: COT + VXN + Futuros Premium + DIX + Rotación + Sectores + Put/Call
 * Actualización: cada 60s
 */

const PROXY = 'https://corsproxy.io/?';

// ── COT — Actualización manual cada viernes 3:30pm ET ────────────────────────
const COT_DATA = {
  date: '07 Mar 2026',
  asset_managers_net: 67583,
  prev_week_net: 65197,
  consecutive_weeks: -3,   // negativo = reduciendo
  cot_index: 27,            // 0-100 vs 3 años
  hist_min: 52000,
  hist_max: 142000,
};

// ── ESTADO GLOBAL ─────────────────────────────────────────────────────────────
const LIVE = {
  ndx:       null,
  nq_fut:    null,
  vxn:       null,
  vix:       null,
  dix:       null,
  dix_trend: 0,
  gex:       null,
  putcall:   null,
  qqq:       null,
  spy:       null,
  xlk:       null,
  soxx:      null,
  cot:       COT_DATA,
  ts:        null,
};

// ── FETCH YAHOO FINANCE ───────────────────────────────────────────────────────
async function fetchYahoo(symbol) {
  try {
    const url = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=5d`;
    const res = await fetch(PROXY + encodeURIComponent(url));
    const data = await res.json();
    const result = data?.chart?.result?.[0];
    if (!result) return null;
    const meta = result.meta;
    const price = meta.regularMarketPrice;
    const prev  = meta.previousClose || meta.chartPreviousClose;
    const chg   = prev ? ((price - prev) / prev * 100) : 0;
    const closes = result.indicators?.quote?.[0]?.close?.filter(Boolean) || [];
    return { price, prev, chg, closes };
  } catch(e) {
    console.warn(`[NQ] Yahoo ${symbol} error:`, e.message);
    return null;
  }
}

// ── FETCH DIX + GEX ───────────────────────────────────────────────────────────
async function fetchDIX() {
  try {
    const url = 'https://squeezemetrics.com/monitor/static/DIX.csv';
    const res = await fetch(PROXY + encodeURIComponent(url));
    const text = await res.text();
    const rows = text.trim().split('\n');
    const recent = rows.slice(-5).map(r => {
      const c = r.split(',');
      return { date: c[0], dix: parseFloat(c[1]) * 100, gex: parseFloat(c[2]) };
    });
    const last = recent[recent.length - 1];
    const prev = recent[recent.length - 2];
    return {
      dix: last.dix,
      gex: last.gex,
      dix_trend: prev ? last.dix - prev.dix : 0,
    };
  } catch(e) {
    console.warn('[NQ] DIX error:', e.message);
    return null;
  }
}

// ── SEÑAL 1: VXN + VIX SPREAD ────────────────────────────────────────────────
function signalVXN() {
  if (!LIVE.vxn) return { score: 0, label: 'N/A', detail: 'Esperando VXN...' };
  const v = LIVE.vxn.price;
  const spread = LIVE.vix ? (v - LIVE.vix.price) : null;

  let score;
  if      (v < 15) score =  1.0;
  else if (v < 18) score =  0.7;
  else if (v < 22) score =  0.2;
  else if (v < 25) score = -0.3;
  else if (v < 30) score = -0.7;
  else             score = -1.0;

  if (spread !== null && spread > 5) score -= 0.2;

  const label = score > 0.3 ? 'BAJO · ALCISTA' : score < -0.3 ? 'ELEVADO · BAJISTA' : 'NEUTRO';
  const spreadTxt = spread !== null ? ` | spread VIX: ${spread >= 0 ? '+' : ''}${spread.toFixed(1)}pts` : '';
  const detail = `VXN ${v.toFixed(2)}${spreadTxt} — ${label}`;

  return { score: Math.max(-1, Math.min(1, score)), label, detail, value: v };
}

// ── SEÑAL 2: NQ FUTURES PREMIUM ──────────────────────────────────────────────
function signalFuturesPremium() {
  if (!LIVE.nq_fut || !LIVE.ndx) return { score: 0, label: 'N/A', detail: 'Esperando futuros...' };

  const ndx = LIVE.ndx.price;
  const fut = LIVE.nq_fut.price;
  const premiumPct = ((fut - ndx) / ndx) * 100;

  let score, label;
  if      (premiumPct >  0.4) { score =  0.9; label = 'PREMIUM FUERTE · ALCISTA'; }
  else if (premiumPct >  0.1) { score =  0.4; label = 'PREMIUM NORMAL'; }
  else if (premiumPct > -0.1) { score =  0.0; label = 'NEUTRO'; }
  else if (premiumPct > -0.4) { score = -0.4; label = 'DESCUENTO · CAUTELA'; }
  else                        { score = -0.9; label = 'DESCUENTO FUERTE · BAJISTA'; }

  const detail = `NQ Fut ${fut.toFixed(0)} vs NDX ${ndx.toFixed(0)} | Premium: ${premiumPct >= 0 ? '+' : ''}${premiumPct.toFixed(2)}%`;
  return { score, label, detail, value: premiumPct };
}

// ── SEÑAL 3: DIX (DARK POOLS + TENDENCIA) ────────────────────────────────────
function signalDIX() {
  if (LIVE.dix === null) return { score: 0, label: 'N/A', detail: 'Esperando DIX...' };
  const d = LIVE.dix;
  const trend = LIVE.dix_trend || 0;

  let score;
  if      (d > 46) score =  1.0;
  else if (d > 44) score =  0.5;
  else if (d > 42) score =  0.0;
  else if (d > 40) score = -0.5;
  else             score = -1.0;

  if (trend > 0.5)  score += 0.15;
  if (trend < -0.5) score -= 0.15;

  const label = score > 0.3 ? 'ACUMULACIÓN' : score < -0.3 ? 'DISTRIBUCIÓN' : 'NEUTRO';
  const trendTxt = trend > 0 ? `▲ +${trend.toFixed(1)}%` : `▼ ${trend.toFixed(1)}%`;
  const detail = `DIX ${d.toFixed(1)}% (${trendTxt} vs ayer) — ${label}`;

  return { score: Math.max(-1, Math.min(1, score)), label, detail, value: d };
}

// ── SEÑAL 4: QQQ vs SPY ROTACIÓN ─────────────────────────────────────────────
function signalRotation() {
  if (!LIVE.qqq || !LIVE.spy) return { score: 0, label: 'N/A', detail: 'Esperando QQQ/SPY...' };

  const diff = LIVE.qqq.chg - LIVE.spy.chg;

  let score, label;
  if      (diff >  1.0) { score =  1.0; label = 'NASDAQ LIDERA FUERTE'; }
  else if (diff >  0.3) { score =  0.6; label = 'NASDAQ LIDERA'; }
  else if (diff > -0.3) { score =  0.0; label = 'ROTACIÓN NEUTRAL'; }
  else if (diff > -1.0) { score = -0.6; label = 'NASDAQ REZAGADO'; }
  else                  { score = -1.0; label = 'SALIDA DE TECH'; }

  const detail = `QQQ ${LIVE.qqq.chg >= 0 ? '+' : ''}${LIVE.qqq.chg.toFixed(2)}% | SPY ${LIVE.spy.chg >= 0 ? '+' : ''}${LIVE.spy.chg.toFixed(2)}% | Diff: ${diff >= 0 ? '+' : ''}${diff.toFixed(2)}%`;
  return { score, label, detail, value: diff };
}

// ── SEÑAL 5: SECTORES XLK + SOXX ─────────────────────────────────────────────
function signalSectors() {
  if (!LIVE.xlk && !LIVE.soxx) return { score: 0, label: 'N/A', detail: 'Esperando XLK/SOXX...' };

  const xlkChg  = LIVE.xlk?.chg  || 0;
  const soxxChg = LIVE.soxx?.chg || 0;
  const avg = (xlkChg + soxxChg) / 2;

  let score, label;
  if      (avg >  1.5) { score =  1.0; label = 'TECH + SEMIS FUERTE'; }
  else if (avg >  0.5) { score =  0.6; label = 'SECTORES ALCISTAS'; }
  else if (avg > -0.5) { score =  0.0; label = 'NEUTROS'; }
  else if (avg > -1.5) { score = -0.6; label = 'SECTORES DÉBILES'; }
  else                 { score = -1.0; label = 'TECH + SEMIS EN VENTA'; }

  const detail = `XLK ${xlkChg >= 0 ? '+' : ''}${xlkChg.toFixed(2)}% | SOXX ${soxxChg >= 0 ? '+' : ''}${soxxChg.toFixed(2)}%`;
  return { score, label, detail, value: avg };
}

// ── SEÑAL 6: PUT/CALL (contraria) ────────────────────────────────────────────
function signalPutCall() {
  if (!LIVE.putcall) return { score: 0, label: 'N/A', detail: 'Esperando Put/Call...' };
  const pc = LIVE.putcall.price;

  let score, label;
  if      (pc > 1.2)  { score =  0.8; label = 'MIEDO EXTREMO · CONTRARIA ALCISTA'; }
  else if (pc > 1.0)  { score =  0.3; label = 'MIEDO MODERADO'; }
  else if (pc > 0.8)  { score =  0.0; label = 'NEUTRO'; }
  else if (pc > 0.7)  { score = -0.2; label = 'CODICIA MODERADA'; }
  else                { score = -0.6; label = 'CODICIA EXTREMA · CONTRARIA BAJISTA'; }

  return { score, label, detail: `Put/Call ${pc.toFixed(2)} — ${label}`, value: pc };
}

// ── SEÑAL 7: COT SEMANAL ──────────────────────────────────────────────────────
function signalCOT() {
  const idx = LIVE.cot.cot_index;
  const wks = LIVE.cot.consecutive_weeks;

  let score;
  if      (idx > 70) score =  1.0;
  else if (idx > 50) score =  0.5;
  else if (idx > 30) score =  0.0;
  else               score = -0.5;

  if (wks <= -3) score -= 0.3;
  else if (wks >= 3) score += 0.3;

  const label = score > 0.3 ? 'ALCISTA' : score < -0.3 ? 'BAJISTA' : 'NEUTRO';
  const weeksTxt = wks < 0 ? `${Math.abs(wks)} sem. reduciendo` : wks > 0 ? `${wks} sem. acumulando` : 'estable';
  const detail = `COT Index ${idx}/100 | ${weeksTxt} | Net: +${(LIVE.cot.asset_managers_net/1000).toFixed(0)}k`;

  return { score: Math.max(-1, Math.min(1, score)), label, detail, value: idx };
}

// ── BIAS ENGINE ───────────────────────────────────────────────────────────────
/*
  SESGO SEMANAL (5 días):
    COT           50%  — posicionamiento institucional real
    VXN régimen   30%  — volatilidad tendencia
    QQQ vs SPY    20%  — rotación de capital

  SESGO DIARIO (1 sesión NY):
    VXN           25%  — condición de volatilidad hoy
    Futuros NQ    25%  — overnight institucional
    DIX           20%  — dark pools acumulación
    QQQ vs SPY    15%  — liderazgo Nasdaq hoy
    XLK + SOXX    10%  — confirmación sectorial
    Put/Call       5%  — sentimiento opciones
*/
function calcBiasEngine() {
  const cot      = signalCOT();
  const vxn      = signalVXN();
  const futures  = signalFuturesPremium();
  const dix      = signalDIX();
  const rotation = signalRotation();
  const sectors  = signalSectors();
  const putcall  = signalPutCall();

  // ── SEMANAL ───────────────────────────────────────────────────────────────
  const weeklyRaw =
    cot.score      * 0.50 +
    vxn.score      * 0.30 +
    rotation.score * 0.20;

  const weeklyPct   = Math.round((weeklyRaw + 1) / 2 * 100);
  const weeklyLabel = weeklyRaw > 0.15 ? 'ALCISTA' : weeklyRaw < -0.15 ? 'BAJISTA' : 'NEUTRO';
  const weeklyConf  = Math.min(95, Math.round(Math.abs(weeklyRaw) * 90));

  // ── DIARIO ────────────────────────────────────────────────────────────────
  const dailyRaw =
    vxn.score      * 0.25 +
    futures.score  * 0.25 +
    dix.score      * 0.20 +
    rotation.score * 0.15 +
    sectors.score  * 0.10 +
    putcall.score  * 0.05;

  const dailyPct   = Math.round((dailyRaw + 1) / 2 * 100);
  const dailyLabel = dailyRaw > 0.15 ? 'ALCISTA' : dailyRaw < -0.15 ? 'BAJISTA' : 'NEUTRO';
  const dailyConf  = Math.min(95, Math.round(Math.abs(dailyRaw) * 90));

  // ── GLOBAL ────────────────────────────────────────────────────────────────
  const globalRaw   = weeklyRaw * 0.45 + dailyRaw * 0.55;
  const globalPct   = Math.round((globalRaw + 1) / 2 * 100);
  const globalLabel = globalRaw > 0.15 ? 'ALCISTA' : globalRaw < -0.15 ? 'BAJISTA' : 'NEUTRO';

  // ── DRIVER DOMINANTE ──────────────────────────────────────────────────────
  const all = [
    { name: 'COT',      score: cot.score,      w: 0.50, detail: cot.detail },
    { name: 'VXN',      score: vxn.score,      w: 0.25, detail: vxn.detail },
    { name: 'Futuros',  score: futures.score,  w: 0.25, detail: futures.detail },
    { name: 'DIX',      score: dix.score,      w: 0.20, detail: dix.detail },
    { name: 'Rotación', score: rotation.score, w: 0.15, detail: rotation.detail },
    { name: 'Sectores', score: sectors.score,  w: 0.10, detail: sectors.detail },
    { name: 'Put/Call', score: putcall.score,  w: 0.05, detail: putcall.detail },
  ];
  const dominant = all.reduce((a, b) =>
    Math.abs(b.score * b.w) > Math.abs(a.score * a.w) ? b : a);

  // ── ANÁLISIS TEXTO ────────────────────────────────────────────────────────
  const analysis = buildAnalysis(weeklyLabel, dailyLabel, globalPct, dominant, futures, vxn);

  return {
    global:  { raw: globalRaw,  pct: globalPct,  label: globalLabel },
    weekly:  { raw: weeklyRaw,  pct: weeklyPct,  label: weeklyLabel, confidence: weeklyConf },
    daily:   { raw: dailyRaw,   pct: dailyPct,   label: dailyLabel,  confidence: dailyConf },
    signals: { cot, vxn, futures, dix, rotation, sectors, putcall },
    dominant,
    analysis,
  };
}

function buildAnalysis(weeklyLabel, dailyLabel, globalPct, dominant, futures, vxn) {
  let txt = '';

  if (weeklyLabel === dailyLabel && weeklyLabel === 'ALCISTA') {
    txt += 'Marcos semanal y diario alineados alcistas. ';
  } else if (weeklyLabel === dailyLabel && weeklyLabel === 'BAJISTA') {
    txt += 'Marcos alineados bajistas — reducir exposición. ';
  } else if (weeklyLabel === 'BAJISTA' && dailyLabel === 'ALCISTA') {
    txt += 'Divergencia: COT semanal bajista pero sesión favorable. Operar con 50% de tamaño. ';
  } else if (weeklyLabel === 'ALCISTA' && dailyLabel === 'BAJISTA') {
    txt += 'Corrección intraday sobre tendencia alcista semanal. Posible entrada en soporte. ';
  } else {
    txt += 'Señales mixtas — esperar confirmación en apertura NY. ';
  }

  txt += `Driver principal: ${dominant.name} (${dominant.detail}). `;

  if (futures.score > 0.3) {
    txt += 'Futuros con premium — institucionales compraron overnight. ';
  } else if (futures.score < -0.3) {
    txt += 'Futuros con descuento — presión vendedora antes de apertura. ';
  }

  if (globalPct > 65) txt += 'Estrategia: LARGO tras confirmación vela 9:45 ET.';
  else if (globalPct < 35) txt += 'Estrategia: Sin posición larga. Esperar señal inversión.';
  else txt += 'Estrategia: Esperar apertura para confirmar dirección.';

  return txt;
}

// ── HISTORIAL ─────────────────────────────────────────────────────────────────
function saveHistory(bias) {
  try {
    const entry = {
      ts:           new Date().toISOString(),
      ndx:          LIVE.ndx?.price,
      vxn:          LIVE.vxn?.price,
      dix:          LIVE.dix,
      gex:          LIVE.gex,
      putcall:      LIVE.putcall?.price,
      cot_net:      LIVE.cot.asset_managers_net,
      cot_idx:      LIVE.cot.cot_index,
      fut_premium:  bias.signals.futures?.value,
      qqq_spy_diff: bias.signals.rotation?.value,
      score_global: bias.global.pct,
      score_weekly: bias.weekly.pct,
      score_daily:  bias.daily.pct,
      label:        bias.global.label,
    };
    const hist = JSON.parse(localStorage.getItem('nq_history') || '[]');
    hist.push(entry);
    if (hist.length > 200) hist.splice(0, hist.length - 200);
    localStorage.setItem('nq_history', JSON.stringify(hist));
  } catch(e) {}
}

// ── ACTUALIZAR DOM ────────────────────────────────────────────────────────────
function updateDOM(bias) {
  const C = { ALCISTA: '#00ff88', BAJISTA: '#ff3355', NEUTRO: '#ffd60a' };
  const set = (id, val, color) => {
    const el = document.getElementById(id);
    if (!el || val == null) return;
    el.innerText = val;
    if (color) el.style.color = color;
  };

  const gc = C[bias.global.label]  || '#ffd60a';
  const wc = C[bias.weekly.label]  || '#ffd60a';
  const dc = C[bias.daily.label]   || '#ffd60a';

  // NDX
  if (LIVE.ndx) {
    const nc = LIVE.ndx.chg >= 0 ? '#00ff88' : '#ff3355';
    const price = LIVE.ndx.price.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
    ['heroNdx','ndx-price','ndx-val'].forEach(id => set(id, price, '#ffffff'));
    ['heroNdxChg','ndx-chg','ndx-change'].forEach(id =>
      set(id, `${LIVE.ndx.chg >= 0 ? '▲' : '▼'} ${Math.abs(LIVE.ndx.chg).toFixed(2)}%`, nc));
  }

  // VXN
  if (LIVE.vxn) {
    const s = bias.signals.vxn;
    const vc = C[s.score > 0.3 ? 'ALCISTA' : s.score < -0.3 ? 'BAJISTA' : 'NEUTRO'];
    ['heroVxn','vxn-val','masterVxn','kpiVxn','row-vxn-val'].forEach(id => set(id, LIVE.vxn.price.toFixed(2), vc));
    set('daily-vxn-title', `VXN ${LIVE.vxn.price.toFixed(2)} — ${s.label}`, vc);
    set('daily-vxn-desc', s.detail);
    const icon = document.getElementById('daily-vxn-icon');
    if (icon) icon.innerText = s.score > 0 ? '✅' : s.score < -0.3 ? '🔴' : '⚠️';
  }

  // DIX
  if (LIVE.dix !== null) {
    const s = bias.signals.dix;
    const dc2 = C[s.score > 0.3 ? 'ALCISTA' : s.score < -0.3 ? 'BAJISTA' : 'NEUTRO'];
    ['heroDix','dix-val','masterDix','kpiDix','row-dix-val'].forEach(id => set(id, LIVE.dix.toFixed(1) + '%', dc2));
    set('daily-dix-title', `DIX ${LIVE.dix.toFixed(1)}% — ${s.label}`, dc2);
    set('daily-dix-desc', s.detail);
  }

  // GEX
  if (LIVE.gex !== null) {
    const gBn = LIVE.gex / 1e9;
    const gc2 = gBn >= 0 ? '#00ff88' : '#ff3355';
    ['heroGex','gex-val','kpiGex','row-gex-val'].forEach(id => set(id, `${gBn >= 0 ? '+' : ''}${gBn.toFixed(1)}B`, gc2));
  }

  // Put/Call
  if (LIVE.putcall) {
    const s = bias.signals.putcall;
    ['heroPcr','putcall-val'].forEach(id => set(id, LIVE.putcall.price.toFixed(2)));
    set('daily-pcr-title', `Put/Call ${LIVE.putcall.price.toFixed(2)} — ${s.label}`);
    set('daily-pcr-desc', s.detail);
  }

  // Futuros NQ
  if (LIVE.nq_fut) {
    const s = bias.signals.futures;
    const fc = s.score > 0.3 ? '#00ff88' : s.score < -0.3 ? '#ff3355' : '#ffd60a';
    set('nq-fut-val',    LIVE.nq_fut.price.toFixed(0), fc);
    set('nq-fut-signal', s.label, fc);
    set('nq-fut-detail', s.detail, fc);
  }

  // Rotación
  if (LIVE.qqq && LIVE.spy) {
    const s = bias.signals.rotation;
    const rc = C[s.score > 0.3 ? 'ALCISTA' : s.score < -0.3 ? 'BAJISTA' : 'NEUTRO'];
    set('rotation-val',    s.detail, rc);
    set('rotation-signal', s.label,  rc);
  }

  // Sectores
  if (LIVE.xlk || LIVE.soxx) {
    const s = bias.signals.sectors;
    const sc = C[s.score > 0.3 ? 'ALCISTA' : s.score < -0.3 ? 'BAJISTA' : 'NEUTRO'];
    set('sectors-val',    s.detail, sc);
    set('sectors-signal', s.label,  sc);
  }

  // Scores
  set('master-score-val', bias.global.pct, gc);
  set('master-score-lbl', bias.global.label, gc);
  set('weeklyBias',       bias.weekly.label, wc);
  set('weeklyScore',      `${bias.weekly.pct}/100`, wc);
  set('weeklyConfidence', bias.weekly.confidence + '%', wc);
  set('dailyBias',        bias.daily.label, dc);
  set('dailyScore',       `${bias.daily.pct}/100`, dc);
  set('dailyConfidence',  bias.daily.confidence + '%', dc);

  // Aguja
  ['bias-needle','score-needle-old'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.left = `calc(${bias.global.pct}% - 8px)`;
  });

  // Gauge SVG
  const gauge = document.querySelector('#biasGaugeCircle, circle.text-emerald-400');
  if (gauge) {
    const circ = 2 * Math.PI * 60;
    gauge.style.strokeDasharray = circ;
    gauge.style.strokeDashoffset = circ - (bias.global.pct / 100 * circ);
    gauge.style.stroke = gc;
    gauge.style.filter = `drop-shadow(0 0 8px ${gc})`;
  }

  // Análisis
  ['masterText','biasExplanation','verdict-text'].forEach(id => set(id, bias.analysis));

  // Timestamp
  const ts = new Date().toLocaleTimeString('es-ES', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  ['updateTime','update-time','last-update'].forEach(id => set(id, ts));

  // Barras tabla peso
  [
    { id: 'vxn', score: bias.signals.vxn.score },
    { id: 'dix', score: bias.signals.dix.score },
    { id: 'gex', score: bias.signals.sectors.score },
  ].forEach(({ id, score }) => {
    const bar = document.getElementById(`row-${id}-bar`);
    if (!bar) return;
    const pct = Math.round((score + 1) / 2 * 100);
    bar.style.width = pct + '%';
    bar.style.background = C[score > 0.3 ? 'ALCISTA' : score < -0.3 ? 'BAJISTA' : 'NEUTRO'] || '#ffd60a';
  });

  console.log(
    `[NQ Agent] ${ts}` +
    ` | NDX: ${LIVE.ndx?.price?.toFixed(0)||'—'}` +
    ` | VXN: ${LIVE.vxn?.price?.toFixed(2)||'—'}` +
    ` | DIX: ${LIVE.dix?.toFixed(1)||'—'}%` +
    ` | Futuros: ${bias.signals.futures?.label||'—'}` +
    ` | QQQ/SPY: ${bias.signals.rotation?.label||'—'}` +
    ` | Bias Global: ${bias.global.label} ${bias.global.pct}/100` +
    ` | Semanal: ${bias.weekly.label} (${bias.weekly.confidence}%)` +
    ` | Diario: ${bias.daily.label} (${bias.daily.confidence}%)`
  );
}

// ── ACTUALIZAR COT MANUAL ─────────────────────────────────────────────────────
function updateCOT(assetManagersNet, leveragedFundsNet, prevWeekNet) {
  LIVE.cot.asset_managers_net = assetManagersNet;
  LIVE.cot.prev_week_net = prevWeekNet;

  const change = assetManagersNet - prevWeekNet;
  if (change > 0)      LIVE.cot.consecutive_weeks = Math.max(1, LIVE.cot.consecutive_weeks + 1);
  else if (change < 0) LIVE.cot.consecutive_weeks = Math.min(-1, LIVE.cot.consecutive_weeks - 1);
  else                 LIVE.cot.consecutive_weeks = 0;

  const range = LIVE.cot.hist_max - LIVE.cot.hist_min;
  LIVE.cot.cot_index = Math.max(0, Math.min(100,
    Math.round((assetManagersNet - LIVE.cot.hist_min) / range * 100)
  ));
  LIVE.cot.date = new Date().toLocaleDateString('es-ES', {day:'2-digit',month:'short',year:'numeric'});

  const dateEl = document.getElementById('cot-last-date');
  if (dateEl) dateEl.innerText = LIVE.cot.date;

  console.log('[NQ] COT actualizado:', LIVE.cot);
  refreshAll();
}

// ── WIDGET COT ────────────────────────────────────────────────────────────────
function injectCOTWidget() {
  if (document.getElementById('cot-update-widget')) return;
  const target = document.querySelector('[id*="cot"]');
  if (!target) return;

  const w = document.createElement('div');
  w.id = 'cot-update-widget';
  w.innerHTML = `
    <div style="background:rgba(0,242,255,.04);border:1px solid rgba(0,242,255,.15);border-radius:12px;padding:18px;margin-top:16px;">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;color:#00f2ff;letter-spacing:.16em;text-transform:uppercase;margin-bottom:12px;">
        ⚡ Actualizar COT · Viernes 3:30pm ET
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr auto;gap:10px;align-items:end">
        <div>
          <div style="font-size:9px;color:#4a5a7a;margin-bottom:4px;font-family:monospace">Asset Mgr Net</div>
          <input id="cot-in-am" type="number" placeholder="${LIVE.cot.asset_managers_net}" style="background:#0a0f1e;border:1px solid rgba(0,242,255,.2);color:#e2e8f8;padding:6px 10px;border-radius:6px;font-family:monospace;font-size:11px;width:100%">
        </div>
        <div>
          <div style="font-size:9px;color:#4a5a7a;margin-bottom:4px;font-family:monospace">Lev. Funds Net</div>
          <input id="cot-in-lf" type="number" placeholder="-42317" style="background:#0a0f1e;border:1px solid rgba(0,242,255,.2);color:#e2e8f8;padding:6px 10px;border-radius:6px;font-family:monospace;font-size:11px;width:100%">
        </div>
        <div>
          <div style="font-size:9px;color:#4a5a7a;margin-bottom:4px;font-family:monospace">Semana Anterior</div>
          <input id="cot-in-prev" type="number" placeholder="${LIVE.cot.prev_week_net}" style="background:#0a0f1e;border:1px solid rgba(0,242,255,.2);color:#e2e8f8;padding:6px 10px;border-radius:6px;font-family:monospace;font-size:11px;width:100%">
        </div>
        <button onclick="
          const am=parseInt(document.getElementById('cot-in-am').value);
          const lf=parseInt(document.getElementById('cot-in-lf').value)||0;
          const pv=parseInt(document.getElementById('cot-in-prev').value);
          if(!isNaN(am)&&!isNaN(pv)){updateCOT(am,lf,pv);this.innerText='✓ OK';this.style.color='#00ff88';}
        " style="background:rgba(0,242,255,.08);border:1px solid rgba(0,242,255,.3);color:#00f2ff;padding:7px 16px;border-radius:6px;font-family:monospace;font-size:10px;cursor:pointer;text-transform:uppercase;letter-spacing:.08em;white-space:nowrap">
          Actualizar
        </button>
      </div>
      <div style="margin-top:10px;font-size:9px;color:#4a5a7a;font-family:monospace">
        Fuente: <a href="https://www.cftc.gov/dea/futures/financial_lf.htm" target="_blank" style="color:#00f2ff">cftc.gov</a>
        · Último: <span id="cot-last-date" style="color:#94a3b8">${LIVE.cot.date}</span>
        · COT Index: <span style="color:#ffd60a">${LIVE.cot.cot_index}/100</span>
        · ${Math.abs(LIVE.cot.consecutive_weeks)} sem. ${LIVE.cot.consecutive_weeks < 0 ? 'reduciendo ▼' : 'acumulando ▲'}
      </div>
    </div>`;

  target.parentNode?.insertBefore(w, target.nextSibling) || document.body.appendChild(w);
}

// ── CICLO PRINCIPAL ───────────────────────────────────────────────────────────
async function refreshAll() {
  const [ndxR, futR, vxnR, vixR, pcR, dixR, qqqR, spyR, xlkR, soxxR] =
    await Promise.allSettled([
      fetchYahoo('%5ENDX'),
      fetchYahoo('NQ%3DF'),
      fetchYahoo('%5EVXN'),
      fetchYahoo('%5EVIX'),
      fetchYahoo('%5EPCCE'),
      fetchDIX(),
      fetchYahoo('QQQ'),
      fetchYahoo('SPY'),
      fetchYahoo('XLK'),
      fetchYahoo('SOXX'),
    ]);

  const ok = r => r.status === 'fulfilled' && r.value;

  if (ok(ndxR))  LIVE.ndx     = ndxR.value;
  if (ok(futR))  LIVE.nq_fut  = futR.value;
  if (ok(vxnR))  LIVE.vxn     = vxnR.value;
  if (ok(vixR))  LIVE.vix     = vixR.value;
  if (ok(pcR))   LIVE.putcall = pcR.value;
  if (ok(qqqR))  LIVE.qqq     = qqqR.value;
  if (ok(spyR))  LIVE.spy     = spyR.value;
  if (ok(xlkR))  LIVE.xlk     = xlkR.value;
  if (ok(soxxR)) LIVE.soxx    = soxxR.value;

  if (ok(dixR)) {
    LIVE.dix       = dixR.value.dix;
    LIVE.gex       = dixR.value.gex;
    LIVE.dix_trend = dixR.value.dix_trend;
  }

  LIVE.ts = new Date();

  const bias = calcBiasEngine();
  updateDOM(bias);
  saveHistory(bias);

  return bias;
}

// ── INIT ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await refreshAll();
  setTimeout(injectCOTWidget, 1500);
  setInterval(refreshAll, 60_000);
});

window.NQ = { LIVE, calcBiasEngine, updateCOT, refreshAll };
