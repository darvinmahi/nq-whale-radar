"""
backtest_martes_post_crash.py
HOY: LUNES 7 ABR 2026 — Preparando para MARTES 8 ABR
Pregunta: En los 28 Lunes con caída >80pts, ¿qué hizo el Martes?
Extra: Comparar con los 6 Lunes de divergencia COT más relevantes
"""
import csv
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

def utc_off(d):
    if date(2025,3,9)<=d<date(2025,11,2) or date(2026,3,8)<=d: return 4
    return 5

# ── CARGA DATOS ───────────────────────────────────────────────────────
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            if et.weekday()>=5: continue
            by_date[et.date()].append({
                "et":et,"o":float(r["Open"]),"h":float(r["High"]),
                "l":float(r["Low"]),"c":float(r["Close"])
            })
        except: pass

# ── SLOTS 15min de 9:30 a 16:00 ──────────────────────────────────────
SLOTS=[]
for h in range(9,16):
    for m in (0,15,30,45):
        if h==9 and m<30: continue
        SLOTS.append((h,m))
N=len(SLOTS); x=list(range(N))
labels=[f"{h}:{m:02d}" for h,m in SLOTS]

def get_ny(d):
    bars=sorted(by_date[d],key=lambda b:b["et"])
    return [b for b in bars if
            (b["et"].hour==9 and b["et"].minute>=30) or
            (10<=b["et"].hour<16)]

def day_stats(ny):
    if not ny: return None
    o=ny[0]["o"]; c=ny[-1]["c"]
    hi=max(b["h"] for b in ny); lo=min(b["l"] for b in ny)
    hi_hr=max(ny,key=lambda b:b["h"])["et"].hour
    lo_hr=min(ny,key=lambda b:b["l"])["et"].hour
    # Vela 9:30
    fc=next((b for b in ny if b["et"].hour==9 and b["et"].minute==30),None)
    return {"o":o,"c":c,"hi":hi,"lo":lo,"chg":round(c-o,1),"rng":round(hi-lo,1),
            "bull":c>o,"hi_hr":hi_hr,"lo_hr":lo_hr,
            "fc_bull":fc["c"]>fc["o"] if fc else None,
            "fc_body":round(abs(fc["c"]-fc["o"]),1) if fc else 0,
            "open":o}

def path_15m(ny, open_price):
    """Vector de pts desde apertura, un valor por slot"""
    p=[0.0]*N
    for b in ny:
        for i,(h,m) in enumerate(SLOTS):
            if b["et"].hour==h and b["et"].minute==m:
                p[i]=round(b["c"]-open_price,1)
    # ffill
    last=0.0
    for i in range(N):
        if p[i]!=0: last=p[i]
        elif i>0: p[i]=last
    return p

# ── CONSTRUIR CASOS ───────────────────────────────────────────────────
sorted_dates=sorted(by_date.keys())
date_set=set(sorted_dates)
cases=[]
for d in sorted_dates:
    if d.weekday()!=0: continue
    mn=get_ny(d); ms=day_stats(mn)
    if not ms or ms["chg"]>-50: continue   # Lunes con caída >50pts
    tue=d+timedelta(days=1)
    if tue not in date_set or tue.weekday()!=1: continue
    tn=get_ny(tue); ts=day_stats(tn)
    if not ts: continue
    p=path_15m(tn, ts["open"])
    cases.append({
        "mon":d,"tue":tue,
        "mon_chg":ms["chg"],"mon_rng":ms["rng"],
        "tue_chg":ts["chg"],"tue_rng":ts["rng"],
        "tue_bull":ts["bull"],
        "tue_fc_bull":ts["fc_bull"],"tue_fc_body":ts["fc_body"],
        "hi_hr":ts["hi_hr"],"lo_hr":ts["lo_hr"],
        "path":p
    })
cases.sort(key=lambda c:c["mon"])

# Clasificar por tamaño de caída
def classify(chg):
    if chg<=-200: return "MEGA CRASH (>200)"
    if chg<=-100: return "CRASH (100-200)"
    return "BEAR STRONG (50-100)"

for c in cases: c["tipo"]=classify(c["mon_chg"])

print(f"Lunes con caída >50pts (2017-2026): {len(cases)}")
print()

# ── TABLA PRINCIPAL ───────────────────────────────────────────────────
print(f"{'Lun Fecha':<13} {'Lun Chg':>9} {'Tipo':<22} {'Mar Fecha':<13} {'Mar Chg':>9} {'↑↓':>4} {'Hi Hr':>6} {'Lo Hr':>6} {'Rng':>6}")
print("-"*95)
for c in cases:
    arr="↑" if c["tue_bull"] else "↓"
    print(f"  {c['mon']}  {c['mon_chg']:>+8.0f}  {c['tipo']:<20}  {c['tue']}  {c['tue_chg']:>+8.0f}  {arr:>4}  {c['hi_hr']:>6}  {c['lo_hr']:>6}  {c['tue_rng']:>6.0f}")

