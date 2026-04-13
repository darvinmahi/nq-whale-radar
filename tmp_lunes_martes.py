"""
lunes_martes_predictor.py
Estudio: ¿Qué hace el MARTES después de un LUNES de X tipo?
COT BULL esta semana — hoy April 7, 2026 (Lunes)
"""
import csv, math
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as patches
import numpy as np

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; SOFT='#94a3b8'; DIM='#475569'

def utc_off(d):
    if date(2025,3,9)<=d<date(2025,11,2) or date(2026,3,8)<=d: return 4
    return 5

# ── CARGAR DATOS 15min ───────────────────────────────────────────────
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            if et.weekday()>=5: continue
            by_date[et.date()].append({
                "et":et, "o":float(r["Open"]), "h":float(r["High"]),
                "l":float(r["Low"]), "c":float(r["Close"]),
                "v":float(r.get("Volume",0) or 0)
            })
        except: pass

# ── CARGAR COT ────────────────────────────────────────────────────────
cot_map = {}
cot_rows = []
with open("data/cot/nasdaq_cot_historical.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            d   = datetime.strptime(r["Report_Date_as_MM_DD_YYYY"],"%Y-%m-%d").date()
            al  = int(r.get("Asset_Mgr_Positions_Long_All",0) or 0)
            as_ = int(r.get("Asset_Mgr_Positions_Short_All",0) or 0)
            ll  = int(r.get("Lev_Money_Positions_Long_All",0) or 0)
            ls  = int(r.get("Lev_Money_Positions_Short_All",0) or 0)
            cot_rows.append({"date":d,"am":al-as_,"lev":ll-ls})
        except: pass
cot_rows.sort(key=lambda x: x["date"])
for i,w in enumerate(cot_rows):
    w["am_d"] = w["am"] - cot_rows[i-1]["am"] if i>0 else 0
    win = [x["lev"] for x in cot_rows[max(0,i-51):i+1]]
    mn,mx = min(win),max(win)
    w["lev_p"] = round((w["lev"]-mn)/(mx-mn)*100,1) if mx!=mn else 50
    ad=w["am_d"]; lp=w["lev_p"]
    if   ad<-5000 and lp>60: sig="BEAR"
    elif ad>5000  and lp<40: sig="BULL"
    else:                      sig="NEUTRAL"
    w["sig"]=sig
    pub=w["date"]+timedelta(days=4)
    for sh in range(7):
        nm=pub+timedelta(days=sh)
        if nm.weekday()==0:
            for dd in range(5):
                cot_map[nm+timedelta(days=dd)]=sig
            break

# ── CALCULAR ESTADÍSTICAS DÍA ─────────────────────────────────────────
def day_stats(bars):
    """Estadísticas completas de un día"""
    if not bars: return None
    bars_s = sorted(bars, key=lambda x: x["et"])
    ny = [b for b in bars_s if
          (b["et"].hour==9 and b["et"].minute>=30) or
          (10<=b["et"].hour<16)]
    if not ny: return None
    open_  = ny[0]["o"]
    close_ = ny[-1]["c"]
    high_  = max(b["h"] for b in ny)
    low_   = min(b["l"] for b in ny)
    range_ = round(high_ - low_, 1)
    chg_pt = round(close_ - open_, 1)
    chg_pc = round(chg_pt / open_ * 100, 3)
    # Primera vela 9:30
    fc = next((b for b in bars_s if b["et"].hour==9 and b["et"].minute==30), None)
    fc_bull = fc["c"] > fc["o"] if fc else None
    fc_body = round(abs(fc["c"]-fc["o"]),1) if fc else 0
    # Apertura gap vs cierre anterior
    open930 = fc["o"] if fc else open_
    # Session high/low timing
    hi_bar = max(ny, key=lambda x: x["h"])
    lo_bar = min(ny, key=lambda x: x["l"])
    return {
        "open":open_, "close":close_, "high":high_, "low":low_,
        "range":range_, "chg_pt":chg_pt, "chg_pc":chg_pc,
        "bull": chg_pt>0, "fc_bull":fc_bull, "fc_body":fc_body,
        "open930": open930,
        "hi_hour": hi_bar["et"].hour, "lo_hour": lo_bar["et"].hour
    }

# ── CONSTRUIR PARES LUNES→MARTES ──────────────────────────────────────
pairs = []
sorted_dates = sorted(by_date.keys())
date_set = set(sorted_dates)

for d in sorted_dates:
    if d.weekday() != 0: continue  # Solo lunes
    # Buscar el martes siguiente (puede ser el martes, o siguiente día hábil)
    tue = d + timedelta(days=1)
    if tue not in date_set:
        tue = d + timedelta(days=2)
    if tue not in date_set: continue
    if tue.weekday() != 1: continue  # debe ser martes real

    mon_s = day_stats(by_date[d])
    tue_s = day_stats(by_date[tue])
    if not mon_s or not tue_s: continue

    cot_sig = cot_map.get(d, "UNKNOWN")

    # Clasificar el lunes
    chg = mon_s["chg_pt"]
    if   chg <= -100: mon_type = "CRASH"      # lunes rojo brutal
    elif chg <= -50:  mon_type = "BEAR_STRONG"
    elif chg <= -20:  mon_type = "BEAR"
    elif chg <= 20:   mon_type = "FLAT"
    elif chg <= 50:   mon_type = "BULL"
    else:             mon_type = "BULL_STRONG"

    pairs.append({
        "mon_date":d, "tue_date":tue,
        "mon":mon_s, "tue":tue_s,
        "mon_type":mon_type, "cot":cot_sig,
        "tue_bull": tue_s["bull"],
        "tue_pts": tue_s["chg_pt"],
    })

print(f"Pares Lunes-Martes analizados: {len(pairs)}")
print(f"Rango: {pairs[0]['mon_date']} → {pairs[-1]['mon_date']}")

# ── ANÁLISIS POR TIPO DE LUNES ────────────────────────────────────────
order = ["CRASH","BEAR_STRONG","BEAR","FLAT","BULL","BULL_STRONG"]
print(f"\n{'Tipo Lunes':<15} {'N':>5} {'Martes↑':>9} {'Avg Pts':>9} {'COT BULL→↑%':>13} {'COT BULL n':>11}")
for mtype in order:
    grp = [p for p in pairs if p["mon_type"]==mtype]
    if not grp: continue
    n = len(grp)
    bulls = sum(1 for p in grp if p["tue_bull"])
    avg_pts = sum(p["tue_pts"] for p in grp)/n
    # Con filtro COT BULL
    cot_bull = [p for p in grp if "BULL" in p["cot"]]
    cb_n = len(cot_bull)
    cb_up = sum(1 for p in cot_bull if p["tue_bull"])
    cb_pct = cb_up/cb_n*100 if cb_n else 0
    print(f"  {mtype:<13} {n:>5} {bulls/n*100:>8.0f}% {avg_pts:>+9.0f}pt {cb_pct:>12.0f}% {cb_n:>11}")

# ── HOY ES LUNES ROJO (TARIFF MONDAY APRIL 7) ─────────────────────────
# NQ abrió cerca de 19000 y cayó FUERTE — estimamos CRASH o BEAR_STRONG
# Basado en datos de mercado de hoy: NQ -5% aprox
print(f"\n{'='*65}")
print("  HOY: LUNES 7 ABR 2026 — TARIFF SELL-OFF")
print("  NQ estimado: CRASH (>-100pts) con sesgo COT BULL")
print(f"{'='*65}")

for mtype in ["CRASH","BEAR_STRONG"]:
    grp = [p for p in pairs if p["mon_type"]==mtype]
    cot_bull = [p for p in grp if "BULL" in p["cot"]]
    if not cot_bull: continue
    bulls = sum(1 for p in cot_bull if p["tue_bull"])
    avg = sum(p["tue_pts"] for p in cot_bull)/len(cot_bull)
    max_up = max((p["tue_pts"] for p in cot_bull),default=0)
    max_dn = min((p["tue_pts"] for p in cot_bull),default=0)
    print(f"\n  {mtype} + COT BULL ({len(cot_bull)} casos):")
    print(f"    Martes sube: {bulls}/{len(cot_bull)} = {bulls/len(cot_bull)*100:.0f}%")
    print(f"    Avg cambio: {avg:+.0f}pts")
    print(f"    Max sube: +{max_up:.0f}pts | Max baja: {max_dn:.0f}pts")
    # Casos específicos
    print(f"    Casos similares:")
    for p in sorted(cot_bull, key=lambda x: x["mon"]["chg_pt"])[:5]:
        mc=p["mon"]["chg_pt"]; tc=p["tue_pts"]
        arrow="↑" if tc>0 else "↓"
        print(f"      {p['mon_date']} Lun:{mc:+.0f}pt → Mar:{tc:+.0f}pt {arrow}")

# ── DISTRIBUCIÓN MARTES SEGÚN TIPO LUNES ─────────────────────────────
print(f"\n  DISTRIBUCIÓN HORARIA del MARTES (picos más frecuentes):")
for mtype in ["CRASH","BEAR_STRONG"]:
    grp = [p for p in pairs if p["mon_type"]==mtype and "BULL" in p["cot"]]
    if not grp: continue
    hi_hrs = [p["tue"]["hi_hour"] for p in grp]
    lo_hrs = [p["tue"]["lo_hour"] for p in grp]
    if hi_hrs:
        from collections import Counter
        hi_c = Counter(hi_hrs).most_common(3)
        lo_c = Counter(lo_hrs).most_common(3)
        print(f"    {mtype}: High en hora {hi_c[0][0]}:xx ({hi_c[0][1]} veces) | Low en hora {lo_c[0][0]}:xx ({lo_c[0][1]} veces)")

# ══════════════════════════════════════════════════════
# GRÁFICA
# ══════════════════════════════════════════════════════
fig = plt.figure(figsize=(22,15), facecolor=BG)
fig.suptitle("LUNES → MARTES HISTÓRICO | NQ Futures 2017-2026 | ¿Qué hace el Martes?",
             color=GOLD, fontsize=14, fontweight='bold', y=0.99)
gs = gridspec.GridSpec(2, 3, figure=fig, hspace=0.42, wspace=0.35,
                       left=0.05, right=0.97, top=0.95, bottom=0.05)

def pct(n,d): return n/d*100 if d else 0

# ── 1. WR Martes sube por tipo de Lunes ──────────────────────────────
ax1 = fig.add_subplot(gs[0,0]); ax1.set_facecolor(PANEL2)
wr_list=[]; n_list=[]; lbl_list=[]
for mtype in order:
    grp=[p for p in pairs if p["mon_type"]==mtype]
    if not grp: continue
    wr_list.append(pct(sum(1 for p in grp if p["tue_bull"]),len(grp)))
    n_list.append(len(grp))
    lbl_list.append(mtype.replace("_","\n"))
clrs=[RED if w<50 else GRN for w in wr_list]
bars=ax1.bar(lbl_list, wr_list, color=clrs, alpha=0.85, width=0.6)
ax1.axhline(50,color=DIM,lw=1,ls='--',alpha=0.6)
ax1.axhline(60,color=GOLD,lw=1,ls='--',alpha=0.4)
for b,w,n in zip(bars,wr_list,n_list):
    ax1.text(b.get_x()+b.get_width()/2, w+1, f'{w:.0f}%',
             color='white',ha='center',fontsize=10,fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2, 4, f'n={n}',
             color=SOFT,ha='center',fontsize=8.5)
ax1.set_ylim(0,95); ax1.set_ylabel('Martes Sube %',color=SOFT)
ax1.set_title('¿Sube Martes? — Por Tipo de Lunes',color=GOLD,fontsize=11,fontweight='bold')
ax1.tick_params(colors=SOFT,labelsize=8)
[ax1.spines[s].set_visible(False) for s in ['top','right']]
ax1.spines['left'].set_color(PANEL); ax1.spines['bottom'].set_color(PANEL)

# ── 2. WR con filtro COT BULL ─────────────────────────────────────────
ax2 = fig.add_subplot(gs[0,1]); ax2.set_facecolor(PANEL2)
wr2=[]; n2=[]; lbl2=[]
for mtype in order:
    grp=[p for p in pairs if p["mon_type"]==mtype and "BULL" in p["cot"]]
    if not grp: continue
    wr2.append(pct(sum(1 for p in grp if p["tue_bull"]),len(grp)))
    n2.append(len(grp))
    lbl2.append(mtype.replace("_","\n"))
clrs2=[GRN if w>=55 else (RED if w<45 else GOLD) for w in wr2]
bars2=ax2.bar(lbl2,wr2,color=clrs2,alpha=0.85,width=0.6)
ax2.axhline(50,color=DIM,lw=1,ls='--',alpha=0.6)
ax2.axhline(60,color=GOLD,lw=1,ls='--',alpha=0.4)
for b,w,n in zip(bars2,wr2,n2):
    ax2.text(b.get_x()+b.get_width()/2, w+1, f'{w:.0f}%',
             color='white',ha='center',fontsize=10,fontweight='bold')
    ax2.text(b.get_x()+b.get_width()/2, 4, f'n={n}',
             color=SOFT,ha='center',fontsize=8.5)
ax2.set_ylim(0,95); ax2.set_ylabel('Martes Sube %',color=SOFT)
ax2.set_title('COT BULL — ¿Sube Martes?',color=GOLD,fontsize=11,fontweight='bold')
ax2.tick_params(colors=SOFT,labelsize=8)
[ax2.spines[s].set_visible(False) for s in ['top','right']]
ax2.spines['left'].set_color(PANEL); ax2.spines['bottom'].set_color(PANEL)

# ── 3. Avg Pts Martes por tipo Lunes ─────────────────────────────────
ax3 = fig.add_subplot(gs[0,2]); ax3.set_facecolor(PANEL2)
avg_list=[]
for mtype in order:
    grp=[p for p in pairs if p["mon_type"]==mtype and "BULL" in p["cot"]]
    if not grp:
        avg_list.append(0)
    else:
        avg_list.append(sum(p["tue_pts"] for p in grp)/len(grp))
valid = [(l,a) for l,a in zip(lbl2,avg_list[:len(lbl2)]) if a!=0]
lbls_v=[x[0] for x in valid]; avgs_v=[x[1] for x in valid]
clrs3=[GRN if a>0 else RED for a in avgs_v]
bars3=ax3.bar(lbls_v,avgs_v,color=clrs3,alpha=0.85,width=0.6)
ax3.axhline(0,color='white',lw=1,alpha=0.5)
for b,a in zip(bars3,avgs_v):
    yp = a+2 if a>0 else a-8
    ax3.text(b.get_x()+b.get_width()/2, yp, f'{a:+.0f}pt',
             color='white',ha='center',fontsize=10,fontweight='bold')
ax3.set_ylabel('Avg Pts Martes (COT BULL)',color=SOFT)
ax3.set_title('Avg Movimiento Martes | COT BULL',color=GOLD,fontsize=11,fontweight='bold')
ax3.tick_params(colors=SOFT,labelsize=8)
[ax3.spines[s].set_visible(False) for s in ['top','right']]
ax3.spines['left'].set_color(PANEL); ax3.spines['bottom'].set_color(PANEL)

# ── 4. Scatter: Pts Lunes vs Pts Martes ───────────────────────────────
ax4 = fig.add_subplot(gs[1,:2]); ax4.set_facecolor(PANEL2)
all_mon=[p["mon"]["chg_pt"] for p in pairs]
all_tue=[p["tue_pts"] for p in pairs]
cot_b=[p for p in pairs if "BULL" in p["cot"]]

ax4.scatter(all_mon, all_tue, color=SOFT, alpha=0.15, s=25, label='Todos')
ax4.scatter([p["mon"]["chg_pt"] for p in cot_b],
            [p["tue_pts"] for p in cot_b],
            color=GRN, alpha=0.5, s=40, label='COT BULL', zorder=5)

# HOY: resalta zona CRASH (< -100pts lunes)
ax4.axvspan(-800,-100,alpha=0.08,color=RED,label='Zona CRASH')
ax4.axhline(0,color='white',lw=0.7,alpha=0.5)
ax4.axvline(0,color='white',lw=0.7,alpha=0.5)
ax4.axvline(-100,color=RED,lw=1.2,ls='--',alpha=0.7,label='Umbral CRASH')

# Tendencia COT BULL
if len(cot_b)>5:
    x_b=np.array([p["mon"]["chg_pt"] for p in cot_b])
    y_b=np.array([p["tue_pts"] for p in cot_b])
    z=np.polyfit(x_b,y_b,1)
    p_=np.poly1d(z)
    xs=np.linspace(min(x_b),max(x_b),100)
    ax4.plot(xs,p_(xs),color=GOLD,lw=2,ls='--',label='Tendencia COT BULL')

ax4.set_xlabel('Pts Lunes (NY Open→Close)',color=SOFT)
ax4.set_ylabel('Pts Martes (NY Open→Close)',color=SOFT)
ax4.set_title('Relación Lunes→Martes | Scatter NQ 2017-2026',color=GOLD,fontsize=11,fontweight='bold')
ax4.tick_params(colors=SOFT)
ax4.legend(fontsize=9,facecolor=BG,labelcolor=SOFT,loc='upper left')
[ax4.spines[s].set_visible(False) for s in ['top','right']]
ax4.spines['left'].set_color(PANEL); ax4.spines['bottom'].set_color(PANEL)

# ── 5. Panel resumen HOY ──────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1,2]); ax5.set_facecolor('#0d0020')
ax5.set_xlim(0,10); ax5.set_ylim(0,12); ax5.axis('off')

ax5.add_patch(patches.FancyBboxPatch((0.2,11.0),9.6,0.75,
    boxstyle="round,pad=0.1",facecolor='#1a0030',edgecolor=PRP,linewidth=2))
ax5.text(5,11.38,'HOY LUNES 7 ABR — TARIFF SELL-OFF',
         ha='center',va='center',fontsize=11,fontweight='bold',color=PRP)

# Stats CRASH + COT BULL
crash_bull=[p for p in pairs if p["mon_type"]=="CRASH" and "BULL" in p["cot"]]
bear_bull=[p for p in pairs if p["mon_type"]=="BEAR_STRONG" and "BULL" in p["cot"]]
combined = crash_bull + bear_bull
n_c=len(combined)
up_c=sum(1 for p in combined if p["tue_bull"])
avg_c=sum(p["tue_pts"] for p in combined)/max(1,n_c)
max_up_c=max((p["tue_pts"] for p in combined),default=0)
max_dn_c=min((p["tue_pts"] for p in combined),default=0)

lines = [
    (GOLD, "bold", "COT BULL + Lunes Caída Fuerte:"),
    (GRN,  "bold", f"Martes sube: {up_c}/{n_c} = {pct(up_c,n_c):.0f}%"),
    (GRN if avg_c>0 else RED, "bold", f"Avg Martes: {avg_c:+.0f} pts"),
    (SOFT, "normal",f"Máx suba: +{max_up_c:.0f}pts"),
    (SOFT, "normal",f"Máx baja: {max_dn_c:.0f}pts"),
    ("", "", ""),
    (GOLD, "bold", "SETUP MARTES 8 ABR:"),
    (GRN,  "bold",  "1. Esperar primera vela 9:30"),
    (SOFT, "normal","   Si verde >15pts → LONG"),
    (SOFT, "normal","   TP1: +50pts =$300 (3MNQ)"),
    (SOFT, "normal","   SL: -25pts =-$150"),
]
for i,(c,w,t) in enumerate(lines):
    if t:
        ax5.text(0.5,10.2-i*0.83,t,fontsize=9.5,color=c,fontweight=w,va='center')

# Probability arc
wr_val=pct(up_c,n_c)
angle=wr_val/100*180
theta=np.linspace(0,np.pi,100)
ax5.plot(5+3.5*np.cos(theta), 1.0+2.2*np.sin(theta), color=DIM, lw=6, solid_capstyle='round')
angle_rad=wr_val/100*np.pi
ax5.plot(5+3.5*np.cos(np.linspace(0,angle_rad,100)),
         1.0+2.2*np.sin(np.linspace(0,angle_rad,100)),
         color=GRN if wr_val>=55 else RED, lw=6, solid_capstyle='round')
ax5.text(5,1.2,f'{wr_val:.0f}%',ha='center',va='center',fontsize=20,fontweight='bold',
         color=GRN if wr_val>=55 else RED)
ax5.text(5,0.4,'Prob. Martes Suba',ha='center',fontsize=9,color=SOFT)
ax5.text(2.8,1.0,'0%',ha='center',fontsize=9,color=DIM)
ax5.text(7.2,1.0,'100%',ha='center',fontsize=9,color=DIM)

out="lunes_martes_predictor.png"
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f"\nGrafica guardada: {out}")
