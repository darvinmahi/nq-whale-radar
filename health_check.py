#!/usr/bin/env python3
"""
HEALTH CHECK — NQ Whale Radar Daily Dashboard
==============================================
Ejecutar antes de cualquier push o trabajo nuevo.
Si algo falla = NO AVANZAR hasta que este verde.

Exit code: 0 = TODO OK, 1 = HAY PROBLEMAS
"""
import json, os, sys
from datetime import date, datetime
BASE = os.path.dirname(os.path.abspath(__file__))

PASS = 0
FAIL = 0
WARNINGS = []
ERRORS = []

def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")

def fail(msg):
    global FAIL
    FAIL += 1
    ERRORS.append(msg)
    print(f"  ❌ {msg}")

def warn(msg):
    WARNINGS.append(msg)
    print(f"  ⚠️  {msg}")

def load(rel):
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        return None
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

print("=" * 60)
print("  HEALTH CHECK — NQ Whale Radar")
print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 60)

# ─── 1. ARCHIVOS CRITICOS EXISTEN ──────────────────────────────
print("\n[1] Archivos críticos:")
critical_files = [
    ("daily_master_db.json",                  "data/research/daily_master_db.json"),
    ("backtest_monday",                        "data/research/backtest_monday_1year.json"),
    ("backtest_tuesday",                       "data/research/backtest_tuesday_1year.json"),
    ("backtest_wednesday",                     "data/research/backtest_wednesday_1year.json"),
    ("backtest_thursday",                      "data/research/backtest_thursday_1year.json"),
    ("backtest_friday",                        "data/research/backtest_friday_1year.json"),
    ("today_analysis",                         "data/research/today_analysis.json"),
    ("gex_today",                              "data/research/gex_today.json"),
    ("agent3_data",                            "agent3_data.json"),
    ("daily_dashboard.html",                   "daily_dashboard.html"),
    ("index.html",                             "index.html"),
]
for name, rel in critical_files:
    if os.path.exists(os.path.join(BASE, rel)):
        sz = os.path.getsize(os.path.join(BASE, rel))
        if sz < 100:
            fail(f"{name} existe pero está vacío ({sz} bytes)")
        else:
            ok(f"{name} ({sz//1024}KB)")
    else:
        fail(f"{name} NO EXISTE: {rel}")

# ─── 2. BACKTEST JSONs TIENEN DATOS CORRECTOS ─────────────────
print("\n[2] Backtest JSONs — estructura y datos:")
days_cfg = [
    ('monday',    'data/research/backtest_monday_1year.json',    'all_mondays'),
    ('tuesday',   'data/research/backtest_tuesday_1year.json',   'all_tuesdays'),
    ('wednesday', 'data/research/backtest_wednesday_1year.json', 'all_wednesdays'),
    ('thursday',  'data/research/backtest_thursday_1year.json',  'all_thursdays'),
    ('friday',    'data/research/backtest_friday_1year.json',    'all_fridays'),
]
for day, rel, sess_key in days_cfg:
    d = load(rel)
    if d is None:
        fail(f"{day}: archivo no existe")
        continue
    sess = d.get(sess_key) or d.get('sessions') or []
    st = d.get('stats', {})
    n = len(sess)
    # Checks
    if n < 50:
        fail(f"{day}: solo {n} sesiones (esperamos >50)")
    else:
        ok(f"{day}: {n} sesiones")
    if 'bull_pct' not in st:
        fail(f"{day}: sin bull_pct en stats")
    else:
        bp = st['bull_pct']
        if bp <= 0 or bp >= 100:
            fail(f"{day}: bull_pct={bp} (invalido)")
        else:
            ok(f"{day}: bull={bp}% bear={st.get('bear_pct',0)}%")
    if 'value_area' not in d:
        fail(f"{day}: sin value_area (hit rates)")
    else:
        va = d['value_area']
        vah_r = va.get('vah',{}).get('hit_rate', -1)
        if vah_r == 100.0:
            warn(f"{day}: VAH hit rate = 100% (puede ser incorrecto)")
        elif vah_r <= 0:
            fail(f"{day}: VAH hit rate = {vah_r}%")
        else:
            ok(f"{day}: VAH={vah_r}% POC={va.get('poc',{}).get('hit_rate',-1)}% VAL={va.get('val',{}).get('hit_rate',-1)}%")
    if 'range_distribution' not in d:
        fail(f"{day}: sin range_distribution")
    else:
        rd = d['range_distribution']
        total_rd = sum(rd.values())
        if total_rd < 10:
            fail(f"{day}: range_distribution total={total_rd} (muy pocos datos)")
        else:
            ok(f"{day}: range_distribution OK (total={total_rd})")
    if 'avg_ny_range' not in d or (d.get('avg_ny_range', 0) or 0) < 50:
        fail(f"{day}: avg_ny_range invalido ({d.get('avg_ny_range')})")
    else:
        ok(f"{day}: avg_ny_range={d['avg_ny_range']:.0f} pts")

# ─── 3. TODAY_ANALYSIS TIENE CAMPOS CORRECTOS ─────────────────
print("\n[3] today_analysis.json — claves requeridas:")
ta = load('data/research/today_analysis.json')
if ta is None:
    fail("today_analysis.json no existe")
