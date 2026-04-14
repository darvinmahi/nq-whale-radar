"""
backtest_or_puro.py
═══════════════════════════════════════════════════════════════════
BACKTEST LIMPIO — OR puro (5m / 15m / 30m) × Lun-Vie
2 años continuos (2024-04-15 → 2026-04-11)
Fuente: data/research/nq_5m_polygon.csv (I:NDX 5min, Polygon.io)

Pregunta central: cuando el OR de X minutos es BULL o BEAR,
¿qué % de días cierra NY en esa misma dirección?

Sin filtros obligatorios. Todos los días.
Sub-filtros como contexto adicional.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pandas as pd
from datetime import time

CSV = 'data/research/nq_5m_polygon.csv'
OUT = 'backtest_or_puro.html'

# ─── CARGAR ───────────────────────────────────────────────────────
print("═"*68)
print("  BACKTEST OR PURO — 5m/15m/30m × Lun-Vie × 2 años")
print("═"*68)

df = pd.read_csv(CSV)
df['et']   = pd.to_datetime(df['Datetime_ET'])
df['date'] = df['et'].dt.date
df['time'] = df['et'].dt.time
df['dow']  = df['et'].dt.weekday
for c in ['Open','High','Low','Close']:
    df[c] = pd.to_numeric(df[c], errors='coerce')
df = df.dropna(subset=['Close']).sort_values('et').reset_index(drop=True)

DOW     = {0:'LUNES',1:'MARTES',2:'MIÉRCOLES',3:'JUEVES',4:'VIERNES'}
DCLR    = {0:'#38bdf8',1:'#a78bfa',2:'#34d399',3:'#fb923c',4:'#f472b6'}
DOW_EN  = {0:'monday',1:'tuesday',2:'wednesday',3:'thursday',4:'friday'}

NY_S = time(9,30); NY_E = time(15,59)
PM_S = time(7, 0); PM_E = time(9,29)

# OR windows exactas con barras de 5min
OR_WINDOWS = {
    'OR_5m':  (time(9,30), time(9,34)),   # barra 9:30
    'OR_15m': (time(9,30), time(9,44)),   # barras 9:30-9:40-9:44 = 3 barras
    'OR_30m': (time(9,30), time(9,59)),   # 6 barras
}

def sess(d, ts, te): return d[(d['time']>=ts)&(d['time']<=te)]

def calc_or(bars):
    if not len(bars): return None
    o = float(bars.iloc[0]['Open']); c = float(bars.iloc[-1]['Close'])
    hi = float(bars['High'].max()); lo = float(bars['Low'].min())
    mv = c-o; rng = hi-lo
    # Umbral direction: 5pts para 5m, 8pts para 15m, 12pts para 30m
    thr = 5
    return {'move':round(mv,1),'range':round(rng,1),
            'dir':'BULL' if mv>thr else ('BEAR' if mv<-thr else 'FLAT')}

# ─── PROCESAR DÍAS ────────────────────────────────────────────────
print("\n  Procesando días...")
rows = []
dates_list = sorted(df['date'].unique())

for d in dates_list:
    day = df[df['date']==d]
    if len(day)<8: continue
    dow = int(day.iloc[0]['dow'])
    if dow>4: continue

    ny = sess(day, NY_S, NY_E)
    pm = sess(day, PM_S, PM_E)
    if len(ny)<3: continue

    ny_o = float(ny.iloc[0]['Open']); ny_c = float(ny.iloc[-1]['Close'])
    ny_hi = float(ny['High'].max()); ny_lo = float(ny['Low'].min())
    ny_mv = round(ny_c-ny_o,1); ny_rng = round(ny_hi-ny_lo,1)
    ny_dir = 'BULL' if ny_mv>20 else ('BEAR' if ny_mv<-20 else 'FLAT')

    # High o Low — ¿cuál llega primero en NY?
    idx_hi = ny['High'].idxmax(); idx_lo = ny['Low'].idxmin()
    hi_first = bool(idx_hi < idx_lo)

    pm_mv=0; pm_dir='FLAT'
    if len(pm)>=2:
        pm_mv = float(pm.iloc[-1]['Close'])-float(pm.iloc[0]['Open'])
        pm_dir = 'BULL' if pm_mv>10 else ('BEAR' if pm_mv<-10 else 'FLAT')

    r = {'date':d,'dow':dow,'ny_move':ny_mv,'ny_range':ny_rng,'ny_dir':ny_dir,
         'hi_first':hi_first,'pm_move':round(pm_mv,1),'pm_dir':pm_dir}

    for ok,(os_,oe_) in OR_WINDOWS.items():
        bars = sess(day,os_,oe_)
        o_   = calc_or(bars)
        r[f'{ok}_dir']   = o_['dir']   if o_ else None
        r[f'{ok}_range'] = o_['range'] if o_ else None
        r[f'{ok}_move']  = o_['move']  if o_ else None

    rows.append(r)

df_r = pd.DataFrame(rows)

# prev day
pm_map = {}
for _,r in df_r.iterrows(): pm_map[r['date']] = r['ny_dir']
def prev_d(d):
    i = dates_list.index(d)
    return pm_map.get(dates_list[i-1],'?') if i>0 else '?'
df_r['prev_dir'] = df_r['date'].apply(prev_d)

n_tot = len(df_r)
d_min = df_r['date'].min(); d_max = df_r['date'].max()
print(f"  {n_tot} días · {d_min} → {d_max}")

# ─── ANÁLISIS ────────────────────────────────────────────────────
print()

# Collect all pattern stats for HTML
all_stats = {}   # [dow][or_key][or_dir] → dict

for dow in range(5):
    all_stats[dow]={}
    dd = df_r[df_r['dow']==dow]
    nd = len(dd)

    bull_n = (dd['ny_dir']=='BULL').sum()
    bear_n = (dd['ny_dir']=='BEAR').sum()
    flat_n = nd - bull_n - bear_n
    
    print(f"\n{'━'*68}")
    print(f"  📅 {DOW[dow]} — {nd} días | NY base: BULL {bull_n/nd*100:.0f}% · BEAR {bear_n/nd*100:.0f}% · FLAT {flat_n/nd*100:.0f}%")
    print(f"  Rango NY: avg={dd['ny_range'].mean():.0f}pts  mediana={dd['ny_range'].median():.0f}pts")
    print(f"{'━'*68}")

    for ok,(os_,oe_) in OR_WINDOWS.items():
        all_stats[dow][ok]={}
        tf = ok.replace('OR_','')
        col_d = f'{ok}_dir'; col_r = f'{ok}_range'
        valid = dd[dd[col_d].notna()]
        
        # Distribution of OR direction
        bull_or = (valid[col_d]=='BULL').sum()
        bear_or = (valid[col_d]=='BEAR').sum()
        flat_or = (valid[col_d]=='FLAT').sum()
        
        print(f"\n  ── OR {tf} ──  OR dir: BULL={bull_or}({bull_or/len(valid)*100:.0f}%) BEAR={bear_or}({bear_or/len(valid)*100:.0f}%) FLAT={flat_or}({flat_or/len(valid)*100:.0f}%)")

        for or_dir in ['BULL','BEAR']:
            sub = valid[valid[col_d]==or_dir]
            n = len(sub)
            if n<3:
                all_stats[dow][ok][or_dir]=None; continue

            exp = or_dir
            ok_n = (sub['ny_dir']==exp).sum()
            rev_n= (sub['ny_dir']==('BEAR' if or_dir=='BULL' else 'BULL')).sum()
            flt_n= n - ok_n - rev_n
            acc  = ok_n/n*100
            rev_p= rev_n/n*100

            avg_ny = sub['ny_move'].mean()
            med_ny = sub['ny_move'].median()
            avg_rng= sub[col_r].mean()
            hi_fp  = sub['hi_first'].sum()/n*100

            # Sub-filtros (context, not mandatory)
            subs={}
            for pm_d in ['BULL','BEAR','FLAT']:
                s=sub[sub['pm_dir']==pm_d]
                if len(s)<3: continue
                c=(s['ny_dir']==exp).sum()
                subs[f'PM_{pm_d}']={'label':f'PM {pm_d}','n':len(s),'c':c,
                    'acc':round(c/len(s)*100,1),'avg':round(s['ny_move'].mean(),1)}
            for pr in ['BULL','BEAR']:
                s=sub[sub['prev_dir']==pr]
                if len(s)<3: continue
                c=(s['ny_dir']==exp).sum()
                subs[f'PD_{pr}']={'label':f'PrevDay {pr}','n':len(s),'c':c,
                    'acc':round(c/len(s)*100,1),'avg':round(s['ny_move'].mean(),1)}
            # Range buckets
            for lo,hi_r,lb in [(0,50,'OR<50'),(50,100,'OR 50-100'),(100,200,'OR 100-200'),(200,999,'OR>200')]:
                s=sub[(sub[col_r]>=lo)&(sub[col_r]<hi_r)]
                if len(s)<3: continue
                c=(s['ny_dir']==exp).sum()
                subs[f'R{lo}']={'label':lb,'n':len(s),'c':c,
                    'acc':round(c/len(s)*100,1),'avg':round(s['ny_move'].mean(),1)}

            # Detail rows
            detail_rows = sub[['date','pm_dir','pm_move',col_r,'ny_dir','ny_move','ny_range','hi_first','prev_dir']].copy()
            detail_rows = detail_rows.rename(columns={col_r:'or_range'})
            detail_rows['correct'] = detail_rows['ny_dir']==exp
            detail_rows = detail_rows.sort_values('date',ascending=False)

            all_stats[dow][ok][or_dir]={
                'n':n,'ok':int(ok_n),'rev':int(rev_n),'flat':int(flt_n),
                'acc':round(acc,1),'rev_p':round(rev_p,1),
                'avg_ny':round(avg_ny,1),'med_ny':round(med_ny,1),
                'avg_rng':round(avg_rng,1),'hi_fp':round(hi_fp,1),
                'subs':subs, 'detail':detail_rows.to_dict('records')
            }

            star = '⭐' if acc>=70 and n>=15 else ('🔥' if acc>=65 and n>=10 else '')
            arrow = '▲' if or_dir=='BULL' else '▼'
            print(f"  OR {tf} {or_dir}{arrow}  N={n:>3}  Acc={acc:>4.0f}%  Rev={rev_p:>4.0f}%  "
                  f"Avg NY={avg_ny:>+5.0f}pts  AvgOR={avg_rng:>4.0f}pts  {star}")
            # Best sub-filters
            best = sorted(subs.values(), key=lambda x:-x['acc'])[:3]
            for s in best:
                if s['acc']>=70:
                    st='⭐' if s['acc']>=80 and s['n']>=5 else ''
                    print(f"       + {s['label']:<22} {s['c']}/{s['n']}={s['acc']:.0f}%  avg={s['avg']:+.0f}pts {st}")

# ─── TOP PATRONES ─────────────────────────────────────────────────
print(f"\n\n{'═'*68}")
print(f"  🏆 TOP — Todos los días (base OR puro, sin filtros)")
print(f"{'═'*68}")
print(f"\n  {'Día':<12} {'TF':<6} {'Dir':<5} {'N':>4} {'Acc':>6} {'Rev':>6} {'AvgNY':>8} {'MedNY':>8}")
print(f"  {'─'*60}")

base_top = []
for dow in range(5):
    for ok in OR_WINDOWS:
        for od in ['BULL','BEAR']:
            r = all_stats[dow][ok].get(od)
            if r and r['n']>=5:
                base_top.append({'dow':DOW[dow],'dowi':dow,'tf':ok.replace('OR_',''),
                    'dir':od,'n':r['n'],'acc':r['acc'],'rev_p':r['rev_p'],
                    'avg':r['avg_ny'],'med':r['med_ny'],'r':r})

base_top.sort(key=lambda x:(-x['acc'],-x['n']))
for t in base_top[:15]:
    star = '⭐' if t['acc']>=70 and t['n']>=15 else ('🔥' if t['acc']>=65 and t['n']>=10 else '')
    print(f"  {t['dow']:<12} {t['tf']:<6} {t['dir']:<5} {t['n']:>4} {t['acc']:>5.0f}% {t['rev_p']:>5.0f}% {t['avg']:>+7.0f}pts {t['med']:>+7.0f}pts  {star}")

# ─── GENERAR HTML ─────────────────────────────────────────────────
print(f"\n\n  Generando {OUT}...")

def ac(a): 
    if a>=75: return '#10b981'
    if a>=65: return '#34d399'
    if a>=55: return '#f59e0b'
    return '#64748b'
def dc(d): return '#10b981' if d=='BULL' else ('#ef4444' if d=='BEAR' else '#94a3b8')

html_parts = [f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OR Puro Backtest — NQ | {d_min}→{d_max}</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#080814;color:#e2e8f0;font-family:'Segoe UI',sans-serif;padding:16px;font-size:13px}}
h1{{color:#f59e0b;font-size:18px;text-align:center;margin-bottom:3px}}
.sub{{color:#475569;font-size:10px;text-align:center;margin-bottom:16px}}
.tabs{{display:flex;gap:5px;flex-wrap:wrap;justify-content:center;margin-bottom:16px}}
.tab{{padding:7px 18px;border-radius:18px;font-size:11px;font-weight:700;cursor:pointer;
      border:1px solid #334155;color:#64748b;background:none;transition:.2s}}
.tab.on{{border-color:var(--c);color:var(--c);background:rgba(255,255,255,.04)}}
.ds{{display:none}}.ds.on{{display:block}}
.card{{background:#0e0e1c;border:1px solid #1e2235;border-radius:9px;padding:16px;margin-bottom:12px}}
.ct{{font-size:13px;font-weight:800;margin-bottom:10px;display:flex;align-items:center;gap:8px}}
.g3{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:12px}}
.g4{{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:12px}}
.sb{{background:#060610;border:1px solid #1a1a2e;border-radius:7px;padding:10px;text-align:center}}
.sl{{font-size:9px;color:#475569;text-transform:uppercase;letter-spacing:.05em}}
.sv{{font-size:20px;font-weight:900;margin-top:3px}}
.ss{{font-size:9px;color:#475569;margin-top:2px}}
.or-block{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}}
.or-card{{background:#0a0a18;border:1px solid #252540;border-radius:8px;padding:14px}}
.or-title{{font-size:12px;font-weight:800;margin-bottom:10px}}
.big-acc{{font-size:42px;font-weight:900;line-height:1}}
.acc-sub{{font-size:11px;color:#475569;margin-top:4px}}
.bar-row{{height:6px;background:#1a1a2e;border-radius:3px;margin:6px 0 10px}}
.bar-fill{{height:100%;border-radius:3px}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
th{{background:#0e0e1c;color:#475569;font-size:9px;font-weight:600;padding:5px 7px;text-align:center;
    border-bottom:1px solid #1e2235;position:sticky;top:0;z-index:5}}
td{{padding:4px 7px;text-align:center;border-bottom:1px solid #09090f;vertical-align:middle}}
.ok{{background:#03100a}}.fail{{background:#100303}}
.pos{{color:#10b981;font-weight:700}}.neg{{color:#ef4444;font-weight:700}}
hr{{border:0;border-top:1px solid #1e2235;margin:12px 0}}
.badge{{display:inline-block;padding:2px 7px;border-radius:8px;font-size:9px;font-weight:700}}
.badge-elite{{background:rgba(16,185,129,.12);color:#10b981;border:1px solid rgba(16,185,129,.3)}}
.badge-ok{{background:rgba(52,211,153,.1);color:#34d399;border:1px solid rgba(52,211,153,.25)}}
</style>
</head>
<body>
<h1>📊 OR PURO — Opening Range × Lunes a Viernes</h1>
<p class="sub">I:NDX 5min · Polygon.io · {d_min} → {d_max} · {n_tot} días continuos · OR 5m / 15m / 30m</p>
<div class="tabs">
"""]

