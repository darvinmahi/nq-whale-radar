"""
Reorganiza el index.html:
1. Elimina la sección Intelligence Grid
2. Mueve Estado del Mercado / Sesgo Ponderado / Conclusión Operativa
   para que aparezcan justo después del Hero (donde estaba Intel Grid)
"""

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ─── Markers ──────────────────────────────────────────────────────────────────
HERO_END       = '<!-- END: Hero Section -->'
INTEL_START    = '<!-- BEGIN: Intelligence Grid (The Master Conclusion) -->'
INTEL_END      = '<!-- END: Intelligence Grid -->'
ESTADO_START   = '<!-- BEGIN: Estado del Mercado -->'
CONCL_END      = '<!-- END: Conclusión Operativa -->'
OI_END         = '<!-- END: Open Interest & Charts -->'
MASTER_START   = '<!-- BEGIN: Master Conclusion -->'

# ─── 1. Extraer el bloque de las 3 secciones (Estado + Sesgo + Conclusión) ───
# El bloque está actualmente entre OI_END y MASTER_START
idx_estado = content.index(ESTADO_START)
idx_concl_end = content.index(CONCL_END) + len(CONCL_END)

# Capturamos incluyendo saltos de línea circundantes
block_start = content.rindex('\n', 0, idx_estado)   # newline before ESTADO_START
block_end   = content.index('\n', idx_concl_end)     # newline after CONCL_END

three_sections_block = content[block_start:block_end]

# ─── 2. Eliminar las 3 secciones de su posición actual ───────────────────────
content_without_sections = content[:block_start] + content[block_end:]

# ─── 3. Eliminar la sección Intelligence Grid ────────────────────────────────
intel_start_idx = content_without_sections.index(INTEL_START)
intel_end_idx   = content_without_sections.index(INTEL_END) + len(INTEL_END)
# include surrounding newlines
block_before = content_without_sections.rindex('\n', 0, intel_start_idx)
block_after  = content_without_sections.index('\n', intel_end_idx)

content_no_intel = (
    content_without_sections[:block_before] +
    content_without_sections[block_after:]
)

# ─── 4. Insertar las 3 secciones justo después de <!-- END: Hero Section --> ──
insert_pos = content_no_intel.index(HERO_END) + len(HERO_END)
content_final = (
    content_no_intel[:insert_pos] +
    three_sections_block +
    content_no_intel[insert_pos:]
)

# ─── 5. Guardar ───────────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content_final)

print("✅ Reorganización completada.")
print(f"   - Sección Intel Grid eliminada")
print(f"   - Estado del Mercado, Sesgo Ponderado y Conclusión Operativa movidas al inicio")
