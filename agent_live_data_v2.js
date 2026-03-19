/**
 * agent_live_data.js — NQ Intelligence v2.0
 * ─────────────────────────────────────────
 * Motor de bias institucional para Nasdaq
 * 7 señales: COT + VXN + Futuros Premium + DIX + Rotación + Sectores + Put/Call
 * Actualización: cada 60s
 */

// ── PROXY WATERFALL — intenta en orden hasta obtener respuesta 2xx ───────────
const PROXIES = [
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
  url => `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(url)}`,
  url => `https://corsproxy.io/?${encodeURIComponent(url)}`,
  url => `https://proxy.cors.sh/${url}`,
];

async function proxyFetch(url, opts = {}) {
  for (const makeProxy of PROXIES) {
    try {
      const res = await fetch(makeProxy(url), { ...opts, signal: AbortSignal.timeout(8000) });
      if (res.ok) return res;
    } catch(e) { /* try next */ }
  }
  throw new Error('All proxies failed for: ' + url);
}

// ── COT — Auto-fetch CFTC Disaggregated Futures ──────────────────────────────
const _NQ = typeof window !== 'undefined' && window.NQ_LIVE ? window.NQ_LIVE : {};
const _COT = _NQ.COT || {};
const COT_DATA = {
  date: _NQ.last_update || 'cargando...',
  asset_managers_net: _COT.net || 0,
  prev_week_net: (_COT.recent_weeks && _COT.recent_weeks[1] ? _COT.recent_weeks[1].net : 0),
  consecutive_weeks: _COT.consecutive_weeks || 0,
  cot_index: _COT.index || 50,
  hist_min: _COT.history_min || 52000,
  hist_max: _COT.history_max || 142000,
};

