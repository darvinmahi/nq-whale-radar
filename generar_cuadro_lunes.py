"""
CUADRO HISTÓRICO DE LUNES — NQ Whale Radar
Genera HTML interactivo con todos los lunes históricos:
- VXN, Gap, Dirección, Patrón ICT esperado
- Link directo a TradingView
- Foto-ready para análisis
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────
# DATA
# ──────────────────────────────────────────────────────────────
NQ_TICKER  = "QQQ"
VIX_TICKER = "^VIX"
VXN_TICKER = "^VXN"
PERIOD     = "13mo"

print("📥 Descargando datos...")
nq  = yf.download(NQ_TICKER,  period=PERIOD, auto_adjust=True, progress=False)
vix = yf.download(VIX_TICKER, period=PERIOD, auto_adjust=True, progress=False)
vxn = yf.download(VXN_TICKER, period=PERIOD, auto_adjust=True, progress=False)

# Flatten multi-index columns if present
def get_col(frame, col):
    if isinstance(frame.columns, pd.MultiIndex):
        return frame[col].iloc[:, 0]
    return frame[col]

nq_open  = get_col(nq,  "Open")
nq_high  = get_col(nq,  "High")
nq_low   = get_col(nq,  "Low")
nq_close = get_col(nq,  "Close")
vix_cl   = get_col(vix, "Close")
vxn_cl   = get_col(vxn, "Close")

df = pd.DataFrame({"NQ_Open": nq_open, "NQ_High": nq_high,
                   "NQ_Low": nq_low,   "NQ_Close": nq_close,
                   "VIX": vix_cl,      "VXN": vxn_cl}).dropna()
df.index = pd.to_datetime(df.index).tz_localize(None)

# ──────────────────────────────────────────────────────────────
# ZONAS VXN
# ──────────────────────────────────────────────────────────────
def vxn_zona(v):
    if v >= 33:  return "🔴🔴 XFEAR", "#ff2d55", "BULLISH (contrarian)"
    if v >= 25:  return "🔴 FEAR",    "#ff6b35", "LEVE BULLISH"
    if v >= 18:  return "🟡 NEUTRAL", "#f59e0b", "BULLISH"
    return              "🟢 GREED",   "#10b981", "⚠️ BEARISH PELIGRO"

def patron_esperado(vxn_val, gap_pct):
    if vxn_val >= 33:
        return "SWEEP + RETURN (amplitud alta)"
    if abs(gap_pct) > 1.5:
        return "NEWS_DRIVE / GAP"
    if vxn_val >= 25:
        return "SWEEP + RETURN"
    if vxn_val >= 18:
        return "ROTATION_POC / EXPANSION"
    return "SWEEP_H_RETURN (SHORT BIAS)"

def mejor_entrada(vxn_val, resultado):
    """Dónde era la mejor entrada según el patrón del día"""
    if vxn_val >= 33:
        return "Esperar sweep Range High o Low → entry en retorno al rango (buffer +50pts)"
    if vxn_val >= 18 and resultado == "BULLISH":
        return "Sweep del Range Low → SWEEP_L_RETURN → BUY en vuelta al VAL"
    if vxn_val < 18:
        return "Sweep del Range High → SWEEP_H_RETURN → SELL en vuelta al VAH"
    return "Esperar confirmación ICT en NY Open 09:30 ET"

# ──────────────────────────────────────────────────────────────
# FILTRAR LUNES
# ──────────────────────────────────────────────────────────────
lunes_rows = []
dates = df.index.tolist()

for i, date in enumerate(dates):
    if date.weekday() != 0:  # 0 = Lunes
        continue

    # Viernes anterior (VXN de ese día)
    prev_dates = [d for d in dates[:i] if d.weekday() == 4]  # 4 = Viernes
    if not prev_dates:
        prev_dates = [d for d in dates[:i]]  # fallback: día anterior
    if not prev_dates:
        continue

    prev_date = prev_dates[-1]

    nq_price  = df.loc[date, "NQ_Close"]
    nq_open   = df.loc[date, "NQ_Open"]
    nq_prev   = df.loc[prev_date, "NQ_Close"]
    vxn_prev  = df.loc[prev_date, "VXN"]
    vix_prev  = df.loc[prev_date, "VIX"]

    gap_pct   = (nq_open - nq_prev) / nq_prev * 100
    total_pct = (nq_price - nq_open) / nq_open * 100
    range_pct = (df.loc[date, "NQ_High"] - df.loc[date, "NQ_Low"]) / nq_open * 100

    if total_pct > 0.15:
        resultado = "BULLISH"
    elif total_pct < -0.15:
        resultado = "BEARISH"
    else:
        resultado = "FLAT"

    zona, color, bias_vxn = vxn_zona(vxn_prev)
    patron  = patron_esperado(vxn_prev, gap_pct)
    entrada = mejor_entrada(vxn_prev, resultado)

    # TradingView link (NQ1! en chart diario centrado en esa fecha)
    tv_date = date.strftime("%Y-%m-%d")
    tv_link = f"https://www.tradingview.com/chart/?symbol=CME_MINI%3ANQ1%21&interval=3"

    lunes_rows.append({
        "fecha":       date.strftime("%Y-%m-%d"),
        "semana":      f"S{date.isocalendar()[1]}",
        "dia_str":     date.strftime("%d %b %Y"),
        "vxn_prev":    round(float(vxn_prev), 1),
        "vix_prev":    round(float(vix_prev), 1),
        "zona":        zona,
        "zona_color":  color,
        "bias_vxn":    bias_vxn,
        "gap_pct":     round(float(gap_pct), 2),
        "total_pct":   round(float(total_pct), 2),
        "range_pct":   round(float(range_pct), 2),
        "resultado":   resultado,
        "patron":      patron,
        "entrada":     entrada,
        "tv_link":     tv_link,
        "nq_price":    round(float(nq_price)),
    })

lunes_df = pd.DataFrame(lunes_rows).sort_values("fecha", ascending=False)
print(f"✅ {len(lunes_df)} lunes encontrados")

# ──────────────────────────────────────────────────────────────
# GENERAR HTML
# ──────────────────────────────────────────────────────────────
def resultado_badge(r):
    if r == "BULLISH":
        return '<span class="badge bull">🟢 BULLISH</span>'
    if r == "BEARISH":
        return '<span class="badge bear">🔴 BEARISH</span>'
    return '<span class="badge flat">🟡 FLAT</span>'

def gap_color(g):
    if g > 0.5:  return "#00ff80"
    if g < -0.5: return "#ff2d55"
    return "#f59e0b"

rows_html = ""
for _, row in lunes_df.iterrows():
    rows_html += f"""
    <tr class="lunes-row" data-vxn="{row['vxn_prev']}" data-res="{row['resultado']}">
      <td class="fecha-cell">
        <div class="fecha-main">{row['dia_str']}</div>
        <div class="fecha-sub">{row['semana']}</div>
      </td>
      <td>
        <div style="color:{row['zona_color']};font-weight:700;font-size:13px;">{row['zona']}</div>
        <div style="color:#888;font-size:11px;margin-top:2px;">VXN: <b style="color:#fff">{row['vxn_prev']}</b> / VIX: {row['vix_prev']}</div>
      </td>
      <td>
        <div style="color:{gap_color(row['gap_pct'])};font-weight:700;">{'+' if row['gap_pct'] > 0 else ''}{row['gap_pct']}%</div>
      </td>
      <td>
        <div style="color:{'#00ff80' if row['total_pct'] > 0 else '#ff2d55'};font-weight:700;">{'+' if row['total_pct'] > 0 else ''}{row['total_pct']}%</div>
        <div style="color:#666;font-size:11px;">Rng: {row['range_pct']}%</div>
      </td>
      <td>{resultado_badge(row['resultado'])}</td>
      <td>
        <div style="color:#a78bfa;font-size:12px;">{row['patron']}</div>
      </td>
      <td>
        <div class="entrada-cell">{row['entrada']}</div>
      </td>
      <td>
        <a href="{row['tv_link']}" target="_blank" class="tv-btn">📈 TV</a>
      </td>
    </tr>
    """

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📅 Cuadro Lunes — Whale Radar NQ</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Inter', sans-serif;
    background: #0a0a0f;
    color: #e2e8f0;
    min-height: 100vh;
    padding: 24px;
  }}
  .header {{
    text-align: center;
    margin-bottom: 32px;
  }}
  .header h1 {{
    font-size: 28px;
    font-weight: 900;
    background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}
  .header p {{ color: #888; font-size: 14px; }}
  
  /* LEYENDA VXN */
  .legend {{
    display: flex;
    gap: 12px;
    justify-content: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
  }}
  .legend-item {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    text-align: center;
  }}
  .legend-item .pct {{ font-size: 18px; font-weight: 900; }}

  /* FILTROS */
  .filters {{
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    justify-content: center;
  }}
  .filter-btn {{
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.15);
    color: #e2e8f0;
    padding: 8px 18px;
    border-radius: 20px;
    cursor: pointer;
    font-size: 13px;
    font-family: 'Inter', sans-serif;
    transition: all 0.2s;
  }}
  .filter-btn:hover, .filter-btn.active {{
    background: rgba(167,139,250,0.2);
    border-color: #a78bfa;
    color: #a78bfa;
  }}

  /* TABLA */
  .table-wrap {{
    overflow-x: auto;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.08);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
  }}
  thead th {{
    background: rgba(255,255,255,0.05);
    padding: 14px 16px;
    text-align: left;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #888;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    white-space: nowrap;
  }}
  .lunes-row {{
    border-bottom: 1px solid rgba(255,255,255,0.04);
    transition: background 0.15s;
  }}
  .lunes-row:hover {{
    background: rgba(167,139,250,0.06);
  }}
  .lunes-row td {{
    padding: 12px 16px;
    vertical-align: top;
  }}
  .lunes-row.hidden {{ display: none; }}
  
  .fecha-main {{ font-weight: 700; font-size: 14px; }}
  .fecha-sub  {{ color: #666; font-size: 11px; margin-top: 2px; }}
  
  .badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 700;
  }}
  .badge.bull {{ background: rgba(0,255,128,0.12); color: #00ff80; border: 1px solid rgba(0,255,128,0.3); }}
  .badge.bear {{ background: rgba(255,45,85,0.12);  color: #ff2d55; border: 1px solid rgba(255,45,85,0.3); }}
  .badge.flat {{ background: rgba(245,158,11,0.12); color: #f59e0b; border: 1px solid rgba(245,158,11,0.3); }}
  
  .entrada-cell {{
    font-size: 11px;
    color: #94a3b8;
    max-width: 280px;
    line-height: 1.5;
  }}
  
  .tv-btn {{
    display: inline-block;
    background: rgba(96,165,250,0.15);
    border: 1px solid rgba(96,165,250,0.3);
    color: #60a5fa;
    padding: 6px 12px;
    border-radius: 8px;
    text-decoration: none;
    font-size: 12px;
    font-weight: 600;
    transition: all 0.2s;
    white-space: nowrap;
  }}
  .tv-btn:hover {{
    background: rgba(96,165,250,0.25);
    color: #93c5fd;
  }}
  
  /* STATS TOP */
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin-bottom: 24px;
  }}
  .stat-card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 16px;
    text-align: center;
  }}
  .stat-num  {{ font-size: 28px; font-weight: 900; color: #a78bfa; }}
  .stat-label {{ font-size: 11px; color: #888; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.06em; }}

  @media(max-width:768px) {{
    .stats-grid {{ grid-template-columns: repeat(2,1fr); }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>📅 Cuadro Histórico — Lunes NQ</h1>
  <p>Backtest {len(lunes_df)} lunes · Whale Radar · Metodología ICT + VXN · Actualizado {datetime.now().strftime('%d/%m/%Y')}</p>
</div>

<!-- STATS -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="stat-num">{len(lunes_df)}</div>
    <div class="stat-label">Lunes analizados</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#00ff80">{round(len(lunes_df[lunes_df['resultado']=='BULLISH'])/len(lunes_df)*100)}%</div>
    <div class="stat-label">Cerraron BULLISH</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#ff2d55">{round(len(lunes_df[lunes_df['resultado']=='BEARISH'])/len(lunes_df)*100)}%</div>
    <div class="stat-label">Cerraron BEARISH</div>
  </div>
  <div class="stat-card">
    <div class="stat-num" style="color:#f59e0b">{round(lunes_df['range_pct'].mean(),2)}%</div>
    <div class="stat-label">Rango prom. día</div>
  </div>
</div>

<!-- LEYENDA VXN -->
<div class="legend">
  <div class="legend-item">
    <div style="color:#ff2d55" class="pct">100%</div>
    <div>🔴🔴 VXN >33 XFEAR</div>
    <div style="color:#888;font-size:10px;">Bull contrarian · Rango ~6%</div>
  </div>
  <div class="legend-item">
    <div style="color:#ff6b35" class="pct">60%</div>
    <div>🔴 VXN 25–33 FEAR</div>
    <div style="color:#888;font-size:10px;">Leve bull · Rango ~1.7%</div>
  </div>
  <div class="legend-item">
    <div style="color:#f59e0b" class="pct">81%</div>
    <div>🟡 VXN 18–25 NEUTRAL</div>
    <div style="color:#888;font-size:10px;">Bull normal · Rango ~1%</div>
  </div>
  <div class="legend-item">
    <div style="color:#10b981" class="pct" style="color:#ff2d55">75%</div>
    <div>🟢 VXN &lt;18 GREED</div>
    <div style="color:#888;font-size:10px;">⚠️ BEAR · Rango ~0.6%</div>
  </div>
</div>

<!-- FILTROS -->
<div class="filters">
  <button class="filter-btn active" onclick="filtrar('ALL', this)">Todos ({len(lunes_df)})</button>
  <button class="filter-btn" onclick="filtrar('BULLISH', this)">🟢 Bullish ({len(lunes_df[lunes_df['resultado']=='BULLISH'])})</button>
  <button class="filter-btn" onclick="filtrar('BEARISH', this)">🔴 Bearish ({len(lunes_df[lunes_df['resultado']=='BEARISH'])})</button>
  <button class="filter-btn" onclick="filtrarVXN('XFEAR', this)">🔴🔴 XFEAR VXN>33 ({len(lunes_df[lunes_df['vxn_prev']>=33])})</button>
  <button class="filter-btn" onclick="filtrarVXN('FEAR', this)">🔴 FEAR VXN 25-33 ({len(lunes_df[(lunes_df['vxn_prev']>=25)&(lunes_df['vxn_prev']<33)])})</button>
  <button class="filter-btn" onclick="filtrarVXN('NEUTRAL', this)">🟡 NEUTRAL ({len(lunes_df[(lunes_df['vxn_prev']>=18)&(lunes_df['vxn_prev']<25)])})</button>
  <button class="filter-btn" onclick="filtrarVXN('GREED', this)">🟢 GREED &lt;18 ({len(lunes_df[lunes_df['vxn_prev']<18])})</button>
</div>

<!-- TABLA -->
<div class="table-wrap">
<table>
  <thead>
    <tr>
      <th>Fecha Lunes</th>
      <th>VXN / Zona</th>
      <th>Gap Apertura</th>
      <th>Move NY Sesión</th>
      <th>Resultado</th>
      <th>Patrón ICT Esperado</th>
      <th>Mejor Entrada</th>
      <th>Chart</th>
    </tr>
  </thead>
  <tbody id="tabla-body">
    {rows_html}
  </tbody>
</table>
</div>

<div style="text-align:center;margin-top:24px;color:#444;font-size:12px;">
  Whale Radar v2.1 · NQ futures proxy QQQ · Sesión NY 09:30–11:30 ET · VXN del viernes previo<br>
  Haz click en 📈 TV → abre TradingView → toma foto del setup → envíala para análisis
</div>

<script>
function filtrar(tipo, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.lunes-row').forEach(row => {{
    if (tipo === 'ALL' || row.dataset.res === tipo) {{
      row.classList.remove('hidden');
    }} else {{
      row.classList.add('hidden');
    }}
  }});
}}

function filtrarVXN(zona, btn) {{
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  document.querySelectorAll('.lunes-row').forEach(row => {{
    const vxn = parseFloat(row.dataset.vxn);
    let show = false;
    if (zona === 'XFEAR')   show = vxn >= 33;
    if (zona === 'FEAR')    show = vxn >= 25 && vxn < 33;
    if (zona === 'NEUTRAL') show = vxn >= 18 && vxn < 25;
    if (zona === 'GREED')   show = vxn < 18;
    row.classList.toggle('hidden', !show);
  }});
}}
</script>
</body>
</html>"""

output_file = "cuadro_lunes.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n✅ CUADRO GENERADO: {output_file}")
print(f"   Abre en: http://localhost:8765/cuadro_lunes.html")
print(f"\n📊 Resumen rápido:")
print(f"   Total lunes:  {len(lunes_df)}")
print(f"   Bullish:      {len(lunes_df[lunes_df['resultado']=='BULLISH'])} ({round(len(lunes_df[lunes_df['resultado']=='BULLISH'])/len(lunes_df)*100)}%)")
print(f"   Bearish:      {len(lunes_df[lunes_df['resultado']=='BEARISH'])} ({round(len(lunes_df[lunes_df['resultado']=='BEARISH'])/len(lunes_df)*100)}%)")
print(f"   VXN XFEAR>33: {len(lunes_df[lunes_df['vxn_prev']>=33])} lunes")
