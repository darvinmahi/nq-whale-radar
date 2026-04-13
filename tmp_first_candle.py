"""
first_candle_backtest.py
Prueba: Si la primera vela de NY (9:30-9:45) cierra VERDE → ¿sube el día?
                                                   cierra ROJA  → ¿baja el día?
Mide: WR global, por día de semana, con/sin filtro COT divergencia
"""
import csv, math
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np

# ── FUNCIÓN OFFSET ────────────────────────────────────────────────────
def utc_offset(d):
    dst25_s=date(2025,3,9); dst25_e=date(2025,11,2); dst26_s=date(2026,3,8)
    if dst25_s<=d<dst25_e or dst26_s<=d: return 4
    return 5

# ── CARGAR DATOS ──────────────────────────────────────────────────────
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
            et  = raw - timedelta(hours=utc_offset(raw.date()))
            if et.weekday()>=5: continue
            by_date[et.date()].append({
                "et":et,"o":float(r["Open"]),"h":float(r["High"]),
                "l":float(r["Low"]),"c":float(r["Close"]),
                "v":float(r.get("Volume",0) or 0)
            })
        except: pass

# ── CARGAR COT (para filtro) ──────────────────────────────────────────
cot_by_week = {}  # isoweek → signal
cot_rows = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
            al  = int(r.get("Asset_Mgr_Positions_Long_All",0) or 0)
            as_ = int(r.get("Asset_Mgr_Positions_Short_All",0) or 0)
            ll  = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
            ls  = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
            cot_rows.append({"date":d,"am_net":al-as_,"lev_net":ll-ls})
        except: pass
cot_rows.sort(key=lambda x: x["date"])
for i,w in enumerate(cot_rows):
    if i>0: w["am_delta"]=w["am_net"]-cot_rows[i-1]["am_net"]
    else:   w["am_delta"]=0
    win=[x["lev_net"] for x in cot_rows[max(0,i-51):i+1]]
    mn,mx=min(win),max(win)
    w["lev_pct"]=round((w["lev_net"]-mn)/(mx-mn)*100,1) if mx!=mn else 50
    ad=w["am_delta"]; lp=w["lev_pct"]
    if   ad<-10000 and lp>60: sig="BEAR_STRONG"
    elif ad<-5000  and lp>60: sig="BEAR"
    elif ad>10000  and lp<40: sig="BULL_STRONG"
    elif ad>5000   and lp<40: sig="BULL"
    else:                      sig="NEUTRAL"
    w["sig"]=sig
    # Semanas de trading que aplica (la siguiente semana al viernes de pub)
    pub_fri = w["date"]+timedelta(days=4)
    for shift in range(7):
        td = pub_fri+timedelta(days=shift)
        if td.weekday()==0:
            for dd in range(5):
                cot_by_week[td+timedelta(days=dd)] = sig
            break