// ── FETCH COT AUTOMÁTICO ──────────────────────────────────────────────────────
async function fetchCOT() {
  try {
    // CFTC Disaggregated Futures — current year report (Fixed Width TXT, ~1MB)
    const url = 'https://www.cftc.gov/dea/newcot/f_disagg.txt';
    const res = await proxyFetch(url);
    const text = await res.text();
    const lines = text.trim().split('\n');

    // Contract code 209742 = NASDAQ-100 E-MINI (or search for NASDAQ)
    const nqLines = lines.filter(line =>
      line.includes('209742') || line.toUpperCase().includes('NASDAQ-100')
    );

    if (nqLines.length === 0) {
      console.warn('[NQ] COT: No se encontró NASDAQ-100 en CFTC data');
      return;
    }

    // Parse CSV — CFTC Disaggregated format columns:
    // The file is comma-separated with many columns. Key columns:
    //   col 0: Market Name
    //   col 2: Report Date (YYYY-MM-DD)
    //   col 9: Asset Manager/Institutional Longs
    //  col 10: Asset Manager/Institutional Shorts
    const parsed = nqLines.map(line => {
      const cols = line.split(',').map(c => c.trim().replace(/"/g, ''));
      return {
        name: cols[0],
        date: cols[2],
        am_long:  parseInt(cols[9])  || 0,
        am_short: parseInt(cols[10]) || 0,
        am_net:   (parseInt(cols[9]) || 0) - (parseInt(cols[10]) || 0),
      };
    }).filter(r => !isNaN(r.am_long)).sort((a, b) => a.date > b.date ? 1 : -1);

    if (parsed.length === 0) {
      console.warn('[NQ] COT: No se pudieron parsear los datos');
      return;
    }

    const latest = parsed[parsed.length - 1];
    const prev   = parsed.length > 1 ? parsed[parsed.length - 2] : null;

    // Update COT_DATA
    LIVE.cot.asset_managers_net = latest.am_net;
    LIVE.cot.prev_week_net = prev ? prev.am_net : latest.am_net;
    LIVE.cot.date = latest.date;

    // Consecutive weeks direction
    if (prev) {
      const change = latest.am_net - prev.am_net;
      if (change > 0)      LIVE.cot.consecutive_weeks = Math.max(1, LIVE.cot.consecutive_weeks + 1);
      else if (change < 0) LIVE.cot.consecutive_weeks = Math.min(-1, LIVE.cot.consecutive_weeks - 1);
      else                 LIVE.cot.consecutive_weeks = 0;
    }

    // Update historical min/max from all available data
    const allNets = parsed.map(r => r.am_net);
    LIVE.cot.hist_min = Math.min(LIVE.cot.hist_min, ...allNets);
    LIVE.cot.hist_max = Math.max(LIVE.cot.hist_max, ...allNets);

    // Recalculate COT Index (0-100)
    const range = LIVE.cot.hist_max - LIVE.cot.hist_min;
    LIVE.cot.cot_index = range > 0
      ? Math.max(0, Math.min(100, Math.round((latest.am_net - LIVE.cot.hist_min) / range * 100)))
      : 50;

    // Update DOM
    const dateEl = document.getElementById('cot-last-date');
    if (dateEl) dateEl.innerText = LIVE.cot.date;

    console.log('[NQ] COT auto-fetched:', LIVE.cot);
    // Actualizar panel visual si ya está en el DOM
    if (typeof updateCOTPanel === 'function') updateCOTPanel();
  } catch(e) {
    console.warn('[NQ] COT fetch error:', e.message);
  }
}

// ── ESTADO GLOBAL ─────────────────────────────────────────────────────────────
const LIVE = {
  ndx:       { price: 24425.09, prev: 24779.50, chg: -1.43, closes: [24612,24779,24425] },
  nq_fut:    { price: 24380.00, prev: 24720.00, chg: -1.38, closes: [24550,24720,24380] },
  vxn:       { price: 27.72, prev: 24.67, chg: 12.41, closes: [22.1,24.67,27.72] },
  vix:       { price: 21.85, prev: 19.80, chg: 10.35, closes: [18.5,19.8,21.85] },
  dix:       43.2,
  dix_trend: -0.8,
  gex:       -1.45e9,
  putcall:   { price: 0.95, prev: 0.91, chg: 4.4, closes: [0.88,0.91,0.95] },
  qqq:       { price: 480.12, prev: 487.20, chg: -1.45, closes: [485,487.2,480.12] },
  spy:       { price: 558.30, prev: 562.10, chg: -0.68, closes: [560,562.1,558.3] },
  xlk:       { price: 210.40, prev: 213.80, chg: -1.59, closes: [212,213.8,210.4] },
  soxx:      { price: 178.20, prev: 182.50, chg: -2.36, closes: [181,182.5,178.2] },
  cot:       COT_DATA,
  ts:        null,
};

// ── FETCH STOOQ (sustituye Yahoo Finance — CSV público, sin auth) ─────────────
// Mapa: símbolo Yahoo → símbolo Stooq
const STOOQ_SYMBOLS = {
  '%5ENDX':  '^ndx',
  '^NDX':    '^ndx',
  'NQ%3DF':  'nq.f',
  'NQ=F':    'nq.f',
  '%5EVXN':  '^vxn',
  '^VXN':    '^vxn',
  '%5EVIX':  '^vix',
  '^VIX':    '^vix',
  '%5EPCCE': '^pcce',
  '^PCCE':   '^pcce',
  'QQQ':     'qqq.us',
  'SPY':     'spy.us',
  'XLK':     'xlk.us',
  'SOXX':    'soxx.us',
};

async function fetchYahoo(symbol) {
  const stooq = STOOQ_SYMBOLS[symbol] || symbol.toLowerCase();
  try {
    // Últimos 10 días de datos diarios — pequeño, rápido, sin auth
    const url = `https://stooq.com/q/d/l/?s=${encodeURIComponent(stooq)}&i=d`;
    const res  = await proxyFetch(url);
    const text = await res.text();

    // Reject HTML error pages from proxy (not CSV data)
    const trimmed = text.trim();
    if (trimmed.startsWith('<') || trimmed.includes('<!DOCTYPE') || trimmed.toLowerCase().includes('<html')) return null;

    // CSV: Symbol,Date,Open,High,Low,Close,Volume  (sin header o con header)
    const lines = trimmed.split('\n').filter(l => l && !l.toLowerCase().startsWith('symbol') && !l.toLowerCase().startsWith('date'));
    if (lines.length === 0) return null;

    // Parsear las últimas 10 filas para el histórico cercano
    const rows = lines.slice(-10).map(l => {
      const cols = l.split(',');
      return { date: cols[1]?.trim(), close: parseFloat(cols[5] || cols[4]) };
    }).filter(r => !isNaN(r.close) && isFinite(r.close) && r.close > 0);

    if (rows.length === 0) return null;

    const last  = rows[rows.length - 1];
    const prev2 = rows.length > 1 ? rows[rows.length - 2] : last;
    const price = last.close;
    const prev  = prev2.close;
    const chg   = prev ? ((price - prev) / prev * 100) : 0;
    const closes = rows.map(r => r.close);

    // Sanity: reject absurd prices (proxy garbage surviving CSV parse)
    // Indices like NDX max ~50k, ETFs max ~1000, ratios max ~5
    if (price > 100_000 || price < 0.001) {
      console.warn(`[NQ] Stooq ${stooq}: price ${price} out of sane range, discarding`);
      return null;
    }

    return { price, prev, chg, closes };
  } catch(e) {
    console.warn(`[NQ] Stooq ${stooq} error:`, e.message);
    return null;
  }
}

// ── FETCH DIX + GEX ───────────────────────────────────────────────────────────
async function fetchDIX() {
  try {
    const url = 'https://squeezemetrics.com/monitor/static/DIX.csv';
    const res = await proxyFetch(url);
    const text = await res.text();
    const trimmedDIX = text.trim();
    if (trimmedDIX.startsWith('<') || trimmedDIX.includes('<!DOCTYPE') || trimmedDIX.toLowerCase().includes('<html')) return null;
    const rows = text.trim().split('\n');
    const recent = rows.slice(-5).map(r => {
      const c = r.split(',');
      return { date: c[0], dix: parseFloat(c[1]) * 100, gex: parseFloat(c[2]) };
    }).filter(r => !isNaN(r.dix) && !isNaN(r.gex));
    if (recent.length === 0) return null;
    const last = recent[recent.length - 1];
    const prev = recent.length > 1 ? recent[recent.length - 2] : null;
    if (isNaN(last.dix) || isNaN(last.gex)) return null;
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

// ── PANEL COT VISUAL ──────────────────────────────────────────────────────────
const COT_HISTORY = (_COT.recent_weeks && _COT.recent_weeks.length
  ? _COT.recent_weeks.slice().reverse().map(w => w.net)
  : [-72100, -78340, -82190, -85470, -89615]);

function buildCOTPanelHTML() {
  const c        = LIVE.cot;
  const net      = c.asset_managers_net;
  const change   = net - c.prev_week_net;
  const idx      = c.cot_index;
  const wks      = c.consecutive_weeks;
  const idxColor = idx > 60 ? '#00ff88' : idx < 40 ? '#ff3355' : '#ffd60a';
  const chgColor = change >= 0 ? '#00ff88' : '#ff3355';
  const chgArrow = change >= 0 ? '▲' : '▼';
  const wksColor = wks > 0 ? '#00ff88' : wks < 0 ? '#ff3355' : '#94a3b8';
  const markerPos = Math.max(1, Math.min(99, idx));

  // Mini barras (últimas 8 semanas de historial)
  const hist = COT_HISTORY.slice(-8);
  const maxAbsNet = hist.length ? Math.max(...hist.map(v => Math.abs(v)), 1) : 1;
  const minBar = 4;
  const barsHTML = hist.map((v, i) => {
    const pct    = Math.max(minBar, Math.abs(v) / maxAbsNet * 100);
    const col    = v >= 0 ? '#00ff88' : '#ff3355';
    const isLast = i === hist.length - 1;
    const opacity = 0.35 + (i / hist.length) * 0.65;
    return `<div style="display:flex;flex-direction:column;align-items:center;flex:1;gap:2px">
      <div style="width:100%;background:rgba(255,255,255,.05);border-radius:3px 3px 0 0;height:52px;
                  display:flex;align-items:flex-end;overflow:hidden;opacity:${opacity}">
        <div style="width:100%;height:${pct}%;background:${col};border-radius:2px 2px 0 0;
          ${isLast ? `box-shadow:0 0 10px ${col}77` : ''}"></div>
      </div>
      <div style="font-size:7px;color:${isLast ? idxColor : '#2a3a5a'}">${isLast ? '▲' : ''}</div>
    </div>`;
  }).join('');

  return `
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px">
      <div>
        <div style="font-size:9px;color:#00f2ff;letter-spacing:.16em;text-transform:uppercase">
          📊 COT · Asset Managers — NQ-100 E-Mini
        </div>
        <div style="font-size:8px;color:#4a5a7a;margin-top:3px">
          <a href="https://www.cftc.gov/dea/futures/financial_lf.htm" target="_blank"
             style="color:#00f2ff;text-decoration:none">CFTC Disaggregated</a>
          &nbsp;·&nbsp;
          <span style="color:#94a3b8">Actualizado: <span id="cot-last-date">${c.date}</span></span>
        </div>
      </div>
      <div style="text-align:right;line-height:1.1">
        <div style="font-size:26px;font-weight:700;color:${idxColor}">${idx}
          <span style="font-size:13px;color:#4a5a7a">/100</span>
        </div>
        <div style="font-size:8px;color:#4a5a7a">COT Index</div>
      </div>
    </div>

    <!-- KPIs -->
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px">
      <div style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.05);border-radius:10px;padding:11px">
        <div style="font-size:8px;color:#4a5a7a;margin-bottom:5px;text-transform:uppercase;letter-spacing:.08em">Net posición</div>
        <div id="cot-net-val" style="font-size:17px;font-weight:700;color:#e2e8f8">
          ${net > 0 ? '+' : ''}${(net / 1000).toFixed(1)}k
        </div>
      </div>
      <div style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.05);border-radius:10px;padding:11px">
        <div style="font-size:8px;color:#4a5a7a;margin-bottom:5px;text-transform:uppercase;letter-spacing:.08em">Cambio sem.</div>
        <div id="cot-chg-val" style="font-size:17px;font-weight:700;color:${chgColor}">
          ${chgArrow} ${Math.abs(change / 1000).toFixed(1)}k
        </div>
      </div>
      <div style="background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.05);border-radius:10px;padding:11px">
        <div style="font-size:8px;color:#4a5a7a;margin-bottom:5px;text-transform:uppercase;letter-spacing:.08em">Racha</div>
        <div id="cot-wks-val" style="font-size:17px;font-weight:700;color:${wksColor}">
          ${wks === 0 ? 'Estable' : Math.abs(wks) + ' sem ' + (wks > 0 ? '▲' : '▼')}
        </div>
      </div>
    </div>

    <!-- Barra Índice COT -->
    <div style="margin-bottom:14px">
      <div style="display:flex;justify-content:space-between;font-size:8px;color:#4a5a7a;margin-bottom:5px">
        <span>🔴 Extremo Bajista</span>
        <span style="color:${idxColor};font-weight:600">Índice ${idx} / 100</span>
        <span>🟢 Extremo Alcista</span>
      </div>
      <div style="position:relative;height:12px;border-radius:20px;overflow:visible;
                  background:linear-gradient(90deg,#ff335577 0%,#ffd60a77 50%,#00ff8877 100%);
                  border:1px solid rgba(255,255,255,.08)">
        <div id="cot-marker" style="
          position:absolute;top:50%;left:${markerPos}%;
          transform:translate(-50%,-50%);
          width:20px;height:20px;border-radius:50%;
          background:${idxColor};
          box-shadow:0 0 12px ${idxColor},0 0 4px #000;
          border:2px solid #0a0f1e;
          transition:left .8s cubic-bezier(.34,1.56,.64,1)">
        </div>
      </div>
      <div style="display:flex;justify-content:space-between;font-size:7px;color:#2a3a5a;margin-top:4px;padding:0 2px">
        <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
      </div>
    </div>

    <!-- Mini barras historial -->
    <div>
      <div style="font-size:8px;color:#4a5a7a;letter-spacing:.1em;text-transform:uppercase;margin-bottom:8px">
        Historial Net Position — últimas ${hist.length || '?'} semanas
      </div>
      <div id="cot-bars" style="display:flex;gap:5px;height:66px;align-items:flex-end">
        ${hist.length > 0 ? barsHTML
          : '<div style="color:#2a3a5a;font-size:9px;align-self:center">Cargando datos CFTC...</div>'}
      </div>
    </div>
  `;
}

function injectCOTWidget() {
  if (document.getElementById('cot-panel')) { updateCOTPanel(); return; }
  const target = document.querySelector('[id*="cot"], [class*="cot"]') || document.body;
  const panel  = document.createElement('div');
  panel.id     = 'cot-panel';
  panel.style.cssText = [
    'background:linear-gradient(135deg,rgba(0,242,255,.05) 0%,rgba(0,255,136,.03) 100%)',
    'border:1px solid rgba(0,242,255,.18)',
    'border-radius:16px',
    'padding:20px 22px',
    'margin-top:20px',
    'font-family:"JetBrains Mono","Courier New",monospace',
  ].join(';');
  panel.innerHTML = buildCOTPanelHTML();
  if (target === document.body) document.body.appendChild(panel);
  else target.parentNode?.insertBefore(panel, target.nextSibling) || document.body.appendChild(panel);
}

function updateCOTPanel() {
  // Agregar al historial si es dato nuevo
  const last = COT_HISTORY[COT_HISTORY.length - 1];
  if (LIVE.cot.asset_managers_net !== 0 && last !== LIVE.cot.asset_managers_net) {
    COT_HISTORY.push(LIVE.cot.asset_managers_net);
    if (COT_HISTORY.length > 12) COT_HISTORY.shift();
  }
  const panel = document.getElementById('cot-panel');
  if (panel) panel.innerHTML = buildCOTPanelHTML();
  else injectCOTWidget();
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
  // Only apply fetched data if price is a valid, in-range number (not NaN/Infinity/garbage)
  const validPrice = (r, min = 0.001, max = 100_000) =>
    ok(r) && typeof r.value.price === 'number' && !isNaN(r.value.price)
    && isFinite(r.value.price) && r.value.price >= min && r.value.price <= max;

  if (validPrice(ndxR, 1000, 60000))  LIVE.ndx     = ndxR.value;
  if (validPrice(futR, 1000, 60000))  LIVE.nq_fut  = futR.value;
  if (validPrice(vxnR, 0, 200))       LIVE.vxn     = vxnR.value;
  if (validPrice(vixR, 0, 200))       LIVE.vix     = vixR.value;
  if (validPrice(pcR, 0, 10))         LIVE.putcall = pcR.value;
  if (validPrice(qqqR, 10, 2000))     LIVE.qqq     = qqqR.value;
  if (validPrice(spyR, 10, 2000))     LIVE.spy     = spyR.value;
  if (validPrice(xlkR, 5, 1000))      LIVE.xlk     = xlkR.value;
  if (validPrice(soxxR, 5, 1000))     LIVE.soxx    = soxxR.value;

  if (ok(dixR) && !isNaN(dixR.value.dix) && !isNaN(dixR.value.gex)) {
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
  await fetchCOT();           // COT auto desde CFTC
  await refreshAll();
  setTimeout(injectCOTWidget, 1500);
  setInterval(refreshAll, 60_000);
  setInterval(fetchCOT, 30 * 60_000);  // Re-check COT cada 30 min
});

window.NQ = { LIVE, calcBiasEngine, updateCOT, refreshAll };
