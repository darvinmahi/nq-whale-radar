import pandas as pd
import json

df = pd.read_csv('ny_profile_asia_london_daily.csv')
df['date'] = pd.to_datetime(df['date'])

cutoff = df['date'].max() - pd.Timedelta(days=180)
df = df[df['date'] >= cutoff].copy()

print('Periodo de analisis:', str(df['date'].min().date()), '->', str(df['date'].max().date()))
print('Total de sesiones:', len(df))
print()

def get_direction(row):
    try:
        if row['pm_close'] >= row['ny_open_price']:
            return 'UP'
        else:
            return 'DOWN'
    except:
        return 'UNKNOWN'

def get_ict_pattern(row):
    pos = str(row.get('ny_open_pos', '')).upper()
    rng = float(row.get('pm_range', 0))
    trend = str(row.get('trend', '')).upper()
    if 'ABOVE' in pos:
        if rng >= 280:
            return 'BREAKER_BLOCK'
        return 'EXPANSION_H'
    elif 'BELOW' in pos:
        if rng >= 280:
            return 'BREAKER_BLOCK'
        return 'EXPANSION_L'
    elif 'INSIDE' in pos:
        if trend == 'BULL' and rng >= 250:
            return 'NEWS_DRIVE'
        elif rng >= 300:
            return 'EXPANSION_H'
        else:
            return 'CONSOLIDATION'
    return 'CONSOLIDATION'

df['ny_dir'] = df.apply(get_direction, axis=1)
df['ict_pattern'] = df.apply(get_ict_pattern, axis=1)

# Nivel EMA200
def ema_side(row):
    try:
        price = float(row['ny_open_price'])
        ema = float(row['ema200'])
        return 'ABOVE' if price > ema else 'BELOW'
    except:
        return 'UNKNOWN'

df['ema200_side'] = df.apply(ema_side, axis=1)

# Mapeo de dias con tildes
días_map = {
    'LUNES': 'LUNES',
    'MARTES': 'MARTES',
    'MIÉRCOLES': 'MIÉRCOLES',
    'JUEVES': 'JUEVES',
    'VIERNES': 'VIERNES'
}

days_order = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES']

all_results = {}

