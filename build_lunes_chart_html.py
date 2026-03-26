"""
build_lunes_chart_html.py
Genera el HTML final con todos los datos + niveles del metodo de trading.
"""
import json, re

# Cargar datos 5m
with open('data/research/lunes_5m_data.json', encoding='utf-8') as f:
    sessions = json.load(f)

# Cargar niveles del metodo
with open('data/research/lunes_levels.json', encoding='utf-8') as f:
    levels = json.load(f)

# Inyectar niveles en cada sesion
for s in sessions:
    d = s['date']
    if d in levels:
        s.update(levels[d])
    else:
        s.update({'ny_open':None,'val':None,'poc':None,'vah':None,
                  'ema200':None,'ema_above':None,'sweep_time':None,
                  'r_high':None,'r_low':None,
                  'vah_hit':False,'poc_hit':False,'val_hit':False,'ema_hit':False,
                  'vah_react':0,'poc_react':0,'val_react':0,'ema_react':0})

sessions_json = json.dumps(sessions, separators=(',',':'))

HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NQ Lunes — 5min + Método Trading | COT + VP + EMA</title>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#07090e;--bg2:#0d1117;--bg3:#111827;--border:#1e2532;
  --text:#e2e8f0;--muted:#64748b;
  --bull:#22c55e;--bear:#ef4444;
  --bull-dim:rgba(34,197,94,.12);--bear-dim:rgba(239,68,68,.12);
  --gold:#f59e0b;--blue:#3b82f6;--purple:#8b5cf6;--cyan:#06b6d4;
  --vah:#f97316;--poc:#facc15;--val:#38bdf8;--ema:#a78bfa;
}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh}

