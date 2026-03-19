"""
VERIFICACIÓN DE REGLAS "NO HACER" — ICT Backtest
=================================================
Lee los trades ya calculados y muestra los números exactos
detrás de cada regla de eliminación.
"""
import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE_DIR, "ict_pure_trades.csv")

df = pd.read_csv(CSV)
df = df[df['result'].isin(['WIN', 'LOSS'])]  # Solo trades cerrados

def wr(sub, label=""):
    if len(sub) == 0:
        return f"  {label}: SIN DATOS"
    w = len(sub[sub['result'] == 'WIN'])
    n = len(sub)
    avg = sub['pnl_pts'].mean()
    return f"  {label:<50} WR: {w/n*100:5.1f}%  | n={n:3d} | Avg PnL: {avg:+6.1f} pts"

print("="*70)
print("  VERIFICACIÓN BACKTESTING — REGLAS DE NO OPERAR")
print("="*70)

# ── REGLA 1: Lunes SELL ───────────────────────────────────────────────────
print("\n📌 REGLA 1: NO operar SELL en Lunes")
print("-"*70)
print(wr(df[(df['day_name']=='Lunes') & (df['direction']=='SELL')],
         "SELL en Lunes (EVITAR)"))
print(wr(df[(df['day_name']=='Lunes') & (df['direction']=='BUY')],
         "BUY  en Lunes (Alternativa)"))

# ── REGLA 2: En Contra de Tendencia ──────────────────────────────────────
print("\n📌 REGLA 2: NO operar EN CONTRA de la tendencia")
print("-"*70)
print(wr(df[df['with_trend']==False], "EN CONTRA de tendencia (EVITAR)"))
print(wr(df[df['with_trend']==True],  "A FAVOR de tendencia  (Operar)"))

# ── REGLA 3: BUY en Martes ────────────────────────────────────────────────
print("\n📌 REGLA 3: BUY en Martes tiene WR bajo")
print("-"*70)
print(wr(df[(df['day_name']=='Martes') & (df['direction']=='BUY')],
         "BUY en Martes (EVITAR)"))
print(wr(df[(df['day_name']=='Martes') & (df['direction']=='SELL')],
         "SELL en Martes (OK)"))

# ── REGLA 4: BUY en DOWNTREND ────────────────────────────────────────────
print("\n📌 REGLA 4: NO BUY cuando el mercado está en DOWNTREND")
print("-"*70)
print(wr(df[(df['direction']=='BUY')  & (df['trend']=='DOWNTREND')],
         "BUY  en DOWNTREND (EVITAR)"))
print(wr(df[(df['direction']=='BUY')  & (df['trend']=='UPTREND')],
         "BUY  en UPTREND   (OK)"))
print(wr(df[(df['direction']=='SELL') & (df['trend']=='DOWNTREND')],
         "SELL en DOWNTREND (OK)"))

# ── TABLA COMPLETA POR DÍA ────────────────────────────────────────────────
print("\n📌 TABLA COMPLETA — WR por Día + Dirección")
print("-"*70)
print(f"  {'Día':<12} {'Dirección':<8} {'Wins':>5} {'Total':>6} {'WR':>7} {'Avg PnL':>9}")
print("  " + "-"*55)
for day in ["Lunes","Martes","Miércoles","Jueves","Viernes"]:
    for direction in ["BUY","SELL"]:
        sub = df[(df['day_name']==day) & (df['direction']==direction)]
        if len(sub) == 0: continue
        w = len(sub[sub['result']=='WIN'])
        n = len(sub)
        avg = sub['pnl_pts'].mean()
        flag = " ⚠️ " if w/n < 0.35 else (" ✅" if w/n >= 0.60 else "")
        print(f"  {day:<12} {direction:<8} {w:>5} {n:>6} {w/n*100:>6.1f}%  {avg:>+8.1f}{flag}")

# ── IMPACTO DE APLICAR LOS FILTROS ───────────────────────────────────────
print("\n📌 IMPACTO DE APLICAR LOS 3 FILTROS")
print("-"*70)
todos = df
filtrado = df[
    ~((df['day_name']=='Lunes')   & (df['direction']=='SELL')) &
    ~((df['day_name']=='Martes')  & (df['direction']=='BUY'))  &
    (df['with_trend'] == True)
]
print(wr(todos,    "SIN filtros (todos los trades)"))
print(wr(filtrado, "CON los 3 filtros aplicados  "))
eliminados = len(todos) - len(filtrado)
print(f"\n  Trades eliminados: {eliminados} de {len(todos)} ({eliminados/len(todos)*100:.1f}%)")
print(f"  Trades restantes:  {len(filtrado)}")
