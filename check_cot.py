import sys, re
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
with open('index.html', encoding='utf-8', errors='replace') as f:
    c = f.read()
idx = c.find('id="cot-analysis"')
print(f'cot-analysis found: {idx > 0}')
if idx > 0:
    sec_end = c.find('</section>', idx)
    chunk = c[idx:sec_end+10]
    print(f'Section length: {len(chunk)} chars')
    print('--- primeros 600 chars ---')
    print(chunk[:600])
    print('--- ultimos 600 chars ---')
    print(chunk[-600:])
print()
print(f'Trifecta: {"Trifecta" in c}')
print(f'HISTORIAL btn: {"HISTORIAL" in c}')
print(f'cot_historial.html link: {"cot_historial.html" in c}')
print(f'COT_TABLE_START count: {c.count("COT_TABLE_START")}')
print(f'week_table (exact nums): {"LONG" in c and "SHORT" in c}')
print(f'KB: {len(c)//1024}')