print()
# ── STATS POR GRUPO ───────────────────────────────────────────────────
for tipo in ["BEAR STRONG (50-100)","CRASH (100-200)","MEGA CRASH (>200)"]:
    g=[c for c in cases if c["tipo"]==tipo]
    if not g: continue
    n=len(g); ups=sum(1 for c in g if c["tue_bull"])
    avg=sum(c["tue_chg"] for c in g)/n
    avg_rng=sum(c["tue_rng"] for c in g)/n
    hi_c=Counter(c["hi_hr"] for c in g).most_common(2)
    lo_c=Counter(c["lo_hr"] for c in g).most_common(2)
    fc_ups=sum(1 for c in g if c["tue_fc_bull"])
    print(f"{tipo}:")
    print(f"  n={n} | Martes sube: {ups}/{n}={ups/n*100:.0f}% | Avg: {avg:+.0f}pts | Avg rango: {avg_rng:.0f}pts")
    print(f"  High típico: hr {hi_c[0][0]} ({hi_c[0][1]}x) | Low típico: hr {lo_c[0][0]} ({lo_c[0][1]}x)")
    print(f"  1a vela 9:30 verde: {fc_ups}/{n} = {fc_ups/n*100:.0f}%")
    print()

# ══════════════════════════════════════════════════
# FIGURA
# ══════════════════════════════════════════════════
fig=plt.figure(figsize=(24,17),facecolor=BG)
fig.suptitle("BACKTEST: MARTES después de LUNES de CAÍDA FUERTE | NQ 2017-2026 | Preparación Martes 8 Abr",
             color=GOLD,fontsize=13,fontweight='bold',y=0.99)
gs=gridspec.GridSpec(2,3,figure=fig,hspace=0.4,wspace=0.28,
                     left=0.05,right=0.97,top=0.95,bottom=0.05)

# ── A. Paths individuales ─────────────────────────────────────────────
ax1=fig.add_subplot(gs[0,:2]); ax1.set_facecolor(PANEL2)

tipos_cfg={
    "BEAR STRONG (50-100)": (BLU, 0.25),
    "CRASH (100-200)":       (GOLD, 0.40),
    "MEGA CRASH (>200)":     (RED,  0.60),
}
for tipo,(col,alpha) in tipos_cfg.items():
    g=[c for c in cases if c["tipo"]==tipo]
    for c in g:
        lc = GRN if c["tue_bull"] else RED
        ax1.plot(x, c["path"], color=lc, alpha=0.12, lw=1)

# Promedio por tipo
for tipo,(col,alpha) in tipos_cfg.items():
    g=[c for c in cases if c["tipo"]==tipo]
    if not g: continue
    avg_p=np.mean([c["path"] for c in g],axis=0)
    n_=len(g); ups_=sum(1 for c in g if c["tue_bull"])
    ax1.plot(x, avg_p, color=col, lw=2.5, alpha=0.9,
             label=f'{tipo.split("(")[0].strip()} n={n_} ({ups_/n_*100:.0f}%↑)')

ax1.axhline(0,color='white',lw=1,alpha=0.4)
for i,(h,m) in enumerate(SLOTS):
    if m==0:
        ax1.axvline(i,color=DIM,lw=0.4,alpha=0.4)
        ax1.text(i,ax1.get_ylim()[0]-3,f'{h}h',ha='center',fontsize=7,color=DIM)

# Ahora mismo: span preparación (es lunes, sesión cerrada NY)
ax1.axvspan(0,N,alpha=0.02,color=GOLD)
ax1.text(N//2,max(c["tue_rng"] for c in cases)*0.38,
         "MAÑANA MARTES\n9:30 - 16:00 ET",
         ha='center',fontsize=12,color=GOLD,alpha=0.25,fontweight='bold')

ax1.set_xticks(x[::4]); ax1.set_xticklabels(labels[::4],fontsize=7.5,color=SOFT,rotation=30)
ax1.set_ylabel('pts desde Open 9:30',color=SOFT)
ax1.set_title('PATH INTRADIARIO — Avg por grupo de Caída del Lunes',
              color=GOLD,fontsize=11,fontweight='bold')
ax1.legend(fontsize=9,facecolor=BG,labelcolor=SOFT,loc='upper left')
ax1.tick_params(colors=SOFT)
[ax1.spines[s].set_visible(False) for s in ['top','right']]

