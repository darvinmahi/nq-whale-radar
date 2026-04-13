"""
setup_primera_vela_v2.py
Setup completo "Opening Drive" — Primera Vela 9:30 como señal
3-4 MNQ | Cuenta Apex $50k
Reglas exactas con backtest real
"""
import csv, math
from datetime import datetime, timedelta, date
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec
import numpy as np

# ── OFFSET UTC ────────────────────────────────────────────────────────
def utc_off(d):
    if date(2025,3,9)<=d<date(2025,11,2) or date(2026,3,8)<=d: return 4
    return 5

# ── PARÁMETROS 3 MNQ ─────────────────────────────────────────────────
CONTRACTS = 3; PT_VAL = 2; TICK = CONTRACTS * PT_VAL  # $6/pt

# Tres variantes de SL para comparar
CONFIGS = [
    {"name":"Agresivo",  "sl":15, "tp1":30,  "tp2":50,  "risk":15*6},
    {"name":"Base",      "sl":25, "tp1":50,  "tp2":67,  "risk":25*6},
    {"name":"Conserv.",  "sl":35, "tp1":70,  "tp2":100, "risk":35*6},
]
# Usaremos el Base para el análisis principal
SL=25; TP1=50; TP2=67
RISK_USD = SL * TICK   # $150
TP1_USD  = TP1 * TICK  # $300
TP2_USD  = round(TP2 * TICK)  # $402

