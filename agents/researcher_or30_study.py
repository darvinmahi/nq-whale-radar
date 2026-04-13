"""
=======================================================
INVESTIGADOR 2B: OR 30min — ESTUDIO COMPLETO
=======================================================
Descarga barras de 30min de Polygon.io para verificar:
  - Cómo cerró el OR 30min (9:30-10:00 ET) cada día
  - Si el OR fue BULL/BEAR/FLAT
  - Qué pasó DESPUÉS del OR hasta el cierre NY (4:00 PM)
  - Accuracy REAL de la estrategia por día

Genera: data/or30_study.json + research_or30.html
"""

import os, sys, json, datetime, time, io
import requests

# Encoding fix para Windows
if sys.stdout and hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "research", "daily_master_db.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "or30_study.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "research_or30.html")

# Polygon.io API
POLYGON_KEY = "piDZh82meEE9pepqoto5jqME8ViMhw9o"
POLYGON_BASE = "https://api.polygon.io"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NQ-Intelligence/3.0"})

# Estrategia del usuario
STRATEGY = {
    "monday":    {"side": "LONG",  "or_expect": "BULL"},
    "tuesday":   {"side": "LONG",  "or_expect": "BULL"},
    "wednesday": {"side": "SHORT", "or_expect": "BEAR"},
    "thursday":  {"side": "SHORT", "or_expect": "BEAR"},
    "friday":    {"side": "SHORT", "or_expect": "BEAR"},
}


def load_master_db():
    """Carga las fechas del master DB."""
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    return db.get("records", [])


def fetch_30min_bars(date_str):
    """Descarga barras de 30min para NQ de un día específico."""
    url = f"{POLYGON_BASE}/v2/aggs/ticker/I:NDX/range/30/minute/{date_str}/{date_str}"
    params = {"apiKey": POLYGON_KEY, "sort": "asc", "limit": 50}
    
    try:
        r = SESSION.get(url, params=params, timeout=15)
        if r.status_code == 200:
            data = r.json()
            return data.get("results", [])
        elif r.status_code == 403:
            return None  # plan free limitation
        else:
            return []
    except Exception as e:
        print(f"    [WARN] Polygon error for {date_str}: {e}")
        return []


def classify_or(bars):
    """Clasifica el Opening Range de las barras de 30min.
    
    OR = primera barra de 30min después de 9:30 ET
    - BULL: cierre > apertura
    - BEAR: cierre < apertura
    - FLAT: |cierre - apertura| < 10pts
    
    Returns: (or_dir, or_open, or_close, or_high, or_low, rest_bars)
    """
    if not bars or len(bars) < 2:
        return None, 0, 0, 0, 0, []
    
    # La primera barra (9:30-10:00 ET) es el Opening Range
    or_bar = bars[0]
    or_open = or_bar.get("o", 0)
    or_close = or_bar.get("c", 0)
    or_high = or_bar.get("h", 0)
    or_low = or_bar.get("l", 0)
    or_move = or_close - or_open
    
    if abs(or_move) < 10:
        or_dir = "FLAT"
    elif or_move > 0:
        or_dir = "BULL"
    else:
        or_dir = "BEAR"
    
    # Barras después del OR (10:00 → 16:00)
    rest_bars = bars[1:]
    
    return or_dir, or_open, or_close, or_high, or_low, rest_bars