# ── B. WR por tipo ────────────────────────────────────────────────────
ax2=fig.add_subplot(gs[0,2]); ax2.set_facecolor(PANEL2)
tipos_order=["BEAR STRONG (50-100)","CRASH (100-200)","MEGA CRASH (>200)"]
wr_vals=[]; n_vals=[]; lbl_vals=[]
avg_vals=[]
for tipo in tipos_order:
    g=[c for c in cases if c["tipo"]==tipo]
    if not g: continue
    n_=len(g); ups_=sum(1 for c in g if c["tue_bull"])
    wr_vals.append(ups_/n_*100)
    n_vals.append(n_)
    avg_vals.append(sum(c["tue_chg"] for c in g)/n_)
    lbl_vals.append(tipo.replace(" (","  \n("))

clrs_w=[GRN if w>=55 else (RED if w<45 else GOLD) for w in wr_vals]
b2=ax2.bar(lbl_vals,wr_vals,color=clrs_w,alpha=0.85,width=0.55)
ax2.axhline(50,color='white',lw=1,ls='--',alpha=0.5)
for b_,w_,n_ in zip(b2,wr_vals,n_vals):
    ax2.text(b_.get_x()+b_.get_width()/2,w_+1.5,f'{w_:.0f}%',
             color='white',ha='center',fontsize=12,fontweight='bold')
    ax2.text(b_.get_x()+b_.get_width()/2,5,f'n={n_}',
             color=SOFT,ha='center',fontsize=9)
ax2.set_ylim(0,90); ax2.set_ylabel('% Martes Sube',color=SOFT)
ax2.set_title('WR Martes Sube\nPor Magnitud Caída Lunes',color=GOLD,fontsize=11,fontweight='bold')
ax2.tick_params(colors=SOFT,labelsize=8)
[ax2.spines[s].set_visible(False) for s in ['top','right']]

# ── C. Tabla de los 6 Lunes de divergencia COT más relevantes ────────
# Los 6 lunes CRASH más recientes (análogos al hoy)
ax3=fig.add_subplot(gs[1,:2]); ax3.set_facecolor(PANEL2)
ax3.set_xlim(0,14); ax3.set_ylim(0,len(cases)+1); ax3.axis('off')

