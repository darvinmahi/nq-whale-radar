import json

with open('data/research/backtest_5dias_6meses.json', encoding='utf-8') as f:
    d = json.load(f)

lunes_dates = ['2026-01-26','2026-02-02','2026-02-09','2026-02-23','2026-03-02','2026-03-09']

levels = {}
for s in d['by_day']['LUNES']['sessions_detail']:
    if s['date'] not in lunes_dates:
        continue
    print(f"\n{s['date']} | {s['pattern']} | {s['direction']}")
    print(f"  ny_open:    {s['ny_open']}")
    print(f"  val:        {s['val']}")
    print(f"  poc:        {s['poc']}")
    print(f"  vah:        {s['vah']}")
    print(f"  ema200:     {s['ema200']} | above={s['ema_above']}")
    print(f"  sweep_time: {s['sweep_time']}")
    print(f"  r_high:     {s['r_high']} | r_low: {s['r_low']}")
    print(f"  vah_hit={s['vah_hit']} react={s['vah_react']} | poc_hit={s['poc_hit']} react={s['poc_react']} | val_hit={s['val_hit']} react={s['val_react']}")
    print(f"  ema_hit={s['ema_hit']} react={s['ema_react']}")

    levels[s['date']] = {
        'ny_open':     s['ny_open'],
        'val':         s['val'],
        'poc':         s['poc'],
        'vah':         s['vah'],
        'ema200':      s['ema200'],
        'ema_above':   s['ema_above'],
        'sweep_time':  s['sweep_time'],
        'r_high':      s['r_high'],
        'r_low':       s['r_low'],
        'vah_hit':     s['vah_hit'],
        'poc_hit':     s['poc_hit'],
        'val_hit':     s['val_hit'],
        'ema_hit':     s['ema_hit'],
        'vah_react':   s['vah_react'],
        'poc_react':   s['poc_react'],
        'val_react':   s['val_react'],
        'ema_react':   s['ema_react'],
    }

with open('data/research/lunes_levels.json','w') as f:
    json.dump(levels, f, indent=2)
print(f"\n\nGuardado: data/research/lunes_levels.json ({len(levels)} sesiones)")
