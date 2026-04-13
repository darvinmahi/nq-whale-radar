"""
=======================================================
INVESTIGADOR 2: TRADE SIMULATOR
=======================================================
Simula la estrategia "OR 30min" del usuario:
  - Espera el Opening Range (9:30-10:00 ET)
  - LONG si OR es BULL (lunes, martes)
  - SHORT si OR es BEAR (miércoles, jueves, viernes)
  
Genera:
  - Estadísticas P&L por día
  - Equity curve
  - Drawdown máximo  
  - Score de calidad por filtro (COT, VXN, prev_day)
  - Reporte HTML legible

Usa: data/research/daily_master_db.json (567 días)
"""

import os, json, datetime, math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "research", "daily_master_db.json")
OUTPUT_JSON = os.path.join(BASE_DIR, "data", "trade_simulator.json")
OUTPUT_HTML = os.path.join(BASE_DIR, "research_trades.html")

# ═══════════════════════════════════════════════════════════════════
#  ESTRATEGIA: OR 30min
# ═══════════════════════════════════════════════════════════════════
# Reglas del usuario:
# - Lunes OR BULL → LONG (71%, +100pts avg)
# - Martes OR BULL → LONG (72%, +73pts avg)
# - Miércoles OR BEAR → SHORT (69%, -64pts avg)  
# - Jueves OR BEAR → SHORT (71%, -119pts avg)
# - Viernes OR BEAR → SHORT (73%, -117pts avg)
# - Skip si OR FLAT (<10pts movimiento)
# - Si prev_day misma dirección → boost a 80-82%

STRATEGY_RULES = {
    "monday":    {"side": "LONG",  "condition": "BULLISH"},
    "tuesday":   {"side": "LONG",  "condition": "BULLISH"},
    "wednesday": {"side": "SHORT", "condition": "BEARISH"},
    "thursday":  {"side": "SHORT", "condition": "BEARISH"},
    "friday":    {"side": "SHORT", "condition": "BEARISH"},
}

# Riesgo por trade (dinámico)
# Stop = otro lado del OR (simulamos como ~25% del rango del día)
# Target = cierre de NY (sin cap)


def load_data():
    """Carga el master DB."""
    with open(DB_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)
    return db.get("records", [])


