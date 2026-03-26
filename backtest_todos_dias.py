import pandas as pd

df = pd.read_csv('ny_profile_asia_london_daily.csv')
df['date'] = pd.to_datetime(df['date'])

cutoff = df['date'].max() - pd.Timedelta(days=180)
df = df[df['date'] >= cutoff].copy()

periodo_str = str(df['date'].min().date()) + ' -> ' + str(df['date'].max().date())
print('Periodo:', periodo_str)
print('Total sesiones:', len(df))
print()

# Determinar direccion NY: si close_inside True y pm_close > ny_open => UP
# Usamos pm_range y posicion de apertura
def get_direction(row):
    try:
        if row['pm_close'] >= row['ny_open_price']:
            return 'UP'
        else:
            return 'DOWN'
    except:
        return 'UNKNOWN'

df['ny_dir'] = df.apply(get_direction, axis=1)

# Patron basado en ny_open_pos
def get_pattern(row):
    pos = str(row.get('ny_open_pos', '')).upper()
    rng = row.get('pm_range', 0)
    if 'INSIDE' in pos:
        return 'REVERSAL'
    elif 'ABOVE' in pos or 'BELOW' in pos:
        return 'BREAKOUT'
    elif rng >= 300:
        return 'EXPANSION_H'
    else:
        return 'CONSOLIDATION'

df['patron'] = df.apply(get_pattern, axis=1)

days_order = ['LUNES', 'MARTES', 'MIERCOLES', 'JUEVES', 'VIERNES']

print('=' * 60)
for day in days_order:
    dd = df[df['weekday'] == day].copy()
    if len(dd) == 0:
        continue

    n = len(dd)
    print()
    print('=== ' + day + ' (' + str(n) + ' sesiones) ===')

    # Rango
    avg_rng = dd['pm_range'].mean()
    rng_300 = (dd['pm_range'] >= 300).mean() * 100
    rng_200 = (dd['pm_range'] >= 200).mean() * 100
    print('  Rango promedio: ' + str(round(avg_rng)) + ' pts')
    print('  Rango >300pts:  ' + str(round(rng_300, 1)) + '%')
    print('  Rango >200pts:  ' + str(round(rng_200, 1)) + '%')

    # Direccion
    up_pct = (dd['ny_dir'] == 'UP').mean() * 100
    dn_pct = (dd['ny_dir'] == 'DOWN').mean() * 100
    sesgo = 'ALCISTA' if up_pct > dn_pct else 'BAJISTA'
    print('  Sesgo: ' + sesgo + ' (' + str(round(up_pct, 1)) + '% UP / ' + str(round(dn_pct, 1)) + '% DOWN)')

    # Top patron
    top_pat = dd['patron'].value_counts()
    if len(top_pat) > 0:
        pat_name = top_pat.index[0]
        pat_pct = round(top_pat.iloc[0] / n * 100, 1)
        print('  Patron dominante: ' + str(pat_name) + ' (' + str(pat_pct) + '%)')
        for p, c in top_pat.items():
            print('    - ' + str(p) + ': ' + str(round(c/n*100, 1)) + '%')

    # Tendencia
    if 'trend' in dd.columns:
        tc = dd['trend'].value_counts(normalize=True) * 100
        trends_str = ', '.join([str(t) + ':' + str(round(p, 1)) + '%' for t, p in tc.items()])
        print('  Trend: ' + trends_str)

    # NY open position
    if 'ny_open_pos' in dd.columns:
        pc = dd['ny_open_pos'].value_counts(normalize=True) * 100
        pos_str = ', '.join([str(p) + ':' + str(round(v, 1)) + '%' for p, v in pc.items()])
        print('  NY Open Pos: ' + pos_str)

    # Close inside VA
    if 'close_inside' in dd.columns:
        ci = dd['close_inside'].mean() * 100
        print('  Close inside VA: ' + str(round(ci, 1)) + '%')

    # VXN promedio
    if 'vxn' in dd.columns:
        vxn_avg = dd['vxn'].mean()
        print('  VXN promedio: ' + str(round(vxn_avg, 1)))

    # Historico de fechas recientes
    recent = dd.sort_values('date', ascending=False).head(6)
    print()
    print('  Ultimas sesiones:')
    for _, row in recent.iterrows():
        fecha = str(row['date'].date())
        rng = int(row['pm_range'])
        dr = row['ny_dir']
        pat = row['patron']
        pos = str(row.get('ny_open_pos', ''))
        print('    ' + fecha + ' | ' + dr.ljust(5) + ' | ' + str(rng).rjust(4) + ' pts | ' + pat.ljust(15) + ' | ' + pos)

print()
print('=' * 60)
print('ANALISIS COMPLETADO')
