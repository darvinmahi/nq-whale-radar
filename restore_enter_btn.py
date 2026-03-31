"""
Restaura la funcion enterDashboard() que fue eliminada accidentalmente.
La inserta antes del ultimo </script> grande o antes de </body>.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

FUNC = """
<script>
  function enterDashboard() {
    const landing = document.getElementById('landing-screen');
    if (!landing) return;
    landing.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
    landing.style.opacity = '0';
    landing.style.transform = 'scale(0.97)';
    setTimeout(() => {
      landing.style.display = 'none';
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }, 600);
  }
</script>
"""

with open('index.html', encoding='utf-8', errors='replace') as f:
    html = f.read()

# Verificar que no existe ya
if 'enterDashboard' in html:
    print('⚠️ enterDashboard ya existe:', [i for i in range(len(html)) if html[i:i+15]=='enterDashboard'])
else:
    # Insertar antes del primer </body> o al final del archivo
    if '</body>' in html:
        html = html.replace('</body>', FUNC + '</body>', 1)
        print('✅ Funcion insertada antes de </body>')
    else:
        html = html + FUNC
        print('✅ Funcion insertada al final del archivo')
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'✅ index.html guardado ({len(html)//1024}KB)')
    
    # Verificacion
    assert 'enterDashboard' in html
    print('✅ Verificacion: función presente')
