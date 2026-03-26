import json, datetime as dt

d = json.load(open('nq_real_data.json'))
candles = d['candles']
mar20 = [c for c in candles if dt.datetime.utcfromtimestamp(c['time']).strftime('%Y-%m-%d') == '2026-03-20']
print(f'Count: {len(mar20)}')

if mar20:
    highs  = [c['high']  for c in mar20]
    lows   = [c['low']   for c in mar20]
    opens  = [c['open']  for c in mar20]
    closes = [c['close'] for c in mar20]

    day_high  = max(highs)
    day_low   = min(lows)
    day_open  = opens[0]
    day_close = closes[-1]

    ny_c = next((c for c in mar20 if dt.datetime.utcfromtimestamp(c['time']).hour==13 and dt.datetime.utcfromtimestamp(c['time']).minute==30), None)
    ny_open_p = ny_c['open'] if ny_c else opens[0]

    ny_candles = [c for c in mar20 if 13<=dt.datetime.utcfromtimestamp(c['time']).hour<20]
    ny_high = max(c['high'] for c in ny_candles) if ny_candles else day_high
    ny_low  = min(c['low']  for c in ny_candles) if ny_candles else day_low
    ny_close_p = ny_candles[-1]['close'] if ny_candles else day_close
    ny_range = round(ny_high - ny_low, 2)
    move_oc  = round(ny_close_p - ny_open_p, 2)
    direction = "BULLISH" if move_oc > 0 else "BEARISH"

    print(f'day_high={day_high}, day_low={day_low}')
    print(f'ny_open={ny_open_p}, ny_high={ny_high}, ny_low={ny_low}, ny_close={ny_close_p}')
    print(f'ny_range={ny_range}, move_oc={move_oc}, dir={direction}')

    asia_c   = [c for c in mar20 if dt.datetime.utcfromtimestamp(c['time']).hour < 7]
    london_c = [c for c in mar20 if 7<=dt.datetime.utcfromtimestamp(c['time']).hour<13]
    print(f'asia: {len(asia_c)}, london: {len(london_c)}, ny: {len(ny_candles)}')

    # Save filtered candles as JS
    candle_js = json.dumps(mar20)
    with open('mar20_candles_stats.json', 'w') as f:
        json.dump({
            'candles': mar20,
            'day_high': day_high, 'day_low': day_low,
            'day_open': day_open, 'day_close': day_close,
            'ny_open': ny_open_p, 'ny_high': ny_high,
            'ny_low': ny_low, 'ny_close': ny_close_p,
            'ny_range': ny_range, 'move_oc': move_oc,
            'direction': direction,
            'total': len(mar20)
        }, f)
    print('Saved mar20_candles_stats.json')
