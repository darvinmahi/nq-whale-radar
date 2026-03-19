/**
 * NAV.JS — Navegación Unificada del AI Financial Terminal
 * Inyectar con: <script src="nav.js"></script> antes de </body>
 */
(function () {
  const PAGES = [
    { label: 'Terminal',      icon: 'monitor_heart',    href: 'index.html',             id: 'index' },
    { label: 'Biblia Datos',  icon: 'auto_stories',     href: 'analisis_promax.html',   id: 'promax' },
    { label: 'Order Flow',    icon: 'waterfall_chart',  href: 'analisis_orderflow.html',id: 'orderflow' },
    { label: 'COT Intel',     icon: 'radar',            href: 'cot_intel.html',         id: 'cot' },
    { label: 'Noticias',      icon: 'newspaper',        href: 'noticias_nasdaq.html',   id: 'noticias' },
    { label: 'Patterns',      icon: 'pattern',          href: 'pattern_intel.html',     id: 'patterns' },
    { label: 'Backtest',      icon: 'history_edu',      href: 'weekly_backtest.html',   id: 'backtest' },
    { label: 'Cross',         icon: 'compare_arrows',   href: 'cross_analysis.html',    id: 'cross' },
    { label: 'Journal',       icon: 'book_2',           href: 'nasdaq_journal.html',    id: 'journal' },
  ];

  // Detectar página actual
  const currentFile = window.location.pathname.split('/').pop() || 'index.html';
  const currentId   = (PAGES.find(p => p.href === currentFile) || PAGES[0]).id;

  // CSS del nav
  const style = document.createElement('style');
  style.textContent = `
    :root { --nav-purple: #a855f7; --nav-purple-dark: #7c3aed; --nav-bg: rgba(2,6,23,0.97); }
    #ag-nav {
      position: fixed; bottom: 0; left: 0; right: 0; z-index: 9990;
      background: var(--nav-bg);
      backdrop-filter: blur(20px);
      border-top: 1px solid rgba(168,85,247,0.2);
      display: flex; align-items: center; justify-content: center;
      padding: 0 8px; height: 58px;
      box-shadow: 0 -4px 30px rgba(168,85,247,0.08);
      font-family: 'JetBrains Mono', 'Courier New', monospace;
    }
    #ag-nav .nav-inner {
      display: flex; align-items: center; gap: 2px;
      overflow-x: auto; max-width: 100%;
      scrollbar-width: none;
    }
    #ag-nav .nav-inner::-webkit-scrollbar { display: none; }
    #ag-nav .nav-item {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      gap: 2px; padding: 6px 10px; border-radius: 10px; cursor: pointer;
      text-decoration: none; color: rgba(148,163,184,0.7);
      transition: all 0.2s ease; border: 1px solid transparent;
      min-width: 60px; white-space: nowrap;
    }
    #ag-nav .nav-item:hover {
      color: var(--nav-purple);
      background: rgba(168,85,247,0.08);
      border-color: rgba(168,85,247,0.2);
    }
    #ag-nav .nav-item.active {
      color: var(--nav-purple);
      background: rgba(168,85,247,0.12);
      border-color: rgba(168,85,247,0.35);
      box-shadow: 0 0 12px rgba(168,85,247,0.15);
    }
    #ag-nav .nav-item .nav-icon {
      font-family: 'Material Symbols Outlined';
      font-size: 18px; line-height: 1;
      font-weight: 300;
    }
    #ag-nav .nav-item .nav-label {
      font-size: 8px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.5px;
    }
    #ag-nav .nav-sep {
      width: 1px; height: 28px;
      background: rgba(168,85,247,0.15);
      margin: 0 4px; flex-shrink: 0;
    }
    /* Ajustar el botón flotante para no solapar el nav */
    .ag-btn { bottom: 70px !important; }
    .ag-terminal { bottom: 136px !important; }
    /* Padding inferior para que el contenido no quede bajo el nav */
    body { padding-bottom: 62px !important; }
  `;
  document.head.appendChild(style);

  // Link Material Symbols si no está presente
  if (!document.querySelector('link[href*="Material+Symbols"]')) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200';
    document.head.appendChild(link);
  }

  // Construir HTML del nav
  const nav = document.createElement('nav');
  nav.id = 'ag-nav';
  nav.setAttribute('role', 'navigation');
  nav.setAttribute('aria-label', 'Navegación principal');

  const inner = document.createElement('div');
  inner.className = 'nav-inner';

  PAGES.forEach((page, i) => {
    if (i > 0 && i % 4 === 0) {
      const sep = document.createElement('div');
      sep.className = 'nav-sep';
      inner.appendChild(sep);
    }

    const a = document.createElement('a');
    a.className = 'nav-item' + (page.id === currentId ? ' active' : '');
    a.href = page.href;
    a.setAttribute('aria-label', page.label);
    a.innerHTML = `
      <span class="nav-icon">${page.icon}</span>
      <span class="nav-label">${page.label}</span>
    `;
    inner.appendChild(a);
  });

  nav.appendChild(inner);
  document.body.appendChild(nav);
})();
