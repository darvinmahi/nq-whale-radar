"""
ESTUDIO ÚLTIMOS 3 MESES DE LUNES
QQQ diario + VXN + COT local
Muestra: dirección, qué habría funcionado (LONG/SHORT) y por qué
"""
import yfinance as yf, csv, sys
from datetime import date, timedelta
from statistics import mean
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── COT local ─────────────────────────────────────────────────────────────
cot_rows = []
with open('data/cot/nasdaq_cot_historical.csv', encoding='utf-8') as f:
    for r in csv.DictReader(f):
        try:
            d = date.fromisoformat(r['Report_Date_as_MM_DD_YYYY'].strip())
            ll = int(r['Lev_Money_Positions_Long_All'])
            ls = int(r['Lev_Money_Positions_Short_All'])
            cot_rows.append({'date':d,'net':ll-ls})
        except: pass
cot_rows.sort(key=lambda x:x['date'])
for i,r in enumerate(cot_rows):
    hist=[x['net'] for x in cot_rows[max(0,i-52):i+1]]
    mn,mx=min(hist),max(hist)
    r['ci']=(r['net']-mn)/(mx-mn)*100 if mx>mn else 50.0

def get_cot(monday_d):
    prev=[r for r in cot_rows if r['date']<=monday_d-timedelta(days=3)]
    return prev[-1] if prev else None

# ── Descarga QQQ + VXN 3 meses diario ─────────────────────────────────────
print("Descargando datos...")
import pandas as pd
qqq = yf.download('QQQ', period='4mo', interval='1d', auto_adjust=True, progress=False)
vxn = yf.download('^VXN', period='4mo', interval='1d', auto_adjust=True, progress=False)
for df in [qqq, vxn]:
    if hasattr(df.columns,'levels'): df.columns = df.columns.get_level_values(0)

def get_close(df_d, target_date):
    for delta in [0,-1,-2,-3]:
        fd = target_date + timedelta(days=delta)
        m = df_d[df_d.index.date==fd]
        if not m.empty: return round(float(m['Close'].iloc[-1]),2)
    return None

# Solo lunes de los últimos 3 meses
lunes = qqq[qqq.index.weekday==0].copy()
lunes = lunes[lunes.index >= pd.Timestamp.now() - pd.Timedelta(days=95)]

results = []
for idx, row in lunes.iterrows():
    d = idx.date()
    fri = d - timedelta(days=3)

    cot = get_cot(d)
    ci  = round(cot['ci'],1) if cot else 50.0
    vxn_v = get_close(vxn, fri)

    fri_qqq = get_close(qqq, fri)
    gap = round((float(row['Open'])-fri_qqq)/fri_qqq*100,2) if fri_qqq else 0

    mon_ret  = round((float(row['Close'])-float(row['Open']))/float(row['Open'])*100,2)
    day_dir  = '🟢 BULL' if mon_ret>0.15 else ('🔴 BEAR' if mon_ret<-0.15 else '⚪ FLAT')
    mejor    = 'LONG ✅' if mon_ret>0 else 'SHORT ✅'

    # Señal de nuestro modelo (VXN+COT)
    if vxn_v and vxn_v < 25 and ci > 50:
        señal = 'LONG 🟢'
        señal_acertó = mon_ret > 0
    elif vxn_v and vxn_v > 28 and ci < 55:
        señal = 'EVITAR/SHORT 🔴'
        señal_acertó = mon_ret <= 0
    else:
        señal = 'NEUTRAL 🟡'
        señal_acertó = None

    results.append({
        'd': d, 'ci': ci, 'vxn': vxn_v,
        'gap': gap, 'ret': mon_ret,
        'dir': day_dir, 'mejor': mejor,
        'señal': señal, 'ok': señal_acertó,
    })

print(f"\n{'='*78}")
print(f"  ÚLTIMOS {len(results)} LUNES (3 meses) — QQQ + COT + VXN")
print(f"{'='*78}")
print(f"\n  {'Fecha':<12} {'COT%':>6} {'VXN':>5} {'Gap%':>6} {'Ret lunes':>10}  {'Señal modelo':>18}  {'Acierto':>8}")
print("  "+"-"*72)

aciertos = []
for r in results:
    ok_str = ''
    if r['ok'] is True:   ok_str = '✅ OK'
    elif r['ok'] is False: ok_str = '❌ FALLO'
    else:                 ok_str = '⚪ N/A'
    if r['ok'] is not None: aciertos.append(r['ok'])

    vxn_str = f"{r['vxn']:.1f}" if r['vxn'] else 'N/A'
    print(f"  {str(r['d']):<12} {r['ci']:>5.1f}% {vxn_str:>5} {r['gap']:>+5.2f}% "
          f"  {r['ret']:>+6.2f}% {r['dir']:<10}  {r['señal']:<18}  {ok_str}")

print(f"\n{'='*78}")
pos = sum(1 for r in results if r['ret']>0)
neg = sum(1 for r in results if r['ret']<=0)
acum = sum(r['ret'] for r in results)
avg  = mean(r['ret'] for r in results)

print(f"\n  📊 RESUMEN:")
print(f"     Lunes BULL: {pos}/{len(results)} = {pos/len(results)*100:.0f}%")
print(f"     Lunes BEAR: {neg}/{len(results)} = {neg/len(results)*100:.0f}%")
print(f"     Ret acumulado si compras TODOS: {acum:+.2f}%  avg: {avg:+.2f}%")
if aciertos:
    pct = sum(aciertos)/len(aciertos)*100
    print(f"\n  🎯 MODELO VXN+COT acertó: {sum(aciertos)}/{len(aciertos)} = {pct:.0f}%")

# Patrón VXN
print(f"\n  📊 POR ZONA VXN:")
for lo,hi,label in [(0,22,'VXN <22 (Calma)'),(22,27,'VXN 22-27 (Normal)'),(27,35,'VXN >27 (Miedo)'),(35,99,'VXN >35 (Pánico)')]:
    grp=[r for r in results if r['vxn'] and lo<=r['vxn']<hi]
    if not grp: continue
    bp=sum(1 for r in grp if r['ret']>0)
    av=mean(r['ret'] for r in grp)
    print(f"     {label:<22}: {bp}/{len(grp)} BULL = {bp/len(grp)*100:.0f}%  avg={av:+.2f}%")

print(f"{'='*78}\n")