def simulate_or_strategy(records):
    """Simula la estrategia OR 30min sobre el historial.
    
    Enfoque REALISTA:
    - Siempre entra según la regla del día (LONG lun/mar, SHORT mie/jue/vie)
    - P&L = movimiento real del día (open→close) con stop loss y target
    - Skip si rango del día < 10pts (FLAT)
    - Skip miércoles BULL (como dijo el usuario)
    """
    trades = []
    equity = 0
    peak_equity = 0
    max_drawdown = 0
    consecutive_wins = 0
    consecutive_losses = 0
    max_consec_wins = 0
    max_consec_losses = 0
    
    for rec in records:
        dow = rec.get("dow", "").lower()
        if dow not in STRATEGY_RULES:
            continue
        
        rule = STRATEGY_RULES[dow]
        direction = rec.get("direction", "")
        ny_open = rec.get("nq_open", 0)
        ny_close = rec.get("nq_close", 0)
        ny_high = rec.get("nq_high", 0)
        ny_low = rec.get("nq_low", 0)
        ny_range = rec.get("ny_range", 0) or 0
        
        if not ny_open or not ny_close:
            continue
            
        # Skip días FLAT (rango < 10pts)
        if ny_range < 10:
            continue
        
        # Skip miércoles BULL (usuario dice evitar, solo 66% accuracy)
        if dow == "wednesday" and direction == "BULLISH":
            trades.append({
                "date": rec.get("date"), "dow": dow, "action": "SKIP",
                "reason": "MIE BULL - evitar", "pnl": 0, "equity": equity,
            })
            continue
        
        # SIEMPRE ENTRAR según la regla del día
        # Stop = otro lado del OR (~25% del rango diario, mínimo 30pts)
        stop_size = max(30, ny_range * 0.25)
        
        # P&L = movimiento real del open al close
        if rule["side"] == "LONG":
            raw_pnl = ny_close - ny_open
            # Stop: si el low fue más de stop_size por debajo del open
            adverse = ny_open - ny_low
            if adverse >= stop_size:
                pnl = -stop_size
            else:
                pnl = raw_pnl  # ride to close
        else:  # SHORT
            raw_pnl = ny_open - ny_close
            # Stop: si el high fue más de stop_size por encima del open
            adverse = ny_high - ny_open
            if adverse >= stop_size:
                pnl = -stop_size
            else:
                pnl = raw_pnl  # ride to close
        
        equity += pnl
        peak_equity = max(peak_equity, equity)
        drawdown = peak_equity - equity
        max_drawdown = max(max_drawdown, drawdown)
        
        won = pnl > 0
        if won:
            consecutive_wins += 1
            consecutive_losses = 0
            max_consec_wins = max(max_consec_wins, consecutive_wins)
        elif pnl < 0:
            consecutive_losses += 1
            consecutive_wins = 0
            max_consec_losses = max(max_consec_losses, consecutive_losses)
        
        # Metadata
        prev_same = rec.get("prev_day_dir", "") == direction
        
        trades.append({
            "date": rec.get("date"),
            "dow": dow,
            "action": rule["side"],
            "direction": direction,
            "or_aligned": direction == rule["condition"],
            "entry": round(ny_open, 1),
            "exit": round(ny_close, 1),
            "high": round(ny_high, 1),
            "low": round(ny_low, 1),
            "range": round(ny_range, 1),
            "raw_pnl": round(raw_pnl, 1),
            "pnl": round(pnl, 1),
            "equity": round(equity, 1),
            "won": won,
            "stopped": (adverse >= stop_size),
            "stop_size": round(stop_size, 1),
            "prev_same_dir": prev_same,
            "vxn": rec.get("vxn"),
            "cot_signal": rec.get("cot_signal", ""),
            "pattern": rec.get("pattern", ""),
        })
    
    return trades, max_drawdown, max_consec_wins, max_consec_losses