for dow in range(5):
    html_parts.append(f'<button class="tab{"  on" if dow==0 else ""}" style="--c:{DCLR[dow]}" onclick="sd({dow})">{DOW[dow]}</button>\n')
html_parts.append('</div>\n')

# TOP TABLE
html_parts.append('<div class="card"><div class="ct">🏆 Ranking Base — OR puro sin filtros (N≥5)</div><div style="overflow-x:auto"><table>\n<tr><th>Día</th><th>TF</th><th>Dirección OR</th><th>N días</th><th>Acc</th><th>Reversal</th><th>Avg NY</th><th>Med NY</th></tr>\n')
for t in base_top[:15]:
    a_c=ac(t['acc']); d_c=dc(t['dir']); mv_c='pos' if t['avg']>0 else 'neg'
    bw=min(int(t['acc']*0.65),65)
    star = '⭐' if t['acc']>=70 and t['n']>=15 else ('🔥' if t['acc']>=65 and t['n']>=10 else '')
    html_parts.append(f"<tr><td style='font-weight:700;color:{DCLR[t['dowi']]}'>{t['dow']}</td>"
        f"<td>{t['tf']}</td>"
        f"<td><span style='color:{d_c};font-weight:700'>{'▲' if t['dir']=='BULL' else '▼'} {t['dir']}</span></td>"
        f"<td style='font-weight:700'>{t['n']}</td>"
        f"<td><span style='color:{a_c};font-weight:900;font-size:14px'>{t['acc']:.0f}%</span> "
        f"<span style='display:inline-block;width:{bw}px;height:5px;background:{a_c};border-radius:2px;vertical-align:middle'></span> {star}</td>"
        f"<td style='color:#ef4444'>{t['rev_p']:.0f}%</td>"
        f"<td class='{mv_c}'>{t['avg']:+.0f}pts</td>"
        f"<td class='{mv_c}'>{t['med']:+.0f}pts</td></tr>\n")
