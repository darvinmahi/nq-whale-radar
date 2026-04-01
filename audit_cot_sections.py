import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('index.html', encoding='utf-8', errors='replace') as f:
    lines = f.readlines()

keywords = ['situaci', 'rango hist', 'niveles extr', 'resumen ejecutivo', 'aumentando cortos',
            'cot index', 'cot-index', 'bearish', 'señal del analista', 'nc bajista',
            'non-commercial net', 'cot_signal', 'analyst', 'nc_net',
            'presión bajista', 'historical', 'cot intel', 'asset manager']
found = []
for i, line in enumerate(lines, 1):
    lo = line.lower()
    if any(k in lo for k in keywords):
        found.append((i, line.rstrip()[:130]))

print(f'Total lineas con info COT: {len(found)}\n')
for ln, txt in found[:80]:
    print(f'L{ln:5}: {txt}')