def simulate_after_or(rule, or_dir, or_open, or_close, or_high, or_low, rest_bars, day_rec):
    """Simula el trade DESPUÉS del OR, si aplica."""
    
    result = {
        "or_dir": or_dir,
        "or_open": round(or_open, 1),
        "or_close": round(or_close, 1),
        "or_range": round(or_high - or_low, 1),
    }
    
    # Skip si OR es FLAT
    if or_dir == "FLAT":
        result["action"] = "SKIP"
        result["reason"] = "OR FLAT (<10pts)"
        result["pnl"] = 0
        return result
    
    # Skip miércoles BULL
    dow = day_rec.get("dow", "").lower()
    if dow == "wednesday" and or_dir == "BULL":
        result["action"] = "SKIP"
        result["reason"] = "MIE BULL - evitar"
        result["pnl"] = 0
        return result
    
    # ¿El OR confirmó la dirección esperada?
    or_aligned = (or_dir == rule["or_expect"])
    result["or_aligned"] = or_aligned
    
    if not or_aligned:
        result["action"] = "SKIP"
        result["reason"] = f"OR {or_dir} vs esperado {rule['or_expect']}"
        result["pnl"] = 0
        return result
    
    # ENTRAR! 
    entry = or_close  # entry después del OR
    stop = or_low if rule["side"] == "LONG" else or_high  # stop al otro lado del OR
    stop_size = abs(entry - stop)
    
    # Calcular P&L con datos del día completo
    ny_close = day_rec.get("nq_close", entry)
    ny_high = day_rec.get("nq_high", entry)
    ny_low = day_rec.get("nq_low", entry)
    
    if rule["side"] == "LONG":
        # Check si el stop fue tocado (low < stop)
        if ny_low <= stop:
            pnl = -(stop_size)
            stopped = True
        else:
            pnl = ny_close - entry
            stopped = False
    else:  # SHORT
        if ny_high >= stop:
            pnl = -(stop_size)
            stopped = True
        else:
            pnl = entry - ny_close
            stopped = False
    
    result["action"] = rule["side"]
    result["entry"] = round(entry, 1)
    result["stop"] = round(stop, 1)
    result["stop_size"] = round(stop_size, 1)
    result["exit"] = round(ny_close, 1)
    result["pnl"] = round(pnl, 1)
    result["won"] = pnl > 0
    result["stopped"] = stopped
    
    return result


