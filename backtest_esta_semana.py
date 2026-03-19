import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime

print("="*70)
print("📊 PLAY-BY-PLAY: BACKTEST DE ESTA SEMANA (Datos 1 Minuto) 📊")
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

# Lista para acumular resultados
resultados_lista = []

dates = sorted(raw['date'].unique())
for d in dates:
    day = raw[raw['date'] == d]
    wd = int(day['weekday'].iloc[0])
    if wd not in DAYS: continue
    
    print(f"\n{'-'*70}")
    print(f"🗓️  {DAYS[wd].upper()} {d}")
    print(f"{'-'*70}")
    
    # Check EMA200
    ema = ema_map.get(d, 0)
    
    # Sesiones exactas de la estrategia
    asia = day[(day['hour'] >= 0) & (day['hour'] < 4)]
    london = day[(day['hour'] >= 4) & (day['hour'] < 9)]
    
    if asia.empty or london.empty:
        print("   ❌ Datos insuficientes para Asia/Londres aún (quizás el día no ha terminado).")
        continue
        
    asia_hi, asia_lo = float(asia['High'].max()), float(asia['Low'].min())
    lon_hi, lon_lo = float(london['High'].max()), float(london['Low'].min())
    
    swept_lo = lon_lo < asia_lo
    swept_hi = lon_hi > asia_hi
    
    print(f"   [ASIA] Rango: {asia_lo:.1f} a {asia_hi:.1f}")
    
    setup = None
    if swept_hi and not swept_lo:
        print(f"   [LONDRES] ⬆️ Rompió HIGH de Asia (subió a {lon_hi:.1f}) -> TRAMPA ALCISTA ➡️ Buscamos SELL")
        setup = "SELL"
    elif swept_lo and not swept_hi:
        print(f"   [LONDRES] ⬇️ Rompió LOW de Asia (bajó a {lon_lo:.1f}) -> TRAMPA BAJISTA ➡️ Buscamos BUY")
        setup = "BUY"
    elif swept_hi and swept_lo:
        print(f"   [LONDRES] ↕️ Rompió AMBOS lados -> Rango expandido (Descartado)")
        setup = None
    else:
        print(f"   [LONDRES] ➖ No rompió el rango de Asia -> SIN SETUP hoy")
        setup = None
        
    if setup is None:
        continue
        
    # Validar reglas por día y contexto
    valido = False
    razon = ""
    precio_actual = float(day['Close'].iloc[0])
    
    if wd == 0:
        razon = "Regla: Los Lunes no se opera (WR bajo)."
    elif wd == 1:
        if setup == "SELL":
            if precio_actual < ema:
                valido = True
            else:
                razon = f"Martes SELL requiere precio bajo EMA200 (Precio={precio_actual:.0f}, EMA={ema:.0f})"
        else:
            razon = "Martes solo permite ventas (SELL)."
    elif wd == 2:
        if setup == "SELL":
            valido = True
        else:
            razon = "Miércoles solo permite ventas (SELL)."
    elif wd == 3:
        if setup == "SELL":
            valido = True
        else:
            razon = "Jueves solo permite ventas (SELL)."
    elif wd == 4:
        if setup == "BUY":
            valido = True
        else:
            razon = "Viernes solo permite compras (BUY)."
            
    if not valido:
        print(f"   ⚠️ SEÑAL RECHAZADA: {razon}")
        continue
        
    # Si es válido, calculamos Profile y ponemos orden
    idx_vp = day[(day['hour'] >= 0) & (day['hour'] < 9)]
    poc, vah, val = calc_profile(idx_vp)
    print(f"   [VOLUME PROFILE 12am-9am] VAL: {val:.1f} | POC: {poc:.1f} | VAH: {vah:.1f}")
    
    if setup == "BUY":
        entry = val
        target = vah
        stop = lon_lo - 2 # Buffer de 2 pts
        print(f"   🟢 CALCULANDO ORDEN: BUY LIMIT en {entry:.1f} | SL: {stop:.1f} | TP: {target:.1f}")
        print(f"   (Riesgo: {entry-stop:.1f} pts | Beneficio: {target-entry:.1f} pts | RR: 1:{(target-entry)/(entry-stop):.2f})")
    else:
        entry = vah
        target = val
        stop = lon_hi + 2
        print(f"   🔴 CALCULANDO ORDEN: SELL LIMIT en {entry:.1f} | SL: {stop:.1f} | TP: {target:.1f}")
        print(f"   (Riesgo: {stop-entry:.1f} pts | Beneficio: {entry-target:.1f} pts | RR: 1:{(entry-target)/(stop-entry):.2f})")
        
    # Check Silver bullet window 9:30 a 11:00
    sb = day[((day['hour'] == 9) & (day['minute'] >= 30)) | (day['hour'] == 10) | ((day['hour'] == 11) & (day['minute'] == 0))]
    
    if sb.empty:
        print("   ⏳ Esperando a que abra New York (datos no disponibles aún).")
        continue
        
    entered = False
    result = "NO ENTRY"
    entry_time = ""
    pnl = 0
    t_entry = ""
    
    for i, r in sb.iterrows():
        hi, lo = float(r['High']), float(r['Low'])
        t = f"{int(r['hour']):02d}:{int(r['minute']):02d}"
        
        # Lógica de entrada
        if not entered:
            # Si el precio curza nuestro limit
            if (setup == "BUY" and lo <= entry and hi >= entry) or \
               (setup == "BUY" and hi < entry): # Abrió con gap abajo
                entered = True
                t_entry = t
                entry_time = t
                print(f"   ✅ [ {t} ] ORDEN ACTIVADA - Entramos al mercado en {entry:.1f}")
                
            elif (setup == "SELL" and hi >= entry and lo <= entry) or \
                 (setup == "SELL" and lo > entry): # Abrió con gap arriba
                entered = True
                t_entry = t
                entry_time = t
                print(f"   ✅ [ {t} ] ORDEN ACTIVADA - Entramos al mercado en {entry:.1f}")
                
        # Lógica de salida si ya entramos
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
        print("   ⏳ El precio nunca retrocedió a nuestro nivel de entrada (VAL/VAH). Oportunidad perdida.")
    elif result not in ["WIN", "LOSS"]:
        close_px = float(sb.iloc[-1]['Close'])
        print(f"   ⏰ [ 11:00 ] Cierre por límite de tiempo. Saliendo en {close_px:.1f}")
        pnl = (close_px - entry) if setup == "BUY" else (entry - close_px)
        
    if pnl != 0:
        money = pnl * 20 # $20 por punto en NQ
        print(f"   💵 RESULTADO DEL DÍA: {pnl:+.1f} puntos (~${money:+,.0f})")
    
    # Guardar resultado de este día
    resultados_lista.append({
        "fecha": str(d),
        "dia_semana": DAYS.get(wd, "?"),
        "setup": setup,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "poc": round(poc, 2) if poc else None,
        "vah": round(vah, 2) if vah else None,
        "val": round(val, 2) if val else None,
        "entrada_time": entry_time,
        "resultado": result,
        "pnl_puntos": round(pnl, 2),
        "pnl_dinero": round(pnl * 20, 2),
        "ema200": round(ema, 2),
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

# ==============================================================================
# 💾 GUARDAR RESULTADOS
# ==============================================================================
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

if resultados_lista:
    # --- CSV ---
    csv_path = os.path.join(OUTPUT_DIR, "backtest_results_semana.csv")
    df_res = pd.DataFrame(resultados_lista)
    df_res.to_csv(csv_path, index=False)
    print(f"\n💾 CSV guardado en: {csv_path}")

    # --- JSON ---
    json_path = os.path.join(OUTPUT_DIR, "backtest_results_semana.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados_lista, f, indent=2, ensure_ascii=False)
    print(f"💾 JSON guardado en: {json_path}")

    # --- Resumen ---
    wins   = sum(1 for r in resultados_lista if r["resultado"] == "WIN")
    losses = sum(1 for r in resultados_lista if r["resultado"] == "LOSS")
    no_entry = sum(1 for r in resultados_lista if r["resultado"] == "NO ENTRY")
    total_pnl = sum(r["pnl_puntos"] for r in resultados_lista)
    total_money = total_pnl * 20
    wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

    print(f"\n{'='*70}")
    print(f"📊 RESUMEN DE LA SEMANA")
    print(f"{'='*70}")
    print(f"   ✅ Wins:        {wins}")
    print(f"   ❌ Losses:      {losses}")
    print(f"   ⏳ Sin entrada: {no_entry}")
    print(f"   🎯 Win Rate:    {wr:.1f}%")
    print(f"   💰 PnL Total:   {total_pnl:+.1f} pts (~${total_money:+,.0f})")
else:
    print("\n⚠️ No se generaron setups válidos esta semana.")

print("\n" + "="*70)
print("FIN DEL REPORTE DE LA SEMANA")
print("="*70 + "\n")
