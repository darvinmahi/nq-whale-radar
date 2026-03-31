"""
generar_lista_lunes.py — Lista de lunes con VXN real + COT index
Genera HTML con tabla lista para backtest manual en TradingView 15min
"""
import yfinance as yf, csv, json
from datetime import datetime, timedelta, date
from collections import defaultdict

# ─── Config ───────────────────────────────────────────────────
PERIOD = "18mo"
CLOSED = {   # festivos NYSE (lunes cerrados)
    date(2026,2,16), date(2026,1,19),
    date(2025,9,1), date(2025,5,26), date(2025,2,17), date(2025,1,20),
}

# ─── Descargar VXN ────────────────────────────────────────────
print("📥 Descargando VXN 18 meses...")
vxn_raw = yf.download("^VXN", period=PERIOD, auto_adjust=True, progress=False)
if isinstance(vxn_raw.columns, __import__('pandas').MultiIndex):
    vxn_s = vxn_raw["Close"].iloc[:,0]
else:
    vxn_s = vxn_raw["Close"]
vxn_s.index = __import__('pandas').to_datetime(vxn_s.index).tz_localize(None)
vxn_dict = {d.date(): round(float(v),1) for d,v in vxn_s.items() if not __import__('math').isnan(float(v))}
print(f"   VXN: {len(vxn_dict)} días")

# ─── Cargar COT ───────────────────────────────────────────────
cot_rows = []
try:
    with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"], "%Y-%m-%d").date()
                ll  = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
                ls  = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
                net = ll - ls
                cot_rows.append({"date":d,"net":net,"sig":"🟢 BULL" if net>0 else "🔴 BEAR"})
            except: pass
    cot_rows.sort(key=lambda x: x["date"])
    print(f"   COT: {len(cot_rows)} semanas")
except Exception as e:
    print(f"   ⚠️ COT: {e}")

def get_cot(mon):
    prev = [r for r in cot_rows if r["date"] < mon]
    return prev[-1] if prev else {"net":0,"sig":"❓"}

# ─── Zona VXN ─────────────────────────────────────────────────
def zona(v):
    if v>=33: return "🔴🔴 XFEAR","#ff2d55",50
    if v>=25: return "🔴 FEAR",   "#ff6b35",30
    if v>=18: return "🟡 NEUTRAL","#f59e0b",15
    return          "🟢 GREED",  "#10b981",10

# ─── Construir lista de lunes ──────────────────────────────────
all_dates = sorted(vxn_dict.keys())
mondays   = []
for d in all_dates:
    if d.weekday() == 0 and d not in CLOSED:
        # VXN del viernes anterior
        prev_vxn = None
        for delta in range(1,5):
            pd_ = d - timedelta(days=delta)
            if pd_ in vxn_dict:
                prev_vxn = vxn_dict[pd_]; break
        if prev_vxn is None: continue
        cot = get_cot(d)
        z_label, z_color, buf = zona(prev_vxn)
        mondays.append({
            "date":d, "vxn":prev_vxn, "zona":z_label, "color":z_color,
            "buf":buf, "cot_sig":cot["sig"], "cot_net":cot["net"]
        })

mondays.sort(key=lambda x: x["date"], reverse=True)
print(f"✅ {len(mondays)} lunes con datos")

# ─── Generar HTML ─────────────────────────────────────────────
rows = ""
for i,m in enumerate(mondays, 1):
    d = m["date"]
    week = d.isocalendar()[1]
    # TV link (NQ1! 15min)
    tv = f"https://www.tradingview.com/chart/?symbol=CME_MINI%3ANQ1%21&interval=15"
    cot_c = "#34d399" if "BULL" in m["cot_sig"] else "#ff2d55"
    rows += f"""
<tr>
  <td class="num">{i}</td>
  <td class="fc"><b>{d.strftime('%d %b %Y')}</b><div class="sub2">S{week} · {d.strftime('%A')}</div></td>
  <td><span class="vxn" style="color:{m['color']}">{m['vxn']}</span></td>
  <td><span style="color:{m['color']};font-size:11px;font-weight:700">{m['zona']}</span></td>
  <td><span style="color:{cot_c};font-weight:700">{m['cot_sig']}</span><div class="sub2">{m['cot_net']:,}</div></td>
  <td style="color:#a78bfa">{m['buf']} pts</td>
  <td><div class="checks">
    <label><input type="checkbox" class="cb"> Sweep Hi</label>
    <label><input type="checkbox" class="cb"> Sweep Lo</label>
    <label><input type="checkbox" class="cb"> CHoCH 5m</label>
    <label><input type="checkbox" class="cb"> FVG 1m</label>
  </div></td>
  <td><select class="sel" onchange="saveRow(this,{i})">
    <option value="">—</option><option value="BULL">🟢 BULL</option>
    <option value="BEAR">🔴 BEAR</option><option value="FLAT">— FLAT</option>
  </select></td>
  <td><input type="number" class="inp" placeholder="pts" step="0.5" onchange="saveRow(this,{i})"></td>
  <td><a href="{tv}" target="_blank" class="tvbtn">📊 TV</a></td>
</tr>"""

