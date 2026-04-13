"""
weekly_plan_apr7.py — Plan semanal 7-11 Abril 2026
COT: BULL (AM+7133 | LEV 35.3%)
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.gridspec as gridspec

BG='#0a0a16'; PANEL='#0f0f1e'; PANEL2='#131325'
GRN='#10b981'; RED='#ef4444'; GOLD='#f59e0b'
BLU='#60a5fa'; PRP='#a78bfa'; GRAY='#334155'
WHITE='#f1f5f9'; DIM='#64748b'; SOFT='#94a3b8'

def R(ax, x, y, w, h, fc, ec, lw=1.5, style="round,pad=0.1"):
    """Draw FancyBboxPatch — compatible con matplotlib 3.10+"""
    ax.add_patch(patches.FancyBboxPatch((x, y), w, h,
        boxstyle=style, facecolor=fc, edgecolor=ec, linewidth=lw))

fig = plt.figure(figsize=(24, 18), facecolor=BG)
fig.suptitle("PLAN DE TRADING SEMANAL  ▸  7-11 Abril 2026  ▸  NQ (MNQ)  ▸  Apex $50k",
             color=GOLD, fontsize=15, fontweight='bold', y=0.99)
gs = gridspec.GridSpec(3, 4, figure=fig, hspace=0.52, wspace=0.32,
                       left=0.03, right=0.98, top=0.95, bottom=0.03)

# ═══════════════════════════════════════════════════
# 1. COT SESGO (top left 2 cols)
# ═══════════════════════════════════════════════════
ac = fig.add_subplot(gs[0, :2]); ac.set_facecolor(PANEL2)
ac.set_xlim(0,10); ac.set_ylim(0,4); ac.axis('off')

R(ac, 0.1,3.3, 9.8,0.55, '#1e293b', GOLD)
ac.text(5,3.58,'COT INSTITUCIONAL — SEMANA 7-11 ABR 2026',ha='center',va='center',fontsize=11,fontweight='bold',color=GOLD)

R(ac, 0.2,1.85, 4.4,1.25, '#0d2010', GRN)
ac.text(2.4,2.95,'ASSET MANAGERS',ha='center',fontsize=10,fontweight='bold',color=GRN)
ac.text(2.4,2.55,'Net Position: +58,591',ha='center',fontsize=12,fontweight='bold',color=WHITE)
ac.text(2.4,2.18,'Delta semana: +7,133 ↑',ha='center',fontsize=11,color=GRN,fontweight='bold')
ac.text(2.4,1.95,'Comprando fuerte',ha='center',fontsize=9,color=GRN,style='italic')

R(ac, 4.8,1.85, 5.05,1.25, '#0d2010', GRN)
ac.text(7.35,2.95,'LEVERAGED MONEY',ha='center',fontsize=10,fontweight='bold',color=SOFT)
ac.text(7.35,2.55,'Net Pos: -41,577',ha='center',fontsize=12,fontweight='bold',color=WHITE)
ac.text(7.35,2.18,'Percentil 35.3% — Zona BAJA',ha='center',fontsize=11,color=GRN,fontweight='bold')
ac.text(7.35,1.95,'Fondos cortos en extremo → reversión alcista',ha='center',fontsize=9,color=GRN,style='italic')

R(ac, 1.5,0.15, 7.0,1.45, '#0a2010', GRN, lw=2.5)
ac.text(5,1.3,'✦  SESGO COT:  BULL  ✦  SOLO LONGS ESTA SEMANA',ha='center',va='center',fontsize=13,fontweight='bold',color=GRN)
ac.text(5,0.85,'AM comprando +7,133 | LEV en mínimos (35%) = Confluencia institucional alcista',ha='center',va='center',fontsize=9,color=SOFT)
ac.text(5,0.45,'Prioridad: filtrar LONGS en Miércoles y Jueves')
ac.texts[-1].set_color(GOLD); ac.texts[-1].set_fontsize(10); ac.texts[-1].set_fontweight('bold')

# ═══════════════════════════════════════════════════
# 2. RIESGO (top right 2 cols)
# ═══════════════════════════════════════════════════
ar = fig.add_subplot(gs[0, 2:]); ar.set_facecolor(PANEL2)
ar.set_xlim(0,10); ar.set_ylim(0,4); ar.axis('off')

R(ar, 0.1,3.3, 9.8,0.55, '#1e293b', BLU)
ar.text(5,3.58,'GESTIÓN DE RIESGO — APEX $50,000',ha='center',va='center',fontsize=11,fontweight='bold',color=BLU)

rows_r = [
    ("Instrumento:",  "MNQ (Micro NQ Futures)  |  1 pt = $2",    WHITE),
    ("Contratos:",    "3 MNQ base  →  escalar a 4 en setups A+",  GRN),
    ("SL:",           "25 pts = $150/trade",                       RED),
    ("TP1:",          "50 pts = $300  →  mover SL a BE",           GRN),
    ("TP2:",          "67 pts = $402  →  salida total",            GRN),
    ("RR:",           "1:2.0 (TP1)  →  1:2.7 (TP2)",             GOLD),
    ("Max trades/día:","2 trades máximo",                          GOLD),
    ("Stop diario:",  "-$300 (2× SL)  →  PARAR",                  RED),
    ("Stop semanal:", "-$600 total  →  PARAR",                     RED),
    ("Goal semana:",  "+$500 mínimo  |  +$900 ideal",              GRN),
]
for i,(k,v,c) in enumerate(rows_r):
    y=2.95-i*0.293
    ar.text(0.3,y,k,fontsize=9,color=DIM,va='center')
    ar.text(3.8,y,v,fontsize=9,color=c,fontweight='bold',va='center')
    ar.plot([0.2,9.8],[y-0.12,y-0.12],color='#1e293b',lw=0.5)

# ═══════════════════════════════════════════════════
# 3. DÍAS (fila media — 4 paneles de Lunes a Jueves)
# ═══════════════════════════════════════════════════
days = [
    {"n":"LUNES 7 ABR",    "b":"⚠ CUIDADO — WR 54%","bc":GOLD,"bg":'#1a1a2e',"ec":GRAY,
     "sesgo":"BULL — Ruido alto","pri":"OPCIONAL — 1 trade máx",
     "pclr":GRAY,
     "setup":"Opening Drive 9:30",
     "desc":["- Primera vela verde >15pts","- Precio BAJO VWAP (contra-VWAP)","- Entry: Break High primera vela","- SL: 25pts | TP1: 50pts"],
     "notas":[("⚠",GOLD," Día MÁS RUIDOSO de la semana"),("✗",RED," COT no se expresa el lunes"),("✓",GRN," Gap bajista → busca reclaim VWAP"),("→",BLU," Máx 1 trade si todo confirma")]},
    {"n":"MARTES 8 ABR",   "b":"NORMAL — WR 55%","bc":BLU,"bg":'#101020',"ec":BLU,
     "sesgo":"BULL activándose","pri":"MEDIA — 2 trades",
     "pclr":BLU,
     "setup":"VWAP Reclaim + London",
     "desc":["- Precio bajo VWAP tras apertura","- Reclaim VWAP 9:45-10:30","- London High confirmado en NY","- SL: Low vela entrada"],
     "notas":[("✓",GRN," Sesgo BULL empieza a activarse"),("✓",GRN," VWAP Reclaim funciona bien"),("✗",RED," Evitar shorts — contra COT BULL"),("→",BLU," 2 trades máx con full SL")]},
    {"n":"MIÉRCOLES 9 ABR","b":"★ MEJOR DÍA — WR 63%","bc":GRN,"bg":'#0d2010',"ec":GRN,
     "sesgo":"BULL FUERTE","pri":"ALTA — FOCO PRINCIPAL",
     "pclr":GRN,
     "setup":"Opening Drive + FVG",
     "desc":["- Primera vela verde >15pts","- FVG premarket → retorno al mid","- VWAP opuesto (contra-VWAP)","- COT BULL: solo LONGS · 3-4 MNQ"],
     "notas":[("★",GOLD," Mejor WR 63% — COT+Mie=76%"),("✓",GRN," DOS setups posibles el mismo día"),("✓",GRN," Aprovechar tamaño completo 3 MNQ"),("→",BLU," Aplicar trailing en TP1")]},
    {"n":"JUEVES 10 ABR",  "b":"★ FOCO — WR 62%","bc":GRN,"bg":'#0d2010',"ec":GRN,
     "sesgo":"BULL consolidación","pri":"ALTA — FOCO SECUNDARIO",
     "pclr":GRN,
     "setup":"ORB Breakout + VWAP",
     "desc":["- ORB 9:30 rango <30pts ideal","- Breakout con VWAP del lado","- Pullback 50% ORB → re-entry","- Escalar a 4 MNQ si Mie fue OK"],
     "notas":[("★",GOLD," Segundo mejor día 62% WR"),("✓",GRN," Continuación del move del Mie"),("✓",GRN," ORB pequeño <30pts = mejor WR"),("→",BLU," Considerar 4 MNQ si equity OK")]},
]

for col,dc in enumerate(days):
    ax = fig.add_subplot(gs[1,col]); ax.set_facecolor(dc["bg"])
    ax.set_xlim(0,10); ax.set_ylim(0,8); ax.axis('off')

    R(ax, 0.1,7.1, 9.8,0.75, '#0f0f20', dc["ec"], lw=2)
    ax.text(5,7.68,dc["n"],ha='center',va='center',fontsize=10,fontweight='bold',color=WHITE)
    ax.text(5,7.28,dc["b"],ha='center',va='center',fontsize=9,fontweight='bold',color=dc["bc"])

    R(ax, 0.15,6.3, 5.0,0.62, '#1e293b', dc["ec"])
    ax.text(2.65,6.62,dc["sesgo"],ha='center',va='center',fontsize=8.5,color=GOLD,fontweight='bold')
    R(ax, 5.35,6.3, 4.5,0.62, '#1e293b', GOLD)
    ax.text(7.6,6.62,f'Setup: {dc["setup"]}',ha='center',va='center',fontsize=8,color=BLU,fontweight='bold')

    ax.plot([0.2,9.8],[6.18,6.18],color='#2d2d4e',lw=0.6)
    ax.text(0.3,5.95,'Condiciones:',fontsize=9,color=GOLD,fontweight='bold')
    for i,line in enumerate(dc["desc"]):
        ax.text(0.3,5.52-i*0.52,line,fontsize=8,color=SOFT)

    ax.plot([0.2,9.8],[3.45,3.45],color='#2d2d4e',lw=0.6)
    ax.text(0.3,3.25,'Notas:',fontsize=9,color=GOLD,fontweight='bold')
    for i,(sym,c,txt) in enumerate(dc["notas"]):
        ax.text(0.3,2.82-i*0.55,sym,fontsize=10,color=c,fontweight='bold')
        ax.text(0.85,2.82-i*0.55,txt,fontsize=8,color=SOFT)

    R(ax, 0.2,0.1, 9.6,0.68, '#0a0a16', dc["pclr"])
    ax.text(5,0.44,f'Prioridad: {dc["pri"]}',ha='center',va='center',fontsize=8.5,fontweight='bold',color=dc["pclr"])

# ═══════════════════════════════════════════════════
# 4. VIERNES (gs[2,:1])
# ═══════════════════════════════════════════════════
af = fig.add_subplot(gs[2, 0]); af.set_facecolor('#1f1010')
af.set_xlim(0,10); af.set_ylim(0,8); af.axis('off')
R(af, 0.1,7.1, 9.8,0.75, '#0f0f20', RED, lw=2)
af.text(5,7.68,'VIERNES 11 ABR',ha='center',va='center',fontsize=10,fontweight='bold',color=WHITE)
af.text(5,7.28,'⛔ NO OPERAR — WR histórico bajo',ha='center',va='center',fontsize=9,fontweight='bold',color=RED)
vlines = [
    (RED,"✗ WR histórico viernes < 25%"),
    (RED,"✗ Profit taking institucional"),
    (RED,"✗ Volatilidad errática, reversiones"),
    (GRN,"✓ Proteger P&L ganado Mie/Jue"),
    (GOLD,"→ SOLO analizar y tomar notas"),
    (GOLD,"→ Revisar COT del viernes a las 3:30pm"),
]
for i,(c,t) in enumerate(vlines):
    af.text(0.5,5.9-i*0.72,t,fontsize=9,color=c,fontweight='bold')
R(af, 0.2,0.1, 9.6,0.68, '#1a0000', RED)
af.text(5,0.44,'⛔ NO OPERAR — DESCANSO',ha='center',va='center',fontsize=9,fontweight='bold',color=RED)

# ═══════════════════════════════════════════════════
# 5. CHECKLIST (gs[2, 1:])
# ═══════════════════════════════════════════════════
ach = fig.add_subplot(gs[2, 1:]); ach.set_facecolor(PANEL2)
ach.set_xlim(0,18); ach.set_ylim(0,8); ach.axis('off')

R(ach, 0.1,7.15, 17.8,0.6, '#1e293b', PRP)
ach.text(9,7.46,'CHECKLIST DIARIO — Antes de cada trade esta semana',ha='center',va='center',fontsize=12,fontweight='bold',color=PRP)

c1 = [("ANTES DE ENTRAR",""),
      ("☐ 1.","COT semana = BULL → solo LONGS"),
      ("☐ 2.","Primera vela 9:30 cerró VERDE >15pts"),
      ("☐ 3.","Precio cierra CONTRA el VWAP (bajo VWAP en vela alcista)"),
      ("☐ 4.","Día: Martes, Miércoles o Jueves"),
      ("☐ 5.","Sin noticias de alto impacto (CPI, FOMC, NFP)"),
      ("☐ 6.","No has perdido ya 2 trades hoy"),
]
c2 = [("EJECUCIÓN 3 MNQ",""),
      ("Entry:","Market order al CIERRE de primera vela (9:45 ET)"),
      ("SL:","25 pts fijo desde entrada (-$150)"),
      ("TP1:","50 pts → mover SL a break-even (+$300)"),
      ("TP2:","67 pts → salida total (+$402)"),
      ("Tiempo:","Si no mueve en 60 min → cerrar manual"),
      ("Escalar:","4 MNQ si Mie confirmó y equity +$200"),
]
c3 = [("REGLAS STOP",""),
      ("🔴 Diario:","Si pierdes 2 SL seguidos → PARA el día"),
      ("🔴 Loss max:","$300 máx pérdida diaria"),
      ("🔴 Semanal:","$600 máx pérdida semanal"),
      ("🟢 Goal día:","$300 mínimo (1 TP1 hit)"),
      ("🟢 Goal sem:","$500-$900 (2-3 wins Mie/Jue)"),
      ("★ Recordar:","Mie+Jue = 62-63% WR → son TUS días"),
]

for ci,col in enumerate([c1,c2,c3]):
    xb = ci*6.0 + 0.3
    for j,(k,v) in enumerate(col):
        y = 6.6-j*0.82
        if j==0:
            ach.text(xb,y,k,fontsize=11,fontweight='bold',color=GOLD)
        else:
            ck = GRN if '☐' in k or '🟢' in k or 'Entry' in k or 'Escalar' in k or 'Goal' in k or '★' in k else (RED if '🔴' in k else BLU)
            ach.text(xb,y,k,fontsize=9.5,color=ck,fontweight='bold')
            ach.text(xb+1.6,y,v,fontsize=9,color=SOFT)
    if ci<2:
        ach.axvline(6.0*(ci+1),color='#2d2d4e',lw=1,ymin=0.05,ymax=0.95)

out="weekly_plan_apr7_2026.png"
plt.savefig(out,dpi=130,bbox_inches='tight',facecolor=BG)
plt.close()
print(f"Plan guardado: {out}")