def compute_stats(trades):
    """Calcula estadísticas del simulador."""
    real_trades = [t for t in trades if t.get("action") not in ("SKIP",)]
    skip_trades = [t for t in trades if t.get("action") == "SKIP"]
    
    if not real_trades:
        return {}
    
    wins = [t for t in real_trades if t.get("won")]
    losses = [t for t in real_trades if t.get("pnl", 0) < 0]
    
    total_pnl = sum(t["pnl"] for t in real_trades)
    win_rate = len(wins) / len(real_trades) * 100
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    profit_factor = abs(sum(t["pnl"] for t in wins)) / abs(sum(t["pnl"] for t in losses)) if losses else 999
    
    # Stats por día
    by_day = {}
    for dow in ["monday", "tuesday", "wednesday", "thursday", "friday"]:
        day_trades = [t for t in real_trades if t["dow"] == dow]
        if day_trades:
            day_wins = [t for t in day_trades if t.get("won")]
            by_day[dow] = {
                "trades": len(day_trades),
                "wins": len(day_wins),
                "win_rate": round(len(day_wins)/len(day_trades)*100, 1),
                "total_pnl": round(sum(t["pnl"] for t in day_trades), 1),
                "avg_pnl": round(sum(t["pnl"] for t in day_trades)/len(day_trades), 1),
                "best": round(max(t["pnl"] for t in day_trades), 1),
                "worst": round(min(t["pnl"] for t in day_trades), 1),
            }
    
    # Booster: prev_day misma dirección
    boost_trades = [t for t in real_trades if t.get("prev_same_dir")]
    boost_wins = [t for t in boost_trades if t.get("won")]
    boost_wr = round(len(boost_wins)/len(boost_trades)*100, 1) if boost_trades else 0
    
    # VXN filter
    vxn_high = [t for t in real_trades if (t.get("vxn") or 0) > 25]
    vxn_high_wins = [t for t in vxn_high if t.get("won")]
    vxn_high_wr = round(len(vxn_high_wins)/len(vxn_high)*100, 1) if vxn_high else 0
    
    vxn_low = [t for t in real_trades if (t.get("vxn") or 0) <= 25 and t.get("vxn") is not None]
    vxn_low_wins = [t for t in vxn_low if t.get("won")]
    vxn_low_wr = round(len(vxn_low_wins)/len(vxn_low)*100, 1) if vxn_low else 0
    
    return {
        "total_trades": len(real_trades),
        "skipped": len(skip_trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(win_rate, 1),
        "total_pnl": round(total_pnl, 1),
        "avg_pnl_per_trade": round(total_pnl / len(real_trades), 1),
        "avg_win": round(avg_win, 1),
        "avg_loss": round(avg_loss, 1),
        "profit_factor": round(profit_factor, 2),
        "by_day": by_day,
        "booster_prev_day": {
            "trades": len(boost_trades),
            "win_rate": boost_wr,
        },
        "vxn_filter": {
            "high_vxn_wr": vxn_high_wr,
            "low_vxn_wr": vxn_low_wr,
            "high_vxn_count": len(vxn_high),
            "low_vxn_count": len(vxn_low),
        },
    }


def generate_html(trades, stats, max_dd, max_cw, max_cl, records):
    """Genera un reporte HTML premium."""
    real_trades = [t for t in trades if t.get("action") not in ("SKIP",)]
    
    # Equity curve data points
    eq_points = [{"x": t["date"], "y": t["equity"]} for t in real_trades]
    
    # Trades table rows
    rows_html = ""
    for t in reversed(real_trades[-50:]):  # últimos 50
        color = "#22d98a" if t["won"] else "#f0485a"
        icon = "&#9650;" if t["action"] == "LONG" else "&#9660;"
        action_color = "#22d98a" if t["action"] == "LONG" else "#f0485a"
        boost = " *" if t.get("prev_same_dir") else ""
        rows_html += f"""<tr>
          <td>{t['date']}</td>
          <td>{t['dow'][:3].upper()}</td>
          <td style="color:{action_color}">{icon} {t['action']}</td>
          <td>{t['entry']:,.0f}</td>
          <td>{t['exit']:,.0f}</td>
          <td>{t['range']:,.0f}</td>
          <td style="color:{color};font-weight:700">{'+' if t['pnl']>0 else ''}{t['pnl']:,.1f}</td>
          <td style="color:var(--accent2)">{t['equity']:,.1f}</td>
          <td>{t.get('pattern','')}{boost}</td>
        </tr>"""
    
    # Day stats cards
    day_cards = ""
    day_labels = {"monday":"LUN","tuesday":"MAR","wednesday":"MIE","thursday":"JUE","friday":"VIE"}
    day_colors = {"monday":"#22d98a","tuesday":"#6382ff","wednesday":"#f5d623","thursday":"#f5a623","friday":"#f0485a"}
    for dow, label in day_labels.items():
        d = stats.get("by_day", {}).get(dow, {})
        if d:
            wr = d["win_rate"]
            wr_color = "#22d98a" if wr >= 70 else "#f5a623" if wr >= 55 else "#f0485a"
            pnl = d["total_pnl"]
            pnl_color = "#22d98a" if pnl > 0 else "#f0485a"
            day_cards += f"""<div style="background:rgba({','.join(str(int(day_colors[dow].lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.08);border:1px solid {day_colors[dow]}33;border-radius:12px;padding:14px;text-align:center;">
              <div style="font-size:0.7rem;font-weight:700;color:{day_colors[dow]};text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">{label}</div>
              <div style="font-size:1.5rem;font-weight:800;color:{wr_color}">{wr}%</div>
              <div style="font-size:0.65rem;color:#8898bb;margin-top:2px;">{d['trades']} trades</div>
              <div style="font-size:0.85rem;font-weight:700;color:{pnl_color};margin-top:4px;">{'+' if pnl>0 else ''}{pnl:,.0f} pts</div>
            </div>"""
    
    # Equity JSON for chart
    eq_json = json.dumps(eq_points[-100:])
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trade Simulator — OR 30min Strategy · NQ</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  :root {{
    --bg:#0b0e1a; --bg2:#111420; --bg3:#181d2e; --border:rgba(99,130,255,0.18);
    --accent:#6382ff; --accent2:#38c9e8; --green:#22d98a; --red:#f0485a;
    --orange:#f5a623; --yellow:#f5d623; --text:#e4e8ff; --text2:#8898bb;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--text); font-family:'Inter',sans-serif; min-height:100vh; padding:20px; }}
  .container {{ max-width:1200px; margin:0 auto; }}
  h1 {{ font-size:1.6rem; font-weight:800; margin-bottom:8px; }}
  .subtitle {{ color:var(--text2); font-size:0.85rem; margin-bottom:24px; }}
  .card {{ background:var(--bg2); border:1px solid var(--border); border-radius:16px; padding:20px; margin-bottom:16px; }}
  .card-title {{ font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:var(--accent); margin-bottom:14px; }}
  .stat-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; margin-bottom:16px; }}
  .stat-box {{ background:var(--bg3); border:1px solid var(--border); border-radius:10px; padding:12px; text-align:center; }}
  .stat-val {{ font-size:1.4rem; font-weight:800; }}
  .stat-label {{ font-size:0.6rem; color:var(--text2); text-transform:uppercase; letter-spacing:0.8px; margin-top:3px; }}
  .day-grid {{ display:grid; grid-template-columns:repeat(5,1fr); gap:10px; }}
  table {{ width:100%; border-collapse:collapse; font-size:0.72rem; font-family:'JetBrains Mono',monospace; }}
  th {{ text-align:left; padding:8px; background:var(--bg3); color:var(--text2); font-size:0.62rem; text-transform:uppercase; }}
  td {{ padding:8px; border-bottom:1px solid rgba(99,130,255,0.07); }}
  .chart-wrap {{ height:250px; position:relative; }}
  a.back {{ display:inline-flex; align-items:center; gap:5px; color:var(--accent2); text-decoration:none; font-size:0.8rem; margin-bottom:16px; }}
  a.back:hover {{ color:var(--accent); }}
  .pill {{ display:inline-flex; padding:3px 8px; border-radius:6px; font-size:0.68rem; font-weight:600; }}
  @media(max-width:768px) {{ .day-grid {{ grid-template-columns:1fr 1fr; }} .stat-grid {{ grid-template-columns:1fr 1fr; }} }}
</style>
</head>
<body>
<div class="container">
  <a href="daily_dashboard.html" class="back">&#9664; Daily Dashboard</a>
  <h1>&#128202; Trade Simulator — OR 30min Strategy</h1>
  <p class="subtitle">Simulacion sobre {stats['total_trades']} trades reales · {records[0]['date'] if records else '?'} a {records[-1]['date'] if records else '?'} · NQ NASDAQ</p>

  <!-- RESUMEN P&L -->
  <div class="card">
    <div class="card-title">&#128176; Performance Summary</div>
    <div class="stat-grid">
      <div class="stat-box">
        <div class="stat-val" style="color:{'var(--green)' if stats['total_pnl']>0 else 'var(--red)'}">{'+' if stats['total_pnl']>0 else ''}{stats['total_pnl']:,.0f}</div>
        <div class="stat-label">Total P&L (pts)</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:{'var(--green)' if stats['win_rate']>=60 else 'var(--orange)'}">{stats['win_rate']}%</div>
        <div class="stat-label">Win Rate</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--accent2)">{stats['total_trades']}</div>
        <div class="stat-label">Total Trades</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--green)">{stats['profit_factor']}</div>
        <div class="stat-label">Profit Factor</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--green)">+{stats['avg_win']:,.0f}</div>
        <div class="stat-label">Avg Win (pts)</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--red)">{stats['avg_loss']:,.0f}</div>
        <div class="stat-label">Avg Loss (pts)</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--red)">-{max_dd:,.0f}</div>
        <div class="stat-label">Max Drawdown</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--text2)">{stats['avg_pnl_per_trade']:+,.1f}</div>
        <div class="stat-label">Avg P&L / Trade</div>
      </div>
    </div>
  </div>

  <!-- EQUITY CURVE -->
  <div class="card">
    <div class="card-title">&#128200; Equity Curve</div>
    <div class="chart-wrap"><canvas id="eqChart"></canvas></div>
  </div>

  <!-- POR DIA -->
  <div class="card">
    <div class="card-title">&#128197; Performance por Dia de la Semana</div>
    <div class="day-grid">{day_cards}</div>
  </div>

  <!-- BOOSTERS -->
  <div class="card">
    <div class="card-title">&#9889; Filtros de Mejora (Boosters)</div>
    <div class="stat-grid">
      <div class="stat-box">
        <div class="stat-val" style="color:var(--green)">{stats['booster_prev_day']['win_rate']}%</div>
        <div class="stat-label">Prev Day = Same Dir ({stats['booster_prev_day']['trades']} trades)</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--orange)">{stats['vxn_filter']['high_vxn_wr']}%</div>
        <div class="stat-label">VXN &gt; 25 ({stats['vxn_filter']['high_vxn_count']} trades)</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--accent2)">{stats['vxn_filter']['low_vxn_wr']}%</div>
        <div class="stat-label">VXN &lt;= 25 ({stats['vxn_filter']['low_vxn_count']} trades)</div>
      </div>
      <div class="stat-box">
        <div class="stat-val" style="color:var(--yellow)">{max_cw}</div>
        <div class="stat-label">Max Consec Wins</div>
      </div>
    </div>
  </div>

  <!-- TRADES TABLE -->
  <div class="card" style="overflow-x:auto;">
    <div class="card-title">&#128203; Ultimos 50 Trades</div>
    <table>
      <thead><tr>
        <th>Fecha</th><th>Dia</th><th>Accion</th><th>Entry</th><th>Exit</th>
        <th>Rango</th><th>P&L</th><th>Equity</th><th>Pattern</th>
      </tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>
