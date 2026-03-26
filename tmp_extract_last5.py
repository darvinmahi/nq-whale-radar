"""Extraer los últimos 5 días de trading completos del CSV para visualización"""
import csv, json

rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv', encoding='utf-8')))
rows.sort(key=lambda r: r['date'])

# Necesitamos al menos 6 días (el day[i] usa prev = day[i-1])
# Últimos 6 filas para tener 5 trades con VA del día anterior
last6 = rows[-6:]

result = []
for i in range(1, len(last6)):
    prev = last6[i-1]
    curr = last6[i]
    
    prev_val   = float(prev['val'])
    prev_vah   = float(prev['vah'])
    prev_range = float(prev['va_range'])
    prev_poc   = float(prev['poc'])
    
    pm_open = float(curr['pm_open'])
    ny_open = float(curr['ny_open_price'])
    prof_hi = float(curr['prof_hi'])
    prof_lo = float(curr['prof_lo'])
    curr_val  = float(curr['val'])
    curr_vah  = float(curr['vah'])
    curr_poc  = float(curr['poc'])
    
    # Clasificar pm_open con VA de ayer
    if pm_open > prev_vah:
        pos = 'ABOVE_VA'
        direc = 'LONG'
        stop   = prev_val - prev_range * 0.10
        if ny_open < prev_vah:
            target = prev_vah
        else:
            target = ny_open + prev_range * 0.50
        riesgo = max(ny_open - stop, 1)
        potenc = target - ny_open
    elif pm_open < prev_val:
        pos = 'BELOW_VA'
        direc = 'SHORT'
        stop   = prev_vah + prev_range * 0.10
        if ny_open > prev_val:
            target = prev_val
        else:
            target = ny_open - prev_range * 0.50
        riesgo = max(stop - ny_open, 1)
        potenc = ny_open - target
    else:
        pos = 'INSIDE_VA'
        direc = 'NONE'
        stop = target = riesgo = potenc = 0

    # Resultado
    close_above = curr.get('close_above_va','False') == 'True'
    close_below = curr.get('close_below_va','False') == 'True'
    close_inside= curr.get('close_inside','False') == 'True'
    
    if direc == 'LONG':
        hit_stop   = prof_lo <= stop
        hit_target = prof_hi >= target
    elif direc == 'SHORT':
        hit_stop   = prof_hi >= stop
        hit_target = prof_lo <= target
    else:
        hit_stop = hit_target = False

    if direc == 'NONE':
        resultado = 'NO_TRADE'
        pts = 0
    elif hit_stop and hit_target:
        resultado = 'WIN' if (direc=='LONG' and close_above) or (direc=='SHORT' and close_below) else 'LOSS'
        pts = potenc if resultado == 'WIN' else -riesgo
    elif hit_stop:
        resultado = 'LOSS'
        pts = -riesgo
    elif hit_target:
        resultado = 'WIN'
        pts = potenc
    else:
        if direc == 'LONG':
            resultado = 'PARTIAL_WIN' if close_above else ('PARTIAL_LOSS' if close_below else 'PARTIAL_WIN')
            pts = prev_range * 0.20 if resultado == 'PARTIAL_WIN' else -prev_range * 0.10
        else:
            resultado = 'PARTIAL_WIN' if close_below else ('PARTIAL_LOSS' if close_above else 'PARTIAL_WIN')
            pts = prev_range * 0.20 if resultado == 'PARTIAL_WIN' else -prev_range * 0.10

    result.append({
        'date':       curr['date'],
        'weekday':    curr['weekday'],
        'direc':      direc,
        'pos':        pos,
        'pm_open':    pm_open,
        'ny_open':    round(ny_open, 2),
        'prof_hi':    round(prof_hi, 2),
        'prof_lo':    round(prof_lo, 2),
        'prev_val':   round(prev_val, 2),
        'prev_vah':   round(prev_vah, 2),
        'prev_poc':   round(prev_poc, 2),
        'curr_val':   round(curr_val, 2),
        'curr_vah':   round(curr_vah, 2),
        'curr_poc':   round(curr_poc, 2),
        'stop':       round(stop, 2),
        'target':     round(target, 2),
        'riesgo':     round(riesgo, 2),
        'potenc':     round(potenc, 2),
        'pts':        round(pts, 1),
        'resultado':  resultado,
        'close_above':close_above,
        'close_below':close_below,
        'close_inside':close_inside,
        'prev_date':  prev['date'],
        'prev_range': round(prev_range, 1),
    })

print(json.dumps(result, indent=2))
