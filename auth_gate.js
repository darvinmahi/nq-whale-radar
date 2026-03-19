/**
 * AUTH_GATE.JS — Login Modal that triggers on button clicks (index.html only)
 * 
 * Behavior:
 *  - index.html loads freely without login
 *  - When user clicks ANY navigation link/button → modal login appears
 *  - If already authenticated (session in localStorage) → navigates directly
 *  - Credentials stay saved so user enters them once and auto-fills next time
 */
(function () {
  'use strict';

  const SESSION_KEY = 'nq_whale_session';
  const SAVED_CREDS_KEY = 'nq_saved_credentials';
  const SESSION_MAX_AGE = 24 * 60 * 60 * 1000; // 24h

  // ═══ Authorized Users ═══
  const USERS = {
    'darvinmahia@gmail.com': {
      hash: 'ef797c8118f02dfb649607dd5d3f8c7623048c9c063d532cc95c5ed7a898a64f',
      name: 'Darvin Mahia'
    }
  };

  // SHA-256
  async function sha256(text) {
    const data = new TextEncoder().encode(text);
    const buf = await crypto.subtle.digest('SHA-256', data);
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // Check valid session
  function hasValidSession() {
    try {
      const s = JSON.parse(localStorage.getItem(SESSION_KEY));
      return s && s.user && s.timestamp && (Date.now() - s.timestamp < SESSION_MAX_AGE);
    } catch { return false; }
  }

  // Load saved credentials
  function getSavedCreds() {
    try { return JSON.parse(localStorage.getItem(SAVED_CREDS_KEY)) || null; }
    catch { return null; }
  }

  // ═══ Inject CSS ═══
  const style = document.createElement('style');
  style.textContent = `
    #nq-auth-overlay {
      position: fixed; inset: 0; z-index: 99999;
      background: rgba(2, 6, 23, 0.92);
      backdrop-filter: blur(20px);
      display: flex; align-items: center; justify-content: center;
      opacity: 0; pointer-events: none;
      transition: opacity 0.35s ease;
    }
    #nq-auth-overlay.active { opacity: 1; pointer-events: all; }
    #nq-auth-modal {
      background: linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,10,60,0.9));
      border: 1px solid rgba(168,85,247,0.35);
      border-radius: 16px;
      padding: 40px 36px 32px;
      width: 360px; max-width: 92vw;
      box-shadow: 0 0 60px rgba(168,85,247,0.2), 0 0 120px rgba(0,242,255,0.08);
      transform: translateY(30px) scale(0.95);
      transition: transform 0.4s cubic-bezier(.2,.9,.3,1);
      font-family: 'Inter', sans-serif;
    }
    #nq-auth-overlay.active #nq-auth-modal {
      transform: translateY(0) scale(1);
    }
    .nq-m-logo-wrap {
      text-align: center; margin-bottom: 12px;
    }
    .nq-m-logo-wrap img {
      height: 44px; width: auto;
      filter: drop-shadow(0 0 10px rgba(168,85,247,0.5));
    }
    .nq-m-logo-text {
      text-align: center; margin-bottom: 4px;
    }
    .nq-m-logo-text .ai { font-family: 'Barlow Condensed', sans-serif; font-size: 24px; font-weight: 800;
      background: linear-gradient(90deg, #a855f7, #00f2ff); -webkit-background-clip: text;
      -webkit-text-fill-color: transparent; text-transform: uppercase; letter-spacing: 0.08em;
    }
    .nq-m-logo-text .fundamental { font-family: 'Barlow Condensed', sans-serif; font-size: 18px; font-weight: 600;
      color: rgba(248,250,252,0.85); text-transform: uppercase; letter-spacing: 0.15em; margin-left: 4px;
    }
    .nq-m-title {
      font-family: 'Barlow Condensed', sans-serif;
      font-size: 11px; font-weight: 600; color: rgba(0,242,255,0.6);
      text-transform: uppercase; letter-spacing: 0.2em;
      margin-bottom: 20px; text-align: center;
      font-family: 'JetBrains Mono', monospace;
    }
    .nq-m-subtitle {
      font-size: 11px; color: rgba(148,163,184,0.7);
      text-align: center; margin-bottom: 24px;
      font-family: 'JetBrains Mono', monospace;
      letter-spacing: 0.08em;
    }
    .nq-m-field {
      position: relative; margin-bottom: 14px;
    }
    .nq-m-field label {
      display: block; font-size: 9px; font-weight: 600;
      color: rgba(0,242,255,0.6); text-transform: uppercase;
      letter-spacing: 0.15em; margin-bottom: 6px;
      font-family: 'JetBrains Mono', monospace;
    }
    .nq-m-field input {
      width: 100%; padding: 10px 14px;
      background: rgba(2,6,23,0.8);
      border: 1px solid rgba(168,85,247,0.25);
      border-radius: 8px; color: #f8fafc;
      font-size: 13px; font-family: 'Inter', sans-serif;
      outline: none; transition: border-color 0.2s;
    }
    .nq-m-field input:focus {
      border-color: rgba(168,85,247,0.7);
      box-shadow: 0 0 12px rgba(168,85,247,0.15);
    }
    .nq-m-field input::placeholder { color: rgba(148,163,184,0.3); }
    .nq-m-remember {
      display: flex; align-items: center; gap: 8px;
      margin-bottom: 18px; cursor: pointer;
    }
    .nq-m-remember input[type="checkbox"] {
      width: 14px; height: 14px; accent-color: #a855f7;
      cursor: pointer;
    }
    .nq-m-remember span {
      font-size: 11px; color: rgba(148,163,184,0.7);
    }
    .nq-m-btn {
      width: 100%; padding: 12px 0;
      background: linear-gradient(135deg, #7c3aed, #a855f7);
      border: none; border-radius: 8px;
      color: #fff; font-size: 12px; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.15em;
      cursor: pointer; transition: all 0.25s;
      font-family: 'Barlow Condensed', sans-serif;
    }
    .nq-m-btn:hover {
      box-shadow: 0 0 20px rgba(168,85,247,0.5);
      transform: translateY(-1px);
    }
    .nq-m-btn:active { transform: scale(0.98); }
    .nq-m-btn.loading {
      pointer-events: none; opacity: 0.6;
    }
    .nq-m-error {
      background: rgba(239,68,68,0.1);
      border: 1px solid rgba(239,68,68,0.3);
      border-radius: 8px; padding: 8px 12px;
      font-size: 11px; color: #ef4444;
      margin-bottom: 14px; display: none;
      text-align: center;
    }
    .nq-m-error.visible { display: block; }
    .nq-m-close {
      position: absolute; top: 14px; right: 16px;
      background: none; border: none; color: rgba(148,163,184,0.5);
      font-size: 20px; cursor: pointer; transition: color 0.2s;
      font-family: 'Material Symbols Outlined';
    }
    .nq-m-close:hover { color: #f8fafc; }
    .nq-m-success {
      text-align: center; display: none;
    }
    .nq-m-success.active { display: block; }
    .nq-m-success .check { font-size: 52px; color: #34d399; margin-bottom: 10px; }
    .nq-m-success .msg { font-size: 14px; color: #f8fafc; font-weight: 600; }
    .nq-m-form.hidden { display: none; }
  `;
  document.head.appendChild(style);

  // ═══ Inject Modal HTML ═══
  const overlay = document.createElement('div');
  overlay.id = 'nq-auth-overlay';
  const saved = getSavedCreds();
  overlay.innerHTML = `
    <div id="nq-auth-modal" style="position:relative">
      <button class="nq-m-close" onclick="document.getElementById('nq-auth-overlay').classList.remove('active')">close</button>
      <div id="nq-auth-form-area">
        <div class="nq-m-logo-wrap">
          <div class="nq-m-logo-text">
            <span class="ai">IA</span><span class="fundamental">Fundamental</span>
          </div>
        </div>
        <div class="nq-m-title">// ACCESO RESTRINGIDO — NQ WHALE RADAR</div>
        <div id="nq-auth-error" class="nq-m-error"></div>
        <form id="nq-auth-form">
          <div class="nq-m-field">
            <label>Email</label>
            <input type="email" id="nq-auth-email" placeholder="operador@iafundamental.com" value="${saved ? saved.email : ''}" required autocomplete="email">
          </div>
          <div class="nq-m-field">
            <label>Contraseña</label>
            <input type="password" id="nq-auth-pass" placeholder="••••••••" value="${saved ? saved.pass : ''}" required autocomplete="current-password">
          </div>
          <label class="nq-m-remember">
            <input type="checkbox" id="nq-auth-remember" ${saved ? 'checked' : ''}>
            <span>Guardar credenciales</span>
          </label>
          <button type="submit" class="nq-m-btn" id="nq-auth-btn">Ingresar al Terminal</button>
        </form>
      </div>
      <div id="nq-auth-success" class="nq-m-success">
        <div class="check"><span class="material-symbols-outlined" style="font-size:inherit;color:inherit">verified</span></div>
        <div class="msg">Acceso Autorizado</div>
        <div style="font-size:11px;color:rgba(148,163,184,0.7);margin-top:6px" id="nq-auth-welcome">Bienvenido, Operador</div>
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // ═══ Pending navigation target ═══
  let pendingHref = null;

  // ═══ Show modal ═══
  function showAuthModal(href) {
    pendingHref = href;
    overlay.classList.add('active');
    // Reset state
    document.getElementById('nq-auth-form-area').classList.remove('hidden');
    document.getElementById('nq-auth-success').classList.remove('active');
    document.getElementById('nq-auth-error').classList.remove('visible');
    document.getElementById('nq-auth-btn').classList.remove('loading');
    // Focus
    const savedC = getSavedCreds();
    if (savedC && savedC.email && savedC.pass) {
      // If creds are saved, auto-focus submit
      document.getElementById('nq-auth-btn').focus();
    } else {
      setTimeout(() => document.getElementById('nq-auth-email').focus(), 300);
    }
  }

  // ═══ Form submit ═══
  document.getElementById('nq-auth-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = document.getElementById('nq-auth-email').value.trim().toLowerCase();
    const pass = document.getElementById('nq-auth-pass').value;
    const btn = document.getElementById('nq-auth-btn');
    const errEl = document.getElementById('nq-auth-error');
    const remember = document.getElementById('nq-auth-remember').checked;

    errEl.classList.remove('visible');
    btn.classList.add('loading');
    btn.textContent = 'Verificando...';

    await new Promise(r => setTimeout(r, 600));

    const user = USERS[email];
    if (!user) {
      btn.classList.remove('loading');
      btn.textContent = 'Ingresar al Terminal';
      errEl.textContent = 'Email no registrado en el sistema.';
      errEl.classList.add('visible');
      return;
    }

    const h = await sha256(pass);
    if (h !== user.hash) {
      btn.classList.remove('loading');
      btn.textContent = 'Ingresar al Terminal';
      errEl.textContent = 'Contraseña incorrecta.';
      errEl.classList.add('visible');
      return;
    }

    // ✅ Success — save session
    localStorage.setItem(SESSION_KEY, JSON.stringify({
      user: user.name, email, timestamp: Date.now()
    }));

    // Save credentials if checked
    if (remember) {
      localStorage.setItem(SAVED_CREDS_KEY, JSON.stringify({ email, pass }));
    } else {
      localStorage.removeItem(SAVED_CREDS_KEY);
    }

    // Show success
    btn.classList.remove('loading');
    document.getElementById('nq-auth-form-area').classList.add('hidden');
    document.getElementById('nq-auth-welcome').textContent = `Bienvenido, ${user.name}`;
    const suc = document.getElementById('nq-auth-success');
    suc.classList.add('active');

    // Navigate after animation
    setTimeout(() => {
      if (pendingHref) window.location.href = pendingHref;
    }, 1200);
  });

  // Close on overlay click (not modal)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.classList.remove('active');
  });

  // Close on Escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') overlay.classList.remove('active');
  });

  // ═══ Intercept all navigation links ═══
  // Pages that require auth
  const guardedPages = [
    'analisis_promax.html', 'analisis_orderflow.html', 'cot_intel.html',
    'noticias_nasdaq.html', 'pattern_intel.html', 'weekly_backtest.html',
    'curso.html', 'curso_ia.html', 'cross_analysis.html'
  ];

  document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href]');
    if (!link) return;

    const href = link.getAttribute('href');
    if (!href) return;

    // Check if this link points to a guarded page
    const isGuarded = guardedPages.some(p => href.includes(p));
    if (!isGuarded) return;

    // If already authenticated, let it go
    if (hasValidSession()) return;

    // Otherwise: prevent navigation, show modal
    e.preventDefault();
    e.stopPropagation();
    showAuthModal(href);
  }, true); // capture phase to catch before any other handler

  // ═══ Also intercept enterDashboard() if it exists ═══
  const origEnter = window.enterDashboard;
  window.enterDashboard = function () {
    if (hasValidSession()) {
      if (typeof origEnter === 'function') origEnter();
      else document.getElementById('dashboard')?.scrollIntoView({ behavior: 'smooth' });
    } else {
      showAuthModal('#dashboard');
    }
  };

  // Special handling: if pendingHref is '#dashboard', scroll instead of navigate
  const origHrefHandler = window.location;

  // Also intercept any onclick buttons that navigate
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[onclick*="location"]');
    if (!btn) return;
    const onclick = btn.getAttribute('onclick') || '';
    const match = onclick.match(/([\w_]+\.html)/);
    if (!match) return;
    const page = match[1];
    if (!guardedPages.some(p => page.includes(p))) return;
    if (hasValidSession()) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    showAuthModal(page);
  }, true);

  // ═══ Expose auth API ═══
  window.NQ_AUTH = {
    isAuthenticated: hasValidSession,
    logout: function () {
      localStorage.removeItem(SESSION_KEY);
      location.reload();
    }
  };

})();