html_parts.append('</table></div></div>\n')

# PER-DAY
for dow in range(5):
    dd = df_r[df_r['dow']==dow]
    nd = len(dd)
    clr= DCLR[dow]
    bull_n=(dd['ny_dir']=='BULL').sum(); bear_n=(dd['ny_dir']=='BEAR').sum()
    flat_n=nd-bull_n-bear_n
    avg_rng=dd['ny_range'].mean(); med_mv=dd['ny_move'].median()

    html_parts.append(f'<div class="ds{"  on" if dow==0 else ""}" id="d{dow}">\n')
    # Day header
    html_parts.append(f'''<div class="card">
<div class="ct" style="color:{clr}">📅 {DOW[dow]} · {nd} días</div>
<div class="g4">
  <div class="sb"><div class="sl">Días totales</div><div class="sv" style="color:{clr}">{nd}</div></div>
  <div class="sb"><div class="sl">BULL / BEAR / FLAT</div>
    <div class="sv" style="font-size:13px">
      <span class="pos">▲{bull_n/nd*100:.0f}%</span>
      <span style="color:#475569;font-size:10px;margin:0 3px">/</span>
      <span class="neg">▼{bear_n/nd*100:.0f}%</span>
      <span style="color:#475569;font-size:10px;margin:0 3px">/</span>
      <span style="color:#64748b">{flat_n/nd*100:.0f}%</span>
    </div>
  </div>
  <div class="sb"><div class="sl">Rango NY prom</div><div class="sv" style="color:#f59e0b">{avg_rng:.0f}pts</div></div>
  <div class="sb"><div class="sl">Mediana cierre</div><div class="sv {'pos' if med_mv>0 else 'neg'}" style="font-size:15px">{med_mv:+.0f}pts</div></div>
</div>
</div>\n''')

    # Each OR
    for ok in OR_WINDOWS:
        tf = ok.replace('OR_','')
        bull_res = all_stats[dow][ok].get('BULL')
        bear_res = all_stats[dow][ok].get('BEAR')

        html_parts.append(f'<div class="card" style="border-color:rgba(255,255,255,.06)">\n')
        html_parts.append(f'<div class="ct">⏱ OR {tf} <span style="font-size:10px;color:#475569;font-weight:400;margin-left:6px">Opening Range primeros {tf}</span></div>\n')
        html_parts.append('<div class="or-block">\n')

        for or_dir, res in [('BULL', bull_res), ('BEAR', bear_res)]:
            if not res:
                html_parts.append(f'<div class="or-card"><div class="or-title">OR {or_dir} — sin datos</div></div>\n')
                continue
            d_c = dc(or_dir); a_c2 = ac(res['acc'])
            arrow = '▲' if or_dir=='BULL' else '▼'
            badge = ('<span class="badge badge-elite">⭐ ELITE</span>' if res['acc']>=70 and res['n']>=15 else
                     '<span class="badge badge-ok">🔥 FUERTE</span>' if res['acc']>=65 and res['n']>=10 else '')
            bw2 = min(int(res['acc']*0.9),90)

            html_parts.append(f'''<div class="or-card">
<div class="or-title">OR <span style="color:{d_c}">{arrow} {or_dir}</span> &nbsp; {badge}</div>
<div class="big-acc" style="color:{a_c2}">{res['acc']:.0f}%</div>
<div class="acc-sub">{res['ok']}/{res['n']} días siguen OR · Rev: {res['rev_p']:.0f}%</div>
<div class="bar-row"><div class="bar-fill" style="width:{bw2}%;background:{a_c2}"></div></div>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:10px">
  <div class="sb"><div class="sl">Avg NY</div>
    <div class="sv {'pos' if res['avg_ny']>0 else 'neg'}" style="font-size:15px">{res['avg_ny']:+.0f}pts</div></div>
  <div class="sb"><div class="sl">Hi 1° NY</div>
    <div class="sv" style="font-size:13px">
      <span style="color:#10b981">H:{res['hi_fp']:.0f}%</span> 
      <span style="color:#ef4444">L:{100-res['hi_fp']:.0f}%</span>
    </div>
  </div>
</div>
<hr>
<div style="font-size:9px;color:#475569;font-weight:600;margin-bottom:5px">CONTEXTO EXTRA (PM, PrevDay, Rango OR)</div>
<table><tr><th style="text-align:left">Filtro</th><th>N</th><th>Acc</th><th>AvgNY</th></tr>\n''')

            for k,s in sorted(res['subs'].items(),key=lambda x:-x[1]['acc']):
                if s['n']<3: continue
                s_ac=ac(s['acc']); smc='pos' if s['avg']>0 else 'neg'
                rc='ok' if s['acc']>=70 else ('fail' if s['acc']<40 else '')
                st3='⭐' if s['acc']>=80 and s['n']>=5 else ''
                html_parts.append(f"<tr class='{rc}'><td style='text-align:left;color:#94a3b8'>{s['label']}{st3}</td>"
                    f"<td>{s['n']}</td><td style='color:{s_ac};font-weight:700'>{s['acc']:.0f}%</td>"
                    f"<td class='{smc}'>{s['avg']:+.0f}pts</td></tr>\n")

            html_parts.append('</table>\n<hr>\n')
            html_parts.append('<div style="font-size:9px;color:#475569;font-weight:600;margin-bottom:4px">TODOS LOS DÍAS</div>')
            html_parts.append('<div style="overflow-x:auto;max-height:320px;overflow-y:auto"><table>\n')
            html_parts.append('<tr><th>Fecha</th><th>PM</th><th>OR mov</th><th>OR rng</th><th>NY dir</th><th>NY mov</th><th>Hi1°</th><th>PrevDay</th><th>✓</th></tr>\n')

            for dd2 in res['detail']:
                rc='ok' if dd2['correct'] else 'fail'
                chk='✅' if dd2['correct'] else '❌'
                hi_s='↑H' if dd2['hi_first'] else '↓L'
                or_rng = dd2.get('or_range',0) or 0
                rng_c = '#f59e0b' if or_rng>=100 else '#64748b'
                html_parts.append(
                    f"<tr class='{rc}'>"
                    f"<td>{dd2['date']}</td>"
                    f"<td style='color:{dc(dd2['pm_dir'])};font-weight:700'>{dd2['pm_dir']}</td>"
                    f"<td class='{'pos' if dd2['pm_move']>0 else 'neg'}'>{dd2['pm_move']:+.0f}</td>"
                    f"<td style='color:{rng_c};font-weight:700'>{or_rng:.0f}pts</td>"
                    f"<td style='color:{dc(dd2['ny_dir'])};font-weight:700'>{dd2['ny_dir']}</td>"
                    f"<td class='{'pos' if dd2['ny_move']>0 else 'neg'}'>{dd2['ny_move']:+.0f}pts</td>"
                    f"<td style='color:{'#10b981' if dd2['hi_first'] else '#ef4444'}'>{hi_s}</td>"
                    f"<td style='color:{dc(dd2['prev_dir'])}'>{dd2['prev_dir']}</td>"
                    f"<td>{chk}</td></tr>\n")

            html_parts.append('</table></div></div>\n')

        html_parts.append('</div>\n</div>\n')

    html_parts.append('</div>\n')

html_parts.append(f'''
<script>
function sd(i){{
  document.querySelectorAll('.ds').forEach((e,j)=>e.classList.toggle('on',j===i));
  document.querySelectorAll('.tab').forEach((e,j)=>e.classList.toggle('on',j===i));
}}
</script>
<div style="text-align:center;margin-top:16px;color:#1e2235;font-size:9px">
  NQ Whale Radar · OR Puro · I:NDX 5min · Polygon.io · {d_min}→{d_max} · {n_tot} días continuos
</div></body></html>''')

with open(OUT,'w',encoding='utf-8') as f: f.write(''.join(html_parts))
print(f"  ✅ Guardado: {OUT}")
print("═"*68)
