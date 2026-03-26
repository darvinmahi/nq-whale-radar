#!/usr/bin/env python3
"""
Apply all 4 fixes to daily_dashboard.html:
 1. DAY_CONFIG tuesday json → backtest_mon_tue_3m.json (sessKey 'all_tuesdays' but load from MARTES)
 2. DAY_CONFIG friday json  → backtest_all_days.json   (sessKey 'all_fridays')
 3. loadDayData: handle tuesday MARTES subkey and friday VIERNES subkey
 4. Replace REAL_BACKTEST block with real data from _real_backtest_block.js
"""
import re

HTML = 'daily_dashboard.html'

with open(HTML, encoding='utf-8') as f:
    content = f.read()

original_len = len(content)

# ── Fix 1 & 2: DAY_CONFIG paths ────────────────────────────────────────────────
old_cfg = """const DAY_CONFIG = {
  monday:    { label: 'LUNES',      emoji: '🟢', json: 'data/research/backtest_monday_1year.json',         chartPrefix: 'lunes_chart_',     sessKey: 'all_mondays' },
  tuesday:   { label: 'MARTES',     emoji: '🔵', json: 'data/research/backtest_tuesday_3m.json',            chartPrefix: 'martes_chart_',    sessKey: 'all_tuesdays' },
  wednesday: { label: 'MIÉRCOLES',  emoji: '🟡', json: 'data/research/backtest_wednesday_3m.json',          chartPrefix: 'miercoles_chart_', sessKey: 'all_wednesdays' },
  thursday:  { label: 'JUEVES',     emoji: '🟠', json: 'data/research/backtest_thursday_noticias_1year.json', chartPrefix: 'jueves_chart_',    sessKey: 'all_thursdays' },
  friday:    { label: 'VIERNES',    emoji: '🔴', json: 'data/research/backtest_5dias_sesiones_6m.json',     chartPrefix: 'viernes_chart_',   sessKey: 'all_fridays' },"""

new_cfg = """const DAY_CONFIG = {
  monday:    { label: 'LUNES',      emoji: '🟢', json: 'data/research/backtest_monday_1year.json',            chartPrefix: 'lunes_chart_',     sessKey: 'all_mondays',    subKey: null },
  tuesday:   { label: 'MARTES',     emoji: '🔵', json: 'data/research/backtest_mon_tue_3m.json',              chartPrefix: 'martes_chart_',    sessKey: 'all_tuesdays',   subKey: 'MARTES' },
  wednesday: { label: 'MIÉRCOLES',  emoji: '🟡', json: 'data/research/backtest_wednesday_3m.json',            chartPrefix: 'miercoles_chart_', sessKey: 'all_wednesdays', subKey: null },
  thursday:  { label: 'JUEVES',     emoji: '🟠', json: 'data/research/backtest_thursday_noticias_1year.json', chartPrefix: 'jueves_chart_',    sessKey: 'all_thursdays',  subKey: null },
  friday:    { label: 'VIERNES',    emoji: '🔴', json: 'data/research/backtest_all_days.json',                chartPrefix: 'viernes_chart_',   sessKey: 'all_fridays',    subKey: 'VIERNES' },"""

if old_cfg in content:
    content = content.replace(old_cfg, new_cfg, 1)
    print("✅ Fix 1+2: DAY_CONFIG patched")
else:
    print("⚠️  DAY_CONFIG not found literally — trying regex")
    # fallback: patch only the two lines
    content = content.replace(
        "json: 'data/research/backtest_tuesday_3m.json',            chartPrefix: 'martes_chart_',    sessKey: 'all_tuesdays' }",
        "json: 'data/research/backtest_mon_tue_3m.json',              chartPrefix: 'martes_chart_',    sessKey: 'all_tuesdays',   subKey: 'MARTES' }",
        1)
    content = content.replace(
        "json: 'data/research/backtest_5dias_sesiones_6m.json',     chartPrefix: 'viernes_chart_',   sessKey: 'all_fridays' }",
        "json: 'data/research/backtest_all_days.json',                chartPrefix: 'viernes_chart_',   sessKey: 'all_fridays',    subKey: 'VIERNES' }",
        1)

# ── Fix 3: loadDayData - add subKey extraction + tuesday/friday normalization ─
old_load = """async function loadDayData(day) {
  setLoadingMsg('Cargando datos…');
  const cfg = DAY_CONFIG[day];
  let data;
  try {
    const res = await fetch(cfg.json);
    if (!res.ok) throw new Error();
    data = await res.json();
  } catch {
    data = buildDemoData(day);
  }
  backTestData = data;
  const cfg2   = DAY_CONFIG[day];
  allSessions  = data[cfg2.sessKey] || data.all_mondays || data.all_sessions || data.sessions || [];
  renderStats(data, day);
  if (day === 'thursday') loadClaimsData();
  hideLoading();
}"""