def run():
    """Ejecuta el estudio OR 30min."""
    print("\n" + "="*60)
    print("  INVESTIGADOR 2B: OR 30min STUDY")
    print("  Polygon.io 30min bars + Estrategia real")
    print("="*60)
    
    records = load_master_db()
    print(f"  [OK] {len(records)} records del master DB")
    
    # Tomar últimos 6 meses de datos (Polygon free = hasta 2 años atrás)
    # Empezar desde la fecha más reciente e ir hacia atrás
    all_results = []
    equity = 0
    api_calls = 0
    max_api = 250  # Polygon free = 5 calls/min, max ~250 días
    
    # Filtrar solo records con datos válidos
    valid_records = [r for r in records if r.get("nq_open") and r.get("nq_close") and r.get("dow","").lower() in STRATEGY]
    print(f"  [OK] {len(valid_records)} records válidos")
    
    # Solo procesar los últimos N meses (por rate limit de API)
    recent_records = valid_records[-max_api:]
    print(f"  [>>] Procesando {len(recent_records)} días (rate limit)")
    
    for i, rec in enumerate(recent_records):
        date_str = rec.get("date", "")
        dow = rec.get("dow", "").lower()
        rule = STRATEGY[dow]
        
        # Rate limiting (Polygon free = 5/min)
        if api_calls > 0 and api_calls % 5 == 0:
            print(f"    [{i+1}/{len(recent_records)}] Rate limit pause...")
            time.sleep(12)
        
        bars = fetch_30min_bars(date_str)
        api_calls += 1
        
        if bars is None:
            # API limitation (403) — usar datos del master DB como fallback
            # Simular OR direction basado en si open<close (simplificado)
            nq_open = rec.get("nq_open", 0)
            nq_close = rec.get("nq_close", 0)
            direction = rec.get("direction", "")
            or_dir = "BULL" if direction == "BULLISH" else "BEAR" if direction == "BEARISH" else "FLAT"
            or_open = nq_open
            or_close = nq_close
            or_high = rec.get("nq_high", nq_open)
            or_low = rec.get("nq_low", nq_open)
            rest_bars = []
            data_source = "fallback"
        elif len(bars) > 0:
            or_dir, or_open, or_close, or_high, or_low, rest_bars = classify_or(bars)
            if or_dir is None:
                continue
            data_source = "polygon"
        else:
            continue
        
        result = simulate_after_or(rule, or_dir, or_open, or_close, or_high, or_low, rest_bars, rec)
        result["date"] = date_str
        result["dow"] = dow
        result["data_source"] = data_source
        result["prev_day_dir"] = rec.get("prev_day_dir", "")
        result["vxn"] = rec.get("vxn")
        result["cot_signal"] = rec.get("cot_signal", "")
        result["pattern"] = rec.get("pattern", "")
        
        if result.get("action") not in ("SKIP",):
            equity += result.get("pnl", 0)
        result["equity"] = round(equity, 1)
        
        all_results.append(result)
        
        if (i+1) % 25 == 0:
            print(f"    [{i+1}/{len(recent_records)}] processed")
    
    print(f"\n  [OK] {len(all_results)} días procesados")
    
    # Estadísticas
    trades = [r for r in all_results if r.get("action") not in ("SKIP", None)]
    skips = [r for r in all_results if r.get("action") in ("SKIP",)]
    
    if not trades:
        print("  [WARN] No hay trades para analizar")
        return
    
    wins = [t for t in trades if t.get("won")]
    losses = [t for t in trades if t.get("pnl", 0) < 0]
    total_pnl = sum(t["pnl"] for t in trades)
    win_rate = round(len(wins) / len(trades) * 100, 1)
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    pf = abs(sum(t["pnl"] for t in wins)) / abs(sum(t["pnl"] for t in losses)) if losses and sum(t["pnl"] for t in losses) != 0 else 999
    
    # Por día
    by_day = {}
    for dow in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        dt = [t for t in trades if t["dow"] == dow]
        if dt:
            dw = [t for t in dt if t.get("won")]
            by_day[dow] = {
                "trades": len(dt),
                "wins": len(dw),
                "win_rate": round(len(dw)/len(dt)*100, 1),
                "total_pnl": round(sum(t["pnl"] for t in dt), 1),
                "avg_pnl": round(sum(t["pnl"] for t in dt)/len(dt), 1),
            }
    
    # Booster: prev_day same direction
    boost_trades = [t for t in trades if t.get("prev_day_dir") and t.get("or_dir") and
                    (t["prev_day_dir"] == "BULLISH" and t["or_dir"] == "BULL") or
                    (t["prev_day_dir"] == "BEARISH" and t["or_dir"] == "BEAR")]
    boost_wins = [t for t in boost_trades if t.get("won")]
    boost_wr = round(len(boost_wins)/len(boost_trades)*100, 1) if boost_trades else 0
    
    stats = {
        "total_trades": len(trades),
        "total_skipped": len(skips),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "total_pnl": round(total_pnl, 1),
        "avg_pnl": round(total_pnl/len(trades), 1),
        "avg_win": round(avg_win, 1),
        "avg_loss": round(avg_loss, 1),
        "profit_factor": round(pf, 2),
        "by_day": by_day,
        "booster_prev_day": {"trades": len(boost_trades), "win_rate": boost_wr},
    }
    
    # Guardar JSON
    output = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "strategy": "OR_30MIN_CONDITIONAL",
        "description": "Solo entra cuando OR 30min confirma la direccion esperada del dia",
        "stats": stats,
        "results": all_results[-100:],
    }
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Generar HTML
    generate_report_html(stats, trades, all_results, output)
    
    print(f"\n  ====== RESULTADOS OR 30min (CONDICIONAL) ======")
    print(f"  Total trades: {len(trades)} (skipped: {len(skips)})")
    print(f"  Win Rate: {win_rate}%")
    print(f"  Total P&L: {total_pnl:+,.0f} pts")
    print(f"  Profit Factor: {pf:.2f}")
    print(f"  Avg Win: +{avg_win:,.0f} pts | Avg Loss: {avg_loss:,.0f} pts")
    print(f"\n  Por dia:")
    for dow, d in by_day.items():
        print(f"    {dow[:3].upper()}: {d['win_rate']}% WR | {d['total_pnl']:+,.0f} pts | {d['trades']} trades")
    if boost_trades:
        print(f"\n  Booster (prev_day same dir): {boost_wr}% WR ({len(boost_trades)} trades)")
    print(f"\n  -> {OUTPUT_JSON}")
    print(f"  -> {OUTPUT_HTML}")
    
    return output


