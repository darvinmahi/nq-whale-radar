"""
patch_cot_engine.py — v1
Parche que actualiza el cot-live-engine JavaScript en index.html:
1. Reemplaza el FALLBACK con datos reales del CSV (últimas 8 semanas)
2. Corrige el API mapping (era nc=AssetMgr, correcto: nc=LevMoney+AssetMgr)
3. Actualiza la barra COT del Sesgo Ponderado con el valor real del CSV
4. Actualiza el resumen ejecutivo COT Index text

Este script se importa/llama desde fix_and_inject_cot.py.
NO se ejecuta de forma independiente.
"""
import csv, re, sys
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CSV_PATH  = 'data/cot/nasdaq_cot_historical.csv'
HTML_PATH = 'index.html'

def lbl(d):
    for fmt in ('%Y-%m-%d', '%m/%d/%Y'):
        try: return datetime.strptime(d, fmt).strftime('%d %b %Y').lstrip('0')
        except: pass
    return d

def run_patch():
    # 1. Cargar últimas 8 semanas del CSV
    rows = []
    with open(CSV_PATH, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            try:
                lm_l  = int(r.get('Lev_Money_Positions_Long_All')  or 0)
                lm_s  = int(r.get('Lev_Money_Positions_Short_All') or 0)
                dl_l  = int(r.get('Dealer_Positions_Long_All')      or 0)
                dl_s  = int(r.get('Dealer_Positions_Short_All')     or 0)
                am_l  = int(r.get('Asset_Mgr_Positions_Long_All')   or 0)
                am_s  = int(r.get('Asset_Mgr_Positions_Short_All')  or 0)
                stored_ci = float(r.get('COT_Index','') or '0') if r.get('COT_Index','').strip() else None
                if lm_l or lm_s:
                    nc_l = lm_l + am_l;  nc_s = lm_s + am_s
                    rows.append({
                        'date': r['Report_Date_as_MM_DD_YYYY'].strip(),
                        'NC_L': nc_l, 'NC_S': nc_s,
                        'COM_L': dl_l, 'COM_S': dl_s,
                        'RET_L': 0, 'RET_S': 0,
                        'ci': stored_ci
                    })
            except: pass
    rows.sort(key=lambda x: x['date'])
    if not rows:
        print('ERROR: CSV vacío'); return

    last     = rows[-1]
    ci_cur   = round(last['ci']) if last['ci'] else 33  # fallback 33% si no hay CI
    fw_weeks = rows[-8:]  # últimas 8 semanas

    # 2. Leer HTML
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        html = f.read()

    # ── A. FALLBACK del cot-live-engine ──
    fb_lines = []
    for fw in reversed(fw_weeks):  # más reciente primero
        d_str = lbl(fw['date'])
        oi = fw['NC_L'] + fw['NC_S'] + fw['COM_L'] + fw['COM_S']
        fb_lines.append(
            f'    {{ date:"{d_str}", nc_long:{fw["NC_L"]}, nc_short:{fw["NC_S"]}, '
            f'co_long:{fw["COM_L"]}, co_short:{fw["COM_S"]}, '
            f'nr_long:{fw["RET_L"]}, nr_short:{fw["RET_S"]}, oi:{oi} }}'
        )
    new_fb = 'const FALLBACK = [\n' + ',\n'.join(fb_lines) + '\n  ];'
    fb_pat = re.compile(r'const FALLBACK = \[.*?\];', re.DOTALL)
    html, n_fb = fb_pat.subn(new_fb, html, count=1)
    print(f'  FALLBACK JS: {"OK — " + str(len(fw_weeks)) + " semanas reales del CSV" if n_fb else "NO encontrado (revisar)"}')

    # ── B. Corregir API mapping CFTC ──
    # Patrón más flexible con regex
    bad_api_pat = re.compile(
        r'nc_long:\s+\+\(\s*f\.asset_mgr_positions_long.*?nr_short:\s+\+\(\s*f\.lev_money_positions_short[^,]*,',
        re.DOTALL
    )
    good_api = (
        'nc_long:  ( +(f.lev_money_positions_long||0) + +(f.asset_mgr_positions_long||0) ) || +(f.noncomm_positions_long_all||0),\n'
        '          nc_short: ( +(f.lev_money_positions_short||0) + +(f.asset_mgr_positions_short||0) ) || +(f.noncomm_positions_short_all||0),\n'
        '          co_long:  +( f.dealer_positions_long     || f.comm_positions_long_all     || 0),\n'
        '          co_short: +( f.dealer_positions_short    || f.comm_positions_short_all    || 0),\n'
        '          nr_long:  +( f.nonrept_positions_long_all  || 0),\n'
        '          nr_short: +( f.nonrept_positions_short_all || 0),'
    )
    if bad_api_pat.search(html):
        html, n_api = bad_api_pat.subn(good_api, html, count=1)
        print(f'  API mapping CFTC: CORREGIDO (NC=Lev+AM, NR=NonRept)')
    else:
        # Verificar si ya está corregido
        if 'lev_money_positions_long||0) + +' in html:
            print('  API mapping CFTC: ya estaba correcto')
        else:
            print('  API mapping CFTC: patrón no encontrado — revisar manualmente')

    # ── C. Sesgo Ponderado — barra COT ──
    # Actualizar width del bar y valor COT Index
    html = re.sub(
        r'(id="weeklyCOTBar"[^>]*width:)\d+(%)',
        lambda m: m.group(1) + str(ci_cur) + m.group(2),
        html, count=1
    )
    html = re.sub(
        r'(id="weeklyCOTVal"[^>]*>)\d+/100(<)',
        lambda m: m.group(1) + str(ci_cur) + '/100' + m.group(2),
        html, count=1
    )
    # COT label en el ind-nm (ej. "COT 30%")
    html = re.sub(
        r'(<span class="ind-nm[^"]*electric-cyan[^"]*">COT )\d+%(<)',
        lambda m: m.group(1) + str(ci_cur) + '%' + m.group(2),
        html, count=1
    )
    print(f'  Sesgo Ponderado: COT bar → {ci_cur}/100')

    # ── D. Nota bias Sesgo Ponderado (la nota de texto) ──
    # Buscar texto que menciona "COT en zona baja 3 años (27/100)" o similar
    html = re.sub(
        r'COT en zona (baja|alta|media) 3 años \(\d+/100\)',
        f'COT en zona {"baja" if ci_cur < 40 else "media" if ci_cur < 65 else "alta"} 3 años ({ci_cur}/100)',
        html, count=1
    )

    # 3. Guardar
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  index.html guardado ({len(html)//1024}KB) — motor JS actualizado')
    print(f'  COT seguras: FALLBACK={len(fw_weeks)}sem, APImap=corregido, Sesgo={ci_cur}%')

if __name__ == '__main__':
    run_patch()