new_load = """async function loadDayData(day) {
  setLoadingMsg('Cargando datos…');
  const cfg = DAY_CONFIG[day];
  let rawData;
  try {
    const res = await fetch(cfg.json);
    if (!res.ok) throw new Error();
    rawData = await res.json();
  } catch {
    rawData = null;
  }

  // Extract subKey section if needed (e.g. tuesday→MARTES, friday→days.VIERNES)
  let data = null;
  if (rawData) {
    if (cfg.subKey && day === 'tuesday') {
      // mon_tue_3m.json structure: { MARTES: { sessions, patterns, ... } }
      const sub = rawData[cfg.subKey] || {};
      const sessions = sub.sessions || [];
      data = {
        title: 'Backtest MARTES NQ',
        period: rawData.period || '',
        total_sessions: sub.total_sessions || sessions.length,
        total_mondays: sub.total_sessions || sessions.length,
        dominant_pattern: sub.dominant_pattern || '',
        dominant_pct: sub.dominant_pct || 0,
        avg_ny_range: sub.avg_ny_range || 0,
        max_ny_range: sub.max_ny_range || 0,
        directions: sub.direction || sub.directions || {},
        patterns: sub.patterns || {},
        range_distribution: sub.range_distribution || {},
        value_area: sub.value_area || {},
        ema200: sub.ema200 || {},
        all_tuesdays: sessions,
      };
    } else if (cfg.subKey && day === 'friday') {
      // backtest_all_days.json structure: { days: { 'VIERNES': { sessions, ... } } }
      const daysMap = rawData.days || {};
      let friDay = null;
      for (const k of Object.keys(daysMap)) {
        if (k.toUpperCase().includes('VIERN') || k.toUpperCase().includes('FRI')) { friDay = daysMap[k]; break; }
      }
      if (friDay) {
        const sessions = friDay.sessions || [];
        const total = sessions.length;
        const dirsRaw = friDay.direction || friDay.directions || {};
        const dirs = {};
        for (const [k,v] of Object.entries(dirsRaw)) {
          dirs[k] = (typeof v === 'number' && v <= 1) ? Math.round(v * total) : v;
        }
        const patsRaw = friDay.patterns || {};
        const pats = {};
        for (const [k,v] of Object.entries(patsRaw)) {
          pats[k] = typeof v === 'number' ? (v <= 1 ? (v*100).toFixed(1)+'%' : v.toFixed(1)+'%') : String(v);
        }
        data = {
          title: 'Backtest VIERNES NQ',
          period: (rawData.period_start || '') + ' → ' + (rawData.period_end || ''),
          total_sessions: total,
          total_mondays: total,
          dominant_pattern: friDay.dominant_pattern || 'CONSOLIDATION',
          dominant_pct: friDay.dominant_pct || 0,
          avg_ny_range: Math.round(friDay.avg_ny_range || 0),
          max_ny_range: Math.round(friDay.max_ny_range || 0),
          directions: dirs,
          patterns: pats,
          range_distribution: friDay.range_distribution || {},
          value_area: friDay.value_area || {},
          ema200: friDay.ema200 || {},
          all_fridays: sessions,
        };
      }
    } else {
      data = rawData;
    }
  }

  // Fallback to embedded REAL_BACKTEST
  if (!data) data = buildDemoData(day);

  backTestData = data;
  allSessions  = data[cfg.sessKey] || data.all_mondays || data.all_sessions || data.sessions || [];
  renderStats(data, day);
  if (day === 'thursday') loadClaimsData();
  hideLoading();
}"""

if old_load in content:
    content = content.replace(old_load, new_load, 1)
    print("✅ Fix 3: loadDayData patched")
else:
    print("⚠️  loadDayData not found literally")

# ── Fix 4: Replace REAL_BACKTEST block with real data ─────────────────────────
# Read real data
with open('_real_backtest_block.js', encoding='utf-8') as f:
    real_block = f.read().strip()   # already "const REAL_BACKTEST = {...};"

# Find start/end of REAL_BACKTEST
rb_start = content.find('\nconst REAL_BACKTEST = {')
if rb_start == -1:
    rb_start = content.find('const REAL_BACKTEST = {')
    if rb_start == -1:
        print("⚠️  REAL_BACKTEST not found")
    else:
        rb_start -= 0  # no newline

# Find end: next 'function buildDemoData' or '};' at same level
rb_end = content.find('\nfunction buildDemoData(', rb_start)
if rb_end == -1:
    rb_end = content.find('function buildDemoData(', rb_start)

if rb_start != -1 and rb_end != -1:
    old_block = content[rb_start:rb_end]
    # Replace with real block + newline
    content = content[:rb_start] + '\n' + real_block + '\n\n' + content[rb_end:]
    print("✅ Fix 4: REAL_BACKTEST replaced with real data")
else:
    print(f"⚠️  Could not find REAL_BACKTEST boundaries: start={rb_start}, end={rb_end}")

# ── Write output ──────────────────────────────────────────────────────────────
with open(HTML, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\nFinal: {original_len} → {len(content)} bytes (+{len(content)-original_len})")
print("✅  daily_dashboard.html updated")