def generate_report_html(stats, trades, all_results, output):
    """Genera reporte HTML premium."""
    # Equity curve
    eq_data = [{"x": r["date"], "y": r["equity"]} for r in all_results if r.get("action") not in ("SKIP", None)]
    eq_json = json.dumps(eq_data[-200:])
    
    # Trades table
    rows = ""
    for t in reversed(trades[-60:]):
        color = "#22d98a" if t.get("won") else "#f0485a"
        icon = "&#9650;" if t["action"] == "LONG" else "&#9660;"
        a_color = "#22d98a" if t["action"] == "LONG" else "#f0485a"
        stopped = " (SL)" if t.get("stopped") else ""
        rows += f"""<tr>
          <td>{t['date']}</td>
          <td>{t['dow'][:3].upper()}</td>
          <td style="color:{a_color}">{icon} {t['action']}</td>
          <td>{t.get('or_dir','')}</td>
          <td>{t.get('entry',0):,.0f}</td>
          <td>{t.get('exit',0):,.0f}</td>
          <td>{t.get('stop_size',0):,.0f}</td>
          <td style="color:{color};font-weight:700">{'+' if t.get('pnl',0)>0 else ''}{t.get('pnl',0):,.0f}{stopped}</td>
          <td style="color:var(--accent2)">{t.get('equity',0):,.0f}</td>
        </tr>"""
    
    # Day performance cards
    day_cards = ""
    day_map = {"monday":"LUN","tuesday":"MAR","wednesday":"MIE","thursday":"JUE","friday":"VIE"}
    day_colors = {"monday":"#22d98a","tuesday":"#6382ff","wednesday":"#f5d623","thursday":"#f5a623","friday":"#f0485a"}
    for dow, label in day_map.items():
        d = stats.get("by_day", {}).get(dow)
        if d:
            wr = d["win_rate"]
            wr_c = "#22d98a" if wr >= 65 else "#f5a623" if wr >= 50 else "#f0485a"
            pnl_c = "#22d98a" if d["total_pnl"] > 0 else "#f0485a"
            day_cards += f"""<div style="background:rgba(99,130,255,0.06);border:1px solid {day_colors[dow]}44;border-radius:12px;padding:14px;text-align:center;">
              <div style="font-size:0.7rem;font-weight:700;color:{day_colors[dow]};letter-spacing:1px;">{label}</div>
              <div style="font-size:1.6rem;font-weight:800;color:{wr_c};margin:6px 0;">{wr}%</div>
              <div style="font-size:0.65rem;color:#8898bb;">{d['trades']} trades</div>
              <div style="font-size:0.85rem;font-weight:700;color:{pnl_c};margin-top:4px;">{'+' if d['total_pnl']>0 else ''}{d['total_pnl']:,.0f} pts</div>
            </div>"""
    
    bp = stats.get("booster_prev_day", {})
    
    html = f"""<!DOCTYPE html>
<html lang="es"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>OR 30min Study - NQ Whale Radar</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
:root {{ --bg:#0b0e1a;--bg2:#111420;--bg3:#181d2e;--border:rgba(99,130,255,0.18);--accent:#6382ff;--accent2:#38c9e8;--green:#22d98a;--red:#f0485a;--orange:#f5a623;--text:#e4e8ff;--text2:#8898bb; }}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;padding:20px}}
.c{{max-width:1200px;margin:0 auto}}.card{{background:var(--bg2);border:1px solid var(--border);border-radius:16px;padding:20px;margin-bottom:16px}}
.card-t{{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--accent);margin-bottom:14px}}
.sg{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:16px}}
.sb{{background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:12px;text-align:center}}
.sv{{font-size:1.4rem;font-weight:800}}.sl{{font-size:.6rem;color:var(--text2);text-transform:uppercase;margin-top:3px}}
.dg{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}}
table{{width:100%;border-collapse:collapse;font-size:.72rem;font-family:'JetBrains Mono',monospace}}
th{{text-align:left;padding:8px;background:var(--bg3);color:var(--text2);font-size:.62rem;text-transform:uppercase}}
td{{padding:8px;border-bottom:1px solid rgba(99,130,255,0.07)}}.cw{{height:250px;position:relative}}
a.bk{{color:var(--accent2);text-decoration:none;font-size:.8rem;display:inline-flex;align-items:center;gap:5px;margin-bottom:16px}}
h1{{font-size:1.5rem;font-weight:800;margin-bottom:6px}}.st{{color:var(--text2);font-size:.85rem;margin-bottom:24px}}
@media(max-width:768px){{.dg{{grid-template-columns:1fr 1fr}}.sg{{grid-template-columns:1fr 1fr}}}}
</style></head><body>
<div class="c">
<a href="daily_dashboard.html" class="bk">&#9664; Daily Dashboard</a>
<h1>&#127919; OR 30min Study — Estrategia Condicional</h1>
<p class="st">Solo entra cuando el Opening Range (9:30-10:00) CONFIRMA la direccion del dia · {stats['total_trades']} trades · {stats['total_skipped']} skipped</p>

<div class="card"><div class="card-t">&#128176; Performance (Entry condicional — como tu operas)</div>
<div class="sg">
<div class="sb"><div class="sv" style="color:{'var(--green)' if stats['total_pnl']>0 else 'var(--red)'}">{'+' if stats['total_pnl']>0 else ''}{stats['total_pnl']:,.0f}</div><div class="sl">Total P&L (pts)</div></div>
<div class="sb"><div class="sv" style="color:{'var(--green)' if stats['win_rate']>=60 else 'var(--orange)'}">{stats['win_rate']}%</div><div class="sl">Win Rate</div></div>
<div class="sb"><div class="sv" style="color:var(--accent2)">{stats['total_trades']}</div><div class="sl">Trades</div></div>
<div class="sb"><div class="sv" style="color:var(--green)">{stats['profit_factor']}</div><div class="sl">Profit Factor</div></div>
<div class="sb"><div class="sv" style="color:var(--green)">+{stats['avg_win']:,.0f}</div><div class="sl">Avg Win (pts)</div></div>
<div class="sb"><div class="sv" style="color:var(--red)">{stats['avg_loss']:,.0f}</div><div class="sl">Avg Loss (pts)</div></div>
<div class="sb"><div class="sv" style="color:var(--green)">{bp.get('win_rate',0)}%</div><div class="sl">Booster PrevDay ({bp.get('trades',0)})</div></div>
<div class="sb"><div class="sv" style="color:var(--text2)">{stats['avg_pnl']:+,.1f}</div><div class="sl">Avg P&L/Trade</div></div>
</div></div>

<div class="card"><div class="card-t">&#128200; Equity Curve</div><div class="cw"><canvas id="eq"></canvas></div></div>

<div class="card"><div class="card-t">&#128197; Performance por Dia</div><div class="dg">{day_cards}</div></div>

<div class="card" style="overflow-x:auto"><div class="card-t">&#128203; Trades (ultimos 60)</div>
<table><thead><tr><th>Fecha</th><th>Dia</th><th>Accion</th><th>OR Dir</th><th>Entry</th><th>Exit</th><th>Stop</th><th>P&L</th><th>Equity</th></tr></thead>
<tbody>{rows}</tbody></table></div>
</div>
<script>
const d={eq_json};
new Chart(document.getElementById('eq'),{{type:'line',data:{{labels:d.map(x=>x.x),datasets:[{{data:d.map(x=>x.y),borderColor:'#38c9e8',backgroundColor:'rgba(56,201,232,0.1)',fill:true,tension:.3,pointRadius:0,borderWidth:2}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{grid:{{color:'rgba(99,130,255,0.08)'}},ticks:{{maxTicksLimit:10,font:{{size:9}}}}}},y:{{grid:{{color:'rgba(99,130,255,0.08)'}}}}}}}}}});
</script></body></html>"""
    
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    run()
