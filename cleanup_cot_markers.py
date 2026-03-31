import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
MS = '<!-- COT_TABLE_START -->'
ME = '<!-- COT_TABLE_END -->'

with open('index.html', encoding='utf-8', errors='replace') as f:
    c = f.read()

# Localizar todos los bloques
starts = [m.start() for m in re.finditer(re.escape(MS), c)]
ends   = [m.start() for m in re.finditer(re.escape(ME), c)]
print(f'Starts: {starts}')
print(f'Ends:   {ends}')

# Si hay 2 starts y 1 end — el primero es el stale sin end, el segundo es el nuevo con end
# Eliminar desde starts[0] hasta starts[1] (exclusive, para no borrar el nuevo)
# Pero si son 2 starts y el segundo tiene un END → eliminar solo el primer start (orphan)

if len(starts) == 2 and len(ends) == 1:
    # Borrar el primer orphan start tag + cualquier contenido hasta el segundo start
    # starts[0] → starts[1] = stale orphan block
    stale_s = starts[0]
    new_s   = starts[1]
    c_clean = c[:stale_s] + c[new_s:]
    print(f'Borrado bloque stale: chars {stale_s}–{new_s}')
elif len(starts) >= 2 and len(ends) >= 2:
    # Borrar primer bloque completo
    e0 = ends[0]
    c_clean = c[:starts[0]] + c[e0 + len(ME):]
    print(f'Borrado primer bloque completo')
else:
    c_clean = c
    print(f'Sin cambios necesarios')

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(c_clean)

# Verificar resultado
starts2 = [m.start() for m in re.finditer(re.escape(MS), c_clean)]
ends2   = [m.start() for m in re.finditer(re.escape(ME), c_clean)]
print(f'Despues — Starts:{starts2}  Ends:{ends2}')
print(f'DOCTYPE ok: {c_clean.startswith("<!DOCTYPE html>")}')
print(f'Tamano: {len(c_clean)//1024}KB')
