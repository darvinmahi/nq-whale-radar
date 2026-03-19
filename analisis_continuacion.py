import yfinance as yf
import pandas as pd
import numpy as np

print("="*80)
print("📌 ANÁLISIS DE CONTINUACIÓN: ¿QUÉ PASA CUANDO LONDRES NO ROMPE ASIA? 📌")
print("="*80)

# 1. Bajar datos de 1 minuto y diarios macro
raw_5m = yf.download("NQ=F", period="60d", interval="5m", progress=False)
if isinstance(raw_5m.columns, pd.MultiIndex):
    raw_5m.columns = raw_5m.columns.get_level_values(0)
raw_5m.index = raw_5m.index.tz_convert('America/New_York')

raw_daily = yf.download(["NQ=F", "^VXN"], period="300d", interval="1d", progress=False)
if isinstance(raw_daily.columns, pd.MultiIndex):
    nq_close = raw_daily['Close']['NQ=F']
else:
    nq_close = raw_daily['Close']

if nq_close.index.tz is None: nq_close.index = nq_close.index.tz_localize('UTC')
nq_close.index = nq_close.index.tz_convert('America/New_York')

# 2. Calcular EMA200
ema200 = nq_close.ewm(span=200, adjust=False).mean()
ema_map = {d.date(): float(v) for d, v in ema200.items()}
nq_close_map = {d.date(): float(v) for d, v in nq_close.items()}

raw_5m['hour'] = raw_5m.index.hour
raw_5m['minute'] = raw_5m.index.minute
raw_5m['date'] = raw_5m.index.date
raw_5m['volume'] = raw_5m['Volume'].fillna(1).replace(0, 1)

def calc_profile(sdf, n_bins=40, pct=0.70):
    if len(sdf) < 2: return None, None, None
    lo, hi = float(sdf['Low'].min()), float(sdf['High'].max())
    if hi <= lo: return (hi+lo)/2, hi, lo
    bins = np.linspace(lo, hi, n_bins+1)
    vb = np.zeros(n_bins)
    for _, r in sdf.iterrows():
        rlo, rhi, rv = float(r['Low']), float(r['High']), float(r['volume'])
        rng = rhi - rlo if rhi > rlo else 1e-9
        for b in range(n_bins):
            ov = min(rhi, bins[b+1]) - max(rlo, bins[b])
            if ov > 0: vb[b] += rv*(ov/rng)
    tot = vb.sum()
    if tot == 0: return (hi+lo)/2, hi, lo
    pi = int(np.argmax(vb)); poc = (bins[pi]+bins[pi+1])/2
    acc = vb[pi]; hi_i, lo_i = pi, pi
    while acc < tot*pct:
        cu = hi_i+1 < n_bins; cd = lo_i-1 >= 0
        if not cu and not cd: break
        vu = vb[hi_i+1] if cu else -1
        vd = vb[lo_i-1] if cd else -1
        if vu >= vd: hi_i+=1; acc+=vu
        else:        lo_i-=1; acc+=vd
    return poc, bins[hi_i+1], bins[lo_i]

fechas = sorted(raw_5m['date'].unique())

dias_respetados = 0
continuacion_ema = 0
falla_ema = 0

resultados_no_sweep = []