now = datetime.now().strftime("%d/%m/%Y %H:%M")

# Counts by zone
n = len(mondays)
nxf = sum(1 for m in mondays if m["vxn"]>=33)
nfe = sum(1 for m in mondays if 25<=m["vxn"]<33)
nne = sum(1 for m in mondays if 18<=m["vxn"]<25)
ngr = sum(1 for m in mondays if m["vxn"]<18)
nbu = sum(1 for m in mondays if "BULL" in m["cot_sig"])
nbe = sum(1 for m in mondays if "BEAR" in m["cot_sig"])

html = f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>📅 Lista Lunes Backtest — NQ 15min</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Inter',sans-serif;background:#07070f;color:#e2e8f0;padding:20px;min-height:100vh}}
h1{{font-size:22px;font-weight:900;background:linear-gradient(135deg,#a78bfa,#60a5fa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
.meta{{color:#444;font-size:11px;margin:4px 0 20px}}

/* STATS */
.stats{{display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:18px}}
.sc{{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);border-radius:10px;padding:10px;text-align:center}}
.sn{{font-size:22px;font-weight:900}}.sl{{font-size:9px;color:#555;text-transform:uppercase;margin-top:2px}}

/* FILTROS */
.filters{{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap;align-items:center}}
.fb{{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);color:#888;padding:5px 12px;border-radius:16px;cursor:pointer;font-size:10px;font-family:'Inter';transition:all .2s}}
.fb.active,.fb:hover{{background:rgba(167,139,250,0.15);border-color:#a78bfa;color:#a78bfa}}
.sp{{margin-left:auto;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);color:#e2e8f0;padding:5px 10px;border-radius:8px;font-size:11px;font-family:'Inter'}}

/* TABLA */
.wrap{{overflow-x:auto;border-radius:12px;border:1px solid rgba(255,255,255,0.06)}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
thead th{{background:rgba(255,255,255,0.04);padding:9px 10px;text-align:left;font-size:9px;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:#444;border-bottom:1px solid rgba(255,255,255,0.05);white-space:nowrap}}
tr{{border-bottom:1px solid rgba(255,255,255,0.03);transition:background .1s}}
tr:hover{{background:rgba(167,139,250,0.04)}}
tr.done{{background:rgba(0,255,128,0.03)}}
tr.hidden{{display:none}}
td{{padding:8px 10px;vertical-align:middle}}
.num{{color:#333;font-size:10px;text-align:center;width:32px}}
.fc b{{font-size:13px;font-weight:700}}
.sub2{{color:#444;font-size:9px;margin-top:1px}}
.vxn{{font-size:20px;font-weight:900}}

/* FORM ELEMENTS */
.checks{{display:flex;flex-direction:column;gap:3px}}
.checks label{{font-size:10px;color:#666;cursor:pointer;display:flex;align-items:center;gap:4px}}
.checks input{{accent-color:#a78bfa;cursor:pointer}}
.sel{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:#e2e8f0;padding:4px 8px;border-radius:7px;font-family:'Inter';font-size:11px;cursor:pointer}}
.inp{{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.08);color:#e2e8f0;padding:4px 8px;border-radius:7px;font-family:'Inter';font-size:11px;width:70px}}
.tvbtn{{display:inline-block;background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.3);color:#60a5fa;padding:4px 10px;border-radius:8px;text-decoration:none;font-size:10px;font-weight:700;transition:all .2s;white-space:nowrap}}
.tvbtn:hover{{background:rgba(96,165,250,0.2)}}

/* PROGRESS */
.prog{{background:rgba(255,255,255,0.05);border-radius:4px;height:6px;margin:8px 0;overflow:hidden}}
.pbar{{height:100%;background:linear-gradient(90deg,#a78bfa,#60a5fa);border-radius:4px;transition:width .3s}}

/* NOTAS */
.nota{{background:rgba(167,139,250,0.06);border:1px solid rgba(167,139,250,0.15);border-radius:10px;padding:14px;margin-bottom:16px;font-size:12px;line-height:1.8;color:#888}}
.nota b{{color:#a78bfa}}
</style>
</head>
<body>

<h1>📅 Lista Lunes — Backtest NQ 15min con ICT + VXN + COT</h1>
<p class="meta">VXN = cierre del Viernes anterior · COT = semana anterior al lunes · Generado: {now}</p>

<div class="nota">
  <b>Metodología 5→1min:</b>
  1️⃣ En <b>15min</b> identifica el Value Area Asia (VAH / POC / VAL) &nbsp;
  2️⃣ Espera <b>sweep</b> del extremo (VAH o VAL) &nbsp;·&nbsp;
  3️⃣ En <b>5min</b> busca CHoCH / BOS &nbsp;·&nbsp;
  4️⃣ En <b>1min</b> entra en el retest del FVG de 1min &nbsp;·&nbsp;
  Stop = sweep + buffer VXN
</div>

<!-- STATS -->
<div class="stats">
  <div class="sc"><div class="sn">{n}</div><div class="sl">Total Lunes</div></div>
  <div class="sc"><div class="sn" style="color:#ff2d55">{nxf}</div><div class="sl">XFEAR ≥33</div></div>
  <div class="sc"><div class="sn" style="color:#ff6b35">{nfe}</div><div class="sl">FEAR 25–33</div></div>
  <div class="sc"><div class="sn" style="color:#f59e0b">{nne}</div><div class="sl">NEUTRAL 18–25</div></div>
  <div class="sc"><div class="sn" style="color:#10b981">{ngr}</div><div class="sl">GREED &lt;18</div></div>
  <div class="sc"><div class="sn" style="color:#34d399">{nbu}</div><div class="sl">COT BULL</div></div>
</div>

<!-- PROGRESO -->
<div style="display:flex;justify-content:space-between;font-size:10px;color:#555;margin-bottom:4px">
  <span>Progreso backtest</span><span id="prog_txt">0 / {n}</span>
</div>
<div class="prog"><div class="pbar" id="pbar" style="width:0%"></div></div>

<!-- FILTROS -->
<div class="filters">
  <button class="fb active" onclick="fa(this)">Todos ({n})</button>
  <button class="fb" onclick="fz('xfear',this)">🔴🔴 XFEAR ({nxf})</button>
  <button class="fb" onclick="fz('fear',this)">🔴 FEAR ({nfe})</button>
  <button class="fb" onclick="fz('neut',this)">🟡 NEUTRAL ({nne})</button>
  <button class="fb" onclick="fz('greed',this)">🟢 GREED ({ngr})</button>
  <button class="fb" onclick="fz('bull_cot',this)">COT BULL</button>
  <button class="fb" onclick="fz('bear_cot',this)">COT BEAR</button>
  <button class="fb" onclick="fz('pending',this)">⏳ Sin hacer</button>
  <select class="sp" onchange="sortRows(this.value)">
    <option value="num">Orden: Más reciente</option>
    <option value="vxn_desc">VXN High → Low</option>
    <option value="vxn_asc">VXN Low → High</option>
  </select>
</div>

<!-- TABLA -->
<div class="wrap">
<table id="tbl">
  <thead><tr>
    <th>#</th><th>📅 Fecha Lunes</th><th>VXN Vie</th>
    <th>🌡️ Zona</th><th>📜 COT</th><th>🎯 Buffer Stop</th>
    <th>✅ Checks ICT</th><th>📈 Resultado</th><th>💰 PnL (pts)</th>
    <th>📊</th>
  </tr></thead>
  <tbody id="tb">{rows}</tbody>
</table>
</div>

<div style="text-align:center;margin-top:14px;color:#222;font-size:10px">
  NQ Whale Radar v2.2 · VXN cierre viernes anterior · COT Leveraged Money · {now}
</div>

<script>
const LS_KEY = 'bt_lunes_v2';
let saved = JSON.parse(localStorage.getItem(LS_KEY)||'{{}}');

function saveRow(el,i){{
  if(!saved[i]) saved[i]={{}};
  if(el.tagName==='SELECT') saved[i].res=el.value;
  if(el.tagName==='INPUT' && el.type==='number') saved[i].pnl=el.value;
  localStorage.setItem(LS_KEY,JSON.stringify(saved));
  updateProg();
}}

function updateProg(){{
  const rows = document.querySelectorAll('#tb tr:not(.hidden)');
  const done = [...rows].filter(r=>{{const s=r.querySelector('.sel');return s&&s.value}}}).length;
  const tot  = rows.length;
  document.getElementById('prog_txt').textContent=`${{done}} / ${{tot}}`;
  document.getElementById('pbar').style.width=tot?`${{Math.round(done/tot*100)}}%`:'0%';
  [...document.querySelectorAll('#tb tr')].forEach(r=>{{
    const s=r.querySelector('.sel');
    if(s&&s.value) r.classList.add('done'); else r.classList.remove('done');
  }});
}}

// Restore saved state
window.addEventListener('load',()=>{{
  Object.entries(saved).forEach(([i,d])=>{{
    const rows=document.querySelectorAll('#tb tr');
    if(rows[i-1]){{
      const s=rows[i-1].querySelector('.sel');
      const p=rows[i-1].querySelector('.inp');
      if(s&&d.res) s.value=d.res;
      if(p&&d.pnl) p.value=d.pnl;
    }}
  }});
  updateProg();
}});

// Filtros
function fa(b){{setA(b);document.querySelectorAll('#tb tr').forEach(r=>r.classList.remove('hidden'));updateProg()}}
function fz(k,b){{
  setA(b);
  document.querySelectorAll('#tb tr').forEach(r=>{{
    const vxn=+r.querySelector('.vxn')?.textContent||0;
    const cot=r.querySelector('[style*="color:#34d399"], [style*="color:#ff2d55"]')?.textContent||'';
    const sel=r.querySelector('.sel')?.value||'';
    let h=false;
    if(k==='xfear') h=vxn<33;
    else if(k==='fear') h=vxn<25||vxn>=33;
    else if(k==='neut') h=vxn<18||vxn>=25;
    else if(k==='greed') h=vxn>=18;
    else if(k==='bull_cot') h=!cot.includes('BULL');
    else if(k==='bear_cot') h=!cot.includes('BEAR');
    else if(k==='pending') h=!!sel;
    r.classList.toggle('hidden',h);
  }});
  updateProg();
}}
function setA(b){{document.querySelectorAll('.fb').forEach(x=>x.classList.remove('active'));b.classList.add('active')}}

function sortRows(v){{
  const tb=document.getElementById('tb');
  const rows=[...tb.querySelectorAll('tr')];
  rows.sort((a,b)=>{{
    const av=+a.querySelector('.vxn')?.textContent||0;
    const bv=+b.querySelector('.vxn')?.textContent||0;
    if(v==='vxn_desc') return bv-av;
    if(v==='vxn_asc') return av-bv;
    return 0;
  }});
  rows.forEach(r=>tb.appendChild(r));
}}
</script>
</body></html>"""

with open("lista_lunes_backtest.html","w",encoding="utf-8") as f:
    f.write(html)

print("\n✅  lista_lunes_backtest.html")
print("   http://localhost:8765/lista_lunes_backtest.html")
print(f"\n   Zonas VXN: XFEAR={nxf} · FEAR={nfe} · NEUTRAL={nne} · GREED={ngr}")
print(f"   COT: BULL={nbu} · BEAR={nbe}")
print("\n   Columnas: VXN Viernes anterior · COT Net · Buffer stop · Checks ICT · Resultado · PnL")
print("   💾 Progreso se guarda en localStorage → no pierdas tu avance")
