"""
martes_5min_apertura.py
Descarga datos 5min NQ y estudia la apertura NY del MARTES:
- Vela 9:30 (5min)
- Vela 9:35 (5min)
- Vela 9:40 (5min)  
- Combos de 2 y 3 velas → WR del día
yfinance limita 5min a los ultimos 60 dias, usamos los disponibles
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta, date
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; SOFT='#94a3b8'; DIM='#475569'; ORG='#f97316'
WHITE='#f1f5f9'

# ── DESCARGAR 5MIN (max ~60 dias en yfinance) ─────────────────────────
print("Descargando NQ 5min (ultimos 60 dias)...")
ticker = yf.Ticker("NQ=F")
df5 = ticker.history(period="60d", interval="5m", auto_adjust=True)
df5.index = pd.to_datetime(df5.index)
# Convertir a ET (UTC-4 en verano)
try:
    df5.index = df5.index.tz_convert('America/New_York')
except:
    df5.index = df5.index.tz_localize('UTC').tz_convert('America/New_York')

print(f"  Barras descargadas: {len(df5)}")
print(f"  Rango: {df5.index[0].date()} → {df5.index[-1].date()}")

# También intentar con 15min histórico para ampliar la muestra
print("\nDescargando NQ 15min (max 60 dias)...")
df15 = ticker.history(period="60d", interval="15m", auto_adjust=True)
df15.index = pd.to_datetime(df15.index)
try:
    df15.index = df15.index.tz_convert('America/New_York')
except:
    df15.index = df15.index.tz_localize('UTC').tz_convert('America/New_York')

# ── TAMBIÉN CARGAR HISTÓRICO 15MIN de nuestro CSV (para amplia base) ──
print("\nCargando historico 15min del CSV...")
import csv as csv_mod
from collections import defaultdict as dd2

by_date_15 = dd2(list)
with open('data/research/nq_15m_intraday.csv', encoding='utf-8') as f:
    for r in csv_mod.DictReader(f):
        try:
            raw = datetime.fromisoformat(r['Datetime'].replace('+00:00',''))
            # Ajuste horario  
            d_raw = raw.date()
            off = 4 if (date(2025,3,9)<=d_raw<date(2025,11,2) or date(2026,3,8)<=d_raw) else 5
            et = raw - timedelta(hours=off)
            by_date_15[et.date()].append({
                'et':et,'o':float(r['Open']),'h':float(r['High']),
                'l':float(r['Low']),'c':float(r['Close'])
            })
        except: pass

# ── ORGANIZAR 5MIN POR FECHA ───────────────────────────────────────────
by_date_5 = defaultdict(list)
for ts, row in df5.iterrows():
    d = ts.date()
    by_date_5[d].append({
        'et': ts, 'o': float(row['Open']), 'h': float(row['High']),
        'l': float(row['Low']), 'c': float(row['Close']),
        'v': float(row.get('Volume', 0) or 0)
    })

print(f"  Fechas con datos 5min: {len(by_date_5)}")

# ── ANÁLISIS: MARTES con datos 5min ───────────────────────────────────
records_5m = []

for d in sorted(by_date_5.keys()):
    if d.weekday() != 1: continue  # Solo martes

    bars_5m = sorted([b for b in by_date_5[d]
                      if (b['et'].hour==9 and b['et'].minute>=30) or
                         (10<=b['et'].hour<16)],
                     key=lambda x: x['et'])
    if len(bars_5m) < 15: continue

    # Velas de apertura
    v1 = next((b for b in bars_5m if b['et'].hour==9 and b['et'].minute==30), None)
    v2 = next((b for b in bars_5m if b['et'].hour==9 and b['et'].minute==35), None)
    v3 = next((b for b in bars_5m if b['et'].hour==9 and b['et'].minute==40), None)
    v4 = next((b for b in bars_5m if b['et'].hour==9 and b['et'].minute==45), None)
    v5 = next((b for b in bars_5m if b['et'].hour==9 and b['et'].minute==50), None)
    v6 = next((b for b in bars_5m if b['et'].hour==9 and b['et'].minute==55), None)

    if not v1 or not v2 or not v3: continue

    tue_open  = v1['o']
    tue_close = bars_5m[-1]['c']
    tue_hi    = max(b['h'] for b in bars_5m)
    tue_lo    = min(b['l'] for b in bars_5m)
    tue_chg   = round(tue_close - tue_open, 1)
    tue_bull  = tue_chg > 0
    tue_rng   = round(tue_hi - tue_lo, 1)

    # Monday context from CSV histórico
    mon = d - timedelta(days=1)
    # Try to get Monday data from yfinance 5min or CSV
    mon_data_5 = sorted([b for b in by_date_5.get(mon,[])
                         if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
                        key=lambda x:x['et'])
    mon_data_15 = sorted([b for b in by_date_15.get(mon,[])
                          if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
                         key=lambda x:x['et'])
    mon_data = mon_data_5 or mon_data_15

    mon_lo = min(b['l'] for b in mon_data) if mon_data else tue_open - 100
    mon_hi = max(b['h'] for b in mon_data) if mon_data else tue_open + 100
    mon_chg = round(mon_data[-1]['c'] - mon_data[0]['o'], 1) if mon_data else 0
    if mon_data:
        pct_m = mon_chg / mon_data[0]['o'] * 100
        if   pct_m >= 0.8: mon_type = 'BULL_STRONG'
        elif pct_m >= 0.3: mon_type = 'BULL'
        elif pct_m >=-0.3: mon_type = 'FLAT'
        elif pct_m >=-0.8: mon_type = 'BEAR'
        else:               mon_type = 'BEAR_STRONG'
    else:
        mon_type = 'UNKNOWN'

    # ── Características de cada vela ─────────────────────────────────
    def vchar(v):
        if v is None: return None
        body = abs(v['c'] - v['o'])
        rng  = v['h'] - v['l']
        return {
            'bull': v['c'] > v['o'],
            'body': round(body, 1),
            'rng':  round(rng, 1),
            'strong': body > rng * 0.6 if rng > 0 else False,
            'weak':   body < rng * 0.3 if rng > 0 else True,
            'wick_hi': round(v['h'] - max(v['o'],v['c']), 1),
            'wick_lo': round(min(v['o'],v['c']) - v['l'], 1),
        }

    vc1 = vchar(v1); vc2 = vchar(v2); vc3 = vchar(v3)
    vc4 = vchar(v4); vc5 = vchar(v5); vc6 = vchar(v6)

    # ── Combos ────────────────────────────────────────────────────────
    combo_2 = f"{'V' if vc1['bull'] else 'R'}+{'V' if vc2['bull'] else 'R'}"
    combo_3 = combo_2 + f"+{'V' if vc3['bull'] else 'R'}"
    combo_6 = ''.join('V' if vchar(vx) and vchar(vx)['bull'] else 'R'
                      for vx in [v1,v2,v3,v4,v5,v6] if vx)

    # ¿El día sigue la dirección de v1?
    follow_v1 = (vc1['bull'] == tue_bull)
    follow_v3 = (vc3['bull'] == tue_bull) if vc3 else None

    # ── Setups ────────────────────────────────────────────────────────
    # Setup A: Entrar en cierre de v1 (9:35 ET), SL bajo v1
    entry_a = v1['c'] + (0.25 if vc1['bull'] else -0.25)
    sl_a    = v1['l'] - 5 if vc1['bull'] else v1['h'] + 5
    tp1_a   = entry_a + (50 if vc1['bull'] else -50)
    tp2_a   = entry_a + (80 if vc1['bull'] else -80)
    sl_pts_a= round(abs(entry_a - sl_a), 1)

    remaining_a = [b for b in bars_5m if b['et'] > v1['et']]
    tp1_hit_a=False; tp2_hit_a=False; sl_hit_a=False
    for b in remaining_a:
        if vc1['bull']:
            if not sl_hit_a and not tp1_hit_a and b['l']<=sl_a: sl_hit_a=True; break
            if not tp1_hit_a and b['h']>=tp1_a: tp1_hit_a=True
            if tp1_hit_a and b['h']>=tp2_a: tp2_hit_a=True; break
        else:
            if not sl_hit_a and not tp1_hit_a and b['h']>=sl_a: sl_hit_a=True; break
            if not tp1_hit_a and b['l']<=tp1_a: tp1_hit_a=True
            if tp1_hit_a and b['l']<=tp2_a: tp2_hit_a=True; break

    if tp2_hit_a: pnl_a = 80*3*2
    elif tp1_hit_a: pnl_a = 50*3*2
    elif sl_hit_a:  pnl_a = -sl_pts_a*3*2
    else:           pnl_a = 0

    # Setup B: Esperar v1+v2 mismo color → entrar en cierre v2 (9:40)
    pnl_b=0; tp1_hit_b=False; sl_hit_b=False; tp2_hit_b=False
    sl_pts_b=0
    if v2 and vc2['bull']==vc1['bull']:
        entry_b = v2['c'] + (0.25 if vc1['bull'] else -0.25)
        sl_b    = min(v1['l'],v2['l']) - 5 if vc1['bull'] else max(v1['h'],v2['h']) + 5
        tp1_b   = entry_b + (50 if vc1['bull'] else -50)
        tp2_b   = entry_b + (80 if vc1['bull'] else -80)
        sl_pts_b= round(abs(entry_b - sl_b), 1)
        remaining_b = [b for b in bars_5m if b['et'] > v2['et']]
        for b in remaining_b:
            if vc1['bull']:
                if not sl_hit_b and not tp1_hit_b and b['l']<=sl_b: sl_hit_b=True; break
                if not tp1_hit_b and b['h']>=tp1_b: tp1_hit_b=True
                if tp1_hit_b and b['h']>=tp2_b: tp2_hit_b=True; break
            else:
                if not sl_hit_b and not tp1_hit_b and b['h']>=sl_b: sl_hit_b=True; break
                if not tp1_hit_b and b['l']<=tp1_b: tp1_hit_b=True
                if tp1_hit_b and b['l']<=tp2_b: tp2_hit_b=True; break
        if tp2_hit_b: pnl_b=80*3*2
        elif tp1_hit_b: pnl_b=50*3*2
        elif sl_hit_b:  pnl_b=-sl_pts_b*3*2

    # Setup C: 3 velas mismo color → entrar en cierre v3 (9:45)
    pnl_c=0; tp1_hit_c=False; sl_hit_c=False; tp2_hit_c=False; c_valid=False
    if v3 and vc3['bull']==vc1['bull']==vc2['bull']:
        c_valid=True
        entry_c = v3['c'] + (0.25 if vc1['bull'] else -0.25)
        sl_c    = min(v1['l'],v2['l'],v3['l']) - 5 if vc1['bull'] else max(v1['h'],v2['h'],v3['h']) + 5
        tp1_c   = entry_c + (50 if vc1['bull'] else -50)
        tp2_c   = entry_c + (80 if vc1['bull'] else -80)
        sl_pts_c= round(abs(entry_c - sl_c), 1)
        remaining_c = [b for b in bars_5m if b['et'] > v3['et']]
        for b in remaining_c:
            if vc1['bull']:
                if not sl_hit_c and not tp1_hit_c and b['l']<=sl_c: sl_hit_c=True; break
                if not tp1_hit_c and b['h']>=tp1_c: tp1_hit_c=True
                if tp1_hit_c and b['h']>=tp2_c: tp2_hit_c=True; break
            else:
                if not sl_hit_c and not tp1_hit_c and b['h']>=sl_c: sl_hit_c=True; break
                if not tp1_hit_c and b['l']<=tp1_c: tp1_hit_c=True
                if tp1_hit_c and b['l']<=tp2_c: tp2_hit_c=True; break
        if tp2_hit_c: pnl_c=80*3*2
        elif tp1_hit_c: pnl_c=50*3*2
        elif sl_hit_c:  pnl_c=-sl_pts_c*3*2

    records_5m.append({
        'd': d, 'mon_type': mon_type, 'mon_chg': mon_chg,
        'mon_lo': mon_lo, 'mon_hi': mon_hi,
        'tue_bull': tue_bull, 'tue_chg': tue_chg, 'tue_rng': tue_rng,
        'vc1': vc1, 'vc2': vc2, 'vc3': vc3, 'vc4': vc4,
        'combo_2': combo_2, 'combo_3': combo_3, 'combo_6': combo_6[:6],
        'follow_v1': follow_v1,
        'pnl_a': pnl_a, 'tp1_a': tp1_hit_a, 'tp2_a': tp2_hit_a, 'sl_a': sl_hit_a,
        'pnl_b': pnl_b, 'tp1_b': tp1_hit_b, 'tp2_b': tp2_hit_b, 'sl_b': sl_hit_b,
        'pnl_c': pnl_c, 'tp1_c': tp1_hit_c, 'tp2_c': tp2_hit_c, 'sl_c': sl_hit_c,
        'c_valid': c_valid,
        'bars_5m': bars_5m, 'v1': v1
    })

N = len(records_5m)
print(f"\nMARTES con datos 5min: {N}")
print()

if N < 3:
    print("INSUFICIENTES DATOS 5MIN. Ampliando con datos 15min historicos...")
    # Usar CSV histórico simulando 5min (usamos los 15min como 1a señal)
    records_5m_old = []
    by_date_15_sorted = sorted(by_date_15.keys())
    for d in by_date_15_sorted:
        if d.weekday() != 1: continue
        bars = sorted([b for b in by_date_15[d]
                       if (b['et'].hour==9 and b['et'].minute>=30) or (10<=b['et'].hour<16)],
                      key=lambda x:x['et'])
        if len(bars)<8: continue
        v1_ = next((b for b in bars if b['et'].hour==9 and b['et'].minute==30), None)
        v2_ = next((b for b in bars if b['et'].hour==9 and b['et'].minute==45), None)
        v3_ = next((b for b in bars if b['et'].hour==10 and b['et'].minute==0), None)
        if not v1_ or not v2_: continue
        tue_chg_ = round(bars[-1]['c']-v1_['o'],1)
        vc1_={'bull':v1_['c']>v1_['o'],'body':round(abs(v1_['c']-v1_['o']),1),'rng':round(v1_['h']-v1_['l'],1)}
        vc2_={'bull':v2_['c']>v2_['o'],'body':round(abs(v2_['c']-v2_['o']),1),'rng':round(v2_['h']-v2_['l'],1)}
        vc3_={'bull':v3_['c']>v3_['o'],'body':round(abs(v3_['c']-v3_['o']),1),'rng':round(v3_['h']-v3_['l'],1)} if v3_ else None
        mon_=d-timedelta(days=1)
        mon_bars=sorted([b for b in by_date_15.get(mon_,[])
                        if (b['et'].hour==9 and b['et'].minute>=30)or(10<=b['et'].hour<16)],key=lambda x:x['et'])
        mon_chg_=round(mon_bars[-1]['c']-mon_bars[0]['o'],1) if mon_bars else 0
        pct_m=mon_chg_/mon_bars[0]['o']*100 if mon_bars else 0
        mon_t=('BULL_STRONG' if pct_m>=0.8 else 'BULL' if pct_m>=0.3 else
               'FLAT' if pct_m>=-0.3 else 'BEAR' if pct_m>=-0.8 else 'BEAR_STRONG')
        combo_2_=f"{'V' if vc1_['bull'] else 'R'}+{'V' if vc2_['bull'] else 'R'}"
        combo_3_=combo_2_+f"+{'V' if vc3_ and vc3_['bull'] else 'R'}"
        follow_v1_=(vc1_['bull']==(tue_chg_>0))
        records_5m_old.append({
            'd':d,'mon_type':mon_t,'mon_chg':mon_chg_,'tue_bull':tue_chg_>0,
            'tue_chg':tue_chg_,'vc1':vc1_,'vc2':vc2_,'vc3':vc3_,
            'combo_2':combo_2_,'combo_3':combo_3_,'follow_v1':follow_v1_,
            'pnl_a':0,'tp1_a':False,'sl_a':False,'pnl_b':0,'tp1_b':False,'sl_b':False,
            'pnl_c':0,'tp1_c':False,'sl_c':False,'c_valid':False
        })
    records_5m = records_5m_old
    N = len(records_5m)
    print(f"  Usando 15min como proxy: {N} martes")
    DATA_NOTE = "(15min simulando señal)"
else:
    DATA_NOTE = "(5min reales)"

print(f"\n{'='*65}")
print(f"RESULTADOS 5MIN {DATA_NOTE}:")
print(f"{'='*65}")

# A. V1 sola
v1_g=[r for r in records_5m if r['vc1']['bull']]
v1_r=[r for r in records_5m if not r['vc1']['bull']]
print(f"\nA. VELA 9:30 (5min) → ¿Sigue el día?")
for grp,lbl in[(v1_g,'V1 VERDE'),(v1_r,'V1 ROJA')]:
    if not grp: continue
    f=sum(1 for r in grp if r['follow_v1'])
    avg_b=sum(r['vc1']['body'] for r in grp)/len(grp)
    print(f"  {lbl} n={len(grp)}: -> sigue {f}/{len(grp)} = {f/len(grp)*100:.0f}%  body_avg={avg_b:.0f}pts")

print(f"\nB. COMBOS 2 VELAS (9:30+9:35):")
print(f"  {'Combo':<12} {'n':>4} {'Dia Sube%':>10} {'Avg Pts':>8}")
for combo in['V+V','V+R','R+V','R+R']:
    grp=[r for r in records_5m if r['combo_2']==combo]
    if not grp: continue
    n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    print(f"  {combo:<12} {n_:>4} {up_/n_*100:>9.0f}% {avg_:>+8.0f}")

print(f"\nC. COMBOS 3 VELAS (9:30+9:35+9:40):")
print(f"  {'Combo':<14} {'n':>4} {'Dia Sube%':>10} {'Avg Pts':>8}")
for combo in['V+V+V','V+V+R','V+R+V','V+R+R','R+V+V','R+V+R','R+R+V','R+R+R']:
    grp=[r for r in records_5m if r['combo_3']==combo]
    if not grp: continue
    n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    print(f"  {combo:<14} {n_:>4} {up_/n_*100:>9.0f}% {avg_:>+8.0f}")

# Setups (solo si datos 5min reales)
if any(r.get('sl_a') or r.get('tp1_a') for r in records_5m):
    print(f"\nD. P&L SETUPS (3MNQ, TP1=+50, TP2=+80):")
    for sname,tk,sk,pk in[('A: Seguir v1 (9:35)','tp1_a','sl_a','pnl_a'),
                           ('B: v1+v2 mismo color (9:40)','tp1_b','sl_b','pnl_b'),
                           ('C: 3 velas seguidas (9:45)','tp1_c','sl_c','pnl_c')]:
        grp_=records_5m if sname[0]!='C' else [r for r in records_5m if r['c_valid']]
        h_=sum(1 for r in grp_ if r[tk]); l_=sum(1 for r in grp_ if r[sk])
        p_=sum(r[pk] for r in grp_); n__=len(grp_)
        print(f"  {sname}: WR={h_/max(1,h_+l_)*100:.0f}% P&L={'+$' if p_>=0 else '-$'}{abs(p_):.0f}")

# ── FIGURA ────────────────────────────────────────────────────────────
fig=plt.figure(figsize=(26,16),facecolor=BG)
fig.suptitle(f"ESTUDIO APERTURA 5MIN — MARTES | {N} casos | Sesión NY 9:30-16:00 ET {DATA_NOTE}",
             color=GOLD,fontsize=13,fontweight='bold',y=0.99)
gs=gridspec.GridSpec(2,3,figure=fig,hspace=0.42,wspace=0.28,
                     left=0.04,right=0.97,top=0.94,bottom=0.06)

# 1. V1 dirección → día
ax1=fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
cats=['V1\nVERDE\n9:30','V1\nROJA\n9:30']
wr1=[sum(1 for r in v1_g if r['follow_v1'])/max(1,len(v1_g))*100,
     sum(1 for r in v1_r if r['follow_v1'])/max(1,len(v1_r))*100]
n1_=[len(v1_g),len(v1_r)]
bars1=ax1.bar([0,1],wr1,color=[GRN,RED],alpha=0.85,width=0.55)
ax1.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,w,n_ in zip(bars1,wr1,n1_):
    ax1.text(b.get_x()+b.get_width()/2,w+2,f'{w:.0f}%',color='white',ha='center',fontsize=16,fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2,10,f'n={n_}',color=SOFT,ha='center',fontsize=10)
ax1.set_xticks([0,1]); ax1.set_xticklabels(cats,fontsize=10,color=SOFT)
ax1.set_ylim(0,100); ax1.set_ylabel('% Día sigue V1',color=SOFT)
ax1.set_title('1a Vela 5min (9:30-9:35)\n¿El día sigue esa dirección?',color=GOLD,fontsize=11,fontweight='bold')
ax1.tick_params(colors=SOFT)
[ax1.spines[s].set_visible(False) for s in ['top','right']]

# 2. Combos 2 velas
ax2=fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
c2_data=[]
for combo in['V+V','R+R','V+R','R+V']:
    grp=[r for r in records_5m if r['combo_2']==combo]
    if not grp: continue
    n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    c2_data.append((combo,up_/n_*100,n_,avg_))
x2c=np.arange(len(c2_data))
clrs_c2=[GRN if d[1]>=60 else (RED if d[1]<40 else GOLD) for d in c2_data]
bars2=ax2.bar(x2c,[d[1] for d in c2_data],color=clrs_c2,alpha=0.85,width=0.6)
ax2.axhline(50,color='white',lw=1.5,ls='--',alpha=0.5)
for b,d in zip(bars2,c2_data):
    ax2.text(b.get_x()+b.get_width()/2,d[1]+2,f'{d[1]:.0f}%',color='white',ha='center',fontsize=13,fontweight='bold')
    ax2.text(b.get_x()+b.get_width()/2,8,f'n={d[2]}',color=SOFT,ha='center',fontsize=9.5)
    ax2.text(b.get_x()+b.get_width()/2,d[1]+11,f'{d[3]:+.0f}pts',color=GRN if d[3]>0 else RED,ha='center',fontsize=9)
ax2.set_xticks(x2c); ax2.set_xticklabels([d[0] for d in c2_data],fontsize=11,color=SOFT)
ax2.set_ylim(0,100); ax2.set_ylabel('% Día Sube',color=SOFT)
ax2.set_title('COMBO 2 velas (9:30+9:35)\nV=verde R=roja → WR día',color=GOLD,fontsize=11,fontweight='bold')
ax2.tick_params(colors=SOFT)
[ax2.spines[s].set_visible(False) for s in ['top','right']]

# 3. Combos 3 velas — solo los más frecuentes
ax3=fig.add_subplot(gs[0,2]); ax3.set_facecolor(PANEL2)
c3_data=[]
for combo in['V+V+V','R+R+R','V+V+R','R+R+V','V+R+V','R+V+R','R+V+V','V+R+R']:
    grp=[r for r in records_5m if r['combo_3']==combo]
    if len(grp)<2: continue
    n_=len(grp); up_=sum(1 for r in grp if r['tue_bull'])
    avg_=sum(r['tue_chg'] for r in grp)/n_
    c3_data.append((combo,up_/n_*100,n_,avg_))
c3_data.sort(key=lambda x:-x[2])  # ordenar por frecuencia
x3c=np.arange(len(c3_data))
clrs_c3=[GRN if d[1]>=60 else (RED if d[1]<40 else GOLD) for d in c3_data]
bars3=ax3.barh(x3c,[d[1] for d in c3_data],color=clrs_c3,alpha=0.85)
ax3.axvline(50,color='white',lw=1.2,ls='--',alpha=0.5)
for b,d in zip(bars3,c3_data):
    ax3.text(d[1]+1.5,b.get_y()+b.get_height()/2,
             f'{d[1]:.0f}%  n={d[2]}  avg{d[3]:+.0f}',
             va='center',fontsize=9,color=WHITE,fontweight='bold')
ax3.set_yticks(x3c); ax3.set_yticklabels([d[0] for d in c3_data],fontsize=10,color=SOFT)
ax3.set_xlim(0,120); ax3.set_xlabel('% Día Sube',color=SOFT)
ax3.set_title('COMBO 3 velas (9:30-9:45)\npatrones predictivos',color=GOLD,fontsize=11,fontweight='bold')
ax3.tick_params(colors=SOFT)
[ax3.spines[s].set_visible(False) for s in ['top','right']]

# 4. Tamaño de la v1 (body)
ax4=fig.add_subplot(gs[1,0]); ax4.set_facecolor(PANEL2)
v1_bodies=[r['vc1']['body'] for r in records_5m if r['vc1']]
v1_ranges=[r['vc1']['rng']  for r in records_5m if r['vc1']]
bins=[0,5,10,15,20,30,50,200]
lb=['0-5','5-10','10-15','15-20','20-30','30-50','50+']
hb,_=np.histogram(v1_bodies,bins=bins)
hr,_=np.histogram(v1_ranges,bins=bins)
xb=np.arange(len(lb))
ax4.bar(xb-0.2,hb,0.35,color=GOLD,alpha=0.85,label='Body (relleno)')
ax4.bar(xb+0.2,hr,0.35,color=SOFT,alpha=0.6,label='Rango (mecha-mecha)')
ax4.set_xticks(xb); ax4.set_xticklabels(lb,fontsize=9,color=SOFT)
ax4.set_ylabel('N martes',color=SOFT)
ax4.set_title(f'Tamaño Vela 9:30 (5min)\nbody avg={sum(v1_bodies)/max(1,len(v1_bodies)):.0f}pts',
              color=GOLD,fontsize=11,fontweight='bold')
for i,(b_,r_) in enumerate(zip(hb,hr)):
    if b_>0: ax4.text(i-0.2,b_+0.3,str(b_),ha='center',fontsize=8.5,color=GOLD)
    if r_>0: ax4.text(i+0.2,r_+0.3,str(r_),ha='center',fontsize=8.5,color=SOFT)
ax4.legend(fontsize=9,facecolor=BG,labelcolor=SOFT)
ax4.tick_params(colors=SOFT)
[ax4.spines[s].set_visible(False) for s in ['top','right']]

# 5. P&L setups (solo si hay datos reales)
ax5=fig.add_subplot(gs[1,1]); ax5.set_facecolor(PANEL2)
setup_pnls=[sum(r['pnl_a'] for r in records_5m),
             sum(r['pnl_b'] for r in records_5m),
             sum(r['pnl_c'] for r in records_5m if r['c_valid'])]
setup_wrs_=[sum(1 for r in records_5m if r['tp1_a'])/max(1,sum(1 for r in records_5m if r['tp1_a'] or r['sl_a']))*100,
             sum(1 for r in records_5m if r['tp1_b'])/max(1,sum(1 for r in records_5m if r['tp1_b'] or r['sl_b']))*100,
             sum(1 for r in records_5m if r['c_valid'] and r['tp1_c'])/max(1,sum(1 for r in records_5m if r['c_valid'] and (r['tp1_c'] or r['sl_c'])))*100]
slbl=['A: Seguir\nV1 cierre','B: V1+V2\ncomo color','C: 3 velas\ncomo color']
bars5=ax5.bar(np.arange(3),setup_pnls,color=[GRN if p>=0 else RED for p in setup_pnls],alpha=0.85,width=0.55)
ax5.axhline(0,color='white',lw=1,alpha=0.4)
for b,p,w in zip(bars5,setup_pnls,setup_wrs_):
    yoff=max(abs(p)*0.05,300)
    ax5.text(b.get_x()+b.get_width()/2,p+(yoff if p>=0 else -yoff*2.5),
             f'{"+$" if p>=0 else "-$"}{abs(p):.0f}\nWR={w:.0f}%',
             ha='center',fontsize=10,color=WHITE,fontweight='bold')
ax5.set_xticks(np.arange(3)); ax5.set_xticklabels(slbl,fontsize=9.5,color=SOFT)
ax5.set_ylabel('P&L Total (3MNQ)',color=SOFT)
ax5.set_title('P&L Setups 5min\n(TP1=+50pts, TP2=+80pts)',color=GOLD,fontsize=11,fontweight='bold')
ax5.tick_params(colors=SOFT); [ax5.spines[s].set_visible(False) for s in ['top','right']]

# 6. Card HOY
ax6=fig.add_subplot(gs[1,2]); ax6.set_facecolor('#07070f')
ax6.set_xlim(0,10); ax6.set_ylim(0,18); ax6.axis('off')
ax6.add_patch(patches.FancyBboxPatch((0.2,16.8),9.6,0.9,
    boxstyle='round,pad=0.1',facecolor='#0a1a0a',edgecolor=GRN,linewidth=2))
ax6.text(5,17.25,'HOY: LEE LAS PRIMERAS 3 VELAS DE 5MIN',
         ha='center',va='center',fontsize=10,fontweight='bold',color=GRN)

# Buscar el mejor combo
best_bull_c3=max(c3_data,key=lambda x:x[1]) if c3_data else (None,0,0,0)
best_bear_c3=min(c3_data,key=lambda x:x[1]) if c3_data else (None,100,0,0)
best_bull_c2=max(c2_data,key=lambda x:x[1]) if c2_data else (None,0,0,0)
best_bear_c2=min(c2_data,key=lambda x:x[1]) if c2_data else (None,100,0,0)

lines=[
    (GOLD,'bold','── SEÑAL 1 VELA (9:30-9:35) ──',''),
    (GRN,'bold','Verde → día sube:',f'{wr1[0]:.0f}%'),
    (RED,'bold','Roja  → día baja:',f'{100-wr1[1]:.0f}%'),
    ('','','',''),
    (GOLD,'bold','── SEÑAL 2 VELAS (9:30+9:35) ──',''),
    (GRN,'bold',f'Mejor alcista {best_bull_c2[0]}:',f'{best_bull_c2[1]:.0f}% WR  n={best_bull_c2[2]}'),
    (RED,'bold',f'Mejor bajista {best_bear_c2[0]}:',f'{100-best_bear_c2[1]:.0f}% WR baja  n={best_bear_c2[2]}'),
    ('','','',''),
    (GOLD,'bold','── SEÑAL 3 VELAS (9:45) ──',''),
    (GRN,'bold',f'Mejor alcista {best_bull_c3[0]}:',f'{best_bull_c3[1]:.0f}% WR  n={best_bull_c3[2]}'),
    (RED,'bold',f'Mejor bajista {best_bear_c3[0]}:',f'{100-best_bear_c3[1]:.0f}% WR baja  n={best_bear_c3[2]}'),
    ('','','',''),
    (GOLD,'bold','── REGLAS OPERATIVAS ──',''),
    (GRN,'bold','Entrada: cierre de 2a-3a vela','SL bajo/alto v1'),
    (BLU,'bold','TP1: +50pts  TP2: +80pts','3MNQ = +$300 / +$480'),
    (RED,'bold','Si velas mixtas (V+R o R+V):','NO entrar, esperar'),
]
for i,(c,w,k,v) in enumerate(lines):
    y=16.1-i*0.9
    if c:
        ax6.text(0.4,y,k,fontsize=8.8,color=c,fontweight=w,va='center')
        if v: ax6.text(5.3,y,v,fontsize=8.8,color=c,fontweight='bold',va='center')

out='martes_5min_apertura.png'
plt.savefig(out,dpi=125,bbox_inches='tight',facecolor=BG)
plt.close()
print(f'\nGrafica guardada: {out}')
