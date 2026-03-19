import yfinance as yf
import pandas as pd
import numpy as np

print("="*70)
print("📊 PLAY-BY-PLAY: ESTA SEMANA (SOLO PROFILE + EMA200) 📊")
print("   (Ignorando las reglas de días de la semana)")
print("="*70)

# Datos diarios para EMA200
ndx_d = yf.download("NQ=F", period="300d", interval="1d", progress=False)
if isinstance(ndx_d.columns, pd.MultiIndex):
    ndx_d.columns = ndx_d.columns.get_level_values(0)
ndx_d.index = pd.to_datetime(ndx_d.index)
if ndx_d.index.tz is None:
    ndx_d.index = ndx_d.index.tz_localize('UTC')
ndx_d.index = ndx_d.index.tz_convert('America/New_York')
ndx_d['EMA200'] = ndx_d['Close'].ewm(span=200, adjust=False).mean()
ema_map = {d.date(): float(v) for d, v in ndx_d['EMA200'].items()}

# Datos 1 minuto (ultimos 7 dias)
raw = yf.download("NQ=F", period="7d", interval="1m", progress=False)
if isinstance(raw.columns, pd.MultiIndex):
    raw.columns = raw.columns.get_level_values(0)
raw.index = raw.index.tz_convert('America/New_York')
raw['hour'] = raw.index.hour
raw['minute'] = raw.index.minute
raw['date'] = raw.index.date
raw['weekday'] = raw.index.dayofweek
raw['volume'] = raw['Volume'].fillna(1).replace(0, 1)

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

DAYS = {0:"Lunes", 1:"Martes", 2:"Miércoles", 3:"Jueves", 4:"Viernes"}

dates = sorted(raw['date'].unique())
for d in dates:
    day = raw[raw['date'] == d]
    wd = int(day['weekday'].iloc[0])
    if wd not in DAYS: continue
    
    print(f"\n{'-'*70}")
    print(f"🗓️  {DAYS[wd].upper()} {d}")
    print(f"{'-'*70}")
    
    ema = ema_map.get(d, 0)
    precio_actual = float(day['Close'].iloc[0])
    tendencia_alcista = precio_actual > ema
    
    asia = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    
    if asia.empty or london.empty:
        print("   ❌ Datos insuficientes para Asia/Londres aún.")
        continue
        
    asia_hi, asia_lo = float(asia['High'].max()), float(asia['Low'].min())
    lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
    
    swept_lo = lon_lo < asia_lo
    swept_hi = lon_hi > asia_hi
    
    print(f"   [MERCADO] Precio: {precio_actual:.0f} | EMA200: {ema:.0f} -> Tendencia: {'ALCISTA' if tendencia_alcista else 'BAJISTA'}")
    print(f"   [ASIA] Rango: {asia_lo:.1f} a {asia_hi:.1f}")
    
    setup = None
    if swept_hi and not swept_lo:
        print(f"   [LONDRES] ⬆️ Rompió HIGH de Asia (subió a {lon_hi:.1f}) -> TRAMPA ALCISTA ➡️ Buscamos SELL")
        setup = "SELL"
    elif swept_lo and not swept_hi:
        print(f"   [LONDRES] ⬇️ Rompió LOW de Asia (bajó a {lon_lo:.1f}) -> TRAMPA BAJISTA ➡️ Buscamos BUY")
        setup = "BUY"
    elif swept_hi and swept_lo:
        print(f"   [LONDRES] ↕️ Rompió AMBOS lados -> Rango expandido")
        setup = None
    else:
        print(f"   [LONDRES] ➖ No rompió el rango de Asia")
        setup = None
        
    if setup is None:
        continue
        
    # Validar SÓLO EMA200 (sin reglas de día de semana)
    valido = False
    razon = ""
    
    if setup == "BUY":
        if tendencia_alcista:
            valido = True
        else:
            razon = "El mercado está BAJO la EMA200, no es seguro COMPRAR (tendencia bajista macro)."
    else: # SELL
        if not tendencia_alcista:
            valido = True
        else:
            razon = "El mercado está MÁS ARRIBA de la EMA200, no es seguro VENDER (tendencia alcista fuerte)."
            
    if not valido:
        print(f"   ⚠️ SEÑAL RECHAZADA: {razon}")
        continue
        
    # Si es válido por EMA, calculamos Profile y ponemos orden
    idx_vp = day[(day['hour'] >= 0) & (day['hour'] < 9)]
    poc, vah, val = calc_profile(idx_vp)
    print(f"   [VOLUME PROFILE 12am-9am] VAL: {val:.1f} | POC: {poc:.1f} | VAH: {vah:.1f}")
    
    if setup == "BUY":
        entry = val
        target = vah
        stop = lon_lo - 2
        print(f"   🟢 ORDEN: BUY LIMIT en {entry:.1f} | SL: {stop:.1f} | TP: {target:.1f}")
    else:
        entry = vah
        target = val
        stop = lon_hi + 2
        print(f"   🔴 ORDEN: SELL LIMIT en {entry:.1f} | SL: {stop:.1f} | TP: {target:.1f}")
        
    # Check Silver bullet window 9:30 a 11:00
    sb = day[((day['hour'] == 9) & (day['minute'] >= 30)) | (day['hour'] == 10) | ((day['hour'] == 11) & (day['minute'] == 0))]
    
    if sb.empty:
        continue
        
    entered = False
    result = "NO ENTRY"
    pnl = 0
    t_entry = ""
    
    for i, r in sb.iterrows():
        hi, lo = float(r['High']), float(r['Low'])
        t = f"{int(r['hour']):02d}:{int(r['minute']):02d}"
        
        if not entered:
            if (setup == "BUY" and lo <= entry) or (setup == "SELL" and hi >= entry):
                entered = True
                t_entry = t
                print(f"   ✅ [ {t} ] ORDEN ACTIVADA - Entramos en {entry:.1f}")
                
        if entered:
            if setup == "BUY":
                if lo <= stop:
                    result = "LOSS"
                    print(f"   💥 [ {t} ] STOP LOSS TOCADO en {stop:.1f}")
                    pnl = stop - entry
                    break
                if hi >= target:
                    result = "WIN"
                    print(f"   🏆 [ {t} ] TARGET ALCANZADO en {target:.1f}")
                    pnl = target - entry
                    break
            else: # SELL
                if hi >= stop:
                    result = "LOSS"
                    print(f"   💥 [ {t} ] STOP LOSS TOCADO en {stop:.1f}")
                    pnl = entry - stop
                    break
                if lo <= target:
                    result = "WIN"
                    print(f"   🏆 [ {t} ] TARGET ALCANZADO en {target:.1f}")
                    pnl = entry - target
                    break
    
    if not entered:
        print("   ⏳ Oportunidad perdida: precio no regresó a nuestro nivel (VAL/VAH).")
    elif result not in ["WIN", "LOSS"]:
        close_px = float(sb.iloc[-1]['Close'])
        print(f"   ⏰ [ 11:00 ] Cierre por tiempo. Saliendo en {close_px:.1f}")
        pnl = (close_px - entry) if setup == "BUY" else (entry - close_px)
        
    if pnl != 0:
        money = pnl * 20
        print(f"   💵 RESULTADO FINAL: {pnl:+.1f} puntos (~${money:+,.0f})")

print("\n" + "="*70)