/* HEADER */
.header{background:linear-gradient(135deg,#0d1117,#111827);border-bottom:1px solid var(--border);
  padding:18px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.header h1{font-size:20px;font-weight:700;
  background:linear-gradient(90deg,#f59e0b,#3b82f6,#8b5cf6);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.3px}
.header p{font-size:12px;color:var(--muted);margin-top:3px}

/* STATS */
.stats{display:flex;gap:10px;padding:12px 28px;background:var(--bg2);
  border-bottom:1px solid var(--border);flex-wrap:wrap}
.sp{background:var(--bg3);border:1px solid var(--border);border-radius:8px;
  padding:7px 14px;display:flex;gap:8px;align-items:center;font-size:12px}
.sp .lbl{color:var(--muted)}.sp .val{font-weight:600;font-family:'JetBrains Mono',monospace}
.green{color:var(--bull)}.red{color:var(--bear)}.gold{color:var(--gold)}.blue{color:var(--blue)}

/* LEGEND */
.legend{padding:10px 28px;display:flex;gap:20px;flex-wrap:wrap;font-size:11px;color:var(--muted);
  background:var(--bg2);border-bottom:1px solid var(--border)}
.li{display:flex;align-items:center;gap:6px}
.lseg{width:22px;height:3px;border-radius:2px}

/* METHOD BOX */
.method-box{margin:0 28px 0;padding:12px 16px;
  background:rgba(59,130,246,.06);border:1px solid rgba(59,130,246,.2);
  border-radius:10px;font-size:12px;display:flex;gap:24px;flex-wrap:wrap;
  border-left:3px solid var(--blue);margin-top:16px;margin-bottom:8px}
.method-box strong{color:var(--blue);display:block;margin-bottom:4px;font-size:11px;letter-spacing:0.5px}
.method-col{display:flex;flex-direction:column;gap:3px}
.ml{display:flex;align-items:center;gap:6px;font-size:11px}
.ldot{width:8px;height:8px;border-radius:50%;flex-shrink:0}

/* FILTERS */
.filters{padding:10px 28px;display:flex;gap:6px;flex-wrap:wrap;
  background:var(--bg);border-bottom:1px solid var(--border)}
.fbtn{background:var(--bg3);border:1px solid var(--border);border-radius:6px;
  color:var(--muted);font-size:11px;font-family:'Inter',sans-serif;
  padding:5px 11px;cursor:pointer;transition:all .15s;font-weight:500}
.fbtn:hover,.fbtn.active{background:#1e2532;border-color:var(--blue);color:var(--text)}

/* GRID */
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(560px,1fr));gap:18px;padding:20px 28px}

/* CARD */
.card{background:var(--bg2);border:1px solid var(--border);border-radius:14px;
  overflow:hidden;transition:box-shadow .2s,transform .2s}
.card:hover{box-shadow:0 8px 32px rgba(0,0,0,.5);transform:translateY(-2px)}
.card.bull-card{border-top:2px solid var(--bull)}
.card.bear-card{border-top:2px solid var(--bear)}
.card.hidden{display:none}

/* CARD HEADER */
.ch{padding:12px 16px;display:flex;align-items:flex-start;justify-content:space-between;
  background:rgba(255,255,255,.02);border-bottom:1px solid var(--border);flex-wrap:wrap;gap:8px}
.ch-left{display:flex;flex-direction:column;gap:6px}
.ch-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.cdate{font-size:15px;font-weight:700;font-family:'JetBrains Mono',monospace;letter-spacing:.5px}
.badge{font-size:10px;font-weight:600;padding:2px 7px;border-radius:4px;letter-spacing:.4px;flex-shrink:0}
.b-bull{background:var(--bull-dim);color:var(--bull);border:1px solid rgba(34,197,94,.3)}
.b-bear{background:var(--bear-dim);color:var(--bear);border:1px solid rgba(239,68,68,.3)}
.b-pat{background:rgba(59,130,246,.1);color:#93c5fd;border:1px solid rgba(59,130,246,.25)}
.b-ok{background:rgba(34,197,94,.1);color:var(--bull);border:1px solid rgba(34,197,94,.3)}
.b-no{background:rgba(239,68,68,.1);color:var(--bear);border:1px solid rgba(239,68,68,.3)}
.ch-right{display:flex;flex-direction:column;gap:6px;align-items:flex-end}
.cotbox{padding:4px 10px;border-radius:6px;font-size:11px;font-weight:600;
  font-family:'JetBrains Mono',monospace;white-space:nowrap}
.cot-bs{background:rgba(34,197,94,.15);color:var(--bull);border:1px solid rgba(34,197,94,.3)}
.cot-bm{background:rgba(6,182,212,.12);color:var(--cyan);border:1px solid rgba(6,182,212,.25)}
.cot-n{background:rgba(100,116,139,.12);color:#94a3b8;border:1px solid rgba(100,116,139,.25)}
.cot-bc{background:rgba(139,92,246,.15);color:#c4b5fd;border:1px solid rgba(139,92,246,.3)}
.cot-br{background:rgba(239,68,68,.12);color:var(--bear);border:1px solid rgba(239,68,68,.3)}

/* LEVELS ROW */
.levels-row{padding:8px 16px;display:flex;gap:12px;flex-wrap:wrap;
  background:rgba(0,0,0,.2);border-bottom:1px solid var(--border);font-size:11px}
.lv{display:flex;align-items:center;gap:4px}
.lv-label{color:var(--muted);font-size:10px}
.lv-val{font-family:'JetBrains Mono',monospace;font-weight:600;font-size:11px}
.lv-hit{font-size:9px;padding:1px 5px;border-radius:3px;margin-left:2px}
.lv-hit.yes{background:rgba(34,197,94,.15);color:var(--bull)}
.lv-hit.no{opacity:.4}

/* CHART */
.cwrap{position:relative;height:340px;background:var(--bg3)}
.cc{width:100%;height:100%}

/* CHART OVERLAY */
.co{position:absolute;top:8px;right:10px;display:flex;flex-direction:column;gap:3px;pointer-events:none}
.ot{font-size:9px;font-family:'JetBrains Mono',monospace;padding:2px 6px;border-radius:4px;font-weight:600;opacity:.85}
.ot.bu{background:rgba(34,197,94,.2);color:var(--bull)}
.ot.be{background:rgba(239,68,68,.2);color:var(--bear)}
.ot.nb{background:rgba(59,130,246,.2);color:#93c5fd}

/* FOOTER */
.cf{padding:8px 16px;display:flex;align-items:center;justify-content:space-between;gap:8px;
  border-top:1px solid var(--border);font-size:11px;color:var(--muted);
  background:rgba(0,0,0,.15);flex-wrap:wrap}
.conc{display:flex;align-items:center;gap:6px;font-size:11px;font-weight:500}
.conc.ok{color:var(--bull)}.conc.fail{color:var(--bear)}

/* TOOLTIP */
#tt{position:fixed;display:none;background:#1a2030;border:1px solid var(--border);
  border-radius:8px;padding:8px 12px;font-size:11px;font-family:'JetBrains Mono',monospace;
  pointer-events:none;z-index:9999;min-width:170px;box-shadow:0 8px 24px rgba(0,0,0,.7)}
#tt .ttime{color:var(--muted);font-size:9px;margin-bottom:6px;border-bottom:1px solid var(--border);padding-bottom:4px}
#tt .tr{display:flex;justify-content:space-between;gap:12px;margin:2px 0}
#tt .tl{color:var(--muted)}.tv{font-weight:600}

/* NOTE */
.note{padding:10px 28px;font-size:11px;color:var(--muted);
  background:var(--bg2);border-top:1px solid var(--border);text-align:center}
.note span{color:var(--gold)}
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>📈 NQ Futures — Sesiones Lunes NY · 5 min + Método Trading</h1>
    <p>Velas 5 min · Sesión NY 9:30–16:00 ET · COT · Volume Profile (VAL/POC/VAH) · EMA 200 · 2026</p>
  </div>
  <div style="font-size:11px;color:var(--muted);font-family:'JetBrains Mono',monospace">NQ=F · 6 sesiones</div>
</div>

<div class="stats" id="statsBar">
  <div class="sp"><span class="lbl">Sesiones</span><span class="val blue" id="sTot">6</span></div>
  <div class="sp"><span class="lbl">COT Match</span><span class="val gold" id="sMatch">—</span></div>
  <div class="sp"><span class="lbl">BULL</span><span class="val green" id="sBull">—</span></div>
  <div class="sp"><span class="lbl">BEAR</span><span class="val red" id="sBear">—</span></div>
  <div class="sp"><span class="lbl">Rango prom</span><span class="val blue" id="sRange">—</span></div>
  <div class="sp"><span class="lbl">EMA hits</span><span class="val" style="color:var(--ema)" id="sEma">—</span></div>
  <div class="sp"><span class="lbl">POC hits</span><span class="val gold" id="sPoc">—</span></div>
</div>

<div class="method-box">
  <div class="method-col">
    <strong>MÉTODO DE TRADING — LÍNEAS EN CHART</strong>
    <div class="ml"><div class="ldot" style="background:var(--vah)"></div>VAH — Value Area High (naranja)</div>
    <div class="ml"><div class="ldot" style="background:var(--poc)"></div>POC — Point of Control (amarillo)</div>
    <div class="ml"><div class="ldot" style="background:var(--val)"></div>VAL — Value Area Low (celeste)</div>
  </div>
  <div class="method-col" style="margin-top:16px">
    <div class="ml"><div class="ldot" style="background:var(--ema)"></div>EMA 200 — Media móvil (violeta)</div>
    <div class="ml"><div class="ldot" style="background:#ffffff;opacity:.4"></div>NY Open — Apertura (blanco punteado)</div>
    <div class="ml"><div class="ldot" style="background:var(--gold)"></div>VWAP — Precio promedio ponderado (dorado)</div>
  </div>
  <div class="method-col" style="margin-top:16px;color:var(--muted);font-size:11px;max-width:280px">
    Cada nivel se marca con 🎯 si el precio <em>reaccionó</em> en él durante la sesión.<br>
    Las insignias HIT/--- en la barra de niveles indican activación o no.
  </div>
</div>

<div class="legend">
  <div class="li"><div class="lseg" style="background:var(--vah)"></div>VAH</div>
  <div class="li"><div class="lseg" style="background:var(--poc);height:2px;border-top:1px dashed var(--poc)"></div>POC</div>
  <div class="li"><div class="lseg" style="background:var(--val)"></div>VAL</div>
  <div class="li"><div class="lseg" style="background:var(--ema);height:2px"></div>EMA 200</div>
  <div class="li"><div class="lseg" style="background:rgba(255,255,255,.3);height:1px;border-top:1px dashed white"></div>NY Open</div>
  <div class="li"><div class="lseg" style="background:var(--gold);height:1px;border-top:1px dashed var(--gold)"></div>VWAP</div>
  <div class="li">🔳 Vela alcista = verde | 🔴 Vela bajista = rojo</div>
</div>

<div class="filters">
  <button class="fbtn active" onclick="filterCards('all',this)">Todos (6)</button>
  <button class="fbtn" onclick="filterCards('BULL',this)">🟢 BULL</button>
  <button class="fbtn" onclick="filterCards('BEAR',this)">🔴 BEAR</button>
  <button class="fbtn" onclick="filterCards('match',this)">✅ COT Match</button>
  <button class="fbtn" onclick="filterCards('nomatch',this)">❌ COT Fail</button>
  <button class="fbtn" onclick="filterCards('ema',this)">EMA Hit</button>
  <button class="fbtn" onclick="filterCards('poc',this)">POC Hit</button>
</div>

<div class="grid" id="grid"></div>

<div class="note">
  <span>Nota:</span> 05 Ene y 12 Ene no disponibles (yfinance 5min = máx 60 días).
  Horario ET ajustado (EST=UTC-5, EDT=UTC-4 desde 08 Mar 2026). Todos los niveles VP del día anterior.
</div>

<div id="tt">
  <div class="ttime" id="tt-time"></div>
  <div class="tr"><span class="tl">Open</span><span class="tv" id="tt-o"></span></div>
  <div class="tr"><span class="tl">High</span><span class="tv" id="tt-h"></span></div>
  <div class="tr"><span class="tl">Low</span><span class="tv" id="tt-l"></span></div>
  <div class="tr"><span class="tl">Close</span><span class="tv" id="tt-c" style="color:var(--gold)"></span></div>
  <div class="tr"><span class="tl">Δ desde open</span><span class="tv" id="tt-d"></span></div>
  <div class="tr"><span class="tl">Δ desde ny</span><span class="tv" id="tt-ny"></span></div>
</div>

<script>
const SESSIONS = """ + sessions_json + r""";

/* ── HELPERS ─────────────────────────────────────────────────── */
function cotCls(c){
  if(c>=70)return'cot-bs'; if(c>=50)return'cot-bm';
  if(c>=30)return'cot-n';  return'cot-bc';
}
function cotSig(c){
  if(c>=70)return'🟢 BULL fuerte';
  if(c>=50)return'🟢 BULL mod';
  if(c>=30)return'⚪ Neutro';
  return'🟢 BULL contrario';
}
function realMatch(dir,cot){
  return((cot>=50||cot<30))===(dir==='BULLISH');
}
function toUnix(iso){return Math.floor(new Date(iso).getTime()/1000)}
function fmtET(unixSec,isDST){
  const d=new Date(unixSec*1000);
  const off=isDST?4:5;
  const h=d.getUTCHours()-off;
  const hh=((h%24)+24)%24;
  return`${String(hh).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')} ET`;
}

/* ── STATS ───────────────────────────────────────────────────── */
function updateStats(){
  const s=SESSIONS;
  const matches=s.filter(x=>realMatch(x.direction,x.cot)).length;
  const bulls=s.filter(x=>x.direction==='BULLISH').length;
  const bears=s.filter(x=>x.direction==='BEARISH').length;
  const avg=(s.reduce((a,b)=>a+b.ny_range,0)/s.length).toFixed(0);
  const emaHits=s.filter(x=>x.ema_hit).length;
  const pocHits=s.filter(x=>x.poc_hit).length;
  document.getElementById('sTot').textContent=s.length;
  document.getElementById('sMatch').textContent=`${matches}/${s.length} (${Math.round(matches/s.length*100)}%)`;
  document.getElementById('sBull').textContent=bulls;
  document.getElementById('sBear').textContent=bears;
  document.getElementById('sRange').textContent=avg+' pts';
  document.getElementById('sEma').textContent=`${emaHits}/6`;
  document.getElementById('sPoc').textContent=`${pocHits}/6`;
}

/* ── FILTER ──────────────────────────────────────────────────── */
function filterCards(f,btn){
  document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.card').forEach(card=>{
    const dir=card.dataset.dir;
    const m=card.dataset.match==='true';
    const eh=card.dataset.emahit==='true';
    const ph=card.dataset.pochit==='true';
    let show=true;
    if(f==='BULL') show=dir==='BULLISH';
    if(f==='BEAR') show=dir==='BEARISH';
    if(f==='match') show=m;
    if(f==='nomatch') show=!m;
    if(f==='ema') show=eh;
    if(f==='poc') show=ph;
    card.classList.toggle('hidden',!show);
  });
}

/* ── BUILD CARD DOM ──────────────────────────────────────────── */
function buildCard(s,i){
  const isBull=s.direction==='BULLISH';
  const match=realMatch(s.direction,s.cot);
  const signal=cotSig(s.cot);
  const isDST=s.date>='2026-03-08';

  let concCls='ok',concTxt='';
  if(!match){
    concCls='fail';
    if(s.date==='2026-02-23') concTxt='❌ Aranceles Trump — evento exógeno anuló COT';
    else concTxt='❌ Sin match COT';
  } else {
    if(s.cot<30) concTxt='✅ Rebote contrario — especuladores muy cortos → ↑';
    else concTxt=`✅ COT ${s.cot>=70?'fuerte':'moderado'} → mesa ${isBull?'alcista':'bajista'} confirmada`;
  }

  const hitBadge=(hit,react)=>
    hit ? `<span class="lv-hit yes">🎯 +${react}pts</span>`
        : `<span class="lv-hit no">---</span>`;

  const card=document.createElement('div');
  card.className=`card ${isBull?'bull-card':'bear-card'}`;
  card.dataset.dir=s.direction;
  card.dataset.match=match;
  card.dataset.emahit=s.ema_hit;
  card.dataset.pochit=s.poc_hit;
  card.dataset.idx=i;

  card.innerHTML=`
    <div class="ch">
      <div class="ch-left">
        <div class="ch-row">
          <span class="cdate">${s.date}</span>
          <span class="badge ${isBull?'b-bull':'b-bear'}">${isBull?'▲ BULL':'▼ BEAR'}</span>
          <span class="badge b-pat">${s.pattern}</span>
          <span class="badge ${match?'b-ok':'b-no'}">${match?'✅ COT MATCH':'❌ COT FAIL'}</span>
        </div>
        <div class="ch-row" style="font-size:12px;color:var(--muted)">
          Rango NY: <strong style="color:${isBull?'var(--bull)':'var(--bear)'};margin:0 4px">${s.ny_range} pts</strong>
          · NY Open: <span style="color:var(--text);font-family:'JetBrains Mono',monospace;margin-left:4px">${s.ny_open}</span>
        </div>
      </div>
      <div class="ch-right">
        <div class="cotbox ${cotCls(s.cot)}">COT ${s.cot} · ${signal}</div>
        <div style="font-size:10px;color:var(--muted)">EMA ${s.ema_above?'↑ precio SOBRE':'↓ precio BAJO'} 200</div>
      </div>
    </div>

    <div class="levels-row">
      <div class="lv">
        <span class="lv-label">VAH</span>
        <span class="lv-val" style="color:var(--vah)">${s.vah??'—'}</span>
        ${hitBadge(s.vah_hit,s.vah_react)}
      </div>
      <div class="lv">
        <span class="lv-label">POC</span>
        <span class="lv-val" style="color:var(--poc)">${s.poc??'—'}</span>
        ${hitBadge(s.poc_hit,s.poc_react)}
      </div>
      <div class="lv">
        <span class="lv-label">VAL</span>
        <span class="lv-val" style="color:var(--val)">${s.val??'—'}</span>
        ${hitBadge(s.val_hit,s.val_react)}
      </div>
      <div class="lv" style="margin-left:auto">
        <span class="lv-label">EMA200</span>
        <span class="lv-val" style="color:var(--ema)">${s.ema200??'—'}</span>
        ${hitBadge(s.ema_hit,s.ema_react)}
      </div>
    </div>

    <div class="cwrap">
      <div class="cc" id="chart-${i}"></div>
      <div class="co">
        <div class="ot nb">5 min · 78 barras</div>
        <div class="ot ${isBull?'bu':'be'}">${isBull?'↑':'↓'} ${s.ny_range} pts</div>
      </div>
    </div>

    <div class="cf">
      <div class="conc ${concCls}">${concTxt}</div>
      <div style="font-size:10px;font-family:'JetBrains Mono',monospace;color:var(--muted)">
        ${s.candles.length} velas · NY Session
      </div>
    </div>
  `;

  return card;
}

/* ── RENDER CHART ────────────────────────────────────────────── */
function renderChart(s,i){
  const el=document.getElementById(`chart-${i}`);
  if(!el||!s.candles.length)return;
  const isDST=s.date>='2026-03-08';
  const isBull=s.direction==='BULLISH';

  const chart=LightweightCharts.createChart(el,{
    layout:{background:{type:'solid',color:'#0d1117'},textColor:'#64748b',
      fontFamily:'JetBrains Mono',fontSize:10},
    grid:{vertLines:{color:'rgba(30,37,50,.7)',style:1},horzLines:{color:'rgba(30,37,50,.7)',style:1}},
    crosshair:{mode:LightweightCharts.CrosshairMode.Normal,
      vertLine:{color:'rgba(100,116,139,.6)',labelBackgroundColor:'#1e2532'},
      horzLine:{color:'rgba(100,116,139,.6)',labelBackgroundColor:'#1e2532'}},
    rightPriceScale:{borderColor:'#1e2532',scaleMargins:{top:.06,bottom:.22}},
    timeScale:{borderColor:'#1e2532',timeVisible:true,secondsVisible:false,
      tickMarkFormatter:(t)=>{
        const d=new Date(t*1000);
        const off=isDST?4:5;
        const h=((d.getUTCHours()-off)%24+24)%24;
        return`${String(h).padStart(2,'0')}:${String(d.getUTCMinutes()).padStart(2,'0')}`;
      }},
    handleScroll:true,handleScale:true,
    width:el.clientWidth,height:el.clientHeight,
  });

  /* Candlestick */
  const cs=chart.addCandlestickSeries({
    upColor:'#22c55e',downColor:'#ef4444',
    borderUpColor:'#22c55e',borderDownColor:'#ef4444',
    wickUpColor:'#22c55e',wickDownColor:'#ef4444',
  });
  const data=s.candles.map(c=>({time:toUnix(c.time),open:c.o,high:c.h,low:c.l,close:c.c}));
  cs.setData(data);
  const t0=data[0].time, tN=data[data.length-1].time;

  /* Volume */
  const vs=chart.addHistogramSeries({
    color:'rgba(100,116,139,.2)',priceFormat:{type:'volume'},priceScaleId:'vol',
  });
  chart.priceScale('vol').applyOptions({scaleMargins:{top:.82,bottom:0},drawTicks:false});
  vs.setData(s.candles.map(c=>({
    time:toUnix(c.time),value:c.v||0,
    color:c.c>=c.o?'rgba(34,197,94,.25)':'rgba(239,68,68,.25)',
  })));

  /* VWAP */
  let cp=0,cv=0;
  const vwap=chart.addLineSeries({color:'rgba(245,158,11,.75)',lineWidth:1,
    lineStyle:2,priceLineVisible:false,lastValueVisible:true,title:'VWAP'});
  vwap.setData(s.candles.map(c=>{
    const tp=(c.h+c.l+c.c)/3; const v=c.v||1;
    cp+=tp*v; cv+=v;
    return{time:toUnix(c.time),value:cp/cv};
  }));

  /* NY Open */
  if(s.ny_open){
    const nyL=chart.addLineSeries({color:'rgba(255,255,255,.35)',lineWidth:1,
      lineStyle:3,priceLineVisible:false,lastValueVisible:false,title:'NY Open'});
    nyL.setData([{time:t0,value:s.ny_open},{time:tN,value:s.ny_open}]);
  }

  /* VAH */
  if(s.vah){
    const vahL=chart.addLineSeries({color:'rgba(249,115,22,.85)',lineWidth:1,
      lineStyle:0,priceLineVisible:false,lastValueVisible:true,title:'VAH'});
    vahL.setData([{time:t0,value:s.vah},{time:tN,value:s.vah}]);
  }

  /* POC */
  if(s.poc){
    const pocL=chart.addLineSeries({color:'rgba(250,204,21,.9)',lineWidth:2,
      lineStyle:1,priceLineVisible:false,lastValueVisible:true,title:'POC'});
    pocL.setData([{time:t0,value:s.poc},{time:tN,value:s.poc}]);
  }

  /* VAL */
  if(s.val){
    const valL=chart.addLineSeries({color:'rgba(56,189,248,.85)',lineWidth:1,
      lineStyle:0,priceLineVisible:false,lastValueVisible:true,title:'VAL'});
    valL.setData([{time:t0,value:s.val},{time:tN,value:s.val}]);
  }

  /* EMA 200 */
  if(s.ema200){
    const emaL=chart.addLineSeries({color:'rgba(167,139,250,.9)',lineWidth:1,
      lineStyle:0,priceLineVisible:false,lastValueVisible:true,title:'EMA200'});
    emaL.setData([{time:t0,value:s.ema200},{time:tN,value:s.ema200}]);
  }

  /* Resize */
  new ResizeObserver(()=>chart.applyOptions({width:el.clientWidth,height:el.clientHeight})).observe(el);

  /* Tooltip */
  chart.subscribeCrosshairMove(param=>{
    const tt=document.getElementById('tt');
    if(!param.time||!param.seriesData){tt.style.display='none';return}
    const bar=param.seriesData.get(cs);
    if(!bar){tt.style.display='none';return}
    const delta=bar.close-data[0].close;
    const nyDelta=s.ny_open?bar.close-s.ny_open:null;
    const dStr=(delta>=0?'+':'')+delta.toFixed(2);
    const nyStr=nyDelta!=null?((nyDelta>=0?'+':'')+nyDelta.toFixed(2)+' pts'):null;
    document.getElementById('tt-time').textContent=s.date+'  '+fmtET(param.time,isDST);
    document.getElementById('tt-o').textContent=bar.open.toFixed(2);
    document.getElementById('tt-h').textContent=bar.high.toFixed(2);
    document.getElementById('tt-l').textContent=bar.low.toFixed(2);
    document.getElementById('tt-c').textContent=bar.close.toFixed(2);
    const dtEl=document.getElementById('tt-d');
    dtEl.textContent=dStr+' pts';
    dtEl.style.color=delta>=0?'var(--bull)':'var(--bear)';
    const nyEl=document.getElementById('tt-ny');
    if(nyStr){nyEl.textContent=nyStr;nyEl.style.color=nyDelta>=0?'var(--gold)':'var(--bear)'}
    else nyEl.textContent='—';
    tt.style.display='block';
    const rect=el.getBoundingClientRect();
    tt.style.left=Math.min(param.point.x+rect.left+20,window.innerWidth-200)+'px';
    tt.style.top=Math.max(param.point.y+rect.top-80,8)+'px';
  });
}

/* ── INIT ────────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded',()=>{
  const grid=document.getElementById('grid');
  SESSIONS.forEach((s,i)=>{grid.appendChild(buildCard(s,i))});
  requestAnimationFrame(()=>{SESSIONS.forEach((s,i)=>renderChart(s,i))});
  updateStats();
});
</script>
</body>
</html>"""

with open('lunes_sesiones_5m.html','w',encoding='utf-8') as f:
    f.write(HTML)

print(f"OK: lunes_sesiones_5m.html generado ({len(HTML)//1024} KB)")