# ── ANALIZAR CADA DÍA ─────────────────────────────────────────────────
DOW = {0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes"}
results = []

for d, bars in by_date.items():
    bars = sorted(bars, key=lambda x: x["et"])
    # Primera vela NY: 9:30
    open930 = [b for b in bars if b["et"].hour==9 and b["et"].minute==30]
    # Resto del día hasta cierre (9:45 en adelante hasta 16:00)
    rest = [b for b in bars if
            (b["et"].hour==9 and b["et"].minute>=45) or
            (10<=b["et"].hour<16)]
    close_bars = [b for b in rest if b["et"].hour==15 and b["et"].minute>=45]

    if not open930 or not rest or not close_bars: continue

    fc = open930[0]  # first candle
    fc_bull  = fc["c"] > fc["o"]   # verde si cierra arriba de apertura
    fc_pts   = round(fc["c"] - fc["o"], 1)  # ¼ +/- puntos primera vela
    fc_range = round(fc["h"] - fc["l"], 1)

    # Cierre del día
    day_close   = close_bars[-1]["c"]
    day_open930 = fc["o"]           # apertura del día = open de primera vela
    day_pts     = round(day_close - day_open930, 1)

    # ¿El día fue en la dirección de la primera vela?
    correct = (fc_bull and day_pts > 0) or (not fc_bull and day_pts < 0)

    # COT contexto
    cot_sig = cot_by_week.get(d, "UNKNOWN")

    # Max favorable excursion desde cierre 9:30
    rest_highs = [b["h"] for b in rest]
    rest_lows  = [b["l"] for b in rest]
    max_up   = round(max(rest_highs) - fc["c"], 1) if rest_highs else 0
    max_down = round(fc["c"] - min(rest_lows), 1)  if rest_lows  else 0

    # ¿Cuánto subió antes de bajar (si primera vela bajista)?
    if fc_bull:
        continuation = max_up
        adversal     = max_down
    else:
        continuation = max_down
        adversal     = max_up

    results.append({
        "date":d,"dow":d.weekday(),"dow_name":DOW[d.weekday()],
        "fc_bull":fc_bull,"fc_pts":fc_pts,"fc_range":fc_range,
        "day_pts":day_pts,"correct":correct,"cot":cot_sig,
        "continuation":continuation,"adversal":adversal
    })

results.sort(key=lambda x: x["date"])
print(f"Total días analizados: {len(results)}")
print(f"Fecha más antigua: {results[0]['date']}")
print(f"Fecha más reciente: {results[-1]['date']}")

# ── ESTADÍSTICAS GLOBALES ─────────────────────────────────────────────
N = len(results)
wins = sum(1 for r in results if r["correct"])
bull_days = [r for r in results if r["fc_bull"]]
bear_days = [r for r in results if not r["fc_bull"]]
bull_wins = sum(1 for r in bull_days if r["correct"])
bear_wins = sum(1 for r in bear_days if r["correct"])

avg_cont_bull = sum(r["continuation"] for r in bull_days)/len(bull_days) if bull_days else 0
avg_cont_bear = sum(r["continuation"] for r in bear_days)/len(bear_days) if bear_days else 0
avg_adv_bull  = sum(r["adversal"]     for r in bull_days)/len(bull_days) if bull_days else 0
avg_adv_bear  = sum(r["adversal"]     for r in bear_days)/len(bear_days) if bear_days else 0

print(f"\n{'='*70}")
print(f"  PRUEBA: PRIMERA VELA 9:30 → DIRECCIÓN DEL DÍA | NQ Futures")
print(f"{'='*70}")
print(f"\n  GLOBAL: {wins}/{N} = {wins/N*100:.1f}% WR")
print(f"  Primera vela VERDE (bull): {bull_wins}/{len(bull_days)} = {bull_wins/len(bull_days)*100:.1f}%")
print(f"  Primera vela ROJA  (bear): {bear_wins}/{len(bear_days)} = {bear_wins/len(bear_days)*100:.1f}%")
print(f"\n  Avg MFE (extensión favorable):")
print(f"    Vela verde → Día sube avg: {avg_cont_bull:.0f}pts | adversal (drawdown): {avg_adv_bull:.0f}pts")
print(f"    Vela roja  → Día baja avg: {avg_cont_bear:.0f}pts | adversal (rebound): {avg_adv_bear:.0f}pts")

# ── POR DÍA DE SEMANA ─────────────────────────────────────────────────
print(f"\n  POR DÍA DE SEMANA:")
for dow_n, dow_i in [("Lunes",0),("Martes",1),("Miercoles",2),("Jueves",3),("Viernes",4)]:
    day_r = [r for r in results if r["dow"]==dow_i]
    if not day_r: continue
    dw = sum(1 for r in day_r if r["correct"])
    print(f"    {dow_n:<10}: {dw}/{len(day_r)} = {dw/len(day_r)*100:.0f}%")

# ── CON FILTRO COT DIVERGENCIA ────────────────────────────────────────
print(f"\n  CON FILTRO COT (solo días en semana de divergencia):")
for sig in ["BEAR_STRONG","BEAR","BULL_STRONG","BULL"]:
    sig_r = [r for r in results if r["cot"]==sig]
    if not sig_r: continue
    sw = sum(1 for r in sig_r if r["correct"])
    # En BEAR, "correct" ya significa que bajó si primera vela bajista
    bear_align = [r for r in sig_r if not r["fc_bull"]] if "BEAR" in sig else []
    bull_align = [r for r in sig_r if r["fc_bull"]]     if "BULL" in sig else []
    print(f"    COT {sig:<12}: {sw}/{len(sig_r)} = {sw/len(sig_r)*100:.0f}% WR total |",
          end=" ")
    if "BEAR" in sig and bear_align:
        ba = sum(1 for r in bear_align if r["correct"])
        print(f"Vela roja + COT BEAR: {ba}/{len(bear_align)}={ba/len(bear_align)*100:.0f}%",end="")
    elif "BULL" in sig and bull_align:
        ba = sum(1 for r in bull_align if r["correct"])
        print(f"Vela verde + COT BULL: {ba}/{len(bull_align)}={ba/len(bull_align)*100:.0f}%",end="")
    print()

# ── MÉTRICAS ADICIONALES ──────────────────────────────────────────────
# Rango medio de la primera vela
avg_fc_range = sum(r["fc_range"] for r in results)/N
small_fc = [r for r in results if r["fc_range"]<30]
big_fc   = [r for r in results if r["fc_range"]>=30]
sw_s = sum(1 for r in small_fc if r["correct"])
sw_b = sum(1 for r in big_fc  if r["correct"])

print(f"\n  POR TAMAÑO DE PRIMERA VELA (rango H-L):")
print(f"    Rango medio primera vela: {avg_fc_range:.0f}pts")
print(f"    Vela PEQUEÑA (<30pts):  {sw_s}/{len(small_fc)} = {sw_s/len(small_fc)*100:.0f}% WR")
print(f"    Vela GRANDE (>=30pts):  {sw_b}/{len(big_fc)}  = {sw_b/len(big_fc)*100:.0f}% WR")

# Días donde la primera vela es > 20pts moviéndose en una dirección
strong_fc = [r for r in results if abs(r["fc_pts"])>=15]
sw_str = sum(1 for r in strong_fc if r["correct"])
print(f"\n  PRIMERA VELA FUERTE (cierre >15pts de apertura):")
print(f"    {sw_str}/{len(strong_fc)} = {sw_str/len(strong_fc)*100:.0f}% WR → {'EDGE REAL' if sw_str/len(strong_fc)>0.60 else 'Sin edge suficiente'}")

# ── GRÁFICA ───────────────────────────────────────────────────────────
BG='#0d0d1a'; PANEL='#131325'; GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'; BLU='#60a5fa'

fig, axes = plt.subplots(2, 3, figsize=(21, 12), facecolor=BG)
fig.suptitle("PRIMERA VELA 9:30 → ¿DIRECCIÓN DEL DÍA? | NQ Futures Backtest",
             color=GOLD, fontsize=15, fontweight='bold', y=0.98)

def pct(n,d): return n/d*100 if d else 0

# 1. WR Global por color de vela
ax = axes[0,0]; ax.set_facecolor(PANEL)
cats = ['Vela VERDE\n(LONG)', 'Vela ROJA\n(SHORT)', 'GLOBAL']
wrs  = [pct(bull_wins,len(bull_days)), pct(bear_wins,len(bear_days)), pct(wins,N)]
clrs = [GRN, RED, GOLD]
bars_ = ax.bar(cats, wrs, color=clrs, alpha=0.8, width=0.5)
ax.axhline(50, color='#475569', lw=1, ls='--', alpha=0.6)
ax.axhline(60, color=GOLD,      lw=1, ls='--', alpha=0.4)
for b,w in zip(bars_,wrs):
    ax.text(b.get_x()+b.get_width()/2, w+0.5, f'{w:.1f}%',
            color='white', ha='center', fontweight='bold', fontsize=12)
ax.set_ylim(0,100); ax.set_ylabel('Win Rate %', color='#64748b')
ax.set_title('WR Global por Color de Vela', color=GOLD, fontsize=11)
ax.tick_params(colors='#64748b'); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')

# 2. WR por día de semana
ax = axes[0,1]; ax.set_facecolor(PANEL)
dows=['Lun','Mar','Mie','Jue','Vie']
dow_wrs=[]; dow_ns=[]
for i in range(5):
    dr=[r for r in results if r["dow"]==i]
    dw=sum(1 for r in dr if r["correct"])
    dow_wrs.append(pct(dw,len(dr)))
    dow_ns.append(len(dr))
clrs_d=[GRN if w>=55 else (RED if w<50 else GOLD) for w in dow_wrs]
b_=ax.bar(dows,dow_wrs,color=clrs_d,alpha=0.8,width=0.6)
ax.axhline(50,color='#475569',lw=1,ls='--',alpha=0.6)
ax.axhline(60,color=GOLD,lw=1,ls='--',alpha=0.4)
for bv,w,n in zip(b_,dow_wrs,dow_ns):
    ax.text(bv.get_x()+bv.get_width()/2,w+0.5,f'{w:.0f}%\n(n={n})',
            color='white',ha='center',fontsize=9,fontweight='bold')
ax.set_ylim(0,100); ax.set_ylabel('Win Rate %',color='#64748b')
ax.set_title('WR por Día de Semana',color=GOLD,fontsize=11)
ax.tick_params(colors='#64748b'); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')

# 3. WR por tamaño de primera vela (bins)
ax = axes[0,2]; ax.set_facecolor(PANEL)
bins=[0,10,20,30,50,100,999]
labels=['0-10','10-20','20-30','30-50','50-100','>100']
bin_wrs=[]; bin_ns=[]
for i in range(len(labels)):
    lo=bins[i]; hi=bins[i+1]
    br=[r for r in results if lo<=r["fc_range"]<hi]
    bw=sum(1 for r in br if r["correct"])
    bin_wrs.append(pct(bw,len(br)))
    bin_ns.append(len(br))
clrs_b=[GRN if w>=55 else (RED if w<50 else GOLD) for w in bin_wrs]
b2=ax.bar(labels,bin_wrs,color=clrs_b,alpha=0.8,width=0.6)
ax.axhline(50,color='#475569',lw=1,ls='--',alpha=0.6)
for bv,w,n in zip(b2,bin_wrs,bin_ns):
    if n>0:
        ax.text(bv.get_x()+bv.get_width()/2,w+0.5,f'{w:.0f}%\nn={n}',
                color='white',ha='center',fontsize=8.5,fontweight='bold')
ax.set_ylim(0,100); ax.set_xlabel('Rango Primera Vela (pts)',color='#64748b')
ax.set_ylabel('Win Rate %',color='#64748b')
ax.set_title('WR por Tamaño de 1ª Vela',color=GOLD,fontsize=11)
ax.tick_params(colors='#64748b'); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')

# 4. Distribución pts del día (bull vs bear first candle)
ax = axes[1,0]; ax.set_facecolor(PANEL)
bull_day_pts=[r["day_pts"] for r in bull_days]
bear_day_pts=[r["day_pts"] for r in bear_days]
bins_hist=np.linspace(-600,600,40)
ax.hist(bull_day_pts,bins=bins_hist,alpha=0.5,color=GRN,label=f'V.Verde ({len(bull_days)}d)')
ax.hist(bear_day_pts,bins=bins_hist,alpha=0.5,color=RED, label=f'V.Roja ({len(bear_days)}d)')
ax.axvline(0,color='white',lw=1.2,alpha=0.7)
ax.axvline(np.mean(bull_day_pts),color=GRN,lw=1.5,ls='--',alpha=0.8,
           label=f'Avg bull {np.mean(bull_day_pts):+.0f}pt')
ax.axvline(np.mean(bear_day_pts),color=RED,lw=1.5,ls='--',alpha=0.8,
           label=f'Avg bear {np.mean(bear_day_pts):+.0f}pt')
ax.legend(fontsize=8,facecolor=BG,labelcolor='#94a3b8')
ax.set_xlabel('Pts NQ al cierre del día',color='#64748b')
ax.set_ylabel('Días',color='#64748b')
ax.set_title('Distribución P&L Días',color=GOLD,fontsize=11)
ax.tick_params(colors='#64748b'); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')

# 5. WR con filtro COT
ax=axes[1,1]; ax.set_facecolor(PANEL)
cot_sigs=['NEUTRAL','BEAR','BEAR_STRONG','BULL','BULL_STRONG']
cot_wrs=[]; cot_ns=[]; cot_clrs=[]
for sig in cot_sigs:
    sr=[r for r in results if r["cot"]==sig]
    sw=sum(1 for r in sr if r["correct"])
    cot_wrs.append(pct(sw,len(sr)))
    cot_ns.append(len(sr))
    cot_clrs.append(RED if "BEAR" in sig else (GRN if "BULL" in sig else '#64748b'))
b3=ax.bar(cot_sigs,cot_wrs,color=cot_clrs,alpha=0.8,width=0.6)
ax.axhline(50,color='#475569',lw=1,ls='--',alpha=0.6)
ax.axhline(60,color=GOLD,lw=1,ls='--',alpha=0.4)
for bv,w,n in zip(b3,cot_wrs,cot_ns):
    if n>0:
        ax.text(bv.get_x()+bv.get_width()/2,w+0.5,f'{w:.0f}%\nn={n}',
                color='white',ha='center',fontsize=8.5,fontweight='bold')
ax.set_ylim(0,100); ax.set_ylabel('Win Rate %',color='#64748b')
ax.set_title('WR por Señal COT semanal',color=GOLD,fontsize=11)
ax.tick_params(colors='#64748b',axis='x',rotation=15)
[ax.spines[s].set_visible(False) for s in ['top','right']]
ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')

# 6. Combo: V.Roja + COT BEAR vs V.Verde + COT BULL
ax=axes[1,2]; ax.set_facecolor(PANEL)
combos=[
    ("V.Roja\nsin COT", [r for r in bear_days if r["cot"]=="NEUTRAL"]),
    ("V.Roja\n+COT BEAR", [r for r in bear_days if "BEAR" in r["cot"]]),
    ("V.Verde\nsin COT", [r for r in bull_days if r["cot"]=="NEUTRAL"]),
    ("V.Verde\n+COT BULL", [r for r in bull_days if "BULL" in r["cot"]]),
]
c_labels=[c[0] for c in combos]
c_wrs=[pct(sum(1 for r in c[1] if r["correct"]),len(c[1])) for c in combos]
c_ns=[len(c[1]) for c in combos]
c_clrs=[RED,RED,GRN,GRN]
c_alpha=[0.4,0.9,0.4,0.9]
b4=ax.bar(c_labels,c_wrs,color=c_clrs,alpha=0.8,width=0.5)
ax.axhline(50,color='#475569',lw=1,ls='--',alpha=0.6)
ax.axhline(60,color=GOLD,lw=1,ls='--',alpha=0.4,label='60% threshold')
for bv,w,n in zip(b4,c_wrs,c_ns):
    if n>0:
        ax.text(bv.get_x()+bv.get_width()/2,w+0.5,f'{w:.0f}%\nn={n}',
                color='white',ha='center',fontsize=9,fontweight='bold')
ax.set_ylim(0,100); ax.set_ylabel('Win Rate %',color='#64748b')
ax.set_title('COMBO: V.Apertura + COT',color=GOLD,fontsize=11)
ax.tick_params(colors='#64748b'); [ax.spines[s].set_visible(False) for s in ['top','right']]
ax.spines['left'].set_color('#2d2d4e'); ax.spines['bottom'].set_color('#2d2d4e')
ax.legend(fontsize=8,facecolor=BG,labelcolor='#94a3b8')

plt.tight_layout(rect=[0,0,1,0.96])
out="first_candle_analysis.png"
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f"\nGrafica: {out}")

# ── RESUMEN EJECUTIVO ─────────────────────────────────────────────────
print(f"\n{'='*70}")
print(f"  RESUMEN EJECUTIVO")
print(f"{'='*70}")
# Best combo
best_lbl=""; best_wr=0
for lbl,grp in combos:
    if not grp: continue
    w=pct(sum(1 for r in grp if r["correct"]),len(grp))
    if w>best_wr: best_wr=w; best_lbl=lbl.replace('\n',' ')
print(f"  Mejor combinacion: {best_lbl} = {best_wr:.0f}% WR")
print(f"  WR solo primera vela: {pct(wins,N):.0f}%")
print(f"  Dias COT BEAR + vela roja: {pct(sum(1 for r in bear_days if 'BEAR' in r['cot'] and r['correct']), len([r for r in bear_days if 'BEAR' in r['cot']])):.0f}%")
print(f"  Conclusion: {'Primera vela tiene EDGE real' if pct(wins,N)>55 else 'Primera vela sola NO tiene edge > 55% — necesita filtro'}")
