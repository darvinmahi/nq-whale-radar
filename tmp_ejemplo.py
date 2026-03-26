import csv
rows = list(csv.DictReader(open('ny_profile_asia_london_daily.csv')))
for r in rows:
    if r['weekday']=='JUEVES' and r['pm_open_pos']=='BELOW_VA':
        vah=float(r['vah']); val=float(r['val']); vr=float(r['va_range'])
        pm_open=float(r['pm_open']); ny_open=float(r['ny_open_price'])
        pm_lo=float(r['pm_lo']); pm_hi=float(r['pm_hi']); pm_close=float(r['pm_close'])
        target = val if ny_open > val else val - vr*0.5
        stop   = vah + vr*0.10
        print(f"Fecha: {r['date']} ({r['weekday']})")
        print(f"  VAH prev dia: {vah:.1f}")
        print(f"  VAL prev dia: {val:.1f}")
        print(f"  VA range    : {vr:.1f}")
        print(f"  PM open     : {pm_open:.1f}")
        print(f"  NY open     : {ny_open:.1f}  <-- ENTRADA SHORT")
        print(f"  PM high     : {pm_hi:.1f}")
        print(f"  PM low      : {pm_lo:.1f}")
        print(f"  PM close    : {pm_close:.1f}")
        print(f"  Target      : {target:.1f}")
        print(f"  Stop        : {stop:.1f}")
        print(f"  Hit target? : {'SI' if pm_lo <= target else 'NO'}")
        print(f"  Pts ganados : {ny_open - target:.1f}")
        print()