for d in fechas:
    day = raw_5m[raw_5m['date'] == d]
    
    asia = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    ny = day[(day['hour'] >= 9) & (day['hour'] < 16)]
    
    if asia.empty or london.empty or ny.empty: continue
        
    asia_hi, asia_lo = float(asia['High'].max()), float(asia['Low'].min())
    lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
    
    swept_hi = lon_hi > asia_hi
    swept_lo = lon_lo < asia_lo
    
    # BUSCAMOS EXACTAMENTE LOS DÍAS DONDE LONDRES SE QUEDÓ DENTRO DEL RANGO DE ASIA
    if not swept_hi and not swept_lo:
        dias_respetados += 1
        
        ny_close, ny_high, ny_low = float(ny.iloc[-1]['Close']), float(ny['High'].max()), float(ny['Low'].min())
        
        try:
            idx_prev = list(nq_close_map.keys()).index(d) - 1
            if idx_prev < 0: continue
            d_prev = list(nq_close_map.keys())[idx_prev]
            ema_val = ema_map.get(d_prev, 0)
            close_prev = nq_close_map.get(d_prev, 0)
            tendencia_diaria = "ALCISTA" if close_prev > ema_val else "BAJISTA"
        except ValueError:
            continue
            
        # Calcular Volume Profile solo de Asia
        asia_poc, asia_vah, asia_val = calc_profile(asia)
        
        # ¿Qué hizo NY al abrir (9:30 a 11)?
        sb = day[((day['hour'] == 9) & (day['minute'] >= 30)) | (day['hour'] == 10) | ((day['hour'] == 11) & (day['minute'] == 0))]
        if sb.empty: continue
        
        sb_close = float(sb.iloc[-1]['Close'])
        precio_apertura_ny = float(sb.iloc[0]['Open'])
        
        # Evaluar continuación basado en la EMA
        # Si la tendencia es alcista, ¿NY terminó más alto de lo que abrió en el SB?
        movimiento_ny = "SUBIO" if sb_close > precio_apertura_ny else "BAJO"
        
        if (tendencia_diaria == "ALCISTA" and movimiento_ny == "SUBIO") or (tendencia_diaria == "BAJISTA" and movimiento_ny == "BAJO"):
            resultado = "✅ CONTINUACIÓN EXITOSA"
            continuacion_ema += 1
        else:
            resultado = "❌ REVERSIÓN / FALLA"
            falla_ema += 1
            
        # Evaluar testeo del POC de Asia
        sb_low = float(sb['Low'].min())
        sb_high = float(sb['High'].max())
        toco_poc = "SÍ" if (sb_low <= asia_poc <= sb_high) else "NO"
            
        resultados_no_sweep.append({
            'Fecha': d,
            'Tendencia (EMA)': tendencia_diaria,
            'Movimiento en NY': movimiento_ny,
            'Acertó EMA?': resultado,
            'Tocó POC/Volumen Asia?': toco_poc
        })

df_res = pd.DataFrame(resultados_no_sweep)

print(f"Total días analizados: {len(fechas)}")
print(f"Días 'Inside Day' (Londres NO rompió Asia): {dias_respetados} días")

if dias_respetados > 0:
    print("\nDetalle de los días donde se respetó el rango (No Sweep):")
    for i, r in df_res.iterrows():
        print(f"👉 {r['Fecha']} | Tendencia: {r['Tendencia (EMA)']:<7} | NY: {r['Movimiento en NY']:<5} | Testeó POC Asia: {r['Tocó POC/Volumen Asia?']} | {r['Acertó EMA?']}")

    print("\n" + "="*80)
    print("💡 CONCLUSIÓN: ¿CÓMO SABER SI EL PRECIO CONTINÚA?")
    win_rate_ema = (continuacion_ema / dias_respetados) * 100
    tocaron_poc = len(df_res[df_res['Tocó POC/Volumen Asia?'] == 'SÍ'])
    pct_poc = (tocaron_poc / dias_respetados) * 100
    
    print(f"1. Si no hay cacería de stops (sweep), la EMA200 dictó si NY subía o bajaba en el {win_rate_ema:.1f}% de los casos.")
    print(f"2. En el {pct_poc:.1f}% de esos días 'quietos', New York bajó a probar el POC (nivel central de volumen) de Asia antes de arrancar.")
    print("\n👉 REGLA DE CONTINUACIÓN:")
    print("   Si llegas a las 9:30am y Londres no rompió ni el alto ni el bajo de Asia,")
    print("   colocas tu orden Límite a favor de la EMA 200, directamente en el POC / VAL de Asia.")
    
print("="*80)
