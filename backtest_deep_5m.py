"""
backtest_deep_5m.py  
═══════════════════════════════════════════════════════════════════
DEEP BACKTEST con datos REALES 5min — OR 5/15/30min × Lun-Vie × 2 años
N estadísticamente válido (~100 días por patrón)

OR 5min  = 9:30-9:34 (1 barra exacta)
OR 15min = 9:30-9:44 (3 barras)
OR 30min = 9:30-9:59 (6 barras)

Fuente: data/research/nq_5m_polygon.csv (I:NDX 5min)
"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from datetime import time

CSV = 'data/research/nq_5m_polygon.csv'
OUT = 'backtest_deep_5m.html'

# ── CARGAR ────────────────────────────────────────────────────────
print("═"*68)
print("  DEEP BACKTEST 5min — OR 5/15/30 × Lun-Vie × 2 años")
print("═"*68)

df = pd.read_csv(CSV)
df['et']   = pd.to_datetime(df['Datetime_ET'])
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time
df['dow']  = df['et'].dt.weekday
for c in ['Open','High','Low','Close']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df = df.dropna(subset=['Close']).sort_values('et').reset_index(drop=True)

NY_S  = time(9, 30); NY_E  = time(15, 59)
PM_S  = time(7,  0); PM_E  = time(9,  29)

# OR windows (ET times)
OR_WINDOWS = {
    'OR_5m':  (time(9,30), time(9,34)),   # 1 barra
    'OR_15m': (time(9,30), time(9,44)),   # 3 barras
    'OR_30m': (time(9,30), time(9,59)),   # 6 barras
}

DOW   = {0:'LUNES',1:'MARTES',2:'MIÉRCOLES',3:'JUEVES',4:'VIERNES'}
DCLR  = {0:'#38bdf8',1:'#a78bfa',2:'#34d399',3:'#fb923c',4:'#f472b6'}

def sess(day, ts, te):
    return day[(day['time'] >= ts) & (day['time'] <= te)]

def or_calc(bars):
    if len(bars) < 1: return None
    o_ = float(bars.iloc[0]['Open'])
    c_ = float(bars.iloc[-1]['Close'])
    hi = float(bars['High'].max())
    lo = float(bars['Low'].min())
    mv = c_ - o_; rng = hi - lo
    return {'open':round(o_,2),'close':round(c_,2),'high':round(hi,2),
            'low':round(lo,2),'move':round(mv,1),'range':round(rng,1),
            'dir':'BULL' if mv>8 else ('BEAR' if mv<-8 else 'FLAT')}

# ── PROCESAR CADA DÍA ────────────────────────────────────────────
print("\n  Procesando...")
rows = []
dates_list = sorted(df['date'].unique())

for d in dates_list:
    day = df[df['date'] == d]
    if len(day) < 10: continue
    dow = int(day.iloc[0]['dow'])
    if dow > 4: continue

    ny = sess(day, NY_S, NY_E)
    pm = sess(day, PM_S, PM_E)
    if len(ny) < 3: continue

    ny_o  = float(ny.iloc[0]['Open'])
    ny_c  = float(ny.iloc[-1]['Close'])
    ny_hi = float(ny['High'].max())
    ny_lo = float(ny['Low'].min())
    ny_mv = round(ny_c - ny_o, 1)
    ny_rng= round(ny_hi - ny_lo, 1)
    ny_dir= 'BULL' if ny_mv > 20 else ('BEAR' if ny_mv < -20 else 'FLAT')

    idx_hi = ny['High'].idxmax()
    idx_lo = ny['Low'].idxmin()
    hi_first = bool(idx_hi < idx_lo)

    pm_mv  = 0; pm_dir = 'FLAT'
    if len(pm) >= 2:
        pm_mv  = float(pm.iloc[-1]['Close']) - float(pm.iloc[0]['Open'])
        pm_dir = 'BULL' if pm_mv > 10 else ('BEAR' if pm_mv < -10 else 'FLAT')

    ors = {}
    for ok, (os_, oe_) in OR_WINDOWS.items():
        ors[ok] = or_calc(sess(day, os_, oe_))

    rows.append({
        'date': d, 'dow': dow,
        'ny_move': ny_mv, 'ny_range': ny_rng, 'ny_dir': ny_dir,
        'hi_first': hi_first,
        'pm_move': round(pm_mv,1), 'pm_dir': pm_dir,
        **{f'{ok}_dir':   (ors[ok]['dir']   if ors[ok] else None) for ok in OR_WINDOWS},
        **{f'{ok}_range': (ors[ok]['range'] if ors[ok] else None) for ok in OR_WINDOWS},
        **{f'{ok}_move':  (ors[ok]['move']  if ors[ok] else None) for ok in OR_WINDOWS},
    })

df_r = pd.DataFrame(rows)

# Add prev day
prev_d_map = {}
for i, r in df_r.iterrows():
    prev_d_map[r['date']] = r['ny_dir']

def get_prev(d):
    idx = dates_list.index(d)
    if idx == 0: return 'FLAT'
    return prev_d_map.get(dates_list[idx-1], 'FLAT')

df_r['prev_dir'] = df_r['date'].apply(get_prev)

n_total = len(df_r)
d_min = df_r['date'].min(); d_max = df_r['date'].max()
print(f"  Días: {n_total} | {d_min} → {d_max}")

# ── ANÁLISIS ─────────────────────────────────────────────────────
print("\n  Analizando patrones...")

def analyse(day_df, or_key, or_dir, rng_thresh=0):
    """Retorna stats para OR dir + optional rng filter"""
    col_d = f'{or_key}_dir'; col_r = f'{or_key}_range'
    v = day_df[day_df[col_d].notna()].copy()
    v = v[v[col_d] == or_dir]
    if rng_thresh > 0:
        v = v[v[col_r] >= rng_thresh]
    n = len(v)
    if n < 3: return None
    exp = or_dir
    ok  = (v['ny_dir'] == exp).sum()
    rev = (v['ny_dir'] == ('BEAR' if or_dir=='BULL' else 'BULL')).sum()
    acc = ok/n*100
    
    subs = {}
    for pm_d in ['BULL','BEAR','FLAT']:
        s = v[v['pm_dir']==pm_d]
        if len(s)<3: continue
        c = (s['ny_dir']==exp).sum()
        subs[f'PM_{pm_d}'] = {'label':f'PM {pm_d}','n':len(s),'c':c,'acc':c/len(s)*100,'avg':s['ny_move'].mean()}
    for pr in ['BULL','BEAR','FLAT']:
        s = v[v['prev_dir']==pr]
        if len(s)<3: continue
        c = (s['ny_dir']==exp).sum()
        subs[f'PV_{pr}'] = {'label':f'PrevDay {pr}','n':len(s),'c':c,'acc':c/len(s)*100,'avg':s['ny_move'].mean()}
    for lo,hi,lb in [(0,50,'OR <50'),(50,100,'OR 50-100'),(100,200,'OR 100-200'),(200,500,'OR >200')]:
        if rng_thresh > 0 and lo < rng_thresh: continue
        s = v[(v[col_r]>=lo)&(v[col_r]<hi)]
        if len(s)<3: continue
        c = (s['ny_dir']==exp).sum()
        subs[f'R{lo}'] = {'label':lb,'n':len(s),'c':c,'acc':c/len(s)*100,'avg':s['ny_move'].mean()}
    # combo PM same + rng>100
    s2 = v[(v['pm_dir']==or_dir)&(v[col_r]>=100)]
    if len(s2)>=3:
        c = (s2['ny_dir']==exp).sum()
        subs['COMBO'] = {'label':f'+PM {or_dir} +rng>100','n':len(s2),'c':c,'acc':c/len(s2)*100,'avg':s2['ny_move'].mean()}

    return {
        'n':n,'ok':int(ok),'rev':int(rev),'acc':round(acc,1),
        'rev_pct':round(rev/n*100,1),
        'avg':round(v['ny_move'].mean(),1),
        'med':round(v['ny_move'].median(),1),
        'avg_rng':round(v[col_r].mean(),1),
        'hi_first_pct':round(v['hi_first'].sum()/n*100),
        'subs': subs,
        'detail': v[['date','pm_dir','pm_move',col_r,col_d,'ny_dir','ny_move','ny_range','hi_first','prev_dir']].rename(
            columns={col_r:'or_range',col_d:'or_dir_col'}
        ).assign(correct=lambda x: x['ny_dir']==exp).sort_values('date',ascending=False).to_dict('records')
    }

all_res = {}
for dow in range(5):
    day_df = df_r[df_r['dow']==dow]
    n_day = len(day_df)
    all_res[dow] = {}
    print(f"\n{'━'*68}")
    print(f"  📅 {DOW[dow]} — {n_day} días")
    
    for or_key in OR_WINDOWS:
        all_res[dow][or_key] = {}
        tf = or_key.replace('OR_','')
        for or_dir in ['BULL','BEAR']:
            res = analyse(day_df, or_key, or_dir)
            all_res[dow][or_key][or_dir] = res
            if res is None: continue
            star = "⭐" if res['acc']>=70 and res['n']>=10 else ("🔥" if res['acc']>=60 and res['n']>=10 else "")
            arrow = "▲" if or_dir=='BULL' else "▼"
            print(f"  {tf} {or_dir}{arrow}  N={res['n']:>3}  Acc={res['acc']:.0f}%  Rev={res['rev_pct']:.0f}%  Avg={res['avg']:+.0f}pts  {star}")
            for k, s in sorted(res['subs'].items(), key=lambda x: -x[1]['acc'])[:5]:
                if s['acc'] >= 65:
                    st = " ⭐" if s['acc']>=80 and s['n']>=5 else ""
                    print(f"       +{s['label']:<25} {s['c']}/{s['n']}={s['acc']:.0f}%  avg={s['avg']:+.0f}pts{st}")

# ── TOP PATTERNS ─────────────────────────────────────────────────
print(f"\n\n{'═'*68}")
print(f"  🏆 TOP PATRONES — N≥10, Acc≥60%")
print(f"{'═'*68}")
tops = []
for dow in range(5):
    for ok in OR_WINDOWS:
        for od in ['BULL','BEAR']:
            r = all_res[dow][ok].get(od)
            if r and r['n']>=10:
                tops.append({'dow':DOW[dow],'tf':ok.replace('OR_',''),'dir':od,
                             'flt':'Base','n':r['n'],'acc':r['acc'],'avg':r['avg']})
            if r:
                for k,s in r['subs'].items():
                    if s['n']>=5:
                        tops.append({'dow':DOW[dow],'tf':ok.replace('OR_',''),'dir':od,
                                     'flt':s['label'],'n':s['n'],'acc':s['acc'],'avg':s['avg']})

tops = sorted(tops, key=lambda x: (-x['acc'],-x['n']))
print(f"\n  {'Día':<12} {'TF':<6} {'Dir':<5} {'Filtro':<28} {'N':>4} {'Acc':>6} {'AvgNY':>8}")
print(f"  {'─'*70}")
for t in tops[:20]:
    star = " ⭐" if t['acc']>=75 and t['n']>=10 else (" 🔥" if t['acc']>=65 and t['n']>=10 else "")
    mv_s = f"+{t['avg']:.0f}" if t['avg']>0 else f"{t['avg']:.0f}"
    print(f"  {t['dow']:<12} {t['tf']:<6} {t['dir']:<5} {t['flt']:<28} {t['n']:>4} {t['acc']:>5.0f}% {mv_s:>7}pts{star}")

# ── GENERAR HTML ─────────────────────────────────────────────────
print(f"\n\n  Generando HTML {OUT}...")

def acc_c(a):
    if a>=75: return '#10b981'
    if a>=65: return '#34d399'
    if a>=55: return '#f59e0b'
    return '#64748b'

def dc(d): return '#10b981' if d=='BULL' else ('#ef4444' if d=='BEAR' else '#94a3b8')

html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Deep OR 5m — NQ | {d_min} → {d_max}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080814;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:16px}}
h1{{color:#f59e0b;font-size:17px;text-align:center;margin-bottom:3px}}
.sub{{color:#475569;font-size:10px;text-align:center;margin-bottom:16px}}
.tabs{{display:flex;gap:5px;flex-wrap:wrap;justify-content:center;margin-bottom:16px}}
.tab{{padding:7px 16px;border-radius:18px;font-size:11px;font-weight:700;cursor:pointer;
      border:1px solid #334155;color:#64748b;background:none;transition:.2s}}
.tab.on{{border-color:var(--c);color:var(--c);background:rgba(255,255,255,.04)}}
.ds{{display:none}}.ds.on{{display:block}}
.card{{background:#0e0e1c;border:1px solid #1e2235;border-radius:9px;padding:14px;margin-bottom:12px}}
.ct{{font-size:12px;font-weight:800;margin-bottom:10px}}
.g2{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.g3{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}}
.sb{{background:#060610;border:1px solid #1a1a2e;border-radius:7px;padding:9px;text-align:center}}
.sl{{font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.05em}}
.sv{{font-size:18px;font-weight:900;margin-top:3px}}
.ss{{font-size:9px;color:#475569;margin-top:1px}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
th{{background:#0e0e1c;color:#475569;font-size:9px;font-weight:600;padding:5px 7px;text-align:center;
    border-bottom:1px solid #1e2235;position:sticky;top:0;z-index:5}}
td{{padding:4px 7px;text-align:center;border-bottom:1px solid #0a0a14}}
.ok{{background:#04110a}}.fail{{background:#110404}}.hi{{background:#0c0c1e}}
.pos{{color:#10b981;font-weight:700}}.neg{{color:#ef4444;font-weight:700}}.neu{{color:#94a3b8}}
hr{{border:0;border-top:1px solid #1e2235;margin:12px 0}}
.badge{{display:inline-block;padding:1px 5px;border-radius:6px;font-size:9px;font-weight:700}}
</style>
</head>
<body>
<h1>🔬 DEEP OR STUDY — NQ 5min Real · {n_total} días</h1>
<p class="sub">{d_min} → {d_max} · OR 5m/15m/30m · Lunes a Viernes · I:NDX Polygon.io</p>
<div class="tabs">
"""
for dow in range(5):
    html += f'<button class="tab{"  on" if dow==0 else ""}" style="--c:{DCLR[dow]}" onclick="sd({dow})">{DOW[dow]}</button>\n'