# Cabecera
ax3.text(0.3,len(cases)+0.5,'Fecha Lunes',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(2.8,len(cases)+0.5,'Lun Chg',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(4.3,len(cases)+0.5,'Tipo',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(7.5,len(cases)+0.5,'Fecha Martes',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(10.0,len(cases)+0.5,'Mar Chg',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(11.5,len(cases)+0.5,'Hi Hr',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(12.5,len(cases)+0.5,'Lo Hr',fontsize=9,color=GOLD,fontweight='bold')
ax3.text(13.2,len(cases)+0.5,'Rng',fontsize=9,color=GOLD,fontweight='bold')
ax3.axhline(len(cases)+0.2,color=DIM,lw=0.7)

for i,c in enumerate(reversed(cases)):
    y=i+0.4
    arr_c=GRN if c["tue_bull"] else RED
    tipo_s=c["tipo"].replace(" (50-100)","").replace(" (100-200)","").replace(" (>200)","")
    tipo_c={
        "BEAR STRONG":BLU,
        "CRASH":GOLD,
        "MEGA CRASH":RED
    }.get(tipo_s,SOFT)
    # Highlight los 6 más similares (crash>100 más recientes)
    highlight = c["mon_chg"]<=-100
    bg_c='#1a1a30' if highlight else BG
    if highlight:
        ax3.add_patch(patches.Rectangle((0,y-0.3),14,0.75,
            facecolor='#1a1a30',edgecolor=GOLD,linewidth=0.5,alpha=0.6))
    ax3.text(0.3,y,str(c["mon"]),fontsize=8.5,color=WHITE if highlight else SOFT,va='center')
    ax3.text(2.8,y,f'{c["mon_chg"]:+.0f}',fontsize=8.5,color=RED,fontweight='bold',va='center')
    ax3.text(4.3,y,tipo_s,fontsize=8,color=tipo_c,va='center')
    ax3.text(7.5,y,str(c["tue"]),fontsize=8.5,color=SOFT,va='center')
    ax3.text(10.0,y,f'{c["tue_chg"]:+.0f}',fontsize=9,color=arr_c,fontweight='bold',va='center')
    ax3.text(11.5,y,f'{c["hi_hr"]}h',fontsize=8.5,color=GRN,va='center')
    ax3.text(12.5,y,f'{c["lo_hr"]}h',fontsize=8.5,color=RED,va='center')
    ax3.text(13.2,y,f'{c["tue_rng"]:.0f}',fontsize=8.5,color=SOFT,va='center')
    ax3.axhline(y-0.3,color=DIM,lw=0.3,alpha=0.4)

WHITE='#f1f5f9'
ax3.text(0.0,len(cases)+0.75,'★ Dorado = CRASH>100pts (más similares a hoy)',
         fontsize=8,color=GOLD)
ax3.set_title(f'TODOS LOS CASOS: {len(cases)} Lunes con caída >50pts → Martes siguiente',
              color=GOLD,fontsize=11,fontweight='bold',pad=8)

# ── D. Panel Resumen para mañana ─────────────────────────────────────
ax4=fig.add_subplot(gs[1,2]); ax4.set_facecolor('#080818')
ax4.set_xlim(0,10); ax4.set_ylim(0,16); ax4.axis('off')

# Stats crash >100
crash=[c for c in cases if c["mon_chg"]<=-100]
n_cr=len(crash); ups_cr=sum(1 for c in crash if c["tue_bull"])
avg_cr=sum(c["tue_chg"] for c in crash)/max(1,n_cr)
avg_rng_cr=sum(c["tue_rng"] for c in crash)/max(1,n_cr)
hi_cr=Counter(c["hi_hr"] for c in crash).most_common(2)
lo_cr=Counter(c["lo_hr"] for c in crash).most_common(2)
fc_cr=sum(1 for c in crash if c["tue_fc_bull"])

ax4.add_patch(patches.FancyBboxPatch((0.2,14.9),9.6,0.85,
    boxstyle="round,pad=0.1",facecolor='#0d1a2d',edgecolor=GOLD,linewidth=2))
ax4.text(5,15.33,'PREPARACION MARTES 8 ABR 2026',
         ha='center',va='center',fontsize=10,fontweight='bold',color=GOLD)

info=[
    (GOLD,"bold","───── CRASH >100pts (n=%d) ─────"%n_cr,""),
    (GRN if ups_cr/max(1,n_cr)>=0.5 else RED,"bold",
     "Martes sube:",f"{ups_cr}/{n_cr} = {ups_cr/max(1,n_cr)*100:.0f}%"),
    (GRN if avg_cr>0 else RED,"bold","Avg movimiento:",f"{avg_cr:+.0f}pts"),
    (SOFT,"normal","Avg rango del día:",f"{avg_rng_cr:.0f}pts"),
    (GRN,"bold",f"HIGH típico:","hr {hi_cr[0][0]}:xx ({hi_cr[0][1]}x)"),
    (RED,"bold",f"LOW típico:","hr {lo_cr[0][0]}:xx ({lo_cr[0][1]}x)"),
    (BLU,"bold","1a vela verde:",f"{fc_cr}/{n_cr} = {fc_cr/max(1,n_cr)*100:.0f}%"),
    ("","","",""),
    (GOLD,"bold","───── SETUP MAÑANA ─────",""),
    (GRN,"bold","COT: BULL","Solo LONGS"),
    (SOFT,"normal","Low suele ser a 9:xx","→ Panic open = trampa"),
    (SOFT,"normal","High suele ser a 10:xx","→ Bounce 9:30-10:30"),
    (GRN,"bold","Si 1a vela verde >15pts","→ LONG"),
    (SOFT,"normal","SL: 25pts  |  TP1: 50pts","3 MNQ = $150/$300"),
    (ORG,"bold","Rango esperado:","~200pts"),
]
for i,(c,w,k,v) in enumerate(info):
    y=13.7-i*0.82
    if c:
        ax4.text(0.4,y,k,fontsize=9,color=c,fontweight=w,va='center')
        if v: ax4.text(5.8,y,v,fontsize=9,color=c,fontweight='bold',va='center')

# Arc
wr_final=ups_cr/max(1,n_cr)*100
import numpy as np
tht=np.linspace(0,np.pi,100)
ax4.plot(5+3.2*np.cos(tht),1.4+2*np.sin(tht),color=DIM,lw=7,solid_capstyle='round')
ax4.plot(5+3.2*np.cos(np.linspace(0,wr_final/100*np.pi,100)),
         1.4+2*np.sin(np.linspace(0,wr_final/100*np.pi,100)),
         color=GRN if wr_final>=50 else RED,lw=7,solid_capstyle='round')
ax4.text(5,1.55,f'{wr_final:.0f}%',ha='center',fontsize=22,fontweight='bold',
         color=GRN if wr_final>=50 else RED)
ax4.text(5,0.5,'Prob. Martes Suba (crash>100)',ha='center',fontsize=8.5,color=SOFT)
ax4.text(2.4,1.4,'0%',fontsize=9,color=DIM,ha='center')
ax4.text(7.6,1.4,'100%',fontsize=9,color=DIM,ha='center')

out="backtest_martes_post_crash.png"
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f"\nGrafica: {out}")
