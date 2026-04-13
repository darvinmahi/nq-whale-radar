import sys, io, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agents"))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from source_polygon import get_bars, get_session_data, compute_volume_profile

print("Test Polygon - datos del jueves 10 Abril")
bars = get_bars("I:NDX", 5, "minute", "2026-04-10", "2026-04-11")
print(f"Barras obtenidas: {len(bars)}")

if bars:
    print(f"Primera: {bars[0]['time_utc']} -> {bars[0]['close']}")
    print(f"Ultima:  {bars[-1]['time_utc']} -> {bars[-1]['close']}")
    
    sessions = get_session_data(bars)
    for key, sess in sessions.items():
        if sess["stats"]:
            s = sess["stats"]
            print(f"\n{sess['label']}")
            print(f"  Rango: {s['range_pts']} pts | {s['direction']} ({s['change_pts']:+.0f} pts)")
            print(f"  Open: {s['open']} -> Close: {s['close']}")
    
    vp = compute_volume_profile(bars)
    if vp:
        print(f"\nVolume Profile:")
        print(f"  POC: {vp['poc']} | VAH: {vp['vah']} | VAL: {vp['val']}")
else:
    print("Sin datos para esa fecha")