for day in days_order:
    dd = df[df['weekday'] == day].copy()
    if len(dd) == 0:
        print('SIN DATOS: ' + day)
        continue

    n = len(dd)
    print('=' * 65)
    print('  DIA: ' + day + '  |  ' + str(n) + ' sesiones')
    print('=' * 65)

    # Rango
    avg_rng = dd['pm_range'].mean()
    rng_300 = (dd['pm_range'] >= 300).mean() * 100
    rng_250 = (dd['pm_range'] >= 250).mean() * 100
    rng_200 = (dd['pm_range'] >= 200).mean() * 100
    rng_median = dd['pm_range'].median()
    print('  [RANGO NY SESSION]')
    print('    Promedio:       ' + str(round(avg_rng)) + ' pts')
    print('    Mediana:        ' + str(round(rng_median)) + ' pts')
    print('    > 300 pts:      ' + str(round(rng_300, 1)) + '%')
    print('    > 250 pts:      ' + str(round(rng_250, 1)) + '%')
    print('    > 200 pts:      ' + str(round(rng_200, 1)) + '%')
    print()

    # Sesgo
    up_pct = (dd['ny_dir'] == 'UP').mean() * 100
    dn_pct = (dd['ny_dir'] == 'DOWN').mean() * 100
    sesgo = 'ALCISTA' if up_pct > dn_pct else 'BAJISTA'
    sesgo_fuerza = 'FUERTE' if abs(up_pct - dn_pct) > 20 else 'MODERADO' if abs(up_pct - dn_pct) > 10 else 'NEUTRO'
    print('  [SESGO DE DIRECCION]')
    print('    Sesgo: ' + sesgo + ' ' + sesgo_fuerza)
    print('    UP:   ' + str(round(up_pct, 1)) + '%  (' + str((dd['ny_dir']=='UP').sum()) + ' dias)')
    print('    DOWN: ' + str(round(dn_pct, 1)) + '%  (' + str((dd['ny_dir']=='DOWN').sum()) + ' dias)')
    print()

    # Trend
    if 'trend' in dd.columns:
        tc = dd['trend'].value_counts(normalize=True) * 100
        print('  [TENDENCIA MACRO]')
        for t, p in tc.items():
            print('    ' + str(t) + ': ' + str(round(p, 1)) + '%')
        print()

    # EMA200
    ec = dd['ema200_side'].value_counts(normalize=True) * 100
    print('  [POSICION vs EMA200]')
    for e, p in ec.items():
        print('    ' + str(e) + ': ' + str(round(p, 1)) + '%')
    print()

    # Patron ICT
    top_pat = dd['ict_pattern'].value_counts()
    print('  [PATRONES ICT]')
    for p, c in top_pat.items():
        pct = round(c / n * 100, 1)
        print('    ' + str(p) + ': ' + str(pct) + '% (' + str(c) + ' dias)')
    print()

    # NY Open Pos
    if 'ny_open_pos' in dd.columns:
        pc = dd['ny_open_pos'].value_counts(normalize=True) * 100
        print('  [NY OPEN POSITION]')
        for p, v in pc.items():
            print('    ' + str(p) + ': ' + str(round(v, 1)) + '%')
        print()

    # Close inside VA
    if 'close_inside' in dd.columns:
        ci = dd['close_inside'].sum()
        ci_pct = dd['close_inside'].mean() * 100
        print('  [CLOSE INSIDE VALUE AREA]: ' + str(round(ci_pct, 1)) + '% (' + str(int(ci)) + ' dias)')
        print()

    # VA Range
    if 'va_range' in dd.columns:
        print('  [VALUE AREA RANGE]')
        print('    Promedio: ' + str(round(dd['va_range'].mean())) + ' pts')
        print()

    # VXN
    if 'vxn' in dd.columns:
        print('  [VOLATILIDAD VXN]: promedio=' + str(round(dd['vxn'].mean(), 1)))
        print()

    # Historico reciente
    recent = dd.sort_values('date', ascending=False).head(8)
    print('  [HISTORICO RECIENTE (ultimas 8 sesiones)]')
    print('    FECHA      | DIR  | RANGO | PATRON           | NY OPEN POS')
    print('    ' + '-' * 60)
    for _, row in recent.iterrows():
        fecha = str(row['date'].date())
        dr = str(row['ny_dir']).ljust(4)
        rng = str(int(row['pm_range'])).rjust(5)
        pat = str(row['ict_pattern']).ljust(17)
        pos = str(row.get('ny_open_pos', '')).ljust(15)
        print('    ' + fecha + ' | ' + dr + ' | ' + rng + ' | ' + pat + ' | ' + pos)
    print()

    # Guardar para JSON
    top_pat_name = top_pat.index[0] if len(top_pat) > 0 else 'N/A'
    top_pat_pct = round(top_pat.iloc[0] / n * 100, 1) if len(top_pat) > 0 else 0
    trend_dom = 'BULL' if 'BULL' in (tc.index[0] if 'trend' in dd.columns else '') else ('MIXED' if 'MIXED' in (tc.index[0] if 'trend' in dd.columns else '') else 'BEAR')
    
    hist_list = []
    for _, row in recent.iterrows():
        hist_list.append({
            'fecha': str(row['date'].date()),
            'dir': str(row['ny_dir']),
            'rango': int(row['pm_range']),
            'patron': str(row['ict_pattern']),
            'ny_open_pos': str(row.get('ny_open_pos', ''))
        })

    all_results[day] = {
        'sesiones': n,
        'avg_rango': round(avg_rng),
        'rango_median': round(rng_median),
        'rango_300_pct': round(rng_300, 1),
        'rango_250_pct': round(rng_250, 1),
        'rango_200_pct': round(rng_200, 1),
        'sesgo': sesgo,
        'sesgo_fuerza': sesgo_fuerza,
        'up_pct': round(up_pct, 1),
        'dn_pct': round(dn_pct, 1),
        'top_pattern': top_pat_name,
        'top_pattern_pct': top_pat_pct,
        'trend_dominante': str(dd['trend'].mode()[0]) if 'trend' in dd.columns else 'N/A',
        'ema200_above_pct': round(ec.get('ABOVE', 0), 1),
        'close_inside_va_pct': round(dd['close_inside'].mean() * 100, 1) if 'close_inside' in dd.columns else 0,
        'vxn_avg': round(dd['vxn'].mean(), 1) if 'vxn' in dd.columns else 0,
        'historico': hist_list
    }

print()
print('=' * 65)
print('GUARDANDO JSON...')
with open('backtest_all_days_results.json', 'w', encoding='utf-8') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print('Guardado en: backtest_all_days_results.json')