html += '</div>\n'

# TOP TABLE
html += '<div class="card"><div class="ct">🏆 TOP 20 — Ordenados por Accuracy (N≥5)</div><div style="overflow-x:auto"><table><tr><th>Día</th><th>TF</th><th>Dir</th><th>Filtro</th><th>N</th><th>Acc</th><th>AvgNY</th></tr>\n'
for t in tops[:20]:
    ac = acc_c(t['acc']); dc2 = dc(t['dir'])
    mv_c = 'pos' if t['avg']>0 else 'neg'
    star = '⭐' if t['acc']>=75 and t['n']>=10 else ('🔥' if t['acc']>=65 else '')
    bw = min(int(t['acc']*0.65),65)
    html += f"<tr><td style='font-weight:700;color:{DCLR[list(DOW.values()).index(t['dow'])]}'>{t['dow']}</td><td>{t['tf']}</td><td style='color:{dc2};font-weight:700'>{'▲' if t['dir']=='BULL' else '▼'} {t['dir']}</td><td style='text-align:left'>{t['flt']}</td><td>{t['n']}</td><td><span style='color:{ac};font-weight:900;font-size:13px'>{t['acc']:.0f}%</span> <span style='display:inline-block;width:{bw}px;height:6px;background:{ac};border-radius:2px;vertical-align:middle'></span> {star}</td><td class='{mv_c}'>{t['avg']:+.0f}pts</td></tr>\n"