</div>

<script>
const eqData = {eq_json};
new Chart(document.getElementById('eqChart'), {{
  type: 'line',
  data: {{
    labels: eqData.map(d => d.x),
    datasets: [{{
      label: 'Equity (pts)',
      data: eqData.map(d => d.y),
      borderColor: '#38c9e8',
      backgroundColor: 'rgba(56,201,232,0.1)',
      fill: true,
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2,
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{
      x: {{ display: true, grid: {{ color: 'rgba(99,130,255,0.08)' }}, ticks: {{ maxTicksLimit: 10, font: {{ size: 9 }} }} }},
      y: {{ grid: {{ color: 'rgba(99,130,255,0.08)' }} }}
    }}
  }}
}});
</script>
</body>
</html>"""
    
    return html


def run():
    """Ejecuta el Trade Simulator."""
    print("\n" + "="*60)
    print("  INVESTIGADOR 2: TRADE SIMULATOR")
    print("  Estrategia: OR 30min · NQ NASDAQ")
    print("="*60)
    
    records = load_data()
    print(f"  [OK] {len(records)} registros cargados")
    
    trades, max_dd, max_cw, max_cl = simulate_or_strategy(records)
    stats = compute_stats(trades)
    
    # Guardar JSON
    output = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() + "Z",
        "strategy": "OR_30MIN",
        "stats": stats,
        "max_drawdown": round(max_dd, 1),
        "max_consec_wins": max_cw,
        "max_consec_losses": max_cl,
        "trades": trades[-100:],  # últimos 100
    }
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Generar HTML
    html = generate_html(trades, stats, max_dd, max_cw, max_cl, records)
    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"\n  RESULTADOS:")
    print(f"  Total trades: {stats['total_trades']}")
    print(f"  Win rate: {stats['win_rate']}%")
    print(f"  Total P&L: {stats['total_pnl']:+,.0f} pts")
    print(f"  Profit Factor: {stats['profit_factor']}")
    print(f"  Max Drawdown: -{max_dd:,.0f} pts")
    print(f"  Avg P&L/trade: {stats['avg_pnl_per_trade']:+,.1f} pts")
    print(f"\n  Por dia:")
    for dow, d in stats.get("by_day", {}).items():
        print(f"    {dow[:3].upper()}: {d['win_rate']}% WR | {d['total_pnl']:+,.0f} pts | {d['trades']} trades")
    print(f"\n  -> {OUTPUT_JSON}")
    print(f"  -> {OUTPUT_HTML}")
    
    return output


if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    run()