else:
    required_keys = ['date', 'casos', 'bearish_pct', 'bullish_pct', 'rango_promedio', 'patron_dominante']
    for k in required_keys:
        if k in ta:
            v = ta[k]
            if v is None or v == '' or v == 0 and k in ('bearish_pct','bullish_pct','casos'):
                warn(f"today_analysis['{k}'] = {v} (puede ser correcto si no hay similares)")
            else:
                ok(f"today_analysis['{k}'] = {v}")
        else:
            fail(f"today_analysis falta clave '{k}'")
    # Verificar que la fecha sea reciente (ultimos 7 dias)
    try:
        ta_date = datetime.strptime(ta['date'], '%Y-%m-%d').date()
        days_old = (date.today() - ta_date).days
        if days_old > 7:
            warn(f"today_analysis tiene {days_old} dias de antigüedad ({ta_date})")
        else:
            ok(f"today_analysis fecha OK: {ta_date} ({days_old}d)")
    except: warn("today_analysis: no se pudo verificar fecha")

# ─── 4. AGENT3 TIENE NY STATS ─────────────────────────────────
print("\n[4] agent3_data.json — NY stats en vivo:")
a3 = load('agent3_data.json')
if a3 is None:
    fail("agent3_data.json no existe")
else:
    ri = a3.get('raw_inputs', {})
    # NY stats (pueden ser None en fin de semana)
    today_wd = date.today().weekday()
    is_weekend = today_wd >= 5
    ny_fields = ['NY_OPEN', 'NY_HIGH', 'NY_LOW', 'NY_RANGE']
    for f in ny_fields:
        v = ri.get(f)
        if v is None or v == 0:
            if is_weekend:
                warn(f"agent3[{f}] = {v} (fin de semana, normal)")
            else:
                fail(f"agent3[{f}] vacio en dia de trading")
        else:
            ok(f"agent3[{f}] = {v}")
    # VXN siempre debe tener dato
    vxn = ri.get('VXN')
    if vxn and float(vxn) > 0:
        ok(f"agent3[VXN] = {vxn}")
    else:
        fail(f"agent3[VXN] vacio: {vxn}")
    # GEX
    gex_b = ri.get('GEX_B')
    if gex_b is not None:
        ok(f"agent3[GEX_B] = {gex_b}B")
    else:
        fail("agent3[GEX_B] vacio")

# ─── 5. GEX TODAY ──────────────────────────────────────────────
print("\n[5] gex_today.json:")
gex = load('data/research/gex_today.json')
if gex is None:
    fail("gex_today.json no existe")
else:
    gex_b = gex.get('gex_billions', None)
    regime = gex.get('gex_regime')
    strikes = gex.get('strikes_analyzed', 0)
    if gex_b is None:
        fail("gex_today: gex_billions vacio")
    elif strikes < 100:
        warn(f"gex_today: solo {strikes} strikes (bajo)")
    else:
        ok(f"gex_today: {gex_b}B | {regime} | {strikes} strikes")

# ─── 6. DAILY_MASTER_DB TIENE REGISTROS RECIENTES ─────────────
print("\n[6] daily_master_db.json — completitud:")
db_raw = load('data/research/daily_master_db.json')
if db_raw is None:
    fail("daily_master_db.json no existe")
else:
    records = db_raw.get('records', db_raw) if isinstance(db_raw, dict) else db_raw
    records = records if isinstance(records, list) else []
    n_total = len(records)
    if n_total < 400:
        fail(f"daily_master_db: solo {n_total} registros (esperamos >400)")
    else:
        ok(f"daily_master_db: {n_total} registros")
    if records:
        # Verificar el registro mas reciente
        sorted_r = sorted([r for r in records if isinstance(r, dict) and 'date' in r],
                          key=lambda x: x['date'], reverse=True)
        if sorted_r:
            latest = sorted_r[0]
            latest_date = datetime.strptime(latest['date'], '%Y-%m-%d').date()
            days_old = (date.today() - latest_date).days
            if days_old > 10:
                warn(f"daily_master_db ultimo registro: {latest['date']} ({days_old}d atras)")
            else:
                ok(f"daily_master_db ultimo registro: {latest['date']}")
            # Verificar campos esenciales en ultimo registro
            essential = ['cot_index', 'vxn', 'direction', 'ny_range', 'pattern']
            missing = [f for f in essential if latest.get(f) is None]
            if missing:
                warn(f"daily_master_db campos vacios en ultimo registro: {missing}")
            else:
                ok(f"daily_master_db campos OK: cot={latest.get('cot_index')} vxn={latest.get('vxn')} dir={latest.get('direction')}")

# ─── RESULTADO FINAL ───────────────────────────────────────────
print("\n" + "=" * 60)
print(f"  RESULTADO: {PASS} OK | {len(WARNINGS)} WARNINGS | {FAIL} ERRORES")
print("=" * 60)

if FAIL > 0:
    print("\n🚨 HAY ERRORES — NO AVANZAR HASTA RESOLVER:")
    for e in ERRORS:
        print(f"   ❌ {e}")
    sys.exit(1)
elif WARNINGS:
    print("\n⚠️  WARNINGS (revisar pero puede continuar):")
    for w in WARNINGS:
        print(f"   ⚠️  {w}")
    print("\n✅ Sistema FUNCIONAL con advertencias")
    sys.exit(0)
else:
    print("\n✅ TODO OK — Sistema 100% funcional. Puedes avanzar.")
    sys.exit(0)