html += '</table></div></div>\n'

# PER-DAY SECTIONS
for dow in range(5):
    day_df2 = df_r[df_r['dow']==dow]
    n_day   = len(day_df2)
    clr     = DCLR[dow]
    bull_n  = (day_df2['ny_dir']=='BULL').sum()
    bear_n  = (day_df2['ny_dir']=='BEAR').sum()
    avg_rng = day_df2['ny_range'].mean()
    med_mv  = day_df2['ny_move'].median()

    html += f'<div class="ds{"  on" if dow==0 else ""}" id="d{dow}">\n'
    html += f'''<div class="card"><div class="ct" style="color:{clr}">📅 {DOW[dow]} — {n_day} días</div>
<div class="g4">
  <div class="sb"><div class="sl">Total</div><div class="sv" style="color:{clr}">{n_day}</div></div>
  <div class="sb"><div class="sl">BULL / BEAR</div><div class="sv" style="font-size:13px"><span class="pos">▲{bull_n/n_day*100:.0f}%</span> / <span class="neg">▼{bear_n/n_day*100:.0f}%</span></div></div>
  <div class="sb"><div class="sl">Rango Prom</div><div class="sv" style="color:#f59e0b">{avg_rng:.0f}pts</div></div>
  <div class="sb"><div class="sl">Mediana NY</div><div class="sv {'pos' if med_mv>0 else 'neg'}" style="font-size:14px">{med_mv:+.0f}pts</div></div>
</div></div>\n'''

    for or_key in OR_WINDOWS:
        tf = or_key.replace('OR_','')
        for or_dir in ['BULL','BEAR']:
            res = all_res[dow][or_key].get(or_dir)
            if not res or res['n'] < 3: continue
            arrow = '▲' if or_dir=='BULL' else '▼'
            ac   = acc_c(res['acc']); dc2 = dc(or_dir)
            star_badge = f'<span class="badge" style="background:rgba(16,185,129,.15);color:#10b981;border:1px solid #10b981;margin-left:6px">⭐ ELITE</span>' if res['acc']>=70 and res['n']>=10 else ''
            bw = min(int(res['acc']*0.9),90)

            html += f'''<div class="card">
<div class="ct">{tf} OR <span style="color:{dc2}">{arrow} {or_dir}</span> → N={res['n']} días{star_badge}</div>
<div class="g2" style="margin-bottom:10px">
  <div>
    <div class="sb" style="margin-bottom:7px">
      <div class="sl">Accuracy NY sigue OR</div>
      <div class="sv" style="color:{ac}">{res['acc']:.0f}%</div>
      <div class="ss">{res['ok']}/{res['n']} días &nbsp;<span style="display:inline-block;width:{bw}px;height:5px;background:{ac};border-radius:2px;vertical-align:middle"></span></div>
    </div>
    <div class="sb">
      <div class="sl">Reversal (opuesto)</div>
      <div class="sv neg" style="font-size:16px">{res['rev_pct']:.0f}%</div>
      <div class="ss">{res['rev']} días</div>
    </div>
  </div>
  <div>
    <div class="sb" style="margin-bottom:7px">
      <div class="sl">Avg / Median NY</div>
      <div class="sv {'pos' if res['avg']>0 else 'neg'}">{res['avg']:+.0f}pts</div>
      <div class="ss">Med: {res['med']:+.0f}pts</div>
    </div>
    <div class="sb">
      <div class="sl">Hi 1° / Lo 1°</div>
      <div class="sv" style="font-size:13px">
        <span style="color:#10b981">H:{res['hi_first_pct']}%</span>  
        <span style="color:#ef4444">L:{100-res['hi_first_pct']}%</span>
      </div>
    </div>
  </div>
</div>
<hr>
<div style="font-size:9px;color:#475569;font-weight:600;margin-bottom:5px">SUB-FILTROS (N≥3)</div>
<table><tr><th style="text-align:left">Filtro</th><th>N</th><th>Acc</th><th>AvgNY</th><th>Bar</th></tr>\n'''
            for k, s in sorted(res['subs'].items(), key=lambda x: -x[1]['acc']):
                if s['n'] < 3: continue
                sa = acc_c(s['acc']); smc = 'pos' if s['avg']>0 else 'neg'
                sbw = min(int(s['acc']*0.55),55)
                rcls = 'ok' if s['acc']>=70 else ('fail' if s['acc']<40 else '')
                st2 = ' ⭐' if s['acc']>=80 and s['n']>=5 else ''
                html += f"<tr class='{rcls}'><td style='text-align:left;color:#94a3b8'>{s['label']}{st2}</td><td>{s['n']}</td><td style='color:{sa};font-weight:700'>{s['acc']:.0f}%</td><td class='{smc}'>{s['avg']:+.0f}pts</td><td><span style='display:inline-block;width:{sbw}px;height:6px;background:{sa};border-radius:2px'></span></td></tr>\n"
            html += '</table>\n<hr>\n'
            html += '<div style="font-size:9px;color:#475569;font-weight:600;margin-bottom:5px">DETALLE DÍAS (más reciente primero)</div>\n'
            html += '<div style="overflow-x:auto"><table><tr><th>Fecha</th><th>PM</th><th>PM mov</th><th>OR Rng</th><th>NY Dir</th><th>NY Mov</th><th>Hi 1°</th><th>PrevDay</th><th>✓</th></tr>\n'
            for dd in res['detail'][:60]:  # max 60 rows
                rcls = 'ok' if dd['correct'] else 'fail'
                chk = '✅' if dd['correct'] else '❌'
                hi_s = '↑' if dd['hi_first'] else '↓'
                or_rng_color = '#f59e0b' if (dd.get('or_range') or 0) >= 100 else '#64748b'
                html += f"<tr class='{rcls}'><td>{dd['date']}</td><td style='color:{dc(dd['pm_dir'])};font-weight:700'>{dd['pm_dir']}</td><td class='{'pos' if dd['pm_move']>0 else 'neg'}'>{dd['pm_move']:+.0f}</td><td style='color:{or_rng_color};font-weight:700'>{dd.get('or_range',0):.0f}pts</td><td style='color:{dc(dd['ny_dir'])};font-weight:700'>{dd['ny_dir']}</td><td class='{'pos' if dd['ny_move']>0 else 'neg'}'>{dd['ny_move']:+.0f}pts</td><td style='color:{'#10b981' if dd['hi_first'] else '#ef4444'}'>{hi_s}</td><td style='color:{dc(dd['prev_dir'])}'>{dd['prev_dir']}</td><td>{chk}</td></tr>\n"
            html += '</table></div></div>\n'
    html += '</div>\n'

html += f'''
<script>
function sd(i){{
  document.querySelectorAll('.ds').forEach((e,j)=>e.classList.toggle('on',j===i));
  document.querySelectorAll('.tab').forEach((e,j)=>e.classList.toggle('on',j===i));
}}
</script>
<div style="text-align:center;margin-top:16px;color:#1e2235;font-size:9px">
  NQ Whale Radar · OR 5m Real · I:NDX Polygon.io · {d_min}→{d_max} · {n_total}días
</div></body></html>'''

with open(OUT,'w',encoding='utf-8') as f: f.write(html)
print(f"  ✅ {OUT} listo")
print("═"*68)