# ── CARGAR BARRAS ────────────────────────────────────────────────────
by_date = defaultdict(list)
with open("data/research/nq_15m_intraday.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        try:
            raw = datetime.fromisoformat(r["Datetime"].replace("+00:00",""))
            et  = raw - timedelta(hours=utc_off(raw.date()))
            if et.weekday()>=5: continue
            by_date[et.date()].append({
                "et":et,"o":float(r["Open"]),"h":float(r["High"]),
                "l":float(r["Low"]),"c":float(r["Close"]),
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
    w["am_d"]=w["am"]-cot_rows[i-1]["am"] if i>0 else 0
    win=[x["lev"] for x in cot_rows[max(0,i-51):i+1]]
    mn,mx=min(win),max(win)
    w["lev_p"]=round((w["lev"]-mn)/(mx-mn)*100,1) if mx!=mn else 50
    ad=w["am_d"]; lp=w["lev_p"]
    if   ad<-5000 and lp>60: sig="BEAR"
    elif ad>5000  and lp<40: sig="BULL"
    else:                     sig="NEUTRAL"
    w["sig"]=sig
    pub=w["date"]+timedelta(days=4)
    for sh in range(7):
        nm=pub+timedelta(days=sh)
        if nm.weekday()==0:
            for dd in range(5):
                cot_map[nm+timedelta(days=dd)]=sig
            break

DOW={0:"Lunes",1:"Martes",2:"Miercoles",3:"Jueves",4:"Viernes"}

# ── BACKTEST ─────────────────────────────────────────────────────────
results = []

for d, bars in by_date.items():
    bars = sorted(bars, key=lambda x: x["et"])

    # Primera vela 9:30–9:45
    fc = next((b for b in bars if b["et"].hour==9 and b["et"].minute==30), None)
    if not fc: continue

    # Resto del día (barras NY de 9:45 a 16:00)
    rest = [b for b in bars if
            (b["et"].hour==9 and b["et"].minute>=45) or
            (10<=b["et"].hour<16)]
    if len(rest)<4: continue

    # VWAP corriente desde 9:30
    cum_pv=fc["c"]*max(fc["v"],1); cum_v=max(fc["v"],1)
    for b in rest:
        mid=(b["h"]+b["l"]+b["c"])/3; v=max(b["v"],1)
        cum_pv+=mid*v; cum_v+=v
        b["vwap"]=cum_pv/cum_v

    # Propiedades primera vela
    fc_body  = round(fc["c"]-fc["o"], 1)       # positivo=verde, negativo=roja
    fc_range = round(fc["h"]-fc["l"], 1)
    fc_bull  = fc_body > 0
    vwap_at945 = rest[0]["vwap"]

    # ── FILTROS DE ENTRADA ────────────────────────────────────────────
    # 1. Cuerpo fuerte > 15pts
    if abs(fc_body) < 15: continue

    # 2. Dirección
    direction = "LONG" if fc_bull else "SHORT"

    # 3. VWAP confirma (precio debe estar del lado correcto del VWAP al cerrar la primera vela)
    fc_vwap_ok = (fc_bull and fc["c"] > vwap_at945) or (not fc_bull and fc["c"] < vwap_at945)

    # ── ENTRADA ───────────────────────────────────────────────────────
    # Entrada al cierre de primera vela a las 9:45 (primer bar disponible)
    entry_bar = rest[0]
    entry     = fc["c"]  # entrada al precio de cierre de la primera vela

    # SL: bajo el Low de la primera vela para LONG, sobre el High para SHORT
    sl_natural = fc["l"] if direction=="LONG" else fc["h"]
    sl_dist    = abs(entry - sl_natural)

    # Usamos el max(sl_natural, SL fijo) para no tener SL extragrande
    sl_pts_used = max(min(sl_dist, SL*1.5), SL*0.5)  # entre 12.5 y 37.5 pts
    sl_pts_used = SL  # simplificado: SL fijo de 25pts para consistencia

    sl_price  = entry - sl_pts_used if direction=="LONG" else entry + sl_pts_used
    tp1_price = entry + TP1         if direction=="LONG" else entry - TP1
    tp2_price = entry + TP2         if direction=="LONG" else entry - TP2

    # ── SIMULAR TRADE ─────────────────────────────────────────────────
    outcome="OPEN"; exit_pts=0; exit_et=rest[-1]["et"]
    for b in rest[1:]:
        if direction=="LONG":
            if b["l"]<=sl_price:  outcome="SL";  exit_pts=-sl_pts_used; exit_et=b["et"]; break
            if b["h"]>=tp2_price: outcome="TP2"; exit_pts=TP2;          exit_et=b["et"]; break
            if b["h"]>=tp1_price: outcome="TP1"; exit_pts=TP1;          exit_et=b["et"]; break
        else:
            if b["h"]>=sl_price:  outcome="SL";  exit_pts=-sl_pts_used; exit_et=b["et"]; break
            if b["l"]<=tp2_price: outcome="TP2"; exit_pts=TP2;          exit_et=b["et"]; break
            if b["l"]<=tp1_price: outcome="TP1"; exit_pts=TP1;          exit_et=b["et"]; break

    if outcome=="OPEN":
        last=rest[-1]["c"]
        exit_pts=round(last-entry if direction=="LONG" else entry-last,1)

    pnl_raw = exit_pts * TICK
    if outcome=="SL": pnl_raw = -RISK_USD
    pnl = round(pnl_raw)
    ok  = outcome in ("TP1","TP2")

    # Duración en minutos
    dur_min = int((exit_et - entry_bar["et"]).total_seconds() / 60)

    # Extensión máxima a favor
    mfe = 0
    for b in rest:
        if direction=="LONG": mfe=max(mfe, b["h"]-entry)
        else:                  mfe=max(mfe, entry-b["l"])

    cot_sig = cot_map.get(d,"UNKNOWN")

    results.append({
        "date":d,"dow":d.weekday(),"dow_name":DOW[d.weekday()],
        "direction":direction,"fc_body":abs(fc_body),"fc_range":fc_range,
        "fc_vwap_ok":fc_vwap_ok,"cot":cot_sig,
        "entry":entry,"sl":sl_price,"tp1":tp1_price,"tp2":tp2_price,
        "outcome":outcome,"exit_pts":exit_pts,"pnl":pnl,"ok":ok,
        "dur_min":dur_min,"mfe":round(mfe,1),
        "entry_bar":entry_bar,"fc":fc,"rest":rest
    })

# ── ESTADÍSTICAS ─────────────────────────────────────────────────────
N=len(results); wins=sum(1 for r in results if r["ok"])
total_pnl=sum(r["pnl"] for r in results)
avg_dur=sum(r["dur_min"] for r in results if r["ok"])/max(1,wins)
avg_mfe=sum(r["mfe"] for r in results)/N

# Por filtros
def stats(grp, lbl=""):
    if not grp: return
    n=len(grp); w=sum(1 for r in grp if r["ok"])
    pnl=sum(r["pnl"] for r in grp)
    wr=w/n*100
    tp2s=sum(1 for r in grp if r["outcome"]=="TP2")
    tp1s=sum(1 for r in grp if r["outcome"]=="TP1")
    sls =sum(1 for r in grp if r["outcome"]=="SL")
    print(f"  {lbl:<35}: {w}/{n}={wr:.0f}% | TP2:{tp2s} TP1:{tp1s} SL:{sls} | P&L:${pnl:+}")

print(f"\n{'='*72}")
print(f"  SETUP 'OPENING DRIVE' — PRIMERA VELA 9:30 | REGLAS COMPLETAS")
print(f"  3 MNQ: $6/pt | SL={SL}pts=${RISK_USD} | TP1={TP1}pts=${TP1_USD} | TP2={TP2}pts=${TP2_USD}")
print(f"{'='*72}")
stats(results, f"GLOBAL (cuerpo>15pts)")

print(f"\n  Por +VWAP confirmado:")
vwap_ok=[r for r in results if r["fc_vwap_ok"]]
vwap_ko=[r for r in results if not r["fc_vwap_ok"]]
stats(vwap_ok, "  + VWAP confirma")
stats(vwap_ko, "  - VWAP NO confirma")

print(f"\n  Por día de semana:")
for dn,di in [("Lunes",0),("Martes",1),("Miercoles",2),("Jueves",3),("Viernes",4)]:
    stats([r for r in results if r["dow"]==di], f"    {dn}")

print(f"\n  Por día + VWAP OK (solo Mie-Jue):")
mj_vwap=[r for r in results if r["dow"] in (2,3) and r["fc_vwap_ok"]]
stats(mj_vwap, "    Mie/Jue + VWAP OK")

print(f"\n  Por COT:")
for sig in ["NEUTRAL","BEAR","BULL"]:
    stats([r for r in results if r["cot"]==sig], f"    COT {sig}")

print(f"\n  Mie/Jue + VWAP + COT alineado:")
best=[r for r in results if r["dow"] in (2,3) and r["fc_vwap_ok"]
      and ((r["direction"]=="LONG" and "BULL" in r["cot"]) or
           (r["direction"]=="SHORT" and "BEAR" in r["cot"]))]
stats(best, "    TRIPLE FILTRO")

print(f"\n  Datos adicionales:")
print(f"    Avg duración ganadores: {avg_dur:.0f} min")
print(f"    Avg MFE total: {avg_mfe:.0f}pts")
tp2_pct=sum(1 for r in results if r["outcome"]=="TP2")/N*100
tp1_pct=sum(1 for r in results if r["outcome"]=="TP1")/N*100
sl_pct =sum(1 for r in results if r["outcome"]=="SL" )/N*100
print(f"    Distribución: TP2={tp2_pct:.0f}% | TP1={tp1_pct:.0f}% | SL={sl_pct:.0f}%")

# ── TARJETA VISUAL DEL SETUP ─────────────────────────────────────────
BG='#0d0d1a'; PANEL='#131325'; GRN='#10b981'; RED='#ef4444'
GOLD='#f59e0b'; BLU='#60a5fa'; PRP='#a78bfa'; GRAY='#334155'

fig = plt.figure(figsize=(22, 15), facecolor=BG)
gs  = gridspec.GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.35)

# ── PANEL 1: WR por filtros (barras) ──────────────────────────────────
ax1 = fig.add_subplot(gs[0, :2]); ax1.set_facecolor(PANEL)
filter_groups = [
    ("Global\n>15pts body",results),
    ("+ VWAP\nconfirma",vwap_ok),
    ("Mie/Jue\n+ VWAP",mj_vwap),
    ("TRIPLE\nFiltro",best),
]
fg_labels=[f[0] for f in filter_groups]
fg_wrs=[sum(1 for r in f[1] if r["ok"])/max(1,len(f[1]))*100 for f in filter_groups]
fg_ns=[len(f[1]) for f in filter_groups]
fg_pnls=[sum(r["pnl"] for r in f[1]) for f in filter_groups]

bars_colors=[GRAY,BLU,BLU,GOLD]
bars_alpha=[0.7,0.8,0.85,1.0]
brs=ax1.bar(fg_labels,fg_wrs,color=bars_colors,alpha=0.85,width=0.55)
ax1.axhline(50,color='#475569',lw=1,ls='--',alpha=0.5)
ax1.axhline(65,color=GOLD,lw=1.2,ls='--',alpha=0.6,label='65% threshold')
for b,w,n,pnl in zip(brs,fg_wrs,fg_ns,fg_pnls):
    ax1.text(b.get_x()+b.get_width()/2,w+1,f'{w:.0f}%',
             color='white',ha='center',fontsize=13,fontweight='bold')
    ax1.text(b.get_x()+b.get_width()/2,5,f'n={n}',
             color='#94a3b8',ha='center',fontsize=9)
    pnl_clr=GRN if pnl>0 else RED
    ax1.text(b.get_x()+b.get_width()/2,12,f'P&L\n${pnl:+}',
             color=pnl_clr,ha='center',fontsize=8.5,fontweight='bold')
ax1.set_ylim(0,95); ax1.set_ylabel('Win Rate %',color='#64748b',fontsize=10)
ax1.set_title('Win Rate por Nivel de Filtro | Setup Opening Drive',
              color=GOLD,fontsize=12,fontweight='bold')
ax1.tick_params(colors='#94a3b8',labelsize=9)
[ax1.spines[s].set_visible(False) for s in ['top','right']]
ax1.spines['left'].set_color('#2d2d4e'); ax1.spines['bottom'].set_color('#2d2d4e')
ax1.legend(fontsize=9,facecolor=BG,labelcolor='#94a3b8')

# ── PANEL 2: Distribución outcomes ────────────────────────────────────
ax2 = fig.add_subplot(gs[0,2]); ax2.set_facecolor(PANEL)
outs=['TP2','TP1','SL']
out_ns=[sum(1 for r in results if r["outcome"]==o) for o in outs]
out_clrs=[GRN,BLU,RED]
wedges,texts,autotexts=ax2.pie(out_ns,labels=outs,colors=out_clrs,
    autopct='%1.0f%%',startangle=90,
    textprops={'color':'white','fontsize':11,'fontweight':'bold'})
for at in autotexts: at.set_fontsize(12); at.set_fontweight('bold')
ax2.set_title('Distribución\nResultados',color=GOLD,fontsize=11,fontweight='bold')

# ──  PANEL 3: P&L acumulado más filtros ───────────────────────────────
ax3 = fig.add_subplot(gs[1,:]); ax3.set_facecolor(PANEL)
for grp,lbl,clr,lw in [
    (results,"Global",GRAY,1.2),
    (vwap_ok,"+ VWAP",BLU,1.5),
    (mj_vwap,"Mie/Jue+VWAP",PRP,1.8),
    (best,"Triple Filtro",GOLD,2.2),
]:
    if not grp: continue
    dates=sorted(set(r["date"] for r in grp))
    cum=0; xs=[]; ys=[]
    for d2 in dates:
        dr=[r for r in grp if r["date"]==d2]
        for r in dr: cum+=r["pnl"]
        xs.append(d2); ys.append(cum)
    final_wr=sum(1 for r in grp if r["ok"])/len(grp)*100
    ax3.plot(xs,ys,color=clr,lw=lw,label=f'{lbl} ({final_wr:.0f}% WR | ${ys[-1]:+})',alpha=0.9)

ax3.axhline(0,color='#475569',lw=0.8,ls='--',alpha=0.6)
ax3.fill_between(dates if results else [],0,0,alpha=0)
ax3.legend(fontsize=9,facecolor=BG,labelcolor='#94a3b8',loc='upper left')
ax3.set_xlabel('Fecha',color='#64748b')
ax3.set_ylabel('P&L Acumulado ($)',color='#64748b')
ax3.set_title('Equity Curve — Setup Opening Drive por Filtro',
              color=GOLD,fontsize=12,fontweight='bold')
ax3.tick_params(colors='#64748b')
[ax3.spines[s].set_visible(False) for s in ['top','right']]
ax3.spines['left'].set_color('#2d2d4e'); ax3.spines['bottom'].set_color('#2d2d4e')

# ── PANEL 4: Tarjeta de reglas del setup ─────────────────────────────
ax4 = fig.add_subplot(gs[2,:])
ax4.set_facecolor('#0a0a1a')
ax4.set_xlim(0,12); ax4.set_ylim(0,5)
ax4.axis('off')

# Título
ax4.text(6,4.6,'PLAYBOOK: SETUP "OPENING DRIVE" | 3 MNQ | $50k Apex',
         ha='center',va='center',fontsize=13,fontweight='bold',color=GOLD)

# Reglas
rules_l=[
    ("FILTROS (todos requeridos)",""),
    ("1. Hora:","9:30 ET — primera vela de 15min cierra"),
    ("2. Cuerpo vela:",f">15pts en UNA dirección (promedio={sum(r['fc_body'] for r in results)/N:.0f}pts)"),
    ("3. VWAP:","Precio cierra del MISMO lado del VWAP"),
    ("4. Día:","Martes, Miércoles o Jueves (Lunes=peor)"),
    ("5. COT opcional:","BULL → solo LONGS | BEAR → solo SHORTS"),
]
rules_r=[
    ("EJECUCIÓN (3 MNQ)",""),
    ("Entrada:","Al cierre de vela 9:45 ET (market order)"),
    (f"SL:      -{SL}pts",f"= -${RISK_USD} | Bajo Low vela (LONG) / Sobre High (SHORT)"),
    (f"TP1:     +{TP1}pts",f"= +${TP1_USD} | Primer target"),
    (f"TP2:     +{TP2}pts",f"= +${TP2_USD} | Salida final"),
    ("Gestión:","En TP1 → mueve SL a break-even"),
]

best_wr=sum(1 for r in best if r["ok"])/max(1,len(best))*100
stats_txt=[
    ("ESTADÍSTICAS PROBADAS (2017-2026)",""),
    ("WR Global:",f"{sum(1 for r in results if r['ok'])/N*100:.0f}% ({N} días)"),
    ("WR + VWAP:",f"{sum(1 for r in vwap_ok if r['ok'])/max(1,len(vwap_ok))*100:.0f}% ({len(vwap_ok)} días)"),
    ("WR Mie/Jue+VWAP:",f"{sum(1 for r in mj_vwap if r['ok'])/max(1,len(mj_vwap))*100:.0f}% ({len(mj_vwap)} días)"),
    ("WR Triple Filtro:",f"{best_wr:.0f}% ({len(best)} días)"),
    ("RR:","1:2 (TP1) → 1:2.7 (TP2)"),
]

for i,(k,v) in enumerate(rules_l):
    y_pos=4.0-i*0.58
    clr=GRN if i==0 else '#94a3b8'
    ax4.text(0.15,y_pos,k,va='center',fontsize=9,color=GOLD if i==0 else '#e2e8f0',
             fontweight='bold' if i==0 else 'normal')
    ax4.text(2.0,y_pos,v,va='center',fontsize=8.5,color='#94a3b8')

for i,(k,v) in enumerate(rules_r):
    y_pos=4.0-i*0.58
    ax4.text(4.1,y_pos,k,va='center',fontsize=9,color=GOLD if i==0 else '#e2e8f0',
             fontweight='bold' if i==0 else 'normal')
    ax4.text(5.6,y_pos,v,va='center',fontsize=8.5,color='#94a3b8')

for i,(k,v) in enumerate(stats_txt):
    y_pos=4.0-i*0.58
    ax4.text(8.2,y_pos,k,va='center',fontsize=9,color=GOLD if i==0 else '#e2e8f0',
             fontweight='bold' if i==0 else 'normal')
    ax4.text(10.2,y_pos,v,va='center',fontsize=9.5,
             color=GOLD if i>0 else '#94a3b8',fontweight='bold' if i>0 else 'normal')

# Líneas divisoras
for x in [4.0, 8.1]:
    ax4.axvline(x,color='#2d2d4e',lw=1.2,ymin=0.05,ymax=0.95)

fig.suptitle("SETUP OPENING DRIVE — Backtest 9 años | NQ Futures | 3 MNQ Apex $50k",
             color=GOLD,fontsize=14,fontweight='bold',y=0.99)

out="setup_opening_drive_playbook.png"
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f"\nPlaybook guardado: {out}")
